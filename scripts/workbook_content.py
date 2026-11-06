"""Source-bound teaching input for the existing native Research Logic Workbook."""
from pathlib import Path
import copy,json,re
import research_logic as rl
FIGURE_FIELDS=['purpose','materials','design','readout','results','interpretation','links','limits']
METHOD_FIELDS=['purpose','design','readout','analysis','counts','limits']
IDENTITY_LABELS={'OBSERVATION':'观察','METHOD':'方法','AUTHOR_INTERPRETATION':'解释','PRESENTATION':'讲述','LIMITATION':'限制','AUTHOR_ARGUMENT':'论证','SCIENTIFIC_EVIDENCE':'证据'}

def relation_text(value,pointer,allow_list=True):
    """Display a reviewed relation field without changing its scientific model."""
    if isinstance(value,str) and value.strip():return value
    if allow_list and isinstance(value,list) and value and all(isinstance(x,str) and x.strip() for x in value):
        return '；'.join(value)
    expected='non-empty text or list of non-empty text' if allow_list else 'non-empty text'
    raise ValueError('WORKBOOK_RELATION_TEXT_TYPE: '+pointer+': expected '+expected)

def relation_text_fields(model):
    # Validate before graph/source traversal, so an invalid field gets its actual
    # JSON pointer rather than a generic list-concatenation or source-input error.
    return [(relation_text(e.get('rationale'),f'/edges/{i}/rationale',False),
             relation_text(e.get('alternatives'),f'/edges/{i}/alternatives'))
            for i,e in enumerate(model.get('edges',[]))]

def source_label(model,field):
    pages=','.join(str(p) for p in sorted({model['sources'][s]['physical_page'] for s in field['source_ids']}))
    exception={'CHECKED':'已核','NOT_REPORTED':'未报告','UNAVAILABLE':'资料缺失','NOT_APPLICABLE':'不适用'}.get(field.get('status'),'')
    return 'p'+pages+' · '+IDENTITY_LABELS.get(field.get('identity'),'记录')+(' · '+exception if exception else '')

def migration_alignment(old,model,content,spec):
    """Explicit contextual alignment; a shared source ID is not semantic equivalence."""
    report=dict(source_snapshot=old['snapshot'],target_snapshot=model['snapshot'],fields=[],gaps=[])
    if old['snapshot']==model['snapshot']:return report
    if (not spec or spec.get('source_snapshot')!=old['snapshot'] or spec.get('target_snapshot')!=model['snapshot'] or not spec.get('reviewer')):
        report['gaps'].append(dict(code='LEGACY_ALIGNMENT_REQUIRED',owner='Workbook',field='migration',detail='Cross-model content needs reviewed source/target snapshots and field-scope alignment.'));return report
    oldnodes={n['id']:n for n in old['nodes']};newnodes={n['id']:n for n in model['nodes']}
    for group,fields in [('figures',FIGURE_FIELDS),('methods',METHOD_FIELDS)]:
        for row in content[group]:
            owner=group+'/'+row['id'];binding=spec.get('owners',{}).get(owner,{})
            targets=binding.get('target_node_ids',[]);granularity=binding.get('granularity')
            valid=(targets and set(targets)<=set(newnodes) and granularity in ['figure_level','method_level','node_level'] and binding.get('reason') and binding.get('review_status')=='PARTIAL')
            for key in fields:
                f=row[key];pointer='/'+group+'/'+str(content[group].index(row))+'/'+key
                if not valid or not set(f['source_ids'])<=set(binding.get('source_ids',[])) or not set(binding.get('source_ids',[]))<=set(model['sources']):
                    report['gaps'].append(dict(code='LEGACY_FIELD_ALIGNMENT_REQUIRED',owner=owner,field=key,detail='Missing, stale or unresolved contextual alignment.'));continue
                # Detect explicit historical node references, not similarities between facts.
                stale=[nid for nid,n in oldnodes.items() if (re.search(r'(?<![\w])'+re.escape(nid)+r'(?![\w])',f['text']) or n['title'] in f['text']) and (nid not in newnodes or n['title']!=newnodes[nid]['title'] or nid not in targets)]
                if stale:report['gaps'].append(dict(code='LEGACY_STALE_NODE_REFERENCE',owner=owner,field=key,detail=','.join(stale)))
                report['fields'].append(dict(source_pointer=pointer,owner=owner,field=key,target_node_ids=targets,granularity=granularity,source_ids=f['source_ids'],reason=binding['reason'],semantic_equivalence='NOT_ASSERTED',review_status='PARTIAL'))
    return report

