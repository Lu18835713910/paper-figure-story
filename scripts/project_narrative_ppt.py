#!/usr/bin/env python3
"""Explicit m2d-preview-1 projection. Old projector/CLI/validators are untouched.
Manual display spec is an audited presentation layer, never new scientific entities.
"""
from __future__ import annotations
import argparse, copy, json, math, re
from pathlib import Path
import plan_narrative as n

VERSION = 'm2d-preview-1'
class ProjectionError(ValueError):
    def __init__(self, code, message): super().__init__(message); self.code=code

def require(condition, code, message):
    if not condition: raise ProjectionError(code,message)
def checked_file(path, sha):
    p=Path(path); require(p.is_file() and n.digest(p)==sha,'FILE_DRIFT',str(p))
def save(path, value):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f: json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')

def project(input_path, spec_path, review_path, *, development_preview=False):
    paths=n.load(input_path); spec=n.load(spec_path); review=n.load(review_path)
    required={'knowledge','assets','story','framework','mapping','reviews','narrative','view','template','panel_assets'}
    require(set(paths)==required,'INPUT_CONTRACT','Explicit input roles required')
    values={k:n.load(v) for k,v in paths.items() if k!='template'}
    m=values['knowledge'];base=values['narrative'];view=values['view']
    valid=n.validate_narrative_plan(m,values['story'],values['framework'],values['mapping'],values['reviews'],base,values['assets'],base_dir=Path(paths['mapping']).parent)
    require(valid['valid'],'NARRATIVE_PLAN_DRIFT',str(valid.get('diagnostics')))
    assembler=n.NarrativeAssembler(m,values['story'],values['framework'],values['mapping'],values['reviews'],values['assets'],base_dir=Path(paths['mapping']).parent)
    require(assembler.view(view['profile'])==view,'VIEW_DRIFT','View must match validated M2-C base')
    require(spec['version']==VERSION and spec['profile']==view['profile'],'SPEC_VERSION','Version/profile mismatch')
    require(review['spec_snapshot']==n.fingerprint(spec),'TEXT_REVIEW_DRIFT','Display spec changed after scoped review')
    require(review['panel_assets_snapshot']==n.fingerprint(values['panel_assets']),'ASSET_REVIEW_DRIFT','Panel audit is stale')
    require(review['status'] in ('PASS','PARTIAL') and review['source_status'] in ('PASS','PARTIAL'),'REVIEW_FAILED','Rejected/unknown source review')
    formal=bool(base['validation']['formal_ready'] and review['status']=='PASS' and review['source_status']=='PASS')
    require(formal or development_preview,'NOT_FORMAL_READY','Requires explicit --development-preview; original formal_ready is not upgraded')
    stmts={s['id']:s for s in base['statements']};units={u['id']:u for u in base['reasoning_units']}
    figures={f['id']:f for f in m['figures']};docs={d['id']:d for d in m['document_registry']}
    assets={a['id']:a for a in values['panel_assets']['assets']}
    require(len(assets)==len(values['panel_assets']['assets']),'ASSET_ID','Duplicate asset ids')
    checked_pdfs=set()
    for a in assets.values():
        require(a['figure_id'] in figures,'FIGURE_REF','Unknown Figure')
        doc=docs[a['source_document_id']]
        require(figures[a['figure_id']]['document_id']==doc['id'] and a['source_sha256']==doc['sha256'],'ASSET_SOURCE','Figure/document/hash mismatch')
        figure_pages={r['locator']['physical_page'] for r in figures[a['figure_id']]['source_refs']}
        require(a['physical_page'] in figure_pages and a['panels'] and 'all' not in a['panels'],'PANEL_REF','Explicit panel/page scope required')
        require(a['panel_review_status']=='PASS_SCOPED','PANEL_REVIEW','Image/panel must have a scoped inspection record')
        checked_file(a['path'],a['sha256']);checked_file(a['source_page_image'],a['source_page_sha256'])
        if doc['id'] not in checked_pdfs: checked_file(doc['path'],doc['sha256']);checked_pdfs.add(doc['id'])
    slides=[];segments=[];bindings=[];all_units=set();all_figs=set();ids=set()
    def unique_id(i):
        require(isinstance(i,str) and i and i not in ids,'DUPLICATE_ID',str(i));ids.add(i)
    require(set(spec)=={'version','profile','style','slides'},'SPEC_CONTRACT','Unexpected top-level spec fields')
    style=spec['style']; require(style['accent']=='#174994','STYLE','Expected academic blue')
    require(set(style)<={'accent','font_family','template_content_frames'},'STYLE','Unknown style decision')
    require('template_content_frames' not in style or type(style['template_content_frames']) is bool,'STYLE','Frame choice must be explicit boolean')
    for i,s in enumerate(spec['slides']):
        require(set(s)=={'id','kind','template_reference_slide','source_unit_ids','elements','connectors','notes'},'SLIDE_CONTRACT','Unexpected slide fields')
        unique_id(s['id']);wanted=set(s['source_unit_ids']);require(wanted and wanted<=units.keys(),'RSU_REF','Unknown narrative unit')
        all_units.update(wanted)
        rsus=sorted({r for uid in wanted for r in units[uid]['source_rsu_ids']})
        figs=sorted({f for uid in wanted for f in units[uid]['figure_ids']});all_figs.update(figs)
        segment_id='PS_'+s['id'];segments.append({'id':segment_id,'source_narrative_unit_ids':s['source_unit_ids'],'source_rsu_ids':rsus,'figure_ids':figs,'statement_ids':[]})
        elements=[]
        for e in s['elements']:
            require(set(e)<={'id','kind','role','text','position','font_size_px','bold','color','fill','alignment','statement_ids','source_pointers','asset_id','stroke','stroke_width_px'},'ELEMENT_CONTRACT','Unexpected element fields')
            unique_id(e['id']); pos=e['position']
            require(set(pos)=={'left','top','width','height'} and all(type(v) in (int,float) and math.isfinite(v) for v in pos.values()),'GEOMETRY','Finite rectangle required')
            require(pos['left']>=0 and pos['top']>=0 and pos['width']>0 and pos['height']>0 and pos['left']+pos['width']<=1280 and pos['top']+pos['height']<=720,'GEOMETRY','Element outside slide')
            require(e['kind'] in ('text','rect','image'),'ELEMENT_KIND','Unsupported native element')
            if 'stroke' in e or 'stroke_width_px' in e:
                require(e['kind']=='rect' and isinstance(e.get('stroke'),str) and bool(re.fullmatch(r'#[0-9A-Fa-f]{6}',e['stroke'])),'HIGHLIGHT_STYLE','Highlight must be an explicit native rectangle stroke')
                require(type(e.get('stroke_width_px')) in (int,float) and math.isfinite(e['stroke_width_px']) and 0<e['stroke_width_px']<=4,'HIGHLIGHT_STYLE','Bounded stroke required')
            refs=e.get('statement_ids',[]);require(set(refs)<=stmts.keys(),'STATEMENT_REF','Unknown exact statement id')
            allowed={sid for uid in wanted for sid in n.statement_ids(units[uid])}
            if e.get('role')=='title': allowed.add(base['central_focus']['statement_id'])
            require(set(refs)<=allowed,'STATEMENT_SCOPE','Statement outside source unit scope: '+e['id'])
            if e['kind']=='text':
                require(e['role'] in ('title','body','annotation','source','presentation_label'),'TEXT_ROLE','Explicit text role required')
                require(bool(e.get('text')) and isinstance(e['text'],str),'TEXT_CONTRACT','Text required')
                require(e['role'] not in ('title','body') or bool(refs),'UNBOUND_TEXT','Scientific title/body requires source statements')
                require(12<=e.get('font_size_px',0)<=52,'TEXT_SIZE','Explicit readable native font required')
            resolved=[]
            for pointer in e.get('source_pointers',[]):resolved.append({'pointer':pointer,'value':n.pointer(m,pointer)})
            if e['kind']=='image':
                require(e.get('asset_id') in assets,'ASSET_REF','Missing asset')
                require(assets[e['asset_id']]['figure_id'] in figs,'ASSET_SCOPE','Image outside segment Figure scope')
            segments[-1]['statement_ids']+=refs
            bindings.append({'slide_id':s['id'],'element_id':e['id'],'role':e.get('role'), 'statement_ids':refs,'source_binding_ids':sorted({b for sid in refs for b in stmts[sid]['source_binding_ids']}),'resolved_m1_supplemental_refs':resolved,'asset_id':e.get('asset_id')})
            elements.append(copy.deepcopy(e))
        connectors=[]
        for c in s['connectors']:
            require(set(c)=={'id','scope','relation_kind','from_element','to_element','start','end','arrow'},'CONNECTOR_CONTRACT','Unexpected connector fields')
            unique_id(c['id']);require(c['scope']=='presentation' and c['relation_kind'] in ('parallel','synthesis','narrative_sequence','panel_pointer'),'PRESENTATION_RELATION','Cannot manufacture scientific relation')
            require(c['from_element'] in {e['id'] for e in elements} and c['to_element'] in {e['id'] for e in elements},'CONNECTOR_REF','Unknown visual endpoint')
            require(type(c['arrow']) is bool,'CONNECTOR_STYLE','Explicit arrow type required')
            for xy in ('start','end'):require(len(c[xy])==2 and all(type(v) in (int,float) and math.isfinite(v) for v in c[xy]) and 0<=c[xy][0]<=1280 and 0<=c[xy][1]<=720,'GEOMETRY','Bad connector endpoint')
            require(c['start'][0]==c['end'][0] or c['start'][1]==c['end'][1],'ROUTING','Only supplied straight orthogonal segments; no router')
            connectors.append(copy.deepcopy(c))
        segments[-1]['statement_ids']=sorted(set(segments[-1]['statement_ids']))
        slides.append({**copy.deepcopy(s),'elements':elements,'connectors':connectors,'segment_ids':[segment_id]})
    require(all_units==set(units),'COVERAGE','This overview preview must retain all narrative units')
    require(all_figs==set(base['coverage']['figure_ids']),'COVERAGE','Figure references lost')
    plan={'narrative_ppt_version':VERSION,'profile':view['profile'],'render_mode':'development_preview' if development_preview else 'formal','formal_ready':formal,
        'warnings':copy.deepcopy(base['validation']['diagnostics'])+ [{'code':'SCIENTIFIC_REVIEW_PARTIAL','message':'R&D preview only; original M2-C and scoped science audit are not independent formal acceptance'}],
        'inputs':{k:{'path':str(Path(v).resolve()),'sha256':n.digest(v)} for k,v in paths.items()},
        'input_manifest':{'path':str(Path(input_path).resolve()),'sha256':n.digest(input_path)},
        'display_spec':{'path':str(Path(spec_path).resolve()),'sha256':n.digest(spec_path)},'display_review':{'path':str(Path(review_path).resolve()),'sha256':n.digest(review_path)},
        'source_narrative':copy.deepcopy(base),'source_view':copy.deepcopy(view),'coverage':copy.deepcopy(base['coverage']),
        'source_scientific_relations':copy.deepcopy(base['source_scientific_relations']),'segments':segments,'slides':slides,'source_map':bindings,
        'panel_assets':copy.deepcopy(values['panel_assets']),'style':copy.deepcopy(style),'scientific_entity_creation':False,
        'limitations_policy':'All original limits/critical statements in source_narrative and notes; visible text is a reviewed summary, not exhaustive panel coverage.'}
    plan['projection_snapshot']=n.fingerprint(plan);return plan

