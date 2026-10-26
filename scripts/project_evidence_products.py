#!/usr/bin/env python3
"""Versioned A/B/C presentation views; scientific strings remain network references."""
from __future__ import annotations
import copy, hashlib, json, math, re, unicodedata
from display_guidance import load_guidance
from pathlib import Path
from presentation_typography import wrap as mixed_wrap,measure

VERSION = 'pfs-products-1'
BLUE = '#174994'
FONT = 'Microsoft YaHei'

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def wrap(text, width, size):
    """Explicit line breaks, never shrink scientific text or split numeric tokens."""
    return mixed_wrap(text,width,size,bold=True)
    text = str(text)
    capacity = max(4, width / size - 1)
    lines = []
    for paragraph in text.split('\n'):
        tokens = re.findall(r'[A-Za-z0-9]+(?:[./+%−–-][A-Za-z0-9]+)*|\s+|.', paragraph)
        row = ''; units = 0.0
        for token in tokens:
            amount = sum(1.0 if unicodedata.east_asian_width(c) in 'WF' else .57 for c in token)
            if amount>capacity and re.search('[A-Za-z]',token) and not re.fullmatch(r'[0-9./+%−–-]+',token):
                # Long identifiers may wrap at characters; numeric values stay
                # intact. Never allow a single Latin token to escape its box.
                for char in token:
                    unit=1.0 if unicodedata.east_asian_width(char) in 'WF' else .57
                    if row and units+unit>capacity:lines.append(row.rstrip());row='';units=0.0
                    row+=char;units+=unit
                continue
            hanging = token in '，。；：、！？）》】,.!?;:' and bool(row)
            if row and units + amount > capacity and not hanging:
                lines.append(row.rstrip()); row = ''; units = 0.0
            row += token; units += amount
        lines.append(row.rstrip())
    return '\n'.join(lines)

def textbox(identifier, text, x, y, w, h, size=23, bold=False, color='#18365C', statement_ids=None, align='left'):
    return {'kind':'text', 'id':identifier, 'text':text, 'position':{'left':x,'top':y,'width':w,'height':h},
            'font_size':size,'bold':bold,'color':color,'align':align,'statement_ids':statement_ids or []}

def rect(identifier, x, y, w, h, fill='#EDF3FC', stroke='#CFDCEE'):
    return {'kind':'rect','id':identifier,'position':{'left':x,'top':y,'width':w,'height':h},'fill':fill,'stroke':stroke}

def line(identifier, points, identity, relation_id=None, arrow=True, dashed=False):
    return {'id':identifier,'points':points,'identity':identity,'source_relation_id':relation_id,'arrow':arrow,'dashed':dashed}

def _unique(items):
    return list(dict.fromkeys(x for x in items if x))

def _params(node):
    out = {}
    for value in node.get('parameters', []):
        out[value.get('key')] = value
    return out

def _clean_question(value):
    return str(value).replace('：哪些证据支持这一研究任务？','')

def _brief_fragment(value):
    """Select a contiguous source clause for A; never rewrite it into a new claim."""
    value=str(value)
    if len(value)>45:
        for stop in ['；','。']:
            index=value.find(stop)
            if 15<=index<len(value)-1:return value[:index+1]
    return value

def _evidence_nodes(network):
    return [n for n in network['nodes'] if n['kind'] == 'evidence']

def _roles(network, entity, role, profile):
    permitted = set(network['profiles'][profile]['statement_ids'])
    values = [s for s in network['statements'] if s['id'] in permitted and entity in s.get('entity_ids', []) and s['role'] == role]
    # Exact M1 fields precede broad multi-Figure narrative paraphrases.
    return sorted(values, key=lambda s: (s.get('source_pointer', {}).get('input_kind') != 'knowledge',
                                        '/parameters/' not in s.get('source_pointer',{}).get('pointer',''), s['id']))

def _source_pages(statements):
    return sorted({r.get('locator',{}).get('physical_page') for s in statements for r in s.get('source_refs',[]) if r.get('locator',{}).get('physical_page')})

def _citation(network, metadata, figures, statements):
    labels = {f['id']:f.get('label', f['id']) for f in network['figures']}
    author = metadata.get('citation_short', network['paper'].get('title','来源论文'))
    doi = metadata.get('doi') or '待核实'
    sources = '、'.join(labels.get(f, f) for f in figures) or ('PDF p.' + ','.join(map(str, _source_pages(statements))))
    return f'{author} · {sources} · DOI {doi}'

def _notes(network, statements, question, meta, figure_ids):
    return {'scientific_question':question, 'paper_type':network['paper']['paper_type'],
            'figure_ids':figure_ids, 'recommended_order':[s['id'] for s in statements],
            'statements':copy.deepcopy(statements), 'scientific_limits':meta.get('minimal_scientific_limits',[]),
            'network_snapshot':network['snapshot'], 'formal_ready':False,
            'relationship_boundary':'Narrative arrows connect statements only; they do not add scientific edges or historical experiment order.',
            'unknown_fields':'Not checked is not equivalent to not reported; dots are not biological replicate counts.'}

def _question(network):
    for s in network['statements']:
        if s.get('source_pointer',{}).get('input_kind') == 'narrative' and ('？' in s['text'] or '?' in s['text']):
            return s['text'], [s['id']]
    s = network['rsus'][0]
    ids = [t['id'] for t in network['statements'] if s['id'] in t.get('rsu_ids',[]) and t['role']=='purpose']
    return _clean_question(s['question']), ids[:1]

def _rsu_for(network, eid):
    return [r for r in network['rsus'] if eid in r['evidence_ids']]

def _statement_for_text(network, entity_id, text):
    return [s['id'] for s in network['statements'] if entity_id in s.get('entity_ids',[]) and s['text']==text]

