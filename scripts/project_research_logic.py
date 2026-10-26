"""Editable graph views of one reviewed research-logic model; no scientific inference."""
from __future__ import annotations
import copy,json,math
from pathlib import Path
import research_logic as rl
from presentation_typography import wrap
BLUE='#174994';DARK='#18365C'
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
def build_scene(network,model,view='A'):
    nm={x['id']:x for x in model['nodes']};em={x['id']:x for x in model['edges']}
    if view in ['A','B']:
        ids=list(model['core']['nodes']);eids=list(model['core']['edges']);detail=view=='B'
        if detail:
            ids += [x['id'] for x in model['nodes'] if x['kind']=='shared_method']
            eids += [e['id'] for e in model['edges'] if e['type']=='shared_workflow' and e['from'] in ids and e['to'] in ids]
            eids += [e['id'] for e in model['edges'] if e['from'] in ids and e['to'] in ids and e['id'] not in eids]
        title='全文科研逻辑' if view=='A' else '综述主题证据与论证逻辑' if network['paper']['paper_type'] in ['review','perspective'] else '完整科研逻辑与实验设计'
    else:
        branch=next(x for x in model['branches'] if x['id']==view);ids=branch['nodes'];eids=branch['edges'];detail=False;title=branch['title']
    layout=copy.deepcopy(model['layout'].get(view) or _default_positions(model,view,ids));width,height=layout['width'],layout['height'];pos=layout['positions']
    if set(pos)!=set(ids):raise ValueError('LOGIC_LAYOUT_NODE_COVERAGE: '+view)
    elements=[];connectors=[];statement_ids=[];nodeids=[];figures=[];body_refs=[]
    sid='LOGIC_'+view
    if view!='A':elements.append(text(sid+'_title',title,[60,75,width-120,65],46,True))
    if view!='A':elements.append(box(sid+'_bar',[0,0,width,15],BLUE,BLUE))
    for nid in ids:
        node=nm[nid];p=pos[nid];x,y,w,h=p
        if node['kind']=='question' or (view=='A' and node['kind']=='synthesis'):
            if node['kind']!='question':elements.append(box(sid+'_'+nid+'_frame',p,'#FFF9EF'))
            e=text(sid+'_'+nid+'_body',node['short_text'],[x+12,y+8,w-24,h-16],31 if node['kind']=='question' and view=='A' else 38 if view=='B' else 25,True)
            e['logic_node_id']=nid;e['statement_ids']=node['statement_ids'];e['source_node_ids']=node['source_entity_ids'];elements.append(e)
            statement_ids+=node['statement_ids'];nodeids+=node['source_entity_ids'];body_refs.append(nid);continue
        elements.append(box(sid+'_'+nid+'_frame',p,'#FFF9EF' if node['identity']=='AUTHOR_INTERPRETATION' else '#F5F8FD'))
        ftitle=27 if view=='A' else 38 if view=='B' else 34
        fbody=22 if view=='A' else 31 if view=='B' else 30
        titleh=ftitle*1.55
        tt=text(sid+'_'+nid+'_label',node['title'],[x+16,y+10,w-32,titleh],ftitle,True);tt['logic_node_id']=nid;elements.append(tt)
        value=node.get('detail_text',node['short_text']) if view=='B' else node['short_text']
        th=h-titleh-28-(62 if view=='B' else 0)
        body=text(sid+'_'+nid+'_body',value,[x+16,y+titleh+13,w-32,th],fbody)
        body['logic_node_id']=nid;body['statement_ids']=node['statement_ids'];body['source_node_ids']=node['source_entity_ids'];body['field_bindings']=node['field_bindings'];elements.append(body)
        statement_ids+=node['statement_ids'];nodeids+=node['source_entity_ids'];body_refs.append(nid)
        if view=='B':
            ref=(node.get('figure_reference','')+'  p'+','.join(str(p) for p in sorted({model['sources'][s]['physical_page'] for s in node['source_ids']}))+'  PARTIAL').strip()
            elements.append(text(sid+'_'+nid+'_source',ref,[x+16,y+h-54,w-32,45],22,color='#61748A'))
    for i,eid in enumerate(eids):
        e=em[eid];hint=layout.get('routes',{}).get(eid,{})
        points=hint.get('points') or _route(pos[e['from']],pos[e['to']],i,width)
        c={'id':sid+'_'+eid,'points':points,'identity':e['identity'],'source_relation_id':None,'source_logic_relation_id':eid,'relation_type':e['type'],'arrow':e['type']!='complements','dashed':e['identity'] in ['AUTHOR_ARGUMENT','AUTHOR_INTERPRETATION','SHARED_PROTOCOL','PRESENTATION'],'color':'#8A5B20' if e['identity']=='AUTHOR_INTERPRETATION' else '#738598' if e['identity']=='SHARED_PROTOCOL' else BLUE}
        connectors.append(c)
        label=hint.get('label_position')
        if label:
            elements.append(text(sid+'_'+eid+'_relation',e.get('display_label',e['label']),label,15 if view=='A' else 24,color=c['color']))
    core_members={nid:[x['id'] for x in model['nodes'] if x.get('parent_id')==nid] for nid in ids}
    legend='实线：科学证据关系   蓝虚线：作者论证   棕虚线：机制解释/假说   灰虚线：共享流程\n论证顺序不等于实验历史；未知重复及缺失补件不自动补全。'
    if view=='A':legend='实线：证据   蓝虚线：论证   棕虚线：假说/解释   灰虚线：共享流程；均不等于真实实验历史'
    elements.append(text(sid+'_legend',legend,[60,height-48 if view=='A' else height-145,width-120,22 if view=='A' else 72],13 if view=='A' else 25,color='#61748A'))
    allsourceids=list(dict.fromkeys(s for nid in ids for s in nm[nid]['source_ids']))
    citation=model.get('short_citation',model['paper_title'])+' · p'+', '.join(str(p) for p in sorted({model['sources'][s]['physical_page'] for s in allsourceids}))+' · model '+model['snapshot'][:12]
    scene={'id':sid,'product':'A' if view=='A' else 'LOGIC','section':'科研逻辑简要图' if view=='A' else title,'title':title,'elements':elements,'connectors':connectors,
           'source_statement_ids':list(dict.fromkeys(statement_ids)),'source_node_ids':list(dict.fromkeys(nodeids)),'source_relation_ids':[],'figure_ids':figures,'citation':citation,
           'source_logic_node_ids':ids,'source_logic_relation_ids':eids,'logic_snapshot':model['snapshot'],
           'notes':{'scientific_question':nm[model['core']['nodes'][0]]['short_text'],'logic_model_snapshot':model['snapshot'],'logic_source_ids':allsourceids,'logic_relations':[em[e] for e in eids],'logical_members':core_members,'formal_ready':False,'source_mapping_status':'PARTIAL','paper_type':network['paper']['paper_type'],'scientific_limits':['论证推进不代表实验日历或分子因果；源字段状态和缺失补件见科学索引及Inventory。']},
           'coverage':{'view':view,'logic_node_ids':ids,'logical_members':core_members,'new_M1_entities':0,'repeated_experiment_counting':False}}
    return {'kind':'main' if view=='A' else 'detail' if view=='B' else 'branch_'+view,'width':width,'height':height,'slides':[scene]}
