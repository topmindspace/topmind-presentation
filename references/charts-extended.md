# 图表全库 · charts-extended.md

> 由 `charts.md` 拆出（§编号保持不变，跨文件稳定引用）。
> 取码：`python scripts/extract_snippet.py --file charts.md --section <编号>`
> 或直接 `--file charts-extended.md --section <编号>`。整读大文件视为违规。

## 52. 双折线 / 面积图 `data-chart="dualline"` · `data-chart="area"`

```html
<!-- 双折线：两条线对比（不引入第二色相：accent 实线 + text-3 虚线） -->
<svg class="chart" data-chart="dualline" viewBox="0 0 560 200">
  <line x1="40" y1="160" x2="540" y2="160" class="s-bds" stroke-width="1"/>
  <path data-draw d="M60,130 L180,104 L300,78 L420,58 L520,44" class="f-none s-acc"
        stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  <path data-draw d="M60,146 L180,132 L300,116 L420,98 L520,80" class="f-none s-txt3"
        stroke-width="2" stroke-dasharray="5 5" stroke-linecap="round"/>
  <text x="60" y="180" text-anchor="middle" class="f-txt3" font-size="11">2026Q3</text>
  <text x="300" y="180" text-anchor="middle" class="f-txt3" font-size="11">2027Q1</text>
  <text x="520" y="180" text-anchor="middle" class="f-txt3" font-size="11">2027Q3</text>
</svg>
```

```html
<!-- 面积图：强调累计量级（面积用 accent 低透明度，线用 accent） -->
<svg class="chart" data-chart="area" viewBox="0 0 560 200">
  <line x1="40" y1="160" x2="540" y2="160" class="s-bds" stroke-width="1"/>
  <path d="M60,132 L180,108 L300,80 L420,60 L520,46 L520,160 L60,160 Z"
        class="f-acc" fill-opacity=".12"/>
  <path data-draw d="M60,132 L180,108 L300,80 L420,60 L520,46" class="f-none s-acc"
        stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
```

**规则**：双系列时第二条走 `s-txt3` 虚线（或 spectrum 下 `s-c2`）；数据点标在线上（`<circle>`），坐标轴只做尺度参考；PPTX 用 `chart.type:'dualline'/'area'`（原生 line/area 图表，`series` 传多系列）。

---

## 53. 气泡图（双维分布 + 第三维权重）`data-chart="bubble"`

```html
<svg class="chart" data-chart="bubble" viewBox="0 0 560 220">
  <line x1="40" y1="180" x2="540" y2="180" class="s-bds" stroke-width="1"/>
  <line x1="40" y1="180" x2="40" y2="20" class="s-bds" stroke-width="1"/>
  <circle cx="140" cy="120" r="16" class="f-acc" fill-opacity=".75"/>
  <circle cx="240" cy="86"  r="26" class="f-acc" fill-opacity=".75"/>
  <circle cx="360" cy="130" r="12" class="f-accs2"/>
  <circle cx="460" cy="60"  r="20" class="f-s2"/>
  <text x="240" y="90" text-anchor="middle" class="t-on-inv" font-size="11">研发</text>
</svg>
```

**规则**：气泡半径 ∝ 第三维（面积按半径平方，勿直接线性映射半径）；≤8 个气泡；轴标签写清量纲；关键气泡标名称。

---

## 54. 进度条组（多项目完成度）`data-chart="progress"`

```html
<svg class="chart" data-chart="progress" viewBox="0 0 560 150">
  <text x="0" y="18" class="f-txt2" font-size="12">指标中心</text>
  <rect x="96" y="8" width="400" height="12" rx="6" class="f-s2"/>
  <rect x="96" y="8" width="332" height="12" rx="6" class="f-acc"/>
  <text x="508" y="19" class="f-txt" font-size="12" font-weight="600">83%</text>
  <text x="0" y="52" class="f-txt2" font-size="12">数据契约</text>
  <rect x="96" y="42" width="400" height="12" rx="6" class="f-s2"/>
  <rect x="96" y="42" width="216" height="12" rx="6" class="f-acc"/>
  <text x="508" y="53" class="f-txt" font-size="12" font-weight="600">54%</text>
</svg>
```

