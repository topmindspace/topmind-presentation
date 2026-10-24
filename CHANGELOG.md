# CHANGELOG

## [0.2.12] - 2026-10-23

### Header 风格下拉遮挡与交互态
- 顶栏风格下拉不再被裁切：`.bar__in` 由 `overflow:hidden` 改为 `visible`（品牌与导航文字省略仍由 `.brand` / `.nav` 各自裁切）；`.toolsbar` / `.seld` 保证弹出层可溢出；下拉列表可容纳 12 套风格。
- Header 全部图标按钮补齐 `:hover` / `:focus-visible` / `:active`，风格按钮打开态高亮；导航链接补 `:focus-visible`。
- 风格菜单：`aria-expanded` / `aria-haspopup`、方向键与 Home/End、Esc 关闭并回焦；标签文案按 `STYLES.length` 同步，避免示例残留「9 套」。
- 单源：`engine.css` + `ui.js` → `sync_runtime` 注入三模板与示例内联副本。

### 质量
- `ci_skill_gates.sh --with-pptx` 全绿；五套示例保真位置 p90 ≤ 0.109（研究模式 0.093）。

## [0.2.11] - 2026-10-17

### docs/ 清理：落地页只在站点
- 删除仓库内的旧落地页与截图：`docs/index.html`、`docs/showcase.html`、`docs/style-gallery.html`、`docs/assets/`、`docs/site-assets/`。本仓库没有 GitHub Pages，这些文件没有被任何脚本、测试、CI 或发布流程使用。`docs/` 只留 `PUBLISHING.md` 与 `MIGRATION-0.2.8.md`。
- 落地页与演示统一指向 https://topmindspace.github.io/presentation/ （源码在 topmindspace.github.io 仓库）；风格总览仍是包内的 `assets/style-gallery.html`。两份 README 的入口与目录说明、`MIGRATION-0.2.8.md` 的对照表已同步。
- `scripts/capture_theme_overview.js` 新增 `--out=<目录>`，可把主题总览截图直接写进站点仓库；`PUBLISHING.md` 新增「落地页（站点）」一节，写明站点截图的刷新步骤与站点规则。
- `check_repo.py` 新规则：`docs/` 只允许 `PUBLISHING.md` 与 `MIGRATION-*.md`；README 中英文与 `docs/*.md` 里的相对链接必须指向存在的文件。

### 版式与门禁
- HTML 章节号与 PPTX 同比例：`clamp(72px,10vw,144px)`（PPTX 96pt ÷ 13.33in 页宽 ≈ 10%），研究模式按 80pt 用 8.3vw，之前 HTML 约大 40%。
- HTML 章节页标题栏加宽（号码列 `minmax(160px,24%)`，`pageTypes.chapter.numW` 3.6 → 2.9），长标题不再被挤成三行。
- PPTX 多图表综合页（侧图 / 迷你图 / 通栏）补上主图图注，与 HTML 一致；已有 `exhibitNo` 时不重复。
- `audit_skill.py` 重复片段检查改为逐字滑窗、按文件分别取窗口，跨文件边界不再误报，重复也不再只报一次。
- README 的「美化前后对比」链接指回站点 `#beautify` 锚点。

## [0.2.10] - 2026-10-17

### M13 多图表综合页、简单页、美化复杂稿与高密度示例
- 新页型（HTML 与 PPTX 同构，版式库 48 → 51）：
  - `dashboard` 仪表盘：2–4 张图 + 关键数字条 + 解读行。同单位、同图型的图共用坐标上限，系列名一致时只画一个共用图例，图注按叙事顺序编号 ①②③④。超过 2 字的单位（如「亿人次」「元/km」）挪进图注，数据标签只留数字。
  - `magazine` 杂志版：大图 + 观点句 + ≤2 个大数字 + ≤3 条带图标的要点。
  - `focus` 简单页：一个数字 / 一句观点 / 一段话 / 一个图标 / 一张图，共 12 种变体（left / center / split）。