def _pointer(doc,pointer):
    for key in pointer.strip('/').split('/') if pointer else []:
        key=key.replace('~1','/').replace('~0','~');doc=doc[int(key)] if isinstance(doc,list) else doc[key]
    return doc

def _methods_not_applicable(model):
    """An empty list needs a sourced applicability decision, never a type guess."""
    try:
        net,index=rl.inputs(model)[0],rl.load(model['inputs']['scientific_index']['path'])
        facet=index['facets']['methods'];a=facet.get('applicability',{})
        ids=facet.get('sources',[])
        im={r['kind']:r for r in net['inputs']};knowledge=rl.load(im['knowledge']['path'])
        if any(e['kind'] in ['method','assay','processing','model','evaluation'] and e['source_role']=='primary_study' for e in knowledge['entities']):return False
        return (net['paper']['paper_type'] in ['review','perspective','editorial_or_voices']
                and index['article_type']==net['paper']['paper_type']
                and index.get('reading_status')=='AVAILABLE_CONTENT_READ'
                and facet['status']=='NOT_APPLICABLE' and bool(facet.get('text'))
                and bool(ids) and set(ids)<=set(model['sources'])
                and all(index.get('sources',{}).get(sid)==model['sources'][sid] for sid in ids)
                and a.get('scope')=='original_experimental_methods'
                and a.get('reviewer') and a.get('reason')
                and a.get('article_type_reviewed') is True and a.get('scope_reviewed') is True
                and a.get('basis_kind')=='reviewed_not_applicable'
                and set(a.get('source_ids',[]))==set(ids)
                and a.get('actual_methods_present') is False
                and index.get('review_subtype') not in ['systematic','meta_analysis'])
    except (KeyError,OSError,TypeError):return False

