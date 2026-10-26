#!/usr/bin/env python3
"""Explicit v1.1 candidate entry: PDF/cache + reviewed M1 -> common network -> A/B/C.

PDF indexing is automatic. Scientific semantic extraction is a separately
reviewed upstream activity; missing it is an explicit resumable gate, not a pass.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path
import evidence_network as en
import project_evidence_products as projection
import validate_knowledge as knowledge

HERE=Path(__file__).resolve().parent
DEFAULT_TEMPLATE=HERE.parent/'assets/default_academic_blue_174994.pptx'

def read_json(path):return knowledge.load_json(Path(path))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def index_pdf(pdf, cache):
    pdf=Path(pdf).resolve();cache=Path(cache).resolve()
    if not pdf.is_file() or pdf.suffix.lower()!='.pdf':raise ValueError('PDF_INPUT: existing PDF required')
    with pdf.open('rb') as stream:
        if stream.read(5)!=b'%PDF-':raise ValueError('PDF_MAGIC: input is not a PDF')
    digest=sha(pdf);meta_path=cache/'metadata.json'
    if meta_path.is_file():
        meta=read_json(meta_path)
        count=meta.get('physical_page_count',0)
        pages=[cache/f'page-{i:02}.txt' for i in range(1,count+1)]
        if meta.get('sha256')==digest and count>0 and all(p.is_file() for p in pages):
            return {'cache_hit':True,'parse_calls':0,'metadata_path':str(meta_path),'sha256':digest,'page_count':count,
                    'text_files':[str(p) for p in pages],'semantics_verified':False}
        raise ValueError('CACHE_DRIFT: cache exists but its source or page inventory is stale; use a new cache directory')
    import pdfplumber
    cache.mkdir(parents=True,exist_ok=True);pages=[]
    with pdfplumber.open(pdf) as doc:
        for i,page in enumerate(doc.pages,1):
            tx=page.extract_text(layout=False) or ''
            target=cache/f'page-{i:02}.txt';target.write_text(tx,encoding='utf-8');pages.append(str(target))
    meta={'case':pdf.stem,'path':str(pdf),'sha256':digest,'physical_page_count':len(pages),'parseable':bool(pages),
          'parse_calls':1,'engine':'pdfplumber','semantic_review_status':'NOT_TESTED'}
    save(meta_path,meta)
    return {'cache_hit':False,'parse_calls':1,'metadata_path':str(meta_path),'sha256':digest,'page_count':len(pages),
            'text_files':pages,'semantics_verified':False}

def extraction_candidates(index, output):
    candidates=[];figures=[]
    for number,filename in enumerate(index['text_files'],1):
        tx=Path(filename).read_text(encoding='utf-8')
        for match in re.finditer(r'(?im)^\s*(?:Figure|Fig\.)\s*(\d+)\s*[:.]?[^\n]*',tx):
            figures.append({'candidate_id':f'figure.{number}.{match.start()}','physical_page':number,
                            'text':match.group(0).strip(),'source_path':filename,'start':match.start(),'end':match.end(),
                            'sha256':sha(filename),'status':'CANDIDATE_NOT_VERIFIED'})
        for match in list(re.finditer(r'[^.!?\n]{45,240}[.!?]',tx))[:12]:
            candidates.append({'candidate_id':f'sentence.{number}.{match.start()}','text':match.group(0).strip(),
                               'source_path':filename,'physical_page':number,'start':match.start(),'end':match.end(),
                               'sha256':sha(filename),'assertion_type':'UNCLASSIFIED','semantic_review_status':'NOT_TESTED'})
    result={'version':'pfs-extraction-candidates-1','source_pdf_sha256':index['sha256'],'figure_candidates':figures,'sentence_candidates':candidates,
            'automation':'PDF text and candidate locations only','scientific_edges':[], 'formal_ready':False,
            'blocker':'REVIEWED_KNOWLEDGE_REQUIRED: candidates are not scientific facts, experiment designs or verified relations.'}
    save(Path(output)/'extraction_candidates.json',result);return result

def bibliography(path,paper_id=None):
    if not path:return {}
    obj=read_json(path)
    if 'citation_short' in obj:return obj
    if paper_id:
        for key,value in obj.items():
            if isinstance(value,dict) and (key.lower() in paper_id.lower() or value.get('paper_id')==paper_id):return value
    raise ValueError('METADATA_MATCH: pass a single-paper metadata object or a keyed registry matching paper ID')

def write_reviews(network,plan,output):
    output=Path(output);nm={n['id']:n for n in network['nodes']};sm={s['id']:s for s in network['statements']}
    records=[];md=['# 本轮实际页面与逐句来源审核','',f"Network snapshot: `{network['snapshot']}`",'',
                  '各层分开：文件/页码定位可自动检查；语义、图像/panel和独立终审不因程序通过而升级。','']
    coverage=[]
    for product in plan['products']:
        for i,scene in enumerate(product['slides'],1):
            display_records={r['id']:r for r in scene.get('notes',{}).get('display_records',[])}
            page=f"{product['kind']}:{i}:{scene['id']}"
            md += [f'## {page}', '',scene['title'],'', '|语句/对象ID|实际展示文字|原文/方法/Figure定位|证据身份与待核|', '|---|---|---|---|']
            for element in scene['elements']:
                if element['kind']!='text':continue
                sids=element.get('statement_ids',[]);nids=element.get('source_node_ids',[])
                display=[display_records[r] for r in element.get('display_record_ids',[]) if r in display_records]
                bound=[sm[s] for s in sids if s in sm];nodes=[nm[n] for n in nids if n in nm]
                refs=[r for b in bound+nodes for r in b.get('source_refs',[])]
                locs=[]
                for ref in refs:
                    loc=ref.get('locator',{});label=ref.get('document_id','')+' p.'+str(loc.get('physical_page',ref.get('physical_page','待核')))+' '+str(loc.get('section',''))
                    if label not in locs:locs.append(label)
                pointers=[s['source_pointer'] for s in bound]+[n.get('source_pointer') or {'input_kind':'knowledge','pointer':n['m1_pointer']} for n in nodes]
                source_spans=[v for r in display for v in r.get('source_spans',[])]
                for span in source_spans:
                    locs.append('原文缓存 '+Path(span['path']).name+' chars '+str(span['start'])+':'+str(span['end']))
                kind='scientific_statement' if pointers else 'presentation_label_or_explicit_unknown'
                if display:kind='source_bound_display_paraphrase_pending_semantic_review'
                record={'page_id':page,'element_id':element['id'],'actual_display_text':element['text'],'statement_ids':sids,'node_ids':nids,
                        'source_references':refs,'source_pointers':pointers,'assertion_type':kind,
                        'display_record_ids':element.get('display_record_ids',[]),'display_source_spans':source_spans,
                        'conditions_and_statistics':'See bound M1 node parameters/quantities; missing fields remain not_checked.',
                        'evidence_status':'INHERITED_ONLY' if pointers else 'NOT_APPLICABLE','semantic_review_status':'PARTIAL' if pointers else 'NOT_APPLICABLE',
                        'independent_review_status':'NOT_TESTED','unresolved_issues':network['review']['unresolved_issues'],'formal_ready':False}
                records.append(record)
                txt=element['text'].replace('\n','<br>').replace('|','／')
                md.append('|'+element['id']+'|'+txt+'|'+('<br>'.join(locs) or '讲述标签/明确待核字段')+'|'+('PARTIAL；未独立终审' if pointers else '不作为论文观察')+'|')
            md += ['', '图像及覆盖：'+json.dumps(scene.get('coverage',{}),ensure_ascii=False),'']
            coverage.append({'page_id':page,'product':scene['product'],'figure_ids':scene['figure_ids'],'visible_asset_ids':scene.get('visible_asset_ids',[]),
                             'source_statement_ids':scene['source_statement_ids'],'source_relation_ids':scene['source_relation_ids'],
                             'coverage':scene.get('coverage',{})})
    review={'version':'pfs-page-review-1','network_snapshot':network['snapshot'],'product_plan_hash':plan['projection_hash'],
            'inputs':network['inputs'],'records':records,'coverage':coverage,'formal_ready':False,
            'semantic_review_status':'PARTIAL','independent_scientific_review':'NOT_TESTED'}
    save(output/'source_review.json',review)
    (output/'source_review.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    return review

def plan_geometry(plan):
    findings=[]
    for product in plan['products']:
        for slide in product['slides']:
            for e in slide['elements']:
                p=e['position']
                if any(not isinstance(v,(int,float)) for v in p.values()) or p['width']<=0 or p['height']<=0:
                    findings.append({'code':'INVALID_GEOMETRY','slide':slide['id'],'element':e['id']});continue
                if p['left']<0 or p['top']<0 or p['left']+p['width']>product['width']+.1 or p['top']+p['height']>product['height']+.1:
                    findings.append({'code':'OFF_CANVAS','slide':slide['id'],'element':e['id']})
                if e['kind']=='text' and len(e['text'].split('\n'))*e['font_size']*1.25>p['height']+2:
                    findings.append({'code':'TEXT_HEIGHT_RISK','slide':slide['id'],'element':e['id'],'lines':len(e['text'].split('\n'))})
    return {'valid':not findings,'findings':findings,'claim_boundary':'Planning preflight, not actual PowerPoint text or visual validation.'}

def execute(args):
    output=Path(args.outdir).resolve()
    if output.exists() and any(output.iterdir()):raise ValueError('OUTPUT_EXISTS: use a new run directory; prior results are preserved')
    output.mkdir(parents=True,exist_ok=True)
    args._run_created=True
    (output/'PROGRESS_CHECKPOINT.md').write_text('# PFS v1.1执行检查点\n\n输入校验中。\n',encoding='utf-8')
    cache=Path(args.cache_dir).resolve() if args.cache_dir else output/'cache'
    index=index_pdf(args.pdf,cache);save(output/'pdf_index_receipt.json',index)
    if not args.knowledge:
        extraction_candidates(index,output)
        save(output/'agent_handoff.json',{'version':'pfs-agent-handoff-1','status':'AGENT_ACTION_REQUIRED',
             'pdf':str(Path(args.pdf).resolve()),'source_sha256':index['sha256'],'cache':str(cache),
             'knowledge_schema':str(HERE.parent/'schemas/knowledge_v1_1.schema.json'),
             'instructions':'Codex reads the cached paper, Methods and original Figures, classifies the article, builds and validates source-bound M1 and asset JSON, then resumes run in a new output directory. The human user is not asked to author JSON. Candidates are not verified claims.',
             'review_gate_retained':True})
        save(output/'execution.json',{'status':'PARTIAL','exit_code':3,'automation':'automatic_pdf_index_and_candidate_extraction',
             'scientific_semantic_extraction':'NOT_IMPLEMENTED_AS_UNATTENDED_CLI','three_products_generated':False,'formal_ready':False,
             'blocker':'REVIEWED_KNOWLEDGE_REQUIRED','resume_command':'Supply reviewed M1 JSON with --knowledge and use a new output directory.'})
        (output/'PROGRESS_CHECKPOINT.md').write_text('# PFS v1.1执行检查点\n\nPARTIAL：PDF索引和候选定位已自动完成；尚未形成语义核验的M1科学事实和关系。未把候选句或图注自动冒充三类正式产物。可复用缓存，补齐经审核的M1 JSON后继续。\n',encoding='utf-8')
        return 3
    model=read_json(args.knowledge)
    if index['sha256'] not in {d.get('sha256') for d in model['document_registry']}:raise ValueError('PDF_KNOWLEDGE_MISMATCH')
    network=en.build_network(args.knowledge,narrative_path=args.narrative,assets_path=args.assets,source_cache=cache,relations_path=args.relations,figure_story_path=args.figure_story,experiment_inventory_path=args.inventory)
    check=en.validate_network(network,verify_files=True)
    save(output/'network_validation.json',check)
    if not check['valid']:raise ValueError('NETWORK_INVALID: '+json.dumps(check['errors'],ensure_ascii=False))
    save(output/'evidence_network.json',network)
    if args.inventory:
        import experiment_inventory as ei
        ei.write_audit(read_json(args.inventory),output/'inventory')
    meta=bibliography(args.metadata,network['paper']['id']) if args.metadata else {}
    if args.guidance:meta['display_guidance']={'path':str(Path(args.guidance).resolve()),'sha256':sha(args.guidance)}
    if getattr(args,'research_logic',None):meta['research_logic']={'path':str(Path(args.research_logic).resolve()),'sha256':sha(args.research_logic)}
    if meta:save(output/'bibliography.resolved.json',meta)
    template=Path(args.template or DEFAULT_TEMPLATE).resolve()
    if template.suffix.lower()!='.pptx' or not template.is_file():raise ValueError('TEMPLATE_INPUT: existing PPTX required')
    results=[]
    for profile in args.modes:
        run=output/profile;run.mkdir()
        delivery={'version':'pfs-delivery-1','scope':getattr(args,'products','presentation'),
                  'report_sections':not getattr(args,'no_front_matter',False),'slide_ids':getattr(args,'slides',None)}
        plan=projection.project_products(network,profile,meta,{'path':str(template),'sha256':sha(template)},delivery)
        valid=projection.validate_products(network,plan,meta)
        save(run/'products.plan.json',plan);save(run/'plan_validation.json',valid)
        if not valid['valid']:raise ValueError('PRODUCT_PLAN_INVALID')
        geometry=plan_geometry(plan);save(run/'geometry_preflight.json',geometry)
        write_reviews(network,plan,run)
        if not args.plan_only:
            if not args.development_preview:raise ValueError('PREVIEW_REQUIRED: no independent scientific final review; use explicit --development-preview')
            for name in ['node','artifact_module','presentation_skill']:
                if not getattr(args,name):raise ValueError('RUNTIME_REQUIRED: '+name)
            command=[args.node,str(HERE/'render_evidence_products.mjs'),'--network',str(output/'evidence_network.json'),'--plan',str(run/'products.plan.json'),
                     '--output-dir',str(run/'pptx'),'--build-dir',str(run/'build'),'--python',sys.executable,'--artifact-module',args.artifact_module,
                     '--presentation-skill',args.presentation_skill,'--development-preview']
            if meta:command+=['--metadata',str(output/'bibliography.resolved.json')]
            rendered=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',env={**os.environ,'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1'})
            (run/'render.stdout.log').write_text(rendered.stdout,encoding='utf-8');(run/'render.stderr.log').write_text(rendered.stderr,encoding='utf-8')
            if rendered.returncode:raise RuntimeError('RENDER_FAILED: see '+str(run/'render.stderr.log'))
        results.append({'profile':profile,'main_slides':len(plan['products'][0]['slides']),
                        'detailed_canvas_slides':sum(len(p['slides']) for p in plan['products'] if p['kind']=='detail'),
                        'generated_product_kinds':[p['kind'] for p in plan['products']],
                        'network_snapshot':network['snapshot'],'preflight':geometry,'plan_only':args.plan_only})
    receipt={'version':'pfs-run-1','status':'GENERATED_FOR_REVIEW' if not args.plan_only else 'PLANNED','automation':'curated_M1_replay_with_automatic_projection',
             'cache_reused':index['cache_hit'],'pdf_parse_calls':index['parse_calls'],'network_snapshot':network['snapshot'],
             'profiles':results,'scientific_review_status':'PARTIAL','formal_ready':False,'visual_review_status':'NOT_YET_RENDERED'}
    save(output/'execution.json',receipt)
    (output/'PROGRESS_CHECKPOINT.md').write_text('# PFS v1.1执行检查点\n\n已按请求的产物范围保存计划和来源记录。'+('实际PPTX已生成，需PowerPoint渲染与视觉复核。' if not args.plan_only else '本次仅内容/几何预检，未生成PPT。')+'\n\nformal_ready=false；未把fixture回放记为自动论文理解。\n',encoding='utf-8')
    return 0

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run');run.add_argument('--pdf',required=True);run.add_argument('--knowledge');run.add_argument('--narrative');run.add_argument('--assets');run.add_argument('--relations');run.add_argument('--figure-story');run.add_argument('--guidance');run.add_argument('--inventory');run.add_argument('--cache-dir');run.add_argument('--metadata');run.add_argument('--outdir',required=True)
    run.add_argument('--modes',nargs='+',choices=['quick','balanced','full'],default=['balanced']);run.add_argument('--template');run.add_argument('--plan-only',action='store_true');run.add_argument('--development-preview',action='store_true')
    run.add_argument('--products',choices=['presentation','with-network','deep'],default='presentation',help='Default main PPT; add independent network or opt into deep inventory/cards.')
    run.add_argument('--no-front-matter',action='store_true',help='Keep a requested short selection without adding report cover/question/summary.')
    run.add_argument('--slides',nargs='+',help='Explicit existing scene IDs for a targeted sample; omitted pages remain recorded as deferred.')
    run.add_argument('--node',default=shutil.which('node'));run.add_argument('--artifact-module');run.add_argument('--presentation-skill')
    run.add_argument('--research-logic',help='Source-adjudicated logic model created after reading, Methods task identification and result mapping; shares A/B topology.')
    val=sub.add_parser('validate-products');val.add_argument('--network',required=True);val.add_argument('--plan',required=True);val.add_argument('--metadata')
    args=p.parse_args(argv)
    try:
        if args.command=='validate-products':
            network=read_json(args.network);check=en.validate_network(network,verify_files=True)
            if not check['valid']:print(json.dumps(check,ensure_ascii=False));return 1
            meta=bibliography(args.metadata,network['paper']['id']) if args.metadata else {}
            result=projection.validate_products(network,read_json(args.plan),meta);print(json.dumps(result,ensure_ascii=False));return 0 if result['valid'] else 1
        return execute(args)
    except (OSError,ValueError,KeyError,TypeError,RuntimeError) as exc:
        if getattr(args,'outdir',None) and getattr(args,'_run_created',False):
            out=Path(args.outdir)
            if out.exists():save(out/'failure.json',{'status':'FAIL','type':type(exc).__name__,'message':str(exc),'formal_ready':False})
        print(str(exc),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
