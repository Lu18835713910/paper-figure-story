#!/usr/bin/env python3
"""M2-B1: source-bound RSU -> presentation segment -> slide planning.
No scientific extraction or PPT authoring occurs here. Legacy interfaces unchanged.
"""
from __future__ import annotations
import argparse,copy,hashlib,json
from pathlib import Path
import plan_research as planning

VERSION='m2b-1'
def semantic_plan_hash(plan):
    value=copy.deepcopy(plan)
    value['diagnostics']=[d for d in value.get('diagnostics',[]) if d.get('code')!='SOURCE_FILES_NOT_CHECKED']
    return planning.fingerprint(value)
class ProjectionError(ValueError):
    def __init__(self,code,message):super().__init__(message);self.code=code

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def pointer_value(model,pointer):return planning.resolve_pointer(model,pointer)
def source_union(items):return planning.source_union(items)
def _params(model,eid):
    idx=next(i for i,n in enumerate(model['entities']) if n['id']==eid)
    node=model['entities'][idx]
    return {p['key']:(p,f'/entities/{idx}/parameters/{j}/value') for j,p in enumerate(node['parameters'])}

def validate_assets(model,assets,verify_files=True):
    errors=[];known_fig={f['id']:f for f in model['figures']};nodes={n['id']:n for n in model['entities']};docs={d['id']:d for d in model['document_registry']};seen=set()
    if not isinstance(assets,dict) or assets.get('asset_version')!=VERSION or not isinstance(assets.get('assets'),list):
        return {'valid':False,'errors':[{'code':'ASSET_FORMAT','message':'asset_version=m2b-1 and assets list required'}]}
    for a in assets['assets']:
        try:
            if a['id'] in seen:raise ProjectionError('ASSET_ID','duplicate asset ID')
            seen.add(a['id'])
            if a['figure_id'] not in known_fig:raise ProjectionError('ASSET_FIGURE','unregistered Figure ID')
            if not a.get('evidence_ids') or any(e not in nodes or nodes[e]['kind']!='evidence' for e in a['evidence_ids']):raise ProjectionError('ASSET_EVIDENCE','explicit existing evidence mapping required')
            for eid in a['evidence_ids']:
                if not any(a['figure_id'] in st['figure_refs'] and eid in st['evidence_ids'] for st in model['stories']):raise ProjectionError('ASSET_EVIDENCE_LINK','Figure and evidence lack a shared source RSU')
                if a.get('physical_page') not in {ref['locator'].get('physical_page') for ref in nodes[eid]['source_refs']}:raise ProjectionError('ASSET_EVIDENCE_PAGE','Figure page absent from evidence support locators')
            if not isinstance(a.get('panels'),list) or not a['panels']:raise ProjectionError('ASSET_PANELS','panel coverage required')
            if a['source_document_id']!=known_fig[a['figure_id']]['document_id']:raise ProjectionError('ASSET_SOURCE','image document and Figure document differ')
            if a['source_document_id'] not in docs:raise ProjectionError('ASSET_SOURCE','unknown image source')
            if type(a['physical_page']) is not int or not 1<=a['physical_page']<=docs[a['source_document_id']].get('physical_page_count',10**6):raise ProjectionError('ASSET_PAGE','invalid physical PDF page')
            if a['physical_page'] not in {s['locator'].get('physical_page') for s in known_fig[a['figure_id']]['source_refs']}:raise ProjectionError('ASSET_PAGE','asset page does not match registered Figure locator')
            b=a.get('crop')
            if not isinstance(b,list) or len(b)!=4 or any(type(x) not in (int,float) for x in b) or not 0<=b[0]<b[2]<=1 or not 0<=b[1]<b[3]<=1:raise ProjectionError('ASSET_CROP','invalid normalized crop')
            if a.get('source_sha256') and a['source_sha256']!=docs[a['source_document_id']]['sha256']:raise ProjectionError('ASSET_SOURCE_HASH','asset PDF snapshot mismatch')
            if verify_files:
                if not Path(a['path']).is_file() or digest(a['path'])!=a['sha256']:raise ProjectionError('ASSET_BYTES','missing image or SHA256 mismatch')
                try:
                    from PIL import Image
                    with Image.open(a['path']) as im:im.verify()
                except Exception as exc:raise ProjectionError('ASSET_IMAGE','asset is not a decodable image') from exc
        except (KeyError,TypeError,ValueError) as exc:
            errors.append({'code':getattr(exc,'code','ASSET_FORMAT'),'message':str(exc),'asset_id':a.get('id') if isinstance(a,dict) else None})
    return {'valid':not errors,'errors':errors}

