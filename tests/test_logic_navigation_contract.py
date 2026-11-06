"""C1 real-artifact CLI regressions; set PFS_C1_CASE to an isolated built case.

No scientific answer or paper-specific relationship ID is encoded here. The
fixtures select identities from the supplied model and alter copies only.
"""
from pathlib import Path
import copy,json,os,sys,subprocess,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import research_logic as rl
from project_research_logic import directed_relation
from pptx import Presentation
from pptx.oxml.xmlchemy import OxmlElement

@unittest.skipUnless(os.environ.get('PFS_C1_CASE'),'PFS_C1_CASE is required for actual-file CLI contract tests')
class NativeNavigationCLI(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.case=Path(os.environ['PFS_C1_CASE']);cls.reg=rl.load(cls.case/'logic_graph_manifest.json');cls.model_path=Path(rl.load(cls.case/'lineage.json')['parent_model']);cls.model=rl.load(cls.model_path)
  cls.out=Path(os.environ.get('PFS_C1_TEST_OUTPUT',str(cls.case/'contract_tests')));cls.out.mkdir(exist_ok=False);cls.runs=[]
 def setUp(self):
  self.d=self.out/self._testMethodName;self.d.mkdir();self.g=copy.deepcopy(self.reg)
 def cli(self,ok,code=None):
  p=self.d/'graphs.json';p.write_text(json.dumps(self.g,ensure_ascii=False,indent=2),'utf8')
  cmd=[sys.executable,'-B',str(ROOT/'scripts/validate_story.py'),str(self.d),'--graph-manifest',str(p),'--logic-model',str(self.model_path),'--profile','full','--require-B']
  r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf8');(self.d/'stdout.log').write_text(r.stdout,'utf8');(self.d/'stderr.log').write_text(r.stderr,'utf8')
  self.runs.append(dict(test=self._testMethodName,command=cmd,exit_code=r.returncode));(self.out/'commands.json').write_text(json.dumps(self.runs,ensure_ascii=False,indent=2),'utf8')
  self.assertEqual(r.returncode,0 if ok else 1,r.stdout+r.stderr)
  if code:self.assertIn(code,r.stdout+r.stderr)
 def nav(self):return next(x for x in self.g['main_graphs'] if x['scope']=='overview_navigation')
 def main_copy(self):
  nav=self.nav();p=self.d/'Main.pptx';p.write_bytes(Path(nav['pptx']).read_bytes());ref=self.d/nav['full_b_reference']['path'];ref.write_bytes((Path(nav['pptx']).parent/ref.name).read_bytes());return p
 def replace_main(self,p):
  for g in self.g['main_graphs']:g['pptx']=str(p);g['pptx_sha256']=rl.file_sha(p)
 def mutate_edge(self,mutation):
  p=self.main_copy();prs=Presentation(p);eid=next(e['id'] for e in self.model['edges'] if e['type']=='complements' and e['identity']=='SCIENTIFIC_EVIDENCE')
  shapes=[]
  for sl in prs.slides:
   for s in sl.shapes:
    if not s._element.tag.endswith('cxnSp'):continue
    cn=s._element.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr');d=json.loads(cn.get('descr','{}')) if cn is not None else {}
    if d.get('logic_edge')==eid:shapes.append(s)
  target=next(s for s in shapes if s._element.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}tailEnd') is not None);mutation(target);prs.save(p);self.replace_main(p)
 def test_01_real_navigation_local_complete_B(self):self.cli(True)
 def test_02_complete_B_is_required(self):
  self.g['graphs']=[g for g in self.g['graphs'] if g['view']!='B'];self.cli(False,'COMPLETE_B_REQUIRED')
 def test_03_complete_B_topology_loss(self):
  b=next(g for g in self.g['graphs'] if g['view']=='B');b['edge_ids'].pop();self.cli(False,'B_TOPOLOGY_LOSS')
 def test_04_A_cannot_masquerade_as_B_overview(self):
  self.g['main_graphs']=[g for g in self.g['main_graphs'] if g['scope']!='overview_navigation'];a=next(g for g in self.g['main_graphs'] if g['view']=='A');a.update(scope='overview',parent_canvas=next(g['id'] for g in self.g['graphs'] if g['view']=='B'));self.cli(False,'FALSE_B_OVERVIEW')
 def test_05_omission_set_cannot_hide_actual_relations(self):
  nav=self.nav();nav['edge_ids'].pop();self.cli(False,'NAVIGATION_VISIBLE_SET_DRIFT')
 def test_06_unexplained_cross_branch_omission_rejected(self):
  main=self.g['main_graphs'];core=set(self.model['core']['edges']);cross=next(g for g in main if g.get('placement')=='main' and set(g['edge_ids'])-core and any(self.model['edges'][i]['type']=='shared_workflow' for i in range(len(self.model['edges'])) if self.model['edges'][i]['id'] in g['edge_ids']))
  main.remove(cross);self.nav()['main_slides'].remove(cross['main_slide']);self.cli(False,'NAVIGATION_OMISSION_DRIFT')
 def test_07_bad_full_B_link_rejected(self):
  self.nav()['full_b_reference']['path']='missing.pptx';self.cli(False,'NAVIGATION_FILE_UNREADABLE')
 def test_08_false_full_B_hash_rejected(self):
  self.nav()['full_b_reference']['sha256']='0'*64;self.cli(False,'FULL_B_REFERENCE_INVALID')
 def test_09_directed_evidence_arrow_missing(self):
  self.mutate_edge(lambda s:s._element.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}tailEnd').set('type','none'));self.cli(False,'NATIVE_DIRECTION_DRIFT')
 def test_10_reverse_arrow_rejected(self):
  def reverse(s):
   s._element.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}tailEnd').set('type','none');a=OxmlElement('a:headEnd');a.set('type','triangle');s._element.spPr.get_or_add_ln().append(a)
  self.mutate_edge(reverse);self.cli(False,'NATIVE_DIRECTION_DRIFT')
 def test_11_wrong_endpoint_rejected(self):
  self.mutate_edge(lambda s:setattr(s,'end_x',s.end_x+2500000));self.cli(False,'NATIVE_ENDPOINT_DRIFT')
 def test_12_shared_workflow_must_stay_undirected(self):
  p=self.main_copy();prs=Presentation(p);eid=next(e['id'] for e in self.model['edges'] if e['type']=='shared_workflow');found=False
  for sl in prs.slides:
   for s in sl.shapes:
    if not s._element.tag.endswith('cxnSp'):continue
    cn=s._element.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr');d=json.loads(cn.get('descr','{}')) if cn is not None else {}
    if d.get('logic_edge')==eid:
     a=OxmlElement('a:tailEnd');a.set('type','triangle');s._element.spPr.get_or_add_ln().append(a);found=True
  self.assertTrue(found);prs.save(p);self.replace_main(p);self.cli(False,'NATIVE_DIRECTION_DRIFT')
 def test_13_main_node_font_gate_not_lowered(self):
  from pptx.util import Pt
  p=self.main_copy();prs=Presentation(p);sl=prs.slides[next(g['main_slide'] for g in self.g['main_graphs'] if g.get('placement')=='main')-1];s=next(s for s in sl.shapes if s.name.endswith('_body') and s.has_text_frame);s.text_frame.paragraphs[0].runs[0].font.size=Pt(7);prs.save(p);self.replace_main(p);self.cli(False,'MAIN_VISUAL_CAPACITY_LIMIT')
 def test_14_B_detail_text_cannot_silently_disappear(self):
  g=next(g for g in self.g['graphs'] if g['view']=='B');p=self.d/'B.pptx';prs=Presentation(g['pptx']);s=next(s for s in prs.slides[0].shapes if s.name.endswith('_body') and s.has_text_frame);s.text='truncated';prs.save(p);g['pptx']=str(p);g['pptx_sha256']=rl.file_sha(p);self.cli(False,'B_DETAIL_TEXT_LOSS')
 def test_15_source_descriptor_tamper_rejected(self):
  p=self.main_copy();prs=Presentation(p);s=next(s for sl in prs.slides for s in sl.shapes if s.name.endswith('_body') and s.has_text_frame);cn=s._element.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr');d=json.loads(cn.get('descr'));d['source_node_ids']=['invented'];cn.set('descr',json.dumps(d));prs.save(p);self.replace_main(p);self.cli(False,'NATIVE_SOURCE_DRIFT')
 def test_16_uncertain_complement_parallel_comparison_no_causal_arrow(self):
  for kind,identity in [('parallel','SCIENTIFIC_EVIDENCE'),('comparison','SCIENTIFIC_EVIDENCE'),('complements','AUTHOR_ARGUMENT'),('shared_workflow','SHARED_PROTOCOL')]:self.assertFalse(directed_relation(dict(type=kind,identity=identity)))
 def test_17_navigation_parent_not_arbitrary(self):
  self.nav()['parent_canvas']='invented';self.cli(False,'COMPLETE_B_REQUIRED')
 def test_18_stale_snapshot_rejected(self):
  self.nav()['logic_snapshot']='stale';self.cli(False,'DELIVERY_MODEL_DRIFT')
 def test_19_raster_overlay_cannot_impersonate_native_network(self):
  from pptx.util import Inches
  p=self.main_copy();prs=Presentation(p);n=next(g['main_slide'] for g in self.g['main_graphs'] if g.get('placement')=='main');prs.slides[n-1].shapes.add_picture(self.g['graphs'][0]['png'],0,0,width=Inches(12));prs.save(p);self.replace_main(p);self.cli(False,'RASTER_LOGIC_REPLACEMENT')
 def test_20_explicit_limited_scope_omissions_can_be_audited(self):
  # A software-only limited-scope fixture, not a proposed omission from the real
  # delivery. Full B and the core remain intact, and no success flag is injected.
  shared=next(e['id'] for e in self.model['edges'] if e['type']=='shared_workflow')
  row=next(g for g in self.g['main_graphs'] if g.get('placement')=='main' and shared in g['edge_ids'])
  p=self.main_copy();prs=Presentation(p);sl=prs.slides[row['main_slide']-1]
  for s in list(sl.shapes):
   if s.name.startswith('RC_'):sl.shapes._spTree.remove(s._element)
  prs.save(p);self.g['main_graphs'].remove(row);self.g['graphs']=[g for g in self.g['graphs'] if g['view']!=row['view']]
  main=[g for g in self.g['main_graphs'] if g.get('placement')=='main'];nav=self.nav();visible=set().union(*(set(g['edge_ids']) for g in main));omitted={e['id'] for e in self.model['edges']}-visible
  self.assertTrue(omitted);self.assertFalse(omitted&set(self.model['core']['edges']))
  nav.update(node_ids=sorted(set().union(*(set(g['node_ids']) for g in main))),edge_ids=sorted(visible),main_slides=[g['main_slide'] for g in main],omitted_edge_ids=sorted(omitted),omitted_edges={e:'有限展示范围软件测试；此关系仅在完整B中呈现，保留来源及科学限制。' for e in omitted})
  self.replace_main(p);self.cli(True)
if __name__=='__main__':unittest.main()
