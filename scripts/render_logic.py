"""Portable native PPT backend for the existing source-validated scene plan.
No layout inference: consumes project_research_logic/project_evidence_products scenes.
"""
import argparse,json,sys,importlib.util,copy
from pathlib import Path

def dependencies():
    missing=[x for x in ['pptx','PIL','lxml'] if importlib.util.find_spec(x) is None]
    return dict(backend='portable-python-pptx',available=not missing,missing=missing,install='python -m pip install -r requirements.txt',host_modules_required=False)

# Report dependencies before importing authoring libraries or opening scientific inputs.
if __name__=='__main__':
    dep=dependencies()
    if '--check-dependencies' in sys.argv or not dep['available']:
        print(json.dumps(dep));raise SystemExit(0 if dep['available'] else 2)
# Keep sibling modules available even with Python's isolated (-I) invocation.
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.enum.shapes import MSO_CONNECTOR,MSO_SHAPE
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.dml.color import RGBColor
from pptx.oxml.xmlchemy import OxmlElement
import research_logic as rl


def validate_package(path):
    """Read back the complete OPC graph; file existence/ZIP validity is insufficient."""
    import posixpath
    from urllib.parse import unquote
    from zipfile import ZipFile
    from lxml import etree as ET
    R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    P='http://schemas.openxmlformats.org/presentationml/2006/main'
    roots={'slide':'sld','notesSlide':'notes','slideLayout':'sldLayout','slideMaster':'sldMaster','notesMaster':'notesMaster'}
    with ZipFile(path) as z:
        if z.testzip():raise ValueError('PPTX_CRC_FAILURE')
        names=set(z.namelist());maps={}
        for name in names:
            if not name.endswith('.rels'):continue
            owner='' if name=='_rels/.rels' else posixpath.join(posixpath.dirname(posixpath.dirname(name)),posixpath.basename(name)[:-5])
            rels={}
            for rel in ET.fromstring(z.read(name)):
                rid=rel.get('Id')
                if rid in rels:raise ValueError('DUPLICATE_RELATIONSHIP: '+name+' '+str(rid))
                rels[rid]=rel
                if rel.get('TargetMode')=='External':continue
                target=unquote(rel.get('Target','').split('#',1)[0])
                part=posixpath.normpath(posixpath.join(posixpath.dirname(owner),target)) if not target.startswith('/') else target.lstrip('/')
                if part not in names:raise ValueError('DANGLING_RELATIONSHIP: '+name+' '+str(rid)+' -> '+part)
                kind=rel.get('Type','').rsplit('/',1)[-1]
                if kind in roots and ET.fromstring(z.read(part)).tag!='{'+P+'}'+roots[kind]:raise ValueError('RELATIONSHIP_TARGET_TYPE: '+name+' '+str(rid))
            maps[owner]=rels
        for name in names:
            if not name.endswith('.xml'):continue
            for element in ET.fromstring(z.read(name)).iter():
                for key,value in element.attrib.items():
                    if key.startswith('{'+R+'}') and value not in maps.get(name,{}):raise ValueError('UNBOUND_RELATIONSHIP_ID: '+name+' '+value)
    prs=Presentation(path)
    # Force lazy slide/notes/image parsing before an output can be considered valid.
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:_=shape.text
            if shape.shape_type==13:_=shape.image.blob
        if slide.has_notes_slide:_=slide.notes_slide.notes_text_frame.text
    return prs


