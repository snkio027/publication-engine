# Publication Engine

独立的 macOS 技术手册出版工具：冻结外部内容输入，生成受限 PDF 预览，核对内容和证据，再冻结供审核的候选字节。**不是正式发布服务。**

本项目从 `snkio027/kb@7fb0ad0c85a4835fabe6482a9e73828d81f25b6a` 抽取。首批独立化不改变 Visual Profile v1.0、Lua/LaTeX 规则或正文。源仓库保留产品 adapter/profile、内容历史、审核和发布资产；本项目只维护通用引擎、共享视觉机械与通用回归。参见 [来源与迁移边界](PROVENANCE.md)。

2026-10-26：知识库内容仓库更名为 `snkio027/knowledge-base`，并迁出全部活动出版代码与产品配置。六个书籍 profile 及消费端回归由 [knowledge-base 产品包](products/knowledge-base/README.md) 接管；内容 checkout 只读，新工作区位于其外。通用引擎、Visual Profile、Python 锁和历史审核证据不变。本批结果见[接管验证](reviews/content-handoff/README.md)。下文来源叙述保留首次独立化的历史范围，不表示产品仍在内容仓库维护。

## 支持范围

- macOS Seatbelt；没有无沙箱回退，不声明 Linux/Windows/CI 支持。
- uv-managed CPython 3.14.8；pypdf 6.10.0；review 组 Pillow 12.0.0。
- 本机 Pandoc、LuaLaTeX、Poppler、TeX 包与字体；由 `doctor` 解析和记录。
- 可信本地 Git 内容仓库与产品目录；不联网拉取正文，不运行任意不可信插件。
- 一个项目描述文件指定一个内容仓库；支持多个产品视图，不扩展多仓库内容聚合。

## 运行

先取得内容项目所锁定的引擎提交，再同步运行环境。以下 `<engine>` 是本仓库路径，`<project>` 是内容项目中的描述文件，路径都可带空格：

```sh
uv sync --project <engine> --locked --group review
uv run --project <engine> --locked --group review python -B <engine>/engine/pub.py doctor
uv run --project <engine> --locked python -B <engine>/engine/pub.py preview \
  --project <project> --profile handbook
uv run --project <engine> --locked python -B <engine>/engine/pub.py candidate \
  --project <project> --profile handbook --from-preview preview/<build-id>/<attempt-id>
```

`--view ID` 可重复；`--prepare-only` 只冻结输入。`candidate` 复制已完成预览的原字节，不重新编译。`publish` 保持关闭。旧 KB 尝试不能通过修改路径被升级成新引擎候选，应使用历史工具查阅。

### 项目描述文件

由内容项目维护，三个路径相对于该文件所在目录解析；它们不是相对于当前 shell 目录，也不是相对于引擎目录：

```json
{
  "schema_version": 1,
  "engine": {
    "repository": "https://github.com/snkio027/publication-engine",
    "commit": "<完整的 40 位引擎提交 SHA>"
  },
  "source_repository": "https://github.com/owner/content",
  "content_root": "..",
  "product_root": "..",
  "output_root": "build/standalone",
  "profiles": {
    "handbook": "publication/profiles/handbook/profile.json"
  }
}
```

`profile.json` 保留现有 schema v2：`sources[].path` 相对于 content root；完整 Git revision 从该内容仓库取源，`WORKTREE` 从该工作树取源；profile 路径及 `dependencies` 相对于 product root。profile 的 repository 必须与 `source_repository` 一致。引擎代码、共享布局、工具和 Python 配置逐字节匹配锁定提交；只改 README/审核记录不要求重锁实现。这里的 repository URL 是来源声明，Git 对象与实际字节校验是本地绑定，不是远端签名认证。

输出必须是单独的空目录，或已带本工具标记的输出目录。拒绝把非空历史目录接管为输出，也拒绝根目录、源根及其祖先、隐藏管理目录和 symlink 路径。内容/产品目录可相同，引擎必须是独立 checkout；不要求它们互为邻居。

