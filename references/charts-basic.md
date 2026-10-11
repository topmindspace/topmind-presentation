# 图表全库 · charts-basic.md

> 由 `charts.md` 拆出（§编号保持不变，跨文件稳定引用）。
> 取码：`python scripts/extract_snippet.py --file charts.md --section <编号>`
> 或直接 `--file charts-basic.md --section <编号>`。整读大文件视为违规。

## 16. 环形图（占比）`data-chart="donut"`

```html
<div class="fig" style="text-align:center">
  <div class="fig__cap">图表标题</div>
  <svg class="chart" data-chart="donut" viewBox="0 0 140 140" style="width:150px;margin-inline:auto">
    <circle cx="70" cy="70" r="54" class="f-none s-bds" stroke-width="15"/>
    <circle data-sweep data-circ="339.3" data-p="0.31" cx="70" cy="70" r="54" class="f-none s-acc"
            stroke-width="15" stroke-dasharray="105.3 234" stroke-linecap="round"
            transform="rotate(-90 70 70)"><title>使用率 31%</title></circle>
    <text x="70" y="68" text-anchor="middle" class="f-txt" font-size="24" font-weight="600"
          data-count="31" data-suffix="%">31%</text>
    <text x="70" y="88" text-anchor="middle" class="f-txt3" font-size="11">使用率</text>
  </svg>
  <div class="row" style="justify-content:center;gap:var(--sp-4);margin-top:var(--sp-4)">
    <span class="chip chip--accent">已使用 31%</span>
    <span class="chip">未使用 69%</span>
  </div>
</div>
```

周长 `= 2π × 54 ≈ 339.3`；`31% → 105.3`，`69% → 234`。
公式：`dasharray="{周长×p} {周长×(1-p)}"`。

**饼图变体**（`data-chart="pie"`）：去掉背景挖孔圆（`.f-none.s-bds` 那一圈），弧段半径铺满即可；中心不再放合计数字，改由右侧图例承担——其余同构，配色仍走语义类。

---

---

## 17. 横向条形图（排名 / 对比）`data-chart="hbar"`

```html
<div class="fig">
  <div class="fig__cap">各域覆盖率</div>
  <svg class="chart" data-chart="hbar" viewBox="0 0 520 150">
    <!-- 每行：标签 + 底槽 + 实条 + 数值；行高 30 -->
    <text x="0" y="18" class="f-txt2" font-size="12">供应链</text>
    <rect x="80" y="7" width="360" height="15" rx="7.5" class="f-s2"/>
    <rect x="80" y="7" width="274" height="15" rx="7.5" class="f-acc"><title>供应链 76%</title></rect>
    <text x="450" y="19" text-anchor="end" class="f-txt" font-size="12" font-weight="600">76%</text>

    <text x="0" y="48" class="f-txt2" font-size="12">财务</text>
    <rect x="80" y="37" width="360" height="15" rx="7.5" class="f-s2"/>
    <rect x="80" y="37" width="205" height="15" rx="7.5" class="f-acc"/>
    <text x="450" y="49" text-anchor="end" class="f-txt" font-size="12" font-weight="600">57%</text>

    <text x="0" y="78" class="f-txt2" font-size="12">研发</text>
    <rect x="80" y="67" width="360" height="15" rx="7.5" class="f-s2"/>
    <rect x="80" y="67" width="126" height="15" rx="7.5" class="f-acc"/>
    <text x="450" y="79" text-anchor="end" class="f-txt" font-size="12" font-weight="600">35%</text>
  </svg>
</div>
```

条宽 `= 槽宽 × p`。

---

---

## 18. 分组柱状图（阶段目标）`data-chart="bar"`

```html
<div class="fig">
  <div class="fig__cap">分阶段目标</div>
  <svg class="chart" data-chart="bar" viewBox="0 0 560 220">
    <line x1="46" y1="170" x2="540" y2="170" class="s-bds" stroke-width="1"/>
    <!-- 柱高 = 值/100 × 130；y = 170 - 柱高 -->
    <rect data-anim="grow" x="60"  y="131" width="58" height="39"  rx="6" class="f-s3"/>
    <rect data-anim="grow" x="188" y="92"  width="58" height="78"  rx="6" class="f-s3"/>
    <rect data-anim="grow" x="316" y="60"  width="58" height="110" rx="6" class="f-acc"/>
    <rect data-anim="grow" x="444" y="53"  width="58" height="117" rx="6" class="f-acc"/>
    <text data-anim="fade" x="89"  y="152" text-anchor="middle" class="t-on-inv" font-size="13" font-weight="600">30%</text>
    <text data-anim="fade" x="89"  y="192" text-anchor="middle" class="f-txt3" font-size="11">2026Q3</text>
  </svg>
</div>
```

---

---

## 19. 堆叠柱状图（构成随阶段变化）`data-chart="stack"`

