"""Self-authored source-bound reuse tests. Not paper-extraction/scientific review."""
from pathlib import Path
import copy,json,sys,tempfile,unittest,subprocess,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import workbook_content as wc,research_logic as rl,evidence_network as en
from test_inventory_synthetic import tiny_pdf

def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),'utf8')
def fixture(root,review=False,na=False):
 root=Path(root);root.mkdir(parents=True,exist_ok=True);pdf=root/'synthetic.pdf';tiny_pdf(pdf)
 values=dict(purpose='比较已登记条件下的空间读数。',materials='组织区域样本，不是患者重复。',design='处理区域与对照区域分别测量。',readout='测量已登记的荧光读数。',result='处理区域的荧光信号较低。',interpretation='支持该条件下的差异，不能推出完整机制。',links='本例只登记一张主图，没有跨图实验链。',limits='这是自编测试材料，不是论文实验。',analysis='比较原记录中的分组和指标。',counts='两块组织区域；独立患者数未核实。')
 if review:
  values.update(purpose='比较两类已引用研究的证据边界。',materials='两类文献论据。',design='对照文献的不同证据范围。',readout='读取原文登记的比较维度。',result='两类论据的支持范围不同。',interpretation='这是文献综合，不是综述作者的新实验。',links='本图为综述概念比较，不登记实验时序。')
 text='\n'.join(values.values())+'\nJT z=7.43, P=0.004; another metric P=0.004. 128 measured cells.\nReviewed narrative synthesis: no original or analytical methods apply.\n'
 save(root/'metadata.json',dict(sha256=rl.file_sha(pdf)))
 page=root/'page-01.txt';page.write_text(text,'utf8');h=hashlib.sha256(text.encode()).hexdigest()
 ref=dict(document_id='DOC',locator=dict(physical_page=1,context_sha256=h),verification='pending')
 params=[dict(key=k,value=v,status='reported',unit='not_applicable',source_refs=[ref]) for k,v in values.items()]
 stat=dict(id='Q_IMMUNE',label='免疫niche趋势的P',value='0.004',meaning='仅指该有序趋势的空间置换P。',metric_id='immune_niche',test_id='JT_torus',unit='probability',population_id='ducts')
 params.append(dict(key='quantitative_result',value=stat,status='reported',unit='probability',source_refs=[ref]))
 def entity(id,kind,parameters):return dict(id=id,kind=kind,name='登记的研究任务' if id=='M' else '登记的证据',source_role='primary_study',inputs=[],outputs=[],parameters=parameters,quantities=[],source_refs=[ref],reporting_status='paper_reported',analysis_unit='not_applicable',unit_note='Synthetic field container, not a replicate',limits=[])
 entities=[entity('E','evidence',params)] if review and na else [entity('M','method',params),entity('E','evidence',[])]
 k=dict(schema_version='1.1',model_status='curated',description='Self-authored reuse fixture; not a real paper.',document_registry=[dict(id='DOC',role='main_paper',format='pdf',title='Synthetic review' if review else 'Synthetic study',version='1',availability='available',sha256=rl.file_sha(pdf),hash_status='verified',source_locator='self-authored test',path=str(pdf),physical_page_count=1)],paper_type=dict(label='review' if review else 'original_research',confidence='high',basis=[ref],classification_origin='manual'),entities=entities,relations=[],figures=[dict(id='F1',document_id='DOC',label='测试主图',kind='conceptual' if review else 'main',source_refs=[ref])],stories=[dict(id='RSU1',question_or_purpose=values['purpose'],method_ids=[] if review and na else ['M'],evidence_ids=['E'],figure_refs=['F1'],finding_or_argument=values['result'],limits=[values['limits']],source_refs=[ref],presentation_order=1,original_section_order=[1],restructuring_reason='Original order',author_explicit_or_presentation='paper')],relation_groups=[],relation_constraints=[],quantity_operations=[])
 kp=root/'knowledge.json';save(kp,k);net=en.build_network(kp);np=root/'network.json';save(np,net)
 src=dict(source_status='SYNTHETIC_LOCATED_NOT_SEMANTIC_REVIEW',document_id='DOC',document_sha256=rl.file_sha(pdf),physical_page=1,path=str(page),sha256=rl.file_sha(page),start=0,end=len(text),excerpt=text,excerpt_sha256=h)
 idx=dict(reading_status='AVAILABLE_CONTENT_READ',methods_task_detection='COMPLETE_AVAILABLE',result_mapping_status='MAPPED_WITH_GAPS',article_type=k['paper_type']['label'],review_subtype='narrative' if review else None,facets={key:dict(status='PARTIAL',text='Self-authored scope',sources=['S']) for key in ['background_gap','core_question','hypotheses','tasks','purpose','materials','groups_controls','conditions','methods','results','author_interpretation','limitations']})
 idx.update(version='pfs-scientific-index-1',source_pdf=str(pdf),file_sha256=rl.file_sha(pdf),page_count=1,formal_ready=False,reading_record=dict(actor='self-authored fixture reviewer',basis=[dict(path=str(page),sha256=rl.file_sha(page))],scope='Self-authored scientific input contract test only'),sources={'S':src})
 if not review:idx.pop('review_subtype')
 if na:idx['facets']['methods']=dict(status='NOT_APPLICABLE',text='已审阅的叙述性综述没有原始实验、检索/纳排或其他实际分析方法。',sources=['S'],applicability=dict(scope='original_experimental_methods',reviewer='self-authored fixture reviewer',reason='Available content reviewed; no applicable original or analytical methods.',source_ids=['S'],article_type_reviewed=True,scope_reviewed=True,basis_kind='reviewed_not_applicable',actual_methods_present=False))
 ip=root/'index.json';save(ip,idx)
 ids=[e['id'] for e in entities];st=[s['id'] for s in net['statements']]
 nodes=[dict(id='Q',kind='question',title='科学问题',short_text='登记的比较能支持什么？',detail_text='Self-authored fixture',identity='AUTHOR_ARGUMENT',source_ids=['S'],source_entity_ids=ids,statement_ids=st,field_bindings=[],review_status='PARTIAL'),dict(id='N',kind='analysis',title='方法、结果与边界',short_text=values['result'],detail_text=values['interpretation'],identity='SCIENTIFIC_EVIDENCE',source_ids=['S'],source_entity_ids=ids,statement_ids=st,field_bindings=[],review_status='PARTIAL')]
 edges=[dict(id='R',**{'from':'Q','to':'N'},type='progression',identity='AUTHOR_ARGUMENT',label='检验问题',rationale='按登记的比较回答问题。',alternatives='不是历史时序或分子因果。',source_ids=['S'],review_status='PARTIAL',causal_claim=False)]
 ad=root/'adjudication.json';save(ad,dict(nodes=nodes,edges=edges))
 m=dict(version=rl.VERSION,paper_title=k['document_registry'][0]['title'],short_citation='Self-authored fixture',formal_ready=False,network_snapshot=net['snapshot'],sources={'S':src},nodes=nodes,edges=edges,core=dict(nodes=['Q','N'],edges=['R']),branches=[],method_explanations=[],inputs={key:dict(path=str(p),sha256=rl.file_sha(p)) for key,p in [('network',np),('scientific_index',ip),('adjudication',ad)]},layout={'A':dict(width=1280,height=720,positions={'Q':[60,90,1160,90],'N':[60,290,1160,230]}),'B':dict(width=1800,height=1000,positions={'Q':[70,170,1600,100],'N':[70,400,1600,370]})})
 m['snapshot']=rl.snapshot(m);mp=root/'model.json';save(mp,m)
 bp=root/'bindings.json';save(bp,dict(logic_snapshot=m['snapshot'],workbook_bindings=dict(figure_panels={'F1':['A']})))
 return dict(root=root,model=m,mp=mp,k=k,kp=kp,net=net,np=np,index=idx,ip=ip,bp=bp,ref=ref,source=src)

