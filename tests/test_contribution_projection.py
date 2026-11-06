"""Synthetic source-bound selection regressions; not independent paper understanding."""
import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_workbook_reuse import fixture,save
import research_logic as rl,evidence_network as en,project_evidence_products as pp
from project_presentation import PresentationProjector,validate_page_plan
from pptx import Presentation
from pptx.util import Inches
from PIL import Image,ImageDraw

REPO=Path(__file__).resolve().parents[1]

def claim_case(root,count=7,review=False):
    f=fixture(root,review=review,na=review)
    for i in range(count):
        e=copy.deepcopy(f['k']['entities'][-1]);e.update(id='C'+str(i+1),kind='claim',name='有源候选论断'+str(i+1))
        e['parameters']=[p for p in e['parameters'] if p['key']=='interpretation'];f['k']['entities'].append(e)
    if review:
        f['k']['relations']=[dict(id='ARG'+str(i+1),**{'from':'E','to':'C'+str(i+1)},type='argument_transition',provenance='paper',certainty='paper_reported',mandatory=False,rationale='自编综述的论据与概念论断关联，非实验验证。',source_refs=[f['ref']]) for i in range(count)]
    save(f['kp'],f['k']);f['net']=en.build_network(f['kp']);save(f['np'],f['net']);return f

def product_plan(f,**options):
    template=REPO/'assets/default_academic_blue_174994.pptx'
    return pp.project_products(f['net'],'balanced',{},dict(path=str(template),sha256=rl.file_sha(template)),dict(dict(scope='presentation',report_sections=True),**options))

def merged_case(root):
    f=fixture(root);k=f['k'];ev=copy.deepcopy(next(e for e in k['entities'] if e['id']=='E'));ev['id']='E2';k['entities'].append(ev)
    s=copy.deepcopy(k['stories'][0]);s.update(id='RSU2',evidence_ids=['E2'],finding_or_argument='第二项已登记的重要发现。',presentation_order=2,original_section_order=[2]);k['stories'].append(s)
    k['relations']=[dict(id='COMPARE',**{'from':'E','to':'E2'},type='compares',provenance='paper',certainty='paper_reported',mandatory=False,rationale='自编来源登记的两个比较读数，非独立生物学重复。',source_refs=[f['ref']])]
    save(f['kp'],k)
    request=dict(request_version='m2a-1',operations=[dict(op='merge',id='MERGED',story_ids=['RSU1','RSU2'],reason='同一问题下的两项有源比较发现。',basis_relation_ids=['COMPARE'],basis_source_pointers=[])])
    return f,request

def branch_case(root):
    f=fixture(root);m=f['model'];base=copy.deepcopy(m['nodes'][1]);m['nodes']=m['nodes'][:1];m['edges']=[];m['branches']=[]
    for i in range(1,4):
        n=copy.deepcopy(base);n.update(id='N'+str(i),title='自编研究分支'+str(i));m['nodes'].append(n)
        e=dict(id='R'+str(i),**{'from':'Q','to':n['id']},type='question_fork',identity='AUTHOR_ARGUMENT',label='有源研究分支',rationale='登记的自编问题分支。',alternatives='共享来源不增加独立实验。',source_ids=['S'],review_status='PARTIAL',causal_claim=False);m['edges'].append(e)
        m['branches'].append(dict(id='branch'+str(i),title=n['title'],nodes=['Q',n['id']],edges=[e['id']]))
    m['core']=dict(nodes=['Q','N1'],edges=['R1']);m['snapshot']=rl.snapshot(m);save(f['mp'],m)
    check=rl.validate_model(m);assert check['valid'],check
    # Deliberately labelled synthetic graph placeholders. These test DOCX coverage,
    # not PowerPoint visual fidelity or acceptance of scientific graphics.
    graphs=[]
    for v in ['A','B','branch1','branch2','branch3']:
        p=Path(root)/(v+'.pptx');prs=Presentation();sl=prs.slides.add_slide(prs.slide_layouts[6]);sl.shapes.add_textbox(0,0,Inches(9),Inches(1)).text='SYNTHETIC '+v;prs.save(p)
        png=p.with_suffix('.png');im=Image.new('RGB',(800,400),'white');ImageDraw.Draw(im).text((25,25),'SYNTHETIC COVERAGE FIXTURE / '+v,fill='black');im.save(png)
        graphs.append(dict(view=v,logic_snapshot=m['snapshot'],pptx=str(p),pptx_sha256=rl.file_sha(p),png=str(png),png_sha256=rl.file_sha(png)))
    gp=Path(root)/'graphs.json';save(gp,dict(graphs=graphs));f['gp']=gp;return f

