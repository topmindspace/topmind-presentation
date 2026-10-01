# 结构组件与锁定版式 · layouts-research.md

> 由 `components.md` 拆出（§编号保持不变，跨文件稳定引用）。
> 取码：`python scripts/extract_snippet.py --file components.md --section <编号>`
> 或直接 `--file layouts-research.md --section <编号>`。整读大文件视为违规。

## 36. research 模式 · 双栏正文 + 脚注（模式 B 专属）

```html
<section class="band" id="s2">
  <div class="wrap">
    <div class="shead rv">
      <div class="t-eyebrow">02 · 现状诊断</div>
      <!-- 行动标题：标题即结论 -->
      <h2 class="t-h1 shead__title">入湖表 68% 从未被查询，资产沉睡是第一问题</h2>
    </div>
    <div class="cols-2 rv">
      <p class="t-body">发现段：一段直接陈述数据与事实，≤ 200 字。</p>
      <p class="t-body">证据段：引用口径与对照数据，外部数据带 [n]。</p>
      <p class="t-body">含义段：这一发现意味着什么，下一步动作。</p>
    </div>
    <div class="footnote">
      注：入湖表共 4,662 张，查询日志取 2026H1；「从未查询」= 半年零访问。
      来源见 <a class="cite" href="#ref-3">[3]</a>。
    </div>
  </div>
</section>
```

> research 模式密度规则（卡片 4–5 条、表格 ≤16 行、单页 ≤3200 字）见 `modes.md` 模式 B。

---

## 36b. research 模式 · Exhibit 编号图表框 + so-what 结论条（锁定版式 R2 主件）

```html
<div class="exhibit rv">
  <div class="exhibit__hd">
    <span class="exhibit__no">Exhibit 3</span>
    <span class="exhibit__t">各域入湖表使用率：供应链领跑，研发垫底</span>
  </div>
  <!-- 图表：svg.chart data-chart="…"（做法见第二部分；尺寸取下限即可） -->
  <svg class="chart" data-chart="hbar" viewBox="0 0 520 150"><!-- …条形图… --></svg>
  <div class="exhibit__src">来源：数据平台运行月报，2026-08；使用率 = 半年内有查询的表 / 入湖表总数</div>
</div>
<div class="sowhat rv">
  <span class="sowhat__k">So what</span>
  <span class="sowhat__v">研发域是激活沉睡资产的第一目标：清僵尸表 + 语义化改造，预计抬升整体使用率 8–10 个百分点。</span>
</div>
```

> **Exhibit 编号纪律**：全篇连续（1..N 不跳号不重复，校验器检查）；文内引用写"如 Exhibit 3 所示"；`.exhibit__src` 必写来源+口径。so-what ≤ 60 字，一行说清含义或建议。**克制条款**：so-what/来源行只在关键论证页（Exhibit 页/结论页）——REPORT_MODEL 的 `soWhat`/`footnote` 字段同步此原则，逐页都加反而增加复杂度。

---

## 36c. research 模式 · 左侧章节导航轨（可选组件 · 默认不启用）

```html
<nav class="rail" id="rail" aria-label="章节导航">
  <a class="rail__a" href="#s1"><span class="rail__n">01</span><span class="rail__t">周期意义</span></a>
  <a class="rail__a" href="#s2"><span class="rail__n">02</span><span class="rail__t">现状诊断</span></a>
  <a class="rail__a" href="#s3"><span class="rail__n">03</span><span class="rail__t">治理架构</span></a>
  <!-- …与章节一一对应；当前章 .on 由脚本自动维护… -->
</nav>
```

> 样式与高亮脚本已内置公共引擎（宽屏常显、窄屏自动隐藏、滚动跟随高亮）；模板中默认注释不启用——**仅 ≥10 章深度白皮书且用户明确要目录常驻时解开**，普通报告加了反而增加版面复杂度。

---

## 36d. research 模式 · 锁定版式速查（R1–R8）

| 版式 | 骨架（自上而下） | 组合要点 |
|------|----------------|---------|
| **R1 论证页** | 行动标题 → `.cols-2`（2–4 段：发现/证据/含义）→ `.sowhat` → `.footnote` | 段落 ≤200 字/段；主题词式标题禁止；**PPTX 映射：`twocol` 页型** |
| **R2 Exhibit 页** | 行动标题 → `.exhibit`（编号+图+来源）→ 2–3 条解读（`.ul`）或右栏 → `.sowhat` | 默认主力版式；图取尺寸下限；**PPTX 映射：`exhibit` 页型（chart 支持 bar/hbar）** |
| **R3 密表页** | 行动标题 → ≤16 行表（含结论列）→ `.sowhat` | 结论列用 `td strong`；行高走 research 密度层；**PPTX 映射：`table` 页型** |
| **R4 指标带页** | 行动标题 → 4–6 个 `.metric` → 小表/迷你图（可选） | 兼作节奏休止页；每 3–4 页一个；**PPTX 映射：`metrics` 页型** |
| **R5 分栏证据页** | 行动标题 → `.g-side`（左宽论述 / 右窄证据，或反向） | **左宽右窄**（`.g-side` = 1.35fr : 1fr ↔ PPTX `split` 左 55% / 右 41.5%，同源）；顶边对齐 `a-start`；**PPTX 映射：`split` 页型** |
| **R6 三栏证据页** | 行动标题 → `.cols-3`（3–6 段并列短论点，每栏 ≤150 字） | 三个并列论点 / 三方观点；**PPTX 映射：`threecol` 页型** |
| **R7 半表半图页** | 行动标题 → `.grid.g-half`（左密表 + 右 `.exhibit` hbar/line） | 表图互证、对照阅读；**PPTX 映射：`halftable` 页型** |
| **R8 矩阵图页** | 行动标题 → `.matrix`（rowHeads × colHeads 网格 + 强调单元） | 定位/优先级/象限判断；**PPTX 映射：`matrix` 页型** |

