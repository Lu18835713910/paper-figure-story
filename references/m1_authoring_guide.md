# Agent编写M1：字段、身份与最小校验

由**执行本Skill的Agent**依据论文、图注、Methods和可用补件构建M1；普通科研用户不需要手工编写JSON。CLI不自动完成科研理解。先复用已阅读的缓存与证据表，不为填写模型重新解析全文。

本页以`schemas/knowledge_v1_1.schema.json`及`scripts/validate_knowledge.py`为准。文件校验≠原文语义核实；通过校验不把`pending`升级为`direct_checked`。

## 1. 实体类型：先判科学身份，再填写字段

|合法kind|用途|易混点|
|---|---|---|
|dataset|数据集或实际数据产物|不是分析方法|
|sample_or_subject|样本、材料或研究对象|无`sample`这个枚举；细胞、切片与患者分开|
|intervention|实际干预、处理|不是检测方法，也不是claim|
|method|研究方法|解释方法测什么，不用方法名冒充结果|
|assay|检测或测量实验|实际观察另记evidence|
|processing|数据处理过程|`analysis`不是M1合法kind；视含义选择处理、模型或评价，不能机械改名|
|model|计算/理论模型|模型预测不是直接实验观察|
|evaluation|性能或可靠性评价|评价设计与评价结果分开|
|evidence|实际读数、观察或分析证据|不是对结果的解释|
|claim|科学主张、论断或解释|不得为了进入story.evidence_ids伪装为evidence|

Research Logic节点可有自己的`kind`，不能据此扩展M1枚举。

## 2. 必填与条件必填

顶层必须包含：`schema_version="1.1"`、`model_status`、`description`、`document_registry`、`paper_type`、`entities`、`relations`、`figures`、`stories`、`relation_groups`、`relation_constraints`、`quantity_operations`。不适用集合使用合同允许的空数组，不省略键；不增添任意字段。

`model_status`合法值为manual_fixture/curated/extracted_unreviewed；真实登记按实际审核状态选取，不把extracted_unreviewed仅改名为curated。paper_type.label可为original_research/methods_or_model/resource_atlas/review/perspective/editorial_or_voices/correction/unknown；confidence为high/medium/low，classification_origin为manual/suggested/manual_override，basis是有源source_ref数组。unknown可作为登记状态，但不是满足Research Logic完整分析的证明。

- 每个entity均需：`id/kind/name/source_role/inputs/outputs/parameters/quantities/source_refs/reporting_status/analysis_unit/limits`。**limits不是只有claim/processing必填，而是全部实体必填；实体limits允许[]**。已知限制应如实写出，缺信息记待核，不能为了校验编造限制。story、relation_group的limits必须非空；支持类关系也要求非空limits。
- `source_role`为`primary_study/external_reference/conceptual`。`reporting_status`为`paper_reported/inferred_needs_review/presentation_only`。paper_reported及所有claim需有来源。不可把未查补件写成paper_reported。
- `analysis_unit`使用合同枚举（donor/library/section/cell/nucleus/spot/ROI/cell_set/gene/model/dataset/not_applicable/not_reported）；后两者必须给`unit_note`。不要猜测生物学重复单位。
- `inputs/outputs`只引用**已登记dataset或sample_or_subject的实体ID**，不是自由文本、方法ID或文件路径。
- parameters每项需`key/value/status/unit/source_refs`。`status=reported`有实际值；`not_checked/not_reported/not_applicable`的value必须为null。`not_checked`与“论文未报告”不同。
- quantities除上述信息还需`population_id/source_role`；unit必须是明确统计单位，群体ID必须存在且来源角色不变。不要把参数数值不加区分地写成样本量。
- 文献记录需`id/role/format/title/version/availability/sha256/hash_status/source_locator`；available另需实际path及verified SHA，PDF建议登记真实`physical_page_count`。not_provided需null SHA和unavailable，不能direct_checked。
- source_ref需`document_id/locator/verification`。locator至少有physical_page/section/paragraph/figure之一；PDF物理页从1开始。context或context_sha256可加强定位，**不能单独替代定位，也不能证明语义**。secondary_only另需可追溯设计参考及via_locator。
- `paper_type`按现有字段填写label/confidence/basis/classification_origin。不是根据标题猜文章类型。

## 3. Story、Figure与关系

