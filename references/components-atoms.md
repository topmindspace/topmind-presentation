# 结构组件与锁定版式 · components-atoms.md

> 由 `components.md` 拆出（§编号保持不变，跨文件稳定引用）。
> 取码：`python scripts/extract_snippet.py --file components.md --section <编号>`
> 或直接 `--file components-atoms.md --section <编号>`。整读大文件视为违规。

## 1. 顶栏 + header 工具组（主题/风格/预览/帮助/全屏/折叠，无模式切换）

三份模式模板共用此结构（公共脚本在 ui.js，注入于各模板）。右侧图标组：风格下拉（9 套实时切换，纯视觉皮肤）/ PPTX 预览（P）/ PPT 生成指引（H）/ 全屏（F）/ 亮暗主题（T）/ 收起工具栏（B）。快捷键 T/P/H/F/B/Esc。

```html
<header class="bar">
  <div class="wrap bar__in">
    <div class="brand">
      <div class="brand__mark">M</div>
      <div class="brand__txt">
        <div class="brand__title">主标题</div>
        <div class="brand__sub">副标题 / 专题名</div>
      </div>
    </div>
    <nav class="nav">
      <a href="#s1">章节一</a>
      <a href="#s2">章节二</a>
      <a href="#refs">参考资料</a>
    </nav>
    <div class="toolsbar">
      <div class="seld" id="styleSel">
        <button class="iconbtn" id="styleBtn" type="button" aria-label="切换风格" title="风格（9 套实时切换）">
          <!-- palette 图标 -->
        </button>
        <div class="seld__pop" id="stylePop" role="menu" aria-label="风格选择">
          <div class="seld__lab">风格 · 9 套</div>
          <div class="seld__list" id="styleList"></div><!-- JS 生成 18 个 .sitem -->
        </div>
      </div>
      <button class="iconbtn" id="pptPreviewBtn" type="button" title="预览 PPTX（P）"><!-- eye 图标 --></button>
      <button class="iconbtn" id="helpBtn" type="button" title="PPT 生成指引（H）"><!-- help 图标 --></button>
      <button class="iconbtn" id="fsBtn" type="button" title="全屏（F）"><!-- maximize / minimize 双态图标 --></button>
      <button class="iconbtn" id="themeBtn" type="button" aria-label="切换亮/暗主题" title="切换亮/暗主题（T）">
        <!-- sun / moon 双态图标 -->
      </button>
      <button class="iconbtn" id="barFold" type="button" title="收起/展开工具栏（B）"><!-- chevron 双态图标 --></button>
    </div>
  </div>
</header>
```

> 完整 HTML（含全部功能图标与帮助模态）直接从任一模式模板复制；样式在 `assets/templates/engine.css`（`.toolsbar/.seld/.sitem/.hdoc`），行为在 `assets/templates/ui.js`，均由 `sync_runtime.py` 注入，**禁止在报告里手改**。
> **帮助模态**（`#helpModal`，复用 `.pmodal` 骨架 + `.hdoc` 文档样式）：双通道说明（页面预览 vs 智能体精导）+ 命令序列 + 可复制提示词（`#helpPrompt` + `#helpCopy`）。
> **交互**：全屏（F，`requestFullscreen`，图标随 `html.is-fs` 切换）；收起工具栏（B，`html.bar--fold` 把 header 收成"品牌标 + 展开钮"的迷你工具条，`--bar-h` 联动收紧、页面锚点自动适配，按文件记忆）；翻页引擎重写——飞行期禁 scroll-snap、连按直跳、滚轮打断、模态打开不翻页；主题记忆按文件隔离（`report-theme:<pathname>`），出厂 `data-theme` 不再被系统偏好覆盖。

---

---

## 2. Hero（16:9 满屏页 band--fit）