def asset_review_complete(asset):
    review=asset.get('visual_review',{})
    if not isinstance(review,dict):return False
    checks=review.get('checks',{})
    if not isinstance(checks,dict):return False
    binding=all(review.get(k)==asset.get(k) for k in ('sha256','source_sha256','physical_page','crop','evidence_ids','figure_id','source_document_id','panels'))
    return binding and bool(asset.get('source_sha256')) and asset.get('verified') is True and review.get('status')=='pass' and isinstance(review.get('reviewer'),str) and bool(review['reviewer'].strip()) and all(checks.get(k) is True for k in ('figure_identity','crop_complete','axes_legends_scalebars','significance_marks','readability'))

class PresentationProjector:
    def __init__(self,model,assets,*,verify_files=True,base_dir=None):
        self.model=copy.deepcopy(model);self.assets=copy.deepcopy(assets)
        self.planner=planning.ResearchPlanner(model,verify_files=verify_files,base_dir=base_dir)
        checks=validate_assets(model,assets,verify_files=verify_files)
        if not checks['valid']:raise ProjectionError('INVALID_ASSETS',json.dumps(checks['errors'],ensure_ascii=False))
        self.nodes={n['id']:n for n in model['entities']};self.figures={f['id']:f for f in model['figures']}
        self.asset_index={a['id']:a for a in assets['assets']}
        self.stats={'asset_verification_passes':1,'pdf_scientific_parse_calls':0,'projections':0}

    def project(self,profile='balanced',request=None):
        bundle=self.planner.plan(profile,request=request);splan=bundle['story_plan'];fplan=bundle['framework_plan']
        units=splan['units'];segments=[];slides=[];nonexp=splan['planning_kind'] in ('knowledge_topics','unclassified','correction_only')
        def block(role,text,pointer=None):return {'role':role,'text':str(text),'knowledge_pointer':pointer}
        def src_for(eids):return source_union([self.nodes[e]['source_refs'] for e in eids])
        def segment(unit,role,eids,figs):
            sid=f'SEG{len(segments)+1:03d}'
            value={'id':sid,'source_unit_id':unit['id'],'source_rsu_ids':list(unit['source_story_ids']),'role':role,'evidence_ids':list(eids),'figure_ids':list(figs),'method_ids':list(unit['method_ids']),
                   'question_refs':list(unit['question_refs']),'finding_refs':list(unit['finding_refs']),'source_refs':source_union([unit['source_refs'],src_for(eids)]),'limits_refs':list(unit['limit_refs'])}
            segments.append(value);return value
        def page(kind,title,seg=None,blocks=None,asset_ids=None,node_ids=None,edge_ids=None,layout=None):
            p={'id':f'SL{len(slides)+1:03d}','kind':kind,'title':title,'segment_ids':[seg['id']] if seg else [],'source_rsu_ids':list(seg['source_rsu_ids']) if seg else [],
               'scientific_question_refs':list(seg['question_refs']) if seg else [],'figure_ids':list(seg['figure_ids']) if seg else [],'evidence_ids':list(seg['evidence_ids']) if seg else [],
               'method_ids':list(seg['method_ids']) if seg else [],'blocks':blocks or [],'asset_ids':asset_ids or [],'node_ids':node_ids or [],'relation_ids':edge_ids or [],
               'recommended_layout':layout or ('figure_story' if kind=='figure' else kind),'source_refs':copy.deepcopy(seg['source_refs']) if seg else [],'profile':profile,'formal_ready':True,'blockers':[]}
            slides.append(p);return p
        title=self.model['document_registry'][0]['title']
        page('cover',title,blocks=[block('article_type',self.model['paper_type']['label'],'/paper_type/label')],layout='academic_cover')
        qs=[]
        for u in units:
            for ref in u['question_refs']:
                if ref not in [b['knowledge_pointer'] for b in qs]:qs.append(block('question',pointer_value(self.model,ref),ref))
        page('questions','核心科学问题' if not nonexp else '核心论点与讨论范围',blocks=qs[:7],layout='questions')
        # The overview is an induced view, never a transitive shortcut or a fixed four-column study map.
        priority={'sample_or_subject':7,'assay':6,'model':6,'evaluation':6,'claim':6,'processing':4,'dataset':3,'intervention':7,'evidence':2,'method':5}
        degree={n:0 for n in self.nodes}
        for r in self.model['relations']:degree[r['from']]+=1;degree[r['to']]+=1
        critical=set()
        for r in self.model['relations']:
            if r['type'] in ('optional_path','parallel_branch','independent_validation','compares','experimental_precedes'):critical.update((r['from'],r['to']))
        cap={'quick':8,'balanced':10,'full':12}[profile]
        ordered=sorted(self.nodes,key=lambda n:(-(30*(n in critical)+priority[self.nodes[n]['kind']]+min(degree[n],4)),list(self.nodes).index(n)))
        anchors=[n for n in self.nodes if self.nodes[n]['kind']=='sample_or_subject']
        anchors+=planning.unique(r['to'] for r in self.model['relations'] if r['type']=='data_depends_on' and r['from'] in anchors and self.nodes[r['to']]['kind']=='dataset')
        # Clinical/material anchors and their direct resource pools must remain visible.
        route_core=planning.unique(x for r in self.model['relations'] if r['type']=='optional_path' for x in (r['from'],r['to']))
        model_routes=bool(route_core) and any(self.nodes[n]['kind']=='model' for n in route_core)
        if model_routes:
            core=planning.unique(anchors+route_core)
            changed=True
            while changed:
                old=len(core)
                for r in self.model['relations']:
                    if r['type']=='data_depends_on' and r['to'] in core:core=planning.unique(core+[r['from']])
                changed=len(core)!=old
            if len(core)>12:raise ProjectionError('FRAMEWORK_NEEDS_SEGMENTATION','Optional-route input closure exceeds readable overview capacity; partition source tasks explicitly')
            selected=core[:cap]
        else:selected=planning.unique(anchors+[n for n in ordered if degree[n]>0])[:cap] or ordered[:cap]
        rels=[r['id'] for r in self.model['relations'] if r['from'] in selected and r['to'] in selected]
        connected={x for r in self.model['relations'] if r['id'] in rels for x in (r['from'],r['to'])}
        if rels:selected=[n for n in selected if n in connected or degree[n]==0]
        page('framework',('核心构建路径与可选分支' if model_routes else '全文科研问题与证据框架') if not nonexp else '可靠性风险、应对与评价框架',node_ids=selected,edge_ids=rels,layout='relation_driven_composite')
        # Add local relationship views only where semantic edges would be invisible.
        missing=[r for r in self.model['relations'] if r['id'] not in rels and (profile=='full' or nonexp or (model_routes and r['type']=='data_depends_on') or r['type'] in ('parallel_branch','independent_validation','optional_path','compares','experimental_precedes'))]
        if missing and (profile!='quick' or (model_routes and len(core)>cap)):
            batches=[];ids=[]
            for rel in missing:
                pair=[rel['from'],rel['to']]
                if len(planning.unique(ids+pair))>8:batches.append(ids);ids=[]
                ids=planning.unique(ids+pair)
            if ids:batches.append(ids)
            for ids in batches:
                es=[r['id'] for r in self.model['relations'] if r['from'] in ids and r['to'] in ids]
                page('framework','关键分支与证据关系',node_ids=ids,edge_ids=es,layout='relation_driven_local')
        for unit in units:
            if profile!='quick' and (len(unit['method_ids'])>=3 or len(unit['figure_ids'])>1):
                seg=segment(unit,'evidence_design',unit['evidence_ids'],unit['figure_ids'])
                bs=[block('question',pointer_value(self.model,p),p) for p in unit['question_refs']]
                for eid in unit['evidence_ids']:
                    params=_params(self.model,eid)
                    if 'design' in params:bs.append(block('context' if nonexp else 'design',*reversed((params['design'][1],params['design'][0]['value']))))
                page('context','论证依据与主题关系' if nonexp else '研究问题与证据设计',seg,bs,layout='evidence_context')
            chunks=[unit['evidence_ids']] if profile=='quick' else [[e] for e in unit['evidence_ids']]
            if not chunks:chunks=[[]]
            for eids in chunks:
                figs=planning.unique(a['figure_id'] for a in self.assets['assets'] if set(a['evidence_ids']).intersection(eids) and a['figure_id'] in unit['figure_ids'])
                seg=segment(unit,'argument' if nonexp else 'evidence',eids,figs)
                candidates=[a for a in self.assets['assets'] if a['figure_id'] in figs and set(a['evidence_ids']).intersection(eids)]
                byfig={}
                for a in candidates:byfig.setdefault(a['figure_id'],[]).append(a)
                chosen=[next((a for a in values if 'all' in a['panels']),values[0]) for values in byfig.values()] if profile=='quick' else [a for values in byfig.values() for a in values]
                targets=chosen if chosen else [None]
                for a in targets:
                    focused=[e for e in eids if not a or e in a['evidence_ids']]
                    bs=[]
                    if profile!='quick':
                        bs+=[block('question',pointer_value(self.model,p),p) for p in unit['question_refs'][:1]]
                    for eid in focused:
                        params=_params(self.model,eid)
                        for key,role in [('design','context' if nonexp else 'design'),('result','argument' if nonexp else 'finding'),('interpretation','inference')]:
                            if key in params:
                                item,pointer=params[key]
                                if item['status']=='reported' and item['value'] is not None:bs.append(block(role,item['value'],pointer))
                        if not params:
                            idx=next(i for i,n in enumerate(self.model['entities']) if n['id']==eid)
                            bs.append(block('argument' if nonexp else 'finding',self.nodes[eid]['name'],f'/entities/{idx}/name'))
                    # Each slide carries evidence-specific limitations, even in quick mode.
                    limits=planning.unique(x for eid in focused for x in self.nodes[eid]['limits'])
                    for limit in limits[:2]:
                        pointer=next(f'/entities/{i}/limits/{j}' for i,n in enumerate(self.model['entities']) if n['id'] in focused for j,value in enumerate(n['limits']) if value==limit)
                        bs.append(block('limit',limit,pointer))
                    caption=self.nodes[focused[0]]['name'] if focused else '主要论点与科学边界'
                    p=page('figure' if a else 'topic',caption,seg,bs,[a['id']] if a else [],layout='figure_story' if a else 'argument_text')
                    if a:p['figure_ids']=[a['figure_id']];p['panels']=list(a['panels']);p['evidence_ids']=focused
                    elif figs or unit['figure_ids'] and not nonexp:
                        p['formal_ready']=False;p['blockers'].append('MISSING_FIGURE_IMAGE')
            if profile=='full':
                seg=segment(unit,'limits_and_methods' if not nonexp else 'scope_and_limits',unit['evidence_ids'],unit['figure_ids'])
                bs=[]
                for ref in unit['finding_refs']:bs.append(block('argument' if nonexp else 'finding',pointer_value(self.model,ref),ref))
                for ref in unit['limit_refs']:
                    for j,limit in enumerate(pointer_value(self.model,ref)):bs.append(block('limit',limit,ref+'/'+str(j)))
                for mid in unit['method_ids']:
                    idx=next(i for i,n in enumerate(self.model['entities']) if n['id']==mid)
                    bs.append(block('discussed_method' if nonexp else 'method',self.nodes[mid]['name'],f'/entities/{idx}/name'))
                    if self.nodes[mid].get('details'):bs.append(block('method_scope' if nonexp else 'method_explanation',self.nodes[mid]['details'],f'/entities/{idx}/details'))
                for start in range(0,len(bs),4):page('method' if not nonexp else 'topic','方法、证据强度与适用边界' if not nonexp else '论点依据与适用边界',seg,bs[start:start+4],layout='method_explanation' if not nonexp else 'argument_text')
        if profile!='quick':
            bs=[]
            for unit in units:
                for ref in unit['limit_refs']:
                    for j,text in enumerate(pointer_value(self.model,ref)):
                        if text not in [x['text'] for x in bs]:bs.append(block('limit',text,ref+'/'+str(j)))
            for start in range(0,min(len(bs),10),5):page('limitations','研究限制与结论强度' if not nonexp else '实践建议的前提与局限',blocks=bs[start:start+5],layout='limitations')
        page('conclusion','研究主要发现' if not nonexp else '核心论点与实践启示',blocks=[block('finding' if not nonexp else 'argument',pointer_value(self.model,u['finding_refs'][0]),u['finding_refs'][0]) for u in units],layout='conclusion')
        # Formal readiness is source/asset completeness, independent of the scientific review verdict.
        for p in slides:
            if not p['source_refs']:
                refs=[]
                for nid in p['node_ids']:refs.extend(self.nodes[nid]['source_refs'])
                for rid in p['relation_ids']:refs.extend(next(r for r in self.model['relations'] if r['id']==rid)['source_refs'])
                for b in p['blocks']:
                    ptr=b.get('knowledge_pointer') or ''
                    parts=ptr.strip('/').split('/')
                    if len(parts)>1 and parts[0] in ('entities','stories'):refs.extend(self.model[parts[0]][int(parts[1])]['source_refs'])
                p['source_refs']=source_union([refs or self.model['paper_type']['basis']])
            used_refs=p['source_refs']
            if any(s['verification']!='direct_checked' for s in used_refs):p['formal_ready']=False;p['blockers'].append('SOURCE_NOT_DIRECT_CHECKED')
            for aid in p['asset_ids']:
                if not asset_review_complete(self.asset_index[aid]):p['formal_ready']=False;p['blockers'].append('ASSET_REVIEW_PENDING')
        shown={f for p in slides if p['kind']=='figure' for f in p['figure_ids']}
        required={f['id'] for f in self.model['figures'] if f['kind'] in ('main','conceptual') and any(f['id'] in u['figure_ids'] for u in units)}
        missing_main=sorted(required-shown)
        if missing_main:
            for p in slides:
                if p['kind'] in ('cover','conclusion'):p['formal_ready']=False;p['blockers'].append('MAIN_FIGURE_COVERAGE_INCOMPLETE')
        self.stats['projections']+=1
        return {'page_plan_version':VERSION,'knowledge_sha256':planning.fingerprint(self.model),'assets_sha256':planning.fingerprint(self.assets),'profile':profile,
                'planning_request':copy.deepcopy(splan['planning_request']),'story_plan_sha256':semantic_plan_hash(splan),'framework_plan_sha256':semantic_plan_hash(fplan),
                'source_status':copy.deepcopy(splan['source_status']),'framework_family':fplan['structure']['family'],
                'source_rsu_ids':list(self.planner.stories),'segments':segments,'slides':slides,'formal_ready':all(p['formal_ready'] for p in slides),
                'coverage':{'required_figure_ids':sorted(required),'shown_figure_ids':sorted(shown),'missing_figure_ids':missing_main,'all_original_relations_available_in_framework_plan':True},
                'statistics':{'rsus':len(self.planner.stories),'segments':len(segments),'slides':len(slides),'method_pages':sum(p['kind']=='method' for p in slides),'figure_pages':sum(p['kind']=='figure' for p in slides),'fulltext_parse_calls':0}}
    def project_all(self,request=None):return {profile:self.project(profile,request=request) for profile in planning.PROFILES}