def slide_content(slide):
    """Stable content identity independent of OPC slide numbering and rIds."""
    import hashlib
    from lxml import etree as ET
    def canonical(part):
        root=ET.fromstring(part.blob)
        for element in root.iter():
            for key,value in list(element.attrib.items()):
                if key.startswith('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'):
                    rel=part.rels[value]
                    payload=rel.target_ref if rel.is_external else hashlib.sha256(rel.target_part.blob).hexdigest()
                    element.set(key,rel.reltype+'|'+payload)
        return hashlib.sha256(ET.tostring(root,method='c14n')).hexdigest()
    # Includes shape geometry, visible text, style, image bytes, source descriptions,
    # hyperlinks and notes. Relationships use payload identities, not renamed paths.
    return dict(slide=canonical(slide.part),notes=canonical(slide.notes_slide.part) if slide.has_notes_slide else None,
                texts=[s.text for s in slide.shapes if s.has_text_frame],
                images=[hashlib.sha256(s.image.blob).hexdigest() for s in slide.shapes if s.shape_type==13])


def validate_scene(slide,scene):
    """Verify actual native objects, source descriptors and model identity."""
    nodes={};edges=set()
    expected={e['id']:e for e in scene['elements'] if e.get('logic_node_id') and e['kind']=='text'}
    found=set()
    relation_map={a['source_logic_relation_id']:a for a in scene.get('connectors',[]) if a.get('source_logic_relation_id')}
    for shape in slide.shapes:
        if shape.shape_type==13:raise ValueError('RASTER_LOGIC_REPLACEMENT')
        cn=shape._element.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr')
        desc=cn.get('descr','') if cn is not None else ''
        if not desc:continue
        info=json.loads(desc)
        if 'logic_node_id' in info:
            item=next((e for e in expected.values() if shape.name=='RC_'+scene['id']+'_'+e['id']),None)
            if item is None or info!={'logic_node_id':item['logic_node_id'],'source_node_ids':item.get('source_node_ids',[]),'statement_ids':item.get('statement_ids',[])} or shape.text!=item['text']:raise ValueError('NATIVE_NODE_SOURCE_DRIFT: '+shape.name)
            found.add(item['id']);nodes[info['logic_node_id']]=True
        if info.get('logic_edge'):
            edge=relation_map.get(info['logic_edge'])
            if edge is None or info['identity']!=edge['identity'] or info['relation_type']!=edge.get('relation_type') or not shape._element.tag.endswith('cxnSp'):raise ValueError('NATIVE_EDGE_IDENTITY_DRIFT')
            edges.add(info['logic_edge'])
    if found!=set(expected) or set(nodes)!=set(scene['source_logic_node_ids']) or edges!=set(scene['source_logic_relation_ids']):raise ValueError('NATIVE_TOPOLOGY_LOSS')
    notes=slide.notes_slide.notes_text_frame.text
    if scene.get('logic_snapshot','') not in notes or any(s not in notes for s in scene.get('notes',{}).get('logic_source_ids',[])):raise ValueError('NATIVE_NOTES_SOURCE_DRIFT')
    # Validate actual serialized direction and path, not just relationship IDs.
    anchors=[(s,e) for s in slide.shapes for e in expected.values() if s.name=='RC_'+scene['id']+'_'+e['id']]
    if anchors:
        shape,element=anchors[0];p=element['position'];factor=shape.width/p['width'];ox=shape.left-p['left']*factor;oy=shape.top-p['top']*factor
        for edge in scene.get('connectors',[]):
            parts=sorted([s for s in slide.shapes if s.name.startswith('RC_EDGE_'+scene['id']+'_'+edge['id']+'_')],key=lambda s:int(s.name.rsplit('_',1)[1]))
            segments=[(a,b) for a,b in zip(display_points(edge),display_points(edge)[1:]) if a!=b]
            if len(parts)!=len(segments):raise ValueError('NATIVE_EDGE_PATH_DRIFT')
            for i,(s,(a,b)) in enumerate(zip(parts,segments)):
                actual=[s.begin_x,s.begin_y,s.end_x,s.end_y];wanted=[ox+a[0]*factor,oy+a[1]*factor,ox+b[0]*factor,oy+b[1]*factor]
                if any(abs(x-y)>8 for x,y in zip(actual,wanted)):raise ValueError('NATIVE_EDGE_ENDPOINT_DRIFT')
                tail=s._element.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}tailEnd')
                head=s._element.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}headEnd')
                arrow=tail is not None and tail.get('type','none')!='none'
                if arrow!=bool(edge.get('arrow') and i==len(parts)-1) or (head is not None and head.get('type','none')!='none'):raise ValueError('NATIVE_EDGE_DIRECTION_DRIFT')

