# PDF到科研逻辑与PPT

1. 确认用户PDF与补件、目标汇报；默认balanced及主PPT，不先索要内部JSON。
2. 使用run_pfs的PDF入口或index_pdf生成/复用按文件SHA绑定的页缓存；查看主Figure和需要放入PPT的panel。
3. 如返回REVIEWED_KNOWLEDGE_REQUIRED，当前Codex读取agent_handoff中的缓存和M1 schema。原创研究先完整读取可用Abstract、Introduction、Results、Discussion、Methods/STAR Methods、Figure legends及补充说明；quick/balanced也完成科学结构阅读和Methods任务识别。综述先读全文并判断叙述/系统/Meta类型；不把引用研究当作作者新实验。缓存不是科学结论。
4. 先建立12类科学索引、Methods任务清单和Methods—Results—Figure—Conclusion双向映射。任务区分实验、控制、计算和共享；保留完整字段、单位、n、重复、统计、来源及冲突，同时给出有源六角色简释。缺补件不是原文未报。完成此步后才判断递进、分叉、并行、互补、汇合、共享和假说；详[科研逻辑合同](research_logic_contract.md)。不预设四个并行主题，不由Figure顺序制造因果或执行历史。
5. 创建或增量完善有源M1：文档、实体/方法/证据/认识、真实关系、Figure与RSU。科研逻辑模型是引用视图，不另造事实数据库。节点/边保留身份、理由、来源和其他解释；文件定位不等于语义终审。
6. 运行知识/来源校验，检查主Figure与入稿panel的边界、轴、图例和统计。all不等于panel终审。用同模型投影A/B，B展开并可压缩回A；C独立验收，不能以总图引用替代逐Figure覆盖。
7. 用同缓存、M1及资产重入run_pfs新目录。默认presentation，独立图with-network，Methods深度deep；显式--research-logic采用新模型，旧默认CLI和漂移门保留。每页提炼真实动作—发现—认识，复杂图按问题拆分，不直接粘贴长RSU。
8. 实际PowerPoint打开/导出PNG，核对字体、范围、原生对象和科学读数。可选workbook复用同模型实际图、设计对照表和完整Methods引用；实际DOCX打开并逐页渲染，禁止IMRD文章改写。有限定点修正，自动与人工状态分开。
9. 交付实际文件、源审及独立状态。PARTIAL不升级为正式可发布；不把Agent辅助或fixture回放写成CLI无人辅助PDF理解。