def validate_page_plan(model,assets,plan,verify_files=True):
    errors=[]
    def fail(code,message):errors.append({'code':code,'message':message})
    try:
        if plan.get('knowledge_sha256')!=planning.fingerprint(model):fail('KNOWLEDGE_BINDING','knowledge snapshot changed')
        if plan.get('assets_sha256')!=planning.fingerprint(assets):fail('ASSET_BINDING','asset snapshot changed')
        ac=validate_assets(model,assets,verify_files)
        errors.extend(ac['errors'])
        rsus={s['id'] for s in model['stories']};nodes={n['id']:n for n in model['entities']};relations={r['id']:r for r in model['relations']};aids={a['id'] for a in assets['assets']}
        if set(plan['source_rsu_ids'])!=rsus:fail('RSU_DRIFT','Presentation fragments must not change the underlying RSU set')
        segments={s['id']:s for s in plan['segments']}
        if len(segments)!=len(plan['segments']):fail('SEGMENT_ID','duplicate segment ID')
        if len({s['id'] for s in plan['slides']})!=len(plan['slides']):fail('SLIDE_ID','duplicate slide ID')
        covered=set()
        for seg in plan['segments']:
            if not set(seg['source_rsu_ids']).issubset(rsus):fail('SEGMENT_RSU','segment invented an RSU')
            covered.update(seg['source_rsu_ids'])
        if covered!=rsus:fail('RSU_COVERAGE','missing original RSU')
        for p in plan['slides']:
            if not set(p['segment_ids']).issubset(segments):fail('SLIDE_SEGMENT','unknown segment reference')
            if not set(p['asset_ids']).issubset(aids):fail('SLIDE_ASSET','unknown image reference')
            for bid in p['evidence_ids']+p['method_ids']+p['node_ids']:
                if bid not in nodes:fail('SLIDE_ENTITY','unknown entity reference')
            for rid in p['relation_ids']:
                if rid not in relations:fail('SLIDE_RELATION','invented scientific relation')
                elif not {relations[rid]['from'],relations[rid]['to']}.issubset(p['node_ids']):fail('SLIDE_RELATION','displayed relation endpoint missing')
            for b in p['blocks']:
                if b.get('knowledge_pointer') and str(pointer_value(model,b['knowledge_pointer']))!=b['text']:fail('TEXT_DRIFT','text differs from its authoritative knowledge pointer')
            if p['kind']=='figure' and not p['asset_ids'] and p['formal_ready']:fail('FORMAL_IMAGE','image-less Figure cannot be formally ready')
        expected=PresentationProjector(model,assets,verify_files=False).project(plan['profile'],request=plan.get('planning_request'))
        if plan!=expected:fail('PAGE_PLAN_DRIFT','source-bound projection changed; validate regenerated plan instead of editing output facts')
    except (KeyError,TypeError,ValueError) as exc:fail(getattr(exc,'code','PLAN_FORMAT'),str(exc))
    return {'valid':not errors,'errors':errors,'formal_ready':bool(plan.get('formal_ready',False)),'scientific_original_review':'separate_required_gate','visual_review':'not_performed_at_planning_stage'}

