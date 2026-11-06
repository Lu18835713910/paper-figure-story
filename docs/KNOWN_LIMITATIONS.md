# rc.4已知限制索引与rc.1历史记录

当前候选为`1.1.1-rc.4`，当前边界见[RC4_ACCEPTED_LIMITATIONS.md](RC4_ACCEPTED_LIMITATIONS.md)。以下为rc.1历史审计记录，页码、数量和当时未验证状态仅适用于历史案例，不能代替rc.4本次实测回执。

# 已知限制｜v1.1.1-rc.1

本文件记录发布候选 **`1.1.1-rc.1`** 已知但**未在本版修复**的限制，以及本次发布不得声称的能力。所有条目均有实测或审计来源；未验证项明确标为 `NOT_TESTED`，不写成通过。

适用范围：本版本承诺"工程可交付 + 门禁可复核"，**不承诺**科学终审通过、用户视觉验收通过、干净机器已验证或 Artifact 宿主能力已验证。

---

## A. 视觉与版面（后续维护，v1.1.2 处理）

### P2-1 主稿 P03 文字高度越界

- 现象：主稿第 3 页两处文本框高度超出容器 **1.80pt / 0.96pt**；文字未丢失、未被裁切。
- 来源：模板既有行高，跨版本存在，非本轮改动引入。
- 影响：视觉上可能在严格 PowerPoint 检查中报"溢出"告警。
- 处置：后续维护（模板行高调整）。本版不做，避免在发布候选阶段改渲染引擎。

### P2-2 Workbook 第 9 页孤行续表

- 现象：第 9 页出现 1 行表格延续 + 约 80% 空白。
- 影响：阅读节奏，不影响内容完整性。
- 处置：后续维护（表格 `keep-with-next` 策略）。

### P2-3 Workbook Figure 页图片受高度上限约束

- 现象：Figure 页图片受 **396pt 高度上限**约束，F2/F5 仅占页宽 **45–48%**；整图小字需放大阅读。
- 原因：版面策略，改动需动 `build_research_workbook.py`（当前冻结）。
- **替代路径**：需要大图时请用 PPT 原生 B（`PPT/Logic_B.pptx`，原尺寸可缩放），不要把 Workbook 内嵌图当作大图验收依据。

### P2-6 Workbook 内嵌 B 预览分辨率低于交付预览

- 现象：Word 内嵌 B 预览 **1920px**，低于交付 `Previews/Logic_B.png` 的 **3825px**。
- 判读：**Word 内的 B 是缩览，权威 B 是 PPTX**。审计、印刷或放大阅读请引用 `PPT/Logic_B.pptx` 与其原尺寸导出。

### P2-7 最小字号表述需分层

- 正确表述：**节点正文 23.24–28.49pt；全画布最小 11.99pt（引文）**。主稿节点最低 12.79pt。
- 不再使用"正文最低 23.24pt"这类省略引文的说法，避免让读者以为全画布无小字。
- 工程下限：独立完整 B 的**绝对 10pt 下限**（`COMPLETE_B_READABILITY_LIMIT`），用于拦截明显小字静默通过；10pt 不是"最佳字号"，也不构成视觉 PASS。

---

## B. 接口与流程（本版披露，不修）

### P2-4 `deliver` 必须显式 `--development-preview`

- `run_pfs.py deliver` 的 `--development-preview` 是 argparse **必填**参数，缺失即失败。
- 语义：表示该案例仍需人工科学复核，**不是软件预发布标识**。
- 影响：脚本化调用需要显式传参；`validate_story.py` 不带该 flag 可同样严格通过。

### P2-8 `Workbook.receipt.render_status=PENDING` 与已导出并存

- 现象：`Audit/Workbook.receipt.json` 中 `render_status` 为 `PENDING`，而 Workbook 已实际导出 34 页。
- 解释：`PENDING` 是**构建阶段字段**，不代表未导出；Office 渲染回执另存于 `Audit/Office/Workbook_word.office.input.receipt.json`。
- 判读：以 Office 回执与 `Previews/Workbook/` 实际页数为准。

