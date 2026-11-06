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

def host_available(args):
    return bool(getattr(args,'node',None) and getattr(args,'artifact_module',None) and Path(args.artifact_module).is_file() and getattr(args,'presentation_skill',None) and (Path(args.presentation_skill)/'container_tools/artifact_tool_utils.mjs').is_file())

def office_export(path,outdir,audit):
    path=Path(path);audit=Path(audit);audit.mkdir(parents=True,exist_ok=True)
    spec=audit/(path.stem+('_word' if path.suffix=='.docx' else '')+'.office.input.json')
    save(spec,dict(input=str(path.resolve()),input_sha256=sha(path),outdir=str(Path(outdir).resolve()),receipt=str(spec.with_suffix('.receipt.json')),kind='docx' if path.suffix=='.docx' else 'pptx',pdf=str(path.with_suffix('.pdf').resolve()),width=1920))
    shell=shutil.which('pwsh') or shutil.which('powershell')
    r=subprocess.run([shell,'-NoProfile','-File',str(HERE/'visual_polish_office.ps1'),'-Manifest',str(spec)],capture_output=True,text=True,encoding='utf8',errors='replace') if shell else None
    save(spec.with_suffix('.run.json'),dict(exit_code=r.returncode if r else None,stdout=r.stdout if r else '',stderr=r.stderr if r else 'PowerShell missing'))
    if not r or r.returncode:raise RuntimeError('OFFICE_EXPORT_FAILED: '+str(spec))
    return read_json(spec.with_suffix('.receipt.json'))

def render_products(args):
    """Supported portable logic views or the explicitly available optional host."""
    import render_logic as native
    dep=native.dependencies()
    if not dep['available']:raise ValueError('DEPENDENCIES_MISSING: '+str(dep))
    plan=read_json(args.plan)
    portable=bool(plan.get('research_logic')) and all(len(p['slides'])==1 and p['slides'][0].get('coverage',{}).get('view') for p in plan['products'])
    if getattr(args,'backend','auto')!='host' and portable:
        result=native.render(args.network,args.plan,args.outdir,getattr(args,'metadata',None))
        if getattr(args,'office',False):
            graphs=[];root=Path(args.outdir)
            for row in result['files']:
                rec=office_export(row['path'],root/'previews'/row['view'],root/'office');png=rec['rendered'][0]['png'];graphs.append(dict(id='logic_'+row['view'],view=row['view'],scope='complete' if row['view']=='B' else 'overview_A' if row['view']=='A' else 'zoom',**({'parent_canvas':'logic_B'} if row['view'] not in ['A','B'] else {}),node_ids=row['node_ids'],edge_ids=row['edge_ids'],logic_snapshot=row['logic_snapshot'],pptx=row['path'],pptx_sha256=row['sha256'],png=png,png_sha256=sha(png)))
            save(root/'logic_graph_manifest.json',dict(version='pfs-logic-graphs-1',logic_snapshot=plan['logic_snapshot'],graphs=graphs,scientific_review='PARTIAL',formal_ready=False))
        return result
    if getattr(args,'backend','auto')=='portable':raise ValueError('UNSUPPORTED_PORTABLE_SCENE: this plan is not a registered logic canvas.')
    if not host_available(args):raise ValueError('UNSUPPORTED_WITHOUT_HOST: portable backend supports registered native logic canvases only; main/Figure scenes are not silently replaced with scaffolds.')
    cmd=[args.node,str(HERE/'render_evidence_products.mjs'),'--network',args.network,'--plan',args.plan,'--output-dir',args.outdir,'--build-dir',str(Path(args.outdir).parent/'build'),'--python',sys.executable,'--artifact-module',args.artifact_module,'--presentation-skill',args.presentation_skill,'--development-preview']
    if args.metadata:cmd+=['--metadata',args.metadata]
    result=subprocess.run(cmd,capture_output=True,text=True,encoding='utf8')
    if result.returncode:raise RuntimeError('HOST_RENDER_FAILED: '+result.stdout+result.stderr)
    return dict(backend='optional-host',stdout=result.stdout)