**规则**：行高 28–34px；数值标条末右对齐；≤6 行；需要"目标线"时改用 bullet（`components.md` §49）。PPTX 映射为 `bullet` 页型。

---

## 55. 迷你趋势线（KPI 内嵌）`data-chart="sparkline"`

```html
<div class="metric">
  <div class="metric__v t-metric">61<small>%</small></div>
  <div class="metric__k">试点率</div>
  <svg class="chart" data-chart="sparkline" viewBox="0 0 120 28" style="width:120px">
    <path d="M2,22 L24,18 L46,20 L68,12 L90,9 L118,4" class="f-none s-acc"
          stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="118" cy="4" r="2.6" class="f-acc"/>
  </svg>
</div>
```

**规则**：只用于指标卡内（不与大图并存）；无坐标轴、无网格；末点必须标圆点；高度 20–30。

---

---

## 57. 斜率图 `data-chart="slope"`

**用途**：两期排名/份额对比——**谁升谁降一目了然**（比双柱更直观）。**系列 ≤6 条**。

```html
<div class="fig">
  <div class="fig__cap">各域试点率：一年之间谁升谁降</div>
  <svg class="chart" data-chart="slope" viewBox="0 0 560 200">
    <!-- 两期轴 -->
    <line x1="90" y1="26" x2="90" y2="176" class="s-bds" stroke-width="1"/>
    <line x1="470" y1="26" x2="470" y2="176" class="s-bds" stroke-width="1"/>
    <text x="90" y="16" text-anchor="middle" class="f-txt3" font-size="11">2025</text>
    <text x="470" y="16" text-anchor="middle" class="f-txt3" font-size="11">2026</text>
    <!-- 4 条斜率线：强调最大涨幅（研发），其余中性 -->
    <path d="M90,52 L470,75" class="f-none s-txt3" stroke-width="2"/>
    <path d="M90,94 L470,83" class="f-none s-txt3" stroke-width="2"/>
    <path d="M90,120 L470,100" class="f-none s-txt3" stroke-width="2"/>
    <path d="M90,148 L470,92" class="f-none s-acc" stroke-width="2.5"/>
    <circle cx="90" cy="52" r="4" class="f-txt3"/><circle cx="470" cy="75" r="4" class="f-txt3"/>
    <circle cx="90" cy="94" r="4" class="f-txt3"/><circle cx="470" cy="83" r="4" class="f-txt3"/>
    <circle cx="90" cy="120" r="4" class="f-txt3"/><circle cx="470" cy="100" r="4" class="f-txt3"/>
    <circle cx="90" cy="148" r="5" class="f-acc"/><circle cx="470" cy="92" r="5" class="f-acc"/>
    <!-- 端点数值（左：end 锚点 / 右：start 锚点） -->
    <text x="78" y="56" text-anchor="end" class="f-txt3" font-size="11">客服 72%</text>
    <text x="78" y="98" text-anchor="end" class="f-txt3" font-size="11">财务 57%</text>
    <text x="78" y="124" text-anchor="end" class="f-txt3" font-size="11">营销 48%</text>
    <text x="78" y="152" text-anchor="end" class="f-txt" font-size="11" font-weight="600">研发 38%</text>
    <text x="482" y="79" class="f-txt3" font-size="11">64%</text>
    <text x="482" y="87" class="f-txt3" font-size="11">61%</text>
    <text x="482" y="104" class="f-txt3" font-size="11">55%</text>
    <text x="482" y="96" class="f-acc" font-size="11" font-weight="600">58%</text>
  </svg>
</div>
```

**规则**：**只两条轴**（两期），不画网格；强调色只给"最值得说的那 1–2 条"；标签必须两端都标（读者要能读出升降幅度）。

---

---

## 58. 哑铃图 `data-chart="dumbbell"`

**用途**：同一指标的前后/两地对比（每行两点一线）。**行数 ≤6**。

