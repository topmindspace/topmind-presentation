# 版式变体注册表（0.2.0 新增）

> **何时读**：标准页型（cards / timeline / twocol）不够用、但内容仍属其语义家族时。
> 变体**不新增 DSL 页型**：`section.variant` 声明，HTML 与 PPTX 双通道按 base 页型渲染 + 变体类名/分支。
> 注册表单源：`scripts/layout-constants.json → layoutVariants`。

## 通用规则

1. 变体必须能回答"为什么不用 base 版"——答不上来就用 base。
2. 变体复用既有组件（`.card` / `.tl` / `.cols-2` / 图标包），**不许为变体另起渲染器**。
3. 内容预算优先：变体不得以丢文字为代价美化（`validate_report` 内容覆盖率 <95% → WARN）。
4. 新增变体三步：在 `layoutVariants.variants` 登记 → 本文件写骨架 → `render_from_model.py` 加 `variant` 分支（+ `build_pptx.js` 同名分支）。

## bento-grid（Bento 拼贴卡）

base `cards`。4–6 张卡、其中 1 张是主结论/总览时用；首卡跨 2 列。

```html
<section class="band" data-page-type="cards" data-variant="bento-grid">
  <div class="wrap">
    <div class="shead rv">…章节头…</div>
    <div class="grid g-bento rv">
      <div class="card card--lead">
        <div class="card__hd"><div class="card__ico" data-icon="目标">[icon:目标]</div>
        <h3 class="t-h3">主结论</h3></div>
        <ul class="ul"><li>≤4 条要点</li></ul>
      </div>
      <div class="card">…其余卡（每卡 ≤3 条）…</div>
      <!-- 共 4–6 张，6 张为上限 -->
    </div>
  </div>
</section>
```

模型：`{type:'cards', variant:'bento-grid', cards:[{title, points, icon}…]}`。
PPTX：`cards` 分支首卡跨 2 列。

## timeline（图标时间线）

base `timeline`。阶段有明确类型语义（里程碑/风险/交付）且图标加速扫读时用；否则用基础 timeline。

```html
<div class="tl">
  <div class="tl__i tl__i--done">
    <div class="tl__ico" data-icon="旗帜">[icon:旗帜]</div>
    <div class="tl__l">2026 Q1</div><div class="tl__t">里程碑</div>
    <p class="t-body">一句话说明（≤60 字）。</p>
  </div>
  <!-- ≤6 个阶段，每阶段 1 个图标 -->
</div>
```

模型：`{type:'timeline', variant:'timeline', phases:[{label, name, d, s, icon:'旗帜'}]}`（数组形态第 5 元亦可）。
PPTX：节点圆点旁贴 `icon:` 图标；无图标回落圆点。

## 2-col-feature（双栏特性）

base `twocol`。左栏是核心主张/特性、右栏是支撑细节时用；两栏对等论证用基础 twocol。

```html
<div class="cols-2 rv">
  <p class="t-body col--feature"><strong>核心主张。</strong>两句话内讲清。</p>
  <p class="t-body"><strong>支撑一。</strong>细节。</p>
  <!-- 共 ≤6 段，特性栏 ≤2 段 -->
</div>
```

模型：`{type:'twocol', variant:'2-col-feature', paragraphs:[[标题, 正文]…]}`。
PPTX：首栏 accent 左线 + 标题放大一档。
