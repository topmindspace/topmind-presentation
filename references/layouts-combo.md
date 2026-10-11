# 结构组件与锁定版式 · layouts-combo.md

> 由 `components.md` 拆出（§编号保持不变，跨文件稳定引用）。
> 取码：`python scripts/extract_snippet.py --file components.md --section <编号>`
> 或直接 `--file layouts-combo.md --section <编号>`。整读大文件视为违规。

## 32. 版式 A：左图右文（一个大图 + 一组解读）

```html
<section class="band" id="s3">
  <div class="wrap">
    <div class="shead rv">…章节头…</div>
    <div class="grid g-side rv" style="align-items:center">
      <div class="fig"><!-- 主图：柱/折线/架构 SVG，宽 ≥ 版心 55% --></div>
      <div class="stack gap-5">
        <h3 class="t-h3">怎么读这张图</h3>
        <ul class="ul">
          <li><strong>结论一。</strong>一句话。</li>
          <li><strong>结论二。</strong>一句话。</li>
          <li><strong>结论三。</strong>一句话。</li>
        </ul>
        <div class="note">…可选：一句强调…</div>
      </div>
    </div>
  </div>
</section>
```

---

## 33. 版式 B：表 + 图并排（对照阅读）

```html
<div class="grid g-2 rv" style="align-items:start">
  <div class="fig"><!-- 环形/条形图 --></div>
  <div class="tbl-wrap">
    <table><!-- 3–5 行小表，与图互相印证 --></table>
  </div>
</div>
```

> 两栏**顶边对齐**（`align-items:start`）；表行数 ≤5，图选中尺寸（环形 150–170px）；高度差过大时给矮的一侧补一张 `card--flat` 注解卡。

---

## 34. 版式 C：2×2 卡图混排（四象限）

```html
<div class="grid g-2 rv">
  <div class="card"><!-- 左上：要点卡 --></div>
  <div class="fig" style="text-align:center"><!-- 右上：环形/雷达 --></div>
  <div class="fig"><!-- 左下：条形/柱 --></div>
  <div class="card"><!-- 右下：要点卡 --></div>
</div>
```

> 图与卡**对角分布**，视觉平衡；每格内容 ≤4 条；1080p 下 2×2 是密度上限，更多就拆页。

---

---

## 39. 大引言 / 金句页（节奏休止页 · 三模式通用 · 主题一致）

> 强调带 + 一句话主张。用于演示模式的"节奏休止"（连续数据页之间的呼吸口）或报告的核心判断页。**全文 1–2 处即可，多了廉价**；不加任何多余的页头角标/页脚信息。
> 默认 `band--accent`（软强调，亮暗同向）；更强用 `band--accent--solid`（强调色实底）。**不用 `band--deep`**——浅色模式下它会渲染成深色页。

```html
<section class="band band--accent band--fit" id="quote-1">
  <div class="wrap">
    <div class="shead shead--center rv">
      <div class="t-eyebrow">03 · 关键判断</div>
      <h2 class="t-h1 shead__title">治理不是把数据管起来，<br>而是让好数据被用起来</h2>
      <div style="font-size:clamp(40px,4.6vh,56px);font-weight:700;color:var(--accent);line-height:1;margin-top:var(--sp-4)">「</div>
      <p class="t-lead" style="max-width:860px;margin-inline:auto;font-size:clamp(18px,2.2vh,22px);font-weight:600">穿越分水岭的钥匙是平台化，不是更大的模型。</p>
      <p class="t-sm" style="margin-top:var(--sp-4);color:var(--accent-text)">—— 企业智能体发展调研 · 42 家深度访谈</p>
    </div>
  </div>
</section>
```

> **PPTX 映射**：金句页 → `quote` 页型（主题一致强调带：accent-soft 底 + 常规文字 + accent 引号/署名；`{quote, author, context?}`）。HTML 版式在标题下加大引号 `「` 与署名行，与 PPTX 同源。

---

## 40. 对比页（锁定版式 · presentation / research 通用）

> 左右双栏对照（现状 vs 目标 / 方案 A vs B / 之前 vs 之后），结论条收口。两栏同构同高（`.grid.g-half` + 两张 `.card`），右栏用强调底 `--accent-soft` 标示"目标态"。

```html
<div class="grid g-half rv">
  <div class="card">
    <h3 class="t-h3">堆场景路径 · 现状</h3>
    <ul class="ul">
      <li><strong>接入慢。</strong>每场景重复对接工具与权限。</li>
      <li><strong>治理弱。</strong>事后审计，回退靠人工。</li>
    </ul>
  </div>
  <div class="card" style="background:var(--accent-soft);border-color:transparent">
    <h3 class="t-h3" style="color:var(--accent)">平台化路径 · 目标</h3>
    <ul class="ul">
      <li><strong>接入快。</strong>统一编排，接入成本降一个量级。</li>
      <li><strong>治理内嵌。</strong>权限、审计、回退进平台层。</li>
    </ul>
  </div>
</div>
<div class="sowhat rv">
  <span class="sowhat__v">平台化不是可选项，而是规模化穿越分水岭的唯一共同路径。</span>
</div>
```

