"""V2 safety regression; self-authored demo only, no PDF or Office rendering."""
from pathlib import Path
import copy,sys,tempfile,unittest
from unittest.mock import patch
from lxml import etree as E
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import polish_presentation as v
import visual_polish_locked as L

class ContentLockedPolish(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.src=self.root/'original.pptx';self.src.write_bytes((Path(__file__).resolve().parents[1]/'examples/layout_demo.pptx').read_bytes());self.data=v.package(self.src);self.parts=v.active_parts(self.data);self.lock=L.snapshot(self.src);root=v.xml(self.data,self.parts[0]);self.sid=next(v.shape_id(q) for q in root.find('p:cSld/p:spTree',v.NS) if v.shape_text(q));self.words=v.shape_text(v.top_shape(root,self.sid))
 def tearDown(self):self.tmp.cleanup()
 def change(self,fn):
  d=copy.deepcopy(self.data);fn(d);p=self.root/'changed.pptx';L.dump(p,d);return L.compare(self.lock,L.snapshot(p))
 def shape_change(self,d,fn):
  r=v.xml(d,self.parts[0]);fn(v.top_shape(r,self.sid));v.put(d,self.parts[0],r)
 def design(self):return dict(slide=1,original_png_sha256='p',current_visual_problem='list',primary_existing_information='same content',layout='local',space_allocation='same page',emphasis='existing result',immutable_content='all',expected_improvement='hierarchy',shapes=[])
 def plan(self):return dict(version=L.VERSION,input_sha256=v.digest(self.src),content_lock_sha256=v.fingerprint(self.lock),designer='Agent',pages=[self.design()])
 def test_01_geometry_only(self):self.assertTrue(self.change(lambda d:self.shape_change(d,lambda q:L.setpos(q,[1,1,8,1])))['valid'])
 def test_02_text_change_blocked(self):self.assertFalse(self.change(lambda d:self.shape_change(d,lambda q:q.find('.//a:t',v.NS).__setattr__('text','UNPLANNED 99%')) )['valid'])
 def test_03_object_deletion(self):
  def f(d):r=v.xml(d,self.parts[0]);r.find('p:cSld/p:spTree',v.NS).remove(v.top_shape(r,self.sid));v.put(d,self.parts[0],r)
  self.assertFalse(self.change(f)['valid'])
 def test_04_page_order(self):
  def f(d):
   r=v.xml(d,'ppt/presentation.xml');ids=r.find('p:sldIdLst',v.NS);q=ids[0];ids.remove(q);ids.append(q);v.put(d,'ppt/presentation.xml',r)
  self.assertFalse(self.change(f)['valid'])
 def test_05_page_count(self):
  def f(d):
   r=v.xml(d,'ppt/presentation.xml');ids=r.find('p:sldIdLst',v.NS);ids.remove(ids[1]);v.put(d,'ppt/presentation.xml',r)
  self.assertFalse(self.change(f)['valid'])
 def test_06_hidden_membership(self):
  def f(d):r=v.xml(d,self.parts[0]);r.set('show','0');v.put(d,self.parts[0],r)
  self.assertFalse(self.change(f)['valid'])
 def test_07_notes(self):
  def f(d):
   p=v.notes_part(d,self.parts[0]);r=v.xml(d,p);r.find('.//a:t',v.NS).text='new scientific inference';v.put(d,p,r)
  self.assertFalse(self.change(f)['valid'])
 def test_08_reflow_preserves_characters(self):
  self.assertTrue(self.change(lambda d:self.shape_change(d,lambda q:L.text_style(q,{},[self.words[:3],self.words[3:]])))['valid'])
 def test_09_cannot_rewrite_by_reflow(self):
  with self.assertRaisesRegex(v.PolishError,'REFLOW_CHANGES'):L.text_style(v.top_shape(v.xml(self.data,self.parts[0]),self.sid),{},['invented'])
 def test_10_font_shrink_blocked(self):
  with self.assertRaisesRegex(v.PolishError,'FONT_SHRINK'):L.text_style(v.top_shape(v.xml(self.data,self.parts[0]),self.sid),dict(font_size=1))
 def test_11_context(self):
  s=copy.deepcopy(self.lock);s['context_sha256']='different';self.assertFalse(L.compare(self.lock,s)['valid'])
 def test_12_requires_agent(self):
  p=self.plan();p['designer']='none'
  with self.assertRaisesRegex(v.PolishError,'AGENT_DESIGN'):L.validate_plan(p,self.src,self.lock,dict(rendered=[dict(slide=1,png_sha256='p')]))
 def test_13_requires_actual_preview(self):
  with self.assertRaisesRegex(v.PolishError,'ACTUAL_DESIGN_PREVIEW'):L.validate_plan(self.plan(),self.src,self.lock,None)
 def test_14_forbids_upstream(self):
  p=self.plan();p['upstream_responses']=['new']
  with self.assertRaisesRegex(v.PolishError,'UPSTREAM_FORBIDDEN'):L.validate_plan(p,self.src,self.lock,dict(rendered=[dict(slide=1,png_sha256='p')]))
 def test_15_old_plan_version_rejected(self):
  p=self.plan();p['version']='pfs-visual-polish-1'
  with self.assertRaisesRegex(v.PolishError,'LOCKED_PLAN_VERSION'):L.validate_plan(p,self.src,self.lock,None)
 def test_16_legacy_mutation_blocked(self):
  for k in ['insert_table_slide','backup','replace_image','replace_text','add_text','narrative']:
   with self.subTest(k=k),self.assertRaisesRegex(v.PolishError,'LEGACY_CONTENT_MUTATION_DISABLED'):v.mutate({}, {}, [], dict(kind=k),{},0)
 def test_17_old_entry_blocked(self):
  with self.assertRaisesRegex(v.PolishError,'LEGACY_CONTENT_MUTATION_DISABLED'):v._legacy_polish(self.src,self.root/'bad')
 def test_18_no_plan_only_qa(self):
  r=v.polish(self.src,self.root/'qa',renderer='none');self.assertEqual(r['status'],'QA_ONLY');self.assertEqual(r['design_mode'],'QA_ONLY');self.assertEqual(r['USER_ACCEPTANCE'],'PENDING');self.assertFalse(r['actual_powerpoint_export'])
 def test_19_content_issue_not_resolved(self):
  ctx={'slides':[dict(slide=1,required_content=[dict(id='x',phrases=['missing experiment'])])]};r=v.polish(self.src,self.root/'qa',renderer='none',context=ctx);self.assertEqual(r['upstream_requests'][0]['code'],'UPSTREAM_CONTENT_ISSUE');self.assertTrue(L.compare(self.lock,L.snapshot(r['output']))['valid'])
 def test_20_unsafe_page_rollback(self):
  p=self.plan();p['pages'][0]['shapes']=[dict(shape_id=self.sid,reflow=['invented'])];before=dict(input_sha256=v.digest(self.src),source_unchanged=True,rendered=[dict(slide=1,png='dummy',png_sha256='p',issues=[])])
  with patch.object(v,'render',return_value=before),patch('shutil.copy2'):r=v.polish(self.src,self.root/'rollback',plan=p)
  self.assertTrue(r['failed_actions']);self.assertTrue(L.compare(self.lock,L.snapshot(r['output']))['valid'])
 def test_21_route_requires_original_edge(self):
  with self.assertRaisesRegex(v.PolishError,'ROUTE_NOT_EXISTING'):L.redraw(copy.deepcopy(self.data),self.parts[0],dict(slide=1,routes=[dict(shape_ids=[self.sid],points=[[1,1],[3,3]])]),{})
 def test_22_source_original_unchanged(self):
  h=v.digest(self.src);r=v.polish(self.src,self.root/'qa',renderer='none');self.assertEqual(h,v.digest(self.src));self.assertTrue(all(v.package(r['output'])[k]==b for k,b in self.data.items()))
 def test_23_arrow_identity_detected(self):
  a=copy.deepcopy(self.lock);a['slides'][0]['objects'][0]['edge']={'reversed':True};self.assertFalse(L.compare(self.lock,a)['valid'])
 def test_24_decoration_only(self):self.assertTrue(self.change(lambda d:L.redraw(d,self.parts[0],dict(slide=1,decorations=[dict(id='wash',position=[1,1,2,2],fill='EDF3FC')]),{}))['valid'])
 def test_25_rewrite_drawingml_order(self):
  q=v.top_shape(v.xml(self.data,self.parts[0]),self.sid);L.style_shape(q,dict(fill='FFFFFF',line='174994'));L.canonical_styles(q);tags=[E.QName(x).localname for x in q.find('p:spPr',v.NS)];self.assertLess(tags.index('solidFill'),tags.index('ln'))
 def test_26_output_overwrite_refused(self):
  v.polish(self.src,self.root/'qa',renderer='none')
  with self.assertRaisesRegex(v.PolishError,'OUTPUT_EXISTS'):v.polish(self.src,self.root/'qa',renderer='none')

if __name__=='__main__':unittest.main(verbosity=2)
