# A总览容量恢复：先规划科学范围，再投影

本页复用现有M1、Evidence Network、Research Logic和display guidance；没有新增科学Schema或自动聚合算法。下面例子全部自编，不是论文理解/科学终审测试。

## 门禁的含义和真正的恢复点

`project_evidence_products.overview()`对源图分秩并压入至多6列；任一列超过6个源节点时报`A_NEEDS_GUIDANCE`。这是默认布局的安全容量，不是论文贡献上限。短标签仍可能另触发`A_NODE_NEEDS_SHORT_SOURCE_LABEL`；显式规划也不能取消文本、路线和画布检查。

贡献识别及范围选择属于Agent科研分析，应在全文/Methods阅读、M1有源登记和贡献覆盖审阅之后，A/B投影之前完成。不能拿Figure编号、节点顺序或关键词替代科学聚合。

1. 保留当前M1/网络及失败日志，复用相同PDF指纹的缓存。
2. 用既有claim/RSU/statement/source ID逐项审阅核心贡献、证据与限制；为A的概括保留源身份及已审核省略理由。共享证据沿用同ID，绝不增加独立验证次数。
3. **即时恢复默认推荐display guidance**：已有M1和失败网络的statement足以支持概括时，只补有源的显示分组。可以只引用真实statement ID，不要求每条再填缓存跨度，也不要求先建scientific_index。它不能代替完整B规划或“发现了全文全部贡献”的审核。
4. 需要详细科研骨架、局部图及同模型Workbook时使用**显式Research Logic**：依照`research_logic_contract.md`建立有源节点与关系；`core.nodes/edges`是简图A，B使用全部已登记逻辑节点和关系，细项用既有`parent_id`关联core。保持真实并行、互补、数据输入和论证身份。源图不需要被改小。已有有效逻辑模型时直接复用，不退回重建guidance。
5. 新建输出目录重新`--plan-only`；核对A/B、Figure故事与总结覆盖后再按实际后端能力渲染。换quick并不能保证消除同秩超载。

显式模型必须先验证，再选择该投影，不能先创建默认A/B再替换。`logic-views`和常规`presentation/with-network`均复用同一模型验证器；来源错误不允许回退掩盖。

## 可复现的合法示例

完整操作演示（推荐先运行，**不读取任何真实论文**）：

```powershell
python -B examples/a_overview_guidance/run_agent_demo.py --outdir NEW_DEMO
```

产出：minimal完整M1、seven_channels超容量输入、over_capacity失败现场、guided_recovery（准确跨度版）、statement_only_recovery（仅既有statement绑定版）、explicit_recovery、原生A/B及commands.json逐条命令/退出码/stdout/stderr。调用均由脚本实际执行，不是手写通过记录。再次运行须新目录。

七通道不是每篇论文必须三组的模板。展示文字、分组及关系由Agent按真实论文决定；示例只教合法字段和命令。

从Skill根目录执行（Windows可用`python`或自己的Python绝对路径）：

```text
python examples/a_overview_guidance/make_synthetic_example.py --outdir NEW_EXAMPLE
python scripts/validate_knowledge.py NEW_EXAMPLE/knowledge.json --verify-files
python scripts/research_logic.py --model NEW_EXAMPLE/research_logic.json

python scripts/run_pfs.py run --pdf NEW_EXAMPLE/synthetic_calibration.pdf --knowledge NEW_EXAMPLE/knowledge.json --cache-dir NEW_EXAMPLE/cache --metadata NEW_EXAMPLE/metadata.json --products with-network --research-logic NEW_EXAMPLE/research_logic.json --outdir NEW_RUN_LOGIC --plan-only

python scripts/run_pfs.py run --pdf NEW_EXAMPLE/synthetic_calibration.pdf --knowledge NEW_EXAMPLE/knowledge.json --cache-dir NEW_EXAMPLE/cache --metadata NEW_EXAMPLE/metadata.json --products with-network --guidance NEW_EXAMPLE/display.guidance.json --outdir NEW_RUN_GUIDED --plan-only
```

`NEW_EXAMPLE`须为空目录。生成器仅包含固定的七通道自编校准表和明确的示例分组：方法、七项观察/论断、一个共享观察、并行组、准确PDF缓存、现有Research Logic及guidance。**它不是从任意论文自动生成逻辑图的工具，不应用它生成真实论文答案。**

不带任一显式规划时，本例同秩7节点会被安全阻断。显式Research Logic示范4节点A与11节点完整B；guidance示范把同一读数表概括成3个展示组，仍引用7个原始E和C身份。编号组仅为合成示例的阅读选择，不是所有论文的推荐分组。

