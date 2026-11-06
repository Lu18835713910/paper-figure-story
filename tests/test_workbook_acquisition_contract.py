import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_research_workbook import acquisition_field,WorkbookFieldError
class AcquisitionContract(unittest.TestCase):
 def setUp(self):self.f=dict(value='Synthetic measurement',status='PARTIAL',source_refs=[])
 def test_canonical(self):self.assertIs(acquisition_field(dict(acquisition=self.f),'X'),self.f)
 def test_legacy(self):self.assertIs(acquisition_field(dict(methods=self.f),'X'),self.f)
 def test_equal_aliases(self):self.assertIs(acquisition_field(dict(acquisition=self.f,methods=dict(self.f)),'X'),self.f)
 def test_conflict(self):
  with self.assertRaisesRegex(WorkbookFieldError,'CONFLICT.*X'):acquisition_field(dict(acquisition=self.f,methods=dict(self.f,status='VERIFIED')),'X')
 def test_missing(self):
  with self.assertRaisesRegex(WorkbookFieldError,'REQUIRED.*X'):acquisition_field({},'X')
 def test_invalid(self):
  for v in [None,'method',{},dict(status='PARTIAL')]:
   with self.subTest(value=v),self.assertRaisesRegex(WorkbookFieldError,'INVALID.*X'):acquisition_field(dict(acquisition=v),'X')
if __name__=='__main__':unittest.main()
