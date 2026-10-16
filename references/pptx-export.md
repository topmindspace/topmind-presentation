# PPTX 生成（页序预览 + 智能体精导 · 常量 / schema / 求解器三单源）

把 HTML 报告生成为**可编辑的 16:9 PPTX**。核心架构：**报告内嵌的 `window.REPORT_MODEL` 是唯一事实源**——HTML 是阅读与演示界面，PPTX 是协作与修改格式，两者来自同一内容模型，PPTX 内全部是原生形状/文本框/表格，**带数据的图表为原生数据图表（chart part + 内嵌 Excel 工作簿，双击即可"编辑数据"）**；**默认零图片（`pictures=0` 全原生可编辑）**，仅当模型显式声明 `section.image` 时放行对应图片；无素材时用 `image.placeholder` 出**配图占位**（原生形状，`pictures` 不增）。版式常量单源（`scripts/layout-constants.json`）+ **DSL schema 单源（`scripts/model-schema.json`）**，双端校验同源、产出一致。全程不依赖任何外部技能（质检脚本 `scripts/validate_pptx.py` 已内置，纯标准库）。

## 架构总览

```
                HTML 报告（页面 + window.REPORT_MODEL，mode 生成时锁定）
                 │                          │
   页序预览（不导出文件）                  智能体精导（唯一交付通道 · 唯一几何引擎）
   header「预览 PPTX」→ 页序计划            extract_model.py → model.json
   （pagePlan：与精导同一求解器拆页，       → build_pptx.js --model=（PptxGenJS，原生可编辑图表）
    缩略图 = 页面上对应的 HTML 幻灯片）    → validate_pptx.py --strict（0/0 才交付）
   + 常显「复制 AI 提示词」
                 │
   单源：layout-constants.json（几何 / 比例尺 / 风格 token / 图表登记）
       + model-schema.json（页型 DSL；注入浏览器 validateModel，extract_model.py 直读）
       + lib_solver.js（布局求解器：容量 / 拆页 / 行高；build_pptx require、浏览器注入、lib_solver.py 金样对齐）
```

- **页序预览**：点 header「预览 PPTX」（快捷键 P）查看交付 PPTX 的页序计划——页序由运行时 `pagePlan()` 给出（与 `build_pptx.js` / `render_from_model.py` 同一布局求解器拆页），缩略图直接克隆页面上对应的 HTML 幻灯片。**M2 起浏览器端不再有第二套几何引擎**（原 2000 行 OOXML 序列化器与服务端长期漂移，已删除）。**页面不直接导出文件**：浏览器端跑不了 strict 质检硬门禁，达不到交付质量；预览模态常显**可复制 AI 提示词**，用户想获得 PPTX 时复制给 AI，由智能体走精导通道生成（`?` 帮助弹窗 / 快捷键 H 有同样说明）。
- **智能体精导（唯一交付 · 唯一几何引擎）**：`extract_model.py` → `build_pptx.js` → `validate_pptx.py --strict` 0/0。用户选「HTML+PPTX」或事后要 PPT 时才跑。
- **双单源**：页面几何/三模式独立比例尺（`typeScale` 基准 + `modeTypeScale` 模式取值）/页型几何/12 风格 token 全在 `scripts/layout-constants.json`；**页型 DSL schema（字段/必填/适用模式）在 `scripts/model-schema.json`**。通道 B 直接 `require`；页面运行时由 `sync_runtime.py` 注入（同时注入三模板的引擎/UI/运行时内联副本）。**改常量只改 JSON，改 schema 只改 schema JSON，然后跑 `python scripts/sync_runtime.py`**。

### 会场与字号（venue · P1-4）

PPTX `modeTypeScale` 以**中型会议室投影**为默认（presentation 正文 13pt）。按会场微调，**不要**用无限缩字号塞字：

| 会场 | 建议 | 做法 |
|------|------|------|
| 小会议室 / 桌面投屏 | 默认可略紧 | 保持 mode 比例尺；密卡页走拆页而非降到 floor 下 |
| 中型会议室（默认） | presentation body 13pt / research 10.5pt | `modeTypeScale` 原值 |
| 礼堂 / 大报告厅 | 提高可读性 | 演示稿优先更大标题档与更少每页单元；必要时整体上移一档角色映射，**仍禁**为塞字破 fontShrink floor |

HTML 侧仍用 MD3 clamp；双端都以「最后一排可读」为准（`presentation-craft` back-of-room）。


## 内容模型（只填模型 · render_from_model 回填正文）

三份模式模板（`assets/templates/{presentation|research|architecture}.html`）尾部已带对应模式的占位。字段：

