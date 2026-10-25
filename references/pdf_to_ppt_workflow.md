# PDF到PPT：Codex负责语义，脚本负责核验和制作

1. 确认用户PDF与补件、目标汇报；默认balanced及主PPT，不先索要内部JSON。
2. 使用run_pfs的PDF入口或index_pdf生成/复用按文件SHA绑定的页缓存；查看主Figure和需要放入PPT的panel。
3. 如返回REVIEWED_KNOWLEDGE_REQUIRED，当前Codex读取agent_handoff中的缓存和M1 schema。读正文论证、图注、关键Methods；区分原创、方法、综述/观点，必要时明确综述的子类型。缓存不是科学结论。
4. 创建有源M1：document_registry、实体/方法/证据/认识、真实关系、Figure和RSU。用精确来源支持每项关键陈述；保留未知n/重复、冲突、作者假说及presentation关系。不要复制陌生论文fixture并仅换标题。已有模型时做来源增量，不另造事实数据库。
5. 运行validate_knowledge和来源校验，建立原图资产清单。all只表示整图展示，不等于每panel已审。实际检查入稿原图的边界、轴、标签、图例和显著性。
6. 用同一缓存、已核M1及资产重入run_pfs新目录。默认products=presentation；用户要求详细图/Methods时才选with-network/deep。无需要求用户知道这些内部参数。
7. 提炼每页真实动作—发现—认识，不把长RSU直接贴正文。开场呈现分支与汇合，来源支持的联系保留，未证机制用假说语气。参考旧成熟版式；复杂图优先放大/科学拆页。
8. 导出PPT，保存人类讲者备注与独立机器审核；实际PowerPoint打开/导出PNG，核对字体/文字范围、图片比例、原生对象与数据方向。只修必要页面，最多两次有记录的针对性修复。
9. 交付PPTX、预览、简明源审。深度模式可独立PARTIAL；关键事实/原图无法核实时停止该部分正式通过，继续其他独立充分部分。不能把Agent辅助测试写成CLI无人辅助理解。