- 图表与图标：新增象形图 `pictogram`（`charts-extended.md` §83，双端同几何），共 37 种图表；HTML 华夫图改成真点阵；自研图标扩到 72 个（256px 单色 PNG），支持线性 / 填充两种 `iconStyle`。
- 标题防孤字：双端都按标点和词边界平衡断行，数字和单位不拆开（新门禁 `TITLE_ORPHAN`）。HTML 标题、简单页观点句与段落改用 `text-wrap:balance` + `keep-all`。
- 新门禁：`CROWD_GAP`（拥挤）、`FOCUS_SPARSE`、`ICON_OVERUSE`、`ICON_STYLE_MIXED`。简单页不参与视觉填充检查，留白是它的本意。
- 美化已有 PPT（复杂稿）：
  - 一页 2 张图 → 双图对照（`compose:"nokm"`，不派生原稿没有的数字）；3–4 张图 → 仪表盘；表 + 图 → 半表半图；长句清单 → 要点列。
  - `agenda:false` 时两端都不补目录。
  - 保留原稿页序时，节奏和相邻同型图只记 INFO，相邻同一版式仍然硬拦。
  - 原图按 contain 放进浅色底卡。
  - 新增 `tests/beautify/samples/complex-ops.pptx`，站点和 showcase 新增美化前后对比。
- PPTX 优化：
  - 仪表盘 / 复合版式中的多系列图表被当成空图跳过。
  - 单系列折线（≤8 点）补数值标签；堆叠柱的段内标签居中，用反白字。
  - 环形图在单位不是 % 时显示「1 种」，改为百分比。
  - 横条图类目过密时被隔行省略，现在缩小字号后全部显示。
  - 热力图图例压住关键数字条；列表圆点比首行文字偏低；杂志版大数字（如「≤ 2 小时」）折行，现在同一组数字统一缩小字号；双图对照页的长单位标签互相挤压。
- 示例与站点：
  - 新增 22 页高密度大型示例「城市公交电动化复盘」（deep-teal：仪表盘 ×2、堆叠成本、半表半图、象形图、热力图、达成、矩阵、杂志版、简单页）。
  - showcase 用真实的能力盘点仪表盘（51 版式 / 37 图表 / 72 图标）替换了虚构的环形图页，并新增「美化」简单页。
  - 风格画廊缩略图去掉小眉标；站点新增「美化前后」和「高密度与简单页」两组截图；主题总览和全部站点截图重新生成。
- 第三次全新主题试跑：县域冷链物流 · 演示模式 · coral-launch，16 页，收进 `tests/trial/lengchain.model.json` 并接入 CI。
- 清理：
  - 版式数、图表数、风格数在文档和注释里统一为 51 / 37 / 12。
  - 象形图原来的 §71 与信息图 §71 重号，改为 §83 并登记到 `section-file-map.json`。
  - 删除不再引用的两张 showcase 截图。

## [0.2.9] - 2026-10-17

### M12 行距、页面减法与复杂信息图
- 正文行距：普通文本框的段落与列表默认 1.5 倍，高度不够时降到 1.3 倍，不再更低。HTML（`--lh-text` / `.lh-tight`）与 PPTX（精确磅值）同源于 `containers.lineSpacing`，求解器容量估算同步折算；新增 `LINE_SPACING_TIGHT`（validate_pptx）与「正文行距」检查（validate_report）。
- 页面做减法：默认去掉页头眉标和页脚小字，只留一个 9pt 浅色页码；省下的高度交给求解器排正文。新增模型开关 `showEyebrow`、`showFootnotes`、`pageNumber`；美化路线默认全显示。隐藏的页脚小字写进演讲者备注，带 `[n]` 引用的来源行与 Exhibit 来源行照常显示。保真门禁、往返核对、美化核对与像素 / 版式基线同步更新。
- PPTX 时间线：2–5 个阶段时改为阶段卡 + 轴线，与 HTML 一致；章节扉页结论两端都显示；研究模式保真位置 p90 从 0.118 降到约 0.10，留出余量。
- 版式：要点 + 指标页改为左列表右指标卡；短段落双栏改为卡片网格；金句页居中且避免单字换行；showcase 两处触到字号下限的文案改写。
- 第二次全新主题试跑（社区养老服务站 · 演示模式，15 页，收进 `tests/trial/yanglao.model.json` 并接入 CI）。发现并优化：表格页的 `points` 两端都没渲染（现在表下一行解读卡，HTML 与 PPTX 同构）；金句页缺 `author` 时 PPTX 显示「—— undefined」；页型必填字段（`model-schema` 的 `pageTypes.required`）此前没有门禁，validate_report 新增「页型必填字段齐全」检查。
- 新增 `references/infographics-guide.md`（复杂信息图指南）：模型字段与示例、选型与组合规则、PPTX 原生图表与形状的边界。
- 文档、四个示例、试跑样例、主题总览、风格画廊、showcase 与 README 截图全部按新行为重新生成；新增 `tests/m12/test_m12.py` 并接入 CI。

