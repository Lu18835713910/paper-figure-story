"""Content-locked Visual Polish execution. Geometry/style only, no science planning.

Uses the existing OOXML editor, source audit and actual PowerPoint exporter.
Every page is a transaction. The original page is restored on invariant failure.
"""
from __future__ import annotations
import copy,hashlib,math,re,shutil
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
VERSION='pfs-visual-polish-locked-2'

def api():
 import polish_presentation as v
 return v
def norm(s):return re.sub(r'\s+','',str(s))
def qn(tag):return '{'+api().NS['a']+'}'+tag
def tx(shape):return norm(api().shape_text(shape))
def bounds(q):
 v=api();x=q.find('p:spPr/a:xfrm',v.NS)
 if x is None:x=q.find('p:xfrm',v.NS)
 if x is None:raise v.PolishError('UNSUPPORTED_GROUP_OR_TRANSFORM')
 a=x.find('a:off',v.NS);b=x.find('a:ext',v.NS)
 return x,[int(a.get('x'))/914400,int(a.get('y'))/914400,int(b.get('cx'))/914400,int(b.get('cy'))/914400]
def edge(q):
 v=api();n=v.shape_name(q)
 is_edge=E.QName(q).localname=='cxnSp' or '_story_arrow_' in n or n.startswith('RC_EDGE_') or n=='VP_PRESENTATION_ARROW'
 if not is_edge:return None
 return dict(name=n,connections=[E.tostring(x).decode() for x in q.xpath('.//p:stCxn|.//p:endCxn',namespaces=v.NS)],heads=[[E.QName(x).localname,x.get('type','none')] for x in q.xpath('.//a:headEnd|.//a:tailEnd',namespaces=v.NS)],dash=[x.get('val') for x in q.xpath('.//a:prstDash',namespaces=v.NS)],autoshape_arrow=[x.get('prst') for x in q.xpath('.//a:prstGeom',namespaces=v.NS)] if '_story_arrow_' in n else None)
def snapshot(path,context=None):
 v=api();data=v.package(path);parts=v.active_parts(data);rows=[]
 for n,part in enumerate(parts,1):
  root=v.xml(data,part);records=[]
  for q in root.find('p:cSld/p:spTree',v.NS):
   if E.QName(q).localname in ['nvGrpSpPr','grpSpPr','extLst']:continue
   pr=q.find('.//p:cNvPr',v.NS);rec=dict(id=v.shape_id(q),name=v.shape_name(q),metadata=E.tostring(pr).decode() if pr is not None else None,text=tx(q),edge=edge(q))
   rec['cells']=[[norm(''.join(c.xpath('.//a:t/text()',namespaces=v.NS))) for c in row.findall('a:tc',v.NS)] for row in q.findall('.//a:tr',v.NS)]
   if E.QName(q).localname=='pic':
    rp=v.xml(data,v.relpart(part));rm={e.get('Id'):e.get('Target') for e in rp};blip=q.find('.//a:blip',v.NS);rid=blip.get('{'+v.NS['r']+'}embed');target=v.resolve_target(part,rm[rid]);crop=q.find('.//a:srcRect',v.NS)
    rec['image']=dict(rid=rid,target=target,sha256=hashlib.sha256(data[target]).hexdigest(),crop=dict(crop.attrib) if crop is not None else {},ratio=bounds(q)[1][2]/bounds(q)[1][3])
   records.append(rec)
  note=v.notes_part(data,part)
  rows.append(dict(slide=n,part=part,hidden=root.get('show','1'),objects=records,notes_sha256=hashlib.sha256(data[note]).hexdigest() if note else None))
 return dict(version=VERSION,source_sha256=v.digest(path),page_order=parts,pages=len(parts),context_sha256=v.fingerprint(context or {}),slides=rows)
