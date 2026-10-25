# 知识模型到展示产物的最小投影合同

状态：**M2-A 结构化科研故事/关系规划已实现；PPT manifest投影、渲染器、关系布局及SVG/PNG导出仍未实现。** 第8节是实际规划API/CLI合同；前述展示投影接口仍是M2-B/M3设计。知识输入继续以 `schemas/knowledge_v1_1.schema.json` 为唯一事实源，不另建论文事实库。验收状态见开发根目录 `M2-A_验收摘要.md`。

## 1. 不变接口与设计依据

本设计已对照只读 v1.0 实际文件：`scripts/build_pptx.py`、`examples/sample_slides.json`、`references/ppt_blueprint.md` 和 `SKILL.md`。M1 不修改这些旧文件和既有行为。

| 旧接口 | 实际要求 | 投影的兼容责任 |
|---|---|---|
| PPT 页面 JSON | 顶层 `meta`、非空 `slides`；各页 `kind`、`title` | 新知识 `schema_version=1.1` 不替代旧页面 JSON，不直接传给旧构建器 |
| `kind=figure` | `figure_ref`；优先 `story_steps`，或旧 `question/design/result/transition` 后备字段 | 延续原图＋可编辑文字链；不得删除旧字段或改变旧 JSON 读取方式 |
| `story_steps` | 2–7 步；具体 `text`、有效 `role`；后续步有 `relation_from_previous`；finding/validation 有 `panel_ref`；highlight 是原句子串；每步不超过100字符 | 不能以截断文本、丢弃边界或伪造 panel 来满足长度/页型限制；需要拆页或人工审核 |
| Figure 资源 | `image` 或 `images`；相对路径基于页面 JSON 所在目录 | 以已核查的 Figure ID 绑定资源，不从文件名猜 Figure/panel；正式 Figure 页缺图时阻断交付 |
| `framework.study_map` | material、groups、core_assays、validations、synthesis；有2–4组、2–4核心实验、2–5验证等旧约束 | 保留旧入口；不能为套四列结构编造分组、验证或机制 |
| `framework.research_units` | 2–4条，均有 id/question/design/finding/figure_ref；跨任务 links 有关系和来源 | 保留旧入口；RSU不等同其固定行数，也不强制每RSU有Figure |
| `logic/route` | nodes/edges；旧10类关系；provenance=paper/presentation；可带展示用x/y | 旧关系枚举与新9类科研关系不同，不得静默等同；坐标不进入知识事实 |
| 构建 CLI | `build_pptx.py DATA --output OUT`；`--template`；`--template-mode auto/tagged/native`；草稿 `--allow-missing-images` | M1不新增/替换CLI，不改变模板优先级和默认蓝色 |
| 资源深度模式 | `quick/balanced/full` 是旧 Skill 的工作策略，默认balanced；不是构建器的模板模式 | M1不改默认页数策略、精读范围或产物深度；不能把balanced误当`--template-mode`值 |

旧 `FIGURE_STORY_ROLES` 为 context/question/design/analysis/finding/validation/inference/transition；旧步骤关系为 motivates/tests/observes/supports/validates/extends/integrates/parallel/compares/synthesizes。它们是**展示讲述链**合同，不是通用方法 I/O 合同。

## 2. 一个权威知识源，独立展示层

知识模型保存科学对象、来源、数量、参数、输入输出和类型化关系。投影层只选择、缩写和排版已存在的事实，不新增 `paper_reported` 关系，不将同一方法复制成独立事实记录。

