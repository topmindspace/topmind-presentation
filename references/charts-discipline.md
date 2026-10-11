# 图表全库 · charts-discipline.md

> 由 `charts.md` 拆出（§编号保持不变，跨文件稳定引用）。
> 取码：`python scripts/extract_snippet.py --file charts.md --section <编号>`
> 或直接 `--file charts-discipline.md --section <编号>`。整读大文件视为违规。

## 64. 图表与"大信息量"的合理性

> 数据量大不等于要一次画完。**图要能被 3 秒读懂**，超出承载就升级形态或拆页。

| 情形 | 处理 |
|------|------|
| 系列 > 5（构成类） | 合并为"其他"（用 `f-c5`/中性），或改 treemap / marimekko |
| 类别 > 8（排名类） | 取 Top 7 + "其余合并"行；全量放附录密表（同源同口径） |
| 时间点 > 8（趋势类） | 改面积/折线（点不标数值），或按季度聚合 |
| 二维 + 第三维 | 散点 → 气泡（半径 ∝ 第三维，面积平方映射） |
| 行数 > 6（bullet/dumbbell/lollipop/progress） | 拆页或改密表（research） |
| 极坐标维度 > 6 | 拆成两组雷达，或改热力矩阵（heatmap） |
| 需要"读数值" | 数值标在数据本体旁（条末/点侧/环内），不强迫查图例换算 |
| 需要"看结构" | 用色阶与位置，弱化数值（避免数字墙） |

**四条硬底线**（校验器会拦）：
1. 图表显示尺寸不得低于 `charts.minSize`（环形 ≥140px、雷达/玫瑰 ≥220/180px、柱折线 viewBox 高 ≥160）。
2. `data-chart` 类型必须在 `layout-constants.json` `charts.types` 登记。
3. 图表配色走 `.f-acc/.f-s*/.f-c*` 语义类——**不写死色值**，随主题/风格自动变色。
4. 一屏只一个视觉重心（图大就不要同时放巨号数字）。

---

---

## 66. 图表误用反例与多样性纪律（交付前自查）

> 登记 36 种 ≠ 用对。**选型决策层（分析意图 → 图型 → 禁用条件）见 `references/playbook.md` §五**；本节是落地自查与校验器口径。

### 66-1 七种最常见的误用（出现即改判）

| 误用 | 症状 | 改成 |
|------|------|------|
| 用 `bar` 表达占比 | 柱高加起来不是 100% | `donut` / `stackline` / `waffle` / `marimekko` |
| 用 `donut` 表达 8 个类别 | 扇区挤成碎片 | 合并为"其他"（≤5 段）或改 `treemap` |
| 用 `line` 表达类别对比（无时间轴） | x 轴是分类而非时间 | `hbar` / `lollipop` / `pareto` |
| 用 `table` 表达趋势 | 读者要自己在数字里找方向 | `line` / `area` / `slope` |
| 用均值型图表达分布 | 均值掩盖离散度 | `boxplot` / `dotplot` |
| 同页放两张同型图 | 两个视觉重心互相打架 | 改 `split` / `halftable` 并让两图**编码不同维度** |
| 多系列图用单色明度阶梯 | 三条线分不清谁是谁 | `f-c1~c5` / `s-c1~c5` 编码色板（见 `design-system.md` §9b） |

### 66-2 多样性纪律（校验器硬拦 · 参数单源 `layout-constants.json` `charts.variety`）

> **preferCoreFirst**：优先用核图 8 拉开多样性；`charts-extended` / advanced **意图命中才加载**。advanced 一旦使用即计入类型数下限（不罚）；**禁止**为过 `minTypes` 硬上冷门图。

