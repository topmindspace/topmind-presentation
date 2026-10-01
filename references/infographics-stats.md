# 信息图 · 统计图形族（sankey/treemap/boxplot/network/marimekko/streamgraph）

> 由 `infographics.md` 拆出（§编号不变）。六类专属页型规格 + HTML 写法 §71–§77。
> 取码：`python scripts/extract_snippet.py --chart sankey` 或 `--file infographics.md --section 71`。
> 通用铁律与边界判断见 `infographics.md`。

### 1. `sankey` · 桑基图页（节点-流带）

```json
{ "type": "sankey", "title": "线索转化流向：初筛环节流失最大", "unit": "条",
  "flows": [["线索","初筛",1000], ["初筛","商机",420], ["商机","报价",260],
            ["报价","签约",120], ["初筛","流失",580], ["商机","流失",160]],
  "chart": { "dataTable": "notes" }, "note": "口径：自然月去重线索" }
```

- **字段**：`flows:[[源,汇,值]…]`（必填）、`unit?`、`chart.dataTable?`、`note?`
- **几何**（`layout-constants.json` `pageTypes.sankey`）：`nodeW` 节点条宽、`nodeGap` 同列间距、`labelW` 标签宽、`minBandH` 节点最小高、`maxNodes` / `maxFlows` 上限
- **生成规则**：① 由 `flows` 抽取节点并**按入边分层**（无入边 = 0 层，其余 = 前驱最大层 + 1，迭代收敛防环）；② 节点高 ∝ `max(入流量, 出流量)`；③ 流带带宽 ∝ 流量占全篇比例，沿 smoothstep 路径铺贴**多段旋转矩形**（上下边界分别采样，段数 = `max(16, 跨度/0.1in)`）；④ 首列节点标签在节点左侧、末列在右侧、中间列在节点右侧（宽度 ≤ 列宽 60%）
- **HTML 侧**：内联 `<svg data-chart="sankey">`，流带用 `<path d="M…C…L…C…Z">` 三次贝塞尔**分别绘制上下边界**后闭合填充

### 2. `treemap` · 树图页（面积编码）

```json
{ "type": "treemap", "title": "区域收入构成：华东占近四成", "unit": "%",
  "items": [["华东",38], ["华南",27], ["华北",21], ["西部",9], ["海外",5]] }
```

- **字段**：`items:[[标签,值]…]`（必填）、`unit?`、`chart.dataTable?`、`note?`
- **几何**：`gap` 间隙、`labelMinH` 显示标签的最小高度、`maxLeaves` / `maxDepth`
- **生成规则**：按值降序 → **递归二分**（每次按累计面积中位切分，沿长边方向切）→ 面积与数值**严格成比例**；色阶按值占比取 4 级（`surface → soft → line → accent`），占比 ≥66% 用 `accent` 且文字走 `onAccent`
- **HTML 侧**：`<rect>` 网格 + `<text>` 标签，`data-chart="treemap"`

### 3. `boxplot` · 箱线图页（分布对比）

```json
{ "type": "boxplot", "title": "各产品线毛利分布", "unit": "%",
  "groups": [["A 线",12,28,35,48,62], ["B 线",18,30,34,40,46], ["C 线",8,20,26,33,44]] }
```

- **字段**：`groups:[[标签,最小,Q1,中位,Q3,最大]…]`（必填，六元组）、`unit?`、`chart.dataTable?`、`note?`
- **几何**：`labelW`、`groupGap`、`boxMaxW` 箱体最大宽、`whiskerCapW` 须线端帽宽、`maxGroups`
- **生成规则**：纵轴范围 = 全组 `[min(最小), max(最大)]`；每组画 ① 须线（最小→Q1、Q3→最大）② 上下端帽 ③ 箱体（Q1→Q3，`soft` 底 + `accent` 描边）④ 中位线（`accent` 粗线）；标签在中位线与极值处标注（数值走数值 token）
- **HTML 侧**：`<line>` 须线 + `<rect>` 箱体 + `<text>`，`data-chart="boxplot"`

### 4. `network` · 关系网络页（节点-边拓扑）

