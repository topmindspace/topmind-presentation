# 风格系统（9 套预设 · 覆盖 8 个色族 + 1 个彩色数据板）

> **何时读**：改配色、换/新增风格、调亮暗 token、配编码色板、对齐风格语汇（字体/圆角/字阶/密度）时。**何时不读**：只想挑风格（Gate 0 参考图 + `--task style-theme` 速览即可）。
> **取节**：`python scripts/extract_snippet.py --task style-theme`（快速选型 + 新增步骤）；单套风格细节 `--file styles.md --section <1-11>`（数字节号）。

## 工作原理

报告结构与样式分离。`design-system.md` 提供**风格无关的 CSS 引擎**（版式、栅格、组件、排版类、SVG 语义类全部复用）；每套风格**覆盖两层 token**：

1. **结构色层**（必须）：强调色、表面色族、文字色、边框——决定「是什么颜色」；
2. **风格语汇层**（必须与定位一致）：`--font-body` / `--font-display` / `--radius` / `--fs-*` 微调 / `--letter-*` / `--lh-*` / `--gap` / `--shadow-*` / `--link`——决定「是什么气质」（字体、圆角、字阶、留白、阴影）。

**语汇清单单源** = `scripts/layout-constants.json` `styleIdentity`；`engine.css` 覆盖块逐项落地；`audit_styles.py` 校验缺一即 FAIL。**只改色不改语汇 = 只有皮肤没有性格**。

切换方式：`<html data-mode="X" data-style="business-blue" data-theme="light">`。

- **模式（三选一，生成时锁定）与风格正交**：结构 / 类名 / 组件由模式模板决定（`assets/templates/`），风格覆盖上述两层 token。
- 生成后 header 风格下拉可实时切换 9 套（纯视觉皮肤不动内容）；交付前切回选定值（`data-style` 与 `REPORT_MODEL.style` 一致，校验器检查）。
- 除 `spectrum` 外，每套风格**只有一个强调色**，层次仍靠表面明度差 + 1px 边框；`spectrum` 的彩色仅限数据系列（见第 9 节边界）。
- 每套都同时给出 light 与 dark 两套**色**值；语汇层（字体/圆角/字阶）两主题共用。
- 风格 × 模式矩阵预览见 `assets/style-gallery.html`（三模式 Tab 为一级维度、9 风格卡片为二级，每张卡按当前模式渲染迷你版式特征）。
- **PPTX 导出侧的色 token 与本文件同源**：单一事实源在 `scripts/layout-constants.json` `styles`（light 变量），两导出通道自动消费（`sync_runtime.py` 注入/校验）；改风格值改 JSON，不要只改本文档。**PPTX 字体族一律 Microsoft YaHei**（投影可读性），不跟 HTML 换衬线/系统栈。

## 快速选型（含三模式推荐风格）

| 风格 | data-style | 一句话定位 | 适用场景 |
|------|-----------|-----------|---------|
| 商务蓝（默认） | `business-blue` | 专业克制、信息密度高，最通用 | 技术/数据/通用商务；**架构模式推荐** |
| 优雅黑白 | `apple-mono` | 极简、大留白、大字，高级产品感 | 产品发布、品牌、高管演示 |
| 麦肯锡咨询 | `mckinsey` | 结构化、正式、咨询范 | 战略/咨询/立项；**研究模式首选** |
| 品牌红 | `brand-red` | 以品牌主色红为强调，正式有辨识度 | 企业品牌材料、正式汇报 |
| 暖沙金 | `warm-sand` | 温暖高级、编辑感 | 年报、品牌叙事、文化；**研究模式推荐** |
| 墨绿 | `deep-teal` | 沉稳可信赖 | 金融、风控、ESG；**研究模式推荐** |
| 石墨深灰 | `graphite-dark` | 深色优先的沉浸石墨风（近黑面板 + 亮蓝青；浅色石墨纸灰为辅助） | 发布会、大屏展示；**架构模式首选** |
| 靛紫 | `indigo-violet` | 创新前沿 | AI、科技、研发 |
| 光谱彩色 | `spectrum` | 中性结构 + 5 色数据色板，图表出彩不花哨 | 数据密集汇报、运营复盘、大屏看板；**架构模式推荐** |