```html
<section class="band band--fit">
  <div class="wrap">
    <div class="grid g-hero" style="gap:clamp(32px,4vw,72px)">
      <div class="stack gap-5 rv">
        <div class="row row-wrap">
          <span class="chip chip--accent">标签一</span>
          <span class="chip chip--line">标签二</span>
        </div>
        <h1 class="t-display">主标题<br>第二行</h1>
        <p class="t-lead" style="max-width:620px">一句话主张 + 补充说明。</p>
        <div class="row row-wrap" style="gap:var(--sp-3)">
          <a class="btn btn--primary" href="#agenda">开始阅读</a>
          <a class="btn btn--ghost" href="#refs">参考资料</a>
        </div>
        <div class="row row-wrap" style="gap:var(--sp-6);margin-top:var(--sp-3)">
          <div>
            <div class="t-metric" style="color:var(--accent)">50%</div>
            <div class="t-xs" style="margin-top:4px">数字一注解</div>
          </div>
          <div>
            <div class="t-metric">62<span style="font-size:.45em"> TB</span></div>
            <div class="t-xs" style="margin-top:4px">数字二注解</div>
          </div>
        </div>
      </div>
      <div class="g-hero__visual rv"><!-- 内联 SVG 主视觉 --></div>
    </div>
  </div>
</section>
```

> `band--fit` = `min-height:calc(100vh - var(--bar-h))` + 垂直居中；内容超一屏时自动退化为流式，安全。

---

---

## 3. 章节头

```html
<div class="shead rv">
  <div class="t-eyebrow">0X · 关键词</div>
  <h2 class="t-h1 shead__title">一句主张</h2>
  <p class="t-lead shead__desc">≤ 2 行，说明本章回答什么问题。</p>
</div>
```

居中变体：`<div class="shead shead--center rv">`

---

---

## 4. 指标卡网格（6 列）

```html
<div class="grid g-6 rv">
  <div class="metric metric--ok">
    <div class="metric__v t-metric">62<small>TB</small></div>
    <div class="metric__k">指标名</div>
    <div class="metric__n">一行注解</div>
  </div>
  <!-- metric--warn 用于需要强调的问题项 -->
</div>
```

---

---

## 5. 卡片（三种变体 + 列表内容）

```html
<!-- 标准卡：图标头 + 列表 -->
<div class="card">
  <div class="card__hd">
    <div class="card__ico">01</div>
    <h3 class="t-h3">标题</h3>
  </div>
  <ul class="ul">
    <li><strong>要点。</strong>补充说明一句话。</li>
    <li><strong>要点。</strong>补充说明一句话。</li>
  </ul>
</div>

<!-- 强调卡（accent 底） -->
<div class="card card--accent">
  <h3 class="t-h3" style="margin-bottom:var(--sp-4)">目标清单</h3>
  <ul class="ul ul--check">
    <li>目标一 <strong>≥ 60%</strong></li>
  </ul>
</div>

<!-- 平卡（灰底，无边框） -->
<div class="card card--flat">
  <h3 class="t-h3" style="margin-bottom:var(--sp-2)">标题</h3>
  <p class="t-body">≤ 3 行正文。</p>
</div>
```

---

---

## 6. 带图标的卡片（从 icons.md 取图标）

```html
<div class="card">
  <div class="card__hd">
    <div class="card__ico">
      <!-- 从 references/icons.md 粘一个 svg，例如"盾牌/安全" -->
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
           stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg>
    </div>
    <h3 class="t-h3">全链路数据安全</h3>
  </div>
  <ul class="ul">
    <li>采集 → 存储 → 使用 → 销毁内嵌合规。</li>
    <li>Agent 消费必须在护栏内、可审计。</li>
  </ul>
</div>
```

---

---

## 7. 表格（含引用标记）

```html
<div class="tbl-wrap rv">
  <table>
    <thead>
      <tr><th style="width:12%">维度</th><th style="width:44%">现状</th><th>目标</th></tr>
    </thead>
    <tbody>
      <tr>
        <td class="k">治理模式</td>
        <td>集中式、事后审计</td>
        <td><strong>联邦自治 + 统一控制平面</strong></td>
      </tr>
      <tr>
        <td class="k">覆盖率</td>
        <td class="num">0%</td>
        <td class="num"><strong>≥ 90%</strong><a class="cite" href="#ref-2">[2]</a></td>
      </tr>
    </tbody>
  </table>
</div>
```

---

---

## 8. 分组对比表（多口径 / 多方案）

```html
<div class="tbl-wrap">
  <table>
    <thead>
      <tr><th style="width:22%">方案</th><th style="width:26%">优势</th>
        <th style="width:26%">代价</th><th>结论</th></tr>
    </thead>
    <tbody>
      <tr><td class="k">方案 A</td><td>建设快、风险低</td><td>复用性弱</td>
        <td>短期过渡可用</td></tr>
      <tr><td class="k">方案 B</td><td>复用强、可扩展</td><td>前期投入大</td>
        <td><strong>推荐</strong>（长期主线）</td></tr>
    </tbody>
  </table>
</div>
```

