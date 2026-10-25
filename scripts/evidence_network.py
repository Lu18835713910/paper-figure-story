#!/usr/bin/env python3
"""Versioned, source-bound read view over M1 and optional M2-C. No PDF reasoning."""
from __future__ import annotations
import argparse, copy, hashlib, json, re
from pathlib import Path
import validate_knowledge as knowledge
import plan_research as planning
import plan_narrative as narrative
VERSION='pfs-evidence-network-1'
SCHEMA=Path(__file__).resolve().parents[1]/'schemas/evidence_network_v1_1.schema.json'
ROLES=('purpose','design','method','readout','result','interpretation','limitation')
class NetworkError(ValueError):
    def __init__(self,code,message): super().__init__(message); self.code=code

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def fingerprint(value): return planning.fingerprint(value)
def _need(ok,code,message):
    if not ok: raise NetworkError(code,message)
def _path(value,base):
    p=Path(value);return (p if p.is_absolute() else Path(base)/p).resolve()
def _source_review(refs,*,inherited=None):
    values=sorted({r.get('verification','unknown') for r in refs})
    return {'status':'PARTIAL','source_file_status':'inherited_locator_only','inherited_verifications':values,
            'inherited_direct_checked':'direct_checked' in values,'text_support':'NOT_TESTED_THIS_RUN',
            'panel_mapping':'NOT_TESTED_THIS_RUN','image_visual':'NOT_TESTED_THIS_RUN',
            'semantic_review_status':'PARTIAL','independent_scientific_review':False,
            'inherited_review':copy.deepcopy(inherited)}
def _role(kind):
    return {'dataset':'design','sample_or_subject':'design','intervention':'design','method':'method','assay':'method',
            'processing':'method','model':'method','evaluation':'readout','evidence':'result','claim':'interpretation'}[kind]
def _facet_kind(kind):
    return {'dataset':'material_sample','sample_or_subject':'material_sample','intervention':'treatment_control',
            'method':'experimental_design','assay':'measurement_readout','processing':'computational_analysis',
            'model':'computational_analysis','evaluation':'measurement_readout','evidence':'observation_result','claim':'scientific_claim'}[kind]
def _display_parameter(p):
    status=p.get('status','not_checked')
    if status=='not_checked': value='待核实'
    elif status=='not_reported':value='原文未报告（继承记录）'
    elif status=='not_applicable':value='不适用'
    else:value=p.get('value') if isinstance(p.get('value'),str) else json.dumps(p.get('value'),ensure_ascii=False,sort_keys=True)
    return str(p.get('key','parameter'))+'：'+str(value)

