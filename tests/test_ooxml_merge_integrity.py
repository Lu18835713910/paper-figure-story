"""Full CLI regressions. PFS_MERGE_CASE points to a read-only real regression input.
Outputs are isolated under PFS_MERGE_OUTPUT; no scientific fixture is rewritten.
"""
from pathlib import Path
import os,sys,json,subprocess,unittest,zipfile,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import render_logic as rr,research_logic as rl
from pptx import Presentation

@unittest.skipUnless(os.environ.get('PFS_MERGE_CASE'),'set PFS_MERGE_CASE for the real-case CLI matrix')
class MergeCLI(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.case=Path(os.environ['PFS_MERGE_CASE']);cls.out=Path(os.environ['PFS_MERGE_OUTPUT']);cls.out.mkdir(parents=True,exist_ok=False);cls.log=[]
  # Preserve the real three base files. A renderer/projection change requires a
  # freshly validated plan, not disabling PRODUCT_PLAN_DRIFT on frozen caches.
  cls.plan_path=Path(os.environ.get('PFS_MERGE_PLAN',str(cls.case/'plan/products.plan.json')))
  cls.meta_path=Path(os.environ.get('PFS_MERGE_METADATA',str(cls.case/'plan/metadata.resolved.json')))
  cls.plan=rl.load(cls.plan_path);cls.map=rl.load(cls.case/'page_map.json')
  assert cls.plan['logic_snapshot']==rl.load(cls.case/'input/research_logic.json')['snapshot']
 def cli(self,name,base,inject=None):
  out=self.out/name;out.mkdir();target=out/'main.pptx'
  args=[str(ROOT/'scripts/render_logic.py'),'--network',str(self.case/'input/evidence_network.json'),'--plan',str(self.plan_path),'--metadata',str(self.meta_path),'--output-dir',str(out/'graphs'),'--main-pptx',str(base),'--page-map',str(self.case/'page_map.json'),'--main-output',str(target),'--development-preview']
  prefix=[sys.executable,'-B']
  if inject:
   # Damage a staged output at the validation boundary, without changing the
   # renderer/validator or bypassing any check; run the actual CLI via runpy.
   driver="""import sys,runpy,zipfile,xml.etree.ElementTree as E
script=sys.argv[1];sys.argv=sys.argv[1:];done=False
def trace(f,event,arg):
 global done
 if event=='line' and f.f_code.co_filename==script and f.f_code.co_name=='render' and not done:
  import linecache
  if 'reopened=validate_package(temp)' in linecache.getline(script,f.f_lineno):
   p=f.f_locals['temp'];mode=MODE
   with zipfile.ZipFile(p) as z:items=[(i,z.read(i.filename)) for i in z.infolist()]
   dst=p.with_suffix('.injected.pptx')
   with zipfile.ZipFile(dst,'w') as z:
    for i,data in items:
     if mode=='relations' and i.filename=='ppt/_rels/presentation.xml.rels':
      r=E.fromstring(data)
      next(e for e in r if e.get('Type','').endswith('/slide')).set('Target','slides/DOES_NOT_EXIST.xml');data=E.tostring(r)
     if mode=='content' and i.filename=='ppt/slides/slide1.xml':
      root=E.fromstring(data);text=root.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}t');assert text is not None;text.text='CHANGED';data=E.tostring(root)
     z.writestr(i,data)
   dst.replace(p);done=True
 return trace
sys.settrace(trace);runpy.run_path(script,run_name='__main__')
""".replace('MODE',repr(inject))
   prefix+=['-c',driver]
  command=prefix+args;r=subprocess.run(command,capture_output=True,text=True,encoding='utf8',env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUTF8':'1'})
  (out/'stdout.log').write_text(r.stdout,'utf8');(out/'stderr.log').write_text(r.stderr,'utf8')
  self.log.append(dict(name=name,command=command,exit_code=r.returncode));(self.out/'commands.json').write_text(json.dumps(self.log,ensure_ascii=False,indent=2),'utf8')
  return r,target,out
 def verify_success(self,name,base):
  original=rr.validate_package(base);before=[rr.slide_content(s) for s in original.slides]
  r,target,out=self.cli(name,base);self.assertEqual(r.returncode,0,r.stderr)
  p=rr.validate_package(target);self.assertEqual(len(p.slides),len(before));receipt=rl.load(out/'graphs/render_receipt.json')
  scenes={prod['slides'][0]['coverage']['view']:prod['slides'][0] for prod in self.plan['products']}
  targets=set(self.map.values());verified=[]
  for i,s in enumerate(p.slides,1):
   if i not in targets:self.assertEqual(rr.slide_content(s),before[i-1]);verified.append(i)
  for view,num in self.map.items():rr.validate_scene(p.slides[num-1],scenes[view])
  self.assertEqual(receipt['main_sha256'],rl.file_sha(target))
  (out/'checks.json').write_text(json.dumps(dict(slides=len(before),non_target_pages_verified=verified,target_pages_verified=self.map,package_relationships='CLOSED',native_source_identity='PRESERVED'),ensure_ascii=False,indent=2),'utf8')
 def test_01_original_noncontinuous(self):self.verify_success('original',self.case/'main.base.pptx')
 def test_02_roundtrip(self):self.verify_success('roundtrip1',self.case/'main.base.rt.pptx')
 def test_03_double_roundtrip(self):self.verify_success('roundtrip2',self.case/'main.base.rt2.pptx')
 def test_04_continuous(self):
  base=self.out/'continuous.pptx';p=Presentation(self.case/'main.base.pptx');_=len(p.slides);p.save(base);self.verify_success('continuous',base)
 def test_05_corrupt_input(self):
  r,target,out=self.cli('corrupt_input',self.case/'audit/merge_failure_evidence/merged_broken_rId30.pptx');self.assertNotEqual(r.returncode,0);self.assertIn('DANGLING_RELATIONSHIP',r.stderr);self.assertFalse(target.exists());self.assertFalse((out/'graphs/render_receipt.json').exists())
 def test_06_corrupt_staged_relationship(self):
  r,target,out=self.cli('corrupt_staged',self.case/'main.base.pptx','relations');self.assertNotEqual(r.returncode,0);self.assertIn('DANGLING_RELATIONSHIP',r.stderr);self.assertFalse(target.exists());self.assertFalse((out/'graphs/render_receipt.json').exists())
 def test_07_changed_staged_non_target(self):
  r,target,out=self.cli('changed_non_target',self.case/'main.base.pptx','content');self.assertNotEqual(r.returncode,0);self.assertIn('NON_TARGET_CONTENT_DRIFT',r.stderr);self.assertFalse(target.exists());self.assertFalse((out/'graphs/render_receipt.json').exists())

if __name__=='__main__':unittest.main()
