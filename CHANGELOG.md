# CHANGELOG

## [Unreleased] — M2 HTML ↔ PPTX 同源（main，未发版）

### 同源
- 新增 `scripts/lib_solver.py`（与 lib_solver.js 逐值对齐同一 golden，120 例），`render_from_model.py` 渲染前同样拆页，HTML 与 PPTX 页序一致。
- 浏览器运行时 `assets/pptx-export.js` 删除整套 OOXML 几何引擎（与服务端不一致、仅用于预览），只保留 schema 校验、内联求解器（`__TOPPPT_SOLVER__` 注入）与 `pagePlan()`；每份 HTML 约减 90KB。
- 预览模态改为按 pagePlan 克隆真实 HTML 版块作缩略图，标注页型与续页；修复缩略图网格行被压扁。
- `cross_verify.py` 改为默认运行的同源核对：页数 = 求解页计划、PPTX/HTML 标题顺序、图表数据与标签、溢出；当即发现 business-blue 引用页顺序漂移并修正。

### 原生图表
- 甘特 / 进度 / 漏斗 / 对比条改为 PPTX 原生可编辑条形图（隐藏基底、剩余轨道、对称占位技巧），删除 shapeGantt / shapeFunnel / shapeVsbar 形状绘制；新增 `tests/charts/native-rows.model.json` 探针（CI 断言 ≥4 个 chart part）。

### 清理
- 删除 `scripts/gen_channel_a.js`、`dist/regression-a`、`validate_pptx --allow-shape-charts`、sync_runtime 中针对旧几何的检查与误报；文档同步改写（pptx-export.md 等）；feedback 门禁改为断言浏览器端不再含几何引擎。

## [Unreleased] — M1 布局求解器（main，未发版）

### 求解器与容量
- 新增 `scripts/lib_solver.js`（纯函数、零依赖、确定性）：`rows()` 行/卡/泳道高度分配（紧张时压缩、富余时拉伸到上限并整组居中）、`fitUp()` 稀疏时字号向上求解、`capacity()` 按页型 × 模式估算承载比、`splitModel()` 超载拆续页（标题加「（续）」，结论只在首页、来源只在末页）、`grid12()`。
- 新增 `scripts/solve_model.js`：报告各页容量比，`--write` / `--out=` 写回拆页后的模型，HTML 与 PPTX 同源消费。
- `build_pptx.js` 读模型后先做容量求解：`--strict` 下超载直接失败（退出码 4）并提示先跑 solve_model；非 strict 自动拆页并告警。

### 版式（PPTX）
- 泳道 / 金字塔 / 矩阵改由求解器分配高度，不再「挤在顶部、下半页空白」。
- 双栏 / 三栏稀疏内容自动切换为「段落卡片网格」（MD3 tonal 卡撑满版心）。
- 玫瑰图、关系网络在宽版心下采用「主图 + 排序面板」组合（右侧按数值排序的条目 + 比例条，全部取自数据）。
- 环形图按版心求解圆心与半径（上限 2.1in），无要点时图例改为图例卡。
- 瀑布图：末项等于前项之和时识别为合计柱；去掉在 LibreOffice/WPS 下错位的累计折线叠加，改为标准瀑布 + 数值标签。
- 箱线图：箱体按组距放宽，数值标签移到箱体右侧，消除与箱线叠印。
- 双区组合页：右区只给 points 时按要点渲染（此前默认画出空柱图）；图表下沿收在注释带之上。
- 信息图内联数据表超过承载（>5 行）自动转入演讲者备注，不再压进结论条。

### 门禁与测试
- 视觉填充门禁对四份示例（演示 / 研究 / 架构 / 产品展示）全部转为硬门禁；架构样张冒烟转为硬门禁。
- 新增 `tests/solver/test_solver.js` + 金样 `golden.json`：10 页型族 × 3 模式 × 4 档共 120 例，断言确定性与拆页不变量；CI 增加「同模型两次构建幻灯片 XML 逐字节一致」检查。
- `regression.py` 全链路回归恢复全绿（修复 showcase 大纲 9 条未双栏、对比页被误要求图标、split 探针越界）。

## M0 止血（PR #6，已合并，未发版）

