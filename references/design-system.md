# 设计系统（风格无关 · 理论 / Token / 栅格 / 语义类）

> **生成报告时读本文件**：设计哲学、CRAP/MD3、页面高度模型、PPTX 比例尺、12 列网格、语义字阶、
> 结构 token、排版类、布局工具、**SVG 主题语义类**（图表配色必读）。
> **组件 CSS 实现目录**（顶栏/卡片/列表/表格/页脚/动效等）在 `../docs/archive/refs/design-system-engine.md`——
> 生成时用 `components-atoms.md` 的组件写法即可，**勿整读 engine 文件**。

本文件提供**设计哲学、Token、栅格、语义字阶、SVG 语义类**——全部风格复用。
**颜色 / 字体 / 圆角 / 阴影的实际值不在此文件**，由 `references/styles.md` 中你所选的那套风格通过 `data-style` 覆盖块注入。
**组件 CSS 类实现目录**（顶栏/卡片/列表/表格/页脚/动效）在 `../docs/archive/refs/design-system-engine.md`——生成时用 `components-atoms.md` 写法即可。

配合方式（三模式独立模板）：
1. 从 `assets/templates/{presentation|research|architecture}.html` 复制对应模式模板起步（模板自带模式密度层与专属组件）。
2. 模板内 `__TOPPPT_ENGINE__` 标记块是公共引擎内联副本（源自 `assets/templates/engine.css`，`sync_runtime.py` 注入，禁止手改）——本文件描述的引擎 CSS 即其内容。
3. 再从 `styles.md` 确认所选风格的 light + dark 覆盖块（模板已内嵌 9 套全量 token，换默认风格只需改 `data-style`）。
4. `<html data-mode="X" data-style="Y" data-theme="light">`——模式生成时锁定，风格可实时切换。

## 1. 设计哲学（所有风格通用）

> **中性色承担结构与层次，单一强调色承担焦点。**

- 层次 = `surface-1/2/3` 明度差 + 1px 边框，**不是**色相差异
- 全篇**只有一个强调色**（哪套风格就哪个色）
- 禁止：渐变、多色胶囊、彩色阴影、用红/绿/紫区分模块
- 暗色不是"把亮色反过来"，surface 走**近黑阶**，文字用高明度灰

## 1a. 设计原理（四条可自检的准则）

> 本节的四条准则是**生成时自问、交付前自检**的判据（吸收业界主流 PPT 技能的设计理论注入做法）。任何一条不成立，先改版式再谈交付。

### ① CRAP 四原则（对比 / 重复 / 对齐 / 亲近）

| 原则 | 含义 | 在本技能里的落地 |
|------|------|-----------------|
| **Contrast 对比** | 重要与次要必须一眼可分 | 单一强调色只给焦点（关键数字/结论/主图）；主标题 `--fw-title:600` 与正文 400 形成字重差；表面明度差 ≥2 阶 |
| **Repetition 重复** | 同一类元素跨页保持同一形态 | 锁定页型库（29 种）——同类内容永远同一种版式；页头/页脚/图表标题位置固定 |
| **Alignment 对齐** | 一切元素落在同一套网格上 | 12 列网格（§1e）+ 版心左边界；禁止"看起来差不多"的目测对齐 |
| **Proximity 亲近** | 相关的内容靠近，无关的拉开 | 卡片内边距 ≥ 组间距；标题与正文间距 < 组与组间距；一屏一视觉重心 |

### ② 7:2:1 配色法则

- **7 成中性底色**（`bg` / `surface-1/2/3`）——承担版面主体
- **2 成结构与文字色**（`border` / `text-2` / `text-3`）——承担骨架与注解
- **1 成强调色**（`accent` / `accent-soft`）——**只给焦点**：关键数字、结论条、主图数据点、当前项
- 反例：整页强调色块 >10%、每个卡片标题都用强调色、用强调色画装饰线——都会让"焦点"失效

### ③ 字体决策矩阵

| 场景 | 正文 `--font-body` | 标题 `--font-display` | 代表风格 |
|------|-------------------|----------------------|---------|
| 通用商务 / 技术 / 数据 | 无衬线（Google Sans / Roboto / 雅黑栈） | 同正文（**字重与字号**制造层级） | business-blue / deep-teal / spectrum |
| 咨询 / 研究 / 报告 | 无衬线正文（Inter / Plex） | **衬线标题**（Georgia / Songti / STSong） | mckinsey / warm-sand |
| 正式品牌 / 政企汇报 | HarmonyOS Sans / 雅黑栈 | 同正文（粗字重 + 收紧字距） | brand-red |
| 极简 / 产品 / 品牌 | 系统栈（SF Pro / Helvetica） | 同正文（**更大字阶 + 大留白**） | apple-mono |
| 沉浸深色 / 架构大屏 | Inter / SF Pro Text | Inter / SF Pro Display | graphite-dark / indigo-violet |

**纪律**：一套报告只用一组字体栈；标题衬线 + 正文无衬线是"编辑感"的标准搭配，反之（标题无衬线 + 正文衬线）在本技能中不采用；数字与表格列一律 `font-variant-numeric: tabular-nums`（PPTX 侧由字体回退保证）。风格语汇（字体栈 / 圆角 / 字阶微调 / 字距 / 行高 / 密度 / 链接色）的单源清单见 `layout-constants.json` `styleIdentity`，与 `engine.css` 覆盖块一一对应（`audit_styles.py` 逐项校验）。

