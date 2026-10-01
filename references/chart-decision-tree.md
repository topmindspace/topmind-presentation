# 图表选型决策树（L2）

> **何时读**：选图 / 分析意图→图型；常读入口仍是 `playbook.md` §五（核图 8 + 多样性摘要）。读完即停。
> 完整登记与代码 → `extract_snippet.py --chart <类型>`；误用纪律 → `charts.md`（先 `charts-discipline`，核图 8，extended 按需）。
> **PPTX 还原度**：`high` 双通道等价｜`medium` 形状可读但视觉降级｜`low` PPTX 显著退化。low 图型见表末「改判」列——交付 PPTX 时优先 `bar`/`hbar`/`line`/`donut`，或 `dataTable=inline` 强制补数据表。

## 决策表

| 分析意图（读者要得出的结论） | 首选 | 还原度 | 次选 | 禁用 / 改判条件 |
|---------------------------|------|--------|------|----------------|
| 谁大谁小 | `hbar` | high | `lollipop` / `bar` | 类别 >8 → Top7 + 附录 |
| 随时间怎么变 | `line` | high | `area`（low）/ `dualline` | 时间点 >8 不标点值；PPTX 慎用 area |
| 占比是多少 | `donut` | high | `pie` / `multidonut` | 扇区 >5 → 合并"其他"或 `treemap`（low） |
| 每 1% 的直觉 | `waffle` | medium | `donut` | 类别 >3 改 `marimekko`（low） |
| 结构在变形 | `streamgraph` | **low** | `stackline`（high） | 系列 >6 合并；PPTX 优先 stackline |
| 总量 × 构成双编码 | `marimekko` | **low** | `treemap`（low） | 列 >6 / 段 >4 → 拆；PPTX 改 stack+table |
| 份额悬殊（头部集中） | `treemap` | **low** | `donut`（high） | 叶 >16 → 合并；PPTX 改 donut/hbar |
| 从 A 到 B 是谁贡献的 | `waterfall` | high | `pareto` | 段 >6 → 合并 |
| 主要矛盾是哪几个 | `pareto` | high | `waterfall` | 类别 >7 → 合并 |
| 转化/流失在哪一环 | `funnel` | medium | `sankey`（low） | 层 >5 → 改 `hbar` |
| 多对多的流向 | `sankey` | **low** | `network`（low） | 节点 >12 / 流带 >24 → 拆；PPTX 改 table |
| 谁和谁相连 | `network` | **low** | `diagram` | 节点 >18 / 边 >30 → 拆；PPTX 改 diagram |
| 两期谁升谁降 | `slope` | medium | `dumbbell` | 系列 >6 → 取 Top 6 |
| 单指标前后对比（多对象） | `dumbbell` | medium | `vsbar`（high） | 行 >6 → 拆页 |
| 实际 vs 目标（含区间） | `bulletchart` | medium | `bullet` | 行 >6 → 拆页 |
| 达成率（多指标同心） | `radialbar` | medium | `gauge`（high） | 环 >5 → 改 `bullet` |
| 一个值够不够 | `gauge` | high | `radialbar` | 单值叙事，勿与图并存 |
| 分布不是均值 | `boxplot` | **low** | `dotplot`（medium） | 组 >8 → 拆页；PPTX 改 dotplot/hbar |
| 双维定位 + 第三维权重 | `bubble` | high | `scatter` | 气泡 >8 → 标注关键项 |
| 六维能力画像 | `radar` | **low** | `rose`（medium） | 维度 >6 → 拆两组；PPTX 改 bar/rose |
| 区间波动（开高低收） | `candlestick` | medium | `line` | 蜡烛 >12 → 聚合 |
| 多项目完成度 | `progress` | high | `bullet` | 行 >6 → 拆页 |
| 迷你趋势（卡内） | `sparkline` | high | — | 只用于指标卡，不与大图并存 |

## 七种最常见的误用（出现即改判）

1. 用 `bar` 表达占比 → 改 `donut`/`stackline`/`waffle`。
2. 用 `donut` 表达 8 个类别 → 合并或改 `treemap`。
3. 用 `line` 表达类别对比（无时间轴）→ 改 `hbar`。
4. 用 `table` 表达趋势 → 改 `line`/`area`。
5. 用均值型图表表达分布 → 改 `boxplot`/`dotplot`。
6. 同一页放两张同型图 → 改 `split`/`halftable` 并让两图**编码不同维度**。
7. 多系列图用单色明度阶梯（分不清） → 用 `f-c1~c5` 编码色板（见 playbook §八）。
