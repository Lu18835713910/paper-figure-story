"""Source-bound synthetic recovery; never reads a blind-test paper or real case."""
from pathlib import Path
import copy, importlib.util, json, subprocess, sys, tempfile, unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import display_guidance as dg, project_evidence_products as pp, project_research_logic as pj
import research_logic as rl, run_pfs, evidence_network as en
spec=importlib.util.spec_from_file_location('a_example',ROOT/'examples/a_overview_guidance/make_synthetic_example.py')
ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex)

class OverviewRecovery(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.f=ex.make(self.root/'source');self.n=rl.load(self.f['network']);self.g=rl.load(self.f['guidance']);self.m=rl.load(self.f['logic'])
  self.meta=rl.load(self.f['metadata']);self.template=dict(path=str(ROOT/'assets/default_academic_blue_174994.pptx'),sha256=rl.file_sha(ROOT/'assets/default_academic_blue_174994.pptx'))
 def cli(self,name,*extra,f=None):
  f=f or self.f
  return subprocess.run([sys.executable,'-B',str(ROOT/'scripts/run_pfs.py'),'run','--pdf',f['pdf'],'--knowledge',f['knowledge'],'--cache-dir',f['cache'],'--metadata',f['metadata'],'--outdir',str(self.root/name),'--products','with-network','--plan-only',*extra],capture_output=True,text=True,encoding='utf-8')
 def plan(self,meta=None):return pp.project_products(self.n,'balanced',meta or self.meta,self.template,dict(scope='with-network',report_sections=True))
 def with_logic(self):return {**self.meta,'research_logic':dict(path=self.f['logic'],sha256=rl.file_sha(self.f['logic']))}
 def test_old_small_cli_path_keeps_working(self):
  f=ex.make(self.root/'small',2);r=self.cli('small_run',f=f);self.assertEqual(r.returncode,0,r.stderr)
 def test_over_capacity_cli_error_has_action_and_keeps_gate(self):
  r=self.cli('plain');self.assertEqual(r.returncode,2)
  for x in ['A_NEEDS_GUIDANCE','capacity 6','--research-logic','--guidance','a_overview_recovery.md','NEW --outdir']:self.assertIn(x,r.stderr)
  self.assertFalse((self.root/'plain/balanced/products.plan.json').exists())
 def test_explicit_cli_uses_validated_logic_before_default_A_or_B(self):
  r=self.cli('explicit','--research-logic',self.f['logic']);self.assertEqual(r.returncode,0,r.stderr)
  p=rl.load(self.root/'explicit/balanced/products.plan.json');a=next(s for s in p['products'][0]['slides'] if s['id']=='LOGIC_A');b=next(x for x in p['products'] if x['kind']=='detail')
  self.assertTrue(pj.validate_AB(self.m,dict(slides=[a]),b)['valid']);self.assertTrue(pp.validate_products(self.n,p,self.with_logic())['valid'])
  with patch.object(pp,'overview',side_effect=AssertionError('discarded default A called')),patch.object(pp,'detailed',side_effect=AssertionError('discarded default B called')):self.plan(self.with_logic())
 def test_guidance_cli_retains_all_registered_claims_and_source_B(self):
  r=self.cli('guided','--guidance',self.f['guidance']);self.assertEqual(r.returncode,0,r.stderr)
  p=rl.load(self.root/'guided/balanced/products.plan.json');a=next(s for s in p['products'][0]['slides'] if s['id']=='A_overview');b=next(x for x in p['products'] if x['kind']=='detail')['slides'][0]
  self.assertTrue({'C'+str(i) for i in range(1,8)}<=set(a['source_node_ids']))
  self.assertEqual(set(b['source_node_ids']),{n['id'] for n in self.n['nodes']});self.assertEqual(set(b['source_relation_ids']),{e['id'] for e in self.n['edges']})
  self.assertEqual(p['products'][0]['summary_coverage']['omitted_claims'],{})
 def test_bad_guidance_rejected_by_real_cli(self):
  self.g['records'][0]['source_statement_ids']=['UNKNOWN'];bad=self.root/'bad.json';ex.save(bad,self.g)
  r=self.cli('bad','--guidance',str(bad));self.assertEqual(r.returncode,2);self.assertIn('GUIDANCE_UNKNOWN_STATEMENT',r.stderr)
 def test_invalid_logic_never_falls_back_to_default(self):
  self.m['nodes'][0]['source_ids']=[];self.m['snapshot']=rl.snapshot(self.m);bad=self.root/'bad_logic.json';ex.save(bad,self.m)
  r=self.cli('bad_logic','--research-logic',str(bad));self.assertEqual(r.returncode,2);self.assertIn('NODE_WITHOUT_SOURCE',r.stderr);self.assertNotIn('A_NEEDS_GUIDANCE',r.stderr)
 def test_duplicate_record_rejected(self):
  self.g['records'].append(copy.deepcopy(self.g['records'][0]))
  with self.assertRaisesRegex(ValueError,'GUIDANCE_DUPLICATE_RECORD'):dg.validate_guidance(self.n,self.g)
 def test_duplicate_overview_node_rejected(self):
  self.g['overview']['nodes'].append(copy.deepcopy(self.g['overview']['nodes'][0]))
  with self.assertRaisesRegex(ValueError,'GUIDANCE_DUPLICATE_NODE'):dg.validate_guidance(self.n,self.g)
 def test_duplicate_overview_edge_rejected(self):
  self.g['overview']['edges'].append(copy.deepcopy(self.g['overview']['edges'][0]))
  with self.assertRaisesRegex(ValueError,'GUIDANCE_DUPLICATE_EDGE'):dg.validate_guidance(self.n,self.g)
 def test_missing_source_and_wrong_span_rejected(self):
  for what in ['missing','span','cache']:
   g=copy.deepcopy(self.g);r=g['records'][0]
   if what=='missing':r.update(source_statement_ids=[],source_spans=[])
   elif what=='span':r['source_spans'][0]['start']+=1
   else:r['source_spans'][0]['path']=str(self.root/'not_registered/page-01.txt')
   with self.assertRaises(ValueError):dg.validate_guidance(self.n,g)
 def test_aggregate_cannot_claim_unmatched_registered_relation(self):
  e=self.g['overview']['edges'][0];e.update(identity='scientific_registered',type='evidence_supports',source_relation_id='SUP1')
  with self.assertRaisesRegex(ValueError,'GUIDANCE_RELATION_ENDPOINT_BINDING'):dg.validate_guidance(self.n,self.g)
 def test_display_parallel_cannot_become_data_dependency(self):
  self.g['overview']['edges'][0]['type']='data_depends_on'
  with self.assertRaisesRegex(ValueError,'GUIDANCE_RELATION_ESCALATION'):dg.validate_guidance(self.n,self.g)
 def test_shared_observation_preserves_one_scientific_identity(self):
  before=copy.deepcopy(self.n);p=self.plan(self.with_logic());self.assertEqual(self.n,before)
  self.assertEqual(sum(n['id']=='E1' for n in self.n['nodes']),1)
  self.assertEqual({e['to'] for e in self.n['edges'] if e['from']=='E1'},{'C1','C2'})
  self.assertTrue(all(not e.get('independent_validation',False) for e in self.m['edges']))
  self.assertTrue(all(e['type']=='question_fork' and e['identity']=='AUTHOR_ARGUMENT' and not e.get('causal_claim') for e in self.m['edges']))
  self.assertFalse(any(e['type'] in ['data_depends_on','experimental_precedes','independent_validation'] for e in self.n['edges']))
 def test_model_sources_and_spans_are_real_cache_substrings(self):
  self.assertTrue(en.validate_network(self.n,verify_files=True)['valid']);self.assertTrue(rl.validate_model(self.m,self.n)['valid'])
  text=Path(self.f['cache'],'page-01.txt').read_text('utf-8')
  for r in self.g['records']:
   for s in r['source_spans']:self.assertEqual(text[s['start']:s['end']],s['text'])
  self.assertFalse(self.m['formal_ready'])
 def test_explicit_layout_capacity_is_not_bypassed(self):
  self.m['layout']['A']['positions']['G1'][3]=30
  with self.assertRaisesRegex(ValueError,'LOGIC_TEXT_FIT'):pj.build_scene(self.n,self.m,'A')
 def test_native_logic_still_contains_real_nodes_and_edges(self):
  import render_logic as rr, delivery_contract as dc
  from pptx import Presentation
  product=pj.build_scene(self.n,self.m,'A');p=Presentation();p.slide_width=1280*9525;p.slide_height=720*9525;s=p.slides.add_slide(p.slide_layouts[6]);rr.draw_scene(s,product,product['slides'][0]);out=self.root/'native.pptx';p.save(out)
  self.assertEqual(dc.rendered_topology(out,'A'),(set(self.m['core']['nodes']),set(self.m['core']['edges'])))

if __name__=='__main__':unittest.main()
