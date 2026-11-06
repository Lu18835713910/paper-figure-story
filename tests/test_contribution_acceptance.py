"""CLI/package coverage propagation with self-authored, source-bound fixtures.

Native logic PPTX and real Workbook DOCX are produced by existing backends.
Labelled PNG placeholders test binding only; no scientific/visual PASS is claimed.
"""
import copy,hashlib,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parent),str(Path(__file__).resolve().parents[1]/'scripts')]
import test_contribution_projection as h
import research_logic as rl,project_evidence_products as pp,render_logic as native
from pptx import Presentation
from pptx.util import Inches

R=Path(__file__).resolve().parents[1]

def prepare(root,omit_claim=False,all_branches=False,review=True,third_core=False,limited=False):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    f=h.claim_case(root/'facts',7);b=h.branch_case(root/'branches');m=b['model']
    m['network_snapshot']=f['net']['snapshot'];m['inputs']['network']=dict(path=str(f['np']),sha256=rl.file_sha(f['np']))
    m['layout']={'A':dict(width=1280,height=720,positions={'Q':[60,80,1160,120],'N1':[60,330,1160,240]},routes={'R1':dict(points=[[640,200],[640,330]])}),'B':dict(width=1800,height=1200,positions={'Q':[60,170,1600,120],**{'N'+str(i):[60+(i-1)*570,450,500,400] for i in range(1,4)}},routes={'R'+str(i):dict(points=[[860,290],[860,350],[310+(i-1)*570,350],[310+(i-1)*570,450]]) for i in range(1,4)})}
    for i in range(1,4):m['layout']['branch'+str(i)]=dict(width=1280,height=720,positions={'Q':[60,80,1160,120],'N'+str(i):[60,330,1160,240]},routes={'R'+str(i):dict(points=[[640,200],[640,330]])})
    m['snapshot']=rl.snapshot(m);mp=root/'model.json';h.save(mp,m);assert rl.validate_model(m)['valid']
    meta=dict(research_logic=dict(path=str(mp),sha256=rl.file_sha(mp)));template=R/'assets/default_academic_blue_174994.pptx'
    plan=pp.project_products(f['net'],'balanced',meta,dict(path=str(template),sha256=rl.file_sha(template)),dict(scope='logic-views',views=['A','B','branch1','branch2','branch3']))
    lp=root/'logic.plan.json';md=root/'metadata.json';h.save(lp,plan);h.save(md,meta)
    rendered=native.render(f['np'],lp,root/'graphs',md);graphs=[]
    for row in rendered['files']:
        v=row['view'];png=b['gp'].parent/(v+'.png')
        graphs.append(dict(id='logic_'+v,view=v,scope='complete' if v=='B' else 'overview_A' if v=='A' else 'zoom',**({'parent_canvas':'logic_B'} if v not in ['A','B'] else {}),node_ids=row['node_ids'],edge_ids=row['edge_ids'],logic_snapshot=m['snapshot'],pptx=row['path'],pptx_sha256=row['sha256'],png=str(png),png_sha256=rl.file_sha(png)))
    gp=root/'graphs.json';h.save(gp,dict(graphs=graphs))
    options=dict(summary_claim_ids=['C'+str(i) for i in range(1,7)],summary_omissions={'C7':'自编有限展示例，保留原有claim。'}) if omit_claim else {}
    report=h.product_plan(f,**options);sp=root/'summary.plan.json';h.save(sp,report)
    prs=Presentation();prs.slide_width=Inches(1280/96);prs.slide_height=Inches(720/96)
    scenes=[s for s in report['products'][0]['slides'] if s['id'].startswith('REPORT_summary')]
    for scene in scenes:
        sl=prs.slides.add_slide(prs.slide_layouts[6])
        for e in scene['elements']:
            if e['kind']!='text':continue
            p=e['position'];native.text(sl,'RC_'+scene['id']+'_'+e['id'],e['text'],[Inches(p[k]/96) for k in ['left','top','width','height']],e['font_size'],e.get('bold',False))
    for _ in ['A','B']:
        sl=prs.slides.add_slide(prs.slide_layouts[6]);sl.notes_slide.notes_text_frame.text='模型快照：'+m['snapshot']+'\n自编原生逻辑占位页。'
    main=root/'main.base.pptx';prs.save(main);pm=root/'page_map.json';h.save(pm,{'A':len(scenes)+1,'B':len(scenes)+2})
    ann=dict(logic_snapshot=m['snapshot'],rows=[],workbook_bindings=dict(figure_panels={'F1':['A']}))
    if all_branches:ann['branch_selection']=dict(view_ids=['branch1','branch2','branch3'],omitted_reasons={})
    ap=root/'annotations.json';h.save(ap,ann)
    rp=None
    if review:
        basis=root/'review_basis.md';basis.write_text('# 自编有源审阅夹具\n仅测试已有ID的分类、支持理由和范围传播，不是实际论文科学终审。\n','utf-8')
        items=[dict(kind='summary',id='C'+str(i),importance='core' if i in [1,7] else 'support',importance_reason='自编审阅的重要性判定。',support_explanation='沿用登记的自编来源，不扩大实验独立性。',source_refs=next(n['source_refs'] for n in f['net']['nodes'] if n['id']=='C'+str(i))) for i in range(1,8)]
        items += [dict(kind='branch',id='branch'+str(i),importance='core' if i<3 or third_core else 'support',importance_reason='自编审阅的分支定位。',support_explanation='共享自编来源，不计为三次生物验证。',source_ids=['S']) for i in range(1,4)]
        data=dict(status='SOURCE_REFERENCED_REVIEW_RECORDED',reviewer='Synthetic test reviewer (not an independent human acceptance)',review_scope='Self-authored available-material fixture; no claim of real-paper completeness.',network_snapshot=f['net']['snapshot'],basis=dict(path=str(basis),sha256=rl.file_sha(basis)),items=items)
        if limited:
            approval=root/'scope_approval.md';approval.write_text('自编批准的有限阅读范围；被省略项仍保留在完整网络。','utf-8')
            exclusions={}
            if omit_claim:exclusions['summary']={'C7':'已批准的有限例子，不宣称完整论文结论。'}
            if not all_branches:exclusions['branch']={'branch3':'支撑分支在本次有限手册范围外，完整B保留。'}
            data['approved_scope']=dict(kind='limited',approved_by='Synthetic test scope approval',reason='有限教学范围，不代表全文贡献消失。',excluded_ids=exclusions,basis=dict(path=str(approval),sha256=rl.file_sha(approval)))
        rp=root/'contribution_review.json';h.save(rp,data)
    return dict(root=root,f=f,model=m,mp=mp,gp=gp,lp=lp,md=md,main=main,pm=pm,ap=ap,sp=sp,rp=rp)