```html
<div class="fig">
  <div class="fig__cap">数据消费构成（按季度）</div>
  <svg class="chart" data-chart="stack" viewBox="0 0 560 220">
    <line x1="40" y1="180" x2="540" y2="180" class="s-bds" stroke-width="1"/>
    <!-- 每柱两段堆叠：下段 f-s3，上段 f-acc；总高 = 值/100*140 -->
    <g>
      <rect data-anim="grow" x="90"  y="120" width="60" height="60" rx="4" class="f-s3"/>
      <rect data-anim="grow" x="90"  y="96"  width="60" height="24" rx="4" class="f-acc"/>
      <text x="120" y="196" text-anchor="middle" class="f-txt3" font-size="11">Q3</text>
    </g>
    <g>
      <rect data-anim="grow" x="250" y="100" width="60" height="80" rx="4" class="f-s3"/>
      <rect data-anim="grow" x="250" y="66"  width="60" height="34" rx="4" class="f-acc"/>
      <text x="280" y="196" text-anchor="middle" class="f-txt3" font-size="11">Q4</text>
    </g>
    <!-- 图例 -->
    <rect x="90" y="10" width="10" height="10" rx="2" class="f-acc"/><text x="104" y="19" class="f-txt3" font-size="11">服务层消费</text>
    <rect x="190" y="10" width="10" height="10" rx="2" class="f-s3"/><text x="204" y="19" class="f-txt3" font-size="11">直连/其他</text>
  </svg>
</div>
```

---

---

## 20. 100% 堆叠条（构成占比）`data-chart="stackline"`

```html
<div class="fig">
  <div class="fig__cap">数据消费构成</div>
  <svg class="chart" data-chart="stackline" viewBox="0 0 560 60">
    <!-- 三段拼满 520 宽，占比 45/35/20 -->
    <rect x="20" y="18" width="234" height="24" rx="6" class="f-acc"/>
    <rect x="254" y="18" width="182" height="24" class="f-s3"/>
    <rect x="436" y="18" width="104" height="24" rx="6" class="f-s2"/>
    <text x="137" y="34" text-anchor="middle" class="t-on-inv" font-size="12" font-weight="600">服务层 45%</text>
    <text x="345" y="34" text-anchor="middle" class="f-txt" font-size="12">直连 35%</text>
    <text x="488" y="34" text-anchor="middle" class="f-txt2" font-size="12">其他 20%</text>
  </svg>
</div>
```

---

---

## 21. 折线 / 面积图（时间趋势）`data-chart="line"`

```html
<div class="fig">
  <div class="fig__cap">可信数据消费率趋势</div>
  <svg class="chart" data-chart="line" viewBox="0 0 560 220">
    <!-- 网格线 -->
    <line x1="46" y1="180" x2="540" y2="180" class="s-bds" stroke-width="1"/>
    <line x1="46" y1="130" x2="540" y2="130" class="s-bds" stroke-width="1" stroke-dasharray="3 5"/>
    <line x1="46" y1="80"  x2="540" y2="80"  class="s-bds" stroke-width="1" stroke-dasharray="3 5"/>
    <!-- 面积（accent 12% 透明） -->
    <path d="M60,150 L180,120 L300,95 L420,70 L520,50 L520,180 L60,180 Z"
          class="f-acc" fill-opacity=".12"/>
    <!-- 折线（data-draw 描边动效） -->
    <path data-draw d="M60,150 L180,120 L300,95 L420,70 L520,50" class="f-none s-acc"
          stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
    <!-- 数据点 -->
    <circle cx="60" cy="150" r="4" class="f-acc"><title>Q3 · 32%</title></circle>
    <circle cx="180" cy="120" r="4" class="f-acc"/><circle cx="300" cy="95" r="4" class="f-acc"/>
    <circle cx="420" cy="70" r="4" class="f-acc"/><circle cx="520" cy="50" r="4" class="f-acc"/>
    <!-- 轴标签 -->
    <text x="60"  y="200" text-anchor="middle" class="f-txt3" font-size="11">Q3</text>
    <text x="180" y="200" text-anchor="middle" class="f-txt3" font-size="11">Q4</text>
    <text x="300" y="200" text-anchor="middle" class="f-txt3" font-size="11">2027H1</text>
    <text x="420" y="200" text-anchor="middle" class="f-txt3" font-size="11">H2</text>
    <text x="520" y="200" text-anchor="middle" class="f-txt3" font-size="11">2028</text>
  </svg>
</div>
```

---

---

## 22. 雷达图（多维能力，≤6 维）`data-chart="radar"`

