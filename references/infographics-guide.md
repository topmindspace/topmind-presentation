# 复杂信息图指南 · infographics-guide.md

> 适用：一页里要放复合版式、组合图表、复杂图表或配图时。三件事：**怎么写模型**、**怎么选和组合**、**PPTX 怎么做到高保真**。
> 字段以 `scripts/model-schema.json` 为准，图型与通道以 `layout-constants.json` 的 `charts.registry` / `charts.fidelityMap` 为准；本文只讲用法，不重复定义。

## 1. 怎么写：模型字段与示例

一页复杂信息图 = **论点**（标题，一句完整判断）+ **证据**（主图，必要时加副图）+ **解读**（`points`，写原因 / 影响 / 下一步）+ 可选**关键数字**（`keyMetrics`，≤4 个）。

| 想要的形态 | 写法 | 落版 |
|---|---|---|
| 主图 + 解读栏 | `type: bar / donut / exhibit` + `chart` + `points` | 左图右栏（side） |
| 双图对照 | 再加 `chart2`（同口径的第二张图） | 两图并排，解读行在下 |
| 主图 + 小图组 | 再加 `minis`（≤2 个小图，每个带 `cap`） | 主图 + 右侧小多图 |
| 复杂图 + 解读带 | `type: heatmap / treemap / marimekko / sankey / boxplot / streamgraph / matrix / metrics …` + `points` 或 `keyMetrics` | 主图满宽，底部「数字 + 解读」带 |
| 要点 + 指标 | `type: points` + `points` + ≤3 个 `metrics` | 左列表，右指标卡 |
| 阶段推进 | `type: timeline`，2–5 个阶段、每段描述 ≤40 字 | 双端都是阶段卡 + 轴线，`now` 阶段浅底 |
| 图文混排 | `type: image`，`image.layout: full / half / grid`；无素材写 `placeholder: true` | 满版 / 左图右文 / 网格 |
| 编号图表 | 研究模式加 `exhibitNo`，`footnote` 写口径 | Exhibit 头 + 来源行 |

```json
{"type": "bar", "title": "主图看总量，小图看结构：研发爬坡最陡",
 "chart": {"labels": ["Q3","Q4","Q1","Q2"], "values": [30,45,55,60], "unit": "%", "max": 100},
 "minis": [{"cap": "客服", "labels": ["Q3","Q4","Q1","Q2"], "values": [50,62,68,72], "unit": "%"},
           {"cap": "研发", "labels": ["Q3","Q4","Q1","Q2"], "values": [18,26,33,38], "unit": "%"}],
 "points": [["研发起点最低、爬坡最陡", "下一阶段增量主要来自研发"],
            ["客服接近平台期", "靠深化场景而不是扩面"]]}
```

要点：
- 解读不复述图上数字（`check_density.py` 会拦），写数字背后的原因或动作。
- 不想升级为复合版式时写 `"compose": "off"`。
- 数据追溯：`chart.dataTable` 默认 `notes`（写进演讲者备注）；low 图型交付 PPTX 时建议 `inline`。

## 2. 怎么选、怎么组合

先按**问题**选图，再按**页面容量**选组合（详细决策见 `chart-decision-tree.md`）：

- 谁大谁小 → `hbar` / `bar`；趋势 → `line`；占比 → `donut`（最小扇区 ≥5%，否则改 KPI 或对比条）；
- 增减拆解 → `waterfall`；结构 × 规模 → `marimekko`；分布 → `boxplot`；流向 → `sankey`；两维对照 → `heatmap` / `matrix`；
- 计划 → `gantt` / `timeline`；单指标达成 → `progress` / `gauge` / `bulletchart`。

组合规则：
1. **一页一个主图**。副图（`chart2` / `minis`）只用来回答主图带出的下一个问题，口径一致。
2. 主图 + 副图 + 解读，三者合计不超过版心；放不下时求解器会拆页或换形态，不要靠缩字号硬塞。
3. 同一版式不连续出现 3 页以上（`check_rhythm.py`），复杂图页之间插一张要点页或金句页透气。
4. 配图用来交代场景（产品界面、现场），不替代数据图；一页最多一组图片。
5. 低保真图型（下节）在要交付 PPTX 的稿子里少用，或换成等价的高保真图型。

