# 页型选型矩阵（L2）

> **何时读**：选页型 / 意图→页型映射；常读入口仍是 `playbook.md`。读完即停。
> 自动选型：`python scripts/recommend_layout.py --mode A --intent "…" --json`
> 穷举表（内容形态 → 版式 → PPTX 页型）见 `components.md` §46；密度档 `components.md` §46b；组合见 playbook §四。

| 我要表达 | 首选页型 | 次选 | 关键约束 |
|---------|---------|------|---------|
| 要点式并列主张（默认页） | `points` | `cards` | 每卡宜 3–5 条；更多拆卡/跟进页，勿截断条目 |
| 现状基线 / 指标快照 | `metrics` | `kpi` | 4–6 个；单数压场用 `kpi` |
| 单个核心数字压场 | `kpi` | `metrics` | hero 一数一结论 |
| 多维对标清单 | `table` | `halftable` | ≤8 行（research ≤16） |
| 时间趋势 / 爬坡 | `bar`（chart.type=line/area/dualline） | `exhibit` | 时间点 >8 改折线；**area 还原度 low，PPTX 优先 line** |
| 构成占比 | `donut`（pie/multidonut/waffle） | `halftable` / **V3 KPI** | 扇区 ≤5，最小扇区 ≥8%；**极偏（min&lt;5% 或 max/min&gt;20）禁 donut→V3** |
| 排名 / 大小对比 | `bar`（chart.type=hbar/lollipop/pareto） | `table` | 类别 >8 取 Top 7 + 附录 |
| 现状 vs 目标 | `bullet` / `comparison` | `bar`（vsbar/bulletchart） | 目标线与实际条同量纲；comparison 的 `verdict`/`soWhat` **二选一** |
| 两期升降（谁升谁降） | `bar`（slope/dumbbell） | `table` | 两端都要标数值 |
| 双维分布 / 优先级 | `bar`（scatter/bubble） | `matrix` | 气泡半径 ∝ √值 |
| 分布 / 离散度 | `boxplot` | `bar`（dotplot） | 组数 ≤8；箱线四件齐备；**boxplot 还原度 low，PPTX 改 dotplot** |
| 增减归因（A→B） | `bar`（waterfall） | `table` | 每段标变化量 + 合计收口 |
| 转化 / 筛选漏斗 | `bar`（funnel） | `sankey` | 层数 ≤5；**sankey 还原度 low，PPTX 改 table** |
| 计划排期（并行） | `bar`（gantt） | `timeline` | 里程碑叙事用 `timeline`，勿混 |
| 里程碑 / 路线叙事 | `timeline` | `steps` | 3–5 个，每个 ≤2 行 |
| 步骤 / 实施节奏 | `steps` | `timeline` | 3–6 步；高亮步 ≤2 处 |
| 二维强度对标 | `heatmap` | `matrix` | 行列 ≤5×5；只用强调色明度阶梯 |
| 定位 / 优先级 / 象限 | `matrix` | `bar`（scatter） | ≤3×3 |
| 层级递进 / 价值阶梯 | `pyramid` | `diagram` | 3–5 层；强调层 ≤1 |
| 关键判断 / 金句休止 | `quote` | `points` | 全文 1–2 处，多了廉价 |
| 完整论述（发现→证据→含义） | `twocol`（research R1） | `threecol` | 段 ≤200 字；标题必须结论句 |
| 数据证据页（主力） | `exhibit`（R2） | `split` | 全篇 Exhibit 连续编号 |
| 三栏并列论点 | `threecol`（R6） | `cards` | 每栏 ≤150 字；栏宽按版心全宽推导 |
| 系统分层架构 | `diagram` | `bar`（chart.type=network） | 节点 ≤24；层 ≤4；**network 还原度 low** |
| 流程 / 职责协作 | `lane` | `diagram` | 每行 ≤6 步；正交折线优先 |
| 素材图片（实拍/截图） | `image` | `split` | 六版式；无图用 `image.placeholder` |
| 待核实项收口 | `flags` 字段 | `table` | 标色必须配说明 |
| 大纲 / 议程 | `agenda`（结构页） | — | ≤8 条单列；>8 双列；>12 自动分页；标题 ≤36 字 |

> **容量契约**（超限请拆页/换形态，禁静默截断）：agenda ≤16 条（`splitMax`）、单条标题 ≤36 字（`titleMaxChars`）；metrics ≤6/行、值 ≤6 字；diagram ≤3 层 × 每层 ≤3 节点、层名 ≤7 字、注解 ≤10 字；timeline ≤5 段、每段说明 ≤22 字；comparison `verdict`/`soWhat` 二选一；threecol/twocol 每栏 ≥120 字、段数 <4 时用三栏；表格单元格 ≤14 字、行 ≤8（research ≤16）。
> **PPTX 还原度**（`charts.fidelityMap`）：`high` = bar/hbar/line/donut/stack/waterfall/gauge/pareto/progress 等；`low` = area/radar/treemap/sankey/streamgraph/marimekko/boxplot/network——PPTX 会退化，优先改 high 图型或 `dataTable=inline`。完整分级见 `chart-decision-tree.md`。
