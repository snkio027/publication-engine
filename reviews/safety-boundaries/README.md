# 缓存执行与候选输出边界修复

2026-10-24 · **IMPLEMENTED / LOCALLY VERIFIED / REVIEW PENDING**。本批只处理独立化审核中的 P1/P2；不变更版式、产品内容或正式发布能力。

## 实现与来源

审核 Base：`5acfa5448957cf7c9ad755db510c48042b5c91fa`。最终可执行实现 pin：`df3fcc238f03a3832de55bc128049adebe323969`。后续记录提交不改变 pin 选取的 `engine/`、`latex/`、`tools/` 或环境文件。KB 消费者 Base 为 `ffd2db9999a79bb237954ad45a6c59117baa38e6`。

### P1：执行的是被锁定源码，而不是旁路缓存

`-B` 禁止缓存写入，但不禁止缓存执行。新增 `source_runtime.py`；受支持的脚本入口先用内建文件读取、`compile`、`exec` 载入策略，早于普通文件系统模块导入。策略从 CPython 已加载的 frozen module 取得 loader，不先导入可能被缓存遮蔽的策略依赖。

常规导入与显式 source loader 均只读取 `.py`，不读取 timestamp/hash `.pyc`；bytecode-only 模块拒绝。策略自身的缓存也不能先运行。准备身份增加 `python_import_policy: source-only-no-pyc-v1`。缓存仍不是快照输入，但不再能以另一份实现参与执行。

主入口、直接执行的 worker、两个检查工具和测试入口均先安装策略；KB 中会导入引擎的两个集成检查也同步安装。没有删除用户缓存、改用宽泛目录扫描或事后恢复历史资产。

信任前提保持有界：固定的 CPython 3.14.8 / uv 环境、解释器启动、入口与策略源码、受信本地产品代码。这里不防御任意宿主预载模块、恶意自定义 importer、被篡改解释器或任意源码；也不把未经保护的宿主导入、`python -m` 当作支持的启动合同。策略依赖本项目固定的 CPython frozen loader，不声明其他 Python 实现支持。

### P2：候选不再只对输出末级目录做 no-follow

共享 `absolute_directory()` 从 `/` 开始，以目录句柄逐级拒绝 symlink，不先 `resolve()` 隐藏链接。预览初始化、准备和候选均使用它。候选保留同一个已验证输出根句柄，完成 workspace marker 检查、原尝试读取和新候选写入，不在标记检查后按字符串重新打开根目录。

测试覆盖输出根链接、父目录链接、既有内部目录链接，以及真实成功预览上的 CLI 反例。链接在调用前已存在，无并发换目录。候选必须失败；临时历史目录的完整文件集合和字节不变。正常候选仍复制原字节，不重新编译。

## 执行记录

最终测试与环境命令：

```sh
uv run --locked --group review python -B tests/run.py \
  --output /private/tmp/publication-safety-fix.nv4n7E/full-guard-final
uv run --locked --group review python -B engine/pub.py doctor
```

逐套日志、[结果](results.json)、[被测文件摘要](tested-files.json)及[环境](environment.json)绑定本次实际执行。消费者的源、PDF、导航与历史资产保护证据由 KB 的 `publication/reviews/safety-boundaries/` 保存，不移入本引擎仓库。

| 测试文件 | 用例数 | 结果 | SKIP |
| --- | ---: | --- | ---: |
| test-publication-isolation.py | 15 | PASS | 0 |
| test-candidate.py | 11 | PASS | 0 |
| test-evidence.py | 17 | PASS | 0 |
| test-source-runtime.py | 7 | PASS | 0 |
| test-reading.py | 11 | PASS | 0 |
| test-preview.py | 14 | PASS | 0 |
| 合计 | 75 | PASS | 0 |

最终 native 套件仍是 7 项组合/判据检查与 7 项真实编译类测试，不称为 14 次独立 PDF 构建。其中真实成功测试增加候选 CLI 父目录链接反例；正向候选字节校验、4 处受保护写入拒绝、编译失败、INT/TERM/KILL 和错误输出拒绝继续通过。测试期间实现摘要未漂移。

本机环境：macOS 27.0.1 arm64、uv 0.13.4、uv-managed CPython 3.14.8、pypdf 6.10.0、Pillow 12.0.0、Pandoc 3.12.1、LuaHBTeX 1.24.0 / TeX Live 2026、Poppler 26.05.0；Seatbelt 写入拒绝探测成立。Python 声明、锁文件和版本文件未修改。

KB 按最终 pin 重新完成 6 个历史 profile / 58 次适配检查，以及 G6 48 页、ESD Reference 58 页、FM 158 页的真实构建、全页渲染与候选冻结。57 份源/AST 文件、5,531 个 destination 位置、400 个链接注释及书签一致；261/264 页 PNG 摘要一致，三处差异仅为身份页。11 页自查未见新增 blocker。上述消费者证据与 75 项引擎回归分别计数。

## 批内自查与未验证边界

[试跑记录](trial-history.json)与[首轮失败日志](trials/cache-identity-first.log)保留，不覆盖历史结果：首轮测试错误假设“没有缓存”和“新增缓存”拥有相同 Git 状态，而临时 engine 没有忽略缓存文件名。修正为比较同一组缓存路径下两份不同缓存内容；固定源码运行、历史哨兵未改等判据不放宽。

`438b015` 的首轮完整 74 项回归及三产品构建通过后，自查又确认入口早期 `import json` 可被同名 `json.pyc` 遮蔽。该临时反例确实改写了哨兵，即使进程最终失败，也不能视为隔离成立。随后将策略前移到首次文件系统导入之前，增加该反例，形成最终 pin 并重新执行完整验证；前一轮通过不替代最终结果。

正向对照单独证明未经保护的 `-B` 子进程确实执行伪造缓存。受保护路径检查缓存内容变化、伪造匹配时间戳、缺失源码、显式 loader、检查工具及启动同名模块；只有对照会按测试设计触碰临时哨兵，生产仓库和真实历史制品均不用于故障注入。

不扩大为完整主机隔离、hermetic build、精细 layout dependency closure 或跨机器字节级可复现；不重测 C++ 技术内容、外部阅读器或非 macOS 平台。不存在 CI 通过声明。正式 `publish` 保持关闭，没有修改 release/tag、字体、Lua/LaTeX 或产品 profile。旧独立化记录保持历史身份，本批修复等待集中复审。
