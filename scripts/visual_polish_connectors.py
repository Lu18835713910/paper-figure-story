"""Lightweight display-geometry QA only; never infer or edit scientific edges."""
import math,itertools

READING_STYLE=dict(line='174994',line_width=1.8,flat=True,arrowhead_size='med')
READING_MARGIN=.07
READING_MIN_LENGTH=.14

def is_reading_edge(root,edge):
 """Only existing presentation guides qualify; never classify RC science edges."""
 import polish_presentation as v
 if edge.get('identity')=='scientific_registered' or edge.get('source_relation_id') or edge.get('m1_relation_id'):return False
 ids=edge.get('shape_ids',[])
 if len(ids)!=1:return False
 q=v.top_shape(root,ids[0]);name=v.shape_name(q)
 return name=='VP_PRESENTATION_ARROW' and all(v.shape_text(v.top_shape(root,edge[k])) for k in ['source_shape_id','target_shape_id'])

def reading_points(source,target,margin=READING_MARGIN,axis_x=None):
 """Whitespace guide, not a node-attached scientific edge; no elbows allowed."""
 import polish_presentation as v
 left=max(source[0],target[0]);right=min(source[0]+source[2],target[0]+target[2]);start=source[1]+source[3]+margin;end=target[1]-margin
 if right-left<=.1:raise v.PolishError('READING_MODULES_NEED_COLUMN_ALIGNMENT')
 if end-start<READING_MIN_LENGTH-1e-6:raise v.PolishError('READING_GAP_TOO_SMALL: align/space existing text modules; do not bend or shrink')
 x=(left+right)/2 if axis_x is None else axis_x
 if not left+.04<=x<=right-.04:raise v.PolishError('READING_AXIS_OUTSIDE_MODULE_COLUMN')
 return [[x,start],[x,end]]

def native_reading_connector(q,path):
 import polish_presentation as v
 import visual_polish_locked as L
 if len(path)!=2 or abs(path[0][0]-path[1][0])>1e-6 or path[1][1]<=path[0][1]:raise v.PolishError('READING_ARROW_MUST_BE_STRAIGHT_DOWN')
 if v.shape_text(q) or q.xpath('.//p:stCxn|.//p:endCxn',namespaces=v.NS):raise v.PolishError('READING_GUIDE_NOT_UNBOUND_PRESENTATION_OBJECT')
 L.path_shape(q,path);q.tag='{'+v.NS['p']+'}cxnSp';nv=q.find('p:nvSpPr',v.NS)
 if nv is not None:
  nv.tag='{'+v.NS['p']+'}nvCxnSpPr';p=nv.find('p:cNvSpPr',v.NS)
  if p is not None:p.tag='{'+v.NS['p']+'}cNvCxnSpPr'
 for body in q.findall('p:txBody',v.NS):q.remove(body)
 q.find('p:spPr/a:xfrm/a:ext',v.NS).set('cx','0')
 L.style_shape(q,READING_STYLE)

def rect_hit(a,b,rect,pad=0):
 """Liang-Barsky segment vs rectangle, including diagonal crossing."""
 x,y,w,h=rect;x-=pad;y-=pad;w+=2*pad;h+=2*pad
 dx,dy=b[0]-a[0],b[1]-a[1];lo,hi=0.,1.
 for p,q in [(-dx,a[0]-x),(dx,x+w-a[0]),(-dy,a[1]-y),(dy,y+h-a[1])]:
  if abs(p)<1e-12:
   if q<0:return False
  elif p<0:lo=max(lo,q/p)
  else:hi=min(hi,q/p)
  if lo>hi:return False
 return True

def overlap(a,b,pad=0):return min(a[0]+a[2],b[0]+b[2])-max(a[0],b[0])>pad and min(a[1]+a[3],b[1]+b[3])-max(a[1],b[1])>pad

def border(p,r,tol=.065):
 x,y,w,h=r;px,py=p
 return (x-tol<=px<=x+w+tol and min(abs(py-y),abs(py-y-h))<=tol) or (y-tol<=py<=y+h+tol and min(abs(px-x),abs(px-x-w))<=tol)

