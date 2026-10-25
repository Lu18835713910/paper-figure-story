#!/usr/bin/env python3
"""M2-C reference-only assembler. No PDF understanding, PPT authoring or old API changes.

CLI exit 0: structurally valid draft exported; 1: rejected/formal gate not met;
2: input error. A zero exit does not certify scientific semantics.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
import plan_research as planning
import validate_knowledge as knowledge

VERSION='m2c-1'
SCHEMA=Path(__file__).resolve().parents[1]/'schemas/narrative_v1_1.schema.json'
DEPTH={'quick':0,'balanced':1,'full':2}
NARRATIVE_KINDS={'organizes','parallel','comparison','synthesis','limits','question_progression'}
FIELDS=('main_message','purpose','approach_or_argument','intermediate_conclusion','unresolved_question')
AXES=('text_support','panel_mapping','image_visual')

class NarrativeError(ValueError):
    def __init__(self,code,message,diagnostics=None):
        super().__init__(message);self.code=code;self.diagnostics=diagnostics or []

def fingerprint(value):return planning.fingerprint(value)
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return knowledge.load_json(path)
def snapshots(model,story,framework,assets):
    return {'knowledge_snapshot':fingerprint(model),'story_plan_snapshot':fingerprint(story),
            'framework_plan_snapshot':fingerprint(framework),
            'request_profile_fingerprint':fingerprint({'profile':story['profile'],'request':story['planning_request']}),
            'assets_snapshot':fingerprint(assets)}

def pointer(model,ref):
    """Strict RFC6901 array indices; no negative or leading-zero index aliases."""
    if not isinstance(ref,str) or not ref.startswith('/'):raise NarrativeError('invalid_ref','Expected absolute JSON pointer')
    value=model
    for raw in ref[1:].split('/'):
        if re.search(r'~(?![01])',raw):raise NarrativeError('invalid_ref','Invalid pointer escape')
        token=raw.replace('~1','/').replace('~0','~')
        try:
            if isinstance(value,list):
                if not re.fullmatch(r'0|[1-9][0-9]*',token):raise ValueError('noncanonical array index')
                value=value[int(token)]
            else:value=value[token]
        except (IndexError,KeyError,TypeError,ValueError) as exc:raise NarrativeError('invalid_ref',ref) from exc
    return value

def statement_ids(unit):
    return list(dict.fromkeys([unit[f] for f in FIELDS if unit[f]]+unit['detail_statement_ids']))

class NarrativeAssembler:
    def __init__(self,model,story_plan,framework_plan,mapping,ledger,assets=None,*,base_dir=None):
        self.model,self.story,self.framework,self.mapping,self.ledger,self.assets=copy.deepcopy((model,story_plan,framework_plan,mapping,ledger,assets or {'assets':[]}))
        self.base_dir=Path(base_dir or '.').resolve()
        self.stats={'pdf_parse_calls':0,'external_model_calls':0,'image_visual_checks':0,'validation_calls':0,'base_builds':0,'view_selections':0}
        self._base=None

    def validate(self):
        self.stats['validation_calls']+=1
        diagnostics=[]
        def issue(code,path,message,severity='error',blocking=True):
            diagnostics.append({'code':code,'path':path,'message':message,'severity':severity,'blocks_formal':blocking})
        schema=load(SCHEMA);knowledge.check_schema(schema)
        for label,value,spec in [('mapping',self.mapping,schema),('ledger',self.ledger,{'$ref':'#/$defs/ledger','$defs':schema['$defs']})]:
            errors=knowledge.schema_errors(value,spec)
            for e in errors:issue('contract_format','/'+label+e['path'],e['message'])
        if diagnostics:return {'valid':False,'formal_ready':False,'diagnostics':diagnostics}
        m,s,f,a,doc=self.model,self.story,self.framework,self.assets,self.mapping
        upstream=knowledge.validate_knowledge(m,verify_files=False)
        if not upstream['valid']:issue('invalid_knowledge','/knowledge','M1 validation rejected input')
        pr=planning.validate_plans(m,s,f)
        for e in pr['errors']:issue('invalid_plan',e.get('path','/plans'),e['message'])
        if any(x['severity']=='error' for x in diagnostics):return {'valid':False,'formal_ready':False,'diagnostics':diagnostics}
        expected=snapshots(m,s,f,a)
        for key,wanted in expected.items():
            if doc['metadata'][key]!=wanted:issue('stale_snapshot','/metadata/'+key,'Bound input snapshot differs; old review cannot be reused')
        if doc['metadata']['paper_type']!=m['paper_type']['label']:issue('paper_type','/metadata/paper_type','Article type differs from M1')
        registered={}
        for c in ('entities','stories','figures','relations','document_registry'):
            registered.update({x['id']:(x,f'/{c}/{i}') for i,x in enumerate(m[c])})
        nodes={x['id']:x for x in m['entities']};rsus={x['id']:x for x in m['stories']};figs={x['id']:x for x in m['figures']}
        sci={x['id']:x for x in m['relations']};documents={x['id']:x for x in m['document_registry']}
        assets={x['id']:x for x in a['assets']}
        if len(assets)!=len(a['assets']):issue('invalid_ref','/assets','Duplicate asset id')
        provenance={}
        for i,item in enumerate(doc['metadata']['provenance']):
            path=Path(item['path']);path=(self.base_dir/path).resolve() if not path.is_absolute() else path.resolve()
            provenance[str(path)]=item
            if not path.is_file() or digest(path)!=item['sha256']:issue('stale_snapshot',f'/metadata/provenance/{i}','Provenance file absent or changed')
        def index(collection,key='id'):
            values=doc[collection];out={x[key]:x for x in values}
            if len(out)!=len(values):issue('invalid_ref','/'+collection,'Duplicate identifier')
            return out
        bindings=index('bindings');statements=index('statements');units=index('reasoning_units');relations=index('reasoning_relations')
        resolved={}
        for bid,b in bindings.items():
            try:
                if b['object_id'] not in registered:raise NarrativeError('invalid_ref','Unknown exact object id '+b['object_id'])
                original,prefix=registered[b['object_id']]
                if not b['pointer'].startswith(prefix+'/') or not b['source_ref_pointer'].startswith(prefix+'/'):
                    raise NarrativeError('invalid_ref','Pointer and source must belong to exact registered object')
                value=pointer(m,b['pointer']);source=pointer(m,b['source_ref_pointer'])
                if not isinstance(source,dict) or 'document_id' not in source or 'locator' not in source:
                    raise NarrativeError('invalid_ref','Source pointer is not a source_ref')
                document=documents[source['document_id']];page=source['locator'].get('physical_page')
                if type(page) is not int or not 1<=page<=document['physical_page_count']:
                    raise NarrativeError('invalid_ref','Physical page outside registered document')
                if b['figure_id']:
                    if b['figure_id'] not in figs or figs[b['figure_id']]['document_id']!=source['document_id']:
                        raise NarrativeError('invalid_ref','Figure does not belong to bound document')
                    if not b['panels']:raise NarrativeError('invalid_ref','Figure binding needs explicit panel scope (all allowed)')
                    related=[story for story in m['stories'] if b['object_id']==story['id'] or b['object_id'] in story['evidence_ids']+story['method_ids'] or any(r['to']==b['object_id'] and r['from'] in story['evidence_ids'] for r in m['relations'])]
                    if not any(b['figure_id'] in story['figure_refs'] for story in related):raise NarrativeError('invalid_ref','Figure and source object have no registered RSU association')
                elif b['panels'] or b['asset_ids']:raise NarrativeError('invalid_ref','Panel/assets require Figure id')
                for aid in b['asset_ids']:
                    if aid not in assets or assets[aid]['figure_id']!=b['figure_id'] or assets[aid]['source_sha256']!=document['sha256']:
                        raise NarrativeError('invalid_ref','Asset must match bound Figure and source hash')
                resolved[bid]={'object_id':b['object_id'],'pointer':b['pointer'],'value':copy.deepcopy(value),'source_reference':copy.deepcopy(source),
                    'figure_id':b['figure_id'],'figure_source_references':copy.deepcopy(figs[b['figure_id']]['source_refs']) if b['figure_id'] else [],'panels':copy.deepcopy(b['panels']),'asset_ids':copy.deepcopy(b['asset_ids']),
                    'locator_check':{'status':'PASS','meaning':'registry pointer and page range only; not sentence/panel/image verification'}}
            except (NarrativeError,KeyError,ValueError) as exc:issue('invalid_ref','/bindings/'+bid,str(exc))
        if doc['central_focus']['statement_id'] not in statements:issue('invalid_ref','/central_focus','Unknown focus statement')
        review_current=self.ledger['knowledge_snapshot']==fingerprint(m) and self.ledger['mapping_snapshot']==fingerprint(doc)
        if not review_current:issue('semantic_review_pending','/ledger','Review ledger bound to another mapping/knowledge; all semantic checks invalidated','warning')
        reviews={};effective={}
        for rec in self.ledger['records']:
            key=(rec['target_type'],rec['target_id'])
            if key in reviews:issue('invalid_ref','/ledger/records','Duplicate target review')
            reviews[key]=rec
            target=(statements if key[0]=='statement' else relations).get(key[1])
            if target is None:issue('invalid_ref','/ledger/records','Unknown review target')
            for item in rec['artifact_paths']:
                path=Path(item);path=(self.base_dir/path).resolve() if not path.is_absolute() else path.resolve()
                if str(path) not in provenance:issue('invalid_ref','/ledger/records','Review artifact not in hashed provenance')
            if rec['status']=='NA':issue('invalid_review','/ledger/records','Semantic review itself cannot be NA')
            if rec['checks']['image_visual']=='PASS' and not rec['image_visual_current']:
                issue('invalid_review','/ledger/records','Past asset hash or text review cannot certify current image visual check')
        def review(kind,key,target):
            rec=reviews.get((kind,key));valid=bool(rec and review_current and rec['target_sha256']==fingerprint(target))
            if not valid:
                issue('semantic_review_pending',f'/{kind}/{key}','No current exact-scope semantic review; wording is not auto-certified','warning')
                return {'status':'NOT_TESTED','checks':{'text_support':'NOT_TESTED','panel_mapping':'NOT_TESTED','image_visual':'NOT_TESTED'},'independent':False}
            if rec['status']=='FAIL' or rec['checks']['text_support']=='FAIL':issue('unsupported_claim',f'/{kind}/{key}','Recorded semantic/source review failed')
            if rec['status']!='PASS' or rec['method']!='independent_review':issue('semantic_review_pending',f'/{kind}/{key}','Only scoped author/prior/partial review; independent semantics not passed','warning')
            if rec['checks']['text_support']!='PASS':issue('semantic_review_pending',f'/{kind}/{key}','Text support check is not PASS','warning')
            if kind=='statement' and any(bindings.get(bid,{}).get('figure_id') for bid in target['source_binding_ids']) and rec['checks']['panel_mapping']!='PASS':issue('semantic_review_pending',f'/{kind}/{key}','Figure/panel semantic check is not PASS','warning')
            return {'status':rec['status'],'checks':copy.deepcopy(rec['checks']),'independent':rec['method']=='independent_review','record':copy.deepcopy(rec)}
        for sid,st in statements.items():
            for bid in st['source_binding_ids']:
                if bid not in bindings:issue('invalid_ref','/statements/'+sid,'Unknown binding '+bid)
            transition=st['assertion_kind']=='presentation_transition'
            if transition and (st['scope']!='presentation' or st['motivation_basis']!='presentation_organized'):
                issue('unsupported_claim','/statements/'+sid,'Pure transition must remain presentation-only')
            if not transition and not st['source_binding_ids']:issue('source_gap','/statements/'+sid,'Scientific/argument statement lacks source binding','warning')
            if st['motivation_basis']=='unknown':issue('source_gap','/statements/'+sid,'Motivation unknown; no invented author history','warning')
            if m['paper_type']['label'] in planning.NONEXPERIMENTAL and (st['scope']=='primary_study' or st['assertion_kind']=='experimental_finding'):
                issue('unsupported_claim','/statements/'+sid,'Nonexperimental article cannot become authors new experiment')
            if st['text_mode']=='literal':
                if len(st['source_binding_ids'])!=1 or st['source_binding_ids'][0] not in resolved or st['display_text']!=str(resolved[st['source_binding_ids'][0]]['value']):
                    issue('literal_drift','/statements/'+sid,'Literal text must equal its exact authoritative value')
            eff=review('statement',sid,st);effective['statement:'+sid]=eff
            rec=eff.get('record')
            if rec and st['assertion_kind'] not in rec['allowed_assertion_kinds']:
                issue('unsupported_claim','/statements/'+sid,'Claim kind exceeds the separately curated source/review scope')
        seen=set();orders=[];coverage={rid:set() for rid in rsus}
        for uid,u in units.items():
            orders.append(u['presentation_order'])
            for rid in u['source_rsu_ids']:
                if rid not in rsus:issue('invalid_ref','/reasoning_units/'+uid,'Unknown exact RSU '+rid);continue
                coverage[rid].update(set(u['figure_ids'])&set(rsus[rid]['figure_refs']))
            allowed_figs={fid for rid in u['source_rsu_ids'] if rid in rsus for fid in rsus[rid]['figure_refs']}
            if not set(u['figure_ids']).issubset(allowed_figs):issue('invalid_ref','/reasoning_units/'+uid,'Figure unrelated to referenced RSU')
            for nid in u['entity_ids']:
                if nid not in nodes:issue('invalid_ref','/reasoning_units/'+uid,'Unknown exact entity id '+nid)
            for sid in statement_ids(u):
                seen.add(sid)
                if sid not in statements:issue('invalid_ref','/reasoning_units/'+uid,'Unknown statement '+sid)
            seen.update(u['source_rsu_ids'])
        if len(orders)!=len(set(orders)):issue('invalid_ref','/reasoning_units','Duplicate presentation order')
        for rid,story in rsus.items():
            if rid not in seen or coverage[rid]!=set(story['figure_refs']):issue('missing_coverage','/coverage/'+rid,'All original RSUs and their multiple Figures must remain covered')
        used={doc['central_focus']['statement_id']}|{sid for u in units.values() for sid in statement_ids(u)}
        if set(statements)!=used:issue('missing_coverage','/statements','Orphan statements or unknown statement references')
        for rid,r in relations.items():
            x,y=units.get(r['source_unit']),units.get(r['target_unit'])
            if not x or not y:issue('invalid_ref','/reasoning_relations/'+rid,'Unknown unit endpoint');continue
            for bid in r['source_binding_ids']:
                if bid not in bindings:issue('invalid_ref','/reasoning_relations/'+rid,'Unknown relation source binding')
            real=sci.get(r['scientific_relation_ref']) if r['scientific_relation_ref'] else None
            if r['identity']=='scientific' or r['scientific_relation_ref']:
                if not real or real['type']!=r['relation_kind']:issue('unsupported_relation','/reasoning_relations/'+rid,'Scientific type/ref must exactly match M1')
                elif real['from'] not in x['entity_ids'] or real['to'] not in y['entity_ids']:issue('unsupported_relation','/reasoning_relations/'+rid,'M1 endpoints not represented by source/target units')
                if r['presentation_only']:issue('unsupported_relation','/reasoning_relations/'+rid,'M1 relation cannot be silently relabeled presentation-only')
                if real and ((real['type']=='argument_transition')!=(r['identity']=='author_argument')):
                    issue('unsupported_relation','/reasoning_relations/'+rid,'Author argument and scientific fact identity must remain separate')
            else:
                if r['relation_kind'] not in NARRATIVE_KINDS:issue('unsupported_relation','/reasoning_relations/'+rid,'Unregistered scientific relation cannot be introduced by narrative')
                if r['identity']=='presentation' and not r['presentation_only']:issue('unsupported_relation','/reasoning_relations/'+rid,'Presentation link must be presentation_only')
                if r['identity']=='author_argument' and (r['presentation_only'] or not r['source_binding_ids']):issue('source_gap','/reasoning_relations/'+rid,'Author argument requires exact source basis')
            effective['relation:'+rid]=review('relation',rid,r)
        for c in doc['conflicts']:
            for bid in c['source_binding_ids']:
                if bid not in bindings:issue('invalid_ref','/conflicts/'+c['id'],'Unknown conflict source')
            for sid in c['guard_statement_ids']:
                if sid not in statements or not statements[sid]['critical']:issue('missing_coverage','/conflicts/'+c['id'],'Conflict guard must be a retained critical statement')
            issue('unresolved_conflict','/conflicts/'+c['id'],'Source conflict retained without merging/correcting a value','warning')
        self._resolved,self._effective=resolved,effective
        return {'valid':not any(d['severity']=='error' for d in diagnostics),'formal_ready':not any(d['blocks_formal'] for d in diagnostics),
                'diagnostics':diagnostics,'source_registry_checks':'pointer/page metadata only','scientific_semantics':'not_automatically_verified',
                'independent_reader_test':'NOT_TESTED','image_visual_this_run':'NOT_TESTED'}

    def assemble(self):
        if self._base is not None:return copy.deepcopy(self._base)
        report=self.validate()
        if not report['valid']:raise NarrativeError('ASSEMBLY_REJECTED','Narrative input/relationship rejected',report['diagnostics'])
        doc=self.mapping;m=self.model;rsus={s['id']:s for s in m['stories']}
        units=sorted(copy.deepcopy(doc['reasoning_units']),key=lambda x:x['presentation_order'])
        for u in units:
            u['source_order']=sorted({n for rid in u['source_rsu_ids'] for n in rsus[rid]['original_section_order']})
            u['source_unit_ids']=[v['id'] for v in self.story['units'] if set(v['source_story_ids'])&set(u['source_rsu_ids'])]
        limits={}
        for i,s in enumerate(m['stories']):
            for j,value in enumerate(s['limits']):limits[f'/stories/{i}/limits/{j}']=value
        for i,e in enumerate(m['entities']):
            for j,value in enumerate(e['limits']):limits[f'/entities/{i}/limits/{j}']=value
        self._base={'narrative_plan_version':VERSION,'metadata':copy.deepcopy(doc['metadata']),'mapping_snapshot':fingerprint(doc),'review_snapshot':fingerprint(self.ledger),
            'central_focus':copy.deepcopy(doc['central_focus']),'reasoning_units':units,'statements':copy.deepcopy(doc['statements']),
            'bindings':copy.deepcopy(doc['bindings']),'resolved_bindings':copy.deepcopy(self._resolved),'reasoning_relations':copy.deepcopy(doc['reasoning_relations']),
            'source_scientific_relations':copy.deepcopy(m['relations']),'conflicts':copy.deepcopy(doc['conflicts']),'mandatory_limits':limits,
            'review_status':copy.deepcopy(self._effective),'validation':report,'upstream_diagnostics':copy.deepcopy(self.story['diagnostics']),
            'coverage':{'source_rsu_ids':list(rsus),'mapped_rsu_ids':list(dict.fromkeys(rid for u in units for rid in u['source_rsu_ids'])),
                        'figure_ids':list(dict.fromkeys(fid for u in units for fid in u['figure_ids']))},
            'automation_boundary':'Human mapping assembled; no scientific reasoning extracted automatically'}
        self._base['base_snapshot']=fingerprint(self._base);self.stats['base_builds']+=1
        return copy.deepcopy(self._base)

    def view(self,profile='balanced'):
        if profile not in DEPTH:raise NarrativeError('PROFILE','Unknown depth')
        base=self.assemble();statements={s['id']:s for s in base['statements']}
        core={base['central_focus']['statement_id']}|{u['main_message'] for u in base['reasoning_units']}|{s['id'] for s in base['statements'] if s['critical']}
        expanded=core|{s['id'] for s in base['statements'] if DEPTH[s['depth']]<=DEPTH[profile]}
        ordered=[s['id'] for s in base['statements']]
        self.stats['view_selections']+=1
        return {'view_version':VERSION,'profile':profile,'base_snapshot':base['base_snapshot'],
                'story_A':{'unit_ids':[u['id'] for u in base['reasoning_units']],'statement_ids':[s for s in ordered if s in core]},
                'story_B':{'unit_ids':[u['id'] for u in base['reasoning_units']],'statement_ids':[s for s in ordered if s in expanded]},
                'story_C':{'statement_ids':ordered,'binding_ids':list(base['resolved_bindings']),'mandatory_limit_refs':list(base['mandatory_limits'])},
                'coverage':copy.deepcopy(base['coverage']),'retained_critical_statement_ids':[s['id'] for s in base['statements'] if s['critical']]}

def validate_narrative_plan(model,story,framework,mapping,ledger,plan,assets=None,*,base_dir=None):
    try:
        expected=NarrativeAssembler(model,story,framework,mapping,ledger,assets,base_dir=base_dir).assemble()
        return {'valid':plan==expected,'diagnostics':[] if plan==expected else [{'code':'NARRATIVE_PLAN_DRIFT','message':'Edited output differs from bound assembler result'}]}
    except NarrativeError as exc:return {'valid':False,'diagnostics':exc.diagnostics}

def export_text(base,view,level):
    st={s['id']:s for s in base['statements']};bs=base['resolved_bindings'];selected=set(view['story_'+level]['statement_ids'])
    def cite(s):
        parts=[]
        for bid in s['source_binding_ids']:
            b=bs.get(bid)
            if not b:continue
            r=b['source_reference']
            figure_pages=','.join(str(ref['locator']['physical_page']) for ref in b['figure_source_references'])
            parts.append(f"主张定位 {r['document_id']} p.{r['locator']['physical_page']}"+(f"；{b['figure_id']}（图页p.{figure_pages}；panel={','.join(b['panels'])}）" if b['figure_id'] else '')+f" [{bid}; {b['pointer']}]")
        return '；'.join(parts) or '汇报组织／无科学来源，见诊断'
    lines=[f"# {base['metadata']['case_id']}｜Story {level}｜{view['profile']}",'',f"基底：{base['base_snapshot']}",f"结构有效；正式通过={base['validation']['formal_ready']}。人工辅助映射，不是自动提取。",'']
    focus=st[base['central_focus']['statement_id']];lines.extend([focus['display_text'],cite(focus),''])
    if level=='C':
        for s in base['statements']:
            status=base['review_status']['statement:'+s['id']]
            lines.extend([f"## {s['id']}｜{s['assertion_kind']} / {s['scope']}",s['display_text'],cite(s),f"语义：{status['status']}；文本/panel/图片：{status['checks']}",''])
    else:
        for u in base['reasoning_units']:
            lines.extend([f"## {u['title']}",f"RSU：{', '.join(u['source_rsu_ids'])}；原文顺序{u['source_order']}，讲述顺序{u['presentation_order']}（不表示实验时间）。"])
            for sid in statement_ids(u):
                if sid in selected:
                    s=st[sid];lines.extend([f"- [{sid} / {s['assertion_kind']}] {s['display_text']}",f"  来源：{cite(s)}"])
            lines.append('')
    if level in ('A','B'):
        titles={u['id']:u['title'] for u in base['reasoning_units']}
        lines.extend(['## 这些部分怎样联系（非实验时间线）',''])
        for r in base['reasoning_relations']:
            x,y=titles[r['source_unit']],titles[r['target_unit']]
            if r['identity']=='scientific':continue
            phrase={'parallel':f'从“{x}”并列考察“{y}”','comparison':f'将“{x}”与“{y}”作对照','synthesis':f'“{x}”与其他认识在“{y}”汇合'}.get(r['relation_kind'],f'论证从“{x}”转向“{y}”')
            lines.append(f'- {phrase}。{r["justification"]}（{r["identity"]}；{r["id"]}）')
        lines.append('')
    lines.extend(['## 全模式保留的原始限制（不可因压缩删去）',''])
    lines.extend(f'- {value}（{ref}）' for ref,value in base['mandatory_limits'].items())
    if base['conflicts']:lines.extend(['','## 未解决冲突',*[f"- {c['id']}：来源{c['source_binding_ids']}；保护语句{c['guard_statement_ids']}；未自动合并/修复。" for c in base['conflicts']]])
    return '\n'.join(lines)+'\n'

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('knowledge','story-plan','framework-plan','mapping','reviews','outdir'):ap.add_argument('--'+name,required=True,type=Path)
    ap.add_argument('--assets',type=Path);ap.add_argument('--profile',choices=[*DEPTH,'all'],default='balanced');ap.add_argument('--require-formal',action='store_true')
    args=ap.parse_args(argv)
    try:
        assembler=NarrativeAssembler(load(args.knowledge),load(args.story_plan),load(args.framework_plan),load(args.mapping),load(args.reviews),load(args.assets) if args.assets else None,base_dir=args.mapping.parent)
        base=assembler.assemble();modes=list(DEPTH) if args.profile=='all' else [args.profile]
        if args.outdir.exists() and any(args.outdir.iterdir()):raise NarrativeError('OUTPUT_EXISTS','Use a new output directory; no old results overwritten')
        args.outdir.mkdir(parents=True,exist_ok=True)
        def save(name,value):(args.outdir/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf-8')
        save('narrative.plan.json',base);save('diagnostics.json',base['validation']);save('relations.json',base['reasoning_relations']);save('coverage.json',base['coverage'])
        relation_text=['# 逻辑关系与分支（身份不等于箭头因果）','']+[f"- {r['id']}：{r['source_unit']} → {r['target_unit']}；{r['identity']} / {r['relation_kind']}；M1={r['scientific_relation_ref']}；{r['justification']}" for r in base['reasoning_relations']]
        (args.outdir/'relations.md').write_text('\n'.join(relation_text)+'\n','utf-8')
        for mode in modes:
            view=assembler.view(mode);save(mode+'.view.json',view)
            for level in 'ABC':(args.outdir/f'{mode}.story_{level}.md').write_text(export_text(base,view,level),'utf-8')
        save('execution.json',{'stats':assembler.stats,'profile_statement_counts':{mode:len(assembler.view(mode)['story_B']['statement_ids']) for mode in modes},'code_sha256':digest(__file__),'contract_sha256':digest(SCHEMA),'formal_ready':base['validation']['formal_ready']})
        print(json.dumps({'valid':True,'formal_ready':base['validation']['formal_ready'],'outdir':str(args.outdir),'profiles':modes},ensure_ascii=False))
        return 1 if args.require_formal and not base['validation']['formal_ready'] else 0
    except NarrativeError as exc:print(json.dumps({'valid':False,'code':exc.code,'message':str(exc),'diagnostics':exc.diagnostics},ensure_ascii=False));return 1
    except (OSError,ValueError,KeyError,TypeError,RecursionError) as exc:print(json.dumps({'valid':False,'code':'INPUT_ERROR','message':str(exc)},ensure_ascii=False));return 2

if __name__=='__main__':raise SystemExit(main())