class Reuse(unittest.TestCase):
 def setUp(self):self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.f=fixture(self.t.name)
 def assembled(self,f=None):
  f=f or self.f;return wc.assemble_content(f['model'],f['bp'])
 def binding(self,**v):
  b=rl.load(self.f['bp']);b['workbook_bindings'].update(v);save(self.f['bp'],b)
 def rebuild(self,inventory=None):
  save(self.f['kp'],self.f['k']);net=en.build_network(self.f['kp'],experiment_inventory_path=inventory);save(self.f['np'],net);self.f['net']=net
  m=self.f['model'];m['network_snapshot']=net['snapshot'];m['inputs']['network']['sha256']=rl.file_sha(self.f['np'])
  for node in m['nodes']:node['statement_ids']=[s['id'] for s in net['statements']];node['source_entity_ids']=[e['id'] for e in self.f['k']['entities']]
  m['snapshot']=rl.snapshot(m);save(self.f['mp'],m);b=rl.load(self.f['bp']);b['logic_snapshot']=m['snapshot'];save(self.f['bp'],b)
 def test_registered_M1_RSU_without_content_or_inventory(self):
  a=self.assembled();self.assertTrue(a['valid'],a['gaps']);self.assertTrue(wc.validate_content(self.f['model'],a['content'])['valid']);self.assertGreater(a['automatic_fields'],0);self.assertEqual(a['new_agent_text_fields'],0)
 def test_result_cannot_bind_method_field(self):
  sid=next(s['id'] for s in self.f['net']['statements'] if s['source_pointer']['pointer'].endswith('/parameters/2/value'));self.binding(figures={'F1':{'results':[sid]}});self.assertFalse(self.assembled()['valid'])
 def test_same_P_different_test_not_bound_by_value(self):
  self.binding(quantitative_results=[dict(ref='QUANT:M:10',expect=dict(metric_id='immune_niche',test_id='SPP1_other_test'))]);a=self.assembled();self.assertTrue(any(g['code']=='QUANTITATIVE_IDENTITY_MISMATCH' for g in a['gaps']))
 def test_cell_cannot_be_relabelled_patient(self):
  self.f['k']['entities'][0]['quantities']=[dict(key='measured_cells',value=128,status='reported',unit='cell',population_id='E',source_role='primary_study',source_refs=[self.f['ref']],note='128 measured cells, not independent patients.')];self.rebuild();a=self.assembled();self.assertTrue(wc.validate_content(self.f['model'],a['content'])['valid']);self.binding(quantitative_results=[dict(ref='COUNT:M:0',expect=dict(unit='donor'))]);self.assertTrue(any(g['code']=='QUANTITATIVE_IDENTITY_MISMATCH' for g in self.assembled()['gaps']))
 def test_changed_generated_fact_rejected(self):
  a=self.assembled();a['content']['figures'][0]['results']['text']='编造实验结果';self.assertIn('WORKBOOK_DERIVATION_DRIFT',wc.validate_content(self.f['model'],a['content'])['errors'])
 def test_binding_conflict_retained(self):
  self.binding(conflicts=['同一记录存在未裁决候选值']);a=self.assembled();self.assertFalse(a['valid']);self.assertEqual(a['gaps'][0]['code'],'SOURCE_CONFLICT')
 def test_legacy_migration_cannot_hide_registered_figure(self):
  c=self.assembled()['content'];c.pop('assembly');c['inputs']=[r for r in c['inputs'] if r['path']!=str(self.f['bp'])];c['expected_figures']=['OTHER'];c['figures'][0]['id']='OTHER';p=Path(self.t.name)/'legacy.json';save(p,c);self.binding(legacy_content=dict(path=str(p),sha256=rl.file_sha(p),model=dict(path=str(self.f['mp']),sha256=rl.file_sha(self.f['mp'])),reviewer='fixture review'));self.assertTrue(any(g['code']=='LEGACY_FIGURE_COVERAGE_MISMATCH' for g in self.assembled()['gaps']))
 def test_all_does_not_pass_panel_mapping(self):self.binding(figure_panels={'F1':['all']});self.assertFalse(self.assembled()['valid'])
 def test_no_registry_cannot_make_chapters(self):
  self.f['k']['figures']=[];self.f['k']['stories']=[];self.rebuild();a=self.assembled();self.assertEqual({x['code'] for x in a['gaps']} & {'FIGURE_REGISTRY_MISSING','RSU_REGISTRY_MISSING'},{'FIGURE_REGISTRY_MISSING','RSU_REGISTRY_MISSING'})
 def test_valid_partial_inventory_no_patient_count_invented(self):
  src=self.f['source'];ref={k:src[k] for k in ['document_id','physical_page','path','sha256','start','end','excerpt','excerpt_sha256']}
  def field(v):return dict(value=v,status='PARTIAL',source_refs=[ref])
  fields={k:field(v) for k,v in dict(question='检验登记条件下差异。',materials='两块组织区域。',groups='处理与对照。',acquisition='检测荧光信号。',analysis='比较登记指标。',result='处理读数较低。',interpretation='不证明完整机制。',limitations='仍需其他证据。').items()};fields['sample_count']=dict(value=None,status='NOT_VERIFIED',source_refs=[],reason='原记录未核实患者样本量，不能把两块区域写成患者重复。')
  inv=dict(version='pfs-experiment-inventory-1',paper_id='DOC',knowledge_sha256=rl.file_sha(self.f['kp']),formal_ready=False,counting_policy='One registered task; regions are not patients.',experiments=[dict(experiment_id='EXP1',display_name='部分参数尚未核实的任务',task_type='experiment',m1_evidence_ids=['E'],figure_ids=['F1'],source_refs=[ref],fields=fields)],method_sections=[])
  ip=Path(self.t.name)/'inventory.json';save(ip,inv);self.rebuild(ip);self.binding(method_ids=['EXP1']);a=self.assembled();self.assertTrue(a['valid'],a['gaps']);self.assertIn('未核实',a['content']['methods'][0]['counts']['text']);self.assertTrue(wc.validate_content(self.f['model'],a['content'])['valid'])
 def test_same_P_two_metric_records_remain_distinct(self):
  p=copy.deepcopy(self.f['k']['entities'][0]['parameters'][-1]);p['value'].update(id='Q_OTHER',metric_id='SPP1_TAM',test_id='SPP1_torus',label='另一个指标的P');self.f['k']['entities'][1]['parameters'].append(p);self.rebuild();a=self.assembled();self.assertTrue(a['valid'],a['gaps']);self.assertEqual(len(a['content']['quantitative_results']),2);self.assertEqual({x['test_id'] for x in a['content']['quantitative_results']},{'JT_torus','SPP1_torus'})
 def test_conflicting_registered_metric_values_blocked(self):
  p=copy.deepcopy(self.f['k']['entities'][0]['parameters'][-1]);p['value'].update(id='Q_CONFLICT',value='0.01');self.f['k']['entities'][1]['parameters'].append(p);self.rebuild();self.assertTrue(any(x['code']=='SOURCE_CONFLICT' for x in self.assembled()['gaps']))
 def test_missing_explanation_produces_task(self):
  self.binding(methods={'M':{'analysis':[]}});a=self.assembled();self.assertTrue(any(g['field']=='analysis' for g in a['gaps']))
 def test_no_same_page_source_upgrade(self):
  for e in self.f['k']['entities']:
   for p in e['parameters']:
    for r in p['source_refs']:r['locator'].pop('context_sha256',None)
  save(self.f['kp'],self.f['k']);net=en.build_network(self.f['kp']);save(self.f['np'],net);self.f['model']['network_snapshot']=net['snapshot'];self.f['model']['inputs']['network']['sha256']=rl.file_sha(self.f['np']);self.f['model']['snapshot']=rl.snapshot(self.f['model']);save(self.f['bp'],dict(logic_snapshot=self.f['model']['snapshot'],workbook_bindings=dict(figure_panels={'F1':['A']})))
  a=self.assembled();self.assertFalse(a['valid']);self.assertTrue(any(g['code']=='SOURCE_BINDING_REQUIRED' for g in a['gaps']))
 def test_review_empty_methods_sourced_not_applicable(self):
  f=fixture(Path(self.t.name)/'review',True,True);a=self.assembled(f);self.assertTrue(a['valid'],a['gaps']);self.assertEqual(a['content']['methods'],[]);self.assertTrue(wc.validate_content(f['model'],a['content'])['valid'])
 def test_review_without_NA_declaration_blocked(self):
  f=fixture(Path(self.t.name)/'review',True,False);a=self.assembled(f);a['content']['methods']=[];self.assertFalse(wc.validate_content(f['model'],a['content'])['valid'])
 def test_research_empty_methods_blocked(self):
  a=self.assembled();a['content']['methods']=[];self.assertFalse(wc.validate_content(self.f['model'],a['content'])['valid'])
 def test_forged_NA_source_blocked(self):
  f=fixture(Path(self.t.name)/'review',True,True);f['index']['facets']['methods']['applicability']['source_ids']=['MISSING'];save(f['ip'],f['index']);f['model']['inputs']['scientific_index']['sha256']=rl.file_sha(f['ip']);f['model']['snapshot']=rl.snapshot(f['model']);save(f['bp'],dict(logic_snapshot=f['model']['snapshot'],workbook_bindings=dict(figure_panels={'F1':['A']})));self.assertFalse(self.assembled(f)['valid'])
 def test_review_actual_methods_retained(self):
  f=fixture(Path(self.t.name)/'review',True,False);a=self.assembled(f);self.assertTrue(a['valid'],a['gaps']);self.assertEqual(len(a['content']['methods']),1)
 def test_systematic_review_must_not_omit_methods(self):
  f=fixture(Path(self.t.name)/'review',True,True);f['index']['review_subtype']='systematic';save(f['ip'],f['index']);f['model']['inputs']['scientific_index']['sha256']=rl.file_sha(f['ip']);f['model']['snapshot']=rl.snapshot(f['model']);save(f['bp'],dict(logic_snapshot=f['model']['snapshot'],workbook_bindings=dict(figure_panels={'F1':['A']})));self.assertFalse(self.assembled(f)['valid'])
 def test_unextracted_is_not_NOT_APPLICABLE(self):
  f=fixture(Path(self.t.name)/'review',True,True);f['index']['facets']['methods']['applicability']['basis_kind']='not_extracted';save(f['ip'],f['index']);f['model']['inputs']['scientific_index']['sha256']=rl.file_sha(f['ip']);f['model']['snapshot']=rl.snapshot(f['model']);save(f['bp'],dict(logic_snapshot=f['model']['snapshot'],workbook_bindings=dict(figure_panels={'F1':['A']})));self.assertFalse(self.assembled(f)['valid'])
 def test_actual_methods_cannot_claim_NOT_APPLICABLE(self):
  f=fixture(Path(self.t.name)/'review',True,True);f['index']['facets']['methods']['applicability']['actual_methods_present']=True;save(f['ip'],f['index']);f['model']['inputs']['scientific_index']['sha256']=rl.file_sha(f['ip']);f['model']['snapshot']=rl.snapshot(f['model']);save(f['bp'],dict(logic_snapshot=f['model']['snapshot'],workbook_bindings=dict(figure_panels={'F1':['A']})));self.assertFalse(self.assembled(f)['valid'])
 def test_NOT_APPLICABLE_source_identity_must_match_model(self):
  f=fixture(Path(self.t.name)/'review',True,True);s=f['index']['sources']['S'];s['start']=1;s['excerpt']=s['excerpt'][1:];s['excerpt_sha256']=hashlib.sha256(s['excerpt'].encode()).hexdigest();save(f['ip'],f['index']);f['model']['inputs']['scientific_index']['sha256']=rl.file_sha(f['ip']);f['model']['snapshot']=rl.snapshot(f['model']);save(f['bp'],dict(logic_snapshot=f['model']['snapshot'],workbook_bindings=dict(figure_panels={'F1':['A']})));self.assertFalse(self.assembled(f)['valid'])
 def test_reader_content_combination_explicitly_rejected(self):
  r=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/build_research_workbook.py'),'--model','unused','--graphs','unused','--output',str(Path(self.t.name)/'none.docx'),'--reader','--content','unused'],capture_output=True,text=True);self.assertEqual(r.returncode,2);self.assertIn('READER_CONTENT_COMBINATION_UNSUPPORTED',r.stderr)
 def cross_model(self):
  content=self.assembled()['content'];old=copy.deepcopy(self.f['model']);new=copy.deepcopy(old);new['snapshot']='different-reviewed-model'
  spec=dict(source_snapshot=old['snapshot'],target_snapshot=new['snapshot'],reviewer='fixture contextual review',owners={})
  for group in ['figures','methods']:
   for row in content[group]:spec['owners'][group+'/'+row['id']]=dict(target_node_ids=['N'],source_ids=['S'],granularity='figure_level' if group=='figures' else 'method_level',review_status='PARTIAL',reason='Explicit contextual correspondence; not equality from source ID.')
  return old,new,content,spec
 def test_shared_source_ids_do_not_suffice_for_cross_model_migration(self):
  old,new,c,spec=self.cross_model();self.assertEqual(wc.migration_alignment(old,new,c,None)['gaps'][0]['code'],'LEGACY_ALIGNMENT_REQUIRED')
 def test_cross_model_records_both_snapshots_and_granularity(self):
  old,new,c,spec=self.cross_model();r=wc.migration_alignment(old,new,c,spec);self.assertFalse(r['gaps']);self.assertEqual(r['source_snapshot'],old['snapshot']);self.assertEqual(r['target_snapshot'],new['snapshot']);self.assertEqual(len(r['fields']),14);self.assertTrue(all(x['semantic_equivalence']=='NOT_ASSERTED' for x in r['fields']))
 def test_stale_target_node_reference_blocks_migration(self):
  old,new,c,spec=self.cross_model();spec['owners']['figures/F1']['target_node_ids']=['DELETED'];self.assertTrue(wc.migration_alignment(old,new,c,spec)['gaps'])
 def test_renamed_historical_node_text_blocks_migration(self):
  old,new,c,spec=self.cross_model();old['nodes'][1]['title']='历史节点独有名称';c['figures'][0]['results']['text']='参见历史节点独有名称。';self.assertTrue(any(x['code']=='LEGACY_STALE_NODE_REFERENCE' for x in wc.migration_alignment(old,new,c,spec)['gaps']))
 def test_wrong_migration_snapshot_not_accepted(self):
  old,new,c,spec=self.cross_model();spec['source_snapshot']='unrelated';self.assertTrue(wc.migration_alignment(old,new,c,spec)['gaps'])
 def test_reader_source_labels_short_and_exceptions_visible(self):
  self.assertEqual(wc.source_label(self.f['model'],dict(source_ids=['S'],status='PARTIAL',identity='METHOD')),'p1 · 方法');self.assertIn('资料缺失',wc.source_label(self.f['model'],dict(source_ids=['S'],status='UNAVAILABLE',identity='LIMITATION')))
 def test_statistical_context_requires_actual_field_and_source(self):
  self.binding(statistical_reviews=[dict(field_ref=dict(group='figures',id='F1',field='results'),value='0.004',metric_id='immune_niche',test_id='JT_torus',review_note='A value on another field is insufficient.',reviewer='fixture reviewer',source_ids=['S'])]);self.assertTrue(any(x['code']=='STATISTICAL_CONTEXT_INVALID' for x in self.assembled()['gaps']))
 def legacy_quant(self,**extra):
  c=self.assembled()['content'];c.pop('assembly');c['inputs']=[r for r in c['inputs'] if r['path']!=str(self.f['bp'])];p=Path(self.t.name)/'legacy_quant.json';save(p,c)
  review=dict(metric_id='immune_niche',test_id='UNRESOLVED_TEST_IMPLEMENTATION',unit='probability',population_id='ducts',source_ids=['S'],review_status='PARTIAL',review_note='Implementation remains unresolved.',reviewer='fixture source review');review.update(extra)
  self.binding(legacy_content=dict(path=str(p),sha256=rl.file_sha(p),model=dict(path=str(self.f['mp']),sha256=rl.file_sha(self.f['mp'])),reviewer='fixture legacy review',quantitative_identities={'Q_IMMUNE':review}))
  return self.assembled()
 def test_identity_review_cannot_replace_original_quantitative_value(self):
  self.assertTrue(any(x['code']=='LEGACY_QUANTITATIVE_REVIEW_INVALID' for x in self.legacy_quant(value='0.01')['gaps']))
 def test_unresolved_quantitative_identity_retained_not_fabricated(self):
  a=self.legacy_quant();self.assertTrue(a['valid'],a['gaps']);q=next(r for r in a['content']['quantitative_results'] if r['origin']=='agent_prepared_legacy');self.assertEqual(q['value'],'0.004');self.assertEqual(q['test_id'],'UNRESOLVED_TEST_IMPLEMENTATION')

if __name__=='__main__':unittest.main()
