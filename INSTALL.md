# 安装与使用｜v1.1.1（正式封包，待批准发布）

本目录为 **`1.1.1`正式版本封包**，尚待负责人批准发布。Git Tag `v1.1.1` **尚未创建**；在该Tag存在之前，任何 `git clone --branch v1.1.1` 都会失败。`v1.1.0` 与 `v1.0.0` 的历史Tag保持可用。

## 选择版本

| 版本 | 状态 | 安装方式 |
|---|---|---|
| v1.1.1 | 发布候选，未上线 | RC压缩包或本地候选目录（本页） |
| v1.1.1 | 目标版本，**Tag未创建** | 负责人发布授权后由Release提供 |
| v1.1.0 | 已发布 | 固定Tag或Release ZIP |
| v1.0.0 | 历史归档 | 固定Tag |

候选目录不等于已上线。请用Release提供的SHA256核对压缩包，避免误用历史RC包。

## ZIP／本地目录安装（发布候选阶段）

解压`Paper-Figure-Story-v1.1.1.zip`，取内部`paper-figure-story`目录，放到个人`~/.codex/skills/`。正确结构为`~/.codex/skills/paper-figure-story/SKILL.md`，不要多套一层。

```powershell
$skillTarget = Join-Path $env:USERPROFILE '.codex/skills/paper-figure-story'
if (Test-Path -LiteralPath $skillTarget) { throw '目标已存在：请先备份到Skills目录以外。' }
Expand-Archive -LiteralPath .\Paper-Figure-Story-v1.1.1.zip -DestinationPath $env:TEMP\pfs_rc
Copy-Item -Recurse "$env:TEMP\pfs_rc\paper-figure-story" $skillTarget
```

已有版本先移到Skills目录以外的备份位置，**勿静默覆盖或保留两个同名Skill**：同名多版本会让人调用到旧版却不自知。安装后在新会话调用`$paper-figure-story`，并核对`VERSION`文件为`1.1.1`。

## 固定Tag安装（v1.1.0 及更早）

```powershell
$skillTarget = Join-Path $env:USERPROFILE '.codex/skills/paper-figure-story'
if (Test-Path -LiteralPath $skillTarget) { throw '目标已存在：请先备份到Skills目录以外。' }
git clone --branch v1.1.0 --single-branch https://github.com/Lu18835713910/paper-figure-story.git $skillTarget
```

历史版将`v1.1.0`替换为`v1.0.0`。仓库根目录就是Skill内容，clone到目标后不要再套一层paper-figure-story。固定Tag只在实际发布后可用。

升级/回退：确认本地无未保存修改，再`git fetch origin --tags`及`git switch --detach v1.1.0`或`git switch --detach v1.0.0`。不要强制推送、reset --hard或删除旧版本来升级。

## 环境与依赖

Python 3.10+（本候选实际验证环境为 **CPython 3.13.14 / Windows**）；依赖按`python -m pip install -r requirements.txt`安装：python-pptx、Pillow、pdfplumber、python-docx、lxml、PyMuPDF。`requirements.txt`已给出**本轮实测通过的最低版本**，更低版本未经验证。

Word/PPT处理使用本地已安装Microsoft Office；字体为Microsoft YaHei与Times New Roman。Codex桌面的load_workspace_dependencies可提供Node及Artifact Tool；它们不随本包重分发，普通Python环境不能据此承诺已具备PPT渲染能力。

安装后先执行以下预检，四项都应正常（命令与判读标准见[宿主依赖与能力边界](docs/HOST_REQUIREMENTS.md)）：

```text
python scripts/run_pfs.py --help
python scripts/render_logic.py --check-dependencies
python -m pip check
python -c "import pptx, fitz, docx, pdfplumber, lxml, PIL; print('ok')"
```

已验证Windows；其他系统、无Office或缺字体环境未通过等价视觉验收。不要从仓库下载Office、专有字体或API凭据。

## Agent快速使用

提供主PDF及实际取得的补件，可选PPTX模板，指定balanced与目标听众。Agent先读原文、Methods及图注，形成共享模型；再产出简图、逐Figure讲述和所需详细图/Workbook。用户不必手写JSON。

缺knowledge的纯CLI返回exit3及REVIEWED_KNOWLEDGE_REQUIRED/agent_handoff.json；由当前Agent继续语义整理，不取消来源审核门。索引不是科学理解。缺补件/未知n保持未核验，不把PARTIAL升为正式终审。

## 真实CLI（供Agent或开发者）

`run_pfs.py`只有5个子命令：`run`、`validate-products`、`render-products`、`deliver`、`check-delivery`。

```text
python scripts/run_pfs.py run --pdf paper.pdf --knowledge reviewed_M1.json --assets figures.json --cache-dir cache --outdir new_run --modes quick balanced full --products presentation --plan-only
python scripts/run_pfs.py render-products --network NETWORK --plan PLAN --metadata METADATA --outdir OUT --backend portable --development-preview
python scripts/run_pfs.py deliver --research-logic MODEL --graphs GRAPH_MANIFEST --workbook-bindings ANNOTATIONS --outdir OUT --request A B Workbook PNG PDF --office --development-preview
python scripts/run_pfs.py check-delivery --root OUT/deliverables --profile full
python scripts/polish_presentation.py --pptx finished.pptx --outdir qa_run
python scripts/build_research_workbook.py --help
```

