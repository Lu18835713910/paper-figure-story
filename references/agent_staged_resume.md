# Agent五阶段执行与中断续跑

这是一份现有入口的操作说明，不是新调度器。每阶段将输入路径/SHA、产物、实际命令/进程退出码、当前科学状态、下一动作写入现有`PROGRESS_CHECKPOINT.md`或本次交接记录。收到`agent_handoff.json`后由**当前执行Agent**接手，其中历史措辞“Codex”不限制只能由Codex执行。普通用户不负责写科研JSON。

从Skill根目录执行下列命令。`INPUT/CACHE/NEW_*`由Agent替换成本案例真实路径；续跑沿用相同参数和解释器。新outdir必须为空，不覆盖失败。Python需可用pdfplumber；Figure像素流程另需PyMuPDF/Pillow，便携图另需python-pptx及本地字体。不能把依赖检查成功等同实际渲染成功。

## 阶段1：阅读、索引和初始登记

开始先区分用户请求：只要逻辑图可使用便携后端；需要普通Figure主稿，必须预先定位可用Node、Artifact模块、presentation-skill（含container_tools/artifact_tool_utils.mjs）。PowerPoint/Word实际导出另依赖本地Office及可访问的COM。路径存在不代表版本/运行已验证；当前宿主未经实际生成测试时记录NOT_TESTED。

```powershell
python -B scripts/render_logic.py --check-dependencies
python -B scripts/run_pfs.py run --pdf paper.pdf --cache-dir CACHE --outdir NEW_INDEX --plan-only
# 无M1时预期进程exit 3，读取NEW_INDEX/execution.json和agent_handoff.json
```

保存PDF及可用Supplementary指纹、cache/metadata.json、page-NN.txt、pdf_index_receipt.json、extraction_candidates.json、agent_handoff.json和阅读/缺件记录。实际过程检查`$LASTEXITCODE`及execution.json，某些宿主封装可能把子进程码只写入stdout，不能以外层exit0认为成功。

Agent阅读全部可用正文/Methods/图注、实际Figure，登记已读范围和缺失；候选句不是已核事实。新会话先读取交接、已审证据表、未解决问题和涉及的缓存页，不重复索引整篇PDF。PDF SHA相同且receipt验证缓存命中后复用。PDF变化则新建cache，不改旧cache指纹。

## 阶段2：构建与验证M1

先读[M1编写指南](m1_authoring_guide.md)，将同一已审事实登记一次；保存knowledge.json及逐Figure证据、比较设计、统计单位、来源/缺件记录。

```powershell
python -B scripts/validate_knowledge.py INPUT/knowledge.json --verify-files --json --report INPUT/M1.validation.json
python -B scripts/evidence_network.py --knowledge INPUT/knowledge.json --source-cache CACHE --output INPUT/network.json
python -B scripts/evidence_network.py --validate INPUT/network.json
```

若已准备assets/narrative/relations/figure_story/inventory，必须在建网与重入时保留对应正式参数，不能漏掉它们重建另一身份。成功标准为实际exit0、valid=true/errors=[]，另独立记录科学PARTIAL。结构通过不证明教学信息已足够。缺资料不把值猜齐；没有完整Inventory并不自动阻断有源M1/Story。

续跑只定点修正报告错误，保留旧M1和验证记录。M1或任一网络输入内容/登记路径改变后，重新官方建网并验证，记录父子snapshot及差异；相同科学文字也不能假定文件身份不变。

## 阶段3：Research Logic与A/B

