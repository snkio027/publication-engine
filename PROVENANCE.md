# 来源与迁移边界

本项目起点是 [KB 7fb0ad0](https://github.com/snkio027/kb/tree/7fb0ad0c85a4835fabe6482a9e73828d81f25b6a/publication)。采用新仓库独立历史；原提交和旧发布资产仍留在 KB，不声称旧 commit 被搬入新 Git 历史。

抽取范围为 `publication/engine/`、`publication/latex/`、两个通用阅读工具及 Python 环境配置。产品 `profiles/`、语义 corpus、正文、出版回执与 PDF 没有迁入。新增 root/project 接口只负责来源与输出拆分；原有 AST 组合、版式函数、Lua 和共享 LaTeX 不改。

通用回归来自原协议、阅读和编译测试，并改为独立临时 Git 仓库。`tests/fixtures/` 的三个小文件源于原 ESD adapter/template/theme，仅用作合成输入的集成测试夹具，不构成 ESD 产品配置或新的 ESD 权威副本。它们的存在不要求用户具有 KB 历史对象。

没有在本次迁移中新增或更改第三方字体、TeX 包或工具许可证；它们仍由本机安装环境提供，未捆绑分发。仓库公开不自动代表已经授予某种新的开源许可证。本批不擅自为历史材料重许可。