## [0.2.8] - 2026-10-17

### M11 复审、安装命令与全新主题试跑
- 新增 `npx @topmindspace/topmind-presentation install [--to 目录] [--force] [--link]`（`scripts/lib_install.js`）：默认直接升级（旧版覆盖、不备份）；已装版本更新时拒绝降级，`--force` 才降；同名目录是之前装的同一技能时自动替换，无关同名目录需 `--force`；符号链接只删链接不删源；拒绝装进源目录。`tests/install/test_install.js` 14 项覆盖，接入 CI。规则借鉴 topmind-writing-skills，不依赖它。
- 全新主题端到端试跑（街角咖啡华东扩张评估 · 研究模式 · warm-sand，17 页：复合版式、折线、瀑布、矩阵、分层示意图、图文混排、对比、时间线），样例收进 `tests/trial/` 并接入 CI。试跑发现并优化：
  - `make_deck --out 目录`（空格写法）崩溃；仅 WARN 导致 strict 失败时不显示 WARN 行；PPTX 质检只显示错误码不显示说明。
  - 研究模式自动 Exhibit 编号与手写编号撞车；现在一个都没写才自动编号，HTML 与 PPTX 同规则（此前 PPTX 不自动编号）。
  - 复合版式的关键数字条 / 解读栏 / 解读带未计入「组合版式」承载件，复合页被当成单件页。
  - PPTX 左图右文页的纯字符串要点被按字符拆成「标题 / 正文」；PPTX 图片用了 pptxgenjs 的椭圆遮罩，照片四角被裁掉。
  - HTML 左图右文页的图注占了右栏，要点被挤到图下方；`--out` 到其他目录时相对路径图片破图（make_deck 现在一并复制）。
- 美化路由：渲染器在要点键后自加「。」，ink-academic 等风格下逐字核对 FAIL；美化模式不再新增任何标点，写稿模式在键已有收尾标点时也不再补。`tests/m11/test_m11.py` 覆盖 12 套风格美化核对。
- 新增 `references/extending.md`：写稿时可自由组合的字段、维护者加风格 / 版式 / 图表 / 字号角色 / 几何 / 阈值的扩展点，以及刻意不开放的部分；`style-pack.md` 补 `stylePptx` 必填项；SKILL.md 与生成食谱指向它，食谱推荐一条命令 `make_deck` 出稿。
- 文档：README 中英文补安装命令与三条规则、插图 / 美化 / 可扩展能力行、`build` 一条命令；版式数统一为 48；`docs/MIGRATION-1.0.md` 更名为 `docs/MIGRATION-0.2.8.md` 并补齐 M6–M11 变化；showcase 安装页改为安装命令与三条规则。

### M10 补齐 M9 未完项
- 研究模式复杂信息图图区：复合 band 页 PPTX 来源行贴在图下、解读带下移、结论条落到页底（底边让开页码），复合页正文起点与 Exhibit 行间距收紧，主图多出约 0.4in；HTML 端复合 band 页主图限高 44vh，整页收进一屏，研究模式版心 1240→1320px。研究示例位置偏移 p90 0.153→0.118，`check_fidelity.py` 删除研究模式放宽（`MODE_THRESH`），四模式统一 ≤0.12。
- 12 套风格 PPTX 气质：新增 `stylePptx`（标题字体 / 字重 / 标题线 / 卡片质感 / 表格质感 / 线宽）。衬线风格（mckinsey / warm-sand / ink-academic）西文 Georgia + 东亚 SimSun，按运行写入 latin / ea；HTML 衬线回退链统一为 Georgia → Noto Serif SC → Source Han Serif SC → Songti SC → STSong → SimSun → Noto Serif CJK SC。
- HTML 表格质感与 PPTX 同源：rule（apple-mono / mckinsey / sky-airy）、三线表（ink-academic）、斑马纹（warm-sand / deep-teal / graphite-dark / spectrum）。
- 暗色主题：12 套风格 HTML 与 PPTX 逐套审查，PPTX 暗色 token 正文 / 弱文字 / 强调色对 bg / surface / soft 对比度全部达标（正文 ≥4.5，强调 ≥3）。
- 瀑布图：PPTX 首柱与合计柱用实色、增量用品牌浅调、减量用 --neg 红，数值标签统一墨色，与 HTML 一致（此前增量实色、减量灰）。
- 矩阵图：HTML 补上 accent 格高亮（此前丢失）；PPTX 格子改 tonal 实底、无描边、文字居中，不再被卡片描边风格误套。
- 中英文间距：含中文的文字运行标注 `lang="zh-CN" altLang="en-US"`；源文本只有一个普通空格，LibreOffice 预览中更宽的间距来自其默认的中西文自动间距，DrawingML 无对应属性，PowerPoint 不会额外加宽。
- 新增 `tests/m10/test_m10.py`（风格全覆盖、衬线回退链、表格同源、统一阈值、矩阵高亮、zh-CN 标注），接入 CI。

