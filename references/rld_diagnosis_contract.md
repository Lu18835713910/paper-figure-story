# RLD 诊断合同（v1.2.0）

本文件定义 `scripts/rld_diagnose.py` 的输入、语义判定规则与输出边界。
**本模块不在 PFS schema 中新增任何枚举**；所有新增概念都活在 RLD 诊断层内部。

---

## 1. 输入

三个 JSON，全部由调用方显式给出，模块内不含任何本机路径：

| 参数 | 内容 | 来源 |
|---|---|---|
| `--units` | 论证单元（`rld_argument_units_v1`） | 由 `evidence_network` + `research_logic` 派生 |
| `--network` | PFS Evidence Network | `scripts/evidence_network.py` 产出 |
| `--logic` | PFS Research Logic | 人工/Agent 裁决后由 `research_logic.py` 校验通过 |
| `--registry` `--manifest` | 可选，数值门禁用 | 见第 5 节 |

`--units` 中每个单元需要的字段：`unit_id`、`kind`、`pfs_anchors`、`claim`、
`observations`、`design`、`limits`、`comparison_conditions`、`source_refs`。
缺失字段按"信息不足"处理，不猜测。

## 2. 语义枚举（8 值）

| 枚举 | 判定含义 | 能否触发因果疑点 |
|---|---|---|
| `CAUSAL_ASSERTION` | 断言 X 导致/促进/介导 Y | **能** |
| `CAUSAL_HYPOTHESIS` | 以假说或检验框架提出（whether / may / 是否 / 假设） | 否 |
| `NEGATED_CAUSAL` | 同一子句内明确否定该因果（did not / 并未 / no evidence that） | 否 |
| `CORRELATION_ONLY` | 只述相关（associated with / 呈正相关） | 否 |
| `DESCRIPTIVE_REGULATION` | 无施动者的被动描述（is actively regulated / 受严格调控） | 否 |
| `UNCERTAIN` | 对已述因果的证椟性保留（suggest / 提示 / 似乎） | 否 |
| `NO_CAUSAL_CONTENT` | 已评估，确无因果内容 | 否 |
| `UNASSESSED_LANGUAGE` | **未评估**（字符集未覆盖 / 空文本） | 上报覆盖缺口 |

判定顺序（优先级从高到低）：否定 → 假说 → 不确定 → 描述性 → 断言 → 仅相关 → 无因果。

## 3. 三条作用域规则

1. **否定不跨子句**：`X promotes Y, but Z was not changed` 仍判断言。
2. **复合词不是否定**：`not only … but also`、`不仅/不同/不断` 先剥离。
3. **连字符复合定语不是因果载体**：`clathrin-mediated endocytosis`、`exercise-induced …`
   中的 `mediated` / `induced` 不计。

名词形态（`regulation`、`downregulation`、`upregulation`）不计为因果载体；
只有动词形态（`regulates/regulated/regulating`）计。

## 4. 归因规则（关键）

`CAUSAL_ASSERTION` 只是"候选"，必须再过 PFS 结构核查：

从该单元的证据实体出发，沿 network 边（无向）走 ≤2 跳，得到可达集合；若其中含
`intervention` 实体，再看：

| 条件 | 结论 | 归因 |
|---|---|---|
| 有可达干预 + 原文明确报告的 `compares` 边 + 干预到读出有连线 | 不报，记 `SUPPORTED_BY_REGISTERED_INTERVENTION` | — |
| 有可达干预，但缺上述之一 | 报 | `PFS_RECONSTRUCTION` |
| 无可达干预，但模型内别处有干预 | 报 | `PFS_RECONSTRUCTION` |
| 模型内**完全没有**干预实体 | 报 | `PAPER_REASONING` |

要点：
- **只有 `certainty=paper_reported` 的 `compares` 才算"已登记对照"**。
  协议级推断（`inferred_needs_review`）不能用来清掉告警。
- 模型里有干预、只是没连到该结论时，**不得指责论文**。
- 报告中的 `competing_explanation` 与 `what_would_change` 必须同时给出，且 `reversible=true`。

## 主张规格

JSON 顶层 schema=rld_numeric_claims_v1，axis.order 为有序时间点，claims 为列表。每条含 claim_id、metric、group、unit、source 和 predicate。ordered_by_series 另给 direction=increase/decrease；extremum_at_last 另给 extremum=min/max；below_comparator_all_series 或 above_comparator_all_series 另给 comparator_group。登记簿 cells 使用 metric、treatment、stage、value、unit。manifest pin 为 canonical_registry_sha256。INSUFFICIENT 表示不可核验。


## RLD 真实模型交接

使用同一论文的 Scientific Index、Evidence Network 和 Research Logic。保留原文及其引用路径。使用随包正式 PFS 验证器，无法补足独立语义审阅时保留 PARTIAL。

```text
python scripts/rld_units.py --index index.json --network network.json --logic logic.json --out argument_units.json
python scripts/rld_diagnose.py --index index.json --network network.json --logic logic.json --out diagnostics.json
```

第二条命令自动派生论证单元。Agent 检查缺失字段和 source_statement_ids，回查原页及实验对照，记录待确认的前提与限制。逻辑标签不得冒充原文。归因候选需人工核对，尤其是已有干预与当前断言的关联。科研准确性 NOT_ESTIMABLE。

数值核验使用 rld_numeric.py --claims claims.json --registry registry.json --manifest manifest.json --manifest-anchor SHA256 --out numeric.json。规格见 references/rld_diagnosis_contract.md。外部锚点须来自独立冻结记录，同次生成的 manifest 与摘要不建立可信来源。判定仅适用于报告的均值；不认证统计显著性、机制或因果。原论文和私人数据不分发。
