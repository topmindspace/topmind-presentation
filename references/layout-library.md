# 版式库（layoutLibrary · 8 家族 48 版式）

> **何时读**：挑版式、排节奏、加新版式时。**单源** = `scripts/layout-constants.json` → `layoutLibrary`；本文是它的说明，数值以 JSON 为准。
> **门禁**：`python scripts/check_rhythm.py <model.json|html> --strict`（节奏 / 家族覆盖 / 反模式，CI 对全部示例硬拦）；`python tests/layouts/test_layouts.py`（每个版式一页 golden + PPTX 几何指纹）。

## 怎么用

版式不需要在 model 里写 id：页型 `type` + `variant` + `chart.type` + `image.layout` 决定落到哪个版式（下表「匹配」列，最具体者胜）。挑版式就是挑这几个字段。每个版式有一个**视觉重量**，节奏规则按重量排：

- ◆ 强调：封面、章节扉页、大引言、结束页——全屏一个焦点；
- ○ 轻：大纲、叙事双栏、满版图——留白多，给观众喘息；
- ◐ 中：大多数图表与框架页；
- ● 密：KPI 墙、表格、甘特、热力——信息最多，不连排。

## 节奏与重心规则

- 同重量连续页数上限：{"presentation": 2, "architecture": 2, "research": 3, "default": 2}（研究模式允许 3 页同重量的论证串）；
- 相邻两页不得同一版式（续页除外）；
- 8 页以上的 deck 至少覆盖 5 个家族；14 页以上建议用 `chapter` 章节扉页分段（WARN）；
- 重心：每页只有一个主视觉（一张图 / 一组卡 / 一张表），说明文字放在侧栏或图注，不和主视觉抢面积；页面下沿 1/4 不留大片空白（validate_report 填充门禁）。

## 反模式（硬拦）

- 单页图标 ≤ 6，数据系列色 ≤ 6，同形卡片 ≤ 8；
- 引言页必须带出处或数据佐证；禁用「So what」类标签、左侧竖条、无信息量的装饰。

## 结构（`structure`）

| 版式 id | 名称 | 匹配 | 重量 |
|---|---|---|---|
| `cover` | 封面 | kind=cover | ◆ 强调 |
| `agenda` | 目录（单栏） | kind=agenda · maxItems=8 | ○ 轻 |
| `agenda-2col` | 目录（≥9 项双栏） | kind=agenda · minItems=9 | ◐ 中 |
| `chapter` | 章节扉页（大号章节数字） | type=chapter | ◆ 强调 |
| `closing` | 结束页 | kind=closing | ◆ 强调 |

## 观点（`viewpoint`）

| 版式 id | 名称 | 匹配 | 重量 |
|---|---|---|---|
| `argument-3` | 大标题 + 论据三点 | type=points | ◐ 中 |
| `quote-evidence` | 金句 + 证据数字 | type=quote | ◆ 强调 |
| `contrast` | 对比论点 | type=comparison | ◐ 中 |
| `problem-solution` | 问题 → 方案 | type=comparison · variant=problem-solution | ◐ 中 |
| `narrative-2col` | 双栏论述 | type=twocol | ● 密 |

## 数据（`data`）