def correct_normal(point,neighbour,rect,at_source,tol=.065):
 x,y,w,h=rect;px,py=point;normals=[]
 for distance,n in [(abs(px-x),(-1,0)),(abs(px-x-w),(1,0)),(abs(py-y),(0,-1)),(abs(py-y-h),(0,1))]:
  if distance<=tol:normals.append(n)
 dx,dy=(neighbour[0]-px,neighbour[1]-py) if at_source else (px-neighbour[0],py-neighbour[1]);sign=1 if at_source else -1
 return any(sign*(dx*nx+dy*ny)>1e-6 for nx,ny in normals)

def points(q):
 import polish_presentation as v
 import visual_polish_locked as L
 x,box=L.bounds(q);left,top,w,h=box
 path=q.find('p:spPr/a:custGeom/a:pathLst/a:path',v.NS)
 if path is not None:
  pw,ph=float(path.get('w')),float(path.get('h'));return [[left+float(p.get('x'))/pw*w,top+float(p.get('y'))/ph*h] for p in path.xpath('./a:moveTo/a:pt|./a:lnTo/a:pt',namespaces=v.NS)]
 return [[left+(w if x.get('flipH')=='1' else 0),top+(h if x.get('flipV')=='1' else 0)],[left+(0 if x.get('flipH')=='1' else w),top+(0 if x.get('flipV')=='1' else h)]]

def path_intersections(a,b):
 out=[]
 for p,q in zip(a,a[1:]):
  for r,s in zip(b,b[1:]):
   dx,dy=q[0]-p[0],q[1]-p[1];ex,ey=s[0]-r[0],s[1]-r[1];cross=dx*ey-dy*ex
   if abs(cross)<1e-10:continue
   tx,ty=r[0]-p[0],r[1]-p[1];t=(tx*ey-ty*ex)/cross;u=(tx*dy-ty*dx)/cross
   if 1e-5<t<1-1e-5 and 1e-5<u<1-1e-5:out.append([p[0]+t*dx,p[1]+t*dy])
 return out

