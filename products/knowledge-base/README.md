# Knowledge Base publication product

本目录是 [knowledge-base](https://github.com/snkio027/knowledge-base) 的活动出版产品包：选源、合订编排、adapter、产品模板/主题、阅读样本和真实产品验收。正文、内容实验和书籍发布事实归知识库；通用引擎不内置 KB 章节。职责和安全规则统一见 [Repository boundaries](../../docs/repository-boundaries.md)。

## 当前身份与迁移历史

[product.json](product.json) 定义产品 `knowledge-base / 1.1.0`、引擎实现 pin、六个 profile、34 份产品输入摘要和三个真实验收 trial。取得本次审核记录所指定的产品交付 Git commit；不要把仓库 HEAD、引擎 pin、内容 revision、Visual Profile 或出版版本当作同一个版本。

配置器生成本机 `project.json`，绑定产品版本/目录/清单摘要、输入集合摘要和所选引擎 pin。每次准备重新验证产品清单与输入，配置后漂移会被拒绝。产品工具脚本由交付 Git commit 绑定；清单的 34 项是排版/阅读输入，不声称清单本身签名认证脚本。

[migration.json](migration.json) 只保留最初从 `a022de3…` 迁入的不可变事实，不再由日常配置/验收读取。产品演进更新当前清单并重新验收，不修改历史迁移记录。当前仍逐字节保留这 34 份文件；新版本变化在运行边界和验收工具，不在版式。

历史 profile 的 `https://github.com/snkio027/kb` 与 source_repository 保留原身份，经 GitHub 重定向到同一知识库。Handbook 固定 `8f479de…`，FM 固定 `45b305e…`，ESD 使用显式 checkout 的 WORKTREE。内容仓库须具有相应历史 Git 对象；浅克隆可能不足。不要重新占用旧名 kb。

## 日常配置与构建

以下在 publication-engine 根目录执行。只需两个 checkout 和本机受支持环境；无需保留任何旧 publication/build 目录。

```sh
uv sync --locked --group review
uv run --locked python -B products/knowledge-base/configure.py \
  --content /path/to/knowledge-base --workspace /path/to/new-workspace
uv run --locked python -B engine/pub.py doctor
uv run --locked python -B engine/pub.py --project /path/to/new-workspace/project.json \
  preview --profile cpp-handbook --view G6
uv run --locked python -B engine/pub.py --project /path/to/new-workspace/project.json \
  candidate --profile cpp-handbook --from-preview preview/<build-id>/<attempt-id>
```

工作区必须新建或为空，位于内容、产品及活动实现输入之外；引擎 checkout 的忽略目录 `tmp/` 合法。输出在 `output/preview/<build-id>/<attempt-id>/work/output/pdf/`。候选仅冻结已有字节，不重新编译、不发布。

```sh
uv run --locked --group review python -B products/knowledge-base/check.py \
  --content /path/to/knowledge-base --output /path/to/new-adapter-check.json
uv run --locked --group review python -B products/knowledge-base/test-configure.py
uv run --locked --group review python -B products/knowledge-base/qualify.py \
  --project /path/to/new-workspace/project.json --output /path/to/new-qualification
```

check 执行当前产品适配保真；qualify 按清单构建 G6、ESD Reference、FM 整书，核验完整机器证据、冻结候选、执行阅读结构检查并生成 contact sheets。`result.json` 的 `CURRENT_PRODUCT_CHECKED` 只表明上述机器检查完成；失败/取消不提交成功。FM 当前 0 个适用阅读 fixture，保持 `NOT_COVERED`。人工阅读、跨阅读器兼容、C++ 技术验证和正式发布均不由该命令完成。

## 可选历史比较

先完成当前产品验收，再显式提供旧尝试与摘要。无隐式路径查找、无历史数据自动下载或替代。

```json
{
  "cpp-handbook": {
    "attempt": "/absolute/path/to/old/preview/build/attempt",
    "artifact_manifest_sha256": "<完整 SHA-256>"
  }
}
```

为 results 中每个 profile 提供一项，保存到外部 baseline JSON：

```sh
uv run --locked --group review python -B products/knowledge-base/check_navigation.py \
  --project /path/to/new-workspace/project.json \
  --results /path/to/new-qualification/results.json \
  --baseline /path/to/baselines.json --output /path/to/new-comparison.json
```

比较核验旧/new artifact manifest，检查源与 AST、页数、destination 位置、outline 和正文点击区域、扣除已登记生成身份后的文本；PNG 差异是人工复核信号，不自动等于视觉失败或接受。目前一次 trial 比较一个视图。缺少显式基线、摘要变化或旧证据不符合验证格式时失败；不要重写旧记录来适配。

当前 `doctor / preview / candidate` 可用，`publish` 关闭。`PREPARED`、机器验收、候选、用户接受和正式发布是不同状态。