---

---

## 9. 时间线

```html
<div class="fig" style="padding:clamp(24px,2.4vw,36px)">
  <div class="tl">
    <div class="tl__i tl__i--done">
      <div class="tl__d"></div>
      <div class="tl__l">2026 Q3</div>
      <div class="tl__t">阶段名</div>
      <p class="t-body">≤ 2 行说明。</p>
      <div class="row row-wrap" style="margin-top:var(--sp-3)">
        <span class="chip chip--accent">关键目标</span>
      </div>
    </div>
    <div class="tl__i tl__i--now"><!-- 当前阶段 --></div>
  </div>
</div>
```

---

---

## 10. 引言 / 提示条

```html
<div class="note rv">
  <i class="note__ico">i</i>
  <div>
    <div class="note__t">小标题</div>
    <p class="t-body" style="color:var(--text-2)">
      一句话结论。<strong style="color:var(--text)">加粗重点</strong>。
    </p>
  </div>
</div>
```

图标可换 `i` / `!` / `★` / `✓`。

---

---

## 11. 强调带（收尾 / CTA / 金句 · 主题一致）

> **关键纪律**：收尾页/金句页不再用 `band--deep`——它在浅色主题下会渲染成**深色页**（"浅色模式末尾出现深色页"的根因）。默认改用主题一致的强调带。

| 类 | 底色 | 文字 | 何时用 |
|----|------|------|--------|
| `.band--accent` | `--accent-soft`（软强调） | 常规 `--text` | **收尾章 / CTA / 小结**（默认，亮暗同向，永不出深色） |
| `.band--accent--solid` | `--accent`（实底强调） | `--accent-on` | 金句 / 关键判断（更强，用风格强调色实底） |
| `.band--tint` | `--surface-1` | 常规 | Agenda / 参考资料（最轻的分块） |
| `.band--deep` | `--surface-inv`（**反相**） | `--text-inv` | ⚠️ 仅显式选择：浅色模式下渲染为**深色页**；全文 ≤1 处且不得作末页（校验器检查） |

```html
<!-- 收尾章（默认：主题一致软强调，浅色模式不再出深色页） -->
<section class="band band--accent band--fit" id="next">
  <div class="wrap">
    <div class="shead shead--center rv">
      <div class="t-eyebrow">下一步</div>
      <h2 class="t-h1 shead__title">主张</h2>
      <p class="t-lead shead__desc">说明。</p>
    </div>
    <div class="grid g-3 rv">
      <div class="card"><h3 class="t-h3" style="margin-bottom:var(--sp-2)">要点</h3>
        <p class="t-body">一句话。</p></div>
    </div>
    <div class="row" style="justify-content:center;gap:var(--sp-3);
         margin-top:clamp(28px,3.4vh,44px);flex-wrap:wrap">
      <a class="btn btn--primary" href="#s1">返回查看</a>
      <a class="btn btn--ghost" href="#refs">参考资料</a>
    </div>
  </div>
</section>

<!-- 金句 / 关键判断（可选：强调色实底，文字自动走 --accent-on） -->
<section class="band band--accent--solid band--fit" id="quote-1">
  <div class="wrap">
    <div class="shead shead--center rv">
      <div class="t-eyebrow">03 · 关键判断</div>
      <h2 class="t-h1 shead__title">一句金句主张</h2>
      <p class="t-lead shead__desc">本章结论的一句话浓缩</p>
    </div>
  </div>
</section>
```

> 强调带内**不要**手写 `color:var(--text-inv)` 之类的反相覆盖——引擎已按带型设好文字色（`.band--accent--solid .t-*` 全部走 `--accent-on`）。
> 确实需要反相深色页（发布会/大屏）时才用 `band--deep`，并在浅色交付前确认这是有意为之。

---

---

## 11b. 待核实标注（二次修改强调色）

> **用途**：无法核实/待业务确认的数字与判断（`xx%`、口径未定、外部预测），用**强调色**标出来，提醒用户交付前二次修改。**标色 = 行动项**，不是装饰。
> 三种载体：`.tbd` 内联标色 → `.tbd-legend` 页级图例（一句话）→ `.flagbar` 块级清单（逐条）。

