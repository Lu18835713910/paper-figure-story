> **最终页型区分（优先）**：`kind=framework` 使用 `study_map` 绘制全文联合总框架；`kind=figure` 使用 `story_steps` 在论文原图旁讲解该Figure的局部实验故事。详细见 [`overall_framework_policy.md`](overall_framework_policy.md)。

# PPT逐页科研故事脚本与实际PPTX生成

**最终输出分为两层**：
- `03_PPT逐页讲述脚本.md`：讲清为什么做、怎样做、发现什么、下一步为什么做。
- `06_PPT页面数据.json` + `07_科研逻辑汇报.pptx`：准备好要上屏的短句、Figure/panel素材路径和引用，使用用户PPT模板或内置HEX #174994学术蓝模板制作**真正的可编辑PPTX**。

样式、上传模板优先级和无Logo默认方案见 [`template_policy.md`](template_policy.md)。

## 默认内容架构（允许因论文类型增减）

| 页位 | 内容 | 上屏目标 |
|---|---|---|
| 1 | 封面 | 科学问题式标题、论文正式题目、引文 |
| 2 | 科学问题 | 领域知识空白、2–3个具体未解决问题 |
| 3 | **研究思路×实验路线联合框架** | 整篇研究的对象/样本/处理与时间、并行组学测量及科研任务、进一步核验、整体研究结论；不使用Figure局部故事链替代 |
| 4–N | **Figure逐图研究故事** | 左侧论文Figure证据，**右侧由Results提炼的多步文字与箭头**（实验/发现/再分析/解释）；内容而不是固定四项表单驱动排版 |
| 可选 | 样本与技术细化 | 只有总体框架太复杂时才另起一页，避免与研究思路重复 |
| N+1 | 核心结论 | 直接发现、功能验证、机制模型与限制分开 |
| N+2 | 核心技术价值 | 技术提供的关键读数与增量，不夸大“唯一” |

## Figure页（关键在右侧多步文字箭头，而非只是图注）

优先阅读 `annotation_story_policy.md`。每个Figure页先抽取可编辑`story_steps`及其关系，左侧为Figure证据，右侧为真正的科研讲述链；`question/design/result/transition`老字段只是兼容旧版的后备方式，不是目标样式。

## Figure页（每个实验故事的必要字段）

```markdown
### Slide 05 | [结论式标题]
- 来源：Fig 2a–d，论文PDF第5页；Results小节「...」
- 上一页留下的问题：...
- 本页科学问题：...
- 样本/分组/对照：...
- 实验设计：...
- 方法/读数：...
- 原图展示：已导出的 `fig2ad.png`（保持图例/坐标/统计）
- 直接观察结果：...
- 可支持的结论及证据级别：...
- 下一页过渡：...
- 讲述词（约60秒）：...
```

**不要**要求主Figure恰好等于一页；一个Figure多条实验故事可拆页，多个Figure共同回答同一问题可合并，所有panel来源需标注。对照、显著性和结论证据强度不可省略。Figure图像如果缺失，不能把留白占位当作最终版成功交付。

## JSON页面数据的最小结构

可运行的自著示例见 `examples/layout_demo.json`。下列字段示意同时展示Figure与关系图接口；其中占位对象不能作为科学事实：

```json
{
  "meta": {"short_citation": "作者，期刊，年份", "paper_title": "论文正式题目"},
  "slides": [
    {"kind": "cover", "title": "科学问题标题", "subtitle": "论文正式题目", "citation": "作者，期刊，年份"},
    {"kind": "question", "title": "需要解决的科学问题", "lead": "目前已有的事实", "bullets": ["问题1", "问题2"]},
    {"kind": "logic", "title": "整篇论文科研逻辑", "diagram_type": "branch_merge", "nodes": [{"id": "q", "title": "尚不清楚的科学问题", "detail": "具体对象、比较和待检验点", "role": "question", "figure_ref": "Fig 1", "x": 0, "y": 0.5}, {"id": "a", "title": "发现A", "detail": "样本+实验+关键观察", "role": "observation", "x": 0.45, "y": 0.2}, {"id": "b", "title": "独立验证B", "detail": "补充的干预或模型", "role": "validation", "x": 0.45, "y": 0.8}], "edges": [{"from": "q", "to": "a", "relation": "tests", "provenance": "paper"}, {"from": "q", "to": "b", "relation": "parallel", "provenance": "presentation"}]},
    {"kind": "route", "title": "实验设计和技术路线", "diagram_type": "parallel_tracks", "nodes": [{"id": "sample", "title": "具体样本及处理", "detail": "物种/组别/时间点", "role": "experiment"}, {"id": "rna", "title": "表达检测", "detail": "RNA-seq观测读数", "role": "analysis"}], "edges": [{"from": "sample", "to": "rna", "relation": "tests", "provenance": "paper"}]},
    {"kind": "figure", "title": "结论式标题", "question": "为什么做", "design": "什么样本、组别、技术、指标", "result": "看到了什么", "takeaway": "支持到哪一步", "transition": "为什么做下一实验", "figure_ref": "Fig 2a–d · PDF p.5", "image": "./figures/fig2ad.png", "story_steps":[{"text":"基于论文Methods开展特定样本与对照实验", "role":"design"},{"text":"观察到与待检验假说有关的差异", "role":"finding", "panel_ref":"Fig 2b", "relation_from_previous":"observes"},{"text":"根据此结果提出下一项研究问题", "role":"transition", "relation_from_previous":"motivates"}]},
    {"kind": "conclusion", "title": "研究结论与边界", "points": ["已被数据支持的结论"], "limitation": "仍待验证的假说"}
  ]
}
```

