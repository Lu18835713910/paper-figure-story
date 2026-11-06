# 原生科研逻辑导航与独立完整B：候选合同

此说明属于Fix C1隔离候选，不代表已发布版本。A是概览，B是独立可编辑大画布；主稿可以选取同一模型的局部视图，不必缩印整个B。

## 来源与关系

先用现有Research Logic登记判断，再用logic_display选择既有节点、关系和字段。显示配置不得改写关系身份、方向或科学事实。

- `SCIENTIFIC_EVIDENCE`的`complements`沿已登记的from→to表达证据支持/输入关系，不代表生物学因果。
- `parallel`、`comparison`、共享流程以及非证据身份的互补关系保持无向；共享流程不得算独立验证。
- 论证、解释与限定仍按原身份和线型区分。几何朝上不能成为取消方向的理由。
- 新投影规范产生`PRODUCT_PLAN_DRIFT`时，从同一有源模型重新投影；不要关闭校验、编辑旧plan的摘要哈希或重新解析论文。

## 正式登记

使用既有`project_research_logic.py`生成A/B/选定局部图，`render_logic.py --main-pptx ...`原生合稿。主稿标题槽保留原页面标题；主稿内不重复绘制场景标题。完整B与主稿并存时，渲染器生成同目录`Complete_B.editable.pptx`及真实可点击引用；可用metadata的`full_b_reference`指定本地文件名。应交付整个目录。

用实际Office导出的PNG登记，而非放入占位图：

```powershell
python -B scripts/register_logic_graphs.py --model MODEL.json --plan products.plan.json --receipt render_receipt.json --png-dir PNG_DIR --navigation navigation.json --output logic_graph_manifest.json
python -B scripts/validate_story.py OUTPUT_DIR --profile full --require-B --logic-model MODEL.json --graph-manifest logic_graph_manifest.json
```

第二条仅检查**图/导航合同子集**，不证明论文全部Full产品已交付。`PNG_DIR`使用`main.png`、`detail.png`、`branch_VIEW.png`以及`main-slide-NNN.png`命名，均对应真实导出。

`navigation.json`是展示范围输入，不是新科学模型：

```json
{
  "full_b_reference": "Complete_B.editable.pptx",
  "omitted_edges": {}
}
```

当完整B的关系未在任何主稿原生视图出现时，`omitted_edges`须逐个使用真实关系ID登记非空理由。官方登记器计算可见集合和省略集合，不从理由中推断新关系。核心关系必须进入主稿；主稿与完整B的节点/边身份、端点及来源可核。导航记录本身不充当科学节点或整B缩略图，不可把A改scope冒充B。

## 正式交付消费链

`run_pfs.py deliver`把原生图、主稿、可访问的B附件和`Audit/LogicGraph.contract.json`按真实文件SHA打包，Manifest的`logic_graph_contract`引用该审核记录及原模型。`check-delivery`与`validate_story --delivery-manifest`实际消费它，重开PPTX、检查节点/边/来源/方向/文本与10pt门禁、相对引用及省略记录；不相信已缓存的`valid=true`。

未请求Office时，主稿记录`preview_status=NOT_EXPORTED`，不伪造PNG。实际PPT对象仍须通过同样的原生与容量检查；视觉验收只能保持NOT_ASSESSED。使用`--office`才能提供实际Office预览证据。独立图原有PNG与PPTX身份验证保持。

历史无图合同的交付物可以在quick/balanced下读取并保留NOT_ASSESSED；不能据此认证Full原生交付。Full要求完整B、真实导航与实际文件审核。Workbook和贡献审核仍有独立合同；图合同通过不代表Workbook、全篇贡献覆盖、科学终审或Release通过。

科学终审继续PARTIAL。无源或有争议的关系须回到内容审阅，渲染器不得自行推理补线。

## 独立B的原尺寸字号检查与正式回归

独立完整B按自身大画布阅读，不能把它缩到16:9后计算“等效字号”。正式合同在其实际PowerPoint对象上检查非空文字的显式字号至少10pt；未知字号或低于下限返回`COMPLETE_B_READABILITY_LIMIT`。这是防止7pt小字静默通过的最低工程门禁，不是最佳阅读字号，也不替代原尺寸/放大阅读、连线和文字遮挡的实际Office审阅。主稿原有10pt节点门禁不变，不能据此将完整B重新缩印到主稿。

发布前回归可使用既有测试CLI的封装入口：

```powershell
python -B scripts/run_release_regressions.py --config PRIVATE_FIXTURE_CONFIG.json --outdir NEW_REGRESSION_DIR
```

配置是私有测试运行说明，不是科学Schema。`fixtures`逐项包含实际`path`和`sha256`；`environment`指定`PFS_MERGE_CASE`、`PFS_MERGE_PLAN`、`PFS_MERGE_METADATA`、新建的`PFS_MERGE_OUTPUT`、`PFS_C1_CASE`、新建的`PFS_C1_TEST_OUTPUT`，以及其他套件所需的`PFS_TEST_RUN`。`suites`列出实际测试文件名`test`及源码`sha256`。使用C2真实交付测试时另提供`PFS_C2_CASE`、`PFS_C2_DELIVERY_ROOT`和新建的`PFS_C2_TEST_OUTPUT`。不要把私人论文或案例目录加入Skill安装包。

运行器先核对夹具/测试SHA，再执行实际测试文件CLI；必须包含Fix A的7项和C1的20项。它同时消费实际测试身份、`Ran`数量、`Skipped`和退出码。任何SKIP、缺项、错误身份、失败或无有效结尾均退出非零，不能用“27项全部跳过且exit 0”认证发布。输出目录不得复用，历史失败日志保留。操作系统临时目录受限时，可把`TEMP`/`TMP`设为当前隔离测试区内的专用临时目录，不改测试断言。
