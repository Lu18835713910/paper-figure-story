# 测试与验收边界｜v1.1.1

## 1. 正式发布门禁

唯一正式测试门禁是**发布回归运行器**，不是 `unittest discover`：

```text
python -B scripts/run_release_regressions.py --config <regression_config.json> --outdir <新目录>
```

- 当前rc.4通过标准：配置声明的全部套件和测试身份均实际执行，源码/夹具SHA一致，0 FAIL、0 SKIP且退出码0。实际数量必须以本次配置和`regression_receipt.json`核对；不得沿用历史229或243作为本次结果。
- `--outdir` 必须是不存在的新目录（已存在则报 `OUTPUT_EXISTS` 并退出，避免覆盖历史失败记录）。
- 结果写入 `<outdir>/regression_receipt.json`：每套件的 `Ran` 数、`skipped` 数、退出码、源码 SHA、stdout/stderr SHA，以及夹具 SHA 校验结果。

运行器除了执行测试，还独立核验四件事，任何一项不符即退出 2：

| 核验 | 失败码 |
|---|---|
| 夹具文件存在且 SHA 与配置一致 | `FIXTURE_MISSING` / `FIXTURE_SHA_DRIFT` |
| 套件源码 SHA 与配置一致 | `TEST_SOURCE_DRIFT` |
| 实际 `Ran N` 与 AST 声明的测试数一致 | `TEST_COUNT_MISMATCH` |
| 实际执行到的测试名与声明集合一致 | `TEST_IDENTITY_MISMATCH` |
| 出现任何 SKIP | `TEST_SKIPPED` |

`test_ooxml_merge_integrity.py` 必须 7 项、`test_logic_navigation_contract.py` 必须 20 项，否则报 `MANDATORY_REGRESSION_IDENTITY`。

### 历史套件清单（v1.1.1-rc.1 实测；不是当前门禁数量）

用例数取自 Fix C2 正式回归回执 `release_regression_final/regression_receipt.json`（valid=true，errors=[]，total_ran=229，total_skipped=0）。**G3-R 整理会话没有重跑这 229 项**（按任务授权，重跑属下一独立会话）；本表用于说明门禁构成与判读标准，不构成本轮的新执行结果。

| 套件 | 用例 | 说明书 |
|---|---:|---|
| `test_ooxml_merge_integrity.py` | 7 | 真实案例 OOXML 合稿矩阵（需夹具） |
| `test_independent_acceptance_fixes.py` | 25 | 独立验收失败项 |
| `test_local_logic_views.py` | 16 | 局部逻辑视图 |
| `test_a_overview_recovery.py` | 16 | A 容量恢复 |
| `test_workbook_reuse.py` | 33 | Workbook 复用与 Reader |
| `test_maintenance_v1_1_1.py` | 45 | 维护候选合同 |
| `test_delivery_entry.py` | 8 | 交付入口 |
| `test_contribution_projection.py` | 14 | 贡献投影 |
| `test_contribution_acceptance.py` | 15 | 贡献验收 |
| `test_workbook_figure_consumer.py` | 11 | Workbook 图消费 |
| `test_logic_navigation_contract.py` | 20 | 逻辑导航交付合同（需夹具） |
| `test_release_regression_gate.py` | 7 | 回归门禁自身 |
| `test_c2_delivery_closure.py` | 12 | 真实 Workbook/来源/Full CLI 闭合（需夹具） |
| **合计** | **229** | 0 FAIL / 0 SKIP |

## 2. 需特定夹具的 27 项如何真正执行

历史日志里出现过 `Ran 27, Skipped 27, exit 0`：7 项 OOXML 合稿测试与 20 项逻辑导航合同测试在**没有真实案例夹具**时整体 `skipUnless`，退出码仍为 0。这是最容易把"未执行"误读成"通过"的位置。

正式回归的处置方式：

1. **夹具不随包分发**（含私有论文与真实交付物），由 `--config` 指向；配置里每个夹具都登记 `path` + `sha256`。
2. 运行器在跑任何测试**之前**先校验全部夹具 SHA；不一致或缺失直接退出 2，一个测试都不执行。
3. 通过 `environment` 段注入三个案例变量：`PFS_MERGE_CASE`（7 项 OOXML）、`PFS_C1_CASE`（20 项导航合同）、`PFS_C2_CASE`（12 项交付闭合）。变量一旦齐全，`skipUnless` 条件成立，这 **39 项是真实执行**而不是跳过。
4. 因为 `TEST_SKIPPED` 本身就是失败码，`total_skipped` 必须为 0；`Ran N` 还必须等于声明的 27 / 12，缺一项即 `TEST_IDENTITY_MISMATCH`。

因此"27 项"在正式回归中是被夹具真实执行的 27 项，不是允许跳过的 27 项。反向验证：把配置里任一夹具 SHA 改错，运行器退出 2 且不执行测试；去掉案例变量，运行器以 `total_skipped=27` 退出 2。

