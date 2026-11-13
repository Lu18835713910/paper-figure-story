# 分发边界

公开包保留 PFS 基线能力及 RLD 辅助诊断。原始 PDF、私人科研数据、登记簿及研究过程不随包分发。

## RLD 真实模型交接

使用同一论文的 Scientific Index、Evidence Network 和 Research Logic。保留原文及其引用路径。使用随包正式 PFS 验证器，无法补足独立语义审阅时保留 PARTIAL。

```text
python scripts/rld_units.py --index index.json --network network.json --logic logic.json --out argument_units.json
python scripts/rld_diagnose.py --index index.json --network network.json --logic logic.json --out diagnostics.json
```

第二条命令自动派生论证单元。Agent 检查缺失字段和 source_statement_ids，回查原页及实验对照，记录待确认的前提与限制。逻辑标签不得冒充原文。归因候选需人工核对，尤其是已有干预与当前断言的关联。科研准确性 NOT_ESTIMABLE。

数值核验使用 rld_numeric.py --claims claims.json --registry registry.json --manifest manifest.json --manifest-anchor SHA256 --out numeric.json。规格见 references/rld_diagnosis_contract.md。外部锚点须来自独立冻结记录，同次生成的 manifest 与摘要不建立可信来源。判定仅适用于报告的均值；不认证统计显著性、机制或因果。原论文和私人数据不分发。
