---
name: paper-figure-story
description: 从科研论文PDF重构科学问题、实验或论据、实际发现及证据边界，用原始Figure和简短文字箭头链制作可编辑中文学术PPT；支持多分支总框架、综述讲述、三档深度及可选Methods和详细证据图。附带RLD诊断模块（rld_diagnose.py），可对既有PFS模型的论证单元做科研逻辑、语言逻辑、表达逻辑三维诊断，因果判定须经PFS干预与对照结构核查，未覆盖语言显式上报而非静默跳过。
---

# Paper Figure Story v1.2.0

> v1.1.1 既有 PFS 脚本及 schema 保留；新增内容仅限 RLD 诊断模块及其文档、测试与示例。
> 工程测试通过不等于科学准确性认证（`scientific_accuracy=NOT_ESTIMABLE`）。

## v1.2.0 正式科研逻辑图入口（优先于旧兼容框架）

当用户要求整篇论文的**科研逻辑框架、分支关系、A/B图或可编辑科研汇报**时，执行Agent首先必须根据原文完成Scientific Index/Methods任务和来源覆盖审阅，再建立/验证同一论文的M1、Evidence Network、显式Research Logic。之后使用`--research-logic <validated-model>`启用同源投影；要求完整B时同时使用`--products with-network`。不得将`balanced`误认为多分支开关，也不得以旧兼容的`study_map`、默认`overview()`或逐Figure线性故事代替有源A/B逻辑模型。

**科学拓扑决定展示拓扑：** 保留论文实际存在的多条研究主线、共享证据、平行任务、问题分叉、汇合与不连通分量；如果论文确实是一条主线，也须如实呈现，绝不为迎合模板虚构分叉。A显示已审核核心，B显示同模型全部已登记的节点/关系，C按Figure独立讲述。结构验证、来源复核和视觉验收分别记录；工程PASS不等于已发现论文所有核心贡献。

仅当用户明确要求兼容旧PPT JSON/`study_map`时才使用旧版展示路径，并标注它**不是完整同源A/B**。遇到`A_NEEDS_GUIDANCE`时，若当前任务要求A/B协同，优先修复有源Research Logic模型与可读布局；不得为了消除容量错误直接退回旧单线图、截断贡献或省略B。独立便携A/B成功不代表主Figure PPT的Artifact后端成功；实际生成状态逐项报告。

## Agent首次执行与中断恢复（先按需读这三页）

科研JSON由**执行Skill的Agent**依据来源构建，普通用户无需编写。开始M1前读[M1编写指南](references/m1_authoring_guide.md)：合法实体类型、全部实体必填limits、Story方法/证据身份及data_bindings，附真实校验的完整自编示例。不要通过修改Schema或伪装实体类型修复输入。

