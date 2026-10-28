#!/usr/bin/env python3
"""Source-validated M2-B rendering entry point; v1.0 CLI is unchanged.
The legacy builder supplies template/Figure scaffolding. Artifact Tool authors graphs.
"""
import argparse,json,os,shutil,subprocess,sys,time
from pathlib import Path
from project_presentation import PresentationProjector,validate_page_plan,legacy_manifest,ProjectionError
import plan_research

def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n','utf-8')
def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('knowledge',type=Path);p.add_argument('--assets',required=True,type=Path);p.add_argument('--outdir',required=True,type=Path);p.add_argument('--profile',choices=['quick','balanced','full','all'],default='balanced');p.add_argument('--template',type=Path);p.add_argument('--template-mode',choices=['auto','tagged','native'],default='auto');p.add_argument('--node',default=shutil.which('node'));p.add_argument('--artifact-module',required=True);p.add_argument('--plan-only',action='store_true')
 a=p.parse_args(argv);started=time.monotonic();script=Path(__file__).resolve().parent;m=json.loads(a.knowledge.read_text('utf-8'));assets=json.loads(a.assets.read_text('utf-8'));projector=PresentationProjector(m,assets,verify_files=True,base_dir=a.knowledge.parent)
 plans=projector.project_all() if a.profile=='all' else {a.profile:projector.project(a.profile)};results=[]
 # Validate the whole requested batch before authoring the first slide.
 for mode,plan in plans.items():
  bundle=projector.planner.plan(mode);save(a.outdir/'plans'/f'story.{mode}.json',bundle['story_plan']);save(a.outdir/'plans'/f'framework.{mode}.json',bundle['framework_plan'])
  validation=validate_page_plan(m,assets,plan,verify_files=True);save(a.outdir/'plans'/f'pages.{mode}.json',plan);save(a.outdir/'plans'/f'pages.{mode}.validation.json',validation)
  if not validation['valid'] or not plan['formal_ready']:raise ProjectionError('NOT_FORMAL_READY',f'{mode}: independent page validation or source/image review incomplete')
 save(a.outdir/'B1_gate.json',{'status':'PASS','profiles':list(plans),'knowledge_sha256':plan_research.fingerprint(m),'meaning':'source bindings/recorded checks; not automatic scientific truth verification'})
 if a.plan_only:return 0
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',PYTHONUTF8='1')
 for mode,plan in plans.items():
  tick=time.monotonic();private=a.outdir/'build'/mode;private.mkdir(parents=True,exist_ok=True);manifest=private/'legacy_scaffold.json';save(manifest,legacy_manifest(m,assets,plan));base=private/'base.pptx';candidate=a.outdir/f'{mode}.pptx'
  if candidate.exists():raise ProjectionError('OUTPUT_EXISTS',f'Refusing to overwrite existing result: {candidate}; choose a revision directory')
  cmd=[sys.executable,'-B',str(script/'build_pptx.py'),str(manifest),'--output',str(base),'--template-mode',a.template_mode]
  if a.template:cmd+=['--template',str(a.template)]
  proc=subprocess.run(cmd,env=env,capture_output=True,text=True,encoding='utf-8');(private/'legacy.log').write_text(proc.stdout+'\n'+proc.stderr,'utf-8')
  if proc.returncode:raise RuntimeError(proc.stderr or proc.stdout)
  cmd=[a.node,str(script/'render_adaptive_pptx.mjs'),'--base',str(base),'--plan',str(a.outdir/'plans'/f'pages.{mode}.json'),'--knowledge',str(a.knowledge),'--output',str(candidate),'--artifact-module',a.artifact_module,'--preview-dir',str(a.outdir/'framework_previews'/mode),'--python',sys.executable]
  proc=subprocess.run(cmd,env=env,capture_output=True,text=True,encoding='utf-8');(private/'artifact.log').write_text(proc.stdout+'\n'+proc.stderr,'utf-8')
  if proc.returncode:raise RuntimeError(proc.stderr or proc.stdout)
  results.append({'profile':mode,'pptx':str(candidate),'slides':len(plan['slides']),'segments':len(plan['segments']),'rsus':len(plan['source_rsu_ids']),'method_pages':plan['statistics']['method_pages'],'figure_pages':plan['statistics']['figure_pages'],'elapsed_s':round(time.monotonic()-tick,3)})
  save(a.outdir/'render_execution.json',{'results':results,'projector_stats':projector.stats,'planning_stats':projector.planner.stats,'elapsed_s':round(time.monotonic()-started,3)})
 print(json.dumps(results,ensure_ascii=False));return 0
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as exc:print(json.dumps({'valid':False,'error':str(exc),'code':getattr(exc,'code','RENDER_ERROR')},ensure_ascii=False),file=sys.stderr);raise SystemExit(1)