story必需：`id/question_or_purpose/evidence_ids/method_ids/figure_refs/finding_or_argument/limits/source_refs/presentation_order/original_section_order/restructuring_reason/author_explicit_or_presentation`。

- `method_ids`仅接受method、assay、processing、model、evaluation；dataset/intervention不合法。保留干预实体，用有源方法记录说明处理和对照，不给干预换类型。
- `evidence_ids`只接受evidence。没有适用观察时可以[]，不是必须给概念综述造实验。claim保持claim；有真实观察时E→C的evidence_supports登记支持强度及限制。
- 两个数组均允许[]，但字段不能缺；“合法空数组”不代表逐Figure教学内容已充分。Figure/story引用必须存在，presentation_order不能重复。
- Figure字段是`id/document_id/label/kind/source_refs`，不是title。M1 Figure声明不是图片资产及panel审核。
- ID在文献、实体、Figure、story、关系等登记集合中全局唯一，引用的是ID，不是name。

关系通用必填：`id/from/to/type/provenance/source_refs/certainty/mandatory/rationale`。支持类型及额外要求：

|type|条件与用途|
|---|---|
|data_depends_on|真实数据输入，必须有data_bindings；见下例|
|experimental_precedes|真实实验先后，需有源order_basis、paper_reported，不能据论文顺序推定|
|parallel_branch/optional_path|需group_id，分别指向parallel_evidence/alternative_routes组，端点属于成员|
|evidence_supports|目标为claim，需support_strength及非空limits|
|independent_validation|需support_strength、limits及independence_basis；重分析不自动独立|
|integrates|需support_strength及非空limits；不创造新独立实验|
|compares|比较关系；不暗示必经流程|
|argument_transition|原文论证或汇报过渡，保留对应身份，不升级为实验支持|

只有data_depends_on与有证据experimental_precedes可mandatory=true；重要不等于必需。presentation关系必须certainty=presentation_only、type=argument_transition；paper_reported关系必须paper来源。causal_validation另需有源intervention的causal_basis_ids。验证器检查强制数据/实验先后是否成环。

### 最小错误→修正示例

1. `kind:"analysis"` → 先判定是processing/model/evaluation等；不能只为通过而改科学身份。
2. 缺`limits` → 给全部实体该键；已核实没有额外实体边界时可[]，已知限制必须保留。story及支持关系不能照抄空数组。
3. `method_ids:["DATA"]` → 将DATA保留为输入数据，引用实际方法ID（如M）；不把DATA改名method。
4. `evidence_ids:["C"]` → C保留claim；引用真实evidence，或不适用时[]，不合成假E。
5. 数据依赖不能仅写`from:"PRODUCER",to:"CONSUMER"`。必须登记DATA(kind=dataset)，PRODUCER.outputs=["DATA"]、CONSUMER.inputs=["DATA"]，并填写：

```json
"data_bindings": [{"output_id":"DATA","input_id":"DATA","usage":"primary"}]
```

两个ID必须相同、真实存在，且生产/消费接口匹配（数据实体自身可直接作端点）。外部参照输入primary_study时使用usage=reference，不冒充研究队列。不是data_depends_on的边不能填data_bindings。

## 4. 完整可运行示例与成功标准

从Skill根目录执行；`DEMO`必须是新空目录，Python需能读取PDF并使用既有依赖：

```powershell
python -B examples/a_overview_guidance/run_agent_demo.py --outdir DEMO
python -B scripts/validate_knowledge.py DEMO/minimal/knowledge.json --verify-files --json --report DEMO/m1_recheck.json
```

`minimal/knowledge.json`是自编双通道的**完整M1实例**（5实体、3关系、1 Figure、2 Story），与自产PDF及实际缓存一起生成。`dataflow.valid.json`另演示显式生产/消费字段；invalid目录保留5类约束的失败输入。不是陌生论文分析工具，不接受真实论文路径。

成功需实际进程exit=0、报告valid=true/errors=[]；MANUAL_FIXTURE警告对合成例正常。真实论文需要Agent另行检查摘录的语义支持和缺件。没有jsonschema库不等于无法校验：本版本官方校验器使用依赖无关的合同子集，仍需运行官方命令，不能用JSON语法检查代替。

M1验证通过后见[A容量恢复](a_overview_recovery.md)；中断续跑见[五阶段交接](agent_staged_resume.md)。