## 3. PPTX 高保真：原生图表 vs 形状

| 等级 | 图型 | PPTX 做法 | 局限 |
|---|---|---|---|
| high | bar · hbar · stack · stackline · line · dualline · donut · multidonut · pie · scatter · bubble · waterfall · gauge · pareto · progress · vsbar · sparkline | 原生 chart part + 内嵌工作簿，双击可编辑数据 | 配色、标签由图表引擎渲染，字距与 HTML 略有差异 |
| medium | funnel · slope · dumbbell · lollipop · dotplot · bulletchart · waffle · radialbar · rose · gantt · candlestick | 原生形状逐点还原，数据表随行 | 改数据要改形状，不能双击编辑 |
| low | area · radar · treemap · sankey · streamgraph · marimekko · boxplot · network | 形状近似（路径采样） | 曲面、流带、图内小标签会有位移；建议 `dataTable: inline` 或换图型 |

做法与边界：
- 能用原生图表就用原生（`MODEL_CHART_COUNT` 会核对）；形状通道的 `dataTable` 不得为 `off`。
- 复合版式在 PPTX 里由同一求解器分区：主图、副图、解读带、关键数字各自成原生对象，双端位置差用 `check_fidelity.py` 量化（位置 p90 ≤0.12）。
- M13 起复杂信息图（marimekko · boxplot · streamgraph · sankey · treemap）在 PPTX 端用 `svgFrame` 按 HTML 的 viewBox 900×340 等比落位，图内标签与 HTML 同位；Exhibit 来源行贴在主图正下方，与 HTML 图框内的来源行同序。剩余差距：表格页的「注：」行仍按版心底边落位（HTML 跟随表格高度），位置差 <0.2。
- 正文行距双端统一为 1.5 倍、不够时 1.3 倍；页眉眉标与页脚小字默认不显示，省下的高度留给图表；需要时用顶层开关 `showEyebrow`、`showFootnotes`、`pageNumber` 打开。

## 4. 高密度复合页：仪表盘与杂志版（M13）

一页同时有数字、图表、观点、图标、图片时，不要堆在一个通用版式里，按内容选：

| 页型 | 什么时候用 | 模型 | 双端落版 |
|---|---|---|---|
| `dashboard` 仪表盘 | 2–4 张**同一口径**的小图 + ≤4 个关键数字 + ≤3 条结论 | `keyMetrics`（可带 `icon`）· `charts[]`（每张带 `cap`）· `points` · 可选 `legend` | 图标 KPI 条 → 共享图例 → n 张图一行 → 底部解读行 |
| `magazine` 杂志版 | 一张有说服力的图片 + 一句金句 + ≤2 个数字 + ≤3 条要点 | `image` · `pull` · `metrics` · `points` | 左图 53% 宽，右侧金句 / 数字 / 要点竖排 |
| 大数字 + 图 + 要点 | 一个数字统领全页 | 普通图表页 + `keyMetrics` + `points`（复合版式自动成 side / band） | 数字条在上，主图 + 解读栏 |
| 图文交错 | 2–3 组「图 + 说明」 | `type: image` + `image.layout: grid` | 网格，说明紧贴图下 |

**多图同页（2–4 张）的规矩**（`lib_dense.dash_charts` / `dashCharts` 双端同源）：
1. **共享图例与配色**：同一系列在每张图里同色；≥2 张多系列图的系列名完全相同时，图例只在图组上方画一次，各图不再各画一份（两端同规则，`lib_dense.dash_legend`）。
2. **共享坐标**：同单位、同类型（bar / hbar / line / stack / area / lollipop / dotplot）且没写 `max` 的图，自动取同一个「好看的上限」，高矮可以直接比。
3. **叙事顺序**：图注自动加 ①②③④，按「总量 → 结构 → 趋势 → 对比」排；结论行按同一顺序引用编号。
4. **一行排开**：PPTX 里 2×2 网格的小图字太小，n 张图一律单行；每张图最窄 ≈2.9in。
5. **长单位进图注**：单位超过 2 个字（「亿人次」「元/km」）时自动挪进图注括号，数据标签只留数字，避免窄格里标签折行。
6. **多系列照常画**：分组柱 / 堆叠柱用 `series`（不必写 `values`）；堆叠柱段内标数，单序列折线 ≤8 点逐点标数（PPTX 值轴隐藏，不标就读不出）。

