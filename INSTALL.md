# 安装与使用｜PFS v1.2.0

**当前正式版本为v1.2.0。** 本页适用于Windows PowerShell下的Codex用户级Skill安装，以及从v1.0.0、v1.1.x升级到v1.2.0。先备份旧目录，再替换为新版；不会将旧脚本与新脚本混在同一活动Skill目录中。

> **发布快照边界：** Git Tag `v1.2.0`和正式Release ZIP是已发布快照；其内部旧版`INSTALL.md`不会随主分支文档更正自动变化。本页为当前在线说明，仍下载原正式ZIP并校验原SHA；不会改变Tag或正式资产身份。

## 让Agent直接安装或升级（从仓库链接开始）

用户不需要自己写PowerShell安装命令。只需要向具有本地文件与终端权限的Agent发送：

> 给我安装或更新这个Skill：https://github.com/Lu18835713910/paper-figure-story

执行Agent应读取本仓库[AGENTS.md](AGENTS.md)，并在当前用户的电脑上按下列步骤操作：

1. **确认真正的Skill安装位置。** Codex用户级默认目录为`~/.codex/skills/paper-figure-story`；有的使用者还配置了工作区级Skill或其他Agent宿主。先定位活动目录和重名副本，不能仅凭默认目录猜测。
2. **使用单独的干净main克隆。** 从`https://github.com/Lu18835713910/paper-figure-story.git`克隆到Skill目录以外的临时/工作位置，检查`git remote -v`、`VERSION`、`SKILL.md`与安装器源码，确认是可信仓库和预期版本。默认使用`main`是为了获得发布后维护的安全安装与调用文档；不是宣称原v1.2.0 ZIP已更新。
3. **执行预检和安全替换：**

   ```bash
   python scripts/install_pfs_skill.py --dry-run
   python scripts/install_pfs_skill.py
   ```

   从克隆仓库根目录运行。对于其他已核实的Agent技能目录，明确提供`--target /absolute/path/to/paper-figure-story`（预检和安装使用相同参数）。安装器只复制已登记的普通文件，校验文件哈希，不复制Git目录及未跟踪私人文件。旧版整个目录备份到当前Skills目录之外，安装失败会尝试回滚。
4. **核对结果。** 查看安装器输出的`version`、`revision`、`target`、`backup`；默认用户级安装的 Python 备份位于 `~/.codex/pfs-skill-backups/`，下方 Windows ZIP 流程的备份位于 `~/pfs-skill-backups/`。在新会话确认Agent确实加载此`SKILL.md`和`VERSION=1.2.0`。若存在其他活动路径的同名Skill，分别报告且不得假称已全部覆盖。
5. **不要直接执行旧版Tag中的安装说明，也不要在旧目录中`git pull`或覆盖合并。** 旧文件可能残留，或用户修改被覆盖。如果缺少Git、Python、主机权限，明确说明阻碍；不要将未完成安装冒充成功。

适用于Windows、macOS与Linux上的具备Python 3.10+和Git的本地Agent；**目前仅进行了隔离文件系统安装/回滚测试，没有证明所有Agent宿主能发现并加载Skill**。本页原有Windows ZIP+SHA安装方式仍作为固定正式发布包的替代安装入口。

## 正式版本与下载