```json
{ "type": "network", "title": "系统依赖拓扑：核心平台为单点枢纽",
  "nodes": [["n1","核心平台"], ["n2","订单中心"], ["n3","结算中心"]],
  "edges": [["n1","n2"], ["n1","n3"], ["n2","n3"]] }
```

- **字段**：`nodes:[[id,标签]…]`（必填）、`edges:[[源id,汇id]…]`（必填）、`chart.dataTable?`、`note?`
- **几何**：`nodeR` / `nodeRMin` 节点半径、`labelMaxW` 标签宽、`maxNodes` / `maxEdges`
- **生成规则**：**确定性环形布局**（按输入顺序等角分布，**不用随机力导向**——保证可复现）；节点半径按度数线性映射（`nodeRMin + deg × 0.03`，上限 `nodeR`）；边为直连细线；标签朝环外侧对齐（左半环右对齐、右半环左对齐）
- **HTML 侧**：`<circle>` + `<line>` + `<text>`，`data-chart="network"`

### 5. `marimekko` · 马赛克图页（双重编码）

```json
{ "type": "marimekko", "title": "渠道结构演变", "unit": "%",
  "cols": [["2023",100], ["2024",130], ["2025",165]],
  "cells": [[40,60], [52,48], [61,39]],
  "legend": ["线上", "线下"] }
```

- **字段**：`cols:[[标签,总量]…]`（必填）、`cells:[[]…]`（必填，**按列索引**，每列一个段值数组）、`legend:[]?` 段名、`unit?`、`chart.dataTable?`、`note?`
- **几何**：`labelW`、`colGap` 列间距、`legendH` 图例行高、`maxCols` / `maxSegs`
- **生成规则**：**列宽 ∝ 列总量**、**列内高度 ∝ 段占比（归一到 100%）**——双重编码不可省略任一侧；段色取四阶调色板；列标签居中在列下方，图例一行在底部
- **HTML 侧**：`<rect>` 网格 + `<text>`，`data-chart="marimekko"`

### 6. `streamgraph` · 流带图页（构成演变）

```json
{ "type": "streamgraph", "title": "收入构成演变：订阅业务持续扩张",
  "labels": ["2021","2022","2023","2024","2025"],
  "series": [{"name":"订阅","values":[18,26,38,52,68]},
             {"name":"服务","values":[34,34,36,34,30]},
             {"name":"硬件","values":[52,44,34,26,18]}] }
```

- **字段**：`series:[{name,values}…]`（必填）、`labels:[]?` 时间轴标签、`chart.dataTable?`、`note?`
- **几何**：`labelW`、`bandMinH` 带最小高、`maxSeries` 上限
- **生成规则**：① 逐时间点求总量；② **基线居中**（`cyMid ± 总量/2`）；③ 逐系列按 smoothstep 插值铺贴多段旋转矩形，**采样点 ≥24**，上下边界分别追踪；④ 系列名做底部图例（色块 + 名称）；⑤ 时间标签沿底部均布
- **HTML 侧**：`<path>` 上下边界分别贝塞尔后闭合填充，`data-chart="streamgraph"`

## 四、双通道与校验（本技能内）

| 环节 | 位置 | 说明 |
|------|------|------|
| 几何常量 | `layout-constants.json` → `pageTypes.{sankey,treemap,boxplot,network,marimekko,streamgraph}` | 上限、间距、采样下限的唯一来源 |
| 页型 schema | `model-schema.json` → `pageTypes.*` | 字段与必填约束（`extract_model.py` 与浏览器端 `validateModel` 同源消费） |
| B 通道（交付） | `build_pptx.js` → `infoSankey` / `infoTreemap` / `infoBoxplot` / `infoNetwork` / `infoMarimekko` / `infoStreamgraph` | 全原生形状（`pictures=0`）+ 数据表 |
| A 通道（预览/回归） | `assets/pptx-export.js` → `infoApprox` | 形状近似，**文本集合与 B 严格一致** |
| HTML 侧写法 | 本文 §71–§77 | 内联 SVG 写法 + `data-chart` 登记 |
| 正文对应断言 | `validate_report.py` `TYPE_FEATURE` | `data-chart="sankey"` 等必须出现在正文 |
| 双通道一致 | `cross_verify.py` | 逐页文本集合比对（chart categories 并入 + 数值 token 对称过滤） |