注意三点：

1. **Visual Polish 不是 `run_pfs.py` 的子命令**，独立入口是`scripts/polish_presentation.py`（`--pptx` / `--outdir`，可选`--plan` / `--renderer`）。写错入口会直接报参数错误。
2. **`deliver` 强制要求显式 `--development-preview`**（argparse 必填参数）。它表示该案例仍需人工科学复核，不是软件预发布标识；不带该flag会立即失败而不是静默降级。`validate_story.py`不带该flag同样可以严格通过。
3. `plan-only`只生成并核验计划，不等于已生成PPT。导出需传`--node`、`--artifact-module`、`--presentation-skill`；缺少 Artifact 宿主时自适应主稿路径返回`HOST_BACKEND_REQUIRED`。没有Agent视觉计划时polish仅`QA_ONLY`。

详[PDF工作流](references/pdf_to_ppt_workflow.md)、[Visual Polish](references/visual_polish.md)及[逻辑导航交付合同](references/logic_navigation_delivery.md)。

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

## 交付范围与验收

历史UniPert示范请求组合得到 **49 项**受管产品；Full交付数量由请求和适用性决定，非固定49项（G5-R案例为38项）。历史UniPert示范交付中另有 **157 项**打包追加附件，属**特定案例的可选附加包**，不属于首发承诺产品。两者的边界、生成入口、验收命令与逐类来源见[交付包合同](docs/DELIVERY_PACKAGE.md)。

## 许可与版本边界

个人非商业使用｜源码可查看；不是OSI开源许可。完整授权见LICENSE。原图、PDF、Office、字体和用户资料的权利不由本包转授。v1.0历史原代码不修补，已知演示缺图等限制见历史Release说明。本候选的8项P2、字号/版面边界与科学审核边界见[已知限制](docs/KNOWN_LIMITATIONS.md)。


## 解压后的候选身份核对

先在解压后的`paper-figure-story`根目录执行下列只读命令。核对结果与候选随包提供、存放在目录外的文件Manifest；不得只核对VERSION字符串。

```text
python -B scripts/candidate_fingerprint.py --root .
python -B scripts/candidate_fingerprint.py --zip <原始ZIP完整路径> --zip-root paper-figure-story
```

包装目录`paper-figure-story/`只在ZIP比较时按显式参数去除。嵌套多一层、乱码改名、成员缺失、CRC损坏或内容SHA变化都需要先调查；不要自行修改文件或覆盖现有安装来“修正”身份。具体聚合算法见README的“候选身份复核”。本轮没有执行安装、覆盖或正式发布。


## 正式v1.1.1能力与验证边界

- portable路径已验证；建议先选择该路径并按INSTALL/宿主文档预检。Windows Office导出已在独立验收机器验证，不代表所有机器均已测试。
- Artifact宿主路径为NOT_TESTED；普通Figure主稿若依赖Artifact，须先验证宿主API与真实创建/导出，不得由portable成功推定宿主可用。
- 本次Full端到端复验复用已有科研模型及相关输入，不是“仅输入PDF即可全自动完成所有科学建模”的独立验证。M1、来源和解释由执行Agent依据论文登记与审核。
- 本案例科学终审PARTIAL，贡献核心审阅NOT_ASSESSED；工程Full不能升级科学审阅。
- Source Data未完整获得；多文档Supplementary一级来源登记存在限制，不能宣称补充材料科学来源完整闭环。
- Logic_B是独立可缩放大画布，不适合直接缩印A4；汇报使用可读局部视图。
- 297项测试经过独立复验，其中依赖的50项私有夹具文件不随公开ZIP分发（不是指只有50项测试）；普通用户不能仅凭公开ZIP复现完整维护回归。可执行公开合成测试，但不能冒充297项门禁。
- 旧版Info-ZIP可能使中文文件名乱码；推荐Windows原生Expand-Archive或Python zipfile解压，解压后核对逐文件SHA。
- 已接受的非阻断排版瑕疵（P8/P15换行、P14句号孤行、索引短续表留白）列入v1.1.2待办，不影响本次原生内容读取；不因此重开排版引擎开发。
- 本封包等待负责人批准实际发布，尚未执行安装、Git提交、推送、Tag或GitHub Release。

---



## RLD 真实模型交接

使用同一论文的 Scientific Index、Evidence Network 和 Research Logic。保留原文及其引用路径。使用随包正式 PFS 验证器，无法补足独立语义审阅时保留 PARTIAL。

```text
python scripts/rld_units.py --index index.json --network network.json --logic logic.json --out argument_units.json
python scripts/rld_diagnose.py --index index.json --network network.json --logic logic.json --out diagnostics.json
```

第二条命令自动派生论证单元。Agent 检查缺失字段和 source_statement_ids，回查原页及实验对照，记录待确认的前提与限制。逻辑标签不得冒充原文。归因候选需人工核对，尤其是已有干预与当前断言的关联。科研准确性 NOT_ESTIMABLE。

数值核验使用 rld_numeric.py --claims claims.json --registry registry.json --manifest manifest.json --manifest-anchor SHA256 --out numeric.json。规格见 references/rld_diagnosis_contract.md。外部锚点须来自独立冻结记录，同次生成的 manifest 与摘要不建立可信来源。判定仅适用于报告的均值；不认证统计显著性、机制或因果。原论文和私人数据不分发。