def assemble_content(model,bindings_path=None):
    """Project registered fields. No paper parsing, numerical matching or inference.

    Optional workbook_bindings in existing annotations contain IDs/selectors only.
    They disambiguate fields/sources or explicitly register a retained legacy input.
    """
    import evidence_network as en
    relation_texts=relation_text_fields(model)
    net=rl.load(model['inputs']['network']['path']);issues=[];warnings=[];catalog={}
    def gap(code,owner,field='',detail=''):
        issues.append(dict(code=code,owner=owner,field=field,detail=detail,action='Agent: review only this registered field/source; do not infer missing facts'))
    b={};inputs=[copy.deepcopy(v) for v in model['inputs'].values()]
    if bindings_path:
        annotations=rl.load(bindings_path)
        if annotations.get('logic_snapshot')!=model['snapshot']:raise ValueError('WORKBOOK_BINDINGS_MODEL_DRIFT')
        b=annotations.get('workbook_bindings',{});inputs.append(dict(path=str(Path(bindings_path).resolve()),sha256=rl.file_sha(bindings_path)))
    for conflict in b.get('conflicts',[]):gap('SOURCE_CONFLICT','Workbook',detail=str(conflict))
    q=rl.validate_model(model,net)
    if not q['valid']:raise ValueError('WORKBOOK_SOURCE_MODEL_INVALID: '+str(q['errors']))
    q=en.validate_network(net)
    if not q['valid']:raise ValueError('WORKBOOK_SOURCE_NETWORK_INVALID: '+str(q['errors']))
    im={x['kind']:x for x in net['inputs']};knowledge=rl.load(im['knowledge']['path'])
    inputs.extend(dict(path=v['path'],sha256=v['sha256']) for v in net['inputs'])
    source_map=b.get('statement_sources',{})
    if source_map and not b.get('reviewer'):raise ValueError('EXPLICIT_SOURCE_MAPPING_REVIEWER_REQUIRED')
    def sources(refs,rid):
        explicit=source_map.get(rid)
        if explicit is not None:
            if not explicit or not set(explicit)<=set(model['sources']):return []
            # Explicit Agent mapping is not automatic same-page equivalence or CHECKED.
            for sid in explicit:
                s=model['sources'][sid]
                if not any(r.get('document_id')==s['document_id'] and r.get('locator',{}).get('physical_page')==s['physical_page'] for r in refs):return []
            return list(explicit)
        found=[]
        for r in refs:
            locator=r.get('locator',{});cache=r.get('source_cache_ref',{})
            h=locator.get('context_sha256') or cache.get('excerpt_sha256') or r.get('excerpt_sha256')
            matches=[sid for sid,s in model['sources'].items() if h and s['document_id']==r.get('document_id') and s['physical_page']==locator.get('physical_page',r.get('physical_page')) and s['excerpt_sha256']==h]
            if len(matches)!=1:return []
            found.extend(matches)
        return list(dict.fromkeys(found))
    alias={'purpose':'purpose','materials':'materials','design':'design','groups':'design','readout':'readout','assay':'readout','measurement':'readout','method':'readout','analysis':'analysis','result':'results','results':'results','interpretation':'interpretation','links':'links','limits':'limits','limit':'limits','limitation':'limits','counts':'counts'}
    for i,s in enumerate(net['statements']):
        key=s.get('source_card_role',s['role']);ptr=s['source_pointer'];raw=None
        if ptr['input_kind']=='experiment_inventory':continue # Read each Inventory field once below.
        if ptr['input_kind']=='knowledge' and ptr['pointer'].endswith('/name'):continue
        if ptr['input_kind']=='knowledge':
            if '/parameters/' in ptr['pointer']:
                raw=_pointer(knowledge,ptr['pointer'].rsplit('/value',1)[0]);key=raw['key']
            elif '/limits/' in ptr['pointer']:key='limits'
            elif ptr['pointer'].endswith('/question_or_purpose'):key='purpose'
        if key not in alias:continue
        if raw and raw['status']!='reported':
            gap('FIELD_NOT_VERIFIED',s['id'],alias[key],raw.get('note',raw['status']));continue
        catalog[s['id']]=dict(text=s['text'],role=alias[key],source_ids=sources(s['source_refs'],s['id']),identity={'results':'OBSERVATION','interpretation':'AUTHOR_INTERPRETATION','limits':'LIMITATION','purpose':'PRESENTATION','links':'PRESENTATION'}.get(alias[key],'METHOD'),figures=s['figure_ids'],entities=s['entity_ids'],reference=dict(kind='network_statement',id=s['id'],pointer='/statements/'+str(i),path=model['inputs']['network']['path'],sha256=model['inputs']['network']['sha256']),origin='registered_field')
    figures={f['id']:dict(title=f.get('label',f['id']),panels=[]) for f in net['figures'] if f['kind'] in ['main','conceptual']}
    if 'figure_story' in im:
        story=rl.load(im['figure_story']['path'])
        for row in story['coverage']:
            if row['figure_id'] in figures:figures[row['figure_id']]['panels']=row['expected_panels']
    method_ids=[e['id'] for e in knowledge['entities'] if e['kind'] in ['method','assay','processing','model','evaluation']]
    method_names={e['id']:e['name'] for e in knowledge['entities']}
    quant={}
    # Relationships are reused by registered endpoint/statement identity, not Figure order.
    nodefigs={node['id']:{fid for st in net['statements'] if st['id'] in node.get('statement_ids',[]) or set(st['entity_ids'])&set(node.get('source_entity_ids',[])) for fid in st['figure_ids']} for node in model['nodes']}
    for i,e in enumerate(model['edges']):
        if not nodefigs[e['from']] or not nodefigs[e['to']] or nodefigs[e['from']]==nodefigs[e['to']]:continue
        rationale,alternatives=relation_texts[i]
        catalog['REL:'+e['id']]=dict(text=rationale+'\n解释边界：'+alternatives,role='links',source_ids=e['source_ids'],identity='PRESENTATION' if e['identity'] in ['PRESENTATION','AUTHOR_ARGUMENT'] else 'AUTHOR_INTERPRETATION',figures=list(nodefigs[e['from']]|nodefigs[e['to']]),entities=[],reference=dict(kind='research_logic_relation',logic_snapshot=model['snapshot'],pointer='/edges/'+str(i),relation_id=e['id'],identity=e['identity']),origin='registered_field')
    # Structured statistical identity is read as one registered parameter value.
    for i,e in enumerate(knowledge['entities']):
        for j,p in enumerate(e['parameters']):
            if p['key']!='quantitative_result':continue
            rid='QUANT:'+e['id']+':'+str(j);value=p['value']
            if isinstance(value,dict) and value.get('status')=='CONFLICT':gap('SOURCE_CONFLICT',rid,detail=json.dumps(value,ensure_ascii=False));continue
            required={'id','label','value','meaning','metric_id','test_id','unit','population_id'}
            if p['status']!='reported' or not isinstance(value,dict) or not required<=set(value):gap('QUANTITATIVE_IDENTITY_MISSING',rid);continue
            ids=sources(p['source_refs'],rid)
            quant[rid]={**copy.deepcopy(value),'value':str(value['value']),'source_ids':ids,'reference':dict(kind='M1_parameter',path=im['knowledge']['path'],sha256=im['knowledge']['sha256'],pointer=f'/entities/{i}/parameters/{j}/value'),'origin':'registered_field'}
        for j,q in enumerate(e['quantities']):
            rid='COUNT:'+e['id']+':'+str(j)
            if q['status']!='reported' or q['unit'] in ['not_applicable','not_reported'] or not q.get('note'):
                gap('QUANTITATIVE_IDENTITY_MISSING',rid,detail='Count needs its registered unit, population and explanation; statistics need an explicit test identity.');continue
            quant[rid]=dict(id=rid,label=e['name']+' / '+q['key'],value=str(q['value']),meaning=q['note'],metric_id=e['id']+'.'+q['key'],test_id='NOT_APPLICABLE_COUNT',unit=q['unit'],population_id=q['population_id'],source_ids=sources(q['source_refs'],rid),reference=dict(kind='M1_quantity',path=im['knowledge']['path'],sha256=im['knowledge']['sha256'],pointer=f'/entities/{i}/quantities/{j}'),origin='registered_field')
    invrec=model['inputs'].get('inventory') or im.get('experiment_inventory')
    if invrec:
        inv=rl.load(invrec['path']);inputs.append(dict(path=invrec['path'],sha256=invrec['sha256']))
        for i,e in enumerate(inv['experiments']):
            eid=e['experiment_id'];method_ids.append(eid);method_names[eid]=e['display_name']
            for key,f in e['fields'].items():
                field={'question':'purpose','materials':'materials','groups':'design','treatments':'design','acquisition':'readout','methods':'readout','analysis':'analysis','statistics':'analysis','result':'results','interpretation':'interpretation','limitations':'limits','sample_count':'counts','biological_replicates':'counts','technical_replicates':'counts','independent_runs':'counts'}.get(key)
                if not field:continue
                rid='INV:'+eid+':'+key
                if f['status']=='CONFLICT':gap('SOURCE_CONFLICT',rid,field,json.dumps(f,ensure_ascii=False));continue
                unknown=f['status'] in ['NOT_VERIFIED','NOT_REPORTED','NOT_APPLICABLE']
                text=f.get('reason') if unknown else f['value']
                if not text:gap('FIELD_NOT_VERIFIED',rid,field);continue
                text=(key+'：'+str(text)) if field=='counts' else (text if isinstance(text,str) else json.dumps(text,ensure_ascii=False))
                catalog[rid]=dict(text=text,role=field,source_ids=sources(f['source_refs'] or e.get('source_refs',[]),rid),identity='LIMITATION' if unknown or field=='limits' else 'OBSERVATION' if field=='results' else 'AUTHOR_INTERPRETATION' if field=='interpretation' else 'METHOD',figures=e['figure_ids'],entities=[eid],reference=dict(kind='Inventory_field',path=invrec['path'],sha256=invrec['sha256'],pointer=f'/experiments/{i}/fields/{key}'),origin='registered_field',source_status=f['status'])
    legacy=b.get('legacy_content');migration=None
    if legacy:
        # Explicit one-time migration of already authored facts, not new-paper extraction.
        if rl.file_sha(legacy['path'])!=legacy['sha256']:raise ValueError('LEGACY_CONTENT_DRIFT')
        lmrec=legacy['model'];lm=rl.load(lmrec['path'])
        if rl.file_sha(lmrec['path'])!=lmrec['sha256'] or not legacy.get('reviewer'):raise ValueError('LEGACY_MIGRATION_REVIEW_REQUIRED')
        lc=rl.load(legacy['path']);oldcheck=validate_content(lm,lc)
        if not oldcheck['valid']:raise ValueError('LEGACY_CONTENT_INVALID: '+str(oldcheck))
        migration=migration_alignment(lm,model,lc,legacy.get('migration'))
        issues.extend(migration['gaps'])
        if figures and set(figures)!=set(lc['expected_figures']):gap('LEGACY_FIGURE_COVERAGE_MISMATCH','Workbook',detail='Registered Figure IDs and the retained legacy scope differ; explicit upstream reconciliation required.')
        for sid,s in lm['sources'].items():
            if sid in model['sources'] and s!=model['sources'][sid]:raise ValueError('LEGACY_SOURCE_ID_CONFLICT: '+sid)
        inputs.extend([dict(path=legacy['path'],sha256=legacy['sha256']),lmrec])
        figures={f['id']:dict(title=f['title'],panels=f['panels']) for f in lc['figures']}
        method_ids=[x['id'] for x in lc['methods']];method_names={x['id']:x['title'] for x in lc['methods']}
        for group,fields in [('figures',FIGURE_FIELDS),('methods',METHOD_FIELDS)]:
            for i,row in enumerate(lc[group]):
                for field in fields:
                    f=row[field];rid='LEGACY:'+group+':'+row['id']+':'+field
                    catalog[rid]=dict(text=f['text'],role=field,identity=f['identity'],source_ids=f['source_ids'],figures=[row['id']] if group=='figures' else [],entities=[row['id']] if group=='methods' else [],reference=dict(kind='legacy_registered_field',path=legacy['path'],sha256=legacy['sha256'],pointer=f'/{group}/{i}/{field}'),origin='agent_prepared_legacy')
        for i,row in enumerate(lc['quantitative_results']):
            quant['LEGACY:QUANT:'+row['id']]={**copy.deepcopy(row),'metric_id':row['id'],'test_id':'UNREGISTERED_LEGACY','unit':'UNREGISTERED_LEGACY','population_id':'UNREGISTERED_LEGACY','reference':dict(kind='legacy_quantitative',path=legacy['path'],sha256=legacy['sha256'],pointer='/quantitative_results/'+str(i)),'origin':'agent_prepared_legacy'}
            review=legacy.get('quantitative_identities',{}).get(row['id'])
            if review:
                required={'metric_id','test_id','unit','population_id','review_status','review_note','source_ids','reviewer'}
                if set(review)!=required or review['review_status'] not in ['PARTIAL','SOURCE_CHECKED'] or not review['source_ids'] or not set(review['source_ids'])<=set(model['sources']) or not set(row['source_ids'])<=set(review['source_ids']):
                    gap('LEGACY_QUANTITATIVE_REVIEW_INVALID',row['id']);continue
                quant['LEGACY:QUANT:'+row['id']].update({key:copy.deepcopy(review[key]) for key in required})
                quant['LEGACY:QUANT:'+row['id']]['identity_origin']='agent_source_review'
        warnings.append('Legacy teaching text was Agent-authored before migration; statistical metadata marked UNREGISTERED_LEGACY is not independently verified.')
    if not figures:gap('FIGURE_REGISTRY_MISSING','Workbook')
    if not net['rsus'] and not legacy:gap('RSU_REGISTRY_MISSING','Workbook')
    assignments=[]
    def field(owner,name,ids):
        if not ids:gap('TEACHING_FIELD_MISSING',owner,name);return None
        selected=[]
        for rid in ids:
            rec=catalog.get(rid)
            if rec is None or rec['role']!=name:gap('FIELD_IDENTITY_MISMATCH',owner,name,rid);continue
            if not rec['source_ids'] or not set(rec['source_ids'])<=set(model['sources']):gap('SOURCE_BINDING_REQUIRED',owner,name,rid);continue
            selected.append(rec)
        if len(selected)!=len(ids):return None
        assignments.append(dict(owner=owner,field=name,refs=[x['reference'] for x in selected],origins=[x['origin'] for x in selected],source_ids=list(dict.fromkeys(s for x in selected for s in x['source_ids']))))
        # Deduplicate only identical display strings; keep every reference/identity above.
        return dict(text='\n'.join(dict.fromkeys(x['text'] for x in selected)),source_ids=assignments[-1]['source_ids'],status='NOT_APPLICABLE' if all(x.get('source_status')=='NOT_APPLICABLE' for x in selected) else 'PARTIAL',identity=selected[0]['identity'])
    output=[]
    for fid,f in figures.items():
        panels=b.get('figure_panels',{}).get(fid,f['panels'])
        if not panels or any(str(x).lower()=='all' for x in panels):gap('EXPLICIT_PANEL_REGISTRY_REQUIRED',fid)
        row=dict(id=fid,title=f['title'],panels=panels)
        for key in FIGURE_FIELDS:
            ids=b.get('figures',{}).get(fid,{}).get(key)
            if ids is None:ids=[rid for rid,r in catalog.items() if fid in r['figures'] and r['role']==key and (not legacy or r['origin']=='agent_prepared_legacy')]
            row[key]=field(fid,key,ids)
        output.append(row)
    methods=[]
    selected_methods=b.get('method_ids',list(dict.fromkeys(method_ids)))
    if not set(selected_methods)<=set(method_ids):gap('METHOD_IDENTITY_MISMATCH','Workbook')
    for mid in dict.fromkeys(selected_methods):
        if mid not in method_names:continue
        row=dict(id=mid,title=method_names[mid])
        for key in METHOD_FIELDS:
            ids=b.get('methods',{}).get(mid,{}).get(key)
            if ids is None:ids=[rid for rid,r in catalog.items() if mid in r['entities'] and r['role']==key and (not legacy or r['origin']=='agent_prepared_legacy')]
            row[key]=field(mid,key,ids)
        methods.append(row)
    if not methods and not _methods_not_applicable(model):gap('METHODS_APPLICABILITY_UNRESOLVED','Workbook')
    anchors=[];seen={}
    selections=b.get('quantitative_results',[dict(ref=rid) for rid in quant])
    for selection in selections:
        rid=selection['ref'];a=quant.get(rid)
        if a is None:gap('QUANTITATIVE_REFERENCE_MISSING',rid);continue
        if any(a.get(key)!=val for key,val in selection.get('expect',{}).items()):gap('QUANTITATIVE_IDENTITY_MISMATCH',rid);continue
        identity=tuple(a.get(key) for key in ['metric_id','test_id','unit','population_id'])
        if identity in seen and seen[identity]!=a['value']:gap('SOURCE_CONFLICT',rid,'quantitative_result',str(identity));continue
        if identity in seen:continue
        seen[identity]=a['value']
        if not a['source_ids']:gap('SOURCE_BINDING_REQUIRED',rid,'quantitative_result');continue
        anchors.append(a)
    refs=list({r['path']:r for r in inputs}.values())
    statistical_reviews=[]
    for review in b.get('statistical_reviews',[]):
        ref=review.get('field_ref',{});rows=output if ref.get('group')=='figures' else methods
        matched=next((r for r in rows if r['id']==ref.get('id')),None)
        text=matched.get(ref.get('field'),{}).get('text','') if matched else ''
        ids=review.get('source_ids',[])
        if not review.get('reviewer') or not review.get('metric_id') or not review.get('test_id') or not review.get('review_note') or not ids or not set(ids)<=set(model['sources']) or str(review.get('value')) not in text or not any(str(review.get('value')) in model['sources'][s]['excerpt'] for s in ids):
            gap('STATISTICAL_CONTEXT_INVALID',ref.get('id','?'));continue
        statistical_reviews.append(copy.deepcopy(review))
    content=dict(version='pfs-workbook-content-1',logic_snapshot=model['snapshot'],expected_figures=list(figures),figures=output,methods=methods,quantitative_results=anchors,inputs=refs,formal_ready=False,assembly=dict(generated=True,bindings=dict(path=str(Path(bindings_path).resolve()),sha256=rl.file_sha(bindings_path)) if bindings_path else None,field_map=assignments,warnings=warnings,migration=migration,statistical_reviews=statistical_reviews,scientific_review='PARTIAL',methods_applicability='NOT_APPLICABLE' if not methods and _methods_not_applicable(model) else 'APPLICABLE'))
    return dict(valid=not issues,content=content,gaps=issues,warnings=warnings,automatic_fields=sum(all(o=='registered_field' for o in a['origins']) for a in assignments),legacy_agent_registered_fields=sum(any(o=='agent_prepared_legacy' for o in a['origins']) for a in assignments),new_agent_text_fields=0,scientific_review='PARTIAL')
