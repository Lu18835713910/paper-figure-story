"""Readable B2 cards from the same source-bound experiment layer as A/B1/C."""
import json,re

LABELS={'question':'科学问题','scientific_question':'科学问题','hypothesis':'待检验解释','materials':'对象与材料','biological_material':'对象与材料',
 'groups':'分组与对照','group_count':'实验组数','sample_count':'样本或测量数量','sample_unit':'数量单位',
 'biological_replicates':'生物学重复','technical_replicates':'技术重复','independent_runs':'独立实验次数',
 'treatments':'处理与条件','acquisition':'数据获取','analysis':'计算与数据分析','statistics':'统计与比较',
 'result':'实际结果','interpretation':'阶段认识','limitations':'科学限制','methods':'方法定位','results_sources':'结果定位',
 'timepoints':'采样时间','software':'软件与版本','controls':'对照','datasets':'数据集','particle_count':'粒子数量',
 'experimental_system':'实验体系','measurement_unit':'测量单位','readout_interpretation':'如何读数',
 'krr_identity':'KRR突变体身份','material_identity_conflict':'材料身份冲突','software_version_conflict':'软件版本冲突',
 'input_expression_runs':'所用表达校正实验次数'}
STATUS={'VERIFIED':'VERIFIED 原文字段已核对','PARTIAL':'PARTIAL 部分可核','NOT_REPORTED':'NOT_REPORTED 已查范围未报告',
 'NOT_VERIFIED':'NOT_VERIFIED 尚未完成核验','CONFLICT':'CONFLICT 来源存在冲突'}

VALUE_LABELS={'voltage_kV':'加速电压（kV）','dose_e_per_A2':'总电子剂量（e⁻/Å²）',
 'energy_filter_eV':'能量过滤狭缝（eV）','frames_per_video':'每段视频帧数','pixel_A':'像素尺寸（Å）',
 'binned_pixel_A':'合并后像素尺寸（Å）','nominal_defocus_um':'标称离焦范围（μm）','nominal_magnification':'标称放大倍率',
 'RMSD_A':'均方根偏差（Å）','layer_RMSD_A_CNBH_aligned':'以CNBH对齐的各层均方根偏差（Å）',
 'MgATP_resolution_A':'MgATP结合结构分辨率（Å）','apo':'未结合配体状态','architecture':'整体架构',
 'reported_dimensions_A':'原文报告尺寸（Å）','height':'高度','length':'长度','width':'宽度',
 'particle_count':'粒子数量','per_condition_assignment':'各条件对应关系','per_dataset_refinement_statistics':'各数据集精修统计',
 'quantitative_resolution':'分辨率数值','accessions':'数据库编号','deposited_atomic_models':'存储的原子模型',
 'deposited_maps':'存储的电镜密度图','software':'软件','crosslinked':'交联组','non_crosslinked':'未交联组',
 'D262C_particle_classes':'D262C粒子分类','corresponding_Calpha_distance_A':'对应Cα间距（Å）',
 'corresponding_gate_Calpha_distance_A':'对应门控位置Cα间距（Å）','WT_R141':'WT的R141位点',
 'KRR_A141':'KRR的A141位点','WT_outward_A208_Calpha_A':'WT外向状态A208 Cα间距（Å）',
 'CorC_inward_corresponding_A':'CorC内向结构对应间距（Å）','WT_D262_separation_A_approx':'WT的D262约略间距（Å）',
 'WT_D262_separation_A_in_Fig4A':'Fig.4A中WT的D262间距（Å）',
 'WT_extracellular_D262':'WT胞外侧D262','WT_intracellular_A208':'WT胞内侧A208',
 'D262C_extracellular_corresponding_site':'D262C胞外侧对应位点','D262C_intracellular_A208':'D262C胞内侧A208',
 'ATP_molecules_per_dimer':'每二聚体ATP分子数','ATP_associated_Mg_per_ATP':'每个ATP相关Mg数量',
 'additional_acidic_patch_Mg_per_subunit':'酸性区域每亚基额外Mg数量',
 'additional_acidic_patch_Mg_per_tetramer':'酸性区域每四聚体额外Mg数量',
 'paired_gamma_phosphate_separation_A_approx':'成对γ磷酸基约略间距（Å）','conserved_site':'保守位点',
 'ECD':'胞外结构域（ECD）','TMD':'跨膜结构域（TMD）','CNBH':'CNBH结构域','CBSP':'CBSP结构域'}

