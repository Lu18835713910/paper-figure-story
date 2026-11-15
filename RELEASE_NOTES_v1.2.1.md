# PFS v1.2.1 Release Notes（候选稿，未发布）

**状态**：维护候选，未创建 Tag / Release。v1.2.0 的 Tag、Release ZIP 与资产保持不变。

## 修复

- 对称关系方向：`parallel` / `compares` / `alternative` 不再出现方向箭头，也不参与拓扑分层。
- A/B 兜底路由有界：避免 B 画布因全局边序号线性下移而异常增高。
- 显示字段预检：缺字段返回 `LOGIC_DISPLAY_FIELD_REQUIRED`，不再抛裸 `KeyError`。
- 箭头可见性：箭头放大并做端点回退（纯渲染变换），有向关系可见、对称关系无箭头。
- 主稿同源：`render_logic.py --page-map` 可把正式 Research Logic 作为原生对象注入指定页。
- 布局：A 视图图例与引用分行；密集要点页按实测换行选字号并自适应卡片高度。
- 文案：封面“宏观侵入渗流模型”；第 13 页区分 `A_story` / `A_full` / `B`。

## 新增

- 故事层 A（`scripts/story_view.py`）：5–7 个叙事单元，绑定原始节点；展示关系引用原始关系或登记为经审核叙事归纳。**需由 Agent 或用户提供经审核的故事视图，不是全自动跨论文故事提取器。**

## 验收

- 正式门禁：21 套件 / 297 项 / 0 FAIL / 0 SKIP。
- 全量 unittest：errors=4 / skipped=54（既有环境/私有夹具基线，非全绿）。
- 真实论文作品：13 页主稿 + A_story + A_full + B，PowerPoint PNG/PDF 导出。
- 已知限制：纯自然语言不会自动发现本 Skill（宿主 `disableModelInvocation=true`）；LibreOffice 跨宿主渲染若未执行记为 NOT_TESTED。