def compare(before,after,approved_archives=None):
 from visual_polish_deck_style import valid_archive
 issues=[]
 if before['page_order']!=after['page_order']:issues.append(dict(code='PAGE_ORDER_OR_COUNT_CHANGED'))
 for old,new in zip(before['slides'],after['slides']):
  n=old['slide']
  if old['hidden']!=new['hidden']:issues.append(dict(slide=n,code='MAIN_BACKUP_MEMBERSHIP_CHANGED'))
  if old['notes_sha256']!=new['notes_sha256']:issues.append(dict(slide=n,code='NOTES_CHANGED'))
  om={x['id']:x for x in old['objects']};nm={x['id']:x for x in new['objects']}
  for sid,a in om.items():
   b=nm.get(sid)
   if b is None:
    permit=next((x for x in (approved_archives or []) if x.get('slide')==n and x.get('shape_id')==sid),None)
    if not permit or not valid_archive(a,permit):issues.append(dict(slide=n,shape=sid,code='ORIGINAL_OBJECT_REMOVED'))
    continue
   for field in ['metadata','text','cells','edge']:
    if a[field]!=b[field]:issues.append(dict(slide=n,shape=sid,code='LOCKED_'+field.upper()+'_CHANGED'))
   if a.get('image'):
    for f in ['rid','target','sha256','crop']:
     if a['image'][f]!=b.get('image',{}).get(f):issues.append(dict(slide=n,shape=sid,code='IMAGE_'+f.upper()+'_CHANGED'))
    if abs(a['image']['ratio']/b['image']['ratio']-1)>.003:issues.append(dict(slide=n,shape=sid,code='IMAGE_DISTORTED'))
  for sid,a in nm.items():
   if sid not in om and (not a['name'].startswith('VP_VISUAL_DECOR_') or a['text'] or a['edge'] or a['cells'] or a.get('image')):issues.append(dict(slide=n,shape=sid,code='UNPLANNED_CONTENT_ADDED'))
 if before['context_sha256']!=after['context_sha256']:issues.append(dict(code='SOURCE_CONTEXT_CHANGED'))
 return dict(valid=not issues,issues=issues,claim='Exact page-local wording/cells, notes, Figure bytes/crop/assignment, object/edge identity, order, backup status and context. Geometry is separately checked against the Agent route plan; this is not scientific semantic re-review.')
def setpos(q,pos):
 v=api();x,old=bounds(q)
 if len(pos)!=4 or pos[2]<=0 or pos[3]<=0 or min(pos[:2])<0:raise v.PolishError('INVALID_GEOMETRY')
 if E.QName(q).localname=='pic' and abs((pos[2]/pos[3])/(old[2]/old[3])-1)>.003:raise v.PolishError('IMAGE_ASPECT_LOCK')
 x.find('a:off',v.NS).attrib.update({'x':str(round(pos[0]*914400)),'y':str(round(pos[1]*914400))});x.find('a:ext',v.NS).attrib.update({'cx':str(round(pos[2]*914400)),'cy':str(round(pos[3]*914400))})
def fill(parent,tag,color):
 for old in list(parent):
  if E.QName(old).localname in ['solidFill','noFill','gradFill','blipFill','pattFill','grpFill']:parent.remove(old)
 e=E.SubElement(parent,qn('noFill') if color in [None,'none'] else qn(tag))
 if color not in [None,'none']:E.SubElement(e,qn('srgbClr'),val=color.lstrip('#'))
def text_style(q,style,reflow=None):
 v=api();body=q.find('p:txBody',v.NS)
 if body is None:raise v.PolishError('TEXT_BODY_REQUIRED')
 old=tx(q);paragraphs=body.findall('a:p',v.NS)
 old_sizes=[int(p.get('sz'))/100 for p in q.xpath('.//a:rPr|.//a:defRPr',namespaces=v.NS) if p.get('sz')]
 if style.get('font_size') and old_sizes and style['font_size']<min(old_sizes)-.01:raise v.PolishError('FONT_SHRINK_FORBIDDEN')
 if reflow is not None:
  if norm(''.join(reflow))!=old:raise v.PolishError('REFLOW_CHANGES_WORDING')
  prototype=paragraphs[0] if paragraphs else None
  for p in paragraphs:body.remove(p)
  for text in reflow:
   p=E.SubElement(body,qn('p'))
   if prototype is not None and prototype.find('a:pPr',v.NS) is not None:p.append(copy.deepcopy(prototype.find('a:pPr',v.NS)))
   r=E.SubElement(p,qn('r'));E.SubElement(r,qn('rPr'),lang='zh-CN');E.SubElement(r,qn('t')).text=text
 props=body.find('a:bodyPr',v.NS)
 if props is not None:
  props.set('wrap','square')
  if style.get('valign'):props.set('anchor',style['valign'])
  for k,z in zip(['lIns','tIns','rIns','bIns'],style.get('margins',[.03,.01,.03,.01])):props.set(k,str(round(z*914400)))
  # Keep font size explicit; do not let PowerPoint secretly shrink text.
  for e in list(props):
   if E.QName(e).localname in ['normAutofit','spAutoFit']:props.remove(e)
  if props.find('a:noAutofit',v.NS) is None:E.SubElement(props,qn('noAutofit'))
 for p in body.findall('a:p',v.NS):
  pr=p.find('a:pPr',v.NS)
  if pr is None:pr=E.Element(qn('pPr'));p.insert(0,pr)
  if style.get('align'):pr.set('algn',style['align'])
  if style.get('space_after') is not None:
   for e in pr.findall('a:spcAft',v.NS):pr.remove(e)
   sp=E.SubElement(pr,qn('spcAft'));E.SubElement(sp,qn('spcPts'),val=str(round(style['space_after']*100)))
  if style.get('line_spacing'):
   for e in pr.findall('a:lnSpc',v.NS):pr.remove(e)
   sp=E.SubElement(pr,qn('lnSpc'));E.SubElement(sp,qn('spcPct'),val=str(round(style['line_spacing']*100000)))
  default=pr.find('a:defRPr',v.NS)
  if default is None:default=E.SubElement(pr,qn('defRPr'))
  for prop in [default]+p.findall('a:r/a:rPr',v.NS)+p.findall('a:endParaRPr',v.NS):
   if style.get('font_size'):prop.set('sz',str(round(style['font_size']*100)))
   if 'bold' in style:prop.set('b','1' if style['bold'] else '0')
   if style.get('color'):fill(prop,'solidFill',style['color'])
   for tag,font in [('latin','Times New Roman'),('ea','Microsoft YaHei'),('cs','Times New Roman')]:
    f=prop.find('a:'+tag,v.NS)
    if f is None:f=E.SubElement(prop,qn(tag))
    f.set('typeface',font)
  spans=style.get('spans',[])
  if spans:
   # Re-split only existing characters. Original per-paragraph word order stays.
   content=''.join(p.xpath('./a:r/a:t/text()',namespaces=v.NS));runs=p.findall('a:r',v.NS);source_pr=runs[0].find('a:rPr',v.NS) if runs else None;template=copy.deepcopy(source_pr if source_pr is not None else default)
   intervals=[]
   for span in spans:
    for m in re.finditer(re.escape(span['text']),content):intervals.append((m.start(),m.end(),span))
   breaks=sorted({0,len(content),*[a for a,b,s in intervals],*[b for a,b,s in intervals]})
   for r in runs:p.remove(r)
   for a,b in zip(breaks,breaks[1:]):
    rr=E.SubElement(p,qn('r'));prr=copy.deepcopy(template);prr.tag=qn('rPr');rr.append(prr)
    for l,h,span in intervals:
     if a>=l and b<=h:
      if span.get('color'):fill(prr,'solidFill',span['color'])
      if 'bold' in span:prr.set('b','1' if span['bold'] else '0')
      if span.get('font_size'):
       if span['font_size']<(style.get('font_size') or min(old_sizes or [0])):raise v.PolishError('SPAN_FONT_SHRINK_FORBIDDEN')
       prr.set('sz',str(round(span['font_size']*100)))
    E.SubElement(rr,qn('t')).text=content[a:b]
 if tx(q)!=old:raise v.PolishError('TEXT_STYLE_DRIFT')