**PPTX 单字体**：`layout-constants.json` 的 `font`/`fontDisplay` 为 Office 单字体名，一律 **Microsoft YaHei**（Windows/Mac Office 可用）。**禁止**把 `PingFang SC`（Mac 独有）或 `SimSun`（投影过细）写入 PPTX token。HTML 侧 CSS 用完整 fallback 栈承载风格字体个性（含 Georgia 衬线标题、SF/Inter 系统栈），PPTX **不跟 HTML 换字体族**——投影可读性优先；色 token 双端同源。

### ④ 去 AI 味（视觉层）

- 不加多余角标、chips 堆叠、日期页码横条（铁律 14）
- 不用渐变、彩色阴影、玻璃拟态、无意义图标墙
- 图标每屏 3–8 个（`icons.md`），架构模式图为王可无图标
- **结论条禁左侧 accent 装饰轨（left rail）**：`.sowhat` / 同类收口条只用 MD3 tonal surface（`accent-soft` 满铺 + 细描边）+ 舒适字阶/行高/内边距表达强调；**禁止**竖色条、霓虹边、装饰 chip 当「AI chrome」。功能向状态条（如 `.flagbar` 待核实）可保留细强调，但不得照搬到结论条。
- 文案层的高危词表见 `layout-constants.json` `aiFlavor.words`（`validate_report.py` 硬拦）；视觉层本条写入 `aiFlavor.visual` 注释与 `content-rules` / `components-atoms` / SKILL

## 1b. MD3 对齐映射（m3.material.io）

本引擎的 token 对齐 Material Design 3 的标准体系，便于"讲 MD3 语言"。

| MD3 系统 | MD3 概念 | 本引擎对应 |
|---------|---------|-----------|
| Color | `primary / on-primary / primary-container` | `--accent / --accent-on / --accent-soft` |
| Color | `surface / surface-container-low~high` | `--surface / --surface-1~3` |
| Color | `on-surface / on-surface-variant` | `--text / --text-2` |
| Color | `outline / outline-variant` | `--border / --border-soft` |
| Color | `inverse-surface / inverse-on-surface` | `--surface-inv / --text-inv` |
| State | hover/focus/pressed state layer（内容色 8%/12%/12% 叠加） | 可交互元素 hover 用 `--surface-2` 或 `color-mix` 叠加，等价于 state layer 的克制实现 |
| Typography | Display / Headline / Title / Body / Label | `.t-display/.t-h1~h3/.t-lead/.t-body/.t-sm`（+ eyebrow=Label） |
| Elevation | Level 0–5（双层阴影） | `--shadow-1/--shadow-2`（极轻，Google 执行） |
| Shape | corner none/xs/s/m/l/xl/full = 0/4/8/12/16/28/∞ | `--r-sm:8 (S) / --r-md:12 (M) / --r-lg:16 (L) / --r-xl:24 (近XL) / --r-full` |
| Motion | emphasized decelerate `cubic-bezier(.05,.7,.1,1)` / standard `cubic-bezier(.2,0,0,1)` | `--ease-emphasized`（显现与翻页）/ `--ease-standard`（常规过渡） |
| Motion | duration short1-4=50–200ms / medium1-4=250–400ms / long1-4=450–600ms / extra-long=700–1000ms | `--dur-short:.18s`（悬停/小过渡）/ `--dur-medium:.28s`（主题切换/尺寸）/ `--dur-long:.6s`（页面显现）/ `--dur-xlong:.7s`（图表生长）——**不得再写硬编码秒数** |
| Layout | 响应式断点、4dp 间距栅格 | `--wrap:1400px` + 1180/960/620px 降级；间距全走 `--sp-*`（4px 基） |
| Accessibility | 最小触控目标 48×48dp | `.btn` 高 48px；桌面密集场景图标钮可 40px |

**MD3 Type Scale 对照**（MD3 标准值 → 本引擎投影优化值，单位 px）：

| MD3 角色 | MD3 字号/行高 | 本引擎类 | 本引擎取值（clamp 上限） |
|---------|--------------|---------|------------------------|
| Display Large | 57 / 64 | `.t-display` | 68 / 1.1（投影加大） |
| Headline Large | 32 / 40 | `.t-h1` | 48 / 1.18 |
| Headline Small | 24 / 32 | `.t-h2` | 34 / 1.25 |
| Title Large | 22 / 28 | `.t-h3` | 22 / 1.35 |
| Body Large | 16 / 24 | `.t-lead` | 21 / 1.62 |
| Body Medium | 14 / 20 | `.t-body` | 17 / 1.68 |
| Label Large | 14 / 20 (500) | `.t-sm` | 15 / 1.6 |
| Label Medium | 12 / 16 (500) | `.t-xs` | 13 / 1.55 |

> 字重执行：MD3 Display/Headline 默认 400，本引擎按用户要求加粗为 700/600（`--fw-display/--fw-title`）；Label 级保持 500–600。行高比例遵循 MD3「角色越小行高比越大」的规律。