> 每栏要点 ≤4 条、同构对仗（同一维度正面 vs 反面）；结论条默认**不写标签字样**（无「So what」/「结论」），靠 MD3 衬条强调；罕见需标签时用 `.sowhat--labeled` + （已弃用默认标签）。
> **PPTX 映射**：`comparison` 页型——`left/right = {title, points:[[k,v]…]}`，左 surface / 右 soft 面板 + `verdict`（结论条，accent 实底）。**`verdict` 与 `soWhat` 互斥**（共用 annotation 结论条槽位，同页双填必叠印）：comparison 填 `verdict` 时不要再填 `soWhat`；渲染器已自动二选一（verdict 优先），模型侧应只给一个。

---

## 41. 大数指标页（锁定版式 · presentation / research 通用）

> 一个压场巨号数字（hero）+ 右列支撑指标。用于"单点核心数字撑起一页"的节奏页：hero 数字 56–76px 走 `--accent`，标签 + 同比变化（▲）在其下；右侧 2–4 个 `.metric` 支撑。

```html
<div class="grid g-side rv" style="align-items:center">
  <div class="stack gap-3">
    <div class="t-metric" style="color:var(--accent);font-size:clamp(56px,7vh,76px)">61%</div>
    <div class="t-h3">2025 企业智能体试点率</div>
    <div class="t-sm" style="color:var(--accent);font-weight:600">▲ +6pt vs 2024</div>
  </div>
  <div class="grid g-3">
    <div class="metric">
      <div class="metric__v t-metric">18<small>%</small></div>
      <div class="metric__k">规模化运行占比</div>
      <div class="metric__n">3 个以上场景稳定运行</div>
    </div>
    <!-- …2–3 个支撑指标 -->
  </div>
</div>
```

> hero 数字必须"一数一结论"（标题负责结论句，hero 负责证据）；支撑指标 ≤4 个、与 hero 不重复同一数字。
> **PPTX 映射**：`kpi` 页型——`hero=[值, 标签, delta?]` + `metrics:[[值, 注]…]`（竖分隔线左右分栏，几何见 `layout-constants.json` 的 `PT.kpi`）。

---

## 42. 环形图页（锁定版式 · presentation / research 通用）

> 占比结构图（3–5 扇区）。环形走 SVG `circle` + `stroke-dasharray` 弧段（12 点钟起顺时针），中心洞放合计值 + 标签，右侧图例行（色点 chip + 数值列表）。

```html
<svg class="chart" data-chart="donut" viewBox="0 0 150 150" style="width:200px;margin-inline:auto">
  <circle cx="75" cy="75" r="54" class="f-none s-bds" stroke-width="26"/>
  <circle cx="75" cy="75" r="54" class="f-acc" stroke-width="26"
          stroke-dasharray="61.1 278.2" transform="rotate(-90 75 75)"><title>已规模化 18%</title></circle>
  <!-- 每扇区一个 circle：dasharray = 弧长 余长（C=339.3，r=54）；rotate 依次累加扇区角度 -->
  <text x="75" y="72" text-anchor="middle" class="f-txt" font-size="22" font-weight="600">100%</text>
  <text x="75" y="92" text-anchor="middle" class="f-txt3" font-size="10">企业占比</text>
</svg>
```

> 显示宽 ≥140px（铁律 12）；扇区 ≤5、最小扇区 ≥8%（太小合并为"其他"）；色板走语义类（`f-acc / f-accs / f-s2`），spectrum 风格用 `f-c1~c5`；中心合计须与图例自洽。
> **PPTX 映射**：`donut` 页型——原生 `pie` 楔形（angleRange 角度拆分两通道同规则）+ 背景色圆挖孔 + 中心合计 + 右侧图例（色点/标签/值/占比），`chart={labels, values, unit?, centerLabel?}`；几何见 `PT.donut`。

---

## 43. 版式 D：全幅图表页（一个图撑满一页）

> 单图信息量大、需要全场聚焦时用：架构总览 / 全景趋势 / 复杂管线 / 大型对比。图占版心 ≥90%，标题负责结论、图负责证据、图注收口。三模式通用（architecture 模式下即 A1/A3 的全幅用法）。