| 载体 | 位置 | 说明 |
|------|------|------|
| `.tbd` | 行内（数字/短句） | accent 色 + 虚线底；**标色项所在页必须配一处 `.tbd-legend` 或 `.flagbar`** |
| `.tbd-legend` | 页脚上方一行 | 一句话说明"标色项待核实"，最轻量 |
| `.flagbar` | 页底清单条 | 逐条列出待核实项（数据页/收尾页收口），accent-soft 底 + 左侧 accent 竖条 |

```html
<!-- 内联标色（表格/正文里的待核实值） -->
<td><span class="tbd">xx%</span></td>
<td><span class="tbd">早期验证</span></td>

<!-- 页级图例（最轻量，配内联 .tbd 用） -->
<div class="tbd-legend">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/></svg>
  <span>标色项为<b>待核实/待补充</b>数据，交付前请二次确认。</span>
</div>

<!-- 块级清单条（逐条列明，数据页/收尾页收口） -->
<div class="flagbar rv">
  <div class="flagbar__hd">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/></svg>
    待核实 · 需二次确认
  </div>
  <ul>
    <li>同事级成熟度评分口径待与业务方确认，正式版请替换 <span class="tbd">xx%</span></li>
    <li>「三年后」时间窗来自访谈主观判断，需以官方路线图数据复核</li>
  </ul>
</div>
```

```css
.tbd{color:var(--accent-text);font-weight:600;border-bottom:1px dashed var(--accent);padding-bottom:1px;white-space:nowrap}
.tbd-legend{display:flex;align-items:flex-start;gap:var(--sp-2);margin-top:var(--sp-4);font-size:var(--fs-xs);color:var(--text-3)}
.tbd-legend b{color:var(--accent-text);font-weight:600}
.flagbar{margin-top:var(--sp-4);border:1px solid var(--border-soft);border-left:3px solid var(--accent);
  border-radius:var(--r-md);background:var(--accent-soft);padding:var(--sp-3) var(--sp-4)}
.flagbar__hd{display:flex;align-items:center;gap:var(--sp-2);font-size:var(--fs-xs);font-weight:700;color:var(--accent-text)}
.flagbar li{position:relative;padding-left:16px;font-size:var(--fs-xs);color:var(--text-2)}
```

> **PPTX 同源**：模型 `section.flags: ["…"]` → 导出为 accent 强调色清单条（底对齐 contentBottom，与来源行/so-what 同页时自动上移让位）；同时写入**演讲者备注**。
> **纪律**：单页 `.tbd` ≤ 12 处（过密改用 `.flagbar`）；标色只用于**真的需要用户确认**的项，不要把普通数字也标色（标色贬值）。规则见 `content-rules.md` 第五节。

---

---

## 11c. 素材图片（版式族 · 配图占位 · 用户图片规范）

> **零外链铁律保持**：`<img src>` 只允许 **data: 内联** 或 **相对路径**，禁 http(s) 外链图。素材图要随报告走，就把图转 data URI 内联（`scripts/prepare_images.py` 可一键转换）。
> **三种图片来源，同一套版式**：① 用户提供图片（`<img>` + `image.src`/`items`）② 无图时的**配图占位**（`.media--ph` + `image.placeholder`，原生形状渲染、不算图片）③ 数据图**不用图**（走内联 SVG 图表，可随主题变色）。
> **比例由单源锁定**：每个版式的宽高比写在 `layout-constants.json` 的 `imageSpec.ratioDefault` / `ratioCssClass`，HTML 用 `.media--r*` 锁定类、PPTX 用同一比例算高度——**两边比例必然一致**，不会出现「HTML 16:9、PPTX 拉宽」。

### 11c-1 版式族（`image.layout` ↔ HTML 类 ↔ 比例）