ANNOTATIONS_VERSION='pfs-relation-annotations-1'
SEMANTIC_TYPES=('uses','measures','derived_from','observes','supports','contradicts','validates_or_tests','depends_on','parallel_to','motivates','integrates','hypothesizes','compares','experimental_precedes')
def _annotation_edges(doc,model,nodes,*,base_dir,knowledge_dir,check_files):
    schema=knowledge.load_json(SCHEMA);spec={'$ref':'#/$defs/relation_annotations_input','$defs':schema['$defs']}
    failures=knowledge.schema_errors(doc,spec)
    _need(not failures,'ANNOTATIONS_FORMAT',str(failures))
    _need(doc['knowledge_snapshot']==fingerprint(model),'ANNOTATIONS_KNOWLEDGE_DRIFT','Annotations name another M1 snapshot')
    node_ids={n['id'] for n in nodes};registered={r['id']:r for r in model['relations']};documents={d['id']:d for d in model['document_registry']}
    seen=set(registered);result=[]
    allowed={'association':{'uses','measures','compares'},'data_dependency':{'derived_from','depends_on'},
             'experimental_order':{'experimental_precedes'},'evidence':{'observes','supports','contradicts','validates_or_tests','parallel_to','integrates','compares'},
             'mechanism_hypothesis':{'hypothesizes'},'author_argument':{'motivates','supports','contradicts','integrates','compares'},
             'presentation':{'motivates','integrates','compares'}}
    for a in doc['relations']:
        _need(a['id'] not in seen,'ANNOTATION_ID','Annotation cannot overwrite a registered or earlier relation ID');seen.add(a['id'])
        _need(a['from'] in node_ids and a['to'] in node_ids and a['from']!=a['to'],'ANNOTATION_ENDPOINT','Existing distinct node endpoints required')
        kind,identity=a['semantic_type'],a['identity']
        _need(kind in allowed[identity],'ANNOTATION_IDENTITY','Semantic type incompatible with relation identity; presentation cannot manufacture scientific dependency or causality')
        _need(not a.get('causal_claim',False),'ANNOTATION_CAUSAL','This candidate contract does not authorize causal validation')
        refs=[]
        for s in a['source_refs']:
            d=documents.get(s['document_id']);_need(d is not None,'ANNOTATION_DOCUMENT','Source document is unregistered')
            page=s['locator']['physical_page']
            _need(d['format']=='pdf' and type(page) is int and 1<=page<=d.get('physical_page_count',0),'ANNOTATION_PAGE','Exact physical PDF page within registered range required')
            _need(d['availability']=='available' and s['document_sha256']==d['sha256'],'ANNOTATION_SOURCE_SHA','Annotation must name the provided registered source fingerprint')
            if check_files:
                p=_path(d['path'],knowledge_dir);_need(p.is_file() and digest(p)==d['sha256'],'ANNOTATION_SOURCE_SHA','Registered source PDF changed')
            c=s['cache'];p=_path(c['path'],base_dir)
            _need(p.is_file() and digest(p)==c['sha256'],'ANNOTATION_CACHE_SHA','Exact cache file fingerprint required')
            text=p.read_text(encoding='utf-8-sig');start,end=c['start'],c['end']
            _need(type(start) is int and type(end) is int and 0<=start<end<=len(text) and text[start:end]==c['excerpt'] and hashlib.sha256(c['excerpt'].encode('utf-8')).hexdigest()==c['excerpt_sha256'],'ANNOTATION_CACHE_SPAN','Cache excerpt and Unicode character span do not match')
            src=copy.deepcopy(s);src['cache']['path']=str(p);refs.append(src)
        out=copy.deepcopy(a);out['type']=kind;out['source_refs']=refs;out['registered_in_m1']=False;out['creates_new_registered_relation']=False
        out['relation_domain']=identity;out['certainty']='presentation_only' if identity=='presentation' else 'association_only' if identity=='association' else 'inferred_needs_review'
        out['provenance']='presentation' if identity=='presentation' else 'paper'
        out['scientific_dependency']=identity=='data_dependency';out['review']['formal_ready']=False
        out['review']['cache_span_check']='EXACT_LOCATION_AND_TEXT_ONLY_NOT_SEMANTIC_PROOF'
        if identity=='data_dependency':
            contract=a.get('io_contract');_need(isinstance(contract,dict),'ANNOTATION_IO_REQUIRED','depends_on/derived_from require an explicit registered M1 I/O contract')
            old=registered.get(contract['source_relation_id'])
            _need(old is not None and old['type']=='data_depends_on' and old['from']==a['from'] and old['to']==a['to'],'ANNOTATION_IO_DIRECTION','Registered producer-to-consumer relation must exactly match')
            _need(contract['data_bindings']==old.get('data_bindings'),'ANNOTATION_IO_BINDING','Declared bindings must exactly match registered producer outputs and consumer inputs')
            out['source_relation_id']=old['id'];out['is_alias_of_registered_relation']=True;out['direction_convention']='producer_to_consumer_even_for_derived_from_alias'
        elif identity=='experimental_order':
            contract=a.get('order_contract');_need(isinstance(contract,dict),'ANNOTATION_ORDER_REQUIRED','Actual order requires registered explicit protocol evidence')
            old=registered.get(contract['source_relation_id'])
            _need(old is not None and old['type']=='experimental_precedes' and old['from']==a['from'] and old['to']==a['to'] and contract['order_basis']==old.get('order_basis'),'ANNOTATION_ORDER_BASIS','Order contract must exactly match registered protocol, not Figure adjacency')
            out['source_relation_id']=old['id'];out['is_alias_of_registered_relation']=True
        else:_need('io_contract' not in a and 'order_contract' not in a,'ANNOTATION_CONTRACT_SCOPE','Association/evidence/presentation cannot imply a data or experimental-order contract')
        result.append(out)
    return result

