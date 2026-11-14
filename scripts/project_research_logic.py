"""Editable graph views of one reviewed research-logic model; no scientific inference."""
from __future__ import annotations
import copy,json,math
from pathlib import Path
import research_logic as rl
from presentation_typography import wrap
BLUE='#174994';DARK='#18365C'

def directed_relation(edge):
    """Registered evidence/argument direction is not biological causality.

    Geometry is irrelevant. Scientific complements use their evidence->task
    orientation; symmetric comparisons and shared protocols remain undirected.
    """
    if edge['type'] in {'parallel','comparison','shared_workflow'}:return False
    if edge['identity']=='SHARED_PROTOCOL':return False
    if edge['type']=='complements':return edge['identity']=='SCIENTIFIC_EVIDENCE'
    return True
def read_model(network,metadata):
    rec=metadata.get('research_logic')
    if not rec:return None
    if rl.file_sha(rec['path'])!=rec['sha256']:raise ValueError('RESEARCH_LOGIC_FILE_DRIFT')
    m=rl.load(rec['path']);check=rl.validate_model(m,network)
    if not check['valid']:raise ValueError('RESEARCH_LOGIC_INVALID: '+json.dumps(check['errors'],ensure_ascii=False))
    return m
def text(id,value,p,size=25,bold=False,color=DARK):
    value=wrap(value,p[2],size,bold=bold)
    if len(value.split('\n'))*size*1.22>p[3]+4:raise ValueError('LOGIC_TEXT_FIT: '+id)
    return {'kind':'text','id':id,'text':value,'position':dict(zip(['left','top','width','height'],p)),'font_size':size,'bold':bold,'color':color,'statement_ids':[]}
def box(id,p,fill='#F5F8FD',stroke='#B8CBE6'):
    return {'kind':'rect','id':id,'position':dict(zip(['left','top','width','height'],p)),'fill':fill,'stroke':stroke}
def _rect(v):return dict(zip(['x','y','w','h'],v))
def _default_positions(model,view,ids):
    # General DAG ranking is a display fallback only. It never adds an edge.
    selected=set(ids);rank={x:0 for x in ids}
    edges=[e for e in model['edges'] if e['from'] in selected and e['to'] in selected and e['type'] not in ['shared_workflow','qualifies']]
    for _ in range(len(ids)):
        changed=False
        for e in edges:
            v=rank[e['from']]+1
            if rank[e['to']]<v:rank[e['to']]=v;changed=True
        if not changed:break
    if max(rank.values(),default=0)>=len(ids):raise ValueError('LOGIC_CYCLE_NEEDS_EXPLICIT_VIEW')
    groups={r:[x for x in ids if rank[x]==r] for r in sorted(set(rank.values()))};out={}
    for r,nodes in groups.items():
        for j,nid in enumerate(nodes):out[nid]=[70+r*580,210+j*340,490,250]
    return {'width':max(1280,(max(rank.values(),default=0)+1)*580+100),'height':max(720,max((len(v) for v in groups.values()),default=1)*340+300),'positions':out}
def _route(a,b,lane,width):
    ax,ay,aw,ah=a;bx,by,bw,bh=b
    if abs(ay-by)<2:
        return [[ax+aw,ay+ah/2],[bx,by+bh/2]] if bx>ax else [[ax,ay+ah/2],[bx+bw,by+bh/2]]
    if bx<=ax+aw/2<=bx+bw and not (abs(ay-by)<2):
        x=ax+aw/2
        if by>ay:return [[x,ay+ah],[x,by]]
        return [[x,ay],[x,by+bh]]
    if bx>ax:
        mid=(ax+aw+bx)/2
        return [[ax+aw,ay+ah/2],[mid,ay+ah/2],[mid,by+bh/2],[bx,by+bh/2]]
    mid=(bx+bw+ax)/2
    return [[ax,ay+ah/2],[mid,ay+ah/2],[mid,by+bh/2],[bx+bw,by+bh/2]]

