import sys,copy,unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'scripts'),str(Path(__file__).resolve().parent)]
import experiment_inventory as inv,workbook_content as wc
from presentation_typography import wrap
import test_inventory_synthetic as fixture_module
class FinalQuality(unittest.TestCase):
 @classmethod
 def setUpClass(cls):fixture_module.SyntheticInventoryTests.setUpClass()
 @classmethod
 def tearDownClass(cls):fixture_module.SyntheticInventoryTests.tearDownClass()
 def check(self,**updates):
  obj=copy.deepcopy(fixture_module.SyntheticInventoryTests.inv);f=dict(value=None,status='NOT_APPLICABLE',source_refs=[fixture_module.SyntheticInventoryTests.ref],applicable=False,reason='This self-authored qualitative model has no sample count.');f.update(updates);obj['experiments'][0]['fields']['sample_count']=f
  return inv.validate_inventory(obj,fixture_module.SyntheticInventoryTests.model,base_dir=fixture_module.SyntheticInventoryTests.work,knowledge_path=fixture_module.SyntheticInventoryTests.kp)
 def test_na_valid(self):self.assertTrue(self.check()['valid'])
 def test_na_numeric_conflict(self):self.assertFalse(self.check(value=3)['valid'])
 def test_na_applicable_conflict(self):self.assertFalse(self.check(applicable=True)['valid'])
 def test_na_reason_required(self):self.assertFalse(self.check(reason='')['valid'])
 def test_na_scope_required(self):self.assertFalse(self.check(source_refs=[])['valid'])
 def test_legacy_unchanged(self):self.assertTrue(inv.validate_inventory(fixture_module.SyntheticInventoryTests.inv,fixture_module.SyntheticInventoryTests.model,base_dir=fixture_module.SyntheticInventoryTests.work,knowledge_path=fixture_module.SyntheticInventoryTests.kp)['valid'])
 def test_legacy_audit_has_no_new_zero_keys(self):
  a=inv.audit_inventory(fixture_module.SyntheticInventoryTests.inv)
  self.assertNotIn('NOT_APPLICABLE',a['summary']['method_source_status_counts'])
 def test_na_audit_reports_status(self):
  obj=copy.deepcopy(fixture_module.SyntheticInventoryTests.inv)
  obj['experiments'][0]['fields']['sample_count'].update(status='NOT_APPLICABLE',applicable=False)
  self.assertEqual(inv.audit_inventory(obj)['summary']['field_status_counts']['sample_count']['NOT_APPLICABLE'],1)
 def test_na_excludes_applicable_denominator(self):self.assertFalse(inv._applicable(dict(fields={'sample_count':dict(status='NOT_APPLICABLE',applicable=False)}),'sample_count'))
 def test_na_source_display(self):self.assertIn('不适用',wc.source_label({'sources':{'S':{'physical_page':1}}},dict(source_ids=['S'],identity='LIMITATION',status='NOT_APPLICABLE')))
 def test_numeric_error_atom(self):
  s=wrap('比较值 0.43 ± 0.04* 与对照',120,22)
  self.assertTrue(any('0.43 ± 0.04*' in line for line in s.splitlines()),s)
 def test_punctuation_never_starts_line(self):
  for text in ['观察结果（0.56→1.00）','条件变化，结果仍有限。','Alpha与中文比较，Beta为对照。']:
   s=wrap(text,150,22)
   self.assertFalse(any(x and x[0] in '，。；：）》】,)' for x in s.splitlines()),s)
 def test_old_units_stay_together(self):self.assertIn('6.5 Å',wrap('局部距离 6.5 Å 作为对照',140,22))
if __name__=='__main__':unittest.main()