- `entities[].id` 是唯一实体索引；方法引用应指向 kind=method/assay/processing/model/evaluation，证据引用指向 kind=evidence。
- `stories[].method_ids/evidence_ids/figure_refs` 复用这些注册对象；同一方法可服务多个RSU，一个Figure可被多个RSU引用，一个RSU也可跨多个Figure、多个PPT页。
- `stories[].presentation_order` 是讲述顺序；`original_section_order`、`restructuring_reason` 和 `author_explicit_or_presentation` 解释是否保留或重组原文。它们不构成真实实验先后。
- 参数/数量来自原实体记录，保留 status、unit、population_id 和 source_role。unknown/not_reported 不可在展示中变成0；外部参考计数不可被改写成本研究队列。
- `document_registry`、实体/关系/RSU的 `source_refs` 是来源权威。展示文字中的“PDF p.N”由定位生成，不由幻灯片页码推断。
- `figures[].kind` 区分 main、supplementary、in_text_reference、external_data_figure、conceptual；正文提及和外部数据图号不能自动计算为主图覆盖。

布局坐标、卡片尺寸、行列、泳道、箭头折点、颜色、缩写标题和页内位置均属于展示层。某方法在视觉上处于另一个方法右侧或下方，不增加 data_depends_on 或 experimental_precedes。

## 3. M2 候选调用边界（设计伪签名）

```text
project_knowledge(knowledge_1_1, presentation_request, figure_assets)
    -> projection_draft
```

这是设计伪签名，**当前没有同名API或CLI**。

最小输入：

1. 经 `validate_knowledge.py` 检查的知识快照；保留知识文件SHA256及校验诊断。校验通过不等于原论文科学事实核查通过。
2. 独立 `presentation_request`：是否明确请求PPT、沿用的quick/balanced/full、输出语言、用户指定模板路径（如有）和输出目录。不能覆盖知识中的参数或关系事实。
3. 独立 `figure_assets`：以已注册Figure ID为键，记录本地原图/合法裁图路径、所含panel及裁图核验状态。资源绑定不是新的实验事实；未绑定或无法可靠核验时返回缺图诊断。

最小输出由三个独立对象组成：

- **旧PPT manifest 草稿**：仍为 `meta/slides`，仅在请求PPT且各项安全前置条件满足时返回可构建草稿。旧构建器继续读取它，不读取新知识文件。
- **投影溯源 sidecar**：记录知识快照哈希，以及每个生成字段/图像/图形边所引用的RSU、实体、方法、证据、Figure和关系ID。
- **诊断**：例如缺图、未核验来源、关系不能无损映射、类型不确定、原文缺失、文本需要人工压缩。不用占位产物掩盖阻断项。

Sidecar最低绑定粒度示意（设计，不是当前Schema新增字段）：

```json
{
  "knowledge_schema_version": "1.1",
  "knowledge_sha256": "<knowledge JSON SHA256>",
  "bindings": [
    {
      "ppt_pointer": "/slides/4/story_steps/1/text",
      "story_ids": ["RSU01", "RSU02"],
      "entity_ids": ["E01"],
      "method_ids": ["M01"],
      "evidence_ids": ["E01"],
      "figure_ids": ["F01"],
      "relation_ids": ["R01"]
    }
  ]
}
```

Pointer中的数组下标是0基；它只定位该次导出的展示字段，不是稳定科学ID。示意中ID必须在对应知识快照中真实存在，E01应为evidence，M01应为方法类实体。空引用数组可省略；不得为了填齐示意而虚构对象。实际Schema字段名或绑定格式若在M2调整，需要独立版本标识，不能修改旧PPT字段的既有含义。

多个PPT字段可以引用同一个M01；同一字段也可引用多个RSU/证据。反向索引可由bindings计算，不另外维护第二份方法参数。人工改写展示文案后应保留引用并重新审读，不默认视为仍与知识事实一致。

## 4. 关系投影规则

新关系 `from/to` 的方向以当前知识合同和验证器为准：`data_depends_on` 使用**生产者→消费者**方向，并以 `data_bindings.output_id/input_id` 指明同一个数据实体。英文关系名不能被解释成反向边。

