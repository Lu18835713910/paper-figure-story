# 运行与测试

## Visual Polish（2026-10-27）

`python -B tests/test_visual_polish.py`执行独立合成回归：原稿/媒体保持、真实字体属性、来源与数值漂移、panel/关键区域、F类缺口上游处理、关系身份、备注保留、隐藏页科学限制、真实CLI及自动入口/关闭选项。此测试不启动Office、不重做论文分析。真实六组样页、两份balanced及一次有记录的视觉修复在私有开发记录中检查；软件PASS不代表视觉或科学终审。

发行包中的`tests/test_inventory_synthetic.py`为自著完整性样例，使用Python标准库；它不证明真实论文语义正确。运行：`python -B tests/test_inventory_synthetic.py`。

本版采用轻量验收：既有缓存/来源复用；同论文同原图对照；CNNM4关键页；5页综述＋1张图；State定向容量/小数；备注、实际PPTX字体/可编辑性和PowerPoint边界；隔离目录代表性生成。开发日志与真实论文材料不随公开包分发。每次具体交付的科学/视觉审核独立记录，不以软件测试数代替。

维护者运行环境依赖`requirements.txt`及Codex提供的Node/Artifact Tool；不在包内下载Office、字体或私有运行时。通用SVG、扫描PDF OCR及无人辅助科研机制推断未验收。


## 2026-10-26 定向可读性与字体验收

维护者对源绑定展示、关系身份、箭头原生对象、计划漂移、旧默认投影、Review/State兼容、18任务/342字段完整性、实际字体及Word导出执行24项定向测试。首轮22通过、2失败；修正默认标签内边距回归与测试中的PDF换行匹配后，仅重跑失败两项，最终24项通过（26次用例执行）。历史全量测试数不累计为本轮结果。

真实PowerPoint导出3张详细/分支图，Word导出22页学习手册并逐页检查PNG。初稿空白页及小样可读性问题保留在私有开发记录；用户视觉接受及独立初学者理解测试尚未完成。原图栅格文字不属于可编辑文本字体审计范围。

发行包保留12项自著科研逻辑合同测试：`python -B tests/test_research_logic_contract.py`。这是结构和来源约束测试，不是论文理解或科学终审。字体审计入口：`python scripts/audit_script_fonts.py --help`；手册入口见INSTALL。真实论文案例、审计日志与对照预览不随公开包分发。
