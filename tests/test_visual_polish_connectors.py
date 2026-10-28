from pathlib import Path
import sys,unittest
from lxml import etree as E
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import visual_polish_connectors as C
import polish_presentation as v

class ConnectorGeometry(unittest.TestCase):
 def test_01_horizontal_avoids_label(self):self.assertFalse(C.rect_hit([0,0],[3,0],[1,.2,1,.4],.05))
 def test_02_line_through_label_rejected(self):self.assertTrue(C.rect_hit([0,.4],[3,.4],[1,.2,1,.4],.05))
 def test_03_diagonal_hits_node(self):self.assertTrue(C.rect_hit([0,0],[3,3],[1,1,1,1]))
 def test_04_label_overlap(self):self.assertTrue(C.overlap([0,0,2,1],[1,.5,2,1]));self.assertFalse(C.overlap([0,0,1,1],[1.1,0,1,1]))
 def test_05_crossing_has_no_inferred_junction(self):self.assertEqual(C.path_intersections([[0,1],[2,1]],[[1,0],[1,2]]),[[1.,1.]])
 def test_06_tangent_arrow_fails(self):self.assertFalse(C.correct_normal([0,.5],[0,0],[0,0,1,1],False))
 def test_07_outward_target_fails(self):self.assertFalse(C.correct_normal([0,.5],[.2,.5],[0,0,1,1],False));self.assertTrue(C.correct_normal([0,.5],[-.2,.5],[0,0,1,1],False))
 def test_08_source_direction(self):self.assertTrue(C.correct_normal([1,.5],[2,.5],[0,0,1,1],True));self.assertFalse(C.correct_normal([1,.5],[.5,.5],[0,0,1,1],True))
 def shape(self,geometry,flip=''):
  return E.fromstring(('<p:cxnSp xmlns:p="'+v.NS['p']+'" xmlns:a="'+v.NS['a']+'"><p:spPr><a:xfrm '+flip+'><a:off x="914400" y="914400"/><a:ext cx="1828800" cy="1828800"/></a:xfrm>'+geometry+'</p:spPr></p:cxnSp>').encode())
 def test_09_native_freeform_decode(self):
  q=self.shape('<a:custGeom><a:pathLst><a:path w="100" h="100"><a:moveTo><a:pt x="0" y="0"/></a:moveTo><a:lnTo><a:pt x="50" y="0"/></a:lnTo><a:lnTo><a:pt x="50" y="100"/></a:lnTo></a:path></a:pathLst></a:custGeom>');self.assertEqual(C.points(q),[[1.,1.],[2.,1.],[2.,3.]])
 def test_10_native_reverse_connector_decode(self):self.assertEqual(C.points(self.shape('<a:prstGeom prst="straightConnector1"/>','flipH="1"')),[[3.,1.],[1.,3.]])

if __name__=='__main__':unittest.main(verbosity=2)