---

## C. 交付包（本版已文档化）

### P2-5 官方 49 项与示范追加 157 项

- 官方 `deliver` 受管产品 **49 项**；历史 UniPert 示范交付另有 **157 项**由候选外脚本追加的附件。
- 157 项**不是**所有新论文都必须生成的标准产品，也不是首发承诺的交付合同。
- 完整边界、生成入口、验收命令与逐类来源见 [交付包合同](DELIVERY_PACKAGE.md)。**不要把 206 说成官方门禁产物。**

---

## D. 环境、宿主与依赖

### G-17 从零生成自适应主稿需要 Artifact 宿主

- 本机具备 `node`，但**没有** `artifact_tool_utils.mjs`；`render_research.py` 在该环境下返回 `exit 1 / HOST_BACKEND_REQUIRED`（可操作报错，不是静默失败）。
- 因此：**portable 能力已验证；从零生成自适应主稿 `NOT_TESTED`**。
- 逐档能力与预检命令见 [宿主依赖与能力边界](HOST_REQUIREMENTS.md)。

### 操作系统与运行环境

| 环境 | 状态 |
|---|---|
| Windows + CPython 3.13.14 + Office + 中英文字体 | **VERIFIED**（本轮与历史回归实际运行） |
| Windows + CPython 3.10–3.12 | `NOT_TESTED` |
| macOS / Linux | `NOT_TESTED`（路径分隔符与字体替换未验收） |
| 无 Office | 无 PNG/PDF 实际导出与 Office 回执；portable 逻辑渲染仍可用 |
| 无中英文字体（Microsoft YaHei / Times New Roman） | 明确失败，不静默替换 |

### 依赖版本

`requirements.txt` 采用**本轮实测版本**作为最低版本。更低版本未安装、未运行，**不承诺可用**；如需放宽下限，必须先在具备旧版本环境的机器上执行 `HOST_REQUIREMENTS.md` 的预检并记录结果。

---

## E. 科学审核边界（不得升级）

- 当前真实案例科学终审为 **`PARTIAL`**：补充表 S1–S5 缺失；存在 Touchstone 计数冲突；未重算模型、未开展湿实验。
- `ESR1` 相关结论为**计算预测**，不等于实验验证。
- 贡献覆盖为 `COVERED_REGISTERED_CLAIMS/BRANCHES`：只说明**已登记输入**的投影范围，不证明论文全部核心贡献已被识别。
- 用户视觉验收 **`NOT_ASSESSED`**；工程测试通过不等于用户接受。
- 论文论证顺序不等于实验真实时间顺序；空间邻近不等于细胞通讯；预测细胞组成不等于 IF 验证。这些边界在产物中必须保留。

---

## F. 本版不得声称的事项

1. ❌ "科学终审通过"（实为 `PARTIAL`）。
2. ❌ "用户视觉验收通过"（实为 `NOT_ASSESSED`）。
3. ❌ "干净机器已验证"（安装与 Office 实机导出属下一阶段）。
4. ❌ "Artifact 宿主能力已验证"（`NOT_TESTED`）。
5. ❌ "206 项交付包可由候选独立复现"（官方合同为 49 项）。
6. ❌ "229 项回归已在本整理会话重跑"（本会话只做轻量验证，完整回归属下一独立会话）。
7. ❌ "v1.1.1 已发布 / Tag 已存在"（Tag 未创建）。

---

## G. 后续维护计划

| 项 | 计划 |
|---|---|
| P2-1 / P2-2 / P2-3 | v1.1.2：模板行高、表格 keep-with-next、Figure 页版面策略 |
| P2-6 | v1.1.2：统一 preview 导出像素 |
| 依赖下限放宽 | 在旧版本环境补测后调整，附实测记录 |
| 157 项可复现打包 | 若负责人要求 206 项可复现，需要审查并整理打包脚本 + 用正式输入独立重建，属独立任务 |
| 干净机器安装 | 下一阶段（需先备份并消除本机两个同名 Skill） |