```html
<section class="band band--fit" id="sX">
  <div class="wrap">
    <div class="shead rv">
      <div class="t-eyebrow">0X · 关键词</div>
      <h2 class="t-h1 shead__title">一句主张（标题负责结论，图负责证据）</h2>
    </div>
    <figure class="fig fig--full rv" style="padding:clamp(16px,2vw,28px)">
      <!-- 主图：宽 ≥ 版心 90%，高 420–560px；数据系列用 f-acc/f-s3（spectrum 用 f-c1~c5） -->
      <svg class="chart" data-chart="…" viewBox="0 0 1200 480" style="width:100%">…</svg>
      <figcaption class="fig__cap" style="margin-top:var(--sp-3)">图注一行：怎么读 + 口径说明</figcaption>
    </figure>
  </div>
</section>
```

> 图内文字 ≥11px；节点/系列 ≤24；超过先精简再拆页。**PPTX 映射**：`diagram`（architecture）或 `exhibit`/`bar`（A/B 模式）。

---

## 44. 版式 E：里程碑时间线页

> 路线图 / 排期 / 阶段复盘。3–5 个里程碑，每个 ≤2 行说明；当前阶段 `tl__i--now`、已完成 `tl__i--done`；关键里程碑挂 chip。

```html
<section class="band" id="sX">
  <div class="wrap">
    <div class="shead rv">
      <div class="t-eyebrow">0X · 路线图</div>
      <h2 class="t-h1 shead__title">四季度三里程碑：平台先行，场景分层放量</h2>
    </div>
    <div class="fig rv" style="padding:clamp(24px,2.4vw,36px)">
      <div class="tl">
        <div class="tl__i tl__i--done">
          <div class="tl__d"></div>
          <div class="tl__l">2026 Q3</div>
          <div class="tl__t">平台层就绪</div>
          <p class="t-body">统一编排与护栏上线。</p>
          <div class="row row-wrap" style="margin-top:var(--sp-3)">
            <span class="chip chip--accent">已交付</span>
          </div>
        </div>
        <div class="tl__i tl__i--now"><!-- 当前阶段：关键里程碑 chip --></div>
        <div class="tl__i"><!-- 后续阶段 --></div>
      </div>
    </div>
  </div>
</section>
```

> **PPTX 映射**：`timeline` 页型（阶段横排，当前阶段强调）。甘特排期（任务条 + 依赖）继续用 `data-chart="gantt"`（`charts.md` §27），两者不要混用：里程碑叙事用时间线、并行排期用甘特。

---

## 45. 版式 F：指标墙页

> 现状基线 / 经营快照 / 复盘仪表。6±2 个指标一排（`g-6`），带类别小图标（`metric__ico`）分组感，口径行收口；research 模式即 R4 指标带页。单数压场用 §41 kpi 版式，不要混。

```html
<section class="band band--top" id="sX">
  <div class="wrap">
    <div class="shead rv">
      <div class="t-eyebrow">0X · 现状基线</div>
      <h2 class="t-h1 shead__title">六组基线数字勾勒落地现状</h2>
    </div>
    <div class="grid g-6 rv">
      <div class="metric">
        <svg class="metric__ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><!-- 类别图标 --></svg>
        <div class="metric__v t-metric">62<small>TB</small></div>
        <div class="metric__k">指标名</div>
        <div class="metric__n">一行注解</div>
      </div>
      <!-- …同构 ≤6 张；指标 ≥7 时合并或拆两页… -->
    </div>
    <div class="row row-wrap rv" style="margin-top:var(--sp-5)">
      <div class="t-sm" style="color:var(--text-3)">口径：统计周期与样本说明<a class="cite" href="#ref-1">[1]</a></div>
    </div>
  </div>
</section>
```

> **PPTX 映射**：`metrics` 页型。带趋势的指标用迷你 sparkline（`charts.md` §30）；问题项 `metric--warn` 数量 ≤2。

---

## 46. 版式选型速查表（内容形态 → 版式 → PPTX 页型）

> 拿到内容先查这张表再动手；模式列空白 = 三模式通用。**禁止临场发明表外结构**——需要新结构时先扩本表与 PPTX 页型（四件套纪律），再使用。