def readable(value,context=''):
    if value is None:return '未提供可核实数值'
    if isinstance(value,list):
        if value and all(isinstance(v,(int,float)) and not isinstance(v,bool) for v in value):
            return (' 至 ' if context=='nominal_defocus_um' and len(value)==2 else '、').join(map(str,value))
        return '\n'.join(readable(v) for v in value)
    if isinstance(value,dict):return '\n'.join(VALUE_LABELS.get(str(k),str(k))+'：'+readable(v,str(k)) for k,v in value.items())
    return str(value)

def build_cards(network,profile,metadata):
    from project_evidence_products import textbox,wrap,_citation,_unique
    layer=network.get('experiment_layer')
    if not layer:return None
    scenes=[]
    for exp in layer['experiments']:
        eid=exp['experiment_id'];fields=exp['fields'];chunks=[]
        for key,field in fields.items():
            value=readable(field.get('value'))
            if field.get('candidates') and field.get('value') in (None,''):
                value='冲突候选（未自动选择）：\n'+readable(field['candidates'])
            if field.get('unit'):value+='\n单位：'+str(field['unit'])
            if field.get('reason'):value+='\n核验边界：'+str(field['reason'])
            value=STATUS.get(field['status'],field['status'])+'\n'+value
            lines=wrap(value,530,21).split('\n')
            for start in range(0,len(lines),9):chunks.append((key,field,'\n'.join(lines[start:start+9]),start>0))
        pages=[];current=[];col=0;y=158
        for key,field,text,continued in chunks:
            height=36+max(27,len(text.split('\n'))*26)+15
            if y+height>643:
                if col==0:col=1;y=158
                else:pages.append(current);current=[];col=0;y=158
            current.append((key,field,text,continued,col,y,height));y+=height+10
        if current:pages.append(current)
        for pi,page in enumerate(pages,1):
            title=eid+'  '+exp['display_name'];els=[textbox('EXP_title',wrap(title,1160,31),60,64,1160,70,31,True)]
            sids=[];nids=[eid]
            for seq,(key,field,text,continued,col,y,height) in enumerate(page):
                x=60+col*590;label=LABELS.get(key,key)+('（续）' if continued else '')
                els.append(textbox('EXP_label_'+str(seq),label,x,y,540,31,22,True))
                bound=[s['id'] for s in network['statements'] if s.get('source_pointer',{}).get('input_kind')=='experiment_inventory' and
                       eid in s.get('entity_ids',[]) and ('/fields/'+key+'/') in s.get('source_pointer',{}).get('pointer','')]
                obj=textbox('EXP_field_'+str(seq),text,x,y+35,540,height-35,21,statement_ids=bound)
                obj['source_node_ids']=[eid];obj['experiment_field']={'experiment_id':eid,'field':key,'status':field['status'],'source_refs':field.get('source_refs',[])}
                els.append(obj);sids+=bound
            els.append(textbox('EXP_review','字段核对状态不等于独立科学终审；数量单位及冲突按原文保留。'+f'  本实验详情 {pi}/{len(pages)}',60,656,1160,28,15,color='#63758B'))
            refs=[r for f in fields.values() for r in f.get('source_refs',[])];pages_ref=sorted({r.get('physical_page',r.get('locator',{}).get('physical_page')) for r in refs if r.get('physical_page',r.get('locator',{}).get('physical_page'))})
            citation=metadata.get('citation_short','来源论文')+' · '+eid+' · PDF p.'+','.join(map(str,pages_ref))+' · DOI '+metadata.get('doi','待核')
            scenes.append({'id':eid.replace('.','_')+'_'+str(pi),'product':'B2','title':title,'elements':els,'connectors':[],
                           'source_statement_ids':_unique(sids),'source_node_ids':nids,'source_relation_ids':[],
                           'figure_ids':exp.get('figure_ids',[]),'citation':citation,
                           'notes':{'experiment':exp,'network_snapshot':network['snapshot'],'scientific_review_status':'PARTIAL','formal_ready':False,
                                    'speaker_script':'以该实验的实际对象、处理、测量和分析解释结果，所有数量按单位读取，待核字段不补造。'}})
    return {'kind':'experiment_cards','width':1280,'height':720,'slides':scenes}