def validate_content(model,content):
    import validate_knowledge as vk
    schema=vk.load_json(Path(__file__).resolve().parents[1]/'schemas/workbook_content_v1_1.schema.json');vk.check_schema(schema)
    errors=vk.schema_errors(content,schema)
    if errors:return dict(valid=False,errors=errors,formal_ready=False)
    if content.get('version')!='pfs-workbook-content-1' or content.get('logic_snapshot')!=model['snapshot']:errors.append('WORKBOOK_CONTENT_MODEL_DRIFT')
    for r in content.get('inputs',[]):
        try:
            if rl.file_sha(r['path'])!=r['sha256']:errors.append('WORKBOOK_FACT_INPUT_DRIFT')
        except (KeyError,OSError):errors.append('WORKBOOK_FACT_INPUT_MISSING')
    def statements(row,fields):
        for field in fields:
            f=row.get(field,{})
            if not isinstance(f,dict) or not f.get('text','').strip():errors.append('TEACHING_FIELD_MISSING:'+row.get('id','?')+':'+field);continue
            if f.get('status') not in ['PARTIAL','CHECKED','NOT_REPORTED','UNAVAILABLE','NOT_APPLICABLE']:errors.append('TEACHING_STATUS_REQUIRED')
            ids=f.get('source_ids',[])
            if not ids or not set(ids)<=set(model['sources']):errors.append('TEACHING_SOURCE_REQUIRED:'+row.get('id','?')+':'+field)
            if f.get('identity') not in ['OBSERVATION','METHOD','AUTHOR_INTERPRETATION','PRESENTATION','LIMITATION']:errors.append('TEACHING_IDENTITY_REQUIRED')
    expected=content.get('expected_figures',[]);figs=content.get('figures',[])
    if not expected or {f['id'] for f in figs}!=set(expected) or len(figs)!=len(expected):errors.append('FIGURE_CHAPTER_COVERAGE')
    for f in figs:
        if not f.get('panels'):errors.append('FIGURE_PANELS_REQUIRED')
        statements(f,FIGURE_FIELDS)
    methods=content.get('methods',[])
    if not methods and not _methods_not_applicable(model):errors.append('METHODS_CHAPTER_REQUIRED_OR_SOURCED_NOT_APPLICABLE')
    for m in methods:statements(m,METHOD_FIELDS)
    for key in ['results','purpose']:
        vals=[f.get(key,{}).get('text','') for f in figs]
        if len(vals)>=3 and len(set(vals))<len(vals):errors.append('REPEATED_FIGURE_TEMPLATE:'+key)
    anchors=content.get('quantitative_results',[])
    for a in anchors:
        ids=a.get('source_ids',[])
        if not ids or not set(ids)<=set(model['sources']):errors.append('QUANTITATIVE_SOURCE_REQUIRED');continue
        compact=lambda t:re.sub(r'\s+','',str(t)).replace(',','')
        if compact(a.get('value','')) not in compact(' '.join(model['sources'][s]['excerpt'] for s in ids)):errors.append('QUANTITATIVE_LITERAL_NOT_IN_SOURCE:'+a.get('id','?'))
    assembly=content.get('assembly',{})
    if assembly.get('generated'):
        try:
            rec=assembly.get('bindings')
            if rec and rl.file_sha(rec['path'])!=rec['sha256']:errors.append('WORKBOOK_BINDINGS_DRIFT')
            else:
                replay=assemble_content(model,rec['path'] if rec else None)
                if not replay['valid'] or replay['content']!=content:errors.append('WORKBOOK_DERIVATION_DRIFT')
        except (OSError,KeyError,ValueError,TypeError) as ex:errors.append('WORKBOOK_REFERENCE_INVALID: '+str(ex))
    return dict(valid=not errors,errors=errors,figures=len(figs),methods=len(methods),quantitative_results=len(anchors),methods_applicability='NOT_APPLICABLE' if not methods and _methods_not_applicable(model) else 'APPLICABLE',binding_status='DETERMINISTIC_REFERENCES' if assembly.get('generated') else 'LEGACY_EXPLICIT_TEXT_NOT_FIELD_BOUND',scientific_review='PARTIAL',formal_ready=False)

