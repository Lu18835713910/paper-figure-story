"""Supported PENDING scientific-index skeleton and source-bound native logic assembly."""
import argparse,copy,hashlib,json
from pathlib import Path
import research_logic as rl
VERSION='pfs-scientific-index-1'
FACETS=['background_gap','core_question','hypotheses','tasks','purpose','materials','groups_controls','conditions','methods','results','author_interpretation','limitations']
def skeleton(paper_index):
    return dict(version=VERSION,source_pdf=paper_index['source_pdf'],file_sha256=paper_index['file_sha256'],page_count=paper_index['page_count'],
        reading_status='PENDING',methods_task_detection='PENDING',result_mapping_status='PENDING',article_type='unknown',formal_ready=False,
        reading_record={'actor':None,'basis':[],'scope':None},sources={},facets={k:dict(status='PENDING',text='',sources=[]) for k in FACETS})
def validate(index):
    # Reuse the dependency-free M1 schema subset; validate dynamic source records
    # explicitly because that engine intentionally does not expand map schemas.
    import validate_knowledge as vk
    schema=vk.load_json(Path(__file__).resolve().parents[1]/'schemas/scientific_index_v1_1.schema.json');vk.check_schema(schema)
    shape=vk.schema_errors(index,schema)
    if not shape:
        for sid,s in index.get('sources',{}).items():
            shape += vk.schema_errors(s,schema['properties']['sources']['additionalProperties'])
    if shape:return dict(valid=False,errors=shape,scientific_review='PARTIAL',formal_ready=False,source_validation='SCHEMA_REJECTED')
    errors=[]
    def need(ok,c): 
        if not ok:errors.append(c)
    need(index.get('version')==VERSION,'SCIENTIFIC_INDEX_VERSION')
    need(index.get('formal_ready') is False,'REVIEW_UPGRADE')
    need(index.get('reading_status')=='AVAILABLE_CONTENT_READ','READING_FIRST_REQUIRED')
    need(index.get('methods_task_detection')=='COMPLETE_AVAILABLE','METHODS_FIRST_REQUIRED')
    need(index.get('result_mapping_status')=='MAPPED_WITH_GAPS','RESULT_MAPPING_FIRST_REQUIRED')
    need(index.get('article_type') in ['original_research','methods_or_model','resource_atlas','review','perspective','editorial_or_voices'],'ARTICLE_TYPE')
    record=index.get('reading_record',{});need(bool(record.get('actor')) and bool(record.get('basis')) and bool(record.get('scope')),'READING_ATTESTATION_REQUIRED')
    sources=index.get('sources',{})
    try:need(rl.file_sha(index['source_pdf'])==index['file_sha256'],'SCIENTIFIC_PDF_DRIFT')
    except (OSError,KeyError):need(False,'SCIENTIFIC_PDF_REQUIRED')
    for key in FACETS:
        f=index.get('facets',{}).get(key,{})
        need(f.get('status') in ['PARTIAL','CHECKED','NOT_APPLICABLE'],'FACET_PENDING:'+key)
        need(bool(f.get('text')),'FACET_TEXT:'+key)
        need(bool(f.get('sources')) and set(f.get('sources',[]))<=set(sources),'FACET_SOURCE:'+key)
        if f.get('status')=='CHECKED':
            r=f.get('semantic_review',{})
            need(bool(r.get('reviewer')) and bool(r.get('support_explanation')),'SEMANTIC_REVIEW_ATTESTATION:'+key)
    for b in record.get('basis',[]):
        try:need(rl.file_sha(b['path'])==b['sha256'],'READING_BASIS_DRIFT')
        except (OSError,KeyError,TypeError):need(False,'READING_BASIS_REQUIRED')
    for sid,s in sources.items():
        try:
            txt=Path(s['path']).read_text('utf-8')
            need(rl.file_sha(s['path'])==s['sha256'],'SOURCE_CACHE_DRIFT:'+sid)
            need(type(s['start']) is int and type(s['end']) is int and 0<=s['start']<s['end']<=len(txt),'SOURCE_SPAN_RANGE:'+sid)
            need(txt[s['start']:s['end']]==s['excerpt'] and hashlib.sha256(s['excerpt'].encode()).hexdigest()==s['excerpt_sha256'],'SOURCE_SPAN:'+sid)
            need(s['document_sha256']==index['file_sha256'] and 1<=s['physical_page']<=index['page_count'],'SOURCE_DOCUMENT:'+sid)
        except (OSError,KeyError,TypeError):need(False,'SOURCE_REFERENCE:'+sid)
    return dict(valid=not errors,errors=errors,scientific_review='PARTIAL',formal_ready=False,source_validation='FILE_AND_EXACT_SPAN_NOT_SEMANTIC_PROOF')
def assemble(index_path,network_path,adjudication_path,inventory_path=None):
    import evidence_network as en
    idx=rl.load(index_path);check=validate(idx)
    if not check['valid']:raise ValueError('SCIENTIFIC_INDEX_BLOCKED: '+str(check))
    net=rl.load(network_path);check=en.validate_network(net)
    if not check['valid']:raise ValueError('SOURCE_NETWORK_BLOCKED: '+str(check))
    data=rl.load(adjudication_path)
    m=copy.deepcopy(data);m.update(version=rl.VERSION,formal_ready=False,network_snapshot=net['snapshot'])
    m['sources']=copy.deepcopy(idx['sources'])
    m['inputs']={'network':{'path':str(Path(network_path).resolve()),'sha256':rl.file_sha(network_path)},'scientific_index':{'path':str(Path(index_path).resolve()),'sha256':rl.file_sha(index_path)},'adjudication':{'path':str(Path(adjudication_path).resolve()),'sha256':rl.file_sha(adjudication_path)}}
    if inventory_path:m['inputs']['inventory']={'path':str(Path(inventory_path).resolve()),'sha256':rl.file_sha(inventory_path)}
    m['snapshot']=rl.snapshot(m);check=rl.validate_model(m,net)
    if not check['valid']:raise ValueError('RESEARCH_LOGIC_BLOCKED: '+str(check))
    return m
def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('init');a.add_argument('--paper-index',required=True);a.add_argument('--output',required=True)
    a=sub.add_parser('validate');a.add_argument('--index',required=True)
    a=sub.add_parser('assemble');a.add_argument('--index',required=True);a.add_argument('--network',required=True);a.add_argument('--adjudication',required=True);a.add_argument('--inventory');a.add_argument('--output',required=True)
    a=p.parse_args()
    if a.cmd=='validate':
        r=validate(rl.load(a.index));print(json.dumps(r,ensure_ascii=False));return 0 if r['valid'] else 2
    output=Path(a.output)
    if output.exists():raise ValueError('OUTPUT_EXISTS')
    result=skeleton(rl.load(a.paper_index)) if a.cmd=='init' else assemble(a.index,a.network,a.adjudication,a.inventory)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8');print(str(output));return 0
if __name__=='__main__':raise SystemExit(main())

