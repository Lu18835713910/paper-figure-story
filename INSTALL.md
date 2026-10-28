# 安装与使用｜v1.1.0

## 选择版本

从实际创建的GitHub Release取得ZIP；候选目录不等于已上线。v1.1.0与v1.0.0固定Tag分别保留，main为最新版。请查看Release提供的SHA256，避免误用历史RC包。

## ZIP安装

解压`Paper-Figure-Story-v1.1.0.zip`，取内部`paper-figure-story`目录，放到个人`~/.codex/skills/`。正确结构为`~/.codex/skills/paper-figure-story/SKILL.md`。已有版本先移到Skills目录以外的备份位置，勿静默覆盖或保留两个同名Skill。安装后在新会话调用`$paper-figure-story`。

## 固定Tag安装

```powershell
$skillTarget = Join-Path $env:USERPROFILE '.codex/skills/paper-figure-story'
if (Test-Path -LiteralPath $skillTarget) { throw '目标已存在：请先备份到Skills目录以外。' }
git clone --branch v1.1.0 --single-branch https://github.com/Lu18835713910/paper-figure-story.git $skillTarget
```

历史版将`v1.1.0`替换为`v1.0.0`。仓库根目录就是Skill内容，clone到目标后不要再套一层paper-figure-story。固定Tag只在实际发布后可用。

升级/回退：确认本地无未保存修改，再`git fetch origin --tags`及`git switch --detach v1.1.0`或`git switch --detach v1.0.0`。不要强制推送、reset --hard或删除旧版本来升级。

## 环境与依赖

Python 3.10+；依赖按`python -m pip install -r requirements.txt`安装：python-pptx、Pillow、pdfplumber、python-docx、lxml、PyMuPDF。PyMuPDF用于成熟index_pdf.py入口。Word/PPT处理使用本地已安装Microsoft Office；字体为Microsoft YaHei与Times New Roman。Codex桌面的load_workspace_dependencies可提供Node及Artifact Tool；它们不随本包重分发，普通Python环境不能据此承诺已具备PPT渲染能力。

已验证Windows；其他系统、无Office或缺字体环境未通过等价视觉验收。不要从仓库下载Office、专有字体或API凭据。

## Agent快速使用

提供主PDF及实际取得的补件，可选PPTX模板，指定balanced与目标听众。Agent先读原文、Methods及图注，形成共享模型；再产出简图、逐Figure讲述和所需详细图/Workbook。用户不必手写JSON。

缺knowledge的纯CLI返回exit3及REVIEWED_KNOWLEDGE_REQUIRED/agent_handoff.json；由当前Agent继续语义整理，不取消来源审核门。索引不是科学理解。缺补件/未知n保持未核验，不把PARTIAL升为正式终审。

## 真实CLI（供Agent或开发者）

```text
python scripts/run_pfs.py run --pdf paper.pdf --knowledge reviewed_M1.json --assets figures.json --cache-dir cache --outdir new_run --modes quick balanced full --products presentation --plan-only
python scripts/run_pfs.py polish --pptx finished.pptx --outdir qa_run
python scripts/build_research_workbook.py --help
```

plan-only生成并核验计划，不等于已生成PPT。导出需传--node、--artifact-module、--presentation-skill及显式--development-preview；它表示案例仍供人工科学复核，不是软件预发布标识。没有Agent视觉计划时polish仅QA_ONLY。详[PDF工作流](references/pdf_to_ppt_workflow.md)及[Visual Polish](references/visual_polish.md)。

## 模板

默认[学术蓝模板](assets/default_academic_blue_174994.pptx)为16:9，无Logo。统一入口--template支持PFS兼容命名版式；普通PPTX使用成熟路径：

```text
python scripts/inspect_template.py user_template.pptx
python scripts/build_pptx.py reviewed_slides.json --template user_template.pptx --template-mode native --output report.pptx
```

native适配母版/比例与颜色，tagged复用命名槽位。任意动画或母版的像素级复刻不承诺。成熟Figure槽最多2幅图片，更多须按问题拆页，不静默丢图。原论文图中的文字保持原貌。

## 深度产物与手册

--products with-network追加独立详细大画布；deep --inventory使用已有Methods清单生成卡片/审查资料，任务数不等于独立实验次数。quick/balanced/full共用来源和关系，仅改变展开。图输出PPTX/PNG；暂无通用SVG导出器。

build_research_workbook.py --reader可生成短句/对照表/图相邻的DOCX手册，再用实际Word导出PDF并逐页检查。文档文字与表可编辑，嵌入图的节点在配套PPTX中编辑。报告实际引擎，不把未运行的Word/Office检查写成通过。

## 许可与版本边界

个人非商业使用｜源码可查看；不是OSI开源许可。完整授权见LICENSE。原图、PDF、Office、字体和用户资料的权利不由本包转授。v1.0历史原代码不修补，已知演示缺图等限制见历史Release说明。