def _figure_story_cards(plan,model,network_assets,*,plan_path,check_files):
    """Reuse E1 source/ledger checks; import only when explicitly requested."""
    import plan_figure_story as fs
    result=fs.validate(plan,development_preview=True)
    _need(result['valid'],'FIGURE_STORY_PLAN_DRIFT',str(result))
    registry=knowledge.load_json(plan['inputs']['inputs']['path'])
    upstream=knowledge.load_json(registry['knowledge'])
    _need(fingerprint(upstream)==fingerprint(model),'FIGURE_STORY_KNOWLEDGE_DRIFT','E1 cards and network must bind the identical M1 snapshot')
    _need(plan.get('scientific_entities_added')==0 and plan.get('source_scientific_relations')==model['relations'],'FIGURE_STORY_SCIENCE_DRIFT','Cards cannot introduce entities or modify M1 science')
    figures={f['id']:f for f in model['figures']};documents={d['id']:d for d in model['document_registry']};entities={e['id']:e for e in model['entities']}
    scopes={f['figure_id']:f['source_rsu_ids'] for f in plan['coverage']}
    rolemap={'purpose':'purpose','design':'design','method':'method','analysis':'readout','readout':'readout','result':'result','inference':'interpretation','interpretation':'interpretation','limit':'limitation','limitation':'limitation'}
    rows=[]
    for i,card in enumerate(plan['cards']):
        fid=card['figure_id'];_need(fid in figures,'FIGURE_STORY_FIGURE','Card Figure not registered')
        d=documents[figures[fid]['document_id']]
        _need(d['availability']=='available','FIGURE_STORY_SOURCE','Original PDF is required')
        own=[a for a in plan['assets'] if a['figure_id']==fid]
        _need(own,'FIGURE_STORY_ASSET','E1 Figure lacks source assets')
        for asset in own:
            _need(asset.get('source_pdf_sha256',asset.get('source_sha256'))==d['sha256'],'FIGURE_STORY_PDF','Card Figure assets name another source PDF')
        if check_files:
            pdf=Path(own[0].get('source_pdf',d.get('path','')))
            _need(pdf.is_file() and digest(pdf)==d['sha256'],'FIGURE_STORY_PDF','Registered source PDF changed')
        eids=planning.unique(eid for a in own for eid in a.get('evidence_ids',[]))
        if not eids:eids=planning.unique(eid for a in network_assets if a['figure_id']==fid for eid in a.get('evidence_ids',[]))
        _need(eids and all(eid in entities and entities[eid]['kind']=='evidence' for eid in eids),'FIGURE_STORY_EVIDENCE','Exact Figure evidence binding required; RSU-wide evidence union is forbidden')
        refs=[]
        for src in card['source_refs']:
            path=_path(src['path'],Path(plan_path).parent)
            _need(path.is_file() and digest(path)==src['sha256'],'FIGURE_STORY_CACHE_SHA',str(path))
            text=path.read_text(encoding='utf-8');start,end=src['start'],src['end']
            _need(type(start) is int and type(end) is int and 0<=start<end<=len(text) and text[start:end]==src['excerpt'] and hashlib.sha256(src['excerpt'].encode('utf-8')).hexdigest()==src['excerpt_sha256'],'FIGURE_STORY_CACHE_SPAN','E1 exact cache span changed')
            page=src['physical_page'];_need(type(page) is int and 1<=page<=d.get('physical_page_count',0),'FIGURE_STORY_PAGE','Source physical page outside registered PDF')
            refs.append({'document_id':d['id'],'locator':{'physical_page':page,'context_sha256':src['excerpt_sha256']},'verification':'pending','document_sha256':d['sha256'],'source_cache_ref':copy.deepcopy(src)})
        _need(card['role'] in rolemap,'FIGURE_STORY_ROLE','Explicit card role required')
        rows.append({'card':card,'role':rolemap[card['role']],'source_refs':refs,'entity_ids':eids,'rsu_ids':copy.deepcopy(scopes[fid]),'pointer':f'/cards/{i}/text'})
    return rows