def style_shape(q,style):
 v=api();sp=q.find('p:spPr',v.NS)
 if sp is None:raise v.PolishError('SHAPE_STYLE_REQUIRED')
 if 'fill' in style:fill(sp,'solidFill',style['fill'])
 if 'line' in style:
  ln=sp.find('a:ln',v.NS)
  if ln is None:ln=E.SubElement(sp,qn('ln'))
  fill(ln,'solidFill',style['line'])
  if style.get('line_width') is not None:ln.set('w',str(round(style['line_width']*12700)))
 for e in sp.findall('a:effectLst',v.NS):sp.remove(e)
 if style.get('halo'):
  effect=E.SubElement(sp,qn('effectLst'));glow=E.SubElement(effect,qn('glow'),rad='19050');E.SubElement(glow,qn('srgbClr'),val='FFFFFF')
 if style.get('flat'):
  for ref in q.findall('p:style/a:effectRef',v.NS):ref.set('idx','0')
  if sp.find('a:effectLst',v.NS) is None:E.SubElement(sp,qn('effectLst'))
 if style.get('compact_arrowheads'):
  for head in sp.xpath('./a:ln/a:headEnd|./a:ln/a:tailEnd',namespaces=v.NS):head.attrib.update({'w':'sm','len':'sm'})
 if style.get('arrowhead_size'):
  size=style['arrowhead_size']
  if size not in ['sm','med','lg']:raise v.PolishError('INVALID_ARROWHEAD_SIZE')
  for head in sp.xpath('./a:ln/a:headEnd|./a:ln/a:tailEnd',namespaces=v.NS):
   if head.get('type','none')!='none':head.attrib.update({'w':size,'len':size})