def build_network_canvas(network,metadata):
    from project_evidence_products import textbox,rect,wrap,line,_short
    layer=network['experiment_layer'];exps=layer['experiments'];rows=(len(exps)+2)//3;width=3200
    known={e['experiment_id'] for e in exps};nm={n['id']:n for n in network['nodes']}
    extra=list(dict.fromkeys(x for r in layer['relations'] for x in [r['from'],r['to']] if x not in known))
    extra_top=235+rows*455-90
    legend_top=extra_top+((len(extra)+2)//3)*245;height=legend_top+((len(layer['relations'])+2)//3)*80+130
    if height>5350:raise ValueError('EXPERIMENT_CANVAS_NEEDS_PARTITION')
    els=[textbox('EXNET_title','实验级科研关系网络：任务、共享流程与互补证据',60,40,3080,72,42,True),
         textbox('EXNET_legend','每个节点是稳定实验任务ID。箭头类型及来源身份逐条保留；uses表示使用/关联，不表示分子因果或实验历史。详细参数见B2同ID。',60,125,3080,65,25,color='#63758B')]
    pos={}
    for i,e in enumerate(exps):
        x=60+(i%3)*980;y=235+(i//3)*455;p={'left':x,'top':y,'width':820,'height':230};pos[e['experiment_id']]=p
        els.append(rect('EXNET_'+e['experiment_id'],x,y,820,230,fill='#EAF1FB'))
        title=e['experiment_id']+'\n'+e['display_name']
        item=textbox('EXNET_text_'+e['experiment_id'],wrap(title,780,29),x+20,y+18,780,190,29,True);item['source_node_ids']=[e['experiment_id']];els.append(item)
    for i,nid in enumerate(extra):
        if nid not in nm:raise ValueError('EXPERIMENT_RELATION_ENDPOINT_UNREGISTERED: '+nid)
        x=60+(i%3)*980;y=extra_top+(i//3)*245;p={'left':x,'top':y,'width':820,'height':170};pos[nid]=p
        els.append(rect('EXNET_extra_'+nid,x,y,820,170,fill='#F7F9FC'))
        item=textbox('EXNET_extra_text_'+nid,wrap(nid+'\n'+nm[nid]['label'],780,26),x+20,y+12,780,145,26);item['source_node_ids']=[nid];els.append(item)
    con=[]
    for i,r in enumerate(layer['relations']):
        a,b=pos[r['from']],pos[r['to']];ys=a['top']+a['height']+15;gutter=b['left']-18
        if a['left']==b['left']:
            gutter=b['left']+b['width']+18
            pts=[[a['left']+410,a['top']+a['height']],[a['left']+410,ys],[gutter,ys],[gutter,b['top']+b['height']/2],[b['left']+820,b['top']+b['height']/2]]
        else:pts=[[a['left']+410,a['top']+a['height']],[a['left']+410,ys],[gutter,ys],[gutter,b['top']+b['height']/2],[b['left'],b['top']+b['height']/2]]
        c=line('EXNET_'+r['id'],pts,r['identity'],r['id'],r['type'] not in ['compares','parallel_to'],r['identity'] in ['author_argument','presentation','mechanism_hypothesis']);c['relation_type']=r['type'];con.append(c)
        identity=r.get('inventory_identity',r['identity'])
        label=r['id']+' '+r['type']+' ['+identity+']\n'+r['from']+' → '+r['to']
        els.append(textbox('EXNET_relation_'+str(i),label,60+(i%3)*980,legend_top+(i//3)*80,920,65,20,color='#63758B'))
    scene={'id':'B1_experiments','product':'B1','title':'实验级科研关系网络','elements':els,'connectors':con,'figure_ids':[],
            'source_statement_ids':[],'source_node_ids':[e['experiment_id'] for e in exps]+extra,'source_relation_ids':[r['id'] for r in layer['relations']],
           'citation':metadata.get('citation_short','来源论文')+' · STAR Methods/Results · DOI '+metadata.get('doi','待核'),
           'notes':{'network_snapshot':network['snapshot'],'experiment_layer':layer,'scientific_review_status':'PARTIAL','formal_ready':False,'user_acceptance':'PENDING'}}
    return {'kind':'experiment_network','width':width,'height':height,'slides':[scene]}