**采用 MD3 的原则，但做两处克制调整**：
1. **阴影降到 Level 1–2**——MD3 允许到 Level 5，但商务演示靠边框 + 表面色差分块更耐看。
2. **强调色不启用动态取色（Dynamic Color）**——改用 9 套固定风格，保证品牌与场合可控。

## 1c. 页面高度模型（page-fit · 16:9 优先 · 每页高度稳定）

> 目标：**默认 16:9 屏上，每页恰好一屏、不溢出、不空旷，且页与页之间高度一致**（翻页节奏稳定，不再出现"高矮不齐"）。

### 页面高度模型（引擎默认行为）

```css
/* engine.css 已内置：每个 .band 至少一屏高 + 垂直居中 */
:root{ --band-pad:clamp(40px,6vh,88px); --band-min:calc(100vh - var(--bar-h)); }
.band{padding-block:var(--band-pad);
      min-height:var(--band-min);min-height:calc(100svh - var(--bar-h));
      display:flex;flex-direction:column;justify-content:center}
.band>.wrap{width:100%}
```

三种对齐（按内容量选，**不再需要手写 min-height**）：

| 类 | 行为 | 何时用 |
|----|------|--------|
| `.band`（默认） | 至少一屏高 + 垂直居中 | 内容接近一屏的常规页（多数页） |
| `.band--top` | 至少一屏高 + 贴顶排布 | 内容约六七成屏，居中会显得"悬空" |
| `.band--flow` | **放弃固定页高**，自然流式 | 长结构页：参考资料 / 附录全量表 |

- 内容超一屏时 `min-height` **不截断**（自动退化为自然流），安全；但校验器会按页高估算报 FAIL，须按下面顺序减量。
- `--band-pad` 由模式模板覆盖（演示 56–116px / 研究 40–80px / 架构 32–64px），**不要直接改 `.band` 规则**。
- `100svh` 兼容移动端浏览器工具栏；旧浏览器回落 `100vh`。
- 顶栏折叠（B 键）会收紧 `--bar-h`，页高随之重算（脚本已派发 resize）。

### 高度预算表（设计时按此规划，校验脚本会抽查）

| 屏幕 | 可视高 | 减顶栏 `--bar-h:68` | 减 band 上下 padding | **内容预算** |
|------|--------|--------------------|---------------------|-------------|
| 1920×1080（基准） | 1080 | 1012 | ≈ 92×2 = 184 | **≈ 830px** |
| 1366×768（下限） | 768 | 700 | ≈ 65×2 = 130 | **≈ 570px** |
| 2560×1440 | 1440 | 1372 | ≈ 116×2 = 232 | ≈ 1140px |

经验值：章节头 shead ≈ 150–190px；一行指标卡 ≈ 150px；一张主图（fig）≈ 300–420px；一张表（6 行）≈ 340px。**1080p 下「shead + 一个主件 + 一行辅助」正好一屏。**

### 超出预算时按此顺序处理，**先减后拆**

1. **精简** —— 删次要信息、列表项合并（每卡 ≤4 条）。
2. **压缩** —— 减栅格 gap、图表取下限尺寸（`charts.minSize`）。
3. **多列** —— 单行长内容改 2/3 列；Agenda 条目多时改 2 列（见 `components.md` Agenda 多列）。
4. **拆页** —— 仍放不下就拆成两页（01a / 01b），**宁拆勿挤**。

- **禁止**：为一屏放下而**无限**缩字号/缩图表（难看小气），或让内容溢出页边界被裁切。内容偏多时：先列表化/精炼，再换组合/拆页，**最后才**按 `fontShrink` 有限下探。
- 自测：在 1920×1080 与 1366×768 各看一遍，每页都能整屏呈现且页高一致。
- 校验：`validate_report.py` 的「页高溢出估算」对**所有非 `--band--flow` 页**做 字×行高+组件 的静态估算，超一屏预算即 FAIL。

### PPTX 侧的同名保障

PPTX 无"页高"概念（固定 13.333×7.5in），对应纪律是**内容不越界、不重叠**：

- 页型几何全部取自 `layout-constants.json` 的 `pageTypes`；内容安全下界为 `pageTypes.layout.contentBottom`（有 so-what / 来源行时收紧到 `contentBottomWithNote`）。
- 文本块按可用高度自适应字号/行距（`fitFont`，有限下探：`containers.fontShrink`，模式 floor presentation/arch 10pt、research 9pt，最多 4 档），表格行高按可用高度计算，列表/泳道/矩阵/卡片行高全部随容器收敛——**优先优化内容与组合；内容确实偏多时允许有限缩字号，但不得压到 floor 以下**。
- `validate_pptx.py` 硬拦：元素越界 / 负坐标 / 非正尺寸 / 文本溢出估算 / 容器级溢出（按容器类型扣 `containers.pad`）/ 字号低于 6.5pt / 未声明图片。

## 1d. PPTX 排版比例尺（导出侧 · 常量单源 · 三模式独立）

> HTML 侧字号走上面的 MD3 Type Scale（clamp 流式，模式密度层见 `modes.md`）；**PPTX 导出侧**字号走三模式**独立**比例尺。
> 数据源：`scripts/layout-constants.json` 的 `typeScale`（基准）+ `modeTypeScale`（三模式独立取值，两导出通道共用，改值只改 JSON 再跑 `sync_runtime.py`）。research 是完整咨询密排比例尺，不是简单 ×0.8 缩放；序列化器按「调用点基准 pt → 最接近 typeScale 角色」映射。