> **模型单写路径**：内容只写 `window.REPORT_MODEL`，再 `python scripts/render_from_model.py 报告.html --inplace` 回填正文——禁止 HTML/模型双写。

| 字段 | 说明 |
|------|------|
| `mode` | `presentation` / `research` / `architecture`（与 `data-mode` 一致，生成时锁定；校验器检查） |
| `style` | 12 套风格之一（不写则取页面 `data-style`） |
| `theme` | `light` / `dark`（不写则取页面 `data-theme`，默认 light）——**PPTX 按此导出亮色版或深色版**（深色走 `stylesDark` token，与 HTML 深色主题同源；validate_report 检查与 `data-theme` 一致） |
| `title` / `subtitle` / `meta` | 封面 |
| `agenda` | `[[编号, 标题, 说明]…]`；>8 条自动双列、行高自适应；**architecture 极简形态可省略**（封面后直接进图，PPTX 相应少一页大纲） |
| `sections` | 章节页数组，页型见下表 |
| `closing` | `{title, points:[[k,v]×3]}` 收尾页（主题一致强调带：accent-soft 底） |

**必须是严格 JSON**（双引号、无尾逗号、无注释），否则 `extract_model.py` 无法解析。

### 章节页型（sections[].type）——29 种，字段约束单源 `scripts/model-schema.json`

**通用（演示为主，research 可用）**

| type | 对应 HTML 版式 | 关键字段 |
|------|---------------|---------|
| `points`（默认） | 要点列表页 | `points:[[k,v]]`、`metrics:[[值,注]]` |
| `metrics` | 指标带页（R4） | `lead`、`metrics:[[值,注]]` |
| `kpi` | 大数指标页（`components.md` §41） | `hero:[值,标签,delta?]`、`metrics:[[值,注]]` |
| `table` | 密表页（R3；research 行上限 16，行高按可用高度自适应） | `table:{head, rows, colW?}` |
| `timeline` | 时间线/路线页 | `phases:[[标签,名称,说明,'done'/'now'/'']]` |
| `steps` | 步骤条页（`components.md` §47） | `steps:[[标题,说明]…]`（元素可为 `{t,d,accent}`）、`groups:[[标签,步数]…]?`、`note?` |
| `bar` | 数据图表页——**原生数据图表**（20 类原生通道）或**形状还原图表**（10 类形状通道，附数据表） | `chart:{type?, labels, values, series?, points?, start?, target?, max?, unit?, colors?, dataTable?}`、`note`（`type` 取值见 `chartTypes` 30 类） |
| `donut` | 环形图页（`components.md` §42：**原生数据图表** + 中心合计 + 数值图例） | `chart:{labels, values, unit?, centerLabel?, colors?, dataTable?}`、`note` |
| `heatmap` | 热力矩阵页（`components.md` §48：4 级色阶，只用强调色明度阶梯） | `rowHeads:[]`、`colHeads:[]`、`cells:[[]]`、`unit?`、`scaleLabel:[低,高]?`、`note?` |
| `bullet` | 达成对比页（`components.md` §49：底槽 + 实际条 + 目标刻度） | `items:[[标签,实际,目标]…]`、`unit?`、`max?`、`note?` |
| `pyramid` | 金字塔页（`components.md` §50：自上而下逐层加宽） | `levels:[[标题,说明]…]`（元素可为 `{t,d,accent}`）、`note?` |
| `image` | 素材图片页（`components.md` §11c：full/half/bleed/grid/compare/wall 六版式，比例与位置锁定；支持配图占位） | `image:{src?\|items?:[]\|placeholder?:true, layout?, fit?, caption?, alt?, hint?}`、`points:[[k,v]]`（half 右栏注解）、`note?` |
| `cards` | 卡片网格（g-3/g-4） | `cards:[{title, points:[]}]`、`columns` |
| `split` | **双区组合页**（g-side；左/右各可为要点｜图表｜表格｜图片，组合版式的通用解） | `left:{type?:'points'(默认)/'table'/'image'/图表类型名, points?/head?/rows?/labels?/values?/series?/image?/cap?}`、`right:{…同构，缺省 type='bar'}` |
| `comparison` | 对比页（`components.md` §40：左右双面板） | `left/right:{title, points:[[k,v]…]}`、`verdict` |
| `chapter` | 章节扉页（大号章节序号 + 标题 + 本章页目；不出页眉） | `title`、`eyebrow`（「01 · 章名」）、`items?`、`body?` |
| `quote` | 金句页（`components.md` §39：主题一致强调带，accent-soft 底） | `quote`、`author`、`metrics`（2–4 个证据数字，必填）、`context?` |
| `diagram` | 分层架构（.arch / A1，含层间连接；**architecture 模式自动走全幅图页型**） | `layers:[[层名,[节点…],'focus'?]]`、`legend:[]` |