def route_hits_node(points,positions,endpoints):
    for nid,(x,y,w,h) in positions.items():
        if nid in endpoints:continue
        for (a,b),(c,d) in zip(points,points[1:]):
            if a==c and x-6<a<x+w+6 and max(min(b,d),y-6)<min(max(b,d),y+h+6):return True
            if b==d and y-6<b<y+h+6 and max(min(a,c),x-6)<min(max(a,c),x+w+6):return True
    return False

def safe_route(positions,source,target,lane,width):
    a,b=positions[source],positions[target];points=_route(a,b,lane,width)
    if not route_hits_node(points,positions,{source,target}):return points
    ax,ay,aw,ah=a;bx,by,bw,bh=b
    # Reuse a small bounded set of channels immediately below the node band.
    # The former `lane*30` used the GLOBAL edge index, so every later fallback
    # edge was pushed progressively further down. B then grew its canvas to
    # accommodate those empty detour lanes (blank lower third + very long
    # vertical runs). Bounding the channel count keeps detours short without
    # dropping any relation or shrinking any text.
    bottom=max(p[1]+p[3] for p in positions.values())+60+(lane%3)*26
    points=[[ax+aw,ay+ah/2],[ax+aw+22,ay+ah/2],[ax+aw+22,bottom],[bx-22,bottom],[bx-22,by+bh/2],[bx,by+bh/2]]
    if route_hits_node(points,positions,{source,target}):raise ValueError('LOGIC_ROUTE_NEEDS_EXPLICIT_CHANNEL: '+source+' '+target)
    return points
# Projection-only display fields. research_logic.validate_model() checks
# scientific identity/source contracts but intentionally does NOT check these;
# build_scene() dereferences them unconditionally. Without an explicit gate a
# model can be `valid:true` and still crash later with a bare KeyError: 'kind'.
DISPLAY_NODE_FIELDS=('kind','identity','title','short_text','source_ids',
                     'statement_ids','source_entity_ids','field_bindings')

def validate_display_contract(model,node_ids=None):
    """Fail early with an actionable code instead of a renderer KeyError."""
    nm={x['id']:x for x in model['nodes']}
    ids=list(node_ids) if node_ids is not None else [x['id'] for x in model['nodes']]
    missing=[]
    for nid in ids:
        node=nm.get(nid)
        if node is None:
            missing.append(str(nid)+' / NODE_NOT_FOUND');continue
        for field in DISPLAY_NODE_FIELDS:
            if field not in node:missing.append(str(nid)+' / '+field)
    return {'valid':not missing,'errors':missing,
            'code':'LOGIC_DISPLAY_FIELD_REQUIRED'}

def require_display_contract(model,node_ids=None):
    q=validate_display_contract(model,node_ids)
    if not q['valid']:
        raise ValueError('LOGIC_DISPLAY_FIELD_REQUIRED: '+', '.join(q['errors'])+
                         '; projection display fields are required even though '
                         'validate_model() does not check them')

# Scene units are 96-dpi px. A tailEnd triangle is drawn at the final point of
# a connector and extends BACK along the last segment. When that point lies on
# a filled node frame, the frame (painted after connectors) clips the triangle.
# Retreating the endpoint one arrow-length keeps the whole head in the visible
# band outside the card. Z-order is intentionally NOT changed.
ARROW_ENDPOINT_RETREAT = 12

def retreat_arrow_endpoint(points,retreat=None):
    """Return the same path with only its final point pulled back along the
    last segment. Bounded: never crosses the preceding corner."""
    gap=ARROW_ENDPOINT_RETREAT if retreat is None else retreat
    if len(points)<2 or gap<=0:return points
    a,b=points[-2],points[-1]
    dx,dy=b[0]-a[0],b[1]-a[1]
    length=math.hypot(dx,dy)
    if length<=gap:return points
    moved=[b[0]-dx/length*gap,b[1]-dy/length*gap]
    return list(points[:-1])+[moved]