```html
<div class="fig">
  <div class="fig__cap">试点率 vs 规模化率：缺口即空间</div>
  <svg class="chart" data-chart="dumbbell" viewBox="0 0 560 180">
    <!-- 行：标签 + 底槽 + 连线 + 双点 + 数值 -->
    <text x="0" y="34" class="f-txt2" font-size="12">客服</text>
    <line x1="323" y1="30" x2="405" y2="30" class="s-txt3" stroke-width="2"/>
    <circle cx="323" cy="30" r="6" class="f-s3"/>
    <circle cx="405" cy="30" r="6" class="f-acc"/>
    <text x="538" y="34" text-anchor="end" class="f-txt" font-size="11" font-weight="600">52 → 72%</text>

    <text x="0" y="72" class="f-txt2" font-size="12">财务</text>
    <line x1="299" y1="68" x2="344" y2="68" class="s-txt3" stroke-width="2"/>
    <circle cx="299" cy="68" r="6" class="f-s3"/>
    <circle cx="344" cy="68" r="6" class="f-acc"/>
    <text x="538" y="72" text-anchor="end" class="f-txt" font-size="11" font-weight="600">46 → 57%</text>

    <text x="0" y="110" class="f-txt2" font-size="12">营销</text>
    <line x1="278" y1="106" x2="307" y2="106" class="s-txt3" stroke-width="2"/>
    <circle cx="278" cy="106" r="6" class="f-s3"/>
    <circle cx="307" cy="106" r="6" class="f-acc"/>
    <text x="538" y="110" text-anchor="end" class="f-txt" font-size="11" font-weight="600">41 → 48%</text>

    <text x="0" y="148" class="f-txt2" font-size="12">研发</text>
    <line x1="266" y1="144" x2="348" y2="144" class="s-acc" stroke-width="2.5"/>
    <circle cx="266" cy="144" r="6" class="f-s3"/>
    <circle cx="348" cy="144" r="6" class="f-acc"/>
    <text x="538" y="148" text-anchor="end" class="f-acc" font-size="11" font-weight="600">38 → 58%</text>
  </svg>
</div>
```

**规则**：起止点同一量纲（左右可标差值）；**差距最大的一行用强调色连线**，其余中性；行高 34–38px。

---

---

## 59. 棒棒糖图 `data-chart="lollipop"`

**用途**：排名 + 量值，比横向条形更轻（适合 5–8 项）。**行数 ≤8**。

```html
<div class="fig">
  <div class="fig__cap">各域数据消费占比</div>
  <svg class="chart" data-chart="lollipop" viewBox="0 0 560 160">
    <line x1="100" y1="10" x2="100" y2="150" class="s-bds" stroke-width="1"/>
    <text x="0" y="26" class="f-txt2" font-size="12">供应链</text>
    <line x1="100" y1="22" x2="404" y2="22" class="s-acc" stroke-width="2"/>
    <circle cx="404" cy="22" r="5" class="f-acc"/>
    <text x="416" y="26" class="f-txt" font-size="11" font-weight="600">76%</text>
    <text x="0" y="54" class="f-txt2" font-size="12">客服</text>
    <line x1="100" y1="50" x2="388" y2="50" class="s-acc" stroke-width="2"/>
    <circle cx="388" cy="50" r="5" class="f-acc"/>
    <text x="400" y="54" class="f-txt" font-size="11" font-weight="600">72%</text>
    <text x="0" y="82" class="f-txt2" font-size="12">财务</text>
    <line x1="100" y1="78" x2="328" y2="78" class="s-txt3" stroke-width="2"/>
    <circle cx="328" cy="78" r="5" class="f-s3"/>
    <text x="340" y="82" class="f-txt2" font-size="11">57%</text>
    <text x="0" y="110" class="f-txt2" font-size="12">营销</text>
    <line x1="100" y1="106" x2="292" y2="106" class="s-txt3" stroke-width="2"/>
    <circle cx="292" cy="106" r="5" class="f-s3"/>
    <text x="304" y="110" class="f-txt2" font-size="11">48%</text>
    <text x="0" y="138" class="f-txt2" font-size="12">研发</text>
    <line x1="100" y1="134" x2="252" y2="134" class="s-txt3" stroke-width="2"/>
    <circle cx="252" cy="134" r="5" class="f-s3"/>
    <text x="264" y="138" class="f-txt2" font-size="11">38%</text>
  </svg>
</div>
```

