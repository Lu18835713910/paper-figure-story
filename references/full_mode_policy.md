# Full 模式输出规则

仅当用户明确要求“深度精读”“完整逐panel审计”“full”“全量证据矩阵”时执行。科研内容原则遵守根目录SKILL.md。

交付以下八项：
1. `01_论文总体科研逻辑.md`——完整背景、问题、中心假设、研究设计、主证据链和局限。
2. `02_Figure逐图研究故事.md`——全部主要Figure及重要Supplementary按panel提取七问。
3. `03_PPT逐页讲述脚本.md`——逐页文案与30–90秒讲述词。
4. `04_证据溯源与核查.md`——来源、统计分母、证据等级、待核查问题。
5. `05_实验设计证据矩阵.csv`——使用 `references/experiment_matrix_header.csv` 的列名。
6. `06_PPT页面数据.json`——全篇总框架和各Figure `story_steps`。
7. `07_科研逻辑汇报.pptx`——按需生成PPTX。
8. `08_PPT模板适配与质检.md`——图表与排版审查及局限。

运行 `python scripts/validate_story.py 输出文件夹 --profile full` 验证结构，再结合 `scripts/audit_pptx.py` 和逐页渲染。完整精读的输出不受balanced页数预算约束，但也禁止无必要机械拆分每个panel。
