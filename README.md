# Paper Figure Story ｜高质量、低消耗论文PPT Skill

## 这次优化什么

这是一版 **流程优化**，不是降低科学准确性的版本。基于一份实际生成的Atera论文报告（30页，其中23页结果分析），将默认工作模式调整为 `balanced`，目标是减少机械性逐panel拆页、重复精读、重复写五份冗长说明、重复导图与重复渲染。

- 默认 `balanced`：常规科研汇报通常12–18页，按复杂度浮动；每个主Figure一般1–2页，关键机制或独立验证最多可多于2页。不会强制删减关键证据。
- `quick`：更短的组会初稿，通常10–14页。
- `full`：类似原版V5的完整逐panel精读与证据文档，适合要做深入审计时。
- 单次科研证据抽取，PPT排版直接复用审定后的JSON，不重新分析全文。
- 用本地 `scripts/index_pdf.py` 建立可复用PDF文本页码索引，查看Figure图片与图注仍是强制要求。
- 将大部分图像处理、PPT组版、结构检查交给本地脚本，生成后集中检查，出现问题只复查相关页面。
- 总框架始终是**研究思路和实验路线合一的模块图**；逐Figure仍是**图旁科研文字+箭头**。默认主色 #174994，16:9，无Logo；用户模板优先。

## Windows安装 / 覆盖

将ZIP解压至：`%USERPROFILE%\.codex\skills\`，确保：

`%USERPROFILE%\.codex\skills\paper-figure-story\SKILL.md`

建议新建Codex会话。首次依赖：

```powershell
python -m pip install python-pptx Pillow pymupdf
```

## 推荐给Codex的短指令

```text
使用 $paper-figure-story，模式 balanced。请基于我上传的论文制作中文可编辑科研汇报PPTX。
先一次性建立Figure证据表，再绘制“科学问题+样本/处理+核心实验/目的+验证+总发现”的全文联合总框架。
逐Figure以原图为证据，旁边用实验—发现—追问的文字与箭头讲述。主图全部覆盖，补图只在关键验证或影响结论时单列，不要机械按panel拆页。目标约15–18页，实际以内容为准。
若没有用户指定模板，则用#174994、16:9、无Logo默认学术模板。
请复用证据表和JSON进行排版，避免重新多遍阅读全文；一次性渲染检查，有问题只修改问题页。
输出科研逻辑与逐图证据、PPTX及简明质检报告。不得牺牲关键实验、科学准确性和证据溯源。
```

## 本地程序

```powershell
python scripts/index_pdf.py "paper.pdf" --outdir "output/_cache"
python scripts/build_pptx.py "output/06_PPT页面数据.json" --output "output/07_科研逻辑汇报.pptx"
python scripts/audit_pptx.py "output/07_科研逻辑汇报.pptx" --strict-images
python scripts/validate_story.py "output" --profile balanced
```

`index_pdf.py`是导航/缓存程序，不是科学审查程序；主Figure图像、原文图注与方法仍需人工/模型核查。所有PPT故事的内容须由原文支持。

**注意**：本包通过脚本静态测试和示例PPT生成测试，但未获得你Codex会话的实际token计量数据，不能保证固定比例的token下降；需要在相同论文、相近任务与模型档位下比较消耗。


## GitHub发布版说明

此仓库默认不含第三方论文原始图像与个人测试数据。生成论文幻灯片时，请自行提供有权使用的论文PDF。

安装方式：克隆本仓库到 `~/.codex/skills/paper-figure-story`；若使用Windows PowerShell：

```powershell
git clone https://github.com/<your-username>/paper-figure-story.git "$env:USERPROFILE\.codex\skills\paper-figure-story"
```

仓库所有者发布前需要自行选择许可证。
