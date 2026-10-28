# 科研逻辑结构与来源合同

版本`pfs-research-logic-1`是M1、RSU、Evidence Network和Inventory之上的引用与论证视图，不替代已有事实。先读当前可用全文、整理Methods任务和结果，再由Agent判定关系；脚本只检验引用和投影，不从编号、关键词或坐标自动推导科学依赖。

## 输入和审核

`inputs`绑定network、scientific_index及适用inventory的路径和SHA256。科学索引含背景缺口、中心问题、假说、任务、目的、材料、分组对照、处理、方法、结果、作者解释、限制12类；标记阅读、Methods识别和结果映射状态。`sources`保存原文文档ID/PDF指纹、物理页、缓存指纹、字符区间、短摘录及摘录指纹。文件/区间验证只证明定位，科学终审独立保存。

`nodes`引用既有source_entity_ids、statement_ids、Inventory字段和source_ids。`edges`记录起终点、类型、身份、判断理由、其他解释及来源。身份包括SCIENTIFIC_EVIDENCE、AUTHOR_ARGUMENT、AUTHOR_INTERPRETATION、PRESENTATION、SHARED_PROTOCOL和ACTUAL_PROTOCOL_ORDER。类型包括progression、question_fork、parallel、complements、evidence_convergence、shared_workflow、hypothesizes、comparison、protocol_order和qualifies。论证推进不等于因果或实验历史；执行顺序还须对应原网络experimental_precedes及端点。假说不得登记成已验证关系，共享流程不得计为独立验证。

当前研发合同要求review_status=PARTIAL、formal_ready=false；不能据定位校验擅自升级独立审阅状态。未来正式发布门需要独立科学审核，不以本合同布尔值替代。

## A和B共享身份

`core.nodes/edges`定义A核心。B保留这些身份和关系，选择性展开Methods、对照、参数与证据，并用parent_id映射详细成员。`compress_to_core`及validate_AB检验B能回到A。独立分支图可展示成员间的细粒度关系；完整模型与图中实际可见边分别报告。任何layout/routes仅影响位置，不添加科学边。C仍使用原逐Figure合同。

每项`method_explanations`引用稳定experiment_id和原字段，含why/design/readout/result/meaning/limit及来源。`methods_view`回读完整Inventory字段，不复制出一套可独立改写的事实。任务重复绑定只计一次；n、样本单位、技术/生物重复、独立实验、粒子数分别保留。

quick/balanced/full共享同一科学索引、来源和逻辑模型。quick少展示展开，balanced保留主要对照和分支，full增加有源细节；`deep`是Methods审计/产物范围，不是第四种科学事实。缺补件不能以NOT_REPORTED代替NOT_VERIFIED。

## 命令和兼容

```text
python scripts/research_logic.py --model logic.json --output validation.json
python scripts/project_research_logic.py --network evidence_network.json --model logic.json --views A B branch_id --outdir plans
python scripts/run_pfs.py run ... --research-logic logic.json --plan-only
```

新入口显式启用；旧CLI和project_products无research_logic时行为不变。模型指纹参与重建漂移检验，未关闭TEXT_DRIFT/PLAN_DRIFT。投影的source_logic_*引用不能冒充M1科学实体。

`logic_display`是版本绑定的显示注释，包含节点问题/方法/发现/意义、布局和边的简短标签。只引用已有节点、关系及来源，不得改科学身份或新增因果；核心边不得隐藏。非核心冗余支持或共享流程可以集中说明，必须在notes.display_only_relations逐条保留理由及原身份。显示注释指纹进入产品计划，防止布局阶段偷改科研内容。旧无注释入口保持原行为。

## 可选科研逻辑拆解手册

```text
python scripts/build_research_workbook.py --model logic.json --graphs graph_exports.json --annotations display_annotations.json --output workbook.docx
```

graph_exports记录同模型各view的PPTX和实际PNG路径、SHA256及logic_snapshot；文档拒绝图或模型漂移。可选annotations只是绑定同一版本与source_ids的术语及审核显示文本，不保存第二套实验事实。正文以总图、代表性分支、Methods对照表、关系矩阵为主；完整清单及字段来源可以结构化附件引用。禁止按IMRD改写论文或重复粘贴Methods。DOCX文字和表格可编辑；嵌入图为配套原生PPT的确切导出图，图节点在PPTX中编辑。实际打开与逐页渲染必做，自动结构检查与人工体验验收分开。

`--reader`采用初学者阅读布局，rows/cards/groups只是有源文字和分页注释；cards绑定原Experiment ID和字段，分组必须恰好覆盖全部适用任务且不能重复计数。先做开篇和一组实验小样，再做完整稿；原始字段、状态与冲突仍独立随附。`--sample`仅供局部预览，不得当作完整Methods交付。