**research 密排专属**

| type | 对应 HTML 版式 | 关键字段 |
|------|---------------|---------|
| `twocol` | 双栏论证页（R1） | `paragraphs:[[小标题,正文]…]`（两栏自动均分） |
| `exhibit` | Exhibit 编号图表页（R2） | `exhibitNo`、`chart:{type?, labels,values,max?,unit?,series?,dataTable?}`（type 见 chartTypes） |
| `threecol` | 三栏证据页（R6） | `paragraphs:[[小标题,正文]…]`（三栏自动均分） |
| `halftable` | 半表半图页（R7） | `table:{head,rows}` + `chart:{type:'hbar',…,dataTable?}`（左表右图互证） |
| `matrix` | 矩阵图页（R8） | `rowHeads:[]`、`colHeads:[]`、`cells:[[str 或 {t,accent}]…]` |

**architecture 专属**

| type | 对应 HTML 版式 | 关键字段 |
|------|---------------|---------|
| `lane` | 泳道页（A2；A3 管线映射为单泳道） | `lanes:[[行头,[步骤…]…]…]`（步骤 str 或 `{t,accent}`） |

**复杂信息图专属（research / architecture）**——形状通道高保真还原 + 数据表：

| type | 对应 HTML 版式 | 关键字段 |
|------|---------------|---------|
| `sankey` | 桑基图页（节点-流带，流向与流量） | `flows:[[源,汇,值]…]`、`unit?`、`chart.dataTable?`、`note?` |
| `treemap` | 树图页（面积编码的层级构成） | `items:[[标签,值]…]`、`unit?`、`chart.dataTable?`、`note?` |
| `boxplot` | 箱线图页（分布对比 min/q1/median/q3/max） | `groups:[[标签,min,q1,med,q3,max]…]`、`unit?`、`chart.dataTable?`、`note?` |
| `network` | 关系网络页（节点-边拓扑） | `nodes:[[id,标签]…]`、`edges:[[源,汇]…]`、`chart.dataTable?`、`note?` |
| `marimekko` | 马赛克图页（列宽 × 列高双重编码） | `cols:[[标签,总量]…]`、`cells:[[]…]`、`unit?`、`chart.dataTable?`、`note?` |
| `streamgraph` | 流带图页（时间上的构成演变） | `series:[{name,values}…]`、`labels:[]?`、`chart.dataTable?`、`note?` |

> 几何常量见 `layout-constants.json` `pageTypes.{sankey,treemap,boxplot,network,marimekko,streamgraph}`（含节点/流带上限、采样点下限、双边界追踪约束）；版式与生成规则详见 `references/infographics.md`。

**通用可选字段（全部页型）**：`soWhat`（结论条，MD3 tonal soft 满铺、**无左轨**；**不绘制「SO WHAT」标签**）、`footnote`（页脚来源行）、`note`（口径注，与 `footnote` 共用注释带末行 `footnoteY=6.72`，同页二者自动合并为一行）、`flags`（**待核实标注清单** `["…"]` → accent 强调色清单条，提示用户二次确认，并写入演讲者备注）、`image`（素材图片 / 配图占位，见 `image` 页型）、`exhibitNo`（非 exhibit 页型也可带 Exhibit 徽标）。research 模式 `soWhat/footnote` **只在关键论证页填写**（克制条款；结论条无 So what 字样）。**`verdict` 与 `soWhat` 互斥**（共用 annotation 结论条槽位，同页双填必叠印）——comparison 页填 `verdict`（accent 实底结论条）时不要再填 `soWhat`；渲染器自动二选一（verdict 优先），`extract_model` 对同页双填发 WARN。

