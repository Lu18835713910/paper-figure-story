# v1.1 RC集成合同

当前版本为`1.1.1`，Tag与Release均已公开。工程与科学验收仍按实际回执分别判定；发布不等于任何新论文自动通过Full或科学终审。现有v1.0入口与M1/M2-A/M2-B/M2-C接口继续保留，未安装覆盖正式Skill。

## 来源与展示

`evidence_network.py`是M1的有指纹读视图，保留原节点、关系及RSU。`--narrative`加入经绑定的M2-C原句；`--figure-story`可引用既有逐panel讲述卡，不增加科学实体。数据依赖、可选方法路线、独立验证、比较、作者论证与汇报过渡必须保持不同身份。继承direct_checked不等于本次独立科学终审。

`display_guidance.py`验证显式`pfs-display-guidance-1`指导。每条短句绑定既有statement或已登记缓存的准确摘录、范围和SHA256；所有改述仍为PARTIAL。A的具体节点、分支、汇合与跨联系可由研究内容规划，通用投影不能只显示相邻关系。C逐页记录预期panel、实际资产、读图短句、术语及限制，具体panel必须由非all资产覆盖。科学关系不得因展示需要新增。

默认A触发`A_NEEDS_GUIDANCE`时，按[A容量恢复与合法输入](a_overview_recovery.md#低成本即时恢复操作单)继续：先做有源贡献审阅；只有M1和失败网络时，默认推荐既有statement绑定的`--guidance`作即时恢复，不强制额外填写跨度。已具备有效Research Logic，或需精细B/局部/Workbook时，采用显式`--research-logic`。保留所有证据，B不因A摘要容量删减。显式模型必须在默认A/B构造之前验证和采用，不得非法回退。完整操作演示为`examples/a_overview_guidance/run_agent_demo.py`，只使用自编合成输入；M1及中断交接见[M1指南](m1_authoring_guide.md)和[五阶段续跑](agent_staged_resume.md)。

`project_evidence_products.py`生成三类计划与逐句来源。`render_evidence_products.mjs`用Artifact Tool及学术模板生成原生文字、形状和连线，原图保持独立图片。B使用较大画布并保留登记边；原知识未抽取的条件和细粒度关系仍需补齐，不能因B有全部ID就宣称整篇精细语义已完成。

## 显式运行

```text
python scripts/run_pfs.py run --pdf paper.pdf --knowledge knowledge.json
  --assets figures.assets.json --cache-dir cache --metadata bibliography.json
  --outdir NEW_OUTPUT --modes quick balanced full --plan-only
```

可选：`--narrative narrative.plan.json --figure-story figure.plan.json --guidance display.guidance.json --template template.pptx`。输出目录必须是新的，禁止覆盖历史结果。首次索引使用pdfplumber；相同PDF哈希及页库存复用缓存，缓存漂移即失败。省略knowledge时退出码3，保存候选定位并停在REVIEWED_KNOWLEDGE_REQUIRED。

复杂A也可传`--research-logic research_logic.json`。先`--plan-only`核查所有档位；显式来源错误必须报错，不能静默退回默认图。已经具备模型的独立原生A/B画布可以用`project_research_logic.py`规划，再由`run_pfs.py render-products --backend portable`渲染；该能力不等于普通Figure主稿可在无宿主时全自动新生成。

真实预览去掉`--plan-only`，显式加`--development-preview --node <node.exe> --artifact-module <artifact_tool.mjs> --presentation-skill <presentations skill directory>`。未完成独立科学终审时，默认正式模式拒绝渲染。程序依赖本地Python、pdfplumber、Artifact Tool和其验证工具；PNG验收另外需要PowerPoint或相容的实际渲染器。包不捆绑这些运行时，也不捆绑论文PDF或Figure。

## 深度与验收

- quick：主图的核心比较和最小结论；影响结论强度的限制正文保留。
- balanced：默认短句讲述、必要具体读图及复杂Figure按问题分页面。详细条件、统计和术语进入备注及审核表。
- full：共享全部科学基础，增加已登记局部图，以及有源方法、论据和限制扩展页。补充页不是新RSU，也不计为另一张Figure故事完成。

自动检查包括来源指纹、网络重建、计划漂移、引用/panel、页面几何、原生对象及PPT包结构。它们不能判定科学语义完整或用户体验接受。需逐页实际渲染，分别登记编写者目视、独立审阅及用户PENDING。原图编号冲突、未核定位混杂、构象快照与机制假说应继续显示或保留在备注。确切V4/V5文件未核验时不得宣称精确复现。

只修改开发副本；不发布、不写远程、不覆盖安装版。保留失败日志，最多一次针对性视觉修复，仍有拥挤或关键自动化缺口则交付RC_PARTIAL及明确恢复项。
# Research Logic呈现质量指引

容量门不代表科研解释应缩短为固定字数。不得用“同G1”等占位、截断句子或只剩claim标题来通过LOGIC_TEXT_FIT。先复核有源文字规划，再使用既有model.layout或logic_display的布局；B可使用独立大画布和现有局部投影，局部图不冒充完整B。A使用short_text，B使用detail_text；现有logic_display的method/discovery/meaning用于B及支持的局部视图，不能假定其自动丰富A。

Agent应在投影前确认A能看清问题、主要任务的方法和发现；B保留设计、读数、观察、支持范围与限制。渲染器不得从短标签补造科研内容。节点、边及来源合同和容量检查保持有效；软件PASS、实际视觉审阅与用户接受分开记录。

宿主渲染沿用run_pfs.py render-products --backend host，并显式提供本进程可用的Node、Artifact模块及presentations工具包路径。缺少宿主时不得将普通Figure计划交给便携逻辑后端冒充成功。完整模型snapshot及已有speaker_script须传入备注；文件SHA验证不等于科学终审。


## 产品分层与实际交付阶段

A是16:9概览，以问题、探索动作、主要发现、后续探索及综合认识概括一条或多条科研主线；这些角色不是固定步骤或字段配额。B沿同源逻辑展开具体实验/分析、操作、数据与读数、结果、证据与限制，使用独立完整可缩放原生大画布。16:9局部图仅选取适合当前讲述的合法节点/关系子集，登记父B、snapshot及省略，不替代完整B。Agent选择内容及分支；PFS不从短标题自动创造科研事实或科学聚合关系。论证顺序不等于真实实验时序或因果。

现有阶段分别是：`run`（可先`--plan-only`）→必要的`render-products`→`build_research_workbook.py`或`deliver`中的有源Workbook适配→`deliver`目录/Manifest→`check-delivery`和`validate_story.py --delivery-manifest`。各阶段必须使用同一登记运行模型/来源；显式content、Workbook字段缺口、Figure资产及宿主要求仍按原合同检查，不得写成单命令Full已闭环。

旧`validate_delivery(requested_B=True)`保留其主稿B总览合同；当前Manifest验收路径不等同于启用该旧开关。独立完整B与主稿局部视图分别验收，不能以关闭校验或把完整B缩为普通页来消除差异。历史无覆盖记录的产品保持NOT_ASSESSED；结构、贡献覆盖、科学终审及视觉接受分别报告。