> **三模式推荐组合速记**：演示 → 商务蓝（默认）/优雅黑白；研究 → 麦肯锡/墨绿/暖沙金；架构 → 石墨深灰/商务蓝/彩色。研究模式偏好衬线标题 + 细线框架的咨询质感，架构模式偏好深色沉浸或彩色数据面，演示模式全部可用、默认商务蓝。

---

## 1. 商务蓝 `business-blue`（默认）

**定位**：专业、克制、信息密度高。中性灰阶 + Google Blue。
**适用**：绝大多数商务/技术/数据汇报。

**语汇**：Google Material · 圆角 16 · 同字族 · 密度 normal · `--link` = accent-text。

```css
html[data-style="business-blue"] {
  --font-body: "Google Sans","Roboto",-apple-system,BlinkMacSystemFont,"Segoe UI",
               "PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans SC",sans-serif;
  --font-display: var(--font-body);
  --radius: 16px; --fw-display:700; --fw-title:600;
  --letter-display:-.03em; --letter-eyebrow:.11em; --lh-body:1.68; --lh-lead:1.62; --link:#1b66c9;
  --bg:#ffffff; --surface:#ffffff; --surface-1:#f8f9fa; --surface-2:#f1f3f4; --surface-3:#e8eaed;
  --surface-inv:#202124; --text:#202124; --text-2:#5f6368; --text-3:#80868b; --text-inv:#ffffff;
  --border:#dadce0; --border-soft:#e8eaed;
  --accent:#1a73e8; --accent-soft:#e8f0fe; --accent-soft-2:#d2e3fc; --accent-text:#1b66c9; --accent-on:#ffffff;
}
html[data-style="business-blue"][data-theme="dark"] {
  --bg:#0d0f13; --surface:#14171c; --surface-1:#191d23; --surface-2:#20252c; --surface-3:#2a3038;
  --surface-inv:#e8eaed; --text:#e8eaed; --text-2:#adb4bd; --text-3:#868d96; --text-inv:#14171c;
  --border:#2f353d; --border-soft:#23282f;
  --accent:#8ab4f8; --accent-soft:#16243a; --accent-soft-2:#1d3557; --accent-text:#8ab4f8; --accent-on:#0d1b2e;
  --link:#8ab4f8;
}
```

---

## 2. 优雅黑白 `apple-mono`

**定位**：苹果式极简。大留白、超大字号、几乎无彩色，靠留白与排版取胜。
**适用**：产品发布、品牌、面向高管/外部的演示。
**特点**：强调色为近黑/近白（按钮实底黑），CTA 可极少量用系统蓝 `#0071e3`（`--link`）；分块少、字大、行宽松。
**语汇**：Apple 极简 · 圆角 20 · **typeBoost**（display/h1 放大）· `--fw-title:500` 更轻 · 行高 1.75 · 栅格 gap 放大 · 阴影几乎归零。