**规则**：按值降序排列；**强调色只给 Top 1–2 项**；行高 28–32px；数值标在点右侧。

---

---

## 61. 玫瑰图 `data-chart="rose"`

**用途**：周期性 / 多维强度（极坐标雷达的"面积版"，比雷达更强调单维突出）。**维度 ≤6**。

```html
<div class="fig" style="text-align:center">
  <div class="fig__cap">六维就绪度（半径 ∝ 得分）</div>
  <svg class="chart" data-chart="rose" viewBox="0 0 200 200" style="width:200px;margin-inline:auto">
    <!-- 中心 100,100；6 个 60° 扇区，半径 88/66/78/52/70/44 -->
    <path d="M100,100 L100,12 A88,88 0 0 1 176.2,56 Z" class="f-acc"/>
    <path d="M100,100 L157.2,67 A66,66 0 0 1 157.2,133 Z" class="f-acc" fill-opacity=".75"/>
    <path d="M100,100 L167.5,139 A78,78 0 0 1 100,178 Z" class="f-acc" fill-opacity=".55"/>
    <path d="M100,100 L100,152 A52,52 0 0 1 55,126 Z" class="f-s3"/>
    <path d="M100,100 L39.4,135 A70,70 0 0 1 39.4,65 Z" class="f-s3"/>
    <path d="M100,100 L61.9,78 A44,44 0 0 1 100,56 Z" class="f-s2"/>
    <circle cx="100" cy="100" r="2.5" class="f-txt3"/>
    <text x="100" y="8" text-anchor="middle" class="f-txt2" font-size="10">语义</text>
    <text x="186" y="54" text-anchor="middle" class="f-txt2" font-size="10">服务</text>
    <text x="178" y="150" text-anchor="middle" class="f-txt2" font-size="10">消费</text>
    <text x="100" y="196" text-anchor="middle" class="f-txt2" font-size="10">底座</text>
    <text x="14" y="150" text-anchor="middle" class="f-txt2" font-size="10">安全</text>
    <text x="22" y="54" text-anchor="middle" class="f-txt2" font-size="10">契约</text>
  </svg>
</div>
```

**规则**：扇区角度均分、半径按值映射（**面积 ∝ 值的平方，勿线性映射半径**）；显示直径 ≥180px；中心留白放维度总数；扇区色走 accent 明度阶梯。

---

---

## 62. 点图 `data-chart="dotplot"`

**用途**：分布 / 离散程度（每个对象多个观测点，看分散与聚集）。**行 ≤6、每行点 ≤5**。

```html
<div class="fig">
  <div class="fig__cap">各域试点率分布（三年观测）</div>
  <svg class="chart" data-chart="dotplot" viewBox="0 0 560 150">
    <!-- 轴：0 / 50 / 100 -->
    <line x1="100" y1="16" x2="100" y2="134" class="s-bds" stroke-width="1"/>
    <line x1="310" y1="16" x2="310" y2="134" class="s-bds" stroke-width="1" stroke-dasharray="3 4"/>
    <line x1="520" y1="16" x2="520" y2="134" class="s-bds" stroke-width="1"/>
    <text x="100" y="146" text-anchor="middle" class="f-txt3" font-size="10">0</text>
    <text x="310" y="146" text-anchor="middle" class="f-txt3" font-size="10">50</text>
    <text x="520" y="146" text-anchor="middle" class="f-txt3" font-size="10">100%</text>
    <!-- 行：标签 + 观测点 -->
    <text x="0" y="34" class="f-txt2" font-size="12">客服</text>
    <circle cx="184" cy="30" r="5" class="f-s3"/><circle cx="247" cy="30" r="5" class="f-s3"/>
    <circle cx="302" cy="30" r="5" class="f-acc"/>
    <text x="0" y="62" class="f-txt2" font-size="12">财务</text>
    <circle cx="289" cy="58" r="5" class="f-s3"/><circle cx="344" cy="58" r="5" class="f-s3"/>
    <circle cx="377" cy="58" r="5" class="f-acc"/>
    <text x="0" y="90" class="f-txt2" font-size="12">营销</text>
    <circle cx="360" cy="86" r="5" class="f-s3"/><circle cx="398" cy="86" r="5" class="f-s3"/>
    <circle cx="428" cy="86" r="5" class="f-acc"/>
    <text x="0" y="118" class="f-txt2" font-size="12">研发</text>
    <circle cx="226" cy="114" r="5" class="f-s3"/><circle cx="285" cy="114" r="5" class="f-s3"/>
    <circle cx="318" cy="114" r="5" class="f-acc"/>
  </svg>
</div>
```