先做贡献覆盖审阅：研究任务、方法、发现、限制及共享证据；不固定分支数，不把末图等同全文结论。已有模型时直接验证复用；默认A超容量则按[A恢复操作单](a_overview_recovery.md#低成本即时恢复操作单)用guidance即时恢复，或有源显式Research Logic直接投影。

保存failure.json、网络、display.guidance或scientific_index/adjudication/research_logic、父子身份、products.plan.json、plan_validation、geometry_preflight、contribution_validation及source_review。精确来源不足是科研登记任务，不靠改SHA或同页替代。

`run`的CACHE/metadata.json与`index_pdf.py`的paper_index.json格式不同，不能互换。已有run缓存时，为scientific_index init提供**仅元数据格式转换**，无需重新抽PDF：

```powershell
python -c "import json,pathlib; p=pathlib.Path('CACHE/metadata.json'); m=json.loads(p.read_text(encoding='utf-8-sig')); q=pathlib.Path('INPUT/paper_index.compat.json'); assert not q.exists(); q.write_text(json.dumps(dict(source_pdf=m['path'],file_sha256=m['sha256'],page_count=m['physical_page_count'])),encoding='utf-8')"
python -B scripts/scientific_index.py init --paper-index INPUT/paper_index.compat.json --output INPUT/scientific_index.pending.json
```

该转换不填任何科学facets或阅读状态。Agent必须在独立索引副本中据已读缓存填写，再validate/assemble，完整操作见恢复reference。绝不能将pending骨架直接写成已审核。

原生独立A/B已有合法显式模型时：

```powershell
python -B scripts/project_research_logic.py --network INPUT/network.json --model INPUT/research_logic.json --views A B --outdir NEW_VIEWS
python -B scripts/run_pfs.py render-products --network INPUT/network.json --plan NEW_VIEWS/products.plan.json --metadata NEW_VIEWS/metadata.resolved.json --outdir NEW_GRAPHS --backend portable --development-preview --office
```

没有实际Office导出环境时省略--office，仅原生PPTX，不声称PNG/PDF/graph清单完成。B独立大画布，局部图按既有合法子集机制；不能把B压成16:9或改成整页PNG。guide默认B仍可能有geometry风险，应转现有显式规划；不因exit0忽略预警。

恢复后验证图与模型、来源snapshot一致；网络更新需合法重绑Research Logic并重投影，下游graph/receipt/Manifest不能沿用旧身份。只改展示也要按既有snapshot/显示SHA合同重登记实际文件，不能仅给旧PPT换备注。

## 阶段4：Figure资产与Workbook教学内容

保存真实Figure请求（PDF页/bbox/panel）、登记图片/SHA、像素核验、panel语义审阅、逐图Story/Methods/定量/限制及Workbook bindings或显式content。没有关键panel/来源先登记缺口，不编造；完整Figure资产可以含多个panel成员，并非每个panel都须单独裁图。

```powershell
python -B scripts/figure_assets.py prepare --pdf paper.pdf --requests INPUT/figure_requests.json --outdir NEW_FIGURES --dpi 240
python -B scripts/figure_assets.py validate NEW_FIGURES/figure_assets.json
```

requests的regions按既有资产合同，由Agent根据实际原图确认bbox，不猜ROI。`run --assets`用的是网络资产输入；Workbook `--figure-assets`消费经过原PDF像素核验的现有Figure资产registry，两者不要仅凭同名文件互换。当前P1接口按figure_id对应逐图章节并核对SHA/来源/panels。

Workbook优先复用已登记M1/Story/来源，annotations绑定真实身份；无content时正式构建器写`.assembly.json`任务清单。缺字段返回exit2且不生成空壳教学手册。只处理具体gap，不从A/B短句反推实验详情。显式content仍是可审核输入，人工补充与自动字段复用分开记录。无适用实验Methods需有源NOT_APPLICABLE；综述的实际检索/分析方法不能抹去。

**资产登记会改变network身份。**尽量先稳定最终资产，再生成最终Research Logic及图；如已提前生成A/B，保留父件并按官方合同派生重绑及重新生成/登记。此处不是要求改Evidence Network科学字段或绕过LOGIC_NETWORK_MISMATCH。

## 阶段5：主稿、Workbook及正式交付

普通Figure主稿需要真实可用Artifact宿主。便携图依赖检查不能代替宿主检查；下列宿主路径须本进程定位并验证，不能复制旧机器路径：

```powershell
python -B scripts/run_pfs.py run --pdf paper.pdf --knowledge INPUT/knowledge.json --cache-dir CACHE --assets INPUT/network.assets.json --metadata INPUT/metadata.json --research-logic INPUT/research_logic.json --products with-network --modes balanced --outdir NEW_MAIN --development-preview --node NODE_EXE --artifact-module ARTIFACT_MJS --presentation-skill PRESENTATION_SKILL
```

保留原调用适用的--figure-story/--relations等参数；未有这些文件时不要传不存在的占位路径。也可将已验证正式plan交给现有render-products --backend host，而不是因缺宿主另造主稿后端。物理字体、Figure保真、备注、原生逻辑、实际打开与逐页PNG需独立验收。

已有同模型graphs、真实主稿、page-map、教学输入后，分阶段构建与交付：

```powershell
python -B scripts/build_research_workbook.py --model INPUT/research_logic.json --graphs NEW_GRAPHS/logic_graph_manifest.json --annotations INPUT/workbook_bindings.json --figure-assets NEW_FIGURES/figure_assets.json --output NEW_WORKBOOK/Workbook.docx
# 有经审核显式教学content时可加--content；不得与--reader混用
python -B scripts/run_pfs.py deliver --research-logic INPUT/research_logic.json --graphs NEW_GRAPHS/logic_graph_manifest.json --main-pptx INPUT/main.validated.pptx --page-map INPUT/page_map.json --plan NEW_VIEWS/products.plan.json --metadata NEW_VIEWS/metadata.resolved.json --content INPUT/content.validated.json --figure-assets NEW_FIGURES/figure_assets.json --summary-plan INPUT/main.products.plan.json --contribution-review INPUT/contribution.review.json --outdir NEW_DELIVERY --request main A B Workbook PNG PDF --profile full --office --development-preview
python -B scripts/run_pfs.py check-delivery --root NEW_DELIVERY/deliverables --profile full
python -B scripts/validate_story.py NEW_DELIVERY/deliverables --delivery-manifest --logic-model INPUT/research_logic.json --profile full --require-B
```

上面是有这些实际输入时的命令形式，**不是一个已自动衔接的单命令Full流程**。无显式content可用deliver的--workbook-bindings尝试适配；不能传空content凑完整性。page-map指向现有批准逻辑页；原页有Figure时合稿可能拒绝，不能删图强行插图。deliver需新生成receipt/Manifest并核验实际相对链接及文件SHA。完整B附件不能遗漏，Word单独移动须提示依赖。

保存最终产物、graph登记、Workbook receipt、Manifest、覆盖报告、Full stdout/stderr及实际退出码。核查known core omission是否阻断Full；历史缺覆盖信息保持NOT_ASSESSED。结构Full、科研内容完整性、科学终审、视觉及用户接受分别报告。

## 中断分类及停止规则

|类别|恢复动作|
|---|---|
|科学信息不足/缺补件/来源不支持|读取具体gap与缓存段，登记PARTIAL/MISSING；不得自动推断|
|M1类型/引用错误|按M1指南定向修正副本并重新官方验证|
|A容量门|保留网络，用有源guidance或显式规划，不删科研贡献|
|模型/文件漂移|核查哪个输入改变，官方派生重建；不手改receipt|
|宿主/字体/Office不可用|保存实际错误；可继续独立可运行阶段，但主稿/导出/Full保持BLOCKED或NOT_TESTED|
|几何/视觉不合格|保留真实预览与风险，只在已授权展示范围处理；不改科研强度|

新会话先读最后有效receipt、指纹及定向任务，不重新做已成功阶段。不要用更多模型文件替代科研判断。第一次盲测结论永久保留；同论文续跑标RECOVERY_TEST，之后再选真正陌生论文做独立盲测。
