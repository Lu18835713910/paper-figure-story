"""Validate requested full-detail network delivery against one authoritative source model."""
import hashlib,json,re
from pathlib import Path

class ContractViolation(ValueError):
    def __init__(self,code,errors):
        self.code=code;self.errors=errors
        super().__init__(code+': '+str(errors))

def relative_dependencies(root,docx):
    """Resolve the actual Word relationship target relative to its containing file."""
    from zipfile import ZipFile
    from lxml import etree as ET
    from urllib.parse import unquote,urlparse
    root=Path(root).resolve();docx=Path(docx).resolve();rows=[]
    with ZipFile(docx) as z:
        for part in z.namelist():
            if not part.endswith('.rels'):continue
            for rel in ET.fromstring(z.read(part)):
                if rel.get('TargetMode')!='External':continue
                target=rel.get('Target','');parsed=urlparse(target)
                if parsed.scheme in ['https','http','mailto']:continue
                path=(docx.parent/unquote(parsed.path).replace('\\','/')).resolve()
                safe=path==root or root in path.parents
                rows.append(dict(target=target,resolved=str(path),valid=safe and path.is_file(),inside_delivery=safe))
    return dict(valid=all(r['valid'] for r in rows),links=rows)

def main_model_audit(path,model):
    from pptx import Presentation
    rows=[];errors=[]
    for i,sl in enumerate(Presentation(path).slides,1):
        logical=any(s.name.startswith(('RC_LOGIC_','RC_EDGE_LOGIC_')) for s in sl.shapes)
        if not logical:continue
        notes=sl.notes_slide.notes_text_frame.text
        ok=model['snapshot'] in notes;rows.append(dict(slide=i,authoritative_model=ok))
        if not ok:errors.append('MAIN_LOGIC_MODEL_DRIFT:'+str(i))
    return dict(valid=not errors,logic_pages=rows,errors=errors)