| layout | HTML 版式 | 比例（锁定类） | 建议像素 | 适用 |
|--------|----------|---------------|---------|------|
| `full` | 版心全宽单图（`figure.media`） | 3:1（`.media--r3-1`） | 2400×800 | 场景实拍、横幅截图 |
| `half` | 左图右注（`.grid.g-side` + `.media` + 右栏 `.stack`） | 4:3（`.media--r4-3`） | 1400×1050 | 图文互证（图 + 3–4 条解读） |
| `bleed` | 通栏出血（`.media--bleed`，负边距破版心） | 21:9（`.media--r21-9`） | 2560×1100 | 章节大图 / 情绪页 |
| `grid` | 多图网格（`.media-grid--2/3/4`） | 4:3（`.media--r4-3`） | 900×675 | 2 / 3 / 4 / 6 张并列互证 |
| `compare` | 双图 A/B 对比（`.media-compare` + `.media__tag`） | 4:3（`.media--r4-3`） | 1400×1050 | 前后对照、方案对比 |
| `wall` | Logo 墙（`.media-wall`，灰阶弱化、悬停还原） | 1:1（`.media--r1-1`） | 480×480 | 客户 / 伙伴 / 生态 Logo |

> `grid` 的列数由张数决定（2→2 列、3→3 列、4→4 列、6→3 列×2 行，单源 `pageTypes.image.gridCols`）；空间不足时**按可用高度收敛并垂直居中**（不会贴顶留大白）。
> **多图版式**（`grid` / `compare` / `wall`）用 `image.items: [{src, alt?, caption?, placeholder?}]`，单页上限 6 张（`imageSpec.maxPerPage`）；`compare` 必须恰好 2 张。

### 11c-2 效果类（比例之外）

| 类 | 效果 |
|----|------|
| `.media` | 圆角 + 1px 边框 + 底色兜底 |
| `.media--contain` | 完整显示不裁切（默认 `object-fit:cover` 裁切填满）↔ 模型 `image.fit:"contain"` |
| `.media--mask` + `.media__cap` | 底部渐隐蒙版 + 图上图注（随主题反相） |
| `.media__cap--below` | 图下常规图注（弱化色，不压图） |
| `.media__src` | 图下来源/口径行（`.t-xs` 语义，与 `footnote` 不重复） |
| `.media--plain` | 去圆角去边框（贴边/整块图用） |
| `.media__tag` | A/B 角标（`compare` 版式，accent-soft 底） |

### 11c-3 配图占位（无图时的正解 · 不要留空洞）

没有素材时**不要省略图、也不要塞无关图**：用配图占位把版式、比例、图注位置一次锁死，交付前替换 `src` 即可。

```html
<!-- full 版式占位：figure 同时挂 media--ph（虚线框 + 斜纹 + 图标 + 尺寸提示） -->
<figure class="media media--r3-1 media--ph rv">
  <div class="media__ph">
    <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2"/>
      <circle cx="9" cy="10" r="1.6"/><path d="m3 18 5-5 4 3.4 3-2.6 6 5.2"/></svg>
    <b>配图占位</b>
    <span>建议 2400×800px · 3:1 · 替换 image.src 即可</span>
  </div>
</figure>
<p class="media__src">图 1：客服智能体工作台（占位示例；交付前替换为真实截图）</p>
```

```json
// 模型侧：placeholder 与 src/items 三选一；占位由原生形状渲染，pictures 不增
{"type":"image","eyebrow":"07 · 场景实拍","title":"…",
 "image":{"placeholder":true,"layout":"full","caption":"图 1：…","hint":"建议 2400×800px"}}
```

> **占位纪律**：占位必须带可见标签（`.media__ph`，校验器硬拦「空占位」）；占位页在 PPTX 里是**原生圆角矩形 + 虚线 + 居中标签**（可编辑、可替换），并写入演讲者备注提示替换；**不要**用 `TODO/TBD` 之类占位文本（`PLACEHOLDER_TEXT` 会拦）。
> 占位与真实图片**不要混用**（同一 `image` 对象里 `placeholder` 优先，图片会被忽略——模型校验会告警）。

### 11c-4 用户图片规范（合理样式与大小）

| 项 | 规范 |
|----|------|
| 分辨率 | 位图按**版式建议尺寸**提供（见 11c-1），且 ≥ 显示尺寸的 **2 倍**；低于建议宽 75% 会提示「放大易糊」 |
| 格式 | `png`（截图/透明）/ `jpeg`（照片，质量 80）/ `webp` / `svg`（矢量图；字体与内嵌图须内联） |
| 体积 | 单图 data: 内联 ≤ 1.5MB、全篇内联 ≤ 8MB（`imageSpec.maxInlineBytes` / `maxTotalInlineBytes`）；超限改用**相对路径**并把 `assets/` 随报告交付 |
| 比例 | 与版式比例一致最好；不一致时 `fit:"cover"` 裁切填满 / `fit:"contain"` 完整显示留白（**默认 cover**） |
| 裁切 | 人像/界面截图优先 `contain`，避免裁掉关键信息；纯背景/纹理用 `cover` |
| 来源 | 图注 + `.media__src` 标口径与版权；商用素材确认授权 |