**什么时候必须拆页**：超过 4 张图；图之间单位或口径不同；任何一张需要 6 个以上类目才讲得清；需要逐图解释（每张图要 2 句以上说明）。拆成「仪表盘总览 + 逐图展开」两到三页。

**元素优先级与取舍**（放不下时按此顺序保留，多出的进演讲者备注，不静默丢弃，`DENSE.overflow`）：标题 > 图表 > 关键数字 > 解读 > 图标 > 图片说明。上限：图 4 · 数字 4 · 结论 3（杂志版数字 2）。

**拥挤门禁**：`LAYOUT_COLLISION` / `CONTAINER_OVERFLOW`（重叠与溢出）、`CROWD_GAP`（相邻卡片间距 <0.12in）、`LAYOUT_MULTI_FOCUS`（一屏大件 ≤1）、`ICON_OVERUSE`（单页图标 ≤8）、`ICON_STYLE_MIXED`；版心填充率与对齐沿用 `LAYOUT_FILL` / `LAYOUT_QA_ALIGN_RHYTHM`。

## 5. 简单页：一个图标、一段话、一个数字（M13 · `type: focus`）

内容很少的页面不要把字放大铺满，也不要只放一行小字。`focus` 页型用**留白 + 非对称构图 + 放大的视觉锚点**：

| 内容 | 写法 | 变体（`variant`） | 默认 |
|---|---|---|---|
| 一个数字 | `number: ["73%", "说明"]` + 可选 `text` · `decoNo` | `left` 左侧巨号 + 右侧说明 · `center` 居中 | left |
| 一句观点 | `statement` + 可选 `text` | `left` 左对齐大字 + 细线 · `center` | left |
| 一段话 | `text` | `left` 窄栏（≤60% 宽）+ 大段首 · `center` | left |
| 一个图标 | `icon` + `label` + 可选 `text` | `center` 大图标居中 · `split` 左图标右文字 | center |
| 一张图表 | `chart` + `text` | `center` 图表居中 · `split` 图 60% + 说明 40% | center |
| 图标 + 文字 | `icon` + `label` + `text` | `split`（默认）· `center` | split |
| 两段文字 | `texts: [[标题, 说明], [标题, 说明]]` | `split` 左右两栏 + 顶线 | split |

**选择规则**：结论句 ≤20 字且没有数据 → statement；有一个统领数字 → number；需要解释背景 → text；表达「类别 / 承诺 / 原则」→ icon / iconText；两件事对照 → twoText；只有一张小图 → chart。同一份稿子里 focus 页不连续超过 2 页，也不超过全篇 25%。

**稀疏门禁 `FOCUS_SPARSE`**（与密度门禁不冲突：`focus` 页免检 UNDERFILL / LAYOUT_FILL / TITLE_ONLY / LOW_CONTENT，改用本门禁）：
- PPTX：正文外框占版心 12%–85%，且有放大锚点（≥22pt 文字、图表、图标块或 `focus:anchor`）。
- HTML：有放大锚点（`focus__num / stmt / ico / fig / para / col`），正文 6–220 字。
- 字多于 220 字说明它不是简单页，改用 points / cards；少于 6 字只剩标题，补一句说明。

## 6. 信息图生成流程与质检

1. **定问题**：这一页回答什么？一句话写成标题（结论句，不是话题词）。
2. **选形态**：按 §2 的问题 → 图型；数据只有一个比例 → pictogram / waffle；多张同口径小图 → dashboard；内容很少 → focus。
3. **写模型**：只写数据和结论，不写坐标；图标名取 `assets/icons/index.json`。
4. **一键出稿**：`python scripts/make_deck.py model.json --out out --fidelity`（渲染 → HTML 质检 → 密度 → PPTX → PPTX 质检 → 双端保真）。
5. **看图**：两端各截一遍（`render_pptx_png.py` / 浏览器截图），逐页看拥挤、孤字、图例重复、图标风格。
6. **质检项**：图表多样性、数据追溯（`dataTable`）、占比图最小扇区 ≥5%、`TITLE_ORPHAN`（标题末行孤字）、`FOCUS_SPARSE`、`ICON_*`、保真位置 p90 ≤0.12。

