# 风格包格式（新增一套风格）

> **何时读**：新增第 10+ 套风格时。风格 token 单源 `scripts/layout-constants.json`，变更后同步与审计见 SKILL.md §12 双单源纪律。

## 新增一个风格 = 改 1 个文件 + 跑 2 条命令

### 1. `scripts/layout-constants.json`（唯一手工改动点）

| 位置 | 必填 | 内容 |
|------|------|------|
| `styles.<name>` | ✅ | 10 token：`accent / ink / body / faint / bg / surface / line / soft / onAccent / font`（另有 `fontDisplay`，缺省同 `font`）。hex **不带** `#` |
| `styleDataColors.<name>` | ✅ | 数据系列色板 `c1–c5`（5 个 hex，不带 `#`；禁与 accent 同色相挤占） |
| `stylesDark.<name>` | 推荐 | 暗色版 10 token（缺省则暗主题回落 light，被 audit 记 WARN） |
| `styleDataColorsDark.<name>` | 随暗色 | 暗色数据色板 |
| `styleAccents.<name>` | ✅ | 该风格全部合法强调色 hex 数组（含 accent 及派生 hover/active）；`validate_report` 用它查"第二色相" |
| `styleIdentity.<name>` | 推荐 | 一句话风格定位（画廊/文档用） |

token 语义：`accent` 唯一强调色（图表主色/链接/图标色）；`ink` 标题墨；`body` 正文；`faint` 次要文字；
`bg` 页底；`surface` 卡面；`line` 分隔线；`soft` 浅强调底；`onAccent` 强调色上文字（保证对比度）。

### 2. 同步与门禁（必跑）

```bash
npm run sync    # sync_runtime.py：把 token 注入 build_pptx.js / assets/pptx-export.js / 三模板
npm run audit   # audit_styles（对比度/色板一致性/单源）+ docs/skill/css 审计
```

### 3. 可视确认（推荐）

```bash
npm run capture-themes   # 重拍 assets/theme-overview*.png（含新风格）
```

并在 `assets/style-gallery.html` 的风格选择器里加一项（纯展示用）。

## 红线

- 不手改任何生成副本（`build_pptx.js` 内的 `PRESETS`、`pptx-export.js` 常量块、模板内联副本）——只改 `layout-constants.json`，由 sync 注入。
- accent 对比度：`onAccent` 在 `accent` 上 ≥ 4.5:1（audit_styles 强制）。
- 单风格单强调色：正文不得出现第二套风格的强调色（`validate_report` 按 `styleAccents` 查）。
