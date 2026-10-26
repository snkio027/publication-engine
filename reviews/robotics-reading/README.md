# 机器人手册阅读版构建记录

2026-10-26 构建，2026-10-27 整理交付。本批为用户提供的机器人手册生成可阅读 PDF，不执行 GitHub Release，不把建议学习基线升级为内容验收或硬件验证。

## 来源与产品身份

| 对象 | 固定身份 |
| --- | --- |
| 内容仓库 | `snkio027/knowledge-base` |
| 内容提交 | `2b90ad93f29800f08d1bc8f6b9083c8904dae7da` |
| 源路径 | `robotics/robotics-learning-handbook-v1.0.md` |
| 源字节 | 64,208；SHA-256 `bb7e3b010fce93a9eb338271264467bc177c70a21cdeb3bb0123d9e5d781663b` |
| 源身份 | `robotics-learning-handbook / 1.0.0 / proposed-learning-baseline` |
| 产品 | `knowledge-base / 1.2.0`，`robotics-handbook` profile |
| 引擎实现 pin | `f809e51d15dc7b5937aac02aee4dcbba31f40098`，本批不变 |
| 产品清单 SHA-256 | `d79aacc4da99194c0e59a1926376181e5062662f0a22a23b218f2636886345d6` |
| 产品输入集合 SHA-256 | `a4919186cff4c1a9e5c81e8290d462522f54ac1dfbcd764d17bc15e114c291e3` |
| PDF | `Robotics-Learning-Handbook-v1.0.0-reading.pdf`，28 页，872,798 字节 |
| PDF SHA-256 | `af995ba9a2ab09e4c8e126c20458cf1222bde4e6486793f07b826b371628e876` |
| 准备标识 | `1b6ab947594afef39c802515dd8bf14d7be07b6cd0cfca732105a7f54b225967` |
| 成功 attempt | `1f21117508454571a3ebf9ddab8dedad` |
| 执行身份 | `8c220484533b9352fe4897cf3f05350e3d65ba2b6b2e4babe18df0e5b82d3f0b` |
| 冻结候选 | `8e149eedd3995083794dfa3198770fe8444572da37052c129635755e4210b8d7` |

产品由当前交付提交绑定；构建发生在该提交之前，输入字节由上述摘要绑定，不宣称执行时 Git HEAD 已经包含新增文件。产品增加五份机器人配置及一个新版本 corpus，合计 40 份输入。原 34 份输入、六个历史 profile、共享 engine/latex/tools 和环境锁逐字节保持不变。

## 转换与分页

23 个编号主题、R0—R7 阶段、30 项参考资料和四个 fenced block 全部保留。adapter 只提取读者身份、绑定源 HTML 锚点与字面块身份；没有修正文、代码、实验结论或资料核验日期。封面、控制页、页脚和 PDF metadata 保留 PREVIEW、学习阅读版、未完成实机验证的边界。

第一份 28 页机器成功预览在视觉检查中发现 S14 标题与说明跨页。仅在新 profile 的 theme 中增加 S01—S30 稳定目标的 keep-with-next；两次试排产生 29 页且末页仅余一条资料。最终将参考条目的段间距设为 4 pt、预留 2.4 个基线行，恢复为 28 页。正文的字体、字号、版心及共享视觉实现没有改变。四次 attempt 均为机器 `PREVIEW_READY`，前面三份没有被当作最终视觉合格载荷；只冻结最终字节。

## 实际验证