> **素材图片（单源 `layout-constants.json` 的 `imageSpec`）**：`image` 三选一必填——`src`（用户图，data: 内联或相对路径）｜`items:[{src,alt?,caption?,placeholder?}]`（多图版式）｜`placeholder:true`（**配图占位**，无素材时锁版式用）。
> - **六版式**（`layout`）：`full` 版心全宽 3:1｜`half` 左图右注 4:3｜`bleed` 通栏出血 21:9｜`grid` 多图网格 4:3（2/3/4/6 张）｜`compare` 双图 A/B 4:3｜`wall` Logo 墙 1:1。比例写在 `imageSpec.ratioDefault`，**HTML 用同比例锁定类、PPTX 用同一比例算高度并垂直居中**——两通道版式一致。
> - **裁切**（`fit`）：`cover`（默认，裁切填满）/ `contain`（完整显示留白）。
> - **占位符**：由**原生圆角矩形 + 虚线 + 居中标签文本**渲染（`pictures` 不增，可编辑可替换）；标签串由双引擎按 `imageSpec` 拼同一串（`配图占位 · 建议 2400×800px`），保证 `cross_verify` 逐页文本一致；同时写入演讲者备注提示替换。占位**不算图片**，不触发 `PICTURES_*` 门禁。
> - **路径解析**：相对路径以**模型文件所在目录**为锚（模型与报告同目录 ⇒ 报告里的相对路径口径一致）；文件缺失报 `IMAGE_SRC_MISSING` 并回落成占位框（不留空洞）。
> - **准入门**：`imageAdmission`（`forbidden` 禁图片化区域 / `allowed` 可保留的复杂视觉资产 / `maxPageAreaPct` 40% / `fullSlideRiskPct` 90%）。
> - **素材准备**：`python scripts/prepare_images.py <图片|目录> --layout full|half|grid…` → 产出可粘贴的 `.media` HTML 片段与 `image` 模型对象（自动缩放/压缩/内联，体积超限自动转相对路径）。

> **图表双通道**：图表类型与通道归属以 `scripts/layout-constants.json` 的 `charts.registry` 为唯一事实源（四元组：`html` 实现 / `pptx` 通道 / `nativeType` 或 `path` 几何约束 / `dataTable` 策略）。**PPTX 还原度分级**（`charts.fidelityMap`）：`high` 双通道等价｜`medium` 形状可读但视觉降级｜`low` PPTX 显著退化（area/radar/treemap/sankey/streamgraph/marimekko/boxplot/network）。**交付 PPTX 时优先 high 图型**（`bar`/`hbar`/`line`/`donut`），或对 low 图型强制 `dataTable=inline` 补数据表——详见 `chart-decision-tree.md`。
> - **原生通道（20 类，`pptx:"native"`）**：`bar / hbar / stack / stackline / line / dualline / area / donut / multidonut / pie / radar / scatter / bubble` + 行式原生 `gantt`（隐形起点基底 + 时长）、`progress`（完成 + 剩余轨道）、`funnel`（对称隐形基底居中）、`vsbar`（簇状条形正负双向）+ 3 类原生技巧 `waterfall`（堆叠柱 + 隐藏基底 + 累计连接线）、`gauge`（doughnut + firstSliceAng 270° 扇形）、`pareto`（多类型组合：柱 + 累计折线）——一律走 `pptxgenjs addChart`，产出真 chart part + 内嵌 Excel 工作簿，PowerPoint/WPS 中双击即可"编辑数据"。`chart.series` 传多系列（`[{name, values}…]`）；`chart.points` 传 XY 点（scatter `[[x,y]…]` / bubble `[[x,y,size]…]`）。
> - **形状通道（`pptx:"shape"`，16 类）**：全部走 OOXML 原生形状高保真还原（`charts.registry[type].path` 约束采样点下限、双边界追踪、禁预设形状替代）。按**载荷形态**分两组：
>   - **可作 `chart.type` 的 10 类**（载荷 = `chart:{labels, values, series?, start?, target?, max?, unit?}`）：`sparkline / slope / dumbbell / lollipop / dotplot / bulletchart / waffle / radialbar / rose / candlestick`——由 `bar` / `exhibit` / `halftable` / `split` 页型承载。
>   - **专属页型 6 类**（载荷是结构化数组：`flows` / `items` / `groups` / `nodes+edges` / `cols+cells` / `series`，不适合作 `chart.type`）：`sankey / treemap / boxplot / network / marimekko / streamgraph`——由同名 `sections[].type` 承载，见页型表「复杂信息图专属」。
> - **可达性不变量**：`charts.types` 的每个类型都必须「模型可表达」——可作 `chart.type`（`model-schema.json` 的 `chartTypes`，**30 类** = 20 原生 + 10 形状）**或**可作 `sections[].type`（上述 6 类信息图页型）。`sync_runtime.py` 双向校验（`registry.types == chartTypes ∪ 信息图页型`），出现孤儿类型即 WARN——防止「登记了但模型表达不了、双引擎实现沦为死代码」。
> - **验证口径**：36 类图表**全部**经探针模型实测双通道——原生通道断言 chart part 落位（`MODEL_CHART_COUNT` 按类型计数），形状通道断言**命中专属渲染器**（`build_pptx.js` 对未命中类型打印回落告警）且 HTML↔PPTX 同源核对通过（`cross_verify.py`）。示例矩阵**永久覆盖 13 类**（`bar` / `donut` / `hbar` / `waterfall` + 6 类信息图页型 + `gantt` / `rose` / `candlestick`）；其余类型靠探针回归，改图表代码后应重跑探针。
> - **数据可追溯（`chart.dataTable`）**：`notes`（默认，数据表写入演讲者备注）/ `inline`（图表下方附原生小字号表格）/ `off`（仅 sparkline 等装饰微图允许）。**形状通道图表的 `dataTable` 不得为 off**（豁免：登记表**自身**声明 `off` 的纯装饰微图，如 `sparkline`——`sync_runtime.py` 与 `validate_pptx.py` 同口径）。校验器 `MODEL_CHART_COUNT` 按类型断言（原生通道必须落成 chart part），`MODEL_CHART_DATATABLE` 硬拦"形状拼图无数据表"与"声明 inline 却无表格落位"。
> - **HTML ↔ PPTX 同源核对**：`cross_verify.py` 断言 PPTX 页数 = 求解器页序计划、章节标题在 PPTX 与 HTML 中按序对齐、原生图表数值 = 模型数值；交付 PPTX 的演讲者备注数据表（`MODEL_CHART_NOTES_MISSING`）与原生图表计数（`MODEL_CHART_COUNT`）一律不豁免。
>
> **自适应排版**：所有文本块按可用高度自适应字号/行距（`fitFont`），表格行高按可用高度计算，列表/泳道/矩阵/卡片行高随容器收敛——保证不越界、不重叠（`validate_pptx.py` 硬拦越界与文本溢出）。**几何铁律**：① 架构节点标题/注解按实际节点高度钳制（注解不得「浮回」标题上，空间不足降级单框混排）；② 图表类目标签含在图高 `h` 内（禁画到 `y+h` 外压 so-what）；③ 多栏均分用**版心全宽**推导（`(CW-(n-1)×gap)/n`，禁用单栏宽当总宽）；④ 图例落图区底部（`bodyBottom-0.28`），禁用页面底部固定偏移；⑤ KPI 支撑指标列在 `dividerX` 右侧（禁全宽默认返回压住 hero）；⑥ 有图注时图片下界收到 `contentBottomWithNote`。Agenda：>8 条自动双列、>12 条自动分页（Agenda I/II）、长标题截断全称沉 notes（`titleMaxChars=36`）、两通道列优先一致。