| 新科研关系 | 必须保留的语义 | 不得因布局而改写成 |
|---|---|---|
| data_depends_on | 明确数据/模型输出被消费；I/O绑定、mandatory及来源 | 方法名相邻就默认数据流 |
| experimental_precedes | 原文明确protocol顺序及order_basis | Figure编号、RSU顺序、讲述页码 |
| parallel_branch | parallel_evidence组及成员 | 一条串行处理链 |
| independent_validation | 独立性依据、证据强度和边界 | 下游实验把前一结果作为采集输入 |
| evidence_supports | 证据→主张、support_strength、limits | 相关性变成因果验证 |
| compares | 对照/横向比较 | 时间方向或因果方向 |
| argument_transition | paper或presentation的论证/汇报过渡 | 强制实验前置条件 |
| optional_path | alternative_routes组、可选性质 | 所有路线都必须先执行 |
| integrates | 多源综合及解释边界 | 所有输入共同证明直接分子机制 |

旧图形edge枚举只有 motivates/tests/supports/validates/compares/parallel/extends/feedback/integrates/alternative，不能直接承载新合同的全部科学语义。M2不得默认执行“新edge.type换成一个看似相近的旧relation”的批量转换。

可接受的兼容路径：旧JSON仍照旧构建；新知识的figure页优先投影到已运行的story_steps；科学边若不能由旧图形合同无损表达，应保留于sidecar并返回 `relation_projection_requires_review`，或等待M2明确实现并审核新的关系展示路径。图中文字标签不能取代机器可追溯的原始关系ID、I/O和证据边界。

不得把未核验的科学边仅改成虚线就当作已解决。当前M1合同只允许presentation provenance的argument_transition；其他科研关系的来源与强制性规则仍按知识校验器执行。

## 5. 提交给构建器之前的门槛

后续实现至少按以下顺序检查：知识结构/语义→来源状态→资产绑定→投影引用完整性→旧manifest check_input→PPT构建/审计→全页视觉核查。各层结果分别报告。

- `manual_fixture` 只能证明手工小样例结构；`extracted_unreviewed` 不能默认为已核实的科研文案。
- `secondary_only` 必须保留其via来源/locator；原论文not_provided时，不声称已全文精读或核对原图。
- 正式figure页必须有正确原图和panel；`--allow-missing-images`仅沿用旧草稿用途，不变成正式成功条件。
- Review/Perspective/Voices等允许无原始实验与无Figure；不能为满足旧framework或Figure约束造假。M2-A仅处理规划类型边界，旧validate_story与页面投影的适配留待M2-B。
- Correction缺原文时只做更正定位和来源诊断；不得返回虚构的完整论文故事。
- 任一图形布局简化若丢失必要分支、optional性质、独立验证或单位，应拆页/局部细化或返回诊断，不能修改科学关系使布局通过。

## 6. 里程碑边界

| 阶段 | 本文涉及的内容 | 当前状态 |
|---|---|---|
| M1 | 来源/实体/关系/RSU合同、独立校验、正负fixture；本文给出后续投影边界 | 仅相应新增合同/校验应以实际测试报告为准；本文为设计 |
| M2-A | 复用已注册文章类型、RSU规划、带来源的重组决策、六类框架结构建议、三挡位展开及结构化规划校验 | **已实现；不包含从原PDF自动抽取/分类** |
| M2-B | 知识规划→旧PPT manifest投影、新总框架绘制、旧validate_story无图文章适配与PPT视觉验收 | **未实施；须用户审查M2-A后再开始** |
| M3 | 章节详细方法页、SVG/PNG独立图谱、分支放大、多PDF角色缓存、DOCX适配 | **未实现** |

本设计不修改v1.0、当前已安装Skill、GitHub或历史案例。没有实现新的PPT自动生成链，也不将旧sample JSON能构建PPT的回归结果算作新知识投影已完成。

## 7. M2进入前应保留的验收约束

