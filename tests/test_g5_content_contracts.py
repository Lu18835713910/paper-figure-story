"""G5 body-slot and relation-text consumer regressions; self-authored input only."""
from pathlib import Path
import copy,json,os,subprocess,sys,tempfile,unittest

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'scripts'))
sys.path.insert(0,str(BASE/'tests'))
from pptx import Presentation
from pptx.util import Inches
import build_pptx as bp,workbook_content as wc,research_logic as rl,evidence_network as en
from test_workbook_reuse import fixture,save


class PageBodyContract(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def cli(self,slides,precheck=True):
        data=self.root/'pages.json';save(data,dict(slides=slides))
        output=self.root/'pages.pptx'
        command=[sys.executable,'-B',str(BASE/'scripts/build_pptx.py'),str(data),'--output',str(output)]
        if precheck:command.append('--precheck')
        return subprocess.run(command,capture_output=True,text=True,encoding='utf8'),output

    def rendered(self,record,index=1):
        prs=Presentation();prs.slide_width=Inches(13.333);prs.slide_height=Inches(7.5)
        sl=prs.slides.add_slide(prs.slide_layouts[6]);bp.add_frame(sl,record['kind'],13.333,7.5)
        bp.populate_slide(sl,record,self.root/'pages.json',index,'Synthetic citation',False)
        return sl

    def test_legacy_points_survive_actual_cli_build(self):
        r,out=self.cli([dict(kind='text',title='Synthetic result',points=['Observed difference','Evidence remains limited'])],False)
        self.assertEqual(r.returncode,0,r.stderr)
        sl=Presentation(out).slides[0]
        shape=next(s for s in sl.shapes if s.name=='PFS_POINTS')
        self.assertIn('Observed difference',shape.text)
        self.assertIn('Evidence remains limited',sl.notes_slide.notes_text_frame.text)

    def test_text_bullets_feed_visible_points_slot_and_notes(self):
        record=dict(kind='text',title='Synthetic result',bullets=['Retained observation','Specific interpretation boundary'])
        sl=self.rendered(record)
        shape=next(s for s in sl.shapes if s.name=='PFS_POINTS')
        self.assertIn('Retained observation',shape.text)
        self.assertIn('Specific interpretation boundary',shape.text)
        self.assertIn('Retained observation',sl.notes_slide.notes_text_frame.text)

    def test_bullets_alias_passes_official_precheck_without_saving(self):
        r,out=self.cli([dict(kind='text',title='Synthetic result',bullets=['Observed difference'])])
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertTrue(json.loads(r.stdout)['valid'])
        self.assertFalse(out.exists())

    def test_missing_required_body_rejected_by_cli_with_slide_and_field(self):
        for kind,field in [('text','points'),('technology','points'),('conclusion','points'),('question','bullets')]:
            with self.subTest(kind=kind):
                r,out=self.cli([dict(kind='cover',title='Cover'),dict(kind=kind,title='Title is not body',lead='Lead is not body')])
                self.assertNotEqual(r.returncode,0)
                self.assertIn('PAGE_BODY_REQUIRED',r.stderr)
                self.assertIn('第2页',r.stderr)
                self.assertIn('/slides/1/'+field,r.stderr)
                self.assertFalse(out.exists())

    def test_empty_and_marker_only_body_items_rejected(self):
        for value in [[],[''],['   '],['•'],['- '],['1. '],['Valid observation',' ']]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError,'PAGE_BODY_(REQUIRED|EMPTY).*第3页.*?/slides/2/points'):
                    bp.body_content(dict(kind='text',points=value),3)

    def test_wrong_body_types_rejected_with_pointer(self):
        for value in [17,{'text':'Observation'},['Valid',{'text':'Invalid'}]]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError,'PAGE_BODY_TYPE.*?/slides/0/points'):
                    bp.body_content(dict(kind='text',points=value),1)

    def test_conflicting_body_fields_rejected(self):
        with self.assertRaisesRegex(ValueError,'PAGE_BODY_CONFLICT'):
            bp.body_content(dict(kind='text',points=['One observation'],bullets=['Another observation']),1)
        self.assertEqual(bp.body_content(dict(kind='text',points=[],bullets=['Retained fact']),1),['Retained fact'])

    def test_question_primary_and_alias_share_visible_slot(self):
        for key in ['points','bullets']:
            with self.subTest(key=key):
                sl=self.rendered(dict(kind='question',title='Question',**{key:['What differs under this condition?']}))
                self.assertIn('What differs',next(s for s in sl.shapes if s.name=='PFS_BULLETS').text)

    def test_cover_figure_and_graph_keep_separate_body_contracts(self):
        cover=dict(kind='cover',title='Synthetic paper')
        figure=dict(kind='figure',title='Observed assay',figure_ref='Synthetic Fig. 1',question='What differs?',design='Compare conditions',result='A measured difference',transition='Compare the boundary next')
        graph=dict(kind='logic',title='Parallel questions',diagram_type='parallel_tracks',nodes=[dict(id='Q',label='Question'),dict(id='N',label='Observation')],edges=[])
        for record in [cover,figure,graph]:
            with self.subTest(kind=record['kind']):self.assertIsNone(bp.body_content(record,1))
        bp.check_input(dict(slides=[cover,figure]))