| 内容形态 | 首选版式 | 次选 | 模式 | PPTX 页型 |
|---------|---------|------|------|-----------|
| 要点式并列主张（默认页型） | points 要点列表（§5 卡片 / §15b 图标列表） | cards（§5） | — | `points` |
| 一个大图 + 一组解读 | A 左图右文（§32） | D 全幅图表（§43） | — | `split` / `bar` / `exhibit` |
| 单图全场聚焦（架构/全景） | D 全幅图表（§43） | A1 分层带（§37） | C | `diagram` / `exhibit` |
| 现状基线 / 指标快照 | F 指标墙（§45） | R4 指标带 | B→F | `metrics` |
| 单个核心数字压场 | kpi 大数页（§41） | — | A/B | `kpi` |
| 构成占比（环形口径） | 环形图页（§42） | R7 半表半图 | A/B | `donut` / `halftable` |
| 构成占比（饼图口径） | pie 饼图（`charts.md` §16 变体） | 环形图页（§42） | A/B | `donut` |
| 构成占比（多系列 ≤4 段） | multidonut 多段环形（`charts.md` §29） | 环形图页（§42） | A/B | `donut` |
| 指标卡内嵌迷你趋势 | sparkline 迷你趋势线（`charts.md` §30 / §55） | — | — | `metrics` / `kpi` |
| 趋势 / 爬坡 | 版式 A + 折线 | R2 Exhibit | — | `exhibit`（chart bar/hbar） |
| 现状 vs 目标 / 方案对比 | comparison 对比页（§40） | vsbar 双向条形（`charts.md` §28） | A/B | `comparison` |
| 多维对标清单 | 表格（§7/8） | R3 密表 | B 密排 | `table` |
| 并列论点（3 个） | 三卡 g-3 / R6 三栏（§36e） | cards | A/B | `cards` / `threecol` |
| 完整论述（发现→证据→含义） | R1 双栏论证（§36） | R5 分栏证据 | B | `twocol` / `split` |
| 路线图 / 里程碑叙事 | E 时间线（§44） | 甘特 gantt（`charts.md` §27） | — | `timeline` |
| 并行排期（任务条+依赖） | 甘特（`charts.md` §27） | E 时间线（§44，仅里程碑） | — | `bar`（chart.type=gantt） |
| 定位 / 优先级 / 象限 | R8 矩阵（§36f） | scatter 散点（`charts.md` §25） | B | `matrix` |
| 系统分层架构 | A1 分层带（§37） | A3 管线（§38） | C | `diagram` |
| 流程 / 职责协作 | A2 泳道（§38b） | A3 管线 | C | `lane` |
| 端到端链路 | A3 管线（§38） | A2 泳道 | C | `lane` |
| 关键判断 / 金句休止 | 金句页（§39） | 深色收尾章（§11） | A 为主 | `quote` |
| 转化 / 筛选漏斗 | funnel（`charts.md` §26） | 版式 A | — | `exhibit`（bar 变体） |
| 增减归因（A→B） | waterfall 瀑布（`charts.md` §24） | 版式 A | — | `exhibit`（bar 变体） |
| 步骤 / 实施节奏（3–6 步） | steps 步骤条（§47） | E 时间线（§44） | — | `steps` |
| 二维强度对标（行业×场景） | heatmap 热力矩阵（§48） | R8 矩阵（§36f） | A/B | `heatmap` |
| 目标达成度对照（实际 vs 目标） | bullet 达成对比（§49） | vsbar（`charts.md` §28） | A/B | `bullet` |
| 层级递进 / 价值阶梯 | pyramid 金字塔（§50） | A1 分层带（§37） | — | `pyramid` |
| 份额悬殊的构成（面积编码） | treemap 树图页（`infographics.md` §72） | 环形图页（§42） | B/C | `treemap` |
| 双指标趋势对比（两条线） | dualline 双折线（`charts.md` §52） | R2 Exhibit | — | `exhibit`（chart line） |
| 累计量趋势（强调量级） | area 面积图（`charts.md` §52） | 折线（`charts.md` §21） | — | `exhibit`（chart area） |
| 双维分布 + 第三维权重 | bubble 气泡图（`charts.md` §53） | scatter（`charts.md` §25） | B | `exhibit`（bar 变体） |
| 多项目完成度进度 | progress 进度条组（`charts.md` §54） | bullet（§49） | A/B | `bullet` |
| 多对多流向 / 归因路径 | sankey 桑基页（`infographics.md` §71） | 漏斗（`charts.md` §26） | B/C | `sankey` |
| 两期排名/份额升降（谁升谁降） | slope 斜率（`charts.md` §57） | dumbbell（`charts.md` §58） | A/B | `exhibit`（chart line） |
| 单指标前后对比（多对象） | dumbbell 哑铃（`charts.md` §58） | vsbar（`charts.md` §28） | A/B | `bullet` |
| 排名 + 量值（比条形更轻） | lollipop 棒棒糖（`charts.md` §59） | hbar（`charts.md` §17） | A/B | `exhibit`（bar 变体） |
| 构成 + 规模（双重维度） | marimekko 马赛克页（`infographics.md` §75） | treemap（`infographics.md` §72） | B/C | `marimekko` |
| 周期性/多维强度（极坐标） | rose 玫瑰（`charts.md` §61） | radar（`charts.md` §22） | A/B | `exhibit`（bar 变体） |
| 分布 / 离散程度 | dotplot 点图（`charts.md` §62） | scatter（`charts.md` §25） | B | `exhibit`（bar 变体） |
| 目标 vs 实际（含定性区间） | bulletchart 子弹图（`charts.md` §63） | bullet 达成对比（§49） | A/B | `bullet` |
| 素材图片（full/half/bleed/grid/compare/wall） | media 图片页（§11c） | split 左文右图（§32） | — | `image` |
| 无素材但要锁版式（配图占位） | `.media--ph` 占位（§11c-3） | — | — | `image.placeholder` |
| 待核实/待补充项收口 | flagbar 清单条（§11b） | tbd-legend 页级图例 | — | `flags` 字段 |
| 构成占比（强调“每 1%”） | waffle 华夫图（`charts.md` §65） | 环形图（§42） | A/B | `donut` |
| 多组分布 / 离散度对比 | boxplot 箱线图页（`infographics.md` §73） | dotplot（`charts.md` §62） | B/C | `boxplot` |
| 主因排序（二八分析） | pareto 帕累托（`charts.md` §67） | 瀑布（`charts.md` §24） | A/B | `exhibit`（bar 变体） |
| 多指标达成率（同心环） | radialbar 径向条形（`charts.md` §68） | gauge（`charts.md` §18） | A/B | `bullet` |
| 结构随时间的此消彼长 | streamgraph 流带图页（`infographics.md` §76） | stackline（`charts.md` §23） | B/C | `streamgraph` |
| 节点-边拓扑关系 | network 关系网络页（`infographics.md` §74） | A1 分层带（§42） | B/C | `network` |
| 区间波动（开高低收） | candlestick K 线（`charts.md` §70） | line（`charts.md` §21） | A/B | `exhibit`（line 变体） |