def deliver(args):
    """Reproduce products from registered facts/artifacts; no paper interpretation."""
    import research_logic as rl,delivery_contract as dc,render_logic as native
    dep=native.dependencies()
    if not dep['available']:raise ValueError(str(dep))
    m=read_json(args.research_logic);check=rl.validate_model(m)
    if not check['valid']:raise ValueError('SOURCE_LOGIC_INVALID: '+str(check))
    root=Path(args.outdir).resolve()
    if root.exists() and any(root.iterdir()):raise ValueError('OUTPUT_EXISTS')
    root.mkdir(parents=True,exist_ok=True);args._run_created=True;audit=root/'audit';audit.mkdir();visible=root/'deliverables';visible.mkdir()
    requested=list(dict.fromkeys(args.request));files=[];issues=[];checks={};main_views=[]
    def record(path,product):
        p=Path(path);files.append(dict(path=str(p.relative_to(visible)),sha256=sha(p),product=product,logic_snapshot=m['snapshot'],scientific_review='PARTIAL'))
    graph_input=read_json(args.graphs);graphs=graph_input['graphs'];checks['graphs']=dc.validate_delivery(m,graphs,verify_files=True)
    if not checks['graphs']['valid']:raise dc.ContractViolation('GRAPH_CONTRACT',checks['graphs']['errors'])
    graphmap={g['view']:g for g in graphs}
    for view in graphmap:
        if view not in graphmap:raise ValueError('GRAPH_MISSING: '+view)
        g=graphmap[view]
        for ext in ['pptx','png']:
            p=visible/('PPT' if ext=='pptx' else 'Previews')/('Logic_'+view+'.'+ext);p.parent.mkdir(exist_ok=True);shutil.copy2(g[ext],p);record(p,view if ext=='pptx' and view in ['A','B'] else 'attachment' if ext=='pptx' else 'PNG')
    if not {'A','B'}<=set(graphmap):raise ValueError('GRAPH_MISSING_A_OR_B')
    if 'main' in requested:
        if not all([args.main_pptx,args.page_map,args.plan]):issues.append('MAIN_SOURCE_AND_NATIVE_PAGE_MAP_REQUIRED')
        else:
            receipt=native.render(m['inputs']['network']['path'],args.plan,audit/'native_graphs',args.metadata,args.main_pptx,read_json(args.page_map),str(audit/'main.preview.pptx'))
            checks['main_model']=dc.main_model_audit(audit/'main.preview.pptx',m)
            checks['main_views']=dc.validate_main_views(m,audit/'main.preview.pptx',receipt['main_pages'],read_json(args.plan))
            scenes={s['coverage']['view']:s for p in read_json(args.plan)['products'] for s in p['slides']}
            for row in receipt['main_pages']:
                s=scenes[row['view']];cov=s['coverage']
                main_views.append(dict(slide=row['slide'],view=row['view'],scope=cov.get('scope','overview_A' if row['view']=='A' else 'complete' if row['view']=='B' else 'branch'),parent_view=cov.get('parent_view'),logic_snapshot=s['logic_snapshot'],node_ids=s['source_logic_node_ids'],edge_ids=s['source_logic_relation_ids'],source_ids=s['notes']['logic_source_ids'],omitted_edge_ids=cov.get('omitted_edge_ids',[]),native=True,scientific_review='PARTIAL'))
            small=[r['slide'] for r in receipt['main_pages'] if r['min_node_font_pt']<10]
            checks['main_capacity']=dict(valid=not small,unreadable_node_pages=small,threshold_pt=10)
            if not checks['main_model']['valid']:issues+=checks['main_model']['errors']
            if not checks['main_views']['valid']:issues+=checks['main_views']['errors']
            if small:issues.append('MAIN_VISUAL_CAPACITY_LIMIT:'+','.join(map(str,small)))
            if checks['main_model']['valid'] and checks['main_views']['valid'] and not small:
                p=visible/'PPT/Main.pptx';shutil.copy2(audit/'main.preview.pptx',p);record(p,'main')
                reference=receipt.get('full_b_reference')
                if reference:
                    if Path(reference).name!=reference:raise ValueError('FULL_B_REFERENCE_MUST_BE_LOCAL_FILENAME')
                    target=p.parent/reference;shutil.copy2(graphmap['B']['pptx'],target);record(target,'attachment')
    if 'Workbook' in requested:
        p=visible/'Workbook/Workbook.docx';p.parent.mkdir(exist_ok=True)
        cmd=[sys.executable,str(HERE/'build_research_workbook.py'),'--model',args.research_logic,'--graphs',args.graphs,'--output',str(p)]
        if args.workbook_bindings:cmd+=['--annotations',args.workbook_bindings]
        if args.content:cmd+=['--content',args.content]
        if getattr(args,'figure_assets',None):cmd+=['--figure-assets',args.figure_assets]
        result=subprocess.run(cmd,capture_output=True,text=True,encoding='utf8');save(audit/'workbook_run.json',dict(command=cmd,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr))
        if result.returncode:issues.append('WORKBOOK_INPUT_GAPS: see audit/workbook_run.json')
        else:
            record(p,'Workbook')
            for f in p.parent.iterdir():
                if f.suffix in ['.pptx','.csv'] or f.name=='Full_Experimental_Inventory.source.json':record(f,'attachment')
            checks['relative_links']=dc.relative_dependencies(visible,p)
            if not checks['relative_links']['valid']:issues.append('BROKEN_RELATIVE_LINK')
            # Machine records belong to audit, not the reader's folder.
            for f in list(p.parent.glob('Workbook.*.json')):shutil.move(str(f),str(audit/f.name))
    if args.office:
        for row in list(files):
            p=visible/row['path']
            if p.suffix not in ['.docx','.pptx'] or row['product']=='attachment':continue
            try:office_export(p,visible/'Previews'/p.stem,audit)
            except RuntimeError:issues.append('OFFICE_EXPORT_FAILED:'+row['path']);continue
            if p.with_suffix('.pdf').exists():record(p.with_suffix('.pdf'),'PDF')
            for png in (visible/'Previews'/p.stem).glob('*.png'):record(png,'PNG')
    graph_contract=None
    mainfile=next((f for f in files if f['product']=='main'),None)
    if mainfile and 'B' in graphmap:
        # Native file verification is independent of Office/visual acceptance.
        # Missing previews are explicit; no placeholder PNG is fabricated.
        from register_logic_graphs import navigation_record
        packed=[]
        for g in graphs:
            q=dict(g)
            for ext in ['pptx','png']:
                q[ext]=str((visible/('PPT' if ext=='pptx' else 'Previews')/('Logic_'+g['view']+'.'+ext)).resolve());q[ext+'_sha256']=sha(q[ext])
            packed.append(q)
        mainrecords=[]
        full_id=next(g['id'] for g in packed if g['view']=='B')
        for row in receipt['main_pages']:
            view=row['view'];png=visible/'Previews/Main'/('slide-'+str(row['slide']).zfill(3)+'.png')
            q=dict(id='MAIN_'+view,placement='main',view=view,source_view=view,scope='overview' if view=='B' else 'overview_A' if view=='A' else 'zoom',parent_canvas=full_id if view!='A' else None,main_slide=row['slide'],logic_snapshot=m['snapshot'],node_ids=row['node_ids'],edge_ids=row['edge_ids'],pptx=str((visible/mainfile['path']).resolve()),pptx_sha256=mainfile['sha256'],preview_status='EXPORTED_PENDING_REVIEW' if args.office else 'NOT_EXPORTED')
            if args.office:q.update(png=str(png.resolve()),png_sha256=sha(png))
            mainrecords.append(q)
        prior=next((g for g in graph_input.get('main_graphs',[]) if g.get('scope')=='overview_navigation'),None)
        if prior:mainrecords.append(navigation_record(m,packed,mainrecords,prior['full_b_reference']['path'],prior['omitted_edges']))
        elif any(g['view']=='B' for g in mainrecords):mainrecords.append(navigation_record(m,packed,mainrecords,receipt['full_b_reference'],{}))
        else:issues.append('MAIN_B_NAVIGATION_POLICY_REQUIRED')
        checks['graph_delivery']=dc.validate_delivery(m,packed+mainrecords,True,True)
        if not checks['graph_delivery']['valid']:issues+=checks['graph_delivery']['errors']
        for g in packed+mainrecords:
            for ext in ['pptx','png']:
                if g.get(ext):g[ext]=str(Path(g[ext]).relative_to(visible)).replace('\\','/')
        contract=audit/'LogicGraph.contract.json';save(contract,dict(logic_snapshot=m['snapshot'],graphs=packed,main_graphs=mainrecords))
        graph_contract=pack_coverage_file(contract,visible,'LogicGraph.contract.json');graph_contract['model']=pack_coverage_file(args.research_logic,visible,'ResearchLogic.source.json')
    present={r['product'] for r in files};missing=[x for x in requested if x not in present]
    if missing:issues.append('REQUESTED_PRODUCTS_NOT_DELIVERED:'+','.join(missing))
    (visible/'README_请保留目录.md').write_text('请保留整个交付目录。Workbook中的完整B链接相对Word所在文件夹解析；只移动Word会导致链接失效。完整B为原尺寸可编辑PPTX。\n科学终审PARTIAL。未交付与阻断见Manifest.json；本目录不含运行缓存。\n','utf8')
    assembly=read_json(audit/'Workbook.assembly.json') if (audit/'Workbook.assembly.json').exists() else None
    provenance=dict(automatic_fields=assembly.get('automatic_fields') if assembly else None,legacy_fields=assembly.get('legacy_agent_registered_fields') if assembly else None,teaching_input='registered_field_assembly' if assembly else 'explicit_prepared_content' if args.content else 'not_generated',cached_graphs=True,new_paper_extraction=False)
    coverage_sources=[]
    wb=next((x for x in files if x['product']=='Workbook'),None)
    receipt=audit/'Workbook.receipt.json'
    if wb and receipt.exists() and read_json(receipt).get('branch_coverage') is not None:
        rec=pack_coverage_file(receipt,visible,'Workbook.receipt.json');rec.update(kind='branch',artifact=wb,model=pack_coverage_file(args.research_logic,visible,'ResearchLogic.source.json'));coverage_sources.append(rec)
    main=next((x for x in files if x['product']=='main'),None)
    if main and getattr(args,'summary_plan',None):
        rec=pack_coverage_file(args.summary_plan,visible,'Summary.products.plan.json');rec.update(kind='summary',artifact=main,network=pack_coverage_file(m['inputs']['network']['path'],visible,'EvidenceNetwork.source.json'));coverage_sources.append(rec)
    review=pack_contribution_review(getattr(args,'contribution_review',None),visible)
    for f in (visible/'Audit').glob('*') if (visible/'Audit').exists() else []:record(f,'coverage_audit')
    manifest=dict(version='pfs-delivery-1',requested=requested,files=files,main_views=main_views,logic_snapshot=m['snapshot'],network_snapshot=m['network_snapshot'],scientific_review='PARTIAL',formal_ready=False,status='PARTIAL' if issues else 'READY_FOR_INDEPENDENT_ACCEPTANCE',not_delivered=missing,issues=issues,checks=checks,provenance=provenance,input_reuse='Registered facts, source-bound legacy migration and cached graphs; not unattended PDF understanding.',coverage_sources=coverage_sources,contribution_review=review)
    manifest['logic_graph_contract']=graph_contract
    coverage=dc.assess_contribution_coverage(visible,manifest,getattr(args,'profile','balanced'));manifest['contribution_coverage']=coverage
    if not coverage['valid']:manifest['status']='PARTIAL'
    save(visible/'Manifest.json',manifest);save(root/'execution.json',manifest);return manifest