class RelationTextContract(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def test_string_keeps_exact_registered_text(self):
        text='Shared source; no independent biological validation.'
        self.assertEqual(wc.relation_text(text,'/edges/0/alternatives'),text)

    def test_list_becomes_readable_without_mutating_input(self):
        alternatives=['Not a causal sequence.','Shared evidence is not counted twice.']
        original=copy.deepcopy(alternatives)
        self.assertEqual(wc.relation_text(alternatives,'/edges/0/alternatives'),'Not a causal sequence.；Shared evidence is not counted twice.')
        self.assertEqual(alternatives,original)

    def test_invalid_alternatives_rejected_with_exact_pointer(self):
        for value in [None,17,True,{},[],['valid',17],['valid',' ']]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError,'WORKBOOK_RELATION_TEXT_TYPE: /edges/1/alternatives:'):
                    wc.relation_text_fields(dict(edges=[dict(rationale='Valid',alternatives='Valid'),dict(rationale='Valid',alternatives=value)]))

    def test_invalid_alternatives_reported_by_learning_cli_without_docx(self):
        model=self.root/'invalid.json';save(model,dict(edges=[dict(rationale='Known explanation',alternatives={'unreviewed':'object'})]))
        output=self.root/'learning.docx'
        command=[sys.executable,'-B',str(BASE/'scripts/build_research_workbook.py'),'--model',str(model),'--graphs','unused','--output',str(output)]
        r=subprocess.run(command,capture_output=True,text=True,encoding='utf8')
        self.assertEqual(r.returncode,2,r.stderr)
        self.assertIn('WORKBOOK_RELATION_TEXT_TYPE: /edges/0/alternatives',r.stdout)
        self.assertFalse(output.exists())

    def test_explicit_logic_only_cli_also_rejects_invalid_type(self):
        model=self.root/'invalid-explicit.json';save(model,dict(edges=[dict(id='E',rationale='Known explanation',alternatives=17)]))
        output=self.root/'explicit.docx'
        command=[sys.executable,'-B',str(BASE/'scripts/build_research_workbook.py'),'--model',str(model),'--graphs','unused','--output',str(output),'--scope','logic-only']
        r=subprocess.run(command,capture_output=True,text=True,encoding='utf8')
        self.assertNotEqual(r.returncode,0)
        self.assertIn('WORKBOOK_RELATION_TEXT_TYPE: /edges/0/alternatives',r.stderr)
        self.assertFalse(output.exists())

    def test_valid_list_survives_official_model_validation_and_assembly(self):
        f=fixture(self.root/'source')
        k=f['k'];k['figures'].append({**copy.deepcopy(k['figures'][0]),'id':'F2','label':'Second synthetic Figure'})
        m2=copy.deepcopy(k['entities'][0]);m2['id']='M2'
        e2=copy.deepcopy(k['entities'][1]);e2['id']='E2'
        k['entities'].extend([m2,e2])
        story=copy.deepcopy(k['stories'][0]);story.update(id='RSU2',method_ids=['M2'],evidence_ids=['E2'],figure_refs=['F2'],presentation_order=2,original_section_order=[2]);k['stories'].append(story)
        save(f['kp'],k);net=en.build_network(f['kp']);save(f['np'],net)
        model=f['model'];model['network_snapshot']=net['snapshot'];model['inputs']['network']['sha256']=rl.file_sha(f['np'])
        for node,entity in zip(model['nodes'],['M','M2']):node['source_entity_ids']=[entity];node['statement_ids']=[]
        alternatives=['Not a true experimental chronology.','Shared measurement does not add independent evidence.']
        model['edges'][0]['alternatives']=alternatives
        save(model['inputs']['adjudication']['path'],dict(nodes=model['nodes'],edges=model['edges']))
        model['inputs']['adjudication']['sha256']=rl.file_sha(model['inputs']['adjudication']['path'])
        model['snapshot']=rl.snapshot(model);save(f['mp'],model)
        bindings=dict(logic_snapshot=model['snapshot'],workbook_bindings=dict(figure_panels={'F1':['A'],'F2':['A']}));save(f['bp'],bindings)
        self.assertTrue(rl.validate_model(model)['valid'])
        before=copy.deepcopy(model)
        result=wc.assemble_content(model,f['bp'])
        linktexts=[row['links']['text'] for row in result['content']['figures']]
        self.assertTrue(any('Not a true experimental chronology.；Shared measurement does not add independent evidence.' in text for text in linktexts),linktexts)
        self.assertEqual(model,before)


if __name__=='__main__':unittest.main()
