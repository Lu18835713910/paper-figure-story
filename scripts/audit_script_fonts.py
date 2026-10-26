"""Inspect actual editable OOXML properties and PDF text fonts without rendering."""
from pathlib import Path,PurePosixPath
from zipfile import ZipFile
import argparse,collections,json,posixpath,re
from lxml import etree as E
from apply_script_fonts import font_availability
A='http://schemas.openxmlformats.org/drawingml/2006/main';P='http://schemas.openxmlformats.org/presentationml/2006/main';W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS={'a':A,'p':P,'w':W};LATIN='Times New Roman';EA='Microsoft YaHei'
def check(path):
 path=Path(path);issues=[];counts=collections.Counter();extras={}
 if path.suffix.lower()=='.pdf':
  import pdfplumber
  pages=[]
  with pdfplumber.open(path) as pdf:
   for i,page in enumerate(pdf.pages):
    counts.update(c['fontname'] for c in page.chars);bad=[c for c in page.chars if c['x0']<-.5 or c['x1']>page.width+.5 or c['top']<-.5 or c['bottom']>page.height+.5]
    if bad:issues.append({'code':'PDF_TEXT_OUTSIDE_PAGE','page':i+1,'count':len(bad)})
    pages.append({'page':i+1,'width':page.width,'height':page.height,'characters':len(page.chars),'images':len(page.images),'text':page.extract_text() or ''})
   for name in counts:
    if not any(t in re.sub(r'[\s-]','',name) for t in ['TimesNewRoman','MicrosoftYaHei']):issues.append({'code':'PDF_FONT_SUBSTITUTION','font':name})
  extras={'pages':pages,'bitmap_fonts':'Original Figure/image fonts are not editable PDF text; diagram fonts verified in linked PPTX.'}
 else:
  with ZipFile(path) as z:
   if path.suffix.lower()=='.pptx':
    root=E.fromstring(z.read('ppt/presentation.xml'));rels=E.fromstring(z.read('ppt/_rels/presentation.xml.rels'));rm={e.get('Id'):e.get('Target') for e in rels};parts=[]
    for e in root.findall('p:sldIdLst/p:sldId',NS):parts.append(posixpath.normpath(posixpath.join('ppt',rm[e.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')])).lstrip('/'))
    for part in parts:
     r=E.fromstring(z.read(part))
     for pr in r.xpath('//a:rPr|//a:defRPr|//a:endParaRPr',namespaces=NS):
      counts['properties']+=1
      for tag,font in [('latin',LATIN),('ea',EA)]:
       f=pr.find('a:'+tag,NS)
       if f is None or f.get('typeface')!=font:issues.append({'code':'PPT_SCRIPT_FONT','part':part,'script':tag,'actual':f.get('typeface') if f is not None else None})
    extras={'live_slides':len(parts),'scope':'Live slide run/default properties; original Figure rasters excluded.'}
   elif path.suffix.lower()=='.docx':
    for part in [n for n in z.namelist() if n.startswith('word/') and n.endswith('.xml')]:
     r=E.fromstring(z.read(part))
     for rf in r.findall('.//w:rFonts',NS):
      counts['properties']+=1
      for attr,font in [('ascii',LATIN),('hAnsi',LATIN),('eastAsia',EA)]:
       if rf.get('{'+W+'}'+attr)!=font:issues.append({'code':'DOCX_SCRIPT_FONT','part':part,'script':attr,'actual':rf.get('{'+W+'}'+attr)})
      if any(k.endswith('Theme') for k in rf.attrib):issues.append({'code':'DOCX_THEME_OVERRIDE','part':part})
   else:raise ValueError('Unsupported artifact extension')
 return {'path':str(path),'valid':not issues,'issues':issues,'counts':dict(counts),**extras}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('paths',nargs='+',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();result={'font_availability':font_availability(),'files':[check(f) for f in a.paths]};a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8');summary=[(Path(f['path']).name,f['valid'],len(f['issues'])) for f in result['files']];print(json.dumps(summary,ensure_ascii=False));return 0 if all(f['valid'] for f in result['files']) else 1
if __name__=='__main__':raise SystemExit(main())
