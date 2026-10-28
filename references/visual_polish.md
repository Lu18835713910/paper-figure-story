# Visual Polish：锁定内容的专业视觉设计

本模块只决定PFS已经确定的内容怎样展示得更好。它不是叙事规划器、科研推断器或另一个PPT生成引擎。执行合同版本`pfs-visual-polish-locked-2`；旧版补页、改写、替图和上游增补计划被明确拒绝。

## 三个独立阶段

1. 内容锁定：保存原PPT副本及指纹、页数和页序、主稿/隐藏备份状态、每页正文和备注、Figure实例及裁剪、表格单元、节点及边身份、方向/线型、来源索引。字段未知时保持未知，不能从图片SHA或文件存在推定科学终审。
2. Agent设计与Builder：Agent看真实PowerPoint PNG，按本页既定任务写明当前问题、第一重要信息、构图、空间分配、已有重点、不可改内容、预期改善或保留理由。Builder只改变原生对象的样式和位置，执行同页已有文字的分行/视觉分组、原生表格样式、已有逻辑边的走线。不能改写科学文字或把正文移到备注来冒充无损。
3. 独立QA：再用实际PowerPoint打开和导出，核对层级、可读性、图像完整性、箭头指向、溢出及前后科学一致性。语义或文件保持校验不等于视觉成功；失败页恢复原稿，保留失败候选及原因。用户视觉确认始终独立。

## 不可变约束

逐页科研问题和讲述任务、事实/数字/分组/统计/限定语、Figure及panel归属、图像字节和已有裁剪、原节点及关系集合/方向/类型、结论/限制、正文/备注、页序及隐藏归属、来源映射全部锁定。仅允许空白和排版分行变化，不允许来源充分但未经原页面规划的“新内容”。

发现不足输出`UPSTREAM_CONTENT_ISSUE`，交回PFS规划；Visual Polish不接收上游文字响应来解决缺口。没有来源的第三方PPT仍可做视觉QA，但不声称完成科学审核。

逻辑图允许移动节点、调整分组空间、路由和箭头形态、字体层级及语义配色；原边不删不添。不足以放下全部关系时报告空间限制，不擅自拆页。走线必须匹配原显示边ID、对应源/目标节点及原生图形ID；保留原箭头方向与实/虚线。复杂折线可由同ID原生可编辑自由线表达，不重绘为位图；带原生连接绑定但不能安全改形的对象会阻断。

## 调用

```powershell
python scripts/run_pfs.py polish --pptx finished.pptx --outdir qa_run
python scripts/polish_presentation.py --pptx finished.pptx --outdir design_run --context context.json --plan agent_design.json --before-receipt qa_run/previews/before/receipt.json
python scripts/polish_presentation.py review --report design_run/visual_polish_report.json --decisions visual_review.json
```

`run_pfs.py run`的原主稿后处理钩子继续调用同一默认入口，`--no-polish`关闭。没有计划时为`QA_ONLY`，不自动改字、规范字体或宣称专业美化；字体不合规会报告。`--renderer none`无法产生视觉通过。没有Agent参与的批量规则不称为专业设计。

计划含版本、输入SHA、内容锁SHA、`designer=Agent`及`pages`。每页绑定真实优化前PNG SHA，包含七项设计说明及`shapes/tables/routes/decorations`。已有文字只通过`reflow`保持全部原字符，`text_style`调整实际Latin/EastAsia字体、字号、颜色及强调，不能靠缩字塞入。`tables`只改原表宽度、行高和样式，不改变单元值或维度。装饰只能为无文字、无图像、无箭头的后台形状。原图只调整位置/等比尺寸，不换图、不改裁剪。

Context只读复用既有资产、panel、来源和显示关系索引；`display_topology`是原PPT对象与边的映射，不是新的科学事实库。不得从Figure编号相邻推导边。原关系身份保持在既有PFS模型和备注，Builder不得改写。

## QA、回退与输出

正文按对象逐页核对，表格逐单元核对；备注和所有非视觉包部件保持字节一致。保存`content_lock.json`、`consistency.json`、实际字体审计及Office对象检查。事务级一致性失败恢复该页；Office拒绝打开时恢复所有本轮尝试页。最终Agent审阅可给`REVERT`，保留被拒候选并恢复原页及其真实匹配PNG。

输出`original.pptx`、`polished.pptx`、原/新PNG、前后对照、设计计划、科学/逻辑保持报告及不能安全处理事项。`automatic_checks=PASS`只表示该组技术检查通过；`PROFESSIONAL_AGENT_REVIEWED`是编写者图像审阅，USER_ACCEPTANCE仍PENDING。明显无改善应标记PARTIAL，不用改动对象数冒充成效。

Quick/Balanced/Full共用本边界；默认PNG宽1280/1920/2560。仅渲染实际变动页，复用指纹匹配预览；每类视觉故障最多两次有记录的定向修正，仍失败保留原图并停止。默认16:9、#174994、中文Microsoft YaHei、英文数字Times New Roman，无Logo；原论文图片字体不改。

当前合成边界测试：`python tests/test_visual_polish.py`，或直接运行`test_visual_polish_locked.py`。旧v1测试原样留在`legacy_visual_polish_v1.py`，其增补/改写预期已不适用于本合同，不作为本轮通过数。真实样页需单独实际PowerPoint视觉验收。

