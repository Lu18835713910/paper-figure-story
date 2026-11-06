"""Independent-acceptance regressions: native delivery, portable scenes, width and depth."""
import unittest,tempfile,sys,copy,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pptx import Presentation
from pptx.util import Inches,Pt
from PIL import Image
import render_logic as native,delivery_contract as dc,presentation_typography as typo,layout_preflight as lp,workbook_content as wc,research_logic as rl
class AcceptanceFix(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.d=Path(self.t.name)
 def scene(self):
  return dict(id='LOGIC_B',title='Scientific results',coverage={'view':'B'},source_logic_node_ids=['N','M'],source_logic_relation_ids=['E'],logic_snapshot='x',notes={},citation='',elements=[dict(kind='text',id='LOGIC_B_'+n+'_body',logic_node_id=n,text=n+' observed result',position=dict(left=50+i*400,top=200,width=300,height=120),font_size=30) for i,n in enumerate(['N','M'])],connectors=[dict(id='LOGIC_B_E',source_logic_relation_id='E',identity='SCIENTIFIC_EVIDENCE',relation_type='evidence_convergence',points=[[350,260],[450,260]],arrow=True)])
 def deck(self):
  prs=Presentation();sl=prs.slides.add_slide(prs.slide_layouts[6]);native.draw_scene(sl,dict(width=1280,height=720),self.scene());p=self.d/'native.pptx';prs.save(p);return p
 def model(self):return dict(snapshot='x',nodes=[dict(id='N'),dict(id='M')],edges=[dict(id='E',**{'from':'N','to':'M'})])
 def record(self,p):
  png=self.d/'p.png';Image.new('RGB',(200,100),'white').save(png)
  return dict(id='B',scope='complete',view='B',logic_snapshot='x',node_ids=['N','M'],edge_ids=['E'],pptx=str(p),pptx_sha256=rl.file_sha(p),png=str(png),png_sha256=rl.file_sha(png))
 def test_portable_no_host_requirement(self):self.assertTrue(native.dependencies()['available']);self.assertFalse(native.dependencies()['host_modules_required'])
 def test_native_nodes_and_edges(self):self.assertEqual(dc.rendered_topology(self.deck(),'B'),({'N','M'},{'E'}))
 def test_zero_raster_graphs(self):self.assertFalse(any(s.shape_type==13 for sl in Presentation(self.deck()).slides for s in sl.shapes))
 def test_native_arrowhead(self):self.assertTrue(any('tailEnd' in s._element.xml for sl in Presentation(self.deck()).slides for s in sl.shapes))
 def test_scaled_merge_preserves_topology(self):
  prs=Presentation();sl=prs.slides.add_slide(prs.slide_layouts[6]);native.draw_scene(sl,dict(width=1280,height=720),self.scene(),(0,0,Inches(8),Inches(4)));p=self.d/'scaled.pptx';prs.save(p);self.assertEqual(dc.rendered_topology(p,'B'),({'N','M'},{'E'}))
 def test_png_cannot_be_native_overview(self):
  p=self.deck();r=self.record(p);prs=Presentation();sl=prs.slides.add_slide(prs.slide_layouts[6]);sl.shapes.add_picture(r['png'],0,0);f=self.d/'raster.pptx';prs.save(f);main={**r,'id':'main','scope':'overview','placement':'main','parent_canvas':'B','main_slide':1,'pptx':str(f),'pptx_sha256':rl.file_sha(f)};self.assertIn('RENDERED_TOPOLOGY_LOSS',dc.validate_delivery(self.model(),[r,main],True)['errors'])
 def test_overview_A_is_checked(self):
  p=self.deck();r=self.record(p);r.update(view='A',scope='overview_A');self.assertIn('RENDERED_TOPOLOGY_LOSS',dc.validate_delivery(self.model(),[r])['errors'])
 def test_edge_loss_blocks_merge(self):
  p=self.deck();r=self.record(p);r['edge_ids']=[];self.assertFalse(dc.validate_delivery(self.model(),[r])['valid'])
 def test_short_label_margin_not_twice(self):
  for t in ['能力','DNA 真值','排空间混杂','Stage 2','128 导管','JT z = 7.43']:
   self.assertNotIn('\n',typo.wrap(t,typo.measure(t,8.5)+7.2,8.5),t)
 def test_long_label_wraps(self):self.assertIn('\n',typo.wrap('比较空间结构与克隆次序的影响',60,12))
 def test_actual_short_label_precheck(self):
  prs=Presentation();sl=prs.slides.add_slide(prs.slide_layouts[6]);t=sl.shapes.add_textbox(0,0,Inches(typo.measure('能力',8.5)/72+.12),Inches(.23));t.name='PFS_EDGE_LABEL';t.text='能力';t.text_frame.margin_left=t.text_frame.margin_right=Inches(.01);t.text_frame.margin_top=t.text_frame.margin_bottom=0;t.text_frame.paragraphs[0].runs[0].font.size=Pt(8.5);self.assertTrue(lp.preflight_prs(prs)['valid'])
 def test_real_unbreakable_numeric_overflow(self):
  prs=Presentation();sl=prs.slides.add_slide(prs.slide_layouts[6]);t=sl.shapes.add_textbox(0,0,Inches(.25),Inches(.25));t.name='PFS_EDGE_LABEL';t.text='123456789 μm';t.text_frame.margin_left=t.text_frame.margin_right=0;t.text_frame.paragraphs[0].runs[0].font.size=Pt(12);self.assertFalse(lp.preflight_prs(prs)['valid'])
 def content(self):
  p=self.d/'fact.txt';p.write_text('R = 0.88','utf-8');m=dict(snapshot='x',sources={'S':dict(excerpt='R = 0.88')});st=dict(text='An actual comparison and its evidence boundary.',source_ids=['S'],identity='OBSERVATION',status='PARTIAL')
  f=dict(id='Fig 1',title='Comparison',panels=['a'],**{k:copy.deepcopy(st) for k in wc.FIGURE_FIELDS});me=dict(id='M',title='Observed method',**{k:copy.deepcopy(st) for k in wc.METHOD_FIELDS});c=dict(version='pfs-workbook-content-1',logic_snapshot='x',expected_figures=['Fig 1'],figures=[f],methods=[me],inputs=[dict(path=str(p),sha256=rl.file_sha(p))],quantitative_results=[dict(id='q',label='R',value='0.88',meaning='Correlation',source_ids=['S'])]);return m,c
 def test_complete_teaching(self):m,c=self.content();self.assertTrue(wc.validate_content(m,c)['valid'])
 def test_missing_figure(self):m,c=self.content();c['expected_figures'].append('Fig 2');self.assertFalse(wc.validate_content(m,c)['valid'])
 def test_empty_method_cannot_claim_depth(self):m,c=self.content();c['methods']=[];self.assertFalse(wc.validate_content(m,c)['valid'])
 def test_unsupported_number_rejected(self):m,c=self.content();c['quantitative_results'][0]['value']='0.99';self.assertFalse(wc.validate_content(m,c)['valid'])
 def test_source_missing_rejected(self):m,c=self.content();c['figures'][0]['results']['source_ids']=[];self.assertFalse(wc.validate_content(m,c)['valid'])
 def test_fact_input_drift(self):m,c=self.content();Path(c['inputs'][0]['path']).write_text('changed','utf-8');self.assertFalse(wc.validate_content(m,c)['valid'])
 def test_model_snapshot_drift(self):m,c=self.content();c['logic_snapshot']='other';self.assertFalse(wc.validate_content(m,c)['valid'])

 def test_main_A_not_silently_omitted(self):
  p=self.deck();r=self.record(p);main={**r,'id':'main','scope':'overview','placement':'main','parent_canvas':'B','main_slide':1};self.assertIn('PLANNED_MAIN_NATIVE_VIEWS_MISSING',dc.validate_delivery(self.model(),[r,main],True)['errors'])
 def test_picture_name_cannot_forge_native_node(self):
  prs=Presentation();sl=prs.slides.add_slide(prs.slide_layouts[6]);im=self.d/'fake.png';Image.new('RGB',(20,20),'white').save(im);s=sl.shapes.add_picture(str(im),0,0);s.name='RC_LOGIC_B_LOGIC_B_N_body';p=self.d/'forged.pptx';prs.save(p);self.assertEqual(dc.rendered_topology(p,'B'),(set(),set()))
 def test_main_cannot_reseal_reduced_identity_list(self):
  p=self.deck();r=self.record(p);main={**r,'id':'main','placement':'main','main_slide':1,'scope':'overview','parent_canvas':'B','node_ids':['N'],'edge_ids':[]}
  self.assertIn('MAIN_VIEW_TOPOLOGY_DRIFT',dc.validate_delivery(self.model(),[r,main],True)['errors'])
 def test_contract_cannot_point_to_different_good_native_main(self):
  p=self.deck();r=self.record(p);main={**r,'id':'main','placement':'main','main_slide':1,'scope':'overview','parent_canvas':'B'}
  prs=Presentation();prs.slides.add_slide(prs.slide_layouts[6]);actual=self.d/'actual_main.pptx';prs.save(actual)
  result=dc.validate_delivery(self.model(),[r,main],True,main_pptx=actual)
  self.assertIn('MAIN_PPTX_IDENTITY_MISMATCH',result['errors']);self.assertIn('RENDERED_TOPOLOGY_LOSS',result['errors'])
 def test_repeated_figure_template_rejected(self):
  m,c=self.content();f=c['figures'][0];c['figures']=[{**copy.deepcopy(f),'id':'Fig '+str(i)} for i in range(1,4)];c['expected_figures']=[f['id'] for f in c['figures']]
  self.assertIn('REPEATED_FIGURE_TEMPLATE:results',wc.validate_content(m,c)['errors'])
 def test_default_workbook_cli_reports_missing_source_inputs(self):
  import subprocess
  r=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/build_research_workbook.py'),'--model','missing','--graphs','missing','--output',str(self.d/'out.docx')],capture_output=True,text=True)
  self.assertEqual(r.returncode,2);self.assertIn('WORKBOOK_TEACHING_CONTENT_REQUIRED',r.stdout);self.assertIn('SOURCE_INPUT_INVALID',r.stdout);self.assertFalse((self.d/'out.docx').exists())
if __name__=='__main__':unittest.main()
