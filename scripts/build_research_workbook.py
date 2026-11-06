"""Structured DOCX workbook from the same research-logic model and PPT exports.

Full scientific facts remain in M1/Inventory. This optional document contains
logic diagrams, source-linked explanations and structured reference appendices.
"""
from __future__ import annotations
import argparse,copy,csv,hashlib,json,shutil
from pathlib import Path
from collections import Counter
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.enum.section import WD_SECTION_START
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image
import research_logic as rl

class WorkbookFieldError(ValueError):
    def __init__(self,code,pointer):
        self.code=code;self.pointer=pointer
        super().__init__(code+': '+pointer)

def acquisition_field(fields,experiment_id):
    """Canonical inventory acquisition; legacy methods may only agree or stand alone."""
    pointer='/experiments/'+str(experiment_id)+'/fields/'
    present=[k for k in ['acquisition','methods'] if k in fields]
    if not present:raise WorkbookFieldError('WORKBOOK_ACQUISITION_REQUIRED',pointer+'acquisition')
    for key in present:
        field=fields[key]
        if not isinstance(field,dict) or not isinstance(field.get('status'),str) or not field['status'] or 'value' not in field:
            raise WorkbookFieldError('WORKBOOK_ACQUISITION_INVALID',pointer+key)
    if len(present)==2 and fields['acquisition']!=fields['methods']:
        raise WorkbookFieldError('WORKBOOK_ACQUISITION_CONFLICT',pointer+'acquisition|methods')
    return fields[present[0]]

def value(x):
    if x is None:return '待核实'
    return x if isinstance(x,str) else json.dumps(x,ensure_ascii=False)
def fonts(run,size=10.5,bold=False,color=None):
    run.font.name='Times New Roman';run.font.size=Pt(size);run.font.bold=bold
    rf=run._element.get_or_add_rPr().get_or_add_rFonts()
    for key,font in [('ascii','Times New Roman'),('hAnsi','Times New Roman'),('eastAsia','Microsoft YaHei')]:rf.set(qn('w:'+key),font)
    if color:run.font.color.rgb=RGBColor.from_string(color)
def table(doc,headers,rows,widths,size=10):
    t=doc.add_table(rows=1,cols=len(headers));t.autofit=False
    for c,w in zip(t.columns,widths):c.width=Inches(w)
    for c,h in zip(t.rows[0].cells,headers):
        c.text=h;pr=c._tc.get_or_add_tcPr();s=OxmlElement('w:shd');s.set(qn('w:fill'),'174994');pr.append(s)
        for r in c.paragraphs[0].runs:fonts(r,size,True,'FFFFFF')
    for c,w in zip(t.rows[0].cells,widths):c.width=Inches(w)
    repeat=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(repeat)
    for row in rows:
        cells=t.add_row().cells
        for c,w in zip(cells,widths):c.width=Inches(w)
        for c,txt in zip(cells,row):
            c.text=value(txt)
            for p in c.paragraphs:
                p.paragraph_format.space_after=Pt(2);p.paragraph_format.line_spacing=1.02
                for r in p.runs:fonts(r,size)
        props=cells[0]._tc.getparent().get_or_add_trPr();props.append(OxmlElement('w:cantSplit'))
    return t
def hyperlink(p,label,target):
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    h=OxmlElement('w:hyperlink');h.set(qn('r:id'),p.part.relate_to(target,RT.HYPERLINK,is_external=True));r=OxmlElement('w:r');rp=OxmlElement('w:rPr');co=OxmlElement('w:color');co.set(qn('w:val'),'174994');rp.append(co);r.append(rp);tt=OxmlElement('w:t');tt.text=label;r.append(tt);h.append(r);p._p.append(h)
def page_setup(section,width=11.69,height=8.27):
    section.page_width=Inches(width);section.page_height=Inches(height)
    section.top_margin=section.bottom_margin=Inches(.45);section.left_margin=section.right_margin=Inches(.55)
