import json,sys,tempfile,unittest,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import delivery_contract as dc,research_logic as rl
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx import Presentation
class DeliveryEntry(unittest.TestCase):
 def setUp(self):self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)
 def word(self,target):
  p=self.p/'Workbook';p.mkdir(exist_ok=True);d=Document();link=OxmlElement('w:hyperlink');link.set(qn('r:id'),d.part.relate_to(target,RT.HYPERLINK,is_external=True));d.add_paragraph()._p.append(link);out=p/'read.docx';d.save(out);return out
 def test_actual_relative_directory_not_basename(self):
  (self.p/'Complete_B.editable.pptx').write_bytes(b'fixture');p=self.word('Complete_B.editable.pptx');self.assertFalse(dc.relative_dependencies(self.p,p)['valid'])
 def test_relative_attachment_present(self):
  p=self.word('Complete_B.editable.pptx');(p.parent/'Complete_B.editable.pptx').write_bytes(b'fixture');self.assertTrue(dc.relative_dependencies(self.p,p)['valid'])
 def test_escape_root_blocked(self):
  p=self.word('../../external.pptx');self.assertFalse(dc.relative_dependencies(self.p,p)['valid'])
 def test_existing_wrong_snapshot_not_accepted(self):
  p=Presentation();s=p.slides.add_slide(p.slide_layouts[6]);q=s.shapes.add_textbox(0,0,100,100);q.name='RC_LOGIC_B_TEST_body';q.text='fixture';s.notes_slide.notes_text_frame.text='模型快照：old';out=self.p/'test.pptx';p.save(out);self.assertFalse(dc.main_model_audit(out,dict(snapshot='new'))['valid'])
 def test_no_host_before_pdf_read(self):
  script=Path(__file__).resolve().parents[1]/'scripts/run_pfs.py';out=self.p/'run';p=subprocess.run([sys.executable,str(script),'run','--pdf','does-not-exist.pdf','--outdir',str(out),'--development-preview'],capture_output=True,text=True);self.assertEqual(p.returncode,2);r=rl.load(out/'execution.json');self.assertEqual(r['pdf_parse_calls'],0);self.assertEqual(r['status'],'BLOCKED')
 def test_adaptive_does_not_copy_scaffold_without_host(self):
  script=Path(__file__).resolve().parents[1]/'scripts/render_research.py';p=subprocess.run([sys.executable,str(script),'missing.json','--assets','missing.json','--outdir',str(self.p/'out')],capture_output=True,text=True);self.assertIn('HOST_BACKEND_REQUIRED',p.stderr);self.assertFalse((self.p/'out').exists())
 def test_package_file_hash_must_match(self):
  p=self.p/'a.pptx';p.write_bytes(b'changed');(self.p/'Manifest.json').write_text(json.dumps(dict(files=[dict(path='a.pptx',sha256='wrong',logic_snapshot='m')],logic_snapshot='m',scientific_review='PARTIAL')),'utf8');self.assertFalse(dc.check_package(self.p)['valid'])
 def test_partial_manifest_is_not_complete(self):
  (self.p/'Manifest.json').write_text(json.dumps(dict(files=[],logic_snapshot='m',scientific_review='PARTIAL',not_delivered=['main'])),'utf8');q=dc.check_package(self.p);self.assertTrue(q['valid']);self.assertFalse(q['requested_complete'])
if __name__=='__main__':unittest.main()