def reviewed_figure_images(model,content,registry_path):
    if registry_path is None:return {},None
    from figure_assets import validate_registry
    from PIL import Image
    registry=rl.load(registry_path);check=validate_registry(registry)
    if not check['valid']:raise ValueError('WORKBOOK_FIGURE_FIDELITY: '+str(check))
    expected={f['id']:f for f in content['figures']};selected={}
    pdf_sha=rl.load(model['inputs']['scientific_index']['path'])['file_sha256']
    for a in registry['assets']:
        fid=a.get('figure_id')
        if fid not in expected:raise ValueError('WORKBOOK_FIGURE_ID: '+str(fid))
        if fid in selected:raise ValueError('WORKBOOK_FIGURE_AMBIGUOUS: '+fid)
        if a['source_pdf_sha256']!=pdf_sha:raise ValueError('WORKBOOK_FIGURE_DOCUMENT: '+fid)
        if not set(expected[fid]['panels'])<=set(a['panels']):raise ValueError('WORKBOOK_FIGURE_PANELS: '+fid)
        with Image.open(a['path']) as im:im.verify()
        selected[fid]=a
    if set(selected)!=set(expected):raise ValueError('WORKBOOK_FIGURE_MISSING: '+str(set(expected)-set(selected)))
    return selected,dict(path=str(Path(registry_path).resolve()),sha256=rl.file_sha(registry_path),assets=[dict(id=a['id'],figure_id=fid,path=a['path'],sha256=a['sha256'],physical_page=a['physical_page'],panels=a['panels'],bbox_pt=a['bbox_pt'],source_pdf_sha256=a['source_pdf_sha256']) for fid,a in selected.items()],scientific_review='PARTIAL')