### M9 全方位优化
- 新增 HTML ↔ PPTX 逐页保真门禁 `check_fidelity.py` + `fidelity_html.js`：按段落配对，量化字级层级（相对整稿中位比值）、颜色 ΔE、换行、位置、字体声明；改进提示用中文写成可执行的步骤；接入 CI（四份示例全部 PASS）。
- 两端对齐：封面 / 章节标题 / 指标大数 / 卡内大数 / 时间线阶段名改走新增角色字号（coverHero · chapterTitle · kpiHero · kpiCard · stepTitle）；眉题降一级；结论条改 tonal；表头改 tonal；Exhibit 行改「品牌色编号 + 墨色图题」；卡片网格行优先。
- PPTX 灰阶统一到品牌色系：热力图第 3 级、子弹图未达标条、树图、马赛克图、流带图（改用风格编码色板）、K 线阴线不再用灰。
- 复杂信息图：关系网络改「枢纽居中 + 椭圆环 + 胶囊节点」与 HTML 同算法；箱线图改横向；树图标签带占比；信息图标签字号上调。
- HTML：独立指标页改主视觉卡（不再顶部一条、下半页空）；收尾页改卡片；研究 / 架构模板的模式层改为 `html[data-mode]` 作用域，标题字号不再被风格层覆盖。
- 风格性格：PPTX 卡片圆角按风格 `styleIdentity.radius` 等比缩放（mckinsey 方正、apple-mono / sky-airy 圆润）。
- 一条命令流水线 `make_deck.py`（`npx topmind-presentation build`）：渲染 → HTML strict → 密度 → PPTX strict → PPTX 质检 →（可选）保真，失败只摘失败行并给「怎么修」。
- 复述检测改为双信号（数字可推导率 + 汉字二元组新信息率），连词伪解读不再放行；新增 16 条人工标注小样本评测（检出 8/8、误报 0/8，旧法 3/8）。示例中被新法识别的复述要点按已有事实改写。
- Agenda 条目下限与 schema 同源（≥3），去掉与 `agendaMin` 矛盾的写死 ≥4。
- SKILL.md 精简（流程改为「写 model → make_deck」），图片规则写入 illustration-layout.md。

### M8 遗留问题清理
- 解读要点：规则写明「原因 / 影响 / 下一步，不复述数字，只用已有事实」；新增 DENSITY_ECHO / DENSITY_NO_INSIGHT 复述提示；四份示例与 Q1 的复述要点按原有事实改写。
- 小图组最多 2 张（DENSITY_MINIS_MAX），HTML 与 PPTX 同步；PPTX 小图随之放大。
- showcase 风格页补解读带、改措辞。
- HTML 热力图按 4 级色阶着色并补色阶图例（两端标数值），与 PPTX 同口径。
- gallery-research 节奏检查通过，CI 节奏门禁覆盖版式库样例稿。
- PPTX 图标跟随风格主色（调色板 PNG 无依赖重着色）。
- 脚手架默认（含不加 --plan）只出空位骨架，示例正文改为显式 --demo。
- image-size 经 npm overrides 锁到 ^2.0.4（pptxgenjs 运行时不调用该包），npm audit 0。

