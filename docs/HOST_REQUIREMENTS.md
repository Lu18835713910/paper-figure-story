# 宿主依赖与能力边界｜v1.1.1

本文件回答一个问题：**在没有 Artifact 宿主的机器上，PFS 到底能做到哪一步。** 三档能力必须分开陈述，不得用一档的通过掩盖另一档的未验证。

---

## 1. 三档能力（不要混谈）

| 档位 | 能力 | 依赖 | 本版本验证状态 |
|---|---|---|---|
| **A. portable** | PDF 索引、M1/Schema 校验、A/B/局部逻辑图的**原生 PPTX 渲染**、按 `page-map` 合稿进已有主稿、Workbook DOCX 生成、`deliver` / `check-delivery` / `validate_story` | 仅 `requirements.txt` 的 6 个 Python 包 | ✅ **VERIFIED**（本轮实测） |
| **B. Office 导出** | 上述产物的**实际 PNG / PDF**、Office 输入回执 | 本地安装的 Microsoft PowerPoint / Word + COM | ⚠️ 本机具备，历史案例已实跑；干净机器未验证 |
| **C. Artifact 宿主** | **从零生成自适应主稿**（`render_adaptive_pptx.mjs` 路径） | `node` + Artifact 模块 `.mjs` + `presentation-skill/container_tools/` 三个文件 | ❌ **NOT_TESTED**（本机缺 Artifact 模块） |

一句话：**A 可用不等于 C 可用；B 可用也不等于 C 可用。** 缺 C 时主稿必须先有 `base.pptx`，再用 `page-map` 合稿，不能声称"已从零生成自适应主稿"。

---

## 2. C 档的三件套

| 组件 | 作用 | 缺失时的准确表现 |
|---|---|---|
| `node`（v18+，本机 v22.22.2） | 执行 `.mjs` 渲染器 | `--node` 取不到可执行文件 → `HOST_BACKEND_REQUIRED` |
| Artifact 模块 `.mjs` | 提供 `finalizePresentation` 等原生 PPTX 装配 API；可经 `--artifact-module` 或环境变量 `ARTIFACT_TOOL_MODULE` 指定，未指定时回退 `import('@oai/artifact-tool')` | `HOST_BACKEND_REQUIRED` |
| `<presentation-skill>/container_tools/` | 需含 `artifact_tool_utils.mjs`、`inspect_presentation_package_integrity.py`、`inspect_presentation_layout_geometry.py` | `Missing --presentation-skill` 或模块导入失败 |

对应入口：

- `python scripts/render_research.py <knowledge> --assets <assets> --outdir <dir> [--node <node>] [--artifact-module <mjs>]`
- `python scripts/run_pfs.py run ... --node <node> --artifact-module <mjs> --presentation-skill <dir>`
- `python scripts/run_pfs.py render-products ... --backend host`（仅真实安装且接口兼容时使用）

历史实测（rc.1期140文件快照；冻结rc.4为155文件；C档Artifact宿主仍为NOT_TESTED，文件数变化不构成宿主验证）：

```text
$ python scripts/render_research.py <knowledge> --assets <assets> --outdir <out>
{"valid": false, "code": "HOST_BACKEND_REQUIRED",
 "error": "This adaptive path needs its optional host; no legacy scaffold is delivered as a finished PPT. Use run_pfs render-products for portable registered logic views."}
exit 1
```

这是**可操作的门禁**：报错直接给出 portable 替代路径，不是静默失败、也不是降级交半成品。

---

## 3. 预检步骤（不要硬编码开发者机器路径）

在 Skill 根目录依次执行，全部可复制粘贴；占位符由使用者按自己环境填写：