| 层级 | 用途 | presentation (pt) | research 密排 (pt) | architecture (pt) |
|------|------|------------------|-------------------|-------------------|
| coverTitle | 封面主标题 | 44 | 36 | 44 |
| coverSub | 封面副标题 | 18 | 14 | 19 |
| h1 | 章节行动标题 | 30 | 22 | 30 |
| h2 | 阶段名/卡片标题 | 17 | 13.5 | 17 |
| lead | 章节导语 | 14 | 11.5 | 14 |
| body | 正文/要点 | 13 | 10.5 | 13 |
| caption | 图表标签/来源行 | 11 | 9 | 11 |
| micro | 页码/图例/微注 | 10 | 8.5 | 10 |

**纪律**：
- 不得用缩小字号替代结构重排——放不下按「精简内容形态→压缩→多列→拆页」处理（见 §1c）；内容形态已最优仍偏多时，允许按 `containers.fontShrink` 有限缩字号。
- 页面几何（`pw/ph/mx`）与页型几何（common/exhibit/diagram/split/research/arch）同在 `layout-constants.json`，与 HTML 版式同源。
- 模式取值只来自 `modeTypeScale`（每个角色一个 pt 值）；未知模式回落 `presentation` 档，不再有第二套 fs 系数。

## 1e. 12 列网格与安全边距

> 单一事实源：`scripts/layout-constants.json` 的 `grid`（`columns` / `gutter` / `colW` / `x[13]` / `y[6]` / `safe`）。
> PPTX 侧由 `build_pptx.js` 消费（跨列框 = `{ x: grid.x[i], w: grid.x[j+1] - grid.x[i] }`）；HTML 侧对应 `engine.css` 的 `.g12` 栅格工具类。

- **12 列轨道**：`x[0]` = 版心左边界，`x[12]` = 版心右边界；`gutter` 为列间距；`colW` 为单列宽
- **6 条行基线**：`y[0]` ≈ 内容区顶（`contentTop`）、`y[5]` = `contentBottom`——用于快速对齐卡片行/图表行
- **安全边距 `safe`**：`top/bottom/left/right`——**任何元素不得越过**（校验器 `SHAPE_OUTSIDE_SLIDE` 与 `MIN_EDGE_MARGIN_IN` 硬拦）
- **常用跨列**：`4/4/4`（三栏）、`6/6`（双栏）、`3/6/3`（侧栏 + 主区）、`8/4`（主区 + 注解列）、`12`（全幅图）
- **纪律**：同一页的卡片/图表框必须落在网格线上；**不得**用"目测居中"代替网格对齐（CRAP 的 Alignment）

## 1f. 语义字阶 C0–T14

> 单一事实源：`layout-constants.json` 的 `typography.levels`——把三模式比例尺的 8 个角色（`coverTitle/coverSub/h1/h2/lead/body/caption/micro`）展开为 **15 个语义层级**，供 HTML 组件类与 PPTX 调用点对齐。**pt 值仍以 `modeTypeScale` 为唯一来源**（本表只做语义映射，不重复存 pt）。

| 层级 | 名称 | 映射角色 | 典型位置 |
|------|------|---------|---------|
| `C0` | 封面 / 章节幕标题 | `coverTitle` | 封面主标题、章节幕标题 |
| `T1` | 页码 / 章节徽章 | `caption` | 页码徽章、章节编号 |
| `T2` | 页面主标题 / 结论标题 | `h1` | 每页顶部结论句（research 行动标题） |
| `T3` | 副标题 / 语境说明 | `lead` | 主标题下方导语 |
| `T4` | 模块标题 / 图表标题 | `h2` | 卡片标题、图表标题、面板标题 |
| `T5` | 证据编号 / 轻量标签 | `micro` | Exhibit 编号、状态标签 |
| `T6` | 证据块标题 / 小节标题 | `h2` | 分栏小标题 |
| `T7` | 正文解释段落 | `body` | 证据解释、管理解读正文 |
| `T8` | 结论条文字 | `body` / 略大于 body | MD3 结论条正文（无 So what 标签） |
| `T9` | SO WHAT 标签 | `caption` | so-what 标签行 |
| `T10` | SO WHAT 正文 / 业务含义 | `body` | so-what 正文、行动含义 |
| `T11` | 图表轴 / 图例 / 刻度 | `micro` | 坐标轴、图例、刻度、单位（**禁用于表格正文**） |
| `T12` | 图表数据标签 | `caption` | 折线点值、柱形标签、百分比 |
| `T13` | 关键 KPI 大数字 | `h1` | KPI 大数字、hero 数值 |
| `T14` | 注释 / 口径 / 来源 / 页脚 | `micro` | footnote、来源行、页脚 |

**纪律（表格语义字号）**：表格正文 / 行动项 / 风险项 / 解释句 / 建议句 / 长项目符号 / 完整短句必须用 **T7 或 T10**；**T11 只允许**轴标签、刻度、图例、极短表格标签、单位、列短标签或非句子型微标签。表格密度必须与内容匹配——字号未低于下限但单元格大面积空洞、阅读重心塌陷，同样判不合格。

