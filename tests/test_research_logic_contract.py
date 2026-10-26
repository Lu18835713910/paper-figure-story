"""Portable synthetic contract tests; these are not real-paper extraction tests."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import research_logic as rl

class LogicContract(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  def save(name,obj):
   p=self.root/name;p.write_text(json.dumps(obj,ensure_ascii=False),'utf-8');return {'path':str(p),'sha256':rl.file_sha(p)}
  self.save=save
  text=self.root/'page.txt';text.write_text('A reported observation and an explicitly limited interpretation.','utf-8');txt=text.read_text('utf-8')
  self.net={'snapshot':'synthetic-source','paper':{'id':'SYN','paper_type':'original_research','documents':[{'id':'DOC','sha256':'pdf-fingerprint','physical_page_count':1}]},'nodes':[{'id':'P'},{'id':'Q'}],'statements':[{'id':'S'}],'edges':[{'id':'ORDER','from':'P','to':'Q','type':'experimental_precedes'}]}
  self.index={'reading_status':'AVAILABLE_CONTENT_READ','methods_task_detection':'COMPLETE_AVAILABLE','result_mapping_status':'MAPPED_WITH_GAPS','article_type':'original_research','facets':{k:{} for k in ['background_gap','core_question','hypotheses','tasks','purpose','materials','groups_controls','conditions','methods','results','author_interpretation','limitations']}}
  source={'document_id':'DOC','document_sha256':'pdf-fingerprint','physical_page':1,'path':str(text),'sha256':rl.file_sha(text),'start':0,'end':len(txt),'excerpt':txt,'excerpt_sha256':__import__('hashlib').sha256(txt.encode()).hexdigest()}
  nodes=[dict(id=i,identity='SCIENTIFIC_EVIDENCE',review_status='PARTIAL',source_ids=['SRC'],source_entity_ids=[e],statement_ids=['S'],field_bindings=[]) for i,e in [('N1','P'),('N2','Q')]]
  edge=dict(id='E',**{'from':'N1','to':'N2'},type='progression',identity='AUTHOR_ARGUMENT',source_ids=['SRC'],review_status='PARTIAL',rationale='Explicitly sourced argument, not a time sequence.',alternatives='Could reflect presentation order; no causal claim.')
  self.m={'version':rl.VERSION,'formal_ready':False,'network_snapshot':self.net['snapshot'],'inputs':{'network':save('network.json',self.net),'scientific_index':save('index.json',self.index)},'sources':{'SRC':source},'nodes':nodes,'edges':[edge],'core':{'nodes':['N1','N2'],'edges':['E']},'branches':[],'method_explanations':[]}
  self.seal()
 def seal(self):self.m['snapshot']=rl.snapshot(self.m)
 def codes(self):self.seal();return {e['code'] for e in rl.validate_model(self.m)['errors']}
 def test_valid_source_bound_argument(self):self.assertTrue(rl.validate_model(self.m)['valid'])
 def test_snapshot_drift(self):self.m['nodes'][0]['id']='changed';self.assertIn('LOGIC_DRIFT',{e['code'] for e in rl.validate_model(self.m)['errors']})
 def test_unsourced_node_rejected(self):self.m['nodes'][0]['source_ids']=[];self.assertIn('NODE_WITHOUT_SOURCE',self.codes())
 def test_hypothesis_cannot_be_evidence(self):self.m['edges'][0].update(type='hypothesizes',identity='SCIENTIFIC_EVIDENCE');self.assertIn('HYPOTHESIS_IDENTITY',self.codes())
 def test_argument_cannot_be_causal(self):self.m['edges'][0]['causal_claim']=True;self.assertIn('UNSUPPORTED_CAUSAL_UPGRADE',self.codes())
 def test_shared_is_not_independent(self):self.m['edges'][0].update(type='shared_workflow',identity='SHARED_PROTOCOL',independent_validation=True);self.assertIn('SHARED_IS_NOT_VALIDATION',self.codes())
 def test_time_order_needs_matching_registered_endpoints(self):
  self.m['edges'][0].update(type='protocol_order',identity='ACTUAL_PROTOCOL_ORDER',registered_relation_id='ORDER')
  self.assertTrue(rl.validate_model({**self.m,'snapshot':rl.snapshot(self.m)})['valid'])
  self.m['edges'][0].update({'from':'N2','to':'N1'});self.assertIn('PROTOCOL_ORDER_ENDPOINT_MISMATCH',self.codes())
 def test_reading_before_planning(self):
  self.index['reading_status']='NOT_READ';self.m['inputs']['scientific_index']=self.save('index.json',self.index);self.assertIn('READING_FIRST_REQUIRED',self.codes())
 def test_source_span_is_not_semantic_pass(self):
  r=rl.validate_model(self.m);self.assertEqual(r['source_location'],'FILE_AND_SPAN_ONLY');self.assertEqual(r['scientific_review'],'PARTIAL');self.assertFalse(r['formal_ready'])
 def test_B_members_compress_without_new_entities(self):
  self.m['nodes'].append({**copy.deepcopy(self.m['nodes'][0]),'id':'CHILD','parent_id':'N1'})
  r=rl.compress_to_core(self.m,['N1','N2','CHILD'],['E']);self.assertEqual(r,{'nodes':['N1','N2'],'edges':['E']})
 def test_narrative_review_cannot_invent_experiments(self):
  self.net['paper']['paper_type']='review';self.index.update(article_type='review',review_subtype='narrative');self.m['inputs']['network']=self.save('network.json',self.net);self.m['inputs']['scientific_index']=self.save('index.json',self.index)
  self.m['inputs']['inventory']=self.save('inventory.json',{'experiments':[{'experiment_id':'NEW_TRIAL','fields':{}}]});self.assertIn('REVIEW_AS_EXPERIMENT',self.codes())
 def test_formal_ready_cannot_be_auto_upgraded(self):self.m['formal_ready']=True;self.assertIn('REVIEW_UPGRADE',self.codes())
if __name__=='__main__':unittest.main()
