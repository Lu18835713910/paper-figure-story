# 安装与使用｜v1.1.0

## 安装

1. 从作者实际发布的Release或本地候选包取得`Paper-Figure-Story-v1.1.0.zip`；候选报告若标RELEASE_BLOCKED即尚未正式发布，不承诺已有下载链接。
2. 解压后检查`paper-figure-story/SKILL.md`。选择个人Codex skills目录，保留既有版本再安装；本包不执行安装脚本或自动覆盖。
3. 新会话调用`$paper-figure-story`。提供PDF、目标听众、时长和可选补件/模板即可，内部M1由Codex创建。

## 环境

Python模块见[requirements.txt](requirements.txt)。Codex桌面通过`load_workspace_dependencies`提供Node与`@oai/artifact-tool`；后者不是本包重分发内容。需要微软雅黑和Times New Roman用于规定字体。实际PNG验收使用Microsoft PowerPoint；本包不分发Office或字体，也不承诺Linux/无Office渲染等价。

## Codex工作流

详[PDF到PPT工作流](references/pdf_to_ppt_workflow.md)。Codex从原文与原图创建/验证M1及资产；不会让用户自己写JSON。索引缓存按PDF SHA复用。扫描稿、关键图缺失、来源冲突保留明确状态，受影响的事实不正式通过。

低层入口供Agent/开发者使用：

```text
python scripts/run_pfs.py run --pdf paper.pdf --knowledge reviewed_M1.json --assets figures.json --cache-dir cache --outdir new_run --modes balanced --products presentation --plan-only
```

不带knowledge时exit3并写`agent_handoff.json`。当前Codex据此读原文、完成模型并用新输出目录重入；不能取消科学审核门。PPT导出需提供当前环境的`--node`、`--artifact-module`和`--presentation-skill`，显式`--development-preview`用于含PARTIAL科学资料的待审核文献报告。正式软件版本不等于每篇文献已完成独立科学终审。

## 模板

默认[学术蓝模板](assets/default_academic_blue_174994.pptx)为16:9，无Logo。新统一入口`--template path.pptx`支持同类PFS命名版式，按source SHA校验。

普通PPTX使用保留的成熟路径：

```text
python scripts/inspect_template.py user_template.pptx
python scripts/build_pptx.py reviewed_slides.json --template user_template.pptx --template-mode native --output report.pptx
```

native采样母版/比例与颜色，tagged复用PFS命名槽位；复杂动画、任意Logo/母版的像素级还原未承诺。成熟Figure槽最多2幅图片；更多须按问题拆页，v1.1会显式报错而不是丢图。用户模板的首次使用须实际打开/渲染核对。

## 深度整理与交付

`--products with-network`追加独立详细图。`--products deep --inventory Full_Experimental_Inventory.json`调用已有实验层、详细图、卡片和审查清单。未知数量不补造。主PPT、来源表、audit JSON与讲者备注共享ID；发给听众的备注不包含机器JSON。

quick/balanced/full是展开规则，可能同页数，不改变事实与基础关系。默认先做关键样张；一次集中检查，只重渲染修改页，保留每次失败和来源冲突。