**回归要求**：改动任一信息图页型的几何/渲染后，必跑 `python scripts/regression.py`（含 A/B 双通道 strict 与 `cross_verify`）；新增页型必须补齐**四件套**（schema 条目 + 几何常量 + 双引擎渲染 + 样例与校验断言）。

## 五、常见失败模式（自检清单）

| 失败 | 正确做法 |
|------|---------|
| 桑基流带只画一条等宽直线 | 上下边界分别采样（≥16 点）后按流量铺带宽 |
| 树图矩形面积与数值不成比例（凭感觉排版） | 严格按值降序 + 递归二分切分，面积线性映射 |
| 箱线图只画箱体不画须线与端帽 | 须线 + 端帽 + 箱体 + 中位线四件齐备 |
| 网络图用随机力导向导致每次布局不同 | 确定性环形布局（同输入必同输出） |
| 马赛克图只编码占比、丢掉列宽 | 列宽 = 列总量、列高 = 段占比，双重编码缺一不可 |
| 流带图采样点不足导致折线感 | 采样点 ≥24，上下边界分别插值 |
| 图内塞正文段落、把标签写成整句 | 文本退到图注级；注解走 `soWhat` / `note` |
| 数据只在图上、无法核对 | `chart.dataTable` 至少 `notes`（数据表入备注）；`inline` 时页内附原生表格 |
| 节点/段数超上限靠缩字号硬塞 | 按上限**拆页**（铁律 11：宁拆勿挤） |

---

## 六、HTML 写法（内联 SVG · `data-chart` 登记）

> 本节与 §一–§五 配套：§一–§五 定义「画成什么样」（几何上限 / 采样规则 / 数据表策略），本节给出「怎么写」（内联 SVG 片段）。
> `data-chart` 值即页型名，`validate_report.py` 用它做「模型页型 ↔ 正文版式」对应断言。

### 71. 桑基图页 `data-chart="sankey"`

**用途**：多个主体之间的**流向与流量**（转化链路、资金流向、迁移路径）。**节点 ≤12、流带 ≤24**；带宽与流量线性成比例。

```html
<div class="fig">
  <div class="fig__cap">线索转化流向（带宽 ∝ 流量 · 单位：条）</div>
  <svg class="chart" data-chart="sankey" viewBox="0 0 900 340">
    <!-- 流带：上下边界分别用三次贝塞尔绘制后闭合填充（不得用等宽直线） -->
    <g class="f-s2" opacity=".85">
      <path d="M140,40 C400,40 460,40 620,40 L620,74 C460,74 400,74 140,74 Z"/>
      <path d="M140,80 C400,80 460,150 620,150 L620,176 C460,176 400,110 140,110 Z"/>
    </g>
    <g class="f-s3" opacity=".85">
      <path d="M140,116 C400,116 460,210 620,210 L620,244 C460,244 400,150 140,150 Z"/>
    </g>
    <g class="f-s1" opacity=".85">
      <path d="M620,40 C740,40 780,60 830,60 L830,150 C780,150 740,74 620,74 Z"/>
    </g>
    <!-- 节点：首列标签在左、末列在右、中间列在节点右侧 -->
    <g class="f-acc"><rect x="120" y="34" width="18" height="118"/><rect x="620" y="34" width="18" height="216"/><rect x="830" y="52" width="18" height="104"/></g>
    <g class="f-txt" font-size="13" font-weight="600" text-anchor="end">
      <text x="112" y="98">线索</text>
    </g>
    <g class="f-txt" font-size="13" font-weight="600">
      <text x="648" y="70">初筛</text><text x="856" y="110">签约</text>
    </g>
    <g class="f-txt3" font-size="11" text-anchor="middle">
      <text x="380" y="52">1,000</text><text x="380" y="122">420</text><text x="380" y="196">580</text>
    </g>
  </svg>
</div>
```

