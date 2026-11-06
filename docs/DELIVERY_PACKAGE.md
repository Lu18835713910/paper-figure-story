# 交付包合同｜v1.1.1-rc.4

本文件界定 **"正式交付包"到底承诺什么**，并把历史 UniPert 示范交付中打包追加的附件明确划到合同之外。**不要把它读成"所有新论文都会产出 206 个文件"。**

---

## 1. 正式请求决定交付范围；下表为历史UniPert示例

`run_pfs.py deliver` 是唯一的正式交付入口，历史UniPert特定请求组合曾得到 **49 项**，这不是所有Full交付的固定数量：

| 类别 | 条数 | 内容 |
|---|---:|---|
| `main` | 1 | 主稿 PPTX（`PPT/Main.pptx`） |
| `A` | 1 | 概览逻辑图（`PPT/Logic_A.pptx`） |
| `B` | 1 | 独立完整 B（`PPT/Logic_B.pptx`，原尺寸、原生可编辑） |
| `Workbook` | 1 | 学习手册（`Workbook/Workbook.docx`） |
| `PDF` | 4 | main / A / B / Workbook 实际导出 PDF |
| `PNG` | 30 | A/B 单页预览、main 逐页预览、Workbook 逐页预览（实际导出） |
| `attachment` | 6 | `Complete_B.editable.pptx` 等同源相对链接附件 |
| `coverage_audit` | 5 | `Audit/basis.json`、`Contribution.review.json`、`LogicGraph.contract.json`、`ResearchLogic.source.json`、`Workbook.receipt.json` |
| **合计** | **49** | |

### 1.1 生成入口

```text
python scripts/run_pfs.py deliver \
  --research-logic MODEL --graphs GRAPH_MANIFEST \
  --main-pptx BASE.pptx --page-map PAGE_MAP --plan PLAN --metadata METADATA \
  --workbook-bindings ANNOTATIONS --figure-assets FIGURES \
  --contribution-review CONTRIB_REVIEW \
  --outdir OUT --request main A B Workbook PNG PDF --office --profile full \
  --development-preview
```

`deliver` 是**已有事实/缓存回放**，不是新论文自动理解。`--development-preview` 必填（见 `docs/KNOWN_LIMITATIONS.md` P2-4）。

### 1.2 验收范围（三项都必须 exit 0）

| 命令 | 覆盖 |
|---|---|
| `python scripts/run_pfs.py check-delivery --root OUT/deliverables --profile full` | Manifest 中每一条：存在性 + SHA + 相对链接 + 请求差额（在 206 项示范包上实测为 206 条全覆盖） |
| `python scripts/validate_story.py OUT/deliverables --delivery-manifest --logic-model MODEL --profile full --require-B` | 主稿/A/B/Workbook 结构、原生拓扑守恒、主稿节点与连接器真实性 |
| `python scripts/figure_assets.py validate OUT/Figures/figure_assets.json` | Figure 登记、ROI、指纹 |

`check-delivery` 对 Manifest 中的**每一条**做存在性 + SHA 核验，不只管 49 项产品。审计实测：改 1 字节 → `FILE_HASH_DRIFT`；截断 PNG → `FILE_HASH_DRIFT`；删除一页预览 → `MISSING_OR_EXTERNAL_FILE`，三种均 exit 2。

---

## 2. 合同之外：157 项示范附加包

历史 UniPert 示范交付的 `Manifest.json` 共 **206 条 = 49 官方 + 157 打包追加**。这 157 项：

- 由**候选之外的打包脚本**追加（`package_final.py`、`finalize_previews.py`、`export_graphs.py`、`c2_common.py`），这些脚本**不在候选内**，也**未**被收录进本 Skill；
- 属**特定案例的可选附加包**（来源摘录、审计证据、Word 逐页预览、Office 回执）；
- **不是**所有新论文都必须生成的标准产品，**不构成**首发承诺；
- 追加过程为**纯新增**：49 项产品的 SHA **0 变化**。

### 2.1 逐类来源（157 项）