```css
html[data-style="apple-mono"] {
  --font-body: -apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",
               "PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  --font-display: -apple-system,BlinkMacSystemFont,"SF Pro Display","Helvetica Neue","PingFang SC",sans-serif;
  --radius: 20px; --fw-display:600; --fw-title:500;
  --fs-display: clamp(3rem,5.4vw,4.75rem);   /* typeBoost */
  --fs-h1: clamp(2.125rem,3.6vw,3.25rem);
  --letter-display:-.04em; --letter-eyebrow:.12em; --lh-body:1.75; --lh-lead:1.7;
  --gap:clamp(22px,2.2vw,36px); --link:#0071e3;
  --bg:#ffffff; --surface:#ffffff; --surface-1:#f5f5f7; --surface-2:#f5f5f7; --surface-3:#e8e8ed;
  --surface-inv:#1d1d1f; --text:#1d1d1f; --text-2:#6e6e73; --text-3:#86868b; --text-inv:#f5f5f7;
  --border:#d2d2d7; --border-soft:#e8e8ed;
  --accent:#1d1d1f; --accent-soft:#f5f5f7; --accent-soft-2:#e8e8ed; --accent-text:#1d1d1f; --accent-on:#ffffff;
  --shadow-1:none; --shadow-2:0 4px 24px rgba(0,0,0,.06);
}
html[data-style="apple-mono"][data-theme="dark"] {
  --bg:#000000; --surface:#000000; --surface-1:#161617; --surface-2:#1d1d1f; --surface-3:#2a2a2d;
  --surface-inv:#f5f5f7; --text:#f5f5f7; --text-2:#a1a1a6; --text-3:#86868b; --text-inv:#1d1d1f;
  --border:#38383d; --border-soft:#2a2a2d;
  --accent:#f5f5f7; --accent-soft:#1d1d1f; --accent-soft-2:#2a2a2d; --accent-text:#f5f5f7; --accent-on:#000000;
  --link:#2997ff;
}
```

---

## 3. 麦肯锡咨询 `mckinsey`

**定位**：结构化、正式、咨询范。衬线标题 + 无衬线正文 + 细线框架 + 小圆角 + 高密表格。
**适用**：战略、咨询、立项、可研、对标。
**特点**：强调色为藏青；标题用衬线（Georgia/宋体），eyebrow 小字大写拉开字距；靠 1px hairline 与网格分块，几乎不用阴影。
**语汇**：咨询范 · **serifDisplay** · 圆角 6（近直角）· 密度 dense · `--letter-eyebrow:.14em` · 行高收紧 1.55 · gap 收紧。

```css
html[data-style="mckinsey"] {
  --font-body: "Inter","IBM Plex Sans",-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
  --font-display: "Georgia","Times New Roman","Songti SC","STSong","SimSun",serif;
  --radius: 6px; --fw-display:600; --fw-title:600;
  --letter-display:-.015em; --letter-eyebrow:.14em; --lh-body:1.55; --lh-lead:1.5;
  --gap:clamp(14px,1.3vw,22px);
  --bg:#ffffff; --surface:#ffffff; --surface-1:#f2f4f7; --surface-2:#f2f4f7; --surface-3:#e4e7ec;
  --surface-inv:#101828; --text:#101828; --text-2:#475467; --text-3:#667085; --text-inv:#ffffff;
  --border:#d0d5dd; --border-soft:#e4e7ec;
  --accent:#003a70; --accent-soft:#eef4fb; --accent-soft-2:#d9e8f6; --accent-text:#003a70; --accent-on:#ffffff;
  --shadow-1:none; --shadow-2:0 1px 2px rgba(16,24,40,.06);
}
html[data-style="mckinsey"][data-theme="dark"] {
  --bg:#0c1116; --surface:#0c1116; --surface-1:#12181f; --surface-2:#182030; --surface-3:#21293a;
  --surface-inv:#e4e7ec; --text:#e4e7ec; --text-2:#aab3c2; --text-3:#8a94a6; --text-inv:#101828;
  --border:#2a3342; --border-soft:#1f2733;
  --accent:#7fb2e5; --accent-soft:#12233a; --accent-soft-2:#1b3358; --accent-text:#7fb2e5; --accent-on:#0c1a2e;
}
```

> 标题用 `.t-h1/.t-h2` 时衬线字体生效（`--font-display`）；eyebrow 走 `--letter-eyebrow:.14em` + `text-transform:uppercase` 强化咨询感。

---

## 4. 品牌红 `brand-red`

**定位**：以品牌主色红为强调，正式且有辨识度。可将下方红色替换为任意企业品牌色。
**适用**：企业品牌材料、正式汇报、对外宣讲。
**语汇**：正式品牌 · HarmonyOS Sans 栈 · 圆角 14 · 同字族粗字重 · 密度 normal。