def read_display(model,metadata):
    rec=metadata.get('logic_display')
    if not rec:return None
    if rl.file_sha(rec['path'])!=rec['sha256']:raise ValueError('LOGIC_DISPLAY_DRIFT')
    d=rl.load(rec['path'])
    if d.get('logic_snapshot')!=model['snapshot'] or d.get('formal_ready') is not False:raise ValueError('LOGIC_DISPLAY_VERSION_OR_REVIEW')
    nm={n['id']:n for n in model['nodes']};em={e['id']:e for e in model['edges']}
    for nid,r in d.get('nodes',{}).items():
        if nid not in nm or not r.get('source_ids') or not set(r['source_ids'])<=set(model['sources']):raise ValueError('LOGIC_DISPLAY_SOURCE')
        if set(r)-{'question','method','discovery','meaning','source_ids'}:raise ValueError('LOGIC_DISPLAY_FACT_OVERRIDE')
    for eid,r in d.get('edges',{}).items():
        if eid not in em or set(r)-{'label','display_note'}:raise ValueError('LOGIC_DISPLAY_EDGE_OVERRIDE')
        if r.get('display_note') and (eid in model['core']['edges'] or not r.get('label')):raise ValueError('CORE_EDGE_CANNOT_BE_HIDDEN')
    views=d.get('views',{})
    if views and d.get('nodes'):
        base=d.get('base_display',{})
        if not base.get('path') or rl.file_sha(base['path'])!=base.get('sha256'):raise ValueError('LOCAL_DISPLAY_BASE_REQUIRED')
        original=rl.load(base['path'])
        if any(d.get(k,{})!=original.get(k,{}) for k in ['nodes','edges']):raise ValueError('LOCAL_DISPLAY_FACT_OVERRIDE')
        for v in ['A','B']:
            if d.get('layout',{}).get(v)!=original.get('layout',{}).get(v):raise ValueError('FROZEN_AB_DISPLAY_OVERRIDE')
    for vid,v in views.items():
        allowed={'title','node_ids','edge_ids','parent_view','logic_snapshot','layout','node_fields','font_sizes','footer_fields','preserve_original_text'}
        if vid in ['A','B'] or set(v)-allowed or v.get('parent_view')!='B' or v.get('logic_snapshot')!=model['snapshot']:raise ValueError('LOCAL_VIEW_IDENTITY')
        ids=v.get('node_ids',[]);eids=v.get('edge_ids',[])
        if not ids or len(ids)!=len(set(ids)) or not set(ids)<=set(nm):raise ValueError('LOCAL_NODE_ID')
        if len(eids)!=len(set(eids)) or not set(eids)<=set(em):raise ValueError('LOCAL_EDGE_ID')
        if any(not {em[e]['from'],em[e]['to']}<=set(ids) for e in eids):raise ValueError('LOCAL_EDGE_ENDPOINT')
        if set(v.get('node_fields',{}))-set(ids):raise ValueError('LOCAL_FIELD_NODE')
        for fields in v.get('node_fields',{}).values():
            if not fields or not set(fields)<={'title','short_text','method','discovery','meaning'}:raise ValueError('LOCAL_FIELD_REFERENCE')
        for f in v.get('footer_fields',[]):
            if set(f)!={'node_id','field','position'} or f['node_id'] not in ids or f['field'] not in ['method','discovery','meaning','short_text']:raise ValueError('LOCAL_FOOTER_REFERENCE')
        layout=v.get('layout',{});positions=layout.get('positions',{});routes=layout.get('routes',{})
        if set(positions)!=set(ids) or not set(routes)<=set(eids):raise ValueError('LOCAL_LAYOUT_ID')
        def on_boundary(point,rect):
            a,b=point;x,y,w,h=rect
            return x-1<=a<=x+w+1 and y-1<=b<=y+h+1 and min(abs(a-x),abs(a-x-w),abs(b-y),abs(b-y-h))<=1
        for eid,r in routes.items():
            points=r.get('points',[])
            if points and (len(points)<2 or not on_boundary(points[0],positions[em[eid]['from']]) or not on_boundary(points[-1],positions[em[eid]['to']])):raise ValueError('LOCAL_ROUTE_ENDPOINT')
    return d
