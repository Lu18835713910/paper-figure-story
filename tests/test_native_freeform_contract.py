"""Native polish -> official graph CLI, with real fixtures and fail-closed errors."""
from pathlib import Path
import os,json,copy,sys,subprocess,unittest
from pptx import Presentation
from pptx.oxml.ns import qn
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import research_logic as rl,visual_polish_locked as vp,delivery_contract as dc
@unittest.skipUnless(os.environ.get('PFS_C1_CASE'),'real graph fixture required')
class FreeformCLI(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.case=Path(os.environ['PFS_C1_CASE']);cls.model=Path(rl.load(cls.case/'lineage.json')['parent_model']);cls.reg=rl.load(cls.case/'logic_graph_manifest.json');cls.out=Path(os.environ['PFS_FREEFORM_OUTPUT']);cls.out.mkdir(parents=True,exist_ok=False)
 def setUp(self):
  self.d=self.out/self._testMethodName;self.d.mkdir();self.g=copy.deepcopy(self.reg)
 def shape(self):
  g=next(g for g in self.g['graphs'] if g['view']=='A');self.path=self.d/'A.pptx';self.pr=Presentation(g['pptx']);self.grow=g
  self.edge=next(s for s in self.pr.slides[0].shapes if s._element.tag==qn('p:cxnSp'))
  x,y=self.edge.begin_x,self.edge.begin_y;xx,yy=self.edge.end_x,self.edge.end_y
  # A real product polish function, not a fabricated custom geometry.
  from lxml import etree as E
  old=self.edge._element;q=E.fromstring(E.tostring(old));name=self.edge.name
  vp.path_shape(q,[(x/914400,y/914400),((x+xx)/2/914400,(y+yy)/2/914400),(xx/914400,yy/914400)])
  from pptx.oxml import parse_xml
  old.getparent().replace(old,parse_xml(E.tostring(q)));self.edge=next(s for s in self.pr.slides[0].shapes if s.name==name)
  return self.edge
 def cli(self,code=None):
  if hasattr(self,'pr'):
   self.pr.save(self.path);self.grow.update(pptx=str(self.path),pptx_sha256=rl.file_sha(self.path))
  p=self.d/'graphs.json';p.write_text(json.dumps(self.g,ensure_ascii=False),'utf8')
  cmd=[sys.executable,'-B',str(ROOT/'scripts/validate_story.py'),str(self.d),'--graph-manifest',str(p),'--logic-model',str(self.model),'--profile','full','--require-B']
  r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf8');(self.d/'stdout').write_text(r.stdout,'utf8');(self.d/'stderr').write_text(r.stderr,'utf8');(self.d/'command.json').write_text(json.dumps(dict(command=cmd,exit_code=r.returncode),ensure_ascii=False),'utf8')
  self.assertEqual(r.returncode,1 if code else 0,r.stdout+r.stderr)
  if code:self.assertIn(code,r.stdout+r.stderr)
 def test_connector(self):self.cli()
 def test_product_polish_freeform(self):self.shape();self.cli()
 def test_wrong_endpoint(self):
  s=self.shape();s.left+=20*914400;self.cli('NATIVE_ENDPOINT_DRIFT')
 def test_missing_identity(self):
  s=self.shape();s._element.find('.//'+qn('p:cNvPr')).set('descr','{}');self.cli('NATIVE_EDGE_IDENTITY_MISSING')
 def test_fake_identity(self):
  s=self.shape();c=s._element.find('.//'+qn('p:cNvPr'));d=json.loads(c.get('descr'));d['logic_edge']='FAKE';c.set('descr',json.dumps(d));self.cli('NATIVE_UNKNOWN_EDGE')
 def test_wrong_semantics(self):
  s=self.shape();c=s._element.find('.//'+qn('p:cNvPr'));d=json.loads(c.get('descr'));d['from_node']='FAKE';c.set('descr',json.dumps(d));self.cli('NATIVE_EDGE_SEMANTICS_DRIFT')
 def test_wrong_direction(self):
  s=self.shape();ln=s._element.find('.//'+qn('a:ln'));from pptx.oxml.xmlchemy import OxmlElement
  a=OxmlElement('a:headEnd');a.set('type','triangle');ln.append(a);self.cli('NATIVE_DIRECTION_DRIFT')
 def test_missing_path(self):
  s=self.shape();g=s._element.find('.//'+qn('a:pathLst'));g.getparent().remove(g);self.cli('NATIVE_EDGE_GEOMETRY_UNVERIFIABLE')
 def test_unsupported_curve(self):
  s=self.shape();s._element.find('.//'+qn('a:lnTo')).tag=qn('a:quadBezTo');self.cli('NATIVE_EDGE_GEOMETRY_UNVERIFIABLE')
 def test_decorative_fill(self):
  s=self.shape();s._element.find('.//'+qn('a:path')).set('fill','norm');self.cli('NATIVE_EDGE_GEOMETRY_UNVERIFIABLE')
 def test_rotation_unverifiable(self):
  s=self.shape();s._element.find('.//'+qn('a:xfrm')).set('rot','2700000');self.cli('NATIVE_EDGE_GEOMETRY_UNVERIFIABLE')
 def test_invalid_segment_name(self):
  s=self.shape();s.name='DECORATION';self.cli('NATIVE_EDGE_GEOMETRY_UNVERIFIABLE')
 def error_cli(self,kind):
  out=self.d/'delivery';script=ROOT/'scripts/run_pfs.py'
  driver="import runpy,sys;sys.path.insert(0,str(__import__('pathlib').Path(sys.argv[1]).parent));m=runpy.run_path(sys.argv[1]);m['main'].__globals__['deliver']=lambda a:(_ for _ in ()).throw("+kind+"('injected'));raise SystemExit(m['main'](sys.argv[2:]))"
  r=subprocess.run([sys.executable,'-B','-c',driver,str(script),'deliver','--research-logic',str(self.model),'--graphs','unused','--outdir',str(out),'--development-preview'],capture_output=True,text=True,encoding='utf8')
  (self.d/'stderr').write_text(r.stderr,'utf8');self.assertNotEqual(r.returncode,0);f=rl.load(out/'failure.json');self.assertFalse((out/'deliverables/Manifest.json').exists());return f
 def test_internal_error_record(self):self.assertEqual(self.error_cli('AttributeError')['code'],'INTERNAL_ERROR')
 def test_expected_error_record(self):self.assertEqual(self.error_cli('ValueError')['code'],'INPUT_OR_CONTRACT_REJECTED')
if __name__=='__main__':unittest.main()