---

## 46b. 密度分级适配（每页先定密度档，再套上表选版式）

> §46 按**内容形态**选版式；本表按**内容丰富度**定密度——两维正交，先查 §46 定"用哪个版式"，再用本表定"排多密"。完整规则见 `content-rules.md` §四-d。

| 密度档 | 判定（presentation / research 基准） | 版式倾向 | 排版参数 |
|-------|--------------------------------------|----------|----------|
| **L 轻** | 1–2 单元 / 一图一主张 / 一核心数字 | kpi（§41）· 金句（§39）· D 全幅图（§43）· 环形图页（§42） | `band--fit` 居中；字号上限；图表大尺寸 |
| **M 中** | 3–4 单元（research 一论证组） | `g-2` · `g-hero` / `g-hero--rev` · `g-side` / `g-side--rev` · `g-31` / `g-13` · `g-211` / `g-121` · `g-quad` · `g-aside` · comparison（§40）· R1/R7 | 标准字号与 gap；主次分明，非对称栅格优先 |
| **H 重** | 5–6 单元（research ≤12；密表/矩阵） | `g-3` · `g-4` · `g-6` · `g-mosaic` · `g-hero-full` 指标墙（§45）· 表格（§7/8）· R3/R6/R8/R4 | 字号下限仍达标；`band--top`；超限先拆页 |

**节奏规则**：连续两页 H 档 → 插一页 L 档休止；同一版式不连用超过 2 页（换栅格节奏，防"模板感"）。

### 栅格与版式工具类（一）· 非对称双栏与自适应列

```html
<!-- Hero 视觉居左（大图开场，文字收右侧） -->
<div class="grid g-hero--rev">…</div>
<!-- 图右文左（g-side 镜像：结论先行、证据靠右） -->
<div class="grid g-side--rev">…</div>
<!-- 3:1 非对称双栏（主内容 : 侧栏注解/指标） -->
<div class="grid g-31">…</div>
<!-- 1:3 非对称双栏（窄引言/导航 : 主内容） -->
<div class="grid g-13">…</div>
<!-- 4:1 / 1:4 强主次双栏（主件 + 窄侧栏：一行指标条 / 一列图例） -->
<div class="grid g-41">…</div>
<div class="grid g-14">…</div>
<!-- 5 等分（一屏 5 个并列单元） -->
<div class="grid g-5">…</div>
<!-- 自适应列（卡片数量不定时自动折行，minmax(220px,1fr)） -->
<div class="grid g-auto">…</div>
```

均随 1180/960/620px 断点自动塌列，与既有 `.g-*` 行为一致。

### 栅格与版式工具类（二）· 拼贴 / 交错图文 / 键值