## 2. 结构 Token（版式/间距/字号/圆角基线）

这些**不随风格变色**，但字号、圆角可被风格微调。

```css
:root {
  color-scheme: light;
  /* 字号 · 流式缩放（投影够大） */
  --fs-display: clamp(2.75rem,4.6vw,4.25rem);
  --fs-h1:      clamp(2rem,3.2vw,3rem);
  --fs-h2:      clamp(1.5rem,2.1vw,2.125rem);
  --fs-h3:      clamp(1.125rem,1.35vw,1.375rem);
  --fs-lead:    clamp(1.0625rem,1.25vw,1.3125rem);
  --fs-body:    clamp(0.9375rem,1.05vw,1.0625rem);
  --fs-sm:      clamp(0.8125rem,0.92vw,0.9375rem);
  --fs-xs:      clamp(0.75rem,0.82vw,0.8125rem);
  --fs-metric:  clamp(2.25rem,3.4vw,3.25rem);
  /* 风格语汇基线（每套风格可覆盖；清单 = layout-constants.styleIdentity） */
  --letter-display: -0.03em;
  --letter-eyebrow: 0.11em;
  --lh-body: 1.68;
  --lh-lead: 1.62;
  --link: var(--accent-text);
  /* 间距 · 8pt */
  --sp-1:4px; --sp-2:8px; --sp-3:12px; --sp-4:16px;
  --sp-5:24px; --sp-6:32px; --sp-7:48px; --sp-8:64px;
  /* 圆角基线（风格可覆盖 --radius） */
  --radius: 16px;
  --r-sm: 8px;
  --r-md: 12px;
  --r-lg: var(--radius);
  --r-xl: calc(var(--radius) + 8px);
  --r-full: 999px;
  /* 版心与页面高度 */
  --wrap: 1400px;
  --gap: clamp(16px,1.6vw,28px);
  --bar-h: 68px;
  --band-pad: clamp(40px,6vh,88px);          /* 页内上下留白（模式模板覆盖） */
  --band-min: calc(100vh - var(--bar-h));    /* 单页最小高度 = 一屏（每页高度稳定） */
  /* 阴影基线（风格可覆盖） */
  --shadow-1: 0 1px 2px rgba(60,64,67,.08),0 1px 3px 1px rgba(60,64,67,.06);
  --shadow-2: 0 1px 3px rgba(60,64,67,.10),0 4px 8px 3px rgba(60,64,67,.06);
  /* 字体占位（风格覆盖 --font-body / --font-display） */
  --font-body: "Google Sans","Roboto",-apple-system,BlinkMacSystemFont,"Segoe UI",
               "PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans SC",sans-serif;
  --font-display: var(--font-body);
  /* 标题字重（主标题粗体；风格可微调） */
  --fw-display: 700;
  --fw-title: 600;
}
html[data-theme="dark"] { color-scheme: dark; }
```

> **颜色 token（--bg/--surface/--text/--border/--accent…）一律不写在这里**，见 `styles.md`。
> 这里只放默认值兜底，真正生效的是风格覆盖块。

## 3. 基础与排版类（用 --font-body / --font-display）

```css
*,*::before,*::after{box-sizing:border-box}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%;
  scroll-snap-type:y proximity}   /* 滚轮整屏停靠（proximity 不卡高屏） */
body{
  margin:0;background:var(--bg);color:var(--text);
  font-family:var(--font-body);
  font-size:var(--fs-body);line-height:1.65;letter-spacing:.01em;
  -webkit-font-smoothing:antialiased;font-feature-settings:"kern" 1,"liga" 1;
  transition:background-color .28s cubic-bezier(.2,0,0,1),color .28s cubic-bezier(.2,0,0,1);
}
h1,h2,h3,h4,p{margin:0}
h1,h2,h3,h4{font-family:var(--font-display);font-weight:var(--fw-title);color:var(--text)}

/* 主标题粗体 */
.t-display{font-size:var(--fs-display);line-height:1.1;letter-spacing:-.03em;font-weight:var(--fw-display)}
.t-h1{font-size:var(--fs-h1);line-height:1.18;letter-spacing:-.022em;font-weight:var(--fw-title)}
.t-h2{font-size:var(--fs-h2);line-height:1.25;letter-spacing:-.015em;font-weight:var(--fw-title)}
.t-h3{font-size:var(--fs-h3);line-height:1.35;letter-spacing:-.008em;font-weight:var(--fw-title)}
.t-lead{font-size:var(--fs-lead);line-height:1.62;color:var(--text-2)}
.t-body{font-size:var(--fs-body);line-height:1.68;color:var(--text-2)}
.t-sm{font-size:var(--fs-sm);line-height:1.6;color:var(--text-3)}
.t-xs{font-size:var(--fs-xs);line-height:1.55;color:var(--text-3)}
.t-metric{font-size:var(--fs-metric);line-height:1;letter-spacing:-.035em;font-weight:500;
  font-variant-numeric:tabular-nums}
.t-eyebrow{font-size:var(--fs-xs);font-weight:600;letter-spacing:.11em;text-transform:uppercase;
  color:var(--accent-text)}
.cite{font-size:.62em;vertical-align:super;color:var(--accent-text);font-weight:600;
  margin-left:2px;text-decoration:none}
.cite:hover{text-decoration:underline}

/* 参考资料外部/内部链接（保留链接效果，新窗口打开） */
.ref-link{color:var(--accent-text);text-decoration:none;font-weight:500;
  border-bottom:1px solid var(--accent-soft-2);padding-bottom:1px;
  transition:border-color .18s,color .18s;white-space:nowrap}
.ref-link:hover{color:var(--accent);border-bottom-color:var(--accent)}
.ref-link svg{width:.82em;height:.82em;vertical-align:-.08em;margin-left:2px;opacity:.75}
```