已完成M1后遇`A_NEEDS_GUIDANCE`，先保留失败目录及缓存，按[A容量恢复操作单](references/a_overview_recovery.md#低成本即时恢复操作单)选择：**已有statement足以支持概括时，默认用statement绑定的display guidance恢复A**；需要精细B、局部图及Workbook协同时，再构建显式Research Logic。两者均需Agent有源内容审阅，不是自动科学聚合。不能为容量删贡献、改并行为因果或缩字。guidance只恢复显示规划，不代表B几何、主稿、Workbook或Full已经通过。

长任务按[五阶段保存与续跑](references/agent_staged_resume.md)执行。新会话核对指纹后从最近有效阶段续跑，不重复解析全文。读真实进程退出码及execution/failure/几何报告，不以stdout中的状态或exit 0单独宣称完成。便携A/B可用不等于Figure主稿Artifact宿主可用；先单独检查宿主，再开展昂贵资产工作。

## 维护候选的标准路径与安全门

先读[受支持的PDF→模型→A/B→Figure→PPT/原生Workbook路径](references/maintenance_workflow_v1_1_1.md)。复用按SHA匹配的缓存；Agent完成科学语义，不改已安装代码。scientific_index骨架必须保持PENDING，完成来源填充并验证后才能组装research_logic。Figure必须登记原PDF/页码/panel/区域/指纹；像素匹配、panel审核与科学语义分别记录，禁止用黑像素阈值拒绝合法黑底。

用户要求完整B时，必须交付模型全部节点/关系的独立原生大画布；主稿按批准的展示范围使用概览或有从属关系的局部视图，不把完整B压缩塞入16:9；不为了连通补边。默认使用公开Python依赖的`scripts/render_logic.py`，支持按显式page-map原生合稿；不得把A/B/局部图整页PNG替换进主稿。先运行`--check-dependencies`，宿主Artifact后端仅为可选。full不弱于balanced，未登记图片或空source_context不能声称通过Figure核验。内部预览可保持PARTIAL，不能升级formal_ready。临时脚本留在运行目录，维护修复留在独立分支，不覆盖安装版。

原生学习手册由`build_research_workbook.py`复用已登记M1/RSU、Figure Story和可选Inventory；省略`--content`时确定性组装，缺字段返回`.assembly.json`定向任务及exit 2，不生成空壳完整手册。显式`--content`继续读取原格式，原有自由文本只标记为legacy输入，不冒充字段级自动绑定。已有事实只登记一次，不为Workbook另写一套科研解释；参数和来源不足时由当前Agent定向核查。仅需逻辑索引可显式`--scope logic-only`并报告PARTIAL。旧`--reader`保留Inventory/annotations路径；与`--content`组合明确拒绝，不静默忽略。合同仍为`schemas/workbook_content_v1_1.schema.json`。

## 候选维护：贡献覆盖与表达审阅（未发布）

本段是基于两份V0.1讨论稿的受控候选，不代表讨论稿已成为发布标准或既有案例科学终审升级。先按[维护流程中的贡献覆盖审阅](references/maintenance_workflow_v1_1_1.md#候选维护贡献覆盖与表达审阅)检查已登记事实，再制作展示；不新增科学事实库。

- 不把标题问题、一个中心入口或最后一张Figure等同于全文唯一贡献。用既有claim、RSU、statement、research_logic与source ID列出候选贡献，分开作者定位、实际支持、核心/支撑/背景及理由；允许一条、多条或共享证据的主线，不预设技术/应用双主线。
- 每项候选核心贡献登记A、B、主稿、Figure Story、Workbook和最终结论中的实际位置，或不适用/省略理由与影响。共享证据沿用同一身份，不因分支、页面或测量重分组而增加独立验证。
- 先清楚呈现正面发现，再准确限定支持范围；结论覆盖已审核心贡献。保留清楚的标题，解释抽象研究动作与必要缩写，关键参数分层呈现。逐句核对简化是否把推断升级为证实、关联升级为因果；Visual Polish不得代做科学修订。
- 贡献覆盖审阅、来源科学审核、软件检查、视觉验收分别报告。COVERED_REGISTERED_CLAIMS/BRANCHES只说明已登记输入的投影范围，不证明论文全部核心贡献已被识别。

## RC1候选：A/B与局部图的科研表达分工

- A为16:9科研逻辑概览：呈现一条或多条“问题—探索—发现—进一步探索—综合认识”的骨架，使读者看清主要研究任务、关键发现及其真实联系。这是表达原则，不是固定五步、固定节点数或线性实验模板。
- B在同一有源骨架下展开具体实验/分析、操作与材料、数据与读数、结果、支持证据及必要限制，保留独立、完整、原生可编辑、可缩放的大画布。不以整图缩到16:9后的字号作为唯一验收尺度。
- 主稿16:9局部图从同源B选择适合当前讲述的节点/关系，标明父B、模型snapshot及展示省略；局部图不冒充完整B。不能因一页容量删改完整B的科学关系。
- Agent依据论文判断贡献、分支数量、科学含义和展示信息层级；PFS执行既有来源、身份、证据强度及容量约束并稳定渲染。叙事/论证顺序不得自动升级为实验真实时间顺序或科学因果。

正式交付仍为多阶段：`run --plan-only`/`run`做索引、规划及有宿主时的主稿生成；`render-products`可分别渲染已规划产品；`build_research_workbook.py`消费有源事实或显式content；`deliver`复用登记的图、已有主稿及Workbook输入完成目录和Manifest；再执行`check-delivery`与`validate_story.py --delivery-manifest`。这不是已验证的单命令Full。无宿主时普通Figure主稿能力仍受限；portable逻辑渲染与已有主稿定向合稿不能替代该能力。

## 默认目标与产物选择

默认交付高质量科研PPT：文献信息、科学问题、简洁多分支开场、逐Figure故事、综合认识。原图是证据，3–5个具体短句及箭头连接对象/处理、分析、发现和认识；步数可随研究问题调整。保留关键对照、数字和影响结论强度的限制，不粘贴RSU长段落，不以残基定位线代替科研讲述。

三类产物共享M1来源：A简洁开场框架；B可选独立详细网络及实验卡/清单；C逐Figure讲述。A引用某图不等于C完成；B关系不因排版变为因果或实验历史。

`run_pfs.py run --products presentation`为默认主PPT，含封面、问题和总结；`with-network`再给独立大画布；`deep --inventory ...`才展开已有Methods清单及实验卡。缺补件或未核n不阻塞有充分来源的主稿，也不能宣称深度审计完成。`full`是正文深度，不隐式生成82页卡片。

维护入口的实际能力：`run_pfs.py render-products --network NETWORK --plan PLAN --metadata METADATA --outdir OUT --backend portable --development-preview`可直接调用现有便携原生A/B画布后端，不需要Node/Artifact宿主。安装PowerPoint时增加`--office`，会导出PNG/PDF并生成供deliver直接消费的`logic_graph_manifest.json`，无需案例专用准备脚本。该后端只支持已登记的逻辑画布；主稿/Figure场景不可把scaffold冒充成品，缺可用宿主时在PDF解析前阻断。`--backend host`仅在真实安装且接口兼容时使用，失败须报告。

已登记成果交付使用 `run_pfs.py deliver --research-logic MODEL --graphs GRAPH_MANIFEST --workbook-bindings ANNOTATIONS --outdir OUT --request A B Workbook PNG PDF --office --development-preview`；旧内容可显式用`--content`。这是已有事实/缓存回放，不是新论文自动理解。更新既有主稿另传`--main-pptx`、`--page-map`、`--plan`与`--metadata`；未登记局部视图、模型不一致或主稿节点字体不足会阻断主稿进入交付目录，不能声称Full。缓存计划哈希过期时，从已审核冻结输入重新投影到新运行目录，不能只改旧计划哈希。

交付目录`deliverables/`只包含PPT、Workbook、预览、Manifest及必要附件；运行模型和日志在同级`audit/`。Word旁的`Complete_B.editable.pptx`必须一起移动。检查使用DOCX实际关系目标和目录解析，不能只按文件名查找；独立B保留原尺寸与原生性。技术完成、科学PARTIAL和用户视觉接受状态分别报告。

`run_pfs.py check-delivery --root OUT/deliverables`复核文件哈希、请求差额与实际相对链接。`validate_story.py OUT/deliverables --delivery-manifest --logic-model MODEL --profile full --require-B`是显式的新交付结构检查（原Markdown/页面JSON校验默认不变），必须有主稿、A/B与Workbook并守恒原生拓扑；缺主稿不得通过Full，也不以此宣称独立科学终审完成。

## 用户只给PDF时，当前Codex负责闭环

用户不必编写M1 JSON。读[PDF到PPT工作流](references/pdf_to_ppt_workflow.md)，使用同一缓存完成：全文可用科学内容阅读→科学信息索引→Methods任务清单→Methods与结果映射→有源科研逻辑判定→同模型A/B与逐Figure故事→实际渲染与科学审核。不得先选主题拓扑再找证据填充。

缺knowledge的CLI返回exit3、`REVIEWED_KNOWLEDGE_REQUIRED`和`agent_handoff.json`，这是交给当前Codex的中间任务。Agent继续语义整理并用新输出目录重入，不能停下来要求用户写JSON，也不能取消来源审核门。候选句、PDF存在或页码定位不等于原文支持。CLI不自行调用远程模型；科研理解由使用此Skill的Codex执行。

综述区分叙述性综述、系统综述及Meta分析。围绕研究路线、文献证据、争议、综合解释与未来问题组织；引述实验不是综述作者新实验。没有检索流程/纳入数/合并效应的来源时不补造。文章论证顺序不等于实验历史。

## 展示、来源与有限审核

必要缩写首次解释实体类别：例如CNNM4膜蛋白、HEK293T细胞系、KRR突变体。文字、框和箭头原生可编辑，原始Figure可替换，禁止重绘实验数据。中文Microsoft YaHei，英文/数字Times New Roman，实际检查PPTX属性。

备注必须是科研人员可讲述的问题、对象/术语、方法/对照、结果、边界与短来源。完整ID、Figure/panel、Methods、指纹、语句身份和冲突保存在独立`audit/*.json`、`source_review.json/md`，不向备注粘贴大型JSON。源头事实、作者解释及presentation连接分别保存。

quick/balanced/full复用同一事实、RSU、关系和图片索引；quick压缩展开，balanced为默认，full增加有源方法/限制和必要局部图。复杂主图按问题拆页，不能为了三档差异删核心数字。三档可能页数相同，不声称每篇都固定页数。只重渲染实际修改页；每类视觉故障最多两次定向修正，仍失败则记录并停止正式通过。

默认16:9学术蓝#174994、无Logo模板。新入口支持PFS兼容16:9 PPTX；普通PPTX先inspect_template，再用成熟build_pptx.py的native/tagged路径。不能承诺任意母版像素级复刻。旧成熟Figure版式最多2幅原图，更多须拆页，禁止静默丢图。详[安装与使用](INSTALL.md)。

深度整理使用[实验层合同](references/experiment_inventory_contract.md)，不删除现有模块。稳定Experiment ID按研究/分析任务登记，任务数不等于独立生物实验次数。n、生物/技术重复、独立测量、粒子、数据集分单位；未获材料为NOT_VERIFIED，实际查完整原文仍无报告才用NOT_REPORTED。VERIFIED字段不等于独立科学终审；PARTIAL可显式生成待审核材料，保留formal_ready=false，不伪造USER_ACCEPTED。

以下成熟版式规范及JSON/CLI兼容路径继续可用；不是要求每次加载全部参考。

## 一、核心目标（不可简化）

把论文的**科学问题→样本与实验设计→观察结果→证据解释→进一步研究**重建成能讲清楚的学术报告。研究对象、实验分组、实际读数、对照及主要结论必须忠实于PDF正文、Methods、Figure legends和必要补充材料。不得用泛泛的技术词汇代替具体科学问题，不得凭借摘要编造实验，不得把空间共定位或统计关联升级为分子因果。

始终区分两种页面：
- **全文联合总框架页**：研究对象/样本/分组/时间→核心实验以及它们要回答的问题→独立核验或机制验证→整篇论文的总体发现。采用多模块与必要的分支汇合，参考 `references/overall_framework_policy.md` 中的模块化框架规则，**不是 Figure 的线性故事链**。
- **逐Figure讲述页**：论文原图或关键panel在左，右侧使用**原文证据提炼的、可编辑的文字及箭头**解释“为什么做→如何做→发现什么→继续追问什么”。图是证据，文字链是讲述主线。独立研究支线标记为并行，不能强行连成因果链。

## 二、默认模式：`balanced`（节约资源，不牺牲核心科研逻辑）

**未指定模式时一律为 balanced。** 另外接受 `quick`、`full`。三种模式的事实核查底线完全相同，区别在于展开页数、补图覆盖、文档详略与视觉迭代量。

| 模式 | 场景 | 默认篇幅 | 逐图与补图范围 | 交付 |
| --- | --- | --- | --- | --- |
| `quick` | 快速组会/初稿 | 按核心问题展开，不设固定页数 | 各主Figure至少覆盖一次；只有关键验证才用补图 | 逻辑证据表、JSON、PPTX、简要质检 |
| **`balanced`** | **日常科研文献汇报（默认）** | **按科研任务与可读性展开，不设固定页数** | **每主Figure一般1–2页，复杂核心机制/独立验证可3页；补图仅在会改变结论时纳入** | **逻辑证据表、JSON、PPTX、简要质检** |
| `full` | 深度精读/方法审计 | 页数按证据需要 | 主图及重要补图详细到panel，较完整的分析文档 | 完整分析材料与详细审计 |

**篇幅不是硬上限。** 不得为了凑页数丢掉主要实验、改变关键证据边界或把不同生物学结论混在同一页。如果论文确实复杂，应先报告计划页数及增加理由，不做无意义拆页。

**单页拆分原则**：以“一项可以独立讲述的科学问题/证据转折”为单位，不以panel数量为单位。不因Fig 2有a–j就机械生成4–10页；能在一页讲清楚且原图可读时整合为一页。Fig 1通常是样本与数据资源概况，可在一页完成；每个主Figure默认先尝试一页，再视需要拆分。补充图默认放入对应主图的证据记录，只有必要时独立成页。

## 三、有限轮次工作流：单次证据抽取 → 一次故事编排 → 程序化PPT → 定点质检

### 0. 输入与PDF索引（由本地程序完成，避免重复全文输入模型）

1. 定位主论文PDF、补充材料、用户指定的PPT/PPTX模板。参考PPT不等于用户指定模板；明确上传模板优先于默认模板。
2. 运行 `python scripts/index_pdf.py 主论文.pdf --outdir 工作目录/_cache`。这只生成PDF逐页文本与Figure候选页索引，**不等于内容核查**。如缓存与文件SHA256匹配则直接复用。
3. 原创研究先完整读取当前可用的Abstract、Introduction、Results、Discussion、Materials and Methods / STAR Methods、主图图注及可用补充Methods和说明；quick/balanced也须完成科学结构阅读与Methods任务识别，再识别关系。复用缓存和已读记录，不重复解析；缺补件登记为未获，不写成原文未报告。深度整理再追溯全部适用字段的参数、重复、统计与冲突。
4. **每张主Figure图片至少查看一次**，核对坐标、颜色、panel与正文解读。只为将进入PPT的panel提取高清裁剪；不要在反复推敲句子时反复截图、重做裁剪。

### 1. 先建立一个权威“科研证据表”，后续复用

先完成12类[科学索引和科研逻辑合同](references/research_logic_contract.md)：背景缺口、中心问题、假说、任务、目的、材料、分组对照、处理、检测分析、实际结果、作者解释、限制。Methods清单记录任务类别、全部已知字段和来源，建立Methods—Results—Figure—Conclusion双向引用。只有Methods而无结果时保留方法任务；未核完整Methods的结果标为PARTIAL。

在此之后判断递进、问题分叉、并行、互补、汇合、共享流程与假说；记录方向、理由、来源及其他解释。论文顺序、论证顺序和真实执行时间分开。共享制备不重复计为独立验证；实验/控制/计算/共享任务总数不等于独立实验数。每项Methods同时保留完整结构记录及有源的“为什么做—怎样比较—读数—结果—认识—限制”六角色简释。

一次生成每个关键实验的：`Figure/panel`、来源页码、问题来源、样本/对照/处理/n、方法及其读数、主要直接结果、最小可支持结论、证据级别、下一项问题、与其他实验的关系。区分 `paper`（原文明示）和 `presentation`（汇报组织关系）。跨Figure相同的样本及方法不重复长篇解释，可引用前面的设计条目。

默认存为 `01_科研逻辑与逐Figure证据.md`。**这一份是内容事实的单一基准**：排版和撰稿阶段优先读取它，只有发现疑点才回到PDF原文定位复查。不要分别用模型从头创作5份重复的大型Markdown，再相互对照。

### 2. 将同一证据表转化为两层PPT内容

新科研逻辑入口使用`research_logic.py`验证来源与已有M1/Inventory引用，`project_research_logic.py`从同一逻辑模型投影A简图、B详细展开及分支图；B必须能压缩回A的核心节点和边。允许有依据的递进，不默认固定数量并行模块。`run_pfs.py run --research-logic ...`显式采用该模型，旧默认CLI/校验行为保留。C的逐Figure覆盖独立验收，不能用总图引用冒充完成。

**A容量与恢复（`A_NEEDS_GUIDANCE`）：**默认A按源图布局分秩、至多6列，任一列超过6个节点会停止；这不是“论文最多6项贡献”或必须删图。贡献识别、A范围选择和来源绑定应在本步骤投影前由当前Agent完成。M1已有效、只需解除A默认容量门时，先用有源`--guidance`（现有statement绑定足够时不要求另建精确跨度）。需要明确的同模型A/B/局部/Workbook协同时使用显式`research_logic.json`，先验证科学索引及模型，再传`--research-logic`重入。显式模型必须与本次网络身份匹配且不能非法回退。两条操作、适用边界和可执行命令见下方reference。不得用数组截断、删贡献、改关系或缩小字号绕过容量。

遇门禁后保留原失败目录，复用`--cache-dir`、填妥规划，再用**新的`--outdir`**重入。合法字段、精确缓存跨度计算、可直接运行的独立合成示例及M1合法写法见[A总览容量恢复](references/a_overview_recovery.md)。不要让用户反推校验器或编写科研JSON；这些登记由执行Skill的Agent完成。`--plan-only`成功仅证明规划继续，主稿/Figure的真实渲染仍须通过既有宿主/依赖检查。

可选深度产物[科研逻辑拆解手册](references/research_logic_contract.md#可选科研逻辑拆解手册)由`build_research_workbook.py`生成DOCX：总图、分支图、设计对照表、关系矩阵、完整Methods结构引用和来源索引。嵌入同模型PPT的实际导出PNG，不另外手工构建逻辑图；文档文字/表可编辑，图中节点在配套PPTX编辑。禁止IMRD文章改写。必须实际打开、渲染并逐页检查。

初学者手册优先`--reader`：三分钟认识对象/缺口/发现/边界→问题为何逐层深入→分支图及相邻实验卡→证据互补→Methods附录。必要教学解释紧贴读数。主体不放长hash、M1/RSU身份、JSON路径、字符偏移或重复机器状态；附录及审计完整保留。复杂图用可读的大插页，不缩小全部文字。以实际Word/PDF检查清除空白页和孤立说明。

逻辑图可使用绑定原模型SHA的`logic_display`显示注释，仅改节点短句、布局和动词标签，不可覆写科学身份、端点或隐藏核心关系。B和分支按身份使用蓝实箭头（证据）、蓝虚箭头（论证推进）、棕虚箭头（解释/假说），共用技术用灰细线或集中说明；辅助关系改变呈现方式时须在审计逐条登记，不能删除原关系。实际导出PNG核对箭头和可读性，不以数量指标代替视觉审阅。

正式生成对象必须检查PPT拉丁/东亚、DOCX ASCII/HAnsi/EastAsia及PDF实际字体；中文Microsoft YaHei，英文/数字Times New Roman，缺字体报错。原始Figure中的字体不改。可用`audit_script_fonts.py`保存实际检查结果。未经用户明确确认保持USER_ACCEPTANCE=PENDING。

- **总框架**：把对象、实际分组/时间、并行组学任务、补充验证和总发现写入 `kind=framework` 的 `study_map`；证据支持的关系用实线，讲述性重排标记为虚线。并非所有图谱型研究都有干预验证，不要编造。
- **Figure页**：根据研究问题选择关键panel，并将本图证据提炼为 `story_steps`，每步是**具体操作/发现/解释**而非空泛标题。默认3–5步即可讲清楚；2–7步按需扩展。不要求所有步骤都重复完整的“问题/方法/结果/下一步”五标签。
- **图组整合**：将同一科研问题下可以看清的连续panel或补图证据放在同一页；根据证据关系而不是Figure字母机械拆页。标题优先使用有证据支撑的结论式表达。
- **页数预算**：在开始截取几十个panel或逐页编写文案前，先输出简短“页码—科学问题—图源”计划，并检查覆盖全部主Figure及主要验证实验。

生成 `06_PPT页面数据.json`，它是PPT**唯一事实输入**。如内容已通过审核，不允许排版阶段改写数字、方法或机制结论。

### 3. 模板与生成（尽量使用确定性的代码）

- 用户指定模板：`scripts/inspect_template.py` 一次读取并匹配；优先保留其比例、布局、字体、配色和Logo。不为同一文件重复做模板分析。
- 默认模板：`assets/default_academic_blue_174994.pptx`，16:9，HEX `#174994`，白/浅灰白背景，**无Logo**，学术会议风。
- 使用 `scripts/build_pptx.py` 将审定JSON生成可编辑PPTX。原始Figure是独立图片，标题、正文、故事步骤、箭头、总图框架均为可编辑对象。
- 允许一次代码生成所有页面，禁止无原因针对每张页面反复进行大模型设计。需要排版修改时先修生成器的通用布局参数，不重复分析原论文。

### 4. 质量审核（集中批量检查，疑点定点复核）

普通阅读引导与科研逻辑连接线分开：Figure讲述顺序用模块留白中的原生竖直向下直线箭头，同页同轴/线宽/颜色/尖端；禁止L/U形回指，空间不足先调整既有文字间距，不缩字或绕弯。科研节点关系仍允许按拓扑正交走线，保留source/target/方向/类型；并列解释不自动加阅读箭头。规则及检查见[Visual Polish](references/visual_polish.md)。


成品主PPT生成后使用独立[Visual Polish](references/visual_polish.md)。先锁定逐页正文/备注、页序、Figure及panel归属、节点/边、隐藏状态与来源；Agent依据真实PNG制定整页视觉设计，再由Builder执行并独立QA。只决定已有内容如何展示，不改写故事、补页、换图或引用上游新内容；不足只报告`UPSTREAM_CONTENT_ISSUE`。无Agent设计计划仅QA。`run_pfs.py run`默认接入，旧入口可接着独立调用；原稿、媒体、PARTIAL及重要限制保留，失败页可回退。程序通过不等于视觉成功或用户认可。

1. 用 `scripts/audit_pptx.py` 对PPTX进行程序检查。
2. 一次批量渲染全部页面为图片，并制作联系表；重点查看总框架、最密集的结果页和统计字小的panel。
3. **只修发现的问题页**，避免无依据地多轮全部重做；对修改页重新渲染。
4. 科研内容审核优先核查：样本/对照/时间/n/分母/统计、Figure源图、重要机制声明、独立验证、结论边界。不要因节省资源跳过这些。
5. 没有发现问题就结束，不为“继续优化”无限迭代。程序审计通过不等于科学事实自动核实。

## 四、交付与结构

`balanced` / `quick` 默认交付以下文件：
- `01_科研逻辑与逐Figure证据.md`：包含整篇故事、研究框架、关键panel实验设计与溯源，避免重复的五份长文档。
- `06_PPT页面数据.json`：所有PPT文案、总框架、Figure图路径与可追溯证据索引。
- `07_科研逻辑汇报.pptx`：可编辑成品；明确要求生成PPT时**必须交付**。
- `08_简明质检.md`：总页数、主Figure覆盖、关键验证、模板来源、科学疑点、文字溢出或图像问题。

只有用户明确要求 `full` 或要求完整逐图方法审计时，按 `references/full_mode_policy.md` 生成五份详细文档、CSV、JSON、PPTX及质检文件。`quick`和`balanced`并不意味着允许遗漏证据、编造关系或省略制作PPTX。

没有要求PPT时仅整理科研逻辑，不启动昂贵的Figure高清裁剪、PPT渲染与全面版式检查。

## 五、科学判断原则（所有模式适用）

- 逐图核对 Results/legend/必要的Methods，每个数值要知道样本、分母与比较对象。未报告标记为`未报告/待核实`。
- 主Figure不是实验实际发生顺序；平行研究支线、验证和叙事转折标记准确。
- 仅在作者明确给出依据时使用因果语言；推断CNV和直接WGS、预测细胞组成和IF验证、空间邻近与细胞通讯不可混同。
- 用户最初参考PPT的特色是**总框架中技术对应问题与验证**，以及**每张原图旁由作者自己归纳的箭头文字链**；绝不让图片取代讲述。
- 图像保持轴、比例尺、图例和panel字母，不虚构统计值；图中小字无法辨识时应分图/放大，而不是强行塞入一页。
- 论文中的结果不应写成“我们发现”，除非用户明确是原作者。

## 参考文档索引（按需读取，不必全量加载）

**入口与流程**
- [M1编写指南](references/m1_authoring_guide.md)：合法实体类型、必填limits、Story身份与data_bindings。
- [A容量恢复操作单](references/a_overview_recovery.md)：`A_NEEDS_GUIDANCE`的两种恢复路径。
- [五阶段保存与续跑](references/agent_staged_resume.md)：中断后核对指纹续跑。
- [受支持的维护路径](references/maintenance_workflow_v1_1_1.md)：PDF→模型→A/B→Figure→PPT/Workbook，含贡献覆盖与表达审阅。
- [PDF到PPT工作流](references/pdf_to_ppt_workflow.md)：只给PDF时的完整闭环。
- [RC集成合同](references/rc_integration_contract.md)：候选身份、入口与不可声称事项。

**合同与Schema**
- [科研逻辑与科学索引合同](references/research_logic_contract.md)：12类字段与手册入口。
- [证据规则](references/evidence_rules.md)：来源、强度与不可混同的推断类型。
- [知识模型](references/knowledge_model.md)及[投影合同](references/knowledge_projection_contract.md)。
- [实验层合同](references/experiment_inventory_contract.md)：任务、重复、n与单位。
- [逻辑导航交付合同](references/logic_navigation_delivery.md)：独立B原尺寸门禁、主稿局部视图从属、私有夹具正式回归用法。**涉及完整B与局部图时必须读。**
- [全文总框架策略](references/overall_framework_policy.md)、[逐图注释故事策略](references/annotation_story_policy.md)、[Figure模板](references/figure_template.md)、[模板策略](references/template_policy.md)、[PPT蓝图](references/ppt_blueprint.md)、[full模式策略](references/full_mode_policy.md)。
- `references/experiment_matrix_header.csv`：Methods矩阵表头。

**展示与验收**
- [讲述投影](references/presentation_projection.md)：知识模型→讲述片段→可编辑PPT，不替代成熟页面JSON流程。
- [Visual Polish](references/visual_polish.md)：内容锁定、原生对象、阅读直线与回退。
- [测试与验收边界](TESTING.md)：正式门禁是`scripts/run_release_regressions.py`（21套件/297项，0 FAIL、0 SKIP，以实际正式配置及regression_receipt.json为准），不是`unittest discover`。
- [已知限制](docs/KNOWN_LIMITATIONS.md)：8项P2、字号/版面边界、科学审核边界。
- [交付包合同](docs/DELIVERY_PACKAGE.md)：交付数量由请求与适用性决定；49项受管交付及157项附加包仅为历史UniPert案例数量。
- [宿主依赖与能力边界](docs/HOST_REQUIREMENTS.md)：portable、Artifact宿主、从零主稿三档能力与预检。

**规则**：按需读取，不应无论任务大小都把全部参考文件加载一遍；先读与当前任务直接相关的合同，遇到具体失败再定位对应文档。

## 六、完成条件

用户能讲清楚“研究为什么做、用什么实验、如何支持发现、为什么进一步研究”，总框架和逐图逻辑用途清晰且可靠，PPT可编辑、可阅读并标注原文图源。默认优先交付**完整、精炼而非冗长**的学术报告。禁止为了省时间而跳过研究事实核查。


v1.1保留的的知识模型→讲述片段→可编辑PPT入口，按需读取 [presentation_projection.md](references/presentation_projection.md)；该入口不替代上述成熟页面JSON与构建流程，验收边界以独立规则及实际测试报告为准。


## RLD 真实模型交接

使用同一论文的 Scientific Index、Evidence Network 和 Research Logic。保留原文及其引用路径。使用随包正式 PFS 验证器，无法补足独立语义审阅时保留 PARTIAL。

```text
python scripts/rld_units.py --index index.json --network network.json --logic logic.json --out argument_units.json
python scripts/rld_diagnose.py --index index.json --network network.json --logic logic.json --out diagnostics.json
```

第二条命令自动派生论证单元。Agent 检查缺失字段和 source_statement_ids，回查原页及实验对照，记录待确认的前提与限制。逻辑标签不得冒充原文。归因候选需人工核对，尤其是已有干预与当前断言的关联。科研准确性 NOT_ESTIMABLE。

数值核验使用 rld_numeric.py --claims claims.json --registry registry.json --manifest manifest.json --manifest-anchor SHA256 --out numeric.json。规格见 references/rld_diagnosis_contract.md。外部锚点须来自独立冻结记录，同次生成的 manifest 与摘要不建立可信来源。判定仅适用于报告的均值；不认证统计显著性、机制或因果。原论文和私人数据不分发。