```html
<div class="fig" style="text-align:center">
  <div class="fig__cap">治理能力雷达</div>
  <svg class="chart" data-chart="radar" viewBox="0 0 260 240" style="width:230px;margin-inline:auto">
    <!-- 同心网格（3 圈）+ 轴线 -->
    <polygon points="130,30 216,80 216,165 130,215 44,165 44,80" class="f-none s-bds" stroke-width="1"/>
    <polygon points="130,70 182,100 182,145 130,175 78,145 78,100" class="f-none s-bds" stroke-width="1"/>
    <line x1="130" y1="120" x2="130" y2="30" class="s-bds" stroke-width="1"/>
    <line x1="130" y1="120" x2="216" y2="80" class="s-bds" stroke-width="1"/>
    <line x1="130" y1="120" x2="216" y2="165" class="s-bds" stroke-width="1"/>
    <line x1="130" y1="120" x2="130" y2="215" class="s-bds" stroke-width="1"/>
    <line x1="130" y1="120" x2="44" y2="165" class="s-bds" stroke-width="1"/>
    <line x1="130" y1="120" x2="44" y2="80" class="s-bds" stroke-width="1"/>
    <!-- 数据多边形 -->
    <polygon points="130,48 198,90 196,150 130,180 60,150 62,95"
             class="f-acc" fill-opacity=".18" stroke="var(--accent)" stroke-width="2"/>
    <!-- 顶点标签 -->
    <text x="130" y="22" text-anchor="middle" class="f-txt2" font-size="11">语义</text>
    <text x="228" y="80" text-anchor="start" class="f-txt2" font-size="11">服务</text>
    <text x="228" y="172" text-anchor="start" class="f-txt2" font-size="11">消费</text>
    <text x="130" y="232" text-anchor="middle" class="f-txt2" font-size="11">底座</text>
    <text x="32" y="172" text-anchor="end" class="f-txt2" font-size="11">安全</text>
    <text x="32" y="80" text-anchor="end" class="f-txt2" font-size="11">契约</text>
  </svg>
</div>
```

---

---

## 23. 仪表盘 / 进度环（达成度）`data-chart="gauge"`

```html
<div class="fig" style="text-align:center">
  <div class="fig__cap">年度目标达成度</div>
  <svg class="chart" data-chart="gauge" viewBox="0 0 200 120" style="width:210px;margin-inline:auto">
    <!-- 半环底槽 -->
    <path d="M20 110 A 80 80 0 0 1 180 110" class="f-none s-bds" stroke-width="16" stroke-linecap="round"/>
    <!-- 进度（弧长 = π×80 ≈ 251；72% → 181） -->
    <path data-draw d="M20 110 A 80 80 0 0 1 180 110" class="f-none s-acc" stroke-width="16"
          stroke-linecap="round" stroke-dasharray="181 251"/>
    <text x="100" y="98" text-anchor="middle" class="f-txt" font-size="30" font-weight="700"
          data-count="72" data-suffix="%">72%</text>
    <text x="100" y="116" text-anchor="middle" class="f-txt3" font-size="11">指标纳管</text>
  </svg>
</div>
```

半环周长 `= π × r`；`dasharray="{周长×p} {周长}"`。

---

---

## 24. 瀑布图（增减归因 / 从 A 到 B）`data-chart="waterfall"`

```html
<div class="fig">
  <div class="fig__cap">使用率提升路径（31% → 60%）</div>
  <svg class="chart" data-chart="waterfall" viewBox="0 0 560 230">
    <line x1="40" y1="190" x2="540" y2="190" class="s-bds" stroke-width="1"/>
    <!-- 每段：起点值→终点值；柱从 min 到 max；y = 190 - 值/100*160 -->
    <rect data-anim="grow" x="60"  y="140" width="70" height="50" rx="5" class="f-s3"/>
    <text x="95"  y="132" text-anchor="middle" class="f-txt2" font-size="12" font-weight="600">31%</text>
    <text x="95"  y="206" text-anchor="middle" class="f-txt3" font-size="11">基线</text>
    <rect data-anim="grow" x="160" y="121" width="70" height="19" rx="5" class="f-acc"/>
    <text x="195" y="113" text-anchor="middle" class="f-acc" font-size="12" font-weight="600">+12</text>
    <text x="195" y="206" text-anchor="middle" class="f-txt3" font-size="11">清僵尸</text>
    <rect data-anim="grow" x="260" y="106" width="70" height="15" rx="5" class="f-acc"/>
    <text x="295" y="98"  text-anchor="middle" class="f-acc" font-size="12" font-weight="600">+9</text>
    <text x="295" y="206" text-anchor="middle" class="f-txt3" font-size="11">语义层</text>
    <rect data-anim="grow" x="360" y="93"  width="70" height="13" rx="5" class="f-acc"/>
    <text x="395" y="85"  text-anchor="middle" class="f-acc" font-size="12" font-weight="600">+8</text>
    <text x="395" y="206" text-anchor="middle" class="f-txt3" font-size="11">服务化</text>
    <rect data-anim="grow" x="460" y="94"  width="70" height="96" rx="5" class="f-s3"/>
    <text x="495" y="86"  text-anchor="middle" class="f-txt" font-size="12" font-weight="700">60%</text>
    <text x="495" y="206" text-anchor="middle" class="f-txt3" font-size="11">目标</text>
    <!-- 连接虚线 -->
    <line x1="130" y1="140" x2="160" y2="140" class="s-txt3" stroke-width="1" stroke-dasharray="3 3"/>
    <line x1="230" y1="121" x2="260" y2="121" class="s-txt3" stroke-width="1" stroke-dasharray="3 3"/>
    <line x1="330" y1="106" x2="360" y2="106" class="s-txt3" stroke-width="1" stroke-dasharray="3 3"/>
    <line x1="430" y1="94"  x2="460" y2="94"  class="s-txt3" stroke-width="1" stroke-dasharray="3 3"/>
  </svg>
</div>
```