### 质量门禁
- 新增 `scripts/check_visual_fill.py`：PPTX → LibreOffice → PNG，在正文区按 24×12 栅格检查有墨占比（VISUAL_FILL）、最大连续空白（VISUAL_EMPTY_BLOCK）、墨水重心（VISUAL_OFF_CENTER）。business-blue 黄金样张为硬门禁（M1 起四份示例全部硬门禁）。CI 与 Release 安装 libreoffice-impress、poppler-utils、fonts-noto-cjk。
- `audit_docs.py` 新增 ⑧ 禁止词：「甲板」、结论条「So what」标签、`.sowhat--labeled`、旧品牌名。

### 引擎（PPTX B 通道）
- 单系列柱 / 条 / 线 / 面积图统一主色（不再按数据点轮换彩虹色），加浅色数值网格线。
- points + metrics：指标改为右侧纵向 MD3 tonal 卡片，要点按高度均分并加细分隔线。
- kpi：hero 落在等高 tonal 卡片内垂直居中，支撑指标按高度均分。
- quote：去掉装饰大引号；新增 `metrics`（2–4 个证据数字）证据卡片行（A 通道与 render_from_model 同步）；schema 增 `quote.metrics`。
- steps / cards：单行卡片随版心拉伸，留白不再集中在下半页。
- 2-col-feature 特性栏去掉左侧竖条，改 tonal 底。
- 图标：运行时不再隐式调用 sharp，直接用包内 `assets/icons/*.png`（降为 256px）；`--strict` 下图标缺失直接失败（exit 3）。
- CLI：缺 `--model` 直接报错退出（`--demo` 显式调试）；支持 `--out=`。

### 样式与文档
- engine.css 去掉 `.col--feature` / `.arch__lname` / `.flagbar` 的左侧装饰竖条；research 示例的 so-what 本地覆盖同步去竖条；删除 `.sowhat--labeled`。
- references 删除「So what」标签示例与标签变体说明；金句页规范改为「金句 + 署名 + 证据」。
- 旧品牌名统一为 topmind-presentation（代码、模板、示例、文档）。
- README 中英两版只保留一张主题总览图；主题总览图重拍（去旧名）并做 256 色量化。
- business-blue 示例：金句页补证据数字；空的「配图占位」页换成推进路线（timeline）页。

### 包
- npm 包排除 showcase 示例；主题总览图与图标瘦身：4.9 MB → 2.7 MB（压缩后）。

## [0.2.7] - 2026-10-11

> 0.2.6 → **0.2.7**（patch）。

### 优化

- 产品 Showcase 按当前包名重写：`assets/examples/2026-09-26-topmind-tms-skills-showcase.*` 换为 `2026-10-11-topmind-presentation-showcase.*`，安装与分发页写 `@topmindspace/topmind-presentation` 的四种装法，版本图表改用 CHANGELOG 记录的 npm 包体积数据；`docs/showcase.html` 同步，去掉历史样张声明。
- `docs/showcase/topmind-showcase/`、`assets/showcase/`、`docs/site-assets/` 下的 Showcase 截图按新版重拍。
- `scripts/capture_showcase_pages.js` 适配独立仓库目录（仓库根即技能根），支持 `PW_CHANNEL=chrome` 使用本机 Chrome、`ONLY=<prefix>` 只重拍指定样张，并等待图表动效结束后再截图。
- README 目录结构说明与实际的 `docs/` 内容对齐；移除未被引用的行业调研过程文档（`docs/industry-pptx-research.md`）。
- 技能本体（`SKILL.md` 正文与 references）不变。

## [0.2.6] - 2026-10-10

> 0.2.5 → **0.2.6**（patch）。

### 优化

- 调研文档 `docs/industry-pptx-research.md` 改为中性的研究方法说明，示例与参考资料为通用内容。
- README 中英文的外链与 canonical 指向正确的站点路径。
- `scripts/ci_privacy_scan.py` 增加自定义盘符路径检查项，扫描覆盖面更完整。
- GitHub Actions 改用 Node 24 运行时的版本：`actions/checkout` v4 → v7、`actions/setup-node` v4 → v7、`actions/setup-python` v5 → v7、`softprops/action-gh-release` v2 → v3；CI 与 Release 的 `node-version` 20 → 24。
- `runs-on` 由 `ubuntu-latest` 固定为 `ubuntu-24.04`：GitHub 在 2026-10-19 至 11-19 期间把 `ubuntu-latest` 逐步切到 Ubuntu 26.04，先停在当前已验证的镜像，切 26.04 另行验证后再改。
- `.gitignore` 补充 Release 附件、npm pack 输出等再生成产物。
- 技能本体（`SKILL.md` 正文与 references）不变。