原生便携图路径（不会生成普通Figure主稿）：

```text
python scripts/project_research_logic.py --network NEW_EXAMPLE/network.json --model NEW_EXAMPLE/research_logic.json --outdir NEW_VIEWS --views A B
python scripts/run_pfs.py render-products --network NEW_EXAMPLE/network.json --plan NEW_VIEWS/products.plan.json --metadata NEW_VIEWS/metadata.resolved.json --outdir NEW_NATIVE --backend portable --development-preview
```

安装PowerPoint且可访问COM时增加`--office`，导出真实PNG/PDF及既有`logic_graph_manifest.json`。只读渲染不提升科学审核。

## guidance现有字段与身份

待填模板：`examples/a_overview_guidance/display.guidance.template.json`。占位符必须用当前网络的真实值替换，模板本身不能直接通过验证；生成器输出才是完整可验证例子。

|字段|取值与用途|
|---|---|
|version|`pfs-display-guidance-1`|
|paper_id|当前`network.paper.id`|
|knowledge_sha256|当前`network.inputs`中`kind=knowledge`的文件指纹|
|formal_ready|必须false；改述保持PARTIAL|
|records[].id/text|唯一显示记录ID及已审阅短句|
|source_statement_ids|既有statement ID，可多项聚合；不得创建新科学事实|
|source_node_ids|实际包含的既有M1节点ID；不得拿附近页码/相似标题替代身份|
|source_spans|可选或补充的准确缓存摘录；statement与span至少一种非空|
|semantic_review_status|固定PARTIAL；定位成功不等于终审|
|overview|title_id、limit_id、唯一nodes[{id,text_id}]、唯一edges；可给position/font_size等既有显示字段|
|figure_pages|无额外Figure显示规划时为[]；不代表Figure故事已完成|

跨度依据**实际缓存解码后的Unicode字符**计算，禁止手填估算偏移：

```python
from pathlib import Path
import hashlib
p = Path(cache_dir) / 'page-01.txt'  # 必须在network的已登记source_cache目录
text = p.read_text(encoding='utf-8-sig')
quote = '原文中确实存在且已核查的句子'
start = text.index(quote)  # 如重复，先人工确认正确段落，不盲取第一次
end = start + len(quote)
assert text[start:end] == quote
span = dict(path=str(p.resolve()), sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
            start=start, end=end, text=quote)
```

若后续Workbook复用M1的`locator.context_sha256`，还须使它与Research Logic中登记的真实摘录身份精确对应。例如M1登记整页context哈希时，例子同时登记从同一真实缓存计算的`S_PAGE`整页跨度和细粒度摘录；不能只因页码相同就认定语义已对齐。旧失败和新输入修订分别保留，不能手改旧receipt的SHA。

`scientific_registered`边必须指定现有`source_relation_id`，端点源实体匹配，类型不能更换。`presentation`/`author_argument_candidate`边只能使用校验器允许的论证/阅读类型且不得伪挂科学relation ID；用`parallel`可以表示阅读并列，不制造数据依赖。一个聚合组包含多项实验，也不把组内证据视为重复样本。

验证器拒绝重复record/node/edge ID、未知statement/node、未登记缓存、错误SHA/跨度、错误科学端点、关系升级及formal_ready提升。它不会自动判断“分组科学上有意义”或“全文贡献已全找出”；必须继续使用既有贡献覆盖审阅、A/B来源核对、版面预检及真实渲染。

## M1登记约束：本轮不改Schema

|遇到的限制|设计意图及合法写法|
|---|---|
|story.method_ids不接受intervention|仅允许method/assay/processing/model/evaluation。干预保持intervention身份；story引用真实检测/处理方法，方法的有源设计/条件参数说明干预及其ID。确有因果证据时，支持边的`causal_basis_ids`引用原intervention；不得把干预改名method或虚构实验先后。当前缺少直接story.intervention_ids，不在本轮新增。|
|story.evidence_ids不接受claim|读数/证据与解释分开；E作为evidence，C保持claim，`evidence_supports`连E→C并保留strength/limits。故事finding_or_argument可引用有源认识，不能把claim换皮为实验。概念性综述使用已有论证路径，不伪造实验支持。|
|figures不接受title|既有字段是`label`；图注/逐图解释使用有源记录，不能新增任意title键。|
|limits=[]被拒绝|story及支持关系要求明确边界；写已知限制或具体“尚未核验”边界，不等同“原文未报告”。entity.limits本来允许[]，不能把某位置的约束泛化至所有limits。|
|某些关系不允许mandatory|仅有源data_depends_on或实验先后可mandatory；并行、论证、支持等设false，不把科学重要性等同数据必需。|
|metadata要求citation_short|单篇metadata使用顶层citation_short；keyed registry必须能匹配paper ID。该字段不是M1科学实体。|
|失败后OUTPUT_EXISTS|保护历史失败；复用cache，在新outdir重试，不删除或覆写旧失败。|