def table_style(q,plan):
 v=api();table=q.find('.//a:tbl',v.NS);rows=table.findall('a:tr',v.NS);grid=table.find('a:tblGrid',v.NS)
 if len(plan['column_widths'])!=len(grid) or len(plan['row_heights'])!=len(rows):raise v.PolishError('TABLE_DIMENSION_LOCK')
 if abs(sum(plan['column_widths'])-plan['position'][2])>.005 or abs(sum(plan['row_heights'])-plan['position'][3])>.005:raise v.PolishError('TABLE_SIZE_SUM')
 setpos(q,plan['position'])
 for col,width in zip(grid,plan['column_widths']):col.set('w',str(round(width*914400)))
 for i,(row,height) in enumerate(zip(rows,plan['row_heights'])):
  row.set('h',str(round(height*914400)))
  for j,cell in enumerate(row.findall('a:tc',v.NS)):
   prop=cell.find('a:tcPr',v.NS)
   if prop is None:prop=E.SubElement(cell,qn('tcPr'))
   prop.attrib.update({'anchor':'ctr','marL':str(round(.085*914400)),'marR':str(round(.085*914400)),'marT':str(round(.04*914400)),'marB':str(round(.04*914400))})
   spec={**plan['default'],**plan.get('rows',{}).get(str(i),{}),**plan.get('cells',{}).get(f'{i}:{j}',{})}
   fill(prop,'solidFill',spec.get('fill','FFFFFF'))
   for edge_name in ['lnL','lnR','lnT','lnB']:
    for old in prop.findall('a:'+edge_name,v.NS):prop.remove(old)
    line=E.SubElement(prop,qn(edge_name),w=str(round((spec.get('separator_top',.5) if edge_name=='lnT' else .5)*12700)));fill(line,'solidFill','FFFFFF')
   # Reuse the text formatter by a temporary wrapper; only style is copied back.
   wrapper=E.Element('{'+v.NS['p']+'}sp');body=copy.deepcopy(cell.find('a:txBody',v.NS));body.tag='{'+v.NS['p']+'}txBody';wrapper.append(body);text_style(wrapper,{k:z for k,z in spec.items() if k!='fill'})
   if spec.get('reflow') is not None:text_style(wrapper,{},spec['reflow'])
   old=cell.find('a:txBody',v.NS);ix=list(cell).index(old);cell.remove(old);body=wrapper.find('p:txBody',v.NS);body.tag=qn('txBody');cell.insert(ix,body)
def path_shape(q,points):
 v=api();sp=q.find('p:spPr',v.NS);xs=[p[0] for p in points];ys=[p[1] for p in points];left,top=min(xs),min(ys);width,height=max(xs)-left,max(ys)-top
 # Connector zero width/height is legal. Custom geometry preserves all bends.
 x=q.find('p:spPr/a:xfrm',v.NS);x.attrib.pop('flipH',None);x.attrib.pop('flipV',None);x.attrib.pop('rot',None)
 x.find('a:off',v.NS).attrib.update({'x':str(round(left*914400)),'y':str(round(top*914400))});x.find('a:ext',v.NS).attrib.update({'cx':str(round(max(width,.0001)*914400)),'cy':str(round(max(height,.0001)*914400))})
 for child in list(sp):
  if E.QName(child).localname in ['prstGeom','custGeom']:sp.remove(child)
 if len(points)==2:
  if points[-1][0]<points[0][0]:x.set('flipH','1')
  if points[-1][1]<points[0][1]:x.set('flipV','1')
  geom=E.Element(qn('prstGeom'),prst='straightConnector1');E.SubElement(geom,qn('avLst'));sp.insert(1,geom);return
 # PowerPoint rejects freeform custom geometry on a cxnSp in this environment.
 # An editable freeform sp retains the same edge ID, arrowheads, dash semantics
 # and endpoint map. Attached connector bindings cannot be safely converted.
 if q.xpath('.//p:stCxn|.//p:endCxn',namespaces=v.NS):raise v.PolishError('ATTACHED_CONNECTOR_REQUIRES_NATIVE_ROUTING')
 q.tag='{'+v.NS['p']+'}sp'
 nv=q.find('p:nvCxnSpPr',v.NS)
 if nv is not None:
  nv.tag='{'+v.NS['p']+'}nvSpPr';child=nv.find('p:cNvCxnSpPr',v.NS)
  if child is not None:child.tag='{'+v.NS['p']+'}cNvSpPr'
 geom=E.Element(qn('custGeom'))
 for tag in ['avLst','gdLst','ahLst','cxnLst']:E.SubElement(geom,qn(tag))
 E.SubElement(geom,qn('rect'),l='0',t='0',r='w',b='h');pl=E.SubElement(geom,qn('pathLst'));p=E.SubElement(pl,qn('path'),w='100000',h='100000',fill='none',stroke='1')
 for i,(px,py) in enumerate(points):
  cmd=E.SubElement(p,qn('moveTo' if i==0 else 'lnTo'));E.SubElement(cmd,qn('pt'),x=str(round((px-left)/max(width,.0001)*100000)),y=str(round((py-top)/max(height,.0001)*100000)))
 sp.insert(1,geom)
def divide_path(points,n):
 lengths=[math.dist(a,b) for a,b in zip(points,points[1:])];total=sum(lengths)
 if not total or n<1:raise api().PolishError('EMPTY_ROUTE')
 cumulative=[0]
 for x in lengths:cumulative.append(cumulative[-1]+x)
 def at(d):
  for i,length in enumerate(lengths):
   if d<=cumulative[i+1]+1e-9:
    f=(d-cumulative[i])/max(length,1e-12);return [points[i][j]+(points[i+1][j]-points[i][j])*f for j in [0,1]]
  return points[-1]
 out=[]
 for i in range(n):
  a,b=total*i/n,total*(i+1)/n;out.append([at(a)]+[points[k] for k in range(1,len(points)-1) if a<cumulative[k]<b]+[at(b)])
 return out