### M7 信息密度治理
- 新增复合版式（chart-readout / chart-dual / chart-minis / chart-band），纳入版式库（48 种），HTML 与 PPTX 同步。
- 模型层：图表页支持 points / keyMetrics / chart2 / minis / compose；缺关键数字时由单序列数据自动派生，缺解读给出提示。
- 新增最低信息密度门禁 check_density.py（演示 / 研究 / 架构三档）及自测，接入 CI。
- 新增 references/density.md（分档、复合版式、插图与图标规则），清理过时的极简规则。
- 重做四份示例低密度页；streamgraph 撑满高度，环形图标签不再重复，热力图图例不再压住底栏。

### M6（未发版）
- HTML 封面改为整块主色色块（与 PPTX 一致）；暗色主题用主色与背景 30% 混合，避免刺眼；12 套风格亮/暗均已核对。
- 新渲染的 HTML 自动填充页眉、页脚、导航与 `<title>`，不再残留模板占位文字。
- `scaffold --plan` 标题初稿只输出标题与页型，正文位置统一为「【待填】」空位，不再含示例正文或编造数字（初稿 strict 校验会报 UNDERFILL，属预期）。
- 短内容卡片页、时间线页、步骤页按字数自动放大字号并铺满（HTML：`cards--roomy`、`tl--h` 横排卡片、`steps--roomy`；PPTX：放大字号、统一垂直居中、时间线整列色卡）。
- 优化：`band--top` / `band--fit` 等附加类名此前被写成无效属性，现并入 class。
 — M5 收尾（main，未发版）

### M4 遗留
- 美化路由：短清单与陈述卡字号向上求解（上限 22pt），陈述卡去掉装饰图标；有标题卡片、≤6 行短表、只有一句话的收尾卡片同步放大或贴合内容高度。
- 图片与其他内容同页时迁入「左要点 + 右图片」版式（等比缩放，不裁切）。
- 演讲者备注逐字写回新稿（封面、目录、各页、收尾），核对器新增备注检查。

### 五条路线
- 新增 `recipes/`：generate / fast / beautify / template / architecture，每份写明什么时候用、输入、保留什么、产出；SKILL.md 顶部加路线表（122 行）。
- 新增 `scripts/extract_template.py`：从参考 PPTX 读取主题色与字体，按色差给出最接近的 3 套内置风格。
- 新增 `scripts/render_pptx_png.py`：PPTX 逐页渲染成 PNG，供看图复核与像素回归共用。

### 工程
- `scripts/doctor.py` 自检（环境、关键文件、运行时戳、BOM、`--full` 实际渲染）；`scripts/cli.js` 提供 `npx topmind-presentation doctor|path`。
- `scripts/pixel_regression.py`：三份黄金样张 PPTX → 48×27 灰度缩略图对比基线（`tests/pixel/baselines/`），接入 CI；失败时上传对照图。
- `scripts/smoke_pack.sh`：npm pack → 临时目录安装 → `doctor --full`，并限制包体 ≤1.4 MB，接入 CI。
- npm 包 2.58 MB → 约 1.1 MB：图标 PNG 改为 160px 调色板图，包内示例只留 model.json，删掉两张按模式的总览图。
- release.yml 开启 `npm publish --provenance`（`id-token: write`），`publishConfig.provenance: true`。

### 文档与素材
- README 中英两版重写；只保留一张 12 套风格总览图（重新拍摄）。风格画廊文案改为 12 套，补齐三套新风格的中文名、描述与适用场景，单系列柱图改用单一强调色。
- 新增升级说明（现为 `docs/MIGRATION-0.2.8.md`）。
- 清理：`assets/showcase/`、`docs/showcase/`、`scripts/capture_showcase_pages.js`、两张按模式的总览图及其引用。

### 优化（整体复核中发现）
- HTML 大数指标页在模型没有要点时会补出「支撑。一句话。」占位；支撑指标在窄列里横排导致数字折行。改为不补字、支撑指标竖排、大数放进色调面板。
- 环图单位为 % 且合计 100 时中心显示「100%」、图例重复占比列（HTML 与 PPTX 两端）。

### M4 已有 PPT 美化