```css
html[data-style="brand-red"] {
  --font-body: "HarmonyOS Sans","PingFang SC","Microsoft YaHei","Noto Sans SC",-apple-system,"Segoe UI",sans-serif;
  --font-display: var(--font-body);
  --radius: 14px; --fw-display:700; --fw-title:600;
  --letter-display:-.025em; --letter-eyebrow:.12em; --lh-body:1.66; --lh-lead:1.6;
  --bg:#ffffff; --surface:#ffffff; --surface-1:#faf7f7; --surface-2:#f5f0f0; --surface-3:#ece5e5;
  --surface-inv:#1f1a1b; --text:#1f1a1b; --text-2:#5d5456; --text-3:#8a8083; --text-inv:#ffffff;
  --border:#e2d9da; --border-soft:#ece5e5;
  --accent:#d0021b; --accent-soft:#fbecec; --accent-soft-2:#f6d5d7; --accent-text:#b00217; --accent-on:#ffffff;
}
html[data-style="brand-red"][data-theme="dark"] {
  --bg:#130d0e; --surface:#130d0e; --surface-1:#1a1213; --surface-2:#231718; --surface-3:#2e1e20;
  --surface-inv:#f3ecec; --text:#f3ecec; --text-2:#c4b6b7; --text-3:#9a8d8e; --text-inv:#1f1a1b;
  --border:#37272a; --border-soft:#2a1e20;
  --accent:#ff5a66; --accent-soft:#331518; --accent-soft-2:#471c21; --accent-text:#ff7a83; --accent-on:#2a0d10;
}
```

---

## 5. 暖沙金 `warm-sand`

**定位**：温暖高级、编辑感/年报感。米白暖底 + 古铜金强调，衬线标题。
**适用**：年度报告、品牌叙事、文化建设、价值观。
**语汇**：编辑/年报 · **serifDisplay** · 圆角 12 · 宽松行高 1.72 · gap 略放 · 阴影极轻。

```css
html[data-style="warm-sand"] {
  --font-body: "Inter","Source Han Sans","PingFang SC","Microsoft YaHei",-apple-system,sans-serif;
  --font-display: "Georgia","Playfair Display","Songti SC","STSong","SimSun",serif;
  --radius: 12px; --fw-display:600; --fw-title:600;
  --letter-display:-.01em; --letter-eyebrow:.13em; --lh-body:1.72; --lh-lead:1.65;
  --gap:clamp(18px,1.8vw,30px);
  --bg:#fbf9f6; --surface:#ffffff; --surface-1:#f6f2ec; --surface-2:#efe9df; --surface-3:#e6ded2;
  --surface-inv:#2a2521; --text:#2a2521; --text-2:#6b5f52; --text-3:#93836f; --text-inv:#f6f2ec;
  --border:#e0d7c9; --border-soft:#eae3d6;
  --accent:#96681f; --accent-soft:#f3ecdd; --accent-soft-2:#eaddc4; --accent-text:#8f6117; --accent-on:#ffffff;
  --shadow-1:none; --shadow-2:0 1px 3px rgba(42,37,33,.08);
}
html[data-style="warm-sand"][data-theme="dark"] {
  --bg:#15120e; --surface:#15120e; --surface-1:#1d1913; --surface-2:#26201a; --surface-3:#312920;
  --surface-inv:#ece5db; --text:#ece5db; --text-2:#c4b8a8; --text-3:#9b8d7a; --text-inv:#2a2521;
  --border:#3a3128; --border-soft:#2c261e;
  --accent:#d9b36a; --accent-soft:#2e2417; --accent-soft-2:#3e3019; --accent-text:#e0c184; --accent-on:#2a1f10;
}
```

---

## 6. 墨绿 `deep-teal`

**定位**：沉稳、可信赖。冷灰底 + 深青强调。
**适用**：金融、风控、ESG、可持续、审计。
**语汇**：金融可信 · Inter/Source Han 栈 · 圆角 12 · 同字族 · 密度 normal。