## 输出边界

`--plan-only`成功只说明当前规划调用完成；**仍须检查plan_validation.json、geometry_preflight.json及contribution_validation.json**。本例guidance默认B有TEXT_HEIGHT_RISK，即使exit=0也不能标记展示合格；应使用显式Research Logic及既有展示配置处理B，而不是修改门禁。`render-products --backend portable`只支持已登记逻辑画布，不能消费含普通Figure页的整套计划。普通Figure主稿标准`run`仍需真实可用Artifact宿主；缺失时在解析前报`MAIN_HOST_DEPENDENCY_REQUIRED`。不开发新Figure引擎，不以scaffold/PNG代替成品。

Workbook使用已有模型、图清单与有源M1/RSU组装；解释不够就生成缺口，不为演示强造内容。独立图和Workbook能生成，也不代表包含主稿的Full交付已通过。

## 低成本即时恢复操作单

前提：M1已通过官方校验，失败目录已保存`evidence_network.json`，PDF/cache未变。以下命令从Skill根目录运行；路径变量由Agent指向**当前案例自己的文件**，保留之前run所用assets、figure-story、relations、inventory等参数，不漏掉它们导致网络身份变化。示例可直接用NEW_DEMO/seven_channels对应文件重放，不给盲测论文预制答案。

### 选择路径

|路径|新增准备|适用与风险|
|---|---|---|
|display guidance（即时默认）|已有network中的statement/node身份；records、overview、有源分组和关系|最快解除默认A门禁；可source_spans=[]，但每条record仍需至少有效statement或准确跨度。默认B和Figure教学并不自动完善，也没有免审来源|
|显式Research Logic|已读科学索引12 facets、精确sources、节点/关系、core、布局、输入指纹|工作量更大，但同模型A/B、局部图、Workbook更直接；需人工科学判定，不能自动从题目生成。已有这些输入时优先复用|

两者同时提供时，显式Research Logic用于A/B，guidance仍可能供Figure页消费；**不是模型错误时的fallback**。非法模型必须修正后重试，不能偷偷改走默认图。

### 1. 先抽取身份清单，不重读全文

```powershell
$net = 'FAILED_RUN/evidence_network.json'
python -B scripts/evidence_network.py --validate $net
```

Agent从network.statements读取`id/text/role/entity_ids/source_refs/source_pointer`，从network.inputs读取kind=knowledge的真实sha256，paper.id作为paper_id。只把当前已有证据能支持的“研究任务—方法—发现”概括进A。用原有贡献审阅表记录各claim→显示组/有理由省略，保留共享证据ID。不能按节点索引机械分成三组。

### 2. 填现有模板，并做有源审阅

复制`examples/a_overview_guidance/display.guidance.template.json`到本案例新输入目录。替换占位符：

- TITLE绑定支持该科学问题的实际statement，不拿任意方法名充当问题来源。
- 每个GROUP_TEXT绑定所概括的所有重要statement与实体ID。可见文字包含任务和实际发现，保持限制。**不能只填node IDs而空缺statements/spans。**
- 如原文已有可综合的最终认识，在现有record/node机制中有源表达对科学问题的回答，不让A停留在研究方向目录。仅根据既有发现作有源概括；不要为“收束”补造机制或因果边。
- LIMIT绑定现有限制statement；若现有statement未登记限制，则先定向核查缓存，使用准确source_span；不能随便借同页ID。
- overview.nodes引用text_id；按实际内容给位置/字号；overview.edges只有有依据的关系。并行可用identity=presentation、type=parallel，不加source_relation_id；登记科研边须scientific_registered、真实source_relation_id、原type和匹配端点。
- IDs不可重复，formal_ready=false、semantic_review_status=PARTIAL；figure_pages=[]只表示本配置未规划Figure页，不宣称逐图完成。

只要statement已足以支撑文本，source_spans可为空，**不必逐记录计算新跨度**。若需要跨度，使用本页已有`text.index`方法，核对双栏阅读顺序及实际子串；记录准确缓存文件SHA，不能手估偏移。

### 3. 正式重入与验收

```powershell
python -B scripts/run_pfs.py run --pdf paper.pdf --knowledge INPUT/knowledge.json --cache-dir CACHE --metadata INPUT/metadata.json --guidance INPUT/display.guidance.json --products with-network --modes balanced --plan-only --outdir NEW_GUIDED_RUN
```

