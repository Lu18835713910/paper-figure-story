"""Run the existing PFS contracts on SELF-AUTHORED examples only.

Not a paper analyzer, scheduler, aggregator or blind-test answer generator.
All outputs/logs go to a new directory supplied by the executing Agent.
"""
from pathlib import Path
import argparse, copy, hashlib, importlib.util, json, os, subprocess, sys

ROOT=Path(__file__).resolve().parents[2]
def save(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--outdir',required=True,type=Path)
    a=ap.parse_args();out=a.outdir.resolve()
    if out.exists() and any(out.iterdir()):ap.error('Use a NEW empty --outdir.')
    out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location('self_authored_example',Path(__file__).with_name('make_synthetic_example.py'))
    ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex)
    records=[]
    def cli(name,script,args,expected=0):
        command=[sys.executable,'-B',str(ROOT/'scripts'/script),*map(str,args)]
        p=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',env={**os.environ,'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1'})
        (out/(name+'.stdout.log')).write_text(p.stdout,'utf-8')
        (out/(name+'.stderr.log')).write_text(p.stderr,'utf-8')
        records.append(dict(case=name,command=command,exit_code=p.returncode,expected_exit=expected,passed=p.returncode==expected))
        save(out/'commands.json',records)
        if p.returncode!=expected:raise RuntimeError(name+': see saved logs')
        return p
    # Fixed, public synthetic content. Never accepts a real-paper input path.
    mini=ex.make(out/'minimal',count=2)
    f=ex.make(out/'seven_channels',count=7)
    for name,z in [('minimal',mini),('seven',f)]:
        cli(name+'_M1','validate_knowledge.py',[z['knowledge'],'--verify-files','--json','--report',out/(name+'.validation.json')])
    def run(name,z,extra=(),expected=0):
        return cli(name,'run_pfs.py',['run','--pdf',z['pdf'],'--knowledge',z['knowledge'],'--cache-dir',z['cache'],'--metadata',z['metadata'],'--outdir',out/name,'--products','with-network','--plan-only',*extra],expected)
    run('small_default',mini)
    p=run('over_capacity',f,expected=2)
    assert 'A_NEEDS_GUIDANCE' in p.stderr and 'capacity 6' in p.stderr
    run('guided_recovery',f,['--guidance',f['guidance']])
    # The lightest supported route uses existing statement identities only.
    # These are fixed synthetic references, not keyword-based paper matching.
    statement_only=json.loads(Path(f['guidance']).read_text('utf-8'))
    source_network=json.loads(Path(f['network']).read_text('utf-8'))
    limits=[s['id'] for s in source_network['statements'] if s['text']=='Synthetic software fixture only; no patients, biological validation, or causal claim.']
    assert limits
    for record in statement_only['records']:
        if record['id']=='LIMIT':record['source_statement_ids']=limits[:1]
        record['source_spans']=[]
    sp=out/'guidance.statement_only.json';save(sp,statement_only)
    run('statement_only_recovery',f,['--guidance',sp])
    cli('explicit_index','scientific_index.py',['validate','--index',Path(f['root'])/'scientific_index.json'])
    cachemeta=json.loads((Path(f['cache'])/'metadata.json').read_text('utf-8'))
    compat=out/'paper_index.compat.json'
    save(compat,dict(source_pdf=cachemeta['path'],file_sha256=cachemeta['sha256'],page_count=cachemeta['physical_page_count']))
    cli('index_skeleton_from_existing_cache','scientific_index.py',['init','--paper-index',compat,'--output',out/'scientific_index.pending.json'])
    cli('pending_index_must_fail','scientific_index.py',['validate','--index',out/'scientific_index.pending.json'],expected=2)
    cli('official_assemble','scientific_index.py',['assemble','--index',Path(f['root'])/'scientific_index.json','--network',f['network'],'--adjudication',f['logic'],'--output',out/'research_logic.assembled.json'])
    cli('assembled_logic','research_logic.py',['--model',out/'research_logic.assembled.json'])
    cli('explicit_logic','research_logic.py',['--model',f['logic']])
    run('explicit_recovery',f,['--research-logic',f['logic']])
    cli('views','project_research_logic.py',['--network',f['network'],'--model',f['logic'],'--outdir',out/'views','--views','A','B'])
    cli('portable_dependencies','render_logic.py',['--check-dependencies'])
    cli('native_AB','run_pfs.py',['render-products','--network',f['network'],'--plan',out/'views/products.plan.json','--metadata',out/'views/metadata.resolved.json','--outdir',out/'native_AB','--backend','portable','--development-preview'])
    # Repeatable M1 failure -> minimum legal correction through the real CLI.
    base=json.loads(Path(mini['knowledge']).read_text('utf-8'))
    variants={}
    k=copy.deepcopy(base);k['entities'][0]['kind']='analysis';variants['invalid_analysis_kind']=k
    for kind in ['claim','processing']:
        k=copy.deepcopy(base);k['entities'][0]['kind']=kind;k['entities'][0].pop('limits');variants[kind+'_missing_limits']=k
    k=copy.deepcopy(base);k['stories'][0]['method_ids']=['E1'];variants['invalid_story_method']=k
    k=copy.deepcopy(base);k['stories'][0]['evidence_ids']=['C1'];variants['invalid_story_evidence']=k
    # A separate explicitly authored dataflow source, no invented real-paper flow.
    good=copy.deepcopy(base)
    datafile=out/'dataflow.txt';datafile.write_text('Synthetic protocol: PRODUCER emits DATA; CONSUMER reads the same DATA. This is not experimental time or biological evidence.','utf-8')
    ref=dict(document_id='FLOW',locator=dict(section='Synthetic protocol',context=datafile.read_text('utf-8')),verification='pending')
    good['document_registry'].append(dict(id='FLOW',role='main_paper',format='text',title='Self-authored dataflow contract example',version='1',availability='available',sha256=hashlib.sha256(datafile.read_bytes()).hexdigest(),hash_status='verified',source_locator='self-authored exact text',path=str(datafile)))
    for id,kind,ins,outs in [('PRODUCER','processing',[],['DATA']),('DATA','dataset',[],[]),('CONSUMER','processing',['DATA'],[])]:
        e=copy.deepcopy(base['entities'][0]);e.update(id=id,kind=kind,name=id,inputs=ins,outputs=outs,parameters=[],source_refs=[ref],limits=['Only the explicitly written synthetic dataflow is asserted.']);good['entities'].append(e)
    good['relations'].append(dict(id='FLOW_EDGE',**{'from':'PRODUCER','to':'CONSUMER'},type='data_depends_on',provenance='paper',certainty='paper_reported',mandatory=True,rationale='Explicit producer output and consumer input share DATA identity.',source_refs=[ref],data_bindings=[dict(output_id='DATA',input_id='DATA',usage='primary')]))
    k=copy.deepcopy(good);k['relations'][-1].pop('data_bindings');variants['missing_data_binding']=k
    k=copy.deepcopy(good);k['relations'][-1]['data_bindings'][0]['output_id']='UNKNOWN';variants['unknown_data_identity']=k
    gp=out/'dataflow.valid.json';save(gp,good)
    cli('dataflow_valid','validate_knowledge.py',[gp,'--verify-files','--json'])
    for name,k in variants.items():
        p=out/'invalid'/ (name+'.json');save(p,k)
        cli(name,'validate_knowledge.py',[p,'--verify-files','--json'],expected=1)
    # No blind-test input is used anywhere above.
    import evidence_network as en, research_logic as rl, project_research_logic as pj, delivery_contract as dc
    from pptx import Presentation
    net=rl.load(f['network']);model=rl.load(f['logic'])
    guided=rl.load(out/'guided_recovery/balanced/products.plan.json')
    A=next(s for s in guided['products'][0]['slides'] if s['id']=='A_overview')
    B=next(p for p in guided['products'] if p['kind']=='detail')['slides'][0]
    assert set('C'+str(i) for i in range(1,8))<=set(A['source_node_ids'])
    assert set(B['source_node_ids'])=={n['id'] for n in net['nodes']}
    assert set(B['source_relation_ids'])=={e['id'] for e in net['edges']}
    assert guided['products'][0]['summary_coverage']['omitted_claims']=={}
    for name in ['guided_recovery','explicit_recovery']:
        receipt=rl.load(out/name/'execution.json')
        assert receipt['cache_reused'] and receipt['pdf_parse_calls']==0
    views=rl.load(out/'views/products.plan.json')
    check=pj.validate_AB(model,views['products'][0],views['products'][1]);assert check['valid']
    for product in views['products']:
        path=out/'native_AB'/ (product['kind']+'_balanced.pptx')
        prs=Presentation(path);view=product['slides'][0]['coverage']['view']
        ids,edges=dc.rendered_topology(path,view)
        expected_nodes=set(model['core']['nodes']) if view=='A' else {n['id'] for n in model['nodes']}
        expected_edges=set(model['core']['edges']) if view=='A' else {e['id'] for e in model['edges']}
        assert (ids,edges)==(expected_nodes,expected_edges)
        assert not any(s.shape_type==13 for sl in prs.slides for s in sl.shapes)
    save(out/'assertions.json',dict(M1=True,recovery=True,source_network_valid=en.validate_network(net,verify_files=True)['valid'],all_seven_claims_mapped=True,source_B_nodes_and_edges_unchanged=True,summary_omissions={},cache_reused_without_reparse=True,single_shared_E1=sum(n['id']=='E1' for n in net['nodes'])==1,independent_validations_added=0,AB=check,native_shapes_reopened=True,main_Figure_PPT='NOT_TESTED',Workbook='NOT_TESTED',Full='NOT_TESTED',scientific_review='PARTIAL',visual_acceptance='NOT_TESTED'))
    print(json.dumps(dict(status='EXAMPLE_EXECUTION_PASS',outdir=str(out),commands=len(records),scope='self-authored M1 and A recovery, not real-paper understanding or Full delivery'),ensure_ascii=False))
    return 0
if __name__=='__main__':raise SystemExit(main())