def decorate(root,plan):
 v=api();tree=root.find('p:cSld/p:spTree',v.NS);sid=max(v.shape_id(q) or 0 for q in tree)+1
 q=E.Element('{'+v.NS['p']+'}sp');nv=E.SubElement(q,'{'+v.NS['p']+'}nvSpPr');E.SubElement(nv,'{'+v.NS['p']+'}cNvPr',id=str(sid),name='VP_VISUAL_DECOR_'+plan['id']);E.SubElement(nv,'{'+v.NS['p']+'}cNvSpPr');E.SubElement(nv,'{'+v.NS['p']+'}nvPr');sp=E.SubElement(q,'{'+v.NS['p']+'}spPr');xf=E.SubElement(sp,qn('xfrm'));E.SubElement(xf,qn('off'),x='0',y='0');E.SubElement(xf,qn('ext'),cx='1',cy='1');E.SubElement(sp,qn('prstGeom'),prst='rect');setpos(q,plan['position']);style_shape(q,plan)
 # All decoration stays behind existing scientific content, never on top of data.
 index=next((i+1 for i,s in enumerate(tree) if v.shape_name(s).startswith('PFS_LAYOUT_')),2);tree.insert(index,q)

def canonical_styles(root):
 # DrawingML child order matters to PowerPoint. Invalid ordering may silently
 # fall back to theme gradients/black text despite otherwise valid ZIP/XML.
 fills=['noFill','solidFill','gradFill','blipFill','pattFill','grpFill']
 orders={'spPr':['xfrm','prstGeom','custGeom']+fills+['ln','effectLst','effectDag','scene3d','sp3d','extLst'],
  'ln':['noFill','solidFill','gradFill','pattFill','prstDash','custDash','round','bevel','miter','headEnd','tailEnd','extLst'],
  'rPr':['ln']+fills+['effectLst','effectDag','highlight','uLnTx','uLn','uFillTx','uFill','latin','ea','cs','sym','hlinkClick','hlinkMouseOver','rtl','extLst'],
  'pPr':['lnSpc','spcBef','spcAft','buClrTx','buClr','buSzTx','buSzPct','buSzPts','buFontTx','buFont','buNone','buAutoNum','buBlip','buChar','tabLst','defRPr','extLst'],
  'tcPr':['lnL','lnR','lnT','lnB','lnTlToBr','lnBlToTr','cell3D']+fills+['headers','extLst']}
 orders['defRPr']=orders['rPr'];orders['endParaRPr']=orders['rPr']
 for el in root.iter():
  key=E.QName(el).localname
  if key not in orders:continue
  ranks={tag:i for i,tag in enumerate(orders[key])};children=list(el)
  for child in children:el.remove(child)
  el.extend(sorted(children,key=lambda x:ranks.get(E.QName(x).localname,100)))