def display_points(edge):
    """Pure rendering transform: pull back the arrowhead endpoint so the
    triangle is not clipped by the filled node frame painted earlier in the
    z-order. The scientific scene model is NEVER modified here; both
    draw_scene() and validate_scene() consume this same function so the
    serialized geometry and its contract stay in agreement.
    """
    pts=edge['points']
    if not edge.get('arrow') or len(pts)<2:return pts
    from project_research_logic import retreat_arrow_endpoint
    return retreat_arrow_endpoint(pts)

def color(s):return RGBColor.from_string(s.lstrip('#'))
def text(slide,name,value,p,size,bold=False,fill='#18365C',align='left',scale=1):
    t=slide.shapes.add_textbox(*[int(v) for v in p]);t.name=name;tf=t.text_frame;tf.clear();tf.word_wrap=False
    tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=0
    from pptx.enum.text import PP_ALIGN,MSO_ANCHOR
    tf.vertical_anchor=MSO_ANCHOR.MIDDLE
    for i,line in enumerate(value.split('\n')):
        q=tf.paragraphs[0] if i==0 else tf.add_paragraph();q.space_after=Pt(0);q.space_before=Pt(0);q.alignment={'left':PP_ALIGN.LEFT,'center':PP_ALIGN.CENTER,'right':PP_ALIGN.RIGHT}[align]
        r=q.add_run();r.text=line;r.font.size=Pt(size*.75*scale);r.font.bold=bold;r.font.color.rgb=color(fill);r.font.name='Times New Roman'
    return t