**规则**：流带 `f-s1/s2/s3` 三阶明度区分主次流（主路径最亮），节点一律 `f-acc`；流带上下边界**分别**用 `C` 曲线描述再闭合（`.f-*` 填充 + `opacity:.85`）；标签字号走图注级（11–13px），数值标在带中段；**节点/流带超上限即拆页**。

### 72. 树图页 `data-chart="treemap"`

**用途**：层级构成 + **面积编码**（区域收入、成本结构、组合占比）。**叶节点 ≤16**；面积与数值严格成比例。

```html
<div class="fig">
  <div class="fig__cap">区域收入构成（面积 ∝ 收入占比）</div>
  <svg class="chart" data-chart="treemap" viewBox="0 0 900 320">
    <!-- 按值降序、递归二分切分；面积线性映射；占比 ≥66% 用 f-acc + 反相文字 -->
    <rect x="1" y="1" width="470" height="318" class="f-acc"/>
    <text x="18" y="34" class="t-on-inv" font-size="15" font-weight="600">华东 38%</text>
    <rect x="475" y="1" width="334" height="318" class="f-s2"/>
    <text x="492" y="34" class="f-txt" font-size="14" font-weight="600">华南 27%</text>
    <rect x="813" y="1" width="86" height="196" class="f-s3"/>
    <text x="822" y="26" class="f-txt" font-size="12">华北 21%</text>
    <rect x="813" y="201" width="86" height="118" class="f-s4"/>
    <text x="822" y="226" class="s-txt3" font-size="11">西部 9%</text>
  </svg>
</div>
```

**规则**：色阶按占比取四阶（`f-acc → f-s2 → f-s3 → f-s4`），占比最高块用 `f-acc` + `s-inv` 反相文字；块间隙用 1–2px 留白（不加描边）；**块高 <34px 时不显示标签**（避免文字挤爆），改由 `note` 说明；面积不得凭感觉排——先算面积再落坐标。

### 73. 箱线图页 `data-chart="boxplot"`

**用途**：分组**分布**对比（中位数、四分位、极值、离散度）。**组数 ≤8**。

```html
<div class="fig">
  <div class="fig__cap">各产品线毛利分布（箱体 = Q1–Q3，中线 = 中位，须 = 极值）</div>
  <svg class="chart" data-chart="boxplot" viewBox="0 0 900 300">
    <line x1="70" y1="270" x2="880" y2="270" class="s-bd"/>
    <!-- 每组四件齐备：须线 + 上下端帽 + 箱体 + 中位线 -->
    <g class="s-txt3" stroke-width="1.5">
      <line x1="180" y1="52" x2="180" y2="240"/><line x1="150" y1="52" x2="210" y2="52"/>
      <line x1="150" y1="240" x2="210" y2="240"/>
    </g>
    <rect x="138" y="96" width="84" height="104" class="f-s2 s-acc"/>
    <line x1="138" y1="128" x2="222" y2="128" class="s-acc" stroke-width="3"/>
    <text x="180" y="292" class="f-txt" font-size="12" text-anchor="middle">A 线</text>
    <text x="180" y="118" class="s-acc" font-size="12" font-weight="600" text-anchor="middle">35%</text>
  </svg>
</div>
```

**规则**：须线 + 端帽 + 箱体 + 中位线**四件齐备**（缺一即不合格）；箱体 `f-s2` 填充 + `s-acc` 描边、中位线 `s-acc` 加粗；组标签在图下方居中，中位数值标在中位线上方（其余极值只在需要读数的页标注）；**不引入第二色相**（离散度靠几何表达，不靠颜色）。

### 74. 关系网络页 `data-chart="network"`

**用途**：节点-边**拓扑关系**（系统依赖、组织协同、影响链路）。**节点 ≤18、边 ≤30**。