#### 美化路由（新）
- `scripts/beautify.py 原稿.pptx --out 新目录 [--style] [--theme] [--compare]`：解析 → 锁定原文 → 逐页诊断 → 映射版式库 → 重新排版，交付新的 HTML + PPTX + `verify.json` + `report.md` + 前后对照图；原稿只读，拒绝输出到原稿目录。
- `scripts/ingest_pptx.py`：读取标题、文本框（层级 / 字号 / 颜色）、表格、原生图表（类别 / 系列）、图片、备注；SmartArt / OLE / 媒体与未迁入的图片列入「不支持对象」，图片导出到 `media/`。
- 不改字契约：切分只允许原样（keep）、分隔符变分栏（sep）、手打序号改由版式绘制（ordinal）。核对器逐页查片段，PPTX 与 HTML 两端都查；数字逐个找回；图表数据与原生 chart XML 逐项一致；新页不得多出原稿没有的字。
- 模型新增 `contentLocked`、`agendaTitle`、`agendaEyebrow`、`closing.eyebrow`、`sourceSlide`、`chart.centerTotal`。锁定原文时：校验器不再要求标题写成主张句，低密度只作提示，陈述卡（无标题整句卡）字号向上求解。
- 渲染不再补字：去掉「要点一 / 要点二 / （第二组要点）」「（待填）」、环图「合计」、写死的「AGENDA / 报告大纲 / 下一步」。
- 测试：`tests/beautify/make_samples.py` 确定性生成三份朴素样例（课件 / 经营汇报 / 方案）；`tests/beautify/test_beautify.py` 断言三份差异 0、图表一致、原稿不变、未迁入对象入报告、三道 strict 校验通过，另有改字 / 改数两类负例，已接入 `ci_skill_gates.sh --with-pptx`。文档 `references/beautify.md`。

#### M3 遗留
- 风格偏好版式接入自动选版：新增 `scripts/lib_layout_pick.py`（风格偏好 + 节奏评分），美化路由与 `recommend_layout.py --style` 共用。
- 数值标签避让目标线：柱图 / 折线的数值标签与目标线相交时抬到线上方（`lib_chart_svg._avoid`）。
- `references/styles.md` 补 §12–14：学术墨蓝 / 活力珊瑚 / 晴空课件的亮暗色值、编码色板与 `engine.css` 覆盖块。
- `SKILL.md` 精简（13.2KB → 12.3KB），加美化路由一行。

#### 优化
- HTML 卡片栅格 `g-N--equal` 丢了列定义，等高卡片退化成单列；bento 卡片变体被同名的 4 列拼贴工具类覆盖，导致末行留洞。
- PPTX 分组柱（≤12 个点）补数值标签，避免值轴隐藏后读不出数；HTML 多系列柱改为分组柱（`grouped()`）。
- 无注释的图表页图形框下沿留 0.25in，不再贴进注释带；版式 golden 随之更新。

### M3 版式库 · 风格库 · 图表系统

#### 单源可再生（先修根因）
- `regression.py` 不再回写示例 model.json（抽取结果写 `dist/regression/`）；新增两道检查：「model.json ≡ HTML 内嵌模型」「示例可由 model.json 完整再生」（`render_from_model --body-only` 与 HTML 内容区逐字一致）。
- `render_from_model.py --inplace --model X.model.json`：参考资料、锚点、图标、Exhibit 编号、来源行全部从模型渲染，不再丢失；四份示例均由 model.json 完整再生。

#### 版式库（8 家族 44 版式）
- `layout-constants.json` → `layoutLibrary`：结构 / 观点 / 数据 / 框架 / 流程 / 媒体 / 卡片 / 表格 8 家族 44 版式，每个版式有匹配规则与视觉重量（强调 / 轻 / 中 / 密）。
- 节奏规则：同重量连续页上限、相邻不同版式、≥8 页至少 5 个家族、≥14 页建议章节扉页；反模式：单页图标 ≤6、系列色 ≤6、同形卡片 ≤8、引言须有佐证、禁用「So what」类标签。新增 `scripts/check_rhythm.py`，CI 对全部示例硬拦。
- 新页型 `chapter`（章节扉页）；新变体：表格 `highlight`（推荐列高亮）、对比 `problem-solution`（问题 → 方案箭头）、架构图 `aside`（横切护栏列）；bento 卡片末行自动补齐。
- 版式 golden：`tests/layouts/build_gallery.py` 从示例与合成样例生成每版式一页的画廊，`tests/layouts/test_layouts.py` 校验 44/44 覆盖 + PPTX 几何指纹。文档 `references/layout-library.md`。