`figure` 页允许 `images: ["a.png", "b.png"]`，推荐每页不超过2张图；相对路径以 JSON 文件所在目录为基准。所有 `kind` 可附 `citation`、`section`，必要时 `speaker_notes` 留在脚本或备注中。

## 风格适配与渲染

- 自动生成：`python scripts/build_pptx.py 06_PPT页面数据.json --output 07_科研逻辑汇报.pptx`
- 使用模板：`python scripts/build_pptx.py 06_PPT页面数据.json --template 用户模板.pptx --output 07_科研逻辑汇报.pptx`
- 非占位模板要求严格复刻时，应先据模板建立标记插槽或手动调整版式；不能用“采样配色”冒充完整复刻。
- 草稿内容允许图片留白用于审稿：加入 `--allow-missing-images`，正式交付不使用该参数。
- PPT必须包含中文准确文字、可读排版、来源小字、可编辑文本；图表如需重新绘制，应严格依据论文数值。

## 科研逻辑图JSON约束：不画默认流水线

`logic`、`route` 页使用 `nodes`（2–10个）及 `edges`，**不再接受仅有 `stages` 的五框流水线**。节点包含：

- `id`：唯一短编号；`title`：科学问题/结果/实验目的；`detail`：具体模型、处理、样本、方法、发现；`role`：`background|question|experiment|observation|analysis|validation|inference|conclusion`。
- `figure_ref`：可选的Fig/panel来源；`x,y`：可选的归一化卡片中心（0–1），用于定制有分支的布局。全部节点都提供`x,y`时遵循人工布局，否则按边的拓扑分层；反馈循环应单独使用`relation=feedback`。
- 每条edge：`from`/`to`为节点ID，`relation`为 `motivates|tests|supports|validates|compares|parallel|extends|feedback|integrates|alternative`；`provenance=paper`（实线）或 `presentation`（虚线，叙事性关联）。可选`label`（短关系名）和`label_y`。
- `diagram_type`仅标注研究结构（如`branch_merge`、`parallel_tracks`、`comparison`、`feedback`），**它不能代替准确的edges关系**。若没有边，必须是独立平行/比较展示并说明原因。
- 对比较型实验适合双轨/镜像；图谱型研究可按分类、空间、物种比较安排支线；机制型可按“动态变化→两组平行证据→候选机制→遗传验证”汇合；多个方法在同一样本上并行检测时，不得画成先后实施。
- 超过10个节点或5列/3行时，拆为两页且保留分支的图形关系，不得缩字强塞。
- 生成器绘制的所有节点、文本及连线均为可编辑的PowerPoint对象。

## v4默认优先的综合研究框架与Figure提炼链

- 默认用一个`kind=framework`研究思路×实验路线联合页，`research_units`每个单元包含`id`、`question`、`design`、`finding`、`figure_ref`，`links`指定跨单元的`from/to/relation/provenance`。例如`数据资源与分类→（空间分析并行）→关联结果/验证`。这是论文研究叙事总览，不是技术名称清单。
- Figure结果页使用`story_steps`，而不是画死的四个带标题卡片。`story_steps[].text`是用户原始PPT右侧文字那种有信息的短句。科学问句、具体实验、结果或进一步验证按原文真实顺序组织；如关系实际平行则用`relation_from_previous=parallel`。
- PPT生成器把`story_steps`放到原Figure右侧，以可编辑的大字文本、上下箭头与局部蓝色重点呈现；`highlight`应是`text`中的原词，且关键发现必须包含`panel_ref`以供查证。