**一键准备素材**：

```bash
python scripts/prepare_images.py <图片或目录> --layout full      # 默认：够大就内联 data URI
python scripts/prepare_images.py ./photos --layout grid --mode path   # 大图走相对路径
# 产出：report-assets/images-snippets.html（可粘贴的 .media 片段）
#       report-assets/images-model.json （可并入 sections[] 的 image 对象）
```

### 11c-5 位置与节奏纪律

> 图放**视觉重心侧**（`g-side` 左 / `g-side--rev` 右 / `stagger` 交替）；主图宽 ≥ 版心 55%；图与文字**顶边对齐**（`a-start`）；**一屏只一个视觉重心**（图大就不要同时放巨号数字）。
> **一屏一图**为默认；`grid`/`wall` 属"多图并列"节奏页，适合放在章节过渡或证据页，不要连续多页堆图。
> 数据图**不要用截图**：折线/柱状/占比一律用内联 SVG 图表（`data-chart`），才能随主题变色并过图表登记校验。

### 11c-6 PPTX 同源（双通道一致性）

> 模型 `section.type:"image"` + `image:{src|items|placeholder, layout, fit, caption, alt, ratio?}`（或 `split.right.type:"image"`）→ **原生图片**（`pictures` 计数）或**原生占位框**（不计入图片）。
> 几何取自 `layout-constants.json` 的 `pageTypes.image` + `imageSpec.ratioDefault`，双引擎（`build_pptx.js` / `pptx-export.js`）用同一套规则算高度与居中，**HTML 与 PPTX 比例一致**。
> **声明式放行**：只有模型显式声明的图片才放行（`PICTURES_NOT_DECLARED` 硬拦未声明图片）；默认全篇 `pictures=0`（全原生可编辑）。
> **路径解析**：相对路径以**模型文件所在目录**为锚（模型与报告同目录 → 报告里的相对路径口径一致）；文件缺失会报 `IMAGE_SRC_MISSING`，并回落成占位框（不留空洞）。
> **预览保真**：预览模态会把图位块替换成真实图片（`ui.js` 按模型填充），占位页则保留虚线占位框 + 标签——预览即交付所见。

---

---

## 12. 页脚

```html
<footer class="foot">
  <div class="wrap foot__in">
    <div class="brand">
      <div class="brand__mark">M</div>
      <div class="brand__txt">
        <div class="brand__title">报告名</div>
        <div class="brand__sub">副标题 · YYYY-MM-DD</div>
      </div>
    </div>
    <div class="t-xs">密级说明</div>
  </div>
</footer>
```

---

---

## 13. Agenda 大纲页（必为第二页）

```html
<section class="band band--tint band--fit" id="agenda">
  <div class="wrap">
    <div class="shead rv">
      <div class="t-eyebrow">Agenda</div>
      <h2 class="t-h1 shead__title">报告大纲</h2>
      <p class="t-lead shead__desc">九章，从趋势到落地。点击任意条目跳转。</p>
    </div>
    <ol class="agenda rv">
      <li class="agenda__i"><a class="agenda__a" href="#why">
        <span class="agenda__n">01</span>
        <span><span class="agenda__t">周期意义</span>
          <div class="agenda__d">治理为何进入智能增长周期</div></span>
        <span class="agenda__go"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></span>
      </a></li>
      <!-- …其余章节同构… -->
    </ol>
  </div>
</section>
```

---

---

## 14. Agenda 多列（条目 >8 个时）

```html
<ol class="agenda agenda--2col rv">
  <!-- …agenda__i 条目… -->
</ol>
```

```css
@media (min-width:900px){
  /* 列优先（先左列后右列），与 PPTX Agenda 列填充一致 */
  .agenda--2col{display:block;column-count:2;column-gap:clamp(20px,3vw,48px)}
  .agenda--2col .agenda__i{break-inside:avoid;border-top:1px solid var(--border-soft)}
}
```