```text
# 1) Python 与包
python -V
python -m pip check

# 2) 正式 CLI 是否完整（应列出 5 个子命令）
python scripts/run_pfs.py --help

# 3) portable 后端自检（应输出 available: true, missing: []）
python scripts/render_logic.py --check-dependencies

# 4) Node 是否存在（找不到会打印 None，不报错）
python -c "import shutil; print(shutil.which('node'))"

# 5) Artifact 模块是否可以定位
python -c "import os; print(os.environ.get('ARTIFACT_TOOL_MODULE', '<unset>'))"

# 6) 宿主是否存在（没有宿主时应为 exit 1 + HOST_BACKEND_REQUIRED）
python scripts/render_research.py <knowledge.json> --assets <assets.json> --outdir <new-dir>
```

**判读规则**

| 观察结果 | 结论 |
|---|---|
| 3) `missing: []` | A 档可用，可开展索引/渲染/交付 |
| 4) 打印 `None` | C 档不可用，只能走 base deck + `page-map` 合稿 |
| 5) `<unset>` 且无 `--artifact-module` | C 档不可用 |
| 6) exit 1 且 `HOST_BACKEND_REQUIRED` | 符合预期，说明门禁生效；**不要**据此宣告交付失败 |
| 6) exit 0 | 宿主可用，但**仍需实际生成一次并在 PowerPoint 打开核验**才算验证 |

PowerPoint/Word 探测（B 档，Windows）：

```text
python -c "import win32com.client as w; w.Dispatch('PowerPoint.Application'); print('com ok')"
```

**`com ok` 只说明 COM 注册可用，不代表导出可用。** B 档是否成立，只能以一次 `--office` 运行是否真的产出 PDF/PNG 和 Office 回执为准；导出失败时同样必须**单独报告"渲染未验证"**，不能写成通过。无 `pywin32` 时直接以该次运行结果判断。

---

## 4. 环境验证矩阵（本版本）

| 环境 | 状态 | 依据 |
|---|---|---|
| Windows + CPython **3.13.14** + Office + 中英文字体 | **VERIFIED** | 本轮 `--help` / `--check-dependencies` / 缺 knowledge 门禁 / 缺宿主门禁 / `pip check`；历史回归在同一环境 229 项通过 |
| Windows + CPython 3.10–3.12 | `NOT_TESTED` | 代码声明 3.10+，本版本未在该区间实跑 |
| macOS / Linux | `NOT_TESTED` | 路径分隔符、字体替换、COM 导出均未验收 |
| 无 Office | 部分可用 | A 档可用；B 档不可用，PNG/PDF 与实际导出回执缺失 |
| 无 Artifact 宿主 | 部分可用 | A + B 可用；**从零自适应主稿不可用** |
| 无中英文字体（微软雅黑 / Times New Roman） | 明确失败 | 不静默替换字体 |

---

## 5. 依赖版本

`requirements.txt` 用**本轮实测版本**做最低版本：`python-pptx>=1.0.2`、`Pillow>=12.3.0`、`pdfplumber>=0.11.10`、`python-docx>=1.2.0`、`lxml>=6.1.3`、`PyMuPDF>=1.28.2`。

- 更低版本**未安装、未运行**，因此不写更低的下限，也不采用"看起来合理"的猜测版本号。
- 若要放宽下限：在具备该旧版本的环境执行第 3 节预检 + 一次 A 档真实渲染，把版本与结果记入维护记录，再改 `requirements.txt`。
- `PyMuPDF` 1.24+ 已弃用 `fitz` 顶层 API，运行日志出现 `The fitz API is deprecated` 属已知提示，不影响功能。

---

## 6. 常见误判

1. "`--check-dependencies` 通过 = PPT 渲染能力齐全" → 错。它只证明 **A 档**，C 档仍需 Node + Artifact 宿主。
2. "`node -v` 有版本 = 宿主可用" → 错。还缺 Artifact 模块与 `container_tools` 三件套。
3. "路径存在 = 可用" → 错。需实际跑一次并打开产物核验；未跑过一律 `NOT_TESTED`。
4. "缺宿主 = 软件有缺陷" → 错。这是**声明的能力边界**，且有 `HOST_BACKEND_REQUIRED` 明确门禁。

当前正式门禁为21套件/297项，以实际正式配置与回执为准，参见TESTING.md；229项仅为历史记录。
