# 最小可运行示例（全合成，不含任何真实论文内容）

四个 JSON 由 `make_example.py` 生成，完全虚构（"化合物 X vs 溶剂，读出 Y"），
用来在不接触任何真实论文数据的前提下跑通一次 RLD 诊断。

```bash
# 重新生成（可选；仓库已含生成结果）
python examples/minimal_rld/make_example.py

# 运行诊断
python scripts/rld_diagnose.py \
  --units   examples/minimal_rld/argument_units.json \
  --network examples/minimal_rld/network.json \
  --logic   examples/minimal_rld/research_logic.json \
  --out     examples/minimal_rld/diagnostics.json
```

## 预期结果（应逐字复现）

```
units: 4 | findings: 2
by dimension: {'SCIENTIFIC_LOGIC': 1, 'LANGUAGE_LOGIC': 1, 'EXPRESSION_LOGIC': 0}
by attribution: {'PFS_RECONSTRUCTION': 1, 'RLD_COVERAGE_GAP': 1}
coverage: {'units_total': 4, 'assessed': 3, 'unassessed': 1, ...}
```

| 单元 | 文本 | 预期处置 | 是否上报 |
|---|---|---|---|
| `AU_CL_SUP` | Compound X promotes readout Y. | `ASSERTED_WITH_REGISTERED_INTERVENTION_SUPPORT` | 否 |
| `AU_CL_ORPHAN` | Compound X drives readout Y. | `ASSERTED_WITHOUT_INTERVENTIONAL_SUPPORT:PAPER_HAS_INTERVENTION_ELSEWHERE` | 是（`CAUSAL_UPGRADE`，归 `PFS_RECONSTRUCTION`） |
| `AU_CL_CORR` | Readout Y is associated with compound X. | `NOT_ASSERTED:CORRELATION_ONLY` | 否 |
| `AU_CL_FOREIGN` | クラステリンは心臓を守る。 | `UNASSESSED` | 是（`SEMANTIC_TYPE_UNRECOGNIZED`，归 `RLD_COVERAGE_GAP`） |

这四个单元正好演示四条设计意图：

1. **有干预有对照就闭嘴** —— 不是"发现越多越好"。
2. **孤儿断言要报，但归到重建侧** —— 模型里有干预，只是没连到这条结论；不等于论文没做实验。
3. **相关性不得升级为因果** —— 只相关就只报相关。
4. **看不出来就说看不出来** —— 未覆盖语言进 `unassessed`，绝不静默算作"无问题"。

## 文件说明

| 文件 | 作用 |
|---|---|
| `network.json` | 合成 PFS 网络：2 个干预、1 个证据、3 个主张、3 条边 |
| `research_logic.json` | 合成逻辑图：5 个节点、2 条证据收敛边 |
| `argument_units.json` | 4 个论证单元（对应上表） |
| `diagnostics.json` | 一次真实运行的输出（供对照） |

注意：示例的 `network.json` 里 `paper.sha256` 为 `null`、`hash_status` 为 `unavailable`，
因为它是合成数据，**没有**任何真实 PDF 与之绑定。不要把它当作来源核验示例。
