"""Final two wording regressions, using retained source-bound real artifacts."""
import os,json,unittest
from pathlib import Path
from pptx import Presentation
from docx import Document
class RC4Wording(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.r=Path(os.environ['PFS_RC4_CASE']);cls.d=cls.r/'delivery/deliverables';cls.p=Presentation(cls.d/'PPT/Main.pptx')
 def test_p6_host_protein_and_plant_readouts_are_distinct(self):
  s=self.p.slides[5];t='\n'.join(q.text for q in s.shapes if q.has_text_frame)+'\n'+s.notes_slide.notes_text_frame.text
  for word in ['酵母','本氏烟草','IVF3545','Mock']:self.assertIn(word,t)
  self.assertNotIn('在番茄中验证 SlPP2C4 互作',t)
 def test_p14_and_word_do_not_generalize_materials_or_replicates(self):
  s=self.p.slides[13];t='\n'.join(q.text for q in s.shapes if q.has_text_frame)+'\n'+s.notes_slide.notes_text_frame.text
  for bad in ['同一批材料','多数为 n=3','直接互作（Y2H/SLC/Co-IP）']:self.assertNotIn(bad,t)
  for word in ['共沉淀','生物学独立样本','100个气孔','至少重复三次']:self.assertIn(word,t)
  doc=Document(self.d/'Workbook/Workbook.docx');body='\n'.join(p.text for p in doc.paragraphs)+'\n'+'\n'.join(c.text for tb in doc.tables for row in tb.rows for c in row.cells)
  for word in ['Fig.1h–n的实验体系','本氏烟草表达体系','互作证据与样本量的适用范围','不一概写成纯化蛋白直接结合']:self.assertIn(word,body)
  identity=json.loads((self.r/'model_identity.json').read_text('utf8'));self.assertEqual(doc.core_properties.identifier,identity['snapshot']);self.assertIs(identity['scientific_model_changed'],False)
if __name__=='__main__':unittest.main()