> 保真机制：每种子页型对应 HTML 的一种锁定版式（`components.md` §36d/§37–38b/§39–42 ↔ 页型表），坐标/字号按同一套常量映射（`layout-constants.json` 的 `pageTypes` + `modeTypeScale`）。**三模式独立比例尺**：research 密排（正文 10.5pt、h1 22pt）；architecture 与 presentation 同基但 diagram 走全幅几何。图表颜色：**12 套风格各有自己的编码色板 c1–c5**（单源 `styleDataColors` / `styleDataColorsDark`，按 `model.theme` 选择），多系列图表自动取用（`dataColors(style, theme)`）；未登记风格时回落「accent / faint / body / line」四阶单色系。**页型字段与必填约束以 `model-schema.json` 为唯一事实源**（`:array` = 非空数组、`:str` = 非空字符串），浏览器端 `validateModel` 与 `extract_model.py` 校验同一份定义。

## 页序预览（已内置三模板）

三份模式模板均已集成：header 工具组「预览 PPTX」（快捷键 P）+「?」PPT 生成指引弹窗（快捷键 H）+ 内嵌页序运行时 + 对应模式模型占位。**生成报告时只填 `window.REPORT_MODEL`，再跑 `render_from_model.py --inplace` 回填正文（超载页按求解器自动拆续页，与 PPTX 同源）。**

- 预览模态读取 `pagePlan()` 渲染交付 PPTX 的页序：每页一张卡（页码 · 页型 · 标题 · 续页标记），缩略图为页面上对应的 HTML 幻灯片
- 打开即自检（schema 单源 + 容量求解）：缺字段列清单，超载页提示「交付时自动拆为 N 页」
- 预览模态常显**「复制 AI 提示词」**；快捷键：`T` 主题 / `P` 预览 / `H` 帮助 / `Esc` 关闭

> 运行时更新（`assets/pptx-export.js`）后：跑 `python scripts/sync_runtime.py`，常量 / schema / 求解器三块自动注入，模板与示例内联副本同步刷新，禁止手改。

## 智能体精导（唯一交付通道 · 硬门禁）