def read_json(path):return knowledge.load_json(Path(path))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def pack_coverage_file(source,root,name):
    """Copy an existing audit/input, retaining its exact bytes; no fact assembly."""
    source=Path(source);target=Path(root)/'Audit'/name;target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists() and sha(target)!=sha(source):raise ValueError('COVERAGE_OUTPUT_EXISTS: '+str(target))
    if source.resolve()!=target.resolve():shutil.copy2(source,target)
    return dict(path=str(target.relative_to(root)).replace('\\','/'),sha256=sha(target))

def pack_contribution_review(path,root):
    if not path:return None
    path=Path(path);review=read_json(path);ref=pack_coverage_file(path,root,'Contribution.review.json')
    for key,item in [('basis',review['basis']),('approval_basis',review.get('approved_scope',{}).get('basis'))]:
        if item is None:continue
        source=Path(item['path']);source=source if source.is_absolute() else path.parent/source
        if sha(source)!=item['sha256']:raise ValueError('CONTRIBUTION_REVIEW_BASIS_DRIFT')
        ref[key]=pack_coverage_file(source,root,key+source.suffix)
    return ref

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


def postprocess_main(args,run,profile):
    """Final PPT only: no model writes, PDF parsing or deep-card regeneration."""
    if getattr(args,'no_polish',False):return {'status':'DISABLED_BY_OPTION'}
    import polish_presentation as polish
    main=run/'pptx'/('main_'+profile+'.pptx')
    if not main.is_file():raise ValueError('POLISH_MAIN_MISSING: '+str(main))
    result=polish.polish(main,run/'visual_polish',profile,
                         context=getattr(args,'polish_context',None),plan=getattr(args,'polish_plan',None),
                         before_receipt=getattr(args,'polish_before_receipt',None),
                         renderer=getattr(args,'polish_renderer','powerpoint'))
    return {'status':result['status'],'output':result['output'],
            'report':str(run/'visual_polish/visual_polish_report.json'),
            'USER_ACCEPTANCE':'PENDING','scientific_review':'INHERITED_NOT_UPGRADED'}

