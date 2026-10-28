# M2-B：知识模型投影与可编辑PPT

本页记录开发版 `project_presentation.py` 与 `render_adaptive_pptx.mjs` 的实际入口。它补充既有流程，不替代成熟的 v1.0 页面JSON、模板或构建器。M2-A规划合同见 [knowledge_projection_contract.md](knowledge_projection_contract.md) 第8节；该文件前部的M2-B状态属于当时的设计记录，当前实现以本页及本轮实测报告为准。

## 事实源与三层结构

新入口的事实权威是通过 `validate_knowledge.py` 的 `schema_version=1.1` 知识快照，来源状态、实体、方法、证据、Figure、RSU及类型化关系均复用其中记录；结构通过仍须人工核查原论文。

| 层 | 保存内容 | 不得混同 |
| --- | --- | --- |
| 科研RSU | 原知识模型 `stories` 的科学问题、方法/证据引用、发现与边界 | RSU不是Figure数量，也不是幻灯片页数 |
| Presentation Segment | 引用原RSU的讲述片段，保留方法、证据、问题和来源引用 | 拆片段不增加实验、不复制方法事实 |
| Slide | 一页的文字块、资产、节点/关系ID及布局建议 | 翻页、摆放和讲述箭头不产生科学关系 |

`blocks[].knowledge_pointer` 将已有事实文字绑定回知识快照。需修改科学内容时先修正、复核知识模型，再重新投影；不能直接改页面计划后仍声称与原快照一致。

## 输入与输出

投影输入为知识JSON、独立资产清单和 `quick/balanced/full` 档位。默认 `balanced`；不重新解析全文，不自动补实验、补参数或推断来源。

```bash
python -B scripts/project_presentation.py knowledge.json --assets assets.json --profile all --verify-files --outdir pages
```

CLI输出每挡 `pages.<profile>.json` 和 `pages.<profile>.validation.json`。页面计划包含知识/资产快照指纹、RSU→Segment→Slide引用、文字指针、Figure资产ID、框架节点/关系ID、覆盖情况及 `formal_ready/blockers`。Python入口是 `PresentationProjector(model, assets, verify_files=True, base_dir=...).project(profile)` 或 `.project_all()`；调用端可传已支持的M2-A `request`。CLI目前不提供独立request参数。

三挡只改变讲述粒度，不改变原RSU集合或科学边。实际页数由证据和资产决定，不承诺固定页数。

| 档位 | 当前展开方式 |
| --- | --- |
| quick | 同单元证据较集中，每Figure优先一个含 `all` 的资产（否则该Figure首个资产）；保留证据边界 |
| balanced | 通常逐证据展开，使用该证据明确绑定的全部资产；复杂单元加研究/论证背景，另列局限 |
| full | 在balanced基础上增加方法名称、原details、发现和适用边界页，方法/边界片段每页最多4块；仍复用同一RSU与方法记录 |

为保持可读性，投影器总览节点上限为quick 8、balanced 10、full 12；后两挡另以最多8节点的局部框架补关系，每条边的两端始终同页。balanced/full保留可选路线、并行、独立验证、比较和明确实验先后这些关键关系；full进一步使模型中每条关系至少出现于一个框架页。研究对象及其直接资源池优先保留为锚点；框架是模型原边的子图，不能跨页添加捷径。

balanced/full会同时保留已绑定的全图与局部资产。旧manifest中局部图的figure_ref精确列出panels，并标明“局部放大，结合全图”；全图不能被局部裁图悄悄替代。资产增多只增加讲述页，不能新建RSU；本轮State/ALS增加的17个detail资产仍分别复用原5个RSU。

Review等非实验文章使用“讨论背景、主要论点、适用边界”，方法是作者讨论的方法，不改写为作者实施的实验。无Figure的真实主题可用文字页；已注册并由RSU引用的主图/概念图仍须覆盖，不能以文字占位假装完成。

## Figure资产与正式门槛

资产容器为 `asset_version: "m2b-1"`、`assets: [...]`。每个资产显式保存 `id/figure_id/evidence_ids/path/sha256/source_document_id/source_sha256/physical_page/crop/panels`，不能按文件名或Figure相邻关系猜配。`crop` 是规范化 `[left, top, right, bottom]`，页码为物理PDF页码。

`--verify-files` 会核对来源文件及图片字节、SHA256和图片可解码性；它不能代替查看原图。正式使用的图片还须 `verified: true` 和独立 `visual_review`：`status: "pass"`、非空字符串 `reviewer`、与资产一致的 `sha256/source_sha256/physical_page/crop/evidence_ids/figure_id/source_document_id/panels`，以及下列五项均为布尔 `true`：`figure_identity/crop_complete/axes_legends_scalebars/significance_marks/readability`。记录必须来自实际目视核查，不得程序自动填成通过。

