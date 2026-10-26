# Repository boundary closure — 2026-10-26

状态：**IMPLEMENTED / LOCALLY VERIFIED / PENDING REVIEW**。本批统一现行文档、显式产品身份、日常验收与迁移对照分离、公共输出约束。不改正文、历史 profile、版式、已发布资产或 Zig 未跟踪文件；不正式发布。

## 版本与范围

| 身份 | 精确值 |
| --- | --- |
| Knowledge Base 审核基线 | `be9ec52d673d284a9c85f8f8607bd60b55ed3e1d` |
| Engine 审核基线 | `9d82561f3881d467879e7d5c9676c3f6905b37d0` |
| 新引擎实现 pin | `f809e51d15dc7b5937aac02aee4dcbba31f40098` |
| 被实际运行的产品交付提交 | `c3c00708649a2cec166a199f4178c18f699074d3` |
| 当前产品 | `knowledge-base / 1.1.0`，`products/knowledge-base/` |
| 产品清单 SHA-256 | `8e513874e5c3a6fdf2591a7275bc52b3d935557339e8f8d1da050110745bc94f` |
| 产品输入集合摘要 | `52f7b598a17e0e7c392d0c2102cbff2215edfe7ae03a954b2541e4910b254170` |
| 原迁移来源 | `a022de309c0ce5c3af0d306e57691f036d869698`，仅历史事实 |

最后的证据登记提交不改实现 pin 或产品字节。[统一合同](../../docs/repository-boundaries.md) 是现行规则的单一入口。[product.json](../../products/knowledge-base/product.json) 是当前产品定义；migration.json 原字节不变，不再作为运行锁。

## 实际检查

平台：macOS arm64、uv-managed CPython 3.14.8；Python/PDF 依赖版本未调整。下表均为**本地执行证据，不是 CI 或技术内容重验**。

| 层 | 结果 | 证据 |
| --- | --- | --- |
| 通用逻辑/适配/真实编译回归 | 84 项 PASS，0 SKIP | [原始结果](engine-checks/results.json)及同目录各套日志 |
| 产品配置回归 | 13 项 PASS；含 3 入口 × 3 受保护位置矩阵 | [原始日志](product-tests.log) |
| 当前产品适配 | 六个 profile、58 项源/adapter 保真检查通过 | [adapter-check](adapter-check.json) |
| 所有 profile 准备 | 6 次 PREPARED；不是 PDF 验收 | [prepare](prepare.json) |
| 当前真实产品验收 | 三份预览、候选与全页渲染完成 | [终态](qualification/result.json)、[逐产品记录](qualification/results.json) |
| 显式历史比较 | 57 份源/AST 同字节；页数、5,531 个目标位置、outline 和 400 个链接注释一致 | [comparison](comparison.json) |
| 错误历史摘要反例 | 非零退出、匹配摘要错误、无成功输出 | [negative](comparison-negative.json) |
| 代表页自查 | 实际查看 9 张新页图，未见新增阻断问题 | [页图与检查范围](visual-inspection.json) |
| 资产保护 | 1,681 个原文件不变，含 517 份 PDF；34 份产品输入不变 | [逐文件摘要](protection.json) |

新增通用反例包含：手写 descriptor 将输出置于内容/产品/实现目录；大小写不敏感 macOS 上的同目录别名；配置后产品漂移；未声明产品输入；旧 descriptor 对新清单失效；派生工具拒绝迁址或没有 root 绑定的尝试。引擎 `tmp/` 的正例也实际通过。原有 Git filter、source-only、候选 symlink、同步失败和取消检查继续执行。

首轮正例发现合成引擎仓库没有忽略 tmp，写入会使 Git 上下文变化，准备因此正确拒绝。修正的是测试夹具的忽略规则，没有放宽生产漂移检测；随后对最终实现完整重跑上述 84 项。

## 两个干净 checkout 的结果

本轮通过本地 `git clone --no-hardlinks` 取得两个已提交版本；未复制忽略目录，内容 checkout 无 `publication/build`，没有旧本机尝试。新引擎通过 `uv sync --locked --offline --group review` 安装锁定环境。两者运行后 Git status 仍为空，详见 [fresh-checkouts](fresh-checkouts.json)。这是本机全历史克隆验证，不声称从公网首次安装或浅克隆验证。

默认 qualify 完成后才单独提供 [baselines](baselines.json) 执行历史比较。它不隐式查找知识库旧 build。具体 argv、退出码、时长和输出已保存在逐产品记录与 `.stdout/.stderr` 中。外部绝对路径是本次证据，不是分发后的默认路径。

| 制品 | 页数/全页渲染 | 语义阅读 fixture | 历史 PNG 对照 |
| --- | --- | --- | --- |
| G6 | 48 / 48 | 3，STRUCTURAL_PASS | 47 张相同，仅第 2 页生成身份改变 |
| ESD Reference | 58 / 58 | 3，STRUCTURAL_PASS | 57 张相同，仅第 2 页生成身份改变 |
| FM Handbook | 158 / 158 | 0，NOT_COVERED | 157 张相同，仅第 2 页生成身份改变 |

总计 264 页，261 张页图字节相同。文本仅有已登记的 preparation/source commit 替换；页数、目标位置及点击区域未漂移。9 张实际查看页为 G6 2/24、ESD 2/24、FM 2/108/109/153/154。历史 preview/正式阅读版标签按各 profile 保留，不因当前运行变成新发布。未做全书人工逐页阅读、阅读器兼容复测、C++ 实验/性能/并发复测。

## 复跑入口

```sh
uv run --locked --group review python -B tests/run.py --output /path/to/new-engine-checks
uv run --locked --group review python -B products/knowledge-base/test-configure.py
uv run --locked python -B products/knowledge-base/configure.py \
  --content /path/to/knowledge-base --workspace /path/to/new-workspace
uv run --locked --group review python -B products/knowledge-base/check.py \
  --content /path/to/knowledge-base --output /path/to/new-adapter-check.json
uv run --locked --group review python -B products/knowledge-base/qualify.py \
  --project /path/to/new-workspace/project.json --output /path/to/new-qualification
uv run --locked --group review python -B products/knowledge-base/check_navigation.py \
  --project /path/to/new-workspace/project.json --results /path/to/new-qualification/results.json \
  --baseline /path/to/explicit-baselines.json --output /path/to/new-comparison.json
```

产品准备的实际清单和 root 绑定见 [project.json](project.json)，运行时实现/产品字节见 [tested-inputs](tested-inputs.json)。机器证据摘要与候选回执在 builds/ 下；实际 PDF 和全页 PNG 留在专用工作区，不进入正式 release 目录。

## 保留边界

- `Final Gate`/“参考”仍由通用 Lua 的既有逻辑识别；显式产品语义标注是后续分层任务，本批未实施。
- FM corpus 覆盖未补，不把 0 fixture 或全页渲染算作语义阅读 PASS。
- 已发布两本手册的 tag 和 8 个 asset ID/size/digest 登记与前批相同；本轮没有重新下载远端载荷。未创建或修改 release。
- 正文、实验、Gate、旧证据、历史布局、Python 锁均未变。只读历史材料不是第二套当前构建入口。
- 机器完成、代表页自查、集中审核接受和正式发布分别记录。本批等待审核，publish 继续关闭。