#### 风格库（12 套）
- 默认风格更名「清新蓝白（默认）」；新增学术墨蓝 `ink-academic`、活力珊瑚 `coral-launch`、晴空课件 `sky-airy`，补齐亮暗 token、编码色板、语汇与审计。
- `styleGrammar`：每套风格绑定偏好家族 / 版式、密度档（airy / normal / dense，HTML `data-density` + 求解器承载系数）与图表皮肤（网格、圆角、标签策略）。

#### 图表
- 新增 `scripts/lib_chart_svg.py`：HTML 端数据驱动 SVG（核心 15 类 + 6 类信息图），标注层 `annotations`（目标线 / 高亮 / 旁注）与 `dataLabels`；配色规则统一（单系列主色、高亮项主色其余浅主色、多系列 c1–c5、负值 f-neg、K 线不用红绿）。
- PPTX：高亮逐点着色、柱图目标线为原生组合图虚线系列、图表皮肤随风格；横向条形图不再出现「彩虹柱」。
- 桑基图 PPTX 重写：全局比例尺、三次贝塞尔流带（custGeom）、流失节点灰化、标签后绘不被遮挡。

#### 示例
- 研究：分 6 章（章节扉页），新增引言、方案对比高亮表、标杆共同做法 bento 页（替换图片占位末页），Exhibit 连续编号并补图题与来源。
- 架构：第 2 页改为 4 层 × 4 节点 + 横切护栏 + 图例；新增指标、选型高亮表、依赖拓扑、章节扉页、里程碑，共 12 页。
- 演示 / showcase：补参考资料、目标线与高亮、bento 安装卡、问题 → 方案页。

#### 优化与清理
- 架构图层高求解参数顺序错误（第 4 层越出版心）、排序面板底板压注释带、引言署名与背景叠印、章节号字号进入比例尺（`chapterNum`）。
- 删除 `scripts/hydrate_charts.py`（被 lib_chart_svg 取代）、未引用的 `.btn--soft` / `.btn--onDark` / `.ul--flow`、「A/B 通道」旧注释；`docs/showcase.html` 与 `docs/style-gallery.html` 同步。
- 负例自足：N11 注入内联 `.tbd`；IMAGE_CAPTION 检查不再依赖模型含图片页。

### M2 HTML ↔ PPTX 同源

#### 同源
- 新增 `scripts/lib_solver.py`（与 lib_solver.js 逐值对齐同一 golden，120 例），`render_from_model.py` 渲染前同样拆页，HTML 与 PPTX 页序一致。
- 浏览器运行时 `assets/pptx-export.js` 删除整套 OOXML 几何引擎（与服务端不一致、仅用于预览），只保留 schema 校验、内联求解器（`__TOPPPT_SOLVER__` 注入）与 `pagePlan()`；每份 HTML 约减 90KB。
- 预览模态改为按 pagePlan 克隆真实 HTML 版块作缩略图，标注页型与续页；缩略图网格行不再被压扁。
- `cross_verify.py` 改为默认运行的同源核对：页数 = 求解页计划、PPTX/HTML 标题顺序、图表数据与标签、溢出；当即发现 business-blue 引用页顺序漂移并修正。

#### 原生图表
- 甘特 / 进度 / 漏斗 / 对比条改为 PPTX 原生可编辑条形图（隐藏基底、剩余轨道、对称占位技巧），删除 shapeGantt / shapeFunnel / shapeVsbar 形状绘制；新增 `tests/charts/native-rows.model.json` 探针（CI 断言 ≥4 个 chart part）。

#### 清理
- 删除 `scripts/gen_channel_a.js`、`dist/regression-a`、`validate_pptx --allow-shape-charts`、sync_runtime 中针对旧几何的检查与误报；文档同步改写（pptx-export.md 等）；feedback 门禁改为断言浏览器端不再含几何引擎。

### M1 布局求解器

#### 求解器与容量
- 新增 `scripts/lib_solver.js`（纯函数、零依赖、确定性）：`rows()` 行/卡/泳道高度分配（紧张时压缩、富余时拉伸到上限并整组居中）、`fitUp()` 稀疏时字号向上求解、`capacity()` 按页型 × 模式估算承载比、`splitModel()` 超载拆续页（标题加「（续）」，结论只在首页、来源只在末页）、`grid12()`。
- 新增 `scripts/solve_model.js`：报告各页容量比，`--write` / `--out=` 写回拆页后的模型，HTML 与 PPTX 同源消费。
- `build_pptx.js` 读模型后先做容量求解：`--strict` 下超载直接失败（退出码 4）并提示先跑 solve_model；非 strict 自动拆页并告警。

