"""Real-file C2 CLI contracts. Supply a completed isolated case; never edit it."""
from pathlib import Path
import copy,hashlib,json,os,shutil,subprocess,sys,tempfile,unittest,zipfile
from docx import Document
from lxml import etree as ET
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2),'utf-8')

@unittest.skipUnless(os.environ.get('PFS_C2_CASE'),'PFS_C2_CASE is required for real Workbook/Full CLI tests')
class DeliveryClosure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case=Path(os.environ['PFS_C2_CASE']);cls.root=Path(os.environ.get('PFS_C2_DELIVERY_ROOT',str(cls.case/'full_delivery/deliverables')));cls.model=cls.case/'inputs/research_logic.json'
        cls.audit=cls.root.parent/'audit';cls.annotations=load(cls.audit/'Workbook.assembly.json')['content']['assembly']['bindings']['path']
        cls.out=Path(os.environ['PFS_C2_TEST_OUTPUT']);cls.out.mkdir(parents=True,exist_ok=False)
    def setUp(self):self.d=self.out/self._testMethodName;self.d.mkdir()
    def cli(self,script,args,expected=0,code=None):
        cmd=[sys.executable,'-B',str(ROOT/'scripts'/script)]+[str(x) for x in args]
        r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8')
        (self.d/'stdout.log').write_text(r.stdout,'utf-8');(self.d/'stderr.log').write_text(r.stderr,'utf-8')
        save(self.d/'execution.json',dict(command=cmd,exit_code=r.returncode))
        if expected==0:self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        else:self.assertNotEqual(r.returncode,0,r.stdout+r.stderr)
        if code:self.assertIn(code,r.stdout+r.stderr)
    def package(self):
        p=self.d/'delivery';shutil.copytree(self.root,p);return p
    def full(self,p,ok=True,code=None):self.cli('validate_story.py',[p,'--delivery-manifest','--logic-model',self.model,'--profile','full','--require-B'],0 if ok else 1,code)
    def test_01_actual_full_products_and_files_pass(self):self.full(self.root)
    def test_02_actual_check_delivery_pass(self):self.cli('run_pfs.py',['check-delivery','--root',self.root,'--profile','full'])
    def test_03_missing_workbook_cannot_be_full(self):
        p=self.package();m=load(p/'Manifest.json');m['files']=[r for r in m['files'] if r['product']!='Workbook'];save(p/'Manifest.json',m)
        self.full(p,False,'FULL_PRODUCTS_REQUIRED')
    def test_04_stale_workbook_receipt_rejected(self):
        p=self.package();m=load(p/'Manifest.json');rec=next(r for r in m['coverage_sources'] if r['kind']=='branch');q=p/rec['path'];d=load(q);d['docx_sha256']='0'*64;save(q,d);rec['sha256']=sha(q)
        for f in m['files']:
            if f['path'].replace('\\','/')==rec['path'].replace('\\','/'):f['sha256']=sha(q)
        save(p/'Manifest.json',m);self.full(p,False,'COVERAGE_RECEIPT_ARTIFACT_DRIFT')
    def test_05_exact_source_span_mismatch_rejected(self):
        d=load(self.case/'inputs/scientific_index.json');key=next(k for k in d['sources'] if k.startswith('C2_'));d['sources'][key]['excerpt']+=' unsupported';q=self.d/'index.json';save(q,d)
        self.cli('scientific_index.py',['validate','--index',q],1,'SOURCE_SPAN:')
    def test_06_materials_is_actual_M1_parameter_binding(self):
        a=load(self.audit/'Workbook.assembly.json');m=load(self.model);net=load(m['inputs']['network']['path']);k=load(next(x['path'] for x in net['inputs'] if x['kind']=='knowledge'))
        rows=[r for r in a['content']['assembly']['field_map'] if r['field']=='materials'];self.assertEqual(len(rows),6)
        for row in rows:
            for ref in row['refs']:
                st=next(s for s in net['statements'] if s['id']==ref['id']);obj=k
                for token in st['source_pointer']['pointer'].split('/')[1:-1]:obj=obj[int(token)] if isinstance(obj,list) else obj[token]
                self.assertEqual(obj['key'],'materials');self.assertTrue(row['source_ids'])
        self.assertEqual(a['legacy_agent_registered_fields'],0)
    def test_07_six_original_figures_really_embedded(self):
        assets=load(self.case/'inputs/workbook_figures.json')['assets']
        with zipfile.ZipFile(self.root/'Workbook/Workbook.docx') as z:h={hashlib.sha256(z.read(p)).hexdigest() for p in z.namelist() if p.startswith('word/media/')}
        self.assertEqual(len(assets),6);self.assertTrue({a['sha256'] for a in assets}<=h)
    def test_08_independent_B_7pt_rejected_by_real_cli(self):
        self.cli('run_pfs.py',['check-delivery','--root',self.case/'gate_repro/B7_package_03','--profile','full'],1,'COMPLETE_B_READABILITY_LIMIT')
    def test_09_original_sources_preserved_and_audited(self):
        a=load(self.case/'audit/original_21_sources_review.json');self.assertEqual(len(a),21);self.assertTrue(all(r['preserved'] and r['exact_span'] and r['semantic_status']=='PARTIAL' for r in a))
    def test_10_docx_native_tables_text_and_all_branches(self):
        d=Document(self.root/'Workbook/Workbook.docx');self.assertGreater(len(d.tables),12)
        text='\n'.join(c.text for t in d.tables for row in t.rows for c in row.cells)
        for value in ['375.4%','1,012','1,021','计算预测','838']:self.assertIn(value,text)
        r=load(self.audit/'Workbook.receipt.json');self.assertEqual(set(r['branch_coverage']['displayed_branch_ids']),set(r['branch_coverage']['expected_branch_ids']));self.assertEqual(r['branch_coverage']['omitted_branches'],{})
    def test_11_wrong_figure_id_rejected_by_official_builder(self):
        assets=load(self.case/'inputs/workbook_figures.json');assets['assets'][0]['figure_id']='UNKNOWN';p=self.d/'figures.json';save(p,assets)
        self.cli('build_research_workbook.py',['--model',self.model,'--graphs',self.case/'logic_graph_manifest.json','--content',self.audit/'Workbook.resolved_content.json','--annotations',self.annotations,'--figure-assets',p,'--output',self.d/'bad.docx'],1,'WORKBOOK_FIGURE_ID');self.assertFalse((self.d/'bad.docx').exists())
    def test_12_materials_gap_cannot_generate_complete_workbook(self):
        c=load(self.audit/'Workbook.resolved_content.json');c['figures'][0]['materials']['text']='';p=self.d/'content.json';save(p,c)
        self.cli('build_research_workbook.py',['--model',self.model,'--graphs',self.case/'logic_graph_manifest.json','--content',p,'--output',self.d/'bad.docx'],1,'$/figures/0/materials/text');self.assertFalse((self.d/'bad.docx').exists())
if __name__=='__main__':unittest.main()
