/** Human speaking layer. Full IDs, source pointers and hashes remain in audit JSON. */
export function humanSpeakerNotes(scene,network,profile){
 const clean=s=>String(s||'').replace(/\n+/g,' ').trim();
 const ids=new Set(scene.source_statement_ids||[]);
 const statements=network.statements.filter(s=>ids.has(s.id));
 const nodes=new Map(network.nodes.map(n=>[n.id,n]));
 const body=scene.elements.filter(e=>e.kind==='text'&&e.id!==scene.id+'_title'&&!/(?:_title|_label|_legend|_review|_citation|_relation|EXNET_|B_extra|_term|TERM|LIMIT)/i.test(e.id)&&((e.statement_ids||[]).length||(e.source_node_ids||[]).length||(e.display_record_ids||[]).length));
 const terms=scene.elements.filter(e=>e.kind==='text'&&/(?:term|术语)/i.test(e.id));
 const limits=scene.elements.filter(e=>e.kind==='text'&&/limit|boundary/i.test(e.id));
 const methods=[...new Set(statements.filter(s=>['design','method'].includes(s.role)).map(s=>clean(s.text)))];
 const displayLimits=(scene.notes?.display_records||[]).filter(r=>r.role==='limitation').map(r=>clean(r.text));
 const figureIds=new Set(scene.figure_ids||scene.notes?.figure_ids||[]);
 const inventoryConflicts=(network.experiment_layer?.experiments||[])
  .filter(e=>(e.figure_ids||[]).some(id=>figureIds.has(id)))
  .flatMap(e=>Object.entries(e.fields||{}).filter(([,f])=>f.status==='CONFLICT')
   .map(([key,f])=>e.experiment_id+' / '+key+'：'+clean(f.value)+'（原文冲突待核）'));
 const restrictions=[...new Set([...limits.map(e=>clean(e.text)),...displayLimits,...statements.filter(s=>s.role==='limitation').map(s=>clean(s.text)),...inventoryConflicts])];
 const lines=['本页问题：'+clean(scene.title)];
 if(terms.length)lines.push('对象与术语：'+terms.map(e=>clean(e.text)).join('；'));
 if(methods.length)lines.push('方法与对照：'+methods.slice(0,3).join('；'));
 if(body.length){lines.push('讲述顺序：');body.forEach((e,i)=>lines.push((i+1)+'．'+clean(e.text)));}
 else if(scene.source_node_ids?.length)lines.push('讲述要点：'+scene.source_node_ids.slice(0,8).map(id=>clean(nodes.get(id)?.label||id)).join('；'));
 if(restrictions.length)lines.push('证据边界：'+restrictions.join('；'));
 if(scene.notes?.logic_relations?.length)lines.push('研究衔接：'+scene.notes.logic_relations.map(e=>e.label+'：'+e.rationale+' 边界：'+e.alternatives).join('\n'));
 if(scene.product==='B2')lines.push('本页仅为该Experiment ID的分页；未知n与重复仍待核，不能按散点、粒子、泳道或页数推算。');
 lines.push('来源：'+clean(scene.citation));
 lines.push('来源索引：'+(scene.source_statement_ids||[]).slice(0,6).join('，')+'；完整映射见同名独立audit JSON。');
 lines.push('审核：来源按已标状态保留；未核事实、作者假说与汇报连接分别对待。');
 return lines.join('\n\n');
}