def validate(plan, *, development_preview=False):
    try:
        for info in [plan['input_manifest'],plan['display_spec'],plan['display_review'],*plan['inputs'].values()]:checked_file(info['path'],info['sha256'])
        rebuilt=project(plan['input_manifest']['path'],plan['display_spec']['path'],plan['display_review']['path'],development_preview=development_preview)
        require(rebuilt==plan,'NARRATIVE_PPT_PLAN_DRIFT','Exact rebuilt projection differs')
        return {'valid':True,'formal_ready':plan['formal_ready'],'projection_snapshot':plan['projection_snapshot']}
    except (ValueError,KeyError,OSError) as exc:return {'valid':False,'code':getattr(exc,'code','INPUT_ERROR'),'message':str(exc)}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs');p.add_argument('--spec');p.add_argument('--reviews');p.add_argument('--output');p.add_argument('--validate-existing');p.add_argument('--development-preview',action='store_true');a=p.parse_args(argv)
    if a.validate_existing:
        result=validate(n.load(a.validate_existing),development_preview=a.development_preview);print(json.dumps(result,ensure_ascii=False));return 0 if result['valid'] else 1
    require(all((a.inputs,a.spec,a.reviews,a.output)),'CLI_INPUT','Explicit --inputs --spec --reviews --output required')
    plan=project(a.inputs,a.spec,a.reviews,development_preview=a.development_preview);save(a.output,plan);print(json.dumps({'valid':True,'slides':len(plan['slides']),'formal_ready':plan['formal_ready'],'render_mode':plan['render_mode']},ensure_ascii=False));return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:print(json.dumps({'valid':False,'code':getattr(exc,'code','INPUT_ERROR'),'message':str(exc)},ensure_ascii=False));raise SystemExit(1)