**规则**：**点重叠时轻微错位**（jitter ≤3px）或用空心圈表示重复；最新一期用强调色点，历史期用中性；行高 28px。

---

---

## 63. 子弹图 `data-chart="bulletchart"`

**用途**：目标 vs 实际 + **定性区间背景**（差/中/优三档），比 bullet 页型多一层"区间参照"。**行数 ≤6**。

```html
<div class="fig">
  <div class="fig__cap">四项能力：实际条 vs 目标刻度（背景为三档区间）</div>
  <svg class="chart" data-chart="bulletchart" viewBox="0 0 560 160">
    <!-- 行 1：背景三档（0-60 / 60-85 / 85-100）+ 实际条 + 目标线 -->
    <text x="0" y="34" class="f-txt2" font-size="12">场景覆盖</text>
    <rect x="100" y="23" width="252" height="14" class="f-s1"/>
    <rect x="352" y="23" width="105" height="14" class="f-s2"/>
    <rect x="457" y="23" width="63" height="14" class="f-s3"/>
    <rect x="100" y="23" width="256" height="14" class="f-acc"/>
    <line x1="436" y1="18" x2="436" y2="42" class="s-txt3" stroke-width="2.5"/>
    <text x="538" y="34" text-anchor="end" class="f-txt" font-size="11" font-weight="600">61 / 80%</text>

    <text x="0" y="68" class="f-txt2" font-size="12">治理就绪</text>
    <rect x="100" y="57" width="252" height="14" class="f-s1"/>
    <rect x="352" y="57" width="105" height="14" class="f-s2"/>
    <rect x="457" y="57" width="63" height="14" class="f-s3"/>
    <rect x="100" y="57" width="143" height="14" class="f-acc" fill-opacity=".75"/>
    <line x1="415" y1="52" x2="415" y2="76" class="s-txt3" stroke-width="2.5"/>
    <text x="538" y="68" text-anchor="end" class="f-txt" font-size="11" font-weight="600">34 / 75%</text>

    <text x="0" y="102" class="f-txt2" font-size="12">工具集成</text>
    <rect x="100" y="91" width="252" height="14" class="f-s1"/>
    <rect x="352" y="91" width="105" height="14" class="f-s2"/>
    <rect x="457" y="91" width="63" height="14" class="f-s3"/>
    <rect x="100" y="91" width="176" height="14" class="f-acc" fill-opacity=".75"/>
    <line x1="394" y1="86" x2="394" y2="110" class="s-txt3" stroke-width="2.5"/>
    <text x="538" y="102" text-anchor="end" class="f-txt" font-size="11" font-weight="600">42 / 70%</text>

    <text x="0" y="136" class="f-txt2" font-size="12">规模化运行</text>
    <rect x="100" y="125" width="252" height="14" class="f-s1"/>
    <rect x="352" y="125" width="105" height="14" class="f-s2"/>
    <rect x="457" y="125" width="63" height="14" class="f-s3"/>
    <rect x="100" y="125" width="76" height="14" class="f-s3"/>
    <line x1="352" y1="120" x2="352" y2="144" class="s-txt3" stroke-width="2.5"/>
    <text x="538" y="136" text-anchor="end" class="f-txt3" font-size="11" font-weight="600">18 / 60%</text>
  </svg>
</div>
```