def select_branches(model,annotations):
    """Select existing view IDs only; omitted detail is not complete coverage."""
    available={b['id']:b for b in model['branches']};selection=annotations.get('branch_selection')
    if selection is None:
        ids=list(available)[:2]
        omitted={k:'未由旧默认的前两分支范围选择；完整B保留该分支，细化阅读仍需明确选择。' for k in available if k not in ids}
    else:
        if not isinstance(selection,dict):raise ValueError('WORKBOOK_BRANCH_SELECTION')
        ids=selection.get('view_ids');omitted=selection.get('omitted_reasons',{})
        if not isinstance(ids,list) or len(set(ids))!=len(ids) or not set(ids)<=set(available):raise ValueError('WORKBOOK_BRANCH_SELECTION_IDS')
        if not isinstance(omitted,dict) or set(omitted)!=set(available)-set(ids) or any(not isinstance(v,str) or not v.strip() for v in omitted.values()):raise ValueError('WORKBOOK_BRANCH_SELECTION_OMISSION_REASONS')
    coverage=dict(expected_branch_ids=list(available),displayed_branch_ids=ids,omitted_branches=omitted,status='PARTIAL' if omitted else 'COVERED_REGISTERED_BRANCHES',scientific_contribution_review='NOT_ASSESSED_BY_BUILDER')
    return [available[k] for k in ids],coverage

