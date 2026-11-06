"""Build a wholly self-authored calibration fixture, NOT a scientific aggregator.

No paper is read. Fixed example decisions below illustrate the existing contracts.
Only standard-library PDF writing plus PFS's installed PDF reader are used.
"""
from pathlib import Path
import argparse, copy, hashlib, json, sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import evidence_network as en, research_logic as rl, run_pfs

def save(p,x):
    Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2),'utf-8')

def example_pdf(path,lines):
    esc=lambda s:s.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
    content=('BT /F1 10 Tf 42 790 Td '+' '.join(('0 -17 Td ' if i else '')+'('+esc(t)+') Tj' for i,t in enumerate(lines))+' ET').encode('ascii')
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',b'<< /Length '+str(len(content)).encode()+b' >>\nstream\n'+content+b'\nendstream']
    out=bytearray(b'%PDF-1.4\n');offset=[0]
    for i,x in enumerate(objects,1):offset.append(len(out));out+=f'{i} 0 obj\n'.encode()+x+b'\nendobj\n'
    xref=len(out);out+=f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode()
    for k in offset[1:]:out+=f'{k:010d} 00000 n \n'.encode()
    out+=f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode();Path(path).write_bytes(out)

def make(root,count=7):
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    protocol='All channels use the same reference; tests are parallel, not a time sequence.'
    boundary='Synthetic software fixture only; no patients, biological validation, or causal claim.'
    observations=[f'Channel {i}: measured offset {i} mV against the shared reference.' for i in range(1,count+1)]
    pdf=root/'synthetic_calibration.pdf'
    example_pdf(pdf,['SYNTHETIC CALIBRATION - NOT A REAL PAPER','Question: compare parallel channel offsets.',protocol,'Figure 1A: channel offsets, in mV.',*observations,'Channels 1 and 2 have different offsets; observation 1 is reused, not remeasured.',boundary])
    cache=root/'cache';run_pfs.index_pdf(pdf,cache)
    page=cache/'page-01.txt';text=page.read_text('utf-8')
    def span(phrase):
        start=text.index(phrase);end=start+len(phrase)
        assert text[start:end]==phrase
        return dict(path=str(page),sha256=rl.file_sha(page),start=start,end=end,text=phrase)
    refs=dict(document_id='SYN',locator=dict(physical_page=1,context_sha256=hashlib.sha256(text.encode()).hexdigest()),verification='pending')
    def param(key,value):return dict(key=key,value=value,status='reported',unit='not_applicable',source_refs=[copy.deepcopy(refs)])
    def entity(id,kind,name,parameters):return dict(id=id,kind=kind,name=name,source_role='primary_study',inputs=[],outputs=[],parameters=parameters,quantities=[],source_refs=[copy.deepcopy(refs)],reporting_status='paper_reported',analysis_unit='not_applicable',unit_note='Synthetic channel, not a biological replicate.',limits=[boundary])
    values=dict(purpose=f'比较{count}个并行通道的偏差。',materials=f'合成{count}通道记录及同一参照。',design='各通道与共享参照比较，不是不同患者。',readout='读取合成表中的电压偏差，单位mV。',result=f'各通道偏差依次登记为1至{count} mV；非真实实验。',interpretation='只能说明该合成记录中的读数差别。',links=f'{count}个通道属于同一张合成表，不构成实验先后。',limits='自编软件校验材料，不是论文科学结论。',analysis='比较固定通道标签及其偏差。',counts='通道不是独立患者或生物学重复。')
    entities=[entity('M_SHARED','method','共用参照测量',[param(k,v) for k,v in values.items()])]
    relations=[];stories=[]
    for i,ob in enumerate(observations,1):
        entities += [entity('E'+str(i),'evidence',f'通道{i}偏差',[param('design',f'通道{i}与同一参照比较。'),param('result',f'通道{i}偏差为{i} mV。'),param('interpretation','合成读数，不作生物学因果外推。')]),entity('C'+str(i),'claim',f'通道{i}有源读数',[param('interpretation',f'通道{i}的合成偏差为{i} mV，不证明其他机制。')])]
        relations.append(dict(id='SUP'+str(i),**{'from':'E'+str(i),'to':'C'+str(i)},type='evidence_supports',provenance='paper',certainty='paper_reported',mandatory=False,rationale=ob,source_refs=[copy.deepcopy(refs)],support_strength='direct_observation',limits=[boundary]))
        stories.append(dict(id='RSU'+str(i),question_or_purpose=f'比较通道{i}与共享参照。',method_ids=['M_SHARED'],evidence_ids=['E'+str(i)],figure_refs=['F1'],finding_or_argument=f'通道{i}的偏差为{i} mV。',limits=[boundary],source_refs=[copy.deepcopy(refs)],presentation_order=i,original_section_order=[i],restructuring_reason='Synthetic original table order, not experimental time.',author_explicit_or_presentation='paper'))
    # One existing observation supports two interpretations; never duplicate E1.
    if count>1:
        c2=next(x for x in entities if x['id']=='C2')
        c2['name']='首两通道读数比较';c2['parameters']=[param('interpretation','通道1与通道2的合成偏差不同；E1读数只被复用一次，不增加测量。')]
        relations.append(dict(id='SHARED_SUPPORT',**{'from':'E1','to':'C2'},type='evidence_supports',provenance='paper',certainty='paper_reported',mandatory=False,rationale='Channel 1 is reused as a reference comparison, not an independent measurement.',source_refs=[copy.deepcopy(refs)],support_strength='direct_observation',limits=['同一E1引用被复用，不增加独立验证。']))
    k=dict(schema_version='1.1',model_status='manual_fixture',description='Self-authored synthetic workflow regression, not a real research paper.',document_registry=[dict(id='SYN',role='main_paper',format='pdf',title='Synthetic parallel calibration',version='1',availability='available',sha256=rl.file_sha(pdf),hash_status='verified',source_locator='Self-authored example',path=str(pdf),physical_page_count=1)],paper_type=dict(label='methods_or_model',confidence='high',basis=[copy.deepcopy(refs)],classification_origin='manual'),entities=entities,relations=relations,figures=[dict(id='F1',document_id='SYN',label='合成通道表',kind='main',source_refs=[copy.deepcopy(refs)])],stories=stories,relation_groups=[dict(id='PARALLEL',type='parallel_evidence',members=['E'+str(i) for i in range(1,count+1)],source_refs=[copy.deepcopy(refs)],limits=['共享参照、并行比较，不是独立生物学验证。'])],relation_constraints=[],quantity_operations=[])
    kp=root/'knowledge.json';save(kp,k)
    n=en.build_network(kp,source_cache=cache);np=root/'network.json';save(np,n)
    metadata=dict(citation_short='自编合成校准示例',doi='not-applicable-synthetic');save(root/'metadata.json',metadata)
    sm={s['id']:s for s in n['statements']}
    def sids(ids):return [sid for sid,s in sm.items() if set(s.get('entity_ids',[]))&set(ids)]
    def src(phrase):
        v=span(phrase);v['excerpt']=v.pop('text');return dict(document_id='SYN',document_sha256=rl.file_sha(pdf),physical_page=1,excerpt_sha256=hashlib.sha256(v['excerpt'].encode()).hexdigest(),source_status='SELF_AUTHORED_SYNTHETIC_EXACT_SPAN_ONLY',**v)
    # M1 above records a whole-page context hash. Preserve that exact source
    # identity as well as the finer excerpts; matching a page number is not enough.
    sources={'S_PAGE':src(text),'S0':src(protocol),'SL':src(boundary),**{'S'+str(i):src(v) for i,v in enumerate(observations,1)}}
    groups=[list(range(1,min(count,2)+1)),list(range(3,min(count,4)+1)),list(range(5,count+1))];groups=[x for x in groups if x]
    records=[dict(id='TITLE',text='多通道偏差如何比较？',source_node_ids=['M_SHARED'],source_statement_ids=sids(['M_SHARED']),source_spans=[span('Question: compare parallel channel offsets.')],semantic_review_status='PARTIAL'),dict(id='LIMIT',text='自编软件测试；共享参照与读数不等于独立生物学验证。',source_node_ids=[],source_statement_ids=[],source_spans=[span(boundary)],semantic_review_status='PARTIAL')]
    positions={};gnodes=[];lnodes=[dict(id='Q',kind='question',title='合成问题',short_text='比较通道偏差；保留共享参照及边界。',detail_text='合成软件输入，不是论文科学答案。',identity='AUTHOR_ARGUMENT',source_ids=['S0'],source_entity_ids=['M_SHARED'],statement_ids=sids(['M_SHARED']),field_bindings=[],review_status='PARTIAL')];ledges=[]
    def edge(eid,a,b,ss):return dict(id=eid,**{'from':a,'to':b},type='question_fork',identity='AUTHOR_ARGUMENT',label='并行比较',rationale='合成源明确并行，仅按编号分组便于概览。',alternatives='分组不表示新的实验、执行顺序或分组优劣。',source_ids=ss,review_status='PARTIAL',causal_claim=False)
    layA={'Q':[60,90,1160,85]};layB={'Q':[60,180,2860,160]};routesA={};routesB={}
    for j,items in enumerate(groups):
        gid='G'+str(j+1);es=['E'+str(i) for i in items];cs=['C'+str(i) for i in items];ids=es+cs
        shown=f'比较通道{items[0]}–{items[-1]}\n偏差{items[0]}–{items[-1]} mV；共享参照'
        records.append(dict(id=gid,text=shown,source_node_ids=ids,source_statement_ids=sids(ids),source_spans=[span(observations[i-1]) for i in items],semantic_review_status='PARTIAL'))
        gnodes.append(dict(id=gid,text_id=gid,role='result',font_size=21,position=dict(left=60+j*405,top=260,width=350,height=165)))
        lnodes.append(dict(id=gid,kind='analysis',title=f'通道{items[0]}–{items[-1]}',short_text=f'共用参照；偏差{items[0]}–{items[-1]} mV。',detail_text=shown+'\n仅为读数分组，不是新实验。',identity='SCIENTIFIC_EVIDENCE',source_ids=['S'+str(i) for i in items],source_entity_ids=ids,statement_ids=sids(ids),field_bindings=[],review_status='PARTIAL'))
        ledges.append(edge('FORK'+str(j+1),'Q',gid,['S0']))
        layA[gid]=[60+j*405,280,350,260];x=60+j*970;layB[gid]=[x,460,850,300]
        cx=235+j*405;routesA['FORK'+str(j+1)]={'points':[[640,175],[640,220],[cx,220],[cx,280]]}
        bcx=x+425;routesB['FORK'+str(j+1)]={'points':[[1490,340],[1490,390],[bcx,390],[bcx,460]]}
        for row,i in enumerate(items):
            nid='N'+str(i);eid='DETAIL'+str(i);bound=['E'+str(i),'C'+str(i)]+(['E1'] if i==2 else [])
            lnodes.append(dict(id=nid,parent_id=gid,kind='analysis',title=f'通道{i}',short_text=f'共享参照下偏差{i} mV。',detail_text=f'与共享参照比较，观察偏差{i} mV。\n这是固定合成记录，非独立生物学验证。',identity='SCIENTIFIC_EVIDENCE',source_ids=['S'+str(i)]+(['S1'] if i==2 else []),source_entity_ids=bound,statement_ids=sids(bound),field_bindings=[],review_status='PARTIAL'))
            ledges.append(edge(eid,gid,nid,['S0','S'+str(i)]));y=940+row*390;layB[nid]=[x,y,850,300]
            routesB[eid]={'points':[[x+425,760],[x+425,y]] if row==0 else [[x+850,610],[x+900+row*15,610],[x+900+row*15,y+150],[x+850,y+150]]}
    g=dict(version='pfs-display-guidance-1',paper_id='SYN',knowledge_sha256=rl.file_sha(kp),formal_ready=False,records=records,overview=dict(title_id='TITLE',limit_id='LIMIT',nodes=gnodes,edges=[dict(id='READ'+str(i),**{'from':gnodes[i-1]['id'],'to':gnodes[i]['id']},type='parallel',identity='presentation',label='并行阅读，非因果') for i in range(1,len(gnodes))]),figure_pages=[])
    # Explicit span checks are executable; no hand-counted offsets.
    for rec in records:
        for sp in rec['source_spans']:assert text[sp['start']:sp['end']]==sp['text']
    save(root/'display.guidance.json',g)
    facets=['background_gap','core_question','hypotheses','tasks','purpose','materials','groups_controls','conditions','methods','results','author_interpretation','limitations']
    idx=dict(version='pfs-scientific-index-1',source_pdf=str(pdf),file_sha256=rl.file_sha(pdf),page_count=1,formal_ready=False,reading_status='AVAILABLE_CONTENT_READ',methods_task_detection='COMPLETE_AVAILABLE',result_mapping_status='MAPPED_WITH_GAPS',article_type='methods_or_model',reading_record=dict(actor='self-authored example author',basis=[dict(path=str(page),sha256=rl.file_sha(page))],scope='Synthetic input only; no paper extraction'),sources=sources,facets={f:dict(status='PARTIAL',text='固定合成源；仅测试现有字段与流程。',sources=['S0','SL']) for f in facets})
    ip=root/'scientific_index.json';save(ip,idx)
    model=dict(version=rl.VERSION,paper_title='合成七通道并行比较',short_citation='自编合成示例',formal_ready=False,network_snapshot=n['snapshot'],sources=sources,nodes=lnodes,edges=ledges,core=dict(nodes=['Q']+[x['id'] for x in gnodes],edges=['FORK'+str(i+1) for i in range(len(groups))]),branches=[],method_explanations=[],inputs=dict(network=dict(path=str(np),sha256=rl.file_sha(np)),scientific_index=dict(path=str(ip),sha256=rl.file_sha(ip))),layout=dict(A=dict(width=1280,height=720,positions=layA,routes=routesA),B=dict(width=3000,height=2400,positions=layB,routes=routesB)))
    model['snapshot']=rl.snapshot(model);save(root/'research_logic.json',model)
    save(root/'workbook_bindings.json',dict(logic_snapshot=model['snapshot'],workbook_bindings=dict(figure_panels={'F1':['A']})))
    return dict(root=str(root),pdf=str(pdf),knowledge=str(kp),network=str(np),guidance=str(root/'display.guidance.json'),logic=str(root/'research_logic.json'),metadata=str(root/'metadata.json'),cache=str(cache),bindings=str(root/'workbook_bindings.json'))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--outdir',required=True,type=Path);a=p.parse_args()
    if a.outdir.exists() and any(a.outdir.iterdir()):p.error('Use a new empty output directory.')
    print(json.dumps(make(a.outdir),ensure_ascii=False,indent=2))
