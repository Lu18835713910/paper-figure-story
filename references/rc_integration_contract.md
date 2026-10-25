# v1.1 RC集成合同

本地候选版状态为RC_PARTIAL。现有v1.0入口与M1/M2-A/M2-B/M2-C接口继续保留，未安装覆盖正式Skill。

## 来源与展示

`evidence_network.py`是M1的有指纹读视图，保留原节点、关系及RSU。`--narrative`加入经绑定的M2-C原句；`--figure-story`可引用既有逐panel讲述卡，不增加科学实体。数据依赖、可选方法路线、独立验证、比较、作者论证与汇报过渡必须保持不同身份。继承direct_checked不等于本次独立科学终审。

`display_guidance.py`验证显式`pfs-display-guidance-1`指导。每条短句绑定既有statement或已登记缓存的准确摘录、范围和SHA256；所有改述仍为PARTIAL。A的具体节点、分支、汇合与跨联系可由研究内容规划，通用投影不能只显示相邻关系。C逐页记录预期panel、实际资产、读图短句、术语及限制，具体panel必须由非all资产覆盖。科学关系不得因展示需要新增。

`project_evidence_products.py`生成三类计划与逐句来源。`render_evidence_products.mjs`用Artifact Tool及学术模板生成原生文字、形状和连线，原图保持独立图片。B使用较大画布并保留登记边；原知识未抽取的条件和细粒度关系仍需补齐，不能因B有全部ID就宣称整篇精细语义已完成。

## 显式运行

```text
python scripts/run_pfs.py run --pdf paper.pdf --knowledge knowledge.json
  --assets figures.assets.json --cache-dir cache --metadata bibliography.json
  --outdir NEW_OUTPUT --modes quick balanced full --plan-only
```

可选：`--narrative narrative.plan.json --figure-story figure.plan.json --guidance display.guidance.json --template template.pptx`。输出目录必须是新的，禁止覆盖历史结果。首次索引使用pdfplumber；相同PDF哈希及页库存复用缓存，缓存漂移即失败。省略knowledge时退出码3，保存候选定位并停在REVIEWED_KNOWLEDGE_REQUIRED。

真实预览去掉`--plan-only`，显式加`--development-preview --node <node.exe> --artifact-module <artifact_tool.mjs> --presentation-skill <presentations skill directory>`。未完成独立科学终审时，默认正式模式拒绝渲染。程序依赖本地Python、pdfplumber、Artifact Tool和其验证工具；PNG验收另外需要PowerPoint或相容的实际渲染器。包不捆绑这些运行时，也不捆绑论文PDF或Figure。

## 深度与验收

- quick：主图的核心比较和最小结论；影响结论强度的限制正文保留。
- balanced：默认短句讲述、必要具体读图及复杂Figure按问题分页面。详细条件、统计和术语进入备注及审核表。
- full：共享全部科学基础，增加已登记局部图，以及有源方法、论据和限制扩展页。补充页不是新RSU，也不计为另一张Figure故事完成。

自动检查包括来源指纹、网络重建、计划漂移、引用/panel、页面几何、原生对象及PPT包结构。它们不能判定科学语义完整或用户体验接受。需逐页实际渲染，分别登记编写者目视、独立审阅及用户PENDING。原图编号冲突、未核定位混杂、构象快照与机制假说应继续显示或保留在备注。确切V4/V5文件未核验时不得宣称精确复现。

只修改开发副本；不发布、不写远程、不覆盖安装版。保留失败日志，最多一次针对性视觉修复，仍有拥挤或关键自动化缺口则交付RC_PARTIAL及明确恢复项。