```css
html[data-style="deep-teal"] {
  --font-body: "Inter","Source Han Sans","PingFang SC","Microsoft YaHei",-apple-system,sans-serif;
  --font-display: var(--font-body);
  --radius: 12px; --fw-display:700; --fw-title:600;
  --letter-display:-.028em; --letter-eyebrow:.11em; --lh-body:1.66; --lh-lead:1.6;
  --bg:#ffffff; --surface:#ffffff; --surface-1:#f2f6f5; --surface-2:#e8f0ef; --surface-3:#dce7e5;
  --surface-inv:#14201e; --text:#14201e; --text-2:#4a5a57; --text-3:#73837f; --text-inv:#ffffff;
  --border:#cfdedc; --border-soft:#e0eae9;
  --accent:#0f6b5c; --accent-soft:#e4f1ee; --accent-soft-2:#cfe5e0; --accent-text:#0d5a4e; --accent-on:#ffffff;
}
html[data-style="deep-teal"][data-theme="dark"] {
  --bg:#0d1312; --surface:#0d1312; --surface-1:#131b1a; --surface-2:#1a2523; --surface-3:#22302d;
  --surface-inv:#e2ecea; --text:#e2ecea; --text-2:#b3c2bf; --text-3:#86948f; --text-inv:#14201e;
  --border:#293834; --border-soft:#1e2a27;
  --accent:#4fc3b0; --accent-soft:#12312c; --accent-soft-2:#1a423b; --accent-text:#66cfbd; --accent-on:#0c2420;
}
```

---

## 7. 石墨深灰 `graphite-dark`（深色优先）

**定位**：深色优先的沉浸石墨风。近黑石墨面板 + 亮蓝青强调，**默认即深色**；浅色变体为「石墨纸灰 + 同系蓝青」，供打印/外发辅助。
**适用**：产品发布会、指挥中心大屏、深色优先场景。
**深色优先的落地**：架构模式模板（默认风格即 graphite-dark）出厂 `data-theme="dark"`；其他模式选用本风格时，交付前建议切到 dark（或向用户明示浅色为辅助变体）。浅色变体的灰阶为**中性石墨灰**（不带蓝味），与商务蓝的白底纯蓝拉开辨识度；强调色为深蓝青（与 dark 侧亮蓝青 #4da3ff 同系）。

**语汇**：沉浸石墨 · Inter/SF 栈 · 圆角 14 · 密度 dense · 深色阴影更沉 · gap 紧。

```css
html[data-style="graphite-dark"] {
  --font-body: "Inter","SF Pro Text","PingFang SC","Microsoft YaHei",-apple-system,sans-serif;
  --font-display: "Inter","SF Pro Display","PingFang SC",sans-serif;
  --radius: 14px; --fw-display:700; --fw-title:600;
  --letter-display:-.03em; --letter-eyebrow:.1em; --lh-body:1.62; --lh-lead:1.55;
  --gap:clamp(14px,1.4vw,24px);
  --bg:#f4f5f7; --surface:#ffffff; --surface-1:#eceef1; --surface-2:#e3e6ea; --surface-3:#d8dbdf;
  --surface-inv:#14171b; --text:#1a1d21; --text-2:#4b5158; --text-3:#767c84; --text-inv:#eef2f6;
  --border:#ced1d6; --border-soft:#e3e6ea;
  --accent:#0369a1; --accent-soft:#e2eff7; --accent-soft-2:#c8e1f2; --accent-text:#075985; --accent-on:#ffffff;
}
html[data-style="graphite-dark"][data-theme="dark"] {
  --bg:#0b0e12; --surface:#12161b; --surface-1:#171d24; --surface-2:#1f2732; --surface-3:#28323f;
  --surface-inv:#eef2f6; --text:#eef2f6; --text-2:#b9c2cd; --text-3:#85909d; --text-inv:#12161b;
  --border:#2b3540; --border-soft:#212932;
  --accent:#4da3ff; --accent-soft:#132841; --accent-soft-2:#1a3a5e; --accent-text:#6fb2ff; --accent-on:#07182b;
  --shadow-1:0 1px 2px rgba(0,0,0,.5); --shadow-2:0 4px 12px rgba(0,0,0,.45);
}
```

