# 实验级来源补充合同

`pfs-experiment-inventory-1`是M1知识模型的有源实验级补充ledger。它保存Methods中已核实的细节，不允许改写M1节点/边或制造RSU。调用`build_network(..., experiment_inventory_path=...)`时，统一网络追加`experiment_layer`及明确标为`experiment_source_view`的节点/陈述；未提供此参数时，旧网络输出保持不变。

## 任务划分与字段状态

Experiment ID按实质研究/分析任务稳定分配，不按Figure、panel、处理组或统计散点数量分配。同一测量方法可跨Figure使用；每个Figure/条件的组别、统计单位和n仍分别登记。蛋白制备、电镜采集、图像重构、功能测量、表达控制、定性定位、归一化等是否单独计任务，应在`counting_policy`明确，避免用相同流程人为扩大实验数。

每项任务保存`experiment_id/display_name/task_type/m1_evidence_ids/figure_ids/fields`。每个字段有`value/status/source_refs`，可加`unit/reason/review_scope/candidates`。字段包括问题、材料/系统、分组、组数、样本量与单位、生物学/技术重复、独立次数、处理、采集、分析、统计、结果、解释和限制。未提取的字段在审核统计中按NOT_VERIFIED计，不能自动变成未报告。

|状态|使用条件|
|---|---|
|VERIFIED|提取者判断该具体值受已定位原文支持；必须绑定准确摘录。不是独立人工科学终审|
|PARTIAL|已找到部分支持，但条件、范围或解释尚不充分；必须有源|
|NOT_REPORTED|实际检查所述原文范围后未报告；保留已检查来源和范围说明。补充文件缺失不能据此断言全论文未报告|
|NOT_VERIFIED|尚未核实、缺可得补充资料或尚未定位；写原因，不补造数值|
|CONFLICT|主文、图内、图注或方法不一致；保留全部候选值及来源，不自动选定一个值|

来源引用保留注册文档ID、物理PDF页、原有`page-XX.txt`路径/SHA256、Unicode字符起止与准确excerpt。校验器验证PDF与缓存身份、页范围和片段匹配；这些检查不能证明语义、panel映射、图片完整或用户已审核。正式终审始终独立，当前`formal_ready=false`。

## 数量与关系

group_count、sample_count、biological_replicates、technical_replicates和independent_runs分别计数。有数字时必须声明统计单位；sample_count可引用单独sample_unit。细胞/粒子/视野/结构/独立测量不能自动升级为生物学重复或独立制备。不得从图中散点外观推n；不同条件的n不得推广。CONFLICT保留候选而不自动汇总。

字段与实验、M1 evidence之间的自动连线只是membership association，明确`scientific_dependency=false`。有源补充关系另列relations，区分SCIENTIFIC_EVIDENCE、DATA_DEPENDENCY、EXPERIMENTAL_COMPARISON、AUTHOR_INTERPRETATION、PRESENTATION_ORDER和UNVERIFIED_HYPOTHESIS。汇报关系不能变成数据依赖；数据依赖须显式输出/输入依据；机制假说不可提升为VERIFIED。原M1关系和RSU不被替换。

## 双向Methods审核与B输出

从每项Results/Figure主张追到Methods；从每个实质Methods小节追到Experiment ID及实际作用/结果。`method_sections`保存已检查段落及关联ID，`missing_materials`列缺少的补图、补表、方法和影响范围。已定位Methods不等于全部条件已充分提取，更不等于整篇科学终审完成。

`audit_inventory()`分别按每个字段报告VERIFIED/PARTIAL/NOT_REPORTED/NOT_VERIFIED/CONFLICT的数量与相同任务分母，并列出具体ID。登记任务数不能自行证明“全文识别100%”；识别分母须经过独立完整性审查。方法定位率和关键结果绑定率也分别报告，不用一个总体百分比掩盖缺项。

`write_audit(inventory, output_dir, validation=report)`生成完整Inventory JSON、可读Markdown和机器统计。B1画实验之间的实际关系，B2按Experiment ID生成可编辑信息卡，B3/B4保存完整清单、统计与来源。A/B/C都读取同一网络，不再各自抄写事实。原始图像仍独立保留，不重绘科学数据。

## 本地验证入口

```text
python -B scripts/experiment_inventory.py --inventory inventory.json --knowledge knowledge.json --audit-dir NEW_AUDIT_DIR
python -B scripts/evidence_network.py --knowledge knowledge.json --experiment-inventory inventory.json --output NEW_NETWORK.json
python -B tests/test_inventory_synthetic.py --report-dir NEW_TEST_REPORT
```

最后一个入口只生成自行编写的合成PDF/缓存/模型，验证结构与拒绝条件；它不读取论文、不证明自动理解通过。代码包不需要携带论文PDF或Figure，实际论文验收日志与合成测试分开保留。
