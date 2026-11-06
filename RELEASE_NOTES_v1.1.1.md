# Paper Figure Story v1.1.1 Release Notes（正式稿）

以独立验收通过的rc.4为功能基线，本次仅文档勘误与版本封包。保留OOXML合稿、FREEFORM语义检查、Workbook Figure消费与字段兼容、NOT_APPLICABLE、来源身份及分层Full门禁；未新增科学模型或渲染引擎。

修正文档229项旧数、固定49项误读和140文件历史快照标注；当前门禁21套件/297项。独立验收为INDEPENDENT_ACCEPTANCE_PASS_WITH_DISCLOSED_LIMITATIONS，阻断0项。

## 正式v1.1.1能力与验证边界

- portable路径已验证；建议先选择该路径并按INSTALL/宿主文档预检。Windows Office导出已在独立验收机器验证，不代表所有机器均已测试。
- Artifact宿主路径为NOT_TESTED；普通Figure主稿若依赖Artifact，须先验证宿主API与真实创建/导出，不得由portable成功推定宿主可用。
- 本次Full端到端复验复用已有科研模型及相关输入，不是“仅输入PDF即可全自动完成所有科学建模”的独立验证。M1、来源和解释由执行Agent依据论文登记与审核。
- 本案例科学终审PARTIAL，贡献核心审阅NOT_ASSESSED；工程Full不能升级科学审阅。
- Source Data未完整获得；多文档Supplementary一级来源登记存在限制，不能宣称补充材料科学来源完整闭环。
- Logic_B是独立可缩放大画布，不适合直接缩印A4；汇报使用可读局部视图。
- 297项测试经过独立复验，其中依赖的50项私有夹具文件不随公开ZIP分发（不是指只有50项测试）；普通用户不能仅凭公开ZIP复现完整维护回归。可执行公开合成测试，但不能冒充297项门禁。
- 旧版Info-ZIP可能使中文文件名乱码；推荐Windows原生Expand-Archive或Python zipfile解压，解压后核对逐文件SHA。
- 已接受的非阻断排版瑕疵（P8/P15换行、P14句号孤行、索引短续表留白）列入v1.1.2待办，不影响本次原生内容读取；不因此重开排版引擎开发。
- 正式Tag、Release及ZIP SHA共同标识本版本。


## 本次公开分发

本次更新中文README、作者角色和最终真实产物GIF，原软件功能文件与已验收正式基线逐字节相同。第三方论文Figure未包含在新展示中，Figure Story仅展示实际讲述区；见docs/images/v1.1.1/ASSET_PROVENANCE.md。GitHub自动Source code ZIP是Tag仓库快照；独立Skill ZIP以随附FILE_MANIFEST为受管文件身份，不能把两类ZIP的SHA视为相同。297项回归和Full引用rc.4独立验收，未声称本新ZIP重跑。