```bash
# 1. 抽模型（报告 → model.json，自动补 style/mode，schema 单源校验 + 模型-正文一致性抽查）
python scripts/extract_model.py "<输出目录>/YYYY-MM-DD-主题.html"

# 2. 生成（PptxGenJS；--style / --theme=light|dark 可覆盖模型风格与亮暗主题；常量自动取 layout-constants.json）
NODE_PATH=<pptxgenjs 所在 node_modules> <node> scripts/build_pptx.js "报告.pptx" --model="报告.model.json"

# 3. 质检（硬门禁，0 errors / 0 warnings 才交付；--model 启用模型往返保真检查）
python scripts/validate_pptx.py "报告.pptx" --strict --model="报告.model.json"
```

> **模型往返保真检查**（`--model`）：验证 PPTX 页数结构与模型一致（封面 + 大纲（有 agenda 时）+ sections + 收尾——**architecture 无 agenda 时按实际断言**），且每个章节标题、封面标题、收尾标题都真实落位在对应的幻灯片上——内容不丢、不串页。错配会报 `MODEL_ROUNDTRIP_*` 警告（strict 下阻止交付）。
> **逐页覆盖**：逐页内容覆盖（section 代表性文本 ≥50% 落在对应页）+ 主题 token 对照（`MODEL_THEME_BG_MISMATCH`，亮暗一致性）。
> **原生图表门禁**：`MODEL_CHART_COUNT` 硬门禁——模型里每个带数据的图表必须落成原生 chart part（可编辑数据），形状拼图不放行。

## PPT 优秀实践（交付基线）

精导产物在"可编辑"之外对齐 PowerPoint 原生使用习惯：

1. **原生数据图表（20 类）**：`bar / hbar / stack / stackline / line / dualline / area / donut / multidonut / pie / radar / scatter / bubble` + 行式原生 `gantt / progress / funnel / vsbar` + 原生技巧 `waterfall / gauge / pareto` 全部走 `pptxgenjs addChart`——真 chart part（`ppt/charts/chartN.xml`）+ 内嵌 Excel 工作簿（`ppt/embeddings/*.xlsx`），在 PowerPoint / WPS 中双击即可"编辑数据"；类别/数值标签由图表自带，单系列按数据点着色（峰值 accent、其余中性，保持 HTML 视觉）。多类型组合图（瀑布/帕累托）用 `addChart([{type,data,options}…], outer)`。
2. **数据表随行**：`chart.dataTable` 三态——`notes`（默认：数据表以「项目 | 数值」文本写入演讲者备注，零版面占用、可复制回 Excel）、`inline`（图表下方附原生小字号表格，压缩图表高度不越界）、`off`（仅 sparkline 等装饰微图）。**形状通道图表的 `dataTable` 不得为 off**（`MODEL_CHART_DATATABLE` 硬拦）——保证非原生图表的数据同样可核对。
3. **演讲者备注**：`lead` / `soWhat` / `note` / `footnote` / 图表口径 / 数据表自动写入页备注（notesSlide）——细节沉到备注区不堆版面，讲稿口径随文件走；封面/收尾页同样有备注。
4. **文档元数据**：`pptx.title/subject/author/company` 从模型填充——文件属性完整，检索与归档友好。
5. **默认零内容图全原生（声明式放行 + 配图占位）**：默认 `pictures=0`（表格为原生 table、文字为原生文本框，全部可就地编辑）；**仅当模型显式声明 `section.image` / `split.left.image` / `split.right.image` 时才导出内容图片**，且内容图数不得超过声明数（`PICTURES_NOT_DECLARED` 硬拦）——图片源只允许 data: 内联或相对路径（外链报 `IMAGE_SRC_EXTERNAL`）。**语义图标（`objectName: icon:*`）单独计数 `icon_pictures`，不进 `pictures` 门禁**（见第 8 条）。**无素材时用 `image.placeholder` 出配图占位**：原生圆角矩形 + 虚线 + 居中标签（可编辑、`pictures` 不增），交付前替换 `src` 即可；版式/比例/图注位置已由 `imageSpec` 锁死。
6. **自适应排版（有限缩字号）**：每个文本块按可用高度在字号阶梯里选"装得下"的最大值；内容偏多时按 `containers.fontShrink` **有限下探**（最多 4 档，floor：presentation/architecture 10pt、research 9pt）。优先顺序：列表化/精炼 → 换/扩组合或拆页 → 最后才缩字号。表格行高按可用高度计算，列表/泳道/矩阵/卡片行高随容器收敛——保证不越界、不重叠；行高 / 容量 / 拆页由 `scripts/lib_solver.js` 统一求解（HTML 端 `lib_solver.py` 金样逐值对齐）。
7. **版面安全边界**：所有页型几何来自 `layout-constants.json` 的 `pageTypes`；内容安全下界 `layout.contentBottom`（有 so-what/来源行时收紧为 `contentBottomWithNote`）。校验器对越界（`SHAPE_OUTSIDE_SLIDE`）、负坐标、非正尺寸、文本溢出估算、字号下限、未声明图片数一律拦截。
8. **图标真导出（PPTX 通道）**：卡片头图标名写入模型 `cards[].icon`（或 HTML `data-icon`），`build_pptx.js` 经 `scripts/icon_lib.js` 取包内预渲染 PNG（`assets/icons/*.png`，运行时不依赖 sharp；可选的 `scripts/icon-assets.json` 着色缓存由维护者离线用 sharp 生成）；`--strict` 下图标缺失直接失败。`objectName` 前缀 `icon:`，`validate_pptx` 单独计数 `icon_pictures`，**不进** `pictures=0` 内容图门禁。无 sharp/资产时回落 accent 小方块路标（可扫读）。图标名 = `icon_lib.js` 键（增长/下降/数据/图表/趋势/占比/表格/效率/成果/安全/权限/检查/风险/团队/流程/计划/智能/洞察/工具/清单）；缺省按标题语义自动挑选。要点列表项目符号仍用 accent 实心方块（列表行首图标属 `.ul--ico`，下一档接同源 PNG）。