def redraw(data,part,design,context=None):
 from visual_polish_deck_style import resolve
 design=resolve(design)
 v=api();root=v.xml(data,part)
 for item in design.get('shapes',[]):
  q=v.top_shape(root,item['shape_id'])
  if q.tag=='{'+v.NS['p']+'}grpSp':raise v.PolishError('GROUP_REQUIRES_EXPLICIT_CHILD_DESIGN')
  if item.get('position'):setpos(q,item['position'])
  if 'style' in item:style_shape(q,item['style'])
  if 'text_style' in item or 'reflow' in item:text_style(q,item.get('text_style',{}),item.get('reflow'))
 for item in design.get('tables',[]):table_style(v.top_shape(root,item['shape_id']),item)
 for route in design.get('routes',[]):
  shapes=[v.top_shape(root,sid) for sid in route['shape_ids']]
  if not all(edge(q) and E.QName(q).localname in ['cxnSp','sp'] for q in shapes):raise v.PolishError('ROUTE_NOT_EXISTING_CONNECTOR')
  registered=next((e for g in (context or {}).get('display_topology',[]) if g['slide']==design['slide'] for e in g['edges'] if e['id']==route.get('edge_id')),None)
  if not registered or registered['shape_ids']!=route['shape_ids']:raise v.PolishError('SOURCE_EDGE_IDENTITY_REQUIRED')
  import visual_polish_connectors as CQ
  reading=CQ.is_reading_edge(root,registered)
  if route.get('kind')=='reading_guide' and not reading:raise v.PolishError('SCIENTIFIC_EDGE_CANNOT_BECOME_READING_GUIDE')
  if reading:
   expected=CQ.reading_points(bounds(v.top_shape(root,registered['source_shape_id']))[1],bounds(v.top_shape(root,registered['target_shape_id']))[1],axis_x=route.get('axis_x'))
   if len(route['points'])!=2 or any(math.dist(a,b)>.003 for a,b in zip(route['points'],expected)):raise v.PolishError('READING_ARROW_MUST_BE_STRAIGHT_DOWN_IN_GAP')
   CQ.native_reading_connector(shapes[0],expected)
   continue
  for point,key in [(route['points'][0],'source_shape_id'),(route['points'][-1],'target_shape_id')]:
   _,(x,y,w,h)=bounds(v.top_shape(root,registered[key]));px,py=point
   on_border=(x-.06<=px<=x+w+.06 and min(abs(py-y),abs(py-y-h))<=.06) or (y-.06<=py<=y+h+.06 and min(abs(px-x),abs(px-x-w))<=.06)
   if not on_border:raise v.PolishError('ROUTE_ENDPOINT_DRIFT')
   neighbour=route['points'][1] if key=='source_shape_id' else route['points'][-2]
   dx,dy=(neighbour[0]-px,neighbour[1]-py) if key=='source_shape_id' else (px-neighbour[0],py-neighbour[1])
   normals=[]
   if abs(px-x)<=.06:normals.append((-1,0))
   if abs(px-x-w)<=.06:normals.append((1,0))
   if abs(py-y)<=.06:normals.append((0,-1))
   if abs(py-y-h)<=.06:normals.append((0,1))
   sign=1 if key=='source_shape_id' else -1
   if not any(sign*(dx*nx+dy*ny)>1e-6 for nx,ny in normals):raise v.PolishError('ARROW_APPROACH_DIRECTION_DRIFT')
  for q,p in zip(shapes,divide_path(route['points'],len(shapes))):path_shape(q,p)
 for item in design.get('decorations',[]):decorate(root,item)
 # Decorations cannot receive a front-most z-order. Original content IDs persist.
 if design.get('content_order'):
  tree=root.find('p:cSld/p:spTree',v.NS)
  for sid in design['content_order']:
   q=v.top_shape(root,sid);tree.remove(q);tree.append(q)
 if design.get('archive_chrome'):
  from visual_polish_deck_style import valid_archive
  tree=root.find('p:cSld/p:spTree',v.NS)
  for item in design['archive_chrome']:
   q=v.top_shape(root,item['shape_id'])
   rec=dict(id=v.shape_id(q),text=tx(q),edge=edge(q),cells=q.findall('.//a:tr',v.NS),image=q.find('.//a:blip',v.NS))
   if not valid_archive(rec,item):raise v.PolishError('SCIENTIFIC_CONTENT_CANNOT_BE_ARCHIVED')
   tree.remove(q)
 canonical_styles(root);v.put(data,part,root)
def dump(path,data):
 with ZipFile(path,'w',ZIP_DEFLATED) as z:
  for n,b in data.items():z.writestr(n,b)
def validate_plan(plan,source,lock,before):
 v=api()
 if plan.get('version')!=VERSION:raise v.PolishError('LOCKED_PLAN_VERSION_REQUIRED; content-changing legacy plans are no longer accepted')
 if plan.get('input_sha256')!=v.digest(source) or plan.get('content_lock_sha256')!=v.fingerprint(lock):raise v.PolishError('CONTENT_LOCK_DRIFT')
 if plan.get('designer')!='Agent':raise v.PolishError('AGENT_DESIGN_REQUIRED')
 if plan.get('actions') or plan.get('upstream_responses'):raise v.PolishError('CONTENT_ACTION_OR_UPSTREAM_FORBIDDEN')
 images={x['slide']:x for x in (before or {}).get('rendered',[])}
 keys={'current_visual_problem','primary_existing_information','layout','space_allocation','emphasis','immutable_content','expected_improvement'}
 seen=set()
 for d in plan.get('pages',[]):
  n=int(d['slide'])
  if n in seen or n<1 or n>lock['pages']:raise v.PolishError('PAGE_SELECTION_INVALID')
  seen.add(n)
  if not keys<=d.keys():raise v.PolishError('INCOMPLETE_AGENT_DESIGN')
  if n not in images or images[n]['png_sha256']!=d.get('original_png_sha256'):raise v.PolishError('ACTUAL_DESIGN_PREVIEW_REQUIRED')