def sample_products(network,metadata,views):
    m=read_model(network,metadata)
    if m is None:raise ValueError('RESEARCH_LOGIC_REQUIRED')
    return [build_scene(network,m,v) for v in views]
def validate_AB(model,A,B):
    a=A['slides'][0];b=B['slides'][0]
    core=rl.compress_to_core(model,b['source_logic_node_ids'],b['source_logic_relation_ids'])
    errors=[]
    if core['nodes']!=sorted(a['source_logic_node_ids']) or core['edges']!=sorted(a['source_logic_relation_ids']):errors.append('B_NOT_COMPRESSIBLE_TO_A')
    if a['logic_snapshot']!=b['logic_snapshot']:errors.append('A_B_MODEL_DRIFT')
    return {'valid':not errors,'errors':errors,'same_model':model['snapshot'],'scientific_review':'PARTIAL'}

def main():
    import argparse,hashlib
    import project_evidence_products as pp
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--network',required=True,type=Path);p.add_argument('--model',required=True,type=Path);p.add_argument('--outdir',required=True,type=Path);p.add_argument('--views',nargs='+',default=['A','B']);p.add_argument('--metadata',type=Path);p.add_argument('--template',type=Path)
    a=p.parse_args();net=rl.load(a.network);meta=rl.load(a.metadata) if a.metadata else {};meta['research_logic']={'path':str(a.model.resolve()),'sha256':rl.file_sha(a.model)}
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
