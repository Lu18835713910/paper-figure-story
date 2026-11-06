"""Register actual native graph exports for Workbook and complete-network delivery QA."""
import argparse,json
from pathlib import Path
import research_logic as rl
from delivery_contract import validate_delivery

def navigation_record(model,graphs,main,reference,omitted_edges=None):
    full=next(g for g in graphs if g['view']=='B' and g['scope']=='complete')
    nodes=set().union(*(set(p['node_ids']) for p in main));edges=set().union(*(set(p['edge_ids']) for p in main))
    return dict(id='MAIN_B_NAVIGATION',view='navigation',scope='overview_navigation',parent_canvas=full['id'],logic_snapshot=model['snapshot'],
        node_ids=sorted(nodes),edge_ids=sorted(edges),omitted_edge_ids=sorted({e['id'] for e in model['edges']}-edges),omitted_edges=omitted_edges or {},
        main_slides=[p['main_slide'] for p in main],pptx=main[0]['pptx'],pptx_sha256=main[0]['pptx_sha256'],
        full_b_reference=dict(path=reference,sha256=full['pptx_sha256']))

def receipt_file(path,expected,field,receipt_path):
    p=Path(path)
    if not p.is_absolute():p=Path(receipt_path).resolve().parent/p
    if not p.is_file():raise ValueError('GRAPH_RECEIPT_INPUT_MISSING:'+field+':'+str(p)+'; retain the input or use --main-pptx with exactly the recorded SHA256 and keep the linked complete B beside it')
    if rl.file_sha(p)!=expected:raise ValueError('GRAPH_RECEIPT_INPUT_SHA_MISMATCH:'+field)
    return str(p.resolve())

def register(model_path,plan_path,receipt_path,png_dir,navigation=None,main_pptx=None):
    model=rl.load(model_path);plan=rl.load(plan_path);receipt=rl.load(receipt_path)
    if receipt.get('main_pages'):
        receipt['main_pptx']=receipt_file(main_pptx or receipt['main_pptx'],receipt['main_sha256'],'main_pptx',receipt_path)
    elif main_pptx:raise ValueError('GRAPH_RECEIPT_HAS_NO_MAIN_PAGES')
    if not rl.validate_model(model)['valid']:raise ValueError('GRAPH_SOURCE_MODEL_INVALID')
    if plan.get('research_logic',{}).get('sha256')!=rl.file_sha(model_path):raise ValueError('GRAPH_MODEL_DRIFT')
    bykind={r['kind']:r for r in receipt['files']};graphs=[]
    for product in plan['products']:
        scene=product['slides'][0];coverage=scene['coverage'];view=coverage['view'];file=bykind[product['kind']]
        file['path']=receipt_file(file['path'],file['sha256'],'files/'+product['kind'],receipt_path)
        png=Path(png_dir)/(product['kind']+'.png')
        graphs.append(dict(id='GRAPH_'+view,view=view,scope='complete' if view=='B' else 'overview_A' if view=='A' else 'zoom',parent_canvas='GRAPH_B' if view not in ['A','B'] else None,
            node_ids=scene['source_logic_node_ids'],edge_ids=scene['source_logic_relation_ids'],logic_snapshot=model['snapshot'],pptx=file['path'],pptx_sha256=file['sha256'],png=str(png.resolve()),png_sha256=rl.file_sha(png)))
    check=validate_delivery(model,graphs,False)
    if not check['valid']:raise ValueError('GRAPH_REGISTRATION_BLOCKED: '+str(check['errors']))
    main=[]
    for page in receipt.get('main_pages',[]):
        view=page['view'];png=Path(png_dir)/('main-slide-'+str(page['slide']).zfill(3)+'.png')
        main.append(dict(id='MAIN_'+view,placement='main',view=view,source_view=view,scope='overview' if view=='B' else 'overview_A' if view=='A' else 'zoom',parent_canvas='GRAPH_B' if view!='A' else None,main_slide=page['slide'],logic_snapshot=model['snapshot'],node_ids=page['node_ids'],edge_ids=page['edge_ids'],pptx=receipt['main_pptx'],pptx_sha256=receipt['main_sha256'],png=str(png.resolve()),png_sha256=rl.file_sha(png)))
    if main:
        if navigation is None and any(p['view']=='B' for p in main) and receipt.get('full_b_reference'):
            navigation=dict(full_b_reference=receipt['full_b_reference'],omitted_edges={})
        if navigation is not None:
            main.append(navigation_record(model,graphs,main,navigation['full_b_reference'],navigation.get('omitted_edges',{})))
        check=validate_delivery(model,graphs+main,any(g['view']=='B' or g['scope']=='overview_navigation' for g in main))
        if not check['valid']:raise ValueError('MAIN_NATIVE_DELIVERY_BLOCKED: '+str(check))
    return dict(main_graphs=main,version='pfs-logic-graph-manifest-1',logic_snapshot=model['snapshot'],graphs=graphs,validation=check,formal_ready=False)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['model','plan','receipt','png-dir','output']:p.add_argument('--'+k,required=True)
    p.add_argument('--navigation',help='Existing-model main navigation: relative full_b_reference and explicit omitted_edges reasons.')
    p.add_argument('--main-pptx',help='Explicit receipt path relocation; the supplied file must match the recorded main SHA256 exactly.')
    a=p.parse_args();out=Path(a.output)
    if out.exists():raise ValueError('OUTPUT_EXISTS')
    try:m=register(a.model,a.plan,a.receipt,a.png_dir,rl.load(a.navigation) if a.navigation else None,a.main_pptx)
    except (ValueError,OSError,KeyError) as ex:
        print(json.dumps(dict(status='FAIL',code='GRAPH_REGISTRATION_REJECTED',message=str(ex),formal_ready=False),ensure_ascii=False));return 2
    out.write_text(json.dumps(m,ensure_ascii=False,indent=2),'utf-8');print(json.dumps({'registered':len(m['graphs']),'formal_ready':False}));return 0
if __name__=='__main__':raise SystemExit(main())