def coverage_file(root,record):
    """Read only a hash-bound file inside the delivered directory."""
    root=Path(root).resolve();p=(root/record['path']).resolve()
    if root not in p.parents or not p.is_file():raise ValueError('COVERAGE_FILE_MISSING_OR_EXTERNAL')
    if hashlib.sha256(p.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('COVERAGE_FILE_DRIFT')
    return p

def assess_contribution_coverage(root,manifest,profile='balanced'):
    """Consume existing coverage, actual objects and optional sourced audit decisions.

    Review records classify existing IDs only. They do not add scientific facts,
    prove that every paper contribution was discovered, or upgrade science review.
    """
    import research_logic as rl
    root=Path(root);errors=[];warnings=[];rows=[];review=None
    def load(rec):return json.loads(coverage_file(root,rec).read_text('utf-8-sig'))
    def require(ok,code):
        if not ok:raise ValueError(code)
    def basis(rec):coverage_file(root,rec)
    try:
        kinds=[r['kind'] for r in manifest.get('coverage_sources',[])]
        require(len(kinds)==len(set(kinds)),'COVERAGE_DUPLICATE_KIND')
        for f in manifest.get('files',[]):
            name=f['path'].replace('\\','/').split('/')[-1]
            expected_kind={'Workbook.receipt.json':'branch','Summary.products.plan.json':'summary'}.get(name)
            if f.get('product')=='coverage_audit' and expected_kind:require(expected_kind in kinds,'COVERAGE_DECLARATION_MISSING')
        if manifest.get('contribution_review'):
            ref=manifest['contribution_review'];review=load(ref)
            require(bool(review.get('reviewer')) and bool(review.get('review_scope')),'CONTRIBUTION_REVIEW_SCOPE_REQUIRED')
            require(review.get('status') in ['SOURCE_REFERENCED_REVIEW_RECORDED','PARTIAL'],'CONTRIBUTION_REVIEW_NOT_RECORDED')
            require(all(i.get('kind') in ['branch','summary'] for i in review.get('items',[])),'CONTRIBUTION_REVIEW_KIND_INVALID')
            # The packaged copy is bound to the original audit basis by hash.
            require(ref['basis']['sha256']==review['basis']['sha256'],'CONTRIBUTION_REVIEW_BASIS_DRIFT');basis(ref['basis'])
            approval=review.get('approved_scope')
            if approval:
                require(approval.get('kind')=='limited' and bool(approval.get('approved_by')) and bool(approval.get('reason')),'CONTRIBUTION_SCOPE_APPROVAL_REQUIRED')
                require(ref['approval_basis']['sha256']==approval['basis']['sha256'],'CONTRIBUTION_SCOPE_BASIS_DRIFT');basis(ref['approval_basis'])
        for rec in manifest.get('coverage_sources',[]):
            kind=rec['kind'];data=load(rec);artifact=coverage_file(root,rec['artifact']) if rec.get('artifact') else None
            product='Workbook' if kind=='branch' else 'main'
            delivered=[f for f in manifest.get('files',[]) if f.get('product')==product]
            if delivered:
                require(artifact is not None and any(f['path'].replace('\\','/')==rec['artifact']['path'].replace('\\','/') and f['sha256']==rec['artifact']['sha256'] for f in delivered),'COVERAGE_ARTIFACT_BINDING_REQUIRED')
            if kind=='branch':
                model=load(rec['model']);require(model['snapshot']==rl.snapshot(model) and model['snapshot']==manifest['logic_snapshot']==data['logic_snapshot'],'COVERAGE_MODEL_DRIFT')
                catalog={b['id']:b for b in model['branches']};cov=data['branch_coverage'];expected=cov['expected_branch_ids'];shown=cov['displayed_branch_ids'];omitted=cov['omitted_branches']
                sources={bid:{s for n in model['nodes'] if n['id'] in b['nodes'] for s in n['source_ids']} for bid,b in catalog.items()}
                require(all(sources[k] and sources[k]<=set(model['sources']) for k in catalog),'COVERAGE_SOURCE_IDENTITY_INVALID')
                require(artifact is not None and rl.file_sha(artifact)==data['docx_sha256'],'COVERAGE_RECEIPT_ARTIFACT_DRIFT')
                from docx import Document
                captions=[p.text for p in Document(artifact).paragraphs if p.style.name=='Caption']
                actual={k for k in catalog if any(p.startswith('同一模型图 '+k+'   ') for p in captions)}
                require(actual==set(shown),'COVERAGE_BRANCH_OBJECT_MISMATCH')
                require(set(shown)=={g['view'] for g in data['graphs'] if g['view'] in catalog},'COVERAGE_BRANCH_RECEIPT_MISMATCH')
                snapshot=model['network_snapshot']
            elif kind=='summary':
                net=load(rec['network']);require(net['snapshot']==rl.fingerprint({k:v for k,v in net.items() if k!='snapshot'})==data['network_snapshot'],'COVERAGE_NETWORK_DRIFT')
                from project_evidence_products import digest
                require(data['projection_hash']==digest(data['products']),'COVERAGE_PLAN_DRIFT')
                catalog={n['id']:n for n in net['nodes'] if n['kind']=='claim'};docs={d['id']:d for d in net['paper']['documents']}
                sources={k:{rl.fingerprint(s) for s in n['source_refs']} for k,n in catalog.items()}
                require(all(sources[k] and all(s['document_id'] in docs and 1<=s['locator']['physical_page']<=docs[s['document_id']]['physical_page_count'] for s in n['source_refs']) for k,n in catalog.items()),'COVERAGE_SOURCE_IDENTITY_INVALID')
                mains=[p for p in data['products'] if p['kind']=='main'];require(len(mains)==1,'COVERAGE_MAIN_PRODUCT_REQUIRED')
                cov=mains[0]['summary_coverage'];expected=cov['expected_claim_ids'];shown=cov['displayed_claim_ids'];omitted=cov['omitted_claims']
                scenes=[s for s in mains[0]['slides'] if s['id'].startswith('REPORT_summary')]
                require(set(shown)=={n for s in scenes for n in s['source_node_ids']},'COVERAGE_SUMMARY_PLAN_MISMATCH')
                if artifact:
                    from pptx import Presentation
                    objects={s.name:s.text for sl in Presentation(artifact).slides for s in sl.shapes if s.has_text_frame}
                    compact=lambda t:re.sub(r'\s+','',t)
                    expected_objects=set()
                    for scene in scenes:
                        for e in scene['elements']:
                            if e.get('source_node_ids'):
                                name='RC_'+scene['id']+'_'+e['id']
                                expected_objects.add(name)
                                require(name in objects and compact(objects[name])==compact(e['text']),'COVERAGE_SUMMARY_OBJECT_MISMATCH')
                                require(all(n in catalog and compact(e['text'])==compact(catalog[n]['label']) for n in e['source_node_ids']),'COVERAGE_SUMMARY_SOURCE_TEXT_MISMATCH')
                    require(expected_objects=={n for n in objects if n.startswith('RC_REPORT_summary') and '_REPORT_conclusion_' in n},'COVERAGE_SUMMARY_OBJECT_SET_MISMATCH')
                snapshot=net['snapshot']
            else:raise ValueError('COVERAGE_KIND_INVALID')
            require(set(expected)==set(catalog) and len(expected)==len(set(expected)) and len(shown)==len(set(shown)) and set(shown)<=set(expected),'COVERAGE_REGISTERED_ID_DRIFT')
            require(set(omitted)==set(expected)-set(shown) and all(isinstance(v,str) and v.strip() for v in omitted.values()),'COVERAGE_OMISSION_REASON_REQUIRED')
            decisions={};review_status='NOT_ASSESSED';allowed={}
            if review:
                require(review['network_snapshot']==snapshot,'CONTRIBUTION_REVIEW_SNAPSHOT_DRIFT')
                for item in review.get('items',[]):
                    if item['kind']!=kind:continue
                    key=item['id'];require(key in catalog and key not in decisions,'CONTRIBUTION_REVIEW_UNKNOWN_OR_DUPLICATE_ID')
                    require(item.get('importance') in ['core','support','background'] and bool(item.get('importance_reason')) and bool(item.get('support_explanation')),'CONTRIBUTION_REVIEW_JUDGMENT_REQUIRED')
                    bound=set(item.get('source_ids',[])) if kind=='branch' else {rl.fingerprint(s) for s in item.get('source_refs',[])}
                    require(bool(bound) and bound<=sources[key],'CONTRIBUTION_REVIEW_SOURCE_MISMATCH');decisions[key]=item
                review_status='SOURCE_REFERENCED_REVIEW_RECORDED' if set(decisions)==set(expected) and review['status']=='SOURCE_REFERENCED_REVIEW_RECORDED' else 'PARTIAL'
                approval=review.get('approved_scope',{});allowed=approval.get('excluded_ids',{}).get(kind,{})
                require(isinstance(allowed,dict) and set(allowed)<=set(omitted) and all(isinstance(v,str) and v.strip() for v in allowed.values()),'CONTRIBUTION_SCOPE_ID_MISMATCH')
            missing_core=[k for k in omitted if decisions.get(k,{}).get('importance')=='core' and k not in allowed]
            unapproved=set(omitted)-set(allowed)
            scoped=review_status=='SOURCE_REFERENCED_REVIEW_RECORDED' and not unapproved and artifact is not None
            content='PASS_REVIEWED_REQUESTED_SCOPE' if scoped else 'PARTIAL' if omitted or review else 'NOT_ASSESSED'
            row=dict(kind=kind,artifact=rec.get('artifact'),registered_projection=('COMPLETE' if not omitted else 'PARTIAL') if artifact else ('PLANNED_COMPLETE' if not omitted else 'PLANNED_PARTIAL'),core_review=review_status,content_status=content,scope='approved_limited' if allowed else 'registered_product',omitted=omitted,approved_omissions=allowed,known_core_omissions=missing_core,can_claim_complete_reviewed_scope=scoped)
            rows.append(row)
    except (OSError,KeyError,TypeError,ValueError) as ex:errors.append(str(ex))
    products={f.get('product') for f in manifest.get('files',[])}
    required=set(manifest.get('requested_coverage',[]))|({'summary'} if 'main' in products else set())|({'branch'} if 'Workbook' in products else set())
    present={r['kind'] for r in rows}
    for kind in sorted(required-present):
        warnings.append('CONTENT_COVERAGE_NOT_ASSESSED:'+kind)
        rows.append(dict(kind=kind,registered_projection='NOT_ASSESSED',core_review='NOT_ASSESSED',content_status='NOT_ASSESSED',scope='legacy_or_missing_record',omitted={},approved_omissions={},known_core_omissions=[],can_claim_complete_reviewed_scope=False))
    if not rows:warnings.append('CONTENT_COVERAGE_NOT_ASSESSED_LEGACY_OR_MISSING_RECORDS')
    known=[r['kind']+':'+i for r in rows for i in r['known_core_omissions']]
    policy=['CORE_CONTRIBUTION_OMITTED:'+k for k in known] if profile=='full' else []
    if known and profile!='full':warnings.append('KNOWN_CORE_OMISSION_REQUIRES_REVIEW; FULL_WOULD_FAIL')
    status='FAIL' if errors or policy else 'PASS_REVIEWED_REQUESTED_SCOPE' if rows and all(r['can_claim_complete_reviewed_scope'] for r in rows) else 'PARTIAL' if any(r['content_status']=='PARTIAL' for r in rows) else 'NOT_ASSESSED'
    return dict(valid=not errors and not policy,status=status,integrity_errors=errors,policy_errors=policy,warnings=warnings,products=rows,profile=profile,known_core_omissions=known,paper_all_core_contributions_discovered='NOT_DETERMINABLE_FROM_PROJECTION',scientific_review='PARTIAL',formal_ready=False)

def check_package(root,profile='balanced'):
    root=Path(root).resolve();manifest=json.loads((root/'Manifest.json').read_text('utf-8-sig'));errors=[];links=[]
    for row in manifest['files']:
        p=(root/row['path']).resolve()
        if root not in p.parents or not p.is_file():errors.append('MISSING_OR_EXTERNAL_FILE:'+row['path']);continue
        if hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:errors.append('FILE_HASH_DRIFT:'+row['path'])
        if row.get('logic_snapshot')!=manifest['logic_snapshot']:errors.append('PRODUCT_MODEL_DRIFT:'+row['path'])
        if p.suffix.lower()=='.docx':
            q=relative_dependencies(root,p);links.append(q)
            if not q['valid']:errors.append('BROKEN_RELATIVE_LINK:'+row['path'])
    graph_check=check_registered_graphs(root,manifest,required=profile=='full' and {'main','B'}<={x['product'] for x in manifest['files']})
    errors+=graph_check.get('errors',[])
    coverage=assess_contribution_coverage(root,manifest,profile)
    return dict(valid=not errors and coverage['valid'],structure_valid=not errors,structure_errors=errors,errors=errors+coverage['integrity_errors']+coverage['policy_errors'],relative_links=links,logic_graph_contract=graph_check,requested_complete=not manifest.get('not_delivered') and not manifest.get('issues'),contribution_coverage=coverage,scientific_review=manifest['scientific_review'])

def check_registered_graphs(root,manifest,required=False):
    """Consume a hash-bound graph audit in the actual delivery, not success flags."""
    import copy
    rec=manifest.get('logic_graph_contract')
    if not rec:return dict(valid=not required,errors=['LOGIC_GRAPH_CONTRACT_REQUIRED'] if required else [],status='NOT_ASSESSED')
    try:
        root=Path(root).resolve();data=json.loads(coverage_file(root,rec).read_text('utf-8-sig'))
        model=json.loads(coverage_file(root,rec['model']).read_text('utf-8-sig'))
        import research_logic as rl
        if not rl.validate_model(model)['valid']:raise ValueError('GRAPH_SOURCE_MODEL_INVALID')
        if data['logic_snapshot']!=manifest['logic_snapshot'] or model['snapshot']!=manifest['logic_snapshot']:raise ValueError('GRAPH_MODEL_DRIFT')
        products=copy.deepcopy(data['graphs']+data.get('main_graphs',[]))
        for p in products:
            for ext in ['pptx','png']:
                if p.get(ext):p[ext]=str(coverage_file(root,dict(path=p[ext],sha256=p[ext+'_sha256'])))
        # Bind the audit's main and B to the actual named delivered products.
        for kind,scope in [('B','complete'),('main','overview_navigation')]:
            actual=[f for f in manifest['files'] if f['product']==kind and f['path'].endswith('.pptx')]
            registered=[p for p in products if p.get('scope')==scope]
            if kind=='main' and not registered:registered=[p for p in products if p.get('placement')=='main']
            if not actual or not registered or not all(any((root/f['path']).resolve()==Path(p['pptx']).resolve() and f['sha256']==p['pptx_sha256'] for f in actual) for p in registered):raise ValueError('GRAPH_DELIVERY_FILE_BINDING')
        return validate_delivery(model,products,True,True)
    except (OSError,ValueError,KeyError) as e:return dict(valid=False,errors=['GRAPH_AUDIT_INVALID:'+str(e)])
def rendered_topology(pptx,view,slide_number=None):
    from pptx import Presentation
    prefix='RC_LOGIC_'+view+'_LOGIC_'+view+'_'
    edge_prefix='RC_EDGE_LOGIC_'+view+'_LOGIC_'+view+'_'
    nodes=set();edges=set()
    prs=Presentation(pptx)
    slides=[prs.slides[int(slide_number)-1]] if slide_number else prs.slides
    for slide in slides:
        for s in slide.shapes:
            if s.name.startswith(prefix) and s.has_text_frame and s.text.strip():
                for suffix in ('_body','_shared'):
                    if s.name.endswith(suffix):nodes.add(s.name[len(prefix):-len(suffix)])
            if s.name.startswith(edge_prefix) and (s._element.tag.endswith('cxnSp') or s._element.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}custGeom') is not None):edges.add(re.sub(r'_\d+$','',s.name[len(edge_prefix):]))
    return nodes,edges
def validate_delivery(model,products,requested_B=False,verify_files=True,main_pptx=None,main_views=None):
    errors=[];nm={n['id']:n for n in model['nodes']};em={e['id']:e for e in model['edges']};full=[p for p in products if p.get('view')=='B' and p.get('scope')=='complete']
    if main_pptx and verify_files:errors+=main_model_audit(main_pptx,model)['errors']
    if requested_B and not full:errors.append('COMPLETE_B_REQUIRED')
    overviews=[p for p in products if p.get('scope') in ['overview','overview_navigation'] and any(q.get('id')==p.get('parent_canvas') for q in full)]
    if requested_B and not overviews:errors.append('MAIN_B_OVERVIEW_REQUIRED')
    if requested_B and not any(p.get('scope')=='overview_navigation' for p in overviews):errors.append('MAIN_B_NAVIGATION_REQUIRED')
    if requested_B and verify_files:
        actual_views={p.get('source_view',p.get('view')) for p in products if p.get('placement')=='main' or p.get('scope')=='overview'}
        expected=set(main_views) if main_views is not None else {'A'}|({'B'} if not any(p.get('scope')=='overview_navigation' for p in overviews) else set())
        if not expected<=actual_views:errors.append('PLANNED_MAIN_NATIVE_VIEWS_MISSING')
    for p in products:
        if p.get('logic_snapshot')!=model['snapshot']:errors.append('DELIVERY_MODEL_DRIFT')
        if any(len(p.get(k,[]))!=len(set(p.get(k,[]))) for k in ['node_ids','edge_ids']):errors.append('DUPLICATE_GRAPH_IDENTITY')
        if p.get('scope')=='overview_navigation':
            errors+=validate_navigation(model,p,products,verify_files)['errors'];continue
        if p.get('scope')=='overview' and (p.get('view')!='B' or p.get('placement')!='main'):errors.append('FALSE_B_OVERVIEW')
        if p.get('placement')=='main':
            view=p.get('source_view',p.get('view'))
            ref=next((q for q in products if q.get('view')==view and q.get('placement')!='main'),None)
            if ref is None or any(set(p.get(k,[]))!=set(ref.get(k,[])) for k in ['node_ids','edge_ids']):errors.append('MAIN_VIEW_TOPOLOGY_DRIFT')
        if p.get('view')=='B':
            if set(p.get('node_ids',[]))!=set(nm) or set(p.get('edge_ids',[]))!=set(em):errors.append('B_TOPOLOGY_LOSS')
        if p.get('scope')=='zoom':
            if not any(q.get('id')==p.get('parent_canvas') for q in full):errors.append('ZOOM_PARENT_MISSING')
            if not set(p.get('node_ids',[]))<=set(nm) or not set(p.get('edge_ids',[]))<=set(em):errors.append('ZOOM_INVENTED_ID')
        for eid in p.get('edge_ids',[]):
            if eid in em and not {em[eid]['from'],em[eid]['to']}<=set(p.get('node_ids',[])):errors.append('DELIVERY_DANGLING_EDGE')
        if verify_files:
            for ext in ['pptx','png']:
                if ext=='png' and p.get('placement')=='main' and p.get('preview_status')=='NOT_EXPORTED' and not p.get('png'):continue
                try:
                    if hashlib.sha256(Path(p[ext]).read_bytes()).hexdigest()!=p[ext+'_sha256']:errors.append('DELIVERY_FILE_DRIFT')
                except (OSError,KeyError):errors.append('DELIVERY_FILE_MISSING')
            if p.get('scope') in ['complete','zoom','overview_A','overview'] and p.get('pptx'):
                try:
                    actual=main_pptx if main_pptx and p.get('placement')=='main' else p['pptx']
                    if main_pptx and p.get('placement')=='main' and hashlib.sha256(Path(main_pptx).read_bytes()).hexdigest()!=p.get('pptx_sha256'):errors.append('MAIN_PPTX_IDENTITY_MISMATCH')
                    ns,es=rendered_topology(actual,p.get('source_view',p['view']),p.get('main_slide'))
                    if ns!=set(p.get('node_ids',[])) or es!=set(p.get('edge_ids',[])):errors.append('RENDERED_TOPOLOGY_LOSS')
                    errors+=native_semantics(actual,p.get('source_view',p['view']),model,p.get('main_slide'),complete=p.get('scope')=='complete',capacity=p.get('placement')=='main')
                except (OSError,ValueError,KeyError):errors.append('RENDERED_TOPOLOGY_UNREADABLE')
            if p.get('scope')=='overview' and not p.get('main_slide'):
                errors.append('MAIN_B_NATIVE_SLIDE_REQUIRED')
            if p.get('placement')=='main' and not p.get('main_slide'):
                errors.append('MAIN_NATIVE_SLIDE_REQUIRED')
    return dict(valid=not errors,errors=errors,requested_B=requested_B,model_nodes=len(nm),model_edges=len(em),scientific_review='PARTIAL',formal_ready=False)

def edge_geometry(shape):
    """Read an open, editable orthogonal edge; never infer from its bounding box."""
    import math
    from pptx.oxml.ns import qn
    from pptx.util import Pt
    q=shape._element
    if q.tag==qn('p:cxnSp'):
        return [(shape.begin_x,shape.begin_y),(shape.end_x,shape.end_y)]
    def fail():raise ValueError('NATIVE_EDGE_GEOMETRY_UNVERIFIABLE:'+shape.name)
    if q.tag!=qn('p:sp') or not shape.name.startswith('RC_EDGE_LOGIC_') or q.getparent().tag==qn('p:grpSp'):fail()
    if any(t.text and t.text.strip() for t in q.findall('.//'+qn('a:t'))):fail()
    sp=q.find(qn('p:spPr'));x=sp.find(qn('a:xfrm')) if sp is not None else None
    paths=sp.findall('a:custGeom/a:pathLst/a:path',{'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}) if sp is not None else []
    if x is None or len(paths)!=1 or any(sp.find(qn('a:'+kind)) is not None for kind in ['solidFill','blipFill','gradFill','pattFill','prstGeom']):fail()
    if any(x.get(k,'0') not in ['0','1','false','true'] for k in ['flipH','flipV']):fail()
    path=paths[0]
    if path.get('fill')!='none' or path.get('stroke','1')!='1':fail()
    try:
        off=x.find(qn('a:off'));ext=x.find(qn('a:ext'))
        ox,oy=float(off.get('x')),float(off.get('y'));cx,cy=float(ext.get('cx')),float(ext.get('cy'))
        w,h=float(path.get('w')),float(path.get('h'));rot=float(x.get('rot','0'))/60000
        if min(cx,cy,w,h)<=0 or not all(math.isfinite(z) for z in [ox,oy,cx,cy,w,h,rot]) or rot%90:fail()
        points=[]
        for i,cmd in enumerate(path):
            if cmd.tag!=qn('a:moveTo' if i==0 else 'a:lnTo') or len(cmd)!=1 or cmd[0].tag!=qn('a:pt'):fail()
            px,py=float(cmd[0].get('x')),float(cmd[0].get('y'))
            if not (0<=px<=w and 0<=py<=h):fail()
            a,b=px/w*cx,py/h*cy
            if x.get('flipH') in ['1','true']:a=cx-a
            if x.get('flipV') in ['1','true']:b=cy-b
            a-=cx/2;b-=cy/2;t=math.radians(rot)
            point=(ox+cx/2+a*math.cos(t)-b*math.sin(t),oy+cy/2+a*math.sin(t)+b*math.cos(t))
            if not points or math.dist(points[-1],point)>=1:points.append(point)
        if len(points)<2:fail()
        for a,b in zip(points,points[1:]):
            if math.dist(a,b)<1 or min(abs(a[0]-b[0]),abs(a[1]-b[1]))>Pt(.02):fail()
        return points
    except (TypeError,AttributeError,ValueError,OverflowError):fail()

def native_semantics(path,view,model,slide_number=None,complete=False,capacity=False):
    """Consume serialized objects: sources, text, direction, ports and obstacles."""
    from render_logic import validate_package
    from project_research_logic import directed_relation
    from pptx.util import Pt
    errors=[];prs=validate_package(path);nodes={n['id']:n for n in model['nodes']};em={e['id']:e for e in model['edges']}
    slides=[prs.slides[int(slide_number)-1]] if slide_number else prs.slides
    for sl in slides:
        frames={};bodies={};edges={}
        for s in sl.shapes:
            if s.shape_type==13:errors.append('RASTER_LOGIC_REPLACEMENT')
            prefix='RC_LOGIC_'+view+'_LOGIC_'+view+'_'
            if s.name.startswith(prefix) and s.name.endswith('_frame'):
                frames[s.name[len(prefix):-6]]=(s.left,s.top,s.width,s.height)
            cn=s._element.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr')
            try:d=json.loads(cn.get('descr','{}')) if cn is not None else {}
            except ValueError:errors.append('NATIVE_METADATA_INVALID');continue
            if not isinstance(d,dict):errors.append('NATIVE_METADATA_INVALID');continue
            nid=d.get('logic_node_id')
            if capacity and nid and s.has_text_frame and any(r.font.size is None or r.font.size<Pt(10)-1 for p in s.text_frame.paragraphs for r in p.runs):errors.append('MAIN_VISUAL_CAPACITY_LIMIT:'+str(slide_number))
            # Complete B is read at its independent physical canvas size. This
            # absolute point-size floor does not normalize it into a 16:9 slide,
            # replace visual review, or relax the main-deck capacity contract.
            if complete and s.has_text_frame and s.text.strip() and any(r.font.size is None or r.font.size<Pt(10)-1 for p in s.text_frame.paragraphs for r in p.runs if r.text.strip()):errors.append('COMPLETE_B_READABILITY_LIMIT:'+s.name)
            if nid and s.name.endswith(('_body','_shared')):
                n=nodes.get(nid,{})
                if d.get('source_node_ids',[])!=n.get('source_entity_ids',[]) or d.get('statement_ids',[])!=n.get('statement_ids',[]):errors.append('NATIVE_SOURCE_DRIFT:'+nid)
                if complete:
                    expected=n.get('short_text','') if n.get('kind')=='question' else n.get('detail_text',n.get('short_text',''))
                    if re.sub(r'\s+','',s.text)!=re.sub(r'\s+','',expected):errors.append('B_DETAIL_TEXT_LOSS:'+nid)
                bodies[nid]=s;frames.setdefault(nid,(s.left,s.top,s.width,s.height))
            eid=d.get('logic_edge')
            if s.name.startswith('RC_EDGE_LOGIC_') and not eid:errors.append('NATIVE_EDGE_IDENTITY_MISSING:'+s.name)
            if eid:
                e=em.get(eid,{})
                if any(d.get(k)!=e.get(v) for k,v in [('from_node','from'),('to_node','to'),('identity','identity'),('relation_type','type')]):errors.append('NATIVE_EDGE_SEMANTICS_DRIFT:'+eid)
                edges.setdefault(eid,[]).append(s)
        def port(point,b,tol=Pt(20)):
            x,y,w,h=b;a,c=point
            return x-tol<=a<=x+w+tol and y-tol<=c<=y+h+tol and min(abs(a-x),abs(a-x-w),abs(c-y),abs(c-y-h))<=tol
        for eid,segments in edges.items():
            e=em.get(eid)
            if not e:errors.append('NATIVE_UNKNOWN_EDGE');continue
            if any(not re.fullmatch(r'RC_EDGE_LOGIC_.+_[0-9]+',s.name) for s in segments):
                errors.append('NATIVE_EDGE_GEOMETRY_UNVERIFIABLE:'+eid);continue
            try:
                segments.sort(key=lambda s:int(s.name.rsplit('_',1)[1]))
                paths=[edge_geometry(s) for s in segments]
            except ValueError as exc:
                errors.append('NATIVE_EDGE_GEOMETRY_UNVERIFIABLE:'+eid+':'+str(exc));continue
            directed=directed_relation(e)
            for i,s in enumerate(segments):
                tail=s._element.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}tailEnd');head=s._element.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}headEnd')
                if bool(tail is not None and tail.get('type','none')!='none')!=bool(directed and i==len(segments)-1) or (head is not None and head.get('type','none')!='none'):errors.append('NATIVE_DIRECTION_DRIFT:'+eid)
                if i and any(abs(a-b)>(Pt(.02) if segments[i]._element.tag.endswith('}sp') or segments[i-1]._element.tag.endswith('}sp') else 0) for a,b in zip(paths[i][0],paths[i-1][-1])):errors.append('NATIVE_PATH_DISCONNECTED:'+eid)
                for start,end in zip(paths[i],paths[i][1:]):
                    for nid,(x,y,w,h) in frames.items():
                        if nid in [e['from'],e['to']]:continue
                        if abs(start[0]-end[0])<Pt(.02) and x<start[0]<x+w and max(min(start[1],end[1]),y)<min(max(start[1],end[1]),y+h):errors.append('NATIVE_PATH_NODE_COLLISION:'+eid)
                        if abs(start[1]-end[1])<Pt(.02) and y<start[1]<y+h and max(min(start[0],end[0]),x)<min(max(start[0],end[0]),x+w):errors.append('NATIVE_PATH_NODE_COLLISION:'+eid)
            if e['from'] not in frames or e['to'] not in frames or not port(paths[0][0],frames.get(e['from'],(0,0,0,0))) or not port(paths[-1][-1],frames.get(e['to'],(0,0,0,0))):errors.append('NATIVE_ENDPOINT_DRIFT:'+eid)
    return sorted(set(errors))

def validate_navigation(model,nav,products,verify_files=True):
    """A same-model main-deck navigation is not a relabeled A or raster B."""
    errors=[];em={e['id']:e for e in model['edges']};nm={n['id'] for n in model['nodes']}
    full=next((p for p in products if p.get('id')==nav.get('parent_canvas') and p.get('view')=='B' and p.get('scope')=='complete'),None)
    main=[p for p in products if p.get('placement')=='main' and p.get('scope')!='overview_navigation']
    visible=set().union(*(set(p.get('edge_ids',[])) for p in main)) if main else set()
    nodes=set().union(*(set(p.get('node_ids',[])) for p in main)) if main else set()
    omitted=set(em)-visible
    if full is None:errors.append('COMPLETE_B_REQUIRED')
    if not main or nav.get('view')!='navigation' or nav.get('logic_snapshot')!=model['snapshot']:errors.append('NAVIGATION_IDENTITY_INVALID')
    if set(nav.get('node_ids',[]))!=nodes or not nodes<=nm or set(nav.get('edge_ids',[]))!=visible or not visible<=set(em):errors.append('NAVIGATION_VISIBLE_SET_DRIFT')
    if set(nav.get('omitted_edge_ids',[]))!=omitted or set(nav.get('omitted_edges',{}))!=omitted or any(not isinstance(v,str) or not v.strip() for v in nav.get('omitted_edges',{}).values()):errors.append('NAVIGATION_OMISSION_DRIFT')
    if not set(model.get('core',{}).get('edges',[]))<=visible:errors.append('CORE_MAIN_RELATION_OMITTED')
    if sorted(nav.get('main_slides',[]))!=sorted(p.get('main_slide') for p in main):errors.append('NAVIGATION_PAGE_DRIFT')
    if any(p.get('pptx')!=nav.get('pptx') or p.get('pptx_sha256')!=nav.get('pptx_sha256') for p in main):errors.append('NAVIGATION_MAIN_IDENTITY_DRIFT')
    ref=nav.get('full_b_reference',{})
    if not ref.get('path') or Path(ref['path']).is_absolute() or (full and ref.get('sha256')!=full.get('pptx_sha256')):errors.append('FULL_B_REFERENCE_INVALID')
    if verify_files:
        try:
            from pptx import Presentation
            from urllib.parse import unquote
            path=Path(nav['pptx']).resolve();target=(path.parent/ref['path']).resolve()
            if path.parent not in target.parents or hashlib.sha256(path.read_bytes()).hexdigest()!=nav['pptx_sha256'] or hashlib.sha256(target.read_bytes()).hexdigest()!=ref['sha256']:errors.append('FULL_B_REFERENCE_DRIFT')
            prs=Presentation(path);actual=[];linked=False
            for i,sl in enumerate(prs.slides,1):
                if any(s.name.startswith(('RC_LOGIC_','RC_EDGE_LOGIC_')) for s in sl.shapes):actual.append(i)
                for s in sl.shapes:
                    if not s.has_text_frame:continue
                    for p in s.text_frame.paragraphs:
                        for r in p.runs:
                            if ref['path'] in s.text and r.hyperlink.address and (path.parent/unquote(r.hyperlink.address)).resolve()==target:linked=True
            if sorted(actual)!=sorted(nav.get('main_slides',[])):errors.append('NAVIGATION_ACTUAL_PAGE_DRIFT')
            if not linked:errors.append('FULL_B_REFERENCE_NOT_VISIBLE_OR_LINKED')
        except (OSError,KeyError,ValueError):errors.append('NAVIGATION_FILE_UNREADABLE')
    return dict(valid=not errors,errors=errors,visible_edge_ids=sorted(visible),omitted_edge_ids=sorted(omitted),scientific_review='PARTIAL')

def validate_main_views(model,pptx,records,plan):
    errors=[];scenes={s['coverage']['view']:s for p in plan['products'] for s in p['slides']};allnodes={n['id'] for n in model['nodes']};em={e['id']:e for e in model['edges']}
    errors+=main_model_audit(pptx,model)['errors']
    for row in records:
        if row['view'] not in scenes:errors.append('UNREGISTERED_MAIN_VIEW');continue
        scene=scenes[row['view']];ids=set(scene['source_logic_node_ids']);eids=set(scene['source_logic_relation_ids']);cov=scene['coverage']
        if scene['logic_snapshot']!=model['snapshot']:errors.append('MAIN_VIEW_MODEL_DRIFT')
        if not ids<=allnodes or not eids<=set(em):errors.append('MAIN_VIEW_UNKNOWN_ID');continue
        if row['view']=='B' and (ids!=allnodes or eids!=set(em)):errors.append('B_TOPOLOGY_LOSS')
        if cov.get('scope')=='local':
            if row['view']=='B' or cov.get('parent_view')!='B' or not ids<=allnodes or not eids<=set(em):errors.append('INVALID_LOCAL_PROJECTION')
            if set(cov.get('omitted_edge_ids',[]))!=set(em)-eids:errors.append('LOCAL_OMISSION_DRIFT')
        if any(not {em[e]['from'],em[e]['to']}<=ids for e in eids):errors.append('LOCAL_DANGLING_EDGE')
        sources={s for n in model['nodes'] if n['id'] in ids for s in n['source_ids']}
        if set(scene['notes']['logic_source_ids'])!=sources:errors.append('MAIN_VIEW_SOURCE_DRIFT')
        cs={c['source_logic_relation_id']:c for c in scene['connectors']}
        if set(cs)!=eids or any(cs[e]['relation_type']!=em[e]['type'] or cs[e]['identity']!=em[e]['identity'] for e in eids if e in cs):errors.append('MAIN_VIEW_RELATION_DRIFT')
        actual=rendered_topology(pptx,row['view'],row['slide'])
        if actual!=(ids,eids):errors.append('MAIN_NATIVE_VIEW_DRIFT:'+row['view'])
    return dict(valid=not errors,errors=errors,main_views=[r['view'] for r in records],scientific_review='PARTIAL')