```html
<!-- 拼贴栅格 g-bento（Bento/马赛克）：4 列基准 + 跨列/跨行；.sp-2/.sp-3/.sp-4 跨列，.rw-2 跨行 -->
<div class="grid g-bento">
  <div class="card sp-2">主卡（跨 2 列）</div>
  <div class="card">小卡</div>
  <div class="card">小卡</div>
  <div class="card rw-2">竖长卡（跨 2 行）</div>
</div>
<!-- 交错图文 stagger（一行图左文右、一行文左图右，节奏感强） -->
<div class="stagger">
  <div class="stagger__row"><div class="stagger__media">…图/卡…</div><div class="stagger__txt">…文…</div></div>
  <div class="stagger__row stagger__row--rev"><div class="stagger__media">…图/卡…</div><div class="stagger__txt">…文…</div></div>
</div>
<!-- 键值对照 kv（定义列表：指标口径 / 参数 / 对照项） -->
<dl class="kv">
  <dt>统计口径</dt><dd>试点及以上企业占比（N=42）</dd>
  <dt>样本周期</dt><dd>2025-09 至 2026-08</dd>
</dl>
```

- `.g-bento` 窄屏降为 2 列（1180px）→ 1 列（620px），span 自动收敛；适合"一屏多个不等大单元"的经营快照/能力矩阵。
- `.stagger` 窄屏（960px）自动取消镜像、单列堆叠。
- `.kv` 用 `dt/dd` 语义标签；`dt` 加粗左列、`dd` 常规右列，适合表格的轻量替代（≤6 组）。

---

### 栅格与版式工具类（三）· 命名区马赛克与等高行

```html
<!-- 三栏非对称：主栏 + 两个辅助栏（2:1:1） / 1:2:1 -->
<div class="grid g-211">…主 · 辅 · 辅…</div>
<div class="grid g-121">…辅 · 主 · 辅…</div>
<!-- 2×2 象限（四宫格，每格等权，等高自动拉伸） -->
<div class="grid g-quad">…四象限…</div>
<!-- 主内容 + 粘性侧栏（长文/大图 + 常驻注解栏；侧栏随滚动吸附） -->
<div class="grid g-aside">
  <div>…主内容…</div>
  <aside class="g-aside__side">…常驻注解 / 指标 / 图例…</aside>
</div>
<!-- 命名区马赛克：hero 通栏 + 三卡（一屏一重心） -->
<div class="grid g-mosaic">
  <div class="g-mosaic__hero">…通栏主件…</div>
  <div class="g-mosaic__a">…</div><div class="g-mosaic__b">…</div><div class="g-mosaic__c">…</div>
</div>
<!-- 全幅主件 + 底部三等分（大图/大表 + 支撑卡） -->
<div class="grid g-hero-full">
  <div class="g-hero-full__main">…全幅主件…</div>
  <div class="g-hero-full__s1">…</div><div class="g-hero-full__s2">…</div><div class="g-hero-full__s3">…</div>
</div>
<!-- 等高行分区（纵向节奏，替代等高卡片堆叠） -->
<div class="grid rows-3">…三行等高…</div>
<!-- 双列键值对照（宽屏两栏排定义，窄屏回落单列） -->
<dl class="kv kv--2col">…</dl>
```

- `g-211 / g-121`：三栏非对称，比 `g-3` 等分更有主次；窄屏（960px）塌为单列。
- `g-quad`：四象限分析 / 四类并列；`grid-auto-rows:minmax(0,1fr)` 保证四格等高。
- `g-aside`：主内容 + 粘性侧栏；侧栏 960px 以下取消吸附并堆到下方。
- `g-mosaic / g-hero-full`：用 `grid-template-areas` 命名区；窄屏自动 `areas:none` 单列堆叠。
- `rows-2 / rows-3`：等高行分区；内容超出时行高自然增长（不截断）。

---

## 46c. 组合版式矩阵（一页 = 主件 + 从件 + 注释层）

> **单件页（只有一张图 / 一张表）是例外，不是默认。** 报告的"丰富"来自**组合**——把图、表、卡片、指标、图片、结构图按主次组织进一页，而不是给图加个标题、加一条 so-what。
> **决策层**（分析意图 → 组合 → 页型，含合法组合表）见 `references/playbook.md` §四；本节给**可复制的组合代码**。
> **纪律**：一屏一个视觉重心（主件明显大于从件）；从件必须承载主件表达不了的信息（趋势 / 对比 / 含义），**不得复述主件数字**；注释层必写口径。

### 46c-1 组合一览（主件 → 从件 → 注释层 → 页型）

| 组合 | 主件 | 从件 | 注释层 | 页型 |
|------|------|------|--------|------|
| 证据页主力 | 图表 | 要点 3–4 条（`.ul--ico`） | `.sowhat` + `.exhibit__src` | `exhibit` |
| 结论先行 | 图表 | 左栏要点（`g-side` 镜像） | `.sowhat` | `split` |
| 表图互证 | 密表 | 图表 | 口径行 | `halftable` |
| 现状基线 | 指标带 4–6 个 | 小表 / 迷你图 | 口径行 | `metrics` |
| 主张 + 基线 | 要点列表 | 指标带 | — | `points`（`metrics` 字段） |
| 架构总览 | 分层图 | 图例 chips | 图注 1–2 行 | `diagram`（`legend`） |
| 图文互证 | 图片 | 要点 3–4 条 | 图注 + `.media__src` | `image`（`layout:"half"`） |
| 并列观察 | 卡片网格 | 结论条 | — | `cards` / `points` |
| **双区自由组合** | 左区 / 右区各可为 图表·表格·图片·要点·指标 | — | `.sowhat` / `flags` | `split`（双区版） |

