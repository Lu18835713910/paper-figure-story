import unittest,sys,os,json,copy,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import workbook_content as wc,project_evidence_products as pp,research_logic as rl

class Citation(unittest.TestCase):
 def test_empty_page(self):
  self.assertNotIn('PDF p.',pp._citation({'paper':{'title':'x'},'figures':[]},{'doi':'d'},[],[]))
 def test_valid_page(self):
  self.assertIn('PDF p.4',pp._citation({'paper':{'title':'x'},'figures':[]},{'doi':'d'},[],[{'source_refs':[{'locator':{'physical_page':4}}]}]))
 def test_doi(self):
  n={'paper':{'title':'x'},'figures':[]};self.assertIn('DOI d',pp._citation(n,{'doi':'d'},[],[]));self.assertIn('DOI 待核实',pp._citation(n,{},[],[]))

class Consumer(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.root=Path(os.environ['PFS_TEST_RUN']);cls.model=rl.load(cls.root.parent/'G2_Cell_resume_2026-11-02/inputs/research_logic.json');cls.content=rl.load(cls.root/'inputs/content.json');cls.reg=rl.load(cls.root.parent/'G2_Cell_delivery_2026-11-02/figure_assets/figure_assets.reviewed.json')
 def checked(self,reg):
  with tempfile.TemporaryDirectory(dir=self.root) as d:
   p=Path(d)/'r.json';p.write_text(json.dumps(reg),'utf8');return wc.reviewed_figure_images(self.model,self.content,p)
 def test_all_seven_real(self):
  images,receipt=self.checked(self.reg);self.assertEqual(set(images),{f['id'] for f in self.content['figures']});self.assertEqual(len(receipt['assets']),7)
 def test_legacy_absent(self):self.assertEqual(wc.reviewed_figure_images(self.model,self.content,None),({},None))
 def test_missing_file(self):
  r=copy.deepcopy(self.reg);r['assets'][0]['path']=str(self.root/'DOES_NOT_EXIST.png')
  with self.assertRaisesRegex(ValueError,'FIDELITY'):self.checked(r)
 def test_bad_sha(self):
  r=copy.deepcopy(self.reg);r['assets'][0]['sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'FIDELITY'):self.checked(r)
 def test_bad_identity(self):
  r=copy.deepcopy(self.reg);r['assets'][0]['figure_id']='UNKNOWN'
  with self.assertRaisesRegex(ValueError,'FIGURE_ID'):self.checked(r)
 def test_missing_figure(self):
  r=copy.deepcopy(self.reg);r['assets'].pop()
  with self.assertRaisesRegex(ValueError,'FIGURE_MISSING'):self.checked(r)
 def test_panel_loss(self):
  r=copy.deepcopy(self.reg);r['assets'][0]['panels']=['A']
  with self.assertRaisesRegex(ValueError,'FIGURE_PANELS'):self.checked(r)
 def test_source_drift(self):
  c=copy.deepcopy(self.content);c['logic_snapshot']='0'*64;self.assertFalse(wc.validate_content(self.model,c)['valid'])
if __name__=='__main__':unittest.main()