def _grid_overview_retained_for_history(network, profile, meta):
    evidences = _evidence_nodes(network)
    q, qids = _question(network)
    elements = [textbox('A_title', q, 60,65,1160,65,30,True,statement_ids=qids)]
    connectors=[]; positions={}; mapping={}; evidence_refs=[]
    cols=3 if len(evidences)>4 else 2
    rows=math.ceil(len(evidences)/cols)
    card_w=(1150-(cols-1)*38)/cols
    card_h=min(185, 480/max(rows,1)-28)
    for i,e in enumerate(evidences):
        x=60+(i%cols)*(card_w+38); y=160+(i//cols)*(card_h+45)
        positions[e['id']] = (x,y,card_w,card_h)
        rsus=_rsu_for(network,e['id'])
        for r in rsus:
            # Only map the method when uniquely owned; ambiguity is kept out of the diagram.
            for m in r['method_ids']:
                if sum(m in rr['method_ids'] for rr in network['rsus'])==1: mapping.setdefault(m,e['id'])
        mapping[e['id']]=e['id']
        for edge in network['edges']:
            if edge['from']==e['id'] and edge['type']=='evidence_supports': mapping[edge['to']]=e['id']
        elements.append(rect('A_card_'+e['id'],x,y,card_w,card_h))
        ps=_params(e); lines=[]; used=[]
        for role in ['design','result']:
            ss=_roles(network,e['id'],role,profile)
            if ss: lines.append(_brief_fragment(ss[0]['text']));used.append(ss[0])
            elif role in ps and ps[role].get('value'): lines.append(_brief_fragment(ps[role]['value']))
        if not lines: lines=[e['label']]
        text='\n'.join(lines)
        # Keep contents intact; diagnostic catches dense source fields for manual review.
        elements.append(textbox('A_text_'+e['id'],wrap(text,card_w-28,19),x+14,y+12,card_w-28,card_h-24,19,statement_ids=[s['id'] for s in used]))
        evidence_refs.extend(used)
    for edge in network['edges']:
        a=mapping.get(edge['from']);b=mapping.get(edge['to'])
        if not a or not b or a==b:continue
        x,y,w,h=positions[a];xx,yy,ww,hh=positions[b]
        # A direct link is drawn only if its segment stays in the inter-card corridor.
        if abs(y-yy)<1 and abs(x-xx)<card_w+40:
            start=[x+w,y+h/2] if x<xx else [x,y+h/2]
            end=[xx,yy+hh/2] if x<xx else [xx+ww,yy+hh/2]
        elif abs(x-xx)<1 and abs(y-yy)<card_h+48:
            start=[x+w/2,y+h] if y<yy else [x+w/2,y]
            end=[xx+ww/2,yy] if y<yy else [xx+ww/2,yy+hh]
        else: continue
        connectors.append(line('A_'+edge['id'],[start,end],edge.get('identity','science'),edge['id'],arrow=edge['type']!='compares',dashed=edge['type'] in ['optional_path','argument_transition']))
    critical=[s for s in network['statements'] if s.get('critical') and s.get('source_pointer',{}).get('input_kind')=='narrative']
    if critical:
        bound=critical[-1];evidence_refs.append(bound)
        elements.append(textbox('A_boundary',wrap(bound['text'],1160,16),60,640,1160,43,16,color='#63758B',statement_ids=[bound['id']]))
    else:
        elements.append(textbox('A_boundary','各模块为互补研究任务；连线仅来自已登记关系，未显示的关系见独立详细网络。',60,650,1160,30,15,color='#63758B'))
    used=_unique([s['id'] for s in evidence_refs]+qids)
    return {'id':'A_overview','product':'A','title':'全文科研逻辑简要版','elements':elements,'connectors':connectors,
            'source_statement_ids':used,'source_node_ids':[e['id'] for e in evidences],
            'source_relation_ids':[a['source_relation_id'] for a in connectors], 'figure_ids':_unique(f for r in network['rsus'] for f in r['figure_ids']),
            'citation':_citation(network,meta,[f['id'] for f in network['figures']],evidence_refs),
            'notes':_notes(network,evidence_refs,q,meta,[f['id'] for f in network['figures']])}

def _story_scene(network, profile, figure, asset, evidences, meta, suffix='', detail=False):
    node_map={n['id']:n for n in network['nodes']}
    selected=[]
    roles=['design','result','interpretation'] if profile=='quick' else ['design','method','result','interpretation']
    for role in roles:
        for eid in evidences:
            candidates=_roles(network,eid,role,profile)
            if candidates:selected.append(candidates[0])
    if not selected:
        for r in network['rsus']:
            if figure['id'] in r['figure_ids']:
                selected.extend(s for s in network['statements'] if s['id'] in r['statement_ids'] and s['role'] in roles)
    selected=list({s['id']:s for s in selected}.values())
    # Multiple evidence units are separated into pages by caller, never truncated here.
    selected=selected[:5]
    ids=[s['id'] for s in selected]
    name=node_map[evidences[0]]['label'] if evidences else figure.get('label',figure['id'])
    title=wrap(name,1160,31)
    title_ids=_statement_for_text(network,evidences[0],name) if evidences else []
    elements=[textbox('C_title',title,60,65,1160,66,31,True,statement_ids=title_ids)]
    elements[0]['source_node_ids']=list(evidences)
    if asset:
        elements.append({'kind':'image','id':'C_original_figure','asset_id':asset['id'],
                         'position':{'left':45,'top':150,'width':748,'height':524}})
    else:
        elements.append(textbox('C_argument','原文论证延展\n本部分没有对应的新实验Figure',90,280,650,160,30,True))
    connectors=[]
    x,w=834,392;top=155;available=460
    font=22 if len(selected)>=4 else 24
    blocks=[]
    for s in selected:
        shown=wrap(_brief_fragment(s['text']),w,font);h=max(60, len(shown.split('\n'))*font*1.30+8)
        blocks.append((s,shown,h))
    total=sum(h for _,_,h in blocks)+28*max(0,len(blocks)-1)
    warnings=[]
    if total>available:
        warnings.append({'code':'DENSE_STORY','text':'Scientific text exceeds comfortable story column; do not silently shrink.', 'required_height':total})
    y=top
    for i,(s,shown,h) in enumerate(blocks):
        elements.append(textbox('C_step_'+str(i+1),shown,x,y,w,h,font,s['role'] in ['result','interpretation'],statement_ids=[s['id']],align='center'))
        y+=h
        if i<len(blocks)-1:
            elements.append({'kind':'down_arrow','id':'C_story_arrow_'+str(i+1),'position':{'left':x+w/2-10,'top':y+6,'width':20,'height':16},'identity':'presentation'})
            y+=28
    limits=[]
    for eid in evidences:
        for s in _roles(network,eid,'limitation',profile):limits.append(s)
    limits=list({s['text']:s for s in limits}.values())
    if limits:
        visible=limits[0]
        shown=wrap(_brief_fragment(visible['text']),w,15)
        elements.append(textbox('C_limit',shown,x,628,w,53,15,color='#63758B',statement_ids=[visible['id']]))
        ids+= [visible['id']]
    all_stmts=selected+limits
    scene={'id':'C_'+figure['id']+suffix,'product':'C','title':name,'elements':elements,'connectors':connectors,
           'figure_ids':[figure['id']],'visible_asset_ids':[asset['id']] if asset else [],
           'source_statement_ids':_unique(ids),'source_node_ids':evidences,'source_relation_ids':[],
           'citation':_citation(network,meta,[figure['id']],all_stmts),
           'notes':_notes(network,all_stmts,_clean_question(name),meta,[figure['id']]),'warnings':warnings,
           'coverage':{'figure_story_present':bool(selected and asset),'visible_panels':asset.get('panels',[]) if asset else [],
                       'reviewed_panels':[], 'panel_mapping_status':asset.get('review',{}).get('panel_mapping','PARTIAL') if asset else 'NOT_APPLICABLE',
                       'statement_count':len(selected),'complete_panel_story':False}}
    scene['notes']['all_source_node_details']=[node_map[e] for e in evidences]
    mids=_unique(m for e in evidences for r in _rsu_for(network,e) for m in r['method_ids'])
    scene['notes']['methods_and_conditions']=[node_map[m] for m in mids if m in node_map]
    scene['notes']['figure_source']=figure
    scene['notes']['image_asset']=asset
    scene['notes']['full_mode_detail_page']=detail
    if detail:
        scene['notes']['detail_reason']='Enlarge a registered local view for readability; the same evidence is not counted twice.'
    return scene

def stories(network, profile, meta):
    scenes=[]; assets=network['assets'];preferred=meta.get('preferred_asset_ids',{})
    for f in network['figures']:
        possible=[a for a in assets if a['figure_id']==f['id'] and not a.get('known_truncation',False)]
        target=preferred.get(f['id'])
        primary=next((a for a in possible if a['id']==target),None) or next((a for a in possible if a.get('panels')==['all']),None) or (possible[0] if possible else None)
        related=primary.get('evidence_ids',[]) if primary else []
        if not related:
            related=_unique(e for r in network['rsus'] if f['id'] in r['figure_ids'] for e in r['evidence_ids'])
        if len(related)>1:
            # One scientific evidence unit per question, not one page per panel.
            for i,eid in enumerate(related):scenes.append(_story_scene(network,profile,f,primary,[eid],meta,'_'+str(i+1)))
        else:scenes.append(_story_scene(network,profile,f,primary,related,meta))
        if profile=='full':
            details=[a for a in possible if a['id']!=(primary or {}).get('id') and a.get('panels')!=['all']]
            if details:
                detail=details[0]
                scenes.append(_story_scene(network,profile,f,detail,detail.get('evidence_ids') or related,meta,'_detail',True))
    # Necessary discussion without a Figure is not disguised as a new experiment.
    for rsu in network['rsus']:
        if rsu['figure_ids']:continue
        ss=[]
        for role in ['design','result','interpretation','limitation']:
            for eid in rsu['evidence_ids']:
                ss+=_roles(network,eid,role,profile)[:1]
        if not ss:ss=[s for s in network['statements'] if s['id'] in rsu['statement_ids'] and s['role'] in ['design','result','interpretation','limitation']]
        ss=list({re.sub(r'\s+','',s['text']):s for s in ss}.values())
        el=[textbox('D_title',wrap(_clean_question(rsu['question']),1150,31),60,65,1150,65,31,True)]
        yy=175
        for i,s in enumerate(ss[:4]):
            tx=wrap(s['text'],1050,25);hh=max(65,len(tx.split('\n'))*34)
            el.append(textbox('D_'+str(i),tx,110,yy,1050,hh,25,s['role'] in ['result','interpretation'],statement_ids=[s['id']]))
            yy+=hh+25
        scenes.append({'id':'C_discussion_'+rsu['id'],'product':'C','title':rsu['question'],'elements':el,'connectors':[],
                       'figure_ids':[],'source_statement_ids':[s['id'] for s in ss[:4]],'source_node_ids':rsu['evidence_ids'],'source_relation_ids':[],
                       'citation':_citation(network,meta,[],ss),'notes':_notes(network,ss,rsu['question'],meta,[])})
    return scenes

def _band_detail_retained_for_history(network, profile, meta):
    """Large editable canvas: detailed task bands plus every registered relation."""
    es=_evidence_nodes(network); nm={n['id']:n for n in network['nodes']}
    width=2440; row_h=410; base=180
    relation_rows=math.ceil(len(network['edges'])/3)
    height=base+len(es)*row_h+170+relation_rows*132+120
    if height>5300: raise ValueError('Detailed canvas exceeds PowerPoint limits; paginate by scientific branch.')
    el=[textbox('B_title','完整科研证据网络｜实验、分析、结果与边界',60,35,2300,70,40,True),
        textbox('B_legend','同一ID在关系带中重复展示时仍指向同一科学节点；关联与论证不等于实验时序或分子因果。',60,112,2300,45,23,color='#63758B')]
    con=[]; used=[]
    for i,e in enumerate(es):
        y=base+i*row_h; rsus=_rsu_for(network,e['id']); methods=_unique(m for r in rsus for m in r['method_ids'])
        ps=_params(e); claims=[nm[a['to']] for a in network['edges'] if a['from']==e['id'] and a['type']=='evidence_supports' and a['to'] in nm]
        design='\n'.join(str(ps[k].get('value')) for k in ['design'] if ps.get(k,{}).get('value')) or '设计详情待抽取/核实'
        result='\n'.join(str(ps[k].get('value')) for k in ['result'] if ps.get(k,{}).get('value')) or e['label']
        interpretations='\n'.join(str(ps[k].get('value')) for k in ['interpretation'] if ps.get(k,{}).get('value'))
        limits=_unique(e.get('limits',[])+[x for c in claims for x in c.get('limits',[])])
        materials='\n'.join(nm[m]['label'] for m in methods if m in nm)
        fields=[]
        for n in [e]+[nm[m] for m in methods if m in nm]:
            for p in n.get('parameters',[]):
                if p.get('key') not in ['design','result','interpretation']:
                    fields.append(f"{p.get('key')}: {p.get('value') if p.get('status')=='reported' else '待核实（'+str(p.get('status'))+'）'}")
            for q in n.get('quantities',[]):
                fields.append(' · '.join(str(q.get(k,'')) for k in ['name','value','unit','population_id','reporting_status'] if q.get(k) is not None))
        fields=fields or ['材料/样本量：待抽取或核实','生物/技术重复：待核实','处理与对照：以设计字段及原文为准','统计检验/阈值：待抽取或核实']
        blocks=[(60,485,'研究任务与方法',materials+'\n'+design),
                (610,620,'实际读数与结果',result),
                (1295,480,'阶段认识与科学边界',interpretations+'\n'+'\n'.join(limits)),
                (1840,540,'实验条件与统计口径','\n'.join(fields))]
        for j,(x,w,label,content) in enumerate(blocks):
            el.append(rect(f'B_{i}_{j}',x,y,w,row_h-40,fill='#EDF3FC' if j%2==0 else '#F5F7FA'))
            el.append(textbox(f'B_h_{i}_{j}',label,x+16,y+14,w-32,36,24,True))
            shown=wrap(content,w-32,20)
            item=textbox(f'B_t_{i}_{j}',shown,x+16,y+59,w-32,row_h-110,20)
            item['source_node_ids']=[e['id']]+methods+[c['id'] for c in claims]
            item['statement_ids']=[s['id'] for s in network['statements'] if set(s.get('entity_ids',[]))&set(item['source_node_ids'])]
            el.append(item)
        el.append(textbox('B_ids_'+str(i),' / '.join([e['id']]+methods+[c['id'] for c in claims]),60,y+row_h-34,2200,28,16,color='#63758B'))
        used += [s['id'] for s in network['statements'] if e['id'] in s.get('entity_ids',[])]
    y=base+len(es)*row_h+25
    el.append(textbox('B_rel_title','已登记的科学与作者论证关系（保留原始ID、方向和身份）',60,y,2300,50,30,True));y+=75
    for i,edge in enumerate(network['edges']):
        col=i%3;row=i//3;xx=60+col*795;yy=y+row*132
        a=nm.get(edge['from'],{'label':edge['from']});b=nm.get(edge['to'],{'label':edge['to']})
        for tag,node,dx in [('from',a,0),('to',b,410)]:
            el.append(rect('B_rel_'+str(i)+tag,xx+dx,yy,345,83,fill='#FFFFFF'))
            el.append(textbox('B_rel_t_'+str(i)+tag,wrap(node['label'],317,17),xx+dx+14,yy+10,317,63,17))
        identity=edge.get('identity','science')
        con.append(line('B_edge_'+edge['id'],[[xx+347,yy+42],[xx+405,yy+42]],identity,edge['id'],edge['type']!='compares',edge['type'] in ['argument_transition','optional_path']))
        el.append(textbox('B_relation_id_'+str(i),f"{edge['id']} · {edge['type']} · {identity}",xx,yy+87,755,35,14,color='#63758B'))
    all_st=[s for s in network['statements'] if s['id'] in set(used)]
    return {'kind':'detail','width':width,'height':height,'slides':[{'id':'B_detailed','product':'B','title':'独立完整科研逻辑网络','elements':el,'connectors':con,
            'figure_ids':[f['id'] for f in network['figures']],'source_statement_ids':_unique(used),
            'source_node_ids':[n['id'] for n in network['nodes']], 'source_relation_ids':[e['id'] for e in network['edges']],
            'citation':_citation(network,meta,[f['id'] for f in network['figures']],all_st),
            'notes':_notes(network,all_st,'哪些实际任务和证据共同支撑全文认识？',meta,[f['id'] for f in network['figures']])}]}

def _short(value, limit=42):
    """A source fragment, never an invented replacement claim."""
    value=str(value).replace('\n',' ').strip()
    if len(value)<=limit:return value
    for stop in ['；','。','，', ';']:
        hits=[m.start() for m in re.finditer(re.escape(stop),value) if 10<=m.start()<=limit]
        if hits:return value[:hits[-1]+1]
    return value[:limit]+'…'

def _record_element(r, identifier, p, size=23, bold=False, align='left'):
    e=textbox(identifier,wrap(r['text'],p['width'],size),**dict(x=p['left'],y=p['top'],w=p['width'],h=p['height']),size=size,bold=bold,statement_ids=r.get('source_statement_ids',[]),align=align)
    e['source_node_ids']=r.get('source_node_ids',[])
    e['display_record_ids']=[r['id']]
    return e

def _edge_route(a,b,lane=0):
    ax,ay,aw,ah=[a[k] for k in ['left','top','width','height']]
    bx,by,bw,bh=[b[k] for k in ['left','top','width','height']]
    if by>=ay+ah:
        mid=ay+ah+(by-ay-ah)/2
        return [[ax+aw/2,ay+ah],[ax+aw/2,mid],[bx+bw/2,mid],[bx+bw/2,by]]
    if bx>=ax+aw and abs(ay-by)<90:
        return [[ax+aw,ay+ah/2],[bx,by+bh/2]]
    # Explicit outside corridor for cross-module links, never drop a distant edge.
    channel=1238+(lane%5)*6
    return [[ax+aw,ay+ah/2],[channel,ay+ah/2],[channel,by+bh/2],[bx+bw,by+bh/2]]

def _guided_overview(network,profile,meta,g):
    rm={r['id']:r for r in g['records']};cfg=g['overview'];els=[];con=[];positions={};used=[]
    title=rm[cfg['title_id']];heading=_record_element(title,'A_title',{'left':60,'top':64,'width':1160,'height':64},30,True);heading['text']=wrap(title['text'].replace('\n',''),1160,30);els.append(heading);used+=[title]
    for i,n in enumerate(cfg['nodes']):
        p=n.get('position') or {'left':60+(i%3)*398,'top':150+(i//3)*125,'width':366,'height':90}
        positions[n['id']]=p;r=rm[n['text_id']];used.append(r)
        els.append(rect('A_node_'+n['id'],p['left'],p['top'],p['width'],p['height'],fill='#EAF1FB' if n.get('role') in ['result','conclusion','foundation'] else '#F7F9FC'))
        inset={**p,'left':p['left']+12,'top':p['top']+5,'width':p['width']-24,'height':p['height']-10}
        item=_record_element(r,'A_text_'+n['id'],inset,n.get('font_size',21),n.get('role') in ['result','conclusion','foundation'],align='center')
        if p['height']<=50:item['text']=wrap(r['text'].replace('\n',''),inset['width'],item['font_size'])
        els.append(item)
    seen_labels=set()
    for i,edge in enumerate(cfg['edges']):
        points=edge.get('points') or _edge_route(positions[edge['from']],positions[edge['to']],i)
        c=line('A_'+edge['id'],points,edge['identity'],edge.get('source_relation_id'),arrow=edge['type'] not in ['compares','parallel'],dashed=edge['identity']!='scientific_registered')
        c.update({'relation_type':edge['type'],'label':edge.get('label',''),'display_edge_id':edge['id']})
        con.append(c)
        if edge.get('label'):
            lp=edge.get('label_position')
            if lp and edge['label'] not in seen_labels:
                width=max(lp['width'],measure(edge['label'],13)+12)
                left=max(50,min(lp['left']+(lp['width']-width)/2,1230-width))
                els.append(textbox('A_edge_label_'+edge['id'],edge['label'],left,lp['top'],width,lp['height'],13,color='#63758B',align='center'))
                seen_labels.add(edge['label'])
    boundary=rm[cfg['limit_id']];used.append(boundary)
    els.append(_record_element(boundary,'A_boundary',{'left':60,'top':641,'width':1160,'height':37},15))
    els.append(textbox('A_identity_legend','实线：登记的证据关系　虚线：论证/汇报联系（不表示实验时序或已证实因果）',60,677,1160,17,12,color='#63758B'))
    ids=_unique(s for r in used for s in r.get('source_statement_ids',[]))
    ss=[s for s in network['statements'] if s['id'] in ids]
    scene={'id':'A_overview','product':'A','title':title['text'],'elements':els,'connectors':con,'source_statement_ids':ids,
           'source_node_ids':_unique(n for r in used for n in r.get('source_node_ids',[])),
           'source_relation_ids':_unique(e.get('source_relation_id') for e in cfg['edges']),
           'figure_ids':[f['id'] for f in network['figures']],'citation':_citation(network,meta,[f['id'] for f in network['figures']],ss),
           'notes':_notes(network,ss,title['text'],meta,[f['id'] for f in network['figures']])}
    scene['notes'].update({'display_records':used,'display_guidance_input':g['_input'],'display_edges':cfg['edges'],'user_acceptance':'PENDING','semantic_review_status':'PARTIAL'})
    return scene

def _field_overview(network,profile,meta):
    g=load_guidance(network,meta)
    if g:return _guided_overview(network,profile,meta,g)
    # Generic source-field network: task and observation remain separate, all
    # registered cross-module relations survive irrespective of grid adjacency.
    es=_evidence_nodes(network);q,qids=_question(network);els=[textbox('A_title',wrap(q,1160,29),60,64,1160,65,29,True,statement_ids=qids)]
    con=[];used=[];positions={};mapping={};cols=min(3,max(1,len(es)));cw=(1100-(cols-1)*70)/cols
    for i,e in enumerate(es):
        x=60+(i%cols)*(cw+70);y=163+(i//cols)*226;ps=_params(e)
        ds=_roles(network,e['id'],'design',profile);rs=_roles(network,e['id'],'result',profile)
        for role,sy,source,fill in [('task',y,ds,'#F7F9FC'),('result',y+95,rs,'#EAF1FB')]:
            p={'left':x,'top':sy,'width':cw,'height':73};positions[e['id']+'_'+role]=p
            val=source[0]['text'] if source else e['label'];ids=[source[0]['id']] if source else [];used+=source[:1]
            els.append(rect('A_'+role+e['id'],x,sy,cw,73,fill))
            els.append(textbox('A_text_'+role+e['id'],wrap(_short(val,44),cw-24,19),x+12,sy+5,cw-24,63,19,role=='result',statement_ids=ids,align='center'))
        con.append(line('A_field_'+e['id'],[[x+cw/2,y+73],[x+cw/2,y+95]],'presentation'))
        mapping[e['id']]=e['id']+'_result'
        for r in _rsu_for(network,e['id']):
            for mid in r['method_ids']:mapping.setdefault(mid,e['id']+'_task')
        for edge in network['edges']:
            if edge['from']==e['id'] and edge['type']=='evidence_supports':mapping[edge['to']]=e['id']+'_result'
    for i,edge in enumerate(network['edges']):
        a=mapping.get(edge['from']);b=mapping.get(edge['to'])
        if not a or not b or a==b:continue
        c=line('A_'+edge['id'],_edge_route(positions[a],positions[b],i),edge.get('identity','scientific_registered'),edge['id'],edge['type']!='compares',edge['type'] in ['optional_path','argument_transition'])
        c['relation_type']=edge['type'];c['label']=edge['type'];con.append(c)
    els.append(textbox('A_boundary','上下短节点分别为实际任务与观察。跨模块连线保留登记关系；展开说明与限制见独立完整图及逐图页。',60,640,1160,39,15,color='#63758B'))
    return {'id':'A_overview','product':'A','title':q,'elements':els,'connectors':con,'figure_ids':[f['id'] for f in network['figures']],
            'source_statement_ids':_unique(qids+[s['id'] for s in used]),'source_node_ids':[e['id'] for e in es],
            'source_relation_ids':_unique(c['source_relation_id'] for c in con),'citation':_citation(network,meta,[f['id'] for f in network['figures']],used),
            'notes':_notes(network,used,q,meta,[f['id'] for f in network['figures']])}

def overview(network,profile,meta):
    g=load_guidance(network,meta)
    if g:return _guided_overview(network,profile,meta,g)
    if not network['edges']:return _field_overview(network,profile,meta)
    if any(e['type']=='optional_path' for e in network['edges']) and any(n['kind']=='model' for n in network['nodes']):
        return _model_branch_overview(network,profile,meta)
    # Rank actual source nodes, including models/resources and conceptual topics.
    # Layout rank is a reading aid, never a claim of historical experimental order.
    nm={n['id']:n for n in network['nodes']};ids=_unique(v for e in network['edges'] for v in [e['from'],e['to']]);rank={n:0 for n in ids}
    incoming={n:[] for n in ids};outgoing={n:[] for n in ids}
    for e in network['edges']:
        if e['type']=='compares':continue
        incoming[e['to']].append(e['from']);outgoing[e['from']].append(e['to'])
    todo=[n for n in ids if not incoming[n]];visited=set()
    while todo:
        node=todo.pop(0)
        if node in visited:continue
        visited.add(node)
        for target in outgoing[node]:
            rank[target]=max(rank[target],rank[node]+1)
            if all(x in visited for x in incoming[target]):todo.append(target)
    # Cyclic/cross-comparison nodes stay explicit in a side rank; no edge dropped.
    maxrank=max(rank.values(),default=0);cols=min(6,max(2,maxrank+1));buckets={c:[] for c in range(cols)}
    for n in ids:buckets[min(cols-1,int(rank[n]*(cols-1)/max(1,maxrank)))].append(n)
    if max(map(len,buckets.values()))>6:raise ValueError('A_NEEDS_GUIDANCE: source graph needs meaningful aggregation')
    q,qids=_question(network);els=[textbox('A_title',wrap(q,1160,29),60,64,1160,67,29,True,statement_ids=qids)];positions={};cw=(1160-26*(cols-1))/cols
    for col,items in buckets.items():
        gap=15;h=min(100,(455-gap*(len(items)-1))/max(1,len(items)))
        for row,nid in enumerate(items):
            n=nm[nid];x=60+col*(cw+26);y=160+(455-(len(items)*h+(len(items)-1)*gap))/2+row*(h+gap);p={'left':x,'top':y,'width':cw,'height':h};positions[nid]=p
            els.append(rect('A_source_'+nid,x,y,cw,h,fill='#EAF1FB' if n['kind'] in ['evidence','claim'] else '#F7F9FC'))
            # Use the curated scientific label, not a clipped design paragraph.
            # Never remove a conclusion by truncating it at a comma or ellipsis.
            text=wrap(n['label'],cw-16,20)
            if len(text.split('\n'))*25>h-8:raise ValueError('A_NODE_NEEDS_SHORT_SOURCE_LABEL: '+nid)
            e=textbox('A_source_text_'+nid,text,x+8,y+5,cw-16,h-10,20,n['kind'] in ['evidence','claim'],statement_ids=_statement_for_text(network,nid,n['label']),align='center');e['source_node_ids']=[nid];els.append(e)
    con=[]
    for i,e in enumerate(network['edges']):
        a=positions[e['from']];b=positions[e['to']]
        if a['left']<b['left']:
            # Use inter-column corridor, keeping all long-distance edges explicit.
            mid=a['left']+a['width']+10+(i%3)*3
            pts=[[a['left']+a['width'],a['top']+a['height']/2],[mid,a['top']+a['height']/2],[mid,b['top']+b['height']/2],[b['left'],b['top']+b['height']/2]]
        elif a['left']==b['left']:
            channel=a['left']+a['width']+8+(i%3)*3
            pts=[[a['left']+a['width'],a['top']+a['height']/2],[channel,a['top']+a['height']/2],[channel,b['top']+b['height']/2],[b['left']+b['width'],b['top']+b['height']/2]]
        else:pts=_edge_route(a,b,i)
        c=line('A_'+e['id'],pts,e['identity'],e['id'],e['type']!='compares',e['type'] in ['optional_path','argument_transition']);c['relation_type']=e['type'];c['label']=e['type'];con.append(c)
    els.append(textbox('A_boundary','节点保留原始科学身份，连线保留已登记关系；阅读位置不表示实际实验先后。长名称的完整表述见备注及独立详细图。',60,642,1160,41,15,color='#63758B'))
    notes=_notes(network,[],q,meta,[f['id'] for f in network['figures']]);notes['source_nodes']=[nm[n] for n in ids];notes['source_edges']=network['edges'];notes['user_acceptance']='PENDING'
    return {'id':'A_overview','product':'A','title':q,'elements':els,'connectors':con,'figure_ids':[f['id'] for f in network['figures']],
            'source_statement_ids':_unique(qids+[sid for el in els for sid in el.get('statement_ids',[])]),'source_node_ids':ids,'source_relation_ids':[e['id'] for e in network['edges']],
            'citation':_citation(network,meta,[f['id'] for f in network['figures']],[]),'notes':notes}

def _model_branch_overview(network,profile,meta):
    """Compact actual model routes; evidence summaries share their source task.

    Aggregation is presentation-only, and all internal edges remain accounted
    for. Fixed row gutters give every cross edge a route outside text boxes.
    """
    nm={n['id']:n for n in network['nodes']};ids=_unique(v for e in network['edges'] for v in [e['from'],e['to']]);owner={n:n for n in ids};members={n:[n] for n in ids}
    for edge in network['edges']:
        if edge['type']=='integrates' and nm[edge['from']]['kind'] in ['model','evaluation'] and nm[edge['to']]['kind']=='evidence':
            owner[edge['to']]=edge['from'];members[edge['from']].append(edge['to']);members.pop(edge['to'],None)
    keys=[n for n in ids if n in members];indeg={n:0 for n in keys};out={n:[] for n in keys}
    for e in network['edges']:
        a,b=owner[e['from']],owner[e['to']]
        if a!=b and b not in out[a]:out[a].append(b);indeg[b]+=1
    todo=[n for n in keys if not indeg[n]];ordered=[]
    while todo:
        a=todo.pop(0);ordered.append(a)
        for b in out[a]:
            indeg[b]-=1
            if indeg[b]==0:todo.append(b)
    ordered+= [n for n in keys if n not in ordered]
    if len(ordered)>16:raise ValueError('A_MODEL_NEEDS_GUIDANCE: use source-bound task aggregation')
    q,qids=_question(network);els=[textbox('A_title',wrap(q,1160,29),60,64,1160,67,29,True,statement_ids=qids)];pos={};rows=4;cols=math.ceil(len(ordered)/rows);cw=(1160-40*(cols-1))/cols
    for i,nid in enumerate(ordered):
        x=60+(i//rows)*(cw+40);y=160+(i%rows)*115;p={'left':x,'top':y,'width':cw,'height':100};pos[nid]=p
        ns=members[nid];labels=[nm[nid]['label']]
        # The overview displays one concrete finding; every source member and
        # its unabridged text remains in notes and the detailed network.
        if len(ns)>1:labels.append(nm[ns[1]]['label'])
        shown='\n'.join(_short(v,28) for v in labels)
        els.append(rect('A_task_'+nid,x,y,cw,100,fill='#EAF1FB' if len(ns)>1 or nm[nid]['kind']=='claim' else '#F7F9FC'))
        e=textbox('A_task_text_'+nid,wrap(shown,cw-20,20),x+10,y+5,cw-20,90,20,len(ns)>1 or nm[nid]['kind']=='claim',align='center');e['source_node_ids']=ns;els.append(e)
    con=[];internal=[]
    for edge in network['edges']:
        a,b=owner[edge['from']],owner[edge['to']]
        if a==b:internal.append(edge['id']);continue
        aa,bb=pos[a],pos[b];exit_y=aa['top']+105
        if aa['left']==bb['left']:
            gutter=aa['left']+aa['width']+14
            pts=[[aa['left']+aa['width']/2,aa['top']+100],[aa['left']+aa['width']/2,exit_y],[gutter,exit_y],[gutter,bb['top']+50],[bb['left']+bb['width'],bb['top']+50]]
        else:
            gutter=bb['left']-14
            pts=[[aa['left']+aa['width']/2,aa['top']+100],[aa['left']+aa['width']/2,exit_y],[gutter,exit_y],[gutter,bb['top']+50],[bb['left'],bb['top']+50]]
        c=line('A_'+edge['id'],pts,edge['identity'],edge['id'],edge['type']!='compares',edge['type'] in ['optional_path','argument_transition']);c['relation_type']=edge['type'];con.append(c)
    els.append(textbox('A_boundary','虚线保留可选方法路线；实线保留原登记关系。框内合并任务及对应发现，完整来源与内部关系见备注及详细网络。',60,642,1160,40,15,color='#63758B'))
    notes=_notes(network,[],q,meta,[f['id'] for f in network['figures']]);notes.update({'presentation_groups':members,'internal_relation_ids':internal,'source_edges':network['edges'],'source_nodes':[nm[n] for n in ids],'user_acceptance':'PENDING'})
    return {'id':'A_overview','product':'A','title':q,'elements':els,'connectors':con,'figure_ids':[f['id'] for f in network['figures']],
            'source_statement_ids':qids,'source_node_ids':ids,'source_relation_ids':[e['id'] for e in network['edges']],
            'citation':_citation(network,meta,[f['id'] for f in network['figures']],[]),'notes':notes}

def guided_stories(network,profile,meta,g):
    rm={r['id']:r for r in g['records']};am={a['id']:a for a in network['assets']};fm={f['id']:f for f in network['figures']};out=[]
    for p in g.get('figure_pages',[]):
        if profile not in p.get('profiles',['quick','balanced','full']):continue
        aids=p['asset_ids'];title=rm[p['title_id']];els=[_record_element(title,'C_title',{'left':60,'top':64,'width':1160,'height':68},30,True)]
        poses=p.get('image_positions') or [{'left':40,'top':153,'width':755,'height':470} for _ in aids]
        if len(poses)!=len(aids):raise ValueError('GUIDANCE_IMAGE_LAYOUT')
        for i,(aid,pos) in enumerate(zip(aids,poses)):
            els.append({'kind':'image','id':'C_original_'+str(i),'asset_id':aid,'position':pos})
        records=[rm[k] for k in p['steps']];w=408;x=826;y=153;blocks=[]
        for r in records:
            shown=wrap(r['text'],w,23);h=max(46,len(shown.split('\n'))*29+6);blocks.append((r,shown,h))
        total=sum(x[2] for x in blocks)+22*max(0,len(blocks)-1)
        if total>465:raise ValueError('GUIDANCE_DENSE_STORY: split by scientific question, '+p['id'])
        for i,(r,shown,h) in enumerate(blocks):
            item=_record_element(r,'C_step_'+str(i+1),{'left':x,'top':y,'width':w,'height':h},23,r.get('role') in ['result','interpretation'],align='center');item['text']=shown;els.append(item);y+=h
            if i<len(blocks)-1:
                els.append({'kind':'down_arrow','id':'C_story_arrow_'+str(i+1),'position':{'left':x+w/2-8,'top':y+3,'width':16,'height':15},'identity':'presentation'});y+=22
        terms=[rm[k] for k in p.get('terminology_ids',[])];limits=[rm[k] for k in p.get('limit_ids',[])];notes=[rm[k] for k in p.get('notes_ids',[])]
        if terms:
            t={'id':terms[0]['id'],'text':'\n'.join(r['text'] for r in terms),'source_statement_ids':_unique(s for r in terms for s in r.get('source_statement_ids',[])),'source_node_ids':_unique(n for r in terms for n in r.get('source_node_ids',[]))}
            el=_record_element(t,'C_terms',{'left':50,'top':626,'width':740,'height':49},16);el['display_record_ids']=[r['id'] for r in terms];els.append(el)
        if limits:
            # Boundaries affecting interpretation remain visible in every mode.
            t={'id':limits[0]['id'],'text':'\n'.join(r['text'] for r in limits),'source_statement_ids':_unique(s for r in limits for s in r.get('source_statement_ids',[])),'source_node_ids':_unique(n for r in limits for n in r.get('source_node_ids',[]))}
            el=_record_element(t,'C_limits',{'left':826,'top':611,'width':408,'height':75},14);el['display_record_ids']=[r['id'] for r in limits];els.append(el)
        used=[title]+records+terms+limits+notes;sids=_unique(s for r in used for s in r.get('source_statement_ids',[]));ss=[s for s in network['statements'] if s['id'] in sids]
        eids=_unique(e for a in aids for e in am[a].get('evidence_ids',[]));panels=_unique(v for aid in aids for v in am[aid].get('panels',[]))
        scene={'id':p['id'],'product':'C','title':title['text'],'elements':els,'connectors':[],'figure_ids':[p['figure_id']],
               'visible_asset_ids':aids,'source_statement_ids':sids,'source_node_ids':_unique(eids+[n for r in used for n in r.get('source_node_ids',[])]),'source_relation_ids':[],
               'citation':_citation(network,meta,[p['figure_id']],ss),'notes':_notes(network,ss,title['text'],meta,[p['figure_id']]),
               'coverage':{'figure_story_present':True,'visible_panels':panels,'reviewed_panels':[],'panel_mapping_status':'PARTIAL','complete_panel_story':False}}
        scene['notes'].update({'display_records':used,'display_guidance_input':g['_input'],'image_assets':[am[a] for a in aids],
                               'image_readability_review':'PENDING_ACTUAL_POWERPOINT_RENDER','user_acceptance':'PENDING','semantic_review_status':'PARTIAL',
                               'speaker_script':p.get('speaker_script','按图旁文字说明实际比较、结果及边界。')})
        out.append(scene)
    return out

def full_source_context(network,meta):
    """Full adds upstream method scope/limitations, not another paper parse."""
    out=[]
    for rsu in network['rsus']:
        candidates=[s for s in network['statements'] if
                    (set(s.get('entity_ids',[])) & set(rsu['method_ids']) and s['role'] in ['method','design','interpretation','limitation']) or
                    (rsu['id'] in s.get('rsu_ids',[]) and s['role']=='limitation')]
        candidates=list({s['text']:s for s in candidates}.values())
        if not candidates:continue
        for part in range(0,len(candidates),4):
            selected=candidates[part:part+4];els=[textbox('CTX_title','方法、论据与适用边界（补充）',60,65,1160,60,31,True)]
            y=165
            for i,s in enumerate(selected):
                text=wrap(s['text'],1100,24);h=max(70,len(text.split('\n'))*31)
                if y+h>675:raise ValueError('FULL_CONTEXT_DENSE: source needs explicit page guidance')
                els.append(textbox('CTX_'+str(i),text,90,y,1100,h,24,s['role']=='limitation',statement_ids=[s['id']]));y+=h+24
            scene={'id':'C_context_'+rsu['id']+'_'+str(part),'product':'C','title':'方法、论据与适用边界（补充）','elements':els,'connectors':[],
                   'figure_ids':rsu['figure_ids'],'source_statement_ids':[s['id'] for s in selected],'source_node_ids':rsu['method_ids']+rsu['evidence_ids'],
                   'source_relation_ids':[],'citation':_citation(network,meta,rsu['figure_ids'],selected),'notes':_notes(network,selected,rsu['question'],meta,rsu['figure_ids']),
                   'coverage':{'figure_story_present':False,'complete_panel_story':False,'page_role':'method_and_limit_depth'}}
            out.append(scene)
    return out

def detailed(network,profile,meta):
    """Connected large canvas, preserving every registered edge and original IDs."""
    es=_evidence_nodes(network);nm={n['id']:n for n in network['nodes']};width=3200;rh=650 if network.get('experiment_layer') else 540;card_h=rh-190;height=250+len(es)*rh+150
    els=[textbox('B_title','完整科研证据网络：研究任务、实际结果与阶段认识',60,35,3080,70,40,True),
         textbox('B_legend','实线为已登记关系（来源审核仍为PARTIAL）；虚线为字段阅读/汇报联系，不代表实验先后。各模块条件及未核事项保留在节点和备注。',60,113,3080,55,24,color='#63758B')]
    con=[];positions={};used=[]
    for i,e in enumerate(es):
        y=230+i*rh;rsus=_rsu_for(network,e['id']);methods=_unique(m for r in rsus for m in r['method_ids']);ps=_params(e)
        claims=[a['to'] for a in network['edges'] if a['from']==e['id'] and a['type']=='evidence_supports']
        exps=[x for x in network.get('experiment_layer',{}).get('experiments',[]) if e['id'] in x.get('m1_evidence_ids',[])]
        design=ps.get('design',{}).get('value') or '设计详情待抽取/核实';result=ps.get('result',{}).get('value') or e['label']
        if exps:design='\n'.join(x['experiment_id']+'：'+_short(x['display_name'],18) for x in exps)
        interp=ps.get('interpretation',{}).get('value') or '\n'.join(nm[c]['label'] for c in claims)
        limits=_unique(e.get('limits',[])+[v for c in claims for v in nm[c].get('limits',[])])
        task_text=('实验任务（具体条件、数量及统计见B2同ID）：\n'+design) if exps else ('RSU关联方法池（不等于本Figure逐项实验）：\n'+'\n'.join(nm[m]['label'] for m in methods)+'\n'+design)
        for role,x,w,text,ids in [('task',60,820,task_text,methods),
                                ('result',1040,820,result,[e['id']]),('claim',2020,820,interp+'\n'+'\n'.join(limits),claims)]:
            p={'left':x,'top':y,'width':w,'height':card_h}
            els.append(rect('B_'+e['id']+'_'+role,x,y,w,card_h,fill='#F7F9FC' if role=='task' else '#EAF1FB'))
            els.append(textbox('B_label_'+e['id']+'_'+role,{'task':'研究任务与关联方法','result':'实际观察或计算结果','claim':'阶段认识与限制'}[role],x+18,y+12,w-36,40,27,True))
            item=textbox('B_text_'+e['id']+'_'+role,wrap(text,w-36,25),x+18,y+61,w-36,card_h-75,25)
            item['source_node_ids']=[e['id']]+ids+[x['experiment_id'] for x in exps];item['statement_ids']=[s['id'] for s in network['statements'] if e['id'] in s.get('entity_ids',[]) and s['role'] in {'task':['design','method'],'result':['result'],'claim':['interpretation','limitation']}[role]]
            els.append(item);used+=item['statement_ids']
            for nid in ids:positions[nid]=p
            if role=='result':positions[e['id']]=p
        # Field-level reading link, deliberately separate from scientific edges.
        con.append(line('B_read_'+e['id'],[[880,y+card_h/2],[1040,y+card_h/2]],'presentation',arrow=True,dashed=True))
        fields=[]
        for n in [e]+[nm[m] for m in methods]:
            for p in n.get('parameters',[]):
                if p.get('key') not in ['design','result','interpretation']:fields.append(str(p.get('key'))+': '+str(p.get('value'))+' ['+str(p.get('status'))+']')
            for q in n.get('quantities',[]):fields.append(str(q))
        condition='\n'.join(fields) or '处理/样本量/统计口径：粗粒度M1未完整登记，需结合逐图来源记录；待核实不等于原文未报告。'
        if exps:condition='实验级分组、数量单位、具体处理与统计状态已按Experiment ID登记在B2信息卡和B3清单；未核实数值不补造，补充文件缺失和原文冲突逐项列出。'
        item=textbox('B_conditions_'+e['id'],wrap(condition,2780,21),60,y+card_h+25,2780,142,21,color='#63758B');item['source_node_ids']=[e['id']]+methods+[x['experiment_id'] for x in exps];els.append(item)
    # Resources, models, conceptual claims and comparison nodes need their own
    # real identities. Never silently map them to a nearby Figure/evidence.
    endpoints=_unique(v for edge in network['edges'] for v in [edge['from'],edge['to']])
    extra=[nid for nid in endpoints if nid not in positions]
    if extra:
        offset=230+len(es)*rh
        els.append(textbox('B_additional_header','跨模块来源、模型或概念节点（原始科学ID）',60,offset,2780,52,28,True))
        for i,nid in enumerate(extra):
            x=60+(i%3)*980;y=offset+70+(i//3)*205
            p={'left':x,'top':y,'width':820,'height':150};positions[nid]=p
            els.append(rect('B_extra_'+nid,x,y,820,150,fill='#F7F9FC'))
            e=textbox('B_extra_text_'+nid,wrap(nm[nid]['label']+'\n'+nid,780,25),x+20,y+12,780,126,25,True);e['source_node_ids']=[nid];els.append(e)
        height=offset+70+math.ceil(len(extra)/3)*205+140
    if height>5350:raise ValueError('B_CANVAS_LIMIT: split large source graph into linked canvases')
    for i,edge in enumerate(network['edges']):
        a=positions.get(edge['from']);b=positions.get(edge['to'])
        if not a or not b:raise ValueError('B_RELATION_ENDPOINT_UNPLACED: '+edge['id'])
        if a['top']==b['top']:
            pts=[[a['left']+a['width'],a['top']+a['height']/2],[b['left'],b['top']+b['height']/2]]
        else:
            # Dedicated outside lanes preserve cross-module edges with no node traversal.
            lane=2900+(i%12)*20
            if a['left']>=2020 and b['left']>=2020:
                pts=[[a['left']+a['width'],a['top']+a['height']/2],[lane,a['top']+a['height']/2],[lane,b['top']+b['height']/2],[b['left']+b['width'],b['top']+b['height']/2]]
            else:
                # Exit below the row, cross through empty inter-row corridors,
                # then enter the target from below; no line through other boxes.
                ay=a['top']+a['height']+24;by=b['top']+b['height']+24
                pts=[[a['left']+a['width']/2,a['top']+a['height']],[a['left']+a['width']/2,ay],[lane,ay],[lane,by],[b['left']+b['width']/2,by],[b['left']+b['width']/2,b['top']+b['height']]]
        c=line('B_'+edge['id'],pts,edge['identity'],edge['id'],edge['type']!='compares',edge['type'] in ['optional_path','argument_transition']);c['relation_type']=edge['type'];con.append(c)
        labelpos=pts[0];els.append(textbox('B_relation_'+edge['id'],wrap(edge['id']+' '+edge['type'],285,15),min(labelpos[0]+4,2850),labelpos[1]-64,285,60,15,color='#63758B'))
    ss=[s for s in network['statements'] if s['id'] in set(used)]
    scene={'id':'B_detailed','product':'B','title':'独立完整科研逻辑网络','elements':els,'connectors':con,'figure_ids':[f['id'] for f in network['figures']],
           'source_statement_ids':_unique(used),'source_node_ids':[n['id'] for n in network['nodes']],'source_relation_ids':[e['id'] for e in network['edges']],
           'citation':_citation(network,meta,[f['id'] for f in network['figures']],ss),'notes':_notes(network,ss,'各项实验、分析和结果如何互相约束？',meta,[f['id'] for f in network['figures']])}
    scene['notes']['complete_source_network']=network
    scene['notes']['completeness_boundary']='All registered edges retained, but unrecorded fine-grained facts/relations are not automatically recovered.'
    return {'kind':'detail','width':width,'height':height,'slides':[scene]}

def project_products(network, profile='balanced', metadata=None, template=None, delivery=None):
    if profile not in ['quick','balanced','full']:raise ValueError('Unsupported profile')
    meta=metadata or {}
    if (delivery or {}).get('scope')=='logic-views':
        from project_research_logic import sample_products,read_model
        logic=read_model(network,meta)
        products=sample_products(network,meta,delivery.get('views',['A','B']))
        return {'version':VERSION,'network_snapshot':network['snapshot'],'profile':profile,'paper_id':network['paper']['id'],
                'template':template,'style':{'accent':BLUE,'font_family':FONT,'latin_font':'Times New Roman'},'products':products,
                'formal_ready':False,'review_status':'PARTIAL','automation_boundary':'Agent-adjudicated research logic; display only, no added M1 entities or causal relations.',
                'input_formats':{'paper':'Reviewed evidence network and source-bound logic','template':'PPTX'},'projection_hash':digest(products),
                'delivery':copy.deepcopy(delivery),'research_logic':copy.deepcopy(meta['research_logic']),'logic_snapshot':logic['snapshot'],**({'logic_display':copy.deepcopy(meta['logic_display'])} if meta.get('logic_display') else {})}
    g=load_guidance(network,meta)
    figure_scenes=stories(network,profile,meta)
    if g:
        replacements=guided_stories(network,profile,meta,g);active={f for s in replacements for f in s['figure_ids']};covered=set(active);merged=[]
        for s in figure_scenes:
            if any(f in covered for f in s['figure_ids']):
                for f in s['figure_ids']:
                    if f in covered:merged.extend(p for p in replacements if f in p['figure_ids']);covered.remove(f)
            elif not any(f in active for f in s['figure_ids']):merged.append(s)
        figure_scenes=merged
    if profile=='full':figure_scenes+=full_source_context(network,meta)
    main={'kind':'main','width':1280,'height':720,'slides':[overview(network,profile,meta)]+figure_scenes}
    products=[main]
    scope=(delivery or {}).get('scope','deep')
    if scope in ('with-network','deep'):products.append(detailed(network,profile,meta))
    if scope=='deep' and network.get('experiment_layer'):
        from experiment_products import build_cards
        cards=build_cards(network,profile,meta)
        if cards:products.append(cards)
        from experiment_products import build_network_canvas
        products.append(build_network_canvas(network,meta))
    if meta.get('research_logic'):
        from project_research_logic import read_model,read_display,build_scene
        logic=read_model(network,meta)
        products[0]['slides'][0]=build_scene(network,logic,'A')['slides'][0]
        display=read_display(logic,meta)
        products=[build_scene(network,logic,'B',display) if p['kind']=='detail' else p for p in products]
    if delivery:
        from presentation_delivery import compose_delivery
        products=compose_delivery(network,products,meta,delivery)
    result={'version':VERSION,'network_snapshot':network['snapshot'],'profile':profile,'paper_id':network['paper']['id'],
            'template':template,'style':{'accent':BLUE,'font_family':FONT,'latin_font':'Times New Roman'},'products':products,
            'formal_ready':False,'review_status':'PARTIAL','automation_boundary':'Source-bound network projection; semantic extraction is upstream.',
            'input_formats':{'paper':'PDF with reviewed M1 JSON','template':'PPTX'},
            'projection_hash':digest(products)}
    if delivery:result['delivery']=copy.deepcopy(delivery)
    if meta.get('research_logic'):
        result['research_logic']=copy.deepcopy(meta['research_logic']);result['logic_snapshot']=logic['snapshot']
    if meta.get('logic_display'):result['logic_display']=copy.deepcopy(meta['logic_display'])
    return result

def validate_products(network, plan, metadata=None):
    expected=project_products(network,plan.get('profile','balanced'),metadata,plan.get('template'),plan.get('delivery'))
    errors=[]
    source_template=plan.get('template') or {}
    try:
        if hashlib.sha256(Path(source_template['path']).read_bytes()).hexdigest()!=source_template['sha256']:
            errors.append({'code':'TEMPLATE_DRIFT','message':'Template bytes differ from the recorded fingerprint.'})
    except (OSError,KeyError,TypeError):
        errors.append({'code':'TEMPLATE_INPUT','message':'A fingerprinted existing PPTX template is required.'})
    if expected!=plan:errors.append({'code':'PRODUCT_PLAN_DRIFT','message':'Rebuilt source-bound presentation differs.'})
    ids={s['id'] for s in network['statements']};relation_ids={e['id'] for e in network['edges']}|{e['id'] for e in network.get('experiment_layer',{}).get('relations',[])}
    for product in plan.get('products',[]):
        for s in product.get('slides',[]):
            for sid in s.get('source_statement_ids',[]):
                if sid not in ids:errors.append({'code':'UNKNOWN_STATEMENT','id':sid})
            for rid in s.get('source_relation_ids',[]):
                if rid not in relation_ids:errors.append({'code':'UNKNOWN_RELATION','id':rid})
    return {'valid':not errors,'errors':errors}
