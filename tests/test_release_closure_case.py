"""Hash-bound real regression artifacts; not a new paper reasoning benchmark."""
import json,os,sys,re,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import research_logic as rl,workbook_content as wc
class ClosureCase(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.r=Path(os.environ['PFS_CLOSURE_CASE']);cls.m=rl.load(cls.r/'inputs/research_logic.json');cls.inv=rl.load(cls.r/'inputs/inventory.json')
 def test_actual_x15_only_counts_are_inapplicable(self):
  x=next(e for e in self.inv['experiments'] if e['experiment_id']=='X15_MODEL');self.assertEqual(x['task_type'],'model')
  for key in ['sample_count','sample_unit','biological_replicates','technical_replicates','independent_runs']:
   f=x['fields'][key];self.assertEqual(f['status'],'NOT_APPLICABLE');self.assertIs(f['applicable'],False);self.assertTrue(f['reason']);self.assertTrue(f['source_refs'])
  self.assertTrue(any(f['status']=='NOT_REPORTED' for e in self.inv['experiments'] if e['experiment_id']!='X15_MODEL' for f in e['fields'].values()))
 def test_model_parent_sources_and_topology_preserved(self):
  l=rl.load(self.r/'lineage.json');self.assertTrue(l['nodes_unchanged']);self.assertTrue(l['edge_identities_unchanged']);self.assertTrue(l['index_unchanged']);self.assertTrue(rl.validate_model(self.m)['valid'])
 def test_registered_teaching_has_no_confirmed_hr_or_efficiency_error(self):
  c=wc.assemble_content(self.m,self.r/'inputs/workbook_bindings.json');self.assertTrue(c['valid'],c.get('gaps'))
  text='\n'.join(f['text'] for group in ['figures','methods'] for row in c['content'][group] for f in row.values() if isinstance(f,dict) and 'text' in f)
  for bad in ['敲低削弱 Sw-5b 抗性与 HR','HR 与抗性减弱','Fig. 3i 残余信号 0.09','eGFP 与 N 蛋白显著降低']:self.assertNotIn(bad,text)
 def test_actual_workbook_pdf_has_no_footer_only_page(self):
  import fitz
  doc=fitz.open(self.r/'final_delivery/deliverables/Workbook/Workbook.pdf');self.assertGreater(len(doc),20)
  for i,p in enumerate(doc):
   body=re.sub(r'逻辑模型\s*[0-9a-f]+\s*\d+','',p.get_text()).strip()
   self.assertTrue(body or p.get_images(),str(i+1))
 def test_actual_word_na_and_identity(self):
  from docx import Document
  d=Document(self.r/'final_delivery/deliverables/Workbook/Workbook.docx');text='\n'.join(p.text for p in d.paragraphs)+'\n'+'\n'.join(c.text for t in d.tables for row in t.rows for c in row.cells)
  self.assertEqual(d.core_properties.identifier,self.m['snapshot']);self.assertNotIn('not applicable [NOT_REPORTED]',text);self.assertIn('NOT_APPLICABLE',text)
if __name__=='__main__':unittest.main()
