# 2026-11-06 — v1.1.1发布文档勘误

修正README/INSTALL发布状态、Tag安装与升级指引，澄清宿主路径。只改文档，不移动v1.1.1 Tag；main和Release附件为勘误文档，Tag保留首次发布快照。

# v1.1.1 — 正式发布（2026-11-06）

基于独立验收rc.4和正式156文件封包；仅发布文档、中文首页及真实成果展示更新，功能文件不变。297项与Full继承rc.4独立证据，不冒称新封包重跑。以下为历史准备与RC记录。

# 1.1.1 — 正式版本封包（2026-11-06，待负责人批准发布）

功能与独立验收rc.4逐字节相同；仅D1–D3文档勘误、正式版本标识及能力边界披露。21套件/297项独立验收及零垫片Full为既有rc.4证据，不冒称本ZIP新回执。详见RELEASE_NOTES_v1.1.1.md。以下RC历史记录保持原文。

# 1.1.1-rc.4 — G5发布前收口候选（未发布）

- 保留G5-F acquisition/methods兼容与冲突拒绝、NOT_APPLICABLE、分页和排版定向修复；不更改科学算法、Research Logic或绘图引擎。
- P6区分番茄SlPP2C4蛋白来源、酵母Y2H、本氏烟草SLC/Co-IP与IVF3545植株读数；P14区分互作证据类型、panel级样本量及实验重复口径。案例展示/教学输入单独登记，权威科学模型snapshot不变。
- 正式回归297项：保留原295项，新增2项P6/P14真实原生正文、备注与Workbook一致性核验；最终回执及零垫片Full证据置于独立审阅目录。
- 仅供独立验收；科学终审PARTIAL。未安装、未提交、未创建Git Tag或Release。以下历史版本记录保持原文。

# 1.1.1-rc.3 — G5定向补正候选（未发布）

- 原G5首次陌生论文盲测失败记录永久保留。本候选只做已授权缺陷补正；工程测试、科研来源审核及用户视觉接受分别裁决，不代表Release Ready。
- 原生主稿正文槽接受既有`points`与`bullets`两种合法输入，并拒绝正文必填页的缺失、空条目、错误类型及冲突内容；错误包含页码和字段路径。封面、Figure与原生逻辑页继续使用各自内容合同。
- Workbook的关系解释消费兼容非空字符串或非空字符串列表；列表按可读文本连接，非法类型报告精确JSON路径，不改变科研模型、来源身份及原字段。
- 新增候选指纹工具，沿用rc.2正式聚合公式并显式指定源码根目录/ZIP包装层；检查Unicode成员名、CRC与实际SHA。VERSION及活动使用文档同步至rc.3；不覆盖历史版本说明。
- 本轮测试数量与实测结果以新的配置、源码SHA和`regression_receipt.json`为准。下列229/243项属于历史候选记录，不可冒充rc.3重跑证据。

## 1.1.1-rc.2 — G4-P1-01历史修复候选（未发布）

FREEFORM几何消费及结构化失败记录修复；历史正式门禁为14套件、243项、0 FAIL、0 SKIP。Cell旧产物仍受真实端点、独立B文字与字号合同拒绝，原裁决`FIX_PARTIAL`保留。该记录不是本轮rc.3测试结果。

# 1.1.1-rc.1 — 发布候选（未发布；正式目标版本 v1.1.1）

本条目覆盖 UniPert 历史案例回归后的四轮工程修复（Fix A/B/C1/C2），累计 **9 个既有文件修改、5 个文件新增、0 删除**。科学/Workbook/渲染引擎（15 个模块）与 7 个 Schema 与 v1.1.0 基线逐字节相同，未修改科学算法、未放宽 Schema。`VERSION` 仍为 `1.1.1-rc.1`；Git Tag `v1.1.1` **尚未创建**，仅在负责人发布授权后生成。科学终审保持 `PARTIAL`，用户视觉验收 `NOT_ASSESSED`。

### Fix A — OOXML 合稿完整性与交付写入

- 删除旧 ZIP 盲目回填逻辑，保留 python-pptx 生成的自洽 OPC 部件图；修复主稿读取时 `KeyError: rId30`（旧包内 `rId30` 指向不存在的 `slide23.xml`）。
- 主稿先写入 `.pending.pptx`，通过结构与可重新打开校验后才发布为目标文件；成功回执在全部检查完成后写出，不再出现"回执已写、产物不可读"。
- 新增 7 项 OOXML 合稿回归（`tests/test_ooxml_merge_integrity.py`），在真实案例夹具上执行。