| 类别 | 条数 | 打包步 | 来源输入 | 溯源级别 |
|---|---:|---|---|---|
| 来源摘录 `Audit/SourceExcerpts/*.txt` | 80 | 复制 `scientific_index` 源缓存块 | 案例 `scientific_index.json` 的 `sources[].path` | **item-level**：`SourceCacheLocations.csv` 记录 source_id / 原缓存路径 / 包内路径 / SHA / 字符区间 |
| 科学输入 `Audit/ScientificInputs/*.json` | 5 | 复制案例输入模型 | 案例 `inputs/` 同名文件 | **item-level**：逐字节复制 |
| 来源审核 `Audit/SourceReview/*.json` | 7 | 复制案例审计记录 | 案例 `audit/` 同名文件 | **item-level**：逐字节复制 |
| 来源审核生成件 `SourceCacheLocations.csv`、`README.md` | 2 | 由索引表生成 / 撰写的目录说明 | 案例 `scientific_index.json` | **generated**：内容可由索引重建 |
| Figure 登记 `Figures/figure_assets.json` | 1 | 改写资产路径 | 案例 `inputs/figure_assets.json` | derived：id/页码/bbox/DPI/SHA 不变，仅路径改写 |
| Figure 原图 `Figures/*.png` | 13 | 复制已登记裁剪 | `figure_assets.json` 对应 id | derived：按登记 bbox+DPI+PDF 页裁剪 |
| 局部视图 PDF `PPT/Logic_{repr,predict,space,cross}.pdf` | 4 | PowerPoint 按 1920px 宽导出 | `PPT/Logic_<view>.pptx`（属 49 项） | derived：整页导出，不重排 |
| Office 回执 `Audit/Office/*.receipt.json` | 4 | 复制 Office 输入回执 | Logic_A / Logic_B / Main / Workbook_word | derived：按产品 1:1 |
| Workbook 页预览 `Previews/Workbook/page-0NN.png` | 34 | 复制 Word 实际导出的逐页光栅 | `Workbook/Workbook.docx`（属 49 项） | derived：第 N 页 |
| Workbook 图文跨页 `Previews/Workbook_F1..F6.png` | 6 | 双页横向拼贴 | 第 {10,11}…{20,21} 页预览 | derived：固定拼贴规则 |
| 全稿联系表 `Previews/Main_contact.png` | 1 | 4 列联系表 | `Previews/Main/slide-*.png`（属 49 项） | derived：固定缩略尺寸 |
| **合计** | **157** | | | 92 item-level + 2 generated + **63 derived** |

逐条明细（含 SHA）见 [DELIVERY_ATTACHMENT_PROVENANCE.csv](DELIVERY_ATTACHMENT_PROVENANCE.csv)。

> 审计报告中"63 项无溯源附件"即为上表 **derived** 的 63 项。本候选把它们从"只记 SHA"提升为"记录生产者 + 来源输入 + 可复核的派生规则"，但**仍不宣称可由候选独立再现**——派生规则可读，不等于打包步骤已入库。

---

## 3. 可复现性边界（必须同时说明）

| 声明 | 是否成立 |
|---|---|
| 49 项官方交付可由候选 CLI 独立生成 | ✅ 成立（唯一入口 `deliver`） |
| 49 项产品可用 `check-delivery` / `validate_story` 全量核验 | ✅ 成立 |
| 157 项附加包有逐类来源与派生规则 | ✅ 成立 |
| **206 项完整扩展包可由候选独立重建** | ❌ **不成立**：打包脚本不在候选内，重建需要案例私有输入 |
| 157 项是"所有新论文的标准产物" | ❌ 不成立：属特定案例可选附加包 |

**发布承诺以正式请求、适用文件及真实Manifest为准；不承诺固定49或206项。** 若负责人后续要求"206 项可复现"，需要另立任务：审查并整理打包脚本及全部依赖、用正式输入独立重建、核对 Manifest/SHA/相对路径/内容身份、确认无私人材料——这属于独立工作，不在本候选声明范围内，也不允许仅以文字说明冒充已实现。

---

## 4. Manifest 字段说明（避免误读）

| 字段 | 含义 | 注意 |
|---|---|---|
| `files[]` | 每个交付文件的 `path` / `sha256` / `product` / `logic_snapshot` / `scientific_review` | 追加项的 `product` 为 `attachment` 或 `PNG`，`scientific_review` 沿用 `PARTIAL` |
| `provenance.supplemental_attachments` | 一句话说明追加附件性质 | 未量化到 49/157，故本文件给出精确拆分 |
| `provenance.automatic_fields` = 84 | Workbook 教学字段自动组装数 | 另有 6 项结构化定量记录 |
| `provenance.new_paper_extraction` = false | 该包未做新论文抽取 | 回放已有登记事实 |
| `Workbook.receipt.render_status` | 构建阶段字段 | `PENDING` 与"已导出 34 页"并存，属正常；Office 回执另存（P2-8） |

---

## 5. 一句话结论

**正式交付完整性由请求、适用性、真实文件身份及合同验证决定；49与206都是历史案例数量，不能生成占位文件凑数。G5-R的38项也不是通用固定数量。结构Full不等于科学终审。**
