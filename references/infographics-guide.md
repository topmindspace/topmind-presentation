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
- 已知差距：Exhibit 来源行在 PPTX 略低；marimekko / boxplot / sankey / streamgraph 的图内标签有少量偏移。演讲时以 HTML 为准，交付编辑以 PPTX 为准。
- 正文行距双端统一为 1.5 倍、不够时 1.3 倍；页眉眉标与页脚小字默认不显示（`showEyebrow` / `showFootnotes` / `pageNumber` 可开关），省下的高度留给图表。