## 统一Deck Style与低成本异常页流程

复用`assets/visual_polish_deck_style.json`（`pfs-deck-style-1`）：27pt同位标题、18pt同级正文/方法、20pt关键结果、13.5pt术语/边界；节点和原生表格使用独立但统一的角色，不靠缩字容纳内容。Latin/数字Times New Roman，EastAsia Microsoft YaHei。页级计划用`style_role`绑定已有对象并锁定配置SHA，由`visual_polish_deck_style.py`统一执行，Agent不再逐对象推理字体。不同页面只决定布局，不强制相同图文结构。

先读既有PPT与展示索引，用SHA匹配的真实PowerPoint缓存生成全稿低分辨率联系表；Agent一次总览，只对复杂异常页看高清和精简对象记录。保留该次精简布局决定，Builder执行共享样式、实际PowerPoint高度/字体/内容合同检查，只重渲染发生变化的页。没有真实Agent视觉决定仍为QA_ONLY，技术PASS不升级视觉或用户状态。不重复输入完整Methods、讲者备注或audit。开销按可测量的文件输入规模、图像检查批次和实际Office渲染次数记录；无法读取Token则明确不可得。

用户明确要求管理标签/冗长文献页脚不进入普通页时，可在已签名页面计划中显式列`archive_chrome`：原shape_id、完整原文（空白归一）及management/bibliography类型。仅允许严格整串匹配的非科学标签或本轮纯书目信息；图片、边、单元格、事实、数字和科学限制不可归档。执行前完整原对象存`archived_page_chrome.json`，备注保持原字节。缺少明确授权计划时原合同依然拒绝删除；不能将此例外用于缩短科学正文。原引用关系继续在原备注、source_context和独立audit中保留。

新增局部边界测试`tests/test_visual_polish_deck_style.py`。16:9中全部节点与关系不能清楚呈现时，报告CAPACITY_LIMIT/VISUAL_PARTIAL，不自行拆页、删边或将小字体技术合格当作读者可理解。

## 连接关系可视化质量

轻量`visual_polish_connectors.py`从原生PPT对象读取真实直线/自由线，复用context的显示source/target，不推断科学关系。显式`connector_qa`或既有display_topology会触发检查：边/箭头存在、端点及进入方向、箭头尺寸和线宽、非端点节点/文字相交、标签互相重叠、目标尖端上方填充图形遮挡。Office导出器补充TextRange2实际文字矩形；预检用含内边距的保守文本框，正式检查用PowerPoint实际边界。直线及自由线均沿用已经验证的合法OOXML生成方式。

实/虚线及箭头type锁定，允许箭头尺寸med/lg与线宽调整，不重新把类型归类。初始参数：实线2pt、虚线1.6pt、目标三角med，阅读引导1.8pt深蓝；这些仅为展示参数，必须再看1920×1080 PNG。不能将正文关系箭头弱化为浅色细线，也不使用Unicode字符代替原生箭头。不通过删除label、缩字、白底覆盖连线来获得零相交。边间交叉单独列入edge_crossings，不自动解释为新连接；程序无碰撞不等于视觉无歧义。仍拥挤时保留VISUAL_CAPACITY_LIMIT，USER_ACCEPTANCE不升级。

来源关系类型、登记状态和显示标签须从原计划读取。没有M1登记的显示/论证联系不得冒充科学已登记关系；原计划有但源PPT未绘制的标签应报告，不能自动补造新正文。

## 普通阅读箭头：与科研逻辑连接线分开

科研逻辑连接线用于已规划节点、证据关系、分叉和汇合，允许按拓扑正交折线，原source/target/类型/方向/实虚线始终锁定。它们不适用下面的“上下留白”规则，不得为统一风格改成普通阅读箭头。

所有Figure讲解页的普通阅读引导，默认采用**PowerPoint原生直线连接符、竖直向下、明确目标尖端**。禁止L形、U形、折返或回指，不用Unicode字符代替箭头。仅复用上游已经确认的阅读顺序；不根据文字相邻自动加边，并列解释不增加箭头，也不冒充科学因果。

程序使用通用`reading_points`/`native_reading_connector`，没有论文名、Figure号或页码分支。原有`VP_PRESENTATION_ARROW`且两端是文字模块、无科学登记ID的显示引导可进入阅读模式；明确标成reading_guide也不能把科研登记关系降级。渲染后保留原对象ID、原source/target及目标箭头type，转换为合法p:cxnSp和straightConnector1；科研逻辑线仍执行原节点边界/法向合同。

阅读箭头置于上下模块之间的留白，共同垂直中轴；默认上下各离模块边界0.07英寸，最短线长0.14英寸。线宽1.8pt、学术蓝#174994、med尖端，同页一致。空间不足返回READING_GAP_TOO_SMALL，先对齐/移动现有文字块，不缩字、不弯折绕行、不删除科学正文。新建或重排阅读箭头统一使用原生直线；用户明确保留的现有向下箭头可只核查，不自动重绘。

实际PowerPoint导出后检查native_straight、vertical_down、bends=0、上下等距、同轴、同色/线宽/尖端、与实际文字边界及原图相交为0。再看PNG，不能只凭对象存在判定清楚。旧式弯折阅读箭头会被QA标记，不能以它是“正交路由”而放行。无Agent视觉决定仍是QA_ONLY。