| 版式 id | 名称 | 匹配 | 重量 |
|---|---|---|---|
| `kpi-wall` | 大数字墙（2–6 个 KPI） | type=metrics | ○ 轻 |
| `kpi-trend` | 主 KPI + 支撑数字 | type=kpi | ○ 轻 |
| `chart-sidenote` | 主图 + 侧注 | type=exhibit | ◐ 中 |
| `chart-table` | 图 + 表 | type=halftable | ● 密 |
| `chart-full` | 通栏主图（仅限无需解读的过渡页，`compose:"off"`） | type=bar | ◐ 中 |
| `waterfall` | 瀑布拆解 | type=bar · chart=waterfall | ◐ 中 |
| `rank-bar` | 排名条 | type=bullet | ◐ 中 |
| `composition` | 构成环图 + 图例卡 | type=donut | ◐ 中 |
| `distribution` | 分布箱线 | type=boxplot | ◐ 中 |
| `mekko` | 双维占比（马赛克） | type=marimekko | ◐ 中 |
| `stream` | 构成演变（河流图） | type=streamgraph | ◐ 中 |
| `chart-readout` | 图表 + 解读栏 + 关键数字条 | compose=side（bar/donut/exhibit + points / keyMetrics） | ● 密 |
| `chart-dual` | 双图对照 + 解读行 | compose=dual（+ chart2） | ● 密 |
| `chart-minis` | 主图 + 小图组（small multiples，最多 2 张） | compose=minis（+ minis） | ● 密 |
| `chart-band` | 主图 + 底部解读带 | compose=band（信息图 / 结构图 / 指标页 + points） | ● 密 |

> 复合版式规则与模型写法见 `density.md`；`compose` 匹配优先于单纯页型。

## 框架（`framework`）

| 版式 id | 名称 | 匹配 | 重量 |
|---|---|---|---|
| `matrix-2x2` | 矩阵（2×2 / 2×3） | type=matrix | ● 密 |
| `pyramid` | 金字塔 | type=pyramid | ◐ 中 |
| `funnel` | 漏斗 | type=bar · chart=funnel | ◐ 中 |
| `hub-spoke` | 中心辐射 | type=network | ◐ 中 |
| `layer-stack` | 分层架构 | type=diagram | ● 密 |
| `area-tree` | 面积树图 | type=treemap | ◐ 中 |

## 流程和时间（`process`）

| 版式 id | 名称 | 匹配 | 重量 |
|---|---|---|---|
| `steps-h` | 横向步骤 | type=steps | ◐ 中 |
| `milestones` | 里程碑时间线 | type=timeline | ◐ 中 |
| `milestones-icon` | 图标里程碑 | type=timeline · variant=timeline | ◐ 中 |
| `roadmap-gantt` | 甘特 / 路线图 | type=bar · chart=gantt | ◐ 中 |
| `swimlane` | 泳道 | type=lane | ● 密 |
| `flow-sankey` | 流向（桑基） | type=sankey | ◐ 中 |

## 图文（`media`）

| 版式 id | 名称 | 匹配 | 重量 |
|---|---|---|---|
| `text-media` | 图文主从（左文右图） | type=split | ◐ 中 |
| `media-full` | 满版图 + 图注 | type=image · image=full | ○ 轻 |
| `media-grid` | 图片网格 | type=image · image=grid | ◐ 中 |
| `media-half` | 左图右文 | type=image · image=half | ◐ 中 |

## 卡片和网格（`cards`）

| 版式 id | 名称 | 匹配 | 重量 |
|---|---|---|---|
| `feature-cards` | 特性卡 | type=cards | ● 密 |
| `bento` | Bento 拼贴（首卡跨列） | type=cards · variant=bento-grid | ● 密 |
| `feature-2col` | 主张 + 细节双栏 | type=twocol · variant=2-col-feature | ◐ 中 |
| `triad` | 三栏特性 | type=threecol | ● 密 |

## 表格（`table`）

| 版式 id | 名称 | 匹配 | 重量 |
|---|---|---|---|
| `compare-table` | 对比表 | type=table | ● 密 |
| `compare-table-hl` | 对比表（高亮列） | type=table · variant=highlight | ● 密 |
| `score-heat` | 评分热力表 | type=heatmap | ● 密 |

## 风格偏好

每套风格在 `styleGrammar` 里声明偏好家族与版式（见 `styles.md` §10）。偏好只影响选型建议，不改变匹配规则。

## 新增版式

1. 先确认现有 44 个版式组合不出来；2. 在 `layoutLibrary.layouts` 加条目（id / family / name / match / weight）；3. 双渲染器实现（`render_from_model.py` + `build_pptx.js`）；4. `python tests/layouts/build_gallery.py && python tests/layouts/test_layouts.py --update`，看 golden 图再提交。