def build_scene(network,model,view='A',display=None):
    # Earliest point where the display contract is actually consumed.
    require_display_contract(model)
    nm={x['id']:x for x in model['nodes']};em={x['id']:x for x in model['edges']}
    local=(display or {}).get('views',{}).get(view)
    if view in ['A','B']:
        ids=list(model['core']['nodes']);eids=list(model['core']['edges']);detail=view=='B'
        if detail:
            ids=[x['id'] for x in model['nodes']]
            eids=[e['id'] for e in model['edges']]
        title='全文科研逻辑' if view=='A' else '综述主题证据与论证逻辑' if network['paper']['paper_type'] in ['review','perspective'] else '完整科研逻辑与实验设计'
    elif local:
        ids=local['node_ids'];eids=local['edge_ids'];detail=False;title=local['title']
    else:
        branch=next(x for x in model['branches'] if x['id']==view);ids=branch['nodes'];eids=branch['edges'];detail=False;title=branch['title']
    active=display if display and view!='A' and (local or display.get('nodes')) else None
    layout=copy.deepcopy((local or {}).get('layout') or (active or {}).get('layout',{}).get(view) or model.get('layout',{}).get(view) or _default_positions(model,view,ids))
    if view=='B' and set(layout.get('positions',{}))!=set(ids):layout=_default_positions(model,view,ids)
    width,height=layout['width'],layout['height'];pos=layout['positions']
    if set(pos)!=set(ids):raise ValueError('LOGIC_LAYOUT_NODE_COVERAGE: '+view)
    elements=[];connectors=[];statement_ids=[];nodeids=[];figures=[];body_refs=[]
    sid='LOGIC_'+view
    if view!='A' and not local:elements.append(text(sid+'_title',title,[60,75,width-120,65],46,True))
    if local:elements.append(text(sid+'_scope','完整B的局部科研视图',[60,30,width-120,30],20,color='#61748A'))
    if view!='A':elements.append(box(sid+'_bar',[0,0,width,15],BLUE,BLUE))
    for nid in ids:
        node=nm[nid];p=pos[nid];x,y,w,h=p
        if local:
            shown=(active or {}).get('nodes',{}).get(nid,{})
            fields=local.get('node_fields',{}).get(nid,['method','discovery','meaning'] if shown else ['short_text'])
            ft=local.get('font_sizes',{}).get('title',30);fb=local.get('font_sizes',{}).get('body',26)
            elements.append(box(sid+'_'+nid+'_frame',p,'#FFF9EF' if node['identity']=='AUTHOR_INTERPRETATION' else '#F5F8FD'))
            context=fields==['title']
            if not context:
                th=max(ft*1.3,len(wrap(node['title'],w-32,ft,bold=True).split('\n'))*ft*1.22+2)
                t=text(sid+'_'+nid+'_label',node['title'],[x+16,y+12,w-32,th],ft,True);t['logic_node_id']=nid;elements.append(t)
            else:th=0
            value='\n'.join(({'method':'方法：','discovery':'发现：','meaning':'边界：'}.get(k,''))+(node[k] if k in ['title','short_text'] else shown[k]) for k in fields)
            body=text(sid+'_'+nid+'_body',value,[x+16,y+12 if context else y+th+23,w-32,h-24 if context else h-th-39],ft if context else fb,context)
            body.update(logic_node_id=nid,statement_ids=node['statement_ids'],source_node_ids=node['source_entity_ids'],field_bindings=node['field_bindings']);elements.append(body)
            statement_ids+=node['statement_ids'];nodeids+=node['source_entity_ids'];body_refs.append(nid);continue
        if node['kind']=='question' or (view=='A' and node['kind']=='synthesis'):
            if node['kind']!='question':elements.append(box(sid+'_'+nid+'_frame',p,'#FFF9EF'))
            e=text(sid+'_'+nid+'_body',node['short_text'],[x+12,y+8,w-24,h-16],31 if node['kind']=='question' and view=='A' else 38 if view=='B' else 25,True)
            e['logic_node_id']=nid;e['statement_ids']=node['statement_ids'];e['source_node_ids']=node['source_entity_ids'];elements.append(e)
            statement_ids+=node['statement_ids'];nodeids+=node['source_entity_ids'];body_refs.append(nid);continue
        elements.append(box(sid+'_'+nid+'_frame',p,'#FFF9EF' if node['identity']=='AUTHOR_INTERPRETATION' else '#F5F8FD'))
        if active and node['kind']=='shared_method':
            shown=active.get('nodes',{}).get(nid,{})
            value='共用技术：'+shown.get('method',node['short_text'])+'  '+shown.get('meaning','不计为独立验证。')
            e=text(sid+'_'+nid+'_shared',value,[x+20,y+10,w-40,h-20],28,color='#61748A');e['logic_node_id']=nid;e['field_bindings']=node['field_bindings'];elements.append(e)
            statement_ids+=node['statement_ids'];nodeids+=node['source_entity_ids'];body_refs.append(nid);continue
        ftitle=27 if view=='A' else 42 if active else 38 if view=='B' else 34
        fbody=22 if view=='A' else 36 if active else 31 if view=='B' else 30
        shown=(active or {}).get('nodes',{}).get(nid,{})
        padx,pady=(20,12) if active else (16,10)
        title_value=shown.get('question',node['title'])
        titleh=max(ftitle*1.55,len(wrap(title_value,w-2*padx,ftitle,bold=True).split('\n'))*ftitle*1.22+4)
        tt=text(sid+'_'+nid+'_label',shown.get('question',node['title']),[x+padx,y+pady,w-2*padx,titleh],ftitle,True);tt['logic_node_id']=nid;elements.append(tt)
        value=node.get('detail_text',node['short_text']) if view=='B' else node['short_text']
        if shown:value='\n'.join(label+shown[key] for key,label in [('method','方法：'),('discovery','发现：'),('meaning','意义：')] if shown.get(key))
        th=h-titleh-28-(62 if view=='B' else 0)
        body=text(sid+'_'+nid+'_body',value,[x+16,y+titleh+13,w-32,th],fbody)
        body['logic_node_id']=nid;body['statement_ids']=node['statement_ids'];body['source_node_ids']=node['source_entity_ids'];body['field_bindings']=node['field_bindings'];elements.append(body)
        statement_ids+=node['statement_ids'];nodeids+=node['source_entity_ids'];body_refs.append(nid)
        if view=='B':
            ref=(node.get('figure_reference','')+'  p'+','.join(str(p) for p in sorted({model['sources'][s]['physical_page'] for s in node['source_ids']}))+('' if active else '  PARTIAL')).strip()
            elements.append(text(sid+'_'+nid+'_source',ref,[x+16,y+h-54,w-32,45],22,color='#61748A'))
    for i,eid in enumerate(eids):
        e=em[eid];hint=layout.get('routes',{}).get(eid,{})
        shown_edge=(active or {}).get('edges',{}).get(eid,{})
        if shown_edge.get('display_note') and view!='B' and not local:continue
        points=hint.get('points') or safe_route(pos,e['from'],e['to'],i,width)
        if route_hits_node(points,pos,{e['from'],e['to']}):raise ValueError('LOGIC_ROUTE_NODE_COLLISION: '+eid)
        # U1 note: the arrowhead endpoint retreat is a PURE RENDERING transform
        # applied in render_logic._display_points(). The scientific scene here
        # must stay byte-identical, otherwise validate_products() rebuilds a
        # deterministic source-bound plan and reports PRODUCT_PLAN_DRIFT.
        required_height=max(p[1] for p in points)+(65 if view=='A' else 40 if local else 200)
        if required_height>height:
            if view=='A' or local:raise ValueError('LOGIC_A_ROUTE_CAPACITY: use explicit channels within the main-slide canvas')
            height=required_height
        c={'id':sid+'_'+eid,'points':points,'identity':e['identity'],'source_relation_id':None,'source_logic_relation_id':eid,'relation_type':e['type'],'arrow':e['identity']!='SHARED_PROTOCOL' if active else e['type']!='complements','dashed':e['identity'] in ['AUTHOR_ARGUMENT','AUTHOR_INTERPRETATION','PRESENTATION'] if active else e['identity'] in ['AUTHOR_ARGUMENT','AUTHOR_INTERPRETATION','SHARED_PROTOCOL','PRESENTATION'],'color':'#8A5B20' if e['identity']=='AUTHOR_INTERPRETATION' else '#738598' if e['identity']=='SHARED_PROTOCOL' else BLUE}
        if active:c.update(stroke_width=3.5,arrow_size='lg')
        c['arrow']=directed_relation(e)
        c.update(from_node=e['from'],to_node=e['to'])
        connectors.append(c)
        label=hint.get('label_position')
        if label:
            elements.append(text(sid+'_'+eid+'_relation',shown_edge.get('label',e.get('display_label',e.get('label',e['type']))),label,local.get('font_sizes',{}).get('relation',18) if local else 15 if view=='A' else 30 if active else 24,color=c['color']))
    core_members={nid:[x['id'] for x in model['nodes'] if x.get('parent_id')==nid] for nid in ids}
    legend='实线：科学证据关系   蓝虚线：作者论证   棕虚线：机制解释/假说   灰虚线：共享流程\n论证顺序不等于实验历史；未知重复及缺失补件不自动补全。'
    if view=='A':legend='实线：证据   蓝虚线：论证   棕虚线：假说/解释   灰虚线：共享流程；均不等于真实实验历史'
    elif active:legend='蓝实箭头：数据输入、支持或限定（按标签区分）   无箭头蓝线：并行或互补\n蓝虚箭头：论证   棕虚箭头：解释/假说   灰线：共享流程；均不表示真实实验日期或已证明的分子因果。'
    if local:
        for i,f in enumerate(local.get('footer_fields',[])):
            n=nm[f['node_id']];value=n[f['field']] if f['field']=='short_text' else display['nodes'][f['node_id']][f['field']]
            t=text(sid+'_limit_'+str(i),value,f['position'],local.get('font_sizes',{}).get('footer',21),color='#61748A');t['logic_node_id']=n['id'];elements.append(t)
        elements.append(text(sid+'_legend','实箭头：证据支持/输入/限定；虚箭头：作者论证（非因果）；灰线：共享流程，非独立验证。',layout.get('legend_position',[60,height-92,width-120,44]),22,color='#61748A'))
    # A is fitted into a main-slide content area; 13 px became about 8 pt.
    # Keep its one-line legend legible without changing node/footer gates.
    else:elements.append(text(sid+'_legend',legend,[60,height-48 if view=='A' else height-145,width-120,22 if view=='A' else 72],17 if view=='A' else 25,color='#61748A'))
    allsourceids=list(dict.fromkeys(s for nid in ids for s in nm[nid]['source_ids']))
    citation=model.get('short_citation',model['paper_title'])+' · PDF p'+', '.join(str(p) for p in sorted({model['sources'][s]['physical_page'] for s in allsourceids}))
    scene={'id':sid,'product':'A' if view=='A' else 'LOGIC','section':'科研逻辑简要图' if view=='A' else title,'title':title,'elements':elements,'connectors':connectors,
           'source_statement_ids':list(dict.fromkeys(statement_ids)),'source_node_ids':list(dict.fromkeys(nodeids)),'source_relation_ids':[],'figure_ids':figures,'citation':citation,
           'source_logic_node_ids':ids,'source_logic_relation_ids':eids,'logic_snapshot':model['snapshot'],
           'notes':{'scientific_question':nm[model['core']['nodes'][0]]['short_text'],'logic_model_snapshot':model['snapshot'],'logic_source_ids':allsourceids,'logic_relations':[em[e] for e in eids],'logical_members':core_members,'formal_ready':False,'source_mapping_status':'PARTIAL','paper_type':network['paper']['paper_type'],'scientific_limits':['论证推进不代表实验日历或分子因果；源字段状态和缺失补件见科学索引及Inventory。']},
           'coverage':{'view':view,'logic_node_ids':ids,'logical_members':core_members,'new_M1_entities':0,'repeated_experiment_counting':False}}
    if active:scene['notes']['display_only_relations']={eid:r for eid,r in active.get('edges',{}).items() if r.get('display_note') and eid in eids}
    if local:
        scene['coverage'].update(scope='local',parent_view='B',omitted_edge_ids=[e for e in em if e not in eids])
        scene['notes'].update(preserve_original_text=local.get('preserve_original_text',False),local_node_records=[dict(id=nid,title=nm[nid]['title'],source_ids=nm[nid]['source_ids'],fields=copy.deepcopy(display.get('nodes',{}).get(nid,{})),short_text=nm[nid]['short_text']) for nid in ids])
    return {'kind':'main' if view=='A' else 'detail' if view=='B' else 'branch_'+view,'width':width,'height':height,'slides':[scene]}
