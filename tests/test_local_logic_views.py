"""Local display subsets, not new scientific nodes. Uses self-authored source fixtures."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_workbook_reuse import fixture,save
import research_logic as rl,project_research_logic as pj,delivery_contract as dc
from pptx import Presentation
import render_logic as renderer

class LocalViews(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name);self.f=fixture(self.p);self.m=self.f['model']
  self.v=dict(title='登记事实的局部展示',parent_view='B',logic_snapshot=self.m['snapshot'],node_ids=['Q','N'],edge_ids=['R'],node_fields={'Q':['short_text'],'N':['short_text']},layout=dict(width=1280,height=720,positions={'Q':[60,100,1160,130],'N':[60,350,1160,240]},routes={'R':dict(points=[[640,230],[640,350]],label_position=[700,260,300,40])}))
  self.d=dict(logic_snapshot=self.m['snapshot'],formal_ready=False,views={'sample':self.v})
 def read(self):
  p=self.p/'display.json';save(p,self.d);return pj.read_display(self.m,{'logic_display':dict(path=str(p),sha256=rl.file_sha(p))})
 def scene(self):return pj.build_scene(self.f['net'],self.m,'sample',self.read())
 def test_non_atera_native_local_view(self):
  product=self.scene();s=product['slides'][0];self.assertEqual(s['source_logic_node_ids'],['Q','N']);self.assertEqual(s['source_logic_relation_ids'],['R']);self.assertEqual(s['coverage']['scope'],'local');self.assertEqual(s['coverage']['parent_view'],'B');self.assertEqual(s['coverage']['new_M1_entities'],0)
  p=Presentation();p.slide_width=1280*9525;p.slide_height=720*9525;sl=p.slides.add_slide(p.slide_layouts[6]);renderer.draw_scene(sl,product,s);out=self.p/'native.pptx';p.save(out)
  self.assertEqual(dc.rendered_topology(out,'sample'),({'Q','N'},{'R'}));self.assertTrue(dc.validate_main_views(self.m,out,[dict(view='sample',slide=1)],dict(products=[product]))['valid'])
 def test_unknown_node_rejected(self):
  self.v['node_ids'].append('UNKNOWN')
  with self.assertRaisesRegex(ValueError,'LOCAL_NODE_ID'):self.read()
 def test_unknown_edge_rejected(self):
  self.v['edge_ids'].append('UNKNOWN')
  with self.assertRaisesRegex(ValueError,'LOCAL_EDGE_ID'):self.read()
 def test_missing_endpoint_rejected(self):
  self.v['node_ids']=['Q']
  with self.assertRaisesRegex(ValueError,'LOCAL_EDGE_ENDPOINT'):self.read()
 def test_old_snapshot_rejected(self):
  self.v['logic_snapshot']='old'
  with self.assertRaisesRegex(ValueError,'LOCAL_VIEW_IDENTITY'):self.read()
 def test_wrong_parent_rejected(self):
  self.v['parent_view']='A'
  with self.assertRaisesRegex(ValueError,'LOCAL_VIEW_IDENTITY'):self.read()
 def test_local_cannot_impersonate_B(self):
  self.d['views']={'B':self.v}
  with self.assertRaisesRegex(ValueError,'LOCAL_VIEW_IDENTITY'):self.read()
 def test_local_cannot_override_relation_direction(self):
  self.v['edges']=[dict(id='R',**{'from':'N','to':'Q'})]
  with self.assertRaisesRegex(ValueError,'LOCAL_VIEW_IDENTITY'):self.read()
 def test_wrong_geometric_endpoint_rejected(self):
  self.v['layout']['routes']['R']['points'][-1]=[100,100]
  with self.assertRaisesRegex(ValueError,'LOCAL_ROUTE_ENDPOINT'):self.read()
 def test_custom_scientific_text_not_allowed(self):
  self.v['node_fields']['N']=['new_claim']
  with self.assertRaisesRegex(ValueError,'LOCAL_FIELD_REFERENCE'):self.read()
 def test_legacy_branches_still_work(self):
  m=copy.deepcopy(self.m);m['branches']=[dict(id='legacy',title='历史支线',nodes=['Q','N'],edges=['R'])];m['layout']['legacy']=copy.deepcopy(self.v['layout'])
  s=pj.build_scene(self.f['net'],m,'legacy')['slides'][0];self.assertEqual(s['source_logic_relation_ids'],['R']);self.assertNotIn('scope',s['coverage'])
 def test_registered_display_facts_cannot_be_replaced(self):
  self.d['nodes']={'N':dict(method='原方法',source_ids=['S'])};base=self.p/'base.json';save(base,self.d);self.d['base_display']=dict(path=str(base),sha256=rl.file_sha(base));self.d['nodes']['N']['method']='新编事实'
  with self.assertRaisesRegex(ValueError,'LOCAL_DISPLAY_FACT_OVERRIDE'):self.read()
 def test_subset_B_cannot_pass_delivery(self):
  row=dict(id='b',view='B',scope='complete',logic_snapshot=self.m['snapshot'],node_ids=['Q'],edge_ids=[])
  self.assertIn('B_TOPOLOGY_LOSS',dc.validate_delivery(self.m,[row],verify_files=False)['errors'])
 def test_native_checks_reject_unknown_and_old_scene(self):
  product=self.scene();s=product['slides'][0];s['logic_snapshot']='old';s['source_logic_node_ids']+=['fake']
  with patch.object(dc,'main_model_audit',return_value={'errors':[]}):
   q=dc.validate_main_views(self.m,'not-opened',[dict(view='sample',slide=1)],dict(products=[product]));self.assertIn('MAIN_VIEW_UNKNOWN_ID',q['errors']);self.assertIn('MAIN_VIEW_MODEL_DRIFT',q['errors'])
 def test_omission_register_required(self):
  product=self.scene();s=product['slides'][0];s['coverage']['omitted_edge_ids']=['R']
  with patch.object(dc,'main_model_audit',return_value={'errors':[]}),patch.object(dc,'rendered_topology',return_value=({'Q','N'},{'R'})):
   self.assertIn('LOCAL_OMISSION_DRIFT',dc.validate_main_views(self.m,'fixture',[dict(view='sample',slide=1)],dict(products=[product]))['errors'])
 def test_explicit_main_view_requirement_not_ignored(self):
  with patch.object(dc,'main_model_audit',return_value={'errors':[]}):
   q=dc.validate_delivery(self.m,[],requested_B=True,verify_files=True,main_views=['sample']);self.assertIn('PLANNED_MAIN_NATIVE_VIEWS_MISSING',q['errors'])

if __name__=='__main__':unittest.main()