def workbook_cli(f,output,selection=None):
    cmd=[sys.executable,str(REPO/'scripts/build_research_workbook.py'),'--model',str(f['mp']),'--graphs',str(f['gp']),'--scope','logic-only','--output',str(output)]
    if selection is not None:
        p=output.with_suffix('.annotations.json');save(p,dict(logic_snapshot=f['model']['snapshot'],rows=[],branch_selection=selection));cmd+=['--annotations',str(p)]
    r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8')
    return dict(command=cmd,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr)

class ContributionProjection(unittest.TestCase):
    def setUp(self):self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name)
    def test_seventh_claim_reaches_summary_without_expanding_page_capacity(self):
        f=claim_case(self.root);p=product_plan(f);s=[s for s in p['products'][0]['slides'] if s['id'].startswith('REPORT_summary')]
        self.assertEqual({n for x in s for n in x['source_node_ids']},{'C'+str(i) for i in range(1,8)})
        self.assertTrue(all(len(x['source_node_ids'])<=6 for x in s));self.assertTrue(pp.validate_products(f['net'],p,{})['valid'])
    def test_explicit_claim_selection_requires_omission_reasons(self):
        f=claim_case(self.root)
        with self.assertRaisesRegex(ValueError,'SUMMARY'):product_plan(f,summary_claim_ids=['C7'])
    def test_explicit_claim_selection_records_omissions(self):
        f=claim_case(self.root);reasons={'C'+str(i):'本次仅审阅第7项；其他贡献保留在原证据网络。' for i in range(1,7)}
        p=product_plan(f,summary_claim_ids=['C7'],summary_omissions=reasons);c=p['products'][0]['summary_coverage']
        self.assertEqual(c['displayed_claim_ids'],['C7']);self.assertEqual(c['omitted_claims'],reasons);self.assertEqual(c['status'],'PARTIAL')
    def test_unknown_or_duplicate_claim_rejected(self):
        f=claim_case(self.root,2)
        for ids in [['BAD'],['C1','C1']]:
            with self.assertRaises(ValueError):product_plan(f,summary_claim_ids=ids)
    def test_six_claims_keep_existing_summary_id_and_one_page(self):
        f=claim_case(self.root,6);p=product_plan(f);self.assertEqual([s['id'] for s in p['products'][0]['slides'] if s['id'].startswith('REPORT_summary')],['REPORT_summary'])
    def test_selected_summary_page_reports_deferred_claims(self):
        f=claim_case(self.root);p=product_plan(f,slide_ids=['REPORT_summary_2']);c=p['products'][0]['summary_coverage']
        self.assertEqual(c['displayed_claim_ids'],['C7']);self.assertEqual(set(c['omitted_claims']),{'C'+str(i) for i in range(1,7)})
    def test_no_front_matter_does_not_add_or_claim_summary_coverage(self):
        f=claim_case(self.root);p=product_plan(f,report_sections=False)
        self.assertNotIn('summary_coverage',p['products'][0]);self.assertFalse(any(s['id'].startswith('REPORT_summary') for s in p['products'][0]['slides']))
    def test_all_profiles_reuse_same_claim_identity_without_network_mutation(self):
        f=claim_case(self.root);before=copy.deepcopy(f['net']);template=REPO/'assets/default_academic_blue_174994.pptx'
        for profile in ['quick','balanced','full']:
            p=pp.project_products(f['net'],profile,{},dict(path=str(template),sha256=rl.file_sha(template)),dict(scope='presentation',report_sections=True))
            self.assertEqual(p['products'][0]['summary_coverage']['displayed_claim_ids'],['C'+str(i) for i in range(1,8)])
        self.assertEqual(f['net'],before)
    def test_review_claims_do_not_require_experimental_support_edges(self):
        f=claim_case(self.root,2,True);before=copy.deepcopy(f['net']);self.assertTrue(all(not u['claim_ids'] for u in f['net']['rsus']))
        p=product_plan(f);s=next(s for s in p['products'][0]['slides'] if s['id']=='REPORT_summary');self.assertEqual(set(s['source_node_ids']),{'C1','C2'});self.assertEqual(f['net'],before)
        self.assertTrue(all(e['type']=='argument_transition' and e['identity']=='author_argument' for e in f['net']['edges']))
    def test_merged_unit_keeps_both_finding_pointers_in_summary(self):
        f,q=merged_case(self.root);p=PresentationProjector(f['k'],dict(asset_version='m2b-1',assets=[]),verify_files=False).project('balanced',q)
        refs={b['knowledge_pointer'] for s in p['slides'] if s['kind']=='conclusion' for b in s['blocks']}
        self.assertEqual(refs,{'/stories/0/finding_or_argument','/stories/1/finding_or_argument'})
        self.assertTrue(validate_page_plan(f['k'],dict(asset_version='m2b-1',assets=[]),p)['valid'])
    def test_default_third_branch_is_explicitly_deferred(self):
        f=branch_case(self.root);out=self.root/'default.docx';r=workbook_cli(f,out);self.assertEqual(r['exit_code'],0,r)
        c=rl.load(out.with_suffix('.receipt.json'))['branch_coverage'];self.assertEqual(c['status'],'PARTIAL');self.assertIn('branch3',c['omitted_branches'])
        from docx import Document
        self.assertTrue(any('自编研究分支3' in p.text and '未展开' in p.text for p in Document(out).paragraphs))
    def test_explicit_three_branch_selection_reaches_actual_docx(self):
        f=branch_case(self.root);out=self.root/'all.docx';r=workbook_cli(f,out,dict(view_ids=['branch1','branch2','branch3'],omitted_reasons={}));self.assertEqual(r['exit_code'],0,r)
        c=rl.load(out.with_suffix('.receipt.json'))['branch_coverage'];self.assertEqual(c['status'],'COVERED_REGISTERED_BRANCHES')
        from docx import Document
        text='\n'.join(p.text for p in Document(out).paragraphs)
        for i in range(1,4):self.assertIn('03 自编研究分支'+str(i),text)
    def test_branch_selection_cannot_silently_omit_or_invent(self):
        f=branch_case(self.root)
        for i,s in enumerate([dict(view_ids=['branch1']),dict(view_ids=['UNKNOWN']),dict(view_ids=['branch1','branch1'])]):
            r=workbook_cli(f,self.root/('bad'+str(i)+'.docx'),s);self.assertNotEqual(r['exit_code'],0);self.assertIn('BRANCH_SELECTION',r['stderr'])
    def test_selected_branch_requires_existing_matching_graph(self):
        f=branch_case(self.root);g=rl.load(f['gp']);g['graphs']=[x for x in g['graphs'] if x['view']!='branch3'];save(f['gp'],g)
        r=workbook_cli(f,self.root/'missing.docx',dict(view_ids=['branch1','branch2','branch3']));self.assertNotEqual(r['exit_code'],0);self.assertIn('WORKBOOK_BRANCH_GRAPH_REQUIRED',r['stderr'])

if __name__=='__main__':unittest.main()