def execute(args):
    output=Path(args.outdir).resolve()
    if output.exists() and any(output.iterdir()):raise ValueError('OUTPUT_EXISTS: use a new run directory; prior results are preserved')
    output.mkdir(parents=True,exist_ok=True)
    args._run_created=True
    if not args.plan_only and not host_available(args):
        save(output/'execution.json',dict(status='BLOCKED',code='MAIN_HOST_DEPENDENCY_REQUIRED',pdf_parse_calls=0,reason='Use render-products for portable native logic views, deliver for registered artifact replay; main/Figure authoring requires the optional supported host.',formal_ready=False));return 2
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
    coverage_review=pack_contribution_review(getattr(args,'contribution_review',None),output)
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
        import delivery_contract as dc
        coverage_record=dict(kind='summary',path=str((run/'products.plan.json').relative_to(output)),sha256=sha(run/'products.plan.json'),network=dict(path='evidence_network.json',sha256=sha(output/'evidence_network.json')))
        coverage_sources=[coverage_record] if plan['products'][0].get('summary_coverage') is not None else []
        coverage_manifest=dict(coverage_sources=coverage_sources,contribution_review=coverage_review)
        content_check=dc.assess_contribution_coverage(output,coverage_manifest,profile)
        save(run/'contribution_validation.json',content_check)
        if not content_check['valid']:
            results.append(dict(profile=profile,plan_only=True,contribution_coverage=content_check));continue
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
            polish_result=postprocess_main(args,run,profile)
            actual=Path(polish_result.get('output') or run/'pptx'/('main_'+profile+'.pptx'))
            if coverage_sources:
                coverage_record['artifact']=dict(path=str(actual.relative_to(output)),sha256=sha(actual))
                content_check=dc.assess_contribution_coverage(output,coverage_manifest,profile);save(run/'contribution_validation.json',content_check)
        results.append({'profile':profile,'main_slides':len(plan['products'][0]['slides']),
                        'detailed_canvas_slides':sum(len(p['slides']) for p in plan['products'] if p['kind']=='detail'),
                        'generated_product_kinds':[p['kind'] for p in plan['products']],
                        'network_snapshot':network['snapshot'],'preflight':geometry,'plan_only':args.plan_only,
                        'visual_polish':polish_result if not args.plan_only else {'status':'NOT_RUN_PLAN_ONLY'},'contribution_coverage':content_check})
    receipt={'version':'pfs-run-1','status':'GENERATED_FOR_REVIEW' if not args.plan_only else 'PLANNED','automation':'curated_M1_replay_with_automatic_projection',
             'cache_reused':index['cache_hit'],'pdf_parse_calls':index['parse_calls'],'network_snapshot':network['snapshot'],
             'profiles':results,'scientific_review_status':'PARTIAL','formal_ready':False,'visual_review_status':'NOT_YET_RENDERED'}
    save(output/'execution.json',receipt)
    (output/'PROGRESS_CHECKPOINT.md').write_text('# PFS v1.1执行检查点\n\n已按请求的产物范围保存计划和来源记录。'+('实际PPTX已生成，需PowerPoint渲染与视觉复核。' if not args.plan_only else '本次仅内容/几何预检，未生成PPT。')+'\n\nformal_ready=false；未把fixture回放记为自动论文理解。\n',encoding='utf-8')
    if any(not r['contribution_coverage']['valid'] for r in results):
        receipt['status']='PARTIAL';save(output/'execution.json',receipt);return 2
    return 0