def add_teaching_sections(doc,model,content,table,newpage,para,figure_images=None):
    check=validate_content(model,content)
    if not check['valid']:raise ValueError(str(check))
    def source(f):return source_label(model,f)
    labels={'purpose':'为什么做','materials':'对象与材料','design':'分组与对照','readout':'方法与读数','results':'实际结果','interpretation':'支持与不支持','links':'与其他Figure的联系','limits':'科学限制','analysis':'数据分析与统计','counts':'样本量与重复'}
    for f in content['figures']:
        newpage('逐Figure科研故事 · '+f['id']+'｜'+f['title'])
        para('对应panel：'+', '.join(f['panels']))
        if figure_images:
            from PIL import Image
            from docx.shared import Inches
            a=figure_images[f['id']]
            with Image.open(a['path']) as im:width=min(10.2,5.5*im.width/im.height)
            para('').add_run().add_picture(a['path'],width=Inches(width))
            para('原论文 '+f['id']+'；PDF p'+str(a['physical_page'])+'；panel '+', '.join(a['panels'])+'。保持原始比例及标记；科学审核PARTIAL。','Caption')
            newpage(f['id']+' 图解与实验设计｜'+f['title'])
        for group in [FIGURE_FIELDS]:
            table(doc,['讲述任务','科研解释','来源及状态'],[[labels[k],f[k]['text'],source(f[k])] for k in group],[1.2,7.4,1.8],11)
    for start in range(0,len(content['methods']),2):
        newpage('Methods与实验设计解析'+('（续）' if start else ''))
        for m in content['methods'][start:start+2]:
            doc.add_heading(m['title'],2)
            table(doc,['方法任务','解释与实际条件','来源'],[[labels[k],m[k]['text'],source(m[k])] for k in METHOD_FIELDS],[1.25,7.3,1.85],10.5)
    if not content['methods']:
        newpage('Methods适用范围')
        index=rl.load(model['inputs']['scientific_index']['path']);para(index['facets']['methods']['text'])
        para('本节依据有源的不适用声明；未提取或资料缺失不属于不适用。检索、纳入排除和实际分析方法若存在仍必须登记。科学终审PARTIAL。')
    newpage('主要结论、证据矩阵与重要定量结果')
    for f in content['figures']:
        para(f['id']+'：'+f['interpretation']['text'])
    table(doc,['指标','数值','研究对象、统计归属与解释边界','来源'],[[a['label'],a['value'],a['meaning']+('\n审核：'+a['review_note'] if a.get('review_note') else '\n统计身份尚未完整登记，不能仅凭同值合并。' if a.get('test_id')=='UNREGISTERED_LEGACY' else ''),source_label(model,dict(source_ids=a['source_ids'],identity='OBSERVATION'))] for a in content.get('quantitative_results',[])],[2.0,1.1,5.4,1.9],10.5)
    reviews=content.get('assembly',{}).get('statistical_reviews',[])
    if reviews:
        newpage('同值统计结果应分别怎样理解')
        table(doc,['指标与图位','数值','检验与审核说明','来源'],[[r['label'],r['value'],r['review_note'],source_label(model,dict(source_ids=r['source_ids'],identity='OBSERVATION'))] for r in reviews],[2.0,1.1,5.4,1.9],10.5)
    migration=content.get('assembly',{}).get('migration')
    if migration and migration['source_snapshot']!=migration['target_snapshot']:
        para('迁移说明：逐图与方法讲解复用历史有源记录，科研逻辑图使用本次已验收模型。已逐字段登记对应的研究范围；Figure或方法级对应不代表节点级语义等同。完整版本与对应表见配套审核记录。')
    para('本手册保留原始证据边界；未知参数与未决统计实现继续待核，不将统计限定当作独立生物学验证。')
    return check
