# v1.1.1 maintenance：正式工具链与Agent边界

首次编写M1先读[M1字段与引用指南](m1_authoring_guide.md)；遇A默认容量门按[A恢复操作单](a_overview_recovery.md#低成本即时恢复操作单)；长任务按[五阶段保存与续跑](agent_staged_resume.md)交接。已有有效M1不重新解析全文；所有科学输入由执行Agent依据来源准备，普通用户无需编写JSON。这些指引复用下面的原有工具，不新增流水线或自动科学聚合。

本分支是未发布维护候选。不要直接修改已安装Skill。需要程序修复时创建独立维护分支；运行目录保存临时脚本和报告，不覆盖原始输入。

## 共享输入，按顺序执行

以下命令在Skill根目录执行；路径仅为运行目录占位符。Python需安装requirements.txt。**昂贵阅读/分析前**运行`python scripts/render_logic.py --check-dependencies`：原生A/B画布只需公开python-pptx、Pillow、lxml，不需Artifact Tool、presentation-skill或container_tools。缺依赖时返回非零及安装命令。实际PNG/PDF可用本机PowerPoint/Word导出；Office缺失应单独报告渲染未验证。

1. `python scripts/index_pdf.py paper.pdf --outdir RUN/_cache`。若现有缓存PDF指纹一致，直接复用。PDF索引/候选句不是科学理解或阅读证明。
2. `python scripts/scientific_index.py init --paper-index RUN/_cache/paper_index.json --output RUN/scientific_index.pending.json`。Schema位于schemas/scientific_index_v1_1.schema.json。骨架保留PENDING，不可直接用于成品。
3. **Agent语义步骤**：阅读可用正文、Methods、图注与补件；或明确继承已有阅读记录、只做本轮定向核验。填写12类facets、阅读者/范围/底稿指纹、逐条准确字符摘录及来源。建立/复用M1 knowledge；不通过PPT节点拼接反推论文事实。不把缺失补件写成原文未报告，不把文件及页码存在写成科学CHECKED。
4. `python scripts/validate_knowledge.py RUN/knowledge.json --verify-files`（以该CLI帮助中的选项为准）；通过evidence_network.py现有build入口生成network。已有run_pfs路径仍可使用。`python scripts/scientific_index.py validate --index RUN/scientific_index.json`。PENDING或空伪完成索引返回非零；CHECKED facet需要语义审阅者及支持理由。
5. **Agent有源判定**：按references/research_logic_contract.md提供logic.adjudication.json中的nodes、edges、core、branches和可选layout/method_explanations；节点引用M1实体/语句或Inventory字段，不新增第二套独立事实。边区分证据、论证、共享流程和假说；允许不连通分量，禁止为了连通新增边。
6. `python scripts/scientific_index.py assemble --index RUN/scientific_index.json --network RUN/network.json --adjudication RUN/logic.adjudication.json --output RUN/research_logic.json`。如有**已经核验**的实验清单，追加`--inventory`；没有清单时不伪造实验数量。快照由原生工具计算，禁止手填。
7. `python scripts/project_research_logic.py --network RUN/network.json --model RUN/research_logic.json --outdir RUN/plan --views A B branch1 branch2`。branch1/2必须是模型中的真实ID。B包含全部节点和关系；overview不是B，局部图也不是B。模型允许独立分支。A需在主PPT画布内显式分配可读位置；B可扩展画布。默认路由发现穿节点会使用外部通道，仍不安全时阻断，不降低字号强塞。
8. `python scripts/render_logic.py --network RUN/network.json --plan RUN/plan/products.plan.json --metadata RUN/plan/metadata.resolved.json --output-dir RUN/graphs --development-preview`生成原生A/B/分支。输出receipt在RUN/graphs/render_receipt.json。本后端消费现有逻辑图场景，不替代任意多页Figure场景渲染；每视图一个画布。主稿先按步骤11构建，再给上述命令追加`--main-pptx RUN/main.base.pptx --page-map RUN/page_map.json --main-output RUN/07_科研逻辑汇报.pptx`；page_map形如`{"A":4,"B":5,"immune":6,"clonal":7}`，只填实际规划的视图和主稿页码。按同模型场景生成原生对象，保留source/node/edge身份，不粘贴图像。render_evidence_products.mjs缺宿主参数时自动选择此可移植逻辑图后端；显式提供有效`--artifact-module`及`--presentation-skill`时仍可使用可选宿主后端。当前独立科学终审未完成，预览旗标是显式审核状态，不是发布授权。用PowerPoint导出每种图的PNG，命名main.png/detail.png/branch_ID.png；主稿图页另外命名main-slide-004.png等。
9. `python scripts/register_logic_graphs.py --model RUN/research_logic.json --plan RUN/plan/products.plan.json --receipt RUN/graphs/render_receipt.json --png-dir RUN/graph_png --output RUN/logic_graph_manifest.json`检查实际原生节点/关系、主稿页码、快照和SHA；主稿PNG不能冒充可编辑对象。Workbook复用同一科研登记，默认执行`python scripts/build_research_workbook.py --model RUN/research_logic.json --graphs RUN/logic_graph_manifest.json --annotations RUN/workbook_refs.json --output RUN/Workbook.docx`。annotations可省略；仅在角色/来源/panel需要显式选择时提供与logic_snapshot绑定的`workbook_bindings`，里面放字段ID或指针而不是另一份事实文本。已有Figure Story覆盖可提供panel；没有注册Figure/RSU或角色解释时返回exit 2及Workbook.assembly.json，当前Agent只补指定缺口，不从A/B短句逆推实验。已有`--content`继续可用；其输入哈希、来源及深度仍须验证。学习章节缺源不能退化为空壳完整手册，逻辑索引需显式`--scope logic-only`。无Inventory不伪造任务或n，合法部分Inventory保留原状态和原因。Word实际导出PDF逐页检查，程序化覆盖不代替科学独立终审。
10. **Figure准备**：Agent确认PDF物理页和选定panel边界，填写`{"regions":[{"id":"F1a","physical_page":6,"bbox_pt":[x0,y0,x1,y1],"panels":["a"],"page_cache":"..."}]}`，单位PDF点。`python scripts/figure_assets.py prepare --pdf paper.pdf --requests RUN/figure_requests.json --outdir RUN/figures --dpi 240`；再`... validate RUN/figures/figure_assets.json`。优先复用经像素比对的页面缓存，否则渲染源区域。不得单取内嵌位图忽略SMask或矢量标签。原生黑底合法，不使用全局黑像素阈值。像素匹配不等于panel/轴/比例尺/科学语义通过；人工状态单列。
11. 主稿JSON引用`figure_assets`登记文件，`enforce_preflight:true`，先`python scripts/build_pptx.py RUN/06_PPT页面数据.json --output RUN/main.base.pptx --precheck`，再正式构建基础稿并按步骤8合稿。只有已登记且像素来源匹配的原论文Figure可装载；Figure保真图片与PFS生成逻辑图原生对象分开。source_context保留scientific_figure来源。delivery_contract.products合并logic_graph_manifest的graphs与main_graphs；requested_B=true时强制主稿A/B及已声明zoom的原生拓扑。只改名字的整图PNG也会拒绝。过密总览保留独立大画布和局部图，不通过删边或关闭预检掩盖容量。wrap/measure传入内容可用宽度，边距只在文本框层扣除一次；真实高度/不可断数字宽度溢出仍阻断。
12. 实际PowerPoint打开/导出PNG，Word逐页预览；`python scripts/validate_story.py RUN --profile full --require-B`（只有用户请求B时加该选项）。full包含balanced共同结构/PPT/Figure/交付检查，外加完整文档及CSV检查。正式缺panel映射为非零。仅内部教学预览可显式追加`--development-preview`，未审panel报告PARTIAL；损坏图片/无登记/无来源/拓扑缺失不可绕过。

## 候选维护：贡献覆盖与表达审阅

这是未发布的候选审核关口，放在步骤5有源判定之前，投影之后再核对实际覆盖。两份V0.1讨论稿仍待负责人批准。复用已有事实与来源，用现有科研审核文档的一张Markdown表记录即可，不创建另一套科学数据库或JSON Schema。

|候选贡献/研究论断（引用既有ID）|作者定位及原文来源ID|实际证据ID、方法/读数|支持程度与限制|核心/支撑/背景及理由|A/B/主PPT/Figure Story/Workbook/结论实际位置|未展示理由及影响|
|---|---|---|---|---|---|---|
|填写已有claim、statement、RSU或节点身份；不得由图形补造事实|分开作者强调与审阅者判断；未核实就标待核|同一证据可支持多个贡献，保留同一身份|区分观察、计算、互补、内部分析、作者解释与缺件|任务不自动等于贡献，PARTIAL不自动等于不重要|逐项核对实际输出；未请求产品写不适用，未生成写未测试|说明是否影响理解或完整性，不能以“布局需要”隐藏重要遗漏|

审核要求：

1. 从作者目标、各Results/论点、Figure、Methods及讨论识别候选，不只看题目或最后Figure。已读底稿有效时不重复全文解析；缺原始内容只能做已有登记覆盖检查，不宣称穷尽贡献。
2. 允许一条、多条或共享证据的研究主线，不固定贡献数、分支数或技术/应用分类。只有有源关系才能进入网络；没有边也可保留独立贡献。
3. 同批数据的下采样、重新分组、统计零模型不增加独立生物学重复；邻片与区域级互补不能升级为同一细胞或所有克隆真值。
4. 核心贡献在总览与结论均缺失、方法结果被压成空泛问答、证据强度被升级或重要冲突被隐去时，记录内容缺口并阻断“贡献完整”声明。补信息回到已有有源字段，不从A/B短句逆推方法。
5. 标题已经清楚就保留；抽象表述解释成具体研究动作；首次必要缩写解释中文含义和实体类别。删去会改变设计、量纲或结论强度的参数应留在可见层，其余在备注/Workbook保留。
6. 结论按已审主要贡献组织：先明确发现，再限定支持范围；综述写作者综合与争议，不伪装为原创实验。改写前后记录“原句—候选句—来源—强度是否变化—待核项”，不开发语言评分器。
7. 来源科学审核、登记内容覆盖、软件一致性和视觉/读者验收分别记录。ID齐全、生成成功或COVERED_REGISTERED_*不代表核心贡献识别已经通过。旧冻结成果只作回归，不静默重写。

候选选择行为（仅展示接口，不改变事实合同）：

- `run_pfs run`使用的`project_products → compose_delivery`默认将所有已登记claim分成每页最多6项的总结，保留原`REPORT_summary`第一页ID。它不会自动判断哪些claim是核心。库调用可在既有delivery options传`summary_claim_ids`及`summary_omissions`（所有未选ID→具体理由）；未解释、未知或重复ID拒绝。此细粒度选择尚未新增CLI旗标；CLI仍可通过既有`--slides`选页，省略项登记在`summary_coverage`。贡献是否允许省略仍由上述审核决定。
- 普通Workbook保持旧默认展开前2个分支，超过时在正文及receipt `branch_coverage`明确标记PARTIAL。需要展开3个或更多合法分支时，在已有annotations中填`branch_selection: {view_ids: [真实分支ID…], omitted_reasons: {未选ID: 理由…}}`；每个所选图仍须有同snapshot的登记PPTX/PNG。选中多个分支会按原有逐分支章节展开，不将它们塞进一页。没有分支或1–2分支的旧调用继续有效。
- 旧`project_presentation`/`render_research`兼容入口的总结保留合并unit的全部唯一finding指针，每页最多6项并登记分页覆盖；不改变RSU或新增实体。它不是`run_pfs run`的新默认入口。
- 综述RSU `claim_ids`可因其关系是`argument_transition`而为空；当前结论消费网络claim节点，显式Research Logic也可引用原claim。不得为了填数组改关系身份。其他未来消费者需要该归属时应另行证明问题。

## 必须分开的状态

文件结构；科学模型及来源语义；Figure源像素；panel完整性；交付守恒；几何；Agent视觉；用户接受。几何PASS不能代替其他层。QA_ONLY没有Agent视觉设计计划，不能称专业视觉重设计。formal_ready不因成功打开/自动测试而升级。

图卡可选lead_height/lead_size、transition_height/transition_size、result_height/result_size是展示字段；不改变事实、节点或关系。`--precheck`只构建内存对象，不渲染。默认旧模板仍可读取；迁移到新严格来源合同所需登记不是兼容性测试的绕过项。

## Workbook字段复用约定（维护B，非新科学Schema）

- 事实保持在既有M1、RSU/card、Inventory和research_logic中。M1参数使用已登记的purpose/materials/design/readout/analysis/result/interpretation/links/counts等明确key；实体name不是实验结果。Figure与方法通过已有成员身份关联，不按标题相似、同页或数值相同合并。
- `workbook_bindings.figures[FigureID][role]`及`methods[MethodID][role]`可列network statement ID；`figure_panels`仅提供已核实的显式panel，不能用all。`method_ids`可显式选择任务，避免把同一任务的不同记录重复展示。
- M1来源只有页码时不自动升级绑定。需要人工映射时，annotations中同时登记`workbook_bindings.reviewer`及`statement_sources[statementID]=[sourceID]`，仍为PARTIAL。自动映射要求文献/页码/摘录指纹的明确身份；不会以同页代替语义核验。
- 结构化统计可沿用M1 parameter.value对象，key为quantitative_result，值保留id/label/value/meaning/metric_id/test_id/unit/population_id。数量继续用原quantities及其单位/群体，不自动把cell/ROI/section当donor。`quantitative_results`选择器仅引用`QUANT:entityID:parameterIndex`或`COUNT:entityID:quantityIndex`，可用expect核对指标/检验/单位；同值不合并。缺身份给定向任务，不能从数字反推。
- 组装保存字段→原文件SHA/指针/statement ID/来源ID映射；验证时重放同一引用并检查派生文本，修改字段或来源后不得只刷新content快照掩盖漂移。research_logic关系只按既有端点身份投影；不会新增关系。
- 旧已登记content可通过显式legacy_content文件SHA、原model文件SHA和reviewer迁移。迁移保留原Agent文字来源、未知统计身份和警告；不得当作新论文自动理解证明。
- Methods为空必须有scientific_index.facets.methods.status=NOT_APPLICABLE、真实sources及applicability：scope=original_experimental_methods、reviewer、reason、source_ids、article_type_reviewed=true、scope_reviewed=true、basis_kind=reviewed_not_applicable、actual_methods_present=false。文献类型与阅读范围要一致；缺失/未提取不适用此规则。系统综述、Meta分析或实际分析方法存在时不能省略。
- `--reader --content`及reader的logic-only组合明确报错；旧Reader的Inventory卡片调用保持不变。没有Inventory时用普通原生Workbook，不构造伪实验卡。