### Fix B — 可读主稿与独立完整 B 的分工（只改展示输入）

- 撤下把完整 B 压入 16:9 的页面；主稿改用 A 概览 + `repr`/`predict`/`space` 三张同源局部视图导航，完整 15 节点 / 18 关系保留在独立大画布 B 中。
- Figure 资产按 ROI 重新登记并核验 SHA；主稿页面与模型节点、关系的对应关系写入 `page_mapping`，不新增科学连线。
- **本轮未修改任何源码、测试或 Schema**（527 文件与 Fix A 字节相同），证据以展示输入 diff 与页面映射记录。

### Fix C1 — 逻辑导航交付合同

- 新增 `references/logic_navigation_delivery.md`：规定独立 B 必须保留原尺寸与原生可编辑性，主稿局部视图须标注父 B、模型 snapshot 与展示省略，不得用整页 PNG 冒充原生网络。
- `register_logic_graphs.py` / `render_logic.py` / `project_research_logic.py`：完整 B 拓扑守恒，支持按显式 `page-map` 原生合稿并登记局部视图，缺宿主时给出可操作的 portable 替代路径。
- `delivery_contract.py` / `validate_story.py` / `run_pfs.py`：交付合同校验实际原生对象（节点文字与连接器）、局部视图从属关系与主稿完整总览，允许合法的不连通分支。
- 新增 20 项逻辑导航合同测试（`tests/test_logic_navigation_contract.py`）。

### Fix C2 — 交付闭合与正式回归门禁

- `delivery_contract.py`：对独立完整 B 的实际对象文字增加**绝对 10pt 下限**（不按 16:9 折算，不放宽主稿 10pt 门禁）；同一真实包把正文改为 7pt 后 `check-delivery --profile full` 由 exit 0 变为 exit 2（`COMPLETE_B_READABILITY_LIMIT`）。
- 新增 `scripts/run_release_regressions.py`：对既有测试 CLI 增加哈希绑定与身份核验（夹具 SHA、套件源码 SHA、`Ran` 计数、SKIP 计数、退出码），任何 SKIP 一律判失败——"全部 SKIP 但 exit 0"不再能冒充通过。
- Workbook 字段绑定：现有 M1 parameter 适配器组装 84 个教学字段 + 6 项结构化定量记录；来源补正保留原 21 个来源并新增 79 个实际 PDF 文本块精确跨度。
- 新增 12 项真实交付闭合测试与 7 项回归门禁测试。

### 发布门禁

- 正式回归：`python -B scripts/run_release_regressions.py --config <config> --outdir <新目录>`，13 套件 / **229 项 / 0 FAIL / 0 非预期 SKIP**。
- 交付验收：`run_pfs.py deliver` → `check-delivery --profile full` → `validate_story --delivery-manifest --profile full --require-B`。
- 依赖：`requirements.txt` 增加已验证的最低版本约束；`render_logic.py --check-dependencies` 返回 `missing: []`。
- 已知限制、交付包边界与宿主依赖分别见 `docs/KNOWN_LIMITATIONS.md`、`docs/DELIVERY_PACKAGE.md`、`docs/HOST_REQUIREMENTS.md`。

# 1.1.1-dev.2 — 独立验收失败项修复；未发布

- 原生逻辑图可移植后端复用既有场景与布局，支持显式主稿页码合稿；Artifact为可选，缺宿主不再阻断完整B。主稿A/B/zoom强制检查真实文字节点与连接器，整图PNG不能代替。
- 原生Workbook接入同源逐Figure八项解释、Methods六项解读及定量证据；学习模式缺深度输入会阻断，logic-only显式PARTIAL。来源哈希、科学审核边界和原有生成器保留。
- 修复wrap重复扣除10pt导致的短标签误报；保留真实高度与不可断数字宽度溢出检查。修复无局部分支Workbook的多余分页。
- Atera和叙述性Review实际生成/Office渲染及维护回归记录随独立候选交付。科学审核PARTIAL不因技术测试升级；未安装、未推送、未发布。

# 1.1.1-dev.1 — 未发布维护候选