## [0.2.5] - 2026-10-08

> 0.2.4 → **0.2.5**（patch）。

### 优化

**规范与触发**

- `SKILL.md` frontmatter 对齐 Agent Skills 规范：顶层只留 `name / description / license / compatibility`，`version / author / updated / action_category / triggers` 移入 `metadata`（字符串值），`agentskills validate` 通过
- 触发词收窄：去掉 `报告`、`研究报告`、`白皮书`、`复盘`、`fast` 等泛词；description 改为「把已有材料做成正式商务演示与多页可视化报告」，架构图类限定为多页或要 PPTX 交付
- description 增加 Do NOT：找资料与核事实 → topmind-research，整理已存笔记与周复盘 → topmind-organize，工作区巡检与例行复盘 → topmind-loop，单张长图/信息图/榜单图 → topmind-poster，改写已有 PPT/Word → 官方 pptx/docx 技能
- `check_triggers.py` 只用 description 的正向部分计分，并增加兄弟技能分流检查：负例带分流线索时，Do NOT 里必须点名目标技能；触发评测补 N12–N17 六条负例（共 39 条）
- 标题改为 `topmind-presentation · 商务演示与可视化报告`，与技能名一致；增加「分工」说明（材料来自 topmind-research 时沿用其数字与来源）

**npm 与安装**

- `package.json` 增加 `files` 白名单，只发运行所需文件：npm 包从 266 个文件、解包 16.9 MB 降到 197 个文件、约 7.3 MB（压缩包 13.3 MB → 4.6 MB），`docs/`、`assets/showcase/`、`evals/` 不再进包
- README（中英）安装说明与发布流程一致：Release zip、git clone、`npx skills add`、npm 安装后用 `npx skills experimental_sync` 或手动复制进技能目录；删去与自动发 npm 矛盾的「不要 npm install」说法
- Release zip 补进 `assets/icons/`（48 个图标与 `index.json`），之前 zip 安装时图标库缺失
- `package-lock.json` 根版本与 `package.json` 对齐

**引用与 CI**

- `references/modes.md`、`design-system.md`、`tech-design.md`、`icons.md` 与 `scripts/build_examples.py` 里指向 `../docs/archive/` 的引用（文件在 topmind-writing-skills 仓库）改为固定提交 `9a37952` 的 GitHub 链接，标明仅维护者备查
- 新增 `scripts/check_repo.py`：版本六处一致、`SKILL.md` 与 references 不引用技能目录外的路径、npm 包内容符合白名单且不超过 10 MB；接入 `ci_skill_gates.sh`
- CI 与 Release 安装 `skills-ref`，门禁里跑 `agentskills validate`
- `SKILL.md`「版本口径」一节并入 `references/tech-design.md` 已有说明，入口文件保持在 13 KB 预算内

## [0.2.4] - 2026-10-01

> 0.2.3 → **0.2.4**（patch）。cover 按新版 cover 技能重生成（dark-saas 风格：深空黑 + 毛玻璃卡片 + 发光节点）。

## [0.2.3] - 2026-10-01

> 0.2.2 → **0.2.3**（patch）。README/落地页换上按 cover 技能配方新生成的白色清新 banner 封面（5:2）。

> 0.2.1 → **0.2.2**（patch）。独立建仓首个发布版。

- 本技能原为 `topmind-writing-skills`（原 `tms-skills`）monorepo 中的 `top-ppt-html`，
  现独立为 `topmind-presentation` 仓库并改名 **`topmind-presentation`**。
- 仓库即技能：技能文件（SKILL.md / assets / references / scripts / evals / agents）
  移到仓库根目录；docs 下落地页 / showcase / 风格画廊 / 行业研究一并迁移。
- 基础设施：根 `package.json`（`@topmindspace/topmind-presentation`，去 `private`）、
  CI（含 `--with-pptx` 门禁）/ Release workflow（tag v* → GitHub Release + npm）、
  `docs/PUBLISHING.md`、隐私扫描。
- 无引用 banner 图已删除；showcase.html 加历史样张声明。

## 0.2.1（monorepo 时代，见原仓库 CHANGELOG）