```html
<div class="fig">
  <div class="fig__cap">系统依赖拓扑（节点半径 ∝ 连接度）</div>
  <svg class="chart" data-chart="network" viewBox="0 0 900 340">
    <!-- 确定性环形布局：按输入顺序等角分布（不用随机力导向） -->
    <g class="s-bd" stroke-width="1.2">
      <line x1="450" y1="60" x2="180" y2="220"/><line x1="450" y1="60" x2="450" y2="280"/>
      <line x1="450" y1="60" x2="720" y2="220"/><line x1="180" y1="220" x2="450" y2="280"/>
      <line x1="720" y1="220" x2="450" y2="280"/>
    </g>
    <circle cx="450" cy="60" r="30" class="f-acc"/>
    <text x="450" y="64" class="t-on-inv" font-size="12" text-anchor="middle">核心平台</text>
    <circle cx="180" cy="220" r="22" class="f-acc"/><text x="180" y="224" class="t-on-inv" font-size="11" text-anchor="middle">订单</text>
    <circle cx="720" cy="220" r="22" class="f-acc"/><text x="720" y="224" class="t-on-inv" font-size="11" text-anchor="middle">结算</text>
    <circle cx="450" cy="280" r="18" class="f-s3"/><text x="450" y="284" class="f-txt" font-size="11" text-anchor="middle">风控</text>
  </svg>
</div>
```

**规则**：布局必须**确定性**（环形，同输入必同输出）——不得用随机力导向；节点半径按连接度线性映射，高连接度用 `f-acc`、低连接度用 `f-s3`；标签朝环外侧对齐（左半环 `text-anchor="end"`、右半环 `start`）；边为细直线（`s-bd`），**不画箭头**（关系对称时）；超上限拆页。

### 75. 马赛克图页 `data-chart="marimekko"`

**用途**：**双重编码**——列宽 = 列总量、列高 = 100% 构成（渠道演变、结构迁移）。**列 ≤6、每列段 ≤4**。

```html
<div class="fig">
  <div class="fig__cap">渠道结构演变（列宽 ∝ 规模，列高 = 构成占比）</div>
  <svg class="chart" data-chart="marimekko" viewBox="0 0 900 320">
    <!-- 2023（窄）→ 2025（宽）：列宽随总量变化，列内按占比分段 -->
    <g>
      <rect x="70" y="60" width="180" height="100" class="f-acc"/><rect x="70" y="160" width="180" height="100" class="f-s2"/>
      <text x="160" y="115" class="t-on-inv" font-size="12" text-anchor="middle">40%</text>
      <text x="160" y="215" class="f-txt" font-size="12" text-anchor="middle">60%</text>
      <text x="160" y="286" class="f-txt" font-size="12" font-weight="600" text-anchor="middle">2023</text>
    </g>
    <g>
      <rect x="264" y="52" width="234" height="121" class="f-acc"/><rect x="264" y="173" width="234" height="112" class="f-s2"/>
      <text x="381" y="286" class="f-txt" font-size="12" font-weight="600" text-anchor="middle">2024</text>
    </g>
    <g>
      <rect x="512" y="44" width="297" height="141" class="f-acc"/><rect x="512" y="185" width="297" height="90" class="f-s2"/>
      <text x="660" y="286" class="f-txt" font-size="12" font-weight="600" text-anchor="middle">2025</text>
    </g>
    <!-- 图例一行 -->
    <rect x="70" y="304" width="12" height="12" class="f-acc"/><text x="88" y="315" class="f-txt" font-size="11">线上</text>
    <rect x="140" y="304" width="12" height="12" class="f-s2"/><text x="158" y="315" class="f-txt" font-size="11">线下</text>
  </svg>
</div>
```

**规则**：**列宽与列高同时编码**（只做其一即为错版）；段色取四阶调色板（`f-acc / f-s2 / f-s3 / f-s4`），段间 1px 留白；列标签居中在列下方，图例一行在底部；段数 >4 时合并小段为「其他」。

### 76. 流带图页 `data-chart="streamgraph"`

**用途**：时间上的**构成演变**（业务结构此消彼长、份额迁移）。**系列 ≤6**；带边界采样点 ≥24。

