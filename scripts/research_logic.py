"""Source-referenced reasoning view over an existing evidence network and inventory.

This module validates/projections Agent adjudications. It does not infer scientific
relations from Figure order, text roles, node positions or keyword matching.
"""
from __future__ import annotations
import argparse,copy,hashlib,json
from pathlib import Path
VERSION='pfs-research-logic-1'
IDENTITIES={'SCIENTIFIC_EVIDENCE','AUTHOR_ARGUMENT','AUTHOR_INTERPRETATION','PRESENTATION','SHARED_PROTOCOL','ACTUAL_PROTOCOL_ORDER'}
RELATIONS={'progression','question_fork','parallel','complements','evidence_convergence','shared_workflow','hypothesizes','comparison','protocol_order','qualifies'}
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def file_sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fingerprint(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def snapshot(model):return fingerprint({k:v for k,v in model.items() if k!='snapshot'})
def inputs(model):
    n=load(model['inputs']['network']['path'])
    inv=load(model['inputs']['inventory']['path']) if model['inputs'].get('inventory') else None
    return n,inv
def experiment_map(inventory):return {e['experiment_id']:e for e in (inventory or {}).get('experiments',[])}
def resolve_field(inventory,binding):
    e=experiment_map(inventory)[binding['experiment_id']]
    return e['fields'][binding['field']]
def validate_model(model,network=None,verify_files=True):
    errors=[]
    def need(ok,code,detail=''):
        if not ok:errors.append({'code':code,'detail':detail})
    need(model.get('version')==VERSION,'LOGIC_VERSION')
    need(model.get('snapshot')==snapshot(model),'LOGIC_DRIFT')
    need(model.get('formal_ready') is False,'REVIEW_UPGRADE')
    for key,rec in model.get('inputs',{}).items():
        if verify_files:
            try:need(file_sha(rec['path'])==rec['sha256'],'LOGIC_INPUT_DRIFT',key)
            except (OSError,KeyError,TypeError):need(False,'LOGIC_INPUT_MISSING',key)
    try:
        n,inv=inputs(model)
    except (OSError,KeyError,TypeError) as e:return {'valid':False,'errors':errors+[{'code':'LOGIC_INPUT','detail':str(e)}]}
    if network is not None:need(n['snapshot']==network['snapshot'],'LOGIC_NETWORK_MISMATCH')
    need(n['snapshot']==model.get('network_snapshot'),'LOGIC_NETWORK_DRIFT')
    index=load(model['inputs']['scientific_index']['path'])
    need(index.get('reading_status')=='AVAILABLE_CONTENT_READ','READING_FIRST_REQUIRED')
    need(index.get('methods_task_detection')=='COMPLETE_AVAILABLE','METHODS_FIRST_REQUIRED')
    need(index.get('result_mapping_status')=='MAPPED_WITH_GAPS','RESULT_MAPPING_FIRST_REQUIRED')
    need(index.get('article_type')==n['paper']['paper_type'],'ARTICLE_TYPE_MISMATCH')
    needed={'background_gap','core_question','hypotheses','tasks','purpose','materials','groups_controls','conditions','methods','results','author_interpretation','limitations'}
    need(needed<=set(index.get('facets',{})),'SCIENCE_INDEX_INCOMPLETE')
    ids={x['id'] for x in n['nodes']};sids={x['id'] for x in n['statements']};exps=experiment_map(inv)
    docs={d['id']:d for d in n['paper']['documents']};sources=model.get('sources',{})
    for sid,ref in sources.items():
        try:
            need(ref['document_id'] in docs,'SOURCE_DOCUMENT',sid)
            need(ref['document_sha256']==docs[ref['document_id']]['sha256'],'SOURCE_DOCUMENT_SHA',sid)
            need(1<=ref['physical_page']<=docs[ref['document_id']]['physical_page_count'],'SOURCE_PAGE',sid)
            if verify_files:
                p=Path(ref['path']);txt=p.read_text(encoding='utf-8');need(file_sha(p)==ref['sha256'],'SOURCE_CACHE_DRIFT',sid)
                need(txt[ref['start']:ref['end']]==ref['excerpt'],'SOURCE_SPAN',sid)
                need(hashlib.sha256(ref['excerpt'].encode()).hexdigest()==ref['excerpt_sha256'],'SOURCE_EXCERPT_SHA',sid)
        except (OSError,KeyError,TypeError):need(False,'SOURCE_REFERENCE',sid)
    nodes=model.get('nodes',[]);nm={x['id']:x for x in nodes}
    need(len(nm)==len(nodes),'DUPLICATE_LOGIC_NODE')
    for node in nodes:
        nid=node['id'];need(node.get('identity') in IDENTITIES,'NODE_IDENTITY',nid)
        need(node.get('review_status')=='PARTIAL','NODE_REVIEW_UPGRADE',nid)
        need(bool(node.get('source_ids')) or bool(node.get('field_bindings')),'NODE_WITHOUT_SOURCE',nid)
        need(set(node.get('source_ids',[]))<=set(sources),'NODE_SOURCE',nid)
        need(set(node.get('source_entity_ids',[]))<=ids,'NODE_ENTITY',nid)
        need(set(node.get('statement_ids',[]))<=sids,'NODE_STATEMENT',nid)
        need(not node.get('parent_id') or node['parent_id'] in nm,'NODE_PARENT',nid)
        for b in node.get('field_bindings',[]):
            need(b.get('experiment_id') in exps,'UNKNOWN_EXPERIMENT',nid)
            if b.get('experiment_id') in exps:need(b.get('field') in exps[b['experiment_id']]['fields'],'UNKNOWN_METHOD_FIELD',nid)
    edges=model.get('edges',[]);em={e['id']:e for e in edges}
    need(len(em)==len(edges),'DUPLICATE_LOGIC_EDGE')
    for e in edges:
        eid=e['id'];need(e.get('from') in nm and e.get('to') in nm and e.get('from')!=e.get('to'),'EDGE_ENDPOINT',eid)
        need(e.get('type') in RELATIONS and e.get('identity') in IDENTITIES,'EDGE_TYPE',eid)
        need(bool(e.get('source_ids')) or e.get('identity')=='PRESENTATION','EDGE_WITHOUT_SOURCE',eid)
        need(set(e.get('source_ids',[]))<=set(sources),'EDGE_SOURCE',eid)
        need(e.get('review_status')=='PARTIAL','EDGE_REVIEW_UPGRADE',eid)
        need(bool(e.get('rationale')) and bool(e.get('alternatives')),'RELATION_JUDGMENT_REQUIRED',eid)
        need(not e.get('causal_claim',False),'UNSUPPORTED_CAUSAL_UPGRADE',eid)
        if e.get('type') in {'progression','question_fork'}:need(e['identity'] in {'AUTHOR_ARGUMENT','PRESENTATION'},'ARGUMENT_IS_NOT_CAUSAL',eid)
        if e.get('type')=='hypothesizes':need(e['identity']=='AUTHOR_INTERPRETATION','HYPOTHESIS_IDENTITY',eid)
        if e.get('type')=='shared_workflow':need(e['identity']=='SHARED_PROTOCOL' and not e.get('independent_validation',False),'SHARED_IS_NOT_VALIDATION',eid)
        if e.get('type')=='protocol_order' or e.get('identity')=='ACTUAL_PROTOCOL_ORDER':
            original=next((r for r in n['edges'] if r['id']==e.get('registered_relation_id')),None)
            need(original is not None and original.get('type')=='experimental_precedes','PROTOCOL_ORDER_REQUIRES_REGISTERED_EVIDENCE',eid)
            if original:
                need(original.get('from') in nm.get(e.get('from'),{}).get('source_entity_ids',[]) and original.get('to') in nm.get(e.get('to'),{}).get('source_entity_ids',[]),'PROTOCOL_ORDER_ENDPOINT_MISMATCH',eid)
        if e.get('independent_validation'):
            for nodeid in [e.get('from'),e.get('to')]:
                for b in nm.get(nodeid,{}).get('field_bindings',[]):
                    task=exps.get(b['experiment_id'],{})
                    need(not task.get('task_type','').startswith('shared_'),'SHARED_COUNTED_INDEPENDENT',eid)
    core=model.get('core',{});need(set(core.get('nodes',[]))<=set(nm),'A_UNKNOWN_NODE');need(set(core.get('edges',[]))<=set(em),'A_UNKNOWN_EDGE')
    for eid in core.get('edges',[]):need({em[eid]['from'],em[eid]['to']}<=set(core['nodes']),'A_EDGE_ENDPOINT',eid)
    need(bool(core.get('nodes')) and bool(core.get('edges')),'EMPTY_CORE')
    for view in model.get('branches',[]):
        need(set(view['nodes'])<=set(nm) and set(view['edges'])<=set(em),'BRANCH_UNKNOWN_ID',view['id'])
        for eid in view['edges']:need({em[eid]['from'],em[eid]['to']}<=set(view['nodes']),'BRANCH_ENDPOINT',eid)
    # User-facing explanations remain references to full records, never replacements.
    exp_ids=[]
    for entry in model.get('method_explanations',[]):
        eid=entry['experiment_id'];exp_ids.append(eid);need(eid in exps,'EXPLANATION_EXPERIMENT',eid)
        need(set(entry.get('source_ids',[]))<=set(sources),'EXPLANATION_SOURCE',eid)
        need(entry.get('review_status')=='PARTIAL','EXPLANATION_REVIEW_UPGRADE',eid)
        for role in ['why','design','readout','result','meaning','limit']:need(bool(entry.get(role)),'EXPLANATION_MISSING_ROLE',eid+':'+role)
        need(bool(entry.get('field_bindings')),'EXPLANATION_UNBOUND',eid)
        for b in entry.get('field_bindings',[]):need(eid in exps and b in exps[eid]['fields'],'EXPLANATION_FIELD',eid)
    need(len(exp_ids)==len(set(exp_ids)),'DUPLICATE_EXPERIMENT_COVERAGE')
    if inv:need(set(exp_ids)==set(exps),'METHOD_TASK_COVERAGE')
    if n['paper']['paper_type']=='review':need(index.get('review_subtype') in ['narrative','systematic','meta_analysis'],'REVIEW_SUBTYPE_REQUIRED')
    if index.get('review_subtype')=='narrative' or n['paper']['paper_type']=='perspective':
        need(not exps and not exp_ids,'REVIEW_AS_EXPERIMENT')
    return {'valid':not errors,'errors':errors,'scientific_review':'PARTIAL','source_location':'FILE_AND_SPAN_ONLY','independent_review':'NOT_TESTED','formal_ready':False}
def compress_to_core(model,node_ids,edge_ids):
    nm={n['id']:n for n in model['nodes']};core=set(model['core']['nodes'])
    def parent(x):
        seen=set()
        while x not in core:
            if x in seen:return None
            seen.add(x);x=nm.get(x,{}).get('parent_id')
            if x is None:return None
        return x
    return {'nodes':sorted({parent(x) for x in node_ids if parent(x)}),'edges':sorted(set(edge_ids)&set(model['core']['edges']))}
def methods_view(model):
    n,inv=inputs(model);exp=experiment_map(inv);plain={x['experiment_id']:x for x in model.get('method_explanations',[])}
    result=[]
    for eid,e in exp.items():
        result.append({'experiment_id':eid,'task_type':e['task_type'],'name':e['display_name'],'logical_nodes':[x['id'] for x in model['nodes'] if any(b['experiment_id']==eid for b in x.get('field_bindings',[]))],
                       'plain_explanation':copy.deepcopy(plain.get(eid)), 'fields':copy.deepcopy(e['fields']),'figure_ids':copy.deepcopy(e['figure_ids']),'source_refs':copy.deepcopy(e.get('source_refs',[])),
                       'status':'PARTIAL','counted_as_independent_validation':False})
    return result
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model',required=True,type=Path);p.add_argument('--output',type=Path);args=p.parse_args()
    result=validate_model(load(args.model));s=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:args.output.write_text(s,encoding='utf-8')
    print(s);return 0 if result['valid'] else 1
if __name__=='__main__':raise SystemExit(main())
