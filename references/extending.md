# 扩展点（在规则内自定义版式与样式）

> **何时读**：用户要的版式、风格、图表在现成选项里找不到，或维护者要加新能力时。
> 原则：规则管「不能出错的部分」（对比度、零外链、HTML↔PPTX 同源、门禁），其余留给发挥。下面每个扩展点都写明改哪里、跑什么验证。

## 一、写稿时可以自由组合的（只改 model.json）

| 想要 | 怎么写 | 说明 |
|---|---|---|
| 换风格 / 深浅色 | 顶层 `style`（12 套之一）+ `theme: light / dark` | 两端同源，HTML 里观众还能实时切换 |
| 复合版式（图 + 关键数字 + 解读） | 图表页加 `keyMetrics`、`points`；双图加 `chart2`；小图组加 `minis`（≤2） | `compose: "off"` 关掉自动升级；band 形态自动排「图 → 来源行 → 解读带 → 结论条」 |
| 同一页型换版式 | `variant`（见 `layout-library.md` 匹配列）、`chart.type`、`image.layout` | 不用写版式 id，由匹配规则选最具体的那个 |
| 图表种类 | `chart.type` 取 `charts.registry` 里的 36 种之一（20 种导出为原生可编辑图表） | 选型看 `chart-decision-tree.md`；数据不变，换类型即换图 |
| 复杂信息图 | 页型 `sankey / treemap / boxplot / network / marimekko / streamgraph / matrix / lane / diagram` | 研究 / 架构模式；PPTX 端为原生形状，可逐块编辑 |
| 图文混排 | `image: { src, layout: full / half / bleed / grid / compare / wall, fit, caption }`；`half` 配 `points` 做左图右文 | `src` 用相对路径（相对 model.json）或 `data:`；`make_deck --out` 会把相对路径图片一并复制 |
| 可编辑示意图 | `diagram`（分层）、`lane`（泳道）、`steps` / `timeline`（流程）、`network`（拓扑） | PPTX 里每个节点都是原生形状与文本框，可直接改字、拖动 |
| 强调某一格 / 某一步 | 单元 / 步骤写成 `{ "t": "...", "accent": true }` | 矩阵、泳道、步骤、分层图通用，两端同样高亮 |
| 编号与出处 | `exhibitNo`、`cap`、`source`、`footnote`、`soWhat` | 研究模式一个 `exhibitNo` 都不写时自动编号；写了任意一个即按手写编号 |
| 待核实标注 | `flags: ["…"]` | 渲染为强调色核对条，提醒用户确认 |
| 页眉页脚 | 顶层 `showEyebrow`、`showFootnotes`（默认 false）、`pageNumber`（默认 true） | 默认只留克制页码，隐藏的页脚小字进演讲者备注；带 `[n]` 引用的来源行照常显示；美化路线（`contentLocked`）默认全显示 |
| 复杂信息图的写法与组合 | 见 `infographics-guide.md` | 字段示例、选型组合、PPTX 原生图表与形状的边界 |

## 二、维护者扩展（改单源 + 跑门禁）

| 扩展 | 改哪里 | 必跑 |
|---|---|---|
| 新增一套风格 | `layout-constants.json`：`styles` / `stylesDark` / `styleDataColors(Dark)` / `styleAccents` / `styleIdentity` / **`stylePptx`**（标题字体、字重、标题线、卡片、表格、线宽）；HTML 端在 `engine.css` 加 `html[data-style=…]` token 块 | `npm run sync` → `npm run audit` → `python3 tests/m10/test_m10.py`（校验 stylePptx 全覆盖、表格两端同源）。详见 `style-pack.md` |
| 风格的 PPTX 气质 | 只改 `stylePptx.<风格>`：`display` serif/sans、`titleBold`、`rule` none/long/bar/bar-thick、`card` tonal/outline/hairline、`table` tonal/rule/three-line/zebra、`lineW` | 取值范围由 `test_m10.py` 卡住；HTML 表格规则在 engine.css 同名区块 |
| 新增版式 | `layoutLibrary.layouts` 加条目 → `render_from_model.py` 与 `build_pptx.js` 各实现一份 | `tests/layouts/build_gallery.py` → `test_layouts.py --update`，看 golden 图再提交。详见 `layout-library.md` |
| 新增图表类型 | `charts.registry` 登记（通道 native / shape、数据表策略）→ `lib_chart_svg.py` 出 SVG → `build_pptx.js` 出原生图或形状 | `check_fidelity.py --examples --strict`、`pixel_regression.py` |
| 新增字号角色 | `modeTypeScale` 加角色，PPTX 用 `roleSz(role, base)`，HTML 用对应 `--fs-*` | 保真门禁的字级层级项 |
| 页面几何 | `pageTypeGeometry` / `layoutSlots`（PPTX 区域）；HTML 走 engine.css | `test_layouts.py`、`check_visual_fill.py` |
| 门禁阈值 | `qualityGates`、`checkBudgets`、`charts.variety`；保真阈值在 `check_fidelity.py` 的 `THRESH` | 改阈值要在 CHANGELOG 写明理由，四模式统一，不给单个模式开口子 |

## 三、不开放的（刻意写死）

- 任意自定义颜色 / 品牌色引擎：交付始终是 12 套风格之一，保证对比度、图表色板和双端一致都经过校验。套公司模板时取最接近的内置风格（`recipes/template.md`）。
- 外链资源：图片、字体、脚本一律内联或相对路径。
- 绕过 strict：HTML 与 PPTX 都要 0 错误 0 警告才交付。
