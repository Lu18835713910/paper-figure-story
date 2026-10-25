"""Set real OOXML Latin/East Asian font properties without splitting text runs."""
from pathlib import Path
from zipfile import ZipFile
import argparse,json,re

def patch_xml(text,latin='Times New Roman',east_asian='Microsoft YaHei'):
    pattern=r'<a:(rPr|defRPr|endParaRPr)\b([^>]*?)(?:/>|>([\s\S]*?)</a:\1>)'
    def replace(m):
        body=m.group(3) or ''
        body=re.sub(r'<a:(?:latin|ea|cs)\b[^>]*(?:/>|>[\s\S]*?</a:(?:latin|ea|cs)>)','',body)
        return '<a:'+m.group(1)+m.group(2)+'>'+body+'<a:latin typeface="'+latin+'"/><a:ea typeface="'+east_asian+'"/><a:cs typeface="'+latin+'"/></a:'+m.group(1)+'>'
    return re.sub(pattern,replace,text)

def apply_fonts(path):
    path=Path(path);temp=path.with_suffix('.fonts.tmp.pptx');changed=[]
    with ZipFile(path) as source,ZipFile(temp,'w') as target:
        for item in source.infolist():
            data=source.read(item.filename)
            if item.filename.startswith('ppt/') and item.filename.endswith('.xml'):
                old=data.decode('utf-8');new=patch_xml(old)
                if new!=old:changed.append(item.filename);data=new.encode('utf-8')
            target.writestr(item,data)
    temp.replace(path)
    return {'path':str(path),'latin':'Times New Roman','east_asian':'Microsoft YaHei','changed_parts':changed,'run_text_changed':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pptx');args=p.parse_args();print(json.dumps(apply_fonts(args.pptx),ensure_ascii=False))