该入口会正式校验guidance及身份，不另造无消费者的状态文件。确认：无A_NEEDS_GUIDANCE；balanced/products.plan.json含A_overview及detail；A的source_node_ids/source_statement_ids覆盖已审重要贡献，detail保持原节点/边；plan_validation.valid=true。检查geometry_preflight，发现风险不得标VISUAL PASS；检查summary_coverage与contribution_validation，不能以“所有登记claim”证明已找全论文贡献。execution.json的cache_reused=true、pdf_parse_calls=0时才称缓存实际复用。

### 4. 需要显式Research Logic时的完整现有操作

科学索引前置不是缓存metadata。`scientific_index init --paper-index`要求`source_pdf/file_sha256/page_count`，可复用`index_pdf.py`生成的paper_index.json（见五阶段指南）。init产生PENDING骨架，Agent依据已读缓存填写12 facets、reading_record、真实sources及准确跨度；状态只能在实际完成对应阅读和映射后填AVAILABLE_CONTENT_READ/COMPLETE_AVAILABLE/MAPPED_WITH_GAPS。PARTIAL允许有源缺口，PENDING不能装配。

```powershell
python -B scripts/scientific_index.py init --paper-index CACHE/paper_index.json --output INPUT/scientific_index.pending.json
# Agent在独立副本中填写有源索引和adjudication.json，不修改原PENDING记录
python -B scripts/scientific_index.py validate --index INPUT/scientific_index.json
python -B scripts/scientific_index.py assemble --index INPUT/scientific_index.json --network FAILED_RUN/evidence_network.json --adjudication INPUT/adjudication.json --output INPUT/research_logic.json
python -B scripts/research_logic.py --model INPUT/research_logic.json --output INPUT/logic.validation.json
python -B scripts/run_pfs.py run --pdf paper.pdf --knowledge INPUT/knowledge.json --cache-dir CACHE --metadata INPUT/metadata.json --research-logic INPUT/research_logic.json --products with-network --modes balanced --plan-only --outdir NEW_LOGIC_RUN
python -B scripts/project_research_logic.py --network NEW_LOGIC_RUN/evidence_network.json --model INPUT/research_logic.json --views A B --outdir NEW_VIEWS
python -B scripts/run_pfs.py render-products --network NEW_LOGIC_RUN/evidence_network.json --plan NEW_VIEWS/products.plan.json --metadata NEW_VIEWS/metadata.resolved.json --outdir NEW_NATIVE --backend portable --development-preview
```

adjudication使用既有paper_title/short_citation/nodes/edges/core/branches/method_explanations/layout；完整实例见演示产出的seven_channels/research_logic.json。assemble可从该结构的独立副本装配，忽略旧inputs/sources/snapshot并用已验证索引及当前网络重建绑定。真实论文不得照搬合成节点；无Inventory不要求造实验清单。用官方assemble计算snapshot，不能只替换哈希。

显式例子的sources由实际自产缓存计算；statement绑定与精确source绑定是两个合同，不能把已有M1页码当作已审核excerpt。来源不足时定向补齐，不再全文解析。模型调用以当前网络重建结果为准；输入资产/路径或文件内容变动导致network变化时，按父子派生记录和官方校验重新装配，不能混用旧图receipt。

### 5. 错误排查与接续

|错误|行动|
|---|---|
|GUIDANCE_UNKNOWN_STATEMENT/NODE|回看当前network真实ID；不是文献标题或旧run的身份|
|GUIDANCE_*DRIFT/EXCERPT_DRIFT|核查真实文件、缓存与字符偏移，不刷新hash掩盖文本变化|
|GUIDANCE_RELATION_*|科学边端点/type严格匹配；汇报并列不能冒充data_depends_on|
|LOGIC_NETWORK_MISMATCH|比较所有网络输入及snapshot，重新合法装配派生模型，不回退默认A|
|LOGIC_TEXT_FIT或geometry风险|使用已有布局/显示规划；保留科研内容，A概括、B大画布及局部分工，不缩字掩盖|
|OUTPUT_EXISTS|保留原失败，新outdir；cache沿用原路径|
|MAIN_HOST_DEPENDENCY_REQUIRED|主稿宿主未满足；可先完成逻辑阶段，不声称Full完成|

下一阶段见[五阶段保存与续跑](agent_staged_resume.md)。首次陌生论文失败永久保留BLIND_TEST_FAIL；后续同论文续跑标RECOVERY_TEST。恢复通过也不是全新盲测通过。
