"""Small safety regression for shared style and explicit chrome archival."""
from pathlib import Path
import copy,sys,tempfile,unittest,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import polish_presentation as v
import visual_polish_locked as L
import visual_polish_deck_style as DS

class DeckStyle(unittest.TestCase):
 def record(self,text='来源与限制见备注'):
  return dict(id=9,text=L.norm(text),metadata='same',name='label',edge=None,cells=[])
 def item(self,text='来源与限制见备注',kind='management'):
  return dict(slide=1,shape_id=9,exact_text=L.norm(text),kind=kind)
 def test_01_shared_fonts_and_sizes(self):
  s=DS.style();self.assertEqual(s['fonts'],dict(east_asia='Microsoft YaHei',latin='Times New Roman'));self.assertEqual(s['roles']['body']['font_size'],18);self.assertEqual(s['roles']['title']['font_size'],27)
 def test_02_role_is_resolved_deterministically(self):
  d=dict(deck_style=dict(version='pfs-deck-style-1',sha256=v.digest(DS.STYLE_PATH)),shapes=[dict(style_role='body',text_style=dict(align='l',font_size=40))])
  r=DS.resolve(d);self.assertEqual(r['shapes'][0]['text_style']['font_size'],18);self.assertEqual(d['shapes'][0]['text_style']['font_size'],40)
 def test_03_changed_style_fails(self):
  with self.assertRaisesRegex(v.PolishError,'DECK_STYLE_DRIFT'):DS.resolve(dict(deck_style=dict(version='pfs-deck-style-1',sha256='bad')))
 def test_04_unknown_role_fails(self):
  with self.assertRaisesRegex(v.PolishError,'UNKNOWN_STYLE_ROLE'):DS.resolve(dict(deck_style=dict(version='pfs-deck-style-1',sha256=v.digest(DS.STYLE_PATH)),shapes=[dict(style_role='invented')]))
 def test_05_chrome_whitelist(self):self.assertTrue(DS.valid_archive(self.record(),self.item()))
 def test_06_science_cannot_be_archived(self):
  for text in ['WT 6.5 Å，KRR 18.1 Å','S4／S5尚未独立终审','来源与限制见备注；KRR外排较弱','CNNM4：膜蛋白']:
   self.assertFalse(DS.valid_archive(self.record(text),self.item(text)))
 def test_07_no_figure_or_edge_archival(self):
  for field in ['image','edge','cells']:
   r=self.record();r[field]={'has_science':True};self.assertFalse(DS.valid_archive(r,self.item()))
 def test_08_wrong_id_or_text_fails(self):
  a=self.item();a['shape_id']=3;self.assertFalse(DS.valid_archive(self.record(),a));a=self.item();a['exact_text']='different';self.assertFalse(DS.valid_archive(self.record(),a))
 def test_09_only_recognized_bibliography(self):
  txt='Bai et al., 2026, Cell 189:6097–6110 · Figure 2 · DOI 10.1016/j.cell.2026.06.039'
  self.assertTrue(DS.valid_archive(self.record(txt),self.item(txt,'bibliography')));self.assertFalse(DS.valid_archive(self.record(txt+'；支持某机制'),self.item(txt+'；支持某机制','bibliography')))
  injected=txt.replace('Figure 2','Figure 2；KRR外排减弱');self.assertFalse(DS.valid_archive(self.record(injected),self.item(injected,'bibliography')))
 def test_10_explicit_permission_required_for_deletion(self):
  a=dict(page_order=['p'],context_sha256='x',slides=[dict(slide=1,hidden=False,notes_sha256='n',objects=[self.record()])]);b=copy.deepcopy(a);b['slides'][0]['objects']=[]
  self.assertFalse(L.compare(a,b)['valid']);self.assertTrue(L.compare(a,b,[self.item()])['valid']);self.assertFalse(L.compare(a,b,[self.item('WT 6.5 Å')])['valid'])
 def test_11_persisted_lock_roundtrip(self):
  p=Path(__file__).resolve().parents[1]/'examples/layout_demo.pptx';a=L.snapshot(p);self.assertTrue(L.compare(json.loads(json.dumps(a)),L.snapshot(p))['valid'])
 def test_12_archive_ledger_keeps_original(self):
  lock=dict(slides=[dict(objects=[self.record()])]);plan=dict(pages=[dict(slide=1,archive_chrome=[self.item()])]);rows=DS.archive_records(lock,plan);self.assertEqual(rows[0]['original_object'],self.record())
 def test_13_flat_arrow_keeps_edge_identity(self):
  from lxml import etree as E
  q=E.fromstring(('<p:cxnSp xmlns:p="'+v.NS['p']+'" xmlns:a="'+v.NS['a']+'"><p:nvCxnSpPr><p:cNvPr id="5" name="RC_EDGE_same"/></p:nvCxnSpPr><p:spPr><a:ln><a:tailEnd type="triangle"/></a:ln></p:spPr></p:cxnSp>').encode())
  before=L.edge(q);L.style_shape(q,dict(flat=True,compact_arrowheads=True,line='A5B5CB'));self.assertEqual(before,L.edge(q));self.assertEqual(q.find('.//a:tailEnd',v.NS).get('len'),'sm')
 def test_14_no_style_does_not_claim_agent(self):self.assertEqual(DS.resolve(dict(shapes=[])),dict(shapes=[]))

if __name__=='__main__':unittest.main(verbosity=2)