## 4. 布局与栅格

```css
.wrap{width:100%;max-width:var(--wrap);margin-inline:auto;padding-inline:clamp(20px,3.2vw,56px)}
section{scroll-margin-top:calc(var(--bar-h) + 16px)}
section.band{scroll-snap-align:start}   /* 配合 html 的 scroll-snap，整屏停靠 */
/* 页面高度模型：每个 .band 至少一屏高 + 垂直居中（每页高度稳定） */
.band{padding-block:var(--band-pad);
  min-height:var(--band-min);min-height:calc(100svh - var(--bar-h));
  display:flex;flex-direction:column;justify-content:center}
.band>.wrap{width:100%}
.band--top{justify-content:flex-start}          /* 内容约六七成屏：贴顶 */
.band--fit{justify-content:center}              /* 兼容旧报告：等价默认行为 */
.band--flow{min-height:0;justify-content:flex-start}  /* 长结构页（参考资料/附录） */
.band--tint{background:var(--surface-1)}
.band--accent{background:var(--accent-soft)}                        /* 软强调（收尾/CTA，亮暗同向） */
.band--accent--solid{background:var(--accent);color:var(--accent-on)} /* 实底强调（金句） */
.band--deep{background:var(--deep-bg);color:var(--deep-fg)}   /* 固定深色反相页（两主题一致），仅显式选择、≤1 处、不作末页 */
.grid{display:grid;gap:var(--gap)}
.g-2{grid-template-columns:repeat(2,minmax(0,1fr))}
.g-3{grid-template-columns:repeat(3,minmax(0,1fr))}
.g-4{grid-template-columns:repeat(4,minmax(0,1fr))}
.g-5{grid-template-columns:repeat(5,minmax(0,1fr))}
.g-6{grid-template-columns:repeat(6,minmax(0,1fr))}
.g-auto{grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
.g-bento{grid-template-columns:repeat(4,minmax(0,1fr));grid-auto-rows:minmax(118px,auto)} /* 拼贴 */
.sp-2{grid-column:span 2}.sp-3{grid-column:span 3}.sp-4{grid-column:span 4}.rw-2{grid-row:span 2}
.g-hero{grid-template-columns:minmax(0,1.08fr) minmax(0,1fr);align-items:center}
.g-side{grid-template-columns:minmax(0,1.35fr) minmax(0,1fr);align-items:start}
.stagger{display:flex;flex-direction:column;gap:clamp(20px,2.8vh,40px)} /* 交错图文 */
.stagger__row{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:clamp(20px,3vw,52px);align-items:center}
.stagger__row--rev .stagger__media{order:2}
.kv{display:grid;grid-template-columns:auto minmax(0,1fr);gap:var(--sp-3) var(--sp-5);align-items:baseline} /* 键值 */
.stack{display:flex;flex-direction:column}
.gap-3{gap:var(--sp-3)}.gap-4{gap:var(--sp-4)}.gap-5{gap:var(--sp-5)}.gap-6{gap:var(--sp-6)}
.row{display:flex;align-items:center;gap:var(--sp-3)}.row-wrap{flex-wrap:wrap}
@media (max-width:1180px){.g-4{grid-template-columns:repeat(2,minmax(0,1fr))}
  .g-5{grid-template-columns:repeat(3,minmax(0,1fr))}
  .g-6{grid-template-columns:repeat(3,minmax(0,1fr))}.g-side{grid-template-columns:1fr}
  .g-bento{grid-template-columns:repeat(2,minmax(0,1fr))}.sp-3,.sp-4{grid-column:span 2}}
@media (max-width:960px){.g-3,.g-hero{grid-template-columns:1fr}
  .stagger__row{grid-template-columns:1fr}
  .g-hero__visual{order:-1;max-width:460px;margin-inline:auto}}
@media (max-width:620px){.g-2,.g-4,.g-5,.g-6{grid-template-columns:1fr}
  .g-bento{grid-template-columns:1fr}.sp-2,.sp-3,.sp-4{grid-column:span 1}.rw-2{grid-row:auto}}
```

> **非对称栅格扩展**（`g-hero--rev` / `g-side--rev` / `g-31` / `g-13` / `g-41` / `g-14`）见 `components.md` §46b。

## 9. SVG 主题语义类（图表随主题/风格变色，关键！）

