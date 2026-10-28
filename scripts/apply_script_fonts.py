"""Set real OOXML Latin/East Asian font properties without splitting text runs."""
from pathlib import Path
from zipfile import ZipFile
import argparse,json,re,os

def font_availability():
    if os.name!='nt':return {'status':'UNVERIFIED_ENVIRONMENT','required':['Microsoft YaHei','Times New Roman']}
    root=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'
    paths=[root/n for n in ['msyh.ttc','msyhbd.ttc','times.ttf','timesbd.ttf','timesi.ttf','timesbi.ttf']]
    missing=[str(p) for p in paths if not p.is_file()]
    if missing:raise RuntimeError('REQUIRED_FONT_MISSING: '+', '.join(missing))
    return {'status':'AVAILABLE','files':[str(p) for p in paths]}

def patch_xml(text,latin='Times New Roman',east_asian='Microsoft YaHei'):
    pattern=r'<a:(rPr|defRPr|endParaRPr)\b([^>]*?)(?:/>|>([\s\S]*?)</a:\1>)'
    def replace(m):
        body=m.group(3) or ''
        body=re.sub(r'<a:(?:latin|ea|cs)\b[^>]*(?:/>|>[\s\S]*?</a:(?:latin|ea|cs)>)','',body)
        return '<a:'+m.group(1)+m.group(2)+'>'+body+'<a:latin typeface="'+latin+'"/><a:ea typeface="'+east_asian+'"/><a:cs typeface="'+latin+'"/></a:'+m.group(1)+'>'
    return re.sub(pattern,replace,text)

def apply_fonts(path):
    availability=font_availability();path=Path(path);temp=path.with_suffix('.fonts.tmp.pptx');changed=[]
    with ZipFile(path) as source,ZipFile(temp,'w') as target:
        for item in source.infolist():
            data=source.read(item.filename)
            if item.filename.startswith('ppt/') and item.filename.endswith('.xml'):
                old=data.decode('utf-8');new=patch_xml(old)
                if new!=old:changed.append(item.filename);data=new.encode('utf-8')
            target.writestr(item,data)
    temp.replace(path)
    return {'path':str(path),'latin':'Times New Roman','east_asian':'Microsoft YaHei','changed_parts':changed,'run_text_changed':False,'font_availability':availability}

def apply_docx_fonts(path):
    from lxml import etree as ET
    availability=font_availability();path=Path(path);temp=path.with_suffix('.fonts.tmp.docx');changed=[]
    ns='http://schemas.openxmlformats.org/wordprocessingml/2006/main';q=lambda x:'{'+ns+'}'+x
    with ZipFile(path) as source,ZipFile(temp,'w') as target:
        for item in source.infolist():
            data=source.read(item.filename)
            if item.filename.startswith('word/') and item.filename.endswith('.xml'):
                root=ET.fromstring(data);modified=False
                for rp in root.iter(q('rPr')):
                    rf=rp.find(q('rFonts'))
                    if rf is None:rf=ET.SubElement(rp,q('rFonts'))
                    for key in ['asciiTheme','hAnsiTheme','eastAsiaTheme','cstheme','csTheme']:rf.attrib.pop(q(key),None)
                    for key,font in [('ascii','Times New Roman'),('hAnsi','Times New Roman'),('eastAsia','Microsoft YaHei'),('cs','Times New Roman')]:rf.set(q(key),font)
                    modified=True
                if modified:data=ET.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True);changed.append(item.filename)
            target.writestr(item,data)
    temp.replace(path)
    return {'path':str(path),'changed_parts':changed,'ascii':'Times New Roman','hAnsi':'Times New Roman','eastAsia':'Microsoft YaHei','run_text_changed':False,'font_availability':availability}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pptx');args=p.parse_args();print(json.dumps((apply_docx_fonts if Path(args.pptx).suffix.lower()=='.docx' else apply_fonts)(args.pptx),ensure_ascii=False))