1. v1.0 sample_slides.json、两套framework入口、模板与Figure story_steps仍能构建/审计；使用结构和关键文本/shape检查，不能仅要求ZIP字节相同。
2. 新投影的每条边可返回原relation ID；坐标变化不会改变科学语义；反向方向、可选/强制性质也不被丢失。
3. 一个method ID被多个RSU和Figure引用时仍只有一份参数；同RSU跨多页不会重复伪造方法事实。
4. 单位和source_role跨所有输出一致；外部donor、研究library、nucleus、spot不可被合并为同一队列筛选计数。
5. 两个指定错误通过通用I/O与独立fixture关系约束拒绝；将实体名和ID整体重命名后测试仍然有效。通用校验器不搜索State/SE/ST/Splotch/COMET等词。
6. 原图核查、来源准确性和人工科研关系审读独立记录；结构PASS不自动升级为科学事实PASS。


## 8. M2-A 已实现的结构化规划合同

`scripts/plan_research.py`只消费已通过M1结构/语义校验的知识模型；它识别并复用已有的question/finding、method/evidence和类型化关系，不从原PDF重新抽取科学事实。无新的PPT manifest、坐标、SVG或位图输出，也不改变build_pptx.py、原Figure故事功能或旧模式规则。

### 输入与输出

```python
ResearchPlanner(knowledge_1_1, verify_files=False, base_dir=None)
    .plan(profile="balanced", request=None)
    .plan_all(request=None)  # 一次校验/索引，复用三挡位

plan_research(knowledge_1_1, profile="balanced", request=None,
              verify_files=False, base_dir=None)
    -> {"story_plan": {...}, "framework_plan": {...}}

validate_plans(knowledge_1_1, story_plan, framework_plan)
    -> {"valid": bool, "errors": [...], ...}
```

每次运行以规范化JSON的 `knowledge_sha256` 绑定原M1模型。`plan_version=m2a-1`与M1的 `knowledge_schema_version=1.1` 分开。缓存只在ResearchPlanner实例内存在，以profile和request哈希为键；返回深拷贝，调用者改写返回值不会污染下一次规划。没有增加磁盘事实库。

| 产物 | 主要内容 |
| --- | --- |
| story_plan | units；source_story_ids；question_refs/finding_refs原文知识指针；method_ids/evidence_ids/figure_ids/claim_ids；原文及汇报顺序；来源状态、限制指针；重组decisions；method_to_units、figure_to_units反向索引；方法细节索引与待核查任务。 |
| framework_plan | 所有原实体的只读视图、所有原关系的精确保留及knowledge_pointer；关系组；六类候选结构与证据ID；重点视图引用；统计单位/群体索引；共享输入的身份边界提示。 |

框架node可复制名称、单位、限制、details/source_refs等供下游直接审阅，但参数和数量只给原模型JSON指针，不维护第二份值。所有边保持原id/from/to/type/provenance/certainty/mandatory、I/O、独立性与来源，规划器不新增科学边。`focus_view`外的边仍在完整图中，不把隐藏路径压成新shortcut。RSU与Figure/方法的对应只证明RSU层级共引，不声称每个方法与每个panel都已一一绑定。

默认按 `original_section_order` 排序，保留已有问题和最小结论；不把输入数组顺序、既有presentation_order或Figure数字当实验顺序。缺少精确原文顺序时依赖已注册的元数据，本阶段不会补读PDF推断。

### 证据支持的重组（选择性人工控制）

可选request受 `schemas/planning_request_v1_1.schema.json` 严格约束，只能引用M1中已有对象，不能覆写参数、数量、来源或关系。

- `operations[].op=merge`：story_ids、输出unit id、具体reason与basis；必须有相关类型化证据关系连通各故事的证据/主张。相邻Figure、共同方法、重复证据ID或布局理由不能单独证明应合并。
- `op=split`：保留原question/finding指针，将既有method/evidence/Figure分配到多个focus；合计覆盖必须保持，允许Figure或共享方法复用，不新增科学问题文字或panel归属。
- `reorder`：必须列出全部规划unit一次，提供reason及真正移动的故事相关来源/关系依据；只改变讲述顺序，完整科研边不变。