def legacy_manifest(model,assets,plan):
    """A temporary scaffold for the unchanged v1.0 builder, not the final authority."""
    amap={a['id']:a for a in assets['assets']};slides=[]
    for p in plan['slides']:
        rec={'kind':'cover' if p['kind']=='cover' else 'figure' if p['kind']=='figure' else 'text','title':p['title'],'section':'科研问题与证据','citation':format_source(p['source_refs']), 'subtitle':'', 'bullets':[], 'points':[]}
        if p['kind']=='cover':rec['subtitle']='中文科研汇报｜'+('综述与知识框架' if model['paper_type']['label'] in planning.NONEXPERIMENTAL else '研究问题、方法与证据')
        elif p['kind']=='figure':
            rec['figure_ref']='、'.join(next(f['label'] for f in model['figures'] if f['id']==fid) for fid in p['figure_ids'])
            if p.get('panels') and p['panels']!=['all']:rec['figure_ref']+=' · panel '+','.join(p['panels'])+'（局部放大，结合全图）'
            rec['images']=[amap[aid]['path'] for aid in p['asset_ids']]
            roles={'question':'question','context':'context','design':'design','finding':'finding','argument':'finding','inference':'inference','limit':'transition'}
            bs=[b for b in p['blocks'] if b['role']!='limit']
            # Split long blocks at punctuation only. Never truncate scientific text.
            steps=[]
            for b in bs:
                if len(b['text'])>100:raise ProjectionError('TEXT_NEEDS_SEGMENTATION','A Figure story block exceeds legacy 100-character safety limit')
                role=roles.get(b['role'],'context')
                # The legacy schema requires a transition field. 'parallel' is a neutral
                # presentation separator, never a scientific edge. No role -> relation inference.
                step={'role':role,'text':b['text'],'relation_from_previous':'parallel'}
                if role in ('finding','validation'):step['panel_ref']=rec['figure_ref']
                steps.append(step)
            if len(steps)<2:steps.append({'role':'transition','text':'证据边界见下方限制。','relation_from_previous':'parallel'})
            if len(steps)>7:raise ProjectionError('TEXT_NEEDS_SEGMENTATION','More than seven story steps require another Slide, not another RSU')
            rec['story_steps']=steps
            rec['presentation_transition_semantics']='narrative_order_only; authoritative scientific edges remain in knowledge.relations'
            rec['limitation']='；'.join(b['text'] for b in p['blocks'] if b['role']=='limit')
        elif p['kind']!='framework':
            rec['bullets']=[b['text'] for b in p['blocks']]
            rec['points']=list(rec['bullets'])
        slides.append(rec)
    return {'meta':{'short_citation':'来源：原论文PDF；详细页码与证据见逐页备注'},'slides':slides}

