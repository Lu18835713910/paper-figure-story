#!/usr/bin/env python3
"""Additive experiment ledger, exact source checks and readable Methods audit.

This is a source-bound supplement to M1, not a second independently rewritable
paper database. It does not parse PDFs or promote extraction to human review.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, re
from collections import Counter
from pathlib import Path
import validate_knowledge as knowledge

VERSION='pfs-experiment-inventory-1'
SCHEMA=Path(__file__).resolve().parents[1]/'schemas/experiment_inventory_v1_1.schema.json'
STATUSES=('VERIFIED','PARTIAL','NOT_REPORTED','NOT_VERIFIED','CONFLICT')
CORE_FIELDS=('question','materials','groups','group_count','sample_count','sample_unit',
             'biological_replicates','technical_replicates','independent_runs',
             'treatments','acquisition','analysis','statistics','result','interpretation','limitations')
COUNT_FIELDS={'group_count','sample_count','biological_replicates','technical_replicates','independent_runs'}
TYPE_MAP={'question':('scientific_question','ScientificQuestion','purpose'),
          'hypothesis':('hypothesis','Hypothesis','purpose'),
          'materials':('material_sample','BiologicalMaterial','design'),
          'system':('experimental_design','ExperimentalSystem','design'),
          'sample_count':('material_sample','Sample','design'),
          'sample_unit':('measurement_readout','Measurement','readout'),
          'groups':('experimental_design','SampleGroup','design'),
          'group_count':('experimental_design','SampleGroup','design'),
          'treatments':('treatment_control','Treatment','design'),
          'controls':('treatment_control','Control','design'),
          'acquisition':('measurement_readout','Measurement','readout'),
          'dataset':('material_sample','Dataset','design'),
          'analysis':('computational_analysis','ComputationalAnalysis','method'),
          'statistics':('computational_analysis','StatisticalTest','method'),
          'result':('observation_result','Observation','result'),
          'interpretation':('scientific_claim','ScientificClaim','interpretation'),
          'limitations':('limitation','Limitation','limitation'),
          'experimental_system':('experimental_design','ExperimentalSystem','design'),
          'measurement_unit':('measurement_readout','Measurement','readout'),
          'material_identity_conflict':('material_sample','BiologicalMaterial','design'),
          'krr_identity':('material_sample','BiologicalMaterial','design'),
          'software_version_conflict':('computational_analysis','ComputationalAnalysis','method'),
          'readout_interpretation':('measurement_readout','Measurement','readout'),
          'methods':('method','Method','method'),
          'results_sources':('evidence_source','EvidenceSource','readout')}
RELATION_IDENTITIES={
 'SCIENTIFIC_EVIDENCE':('evidence',{'supports','contradicts','validates','tested_by','integrates'}),
 'DATA_DEPENDENCY':('data_dependency',{'derived_from','depends_on'}),
 'EXPERIMENTAL_COMPARISON':('association',{'uses','compares','measures','parallel_to'}),
 'AUTHOR_INTERPRETATION':('author_argument',{'motivates','integrates','supports','compares'}),
 'PRESENTATION_ORDER':('presentation',{'motivates','integrates','compares'}),
 'UNVERIFIED_HYPOTHESIS':('mechanism_hypothesis',{'hypothesizes'})}

class InventoryError(ValueError):
    def __init__(self,code,message):super().__init__(message);self.code=code

def _need(ok,code,message):
    if not ok:raise InventoryError(code,message)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def fingerprint(obj):return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def _read(path):return knowledge.load_json(Path(path))
def _unique(values):return list(dict.fromkeys(values))
def _path(value,base):
    p=Path(value);return (p if p.is_absolute() else Path(base)/p).resolve()

def _refs(field):return field.get('source_refs',[]) if isinstance(field,dict) else []
def _text(value):
    if value is None:return '—'
    return value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,sort_keys=True)

def _has_numeric(value):
    if type(value) in (int,float):return True
    if isinstance(value,list):return any(_has_numeric(x) for x in value)
    if isinstance(value,dict):return any(_has_numeric(x) for x in value.values())
    return bool(re.search(r'\d',value)) if isinstance(value,str) else False

def _source_check(ref,documents,*,base_dir,knowledge_dir,verify_files,cache):
    did=ref.get('document_id');_need(did in documents,'INVENTORY_DOCUMENT','Unregistered source document')
    doc=documents[did];page=ref.get('physical_page',ref.get('locator',{}).get('physical_page'))
    _need(type(page) is int and 1<=page<=doc.get('physical_page_count',0),'INVENTORY_PAGE','Physical page outside registered PDF')
    _need(doc.get('format')=='pdf' and doc.get('availability')=='available','INVENTORY_SOURCE_UNAVAILABLE','Source must be an available registered PDF')
    if ref.get('document_sha256') is not None:_need(ref['document_sha256']==doc['sha256'],'INVENTORY_PDF_SHA','Source refers to another PDF')
    if verify_files and did not in cache['documents']:
        pdf=_path(doc['path'],knowledge_dir)
        _need(pdf.is_file() and sha(pdf)==doc['sha256'],'INVENTORY_PDF_SHA','Registered PDF changed')
        cache['documents'].add(did)
    p=_path(ref.get('path',''),base_dir)
    _need(p.name==f'page-{page:02d}.txt','INVENTORY_CACHE_PAGE','Page number and page-cache filename must agree')
    if str(p) not in cache['pages']:
        _need(p.is_file() and sha(p)==ref.get('sha256'),'INVENTORY_CACHE_SHA','Exact source page fingerprint required')
        metadata=p.parent/'metadata.json'
        _need(metadata.is_file() and _read(metadata).get('sha256')==doc['sha256'],'INVENTORY_CACHE_DOCUMENT','Cache metadata must bind the registered PDF')
        cache['pages'][str(p)]=(p.read_text(encoding='utf-8-sig'),sha(p))
    text,digest=cache['pages'][str(p)]
    _need(digest==ref.get('sha256'),'INVENTORY_CACHE_SHA','Source page hash differs')
    start,end=ref.get('start'),ref.get('end');excerpt=ref.get('excerpt')
    _need(type(start) is int and type(end) is int and 0<=start<end<=len(text) and text[start:end]==excerpt,
          'INVENTORY_SOURCE_SPAN','Exact Unicode source excerpt and range required')
    if ref.get('excerpt_sha256') is not None:_need(hashlib.sha256(excerpt.encode()).hexdigest()==ref['excerpt_sha256'],'INVENTORY_EXCERPT_SHA','Excerpt hash differs')
    return {'document_id':did,'locator':{'physical_page':page,'section':ref.get('section',''),
            'context_sha256':hashlib.sha256(excerpt.encode()).hexdigest()},'verification':'pending',
            'document_sha256':doc['sha256'],'source_cache_ref':{**copy.deepcopy(ref),'path':str(p),'physical_page':page},
            'check_scope':'exact_file_location_and_excerpt_only_not_independent_semantic_review'}

def _validate(inventory,model,*,base_dir,knowledge_path=None,verify_files=True):
    schema=_read(SCHEMA);knowledge.check_schema(schema);errors=knowledge.schema_errors(inventory,schema)
    _need(not errors,'INVENTORY_SCHEMA',str(errors))
    _need(inventory['paper_id']==model['document_registry'][0]['id'],'INVENTORY_PAPER','Inventory binds another paper')
    if knowledge_path is not None:_need(inventory['knowledge_sha256']==sha(knowledge_path),'INVENTORY_KNOWLEDGE_DRIFT','Inventory binds another M1 file')
    _need(not inventory.get('formal_ready',False),'INVENTORY_REVIEW_PROMOTION','Inventory cannot promote human scientific review')
    docs={d['id']:d for d in model['document_registry']};entities={e['id']:e for e in model['entities']};figures={f['id'] for f in model['figures']}
    kdir=Path(knowledge_path).resolve().parent if knowledge_path else Path(base_dir)
    cache={'documents':set(),'pages':{}};ids=set();source_rows={};warnings=[]
    for i,e in enumerate(inventory['experiments']):
        eid=e['experiment_id'];_need(eid not in ids and eid not in entities,'INVENTORY_ID','Duplicate experiment or M1 entity collision');ids.add(eid)
        _need(e.get('m1_evidence_ids') and all(n in entities and entities[n]['kind']=='evidence' for n in e['m1_evidence_ids']),
              'INVENTORY_M1_BINDING','Experiment must link existing evidence entities')
        _need(set(e.get('figure_ids',[]))<=figures,'INVENTORY_FIGURE','Unregistered Figure')
        refs=[]
        for key,f in e['fields'].items():
            _need(isinstance(f,dict) and f.get('status') in STATUSES and 'value' in f and isinstance(f.get('source_refs'),list),
                  'INVENTORY_FIELD_FORMAT','Every source field must declare value, valid status and source_refs')
            fspec={'$ref':'#/$defs/field','$defs':schema['$defs']}
            _need(not knowledge.schema_errors(f,fspec),'INVENTORY_FIELD_FORMAT','Invalid field source/status structure')
            status=f['status'];value=f.get('value');rawrefs=_refs(f)
            if status=='VERIFIED':_need(value not in (None,'',[],{}) and rawrefs,'INVENTORY_VERIFIED_SOURCE','VERIFIED requires an actual value and source excerpt')
            if status=='PARTIAL':_need(rawrefs,'INVENTORY_PARTIAL_SOURCE','PARTIAL needs some located support; otherwise use NOT_VERIFIED')
            if status in ('NOT_VERIFIED','NOT_REPORTED','CONFLICT'):_need(bool(f.get('reason') or f.get('review_scope')),'INVENTORY_STATUS_REASON','Missing/conflict status needs an explicit reason/scope')
            if status=='NOT_REPORTED':
                _need(bool(rawrefs),'INVENTORY_NOT_REPORTED_SCOPE','NOT_REPORTED needs actually checked source scope, not merely missing extraction')
                _need(not _has_numeric(value),'INVENTORY_NOT_REPORTED_NUMBER','NOT_REPORTED cannot supply a numeric count')
            if status=='CONFLICT':_need(bool(f.get('candidates') or isinstance(value,(list,dict))), 'INVENTORY_CONFLICT_CANDIDATES','Conflicting candidates must be retained, not silently selected')
            if key in COUNT_FIELDS and status in ('VERIFIED','PARTIAL') and _has_numeric(value):
                unit=f.get('unit') or (e['fields'].get('sample_unit',{}).get('value') if key=='sample_count' else None)
                _need(bool(unit),'INVENTORY_COUNT_UNIT','Counts require their actual statistical unit')
                derivation=str(f.get('derivation',''))+' '+str(f.get('counting_basis',''))
                _need(not any(x in derivation.lower() for x in ('plotted_points','scatter_count','counted_from_plot','图中散点')),'INVENTORY_DOT_COUNT','Plot dots cannot be promoted to sample or replicate counts')
                if key in ('biological_replicates','technical_replicates','independent_runs'):
                    illegal=('particle','micrograph','spot','structure','dataset','condition','measurement','cells','细胞数','粒子','视野','散点')
                    _need(not any(x in str(unit).lower() for x in illegal),'INVENTORY_REPLICATE_UNIT','Measurement/data units are not biological or run replication')
            normalized=[_source_check(r,docs,base_dir=base_dir,knowledge_dir=kdir,verify_files=verify_files,cache=cache) for r in rawrefs]
            source_rows[(eid,key)]=normalized;refs+=normalized
        _need(refs,'INVENTORY_EXPERIMENT_SOURCE','Each substantive task must have located sources')
        for ref in e.get('methods_refs',[]):_source_check(ref,docs,base_dir=base_dir,knowledge_dir=kdir,verify_files=verify_files,cache=cache)
        if not e['fields'].get('sample_count'):warnings.append({'code':'INVENTORY_SAMPLE_UNCHECKED','experiment_id':eid})
    for section in inventory.get('method_sections',[]):
        _need(set(section.get('experiment_ids',[]))<=ids,'INVENTORY_METHOD_MEMBERSHIP','Method section names an unknown experiment')
        _need(section.get('source_refs'),'INVENTORY_METHOD_SOURCE','Method audit section requires a real source scope')
        for ref in section['source_refs']:_source_check(ref,docs,base_dir=base_dir,knowledge_dir=kdir,verify_files=verify_files,cache=cache)
    for missing in inventory.get('missing_materials',[]):
        if isinstance(missing,dict):_need(set(missing.get('affected_experiment_ids',[]))<=ids,'INVENTORY_MISSING_MEMBERSHIP','Missing material affects an unknown experiment')
    seen=set();valid_nodes=ids|set(entities)
    for e in inventory['experiments']:valid_nodes.update(e['experiment_id']+'::'+key for key in e['fields'])
    for relation in inventory.get('relations',[]):
        _need(relation['id'] not in seen,'INVENTORY_RELATION_ID','Duplicate supplemental relation');seen.add(relation['id'])
        _need(relation['from'] in valid_nodes and relation['to'] in valid_nodes and relation['from']!=relation['to'],'INVENTORY_RELATION_ENDPOINT','Unknown/self relation endpoint')
        identity=relation['identity'];_need(identity in RELATION_IDENTITIES,'INVENTORY_RELATION_IDENTITY','Unknown relationship identity')
        _need(relation['type'] in RELATION_IDENTITIES[identity][1],'INVENTORY_RELATION_ESCALATION','Relationship type cannot be promoted by presentation identity')
        _need(not relation.get('causal_claim',False),'INVENTORY_CAUSAL','This ledger does not authorize causal review promotion')
        _need(relation.get('source_refs'),'INVENTORY_RELATION_SOURCE','Relationship requires sources, including presentation arrangement basis')
        for ref in relation['source_refs']:_source_check(ref,docs,base_dir=base_dir,knowledge_dir=kdir,verify_files=verify_files,cache=cache)
        if identity=='DATA_DEPENDENCY':_need(relation.get('dependency_basis')=='explicit_output_input','INVENTORY_IO_BASIS','Data dependency requires explicitly sourced output/input evidence')
        if identity=='UNVERIFIED_HYPOTHESIS':_need(relation.get('evidence_status') in ('PARTIAL','NOT_VERIFIED'),'INVENTORY_HYPOTHESIS_PROMOTION','Hypothesis cannot become VERIFIED mechanism')
    return source_rows,warnings

def validate_inventory(inventory,model,*,base_dir='.',knowledge_path=None,verify_files=True):
    try:
        _,warnings=_validate(inventory,model,base_dir=base_dir,knowledge_path=knowledge_path,verify_files=verify_files)
        return {'valid':True,'errors':[],'warnings':warnings+[{'code':'INDEPENDENT_SEMANTICS_PENDING','message':'Exact excerpts and field status do not establish human scientific final review.'}],
                'formal_ready':False,'source_location_check':'PASS','independent_scientific_review':'NOT_TESTED'}
    except (OSError,ValueError,KeyError,TypeError,IndexError) as exc:
        return {'valid':False,'errors':[{'code':getattr(exc,'code','INVENTORY_INPUT'),'message':str(exc)}],'warnings':[],'formal_ready':False}

def _status(fields):
    values=[f.get('status','NOT_VERIFIED') for f in fields.values()]
    for v in ('CONFLICT','NOT_VERIFIED','PARTIAL','NOT_REPORTED'):
        if v in values:return v
    return 'VERIFIED'

def _methods_refs(inventory,e):
    result=list(e.get('methods_refs',[]))
    for key in ('methods','methods_sources','methods_refs'):result+=_refs(e['fields'].get(key,{}))
    for s in inventory.get('method_sections',[]):
        if e['experiment_id'] in s.get('experiment_ids',[]):result+=s.get('source_refs',[])
    return result

def _is_methods_source(ref):
    section=str(ref.get('section',ref.get('locator',{}).get('section','')))
    if re.search(r'\b(?:STAR\s+Methods|Materials\s+and\s+Methods|Methods)\b',section,re.I):return True
    if re.search(r'\bResults?\b|legend|Figure',section,re.I):return False
    try:
        text=Path(ref['path']).read_text(encoding='utf-8-sig')
        return bool(re.search(r'(?im)^\s*(?:STAR\s*.?\s*METHODS|MATERIALS\s+AND\s+METHODS|METHOD\s+DETAILS|EXPERIMENTAL MODEL AND STUDY PARTICIPANT DETAILS|QUANTIFICATION AND STATISTICAL ANALYSIS)\s*$',text))
    except (KeyError,OSError):return False

def _applicable(e,key):
    f=e['fields'].get(key,{})
    if f.get('applicable') is False:return False
    # Computational tasks have data/analysis units; they are not wet-lab
    # biological/technical replication unless explicitly marked applicable.
    if e.get('task_type') in ('computational_analysis','shared_computational_workflow') and key in ('group_count','biological_replicates','technical_replicates','independent_runs'):
        return f.get('applicable') is True
    return True

def audit_inventory(inventory):
    es=inventory['experiments'];n=len(es);fields={k:Counter() for k in CORE_FIELDS};appcounts={k:Counter() for k in CORE_FIELDS};excluded={k:[] for k in CORE_FIELDS}
    methods=0;actual_methods=0;method_status=Counter();rows=[]
    missing_ids={eid for m in inventory.get('missing_materials',[]) if isinstance(m,dict) for eid in m.get('affected_experiment_ids',[])}
    for e in es:
        for k in CORE_FIELDS:
            status=e['fields'].get(k,{}).get('status','NOT_VERIFIED');fields[k][status]+=1
            if _applicable(e,k):appcounts[k][status]+=1
            else:excluded[k].append(e['experiment_id'])
        mrefs=_methods_refs(inventory,e);methods+=bool(mrefs)
        actual=any(_is_methods_source(r) for r in mrefs);actual_methods+=actual
        ms=e.get('method_source_status',e['fields'].get('methods',{}).get('status','NOT_VERIFIED'))
        if not actual:ms='PARTIAL' if mrefs else 'NOT_VERIFIED'
        relevant=[s for s in inventory.get('method_sections',[]) if e['experiment_id'] in s.get('experiment_ids',[]) and not re.search('Results|legend',s.get('section',''),re.I)]
        if ms=='VERIFIED' and (e['experiment_id'] in missing_ids or any(s.get('status')!='VERIFIED' for s in relevant)):ms='PARTIAL'
        method_status[ms]+=1
        rows.append({'experiment_id':e['experiment_id'],'task':e['display_name'],'task_type':e['task_type'],
                     'm1_evidence_ids':e['m1_evidence_ids'],'figure_ids':e.get('figure_ids',[]),
                     'methods_located':bool(mrefs),'methods_refs':mrefs,
                     'actual_methods_source_located':actual,'method_source_status':ms,
                     'field_status':{k:e['fields'].get(k,{}).get('status','NOT_VERIFIED') for k in CORE_FIELDS},
                     'overall_extraction_status':_status(e['fields'])})
    byfield={k:{'denominator':n,**{s:c.get(s,0) for s in STATUSES},'applicable_denominator':n-len(excluded[k]),
               'applicable_status_counts':{s:appcounts[k].get(s,0) for s in STATUSES},'not_applicable_experiment_ids':excluded[k]} for k,c in fields.items()}
    known=[e['experiment_id'] for e in es if e['fields'].get('sample_count',{}).get('status')=='VERIFIED' and _applicable(e,'sample_count')]
    conflict=[e['experiment_id'] for e in es if any(f.get('status')=='CONFLICT' for f in e['fields'].values())]
    needed=_unique(eid for m in inventory.get('missing_materials',[]) if isinstance(m,dict) for eid in m.get('affected_experiment_ids',[]))
    key_results=[e for e in es if e['fields'].get('result',{}).get('value') is not None]
    result_bound=sum(bool(_refs(e['fields']['result'])) for e in key_results)
    summary={'experiment_count':n,'experiment_ids':[e['experiment_id'] for e in es],
             'counting_policy':inventory.get('counting_policy','Task, not Figure/panel/condition/dot count.'),
             'task_type_counts':dict(Counter(e['task_type'] for e in es)),
             'methods_localization':{'numerator':methods,'denominator':n,'status':'located_only_not_full_semantic_verification'},
             'actual_methods_source_localization':{'numerator':actual_methods,'denominator':n,'scope':'Methods/STAR source distinguished from Results/legend-only location'},
             'method_source_status_counts':{'denominator':n,**{s:method_status.get(s,0) for s in STATUSES},'scope':'Extractor Methods scope, not independent scientific final review; missing supplement/partial section downgrades completeness'},
             'field_status_counts':byfield,'verified_sample_count_experiment_ids':known,'conflicting_experiment_ids':conflict,
             'supplement_needed_experiment_ids':needed,'key_result_binding':{'numerator':result_bound,'denominator':len(key_results)},
             'identification_coverage':{'status':'PARTIAL','denominator':'all substantive tasks in inspected corpus; total not independently certified','registered_tasks':n},
             'methods_bidirectional_coverage':{'inspected_sections':len(inventory.get('method_sections',[])),
                 'sections_with_registered_experiments':sum(bool(s.get('experiment_ids')) for s in inventory.get('method_sections',[])),
                 'section_records':copy.deepcopy(inventory.get('method_sections',[])),
                 'experiments_without_actual_methods_source':[r['experiment_id'] for r in rows if not r['actual_methods_source_located']]},
             'methods_completeness':'PARTIAL','independent_scientific_review':'NOT_TESTED','formal_ready':False}
    md=['# Full Experimental Inventory审查','',
        '字段VERIFIED表示本轮提取者认为原文支持，并经机器核对位置/摘录；不等于独立人工科学终审。缺提取字段一律NOT_VERIFIED，不自动变成NOT_REPORTED。','',
        '任务划分口径：'+_text(summary['counting_policy']),'',
        f'登记 {n} 项任务；来源定位 {methods}/{n}，其中实为Methods/STAR来源 {actual_methods}/{n}（Results/legend-only单列）；有值关键结果来源绑定 {result_bound}/{len(key_results)}。识别覆盖分母未独立认证，不能仅以这些登记任务作为“全文100%覆盖”的证明。','',
        '|Experiment ID|实质任务|对象|组数|样本量/单位|生物学重复|技术重复|独立次数|Methods定位|统计|结果|状态|',
        '|---|---|---|---|---|---|---|---|---|---|---|---|']
    def val(e,k):
        f=e['fields'].get(k,{});return (_text(f.get('value'))+' ['+f.get('status','NOT_VERIFIED')+']').replace('|','／').replace('\n','<br>')
    for e,r in zip(es,rows):
        md.append('|'+ '|'.join([e['experiment_id'],e['display_name'],val(e,'materials'),val(e,'group_count'),val(e,'sample_count')+' / '+val(e,'sample_unit'),val(e,'biological_replicates'),val(e,'technical_replicates'),val(e,'independent_runs'),('Methods/STAR ' if r['actual_methods_source_located'] else '仅Results/legend或尚未定位 ')+r['method_source_status'],val(e,'statistics'),val(e,'result'),r['overall_extraction_status']])+'|')
    md+=['','## 分状态统计（所有分母分别列明）','','|字段|分母|VERIFIED|PARTIAL|NOT_REPORTED|NOT_VERIFIED|CONFLICT|','|---|---:|---:|---:|---:|---:|---:|']
    for key,v in byfield.items():md.append('|'+key+'|'+str(n)+'|'+'|'.join(str(v[s]) for s in STATUSES)+'|')
    md+=['','## 适用任务分母（不把计算任务当湿实验重复）','','|字段|适用分母|VERIFIED|PARTIAL|NOT_REPORTED|NOT_VERIFIED|CONFLICT|排除ID|','|---|---:|---:|---:|---:|---:|---:|---|']
    for key,v in byfield.items():md.append('|'+key+'|'+str(v['applicable_denominator'])+'|'+'|'.join(str(v['applicable_status_counts'][s]) for s in STATUSES)+'|'+','.join(v['not_applicable_experiment_ids'])+'|')
    md+=['','Methods来源完整度分状态：'+_text(summary['method_source_status_counts']),
         '','定义：VERIFIED仅表示已定位实际Methods且该任务的已登记方法范围已核实；有缺补资料/部分方法小节时降为PARTIAL。不是独立人工终审，也不以7/7找到ref冒充7/7完整方法。']
    md+=['','## 每项可核实细节与来源','']
    for e in es:
        md += ['### '+e['experiment_id']+' '+e['display_name'],'']
        for key,f in e['fields'].items():
            md += ['- **'+key+'**：'+_text(f.get('value'))+' ['+f['status']+']'+('；单位：'+_text(f['unit']) if f.get('unit') else ''),
                   '  - '+('；'.join(r.get('document_id','')+' p.'+str(r.get('physical_page'))+' '+Path(r.get('path','')).name+' chars '+str(r.get('start'))+':'+str(r.get('end')) for r in _refs(f)) or '来源尚未完成定位')]
            if f.get('reason'):md+=['  - 状态依据：'+str(f['reason'])]
            if f.get('candidates'):md+=['  - 冲突候选：'+_text(f['candidates'])]
        md+=['']
    md+=['## 缺失补充材料及影响','',_text(inventory.get('missing_materials',[])),
         '','## Methods双向核查','',_text(inventory.get('method_sections',[])),
         '','所有原文片段保存在Inventory JSON及来源缓存；本表不是补充资料已经齐全或样本量全部已核的声明。']
    return {'summary':summary,'rows':rows,'markdown':'\n'.join(md)+'\n'}

def write_audit(inventory,output_dir,*,validation=None):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True);result=audit_inventory(inventory)
    jp=out/'Full_Experimental_Inventory.json';mp=out/'FULL_EXPERIMENT_INVENTORY_AUDIT.md';ap=out/'inventory_audit.json'
    jp.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    mp.write_text(result.pop('markdown'),encoding='utf-8');result['validation']=validation
    ap.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {'json_path':str(jp),'markdown_path':str(mp),'audit_path':str(ap),'summary':result['summary']}

def build_experiment_layer(inventory,model,*,base_dir='.',knowledge_path=None,verify_files=True):
    refs,warnings=_validate(inventory,model,base_dir=base_dir,knowledge_path=knowledge_path,verify_files=verify_files)
    nodes=[];associations=[];statements=[];edges=[];experiments=copy.deepcopy(inventory['experiments'])
    for i,e in enumerate(experiments):
        eid=e['experiment_id'];allrefs=list({fingerprint(r):r for key in e['fields'] for r in refs[(eid,key)]}.values());conditions=e['fields'].get('treatments',{}).get('value')
        node={'id':eid,'stable_id':eid,'kind':'experiment','entity_type':'Experiment' if e['task_type']!='computational_analysis' else 'ComputationalAnalysis',
              'label':e['display_name'],'display_name':e['display_name'],'source_refs':allrefs,'identity':'experiment_source_view',
              'm1_pointer':f'/experiments/{i}','source_pointer':{'input_kind':'experiment_inventory','pointer':f'/experiments/{i}'},
              'evidence_status':_status(e['fields']),'applicable_conditions':conditions,'experiment_id':eid,
              'm1_evidence_ids':e['m1_evidence_ids'],'figure_ids':e.get('figure_ids',[]),'details':e['display_name'],'parameters':[],'quantities':[],
              'group_ids':[eid+'::groups'] if 'groups' in e['fields'] else [],
              'group_reference_scope':'source field containing the declared groups, not invented individual sample IDs',
              'sample_count':copy.deepcopy(e['fields'].get('sample_count',{}).get('value')),
              'sample_unit':copy.deepcopy(e['fields'].get('sample_unit',{}).get('value')),
              'biological_replicates':copy.deepcopy(e['fields'].get('biological_replicates',{}).get('value')),
              'technical_replicates':copy.deepcopy(e['fields'].get('technical_replicates',{}).get('value')),
              'independent_runs':copy.deepcopy(e['fields'].get('independent_runs',{}).get('value')),
              'quantity_field_status':{k:e['fields'].get(k,{}).get('status','NOT_VERIFIED') for k in sorted(COUNT_FIELDS|{'sample_unit'})},
              'inputs':[],'outputs':[],'limits':[],'analysis_unit':'not_checked','methods_refs':_methods_refs(inventory,e),
              'results_refs':copy.deepcopy(_refs(e['fields'].get('result',{}))+_refs(e['fields'].get('results_sources',{}))),
              'review':{'formal_ready':False,'independent_scientific_review':False,'semantic_review_status':'PARTIAL'}}
        nodes.append(node)
        for mid in e['m1_evidence_ids']:
            associations.append({'id':'INV.ASSOC.'+eid+'.'+mid,'from':eid,'to':mid,'type':'documents_existing_evidence',
                                 'identity':'association','basis_pointer':f'/experiments/{i}/m1_evidence_ids','scientific_dependency':False,'scope':'source_record_membership_only'})
        for key,f in e['fields'].items():
            fid=eid+'::'+key;kind,etype,role=TYPE_MAP.get(key,('experimental_design','ExperimentalSystem','design'));text=_text(f.get('value'))
            n={'id':fid,'stable_id':fid,'kind':kind,'entity_type':etype,'label':key+': '+text,'display_name':key+': '+text,
               'source_refs':refs[(eid,key)],'identity':'experiment_source_view','owner_id':eid,'experiment_id':eid,
               'm1_pointer':f'/experiments/{i}/fields/{key}','source_pointer':{'input_kind':'experiment_inventory','pointer':f'/experiments/{i}/fields/{key}'},
               'evidence_status':f['status'],'applicable_conditions':conditions,'details':text,'parameters':[],'quantities':[],
               'analysis_unit':f.get('unit','not_checked'),'inputs':[],'outputs':[],'limits':[],'source_field':copy.deepcopy(f)}
            nodes.append(n);associations.append({'id':'INV.ASSOC.'+fid,'from':eid,'to':fid,'type':'has_experiment_field','identity':'association',
                                                'basis_pointer':n['m1_pointer'],'scientific_dependency':False,'scope':'registered_field_membership_only'})
            if f.get('value') not in (None,'',[],{}) and f['status'] not in ('NOT_VERIFIED','NOT_REPORTED'):
                statements.append({'id':'INV.'+fid,'text':text,'role':role,'entity_ids':[eid]+e['m1_evidence_ids'],'rsu_ids':[],
                    'figure_ids':e.get('figure_ids',[]),'source_refs':refs[(eid,key)],
                    'source_pointer':{'input_kind':'experiment_inventory','pointer':f'/experiments/{i}/fields/{key}/value'},
                    'review':{'status':'PARTIAL','source_file_status':'exact_cache_and_pdf_checked' if verify_files else 'cache_checked_pdf_not_rechecked',
                              'text_support':'EXTRACTOR_ASSERTED_NOT_INDEPENDENTLY_FINAL_REVIEWED','semantic_review_status':'PARTIAL','independent_scientific_review':False},
                    'depth':'full','critical':False,'assertion_kind':'curated_experiment_source_record','extraction_status':f['status']})
    docs={d['id']:d for d in model['document_registry']};cache={'documents':set(),'pages':{}};kdir=Path(knowledge_path).resolve().parent if knowledge_path else Path(base_dir)
    for r in inventory.get('relations',[]):
        rr=copy.deepcopy(r);rr['inventory_identity']=r['identity'];rr['identity']=RELATION_IDENTITIES[r['identity']][0]
        rr['source_refs']=[_source_check(s,docs,base_dir=base_dir,knowledge_dir=kdir,verify_files=verify_files,cache=cache) for s in r['source_refs']]
        rr['registered_in_m1']=False;rr['certainty']='source_bound_candidate_needs_review';rr['formal_ready']=False;edges.append(rr)
    return {'version':VERSION,'experiments':experiments,'nodes':nodes,'associations':associations,'relations':edges,
            'statements':statements,'audit':audit_inventory(inventory)['summary'],'method_sections':copy.deepcopy(inventory.get('method_sections',[])),
            'missing_materials':copy.deepcopy(inventory.get('missing_materials',[])),
            'review':{'formal_ready':False,'semantic_review_status':'PARTIAL','independent_scientific_review':'NOT_TESTED','warnings':warnings},
            'boundary':'Additive exact-source experiment records; M1 objects/relations and RSUs are not replaced.'}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inventory',required=True,type=Path);p.add_argument('--knowledge',required=True,type=Path);p.add_argument('--audit-dir',type=Path)
    a=p.parse_args(argv)
    try:
        inv=_read(a.inventory);model=_read(a.knowledge);report=validate_inventory(inv,model,base_dir=a.inventory.parent,knowledge_path=a.knowledge)
        if report['valid'] and a.audit_dir:
            protected={a.inventory.resolve(),a.knowledge.resolve()}|{_path(d['path'],a.knowledge.parent) for d in model['document_registry'] if d.get('path')}
            protected.update(_path(r['path'],a.inventory.parent) for e in inv['experiments'] for f in e['fields'].values() for r in _refs(f))
            targets={a.audit_dir.resolve()/n for n in ('Full_Experimental_Inventory.json','FULL_EXPERIMENT_INVENTORY_AUDIT.md','inventory_audit.json')}
            _need(not protected.intersection(targets),'INVENTORY_OUTPUT_COLLISION','Audit output cannot overwrite an input or source')
            report['outputs']=write_audit(inv,a.audit_dir,validation=report)
        print(json.dumps(report,ensure_ascii=False));return 0 if report['valid'] else 2
    except (OSError,ValueError,TypeError,KeyError) as exc:print(json.dumps({'valid':False,'message':str(exc)}));return 2
if __name__=='__main__':raise SystemExit(main())
