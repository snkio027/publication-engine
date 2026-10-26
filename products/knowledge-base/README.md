# Knowledge Base publication product

本目录接管 [knowledge-base](https://github.com/snkio027/knowledge-base) 的六个出版 profile、adapter、模板、主题、语义 corpus 和消费端回归。内容仓库不再带出版执行代码或环境；它保留正文、历史 PDF、审核证据与发布资产。本目录是显式选择的产品包，不是通用引擎的内置业务分支；通用测试也不依赖该内容仓库。

## 输入与版本

[migration.json](migration.json) 绑定内容仓库 `a022de309c0ce5c3af0d306e57691f036d869698` 中的 34 份迁入文件。六个 profile、adapter、模板、主题、三份 ESD 依赖及 corpus 均逐字节保留，目录内部继续使用原相对路径以保持 adapter dependency closure。原有固定内容提交不变；ESD 仍读取明确指定内容 checkout 的 WORKTREE。

引擎实现继续锁定 `df3fcc238f03a3832de55bc128049adebe323969`。迁入产品包没有改变 `engine/`、`latex/`、`tools/` 或 Python 运行环境；它不是一次引擎升级或 Visual Profile 更新。配置入口会检查 pin 及迁入字节，拒绝未登记漂移。后续产品修订须形成新版本与验收，不覆盖这里的历史身份。

仓库当前名称是 `snkio027/knowledge-base`；profile 中的 `https://github.com/snkio027/kb` 是保留的历史来源 URL，经 GitHub 重定向访问同一仓库。配置文件的 `source_repository` 与该身份一致，不能只修改其中一边。不要重新占用旧仓库名 `kb`，否则会破坏历史链接重定向。

## 使用

以下命令在 publication-engine 根目录执行，内容路径由使用者明确提供，不要求两个仓库相邻。工作区必须是新目录或空目录，且位于内容仓库和产品输入之外；配置只写外部 `project.json`，构建输出也在外部。

```sh
uv sync --locked --group review
uv run --locked python -B products/knowledge-base/configure.py \
  --content /path/to/knowledge-base --workspace /path/to/new-publication-workspace

uv run --locked python -B engine/pub.py doctor
uv run --locked python -B engine/pub.py --project /path/to/new-publication-workspace/project.json \
  preview --profile cpp-handbook --view G6
uv run --locked python -B engine/pub.py --project /path/to/new-publication-workspace/project.json \
  preview --profile esd --view ESD-REFERENCE-001
uv run --locked python -B engine/pub.py --project /path/to/new-publication-workspace/project.json \
  preview --profile cpp-failure-model
uv run --locked python -B engine/pub.py --project /path/to/new-publication-workspace/project.json \
  candidate --profile cpp-handbook --from-preview preview/<build-id>/<attempt-id>
```

PDF 在工作区 `output/preview/<build-id>/<attempt-id>/work/output/pdf/`；全页渲染和机器证据保存在同一尝试内。候选仅复制已检查的原字节。`CONFIGURED_NOT_BUILT`、`PREPARED`、`PREVIEW_READY` 与正式发布互不等价；`publish` 仍关闭。

```sh
uv run --locked --group review python -B products/knowledge-base/check.py \
  --content /path/to/knowledge-base --output /path/to/new-product-check.json
uv run --locked --group review python -B products/knowledge-base/test-configure.py
```

真实产品构建、比较及新证据见本批迁移审核记录。旧回归记录是历史事实，不因文件迁移被当作重跑；旧预览仍须使用其历史版本工具查阅，不会被新入口接管。