def polish(input_path,outdir,profile='balanced',context=None,plan=None,before_receipt=None,renderer='powerpoint',cycle=1):
 v=api();src=Path(input_path).resolve();out=Path(outdir).resolve()
 if profile not in v.MODES or cycle not in [1,2]:raise v.PolishError('PROFILE_OR_CYCLE')
 if out.exists() and any(out.iterdir()):raise v.PolishError('OUTPUT_EXISTS')
 context=v.read(context) if isinstance(context,(str,Path)) else context or {};plan=v.read(plan) if isinstance(plan,(str,Path)) else plan
 protected=v.verify_context(context);data=v.package(src);original=copy.deepcopy(data);lock=snapshot(src,context);out.mkdir(parents=True,exist_ok=True);shutil.copy2(src,out/'original.pptx');v.save(out/'content_lock.json',lock);v.save(out/'source_context.json',context)
 audit=v.audit_input(src,context);v.save(out/'diagnosis.json',audit)
 before=v.render(src,out/'previews/before',profile,provided=before_receipt) if renderer!='none' else None
 if plan:validate_plan(plan,src,lock,before)
 from visual_polish_deck_style import archives,archive_records
 approved=archives(plan);v.save(out/'archived_page_chrome.json',archive_records(lock,plan))
 requests=[dict(slide=p['slide'],code='UPSTREAM_CONTENT_ISSUE',original_code=x['code'],detail=x.get('detail'),request_id=x.get('request_id')) for p in audit['slides'] for x in p['issues'] if x['category']=='Content Coverage']
 v.save(out/'upstream_requests.json',dict(requests=requests,action='Return to PFS content planning; never import additional data or resolve the gap inside Visual Polish.'))
 applied=[];failed=[]
 for design in (plan or {}).get('pages',[]):
  n=int(design['slide']);part=lock['page_order'][n-1]
  try:
   if design.get('retain_reason'):continue
   redraw(data,part,design,context);draft=out/'transaction.pptx';dump(draft,data);check=compare(lock,snapshot(draft,context),approved)
   if not check['valid']:raise v.PolishError(str(check['issues']))
   applied.append(n)
  except (v.PolishError,KeyError,ValueError,TypeError) as e:data[part]=original[part];failed.append(dict(slide=n,reason=str(e),action='ORIGINAL_PAGE_RESTORED'))
 final=out/'polished.pptx';dump(final,data);check=compare(lock,snapshot(final,context),approved);v.save(out/'consistency.json',check)
 # Only slide visual XML may differ. Notes, source mappings, media, masters,
 # relationships, order and hidden flags are never rewritten by this builder.
 other_changed=[p for p,b in original.items() if p not in lock['page_order'] and data.get(p)!=b]
 if other_changed or not check['valid']:raise v.PolishError('NON_VISUAL_PACKAGE_DRIFT')
 fa=v.check_fonts(final);v.save(out/'font_audit.json',fa);changed=[i for i,p in enumerate(lock['page_order'],1) if data[p]!=original[p]]
 after=None
 if renderer!='none':
  if changed:
   try:after=v.render(final,out/'previews/after',profile,slides=changed)
   except v.PolishError as exc:
    shutil.copy2(final,out/'rejected_unreadable.pptx');dump(final,original)
    failed.append(dict(slide=changed,reason=str(exc),action='ALL_ATTEMPTED_PAGES_RESTORED_AFTER_RENDER_FAILURE'))
    v.save(out/'render_failure_rollback.json',dict(reason=str(exc),attempted_pages=changed,restored_sha256=v.digest(final),source_sha256=v.digest(src)))
    applied=[];changed=[];data=copy.deepcopy(original);after=dict(before,input=str(final),input_sha256=v.digest(final),rendered=[])
    check=compare(lock,snapshot(final,context));v.save(out/'consistency.json',check);fa=v.check_fonts(final);v.save(out/'font_audit.json',fa)
  else:after=dict(before,input=str(final),input_sha256=v.digest(final),rendered=[]);(out/'previews/after').mkdir(parents=True,exist_ok=True)
  done={p['slide']:p for p in after['rendered']}
  for p in before['rendered']:
   n=p['slide']
   if n not in done:
    dest=out/'previews/after'/f'slide-{n:03d}.png';shutil.copy2(p['png'],dest);done[n]=dict(p,png=str(dest),reused_unchanged_page=True)
  after['rendered']=sorted(done.values(),key=lambda p:p['slide']);v.save(out/'previews/after/receipt.json',after)
  (out/'before_after').mkdir()
  for n in changed:v.before_after(next(p['png'] for p in before['rendered'] if p['slide']==n),done[n]['png'],out/'before_after'/f'slide-{n:03d}.png')
 issues=[dict(slide=p['slide'],**x) for p in (after or {}).get('rendered',[]) for x in p['issues']]
 audit_after=v.audit_input(final,context);v.save(out/'post_diagnosis.json',audit_after)
 issues += [dict(slide=p['slide'],**i) for p in audit_after['slides'] for i in p['issues'] if i['code'] in ['OFF_CANVAS','IMAGE_ASPECT','CRITICAL_REGION_CLIPPED']]
 connector_checks=[]
 if plan and after:
  import visual_polish_connectors as CQ
  for design in plan.get('pages',[]):
   design=copy.deepcopy(design)
   if not design.get('connector_qa'):
    rr=v.xml(data,lock['page_order'][design['slide']-1]);gg=next((g for g in context.get('display_topology',[]) if g['slide']==design['slide'] and g.get('edges')),None)
    if gg:design['connector_qa']=dict(label_ids=[v.shape_id(q) for q in rr.find('p:cSld/p:spTree',v.NS) if '_edge_label_' in v.shape_name(q)])
    else:
     aa=[v.shape_id(q) for q in rr.find('p:cSld/p:spTree',v.NS) if '_story_arrow_' in v.shape_name(q) and edge(q)]
     if not aa:continue
     design['connector_qa']=dict(reading_autoshape_ids=aa)
   op=next((p for p in after['rendered'] if p['slide']==design['slide']),None)
   cq=CQ.audit_autoshapes(final,design,op) if design['connector_qa'].get('reading_autoshape_ids') else CQ.audit(final,context,design,op)
   connector_checks.append(dict(slide=design['slide'],**cq));issues += [dict(slide=design['slide'],**i) for i in cq['issues']]
 v.save(out/'connector_checks.json',connector_checks)
 preserved=all(v.digest(p)==h for p,h in protected.items())
 report=dict(version=VERSION,input=str(src),input_sha256=v.digest(src),output=str(final),output_sha256=v.digest(final),profile=profile,cycle=cycle,slides_before=lock['pages'],slides_after=lock['pages'],changed_pages=changed,actions=[dict(id='visual-redesign-'+str(n),original_slide=n,kind='locked-page-design') for n in applied],failed_actions=failed,automatic_checks='PASS' if check['valid'] and preserved and fa['valid'] and not issues and not failed else 'PARTIAL',automatic_issues=issues,invariants=dict(content_and_topology_lock=check['valid'],non_visual_parts_unchanged=not other_changed,protected_sources_unchanged=preserved,source_input_unchanged=v.digest(src)==lock['source_sha256']),upstream_requests=requests,unresolved=requests+failed,actual_powerpoint_export=after is not None,scientific_review=context.get('scientific_review','NOT_AVAILABLE'),science_audit='NOT_PERFORMED_BY_VISUAL_POLISH',agent_visual_review='PENDING',USER_ACCEPTANCE='PENDING',design_mode='AGENT_DESIGNED' if plan else 'QA_ONLY',status='DESIGNED_PENDING_VISUAL_REVIEW' if plan else 'QA_ONLY',rollback_available=True)
 v.save(out/'visual_polish_report.json',report);v.write_report(out,report);return report