#### 版式（PPTX）
- 泳道 / 金字塔 / 矩阵改由求解器分配高度，不再「挤在顶部、下半页空白」。
- 双栏 / 三栏稀疏内容自动切换为「段落卡片网格」（MD3 tonal 卡撑满版心）。
- 玫瑰图、关系网络在宽版心下采用「主图 + 排序面板」组合（右侧按数值排序的条目 + 比例条，全部取自数据）。
- 环形图按版心求解圆心与半径（上限 2.1in），无要点时图例改为图例卡。
- 瀑布图：末项等于前项之和时识别为合计柱；去掉在 LibreOffice/WPS 下错位的累计折线叠加，改为标准瀑布 + 数值标签。
- 箱线图：箱体按组距放宽，数值标签移到箱体右侧，消除与箱线叠印。
- 双区组合页：右区只给 points 时按要点渲染（此前默认画出空柱图）；图表下沿收在注释带之上。
- 信息图内联数据表超过承载（>5 行）自动转入演讲者备注，不再压进结论条。

#### 门禁与测试
- 视觉填充门禁对四份示例（演示 / 研究 / 架构 / 产品展示）全部转为硬门禁；架构样张冒烟转为硬门禁。
- 新增 `tests/solver/test_solver.js` + 金样 `golden.json`：10 页型族 × 3 模式 × 4 档共 120 例，断言确定性与拆页不变量；CI 增加「同模型两次构建幻灯片 XML 逐字节一致」检查。
- `regression.py` 全链路回归恢复全绿（showcase 大纲 9 条改为双栏，对比页不再被误要求图标，split 探针不再越界）。

### M0 止血（PR #6）

#### 质量门禁
- 新增 `scripts/check_visual_fill.py`：PPTX → LibreOffice → PNG，在正文区按 24×12 栅格检查有墨占比（VISUAL_FILL）、最大连续空白（VISUAL_EMPTY_BLOCK）、墨水重心（VISUAL_OFF_CENTER）。business-blue 黄金样张为硬门禁（M1 起四份示例全部硬门禁）。CI 与 Release 安装 libreoffice-impress、poppler-utils、fonts-noto-cjk。
- `audit_docs.py` 新增 ⑧ 禁止词：「甲板」、结论条「So what」标签、`.sowhat--labeled`、旧品牌名。

#### 引擎（PPTX B 通道）
- 单系列柱 / 条 / 线 / 面积图统一主色（不再按数据点轮换彩虹色），加浅色数值网格线。
- points + metrics：指标改为右侧纵向 MD3 tonal 卡片，要点按高度均分并加细分隔线。
- kpi：hero 落在等高 tonal 卡片内垂直居中，支撑指标按高度均分。
- quote：去掉装饰大引号；新增 `metrics`（2–4 个证据数字）证据卡片行（A 通道与 render_from_model 同步）；schema 增 `quote.metrics`。
- steps / cards：单行卡片随版心拉伸，留白不再集中在下半页。
- 2-col-feature 特性栏去掉左侧竖条，改 tonal 底。
- 图标：运行时不再隐式调用 sharp，直接用包内 `assets/icons/*.png`（降为 256px）；`--strict` 下图标缺失直接失败（exit 3）。
- CLI：缺 `--model` 直接报错退出（`--demo` 显式调试）；支持 `--out=`。

#### 样式与文档
- engine.css 去掉 `.col--feature` / `.arch__lname` / `.flagbar` 的左侧装饰竖条；research 示例的 so-what 本地覆盖同步去竖条；删除 `.sowhat--labeled`。
- references 删除「So what」标签示例与标签变体说明；金句页规范改为「金句 + 署名 + 证据」。
- 旧品牌名统一为 topmind-presentation（代码、模板、示例、文档）。
- README 中英两版只保留一张主题总览图；主题总览图重拍（去旧名）并做 256 色量化。
- business-blue 示例：金句页补证据数字；空的「配图占位」页换成推进路线（timeline）页。

#### 包
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