---

---

## 25. 散点 / 气泡图（双维分布 / 优先级矩阵）`data-chart="scatter"`

```html
<div class="fig">
  <div class="fig__cap">用例优先级：价值 × 实施难度（气泡=数据量）</div>
  <svg class="chart" data-chart="scatter" viewBox="0 0 560 260">
    <!-- 象限分割线 -->
    <line x1="60" y1="210" x2="530" y2="210" class="s-bds" stroke-width="1"/>
    <line x1="60" y1="20"  x2="60"  y2="210" class="s-bds" stroke-width="1"/>
    <line x1="295" y1="20" x2="295" y2="210" class="s-txt3" stroke-width="1" stroke-dasharray="3 5"/>
    <line x1="60" y1="115" x2="530" y2="115" class="s-txt3" stroke-width="1" stroke-dasharray="3 5"/>
    <!-- 轴标签 -->
    <text x="530" y="228" text-anchor="end" class="f-txt3" font-size="11">业务价值 →</text>
    <text x="52" y="30" text-anchor="end" class="f-txt3" font-size="11" transform="rotate(-90 52 30)">难度 →</text>
    <!-- 气泡：cx=价值, cy=难度, r=规模；右上=优先做 -->
    <circle cx="420" cy="70"  r="16" class="f-acc" fill-opacity=".85"><title>ChatBI 问数 · 高价值低难度</title></circle>
    <circle cx="350" cy="110" r="12" class="f-acc" fill-opacity=".6"/>
    <circle cx="180" cy="80"  r="10" class="f-s3"/>
    <circle cx="140" cy="160" r="8"  class="f-s3"/>
    <circle cx="440" cy="170" r="11" class="f-s3"/>
    <!-- 点标签 -->
    <text x="420" y="48" text-anchor="middle" class="f-txt2" font-size="11">ChatBI 问数</text>
    <text x="350" y="136" text-anchor="middle" class="f-txt2" font-size="11">经营预警</text>
    <text x="180" y="60" text-anchor="middle" class="f-txt2" font-size="11">主数据治理</text>
  </svg>
</div>
```

---

---

## 26. 漏斗图（转化 / 筛选）`data-chart="funnel"`

```html
<div class="fig" style="text-align:center">
  <div class="fig__cap">数据资产激活漏斗</div>
  <svg class="chart" data-chart="funnel" viewBox="0 0 560 240" style="max-width:560px;margin-inline:auto">
    <!-- 每层：居中梯形/矩形，宽 ∝ 数值；层间距 8 -->
    <rect data-anim="fade" x="80"  y="10"  width="400" height="44" rx="8" class="f-acc" fill-opacity=".95"/>
    <text x="280" y="37" text-anchor="middle" class="t-on-inv" font-size="13" font-weight="600">入湖表 4,662</text>
    <rect data-anim="fade" x="120" y="66"  width="320" height="44" rx="8" class="f-acc" fill-opacity=".75"/>
    <text x="280" y="93" text-anchor="middle" class="t-on-inv" font-size="13" font-weight="600">纳入指标中心 2,100</text>
    <rect data-anim="fade" x="160" y="122" width="240" height="44" rx="8" class="f-acc" fill-opacity=".55"/>
    <text x="280" y="149" text-anchor="middle" class="t-on-inv" font-size="13" font-weight="600">挂接数据契约 890</text>
    <rect data-anim="fade" x="200" y="178" width="160" height="44" rx="8" class="f-acc" fill-opacity=".38"/>
    <text x="280" y="205" text-anchor="middle" class="f-txt" font-size="13" font-weight="600">被 Agent 消费 320</text>
    <!-- 侧边转化率 -->
    <text x="500" y="93"  class="f-txt3" font-size="11">45%</text>
    <text x="440" y="149" class="f-txt3" font-size="11">42%</text>
    <text x="392" y="205" class="f-txt3" font-size="11">36%</text>
  </svg>
</div>
```

> 层宽 = 值/最大值 × 最大层宽；层数 ≤ 5，多了改条形图。