**规则**：三档区间用 `f-s1/f-s2/f-s3`（中性明度差，**不引入红绿**）；实际条压区间之上；目标线为竖线；未达标行实际条转中性色（`f-s3`）；数值统一"实际 / 目标"。

---

---

## 65. 华夫图（构成占比 · 每格 1%）`data-chart="waffle"`

**用途**：把百分比画成 10×10 点阵——**每格 = 1%**，比饼图更易比较"差几格"。适合"覆盖率 / 达成率 / 构成占比"这类单一比例叙事。**类别 ≤3 组**（多组改用 marimekko / treemap）。

```html
<div class="fig">
  <div class="fig__cap">可信数据覆盖率 46%（每格 = 1%）</div>
  <svg class="chart" data-chart="waffle" viewBox="0 0 560 190">
    <g transform="translate(16,16)">
      <path class="f-s1"  d="M144 108h15v15h-15z M162 108h15v15h-15z M0 126h15v15h-15z M18 126h15v15h-15z M36 126h15v15h-15z M54 126h15v15h-15z M72 126h15v15h-15z M90 126h15v15h-15z M108 126h15v15h-15z M126 126h15v15h-15z M144 126h15v15h-15z M162 126h15v15h-15z M0 144h15v15h-15z M18 144h15v15h-15z M36 144h15v15h-15z M54 144h15v15h-15z M72 144h15v15h-15z M90 144h15v15h-15z M108 144h15v15h-15z M126 144h15v15h-15z M144 144h15v15h-15z M162 144h15v15h-15z M0 162h15v15h-15z M18 162h15v15h-15z M36 162h15v15h-15z M54 162h15v15h-15z M72 162h15v15h-15z M90 162h15v15h-15z M108 162h15v15h-15z M126 162h15v15h-15z M144 162h15v15h-15z M162 162h15v15h-15z"/>
      <path class="f-accs" d="M108 72h15v15h-15z M126 72h15v15h-15z M144 72h15v15h-15z M162 72h15v15h-15z M0 90h15v15h-15z M18 90h15v15h-15z M36 90h15v15h-15z M54 90h15v15h-15z M72 90h15v15h-15z M90 90h15v15h-15z M108 90h15v15h-15z M126 90h15v15h-15z M144 90h15v15h-15z M162 90h15v15h-15z M0 108h15v15h-15z M18 108h15v15h-15z M36 108h15v15h-15z M54 108h15v15h-15z M72 108h15v15h-15z M90 108h15v15h-15z M108 108h15v15h-15z M126 108h15v15h-15z"/>
      <path class="f-acc"  d="M0 0h15v15h-15z M18 0h15v15h-15z M36 0h15v15h-15z M54 0h15v15h-15z M72 0h15v15h-15z M90 0h15v15h-15z M108 0h15v15h-15z M126 0h15v15h-15z M144 0h15v15h-15z M162 0h15v15h-15z M0 18h15v15h-15z M18 18h15v15h-15z M36 18h15v15h-15z M54 18h15v15h-15z M72 18h15v15h-15z M90 18h15v15h-15z M108 18h15v15h-15z M126 18h15v15h-15z M144 18h15v15h-15z M162 18h15v15h-15z M0 36h15v15h-15z M18 36h15v15h-15z M36 36h15v15h-15z M54 36h15v15h-15z M72 36h15v15h-15z M90 36h15v15h-15z M108 36h15v15h-15z M126 36h15v15h-15z M144 36h15v15h-15z M162 36h15v15h-15z M0 54h15v15h-15z M18 54h15v15h-15z M36 54h15v15h-15z M54 54h15v15h-15z M72 54h15v15h-15z M90 54h15v15h-15z M108 54h15v15h-15z M126 54h15v15h-15z M144 54h15v15h-15z M162 54h15v15h-15z M0 72h15v15h-15z M18 72h15v15h-15z M36 72h15v15h-15z M54 72h15v15h-15z M72 72h15v15h-15z M90 72h15v15h-15z"/>
    </g>
    <g transform="translate(230,40)" font-size="13">
      <rect x="0" y="0" width="13" height="13" class="f-acc"/>
      <text x="22" y="12" class="f-txt" font-weight="600">46% 已覆盖</text>
      <rect x="0" y="30" width="13" height="13" class="f-accs"/>
      <text x="22" y="42" class="f-txt2">22% 建设中</text>
      <rect x="0" y="60" width="13" height="13" class="f-s1"/>
      <text x="22" y="72" class="f-txt2">32% 待启动</text>
      <text x="0" y="108" class="f-txt3" font-size="11">口径：纳入可信清单的数据集 / 全量数据集</text>
    </g>
  </svg>
</div>
```