```html
<div class="fig">
  <div class="fig__cap">收入构成演变（基线居中 · 带宽 ∝ 规模）</div>
  <svg class="chart" data-chart="streamgraph" viewBox="0 0 900 320">
    <!-- 上下边界分别贝塞尔后闭合填充；基线居中（上下对称展开） -->
    <path class="f-acc" opacity=".9"
      d="M60,120 C220,108 380,88 540,74 C660,64 780,58 860,56 L860,96 C780,100 660,110 540,124 C380,140 220,152 60,160 Z"/>
    <path class="f-s2" opacity=".9"
      d="M60,160 C220,152 380,140 540,124 C660,110 780,100 860,96 L860,132 C780,138 660,150 540,164 C380,180 220,190 60,196 Z"/>
    <path class="f-s3" opacity=".9"
      d="M60,196 C220,190 380,180 540,164 C660,150 780,138 860,132 L860,196 C780,204 660,214 540,226 C380,240 220,248 60,252 Z"/>
    <g class="f-txt" font-size="11" text-anchor="middle">
      <text x="60" y="286">2021</text><text x="260" y="286">2022</text>
      <text x="460" y="286">2023</text><text x="660" y="286">2024</text><text x="860" y="286">2025</text>
    </g>
  </svg>
</div>
```

**规则**：**基线居中**（上下对称展开，不是从零堆叠）；每条带的**上边界与下边界分别**用 `C` 曲线描述后闭合（相邻带共用边界，必须闭合无缝隙）；带内直接标系列名（≤4 个）或底部图例一行；x 轴只标首/中/末三处；**不画纵轴网格**（重点是形态不是读数）。

### 77. 信息图页型的通用纪律（统计图形族共享）

1. **一页一图**：本部分页型每页只放一张信息图；注解走 `soWhat`（结论条）/ `footnote`（口径来源）/ `flags`（待核实）槽位，**不在图内塞正文段落**。
2. **文本退到图注级**：节点/段/带标签字号 10–13px（`micro`/`caption` 语义层级），页头仍只保留 eyebrow + 主标题 + 可选导语（铁律 14）。
3. **数据可追溯**：模型 `section.chart.dataTable` 至少 `notes`（数据表写入 PPTX 演讲者备注）；需要页内可见时用 `inline`（PPTX 侧在图形下方附原生表格）。
4. **上限即拆页**：节点/叶/组/列/系列超上限时按铁律 11「宁拆勿挤」**拆页**，不得缩字号硬塞。
5. **零外链**：本部分全部为**内联 SVG**（铁律 1），配色走 `.f-*/.s-*` 语义类（不写死 hex，随主题/风格切换）。
6. **四件套纪律**：新增/修改信息图页型必须同时更新 `model-schema.json`（字段）+ `layout-constants.json`（几何）+ `build_pptx.js` 与 `assets/pptx-export.js`（双引擎）+ 本文件与样例（断言），并跑 `python scripts/regression.py`。

---

## 八、结构图形族（架构 / 流程 / 层级 / 时序 / 闭环）

> **与 §一–§五 的分工**：统计图形回答"数据长什么样"；结构图形回答 **"一整套结构长什么样、链路怎么走、谁先谁后"**。二者共同构成"图为王"的能力面。
> **为什么单独成族**：v7 的架构表达只有分层带（`.arch`）+ 泳道（`.lane`）+ 简单管线，**不支持分支 / 判断 / 汇合 / 异常路径 / 层级 / 时序**，于是复杂结构被压成"矩阵方块 + 文字箭头"。本族补上这层表达力。

### 写法与映射（先看这三条）

1. **HTML 侧**：结构图形是**主图 SVG**——放在 `figure.fig` 内，**不加 `class="chart"`、不登记 `data-chart`**。它表达的是结构而非数据系列，因此不参与图表登记与多样性统计（`validate_report.py` 只对 `class="chart"` 的 SVG 做类型核对）。
2. **PPTX 映射**：结构图形页在模型中表达为 **`diagram` 页型**（architecture 模式自动走全幅几何）——`layers` 承载主干分层 / 阶段，`legend` 承载形状图例，分支与例外写入 `note`（自动进**演讲者备注**）。**不新增页型**，因此不破坏"锁定版式 ↔ PPTX 页型一一成对"。
3. **通用纪律**：正交折线优先于斜线；连线 1.5–2px；图内文字 ≥11px；一屏一图、一个视觉重心；节点 / 步骤超上限**拆页**（结构容量）；限内标签偏挤可按 `containers.fontShrink` 有限下探；配色走 `.f-*/.s-*` 语义类（不写死色值），强调色只给主路径与关键判断。