def format_source(refs):
    pages=planning.unique(s['locator'].get('physical_page') for s in refs if s['locator'].get('physical_page'))
    return '来源：原文PDF p.'+','.join(map(str,pages)) if pages else '来源：原文PDF'

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('knowledge',type=Path);p.add_argument('--assets',type=Path,required=True);p.add_argument('--outdir',type=Path,required=True);p.add_argument('--profile',choices=[*planning.PROFILES,'all'],default='balanced');p.add_argument('--verify-files',action='store_true')
    a=p.parse_args(argv)
    try:
        model=planning.knowledge.load_json(a.knowledge);assets=planning.knowledge.load_json(a.assets)
        projector=PresentationProjector(model,assets,verify_files=a.verify_files,base_dir=a.knowledge.parent)
        plans=projector.project_all() if a.profile=='all' else {a.profile:projector.project(a.profile)}
        validations={profile:validate_page_plan(model,assets,plan,a.verify_files) for profile,plan in plans.items()}
        if any(not r['valid'] for r in validations.values()):raise ProjectionError('PLAN_VALIDATION',json.dumps(validations,ensure_ascii=False))
        a.outdir.mkdir(parents=True,exist_ok=True)
        for profile,plan in plans.items():
            (a.outdir/f'pages.{profile}.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            (a.outdir/f'pages.{profile}.validation.json').write_text(json.dumps(validations[profile],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'valid':True,'profiles':list(plans),'formal_ready':{k:v['formal_ready'] for k,v in plans.items()},'stats':projector.stats,'planning_stats':projector.planner.stats},ensure_ascii=False));return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:print(json.dumps({'valid':False,'code':getattr(exc,'code','INPUT_ERROR'),'message':str(exc)},ensure_ascii=False));return 1
if __name__=='__main__':raise SystemExit(main())