- [v1.2.0正式Release](https://github.com/Lu18835713910/paper-figure-story/releases/tag/v1.2.0)
- [Paper-Figure-Story-v1.2.0.zip](https://github.com/Lu18835713910/paper-figure-story/releases/download/v1.2.0/Paper-Figure-Story-v1.2.0.zip)
- [正式SHA-256文件](https://github.com/Lu18835713910/paper-figure-story/releases/download/v1.2.0/Paper-Figure-Story-v1.2.0.zip.sha256)

正式ZIP SHA-256：`14b216a5188b9bf811bd1443a23d049ea301f39ce3edb6eec5d16ad3d1c43a42`。旧版v1.1.1/v1.1.0/v1.0.0均为历史发布版，新安装与升级推荐使用v1.2.0。

## Windows首次安装与安全覆盖升级

在已下载ZIP的文件夹打开**Windows PowerShell**，复制运行下方完整命令。首次安装时直接安装；如果`~/.codex/skills/paper-figure-story`已有旧版，则先将旧目录整体移到`~/pfs-skill-backups/`中的唯一备份目录，再安装v1.2.0。安装过程中会验证正式ZIP SHA、ZIP目录结构和安装后版本；复制或版本校验失败时尝试恢复旧目录。

```powershell
$ErrorActionPreference = 'Stop'
$zip = (Resolve-Path -LiteralPath '.\Paper-Figure-Story-v1.2.0.zip').Path
$expectedSha = '14b216a5188b9bf811bd1443a23d049ea301f39ce3edb6eec5d16ad3d1c43a42'
if ((Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedSha) {
    throw 'ZIP SHA-256不匹配：停止安装，请从正式Release重新下载。'
}

$skillRoot = Join-Path $HOME '.codex\skills'
$target = Join-Path $skillRoot 'paper-figure-story'
$backupRoot = Join-Path $HOME 'pfs-skill-backups'
$work = Join-Path $env:TEMP ('pfs-v120-' + [guid]::NewGuid().ToString('N'))
$backup = Join-Path $backupRoot ('paper-figure-story-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 6))
$oldMoved = $false

New-Item -ItemType Directory -Path $work -Force | Out-Null
try {
    Expand-Archive -LiteralPath $zip -DestinationPath $work
    $source = Join-Path $work 'paper-figure-story'
    if (-not (Test-Path -LiteralPath (Join-Path $source 'SKILL.md') -PathType Leaf) -or
        -not (Test-Path -LiteralPath (Join-Path $source 'VERSION') -PathType Leaf)) {
        throw 'ZIP目录结构不符合预期：未找到paper-figure-story/SKILL.md和VERSION。'
    }
    if ((Get-Content -LiteralPath (Join-Path $source 'VERSION') -Raw).Trim() -ne '1.2.0') {
        throw 'ZIP内部VERSION不是1.2.0：停止安装。'
    }

    New-Item -ItemType Directory -Path $skillRoot -Force | Out-Null
    if (Test-Path -LiteralPath $target) {
        $existing = Get-Item -LiteralPath $target -Force
        if (-not $existing.PSIsContainer -or
            (($existing.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)) {
            throw '目标不是普通目录（可能是软链接）：请手动核对安装位置。'
        }
        New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
        Move-Item -LiteralPath $target -Destination $backup
        $oldMoved = $true
    }

    try {
        Copy-Item -LiteralPath $source -Destination $target -Recurse
        if ((Get-Content -LiteralPath (Join-Path $target 'VERSION') -Raw).Trim() -ne '1.2.0' -or
            -not (Test-Path -LiteralPath (Join-Path $target 'SKILL.md') -PathType Leaf)) {
            throw '安装后版本验证失败。'
        }
        Write-Host "已安装PFS v1.2.0：$target"
        if ($oldMoved) { Write-Host "旧版本已备份：$backup" }
    } catch {
        if (Test-Path -LiteralPath $target) {
            Remove-Item -LiteralPath $target -Recurse -Force
        }
        if ($oldMoved) { Move-Item -LiteralPath $backup -Destination $target }
        throw
    }
} finally {
    if (Test-Path -LiteralPath $work) { Remove-Item -LiteralPath $work -Recurse -Force }
}
```

**升级原则：** 这是整个目录的安全替换，不是`Copy-Item`直接合并覆盖。你此前修改的Skill文件不被自动迁移，仍在备份目录中。请先结束正在运行的PFS任务再升级，并在升级后新开Codex会话。上述路径仅适用于Codex用户级默认安装；若实际启用的是工作区级Skill或其他Agent宿主的目录，必须先核对实际加载路径，不能假定会搜索并覆盖全电脑所有同名Skill。目标为软链接/重解析点时会主动停止，防止误操作。

### 验证当前电脑安装

```powershell
$target = Join-Path $HOME '.codex\skills\paper-figure-story'
Get-Content -LiteralPath (Join-Path $target 'VERSION')
Test-Path -LiteralPath (Join-Path $target 'SKILL.md')
python (Join-Path $target 'scripts\run_pfs.py') --help
```

应分别看到`1.2.0`、`True`，且帮助中有`run`、`validate-products`、`render-products`、`deliver`、`check-delivery`五个子命令。**新会话中也应让Agent报告实际读取的SKILL.md路径和VERSION**；仓库本身显示v1.2.0不能证明旧会话已经重新加载。

### Git方式（仅供全新目录或固定Tag参考）

```powershell
git clone --branch v1.2.0 --single-branch https://github.com/Lu18835713910/paper-figure-story.git "$HOME\.codex\skills\paper-figure-story"
```

已有同名目录时不要直接`git clone`到该路径；请使用前述ZIP安全升级流程。不要用`git reset --hard`、`git clean -fd`等可能丢失本地修改的操作来升级。

## 环境与依赖

Python 3.10+（历史v1.1.1的实测环境为 **CPython 3.13.14 / Windows**）；依赖按`python -m pip install -r requirements.txt`安装：python-pptx、Pillow、pdfplumber、python-docx、lxml、PyMuPDF。`requirements.txt`已给出**本轮实测通过的最低版本**，更低版本未经验证。

Word/PPT处理使用本地已安装Microsoft Office；字体为Microsoft YaHei与Times New Roman。Codex桌面的load_workspace_dependencies可提供Node及Artifact Tool；它们不随本包重分发，普通Python环境不能据此承诺已具备PPT渲染能力。

依赖准备后，在Skill根目录执行下列四项预检（命令与判读标准见[宿主依赖与能力边界](docs/HOST_REQUIREMENTS.md)）：

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
python scripts/run_pfs.py run --pdf paper.pdf --knowledge reviewed_M1.json --assets figures.json --research-logic research_logic.json --cache-dir cache --outdir new_run --modes balanced --products with-network --plan-only
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

上述run示例假定Agent已根据论文准备并验证有来源的M1和Research Logic；它不会从纯PDF自动生成上述JSON。

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

个人非商业使用｜源码可查看；不是OSI开源许可。完整授权见LICENSE。原图、PDF、Office、字体和用户资料的权利不由本包转授。v1.0历史原代码不修补，已知演示缺图等限制见历史Release说明。历史v1.1.1候选的8项P2、字号/版面边界与科学审核边界见[已知限制](docs/KNOWN_LIMITATIONS.md)。

## v1.2.0当前使用边界

- `balanced`只决定内容展开深度，**不是**多分支拓扑开关。Agent必须依据实际论文识别一条或多条研究主线，不能为了好看虚构分叉。
- **同源科研逻辑A/B**需由Agent建立并审核Research Logic，通过`--research-logic`接入；完整B需选择`--products with-network`。旧默认overview/detailed兼容路径不应冒充已审的同源A/B模型。
- A是16:9科研逻辑概览，B是全部已登记节点和关系的原生可编辑大画布，C是逐Figure故事。真实存在的并行、比较、共享方法和证据汇合必须保留；如论文只有一条主线则应如实表达。
- `run_pfs.py run`不是单命令无人值守论文分析。缺少`--knowledge`时返回`REVIEWED_KNOWLEDGE_REQUIRED`；科学事实由实际调用Skill的Agent从论文和可用补充材料中审核并登记。
- RLD可选：需来自同一论文的Scientific Index、Evidence Network和Research Logic；疑点需回查原文，不能据此直接判定论文造假。
- 逻辑图的portable后端不等于从零生成普通Figure主PPT；Artifact宿主、Office导出、Workbook完整性与人工科学/视觉验收各有独立边界。
- 原v1.2.0 Release ZIP/Tag中的历史安装说明不会因这次在线文档更新而改变。要让离线包也带上新文档，需要另发维护版，而不应无声替换已公布SHA的正式ZIP。

参考：[v1.2.0发布说明](RELEASE_NOTES_v1.2.0.md) · [宿主要求](docs/HOST_REQUIREMENTS.md) · [历史已知限制](docs/KNOWN_LIMITATIONS.md) · [Skill说明](SKILL.md)。
