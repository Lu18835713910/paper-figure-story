"""Portable stdlib-only smoke/negative tests using entirely self-authored data.

Run: python -B tests/test_inventory_synthetic.py --report-dir NEW_DIRECTORY
No third-party paper, image or fixture is read. A tiny valid PDF is authored
only as source identity test material; these tests do not prove PDF reasoning.
"""
from pathlib import Path
import argparse,copy,hashlib,json,sys,tempfile,unittest
S=Path(__file__).resolve().parents[1]/'scripts';sys.path.insert(0,str(S));sys.dont_write_bytecode=True
import experiment_inventory as inv
import evidence_network as network
import validate_knowledge as knowledge
TEST_REPORT=None

def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def tiny_pdf(path):
    stream=b'BT /F1 12 Tf 40 700 Td (SYNTHETIC TEST ONLY) Tj ET'
    objs=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
          b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',
          b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    b=bytearray(b'%PDF-1.4\n');offsets=[0]
    for i,obj in enumerate(objs,1):offsets.append(len(b));b.extend(str(i).encode()+b' 0 obj\n'+obj+b'\nendobj\n')
    xref=len(b);b.extend(b'xref\n0 6\n0000000000 65535 f \n')
    for n in offsets[1:]:b.extend(f'{n:010d} 00000 n \n'.encode())
    b.extend(b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n'+str(xref).encode()+b'\n%%EOF\n');Path(path).write_bytes(b)

class SyntheticInventoryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
    cls.tmp=None
    if TEST_REPORT:
        cls.work=TEST_REPORT/'synthetic_fixture';cls.work.mkdir()
    else:
        cls.tmp=tempfile.TemporaryDirectory(prefix='pfs_inventory_synthetic_');cls.work=Path(cls.tmp.name)
    pdf=cls.work/'synthetic.pdf';tiny_pdf(pdf);cache=cls.work/'cache';cache.mkdir()
    tx='SYNTHETIC TEST ONLY. Methods: compare Alpha with Beta. Three independent runs. Result: the test output differs.\n'
    page=cache/'page-01.txt';page.write_text(tx,encoding='utf-8');save(cache/'metadata.json',{'sha256':inv.sha(pdf),'physical_page_count':1})
    src={'document_id':'SYN_DOC','locator':{'physical_page':1,'section':'Self-authored synthetic test'},'verification':'pending'}
    cls.model={'schema_version':'1.1','model_status':'manual_fixture','description':'Self-authored source integrity test, not a paper.',
       'document_registry':[{'id':'SYN_DOC','role':'main_paper','format':'pdf','title':'Synthetic test','version':'1',
        'availability':'available','sha256':inv.sha(pdf),'hash_status':'verified','source_locator':'Self-authored','path':str(pdf),'physical_page_count':1}],
       'paper_type':{'label':'methods_or_model','confidence':'high','basis':[src],'classification_origin':'manual'},
       'entities':[{'id':'SYN_E','kind':'evidence','name':'Self-authored synthetic observation','source_role':'primary_study','inputs':[],'outputs':[],
        'parameters':[],'quantities':[],'source_refs':[src],'reporting_status':'paper_reported','analysis_unit':'not_applicable','unit_note':'Synthetic integrity example','limits':[]}],
       'relations':[],'figures':[],'stories':[],'relation_groups':[],'relation_constraints':[],'quantity_operations':[]}
    cls.kp=cls.work/'knowledge.json';save(cls.kp,cls.model)
    cls.ref={'document_id':'SYN_DOC','physical_page':1,'path':str(page),'sha256':inv.sha(page),'start':0,'end':len(tx),'excerpt':tx}
    def f(value,**kw):return {'value':value,'status':'VERIFIED','source_refs':[cls.ref],**kw}
    cls.inv={'version':inv.VERSION,'paper_id':'SYN_DOC','knowledge_sha256':inv.sha(cls.kp),'formal_ready':False,
      'counting_policy':'One substantive synthetic task; conditions and plotted points are not tasks.',
      'experiments':[{'experiment_id':'SYN.EXP.001','display_name':'Synthetic comparison','task_type':'experiment','m1_evidence_ids':['SYN_E'],'figure_ids':[],
       'fields':{'question':f('Compare Alpha and Beta'),'materials':f('Self-authored synthetic material'),'groups':f(['Alpha','Beta']),
        'group_count':f(2,unit='groups'),'independent_runs':f(3,unit='independent experiments'),
        'sample_count':{'value':None,'status':'NOT_VERIFIED','source_refs':[],'reason':'No sample assessment in this synthetic example'},
        'result':f('Synthetic output differs')}}],
      'method_sections':[{'section':'Synthetic test method','experiment_ids':['SYN.EXP.001'],'source_refs':[cls.ref]}]}
 @classmethod
 def tearDownClass(cls):
    if cls.tmp:cls.tmp.cleanup()
 def check(self,obj):return inv.validate_inventory(obj,self.model,base_dir=self.work,knowledge_path=self.kp)
 def mutate(self,path,value):
    v=copy.deepcopy(self.inv);target=v
    for k in path[:-1]:target=target[k]
    target[path[-1]]=value;return v
 def test_01_synthetic_m1_is_valid(self):self.assertTrue(knowledge.validate_knowledge(self.model,verify_files=True)['valid'])
 def test_02_exact_sources_valid(self):self.assertTrue(self.check(self.inv)['valid'])
 def test_03_wrong_model_hash(self):self.assertFalse(self.check(self.mutate(['knowledge_sha256'],'0'*64))['valid'])
 def test_04_no_human_review_promotion(self):self.assertFalse(self.check(self.mutate(['formal_ready'],True))['valid'])
 def test_05_source_excerpt_changed(self):self.assertFalse(self.check(self.mutate(['experiments',0,'fields','result','source_refs',0,'excerpt'],'invented'))['valid'])
 def test_06_no_source_verified(self):self.assertFalse(self.check(self.mutate(['experiments',0,'fields','result','source_refs'],[]))['valid'])
 def test_07_count_has_unit(self):self.assertFalse(self.check(self.mutate(['experiments',0,'fields','group_count','unit'],None))['valid'])
 def test_08_dots_not_samples(self):self.assertFalse(self.check(self.mutate(['experiments',0,'fields','group_count','derivation'],'counted_from_plot'))['valid'])
 def test_09_missing_is_not_not_reported(self):self.assertFalse(self.check(self.mutate(['experiments',0,'fields','sample_count','status'],'NOT_REPORTED'))['valid'])
 def test_10_membership_not_causal(self):
    layer=inv.build_experiment_layer(self.inv,self.model,base_dir=self.work,knowledge_path=self.kp)
    self.assertTrue(all(a['identity']=='association' and not a['scientific_dependency'] for a in layer['associations']));self.assertEqual(layer['relations'],[])
 def test_11_same_m1_entities_and_no_new_rsu(self):
    p=self.work/'inventory.json';save(p,self.inv);base=network.build_network(self.kp);v=network.build_network(self.kp,experiment_inventory_path=p)
    self.assertEqual(base['rsus'],v['rsus']);self.assertEqual(base['edges'],v['edges']);self.assertTrue(all(n in v['nodes'] for n in base['nodes']));self.assertTrue(network.validate_network(v)['valid'])
 def test_12_network_tampering_rejected(self):
    p=self.work/'inventory.json';save(p,self.inv);v=network.build_network(self.kp,experiment_inventory_path=p);v['experiment_layer']['experiments'][0]['display_name']='tampered'
    v['snapshot']=network.fingerprint({k:x for k,x in v.items() if k!='snapshot'});self.assertFalse(network.validate_network(v)['valid'])
 def test_13_presentation_cannot_create_dependency(self):
    v=copy.deepcopy(self.inv);v['relations']=[{'id':'SYN.REL','from':'SYN.EXP.001','to':'SYN_E','type':'depends_on','identity':'PRESENTATION_ORDER','source_refs':[self.ref]}];self.assertFalse(self.check(v)['valid'])
 def test_14_readable_audit_exists(self):
    out=inv.write_audit(self.inv,self.work/'audit',validation=self.check(self.inv));self.assertTrue(Path(out['markdown_path']).is_file());self.assertEqual(out['summary']['field_status_counts']['sample_count']['NOT_VERIFIED'],1)

def main():
    global TEST_REPORT
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report-dir',type=Path);args=p.parse_args()
    paths=[Path(__file__),S/'experiment_inventory.py',S/'evidence_network.py',S.parent/'schemas/experiment_inventory_v1_1.schema.json',S.parent/'schemas/evidence_network_v1_1.schema.json']
    versions={str(p):inv.sha(p) for p in paths}
    out=args.report_dir
    if out:
        if out.exists() and any(out.iterdir()):raise ValueError('Use a new report directory; prior test logs are preserved')
        out.mkdir(parents=True,exist_ok=True)
        TEST_REPORT=out
        with (out/'unittest.log').open('w',encoding='utf-8') as f:r=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SyntheticInventoryTests))
    else:r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SyntheticInventoryTests))
    result={'tests':r.testsRun,'passed':max(0,r.testsRun-len(r.failures)-len(r.errors)),'failures':[(str(t),x) for t,x in r.failures],'errors':[(str(t),x) for t,x in r.errors],
            'exit_code':0 if r.wasSuccessful() else 1,'source_versions_before':versions,'changed_source_during_test':[str(p) for p in paths if inv.sha(p)!=versions[str(p)]],
            'scope':'Self-authored synthetic source contracts only; not real-paper extraction or visual review.'}
    if out:save(out/'results.json',result)
    print(json.dumps(result,ensure_ascii=False));return result['exit_code']
if __name__=='__main__':raise SystemExit(main())