> **深浅两套变体的分工**：dark 是本风格的主面孔（沉浸/大屏/发布会）；light 是辅助（打印/外发/明亮环境）。风格画廊（`style-gallery.html`）中本风格卡片以 dark 为主预览、light 为辅助条，直接传达这一分工。

---

## 8. 靛紫 `indigo-violet`

**定位**：创新、前沿。冷白底 + 靛紫强调。
**适用**：AI、科技、研发、创新、前沿技术。
**语汇**：科技前沿 · Inter/SF 栈 · 圆角 16 · 轻快字距 · 密度 normal。

```css
html[data-style="indigo-violet"] {
  --font-body: "Inter","SF Pro Text","PingFang SC","Microsoft YaHei",-apple-system,sans-serif;
  --font-display: var(--font-body);
  --radius: 16px; --fw-display:700; --fw-title:600;
  --letter-display:-.032em; --letter-eyebrow:.12em; --lh-body:1.68; --lh-lead:1.62;
  --bg:#ffffff; --surface:#ffffff; --surface-1:#f4f4fb; --surface-2:#ececf7; --surface-3:#e0e0f0;
  --surface-inv:#1b1a2e; --text:#1b1a2e; --text-2:#52506b; --text-3:#7a779a; --text-inv:#ffffff;
  --border:#d7d7e8; --border-soft:#e6e6f2;
  --accent:#5b5bd6; --accent-soft:#ececf9; --accent-soft-2:#dcdcf3; --accent-text:#4848c0; --accent-on:#ffffff;
}
html[data-style="indigo-violet"][data-theme="dark"] {
  --bg:#100f1c; --surface:#100f1c; --surface-1:#171629; --surface-2:#1f1e36; --surface-3:#292845;
  --surface-inv:#e6e5f5; --text:#e6e5f5; --text-2:#b6b4d4; --text-3:#8b89b0; --text-inv:#1b1a2e;
  --border:#322f52; --border-soft:#262441;
  --accent:#a5a4f0; --accent-soft:#232146; --accent-soft-2:#2e2c58; --accent-text:#b6b5f5; --accent-on:#171631;
}
```

---

## 9. 光谱彩色 `spectrum`（彩色定位 · 数据色板以彩色为主）

**定位**：中性结构 + 彩色的 5 色数据色板。图表、图例、小段标签"出彩"，页面骨架依然安静。
**适用**：数据密集汇报、运营复盘、大屏看板、多系列对比。

**彩色边界（9 套风格同一条纪律）**：
- 彩色**只**出现在：图表数据系列（`.f-c1~c5` / `.s-c1~c5`）、图例 chip、小段标签、仪表盘/环形分段。
- **不用**彩色的地方：标题、正文、边框、按钮、大面积底色、卡片背景——这些全部保持中性 + 单一 `--accent`。
- 同屏彩色数据系列 ≤ 5；超过就合并为"其他"。
- **9 套风格各有自己的 `c1–c5`**（单源 `styleDataColors`，见第 11 节与 `design-system.md` §9b）——本风格只是把彩色作为**定位**（`c1` = 强调色），并不是"唯一能出彩的风格"。

**语汇**：数据看板 · Inter/SF 栈 · 圆角 14 · 密度 dense · 紧凑 gap · 行高略紧。