> `split` 是组合页的通用解：`left` 与 `right` 各自可承载 图表 / 表格 / 图片 / 要点 / 指标（字段见 `model-schema.json`），因此 **图+图、图+表、表+文、指标+图** 都能在一页内成立。

### 46c-2 代码：主件图 + 从件要点 + 注释层（最常用）

```html
<div class="grid g-side rv" style="align-items:start">
  <div class="fig"><!-- 主件：宽 ≥ 版心 55%，取 charts.minSize 之上 --></div>
  <div class="stack gap-4">
    <h3 class="t-h3">怎么读这张图</h3>
    <ul class="ul ul--ico">
      <li><!-- icons.md 取图标 --><strong>结论一。</strong>图里读不出的含义。</li>
      <li><strong>结论二。</strong>对比或趋势判断。</li>
      <li><strong>结论三。</strong>下一步动作。</li>
    </ul>
  </div>
</div>
<div class="sowhat rv"><span class="sowhat__v">一行含义（≤60 字）。</span></div>
```

### 46c-3 代码：双区自由组合（左图 + 右表 / 左文 + 右图）

```html
<!-- 左图右表：两张不同维度的证据同屏互证 -->
<div class="grid g-2 rv" style="align-items:start">
  <div class="fig"><div class="fig__cap">图：结构与趋势</div><!-- svg.chart --></div>
  <div class="tbl-wrap"><table><!-- ≤8 行小表：明细与口径 --></table></div>
</div>

<!-- 左文右图：结论先行（g-side--rev 可镜像） -->
<div class="grid g-side rv" style="align-items:start">
  <div class="stack gap-4"><h3 class="t-h3">判断</h3><ul class="ul">…</ul></div>
  <div class="fig"><!-- 主件图 --></div>
</div>
```

### 46c-4 代码：主件全幅 + 底部支撑带（大图 + 三卡）

```html
<div class="grid g-hero-full rv">
  <div class="g-hero-full__main"><!-- 全幅主件：大图 / 大表 --></div>
  <div class="g-hero-full__s1"><div class="card">支撑一</div></div>
  <div class="g-hero-full__s2"><div class="card">支撑二</div></div>
  <div class="g-hero-full__s3"><div class="card">支撑三</div></div>
</div>
```

### 46c-5 代码：不等大拼贴（一屏一重心 + 多个从件）

```html
<div class="grid g-bento rv">
  <div class="card sp-2"><!-- 主卡（跨 2 列）：核心结论 --></div>
  <div class="card"><!-- 小卡 --></div>
  <div class="card"><!-- 小卡 --></div>
  <div class="card rw-2"><!-- 竖长卡（跨 2 行）：明细 / 时间线 --></div>
</div>
```

> **组合版式与 PPTX 同源**：上表每个组合都映射到一个已登记页型（`split` / `halftable` / `exhibit` / `metrics` / `points` / `diagram` / `image` / `cards`），因此**不会出现"HTML 排得丰富、PPTX 交付不出来"**。新增组合前先确认页型已登记（`model-schema.json` + `layout-constants.json` `pageTypeGeometry`）。
> **校验**：research 模式下「含 ≥2 种承载类型的内容页 ≥30%」由 `validate_report.py` 的 `图表多样性 / 组合版式` 检查把关（阈值单源 `charts.variety.compositeMinRatio`）。

---

## 47. 步骤条页（锁定版式 · 三模式通用）`steps`

**用途**：实施节奏 / 操作流程 / 阶段推进（3–6 步最佳，超 6 步折行；可分阶段分组）。
**内容形态**：每步一个动作 + 一句说明；关键步用 `.step--a` 高亮。

```html
<section class="band" id="s7">
  <div class="wrap">
    <div class="shead rv">
      <div class="t-eyebrow">05 · 落地节奏</div>
      <h2 class="t-h1 shead__title">四步走：从单场景试点到平台化放量</h2>
    </div>
    <!-- 可选分组标签（多阶段时用；单段可删） -->
    <div class="steps__phase rv">第一阶段 · 打基础</div>
    <div class="steps rv">
      <div class="step"><div class="step__n">01</div>
        <div class="step__t">选场景</div><div class="step__d">客服 / 研发 / 数据三类先跑通</div></div>
      <div class="step step--a"><div class="step__n">02</div>
        <div class="step__t">建平台</div><div class="step__d">三层解耦 + 统一编排（关键步高亮）</div></div>
      <div class="step"><div class="step__n">03</div>
        <div class="step__t">立治理</div><div class="step__d">权限、审计、回退进平台层</div></div>
      <div class="step"><div class="step__n">04</div>
        <div class="step__t">放量复制</div><div class="step__d">同一套护栏复制到新场景</div></div>
    </div>
  </div>
</section>
```

