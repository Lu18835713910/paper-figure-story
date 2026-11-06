"""Real CLI receipt relocation: file names never establish scientific identity."""
import json,os,subprocess,sys,tempfile,unittest,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ReceiptRelocation(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.case=Path(os.environ['PFS_G5_CASE'])
  cls.receipt=json.loads((cls.case/'run/graphs_final/render_receipt.json').read_text('utf8'))
  cls.home=Path(os.environ['PFS_G5_TEST_OUTPUT']);cls.home.mkdir(parents=True,exist_ok=True)
 def invoke(self,receipt,override=None,relative=False):
  d=Path(tempfile.mkdtemp(dir=self.home));r=d/'receipt.json';out=d/'graph.json'
  if relative:
   receipt=json.loads(json.dumps(receipt));shutil.copy2(receipt['files'][0]['path'],d/'view.pptx');receipt['files'][0]['path']='view.pptx'
  r.write_text(json.dumps(receipt,ensure_ascii=False),'utf8')
  cmd=[sys.executable,'-B',str(ROOT/'scripts/register_logic_graphs.py'),'--model',str(self.case/'inputs/research_logic.json'),'--plan',str(self.case/'run/plan_final/products.plan.json'),'--receipt',str(r),'--png-dir',str(self.case/'run/graph_png_final'),'--navigation',str(self.case/'run/navigation.json'),'--output',str(out)]
  if override:cmd+=['--main-pptx',str(override)]
  p=subprocess.run(cmd,capture_output=True,text=True,encoding='utf8');return p,out,d
 def moved(self):
  r=json.loads(json.dumps(self.receipt));r['main_pptx']=str(self.home/'no-longer-retained-main.pptx');return r
 def test_missing_main_has_structured_rejection(self):
  p,out,_=self.invoke(self.moved());self.assertEqual(p.returncode,2,p.stderr);self.assertIn('GRAPH_RECEIPT_INPUT_MISSING:main_pptx',p.stdout);self.assertFalse(out.exists());self.assertNotIn('Traceback',p.stderr)
 def test_wrong_override_sha_is_rejected(self):
  p,out,_=self.invoke(self.moved(),self.receipt['files'][0]['path']);self.assertEqual(p.returncode,2,p.stderr);self.assertIn('GRAPH_RECEIPT_INPUT_SHA_MISMATCH:main_pptx',p.stdout);self.assertFalse(out.exists())
 def test_exact_sha_renamed_main_is_accepted(self):
  d=Path(tempfile.mkdtemp(dir=self.home));main=d/'renamed-main.pptx';shutil.copy2(self.receipt['main_pptx'],main)
  full=next(f for f in self.receipt['files'] if f['view']=='B');shutil.copy2(full['path'],d/self.receipt['full_b_reference'])
  p,out,_=self.invoke(self.moved(),main);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertTrue(out.exists());self.assertEqual(json.loads(out.read_text('utf8'))['main_graphs'][0]['pptx'],str(main.resolve()))
 def test_relative_product_path_is_resolved_from_receipt(self):
  # Resolve to a retained real file, never cwd or a similarly named deck.
  p,out,d=self.invoke(self.receipt,relative=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertTrue(out.exists());self.assertEqual(json.loads(out.read_text('utf8'))['graphs'][0]['pptx'],str((d/'view.pptx').resolve()))
if __name__=='__main__':unittest.main()