def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0]=='polish':
        import polish_presentation
        try:return polish_presentation.main(argv[1:])
        except (OSError,ValueError,KeyError,TypeError,RuntimeError) as exc:print(str(exc),file=sys.stderr);return 2
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run');run.add_argument('--pdf',required=True);run.add_argument('--knowledge');run.add_argument('--narrative');run.add_argument('--assets');run.add_argument('--relations');run.add_argument('--figure-story');run.add_argument('--guidance');run.add_argument('--inventory');run.add_argument('--cache-dir');run.add_argument('--metadata');run.add_argument('--outdir',required=True)
    run.add_argument('--modes',nargs='+',choices=['quick','balanced','full'],default=['balanced']);run.add_argument('--template');run.add_argument('--plan-only',action='store_true');run.add_argument('--development-preview',action='store_true')
    run.add_argument('--products',choices=['presentation','with-network','deep'],default='presentation',help='Default main PPT; add independent network or opt into deep inventory/cards.')
    run.add_argument('--no-front-matter',action='store_true',help='Keep a requested short selection without adding report cover/question/summary.')
    run.add_argument('--slides',nargs='+',help='Explicit existing scene IDs for a targeted sample; omitted pages remain recorded as deferred.')
    run.add_argument('--contribution-review',help='Optional existing source-bound review of registered contribution IDs; not automatic classification.')
    run.add_argument('--node',default=shutil.which('node'));run.add_argument('--artifact-module');run.add_argument('--presentation-skill')
    run.add_argument('--research-logic',help='Source-adjudicated logic model created after reading, Methods task identification and result mapping; shares A/B topology.')
    run.add_argument('--no-polish',action='store_true',help='Skip the shared final-PPT Visual Polish stage; original PPT remains available.')
    run.add_argument('--polish-context',help='Read-only source/panel/relationship context for the final PPT.')
    run.add_argument('--polish-plan',help='Fingerprint-bound, explicitly reviewed targeted edit plan; no plan invents no content.')
    run.add_argument('--polish-before-receipt',help='Reuse actual PowerPoint previews only when input and PNG fingerprints match.')
    run.add_argument('--polish-renderer',choices=['powerpoint','none'],default='powerpoint',help='none is a diagnostic run and cannot pass visual acceptance.')
    val=sub.add_parser('validate-products');val.add_argument('--network',required=True);val.add_argument('--plan',required=True);val.add_argument('--metadata')
    rp=sub.add_parser('render-products',help='Render a validated registered plan; portable logic or optional host.')
    for key in ['network','plan','outdir']:rp.add_argument('--'+key,required=True)
    rp.add_argument('--metadata');rp.add_argument('--backend',choices=['auto','portable','host'],default='auto');rp.add_argument('--node',default=shutil.which('node'));rp.add_argument('--artifact-module');rp.add_argument('--presentation-skill');rp.add_argument('--development-preview',action='store_true',required=True)
    rp.add_argument('--office',action='store_true',help='Export native logic views through installed PowerPoint and produce the existing graph manifest for deliver.')
    dl=sub.add_parser('deliver',help='Source-checked delivery from registered models and retained input artifacts.')
    for key in ['research-logic','graphs','outdir']:dl.add_argument('--'+key,required=True)
    for key in ['main-pptx','page-map','plan','metadata','workbook-bindings','content']:dl.add_argument('--'+key)
    dl.add_argument('--figure-assets',help='Optional verified original Figure registry for teaching Workbook.')
    dl.add_argument('--summary-plan',help='Existing report plan containing summary_coverage, bound to the actual delivered main PPT.')
    dl.add_argument('--contribution-review',help='Optional existing sourced contribution audit; copied with its hashed review/approval basis.')
    dl.add_argument('--profile',choices=['quick','balanced','full'],default='balanced',help='Coverage policy only; does not change scientific facts or regenerate diagrams.')
    dl.add_argument('--request',nargs='+',choices=['main','A','B','Workbook','PNG','PDF'],default=['main','A','B','Workbook','PNG','PDF']);dl.add_argument('--office',action='store_true');dl.add_argument('--development-preview',action='store_true',required=True)
    pkg=sub.add_parser('check-delivery');pkg.add_argument('--root',required=True);pkg.add_argument('--profile',choices=['quick','balanced','full'],default='balanced')
    args=p.parse_args(argv)
    def failure(exc,internal=False):
        import traceback
        out=Path(args.outdir) if getattr(args,'outdir',None) else None
        if out and not out.exists():out.mkdir(parents=True);args._run_created=True
        if out and getattr(args,'_run_created',False):
            save(out/'failure.json',dict(status='FAIL',code='INTERNAL_ERROR' if internal else getattr(exc,'code','INPUT_OR_CONTRACT_REJECTED'),errors=getattr(exc,'errors',[]),type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc() if internal else None,formal_ready=False))
            for f in [out/'execution.json',out/'deliverables/Manifest.json']:
                if f.exists():f.rename(f.with_suffix('.failed.json'))
    try:
        if args.command=='check-delivery':
            from delivery_contract import check_package
            result=check_package(args.root,args.profile);print(json.dumps(result,ensure_ascii=False));return 0 if result['valid'] and result['requested_complete'] else 2
        if args.command=='render-products':
            print(json.dumps(render_products(args),ensure_ascii=False));return 0
        if args.command=='deliver':
            result=deliver(args);print(json.dumps(dict(status=result['status'],not_delivered=result['not_delivered'],issues=result['issues'],contribution_coverage=result['contribution_coverage']),ensure_ascii=False));return 0 if not result['issues'] and result['contribution_coverage']['valid'] else 2
        if args.command=='validate-products':
            network=read_json(args.network);check=en.validate_network(network,verify_files=True)
            if not check['valid']:print(json.dumps(check,ensure_ascii=False));return 1
            meta=bibliography(args.metadata,network['paper']['id']) if args.metadata else {}
            result=projection.validate_products(network,read_json(args.plan),meta);print(json.dumps(result,ensure_ascii=False));return 0 if result['valid'] else 1
        return execute(args)
    except (OSError,ValueError,KeyError,TypeError,RuntimeError) as exc:
        failure(exc);print(str(exc),file=sys.stderr);return 2
    except Exception as exc:
        failure(exc,internal=True)
        import traceback
        traceback.print_exc();return 1

if __name__=='__main__':raise SystemExit(main())