def draw_scene(slide,product,scene,frame=None,omit_scene_title=False):
    W,H=product['width'],product['height']
    if frame is None:frame=(0,0,Inches(W/96),Inches(H/96))
    x,y,w,h=frame;factor=min(w/W,h/H);ox=x+(w-W*factor)/2;oy=y+(h-H*factor)/2;scale=factor/Inches(1/96)
    def rect(p):return [ox+p['left']*factor,oy+p['top']*factor,p['width']*factor,p['height']*factor]
    # Connector identity and endpoints are preserved in DrawingML metadata.
    for a in scene.get('connectors',[]):
        dpts=display_points(a)
        segments=[(u,v) for u,v in zip(dpts,dpts[1:]) if u!=v]
        for j,((ax,ay),(bx,by)) in enumerate(segments,1):
            c=slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,int(ox+ax*factor),int(oy+ay*factor),int(ox+bx*factor),int(oy+by*factor));c.name='RC_EDGE_'+scene['id']+'_'+a['id']+'_'+str(j)
            c.line.color.rgb=color(a.get('color','#174994'));c.line.width=Pt(max(.8,a.get('stroke_width',2.2)*.75*scale))
            if a.get('dashed'):c.line.dash_style=MSO_LINE_DASH_STYLE.DASH
            if a.get('arrow') and j==len(segments):
                # Large canvases are downscaled on PNG/PDF export; a 'med' head
                # collapses to a few pixels and reads as no direction at all.
                tail=OxmlElement('a:tailEnd');tail.set('type','triangle');tail.set('w','lg');tail.set('len','lg');c._element.spPr.get_or_add_ln().append(tail)
            cn=c._element.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr');cn.set('descr',json.dumps({'logic_edge':a.get('source_logic_relation_id'),'identity':a['identity'],'relation_type':a.get('relation_type'),'from_node':a.get('from_node'),'to_node':a.get('to_node')},ensure_ascii=False))
    for e in scene['elements']:
        if omit_scene_title and e['id']==scene['id']+'_title':continue
        name='RC_'+scene['id']+'_'+e['id'];p=rect(e['position'])
        if e['kind']=='rect':
            q=slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,*map(int,p));q.name=name;q.fill.solid();q.fill.fore_color.rgb=color(e.get('fill','#FFFFFF'));q.line.color.rgb=color(e.get('stroke','#B8CBE6'))
        elif e['kind']=='text':
            q=text(slide,name,e['text'],p,e['font_size'],e.get('bold',False),e.get('color','#18365C'),e.get('align','left'),scale)
            if e.get('logic_node_id'):q._element.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr').set('descr',json.dumps({'logic_node_id':e['logic_node_id'],'source_node_ids':e.get('source_node_ids',[]),'statement_ids':e.get('statement_ids',[])},ensure_ascii=False))
        elif e['kind']=='image':raise ValueError('LOGIC_PLAN_MUST_BE_NATIVE_NOT_IMAGE')
        else:raise ValueError('UNSUPPORTED_PORTABLE_ELEMENT: '+e['kind'])
    local=scene['coverage'].get('scope')=='local';fy=H-42 if local else H-32
    text(slide,'RC_CITATION',scene.get('citation',''),[ox+60*factor,oy+fy*factor,(W-120)*factor,32*factor],max(16,10/.75/scale),False,'#61748A',scale=scale)
    notes=scene.get('notes',{});slide.notes_slide.notes_text_frame.text='科学问题：'+str(notes.get('scientific_question',scene['title']))+'\n关系表示证据与论文论证，不表示实验日历。\n来源索引：'+', '.join(notes.get('logic_source_ids',[]))+'\n模型快照：'+scene.get('logic_snapshot','')+'\n科学审核PARTIAL；缺失补件与限制见配套来源记录。'
    if local:
        frame=slide.notes_slide.notes_text_frame;frame.text+='\n完整B的局部科研视图；未显示关系仍保留在独立B。\n'
        for r in notes['local_node_records']:
            frame.text+='\n'+r['id']+' '+r['title']+'\n'+'\n'.join(k+'：'+r['fields'][k] for k in ['method','discovery','meaning'] if k in r['fields'])+'\n来源：'+','.join(r['source_ids'])+'\n'
        for r in notes['logic_relations']:frame.text+='\n'+r['id']+' ['+r['type']+' / '+r['identity']+'] '+r['rationale']+'；限制：'+r['alternatives']
    return dict(view=scene['coverage']['view'],node_ids=scene['source_logic_node_ids'],edge_ids=scene['source_logic_relation_ids'],logic_snapshot=scene['logic_snapshot'],native=True,min_display_font_pt=min((e['font_size']*.75*scale for e in scene['elements'] if e['kind']=='text'),default=0),min_node_font_pt=min((e['font_size']*.75*scale for e in scene['elements'] if e.get('logic_node_id') and e['kind']=='text'),default=0))