## 版式与质量如何保证

1. **同源**：模型从报告抽取（含一致性抽查），PPTX 内容与页面不会走样；改报告就重新抽模型。
2. **双单源**：两通道共用 `layout-constants.json`（页面几何 `pw/ph/mx`、**12 列网格 `grid`**、**语义字阶 `typography` C0–T14**、三模式排版比例尺、页型几何、**12 风格 token × 亮暗**、**图表登记四元组 `charts.registry`**、**容器内边距 `containers`**、**锚点容差 `anchorTolerance`**、**图片准入门 `imageAdmission`**、**图片规格 `imageSpec`（版式/比例/建议尺寸/占位标签/体积上限）**、**深度模式 `deepMode`**）与 `model-schema.json`（**29 页型 DSL + chartTypes + chartDataTable 策略**）；`sync_runtime.py` 注入并校验（含页型四件套、图表登记四元组、语义字阶 role、**图片版式↔比例锁定类↔双引擎实现**四项完整性），杜绝漂移。
3. **同版式**：锁定版式库——HTML 组件与 PPTX 页型成对出现（`components.md` §36d/§37–38b/§39–42/§47–50 ↔ 页型表）；不允许临场发明结构（锁定版式纪律）。**新增页型四件套**：schema 条目 + 几何常量 + 渲染实现（`build_pptx.js`，唯一几何引擎）+ 样例与校验断言，缺一不可。
4. **双硬门槛**：信息结构可编辑（原生文本框/形状/表格；图片默认 0、声明式放行）+ 视觉语义保真（页型几何同源映射）；结构重排优先于缩字号，缩字号仅限 `fontShrink` 有限下探。
5. **硬门禁**：`validate_pptx.py --strict` 检查非法尺寸、越界元素、字体下限、未声明图片数、覆盖率、信息密度、**按类型的原生图表断言（`MODEL_CHART_COUNT`）**、**数据表落位（`MODEL_CHART_DATATABLE`）**，0/0 才交付。
6. **断点可恢复**：REPORT_MODEL 即"恢复锚点"——上下文中断后重跑 extract→build 即恢复，不重新生成。

## 回归（维护工具）

- `regression.py`：每份示例 HTML strict + 精导 PPTX strict 0/0 + 双区组合页探针 + 深色主题探针 + 门禁反向验证 + `cross_verify.py`（HTML ↔ PPTX 同源核对）
- `probe_image_export.py`（素材图片探针）：示例矩阵刻意保持 `pictures=0` 基线，真实素材图片的路径 / 版式 / 裁切 / 声明式放行门禁靠本探针覆盖
- `tests/solver/`：求解器金样（JS）+ Python 端逐值一致性；`tests/charts/native-rows.model.json`：行式原生图表探针

## 路径 C · 渲染回归（可选，需本机 PowerPoint）

对单页视觉还原度要求极高时：用 PowerPoint COM 导出 PNG 逐页对照 HTML。**可选质量增强，不是交付硬门禁**（环境依赖重）。日常覆盖：`check_visual_fill.py` 把 PPTX 渲染成 PNG 做填充率 / 空白 / 重心门禁。

## 质量门禁（闭环）

