"""Presentation scope and report sections, using existing source IDs only."""
import copy

def compose_delivery(network,products,metadata,options):
    from project_evidence_products import textbox,wrap,_question,_notes,_citation,_unique
    if options.get('scope') not in ('presentation','with-network','deep'):raise ValueError('UNKNOWN_DELIVERY_SCOPE')
    out=copy.deepcopy(products);main=out[0];original=main['slides'];nm={n['id']:n for n in network['nodes']}
    def scene(identifier,title,elements,sids=None,nids=None,section='研究总结'):
        ss=[s for s in network['statements'] if s['id'] in set(sids or [])]
        return {'id':identifier,'product':'TEXT','section':section,'title':title,'elements':[textbox(identifier+'_title',wrap(title,1160,32),60,65,1160,90,32,True)]+elements,
                'connectors':[],'figure_ids':[],'source_statement_ids':sids or [],'source_node_ids':nids or [],'source_relation_ids':[],
                'citation':_citation(network,metadata,[],ss),'notes':_notes(network,ss,title,metadata,[])}
    if options.get('report_sections',True):
        title=network['paper']['title'];q,qids=_question(network)
        cover=scene('REPORT_cover','科研文献汇报',[
            textbox('REPORT_paper',wrap(title,1130,35),60,220,1130,230,35,True),
            textbox('REPORT_type','文献类型：'+network['paper']['paper_type'],60,530,1130,42,23),
            textbox('REPORT_cite',wrap(metadata.get('citation_short',''),1130,22),60,590,1130,60,22)],section='文献信息')
        ms=[n for n in network['nodes'] if n['kind']=='method'][:3]
        intro=scene('REPORT_question','研究问题与证据路径',[
            textbox('REPORT_question_body',wrap(q,1130,30),60,190,1130,145,30,True,statement_ids=qids),
            textbox('REPORT_methods',wrap('研究方法：'+'；'.join(n['label'] for n in ms),1130,25),60,370,1130,180,25)],qids,[n['id'] for n in ms],section='科学问题')
        claims=[n for n in network['nodes'] if n['kind']=='claim'];claim_map={n['id']:n for n in claims}
        chosen_ids=options.get('summary_claim_ids',list(claim_map));omissions=options.get('summary_omissions',{})
        if not isinstance(chosen_ids,list) or len(set(chosen_ids))!=len(chosen_ids) or not set(chosen_ids)<=set(claim_map):raise ValueError('SUMMARY_CLAIM_SELECTION')
        if not isinstance(omissions,dict) or set(omissions)!=set(claim_map)-set(chosen_ids) or any(not isinstance(v,str) or not v.strip() for v in omissions.values()):raise ValueError('SUMMARY_OMISSION_REASONS_REQUIRED')
        summaries=[]
        # Preserve the six-card canvas capacity, not an arbitrary six-claim limit.
        for start in range(0,max(1,len(chosen_ids)),6):
            group=[claim_map[k] for k in chosen_ids[start:start+6]];elems=[];sids=[]
            for i,n in enumerate(group):
                bound=[s['id'] for s in network['statements'] if n['id'] in s.get('entity_ids',[]) and s['role']=='interpretation']
                e=textbox('REPORT_conclusion_'+str(start+i),wrap(n['label'],535,27),60+(i%2)*600,190+(i//2)*130,535,105,27,True,statement_ids=bound)
                e['source_node_ids']=[n['id']];elems.append(e);sids+=bound
            limits=[s for s in network['statements'] if s['role']=='limitation' and any(n['id'] in s.get('entity_ids',[]) for n in group)]
            if limits:
                chosen=limits[-1];elems.append(textbox('REPORT_limit',wrap(chosen['text'],1130,19),60,600,1130,70,19,statement_ids=[chosen['id']]));sids.extend(s['id'] for s in limits)
            identifier='REPORT_summary'+('_'+str(start//6+1) if start else '')
            summary=scene(identifier,'综合认识与证据边界'+('（续）' if start else ''),elems,_unique(sids),[n['id'] for n in group])
            summary['notes']['summary_limit_statement_ids']=[s['id'] for s in limits]
            summaries.append(summary)
        main['slides']=[cover,intro]+original+summaries
    select=options.get('slide_ids')
    if select:
        available={s['id']:s for s in main['slides']}
        if len(set(select))!=len(select) or any(x not in available for x in select):raise ValueError('UNKNOWN_OR_DUPLICATE_SLIDE_SELECTION')
        main['slides']=[available[x] for x in select]
        main['deferred_slide_ids']=[s['id'] for s in ([cover,intro]+original+summaries if options.get('report_sections',True) else original) if s['id'] not in select]
    if options.get('report_sections',True):
        displayed=_unique(n for s in main['slides'] if s['id'].startswith('REPORT_summary') for n in s['source_node_ids'])
        omitted={k:omissions.get(k,'Explicit slide_ids selection deferred its summary page.') for k in claim_map if k not in displayed}
        main['summary_coverage']=dict(expected_claim_ids=list(claim_map),selected_claim_ids=chosen_ids,displayed_claim_ids=displayed,omitted_claims=omitted,status='PARTIAL' if omitted else 'COVERED_REGISTERED_CLAIMS',scientific_contribution_review='NOT_ASSESSED_BY_PROJECTOR')
    main['coverage_scope']='selected_pages' if select else 'planned_report'
    return out