**规则**：三组以内用 `f-acc / f-accs / f-s1`（同色相明度阶梯）；**格数必须严格等于百分比**（46% = 46 格）；点阵按行优先填色；不写死色值。

---

---

## 67. 帕累托图（主因排序 · 二八分析）`data-chart="pareto"`

**用途**：降序柱 + 累计占比折线 + **80% 参考线**——一眼看出"哪几项贡献了大部分"。**类别 ≤7**。

```html
<div class="fig">
  <div class="fig__cap">六类缺陷：前 3 类贡献 77% 的问题量</div>
  <svg class="chart" data-chart="pareto" viewBox="0 0 560 200">
    <line x1="72" y1="160" x2="500" y2="160" class="s-bd"/>
    <!-- 80% 参考线 -->
    <line x1="72" y1="56" x2="500" y2="56" class="s-txt3" stroke-width="1" stroke-dasharray="4 4"/>
    <text x="504" y="60" class="f-txt3" font-size="10">80%</text>
    <!-- 柱（降序） -->
    <rect x="72"  y="30"  width="56" height="130" class="f-acc"/>
    <rect x="138" y="78"  width="56" height="82"  class="f-acc" fill-opacity=".82"/>
    <rect x="204" y="109" width="56" height="51"  class="f-acc" fill-opacity=".68"/>
    <rect x="270" y="122" width="56" height="38"  class="f-s2"/>
    <rect x="336" y="136" width="56" height="24"  class="f-s2"/>
    <rect x="402" y="143" width="56" height="17"  class="f-s2"/>
    <!-- 累计占比折线 -->
    <polyline points="100,111 166,79 232,60 298,46 364,37 430,30" fill="none"
      class="s-acc" stroke-width="2.5"/>
    <g class="f-acc">
      <circle cx="100" cy="111" r="3.5"/><circle cx="166" cy="79" r="3.5"/>
      <circle cx="232" cy="60" r="3.5"/><circle cx="298" cy="46" r="3.5"/>
      <circle cx="364" cy="37" r="3.5"/><circle cx="430" cy="30" r="3.5"/>
    </g>
    <!-- 类别标签 -->
    <g class="f-txt2" font-size="10" text-anchor="middle">
      <text x="100" y="176">口径缺失</text><text x="166" y="176">字段空值</text>
      <text x="232" y="176">更新延迟</text><text x="298" y="176">重复入库</text>
      <text x="364" y="176">权限错配</text><text x="430" y="176">其他</text>
    </g>
  </svg>
</div>
```

**规则**：柱**必须降序**；累计线走 `s-acc` + `f-acc` 点；80% 线用虚线（`s-txt3`）；前 N 项（累计 ≤80%）用 accent，其余转 `f-s2`；数值标柱顶，不重复标左右轴。

---

---

## 68. 径向条形图（多指标达成率）`data-chart="radialbar"`

**用途**：多指标达成率画成**同心环**——比并排进度条更紧凑，适合"一屏四指标"。**环数 ≤5**。注意：需内联 `style="width:200px"` 以上（校验器按 `pxWidthMin` 核）。

