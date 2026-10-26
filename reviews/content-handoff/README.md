# Knowledge Base publication handoff

日期：2026-10-26。状态：**IMPLEMENTED / LOCAL QUALIFICATION COMPLETE / PENDING REVIEW**。

用户要求将内容仓库改名为 `knowledge-base`，并确认将 profile、adapter、模板与活动出版回归全部迁出，只留下内容和历史资产。内容 Base 为 `a022de309c0ce5c3af0d306e57691f036d869698`；引擎 Base 为 `1abca318e5289431034eb800c02d49e43ea2aac6`。本轮没有正式发布操作。

## 实现与边界

- 新增 [products/knowledge-base](../../products/knowledge-base/README.md)，包含六个 profile。30 份 profile/adapter/template/theme/table 文件、三份 ESD 依赖和一个 corpus 共 34 份逐字节迁入；[迁移清单](../../products/knowledge-base/migration.json)绑定原提交、路径、字节数和 SHA-256。
- 三个消费端检查脚本从原仓库改为显式接收内容/描述文件路径，新增独立配置入口。产品包不接入通用测试注册表，不要求通用引擎 checkout 旁边存在内容仓库。
- 内容仓库删除 107 个内嵌引擎、旧 v1 出版实现、环境声明、入口与配置文件。旧实现由 Git 保留，不复制为第二套活动代码。`reviews/`、`releases/` 的历史脚本是证据附件，不是受支持的构建入口。
- 引擎实现 pin 仍为 `df3fcc238f03a3832de55bc128049adebe323969`。通用代码、Lua/LaTeX、Python 及依赖锁、原有测试和历史审核文件均不变。19 份选定引擎输入按 pin 校验；相对引擎 Base 的 53 个非 README 原文件逐字节不变。
- 生成的描述文件与新输出位于内容仓库外。拒绝非空工作区、重复配置、链接父路径、内容/引擎/产品目录、产品字节或 pin 漂移；保留先装 source-only 策略再导入模块的启动顺序。
- 历史 profile 的 `repository` 字段保留 `snkio027/kb` 原字节，依赖更名后的 GitHub 重定向；描述文件与它保持一致。不能只改一边。此 URL 与知识库新名称表示同一个仓库 ID，不是另一个内容源。

## 实际验证

运行环境：macOS arm64、uv 管理的 CPython 3.14.8，现有 Pandoc / LuaLaTeX / Poppler。完整命令和输出见下列证据，不声明 CI。

| 检查 | 实际结果与证据 |
| --- | --- |
| 通用引擎回归 | **75 PASS / 0 SKIP**：50 logic（含缓存与链接父目录反例）、11 adapters、14 native；[完整结果](engine-checks/results.json) |
| 新配置边界 | **10 PASS**；[命令](checks/commands.json)、[unittest 输出](checks/product-configure.stderr) |
| 迁入原字节与源适配 | **34 文件相同、58 source adapter checks PASS**；[记录](product-check.json) |
| 六种 profile 输入准备 | 全部 **PREPARED**，不是六份 PDF 全文重建；[记录](prepare.json) |
| 三个真实产品 | G6 **48 页**、ESD Reference **58 页**、FM **158 页**，全页渲染并冻结候选；[构建与比较](builds.json) |
| 内容与分页对照 | **57 份 source/AST 相同、264 页页数相同**；261 张 PNG 完全相同，每份仅第 2 页生成身份变化 |
| 导航 | **5,531 个 destination 位置相同、400 个链接及 outline 相同**；[导航明细](navigation.json) |
| 代表页自查 | **9 页已查看**：三份第 2 页、G6/ESD 第 24 页、FM 第 108/109/153/154 页；[页图与边界](visual-inspection.json) |
| 文档 | 72 份 Markdown、977 处本地链接，无结构/链接错误；[结果](checks/source-docs.stdout) |
| 历史保护 | **1,678 个文件相同，含 517 份已有 PDF**；四个 Zig 未跟踪文件不变；[逐文件摘要](protection.json) |
| GitHub 更名 | 原/新 URL 指向 ID `1334077602`；两组 tag、两条 Release 和八个资产 ID/大小/GitHub 摘要不变；[只读核对](remote.json) |

完整构建使用 `qualify.py --project <external-project.json> --output <new-directory>`，随后运行 `check_navigation.py --content <content> --results <results.json> --output <new-json>`。生成的 [project.json](project.json) 是本次机器路径记录，不应作为跨机器配置直接复用；重新接入应调用产品 `configure.py`。

机器成功证据按产品保存于 `builds/`；[tested-inputs.json](tested-inputs.json) 绑定本轮实际产品与引擎文件摘要。产品配置测试最终版增加了拒绝将引擎自身当作内容的反例；三份构建使用相同 descriptor 和迁入字节，配置入口的这一前置拒绝不参与渲染输入。最终十项配置测试已重跑。

## 发现与处理

删除旧脚本后，既有 C++ 文档检查发现资产登记中的四个源码文件链接失效。没有放宽检查器：把该登记的五处实现链接（含模板目录）固定到其所描述的 `6ad0ade` 历史提交，并添加日期注记；原核对事实、摘要和证据时间口径不变。随后原检查器通过。其他不可变历史审核材料仍应在各自原提交语境阅读，当前归档说明明确这一点。

本轮未发现由迁移新增的裁切、乱码、代码身份或版式阻断。原有非阻塞视觉限制保持，不以本轮迁移重开排版设计。

暂存检查 `git diff --cached --check` 另报告迁入 `products/knowledge-base/design/texlive.profile` 的既有末尾空行。该文件与原 Git blob 字节相同，为遵守原件保真未格式化；排除这一已核对文件后的暂存空白检查通过。此项不登记为“无例外全绿”。当前八份入口/接管文档的 89 处本地链接另行检查通过，见 [entry-links.json](entry-links.json)。

## 未做什么

未重跑 C++/性能/并发实验，未重建 407 页全书、全部 12 份历史视图或全阅读器矩阵；没有新视觉批准、跨平台或确定性构建声明。远端资产核对使用 GitHub 返回的 ID/大小/摘要，**没有重新下载 Release 资产**。已发布 PDF、tag、授权与分发记录不变，`publish` 仍关闭。这里是本地实施验收证据，不代替用户集中审核或正式发布授权。