def audit(path,context,design,office_page=None):
 import polish_presentation as v
 import visual_polish_locked as L
 data=v.package(path);part=v.active_parts(data)[design['slide']-1];root=v.xml(data,part);tree=root.find('p:cSld/p:spTree',v.NS);objects={v.shape_id(q):q for q in tree if v.shape_id(q)};order={v.shape_id(q):i for i,q in enumerate(tree) if v.shape_id(q)}
 graph=next(g for g in context['display_topology'] if g['slide']==design['slide']);node_ids=graph.get('nodes') or {str(sid):sid for e in graph['edges'] for sid in [e['source_shape_id'],e['target_shape_id']]};nodes={k:L.bounds(objects[sid])[1] for k,sid in node_ids.items()};label_ids=design.get('connector_qa',{}).get('label_ids',[])
 if graph['edges'] and all(is_reading_edge(root,e) for e in graph['edges']):return audit_reading_guides(path,context,design,office_page)
 actual={p['id']:[z/72 for z in p['text_bounds']] for p in (office_page or {}).get('text_objects',[]) if 'text_bounds' in p}
 texts={}
 for sid,q in objects.items():
  if not v.shape_text(q):continue
  r=list(L.bounds(q)[1]);bp=q.find('p:txBody/a:bodyPr',v.NS)
  if bp is not None:
   ml,mt,mr,mb=[int(bp.get(k,'0'))/914400 for k in ['lIns','tIns','rIns','bIns']];r=[r[0]+ml,r[1]+mt,max(.001,r[2]-ml-mr),max(.001,r[3]-mt-mb)]
  texts[sid]=actual.get(sid,r)
 issues=[];rows=[];seenpaths={}
 for e in graph['edges']:
  segments=[];styles=[];missing=[]
  for sid in e['shape_ids']:
   if sid not in objects:missing.append(sid);continue
   q=objects[sid];p=points(q)
   if segments and math.dist(segments[-1],p[0])>.025:issues.append(dict(edge=e['id'],code='CONNECTOR_PIECE_DISCONTINUITY'))
   segments.extend(p if not segments else p[1:]);ln=q.find('p:spPr/a:ln',v.NS);styles.append(dict(shape_id=sid,width_pt=int(ln.get('w','0'))/12700,tail_type=(ln.find('a:tailEnd',v.NS).get('type') if ln.find('a:tailEnd',v.NS) is not None else None),tail_size=(dict(ln.find('a:tailEnd',v.NS).attrib) if ln.find('a:tailEnd',v.NS) is not None else {})))
  source=L.bounds(objects[e['source_shape_id']])[1];target=L.bounds(objects[e['target_shape_id']])[1]
  row=dict(edge_id=e['id'],exists=not missing,source_matches=bool(segments) and border(segments[0],source),target_matches=bool(segments) and border(segments[-1],target),target_arrow=bool(styles) and styles[-1]['tail_type'] not in [None,'none'],styles=styles,label_hits=[],node_hits=[],text_hits=[],tip_occluded=[])
  row['source_departs_outward']=len(segments)>1 and correct_normal(segments[0],segments[1],source,True);row['target_approaches_inward']=len(segments)>1 and correct_normal(segments[-1],segments[-2],target,False)
  if missing:issues.append(dict(edge=e['id'],code='MISSING_EDGE_SHAPES',ids=missing))
  if styles and min(s['width_pt'] for s in styles)<1.4:issues.append(dict(edge=e['id'],code='CONNECTOR_TOO_THIN'))
  if styles and (styles[-1]['tail_size'].get('w')=='sm' or styles[-1]['tail_size'].get('len')=='sm'):issues.append(dict(edge=e['id'],code='TARGET_ARROWHEAD_TOO_SMALL'))
  for k in ['source_matches','target_matches','target_arrow','source_departs_outward','target_approaches_inward']:
   if not row[k]:issues.append(dict(edge=e['id'],code='INVALID_'+k.upper()))
  for sid,r in texts.items():
   if any(rect_hit(a,b,r,.035 if sid in label_ids else .01) for a,b in zip(segments,segments[1:])):
    row['text_hits'].append(sid)
    if sid in label_ids:row['label_hits'].append(sid)
  for key,r in nodes.items():
   if node_ids[key] in [e['source_shape_id'],e['target_shape_id']]:continue
   if any(rect_hit(a,b,r,.045) for a,b in zip(segments,segments[1:])):row['node_hits'].append(key)
  for field in ['text_hits','node_hits']:
   if row[field]:issues.append(dict(edge=e['id'],code='CONNECTOR_'+field.upper(),ids=row[field]))
  # Arrow back/body is outside target. Check visible front objects at the tip;
  # endpoint target border itself is an intended contact, not an occluder.
  for sid,q in objects.items():
   if not segments or order[sid]<=order[e['shape_ids'][-1]] or sid in e['shape_ids']+[e['target_shape_id'],e['source_shape_id']]:continue
   filled=q.find('p:spPr/a:solidFill',v.NS) is not None or q.tag.endswith('pic')
   if filled and rect_hit(segments[-1],segments[-1],L.bounds(q)[1],-.01):row['tip_occluded'].append(sid)
  if row['tip_occluded']:issues.append(dict(edge=e['id'],code='ARROW_TIP_OCCLUDED',ids=row['tip_occluded']))
  seenpaths[e['id']]=segments;row['points']=segments;rows.append(row)
 overlaps=[]
 for a,b in itertools.combinations(label_ids,2):
  if a in texts and b in texts and overlap(texts[a],texts[b]):overlaps.append([a,b])
 if overlaps:issues.append(dict(code='LABEL_LABEL_OVERLAP',pairs=overlaps))
 for label in label_ids:
  for sid,rect in texts.items():
   if sid not in label_ids and overlap(texts[label],rect):issues.append(dict(code='LABEL_OTHER_TEXT_OVERLAP',label=label,shape=sid))
 crossings=[]
 for a,b in itertools.combinations(rows,2):
  pts=path_intersections(a['points'],b['points'])
  if pts:crossings.append(dict(edges=[a['edge_id'],b['edge_id']],points=pts,meaning='Geometric crossing, never a new scientific junction; requires PNG review.'))
 return dict(valid=not issues,issues=issues,edges=rows,label_overlaps=overlaps,edge_crossings=crossings,boundary_basis='PowerPoint TextRange2 actual bounds' if actual else 'Conservative text-box bounds',display_geometry_only=True,visual_status='PENDING_AGENT_AND_USER',scientific_relations_changed=False)

