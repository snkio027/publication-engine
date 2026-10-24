# 独立化验证记录

2026-10-24 · **IMPLEMENTED / LOCALLY VERIFIED / REVIEW PENDING**。本记录不是用户接受、CI 通过或正式发布。

## 来源与交付边界

从 [KB `7fb0ad0`](https://github.com/snkio027/kb/tree/7fb0ad0c85a4835fabe6482a9e73828d81f25b6a/publication) 抽取通用实现，采用独立 Git 历史。可执行实现锁定为 `e740367ac9c382f245bf29a0b86f019982622154`；后续审核提交增加测试与记录，不改变该 pin 所选取的 `engine/`、`latex/`、`tools/` 和环境配置字节。

本项目提供显式的 engine / content / product / output 根目录协议、精确实现 pin、受限预览和候选冻结。KB 保留历史 profile、产品 adapter、正文、阅读 corpus、原始审核和 release；本项目没有 KB checkout 或 KB 历史对象的测试前置依赖。共享 LaTeX、Lua、排版组件未改，正式 `publish` 入口仍关闭。

## 本地执行结果

最终命令在 `/Users/nekoreb/Workspace/03_Projects/publication-engine` 执行：

```sh
uv sync --locked --group review
uv run --locked --group review python -B tests/run.py --output tmp/qualification-final
uv run --locked --group review python -B engine/pub.py doctor
```

| 测试文件 | 用例数 | 结果 | SKIP |
| --- | ---: | --- | ---: |
| test-publication-isolation.py | 15 | PASS | 0 |
| test-candidate.py | 9 | PASS | 0 |
| test-evidence.py | 17 | PASS | 0 |
| test-reading.py | 11 | PASS | 0 |
| test-preview.py | 14 | PASS | 0 |
| 合计 | 66 | PASS | 0 |

最后一套包含 7 项组合/判据检查与 7 项真实编译类测试，不把 14 项全部称为独立 PDF 构建。真实测试覆盖成功、编译失败、INT/TERM/KILL、语义组件和故意破坏的 PDF 判据。正向编译同时尝试写入临时历史 dist、引擎、正文和产品模板；四处都被拒绝，原字节不变。独立输入根、带空格路径、无关 cwd、engine/content commit 混用、引擎漂移、输出接管、symlink、越界、Git filter、终态同步及提交窗口均有回归。

结果、精确命令和耗时见 [results.json](results.json)，逐套原始输出见同目录 `.log`。实际测试与实现摘要见 [tested-files.json](tested-files.json)。测试执行器前后核对实现文件，本次最终执行未观察到漂移。

[environment.json](environment.json) 记录本机 macOS 27.0.1 arm64、uv 0.13.4、uv-managed Python 3.14.8、pypdf 6.10.0、Pillow 12.0.0、Pandoc 3.12.1、LuaHBTeX 1.24.0 / TeX Live 2026、Poppler 26.05.0 及实际路径/摘要。Seatbelt 写入拒绝探测成立。未运行 Linux/Windows 或 GitHub CI。

## 消费者实测

KB 集成记录位于其 `publication/reviews/standalone/`，不复制整套产品证据到引擎仓库：

- 六个原 profile 共 58 次源适配检查通过；共享视觉文件和五个编排函数与抽取前基线一致。
- G6 48 页、ESD Reference 58 页、FM 158 页，共 264 页实际编译、全页渲染及候选冻结。
- 57 份源/AST 快照文件逐字节一致；5,531 个 PDF destination 位置一致；400 个正文/导航链接注释及书签层级一致。
- 261 页 PNG 摘要一致，三份 PDF 各自仅第 2 页生成身份变化；17 页自查未发现新增视觉 blocker。
- G6/ESD 既有语义 corpus 各命中 3 项；FM 无匹配 fixture，仍为 `NOT_COVERED`，由全页比较与代表页自查补充，不伪报 corpus PASS。

这些是本地消费者回归，不等于全部六个产品全量 PDF 重建，也不等于新版正文或 C++ 技术验证。407 页整书未在本批重建，阅读器兼容性未重测。

## 批内试跑与限制

[trial-history.json](trial-history.json) 保留前置三次完整试跑：前两次为 FAIL，第三次为 PASS。早期一次 native 执行读到旧 CLI（不接受 `--project`），另一次捕获到 `pub.py` 内容漂移；未把部分通过计为全套通过。漂移外因未确定，也不归咎于某个未经证实的进程。随后固定实现提交、增加执行期间摘要保护，在临时目录完成一轮，再回到最终目录完成上述 66 项完整重跑。最终实现字节与 pin 一致；本记录不声称已经证明外部环境永不漂移。

本批没有实现细粒度 layout dependency closure、完整读取白名单、跨机器 deterministic build、缓存、多平台或正式发布事务。原有 short-tail / whitespace 等视觉限制保留；没有创建新 Visual Profile。当前结果供集中审核，不能据此重发历史手册。