```css
.f-acc{fill:var(--accent)}.f-accs{fill:var(--accent-soft)}.f-accs2{fill:var(--accent-soft-2)}
.f-s1{fill:var(--surface-1)}.f-s2{fill:var(--surface-2)}.f-s3{fill:var(--surface-3)}
.f-inv{fill:var(--surface-inv)}.f-none{fill:none}
.f-txt{fill:var(--text)}.f-txt2{fill:var(--text-2)}.f-txt3{fill:var(--text-3)}
.s-bd{stroke:var(--border)}.s-bds{stroke:var(--border-soft)}
.s-acc{stroke:var(--accent)}.s-txt3{stroke:var(--text-3)}
.t-on-inv{fill:var(--text-inv)}
```

> 强调色实底块上的文字用 `.t-on-inv`，不要写死 `#fff`。

## 9b. 编码色板语义类（多系列图表 · 9 套风格各自可辨）

> **两套颜色，两种纪律**：
> · **结构色**（标题 / 正文 / 边框 / 按钮 / 大面积底色）——**永远中性 + 单一强调色**，层次靠表面明度差 + 1px 边框。这是"焦点不被稀释"的保证。
> · **编码色**（数据系列 / 图例色点 / 小段标签）——**必须可区分**，否则图读不懂。9 套风格**各有自己的 `c1–c5`**（单源 `layout-constants.json` 的 `styleDataColors` / `styleDataColorsDark`）。

```css
/* 无 data-style 时的兜底（回落中性，不串色） */
:root{
  --c1:var(--accent); --c2:var(--surface-3); --c3:var(--border);
  --c4:var(--accent-soft-2); --c5:var(--text-3);
}
/* 9 套风格各自的编码色板（由 sync_runtime.py 与 layout-constants.json 保持同源；audit_styles.py 逐值校验） */
html[data-style="mckinsey"]{--c1:#003a70;--c2:#2826bb;--c3:#21a18e;--c4:#b76848;--c5:#99903d}
html[data-style="mckinsey"][data-theme="dark"]{--c1:#7fb2e5;--c2:#6f6bdb;--c3:#8ce3d8;--c4:#d1a694;--c5:#cbc586}
/* …其余 8 套同构，见 assets/templates/engine.css… */
.f-c1{fill:var(--c1)}.f-c2{fill:var(--c2)}.f-c3{fill:var(--c3)}.f-c4{fill:var(--c4)}.f-c5{fill:var(--c5)}
.s-c1{stroke:var(--c1)}.s-c2{stroke:var(--c2)}.s-c3{stroke:var(--c3)}.s-c4{stroke:var(--c4)}.s-c5{stroke:var(--c5)}
```

- 多系列图表（多段环形、分组柱、多折线、散点分组、桑基流带、马赛克段）**统一用 `f-c1~c5` / `s-c1~c5`**，不要写死色值。
- **`c1` 恒等于该风格的强调色**（保持风格身份）；`c2`/`c3` 为近似色，`c4`/`c5` 为降饱和补色。
- 同屏彩色系列 **≤5**；超出合并为"其他"。
- **红绿语义禁用仍成立**：状态类表达（热力矩阵强度、达成对比达标/未达标、K 线涨跌）**不得**用红绿区分好坏，一律走强调色明度阶梯——编码色板只用于**分类**，不用于**评价**。
- 图例 chip 配套：用 `f-c*` 画小色点（见 `components.md` 图例片段），不要用 `style="background:#xxx"` 写死色值。
- **单源色值一律「裸 hex」（不带 `#`）**：`styleDataColors` / `styleDataColorsDark` 存 6 位裸 hex，`#` 前缀会原样流入 PPTX 的 OOXML `<a:srgbClr val="…">` 造成非法色值（PowerPoint 静默忽略该色 / 触发修复）；`#` 只出现在 `engine.css` 的 CSS 覆盖块与画廊派生处。`audit_styles.py` 校验格式，`validate_pptx.py` 的 `INVALID_HEX_COLOR` 硬拦成品包。

## 9c. 对齐与分布工具类（布局修正用）

```css
.a-c{align-items:center}.a-start{align-items:start}.a-end{align-items:end}
.j-c{justify-content:center}.j-between{justify-content:space-between}
.grow{flex:1;min-width:0}
```

- 混排栅格（图+卡、图+文）**必须显式选一个对齐**：图高卡矮用 `a-start`，两者接近用 `a-c`。
- `band--fit` 内容偏少想贴顶而非居中：改用 `band--top`（下方 `components.md` §4）。

## 9d. 强调带 / 待核实标注 / 素材图片