def _assemble(knowledge_path,*,narrative_path=None,assets_path=None,source_cache=None,relations_path=None,figure_story_path=None,experiment_inventory_path=None,check_files=True):
    kp=Path(knowledge_path).resolve();model=knowledge.load_json(kp)
    planner=planning.ResearchPlanner(model,verify_files=False,base_dir=kp.parent)
    planned=planner.plan_all()
    inputs=[{'kind':'knowledge','path':str(kp),'sha256':digest(kp)}]
    def optional(kind,value):
        if value is None:return None,None
        p=Path(value).resolve()
        if kind=='source_cache' and p.is_dir():p=p/'metadata.json'
        value=knowledge.load_json(p);inputs.append({'kind':kind,'path':str(p),'sha256':digest(p)})
        return value,p
    nar,np=optional('narrative',narrative_path);assets,ap=optional('assets',assets_path);cache,cp=optional('source_cache',source_cache);annotations,rp=optional('relations',relations_path);figure_story,fp=optional('figure_story',figure_story_path)
    inventory,ip=optional('experiment_inventory',experiment_inventory_path)
    docs={x['id']:x for x in model['document_registry']};entities={x['id']:x for x in model['entities']};figs={x['id']:x for x in model['figures']}
    if cache is not None:
        _need(isinstance(cache,dict) and cache.get('sha256') in {d['sha256'] for d in docs.values()},'CACHE_SOURCE','Cache metadata must name a registered source PDF SHA256')
    diagnostics=copy.deepcopy(planner.validation['warnings'])
    diagnostics.append({'code':'SCIENTIFIC_REVIEW_PENDING','message':'File/pointer checks do not certify semantics, panel mapping, visual completeness or independent review.'})
    diagnostics.append({'code':'RELATION_EXTENSION_NOT_EXTRACTED','message':'Explicit pfs-relation-annotations-1 supports sourced candidate types including contradicts/hypothesizes; no relation is inferred from node labels. Association views are not scientific dependencies.'})
    nodes=[];edges=[];rsus=[];statements=[];associations=[];outassets=[]
    entity_rsus={x:[] for x in entities};entity_figs={x:[] for x in entities}
    for s in model['stories']:
        for eid in s['method_ids']+s['evidence_ids']:
            entity_rsus[eid].append(s['id']);entity_figs[eid].extend(s['figure_refs'])
        for r in model['relations']:
            if r['type']=='evidence_supports' and r['from'] in s['evidence_ids']:
                entity_rsus[r['to']].append(s['id']);entity_figs[r['to']].extend(s['figure_refs'])
    entity_rsus={k:planning.unique(v) for k,v in entity_rsus.items()};entity_figs={k:planning.unique(v) for k,v in entity_figs.items()}
    def statement(sid,text,role,pointer,refs,eids=None,rids=None,fids=None,input_kind='knowledge',depth='balanced',critical=False,assertion_kind=None,inherited=None):
        _need(isinstance(text,str) and bool(text.strip()),'TEXT','Statement must bind a nonempty source string')
        st={'id':sid,'text':text,'role':role,'entity_ids':list(eids or []),'rsu_ids':list(rids or []),'figure_ids':list(fids or []),
            'source_refs':copy.deepcopy(refs),'source_pointer':{'input_kind':input_kind,'pointer':pointer},
            'review':_source_review(refs,inherited=inherited),'depth':depth,'critical':critical,
            'assertion_kind':assertion_kind or ('inherited_scientific_record' if role not in ('purpose','limitation') else 'inherited_source_field')}
        statements.append(st);return sid
    def facet(fid,kind,label,pointer,refs,owner=None,**extra):
        node={'id':fid,'kind':kind,'label':label,'m1_pointer':pointer,'source_refs':copy.deepcopy(refs),
              'identity':'source_field_view','owner_id':owner,'details':label,'parameters':[],'quantities':[],
              'analysis_unit':'not_applicable','inputs':[],'outputs':[],**copy.deepcopy(extra)}
        nodes.append(node);return node
    def association(aid,from_id,to_id,kind,pointer):
        associations.append({'id':aid,'from':from_id,'to':to_id,'type':kind,'identity':'association','basis_pointer':pointer,
                             'scientific_dependency':False,'scope':'registered_field_or_membership_only'})
    for i,e in enumerate(model['entities']):
        prefix=f'/entities/{i}';role=_role(e['kind']);refs=e['source_refs']
        nodes.append({'id':e['id'],'kind':e['kind'],'label':e['name'],'m1_pointer':prefix,'source_refs':copy.deepcopy(refs),
                      'identity':'scientific_entity','details':e.get('details',''),'parameters':copy.deepcopy(e['parameters']),
                      'quantities':copy.deepcopy(e['quantities']),'analysis_unit':e['analysis_unit'],'unit_note':e.get('unit_note'),
                      'inputs':copy.deepcopy(e['inputs']),'outputs':copy.deepcopy(e['outputs']),'reporting_status':e['reporting_status'],
                      'limits':copy.deepcopy(e['limits'])})
        statement('M1.'+e['id']+'.name',e['name'],role,prefix+'/name',refs,[e['id']],entity_rsus[e['id']],entity_figs[e['id']],depth='quick')
        if e.get('details'):statement('M1.'+e['id']+'.details',e['details'],role,prefix+'/details',refs,[e['id']],entity_rsus[e['id']],entity_figs[e['id']])
        for j,p in enumerate(e['parameters']):
            ptr=prefix+f'/parameters/{j}';fid=e['id']+f'::parameters/{j}'
            prole={'design':'design','result':'result','interpretation':'interpretation','assay':'readout','readout':'readout','measurement':'readout'}.get(str(p.get('key','')).lower(),role)
            pkind={'design':'experimental_design','result':'observation_result','interpretation':'scientific_claim','readout':'measurement_readout'}.get(str(p.get('key','')).lower(),_facet_kind(e['kind']))
            facet(fid,pkind,_display_parameter(p),ptr,p['source_refs'],e['id'],parameter=copy.deepcopy(p))
            association('ASSOC.'+fid,e['id'],fid,'has_parameter',ptr)
            if isinstance(p.get('value'),str) and p['value'].strip():
                statement('M1.'+e['id']+f'.parameter.{j}',p['value'],prole,ptr+'/value',p['source_refs'],[e['id']],entity_rsus[e['id']],entity_figs[e['id']],depth='quick' if str(p.get('key','')).lower() in ('design','result','interpretation','assay','readout','measurement') else 'full',critical=str(p.get('key','')).lower() in ('design','result','interpretation'))
        for j,q in enumerate(e['quantities']):
            ptr=prefix+f'/quantities/{j}';fid=e['id']+f'::quantities/{j}'
            facet(fid,'measurement_readout',json.dumps(q,ensure_ascii=False,sort_keys=True),ptr,q.get('source_refs',refs),e['id'],quantity=copy.deepcopy(q))
            association('ASSOC.'+fid,e['id'],fid,'has_quantity',ptr)
        for j,value in enumerate(e['limits']):
            ptr=prefix+f'/limits/{j}';fid=e['id']+f'::limits/{j}'
            facet(fid,'limitation',value,ptr,refs,e['id']);association('ASSOC.'+fid,e['id'],fid,'has_limitation',ptr)
            statement('M1.'+e['id']+f'.limit.{j}',value,'limitation',ptr,refs,[e['id']],entity_rsus[e['id']],entity_figs[e['id']],depth='quick',critical=True)
    for i,s in enumerate(model['stories']):
        ptr=f'/stories/{i}';claims=planning.unique(r['to'] for r in model['relations'] if r['type']=='evidence_supports' and r['from'] in s['evidence_ids'])
        qid=s['id']+'::question';facet(qid,'scientific_question',s['question_or_purpose'],ptr+'/question_or_purpose',s['source_refs'],s['id'])
        stids=[statement('M1.'+s['id']+'.question',s['question_or_purpose'],'purpose',ptr+'/question_or_purpose',s['source_refs'],s['method_ids']+s['evidence_ids'],[s['id']],s['figure_refs'],depth='quick',critical=True),
               statement('M1.'+s['id']+'.finding',s['finding_or_argument'],'interpretation' if model['paper_type']['label'] in planning.NONEXPERIMENTAL else 'result',ptr+'/finding_or_argument',s['source_refs'],s['evidence_ids'],[s['id']],s['figure_refs'],depth='quick',critical=True)]
        for j,mid in enumerate(s['method_ids']):association('ASSOC.'+s['id']+'.method.'+str(j),qid,mid,'uses',ptr+f'/method_ids/{j}')
        for j,value in enumerate(s['limits']):
            lp=ptr+f'/limits/{j}';lid=s['id']+f'::limits/{j}';facet(lid,'limitation',value,lp,s['source_refs'],s['id']);association('ASSOC.'+lid,qid,lid,'has_limitation',lp)
            stids.append(statement('M1.'+s['id']+f'.limit.{j}',value,'limitation',lp,s['source_refs'],[],[s['id']],s['figure_refs'],depth='quick',critical=True))
        rsus.append({'id':s['id'],'question':s['question_or_purpose'],'method_ids':copy.deepcopy(s['method_ids']),'evidence_ids':copy.deepcopy(s['evidence_ids']),
                     'claim_ids':claims,'figure_ids':copy.deepcopy(s['figure_refs']),'statement_ids':stids,'original_order':copy.deepcopy(s['original_section_order']),
                     'source_refs':copy.deepcopy(s['source_refs']),'m1_pointer':ptr,'question_node_id':qid})
    for i,d in enumerate(model['document_registry']):facet(d['id']+'::source','evidence_source',d['title'],f'/document_registry/{i}',[],d['id'],document_id=d['id'],document=copy.deepcopy(d))
    for r in model['relations']:
        edge=copy.deepcopy(r);edge['identity']='presentation' if r['provenance']=='presentation' else 'author_argument' if r['type']=='argument_transition' else 'scientific_registered';edges.append(edge)
    if nar is not None:
        _need(nar.get('narrative_plan_version')=='m2c-1','NARRATIVE_VERSION','Expected assembled M2-C m2c-1 plan')
        _need(nar.get('base_snapshot')==fingerprint({k:v for k,v in nar.items() if k!='base_snapshot'}),'NARRATIVE_PLAN_DRIFT','M2-C base snapshot no longer matches its assembled plan')
        _need(nar.get('metadata',{}).get('knowledge_snapshot')==fingerprint(model),'NARRATIVE_KNOWLEDGE_DRIFT','M2-C binds another knowledge snapshot')
        _need(nar.get('source_scientific_relations')==model['relations'],'NARRATIVE_RELATION_DRIFT','M2-C scientific relations changed')
        bs=nar.get('resolved_bindings',{});bindings={b['id']:b for b in nar.get('bindings',[])}
        for bid,b in bindings.items():
            actual=narrative.pointer(model,b['pointer']);src=narrative.pointer(model,b['source_ref_pointer'])
            _need(bid in bs and actual==bs[bid]['value'] and src==bs[bid]['source_reference'],'NARRATIVE_BINDING_DRIFT',bid)
        rolemap={'direct_observation':'result','experimental_finding':'result','computational_prediction':'result','external_report':'interpretation',
                 'author_interpretation':'interpretation','mechanism_hypothesis':'interpretation','normative_recommendation':'interpretation','presentation_transition':'purpose'}
        unit_members={}
        for u in nar.get('reasoning_units',[]):
            for sid in narrative.statement_ids(u):unit_members.setdefault(sid,[]).extend(u['source_rsu_ids'])
        for i,st in enumerate(nar.get('statements',[])):
            prior=nar.get('review_status',{}).get('statement:'+st['id'],{}).get('record')
            if prior:_need(prior.get('target_sha256')==fingerprint(st),'NARRATIVE_TEXT_DRIFT','Inherited M2-C review targets another exact statement')
            refs=planning.source_union([[bs[bid]['source_reference'] for bid in st['source_binding_ids']]])
            eids=planning.unique(bindings[bid]['object_id'] for bid in st['source_binding_ids'] if bindings[bid]['object_id'] in entities)
            fids=planning.unique(bindings[bid]['figure_id'] for bid in st['source_binding_ids'] if bindings[bid]['figure_id'])
            rids=planning.unique(unit_members.get(st['id'],[]));sid='NAR.'+st['id']
            statement(sid,st['display_text'],rolemap[st['assertion_kind']],f'/statements/{i}/display_text',refs,eids,rids,fids,'narrative',st['depth'],st['critical'],st['assertion_kind'],nar.get('review_status',{}).get('statement:'+st['id']))
            for r in rsus:
                if r['id'] in rids:r['statement_ids'].append(sid)
    if assets is not None:
        _need(isinstance(assets,dict) and isinstance(assets.get('assets'),list),'ASSET_FORMAT','assets input needs assets array')
        for i,a in enumerate(assets['assets']):
            _need(a.get('figure_id') in figs,'ASSET_FIGURE',str(a.get('id')))
            p=_path(a['path'],ap.parent);h=a.get('sha256')
            _need(isinstance(h,str) and bool(re.fullmatch('[0-9a-fA-F]{64}',h)),'ASSET_SHA','Valid asset SHA256 required')
            if check_files:_need(p.is_file() and digest(p).lower()==h.lower(),'ASSET_DRIFT',str(p))
            source_hash=a.get('source_sha256',a.get('source_pdf_sha256'))
            _need(source_hash==docs[figs[a['figure_id']]['document_id']]['sha256'],'ASSET_SOURCE','Asset source PDF differs')
            _need(set(a.get('evidence_ids',[]))<={eid for eid,e in entities.items() if e['kind']=='evidence'},'ASSET_EVIDENCE','Unknown or non-evidence asset evidence ID')
            _need(a.get('source_document_id',figs[a['figure_id']]['document_id'])==figs[a['figure_id']]['document_id'],'ASSET_DOCUMENT','Asset names another document')
            out=copy.deepcopy(a);out['path']=str(p);out['source_pointer']={'input_kind':'assets','pointer':f'/assets/{i}'}
            out['source_document_id']=a.get('source_document_id',figs[a['figure_id']]['document_id'])
            out['review']={'source_status':'INHERITED_ONLY','panel_mapping_status':'PARTIAL' if 'all' in a.get('panels',[]) else 'INHERITED_ONLY',
                           'visual_status':'NOT_TESTED_THIS_RUN','semantic_review_status':'PARTIAL','inherited_visual_review':copy.deepcopy(a.get('visual_review')),
                           'fine_panel_pass':False,'file_identity':'sha256_checked_at_build','independent_scientific_review':False}
            outassets.append(out)
    if figure_story is not None:
        for item in _figure_story_cards(figure_story,model,outassets,plan_path=fp,check_files=check_files):
            card=item['card'];sid='FS.'+card['id']
            _need(sid not in entities,'FIGURE_STORY_ID_SCOPE','Presentation card ID cannot masquerade as an M1 entity')
            statement(sid,card['text'],item['role'],item['pointer'],item['source_refs'],item['entity_ids'],item['rsu_ids'],[card['figure_id']],'figure_story','quick',True,card.get('assertion_kind','inherited_scientific_record'),{'version':figure_story['version'],'card_id':card['id'],'source_snapshot':figure_story['snapshot'],'formal_ready':False})
            st=statements[-1];st['figure_story_card_id']=card['id'];st['panels']=copy.deepcopy(card['panels']);st['source_card_role']=card['role'];st['source_m1_pointers']=copy.deepcopy(card['m1_pointers']);st['identity']='figure_story_presentation_statement'
            for unit in rsus:
                if unit['id'] in item['rsu_ids']:unit['statement_ids'].append(sid)
    if annotations is not None:edges.extend(_annotation_edges(annotations,model,nodes,base_dir=rp.parent,knowledge_dir=kp.parent,check_files=check_files))
    experiment_layer=None
    if inventory is not None:
        import experiment_inventory as experiments
        experiment_layer=experiments.build_experiment_layer(inventory,model,base_dir=ip.parent,knowledge_path=kp,verify_files=check_files)
        existing_nodes={n['id'] for n in nodes};existing_edges={e['id'] for e in edges}
        _need(not existing_nodes.intersection(n['id'] for n in experiment_layer['nodes']),'EXPERIMENT_NODE_COLLISION','Supplement cannot overwrite M1/source-view nodes')
        _need(not existing_edges.intersection(e['id'] for e in experiment_layer['relations']),'EXPERIMENT_RELATION_COLLISION','Supplement cannot overwrite registered relationships')
        nodes.extend(experiment_layer['nodes']);associations.extend(experiment_layer['associations']);statements.extend(experiment_layer['statements']);edges.extend(experiment_layer['relations'])
    figures=[{**copy.deepcopy(f),'asset_ids':[a['id'] for a in outassets if a['figure_id']==f['id']]} for f in model['figures']]
    ids=[s['id'] for s in statements];_need(len(ids)==len(set(ids)),'DUPLICATE_STATEMENT','Duplicate statement IDs')
    _need(len({n['id'] for n in nodes})==len(nodes),'DUPLICATE_NODE','Duplicate network node IDs')
    profiles={};depth={'quick':0,'balanced':1,'full':2}
    core={s['id'] for s in statements if s['critical'] or s['depth']=='quick'}
    for profile in planning.PROFILES:
        selected=[s['id'] for s in statements if s['id'] in core or depth[s['depth']]<=depth[profile]]
        profiles[profile]={'statement_ids':selected,'rsu_ids':[s['id'] for s in rsus],'figure_ids':[f['id'] for f in figures],
                           'relation_ids':[e['id'] for e in edges],'node_ids':[n['id'] for n in nodes if profile=='full' or n['identity']=='scientific_entity' or n['kind'] in ('scientific_question','limitation','evidence_source') or profile=='balanced' and 'parameter' in n and n['parameter'].get('status')=='reported'],
                           'detail_level':profile,'depth_policy':copy.deepcopy(planned[profile]['story_plan']['depth_policy'])}
        if experiment_layer is not None:
            profiles[profile]['node_ids']=planning.unique(profiles[profile]['node_ids']+[n['id'] for n in experiment_layer['nodes']])
            profiles[profile]['experiment_ids']=[e['experiment_id'] for e in experiment_layer['experiments']]
    net={'version':VERSION,'inputs':inputs,'paper':{'id':model['document_registry'][0]['id'],'title':model['document_registry'][0]['title'],
         'paper_type':model['paper_type']['label'],'documents':copy.deepcopy(model['document_registry'])},'nodes':nodes,'edges':edges,'associations':associations,
         'rsus':rsus,'figures':figures,'statements':statements,'assets':outassets,
         'review':{'formal_ready':False,'status':'PARTIAL','source_verification':'inherited_only; optional file SHA checks are not semantics',
                   'semantic_review_status':'PARTIAL','independent_scientific_review':False,'independent_reader_test':'NOT_TESTED',
                   'unresolved_issues':['No current independent scientific review','Facet roles classify source fields; they do not add observed facts','Unknown conditions remain not_checked, not not_reported']},
         'profiles':profiles,'diagnostics':diagnostics,'knowledge_snapshot':fingerprint(model),'statistics':{'knowledge_parse_calls':1,'knowledge_index_builds':1,'pdf_parse_calls':0,
                   'scientific_entities_added':0,'source_field_view_nodes':sum(n['identity']=='source_field_view' for n in nodes),'base_relations':len(model['relations'])}}
    if experiment_layer is not None:
        net['experiment_layer']=experiment_layer
        net['statistics']['experiment_source_records_added']=len(experiment_layer['experiments'])
        net['statistics']['experiment_source_view_nodes']=len(experiment_layer['nodes'])
        net['diagnostics'].append({'code':'EXPERIMENT_SEMANTICS_PENDING','message':'Inventory extends the same network with exact-source records; field VERIFIED is not independent scientific final review.'})
    net['snapshot']=fingerprint(net);return net

