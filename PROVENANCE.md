# 来源与迁移边界

本项目起点是 [KB 7fb0ad0](https://github.com/snkio027/kb/tree/7fb0ad0c85a4835fabe6482a9e73828d81f25b6a/publication)。采用新仓库独立历史；原提交和旧发布资产仍留在 KB，不声称旧 commit 被搬入新 Git 历史。

## 第一阶段：通用引擎抽取

首次抽取范围为 `publication/engine/`、`publication/latex/`、两个通用阅读工具及 Python 环境配置。当时产品 `profiles/`、语义 corpus、正文、出版回执与 PDF 没有迁入。新增 root/project 接口只负责来源与输出拆分；原有 AST 组合、版式函数、Lua 和共享 LaTeX 不改。

通用回归来自原协议、阅读和编译测试，并改为独立临时 Git 仓库。`tests/fixtures/` 的三个小文件源于原 ESD adapter/template/theme，仅用作合成输入的集成测试夹具，不构成 ESD 产品配置或新的 ESD 权威副本。它们的存在不要求用户具有 KB 历史对象。

没有在本次迁移中新增或更改第三方字体、TeX 包或工具许可证；它们仍由本机安装环境提供，未捆绑分发。仓库公开不自动代表已经授予某种新的开源许可证。本批不擅自为历史材料重许可。

## 第二阶段：产品接管

`9d82561f3881d467879e7d5c9676c3f6905b37d0` 将知识库 `a022de309c0ce5c3af0d306e57691f036d869698` 中 34 份活动产品文件逐字节接入 `products/knowledge-base/`。六个 profile、adapter、模板、主题、ESD 依赖和 corpus 由本仓库维护；正文、内容验证、PDF、发布回执及历史证据仍在更名后的 knowledge-base。精确记录见 [migration.json](products/knowledge-base/migration.json) 与 [迁移验收](reviews/content-handoff/README.md)。这些历史记录不回写。

## 当前维护

当前产品定义由 [product.json](products/knowledge-base/product.json) 管理，配置器不再以迁移事实作为永久运行锁。职责、版本、写入和验收以 [Repository boundaries](docs/repository-boundaries.md) 为单一合同。旧知识库实现只在其精确 Git 历史中保留，当前没有兼容执行副本。