> **阈值（layout-constants `contentQuality.agenda`）**：**大纲 = 章（3–7 条），不是页目录**；每章 1+ 页，页标题不进 Agenda。≤8 单列；仅异常超 8 才 `.agenda--2col`；PPTX 自动分页只是安全网。单条标题 ≤36 字（`titleMaxChars`，超长截断+全称沉 notes）。放不下先归并回章，禁逐页罗列撑爆一屏。
> 条目仍偏高：压缩 `.agenda__a` 的 `padding`（如 `clamp(12px,1.6vh,18px)`）。

---

---

## 15. 页码指示（翻页导航）

```html
<!-- 固定右侧，圆点由脚本按 section.band 数量生成；脚本见 assets/templates/ui.js -->
<aside class="pager" id="pager" aria-label="页码导航">
  <div class="pager__count" id="pagerCount">1 / 9</div>
  <div class="pager__dots" id="pagerDots"></div>
</aside>
```

翻页脚本行为：`←/↑/PgUp` 上一页，`→/↓/PgDn/空格` 下一页，`Home/End` 首/末页；滚动时高亮当前页圆点并更新计数。

---

---

## 15b. 图标列表（ul--ico · 关键列表推荐）

3–5 条的关键列表，行首加小图标，扫读性明显提升。图标从 `icons.md` 选，**一条列表一个语义**。

```html
<ul class="ul ul--ico">
  <li>
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3"/></svg>
    <strong>底座已建成。</strong>62TB 数据湖、4,662 张入湖表。
  </li>
  <li>
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M22 7l-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/></svg>
    <strong>消费在爬坡。</strong>可信数据消费率连续四个季度上行。
  </li>
  <li>
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/></svg>
    <strong>契约是短板。</strong>覆盖率为 0，Agent 消费没有 SLA。
  </li>
</ul>
```

```css
.ul--ico li{padding-left:34px}
.ul--ico li>svg{position:absolute;left:0;top:.14em;width:17px;height:17px;color:var(--accent-text)}
```

> 图标语义表见 `icons.md` 末尾速查；密度准则：每屏 3–8 个图标。

---

---

## 15c. 带图标的指标卡（metric__ico）

指标卡右上角放类别小图标（规模/效率/质量各一个），一排指标卡立刻有了分组感。

```html
<div class="metric">
  <svg class="metric__ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3"/></svg>
  <div class="metric__v t-metric">62<small>TB</small></div>
  <div class="metric__k">数据湖规模</div>
  <div class="metric__n">较年初 +18%</div>
</div>
```

```css
.metric{position:relative}
.metric__ico{position:absolute;top:clamp(14px,1.4vw,20px);right:clamp(14px,1.4vw,20px);
  width:20px;height:20px;color:var(--text-3)}
```

---

# 第二部分 · 锁定版式与版式选型

> 锁定版式 = **不允许临场发明结构**：内容形态 → 版式 → PPTX 页型一一成对（见 §46 选型表）。research 专属（R1–R8）与 architecture 专属（A1–A3）在 §36–§38b，通用锁定页型在 §39–§50。
> **新增页型四件套纪律**：schema 条目 + 几何常量 + 双引擎渲染 + 样例与校验断言，缺一不可；组件全部内置于 `engine.css` / 模板（HTML 侧）与 `build_pptx.js` + `pptx-export.js`（PPTX 侧），几何常量在 `layout-constants.json`。

---

## 结论条 `.sowhat`（本页重点收口）

> **语义**：本页关键 takeaway，不是脚注。  
> **版式**：MD3 tonal surface——`accent-soft` 满铺 + 细描边 + 略大于正文的 `--fw-title` / `line-height:1.65` + 舒适内边距（`--sp-5`/`--sp-6`）。**禁止左侧 accent 装饰轨**（anti-AI-flavor）。  
> **标签**：**默认不显示**「So what / SO WHAT / 结论」字样；只写句子（或 `.sowhat__stack` 短多行）。罕见需标签时加 `.sowhat--labeled` + `.sowhat__k`。  
> **间距**：与上方主内容 `margin-top: clamp(28px,3.6vh,48px)`（≥`--sp-6` 量级），禁止贴底；善用页内呼吸，不挤、不空。  
> **PPTX**：`soWhatBar()` 同源 soft 满铺衬底 + 正文（无左轨），**不绘制 SO WHAT 字符串**。

```html
<div class="sowhat rv"><span class="sowhat__v">一行含义或建议（≤60 字）。</span></div>
```