缺图、缺人工图像核查记录、来源未 `direct_checked` 或主图覆盖不足时，计划可能仍可作为诊断草稿输出，但 `formal_ready` 为false，拒绝作为正式交付。Review的概念图也适用。单独一个 `verified: true` 不足以通过。旧构建器的 `--allow-missing-images` 仍仅限草稿，不能用作正式验收依据。

`formal_ready` 只汇总结构、来源状态和已登记的资产检查条件，不表示程序完成了科研事实复核或PPT视觉验收；科学审核、全页渲染、溢出/比例/对象检查必须分别报告。未启用文件校验的计划不得作为正式文件核验结果。

## 从计划到PPTX

1. 先验证知识、来源、资产和页面计划；保留相关结果。`validate_page_plan` 会校验快照绑定、RSU/Segment/Slide引用、文字指针及计划重生成一致性。
2. 调用Python `legacy_manifest(model, assets, page_plan)` 产生临时的旧格式 `meta/slides`，再按原接口构建底稿：

   ```bash
   python -B scripts/build_pptx.py legacy_manifest.json --output base.pptx
   ```

   该manifest仅是兼容底稿，不是第二份科研事实库；它的框架页不会替代新类型化科研图。Figure的 `relation_from_previous: "parallel"` 是旧合同的中性占位，含义由 `presentation_transition_semantics` 声明为讲述次序，不等同知识关系中的 `parallel_branch`。文字过长/步骤过多须拆页或复核，不能截断事实使旧合同通过。
3. 用新renderer将已选科研节点、关系和讲述提示作为可编辑原生对象写入底稿：

   ```bash
   node scripts/render_adaptive_pptx.mjs --base base.pptx --plan pages/pages.balanced.json --knowledge knowledge.json --output final.pptx --artifact-module /absolute/path/artifact_tool.mjs
   ```

   需要本地Artifact Tool运行时；可省略 `--artifact-module` 使用环境变量 `ARTIFACT_TOOL_MODULE` 或可解析的 `@oai/artifact-tool`。底稿与输出须不同，输出文件已存在时拒绝覆盖。计划按数组位置对应底稿，也支持显式0基 `slide_index/base_slide_index` 或1基 `slide_number`。

renderer只消费已存在的实体/关系，不执行知识/计划的完整科学审核。框架的 `node_ids/relation_ids` 必须来自知识模型，关系两端必须都在该页；renderer接受每框架页1–16节点，而投影器采用上述更小的可读性上限。方向、实/虚线及图例按实际关系类型绘制，只有 `experimental_precedes` 表示实验时间先后。`compares/parallel_branch` 为无方向关系，`argument_transition` 是论证转接；不能用Figure编号或页序制造数据流、因果或前后实验。

Figure/文字讲述页中的流程箭头只承担汇报衔接，renderer为含此类箭头的页面加“讲述顺序；科研关系见框架图”提示。科研边仍以知识模型原relation ID、from/to/type和来源为准。框架布局只改变坐标，不补边、反转边或给独立支线造汇合。

输出为PPTX及同名 `.render-report.json`。新增文字、节点和连接线是原生对象；原Figure继续是图片。renderer将新增对象移植回原OPC包，保存来源元数据到备注，避免整套PPT被重写；未修改的页面XML、图片、母版等仍须由实际包/对象回归检查证实。可用 `--preview-dir DIR` 导出本次修改页的PNG及layout JSON，**它不替代最终全页渲染**。

## 模板与验收边界

默认底稿仍使用 `assets/default_academic_blue_174994.pptx`；旧构建器的用户模板、`--template-mode auto/tagged/native` 接口保留。新renderer目前要求16:9底稿，采用 `#174994` 和默认Microsoft YaHei（计划可提供 `style.font_family/theme.font_family`），不拉伸不同宽高比。

用户模板的完整适配、Logo/配色/字体保留及不同底稿复杂元素避让，在M2-B标记为**待专门实测**；不能因为接口存在或默认模板通过，就声称任意模板已支持。每份正式PPT仍须渲染全部页面并检查文字溢出、图像比例/可读性、重叠、备注溯源和可编辑对象。

M3的独立SVG/PNG科研图谱导出、进一步分支放大、复杂多PDF角色缓存、DOCX等扩展未在本页入口实现；不因本轮已能生成PPTX而宣称这些功能完成。