| 产物 | 校验工具（均在本技能内） | 通过标准 |
|------|---------|---------|
| HTML 报告 | `scripts/validate_report.py <报告.html>` | 全 PASS（模式感知预算 + 页高模型与溢出估算 + 模型一致性 + 页型↔版式对应 + 锚点闭环 + 图表登记与最小尺寸 + Exhibit 连续性 + **强调带约束/待核实标注/素材图片（零外链·alt·版式与比例锁定类对应·占位可见标签·内联体积）** + 预览配套断言） |
| PPTX（精导交付） | `scripts/validate_pptx.py <报告.pptx> --strict --model=<报告.model.json>` | 0 errors / 0 warnings（含**模型往返保真**、**按类型原生图表硬门禁**、**数据表落位**、**越界/文本溢出/未声明图片**、**图片版式·裁切·多图数量·相对路径文件存在性**） |
| 素材图片（真实位图） | `scripts/probe_image_export.py` | build→strict 0/0 且 `pictures == 声明数`（示例矩阵零图片，真实素材路径/版式靠本探针覆盖） |
| 素材准备（用户图片） | `scripts/prepare_images.py <图片\|目录>` | 产出 `.media` HTML 片段 + `image` 模型对象；超体积自动转相对路径；低于建议分辨率给出提示 |
| HTML ↔ PPTX 同源 | `scripts/cross_verify.py`（python-pptx 第三方裁判） | PPTX 页数 = 页序计划、章节标题在两端按序对齐、原生图表数值与模型一致 |
| 风格与单源（改色/改常量后） | `scripts/audit_styles.py` | 12 风格 × light/dark × WCAG 配对全达标 + engine.css ↔ layout-constants.json 双源一致 + **单源完整性**（styleAccents 覆盖 / charts 登记表自洽 / 校验预算键齐全） |
| 常量 / schema / 页型四件套 / 图表四元组 | `scripts/sync_runtime.py` | 注入成功 + 双端引用校验 PASS + **每个 schema 页型都有几何映射** + **charts.types ↔ registry 双向一致** + **非原生图表 dataTable 不为 off** + 语义字阶 role 存在 + 哈希摘要一致 |
| 交付说明 | `scripts/quality_gate.py 报告.html --deliver` | 文件与体积、模式、风格、篇幅、交付格式、校验结论与引用条数**七要素齐备即过**，缺一即 FAIL——**不要手拼** |

> **渲染冒烟（可选路径 C 开源版）**：`soffice --headless --convert-to pdf <报告.pptx>`（LibreOffice，保真度约 85%）；本机未装可跳过，strict + python-pptx 双裁判已覆盖结构与可解析性。

## 环境备注（外部依赖仅两个，均已说明）

- **Node + pptxgenjs**：仅精导通道与回归双裁判需要。在技能目录执行 `npm install pptxgenjs`，或把 `NODE_PATH` 指向任意已含 pptxgenjs 的 node_modules；`regression.py` 会自动探测（`TOP_PPT_NODE_PATH` / `NODE_PATH` / 仓库内 node_modules / 全局 npm root）。
- **Python（标准库）**：跑 `validate_report.py` / `validate_pptx.py` / `extract_model.py`（读 `model-schema.json` 单源）/ `sync_runtime.py` / `audit_styles.py`，无第三方依赖；`cross_verify.py` 可选依赖 python-pptx（未装则自动跳过该第三方裁判，不影响交付判定）。
- 页面预览运行时零依赖（浏览器纯序列化，无 ZIP 打包）。

### Chrome 一致性（P1-6）

跨页页眉/页脚/页码（chrome）应**锁死同一几何**：同 y、同字号角色、同边距（`layoutSystem.zones.chromePct`）。禁止逐页漂移页码位置或交替有无页脚。HTML 用模板页脚；PPTX 由 `pageTypes` chrome 槽位同源落位。便宜门禁：`validate_pptx` 对页脚/页码 y 漂移做 WARN（见 `qualityGates.chromeDriftIn`）。

## 双端保真门禁（M9）

`python3 scripts/check_fidelity.py 报告.html 稿件.pptx --strict`（示例全集：`--examples`）。HTML 端用 Chrome 量每个文字块的位置、字号、颜色、行数；PPTX 端逐段落读字号 / 颜色 / 字体声明，LibreOffice 转 PDF 量行数。两端尺寸本来不同，字号按「相对整稿中位比值」比层级（落在 0.8–1.25 算一致）。阈值：配对 ≥80%、字级偏差 ≤15%、颜色 ΔE>12 ≤8%、换行差 ≥2 行 ≤20%、位置 p90 ≤0.12（research 0.16，网页图卡更高）、缺字体声明 0。新增字号角色写进 `modeTypeScale` 后经 `roleSz()` 取用，不要硬编码。