def build(model_path,manifest_path,output,annotations_path=None,content_path=None,figure_assets_path=None):
    from workbook_content import relation_text_fields
    model=rl.load(model_path)
    relation_texts=relation_text_fields(model)
    relation_display={e['id']:texts for e,texts in zip(model.get('edges',[]),relation_texts)}
    check=rl.validate_model(model)
    if not check['valid']:raise ValueError(str(check))
    net,inv=rl.inputs(model);methods=rl.methods_view(model);em={x['experiment_id']:x for x in methods};nm={x['id']:x for x in model['nodes']};index=rl.load(model['inputs']['scientific_index']['path'])
    annotations=rl.load(annotations_path) if annotations_path else {}
    if annotations:
        if annotations.get('logic_snapshot')!=model['snapshot']:raise ValueError('WORKBOOK_ANNOTATION_DRIFT')
        for row in annotations.get('rows',[]):
            if not row.get('source_ids') or not set(row['source_ids'])<=set(model['sources']):raise ValueError('WORKBOOK_ANNOTATION_SOURCE')
    manifest=rl.load(manifest_path);graphs={x['view']:x for x in manifest['graphs'] if x['logic_snapshot']==model['snapshot']}
    branches,branch_coverage=select_branches(model,annotations)
    required=['A','B']+[b['id'] for b in branches]
    for name in required:
        if name not in graphs:raise ValueError('WORKBOOK_BRANCH_GRAPH_REQUIRED: '+name)
        rec=graphs[name]
        if rl.file_sha(rec['png'])!=rec['png_sha256'] or rl.file_sha(rec['pptx'])!=rec['pptx_sha256']:raise ValueError('WORKBOOK_GRAPH_DRIFT: '+name)
    content=rl.load(content_path) if content_path else None
    if content:
        from workbook_content import validate_content
        ccheck=validate_content(model,content)
        if not ccheck['valid']:raise ValueError('WORKBOOK_DEPTH_BLOCKED: '+str(ccheck))
    from workbook_content import reviewed_figure_images
    if figure_assets_path and not content:raise ValueError('WORKBOOK_FIGURE_CONTENT_REQUIRED')
    figure_images,figure_receipt=reviewed_figure_images(model,content,figure_assets_path) if figure_assets_path else ({},None)
    output=Path(output)
    if output.exists():raise ValueError('OUTPUT_EXISTS')
    output.parent.mkdir(parents=True,exist_ok=True)
    doc=Document();page_setup(doc.sections[0]);doc.core_properties.title=model['paper_title']+' 科研逻辑拆解手册';doc.core_properties.identifier=model['snapshot'];doc.core_properties.subject='Shared research logic, Methods and evidence';doc.core_properties.author='Paper Figure Story'
    for sty in ['Normal','Caption','Heading 1','Heading 2','Title']:
        s=doc.styles[sty];s.font.name='Times New Roman';s._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'Microsoft YaHei');s.font.color.rgb=RGBColor.from_string('000000' if sty=='Title' else '174994' if sty.startswith('Heading') else '202A36');s.font.size=Pt(28 if sty=='Title' else 18 if sty=='Heading 1' else 13 if sty=='Heading 2' else 10.5)
        s.paragraph_format.space_after=Pt(6);s.paragraph_format.line_spacing=1.06
        s.font.bold=sty.startswith('Heading')
    footer=doc.sections[0].footer.paragraphs[0];fonts(footer.add_run('逻辑模型 '+model['snapshot'][:16]+'   '),8)
    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
    used=[]
    def para(txt,style=None):return doc.add_paragraph(txt,style)
    def heading(txt):doc.add_heading(txt,1)
    def newpage(txt):
        p=doc.add_heading(txt,1);p.paragraph_format.page_break_before=True
    def diagram(view,max_width=10.5,max_height=5.3):
        g=graphs[view];im=Image.open(g['png']);ratio=im.width/im.height;w=min(max_width,max_height*ratio);p=para('');p.paragraph_format.space_after=Pt(0);p.add_run().add_picture(g['png'],width=Inches(w));para('同一模型图 '+view+'   '+model['snapshot'][:16]+'   图形节点可在配套PPTX编辑','Caption');used.append({'view':view,'png':g['png'],'png_sha256':g['png_sha256'],'pptx':g['pptx'],'logic_snapshot':model['snapshot']})
    doc.add_heading(annotations.get('title','科研逻辑拆解手册' if inv else '科研论证拆解手册'),0)
    para(model['paper_title'])
    heading('01 核心问题与研究缺口')
    para(nm[model['core']['nodes'][0]]['short_text'])
    rows=[]
    for key in ['background_gap','core_question','hypotheses']:
        facet=index['facets'][key];sids=facet.get('sources',facet.get('source_ids',[]))
        explanation=facet.get('text') or (nm[model['core']['nodes'][0]]['short_text'] if key=='core_question' else '旧底稿未提供本层完整解释（PARTIAL）；不由图形逆推研究缺口或假说。')
        rows.append([{'background_gap':'已有认识与缺口','core_question':'中心问题','hypotheses':'待检验解释与边界'}[key],explanation,'p'+','.join(str(model['sources'][s]['physical_page']) for s in sids if s in model['sources'])])
    table(doc,['问题层次','科学内容','来源'],rows,[1.6,7.2,1.6],11)
    glossary=[r for r in annotations.get('rows',[]) if r.get('kind')=='glossary']
    if glossary:
        newpage('阅读术语')
        table(doc,['对象或术语','含义','来源'],[[r['term'],r['meaning'],'p'+','.join(str(model['sources'][s]['physical_page']) for s in r['source_ids'])] for r in glossary],[2.0,7.0,1.4],10)
    if content:para('已接入'+str(len(content['figures']))+'张Figure的逐图讲解及'+str(len(content['methods']))+'项Methods解读；这些是教学任务数，不是独立实验数。未获取的补件/重复参数仍标为PARTIAL。')
    else:para(str(len(methods))+'条记录包含实验、控制、计算或共享任务，不等于同等数量的独立实验。图和表采用论文论证关系，不冒充实验执行日历。' if inv else ('本手册整理综述论证与引用证据，不把引用研究登记成作者的新实验。' if net['paper']['paper_type'] in ['review','perspective'] else '本手册重建研究论证；本次未接入实验级Inventory，不代表论文没有实验。不能据此补填样本量、重复或统计信息。'))
    para('审核说明：本手册科学终审为PARTIAL（部分核实）。表中“观察、方法、解释、讲述、限制”表示内容类别，不表示全部已终审；缺失资料、统计歧义等具体例外在对应条目保留。')
    newpage('02 全文科研逻辑总览');diagram('A')
    # Regular reading pages; the unchanged editable poster remains a companion.
    section=doc.add_section(WD_SECTION_START.NEW_PAGE);page_setup(section);heading('完整科研论证与证据关系' if net['paper']['paper_type'] in ['review','perspective','editorial_or_voices'] else '完整科研逻辑与实验设计');diagram('B',10.5,4.65)
    poster=output.parent/'Complete_B.editable.pptx'
    if poster.exists() and rl.file_sha(poster)!=graphs['B']['pptx_sha256']:raise ValueError('COMPANION_OUTPUT_EXISTS')
    if Path(graphs['B']['pptx']).resolve()!=poster.resolve():shutil.copy2(graphs['B']['pptx'],poster)
    para('本页用于看清完整关系的分支与汇合。逐节点、来源和关系标签请打开下列原尺寸大画布并放大阅读；独立PPTX中的节点、文字和连线均可编辑。')
    hyperlink(para('完整B大画布：'),poster.name,poster.name)
    para('请保留本手册所在文件夹及配套文件；单独移动Word文件会使上述相对链接失效。')
    for bid,reason in branch_coverage['omitted_branches'].items():
        title=next(b['title'] for b in model['branches'] if b['id']==bid)
        para('分支阅读范围（PARTIAL）：未展开“'+title+'”。'+reason)
    section=doc.add_section(WD_SECTION_START.NEW_PAGE);page_setup(section)
    for bi,branch in enumerate(branches):
        if bi:doc.add_page_break()
        heading('03 '+branch['title']);diagram(branch['id'])
        exids=list(dict.fromkeys(b['experiment_id'] for nid in branch['nodes'] for b in nm[nid]['field_bindings']))
        if not exids:
            para('本分支尚未绑定实验级Inventory；图中事实的来源见索引。实验材料、分组、重复与统计口径仍需按原文逐项审核。')
            continue
        newpage('实验设计 读数与结果对照')
        rows=[]
        for eid in exids:
            m=em[eid];p=m['plain_explanation'];pages=','.join(str(model['sources'][s]['physical_page']) for s in p['source_ids']);rows.append([eid+'\n'+m['name']+'\n'+','.join(m['figure_ids'])+' / p'+pages,p['why'],p['design']+'\n'+p['readout'],p['result'],p['meaning']+'\n'+p['limit']])
        table(doc,['任务与来源','为什么做','怎样比较和读图','实际发现','能说明和不能说明'],rows,[1.65,1.55,2.65,2.0,2.55],9.5)
    # With no branches this is already the first paragraph of the new section.
    # Another page break would leave an empty page between B and the evidence table.
    if branches:newpage('04 跨分支证据与综合认识')
    else:heading('04 跨分支证据与综合认识')
    chosen=[e for e in model['edges'] if e['id'] in model['core']['edges']]
    for j in range(0,len(chosen),8):
        if j:doc.add_page_break();heading('跨分支关系与解释边界')
        rows=[]
        for e in chosen[j:j+8]:
            from workbook_content import IDENTITY_LABELS
            types={'progression':'论证递进','comparison':'比较','question_fork':'问题分支','evidence_convergence':'证据汇合','data_dependency':'数据输入','complements':'互补','parallel':'并行','qualifies':'限定','independent_validation':'独立核验','sequence':'实际先后'}
            rationale,alternatives=relation_display[e['id']]
            rows.append([e['id']+' '+nm[e['from']]['title']+' / '+nm[e['to']]['title'],types.get(e['type'],e['type'])+'\n'+IDENTITY_LABELS.get(e['identity'],e['identity']),rationale,alternatives,'p'+','.join(str(model['sources'][s]['physical_page']) for s in e['source_ids'])])
        table(doc,['起点与终点','关系身份','判断理由','不能额外推出','来源与状态'],rows,[2.0,1.7,2.7,2.7,1.3],10)
    if inv:
        full=output.parent/'Full_Experimental_Inventory.source.json';shutil.copy2(model['inputs']['inventory']['path'],full)
        csvpath=output.parent/'Methods字段与来源完整索引.csv'
        with csvpath.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f);w.writerow(['Experiment ID','字段','完整值','字段状态','原始字段来源','原始限制'])
            for m in methods:
                for key,field in m['fields'].items():w.writerow([m['experiment_id'],key,value(field.get('value')),field.get('status'),json.dumps(field.get('source_refs',[]),ensure_ascii=False),value(field.get('reason'))])
        for j in range(0,len(methods),9):
            newpage('05 完整Methods结构化清单' if j==0 else 'Methods清单续表')
            rows=[]
            for m in methods[j:j+9]:
                f=m['fields'];p=m['plain_explanation'];counts='；'.join(k+'='+value(f.get(k,{}).get('value'))+' ['+f.get(k,{}).get('status','NOT_VERIFIED')+']' for k in ['sample_count','biological_replicates','technical_replicates','independent_runs'])
                rows.append([m['experiment_id']+'\n'+m['task_type'],m['name'],p['design']+'\n'+p['readout'],counts,acquisition_field(f,m['experiment_id'])['status']+' / '+f['result']['status']+'\n'+','.join(m['figure_ids'])+'\n字段 '+str(len(f))+'项'])
            table(doc,['稳定ID与任务类别','任务名称','设计和关键检测','数量及重复的原记录','Methods/结果状态'],rows,[1.65,1.8,3.1,2.55,1.3],8.8)
        para('以上'+str(len(methods))+'项保留全部原始字段的结构化引用。完整材料、分组、处理、方法、分析、统计、Results及逐字段来源在配套文件中，不以压缩表替换原记录。')
        p=para('完整结构化Methods记录：');hyperlink(p,full.name,full.name)
        p=para('逐字段可编辑CSV：');hyperlink(p,csvpath.name,csvpath.name)
        para('原记录SHA256 '+rl.file_sha(full),'Caption')
    if content:
        from workbook_content import add_teaching_sections
        add_teaching_sections(doc,model,content,table,newpage,para,figure_images)
    newpage('06 来源与核验状态索引')
    statusrows=[['文件 页码与摘录','已检查文件SHA及字符区间','定位成功不等于科学语义或独立终审通过'],['正文和Methods阅读',index['reading_status'],'Supplementary缺失不等于原文未报告'],['科学解释','PARTIAL；独立终审未进行','机制解释保留原身份，未知参数不填补']]
    statusrows += [[r['title'],r['detail'],r['impact']] for r in annotations.get('rows',[]) if r.get('kind')=='status']
    table(doc,['核验层次','当前状态','影响'],statusrows,[2.0,4.1,4.3],10.5)
    sources=[]
    for sid,s in model['sources'].items():sources.append([sid,str(s['physical_page']),Path(s['path']).name+' 字符 '+str(s['start'])+'–'+str(s['end']),'定位已核；语义待终审'])
    for j in range(0,len(sources),12):
        if j:doc.add_page_break();heading('来源索引续表')
        table(doc,['来源ID','物理页','缓存定位','状态'],sources[j:j+12],[2.0,.7,4.0,3.7],9.5)
    para('逻辑模型 '+model['snapshot']);para('配套PPTX中的节点、连线与本文图像来自同一模型版本。文档文字和表格可编辑；图像可替换，节点编辑在配套PPTX中完成。')
    # The bundled Word template may include paragraph rules; keep the title plain.
    for root in [doc.element,doc.styles.element]:
        for border in list(root.iter(qn('w:pBdr'))):border.getparent().remove(border)
    doc.save(output)
    from apply_script_fonts import apply_docx_fonts
    apply_docx_fonts(output)
    receipt={'version':'pfs-workbook-1','docx':str(output),'docx_sha256':rl.file_sha(output),'logic_model':str(Path(model_path).resolve()),'logic_snapshot':model['snapshot'],'network_snapshot':model['network_snapshot'],'annotations_sha256':rl.file_sha(annotations_path) if annotations_path else None,'graphs':used,'inventory_source_sha256':rl.file_sha(full) if inv else None,'experiment_ids':[m['experiment_id'] for m in methods],'format':'Structured diagrams, comparisons and source tables; full Methods companion preserved, no article rewrite.','document_text_tables_editable':True,'diagram_editing':'Native nodes/arrows editable in linked PPTX; DOCX contains their exact exported PNGs.','render_status':'PENDING','formal_ready':False}
    receipt.update(content_sha256=rl.file_sha(content_path) if content_path else None,teaching_coverage=ccheck if content else {'valid':False,'status':'PARTIAL_TEACHING_CONTENT_NOT_CONNECTED'},workbook_scope='full-learning' if content else 'logic-only',branch_coverage=branch_coverage)
    if figure_receipt:receipt['figure_assets']=figure_receipt
    output.with_suffix('.receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8');return receipt
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model',required=True,type=Path);p.add_argument('--graphs',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--annotations',type=Path);p.add_argument('--content',type=Path,help='Source-bound Figure stories, Methods and quantitative evidence; omit only for explicitly partial logic-only output');p.add_argument('--reader',action='store_true');p.add_argument('--sample',action='store_true');p.add_argument('--scope',choices=['learning','logic-only'],default='learning');p.add_argument('--figure-assets',type=Path,help='Optional verified original Figure registry keyed by figure_id');a=p.parse_args()
    if a.reader and a.figure_assets:p.error('READER_FIGURE_ASSETS_UNSUPPORTED')
    if a.reader and a.content:p.error('READER_CONTENT_COMBINATION_UNSUPPORTED: legacy Reader uses Inventory/annotations; use the standard Workbook layout for --content. No input is silently ignored.')
    if a.reader and a.scope!='learning':p.error('READER_SCOPE_COMBINATION_UNSUPPORTED')
    if a.reader and not a.annotations:p.error('READER_ANNOTATIONS_REQUIRED')
    content_path=a.content
    if not a.reader and a.scope=='learning' and not content_path:
        from workbook_content import assemble_content
        try:assembly=assemble_content(rl.load(a.model),a.annotations)
        except (OSError,ValueError,KeyError,TypeError) as ex:
            assembly=dict(valid=False,gaps=[dict(code='SOURCE_INPUT_INVALID',detail=str(ex))],scientific_review='PARTIAL')
        audit=a.output.with_suffix('.assembly.json');audit.parent.mkdir(parents=True,exist_ok=True)
        if audit.exists():raise ValueError('OUTPUT_EXISTS: '+str(audit))
        audit.write_text(json.dumps(assembly,ensure_ascii=False,indent=2),'utf8')
        if not assembly['valid']:
            print(json.dumps(dict(status='PARTIAL',code='WORKBOOK_TEACHING_CONTENT_REQUIRED',gap_report=str(audit),gaps=assembly['gaps'],docx_generated=False,formal_ready=False),ensure_ascii=False));return 2
        content_path=a.output.with_suffix('.resolved_content.json')
        if content_path.exists():raise ValueError('OUTPUT_EXISTS: '+str(content_path))
        content_path.write_text(json.dumps(assembly['content'],ensure_ascii=False,indent=2),'utf8')
    if a.reader:
        from reader_workbook import build_reader
        r=build_reader(a.model,a.graphs,a.output,a.annotations,a.sample)
    else:r=build(a.model,a.graphs,a.output,a.annotations,content_path,a.figure_assets)
    print(json.dumps({'docx':r['docx'],'experiments':len(r['experiment_ids']),'graphs':len(r['graphs']),'teaching_figures':r.get('teaching_coverage',{}).get('figures',0),'method_explanations':r.get('teaching_coverage',{}).get('methods',0)},ensure_ascii=False))
if __name__=='__main__':
    try:raise SystemExit(main())
    except WorkbookFieldError as ex:
        print(json.dumps(dict(status='FAIL',code=ex.code,pointer=ex.pointer,docx_generated=False,formal_ready=False),ensure_ascii=False));raise SystemExit(2)
