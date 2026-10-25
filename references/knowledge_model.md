# Knowledge 1.1：M1 数据合同与校验边界

状态：M1冻结数据合同，M2-A规划器继续复用；不是已发布 Skill。入口为 `schemas/knowledge_v1_1.schema.json` 与 `scripts/validate_knowledge.py`，与现有 PPT JSON 分开。`SKILL.md`、README、旧脚本、默认模板及 quick/balanced/full 均保持原文件内容。

## 调用

在 `02_v1.1_dev` 下执行（Python 3.10+；M1 新校验器仅使用标准库）：

```powershell
python -B paper-figure-story/scripts/validate_knowledge.py development/tests/fixtures/state.valid.json --verify-files --json
python -B paper-figure-story/scripts/validate_knowledge.py development/tests/fixtures/als.valid.json --verify-files --report development/results/als_validation.json
python -B -m unittest discover -s development/tests -p 'test_*.py' -v
```

退出码：0=结构与语义约束有效（可含警告），1=模型被拒绝，2=文件/JSON/schema读取失败。`--verify-files`核对已提供来源文件的真实 SHA256；它不核验引文是否支持科研主张。相对来源路径以模型 JSON 所在目录为基准。JSON重名键、NaN和Infinity拒绝。

## 一个模型中的实体与引用

- `document_registry`：来源ID、角色、格式、版本、位置、可用性和哈希。已提供文件必须有真实路径和64位SHA256；未提供原文使用 `sha256:null / hash_status:unavailable / availability:not_provided`，不得伪造PDF哈希。指定 `physical_page_count` 仅表示注册资料声明的页数，不证明已读取原件。
- `source_refs`：注册文档ID、具体页/节/段/图定位、核查状态。PDF物理页不混用为DOCX页码。`secondary_only` 必须同时给出真实二次资料的 `via_document_id` 和 `via_locator`；`direct_checked` 不能指向未提供原件。`paper_reported` 表示该条内容被归于论文报告，**不表示本轮已经直接核实**；直接核查状态由来源对象单独记录。
- `entities`：10种节点类型：dataset、sample_or_subject、intervention、assay、processing、model、evaluation、evidence、claim及通用method（以schema枚举为准）。每个节点具有全局唯一ID、来源角色、输入输出、分析单位、参数和限制。输入输出仅引用已有dataset/sample实体。复杂多层方法可用一个主要 `analysis_unit`，具体样本量仍逐项保存其独立单位。
- `parameters`：reported 必须有实际值；not_reported、not_checked、not_applicable 必须用null并有来源。未核查不能冒充原文未报告。字符串“未报告”不能包装成reported值。一个节点中参数key唯一。
- `quantities`：数值、单位、population_id、source_role均明确；外部参考图谱计数不能改称本文病例。donor/library/section/cell/nucleus/spot/ROI保留各自含义。只有显式 `quantity_operations` 中同单位、同来源角色、同population的已报告计数才允许相减/串行筛选；不从自然语言句子自动推断算术。
- `figures`：已注册主图、补图、文本提及或外部数据图的定位。此阶段不实现图注检索/主图误报修复，只保证新模型能够区分类型。
- `stories`：问题、证据ID、方法ID、Figure引用、结论/论点、限制、来源、原文顺序、汇报顺序和重组原因。证据必须指向evidence节点，方法指向实际method/assay/processing/model/evaluation节点。允许一个RSU多图、同图多RSU、同方法多RSU，也允许无Figure、无方法的概念故事；不要求“一个Figure等于一页”。

所有参数和故事必须有来源。归于原文明示的节点/关系必须有来源。ID跨文档、节点、图、故事、关系、组与约束全局唯一；不接受缺失端点。

## 关系语义

方向约定统一为：`from`是数据提供方/前一步/支持方，`to`是消费方/后一步/被支持主张。英文 `data_depends_on` 的字面方向容易混淆，因此应依此约定读取，不作反向解释。

| type | 必要约束 |
| --- | --- |
| data_depends_on | 必须给出data_bindings，生产端输出与消费端输入引用同一数据实体。外部资料进入本文方法时标为reference用途。 |
| experimental_precedes | 必须有明确protocol顺序说明及独立source_refs；Figure/Results顺序不能替代。 |
| parallel_branch | 关联parallel_evidence组，端点为其成员，不能标mandatory，也不承载data_bindings。 |
| optional_path | 关联alternative_routes组，不能标mandatory，表示可选路线。 |
| independent_validation | 说明独立性、证据强度与限制，不能借此制造数据输入。 |
| evidence_supports | 指向claim，说明证据强度与边界。causal_validation还需引用已报告intervention。 |
| compares | 横向比较，无必然时间方向，mandatory=false。 |
| argument_transition | 区分paper与presentation；汇报重排只能用presentation_only，不宣称实验事实。 |
| integrates | 多证据汇合，明确强度与限制，不自动产生因果含义。 |

无来源推断可记为inferred_needs_review且mandatory=false。只有已报告数据依赖/实验先后可设mandatory；这些强制关系必须无环。比较和可选路径不参与此DAG检查。

`relation_constraints` 是**有来源的模型数据**，不是校验器中的论文白名单。M1支持forbid_relation规则：指定端点、禁止类型、是否仅禁止强制边、理由与来源。它用于保存已人工核查的“不应建立此依赖”知识；校验器不能从一段未读论文自动发现所有禁止关系。State与ALS禁则仅出现在非发布fixture，脚本中没有论文名称或专用节点ID。独立改名测试确保同类约束不依赖标签名称。

## M1 测试资料的真实范围

`development/reference_tests` 是原始测试资料的独立副本；`development/tests/fixtures` 是为本轮合同整理的人工小样例，均位于Skill发布根目录之外。没有新增任何论文原图。

- State：保持SE预训练与表达空间ST的可选关系；潜空间ST有显式嵌入输入。含5个候选RSU和Fig1–5锚点。
- ALS：保留Visium/Splotch、multiome与COMET/HALO并行、外部图谱reference用途及donor/cell/library等单位。含5个候选RSU和Fig1–7锚点。
- 4个负fixture分别注入强制SE依赖、Splotch→COMET数据边、Splotch→COMET实验顺序、外部donor→本研究cell筛选。另一正fixture用显式合成字段演示not_reported合同，不声称论文存在该参数缺项。

原项目提供的是人工报告与concept-v0.1 JSON，本轮指定项目内未找到两篇原PDF。页码及参数保留二次来源身份；新样例通过只证明数据结构、已声明关系与来源文件哈希一致，**不证明自动抽取、原文准确率、全文Methods覆盖率或科学关系穷尽**。

## Schema 与运行时的职责

Schema使用Draft 2020-12可表达的结构约束；跨ID、来源角色、I/O匹配、统计单位、论文关系禁则和多对多引用由Python语义校验补足。当前环境没有jsonschema/fastjsonschema，校验器内置**仅覆盖此合同所用关键词的严格子集执行器**，可离线运行；它遇到未知schema关键词会失败，不会静默跳过，也不宣称是通用JSON Schema实现。未在本轮用外部完整Draft验证器做一致性认证。

仍需人工判断：来源是否真正支持某条关系、same donor是否独立重复、原文未报告判定、模型边界是否过强。若来源或禁则本身错误，结构校验无法代替专家阅读。M2-A的实际规划API、两种结构化输出及三挡位展开规则见 `knowledge_projection_contract.md` 第8节；本M1 schema/validator不变。原PDF自动抽取/自动科学问题切分、PPT投影及新渲染、SVG导出和Word读取均未因此实现。