def build_network(knowledge_path,*,narrative_path=None,assets_path=None,source_cache=None,relations_path=None,figure_story_path=None,experiment_inventory_path=None):
    return _assemble(knowledge_path,narrative_path=narrative_path,assets_path=assets_path,source_cache=source_cache,relations_path=relations_path,figure_story_path=figure_story_path,experiment_inventory_path=experiment_inventory_path,check_files=True)

def validate_network(network,verify_files=True):
    errors=[];warnings=[]
    def error(code,message):errors.append({'code':code,'message':message})
    try:
        schema=knowledge.load_json(SCHEMA);knowledge.check_schema(schema);errors.extend(knowledge.schema_errors(network,schema))
        if errors:return {'valid':False,'errors':errors,'warnings':warnings}
        copied=copy.deepcopy(network);snapshot=copied.pop('snapshot')
        if fingerprint(copied)!=snapshot:error('NETWORK_SNAPSHOT_DRIFT','Network content no longer matches its snapshot')
        im={x['kind']:x for x in network['inputs']}
        _need(len(im)==len(network['inputs']) and 'knowledge' in im,'INPUTS','Unique inputs including knowledge required')
        for value in im.values():_need(digest(value['path'])==value['sha256'],'INPUT_DRIFT',value['path'])
        args={key+'_path':im[key]['path'] for key in ('narrative','assets','relations','figure_story','experiment_inventory') if key in im}
        if 'source_cache' in im:args['source_cache']=im['source_cache']['path']
        rebuilt=_assemble(im['knowledge']['path'],**args,check_files=verify_files)
        if rebuilt!=network:error('NETWORK_FACT_DRIFT','Network differs from deterministic source-bound reconstruction; text/IDs/relations/review cannot be edited')
        if verify_files:
            model=knowledge.load_json(im['knowledge']['path']);report=knowledge.validate_knowledge(model,verify_files=True,base_dir=Path(im['knowledge']['path']).parent)
            errors.extend(report['errors']);warnings.extend(report['warnings'])
        else:warnings.append({'code':'SOURCE_FILES_NOT_RECHECKED','message':'Registered source and image files were not rechecked in this validation.'})
        for a in network['assets']:
            if 'all' in a.get('panels',[]):warnings.append({'code':'COARSE_PANEL_ASSET','message':a['id']+': whole-Figure asset does not establish fine panel PASS'})
        warnings.append({'code':'SCIENTIFIC_REVIEW_PENDING','message':'Structural validity is not independent scientific or visual acceptance.'})
    except (OSError,ValueError,KeyError,TypeError,IndexError) as exc:error(getattr(exc,'code','NETWORK_INPUT'),str(exc))
    return {'valid':not errors,'errors':errors,'warnings':warnings}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--knowledge',type=Path);p.add_argument('--narrative',type=Path);p.add_argument('--assets',type=Path);p.add_argument('--source-cache',type=Path);p.add_argument('--relations',type=Path);p.add_argument('--figure-story',type=Path);p.add_argument('--experiment-inventory',type=Path);p.add_argument('--output',type=Path);p.add_argument('--validate',type=Path);p.add_argument('--no-source-file-check',action='store_true');a=p.parse_args(argv)
    try:
        if a.validate:result=validate_network(knowledge.load_json(a.validate),not a.no_source_file_check);print(json.dumps(result,ensure_ascii=False));return 0 if result['valid'] else 1
        _need(a.knowledge is not None and a.output is not None,'CLI_INPUT','--knowledge and --output required')
        net=build_network(a.knowledge,narrative_path=a.narrative,assets_path=a.assets,source_cache=a.source_cache,relations_path=a.relations,figure_story_path=a.figure_story,experiment_inventory_path=a.experiment_inventory)
        protected={Path(v['path']).resolve() for v in net['inputs']}|{Path(v['path']).resolve() for v in net['paper']['documents'] if v.get('path')}|{Path(v['path']).resolve() for v in net['assets']}
        protected.update(Path(s['cache']['path']).resolve() for e in net['edges'] for s in e.get('source_refs',[]) if isinstance(s.get('cache'),dict))
        protected.update(Path(s['source_cache_ref']['path']).resolve() for e in net['edges'] for s in e.get('source_refs',[]) if isinstance(s.get('source_cache_ref'),dict))
        protected.update(Path(s['source_cache_ref']['path']).resolve() for st in net['statements'] for s in st.get('source_refs',[]) if isinstance(s.get('source_cache_ref'),dict))
        if 'experiment_layer' in net:
            protected.update(Path(s['source_cache_ref']['path']).resolve() for n in net['experiment_layer']['nodes'] for s in n.get('source_refs',[]) if isinstance(s.get('source_cache_ref'),dict))
        _need(a.output.resolve() not in protected,'INPUT_OUTPUT_COLLISION','Network output cannot overwrite an input, source PDF or Figure asset')
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(net,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'valid':True,'output':str(a.output.resolve()),'snapshot':net['snapshot'],'formal_ready':False},ensure_ascii=False));return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:print(json.dumps({'valid':False,'code':getattr(exc,'code','INPUT'),'message':str(exc)},ensure_ascii=False));return 2
if __name__=='__main__':raise SystemExit(main())