```css
html[data-style="spectrum"] {
  --font-body: "Inter","SF Pro Text","PingFang SC","Microsoft YaHei",-apple-system,sans-serif;
  --font-display: var(--font-body);
  --radius: 14px; --fw-display:700; --fw-title:600;
  --letter-display:-.03em; --letter-eyebrow:.1em; --lh-body:1.6; --lh-lead:1.55;
  --gap:clamp(12px,1.2vw,20px);
  --bg:#fbfcfe; --surface:#ffffff; --surface-1:#f4f6fa; --surface-2:#eceff5; --surface-3:#dfe4ec;
  --surface-inv:#171a21; --text:#171a21; --text-2:#4d5566; --text-3:#7b8494; --text-inv:#ffffff;
  --border:#d6dce6; --border-soft:#e6eaf1;
  --accent:#4563ef; --accent-soft:#eceeff; --accent-soft-2:#d8defb; --accent-text:#3d5bef; --accent-on:#ffffff;
}
html[data-style="spectrum"][data-theme="dark"] {
  --bg:#0e1116; --surface:#131720; --surface-1:#171c26; --surface-2:#1d2330; --surface-3:#252c3b;
  --surface-inv:#e8ebf2; --text:#e8ebf2; --text-2:#a7afbf; --text-3:#7e8798; --text-inv:#171a21;
  --border:#2b3342; --border-soft:#212839;
  --accent:#8ba0f8; --accent-soft:#1b2242; --accent-soft-2:#26305c; --accent-text:#93a7f9; --accent-on:#141a38;
}
```

> **编码色板（`--c1..--c5`）不在本节重复列出**：9 套风格各自的 5 色由单源 `styleDataColors` / `styleDataColorsDark` 注入 `engine.css` 覆盖块（第 11 节），避免两处维护。

---

## 10. 为什么是 9 套（风格集的准入门槛）

> **风格集刻意保持 9 套**：覆盖 8 个色族（蓝 / 藏青 / 蓝青深色 / 黑白 / 红 / 金棕 / 墨绿 / 紫）+ 1 个彩色数据板，任意组合已足够。
> **每多一套风格的真实成本**：单源 5 张表（`styles` / `stylesDark` / `styleAccents` / `styleDataColors` / `styleDataColorsDark`）× 亮暗 + `engine.css` 4 个块 + `ui.js` 色板 + 画廊卡片 + 参考图重生成 + 审计与回归全跑一遍。**选项冗余不是免费的。**

**新增一套风格的门槛（三条全满足才加）**：

1. **新色族**——引入现有 8 族之外的色相族，而不是同族换明度 / 换名；
2. **新语汇**——带来新的字体搭配（衬线 / 等宽）或新的圆角、阴影语汇；
3. **场景缺口**——现有 9 套无法覆盖的真实场景，且能给出反例。

> **反面教材**：同色族换名的风格（曾扩到 18 套后删回 9 套）——选项冗余有真实成本。新增门槛见 §10。
> 这 9 套与前 9 套**同色族换名**（蓝 / 红 / 绿青 / 金棕 / 无彩各多一份），既未引入新色族，也未引入新语汇 → 属于"看上去有用、实际低价值"的选项冗余。
> 需要"政企庄重 / 东方雅致 / 环保自然"等气质时，用现有 9 套的**组合**近似：`brand-red`（宋体标题）→ 政企庄重；`mckinsey` / `warm-sand`（衬线标题）→ 东方雅致 / 编辑感；`deep-teal` → ESG / 可持续。

**配色纪律不变**：除 `spectrum` 外每套**只有一个强调色**，层次靠表面明度差 + 1px 边框；`styleAccents` 收录各套 light/dark 强调色（含派生 hover/active 色），供 `validate_report.py` 做「单一强调色」检查。

---

## 11. 编码色板（每套风格各 5 色 · 数据专用）

> **9 套 ≠ 9 种皮肤而已**：每套风格都带自己的**编码色板 `c1–c5`**，用于多系列图表（多段环形 / 分组柱 / 多折线 / 散点分组 / 桑基流带 / 马赛克段）。这样"数据密集报告"在任何风格下都能出彩色系列，而**结构色仍保持单一强调色**。