| 类别 | 本次结果 | 证据边界 |
| --- | --- | --- |
| 机器人定向回归 | 9 项 PASS | 固定源身份、54 个目标、代码/关系保真、状态提升/未知 HTML/代码修改/错位锚点反例，以及参考目标集合 |
| 配置回归 | 13 项 PASS | 产品漂移、输入/输出边界与配置不覆盖；不是所有通用引擎回归重跑 |
| 当前源适配检查 | 59 项 PASS | 七个 profile 的源转换；不是七份 PDF 重新构建 |
| 真实构建与全页渲染 | 28/28 页 | 本机 LuaLaTeX + Poppler |
| PDF 内容检查 | 95 个源标题区域、491 个有序单元、10 处 inline literal、130 条表格行关系 | 自动提取与源关系比对；不是技术正确性证明 |
| 导航补检 | 54 个显式源目标、88 处源内部引用与 88 个正文点击区域一致；30 个外部 URL 有点击区域 | 排除目录页计数；没有联网重验 URL |
| 参考条目 | 30 条标题与说明位于同页 | PDF 目标及文本核对，补充视觉审阅 |
| 阅读 corpus | 9 类 fixture，STRUCTURAL_PASS，无结构问题 | 不等于独立视觉接受 |
| 视觉自查 | 全页 contact sheet；1、2、3、4、10、13、21、23、24、25、27、28 页详细查看 | 未发现裁切、重叠、缺字或断裂参考条目；不是跨阅读器兼容认证 |

最终 PNG 的第 1、3、10、13、21、25 页与已详细查看的前一试排对应页字节相同；最终控制页、参考页及 contact sheet 另外查看。九类 fixture 涵盖目录、正文入口、编码器公式、PI 骨架、采购核查、安全、目录树、实验模板和参考资料。

本地环境：macOS 27.0.1 arm64，uv 0.13.5 / CPython 3.14.8，pypdf 6.10.0，Pandoc 3.12.1，LuaHBTeX 1.24.0 / TeX Live 2026，Poppler 26.05.0。环境 doctor 观察到 Seatbelt 写入拒绝；完整运行身份见候选及知识库随件证据。

[tests.json](tests.json)记录定向及配置回归的命令和输出；[adapter-check.json](adapter-check.json)保留源适配结果；[navigation-check.json](navigation-check.json)记录 PDF 目标/点击区域；[verify-pdf.py](verify-pdf.py)是本次只读审计辅助脚本，不是新的构建入口。[protection.json](protection.json)记录 517 份历史 PDF、design/dist 与四个未跟踪 Zig 文件共 523 个文件的摘要核对，以及原产品输入保护。

## 复核命令

以下命令在引擎根目录运行；`$workspace` 必须是新建或空的受支持工作区，`$content` 指向知识库。输出路径和构建 ID 以实际返回为准。

```sh
uv run --locked --offline --group review python -B products/knowledge-base/configure.py \
  --content "$content" --workspace "$workspace"
uv run --locked --offline --group review python -B engine/pub.py \
  --project "$workspace/project.json" preview --profile robotics-handbook
uv run --locked --offline --group review python -B tools/reading-review.py "$attempt" \
  --corpus products/knowledge-base/publication/tools/reading-corpus-v1.2.json
uv run --locked --offline --group review python -B tools/inspect-pages.py "$attempt"
uv run --locked --offline --group review python -B reviews/robotics-reading/verify-pdf.py "$attempt"
uv run --locked --offline --group review python -B engine/pub.py \
  --project "$workspace/project.json" candidate --profile robotics-handbook \
  --from-preview "preview/$build_id/$attempt_id"
```

实际工作区是本 checkout 忽略目录 `tmp/robotics-v1-reading-20261026/`。候选冻结复制已经检查的字节，没有再次编译。交付 PDF 与精选证据保存到知识库的 `robotics/publication/v1.0.0-reading/`；它不是 GitHub Release 或历史已发布手册的替换。

## 未执行与限制

没有重新核验硬件参数、动态外链、算法正确性或实机安全；没有运行手册中的实验。未做 Preview/Chromium/Acrobat 的交互 smoke、PDF/UA 认证或跨平台可复现性测试。旧三项整书 qualification 和通用 84 项回归本批未重跑；历史证据没有改写。正文原始身份及未验证边界保持不变，正式 `publish` 仍关闭。