class CoverageAcceptance(unittest.TestCase):
    def setUp(self):
        retained=os.environ.get('PFS_COVERAGE_TEST_OUTPUT')
        if retained:
            self.root=Path(retained)/('c_'+hashlib.sha256(self._testMethodName.encode()).hexdigest()[:10]);self.root.mkdir(parents=True,exist_ok=False)
            h.save(self.root/'case.json',dict(test=self._testMethodName,provenance='self-authored source-bound contract fixture'))
        else:self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.calls=[]
    def cli(self,*args):
        cmd=[sys.executable,'-B',*map(str,args)];p=subprocess.run(cmd,capture_output=True,encoding='utf-8')
        self.calls.append(dict(command=cmd,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr));h.save(self.root/'CLI_results.json',self.calls)
        return p
    def deliver(self,x,profile='balanced'):
        args=[R/'scripts/run_pfs.py','deliver','--research-logic',x['mp'],'--graphs',x['gp'],'--main-pptx',x['main'],'--page-map',x['pm'],'--plan',x['lp'],'--metadata',x['md'],'--summary-plan',x['sp'],'--workbook-bindings',x['ap'],'--request','main','A','B','Workbook','--outdir',self.root/'delivery','--profile',profile,'--development-preview']
        if x['rp']:args+=['--contribution-review',x['rp']]
        p=self.cli(*args);self.package=self.root/'delivery/deliverables';return p
    def validate(self,x,profile='full'):
        p=self.cli(R/'scripts/validate_story.py',self.package,'--delivery-manifest','--logic-model',x['mp'],'--profile',profile)
        return p,json.loads(p.stdout)
    def test_seven_claims_real_manifest_and_native_summary(self):
        x=prepare(self.root/'input',all_branches=True);p=self.deliver(x,'full');self.assertEqual(p.returncode,0,p.stderr)
        p,q=self.validate(x);self.assertEqual(p.returncode,0,q);self.assertTrue(q['structural_validation']['valid'])
        c=q['contribution_validation'];self.assertEqual(c['status'],'PASS_REVIEWED_REQUESTED_SCOPE');self.assertEqual(c['paper_all_core_contributions_discovered'],'NOT_DETERMINABLE_FROM_PROJECTION')
        self.assertEqual(next(r for r in c['products'] if r['kind']=='summary')['registered_projection'],'COMPLETE')
    def test_core_claim_omitted_full_fails_but_structure_passes(self):
        x=prepare(self.root/'input',omit_claim=True,all_branches=True);p=self.deliver(x,'full');self.assertEqual(p.returncode,2)
        p,q=self.validate(x);self.assertEqual(p.returncode,1);self.assertTrue(q['structural_validation']['valid']);self.assertIn('summary:C7',q['contribution_validation']['known_core_omissions'])
        for profile in ['quick','balanced']:
            p,q=self.validate(x,profile);self.assertEqual(p.returncode,0,q);self.assertEqual(q['contribution_validation']['status'],'PARTIAL')
    def test_core_third_branch_omitted_full_fails(self):
        x=prepare(self.root/'input',third_core=True);p=self.deliver(x,'full');self.assertEqual(p.returncode,2)
        p,q=self.validate(x);self.assertEqual(p.returncode,1);self.assertTrue(q['structural_validation']['valid']);self.assertIn('branch:branch3',q['contribution_validation']['known_core_omissions'])
    def test_support_branch_approved_limited_scope(self):
        x=prepare(self.root/'input',limited=True);self.assertEqual(self.deliver(x,'full').returncode,0)
        p,q=self.validate(x);self.assertEqual(p.returncode,0,q);b=next(r for r in q['contribution_validation']['products'] if r['kind']=='branch');self.assertEqual(b['registered_projection'],'PARTIAL');self.assertEqual(b['content_status'],'PASS_REVIEWED_REQUESTED_SCOPE');self.assertEqual(b['scope'],'approved_limited')
    def test_no_core_review_is_not_content_pass(self):
        x=prepare(self.root/'input',all_branches=True,review=False);self.assertEqual(self.deliver(x).returncode,0)
        p,q=self.validate(x);self.assertEqual(p.returncode,0,q);self.assertEqual(q['contribution_validation']['status'],'NOT_ASSESSED')
    def test_support_omission_without_scope_approval_stays_partial(self):
        x=prepare(self.root/'input');self.assertEqual(self.deliver(x).returncode,0)
        p,q=self.validate(x);self.assertEqual(p.returncode,0,q);self.assertEqual(q['contribution_validation']['status'],'PARTIAL')
    def test_legacy_workbook_without_metadata_remains_compatible_not_assessed(self):
        x=prepare(self.root/'input',all_branches=True,review=False);self.assertEqual(self.deliver(x).returncode,0)
        src=self.package;legacy=self.root/'legacy';legacy.mkdir();m=rl.load(src/'Manifest.json')
        m['files']=[r for r in m['files'] if r.get('product')!='coverage_audit'];m.pop('coverage_sources');m.pop('contribution_review');m.pop('contribution_coverage')
        for row in m['files']:
            target=legacy/row['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src/row['path'],target)
        m.pop('logic_graph_contract',None)
        h.save(legacy/'Manifest.json',m);self.package=legacy;p,q=self.validate(x,'balanced');self.assertEqual(p.returncode,0,q);self.assertTrue(q['structural_validation']['valid']);self.assertEqual(q['contribution_validation']['status'],'NOT_ASSESSED')
        # C1: absent real-file graph audit remains readable/compatible, but can no
        # longer be certified as a Full native-graph delivery.
        p,q=self.validate(x,'full');self.assertEqual(p.returncode,1);self.assertIn('LOGIC_GRAPH_CONTRACT_REQUIRED',q['errors'])
    def test_receipt_cannot_claim_unrendered_branch_even_after_rehash(self):
        x=prepare(self.root/'input',review=False);self.assertEqual(self.deliver(x).returncode,0);m=rl.load(self.package/'Manifest.json');rec=next(r for r in m['coverage_sources'] if r['kind']=='branch');path=self.package/rec['path'];j=rl.load(path);j['branch_coverage']['displayed_branch_ids'].append('branch3');j['branch_coverage']['omitted_branches']={};h.save(path,j);rec['sha256']=rl.file_sha(path)
        next(r for r in m['files'] if r['path'].replace('\\','/')==rec['path'])['sha256']=rec['sha256'];h.save(self.package/'Manifest.json',m)
        p,q=self.validate(x);self.assertEqual(p.returncode,1);self.assertIn('COVERAGE_BRANCH_OBJECT_MISMATCH',q['errors'])
    def test_registered_source_mismatch_cannot_supply_core_review(self):
        x=prepare(self.root/'input',all_branches=True);j=rl.load(x['rp']);j['items'][0]['source_refs'][0]['document_id']='FOREIGN_DOC';h.save(x['rp'],j);self.assertEqual(self.deliver(x).returncode,2)
        p,q=self.validate(x);self.assertEqual(p.returncode,1);self.assertIn('CONTRIBUTION_REVIEW_SOURCE_MISMATCH',q['errors'])
    def test_check_delivery_cli_consumes_coverage(self):
        x=prepare(self.root/'input',third_core=True);self.deliver(x)
        p=self.cli(R/'scripts/run_pfs.py','check-delivery','--root',self.package,'--profile','full');q=json.loads(p.stdout);self.assertEqual(p.returncode,2);self.assertTrue(q['structure_valid']);self.assertIn('branch:branch3',q['contribution_coverage']['known_core_omissions'])
    def test_approved_limited_scope_can_exclude_known_core_without_claiming_full_paper(self):
        x=prepare(self.root/'input',omit_claim=True,all_branches=True,limited=True);self.assertEqual(self.deliver(x,'full').returncode,0)
        p,q=self.validate(x);self.assertEqual(p.returncode,0,q);s=next(r for r in q['contribution_validation']['products'] if r['kind']=='summary');self.assertEqual(s['registered_projection'],'PARTIAL');self.assertEqual(s['scope'],'approved_limited');self.assertFalse(q['contribution_validation']['formal_ready'])
    def test_summary_coverage_cannot_replace_missing_actual_text(self):
        x=prepare(self.root/'input',all_branches=True);self.assertEqual(self.deliver(x).returncode,0)
        m=rl.load(self.package/'Manifest.json');row=next(r for r in m['files'] if r['product']=='main');path=self.package/row['path'];prs=Presentation(path)
        for sl in prs.slides:
            for shape in list(sl.shapes):
                if shape.name=='RC_REPORT_summary_2_REPORT_conclusion_6':sl.shapes._spTree.remove(shape._element)
        prs.save(path);row['sha256']=rl.file_sha(path);next(r for r in m['coverage_sources'] if r['kind']=='summary')['artifact']['sha256']=row['sha256'];h.save(self.package/'Manifest.json',m)
        p,q=self.validate(x);self.assertEqual(p.returncode,1);self.assertIn('COVERAGE_SUMMARY_OBJECT_MISMATCH',q['errors'])
    def test_missing_declared_metadata_cannot_trust_cached_pass(self):
        x=prepare(self.root/'input',all_branches=True);self.assertEqual(self.deliver(x).returncode,0);m=rl.load(self.package/'Manifest.json');m['coverage_sources']=[];h.save(self.package/'Manifest.json',m)
        p,q=self.validate(x);self.assertEqual(p.returncode,1);self.assertIn('COVERAGE_DECLARATION_MISSING',q['errors'])
    def test_actual_delivery_requires_coverage_artifact_binding(self):
        x=prepare(self.root/'input',all_branches=True);self.assertEqual(self.deliver(x).returncode,0);m=rl.load(self.package/'Manifest.json');next(r for r in m['coverage_sources'] if r['kind']=='summary').pop('artifact');h.save(self.package/'Manifest.json',m)
        p,q=self.validate(x);self.assertEqual(p.returncode,1);self.assertIn('COVERAGE_ARTIFACT_BINDING_REQUIRED',q['errors'])
    def test_standard_run_plan_only_consumes_coverage_and_full_policy(self):
        f=h.claim_case(self.root/'facts',7);cache=self.root/'cache';first=self.root/'first'
        base=[R/'scripts/run_pfs.py','run','--pdf',f['kp'].parent/'synthetic.pdf','--knowledge',f['kp'],'--cache-dir',cache,'--modes','full','--plan-only']
        p=self.cli(*base,'--outdir',first);self.assertEqual(p.returncode,0,p.stderr);q=rl.load(first/'execution.json')['profiles'][0]['contribution_coverage'];self.assertEqual(q['status'],'NOT_ASSESSED');self.assertEqual(q['products'][0]['registered_projection'],'PLANNED_COMPLETE')
        net=rl.load(first/'evidence_network.json');basis=self.root/'basis.md';basis.write_text('自编完整范围审阅；C7是本测试登记的核心，禁止以选页掩盖。','utf-8')
        items=[dict(kind='summary',id='C'+str(i),importance='core' if i==7 else 'support',importance_reason='自编判定。',support_explanation='自编有源记录。',source_refs=next(n['source_refs'] for n in net['nodes'] if n['id']=='C'+str(i))) for i in range(1,8)]
        review=self.root/'review.json';h.save(review,dict(status='SOURCE_REFERENCED_REVIEW_RECORDED',reviewer='Synthetic reviewer',review_scope='Synthetic complete registered scope',network_snapshot=net['snapshot'],basis=dict(path=str(basis),sha256=rl.file_sha(basis)),items=items))
        second=self.root/'second';p=self.cli(*base,'--outdir',second,'--slides','REPORT_summary','--contribution-review',review);self.assertEqual(p.returncode,2,p.stderr);q=rl.load(second/'execution.json')['profiles'][0]['contribution_coverage'];self.assertIn('summary:C7',q['known_core_omissions'])

if __name__=='__main__':unittest.main()
