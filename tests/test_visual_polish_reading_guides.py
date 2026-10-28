from pathlib import Path
import sys,unittest,copy
from lxml import etree as E
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import polish_presentation as v
import visual_polish_locked as L
import visual_polish_connectors as C

class ReadingGuides(unittest.TestCase):
 def root(self,name='VP_PRESENTATION_ARROW'):
  return E.fromstring(('<p:sld xmlns:p="'+v.NS['p']+'" xmlns:a="'+v.NS['a']+'"><p:cSld><p:spTree><p:sp><p:nvSpPr><p:cNvPr id="3" name="'+name+'"/><p:cNvSpPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="914400" cy="914400"/></a:xfrm><a:ln><a:headEnd type="none"/><a:tailEnd type="triangle"/></a:ln></p:spPr></p:sp><p:sp><p:nvSpPr><p:cNvPr id="1" name="body1"/></p:nvSpPr><p:txBody><a:p><a:r><a:t>existing method</a:t></a:r></a:p></p:txBody></p:sp><p:sp><p:nvSpPr><p:cNvPr id="2" name="body2"/></p:nvSpPr><p:txBody><a:p><a:r><a:t>existing result</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>').encode())
 def edge(self):return dict(shape_ids=[3],source_shape_id=1,target_shape_id=2)
 def test_01_clear_vertical_gap(self):self.assertEqual(C.reading_points([1,1,4,1],[1,3,4,1]),[[3.,2.07],[3.,2.93]])
 def test_02_insufficient_gap_no_bending(self):
  with self.assertRaisesRegex(v.PolishError,'READING_GAP_TOO_SMALL'):C.reading_points([1,1,4,1],[1,2.1,4,1])
 def test_03_parallel_no_automatic_arrow(self):
  with self.assertRaisesRegex(v.PolishError,'READING_MODULES_NEED_COLUMN_ALIGNMENT'):C.reading_points([1,1,2,1],[5,1,2,1])
 def test_04_only_existing_presentation_role(self):self.assertTrue(C.is_reading_edge(self.root(),self.edge()));self.assertFalse(C.is_reading_edge(self.root('RC_EDGE_A_registered'),self.edge()))
 def test_05_scientific_registration_not_downgraded(self):
  for extra in [dict(identity='scientific_registered'),dict(source_relation_id='R7'),dict(m1_relation_id='R7')]:self.assertFalse(C.is_reading_edge(self.root(),dict(self.edge(),**extra)))
 def test_06_native_connector_preserves_identity_and_heads(self):
  q=v.top_shape(self.root(),3);before=L.edge(q);C.native_reading_connector(q,[[3,2.07],[3,2.93]]);self.assertEqual(q.tag,'{'+v.NS['p']+'}cxnSp');self.assertEqual(q.find('p:spPr/a:prstGeom',v.NS).get('prst'),'straightConnector1');self.assertEqual(q.find('p:spPr/a:xfrm/a:ext',v.NS).get('cx'),'0');self.assertEqual(before,L.edge(q))
  for actual,expected in zip(C.points(q),[[3.,2.07],[3.,2.93]]):
   for x,y in zip(actual,expected):self.assertAlmostEqual(x,y,places=7)
 def test_07_elbow_is_rejected(self):
  with self.assertRaisesRegex(v.PolishError,'READING_ARROW_MUST_BE_STRAIGHT_DOWN'):C.native_reading_connector(v.top_shape(self.root(),3),[[1,1],[1,2],[2,2]])
 def test_08_upward_or_slanted_is_rejected(self):
  for pp in [[[1,2],[1,1]],[[1,1],[1.2,2]]]:
   with self.assertRaisesRegex(v.PolishError,'READING_ARROW_MUST_BE_STRAIGHT_DOWN'):C.native_reading_connector(v.top_shape(self.root(),3),pp)
 def test_09_reading_axis_must_stay_in_column(self):
  with self.assertRaisesRegex(v.PolishError,'READING_AXIS_OUTSIDE_MODULE_COLUMN'):C.reading_points([1,1,4,1],[1,3,4,1],axis_x=7)
 def test_10_shared_style_visible(self):self.assertEqual(C.READING_STYLE['line'],'174994');self.assertEqual(C.READING_STYLE['line_width'],1.8);self.assertEqual(C.READING_STYLE['arrowhead_size'],'med')

if __name__=='__main__':unittest.main(verbosity=2)
