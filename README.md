# Paper Figure Story（PFS）

**让每张 Figure 都有逻辑，让每项结论都有依据。**

从论文的科学问题出发，梳理实验设计、观察结果、论证关系与证据边界；生成科研逻辑图、逐 Figure 故事、可编辑汇报材料及学习手册。**v1.2.0 新增 Research Logic Diagnostics（RLD）**，进一步辅助检查科研推理、语言表述和论证结构。

![PFS 品牌与真实成果展示](docs/images/v1.1.1/hero.png)

**当前正式版本：v1.2.0（已发布）** · quick / balanced / full · 个人非商业使用 · 源码可查看

[**下载 v1.2.0**](https://github.com/Lu18835713910/paper-figure-story/releases/tag/v1.2.0) · [安装说明](INSTALL.md) · [本版更新](RELEASE_NOTES_v1.2.0.md) · [RLD 最小示例](examples/minimal_rld/README.md) · [历史版本](CHANGELOG.md)

> **定位**：PFS 帮助研究者读懂“为什么这样研究、证据如何连接”；RLD 帮助检查“这些推理、措辞与证据是否匹配”。Agent 与研究者需要审核原文，软件结构验证不等于科学事实或因果结论已经获得认证。

## 8 秒看看 PFS 的真实成果

![v1.1.1 已验收的真实产物演示，非自动运行录像](docs/images/v1.1.1/outputs-demo.gif)

[查看静态预览](docs/images/v1.1.1/outputs-demo-static.png) · [素材来源与裁切说明](docs/images/v1.1.1/ASSET_PROVENANCE.md)

*以上为 v1.1.1 阶段的真实展示案例，沿用至 v1.2.0；并非新版本 RLD 自动诊断的录像，也不代表任何论文的科学终审通过。*

## v1.2.0 新增：Research Logic Diagnostics（RLD）

RLD 接收**同一篇论文**已经建立的 Scientific Index、Evidence Network 和 Research Logic，从有源节点与语句派生论证单元，再进行分层诊断。它不是脱离 PFS 的“任意 PDF 一键审稿器”。

```text
论文全文、Figure、Methods 与可用补件
          │  Agent 依据原文登记、核对
          ▼
 Scientific Index ── Evidence Network ── Research Logic
          │                    │                │
          └────────────────────┴────────────────┘
                               ▼
                    论证单元（argument_units）
                               ▼
        科研逻辑检查 · 语言逻辑检查 · 表达逻辑检查
                               │
                               ▼
               有来源的疑点、归因候选、待核查事项
               （数值主张可调用单独的可信比较路径）
```

| 诊断方向 | 主要检查什么 | 必须保留的边界 |
|---|---|---|
| **科研逻辑** | 主张与证据是否对应，干预、对照和读出是否支持所述推理 | 网络中有干预不等于当前结论有因果证据 |
| **语言逻辑** | 因果断言、假说、相关性、否定与保留语的混用 | 中英语义识别是候选诊断，不是论文错误判决 |
| **表达逻辑** | 论证链、研究分支、结论与限制的衔接 | 缺失关系可能是 PFS 重建遗漏，不必然是论文缺陷 |
| **数值与来源核验** | 在可信登记簿中按组别、指标、时期、单位和比较基准复核指定主张 | 报告均值比较不证明统计显著性、实验因果或机制 |

真实论文回归中，烟草案例从 PFS 工件派生 **15 个论证单元 / 9 条诊断疑点**；另一篇 Cell Reports 案例派生 **29 个论证单元 / 2 条疑点**。烟草预设的 30 条均值主张计算为 **14 SUPPORTS / 16 REFUTES**，与独立复算逐条一致。**这些数字是特定测试集上的流程和数值回归，不是论文错误计数、RLD准确率或普遍科学有效性。**

[阅读 RLD 诊断合同](references/rld_diagnosis_contract.md) · [查看可运行合成示例](examples/minimal_rld/README.md) · [v1.2.0 发布说明](RELEASE_NOTES_v1.2.0.md)

## PFS 原有能力：从科研问题到可编辑成果

### 1. 科研逻辑 A/B：概览与完整证据网络

研究并非按 Figure 编号机械排列。PFS 可以按有来源的真实关系呈现**并行、分叉、递进、比较与证据汇合**，且不把叙事顺序伪装成实验发生的时间顺序。

![PFS 实际科研逻辑 A 概览](docs/images/v1.1.1/logic-a.png)

![PFS 科研逻辑 B 的可读局部](docs/images/v1.1.1/logic-b-preview.png)

[打开完整 B 大画布](docs/images/v1.1.1/logic-b-complete.png) · *详细 B 为独立可编辑大画布，不能强行压进普通 16:9 幻灯片。*

### 2. 逐 Figure 科研故事与可编辑 PPT

每个重要 Figure 围绕“**为什么做 → 怎样比较 → 实际看到什么 → 支持哪层认识 → 还有什么限制**”组织讲述，不凭美观增加实验依赖。

![PFS 真实 PPT 逐 Figure 讲述区](docs/images/v1.1.1/figure-story.png)

*标题、文字与结构关系可使用 PowerPoint 原生对象；原论文 Figure 作为图片保留，不会伪造图内数据。示例未公开第三方论文原图。*

### 3. Research Logic Workbook

![PFS 真实 Research Logic Workbook Methods 页面](docs/images/v1.1.1/workbook.png)

结合 Methods、实验对照、结果、来源与限制生成学习资料（DOCX；PDF 需在相应宿主实际导出及检查）。示例来自先前已验收案例，不代表新版本在任意环境的 Word/Office 导出均通过。

### 4. Visual Polish 与三档深度

Visual Polish 在科研内容已确认后处理视觉表达：统一版面、连接线、留白与阅读方向，**不擅自修改科学事实、证据边或结论强度**。

| 模式 | 主要用途 |
|---|---|
| `quick` | 快速抓住科学问题、主要任务与发现 |
| `balanced`（默认） | 平衡逐 Figure 讲述与证据解释，适合组会、正式汇报 |
| `full` | 在有充分原文、方法和证据输入时展开完整请求范围，并执行更严格的交付检查 |

模式代表展开深度，不是自动科学准确性等级；页数和产物以任务、来源及宿主能力为准。

## 安装与快速开始

请从**[正式 v1.2.0 Release](https://github.com/Lu18835713910/paper-figure-story/releases/tag/v1.2.0)**下载：

- [`Paper-Figure-Story-v1.2.0.zip`](https://github.com/Lu18835713910/paper-figure-story/releases/download/v1.2.0/Paper-Figure-Story-v1.2.0.zip)
- [`Paper-Figure-Story-v1.2.0.zip.sha256`](https://github.com/Lu18835713910/paper-figure-story/releases/download/v1.2.0/Paper-Figure-Story-v1.2.0.zip.sha256)

正式 ZIP SHA-256：

```text
14b216a5188b9bf811bd1443a23d049ea301f39ce3edb6eec5d16ad3d1c43a42
```

在 Windows PowerShell 中，下载后于 ZIP 所在目录运行以下示例；**已有同名Skill请先备份到Skills目录之外，不静默覆盖。**

```powershell
$target = Join-Path $env:USERPROFILE '.codex\skills\paper-figure-story'
if (Test-Path -LiteralPath $target) { throw '目标Skill已存在，请先移至Skills目录外备份。' }
Expand-Archive -LiteralPath '.\Paper-Figure-Story-v1.2.0.zip' -DestinationPath '.\pfs_v120'
New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
Copy-Item -LiteralPath '.\pfs_v120\paper-figure-story' -Destination $target -Recurse
```

安装后应存在 `paper-figure-story/SKILL.md`；如果解压结构不同，以实际 ZIP 内容和[安装文档](INSTALL.md)核对。也可以通过固定 Tag 获取代码：

```bash
git clone --branch v1.2.0 --single-branch https://github.com/Lu18835713910/paper-figure-story.git
```

在支持本地Skills的Agent里提供论文和可用补件，例如：

> 使用 $paper-figure-story，按 balanced 模式梳理这篇论文。先核对全文、Methods、Figure 图注和来源，重建科研问题、真实实验与证据链；生成科研逻辑 A/B、逐 Figure 汇报材料和所需学习手册，保留限制及待人工核查事项。

**需要运行RLD时**，先让Agent完成有来源的PFS三件工件，再使用包内入口（以下文件名为示例）：

```bash
python scripts/rld_units.py --index index.json --network network.json --logic logic.json --out argument_units.json
python scripts/rld_diagnose.py --index index.json --network network.json --logic logic.json --out diagnostics.json
```

第二条命令可以从三件工件直接派生论证单元；Agent仍须回查缺失主张、前提、来源语句、实验对照和科研语境。数值复核须由**独立固定的证据登记簿与外部可信摘要**支持，详细参数及判定规则见[RLD合同](references/rld_diagnosis_contract.md)和[Skill说明](SKILL.md)。这不表示任意PDF里的数字能自动得到可靠结论。

## 已知限制与科学边界

- **科研审核**：RLD 是辅助诊断，不能替代论文作者、领域专家、人工审阅或同行评议。`scientific_accuracy=NOT_ESTIMABLE`。Cell Reports 合规输入仍为 `PARTIAL`，F5疑点保持 `OPEN`，烟草 `AU_L_CL_REG` 的归因仍待人工裁定。部分论证单元缺少直接登记的主张，必须回查原文。
- **数值解释**：14 SUPPORTS / 16 REFUTES 仅对应事先规定的均值比较；不等于统计显著性、论文错误条数或因果结论。来源摘要必须独立保管，不能与修改后的数据一起自证。
- **渲染与宿主**：v1.2.0 发布验收没有重跑完整PPTX渲染；Workbook和投影仍存在既有环境/输入限制。portable逻辑图、主PPT生成、Office导出和Artifact宿主属于不同能力门，成功一种不证明另一种通过。
- **模型来源**：科研事实由执行Agent依据论文登记；只有PDF且缺少经过审核的知识模型时，CLI不会自动证明机制。未获得的补充资料不可宣称已审核。
- **公开资产**：不分发内部科研论文、真实私有模型、canonical登记簿或未获授权的第三方Figure；公开案例及展示资料见[素材来源说明](docs/images/v1.1.1/ASSET_PROVENANCE.md)。

[详细已知限制](docs/KNOWN_LIMITATIONS.md) · [宿主依赖](docs/HOST_REQUIREMENTS.md) · [交付包合同](docs/DELIVERY_PACKAGE.md) · [测试范围](TESTING.md)

## 版本、示例与历史

| 版本 | 主要更新 | 下载 |
|---|---|---|
| **v1.2.0（当前）** | PFS→RLD真实模型交接；科研、语言与表达逻辑候选诊断；可信数值比较 | [正式Release](https://github.com/Lu18835713910/paper-figure-story/releases/tag/v1.2.0) |
| v1.1.1 | 科研逻辑A/B、逐Figure讲述、Workbook、发布校验与既有工具链 | [历史Release](https://github.com/Lu18835713910/paper-figure-story/releases/tag/v1.1.1) |
| v1.1.0 | 共享证据关系及视觉、内容和交付工作流完善 | [历史Release](https://github.com/Lu18835713910/paper-figure-story/releases/tag/v1.1.0) |
| v1.0.0 | 初期逐Figure故事和可编辑学术汇报案例 | [历史Release](https://github.com/Lu18835713910/paper-figure-story/releases/tag/v1.0.0) |

[原生Atera公开示例](examples/atera/README.md) · [PFS v1.0 历史首页](docs/legacy/README_v1.0.md) · [v1.1.1版本说明](RELEASE_NOTES_v1.1.1.md) · [v1.2.0版本说明](RELEASE_NOTES_v1.2.0.md) · [更新历史](CHANGELOG.md)

## 许可证、版权与反馈

本项目采用 **Personal Non-Commercial Use License**：个人非商业使用、源码可查看，**不是 MIT、Apache 或 OSI 意义的开源许可证**。科研论文原图、数据和商标受其各自权利约束。详见[LICENSE](LICENSE)及[公开材料说明](PUBLICATION_NOTES.md)。

[提交问题与反馈](https://github.com/Lu18835713910/paper-figure-story/issues) · [安装与依赖](INSTALL.md) · [返回页首](#paper-figure-storypfs)