> 注：`tests/test_presentation_quality_notes.py` 另有 `NODE` 环境缺失时的 `skipTest`，该套件不在 13 个正式套件内，不影响门禁。

## 3. 可独立运行的合成测试（辅助，不是门禁）

下列自著合成测试不依赖私有夹具，可直接运行，用于快速定位回归；它们**不替代**本候选的正式发布门禁：

```text
python -B tests/test_inventory_synthetic.py
python -B tests/test_research_logic_contract.py
python -B tests/test_visual_polish_locked.py
python -B tests/test_visual_polish_deck_style.py
python -B tests/test_visual_polish_connectors.py
python -B tests/test_visual_polish_reading_guides.py
```

`tests/legacy_visual_polish_v1.py` 是旧合同记录，不作为当前验收套件。

## 4. 其他预检（非测试门禁）

```text
python scripts/run_pfs.py --help                                  # 5 个子命令
python scripts/render_logic.py --check-dependencies               # portable 依赖
python -m pip check                                               # 环境一致性
```

## 5. 测试不能证明什么

- 单元/集成测试通过 **不等于**科学终审通过：真实案例的科学审核在当前发布候选上仍为 `PARTIAL`（缺补充表 S1–S5、存在计数冲突）。
- 测试通过 **不等于**用户视觉验收：`NOT_ASSESSED`。
- 测试通过 **不等于**干净机器可用：安装测试与 Office 实机导出属下一阶段。
- 真实论文案例、审计日志与私有夹具不随公开包分发，因此外部复现历史套件及本候选完整门禁需要自备等价夹具；范围与替代做法见 `docs/KNOWN_LIMITATIONS.md`。

## 历史验证记录（不代表本次重跑）

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


## rc.2 G4-P1-01 candidate gate
14 suites / 243 tests (prior 229 + 14 FREEFORM/structured-failure regressions). Required test_native_freeform_contract.py has 14 identities and uses PFS_C1_CASE plus a new PFS_FREEFORM_OUTPUT. Refresh the private suite configuration SHA for this new test; retain all previous test SHA values. The runner requires this suite and rejects skips. Cell legacy Full remains subject to all current metadata, detail-text and font contracts; no historical acceptance or G4 verdict is changed.


## rc.3 G5定向合同与打包身份

rc.2的243项与历史夹具保留。rc.3新增`test_g5_content_contracts.py`（15项）和`test_candidate_fingerprint.py`（9项）；其他本轮套件及最终总数以正式runner配置声明与实际回执为准。无论总数多少，SKIP、测试身份遗漏、夹具或源码SHA不匹配均不能算通过。

```text
python -B -m unittest discover -s tests -p test_g5_content_contracts.py -v
python -B -m unittest discover -s tests -p test_candidate_fingerprint.py -v
python -B scripts/candidate_fingerprint.py --root <候选根目录>
python -B scripts/candidate_fingerprint.py --zip <候选ZIP> --zip-root paper-figure-story
```

前两项是定向复现命令，不替代正式发布runner。指纹公式沿用rc.2的`sha256(UTF-8(LF.join(排序后的根相对POSIX路径 + 空格 + 文件SHA256)))`，最后不追加换行。ZIP包装层须显式指定；目录、ZIP和解压后根目录应得出完全相同的文件表及聚合SHA。输出清单保存在候选外，不让清单自指。

原G5的空正文误通过、Workbook教学缺口及所有历史失败回执须保留。缺少教学事实时返回非零和具体缺口；不能把字符串列表归一化、仅生成PPT或结构测试通过写成完整Workbook、Full或科学终审通过。


## rc.4最终受控门禁（未发布）
原295项测试身份和源码SHA保留，新增`test_rc4_wording_closure.py`的2项真实产物核验，正式总数297；最终回执要求0 FAIL、0 SKIP，禁止用历史数量替代实际回执。
新增套件通过`PFS_RC4_CASE`指定隔离案例根目录（含`delivery/deliverables`与`model_identity.json`）；缺少夹具不能算PASS。私有正式配置、297项身份、夹具SHA、实际命令及回执随独立审阅资料提供，不把论文或私有夹具打入源码ZIP。
执行：`python -B scripts/run_release_regressions.py --config <已核对SHA的审阅配置> --outdir <新的空输出路径>`。
P6/P14科学措辞核验与软件回归分别记录；科学终审仍为PARTIAL，用户/独立验收不因297项通过而自动通过。详见`docs/RC4_ACCEPTED_LIMITATIONS.md`。


## 正式封包证据继承
正式版功能文件与已独立验收rc.4逐字节相同；297项独立回执是rc.4的功能不变证据，不是正式ZIP重新执行的回执。仅文档/版本改动不要求重复科研内容重建，按F_DOC_ERRATA.md裁决执行本次文档契约、版本和基本CLI检查。历史rc.4段落保留为历史记录。