def audit_reading_guides(path,context,design,office_page=None):
 import polish_presentation as v
 import visual_polish_locked as L
 data=v.package(path);root=v.xml(data,v.active_parts(data)[design['slide']-1]);graph=next(g for g in context['display_topology'] if g['slide']==design['slide']);actual={p['id']:[z/72 for z in p['text_bounds']] for p in (office_page or {}).get('text_objects',[]) if 'text_bounds' in p};issues=[];rows=[]
 for e in graph['edges']:
  q=v.top_shape(root,e['shape_ids'][0]);pp=points(q);source=L.bounds(v.top_shape(root,e['source_shape_id']))[1];target=L.bounds(v.top_shape(root,e['target_shape_id']))[1];ln=q.find('p:spPr/a:ln',v.NS);head=ln.find('a:tailEnd',v.NS);color=ln.find('a:solidFill/a:srgbClr',v.NS);geom=q.find('p:spPr/a:prstGeom',v.NS)
  simple=len(pp)==2 and abs(pp[0][0]-pp[-1][0])<.001 and pp[-1][1]>pp[0][1];gap0=pp[0][1]-source[1]-source[3];gap1=target[1]-pp[-1][1]
  row=dict(edge_id=e['id'],kind='presentation_reading_guide',shape_id=e['shape_ids'][0],points=pp,native_straight=q.tag=='{'+v.NS['p']+'}cxnSp' and geom is not None and geom.get('prst')=='straightConnector1',vertical_down=simple,bends=max(0,len(pp)-2),source_gap=gap0,target_gap=gap1,gaps_equal=abs(gap0-READING_MARGIN)<.003 and abs(gap1-READING_MARGIN)<.003,line_width_pt=int(ln.get('w'))/12700,color=color.get('val') if color is not None else None,arrow_type=head.get('type') if head is not None else None,arrow_size=[head.get('w'),head.get('len')] if head is not None else [],text_hits=[],image_hits=[])
  for sid,r in actual.items():
   if any(rect_hit(a,b,r,.02) for a,b in zip(pp,pp[1:])):row['text_hits'].append(sid)
  for obj in root.findall('p:cSld/p:spTree/p:pic',v.NS):
   if any(rect_hit(a,b,L.bounds(obj)[1],.02) for a,b in zip(pp,pp[1:])):row['image_hits'].append(v.shape_id(obj))
  row['valid']=is_reading_edge(root,e) and row['native_straight'] and row['vertical_down'] and row['gaps_equal'] and row['color']==READING_STYLE['line'] and abs(row['line_width_pt']-READING_STYLE['line_width'])<.01 and row['arrow_type']=='triangle' and row['arrow_size']==['med','med'] and not row['text_hits'] and not row['image_hits']
  if not row['valid']:issues.append(dict(edge=e['id'],code='READING_GUIDE_NOT_STRAIGHT_VISIBLE_OR_CLEAR'))
  rows.append(row)
 axes=[r['points'][0][0] for r in rows];aligned=bool(axes) and max(axes)-min(axes)<.003
 if not aligned:issues.append(dict(code='READING_GUIDE_AXES_NOT_ALIGNED'))
 return dict(valid=not issues,issues=issues,reading_guides=rows,common_axis=aligned,boundary_basis='PowerPoint actual text bounds' if actual else 'Preflight native geometry',scientific_relationships_added=0,visual_status='PENDING_AGENT_AND_USER')

def audit_autoshapes(path,design,office_page=None):
 import polish_presentation as v
 import visual_polish_locked as L
 data=v.package(path);root=v.xml(data,v.active_parts(data)[design['slide']-1]);wanted=design['connector_qa']['reading_autoshape_ids'];actual={p['id']:[z/72 for z in p['text_bounds']] for p in (office_page or {}).get('text_objects',[]) if 'text_bounds' in p};issues=[];rows=[]
 for sid in wanted:
  q=v.top_shape(root,sid);r=L.bounds(q)[1];geom=q.find('p:spPr/a:prstGeom',v.NS);solid=q.find('p:spPr/a:solidFill/a:srgbClr',v.NS);hits=[tid for tid,rect in actual.items() if overlap(r,rect)];valid=geom is not None and geom.get('prst') in ['downArrow','rightArrow'] and min(r[2:])>=.14 and solid is not None and solid.get('val')=='174994' and not hits
  row=dict(shape_id=sid,kind='presentation_reading_guide',exists=True,native_arrow=geom.get('prst') if geom is not None else None,bounds=r,text_hits=hits,valid=valid);rows.append(row)
  if not valid:issues.append(dict(shape=sid,code='READING_GUIDE_VISIBILITY_OR_OVERLAP'))
 return dict(valid=not issues,issues=issues,reading_guides=rows,scientific_relationships_added=0,visual_status='PENDING_AGENT_AND_USER')