1. **类型数下限**：全篇不同 `data-chart` 类型数 ≥ `min(minTypes[mode], ⌈图表页数 × 0.6⌉)`（research 上限 6 / presentation 4 / architecture 3）。
2. **不连续同型**：相邻图表页不得使用同一 `data-chart` 类型——读者视角就是"又一张一样的图"。
3. **组合版式比例**（research）：含 ≥2 种承载类型（图表 / 表格 / 卡片 / 指标 / 图片 / 结构图）的内容页 ≥ **30%**——单件页是例外不是默认。组合方式见 `components.md` §46c 与 `references/playbook.md` §四。
4. **一屏一个视觉重心**：主件明显大于从件；两个并列大件必须拆页或走 `split` 明确左右分工。

### 66-3 编码色 ≠ 状态色（别混用）

- **分类**（哪个系列 / 哪个域 / 哪个渠道）→ `f-c1~c5` / `s-c1~c5`：9 套风格各有自己的 5 色板，随主题自动切换。
- **状态 / 评价**（好 vs 坏、达标 vs 未达标、涨 vs 跌）→ **只用强调色明度阶梯 + 中性色**，**不得用红绿**（`heatmap` / `bullet` / `bulletchart` / `candlestick` 的既有规则不变）。
- 两者不可互换：用红绿表达"哪个域"会让读者误读为"好坏"；用色阶表达"达标与否"会让读者分不清类别。

### 66-4 误用 → 改判对照代码（三组高频案例）

**① 占比用了 `bar`（柱高相加无意义）→ 改 `donut`**

```html
<!-- ✗ 误用：构成数据画成独立柱，读者无法感知"份额" -->
<svg class="chart" data-chart="bar" viewBox="0 0 480 190">
  <rect x="40"  y="30"  width="60" height="120" class="f-c1"/>   <!-- 工具 42% -->
  <rect x="160" y="69"  width="60" height="81"  class="f-c2"/>   <!-- 资讯 31% -->
  <rect x="280" y="107" width="60" height="43"  class="f-c3"/>   <!-- 社交 27% -->
</svg>

<!-- ✓ 改判：donut，扇区 ≤5，数值标环心，口径写来源行（完整代码 --chart donut） -->
<svg class="chart" data-chart="donut" viewBox="0 0 150 150" style="width:190px;margin-inline:auto">
  <circle cx="75" cy="75" r="54" class="f-none s-bds" stroke-width="15"/>
  <circle data-sweep data-circ="339.3" data-p="0.42" cx="75" cy="75" r="54" class="f-none s-acc"
          stroke-width="15" stroke-dasharray="142.5 196.8" transform="rotate(-90 75 75)"/>
  <text x="75" y="73" text-anchor="middle" class="f-txt" font-size="24">42%</text>
  <text x="75" y="93" text-anchor="middle" class="f-txt3" font-size="11">工具类</text>
</svg>
```

**② `donut` 硬塞 8 个类别（最小扇区 <8%）→ 合并"其他"或改 `treemap`**

```html
<!-- ✗ 误用：8 段扇区，4 段 <8% 挤成碎片，图例比图还大 -->
<!-- ✓ 改判：保留 Top 4，其余并入"其他"（f-c5/中性）；叶 >16 才升级 treemap -->
```
> 执行：`data-p` 取 0.42/0.31/0.14/0.08/0.05（其他），扇区 5 段封顶；"其他"明细沉附录密表（同源同口径）。

**③ `line` 表达类别对比（x 轴不是时间）→ 改 `hbar`**

```html
<!-- ✗ 误用：x 轴是部门名，折线暗示了不存在的时序连续性 -->
<svg class="chart" data-chart="line" viewBox="0 0 480 190">
  <polyline points="40,120 160,60 280,90 400,40" class="s-acc" fill="none"/>
  <text x="40" y="180" class="f-txt3">研发</text>  <!-- 分类被当成了时间 -->
</svg>

<!-- ✓ 改判：hbar——排名类比较，类别名在左、数值标条末（完整代码 --chart hbar） -->
<svg class="chart" data-chart="hbar" viewBox="0 0 520 210">
  <rect x="90" y="20"  width="360" height="26" class="f-acc"/>  <!-- 研发 849 -->
  <rect x="90" y="70"  width="330" height="26" class="f-c2"/>   <!-- 供应 834 -->
</svg>
```

---

