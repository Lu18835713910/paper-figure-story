"""v1.1.1 source fidelity, complete topology, reading gates and card geometry regressions."""
from pathlib import Path
import copy,hashlib,io,json,subprocess,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import fitz
from PIL import Image
import figure_assets as fa,delivery_contract as dc,scientific_index as si,layout_preflight as lp
import project_research_logic as pr
class Maintenance(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.d=Path(self.tmp.name)
 def pdf(self,color='white',mask=False,vector=False):
  im=Image.new('RGBA' if mask else 'RGB',(120,120),(0,0,0,0) if mask else color)
  if mask:
   from PIL import ImageDraw
   ImageDraw.Draw(im).rectangle((30,30,90,90),fill=(255,30,20,255))
  b=io.BytesIO();im.save(b,format='PNG');p=self.d/'source.pdf';doc=fitz.open();page=doc.new_page(width=200,height=200);page.insert_image(fitz.Rect(20,20,180,180),stream=b.getvalue())
  if vector:page.insert_text((25,30),'Panel A - Axis / legend')
  doc.save(p);doc.close();return p
 def asset(self,**kw):
  pdf=self.pdf(**kw);reg=fa.prepare(pdf,[dict(id='F1',physical_page=1,bbox_pt=[10,10,190,190],panels=['a'])],self.d/'assets',72);return reg
 def test_plain(self):self.assertTrue(fa.validate_registry(self.asset())['valid'])
 def test_smask(self):
  r=self.asset(mask=True);self.assertTrue(fa.validate_registry(r)['valid'])
  with fitz.open(r['assets'][0]['source_pdf']) as d:
   x=d[0].get_images(full=True)[0];im=fa.composite_embedded(d,x[0],x[1]);self.assertEqual(im.getpixel((0,0)),(255,255,255))
 def test_native_black(self):self.assertTrue(fa.validate_registry(self.asset(color='black'))['valid'])
 def test_vector_and_raster(self):self.assertTrue(fa.validate_registry(self.asset(vector=True))['valid'])
 def test_bad_pixels_even_resealed(self):
  r=self.asset(mask=True);a=r['assets'][0];Image.new('RGB',a['pixels'],'black').save(a['path']);a['sha256']=fa.sha(a['path']);self.assertFalse(fa.validate_registry(r)['valid'])
 def test_missing_source(self):self.assertEqual(fa.validate_asset({})['status'],'UNVERIFIED')
 def test_bad_page(self):
  p=self.pdf()
  with self.assertRaises(ValueError):fa.region(p,0,[0,0,200,200])
 def test_bad_crop(self):
  p=self.pdf()
  with self.assertRaises(ValueError):fa.region(p,1,[-1,0,200,200])
 def test_all_not_fine_mapping(self):
  r=self.asset();r['assets'][0]['panels']=['all'];self.assertFalse(fa.validate_registry(r)['valid'])
 def test_pdf_drift(self):
  r=self.asset();Path(r['assets'][0]['source_pdf']).write_bytes(b'broken');self.assertFalse(fa.validate_registry(r)['valid'])
 def test_alpha_drift(self):
  r=self.asset();a=r['assets'][0];im=Image.new('RGBA',a['pixels'],(255,255,255,0));im.save(a['path']);a['sha256']=fa.sha(a['path']);self.assertFalse(fa.validate_registry(r)['valid'])
 def test_unregistered_build(self):
  p=self.d/'x.png';Image.new('RGB',(10,10)).save(p)
  with self.assertRaisesRegex(ValueError,'REGISTRY_REQUIRED'):fa.validate_manifest_images({'slides':[dict(kind='figure',images=[str(p)])]},self.d)
 def test_text_no_figure_error(self):self.assertEqual(fa.validate_manifest_images({'slides':[dict(kind='text')]},self.d)['status'],'NOT_APPLICABLE')
 def model(self):
  return dict(snapshot='source',nodes=[dict(id='N1'),dict(id='N2'),dict(id='N3')],edges=[dict(id='E',**{'from':'N1','to':'N2'})])
 def full(self):return dict(id='B',view='B',scope='complete',logic_snapshot='source',node_ids=['N1','N2','N3'],edge_ids=['E'])
 def test_empty_or_relabelled_overview_is_rejected(self):
  # C1 intentionally closes the former metadata-only false-positive contract.
  self.assertFalse(dc.validate_delivery(self.model(),[self.full(),dict(scope='overview',parent_canvas='B',logic_snapshot='source',node_ids=[],edge_ids=[])],True,False)['valid'])
 def test_zoom_only_not_B(self):self.assertFalse(dc.validate_delivery(self.model(),[dict(scope='zoom',logic_snapshot='source',node_ids=['N1'],edge_ids=[],parent_canvas='B')],True,False)['valid'])
 def test_B_missing_node(self):
  r=self.full();r['node_ids'].pop();self.assertIn('B_TOPOLOGY_LOSS',dc.validate_delivery(self.model(),[r],True,False)['errors'])
 def test_B_missing_edge(self):
  r=self.full();r['edge_ids']=[];self.assertFalse(dc.validate_delivery(self.model(),[r],True,False)['valid'])
 def test_zoom_invented_edge(self):
  z=dict(scope='zoom',parent_canvas='B',logic_snapshot='source',node_ids=['N1','N2'],edge_ids=['invented']);self.assertFalse(dc.validate_delivery(self.model(),[self.full(),z],True,False)['valid'])
 def test_B_not_unconditionally_required(self):self.assertTrue(dc.validate_delivery(self.model(),[],False,False)['valid'])
 def test_skeleton_is_pending(self):
  p=self.pdf();x=si.skeleton(dict(source_pdf=str(p),file_sha256=fa.sha(p),page_count=1));self.assertFalse(si.validate(x)['valid']);self.assertEqual(x['reading_status'],'PENDING')
 def test_fake_completion_empty_is_rejected(self):
  p=self.pdf();x=si.skeleton(dict(source_pdf=str(p),file_sha256=fa.sha(p),page_count=1));x.update(reading_status='AVAILABLE_CONTENT_READ',methods_task_detection='COMPLETE_AVAILABLE',result_mapping_status='MAPPED_WITH_GAPS');self.assertFalse(si.validate(x)['valid'])
 def test_card_three_parts(self):
  x=lp.card_stack('研究问题','比较Alpha与Beta','Fig.1a',2.5,1.45);self.assertGreaterEqual(x['figure_y'],x['detail_y']+x['detail_h']+.059)
 def test_card_dense_fails_without_font_shrink(self):
  with self.assertRaisesRegex(ValueError,'CARD_STACK_OVERFLOW'):lp.card_stack('研究问题','很长的科研内容'*100,'Fig.2',2,1)
 def test_canvas_B_contains_non_core_child(self):
  n=lambda id,kind:dict(id=id,kind=kind,identity='SCIENTIFIC_EVIDENCE',short_text=id,title=id,detail_text=id,source_ids=['S'],statement_ids=[],source_entity_ids=[],field_bindings=[])
  m=dict(nodes=[n('Q','question'),n('R','synthesis'),n('CHILD','experiment')],edges=[],core={'nodes':['Q','R'],'edges':[]},branches=[],layout={},sources={'S':dict(physical_page=1)},snapshot='x',paper_title='test')
  p=pr.build_scene({'paper':{'paper_type':'original_research'}},m,'B');self.assertEqual(set(p['slides'][0]['source_logic_node_ids']),{'Q','R','CHILD'})
 def test_full_profile_rejects_missing_ppt(self):
  import validate_story as vs
  for f in vs.FILES:(self.d/f).write_text('Figure 1 样本 实验 结果 下一 来源','utf-8')
  r=subprocess.run([sys.executable,str(Path(vs.__file__)),str(self.d),'--profile','full'],capture_output=True)
  self.assertNotEqual(r.returncode,0);self.assertIn(b'07_',r.stdout)

 def test_missing_main_overview_blocked(self):
  self.assertIn('MAIN_B_OVERVIEW_REQUIRED',dc.validate_delivery(self.model(),[self.full()],True,False)['errors'])
 def test_explicit_dpi_request(self):
  p=self.pdf();r=fa.prepare(p,[dict(id='p',physical_page=1,bbox_pt=[0,0,200,200],dpi=100,panels=['a'])],self.d/'with_dpi');self.assertTrue(fa.validate_registry(r)['valid'])
 def test_invalid_crop_arity(self):
  p=self.pdf()
  with self.assertRaisesRegex(ValueError,'CROP_BOUNDS'):fa.region(p,1,[0,1])
 def test_multi_panel_mixed(self):
  r=self.asset(mask=True,vector=True);r['assets'][0]['panels']=['a','b','c'];self.assertTrue(fa.validate_registry(r)['valid']);self.assertEqual(r['assets'][0]['panel_mapping_status'],'PENDING')
 def test_route_obstacle(self):
  pos={'A':[10,210,200,200],'B':[310,210,200,200],'C':[610,210,200,200]}
  old=pr._route(pos['A'],pos['C'],0,1200);self.assertTrue(pr.route_hits_node(old,pos,{'A','C'}))
  new=pr.safe_route(pos,'A','C',0,1200);self.assertFalse(pr.route_hits_node(new,pos,{'A','C'}))
 def test_empty_context_image_is_blocking(self):
  from pptx import Presentation
  from pptx.util import Inches
  import polish_presentation as pp
  im=self.d/'image.png';Image.new('RGB',(100,100),'white').save(im)
  prs=Presentation();sl=prs.slides.add_slide(prs.slide_layouts[6]);sl.shapes.add_picture(str(im),0,0,width=Inches(2));f=self.d/'image.pptx';prs.save(f)
  q=pp.audit_input(f,{})
  self.assertTrue(any(i['code']=='FIGURE_ASSET_UNREGISTERED' and i['status']=='BLOCKED' for i in q['slides'][0]['issues']))
 def test_empty_context_text_has_no_figure_error(self):
  from pptx import Presentation
  import polish_presentation as pp
  prs=Presentation();prs.slides.add_slide(prs.slide_layouts[6]);f=self.d/'text.pptx';prs.save(f)
  q=pp.audit_input(f,{})
  self.assertFalse(any('FIGURE' in i['code'] for i in q['slides'][0]['issues']))
 def test_full_runs_deep_csv_and_ppt_checks(self):
  import validate_story as vs
  from pptx import Presentation
  for f in vs.FILES:(self.d/f).write_text('Figure 1 样本 实验 结果 下一 来源','utf-8')
  (self.d/'06_PPT页面数据.json').write_text(json.dumps({'slides':[{'kind':'framework'},{'kind':'figure'}]}),'utf-8')
  (self.d/'08_PPT模板适配与质检.md').write_text('qa','utf-8')
  prs=Presentation()
  for _ in range(3):prs.slides.add_slide(prs.slide_layouts[6])
  prs.save(self.d/'07_科研逻辑汇报.pptx')
  r=subprocess.run([sys.executable,str(Path(vs.__file__)),str(self.d),'--profile','full'],capture_output=True)
  self.assertNotEqual(r.returncode,0);self.assertIn('CSV缺少列'.encode(),r.stdout)
 def test_native_render_drift_rejected(self):
  from pptx import Presentation
  p=self.d/'empty.pptx';prs=Presentation();prs.slides.add_slide(prs.slide_layouts[6]);prs.save(p)
  self.assertEqual(dc.rendered_topology(str(p),'B'),(set(),set()))

 def valid_index(self):
  p=self.pdf();x=si.skeleton(dict(source_pdf=str(p),file_sha256=fa.sha(p),page_count=1));f=self.d/'span.txt';f.write_text('Actual source excerpt.','utf-8');txt=f.read_text('utf-8')
  src=dict(document_id='D',document_sha256=fa.sha(p),physical_page=1,path=str(f),sha256=fa.sha(f),start=0,end=len(txt),excerpt=txt,excerpt_sha256=hashlib.sha256(txt.encode()).hexdigest(),source_status='PARTIAL')
  x.update(reading_status='AVAILABLE_CONTENT_READ',methods_task_detection='COMPLETE_AVAILABLE',result_mapping_status='MAPPED_WITH_GAPS',article_type='original_research',reading_record=dict(actor='test fixture',basis=[dict(path=str(f),sha256=fa.sha(f))],scope='Synthetic contract test, not a real-paper extraction'),sources={'S':src},facets={k:dict(status='PARTIAL',text='Bound statement',sources=['S']) for k in si.FACETS});return x
 def test_completed_source_index(self):self.assertTrue(si.validate(self.valid_index())['valid'])
 def test_index_schema_rejects_bad_span_type(self):
  x=self.valid_index();x['sources']['S']['start']='0';self.assertFalse(si.validate(x)['valid'])
 def test_no_page_only_semantic_upgrade(self):
  x=self.valid_index();x['facets']['results']['status']='CHECKED';self.assertFalse(si.validate(x)['valid'])
 def test_reading_basis_drift(self):
  x=self.valid_index();x['reading_record']['basis'][0]['sha256']='0'*64;self.assertFalse(si.validate(x)['valid'])
 def test_graph_minimum_grows_available_card(self):
  import build_pptx as bp
  nodes=[dict(id='A',title='问题',detail='具体结果',figure_ref='Fig.1')]
  legacy=bp._graph_layout(nodes,[],10,4);large=bp._graph_layout(nodes,[],10,4,1.0)
  self.assertEqual(len(legacy),3);self.assertGreater(large[2],legacy[2])
 def test_actual_graph_slots_do_not_overlap(self):
  import build_pptx as bp
  from pptx import Presentation
  from pptx.util import Inches
  prs=Presentation();sl=prs.slides.add_slide(prs.slide_layouts[6]);area=sl.shapes.add_textbox(Inches(.3),Inches(.5),Inches(9),Inches(5));area.name='PFS_GRAPH_AREA'
  bp.render_argument_graph(sl,dict(nodes=[dict(id='A',title='研究问题',detail='比较对象与实际发现',figure_ref='Fig.1a')],edges=[]))
  t={s.name:s for s in sl.shapes}
  self.assertLessEqual(t['PFS_GRAPH_NODE_DETAIL'].top+t['PFS_GRAPH_NODE_DETAIL'].height,t['PFS_GRAPH_FIGREF'].top)
 def test_singular_figure_image_is_not_a_bypass(self):
  with self.assertRaisesRegex(ValueError,'REGISTRY_REQUIRED'):fa.validate_manifest_images({'slides':[dict(kind='figure',image='raw.png')]},self.d)

 def test_shared_method_native_node_is_conserved(self):
  from pptx import Presentation
  from pptx.util import Inches
  prs=Presentation();sl=prs.slides.add_slide(prs.slide_layouts[6]);t=sl.shapes.add_textbox(0,0,Inches(2),Inches(1));t.name='RC_LOGIC_B_LOGIC_B_SHARED_shared';t.text='Shared workflow, not independent evidence';p=self.d/'shared.pptx';prs.save(p)
  self.assertEqual(dc.rendered_topology(str(p),'B'),({'SHARED'},set()))

 def mapping_audit(self,reviewed,expected,asset_panels=None):
  from pptx import Presentation
  from pptx.util import Inches
  import polish_presentation as pp
  r=self.asset();a=r['assets'][0]
  if reviewed:a['panel_mapping_status']='CHECKED'
  prs=Presentation();sl=prs.slides.add_slide(prs.slide_layouts[6]);sl.shapes.add_picture(a['path'],0,0,width=Inches(2));t=sl.shapes.add_textbox(Inches(3),0,Inches(2),Inches(1));t.text='Fig.2c cited as background';p=self.d/'mapping.pptx';prs.save(p)
  c={'assets':[dict(sha256=a['sha256'],panels=asset_panels or ['1A'],panel_mapping_status='CHECKED')],'figure_registry':r,'slides':[dict(slide=1,expected_panels=expected)]}
  return {q['code'] for q in pp.audit_input(p,c)['slides'][0]['issues']}
 def test_citation_is_not_automatically_a_visible_panel(self):self.assertNotIn('PANEL_MAPPING_UNRESOLVED',self.mapping_audit(True,['1A']))
 def test_context_cannot_upgrade_pending_registry(self):self.assertIn('PANEL_MAPPING_UNRESOLVED',self.mapping_audit(False,['1A']))
 def test_empty_expected_cannot_waive_all_mapping(self):self.assertIn('PANEL_MAPPING_UNRESOLVED',self.mapping_audit(True,[],['all']))
if __name__=='__main__':unittest.main()

