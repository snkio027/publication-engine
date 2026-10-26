# Repository boundaries

本合同是当前职责与接口的单一维护入口：**两个仓库、三个逻辑职责、一个执行工作区**。仅支持可信本机 macOS + uv；不授权正式发布，也不改变 Visual Profile v1.0。

## 1. 谁决定什么

| 对象 | 权威与维护位置 | 边界 |
| --- | --- | --- |
| 正文、术语、源锚点、文章结构、学习路线、编辑规范 | knowledge-base | 内容正确性由内容流程决定 |
| 示例、实验、练习、Gate、内容验证脚本 | knowledge-base | 内容仓库可以有可执行代码；不是 PDF 引擎 |
| 内容接受、已发布书籍、授权、tag、下载回执 | knowledge-base / GitHub Releases | 保留书籍发布事实和不可变资产 |
| 书籍选源/revision、合订顺序、视图、书名/版本 | products/knowledge-base | `views[].documents` 是产品编排单一来源 |
| KB 实验/反例/Gate 约定识别、adapter、产品模板/主题、阅读 corpus | products/knowledge-base | 转换已声明语义，不改技术结论或代码 |
| 通用快照、保真、排版、导航、隔离、终态、候选 | engine / latex / tools | 通过显式配置加载产品，不内置书籍章节 |
| macOS/uv 环境、通用合成回归 | publication-engine | 不依赖真实 KB checkout 或旧构建 |
| project.json、预览、渲染、候选、执行日志 | 专用工作区 | 本机实例与运行状态，不是内容源或发布批准 |
| 复盘、原始设计研究、历史脚本/证据 | knowledge-base/publication | 知识或历史档案，不是活动运行入口 |

内容声明危险例身份，产品识别它，共享组件负责在分页后保留它。排版暴露内容错误时，必须通过知识库内容修订形成新源版本；禁止 adapter 暗改正文。源文章的章节结构不等于产品合订章序。

## 2. 输入与写入合同

依赖方向为：内容只读 → 产品显式配置 → 引擎 → 工作区 → 人工审核/授权 → 书籍发布记录。`channel=PUBLICATION` 只表示呈现身份，不表示获得授权或已经发布。

消费者提供 `project.json`；KB 配置器由当前 `product.json` 生成它，写在工作区。绝对路径或 descriptor-relative roots 表示本机位置，不构成可复用产品定义。

所有受支持出版写入口共用 `engine/boundaries.py`：

- 输出不得等于内容根、产品根、活动实现输入，也不得位于其内部或成为其祖先。
- 活动实现包括 `engine/`、`latex/`、`tools/` 和 Python 环境锁；不得以仓库根或其祖先为输出。
- 拒绝隐藏管理目录与任一已有 symlink 路径组件。已有目录不因叫 build/dist 就可接管；准备根必须为空或有正确标记。
- `publication-engine/tmp/` 可以容纳工作区。“外部”是相对受保护输入，不要求位于引擎 checkout 外。工作区应被 Git 忽略，避免运行改变所记录的 Git 上下文。
- 配置、直接 descriptor 的 preview/candidate、产品 check/qualify/历史比较、阅读检查和 contact sheets 均执行该边界；检查结果文件排他创建。
- 派生工具只能给位于其已绑定 output root 的完整已提交预览增加文件。旧尝试可以只读比较，不能因复制到新目录而升级成新协议尝试。

这不是对任意 Python、恶意 adapter、同账号并发目录替换或系统管理员的防御。source-only loader、Git filter 拒绝、Seatbelt worker 和终态提交约束继续成立。测试执行器只操作合成临时输入，测试报告不是正式出版入口。

## 3. 身份不能互相替代

| 身份 | 记录与含义 |
| --- | --- |
| 内容 revision | profile 中的完整 Git commit 或 WORKTREE；内容 SHA 单独绑定 |
| 产品交付 commit | 获取产品工具及审核记录的仓库提交；不是引擎实现 pin |
| 产品 ID / version / subdirectory | 当前 `product.json` 的显式身份，与产品输入集合摘要共同使用 |
| 产品输入 | 当前清单列出的 profile/adapter/template/theme/依赖/corpus 字节；每次准备重新核对 |
| 引擎 pin | 清单选定的完整提交；只核对 engine/latex/tools 与三份 Python 环境文件 |
| 迁移事实 | `migration.json` 固定原迁入来源 `a022de3…`，不再参与日常运行配置 |
| Visual Profile | v1.0，不能由实现提交变化自动升级 |
| 出版版本、候选、release | 读者身份、被检查字节、已授权分发事实，三者分别记录 |

描述文件保存产品版本、清单摘要、完整产品输入集合摘要和引擎 pin；准备快照另保存选定输入及原始清单。修改清单或产品字节后，旧 descriptor 拒绝继续，需重新配置。profile 目录出现清单未声明的额外输入也拒绝。未选择 profile 的文件不进入排版，但其锁定身份仍按整包核对。

产品配置器和验收脚本由产品交付 Git commit 绑定，不属于排版输入清单；它们不是随清单摘要一起获得安全认证。通用 schema v1 消费者可不提供 product 字段，此时明确记为 `UNVERSIONED_CONSUMER_INPUTS`；KB 受支持入口必须使用版本化产品。仓库 URL 是声明，实际字节和 Git 对象是本地验证，不声称远端签名认证。

## 4. 验证与证据

| 活动 | 命令/范围 | 不能推出 |
| --- | --- | --- |
| 内容实验 | knowledge-base 的内容验证脚本 | PDF 已验收 |
| 通用回归 | tests/run.py；独立合成仓库 | KB 整本书已验收 |
| 当前适配检查 | 产品 check.py；当前锁与显式内容根 | PDF/C++ 技术验证 |
| 当前产品验收 | 产品 qualify.py；当前清单声明的 trial | 人工阅读、阅读器兼容或发布 |
| 历史比较 | check_navigation.py + 显式 baseline JSON | 旧本机尝试必定可用、视觉批准 |
| 人工接受 | 指定制品摘要与页面/阅读范围 | 新字节、其他平台自动接受 |
| 正式分发 | 单独批准的书籍发布流程 | 任意后续重建可覆盖资产 |

`qualify.py` 默认不读取知识库 `publication/reviews/runtime-evidence` 或忽略的旧 build。只需要两个 checkout（内容仓库必须具有所选历史 revision）、锁定运行环境与本机 PDF 工具。历史比较明确接受 profile → 绝对 attempt 路径 + artifact manifest SHA-256；缺失或变化即失败，不自动寻找替代基线。

`PREPARED`、`PREVIEW_READY`、`CURRENT_PRODUCT_CHECKED`、`CANDIDATE_PREPARED_FOR_REVIEW` 分别是机器状态。`STRUCTURAL_PASS` 不等于视觉接受；`NOT_COVERED` 不能算 PASS。失败/取消不改已有成功记录。当前 CLI 启用 doctor、preview、candidate，publish 关闭。书籍正式发布、授权与回执仍归知识库。

## 5. 明确保留的限制

- 通用 `blocks.lua` 仍识别 `Final Gate` / “参考”标题。未来应由产品显式标注、通用 filter 消费；本批不改既有版式。
- FM 阅读 corpus 目前 0 个适用 fixture，保持 `NOT_COVERED`。全页渲染和定向人工页检不能冒充完整语义 fixture 覆盖。
- 输入可追溯不等于跨机器字节可复现；TeX/字体运行依赖是观察结果，不是完整 hermetic closure。
- 历史引擎仅在知识库精确 Git 提交中保留；没有第二套当前兼容执行入口。历史证据不追写为当前测试。
