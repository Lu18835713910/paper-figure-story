# Visual Polish：成品PPT的独立质量关

入口版本`pfs-visual-polish-1`。输入已完成的PPTX，不重新解析全文、不建立科研事实库、不修改Methods Inventory。保留原稿和科学审核状态，完成实际PowerPoint渲染、逐页诊断、定向编辑及复核。

## 调用

`run_pfs.py run`完成初版主PPT后默认调用`postprocess_main`；不批量处理深度卡。`--plan-only`不启动，`--no-polish`关闭。原`pptx/main_balanced.pptx`保留，最终版在`visual_polish/polished.pptx`。旧`build_pptx.py`接口不变，Agent在生成后独立调用：

```powershell
python scripts/run_pfs.py polish --pptx finished.pptx --outdir polish_run --profile balanced
python scripts/polish_presentation.py --pptx finished.pptx --outdir polish_run --context context.json --plan edits.json
python scripts/polish_presentation.py review --report polish_run/visual_polish_report.json --decisions final_image_review.json
```

Agent先看真实PNG，再提供绑定输入SHA的定向计划。无计划只规范字体、诊断对象和渲染，**不自动重写正文、添加表格内容或宣称视觉通过**。自动入口也可传`--polish-context`、`--polish-plan`及`--polish-before-receipt`；多档应分别传匹配该成品的计划。文件SHA不符则拒绝编辑。

需要Windows PowerPoint、微软雅黑和Times New Roman。`--renderer none`仅技术诊断，视觉状态PARTIAL；实际导出失败保存日志，不用模拟画面代替。

## 五步质量关

1. 实际PNG＋可编辑对象检查，输出逐页`diagnosis.json`；指标只是候选，不能代替图片审阅。
2. 分类：A字体换行；B布局；C视觉编码；D原图完整性；E导航；F内容覆盖。F输出上游请求，不能在视觉层编造。
3. 显式定向操作：已有比较转表格/双栏、Figure保留原图并调整比例、保留真实分叉汇合。原文压缩由Agent核对主体、数字、方向和限制。
4. 实际Latin字体Times New Roman、EastAsia字体Microsoft YaHei；新增对象学术蓝`#174994`。原位图字体不改；保留原PPT模板/母版。可用context的`template:{path,sha256}`登记只读样式参考，校验文件而不承诺任意模板自动套用。
5. 二次导出受影响页，检查溢出、比例、panel、文字损失和箭头，记录最终PNG SHA。编写者审阅、用户接受和科学终审分开。

## 复用来源与编辑合同

Context只读引用原有资料：

- `protected_sources`、`sources`：文件路径和SHA，适用于原模型、来源及Inventory。
- `assets`：路径、SHA、细粒度panels、映射与视觉状态；可登记原图`bbox_px`和轴/图例/统计区的`critical_regions`。`all`不能满足细粒度panel要求。SHA一致不证明裁图完整，必须查看原图。
- `relationships`：已有ID和identity；presentation不能升级科学关系。
- `slides`：页类型、预期panel、必要内容，以及转备份时仍须在主稿可见的`important_limits`。
- `upstream_responses`：上游针对缺口提供的已审核内容；含request_id、路径、SHA及原文绑定。科学终审仍PARTIAL。

计划含`version`、`input_sha256`、`visual_reviews`、`actions`和`resolves`。视觉审阅绑定真实PNG SHA。文字使用`{text,refs:[{kind:"deck",slide:1}]}`，必须可在原稿或备注定位；上游文字使用`{kind:"upstream",response:"已登记ID"}`，须有经检查的文件及原文绑定。

局部操作为`layout`、`table`、`insert_table_slide`、`replace_text`、`add_text`、`narrative`、`replace_image`、`backup`。改写前文字保留备注，原媒体字节留在包内；替换图需已核实资产及panel、保持比例。删除带动画对象被阻断；组对象不得误用子坐标。不能安全编辑的复杂对象保留并报告。

F缺口不能由布局动作清除。上游显式响应须匹配request_id，才可定向补页。审计可转隐藏备份，重要科学限制仍在普通讲述页可见。来源和字面绑定是漂移防线，**不能自动证明语义/因果正确或来源充分**；Agent仍须审阅。第三方无来源PPT只做可验证视觉处理，`science_audit=NOT_PERFORMED_BY_VISUAL_POLISH`。

## 模式、成本与状态

三档共享科学及字体约束，默认PNG宽度Quick1280、Balanced1920、Full2560像素。Quick重点明显缺陷；Balanced逐页并检查关键Figure；Full还需充分查看复杂表格/统计局部，审阅范围须写入记录。不重跑三套科研分析。

复用SHA一致的真实Office预览，仅重导出修改页。最多两轮有记录的视觉定向修复；无内部无限优化循环，`--cycle`仅1或2。Agent不得借新目录重置轮次预算。无法可靠修复则保留原页、失败预览和PARTIAL。

输出：`original.pptx`、`polished.pptx`、完整最终/受影响预览、`before_after/`、JSON/MD报告、字体检查、媒体/来源不变性、上游请求及未解决事项。`automatic_checks=PASS`不是视觉认可；`POLISHED_AGENT_REVIEWED`仅编写者看过图，用户始终PENDING直到直接确认。

合成测试：`python tests/test_visual_polish.py`；不含第三方论文资料。真实Office、六组样页与两份balanced检查在本地独立保存，不能由合成测试数代替。