- 登记和比对PDF区域Figure；完整处理SMask/色彩/矢量标注，原生黑底不误判；像素、panel与语义审核分离。
- B投影保留全部模型节点/关系，交付校验检查实际原生对象、局部从属与主稿完整总览；允许不连通。
- scientific_index Schema、PENDING生产者、有源组装入口、真实图形清单生产者，恢复原生Workbook路径。
- full复用共同PPT检查并恢复深层CSV；空来源、未登记Figure和未审panel不再静默放行。内部预览显式PARTIAL。
- 图卡三槽联立容量预检、长标题自适应、绕开非端点节点；无Inventory时Workbook不再误标综述、生成空表或多余空白页。
- 现有维护回归与真实Atera/Review定向验证见本次运行报告。独立科学终审、Inventory完备性与用户视觉接受仍未完成；不是正式Release。
- 不包含WorkBuddy运行中的完整临时布局补丁；未推送、未更新v1.1.0 Tag/Release或安装目录。

# CHANGELOG

## 1.1.0 — 2026-10-28

- 科研问题、Methods、Figure、结果、作者解释及限制共享来源和知识模型。
- 简要/详细多分支科研逻辑图、逐Figure故事及可编辑PPT；不将Figure编号当成实验时序。
- Research Logic Workbook DOCX与实际Word/PDF路径，图节点在配套PPTX中编辑。
- 内容锁定Visual Polish：Agent计划、原生对象编辑、独立QA/回退；科研网络折线与普通阅读竖直直线分开。
- 普通阅读箭头修复已进入正式源码；不重新引入L/U回指。
- 补全直接使用的lxml及成熟PDF入口PyMuPDF依赖；不改科研算法。
- 原创角色/确认版海报、准确README、个人非商业许可和v1.0历史归档。

## 1.0.0 — 历史补充归档

指向原公开提交cbdcb825db500a53c9bfef0c40c4b41882130735。归档创建日期不代表最初公开日期，原代码和LICENSE不变。

## 既有开发记录

# Changelog

## v1.1.0 本地候选更新 — 2026-10-27（Visual Polish；待用户视觉确认）

- 新增成品PPT独立后处理及PowerPoint实际导出，保留原稿、备注、媒体和来源；不重做科研分析。
- 默认主稿生成后调用，支持关闭及独立CLI；比较表、图文比例、图像完整性及审计备份采用来源绑定的局部计划。
- 缺失内容单独请求上游，科学PARTIAL不升级；真实图片审阅与技术校验分开。
- 合成回归和两类真实论文样页/主稿在本地验收；不包含论文资产，不发布GitHub。

## v1.1.0 候选更新 — 2026-10-26（待视觉确认）

- 在同一科研逻辑模型上添加有来源、指纹约束的展示注释；详细图与两个分支使用问题、方法、发现和意义短句及方向明确的原生箭头。科学关系身份保持不变。
- 可选科研逻辑学习手册采用可编辑实验卡、邻近教学解释、分支插页和独立Methods/来源附录；完整Inventory及字段索引另存，不删除未核事项。
- PPTX与DOCX显式设置中文微软雅黑、英文和数字Times New Roman；Windows缺失必需字体时明确失败。新增实际文件字体审计，PDF检查真实嵌入字体。
- 保留旧默认投影；修正展示改动带来的默认标签内边距回归。未重新生成既有主稿或82页历史实验卡。
- 本地技术验收与用户视觉验收分开；本候选尚未发布，用户接受状态为PENDING。

## v1.1.0 — 2026-10-25

- 从同一有源M1规划RSU、跨Figure关系与多分支开场，保留科学关系与汇报组织的身份。
- 保留原图旁具体短句/原生箭头讲述，新增报告产物选择；默认不生成详细图和大批实验卡。
- 保留可选Methods实验Inventory、数量单位/重复/统计核验、详细大画布和实验卡；缺源可部分核验，不宣传全部独立终审。
- 讲者备注改为可讲述文字，完整机器记录分离到audit JSON。
- 加入实际中英文脚本字体属性，修复小数标点换行、详细关系标签宽度和旧State quick容量不一致；成熟图片槽超过2幅时显式阻止丢图。
- PDF只有候选索引时保留科学审核门，由Codex完成语义整理后继续；用户不必手写M1。
- 保留v1.0 JSON/模板入口，三档共享来源；PPTX模板路径按实际支持范围说明。

不包含自动因果发现、跨论文证据综合或独立科研逻辑推理引擎；软件发布和文献科学终审分开。

## v1.0

基线的默认学术模板、模块化研究框架、原图旁短句与箭头、成熟JSON和模板生成入口继续保留。许可性质不变。