**规则**：步数 3–6；每步标题 ≤8 字、说明 ≤30 字；`.step--a` 全文 ≤2 处；PPTX 页型 `steps`（超 `maxPerRow:6` 自动折行，`groups` 字段可分组）。

---

## 48. 热力矩阵页（锁定版式 · A/B）`heatmap`

**用途**：二维强度对标（行业 × 场景、区域 × 品类、团队 × 能力），比矩阵更适合**有数值强度**的场景。

```html
<div class="heat rv">
  <div class="heat__grid" style="--heat-cols:5;--heat-label:132px">
    <div></div>
    <div class="heat__h">客服</div><div class="heat__h">研发</div><div class="heat__h">营销</div>
    <div class="heat__h">供应链</div><div class="heat__h">财务</div>
    <div class="heat__rh">金融</div>
    <div class="heat__c heat__c--3">78<small>高</small></div>
    <div class="heat__c heat__c--1">46<small>中</small></div>
    <div class="heat__c heat__c--2">63<small>中高</small></div>
    <div class="heat__c">38<small>低</small></div>
    <div class="heat__c heat__c--2">61<small>中高</small></div>
  </div>
  <div class="heat__legend">
    <span>就绪度</span>
    <span class="heat__sw" style="background:var(--surface-1)"></span>
    <span class="heat__sw" style="background:var(--accent-soft)"></span>
    <span class="heat__sw" style="background:var(--accent-soft-2)"></span>
    <span class="heat__sw" style="background:var(--accent)"></span>
    <span>低 → 高（单位：分）</span>
  </div>
</div>
```

**规则**：4 级色阶（`--1/--2/--3` + 默认）**只用强调色明度阶梯**，不引入第二色相；行列 ≤5×5（超了改附录密表）；单元格数值 + 一行强度词；口径写 `.footnote`。PPTX 页型 `heatmap`（`rowHeads/colHeads/cells/unit/scaleLabel`）。

---

## 49. 达成对比页（锁定版式 · A/B）`bullet`

**用途**：目标 vs 实际（OKR 复盘、能力就绪度、KPI 达成）；比双向条形更适合"有明确目标线"的场景。

```html
<div class="bul rv" style="--bul-label:minmax(0,2.4fr)">
  <div class="bul__row">
    <div class="bul__k">场景覆盖</div>
    <div class="bul__track"><div class="bul__fill" style="width:61%"></div>
      <div class="bul__tgt" style="left:80%"></div></div>
    <div class="bul__v"><b>61%</b> / 80%</div>
  </div>
  <div class="bul__row bul__row--warn">
    <div class="bul__k">治理就绪</div>
    <div class="bul__track"><div class="bul__fill" style="width:34%"></div>
      <div class="bul__tgt" style="left:75%"></div></div>
    <div class="bul__v"><b>34%</b> / 75%</div>
  </div>
</div>
```

**规则**：`bul__fill` 的 width 与 `bul__tgt` 的 left 用**同一量纲百分比**（建议统一以 `max` 为 100%）；未达标行加 `.bul__row--warn`（填充转中性色，不引入红绿）；行数 ≤6。PPTX 页型 `bullet`（`items:[[标签,实际,目标]…]` + `unit`/`max`）。

---

## 50. 金字塔页（锁定版式 · 三模式通用）`pyramid`

**用途**：层级递进（价值阶梯、能力成熟度、优先级金字塔）；**顶层最窄**，逐层加宽。

```html
<div class="pyr rv">
  <div class="pyr__lvl" style="--w:42%">
    <div class="pyr__t">自主决策</div><div class="pyr__d">护栏内自动执行，人工只审例外</div></div>
  <div class="pyr__lvl pyr__lvl--a" style="--w:72%">
    <div class="pyr__t">副驾协同</div><div class="pyr__d">人机分工明确（当前主力形态）</div></div>
  <div class="pyr__lvl" style="--w:100%">
    <div class="pyr__t">问答与检索</div><div class="pyr__d">知识问答、找数问数，替换成本最低</div></div>
</div>
```

**规则**：层级 3–5 层；`--w` 单调递增（建议 42/72/100 或 34/56/78/100）；`--a` 强调层 ≤1；层标题 ≤6 字、说明 ≤24 字。PPTX 页型 `pyramid`（`levels`）。