def render(network,plan_path,output,metadata=None,main_pptx=None,page_map=None,main_output=None):
    import project_evidence_products as pp
    net=rl.load(network);plan=rl.load(plan_path);meta=rl.load(metadata) if metadata else {}
    reference=meta.get('full_b_reference') or ('Complete_B.editable.pptx' if main_output and any(p['slides'][0].get('coverage',{}).get('view')=='B' for p in plan['products']) else None)
    q=pp.validate_products(net,plan,meta)
    if not q['valid']:raise ValueError('PLAN_VALIDATION: '+str(q))
    if not plan.get('research_logic'):raise ValueError('SOURCE_LOGIC_MODEL_REQUIRED')
    m=rl.load(plan['research_logic']['path']);q=rl.validate_model(m,net)
    if not q['valid']:raise ValueError('SOURCE_LOGIC_INVALID: '+str(q))
    for product in plan['products']:
        if len(product['slides'])!=1 or any(e['kind'] not in ['text','rect'] for e in product['slides'][0]['elements']):raise ValueError('UNSUPPORTED_PORTABLE_SCENE_BEFORE_AUTHORING')
    out=Path(output);out.mkdir(parents=True,exist_ok=True);files=[];scenes={}
    if (out/'render_receipt.json').exists():raise ValueError('OUTPUT_EXISTS: render receipt already exists')
    if main_pptx:validate_package(main_pptx)
    for product in plan['products']:
        if len(product['slides'])!=1:raise ValueError('PORTABLE_LOGIC_ONE_CANVAS_PER_VIEW')
        scene=product['slides'][0];scenes[scene['coverage']['view']]=(product,scene)
        f=out/(product['kind']+'_'+plan['profile']+'.pptx')
        if f.exists():raise ValueError('OUTPUT_EXISTS: '+str(f))
        prs=Presentation();prs.slide_width=Inches(product['width']/96);prs.slide_height=Inches(product['height']/96);sl=prs.slides.add_slide(prs.slide_layouts[6]);info=draw_scene(sl,product,scene);prs.save(f)
        from apply_script_fonts import apply_fonts
        apply_fonts(f)
        reopened=validate_package(f)
        if len(reopened.slides)!=1:raise ValueError('SLIDE_COUNT_DRIFT')
        validate_scene(reopened.slides[0],scene)
        files.append(dict(kind=product['kind'],path=str(f.resolve()),sha256=rl.file_sha(f),slides=1,width=product['width'],height=product['height'],**info))
    merged=[]
    if main_pptx:
        if not main_output or Path(main_output).exists():raise ValueError('NEW_MAIN_OUTPUT_REQUIRED')
        prs=Presentation(main_pptx);original=[slide_content(s) for s in prs.slides];prs.core_properties.identifier=m['snapshot'];changed_parts=set();targets={}
        for view,numbers in (page_map or {}).items():
          if view not in scenes:raise ValueError('UNREGISTERED_LOGIC_VIEW: '+view)
          for number in (numbers if isinstance(numbers,list) else [numbers]):
            number=int(number)
            if not 1<=number<=len(original) or number in targets:raise ValueError('INVALID_MAIN_PAGE_MAP')
            product,scene=scenes[view];targets[number]=scene;sl=prs.slides[number-1];oldnotes=sl.notes_slide.notes_text_frame.text;oldtext='\n'.join(s.text for s in sl.shapes if s.has_text_frame)
            if any(s.shape_type==13 for s in sl.shapes):raise ValueError('MAIN_LOGIC_SLOT_CONTAINS_FIGURE: '+str(number))
            changed_parts.add(str(sl.part.partname).lstrip('/'));changed_parts.add(str(sl.notes_slide.part.partname).lstrip('/'))
            old_title=next((s.text for s in sl.shapes if s.name=='PFS_TITLE' and s.has_text_frame),'')
            # Explicit replacement of this planned logic slot, never a PNG substitution.
            for s in list(sl.shapes):sl.shapes._spTree.remove(s._element)
            title=old_title or scene['title']
            text(sl,'PFS_TITLE',title,[Inches(.45),Inches(.15),prs.slide_width-Inches(.9),Inches(.5)],32,True)
            info=draw_scene(sl,product,scene,(Inches(.35),Inches(.8),prs.slide_width-Inches(.7),prs.slide_height-Inches(1.35)),omit_scene_title=True)
            if reference:
                if Path(reference).name!=reference:raise ValueError('FULL_B_REFERENCE_MUST_BE_LOCAL_FILENAME')
                q=text(sl,'PFS_FULL_B_REFERENCE','完整B（可编辑大画布）：'+reference,[Inches(.45),prs.slide_height-Inches(.25),prs.slide_width-Inches(.9),Inches(.2)],10/.75,False,'#174994')
                q.text_frame.paragraphs[0].runs[0].hyperlink.address=reference
                sl.notes_slide.notes_text_frame.text+='\n完整B相对引用：'+reference+'；请保留同目录附件。'
            if oldnotes and '模型快照：' not in oldnotes:sl.notes_slide.notes_text_frame.text+='\n\n原页补充讲述与来源：\n'+oldnotes
            if scene.get('notes',{}).get('preserve_original_text'):sl.notes_slide.notes_text_frame.text+='\n\n原页实验参数与结果留存（仅作补充；讲述按新局部视图及对应Figure页）：\n'+oldtext
            merged.append(dict(slide=int(number),original_notes=oldnotes,non_logic_notes_preserved=bool(oldnotes and '模型快照：' not in oldnotes),**info))
        # Keep the newly serialized OPC graph coherent. Old paths may refer to
        # different slides after python-pptx renames parts on .slides access.
        target=Path(main_output);temp=target.with_suffix('.pending.pptx')
        if temp.exists():raise ValueError('OUTPUT_EXISTS: '+str(temp))
        prs.save(temp)
        # Font repair is restricted to changed slide/notes parts. Never restyle
        # unrelated Figure pages, masters or their original source annotations.
        from zipfile import ZipFile
        from apply_script_fonts import patch_xml,font_availability
        font_availability();fonttemp=target.with_suffix('.pending.fonts.pptx')
        with ZipFile(temp) as source,ZipFile(fonttemp,'w') as dest:
            for item in source.infolist():
                data=source.read(item.filename)
                if item.filename in changed_parts:data=patch_xml(data.decode('utf-8')).encode('utf-8')
                dest.writestr(item,data)
        fonttemp.replace(temp)
        reopened=validate_package(temp)
        if len(reopened.slides)!=len(original):raise ValueError('SLIDE_COUNT_DRIFT')
        for i,slide in enumerate(reopened.slides,1):
            if i in targets:validate_scene(slide,targets[i])
            elif slide_content(slide)!=original[i-1]:raise ValueError('NON_TARGET_CONTENT_DRIFT: '+str(i))
        if reopened.core_properties.identifier!=m['snapshot']:raise ValueError('MAIN_MODEL_SNAPSHOT_DRIFT')
        temp.replace(target)
        if reference:
            import shutil
            full=next((r for r in files if r['view']=='B'),None)
            if not full:raise ValueError('COMPLETE_B_REQUIRED_FOR_REFERENCE')
            ref=target.parent/reference
            if ref.exists() and rl.file_sha(ref)!=full['sha256']:raise ValueError('FULL_B_REFERENCE_COLLISION')
            shutil.copy2(full['path'],ref)
    receipt=dict(version='pfs-render-receipt-1',backend='portable-python-pptx',network_snapshot=net['snapshot'],files=files,main_pages=merged,main_pptx=str(Path(main_output).resolve()) if main_output else None,main_sha256=rl.file_sha(main_output) if main_output else None,full_b_reference=reference,source_relations_added=0,formal_ready=False)
    (out/'render_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),'utf-8');return receipt

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check-dependencies',action='store_true')
    for k in ['network','plan','output-dir','metadata','main-pptx','page-map','main-output']:p.add_argument('--'+k)
    p.add_argument('--development-preview',action='store_true');a=p.parse_args()
    if a.check_dependencies:print(json.dumps(dependencies()));return 0 if dependencies()['available'] else 2
    if not dependencies()['available']:raise ValueError(str(dependencies()))
    if not a.development_preview:raise ValueError('EXPLICIT_DEVELOPMENT_PREVIEW_REQUIRED; scientific review remains PARTIAL')
    if not all([a.network,a.plan,a.output_dir]):p.error('--network --plan --output-dir required')
    r=render(a.network,a.plan,a.output_dir,a.metadata,a.main_pptx,rl.load(a.page_map) if a.page_map else None,a.main_output);print(json.dumps({'files':len(r['files']),'native_main_pages':len(r['main_pages']),'backend':r['backend']}));return 0
if __name__=='__main__':raise SystemExit(main())