> 不允许临场发明 R8 之外的结构；需要新结构时先扩本表并同步 PPTX 页型与 `layout-constants.json` 页型几何，再使用（锁定版式纪律）。

---

## 36e. research 模式 · 三栏证据页（R6）

```html
<section class="band" id="s6">
  <div class="wrap">
    <div class="shead rv">
      <div class="t-eyebrow">06 · 风险与治理</div>
      <h2 class="t-h1 shead__title">规模化三重门槛：技术可控、组织就绪、经济可行</h2>
    </div>
    <div class="cols-3 rv">
      <p class="t-body"><strong>论点一。</strong>第一栏论述，每栏 ≤150 字，保持三栏均衡。</p>
      <p class="t-body"><strong>论点二。</strong>第二栏论述，与第一栏并列推进。</p>
      <p class="t-body"><strong>论点三。</strong>第三栏论述，收束到本页结论。</p>
    </div>
    <div class="footnote">注：三方口径与样本说明一行。</div>
  </div>
</section>
```

> `.cols-3` 是 CSS 多栏（column-count:3，窄屏自动降栏），与 `.cols-2` 同族；**REPORT_MODEL 对应 `{"type":"threecol","paragraphs":[[小标题,正文]…]}`**，序列化器三栏均分。

---

## 36f. research 模式 · 半表半图页（R7）与矩阵图页（R8）

```html
<!-- R7 半表半图：左密表 + 右 Exhibit，对照阅读 -->
<div class="grid g-half rv">
  <div class="tbl-wrap">
    <table>
      <thead><tr><th style="width:30%">业务域</th><th>试点率</th><th>同比增幅</th></tr></thead>
      <tbody>
        <tr><td class="k">客服</td><td class="num">72%</td><td><strong>+9pt</strong></td></tr>
        <tr><td class="k">研发</td><td class="num">38%</td><td><strong>+15pt</strong></td></tr>
      </tbody>
    </table>
  </div>
  <div class="exhibit">
    <div class="exhibit__hd">
      <span class="exhibit__no">Exhibit 2</span>
      <span class="exhibit__t">右栏图表标题（结论式）</span>
    </div>
    <svg class="chart" data-chart="hbar" viewBox="0 0 480 190"><!-- …条形图… --></svg>
    <div class="exhibit__src">来源：<真实来源名>，YYYY-MM；口径说明</div>
  </div>
</div>

<!-- R8 矩阵图：rowHeads × colHeads + 强调单元 -->
<div class="matrix rv">
  <div class="matrix__grid" style="--mx-cols:3">
    <div></div>
    <div class="matrix__h">实施难度 · 低</div>
    <div class="matrix__h">实施难度 · 中</div>
    <div class="matrix__h">实施难度 · 高</div>
    <div class="matrix__rh">业务价值 · 高</div>
    <div class="matrix__c matrix__c--a"><b>客服问数</b>首批放量</div>
    <div class="matrix__c"><b>研发副驾</b>二批放量</div>
    <div class="matrix__c"><b>端到端交付</b>暂缓</div>
    <div class="matrix__rh">业务价值 · 中</div>
    <div class="matrix__c"><b>知识检索</b>常规推进</div>
    <div class="matrix__c"><b>经营预警</b>常规推进</div>
    <div class="matrix__c matrix__c--a"><b>自主决策</b>护栏试点</div>
  </div>
  <div class="matrix__note">图例：强调单元 = 优先投入项；其余按季度节奏推进。</div>
</div>
```

> **R7 REPORT_MODEL**：`{"type":"halftable","table":{head,rows},"chart":{type:'hbar',labels,values,max,unit}}`——左表右图同屏互证。
> **R8 REPORT_MODEL**：`{"type":"matrix","rowHeads":[…],"colHeads":[…],"cells":[[str 或 {t,accent}]…]}`——强调单元 `{t,accent:true}` 对应 HTML `matrix__c--a`。
> 矩阵行列数建议 ≤3×3（信息密度上限），超出先精简维度。

---