def finish_review(report_path,decisions):
 v=api();path=Path(report_path);report=v.read(path);choice=v.read(decisions) if isinstance(decisions,(str,Path)) else decisions;root=path.parent;receipt=v.read(root/'previews/after/receipt.json');pages={p['slide']:p for p in receipt['rendered']}
 if choice.get('output_sha256')!=v.digest(report['output']):raise v.PolishError('FINAL_REVIEW_OUTPUT_DRIFT')
 positive=set();reverted=[];data=v.package(report['output']);old=v.package(root/'original.pptx');lock=v.read(root/'content_lock.json')
 for p in choice['pages']:
  n=int(p['slide'])
  if n not in pages or pages[n]['png_sha256']!=p['png_sha256'] or v.digest(pages[n]['png'])!=p['png_sha256']:raise v.PolishError('FINAL_REVIEW_IMAGE_DRIFT')
  if p['status']=='PASS':positive.add(n)
  elif p['status']=='REVERT':data[lock['page_order'][n-1]]=old[lock['page_order'][n-1]];reverted.append(n)
 if reverted:
  shutil.copy2(report['output'],root/'rejected_candidate.pptx');dump(report['output'],data);before=v.read(root/'previews/before/receipt.json')
  for n in reverted:
   current=pages[n];shutil.copy2(current['png'],root/f'rejected-slide-{n:03d}.png');base=next(p for p in before['rendered'] if p['slide']==n);shutil.copy2(base['png'],current['png']);pages[n]=dict(base,png=current['png'],restored_exact_original=True)
  receipt.update(input_sha256=v.digest(report['output']),rendered=sorted(pages.values(),key=lambda p:p['slide']));v.save(root/'previews/after/receipt.json',receipt);report['output_sha256']=v.digest(report['output'])
  approved=v.read(root/'archived_page_chrome.json') if (root/'archived_page_chrome.json').is_file() else []
  check=compare(lock,snapshot(report['output'],v.read(root/'source_context.json')),approved);v.save(root/'consistency_after_revert.json',check)
  if not check['valid']:raise v.PolishError('REVERT_DID_NOT_RESTORE_LOCK')
  v.save(root/'font_audit_after_revert.json',v.check_fonts(report['output']))
 report.update(agent_visual_review='REVIEWED' if set(report['changed_pages'])<=positive else 'PARTIAL',visual_decisions=choice,reverted_pages=reverted,USER_ACCEPTANCE='PENDING',independent_reader_test='NOT_PERFORMED')
 report['status']='PROFESSIONAL_AGENT_REVIEWED' if report['design_mode']=='AGENT_DESIGNED' and set(report['changed_pages'])<=positive and report['automatic_checks']=='PASS' and not report['unresolved'] else ('QA_ONLY' if report['design_mode']=='QA_ONLY' else 'PARTIAL')
 v.save(path,report);v.write_report(root,report);return report