---

---

## 27. 甘特 / 路线图（计划排期）`data-chart="gantt"`

```html
<div class="fig">
  <div class="fig__cap">数字大脑 3.0 四个季度路线</div>
  <svg class="chart" data-chart="gantt" viewBox="0 0 560 190">
    <!-- 季度刻度：4 列，每列 110 宽，从 x=130 起 -->
    <line x1="130" y1="28" x2="130" y2="160" class="s-bds" stroke-width="1"/>
    <line x1="240" y1="28" x2="240" y2="160" class="s-bds" stroke-width="1" stroke-dasharray="3 4"/>
    <line x1="350" y1="28" x2="350" y2="160" class="s-bds" stroke-width="1" stroke-dasharray="3 4"/>
    <line x1="460" y1="28" x2="460" y2="160" class="s-bds" stroke-width="1" stroke-dasharray="3 4"/>
    <text x="185" y="20" text-anchor="middle" class="f-txt3" font-size="11">Q3</text>
    <text x="295" y="20" text-anchor="middle" class="f-txt3" font-size="11">Q4</text>
    <text x="405" y="20" text-anchor="middle" class="f-txt3" font-size="11">2027Q1</text>
    <text x="515" y="20" text-anchor="middle" class="f-txt3" font-size="11">Q2</text>
    <!-- 每行：任务标签 + 横道（accent=主线，s3=支撑） -->
    <text x="0" y="56" class="f-txt2" font-size="12">指标中心</text>
    <rect data-anim="grow" x="130" y="42" width="220" height="20" rx="10" class="f-acc"/>
    <text x="0" y="94" class="f-txt2" font-size="12">数据契约</text>
    <rect data-anim="grow" x="185" y="80" width="220" height="20" rx="10" class="f-acc" fill-opacity=".75"/>
    <text x="0" y="132" class="f-txt2" font-size="12">治理 Agent</text>
    <rect data-anim="grow" x="295" y="118" width="220" height="20" rx="10" class="f-s3"/>
    <!-- 里程碑菱形 -->
    <polygon points="350,36 358,44 350,52 342,44" class="f-acc"><title>Q4 末：指标中心上线</title></polygon>
  </svg>
</div>
```

> 横道 `data-anim="grow"` 需把 CSS 的 `transform-origin` 换成 `left center`（横向生长，见第 35 节附注）。

---

---

## 28. 双向对比条形（正/反、A/B 对比）`data-chart="vsbar"`

```html
<div class="fig">
  <div class="fig__cap">直连源库 vs 指标中心（业务满意度）</div>
  <svg class="chart" data-chart="vsbar" viewBox="0 0 560 140">
    <!-- 中线 -->
    <line x1="280" y1="10" x2="280" y2="130" class="s-bds" stroke-width="1"/>
    <!-- 每行：左条（s3，从中间向左）+ 右条（acc，从中间向右） -->
    <text x="270" y="30" text-anchor="end" class="f-txt2" font-size="12">找数时长</text>
    <rect x="120" y="18" width="150" height="15" rx="7.5" class="f-s3"/>
    <rect x="280" y="18" width="60"  height="15" rx="7.5" class="f-acc"/>
    <text x="112" y="30" text-anchor="end" class="f-txt" font-size="11" font-weight="600">2 天</text>
    <text x="348" y="30" class="f-acc" font-size="11" font-weight="600">2 分钟</text>

    <text x="270" y="68" text-anchor="end" class="f-txt2" font-size="12">口径一致性</text>
    <rect x="190" y="56" width="80" height="15" rx="7.5" class="f-s3"/>
    <rect x="280" y="56" width="190" height="15" rx="7.5" class="f-acc"/>
    <text x="182" y="68" text-anchor="end" class="f-txt" font-size="11" font-weight="600">各说各话</text>
    <text x="478" y="68" class="f-acc" font-size="11" font-weight="600">统一定义</text>

    <text x="270" y="106" text-anchor="end" class="f-txt2" font-size="12">Agent 可用性</text>
    <rect x="240" y="94" width="30" height="15" rx="7.5" class="f-s3"/>
    <rect x="280" y="94" width="170" height="15" rx="7.5" class="f-acc"/>
    <text x="232" y="106" text-anchor="end" class="f-txt" font-size="11" font-weight="600">不可用</text>
    <text x="458" y="106" class="f-acc" font-size="11" font-weight="600">原生可消费</text>
  </svg>
</div>
```

---

---

## 29. 多段环形（多系列占比，≤4 段）`data-chart="multidonut"`