def sample_products(network,metadata,views):
    m=read_model(network,metadata)
    if m is None:raise ValueError('RESEARCH_LOGIC_REQUIRED')
    # Preflight before any product projection so the CLI reports a specific
    # field list rather than a traceback deep inside the renderer.
    require_display_contract(m)
    display=read_display(m,metadata)
    return [build_scene(network,m,v,display) for v in views]
def validate_AB(model,A,B):
    a=A['slides'][0];b=B['slides'][0]
    core=rl.compress_to_core(model,b['source_logic_node_ids'],b['source_logic_relation_ids'])
    errors=[]
    if core['nodes']!=sorted(a['source_logic_node_ids']) or core['edges']!=sorted(a['source_logic_relation_ids']):errors.append('B_NOT_COMPRESSIBLE_TO_A')
    if a['logic_snapshot']!=b['logic_snapshot']:errors.append('A_B_MODEL_DRIFT')
    if set(b['source_logic_node_ids'])!={n['id'] for n in model['nodes']} or set(b['source_logic_relation_ids'])!={e['id'] for e in model['edges']}:errors.append('B_TOPOLOGY_LOSS')
    return {'valid':not errors,'errors':errors,'same_model':model['snapshot'],'scientific_review':'PARTIAL'}

def main():
    import argparse,hashlib
    import project_evidence_products as pp
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--network',required=True,type=Path);p.add_argument('--model',required=True,type=Path);p.add_argument('--outdir',required=True,type=Path);p.add_argument('--views',nargs='+',default=['A','B']);p.add_argument('--metadata',type=Path);p.add_argument('--template',type=Path)
    a=p.parse_args();net=rl.load(a.network);meta=rl.load(a.metadata) if a.metadata else {};meta['research_logic']={'path':str(a.model.resolve()),'sha256':rl.file_sha(a.model)}
    model=rl.load(a.model)
    meta.setdefault('citation_short',model.get('short_citation',model['paper_title']))
    template=a.template or Path(__file__).resolve().parents[1]/'assets/default_academic_blue_174994.pptx'
    plan=pp.project_products(net,'balanced',meta,{'path':str(template),'sha256':rl.file_sha(template)},{'scope':'logic-views','views':a.views})
    check=pp.validate_products(net,plan,meta)
    if not check['valid']:raise ValueError(str(check))
    a.outdir.mkdir(parents=True,exist_ok=True)
    for name,obj in [('products.plan.json',plan),('metadata.resolved.json',meta),('validation.json',check)]:
        out=a.outdir/name
        if out.exists():raise ValueError('OUTPUT_EXISTS: '+str(out))
        out.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'valid':True,'products':[(x['kind'],len(x['slides'])) for x in plan['products']]}))
    return 0
if __name__=='__main__':raise SystemExit(main())
