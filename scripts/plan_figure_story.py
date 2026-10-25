"""Explicit m2e1-1 reference-only Figure/Panel Story Planner. Legacy paths untouched."""
from pathlib import Path
import argparse,copy,hashlib,json,math
import plan_narrative as n
VERSION='m2e1-1'
ROLES={'purpose','design','analysis','readout','result','interpretation','limit'}
STATUSES={'PASS_SCOPED','PARTIAL','NOT_TESTED','FAIL'}
class StoryError(ValueError):
    def __init__(self,code,message):super().__init__(message);self.code=code
def need(ok,code,message):
    if not ok:raise StoryError(code,message)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def textsha(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def save(p,x):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf-8')
def explicit(panels):return bool(panels) and len(panels)==len(set(panels)) and all(isinstance(x,str) and len(x)==1 and x.isupper() for x in panels)
def source(ref):
    need(sha(ref['path'])==ref['sha256'],'SOURCE_DRIFT',ref['path'])
    text=Path(ref['path']).read_text('utf-8');s,e=ref['start'],ref['end']
    need(0<=s<e<=len(text) and text[s:e]==ref['excerpt'] and textsha(ref['excerpt'])==ref['excerpt_sha256'],'SOURCE_SPAN','Exact source span changed')
def index(rows,name):
    out={x['id']:x for x in rows};need(len(out)==len(rows),'DUPLICATE',name);return out
class FigureStoryPlanner:
    def __init__(self,input_path,package_path,review_path):
        self.paths={'inputs':str(Path(input_path).resolve()),'package':str(Path(package_path).resolve()),'reviews':str(Path(review_path).resolve())}
        self.inputs=n.load(input_path);self.data=n.load(package_path);self.review=n.load(review_path)
        self.values={k:n.load(v) for k,v in self.inputs.items() if k not in ('template',)}
        for k,h in self.data['input_hashes'].items():need(k in self.inputs and sha(self.inputs[k])==h,'UPSTREAM_DRIFT',k)
        need(self.data['version']==VERSION and self.review['version']==VERSION,'VERSION','Explicit E1 contract required')
        need(self.review['content_snapshot']==n.fingerprint(self.data),'CONTENT_DRIFT','Review is for another package')
        v=self.values
        checked=n.validate_narrative_plan(v['knowledge'],v['story'],v['framework'],v['mapping'],v['reviews'],v['narrative'],v['assets'])
        need(checked['valid'],'NARRATIVE_PLAN_DRIFT',str(checked.get('diagnostics')))
        self.model=v['knowledge'];self.base=v['narrative'];self.figures=index(self.data['figures'],'figures');self.cards=index(self.data['cards'],'cards');self.assets=index(self.data['assets'],'assets');self.regions=index(self.data['regions'],'regions');self.segments=index(self.data['segments'],'segments')
        self._check()
    def _check(self):
        d=self.data;r=self.review;m=self.model
        mfig={f['id']:f for f in m['figures']};rsus={s['id'] for s in m['stories']};stmts={s['id'] for s in self.base['statements']}
        need(not d.get('created_scientific_entities'),'NEW_SCIENTIFIC_ENTITY','Presentation may not create M1 entities')
        need(all(not x.get('auto_corrected',False) for x in d['conflicts']),'CONFLICT_CORRECTION','Original labels cannot be silently corrected')
        for f in d['figures']:
            need(f['id'] in mfig and explicit(f['expected_panels']),'PANEL_ALL','Expected panels must be explicit')
            need(f['expected_panels']==r['panel_inventory'][f['id']],'INVENTORY_DRIFT',f['id'])
            need(set(f['source_rsu_ids'])<=rsus and f['source_rsu_ids'],'RSU_REF',f['id'])
            for p in f['expected_panels']:
                pr=f['panel_reviews'][p]
                for status in ['source_status','panel_mapping_status','visual_status','semantic_review_status']:need(pr[status] in STATUSES,'STATUS',status)
                for ref in pr['source_refs']:source(ref)
                need(pr['source_refs'],'UNSUPPORTED_PANEL',p)
        for c in d['cards']:
            need(c['figure_id'] in self.figures and explicit(c['panels']) and set(c['panels'])<=set(self.figures[c['figure_id']]['expected_panels']),'PANEL_ALL',c['id'])
            need(c['role'] in ROLES and c['source_refs'],'UNSUPPORTED_STATEMENT',c['id'])
            need(set(c['narrative_statement_ids'])<=stmts,'STATEMENT_REF',c['id'])
            for pointer in c['m1_pointers']:n.pointer(m,pointer)
            need(c['m1_pointers'],'M1_REF',c['id'])
            for ref in c['source_refs']:source(ref)
            rev=r['card_reviews'].get(c['id'],{})
            need(rev.get('text_sha256')==textsha(c['text']) and rev.get('assertion_kind')==c['assertion_kind'],'TEXT_DRIFT',c['id'])
            need(rev.get('status') in ('PASS_SCOPED','PARTIAL'),'SEMANTIC_REVIEW',c['id'])
            need(rev.get('source_ids')==[x['id'] for x in c['source_refs']],'SOURCE_BINDING',c['id'])
        for a in d['assets']:
            need(explicit(a['panels']) and a['figure_id'] in self.figures,'PANEL_ALL',a['id'])
            need(not a['known_truncation'] and a['crop_review_status']=='PASS_SCOPED','CROP_TRUNCATION',a['id'])
            for key,hkey in [('path','sha256'),('source_pdf','source_pdf_sha256'),('source_page_image','source_page_sha256')]:need(sha(a[key])==a[hkey],'ASSET_DRIFT',a['id'])
            fig=mfig[a['figure_id']];need(a['physical_page'] in {s['locator']['physical_page'] for s in fig['source_refs']},'FIGURE_PAGE',a['id'])
        for reg in d['regions']:
            need(reg['asset_id'] in self.assets and reg['review_status']=='PASS_SCOPED','ROI_REVIEW',reg['id'])
            a=self.assets[reg['asset_id']];need(reg['asset_sha256']==a['sha256'] and reg['panel'] in a['panels'],'ROI_SOURCE',reg['id'])
            x,y=reg['safe_point'];l,t,rr,b=reg['bbox_pixels'];need(0<=l<=x<=rr<=a['width'] and 0<=t<=y<=b<=a['height'],'ROI_GEOMETRY',reg['id'])
            pl,pt,pr,pb=reg['protected_bbox'];need(not(pl<x<pr and pt<y<pb),'ROI_OCCLUSION','Tip inside protected original label/data')
            need(reg['basis'] in ('pdf_text_bbox','reused_visually_checked_roi'),'ROI_BASIS',reg['id'])
        scientific={r['id']:r for r in m['relations']}
        for e in d['relations']:
            need(e['identity'] in ('scientific_registered','source_data_derivation','author_argument_candidate','scientific_candidate','presentation'),'RELATION_IDENTITY',e['id'])
            need(n.fingerprint(e)==r['relation_snapshots'].get(e['id']),'RELATION_UPGRADE',e['id'])
            if e['identity']=='scientific_registered':
                old=scientific.get(e['source_relation_id']);need(old is not None and all(e[k]==old[k] for k in ['from','to','type']),'SCIENCE_EDGE',e['id'])
            else:
                need(e['from'] in self.cards and e['to'] in self.cards,'RELATION_ENDPOINT',e['id'])
                if e['identity']!='presentation':
                    need(e['source_refs'],'RELATION_SOURCE',e['id'])
                    for ref in e['source_refs']:source(ref)
            if e['identity']=='source_data_derivation':need(e['type']=='measurement_quantification','RELATION_UPGRADE','Derivation is not independent validation')
        for s in d['segments']:
            need(s['figure_id'] in self.figures and set(s['card_ids'])<=self.cards.keys(),'SEGMENT_REF',s['id'])
            need(all(self.cards[c]['figure_id']==s['figure_id'] for c in s['card_ids']),'FIGURE_CONTAINER',s['id'])
        pageids=set()
        for p in d['pages']:
            need(p['id'] not in pageids,'DUPLICATE','page');pageids.add(p['id'])
            need(p['figure_id'] in self.figures and p['segment_ids'] and set(p['segment_ids'])<=self.segments.keys(),'PAGE_SEGMENT',p['id'])
            need(all(self.segments[x]['figure_id']==p['figure_id'] for x in p['segment_ids']),'FIGURE_CONTAINER',p['id'])
            allowed={c for s in p['segment_ids'] for c in self.segments[s]['card_ids']};els=index(p['elements'],'elements')
            for e in p['elements']:
                x,y,w,h=(e['position'][k] for k in ['left','top','width','height'])
                need(all(math.isfinite(z) for z in [x,y,w,h]) and min(x,y)>=0 and min(w,h)>0 and x+w<=1280 and y+h<=720,'GEOMETRY',e['id'])
                if e['kind']=='text':need(e['card_id'] in allowed,'UNBOUND_TEXT',e['id'])
                elif e['kind']=='image':need(e['asset_id'] in self.assets and self.assets[e['asset_id']]['figure_id']==p['figure_id'],'ASSET_SCOPE',e['id'])
                else:
                    need(e['kind'] in ('label','rect'),'ELEMENT_KIND',e['id'])
                    if e['kind']=='label':need(r['label_snapshots'].get(p['id']+'/'+e['id'])==textsha(e['text']),'LABEL_REVIEW','Unreviewed caption is not an unbound scientific text channel')
            for a in p['arrows']:
                need(a['identity']=='image_pointer' and a['source_element_id'] in els and a['target_image_id'] in els,'POINTER_IDENTITY',a['id'])
                need(a['region_id'] in self.regions and self.regions[a['region_id']]['asset_id']==els[a['target_image_id']]['asset_id'],'POINTER_TARGET',a['id'])
                im=els[a['target_image_id']];reg=self.regions[a['region_id']];asset=self.assets[reg['asset_id']];pos=im['position']
                target=[pos['left']+reg['safe_point'][0]/asset['width']*pos['width'],pos['top']+reg['safe_point'][1]/asset['height']*pos['height']]
                need(len(a['path'])>=2 and all(len(xy)==2 and all(math.isfinite(v) for v in xy) and 0<=xy[0]<=1280 and 0<=xy[1]<=720 for xy in a['path']),'POINTER_GEOMETRY',a['id'])
                need(all(abs(v-w)<1e-6 for v,w in zip(a['path'][-1],target)),'POINTER_DRIFT',a['id'])
                sp=els[a['source_element_id']]['position'];x,y=a['path'][0]
                need(sp['left']-1<=x<=sp['left']+sp['width']+1 and sp['top']-1<=y<=sp['top']+sp['height']+1,'POINTER_ORIGIN',a['id'])
            for e in p['elements']:
                if e['kind']=='image':
                    for pn in self.assets[e['asset_id']]['panels']:
                        pr=self.figures[p['figure_id']]['panel_reviews'][pn]
                        need(pr['source_status'] not in ('FAIL','NOT_TESTED') and pr['panel_mapping_status']=='PASS_SCOPED','BLOCKED_PANEL',pn)
    def plan(self,profile='balanced',*,development_preview=False):
        need(profile in ('quick','balanced','full'),'PROFILE',profile)
        formal=self.base['validation']['formal_ready'] and all(x['status']=='PASS_SCOPED' for x in self.review['card_reviews'].values()) and self.review['independent_scientific_review']=='PASS'
        need(formal or development_preview,'NOT_FORMAL_READY','Explicit --development-preview required; original PARTIAL persists')
        pages=copy.deepcopy([p for p in self.data['pages'] if profile in p['profiles']]);coverage=[]
        for f in self.figures.values():
            fp=[p for p in pages if p['figure_id']==f['id']];cis={c for p in fp for sid in p['segment_ids'] for c in self.segments[sid]['card_ids']}
            visible=sorted({pn for p in fp for e in p['elements'] if e['kind']=='image' for pn in self.assets[e['asset_id']]['panels']})
            discussed=sorted({pn for c in cis if self.cards[c]['role'] in ('readout','result','analysis') for pn in self.cards[c]['panels']})
            reviewed=sorted(p for p,v in f['panel_reviews'].items() if v['source_status']=='PASS_SCOPED' and v['panel_mapping_status']=='PASS_SCOPED')
            exp=set(f['expected_panels']);roles={self.cards[c]['role'] for c in cis}
            omitted=exp-(set(visible)&set(discussed));deferred=[{'panel':p,'reason':f['deferral_reasons'][profile].get(p,'Not rendered/discussed by selected view; not complete')} for p in sorted(omitted)]
            coverage.append({'figure_id':f['id'],'expected_panels':f['expected_panels'],'reviewed_panels':reviewed,'visible_panels':visible,'discussed_panels':discussed,'deferred_panels_with_reason':deferred,'roles_present':sorted(roles),'page_ids':[p['id'] for p in fp],'source_rsu_ids':f['source_rsu_ids'],'story_complete_scoped':not omitted and ROLES<=roles and set(f['critical_card_ids'])<=cis,'formal_scientific_acceptance':False,'source_status':'PARTIAL','panel_mapping_status':'PASS_SCOPED' if exp<=set(reviewed) else 'PARTIAL','visual_status':'NOT_TESTED','semantic_review_status':'PARTIAL','independent_reader_test':'NOT_TESTED'})
        for p in pages:
            for e in p['elements']:
                if e['kind']=='text':e['text']=self.cards[e['card_id']]['text']
        plan={'version':VERSION,'profile':profile,'render_mode':'development_preview' if development_preview else 'formal','formal_ready':bool(formal),'inputs':{k:{'path':v,'sha256':sha(v)} for k,v in self.paths.items()},'template':{'path':self.inputs['template'],'sha256':sha(self.inputs['template'])},'source_narrative_snapshot':self.base['base_snapshot'],'source_scientific_relations':copy.deepcopy(self.model['relations']),'source_entity_ids':[e['id'] for e in self.model['entities']],'scientific_entities_added':0,'coverage':coverage,'cards':copy.deepcopy(self.data['cards']),'segments':copy.deepcopy(self.data['segments']),'assets':copy.deepcopy(self.data['assets']),'regions':copy.deepcopy(self.data['regions']),'relations':copy.deepcopy(self.data['relations']),'conflicts':copy.deepcopy(self.data['conflicts']),'slides':pages,'warnings':['M2-C formal_ready=false retained; scoped source and image review is not independent scientific review.','No original labels, statistical comparisons, or causal pathways are silently repaired.'],'style':{'accent':'#174994','font_family':'Microsoft YaHei','width':1280,'height':720}}
        plan['snapshot']=n.fingerprint(plan);return plan
def validate(plan,development_preview=False):
    try:
        for x in plan['inputs'].values():need(sha(x['path'])==x['sha256'],'INPUT_DRIFT',x['path'])
        q=FigureStoryPlanner(*(plan['inputs'][k]['path'] for k in ['inputs','package','reviews']))
        need(q.plan(plan['profile'],development_preview=development_preview)==plan,'PLAN_DRIFT','Exact rebuilt plan differs')
        return {'valid':True,'formal_ready':plan['formal_ready'],'snapshot':plan['snapshot']}
    except (ValueError,KeyError,OSError) as e:return {'valid':False,'code':getattr(e,'code','INPUT_ERROR'),'message':str(e)}
def main(argv=None):
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--inputs');a.add_argument('--package');a.add_argument('--reviews');a.add_argument('--profile',choices=['quick','balanced','full'],default='balanced');a.add_argument('--output');a.add_argument('--validate-existing');a.add_argument('--development-preview',action='store_true');x=a.parse_args(argv)
    if x.validate_existing:
        r=validate(n.load(x.validate_existing),x.development_preview);print(json.dumps(r,ensure_ascii=False));return 0 if r['valid'] else 1
    need(all([x.inputs,x.package,x.reviews,x.output]),'CLI_INPUT','Explicit input/package/reviews/output required')
    q=FigureStoryPlanner(x.inputs,x.package,x.reviews);p=q.plan(x.profile,development_preview=x.development_preview);save(x.output,p);print(json.dumps({'valid':True,'slides':len(p['slides']),'coverage':p['coverage'],'formal_ready':p['formal_ready']},ensure_ascii=False));return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as e:print(json.dumps({'valid':False,'code':getattr(e,'code','INPUT_ERROR'),'message':str(e)},ensure_ascii=False));raise SystemExit(1)