basis_relation_ids与basis_source_pointers必须真实存在、相关且有来源。二次来源仍为secondary_only；结构检查无法自动确认“该引文足以支持这次合并/拆分”。因此重组是有溯源、可审查的汇报决策，**不是已经实现自动科学问题切分或语义等价认证**。

### quick / balanced / full 的可执行规则

| 项目 | quick | balanced（默认） | full |
| --- | --- | --- | --- |
| 所有RSU、Figure映射、完整图及来源/限制 | 全保留 | 全保留 | 全保留 |
| 方法细节索引 | 不展开 | 每RSU最多2个；按已登记参数数、输入数、跨RSU复用次数确定性优先 | 全部已注册方法，含未分配RSU的方法并明确列出 |
| 框架重点视图 | 证据/主张及可选、并行、比较、独立验证、真实先后关系端点 | 加全部RSU方法，并沿已有关系扩展1跳 | 全节点/全边 |
| 参数疑点待核查清单 | 0项选中（仍记录待查总数） | 最多6项 | 全部已登记缺项 |
| 原文解析/LLM调用 | 0 / 0 | 0 / 0 | 0 / 0 |

待核查任务只是未执行的精准回查建议，不能声称重新精读了Methods。全量底线校验在各模式相同；模式减少的是展开量和后续工作清单，本阶段不承诺quick运行时间按比例更短。plan_all共享校验、实体/关系索引与已提取证据，不按挡位重新全文解析。`stats`以及对校验调用、文件打开、subprocess的测试用于验证复用；`--verify-files`可读取已提供文件做哈希，但不解析原文内容。

### 框架类型选择

每次对progressive、parallel_convergence、dual_branch、comparison_matrix、method_evaluation、knowledge_topics六类给出确定性分数、已注册依据ID和固定枚举顺序的同分优先级。选择不随profile改变。

- 递进：实际数据依赖或已报告protocol先后；二者仍是不同边类型，不表示全文只有单线。
- 并行汇合：parallel_evidence组及已有共同主张/独立验证优先；只保留已声明的汇合，不假定每支都收敛。
- 双分支：识别实际两个可选路线提供方，或双成员并行组；不会把State组内的共同输出artifact算成第三条训练路线。
- 比较矩阵：明确compares边；不依据Figure版面排列猜比较。
- 方法评估：模型输出沿data/optional路径连到evaluation，或同RSU明确共引；孤立model/evaluation共存不够。
- 知识主题：Review/Perspective/Voices与未定类型的保守结构。非实验文章若把primary_study assay/intervention声明为作者已执行实验，阻止规划；外部/概念方法只标discussed_method。Correction仅处理已给更正条目，不能重建缺失原研究。

family始终是layout hint，附原关系证据和需要审查的边界，不是新的科学事实，也不决定PPT坐标。结构标签不建立新边。

### CLI 与校验边界

```powershell
python -B paper-figure-story/scripts/plan_research.py development/tests/fixtures/state.valid.json --profile all --verify-files --outdir development/m2a/examples/state
python -B paper-figure-story/scripts/plan_research.py development/tests/fixtures/als.valid.json --profile balanced --request development/m2a/requests/als_split.request.json --outdir development/m2a/examples/als_split
python -B development/m2a/run_checks.py
```

CLI写出 `story_plan.<profile>.json` 与 `framework_plan.<profile>.json`；default balanced，all复用一实例。退出码0成功、1知识/决策拒绝、2文件/JSON错误。validate_plans按相同知识快照、profile和request重建预期视图并拒绝PLAN_DRIFT；不得删去原PDF未提供等关键警告，只有是否执行文件哈希检查引起的SOURCE_FILES_NOT_CHECKED差异可以归一化。

State/ALS示例均为原M1人工二次资料fixture；原PDF在指定项目中仍缺失，没有真实论文抽取或原图核验通过声明。M2-B的PPT映射/视觉验收、M3图谱/DOCX工作须另行授权。