```css
/* 强调带（主题一致）：收尾/CTA 用 accent；金句可 accent--solid；
   band--deep = 固定深色反相页（两主题一致，始终深底浅字，不随主题翻转）——仅显式选择、≤1 处、不作末页 */
.band--accent{background:var(--accent-soft)}
.band--accent .t-eyebrow{color:var(--accent-text)}
.band--accent--solid{background:var(--accent);color:var(--accent-on)}
.band--accent--solid .t-h1,.band--accent--solid .t-h2,.band--accent--solid .t-h3,
.band--accent--solid .t-display{color:var(--accent-on)}
.band--accent--solid .t-lead,.band--accent--solid .t-body{color:color-mix(in srgb,var(--accent-on) 80%,transparent)}
.band--accent--solid .card{background:color-mix(in srgb,var(--accent-on) 12%,transparent);border-color:transparent}
.band--deep{background:var(--deep-bg);color:var(--deep-fg)}
.band--deep .t-lead,.band--deep .t-body{color:var(--deep-fg-2)}
.band--deep .t-eyebrow{color:color-mix(in srgb,var(--accent) 40%,#fff)}

/* 待核实标注（二次修改强调色）：.tbd 内联 + .tbd-legend 图例 + .flagbar 清单 */
.tbd{color:var(--accent-text);font-weight:600;border-bottom:1px dashed var(--accent);padding-bottom:1px;white-space:nowrap}
.tbd-legend{display:flex;align-items:flex-start;gap:var(--sp-2);margin-top:var(--sp-4);font-size:var(--fs-xs);color:var(--text-3)}
.tbd-legend svg{width:14px;height:14px;flex:none;margin-top:.18em;color:var(--accent-text)}
.flagbar{margin-top:var(--sp-4);border:1px solid var(--border-soft);border-left:3px solid var(--accent);
  border-radius:var(--r-md);background:var(--accent-soft);padding:var(--sp-3) var(--sp-4)}
.flagbar__hd{display:flex;align-items:center;gap:var(--sp-2);font-size:var(--fs-xs);font-weight:700;color:var(--accent-text)}
.flagbar li{position:relative;padding-left:16px;font-size:var(--fs-xs);color:var(--text-2)}

/* 素材图片族（比例锁定 / 裁切 / 蒙版图注 / 通栏出血 / 配图占位 / 多图网格 / 双图对比 / Logo 墙）
   src 仅 data: 内联或相对路径；比例与 imageSpec.ratioCssClass 一一对应（PPTX 用同一比例算高度） */
.media{position:relative;display:block;border-radius:var(--r-lg);overflow:hidden;background:var(--surface-1);border:1px solid var(--border-soft)}
.media img{display:block;width:100%;height:100%;object-fit:cover}
.media--r16-9{aspect-ratio:16/9}.media--r4-3{aspect-ratio:4/3}.media--r3-2{aspect-ratio:3/2}
.media--r1-1{aspect-ratio:1/1}.media--r21-9{aspect-ratio:21/9}.media--r3-1{aspect-ratio:3/1}
.media--contain img{object-fit:contain}.media--plain{border:none;border-radius:0}
.media--mask::after{content:"";position:absolute;inset:0;z-index:1;
  background:linear-gradient(180deg,transparent 42%,color-mix(in srgb,var(--surface-inv) 64%,transparent))}
.media__cap{position:absolute;left:0;right:0;bottom:0;z-index:2;padding:var(--sp-4) var(--sp-5);color:var(--text-inv);font-size:var(--fs-sm)}
.media__cap--below{position:static;color:var(--text-3);padding:var(--sp-3) 0 0;font-size:var(--fs-xs)}
.media--full{margin-inline:calc(-1 * clamp(20px,3.2vw,56px));border-radius:0;border-left:none;border-right:none}
.media--bleed{margin-inline:calc(-1 * clamp(20px,3.2vw,56px));border-radius:0;border-left:none;border-right:none}
.media--ph{border:1px dashed var(--border);background:var(--surface-1);display:grid;place-items:center;text-align:center;gap:var(--sp-2)}
.media--ph::before{content:"";position:absolute;inset:0;opacity:.45;
  background-image:repeating-linear-gradient(135deg,transparent 0 9px,var(--border-soft) 9px 10px)}
.media__ph{position:relative;z-index:1;display:flex;flex-direction:column;align-items:center;gap:6px;padding:var(--sp-4)}
.media__ph svg{width:28px;height:28px;stroke:var(--accent);fill:none;stroke-width:1.6}
.media__ph b{font-size:var(--fs-sm);font-weight:600;color:var(--text-2)}
.media__ph span{font-size:var(--fs-xs);color:var(--text-3)}
.media-grid{display:grid;gap:clamp(12px,1.6vw,22px);align-items:start}
.media-grid--2{grid-template-columns:repeat(2,minmax(0,1fr))}
.media-grid--3{grid-template-columns:repeat(3,minmax(0,1fr))}
.media-grid--4{grid-template-columns:repeat(4,minmax(0,1fr))}
.media-compare{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:clamp(16px,2.4vw,40px);align-items:start}
.media__tag{display:inline-flex;align-items:center;justify-content:center;min-width:26px;height:22px;
  padding-inline:8px;border-radius:var(--r-full);background:var(--accent-soft);color:var(--accent-text);
  font-size:var(--fs-xs);font-weight:700;letter-spacing:.04em}
.media-wall{display:grid;grid-template-columns:repeat(auto-fit,minmax(96px,1fr));gap:clamp(10px,1.4vw,20px);align-items:center}
.media-wall .media{background:var(--surface-2);filter:grayscale(1);opacity:.82;transition:filter .2s,opacity .2s}
.media-wall .media:hover{filter:none;opacity:1}
.media__src{margin-top:var(--sp-2);font-size:var(--fs-xs);color:var(--text-3)}
```

> 均为**主题一致**实现：不写死色值，浅色/深色自动适配（`.media__cap` 用 `--text-inv` 在深色图上仍可读；`.media__ph svg` 用 `--accent` 随风格换色）。详见 `components.md` §11/§11b/§11c。

