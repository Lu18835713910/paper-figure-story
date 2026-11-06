#!/usr/bin/env python3
"""Structural QA for Paper Figure Story outputs; never claims scientific verification."""
import argparse
import csv
import pathlib
import re
import sys

FILES = [
    '01_论文总体科研逻辑.md',
    '02_Figure逐图研究故事.md',
    '03_PPT逐页讲述脚本.md',
    '04_证据溯源与核查.md',
    '05_实验设计证据矩阵.csv',
]
REQUIRED_CSV = ['Figure', 'Panel', '问题来源', '科学问题', '样本与分组', '对照', '实验方法', '测量指标', '关键结果', '结论及证据级别', '下一步问题', '论文来源']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('outdir', type=pathlib.Path)
    p.add_argument('--allow-partial', action='store_true', help='Validate only files present')
    p.add_argument('--profile', choices=['balanced','quick','full'], default='balanced', help='Output profile')
    p.add_argument('--require-B', action='store_true', help='Require a complete source-model B canvas and its main-deck overview')
    p.add_argument('--development-preview', action='store_true', help='Explicit internal preview: unresolved panel semantics remain PARTIAL; structural/fidelity blockers are never bypassed')
    p.add_argument('--delivery-manifest', action='store_true', help='Explicit registered-delivery contract; legacy document validation remains unchanged')
    p.add_argument('--logic-model', type=pathlib.Path)
    p.add_argument('--graph-manifest',type=pathlib.Path,help='Validate the actual native graph/main-navigation subset only; does not certify complete paper delivery.')
    args = p.parse_args()
    root = args.outdir
    if args.graph_manifest:
        import json,research_logic as rl
        from delivery_contract import validate_delivery
        if not args.logic_model:p.error('--graph-manifest requires --logic-model')
        model=rl.load(args.logic_model);registration=rl.load(args.graph_manifest)
        result=validate_delivery(model,registration['graphs']+registration.get('main_graphs',[]),args.require_B,True)
        source=rl.validate_model(model)
        if not source['valid']:result['errors'].append('SOURCE_MODEL_INVALID');result['valid']=False
        result.update(scope='Native graph/navigation contract subset only; NOT a complete Full paper-delivery result.',scientific_review='PARTIAL')
        print(json.dumps(result,ensure_ascii=False));return 0 if result['valid'] else 1
    if args.delivery_manifest:
        import json,research_logic as rl
        from delivery_contract import check_package,rendered_topology,main_model_audit
        if not args.logic_model:p.error('--delivery-manifest requires --logic-model')
        model=rl.load(args.logic_model);manifest=rl.load(root/'Manifest.json');q=check_package(root,args.profile);errors=list(q['errors'])
        if not rl.validate_model(model)['valid']:errors.append('SOURCE_MODEL_INVALID')
        if manifest['logic_snapshot']!=model['snapshot']:errors.append('DELIVERY_MODEL_DRIFT')
        if not q['requested_complete']:errors.append('REQUESTED_DELIVERY_INCOMPLETE')
        products={x['product'] for x in manifest['files']}
        if args.profile=='full' and not {'main','A','B','Workbook'}<=products:errors.append('FULL_PRODUCTS_REQUIRED')
        if args.require_B and not {'main','B'}<=products:errors.append('MAIN_AND_COMPLETE_B_REQUIRED')
        for row in manifest['files']:
            if row['product'] in ['A','B'] and row['path'].endswith('.pptx'):
                view=row['product'];ns,es=rendered_topology(root/row['path'],view)
                if ns!=set(model['core']['nodes'] if view=='A' else [n['id'] for n in model['nodes']]) or es!=set(model['core']['edges'] if view=='A' else [e['id'] for e in model['edges']]):errors.append('NATIVE_TOPOLOGY_DRIFT:'+view)
            if row['product']=='main' and row['path'].endswith('.pptx'):errors+=main_model_audit(root/row['path'],model)['errors']
        structural_errors=q['structure_errors']+[e for e in errors if e not in q['errors']]
        print(json.dumps(dict(valid=not errors,errors=errors,structural_validation=dict(valid=not structural_errors,errors=structural_errors),contribution_validation=q['contribution_coverage'],scope='Structure and source-bound registered coverage are assessed separately; neither certifies full-paper discovery or scientific final review',scientific_review='PARTIAL'),ensure_ascii=False));return 0 if not errors else 1
    errors, warns = [], []
    from delivery_contract import assess_contribution_coverage
    import json
    coverage=assess_contribution_coverage(root,json.loads((root/'Manifest.json').read_text('utf-8-sig')) if (root/'Manifest.json').is_file() else {},args.profile)
    errors.extend(coverage['integrity_errors']+coverage['policy_errors']);warns.extend(coverage['warnings'])
    if args.profile in ('balanced','quick','full'):
        light_files = (FILES + ['06_PPT页面数据.json','07_科研逻辑汇报.pptx','08_PPT模板适配与质检.md']) if args.profile=='full' else ['01_科研逻辑与逐Figure证据.md', '06_PPT页面数据.json', '07_科研逻辑汇报.pptx', '08_简明质检.md']
        for n in light_files:
            fp = root / n
            if not fp.exists():
                (warns if args.allow_partial else errors).append('缺少文件：' + n)
            elif not fp.stat().st_size:
                errors.append('文件为空：' + n)
        jpath = root / '06_PPT页面数据.json'
        if jpath.is_file():
            try:
                import json
                doc = json.loads(jpath.read_text(encoding='utf-8'))
                from figure_assets import validate_manifest_images
                validate_manifest_images(doc,root)
                if args.require_B and not doc.get('delivery_contract'):
                    errors.append('COMPLETE_B_CONTRACT_REQUIRED')
                if doc.get('delivery_contract'):
                    from delivery_contract import validate_delivery
                    dc=doc['delivery_contract'];model=json.loads((root/dc['model']).read_text('utf-8-sig'));result=validate_delivery(model,dc.get('products',[]),args.require_B or dc.get('requested_B',False),main_pptx=root/'07_科研逻辑汇报.pptx')
                    errors.extend(result['errors'])
                ss = doc.get('slides', [])
                if not isinstance(ss,list) or not ss:
                    errors.append('PPT JSON缺少有效slides')
                elif not any(x.get('kind')=='framework' for x in ss):
                    errors.append('PPT JSON缺少全文联合总框架(kind=framework)')
                if ss and not any(x.get('kind')=='figure' for x in ss):
                    errors.append('PPT JSON缺少逐Figure页')
            except Exception as e:
                errors.append('JSON解析失败：'+str(e))
        pptx = root / '07_科研逻辑汇报.pptx'
        if pptx.exists() and pptx.stat().st_size:
            try:
                from pptx import Presentation
                prs = Presentation(str(pptx))
                if len(prs.slides)<3:
                    errors.append('PPT页数过少：'+str(len(prs.slides)))
                has_images=any(s.shape_type==13 for slide in prs.slides for s in slide.shapes)
                if has_images:
                    ctx=doc.get('source_context') if jpath.is_file() else None
                    if not ctx:errors.append('PPT_SOURCE_CONTEXT_REQUIRED')
                    else:
                        import polish_presentation as pp
                        context=json.loads((root/ctx).read_text('utf-8-sig')) if isinstance(ctx,str) else ctx
                        qa=pp.audit_input(pptx,context)
                        blocking={'OFF_CANVAS','IMAGE_ASPECT','CRITICAL_REGION_CLIPPED','FIGURE_ASSET_UNREGISTERED','FIGURE_SOURCE_MAPPING_REQUIRED','FIGURE_FIDELITY_BLOCKED','LOGIC_DIAGRAM_SOURCE_BLOCKED','MISSING_FIGURE','PANEL_MAPPING_UNRESOLVED'}
                        for page in qa['slides']:
                            for issue in page['issues']:
                                if issue['code'] in blocking:
                                    dest=warns if args.development_preview and issue['code']=='PANEL_MAPPING_UNRESOLVED' else errors
                                    dest.append('slide '+str(page['slide'])+': '+issue['code'])
            except Exception as e:
                errors.append('PPT解析失败：'+str(e))
        if args.profile!='full':
            print(f'检查目录：{root}  Profile: {args.profile}')
            print('CONTRIBUTION_COVERAGE: '+json.dumps(coverage,ensure_ascii=False))
            for v in warns: print('WARN:',v)
            for v in errors: print('ERROR:',v)
            if not warns and not errors: print('PASS：文件与结构检查通过（不是科学内容核实）')
            return 1 if errors else 0
    for n in FILES:
        f = root / n
        if not f.exists():
            (warns if args.allow_partial else errors).append('缺少文件：' + n)
        elif not f.stat().st_size:
            errors.append('文件为空：' + n)
    fig = root / FILES[1]
    if fig.is_file():
        s = fig.read_text(encoding='utf-8')
        figures = re.findall(r'(?im)^\s*#{1,4}\s*(?:Figure|Fig\.?|图)\s*\d+', s)
        if not figures:
            warns.append('逐图文件没有可识别的 Figure 小节标题')
        for word in ['样本', '实验', '结果', '下一', '来源']:
            if word not in s:
                warns.append(f'逐图文件缺少关键词：{word}')
        if not re.search(r'\bFig(?:ure)?\.?\s*\d+\s*[a-z]?\b', s, re.I):
            warns.append('逐图报告缺少可核查的 Fig/panel 引用')
    ppt = root / FILES[2]
    if ppt.is_file():
        s = ppt.read_text(encoding='utf-8')
        if not re.search(r'(?im)^\s*#{1,4}\s*(?:Slide|幻灯片|第\s*\d+\s*页)', s):
            warns.append('PPT逐页文件没有可识别的页级标题')
        for w in ['科学问题', '技术路线', '实验', '结果']:
            if w not in s:
                warns.append(f'PPT逐页文件可能缺少：{w}')
    datafile = root / FILES[4]
    if datafile.is_file():
        try:
            with datafile.open('r', encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f)
                names = reader.fieldnames or []
                missing = [x for x in REQUIRED_CSV if x not in names]
                if missing:
                    errors.append('证据矩阵CSV缺少列：' + ', '.join(missing))
                rows = list(reader)
                if not rows:
                    warns.append('证据矩阵CSV没有数据行')
                else:
                    n_missing = sum(not r.get('论文来源', '').strip() for r in rows)
                    if n_missing:
                        warns.append(f'{n_missing}条证据缺少论文来源')
        except Exception as e:
            errors.append('读取CSV失败：' + str(e))
    print(f'检查目录：{root}')
    print('基础静态检查（不能代替原文事实核查）')
    print('CONTRIBUTION_COVERAGE: '+json.dumps(coverage,ensure_ascii=False))
    for s in warns:
        print('WARN:', s)
    for s in errors:
        print('ERROR:', s)
    if not warns and not errors:
        print('PASS：结构检查通过；仍需核对原论文。')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
