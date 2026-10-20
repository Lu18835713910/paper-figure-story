> 本文仅规范逐Figure结果页右侧文字箭头链；**不得**将这类线性链当作整篇论文联合总框架。全文总框架参照 `overall_framework_policy.md`。

# 从用户原始PPT提取的核心讲述规则（优先执行）

## 纠偏：图片区只是“证据”，其旁的文字/箭头才是“科研叙事正文”

用户的4份参考PPT中：左侧多为论文Figure/panel截图；右侧由用户亲自整理出多段短句并用箭头推进。**Skill应学习右侧文字的“科学推理结构”，不能把原图当作要复刻的主要结构，也不能照搬Figure legend成为文字。**

- 原图：回答“数据和证据在哪里”，提供查证、视觉支撑，保持原始比例及统计元素。
- 右侧短句：回答“做了什么实验/分析，为什么这样做，观察到了什么，说明什么，以及由此进一步做什么”。这部分需要从论文Results+Methods+legend重新**提炼**。
- 箭头：表达“由于这个发现，所以继续开展下一项分析/干预”，不是装饰。如果两个panel是同时或平行测量，采用并列、不使用暗示时序或因果的实心顺序箭头。
- 强调：把最有分量的实验方法、关键结果词句局部着重，默认使用用户指定的主色`#174994`；不照抄原参考PPT的Logo或配色。

## 原始PPT显示的实际例子（仅作叙事样式来源；内容仍须回到论文核实）

### QTL参考PPT第6页（对应原论文Fig 3）
`整合基因型与标准化ATAC-seq分析 → 检测开放peak并开展caQTL关联 → caQTL验证、功能注释以及与GWAS/eQTL共定位 → 总结这些遗传调控位点与调控元件及复杂性状的关系`。
核心是实验/生信操作、输出结果、继续深挖，而不只是写“Peak图/曼哈顿图”。原稿部分统计口径需严格重核，不要照抄未经修正的36%。

### 番茄参考PPT第6与第8页（原文Fig 3、Fig 5相关panel）
- 第6页：`时间序列RNA-seq/SOM分析 → 热响应转录变化 → Hi-C空间结构变化分析 → 接触频率变化 → ATAC-seq及motif分析 → 开放区域和候选调控因子关系`。
- 第8页：`时间序列RNA-seq/motif → 候选热响应TF → ATAC-seq与DAP-seq → TF候选结合位点 → C-Hi-C/HiChIP染色质互作证据 → 解释HSFA1a可能参与的调控`。
- 这些右侧提炼文字是本技能的**结构范本**；其中“驱动”等强因果用语必须通过原始遗传干预证据来判断能否保留。

### 脓毒症参考PPT第9页（论文Fig 4）
`基因/抗体干预关键细胞因子 → 比较LPS/CLP模型中组织转录和生理指标 → 阻断后生理效应的实际变化 → 判断关键细胞因子在疾病中的功能作用`。
该页右侧是“干预-表型结果”的小故事，而非直接讲热图中每个panel的颜色。

### 猕猴参考PPT第7页（对应皮层层级组织分析）
`皮层细胞组成与空间密度计算 → 检验细胞密度和感觉皮层解剖层级的关联 → 发现负相关关系 → 总结一种候选皮层空间组织规律`。
这是“描述性分析—规律发现”，不能强制加入基因敲除或因果验证。

## 逐Figure页的抽取与显示算法

1. 先对应论文Results正文和legend，识别Figure/panel涉及的各项实际实验与分析，不从图片视觉猜测方法或结论。
2. 找出该图至少2段、至多7段对听众有推进意义的**短文字步骤**，每步只表达一个可核查的科学动作/发现/解释/新问题。常见4–5步，文章允许更少或拆页。
3. 每个步骤编码`role=context|question|design|analysis|finding|validation|inference|transition`；证据步骤附`panel_ref`，否则不能算作原图直接结论。
4. 连接必须有`relation_from_previous`。`motivates/tests/observes/supports/validates/extends/integrates/synthesizes`允许推进箭头；`parallel/compares`采用平行或比较线，不得表示必然顺序。
5. `story_steps[].highlight`仅选择整句中的重要原词局部强调；不要整页多色、每个词都加粗。
6. 左侧摆正确Figure/panel，右侧以大字号、可编辑文本/箭头显示步骤；Figure legend和来源小字位于底部，不允许大量英文legend占用讲述区域。
7. 全局“研究思路+实验路线联合图”与局部“逐Figure文字箭头链”是两种不同图，不能互相替代。

## JSON示意（示意句，正式数值/结论应按上传论文重核）

```json
{
  "kind":"figure",
  "title":"HSFA1a结合与热诱导染色质接触相关",
  "figure_ref":"Fig 5a–f",
  "image":"figures/fig5.png",
  "story_steps":[
    {"text":"对热胁迫时间序列的表达变化进行Motif分析", "role":"analysis"},
    {"text":"识别候选热响应转录因子HSFA1a", "role":"inference", "highlight":"HSFA1a", "relation_from_previous":"supports"},
    {"text":"联合ATAC-seq和DAP-seq定位可及区域与候选结合位点", "role":"design", "relation_from_previous":"tests"},
    {"text":"通过C-Hi-C及RNAPII HiChIP分析增强子-启动子接触", "role":"analysis", "relation_from_previous":"extends"},
    {"text":"HSFA1a结合区域与部分热诱导接触锚点具有相关性", "role":"finding", "panel_ref":"Fig 5e–f", "highlight":"相关性", "relation_from_previous":"supports"},
    {"text":"需进一步用遗传干预检验HSFA1a的必要性", "role":"transition", "relation_from_previous":"motivates"}
  ]
}
```