```html
<div class="fig">
  <div class="fig__cap">四项能力成熟度（同心环，自外向内）</div>
  <svg class="chart" data-chart="radialbar" viewBox="0 0 240 240" style="width:240px">
    <g transform="rotate(-90 120 120)" fill="none" stroke-width="15">
      <circle cx="120" cy="120" r="100" class="s-bd" stroke-opacity=".45"/>
      <circle cx="120" cy="120" r="100" class="s-acc" stroke-linecap="round" stroke-dasharray="471 157"/>
      <circle cx="120" cy="120" r="80" class="s-bd" stroke-opacity=".45"/>
      <circle cx="120" cy="120" r="80" class="s-acc" stroke-linecap="round" stroke-opacity=".85" stroke-dasharray="302 201"/>
      <circle cx="120" cy="120" r="60" class="s-bd" stroke-opacity=".45"/>
      <circle cx="120" cy="120" r="60" class="s-acc" stroke-linecap="round" stroke-opacity=".7" stroke-dasharray="170 207"/>
      <circle cx="120" cy="120" r="40" class="s-bd" stroke-opacity=".45"/>
      <circle cx="120" cy="120" r="40" class="s-acc" stroke-linecap="round" stroke-opacity=".55" stroke-dasharray="75 176"/>
    </g>
    <text x="120" y="114" text-anchor="middle" class="f-txt" font-size="26" font-weight="700">75%</text>
    <text x="120" y="134" text-anchor="middle" class="f-txt3" font-size="11">平台成熟度</text>
  </svg>
</div>
```

**规则**：底环 `s-bd`（低透明）+ 进度环 `s-acc`（**明度阶梯区分，不引入多色相**）；`stroke-dasharray` = `周长×达成率` + 剩余（周长 = 2πr）；统一 `rotate(-90 圆心)` 从 12 点起画；中心放总量或首要指标。

---

---

## 70. K 线图（区间波动 · 开高低收）`data-chart="candlestick"`

**用途**：每个时间点的**开 / 高 / 低 / 收**——波动幅度与方向。适合"价格 / 评分 / 指标的区间波动"。**蜡烛 ≤12 根**。

```html
<div class="fig">
  <div class="fig__cap">八期评分波动（实体 = 开收，须 = 高低）</div>
  <svg class="chart" data-chart="candlestick" viewBox="0 0 560 200">
    <line x1="60" y1="180" x2="540" y2="180" class="s-bd"/>
    <!-- 上涨（收 > 开）= accent；下跌 = 中性 f-s3（不引入红绿） -->
    <g class="s-acc" stroke-width="1.5">
      <line x1="80" y1="103" x2="80" y2="161"/><line x1="200" y1="98" x2="200" y2="137"/>
      <line x1="260" y1="55" x2="260" y2="108"/><line x1="440" y1="70" x2="440" y2="103"/>
      <line x1="500" y1="41" x2="500" y2="79"/>
    </g>
    <g class="f-acc">
      <rect x="67" y="113" width="26" height="31"/><rect x="187" y="103" width="26" height="19"/>
      <rect x="247" y="65" width="26" height="38"/><rect x="427" y="74" width="26" height="14"/>
      <rect x="487" y="48" width="26" height="26"/>
    </g>
    <g class="s-txt3" stroke-width="1.5">
      <line x1="140" y1="84" x2="140" y2="127"/><line x1="320" y1="48" x2="320" y2="84"/>
      <line x1="380" y1="65" x2="380" y2="98"/>
    </g>
    <g class="f-s3">
      <rect x="127" y="113" width="26" height="10"/><rect x="307" y="65" width="26" height="12"/>
      <rect x="367" y="77" width="26" height="12"/>
    </g>
    <g class="f-txt3" font-size="10" text-anchor="middle">
      <text x="80" y="194">1</text><text x="140" y="194">2</text><text x="200" y="194">3</text>
      <text x="260" y="194">4</text><text x="320" y="194">5</text><text x="380" y="194">6</text>
      <text x="440" y="194">7</text><text x="500" y="194">8</text>
    </g>
  </svg>
</div>
```

**规则**：**不引入红绿**——上涨用 `f-acc` 实体 + `s-acc` 须，下跌用 `f-s3` 实体 + `s-txt3` 须；实体宽度一致、须为 1.5px 竖线；坐标轴只标时间序号，数值靠图注给区间。

---