```html
<div class="fig" style="text-align:center">
  <div class="fig__cap">数据消费构成（四类）</div>
  <svg class="chart" data-chart="multidonut" viewBox="0 0 160 160" style="width:170px;margin-inline:auto">
    <!-- 周长 2π×60≈377；段:45%→169.6 / 25%→94.2 / 18%→67.9 / 12%→45.2
         每段 dashoffset 依次累减；缝隙用 2px 背景色描边 -->
    <circle cx="80" cy="80" r="60" class="f-none s-bds" stroke-width="18"/>
    <circle cx="80" cy="80" r="60" class="f-none s-acc" stroke-width="18"
            stroke-dasharray="169.6 207.4" transform="rotate(-90 80 80)"/>
    <circle cx="80" cy="80" r="60" class="f-none" stroke="var(--accent)" stroke-opacity=".55" stroke-width="18"
            stroke-dasharray="94.2 282.8" stroke-dashoffset="-169.6" transform="rotate(-90 80 80)"/>
    <circle cx="80" cy="80" r="60" class="f-none s-txt3" stroke-width="18"
            stroke-dasharray="67.9 309.1" stroke-dashoffset="-263.8" transform="rotate(-90 80 80)"/>
    <circle cx="80" cy="80" r="60" class="f-none s-bds" stroke-width="18"
            stroke-dasharray="45.2 331.8" stroke-dashoffset="-331.7" transform="rotate(-90 80 80)"/>
    <text x="80" y="78" text-anchor="middle" class="f-txt" font-size="22" font-weight="700">4 类</text>
    <text x="80" y="98" text-anchor="middle" class="f-txt3" font-size="11">消费方式</text>
  </svg>
  <div class="row row-wrap" style="justify-content:center;gap:var(--sp-3);margin-top:var(--sp-4)">
    <span class="chip chip--accent">服务层 45%</span>
    <span class="chip">直连 25%</span>
    <span class="chip">导出 18%</span>
    <span class="chip">其他 12%</span>
  </div>
</div>
```

> 段色层级：主段 `--accent` 实色 → 次段 accent 55% 透明 → 再次 `--text-3` → 最次 `--border-soft`。**同族明度递减，不引入第二色相。**

---

---

## 29b. 多系列图表 · 数据色板（9 套风格各有 c1–c5）

多系列图表（多段环形、分组柱、多折线、散点分组）统一用 `f-c1~c5` / `s-c1~c5`：
**9 套风格各有自己的 5 色板**（单源 `styleDataColors` / `styleDataColorsDark`，随主题自动切换）：同一份代码在任何风格下都能出可区分的彩色系列，而结构色仍恒为中性 + 单一强调色。

```html
<div class="fig" style="text-align:center">
  <div class="fig__cap">各域数据消费占比（四系列）</div>
  <svg class="chart" data-chart="multidonut" viewBox="0 0 160 160" style="width:170px;margin-inline:auto">
    <circle cx="80" cy="80" r="60" class="f-none s-bds" stroke-width="18"/>
    <!-- 周长≈377；38%→143.2 / 27%→101.8 / 21%→79.2 / 14%→52.8 -->
    <circle cx="80" cy="80" r="60" class="f-none s-c1" stroke-width="18"
            stroke-dasharray="143.2 233.8" transform="rotate(-90 80 80)"/>
    <circle cx="80" cy="80" r="60" class="f-none s-c2" stroke-width="18"
            stroke-dasharray="101.8 275.2" stroke-dashoffset="-143.2" transform="rotate(-90 80 80)"/>
    <circle cx="80" cy="80" r="60" class="f-none s-c3" stroke-width="18"
            stroke-dasharray="79.2 297.8" stroke-dashoffset="-245" transform="rotate(-90 80 80)"/>
    <circle cx="80" cy="80" r="60" class="f-none s-c4" stroke-width="18"
            stroke-dasharray="52.8 324.2" stroke-dashoffset="-324.2" transform="rotate(-90 80 80)"/>
    <text x="80" y="78" text-anchor="middle" class="f-txt" font-size="22" font-weight="700">4 域</text>
    <text x="80" y="98" text-anchor="middle" class="f-txt3" font-size="11">消费占比</text>
  </svg>
  <!-- 图例：小色点 + 文字（色点用 f-c*，文字保持中性） -->
  <div class="row row-wrap" style="justify-content:center;gap:var(--sp-4);margin-top:var(--sp-4)">
    <span class="row" style="gap:6px"><svg width="10" height="10" viewBox="0 0 10 10"><rect width="10" height="10" rx="3" class="f-c1"/></svg><span class="t-sm">供应链 38%</span></span>
    <span class="row" style="gap:6px"><svg width="10" height="10" viewBox="0 0 10 10"><rect width="10" height="10" rx="3" class="f-c2"/></svg><span class="t-sm">财务 27%</span></span>
    <span class="row" style="gap:6px"><svg width="10" height="10" viewBox="0 0 10 10"><rect width="10" height="10" rx="3" class="f-c3"/></svg><span class="t-sm">研发 21%</span></span>
    <span class="row" style="gap:6px"><svg width="10" height="10" viewBox="0 0 10 10"><rect width="10" height="10" rx="3" class="f-c4"/></svg><span class="t-sm">营销 14%</span></span>
  </div>
</div>
```