| 项 | 说明 |
|----|------|
| 单源 | `scripts/layout-constants.json` 的 `styleDataColors`（light）/ `styleDataColorsDark`（dark），各 9 套 × 5 色 |
| HTML 消费 | `engine.css` 的 `html[data-style="X"]{--c1..--c5}` 覆盖块 → 语义类 `.f-c1~c5` / `.s-c1~c5`（由 `sync_runtime.py` 注入模板） |
| PPTX 消费 | `build_pptx.js` / `pptx-export.js` 的 `dataColors(style, theme)`（按 `model.theme` 选 light/dark 表） |
| 生成规则 | `c1` = 该风格强调色；`c2`/`c3` = 近似色（±32°/±38°）；`c4`/`c5` = 降饱和补色（168°/205°，饱和度 ×0.6） |
| 硬约束 | 每色对所在主题 `bg` 对比度 ≥ 3.0；同套内两两色相差 ≥25° 或明度差 ≥0.12（`audit_styles.py` 逐值校验） |
| 色值格式 | **一律裸 hex（6 位、不带 `#`）**，与 `styles` / `stylesDark` / `styleAccents` 同口径；`#` 前缀会原样流入 PPTX 的 `<a:srgbClr val>` 造成非法色值，`engine.css` 覆盖块与画廊才补 `#`（`audit_styles.py` 校验 + `validate_pptx.py` 的 `INVALID_HEX_COLOR` 硬拦） |
| 使用边界 | 彩色**只**出现在数据本体（数据系列 / 图例色点 / 小段标签）；同屏 ≤5 系列。**状态类表达（好/坏、达标/未达标、涨/跌）不得用红绿**，仍走强调色明度阶梯 |

改色值只改 JSON → 跑 `python scripts/sync_runtime.py`（注入 engine.css 消费端已在 JSON 单源内）→ `python scripts/audit_styles.py`。

---

## 新增一套风格的步骤

> **先过第 10 节的门槛**（新色族 + 新语汇 + 场景缺口，三条全满足）——否则不加。

1. 在「快速选型」表加一行（中/英文名 + data-style + 定位 + 适用 + 族）。
2. 选一个**中性色族**（冷灰/暖灰/纯黑白）+ 一个**强调色**，写 light + dark 两个覆盖块。
3. 定**风格语汇**（缺一即「只有皮肤没有性格」）：字体栈 `--font-body` / `--font-display`、圆角 `--radius`、字阶微调（`--fs-*`）、字距/行高（`--letter-*` / `--lh-*`）、密度（`--gap`）、阴影、必要时 `--link`。
4. **六处同步**（缺一即漂移）：
   - `scripts/layout-constants.json` → `styles`（light 10 字段）+ `stylesDark`（dark 10 字段）+ `styleAccents`（强调色族）+ **`styleIdentity`（语汇清单）** + **`styleDataColors` / `styleDataColorsDark`（编码色板 c1–c5，见第 11 节）**
   - `assets/templates/engine.css` → `html[data-style="X"]{…}` + `html[data-style="X"][data-theme="dark"]{…}` + **编码色板两个覆盖块（`--c1..--c5`）**——语汇 token 必须落在 light 块
   - `assets/templates/ui.js` → `var STYLES` 数组加一项（`['id','中文名','#亮色accent']`）
   - 本文件速查表 + 各节 CSS（语汇与 engine 逐字一致）+ 第 11 节编码色板表
   - `assets/style-gallery.html` 画廊 `STYLE_META` 描述行（`pfontBody`/`pfontDisplay`/`prad`/`pscale`/`peye`/`plh`/`pgap`/`pw`/`pletter`；配色由注入的 `PRESETS` 自动派生）
   - `references/design-system.md` 字体决策矩阵（若引入新字体语汇）
5. 跑 `python scripts/sync_runtime.py`（注入到三模板与画廊）→ `python scripts/audit_styles.py`（**9 套** × light/dark × 8 组 WCAG + 双源色 token + 编码色板 + ui.js 色板 + **风格语汇 styleIdentity**，全过才通过）→ `python scripts/build_examples.py` → `python scripts/regression.py`。
6. 可选：`node scripts/capture_theme_overview.js`（需 playwright）重生成 `assets/theme-overview*.png` 参考图。