## 输入、身份和隔离

准备记录分别保留 engine/content Git 上下文、引擎 pin、描述文件摘要、实际 root 绑定、输入字节和运行身份。源 commit 与引擎 commit 不互换。内容链接解析仍从 content root 的固定 Git revision 取源，不能误用新引擎仓库的历史。

快照内部沿用 `publication/engine/`、`publication/latex/` 的**虚拟命名空间**，这是现有渲染 ABI，不是安装目录要求。产品文件与该命名空间碰撞时拒绝；每个实际输入另记录所属 root 与相对路径。固定 Git 源不因工作树更改而切换版本；WORKTREE、产品、引擎或描述文件漂移会阻止成功。目录位置参与当前来源身份，不承诺移动目录后 build ID 不变。

worker 仅可写本次 `work/`，禁止联网；输入、引擎/内容/产品目录和历史输出不在可写范围。原始 AST 保真、PDF 内容/导航检查、全页 PNG 摘要、视图集合和候选冻结继续采用既有合同。成功终态通过文件同步后的排他 link 提交；缺少、失败或取消终态不能解释为成功。

文档指定的脚本入口在首次文件系统模块导入前，从原始源码安装 `source-only-no-pyc-v1` 策略：常规与显式 source loader 都只编译 `.py`，不读取 timestamp/hash `.pyc`；无源码的 bytecode loader 明确拒绝。策略通过已加载的 CPython frozen loader 安装，自身也从源码启动，不能先消费自己的缓存。`-B` 只作为禁止缓存写入的补充，不再承担防止缓存执行的安全保证。入口、策略源码、CPython/uv 启动与受信运行环境仍是信任前提；不支持通过 `python -m` 或未经保护的宿主任意导入来建立这一保证。这不是任意 Python 的安全加载器或系统启动隔离。

预览和候选使用同一逐级 no-follow 输出路径检查。候选从 `/` 遍历到输出根，标记验证、源尝试读取和候选写入保留同一个根目录句柄，不再只检查最后一级。拒绝的 linked ancestor 不会被接管，也不会先复制再报告失败。定向修复与反例证据见 [安全边界修复](reviews/safety-boundaries/README.md)。

本批没有实施精细布局依赖闭包或完整读取白名单。选定的仓库输入与工具在前后核对；额外 TeX/字体 `.fls` 依赖仍是运行后观察，不是 hermetic build 或跨机器字节级可复现证明。可信 adapter 的错误检测也不等于对恶意 Python 的语义证明。

## 检查与人工阅读

```sh
uv run --project <engine> --locked --group review python -B <engine>/tests/run.py \
  --output <engine>/tmp/check-new
uv run --project <engine> --locked python -B <engine>/tools/reading-review.py \
  <completed-attempt> --corpus <content-project>/reading-corpus.json
uv run --project <engine> --locked --group review python -B <engine>/tools/inspect-pages.py \
  <completed-attempt>
```

测试运行目录必须新建；执行器核对测试登记完整性并报告各套数量、SKIP、命令、输出和实现漂移。通用夹具不依赖 KB checkout、KB 的历史 Git 对象或已发布书籍。KB 的真实产品验收属于消费者集成测试，不搬进引擎单元测试。

语义阅读 corpus 由内容项目显式提供；没有适用 fixture 时为 `NOT_COVERED`，不是 PASS。全页自动渲染、代表页自查、用户接受和阅读器兼容性是不同证据。重新生成的正式身份 PDF 也不等于获准发布。

## 维护边界

后续通用实现只在本项目修改；KB 的旧引擎作为冻结历史入口保留，不维持两套活动实现。消费者通过修改 pin 升级，并重新执行适用的产品验收。历史 profile、PDF、release/tag 和接受记录不随引擎升级回写。

当前工程版本 `0.1.0` 只表示独立化工具版本，不改变 Visual Profile v1.0，也不升级任何手册的内容或出版版本。首次审核记录见 [qualification](reviews/standalone/README.md)。