**彩色使用边界（9 套风格同一条纪律）**：
- 彩色**只**在数据系列、图例色点、小段标签；标题/正文/边框/按钮/大底色保持中性 + 单一 `--accent`。
- 同屏彩色系列 ≤ 5，超出合并为「其他」（用 `f-c5`）。
- 多折线同理：每条线 `s-c1` / `s-c2` / `s-c3`，数据点同色。

---

---

## 30. 大数字 + 迷你趋势线（KPI 卡）

```html
<div class="metric">
  <div class="metric__k">可信数据消费率</div>
  <div class="metric__v t-metric">45<small>%</small></div>
  <svg viewBox="0 0 120 28" style="width:100%;height:26px;margin-top:6px">
    <path data-draw d="M2,22 L22,18 L42,20 L62,12 L82,14 L102,7 L118,4" class="f-none s-acc"
          stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="118" cy="4" r="2.6" class="f-acc"/>
  </svg>
  <div class="metric__n">近四季度持续上行</div>
</div>
```

---

---

## 31. 进度条列表（多项目完成度）

```html
<div class="card">
  <h3 class="t-h3" style="margin-bottom:var(--sp-4)">各域治理进度</h3>
  <div class="stack gap-4">
    <div>
      <div class="row" style="justify-content:space-between;margin-bottom:5px">
        <span class="t-sm" style="color:var(--text)">供应链</span>
        <span class="t-sm" style="color:var(--text-3)">76%</span>
      </div>
      <div style="height:8px;border-radius:999px;background:var(--surface-2);overflow:hidden">
        <div style="width:76%;height:100%;border-radius:999px;background:var(--accent)"></div>
      </div>
    </div>
  </div>
</div>
```

---

# 第二部分 · 图表尺寸与轻量交互

> 尺寸下限（低于即不合格）与进入视口的克制动效；阈值唯一事实源 `layout-constants.json` `charts.minSize`。

---

## 35. 图表尺寸下限 + 轻量交互

### 尺寸下限（不要再小；校验脚本按 data-chart 类型核对）

> **阈值唯一事实源 = `scripts/layout-constants.json` 的 `charts.minSize`**（下表为其可读版；改阈值只改 JSON）。
> `pxWidthMin` = 内联 `width:NNNpx` 硬下限（FAIL）；`vbHeightMin` = 通宽图 `viewBox` 高度建议下限（WARN）。

| data-chart | 图表 | 最小尺寸 | 类型键 |
|-----------|------|---------|--------|
| donut / multidonut | 环形 | 显示直径 140px | `pxWidthMin:140` |
| gauge | 仪表盘 / 进度环 | 显示直径 180px | `pxWidthMin:180` |
| radar | 雷达图（≤6 维） | 显示直径 220px | `pxWidthMin:220` |
| rose | 玫瑰图（≤6 维） | 显示直径 180px | `pxWidthMin:180` |
| bar / stack | 柱状 / 堆叠柱 | viewBox 高 160 | `vbHeightMin:160` |
| line / dualline / area | 折线 / 双折线 / 面积 | viewBox 高 160 | `vbHeightMin:160` |
| waterfall | 瀑布 | viewBox 高 170 | `vbHeightMin:170` |
| scatter / bubble | 散点 / 气泡 | viewBox 高 180 | `vbHeightMin:180` |
| funnel | 漏斗（≤5 层） | viewBox 高 160 | `vbHeightMin:160` |
| treemap | 矩形树图 | viewBox 高 170 | `vbHeightMin:170` |
| marimekko | 马赛克图（变宽堆叠） | viewBox 高 160 | `vbHeightMin:160` |
| dumbbell | 哑铃图（前后对比） | viewBox 高 160 | `vbHeightMin:160` |
| lollipop | 棒棒糖图（排名） | viewBox 高 140 | `vbHeightMin:140` |
| bulletchart | 子弹图（目标 vs 实际） | viewBox 高 140 | `vbHeightMin:140` |
| gantt | 甘特 | viewBox 高 130 | `vbHeightMin:130` |
| dotplot | 点图（分布） | viewBox 高 120 | `vbHeightMin:120` |
| hbar / vsbar | 横向条形 | viewBox 高 100 | `vbHeightMin:100` |
| progress | 进度条组 | viewBox 高 100 | `vbHeightMin:100` |
| stackline | 100% 堆叠条 | viewBox 高 40 | `vbHeightMin:40` |
| sparkline | 迷你趋势线（KPI 内嵌） | viewBox 高 20 | `vbHeightMin:20` |
| sankey | 桑基 / 流向图 | viewBox 高 200 | `vbHeightMin:200` |
| slope | 斜率图（两期对比） | viewBox 高 180 | `vbHeightMin:180` |
| waffle | 华夫图（构成占比点阵） | viewBox 高 160 | `vbHeightMin:160` |
| boxplot | 箱线图（多组分布） | viewBox 高 180 | `vbHeightMin:180` |
| pareto | 帕累托（柱+累计线） | viewBox 高 180 | `vbHeightMin:180` |
| radialbar | 径向条形（多环进度） | 显示直径 200px | `pxWidthMin:200` |
| streamgraph | 流图 / 堆叠面积 | viewBox 高 160 | `vbHeightMin:160` |
| candlestick | K 线（区间波动） | viewBox 高 180 | `vbHeightMin:180` |
| （无 data-chart） | 主图（架构/流程 SVG） | 宽 ≥ 版心 55% | — |

**原则：宁可少放一张图，也不把图缩成一团。** 新图表类型必须在 `charts.types` 登记并配 `minSize`，否则校验器会提示「未登记」。

### 轻量交互（进入视口触发，克制不炫技）

**① 柱状生长 / 元素淡入（CSS，配合 JS 给容器加 `.in`）**

```css
[data-anim]{transform-box:fill-box}
.chart rect[data-anim="grow"]{transform:scaleY(0);transform-origin:center bottom;
  transition:transform .7s cubic-bezier(.05,.7,.1,1)}
.chart.in rect[data-anim="grow"]{transform:scaleY(1)}
.chart [data-anim="fade"]{opacity:0;transition:opacity .6s ease .18s}
.chart.in [data-anim="fade"]{opacity:1}
```

```html
<svg class="chart" data-chart="bar" viewBox="0 0 400 210">
  <rect data-anim="grow" x="52" y="131" width="58" height="39" rx="6" class="f-s3"/>
  <rect data-anim="grow" x="146" y="92" width="58" height="78" rx="6" class="f-s3"/>
  <text data-anim="fade" x="81" y="193" text-anchor="middle" class="f-txt3" font-size="11">Q3</text>
</svg>
```

> **横向生长**（甘特横道、横条）：svg 加 `chart--x` 即可，模板已内置 `.chart--x` 规则（`scaleX` + 左原点）。

**② 折线描边（`data-draw`）** —— 折线 path 上加 `data-draw`，JS 用 `getTotalLength()` 做 dashoffset 描边。

**③ 环形扫入（`data-sweep`）** —— 环形 accent 弧加 `data-sweep data-circ="339" data-p="0.31"`，JS 从 0 扫到 31%。

**④ 数字 count-up（`data-count`）** —— `<text data-count="31" data-suffix="%">0%</text>`，进入视口从 0 数到 31%。

**⑤ 悬浮提示（原生 `<title>`）** —— 图形内嵌 `<title>2026Q4 · 60%</title>`，鼠标悬停出提示，零成本。

### 动效触发 JS（已内置公共 UI 脚本，全页通用）

```js
(function(){
  function countUp(el){var t=parseFloat(el.dataset.count),s=el.dataset.suffix||'',
    d=(el.dataset.count.split('.')[1]||'').length,t0=null;
    (function st(ts){if(!t0)t0=ts;var p=Math.min(1,(ts-t0)/900);
      el.textContent=(t*p).toFixed(d)+s;if(p<1)requestAnimationFrame(st)})(performance.now());}
  function draw(p){var L=p.getTotalLength();p.style.strokeDasharray=L;p.style.strokeDashoffset=L;
    requestAnimationFrame(function(){p.style.transition='stroke-dashoffset 1s cubic-bezier(.05,.7,.1,1)';
      p.style.strokeDashoffset=0;});}
  function sweep(c){var L=+c.dataset.circ,p=+c.dataset.p;
    c.style.strokeDasharray=L;c.style.strokeDashoffset=L;
    requestAnimationFrame(function(){c.style.transition='stroke-dashoffset 1s cubic-bezier(.05,.7,.1,1)';
      c.style.strokeDashoffset=L*(1-p);});}
  if(!('IntersectionObserver' in window))return;
  var io=new IntersectionObserver(function(es){es.forEach(function(e){
    if(!e.isIntersecting)return;var g=e.target;io.unobserve(g);g.classList.add('in');
    g.querySelectorAll('[data-count]').forEach(countUp);
    g.querySelectorAll('[data-draw]').forEach(draw);
    g.querySelectorAll('[data-sweep]').forEach(sweep);})},{threshold:.3});
  document.querySelectorAll('.chart,[data-chart]').forEach(function(el){io.observe(el)});
})();
```

> 尊重 `prefers-reduced-motion`：系统要求减动效时，直接显示终态（给 `[data-anim]` 兜底 `transition:none`）。

---

# 第三部分 · 扩展图表

> 与第一部分同族：纯 SVG + `data-chart` 标记 + 语义类配色；新增类型须在 `charts.types` 登记并配 `minSize`。

---

