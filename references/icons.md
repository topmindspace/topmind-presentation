# 图标库（语义选型 · 克制取用）

> **何时读**：需要卡片头 / 列表行首 / 指标角标 / 提示条图标时。  
> **取码**：本节「高频取码」或 `python scripts/extract_snippet.py --task icons`。  
> **完整 SVG 枚举**（60+）：`../docs/archive/refs/icons-catalog.md`（生成默认**不**预读；仅当高频未覆盖语义时按名查阅）。

全部 24×24、描边（stroke 1.8，圆角线帽），`currentColor` 随主题变色。共 **48** 个，单源 `assets/icons/`（`*.svg` HTML 内联 + `*.png` 512px 预渲染供 PPTX），`index.json` 为关键词→图标映射 + 默认表。校验：`python scripts/check_icons.py`。

> **PPTX 通道（真导出）**：图标名写入模型 `cards[].icon`（或 HTML `data-icon` / hydrate 标记 `<i data-icon="名"></i>`），`build_pptx.js` 经 `icon_lib.js` 取 PNG 嵌入（优先 `icon-assets.json` 的 accent 着色版 → 回落 `assets/icons/*.png` 512px 预渲染 → 最后才回落 accent 小方块路标），与 HTML 同名同语义。`objectName` 前缀 `icon:`，`validate_pptx` 单独计数（`icon_pictures`），**不进** `pictures=0` 内容图门禁。图标名取值 = `assets/icons/index.json` 的键（48 个）。

## 使用准则（先读再用）

## 行业共识原则（商务演示 · 非装饰）

图标在正式商务演示文稿中是 **wayfinding（路标）**，不是插画墙。对齐常见咨询/产品 Deck 实践：

1. **语义先行**：每个图标必须能回答「这是哪一类信息」；换掉标题后图标仍应成立，否则删。
2. **同一家族**：全篇统一描边风（stroke ≈1.8、圆角线帽、`currentColor`）；禁混用填充风/emoji/三方彩色标。
3. **有限密度**：演示 3–8 / 研究 2–4 / 架构主图内 0；超过即噪音。
4. **位置克制**：只走四正当位置（卡头 / 关键列表 / 指标角标 / 提示条）；**Agenda 大编号、表格单元格、图表内部、正文行内**一律不用。
5. **一致性 > 个性**：同类信息复用同一语义图标（如「风险」全篇都用警告），不要每页换隐喻。
6. **可导出意识**：卡片头写 `data-icon` / 模型 `cards[].icon`，PPTX 真导出同名 PNG；缺省按标题语义自动挑选（`icon_lib.pickIconName`：关键词命中，选不出用默认表轮换）。

**选型铁律**：按内容选图标，选不出用默认；只在必须/有必要用图标的场景使用（四正当位置），不要为装饰而堆图标。

违反时：先减数量，再统一家族，最后才考虑换布局——不要靠堆图标补「空旷」。



**图标是信息路标，不是装饰。**

### Mode A 内容页落地（必做，非可选点缀）

含 **cards / points / key lists / note strips** 的内容页须在下表正当位置取用图标；showcase / scaffold / 引擎实践不得再交「零图标展板」。密度：演示 3–8 / 研究 2–4。门禁：`validate_report` 对「≥2 卡且无 `.card__ico`」发 **WARN**。

### 哪里用（四个正当位置）

| 位置 | 做法 | 效果 |
|------|------|------|
| **卡片头** `.card__ico` | 每张要点卡一个小图标 | 类型一眼可辨（最推荐） |
| **关键列表** `.ul--ico` | 行首小图标（`components.md` §7） | 3–5 条可扫读 |
| **指标卡** `.metric__ico` | 右上角小图标 | 规模/效率/质量区分 |
| **提示条** `.note__ico` | 真图标替代字母 `i` | 结论/警告/信息 |

### 禁区（哪里不用）

- **Agenda 大纲**——大编号已是路标
- **表格单元格**——破坏栅格对齐
- **图表内部**——系列用色，不用图标
- **正文行内**——打断阅读（引用标记除外）
- **装饰性堆砌**——一屏图标墙、与文案无关的插图风图标

### 尺寸档（唯一合法）

| 场景 | 尺寸 |
|------|------|
| 列表行首 `.ul--ico` | **16–18px**（默认 17） |
| 卡片头 `.card__ico` | **20–24px**（默认 18–20 视主题） |
| 指标角标 `.metric__ico` | **16–20px** |
| 行内特例 | `width:1em` |

光学中心对文字 x-height；图文距 `--sp-2`（8px）。同屏同尺寸。校验：`LAYOUT_ICON_SIZE`（∉ {16,18,20,24} → WARN）。

### 密度与一致性

- 每屏 **3–8** 个；research 减半（2–4）；architecture 主图内 0，图例旁 ≤2
- 长报告（≥6 页）至少一处 `.card__ico` 或 `.ul--ico`（否则 WARN）
- 全篇统一描边风 stroke 1.8；不改 `stroke="currentColor"`；彩色只属于数据系列

## 速查：按语义选图标

| 语义 | 选用（高频名） |
|------|----------------|
| 规模/底座 | 数据库、云/平台、文件夹/资产 |
| 效率/性能 | 仪表盘/效率、闪电/高效、时钟/时间 |
| 增长/成果 | 增长/上升、奖章/成果、旗帜/里程碑 |
| 风险/问题 | 警告、下降/回落 |
| 治理/安全 | 盾牌/安全、锁/权限 |
| 口径/规则 | 文档/报告、检查/对勾 |
| 组织/分工 | 用户/团队、架构/层级 |
| 流程/血缘 | 分支/流程、循环/飞轮 |
| 计划/路线 | 日历/计划、罗盘/方向、旗帜/里程碑 |
| 智能/Agent | 芯片/AI、火箭/发射 |
| 洞察/分析 | 搜索/洞察、灯泡/创意 |
| 建设/工具 | 扳手/工具、齿轮/设置 |
| 图表语义 | 柱状图、趋势/折线、环形/占比、表格/网格 |
| 沟通/联系 | 对话、邮件、手机、定位/地点 |
| 财务/资源 | 纸币/财务、时钟/时间 |
| 动作 | 右箭头、下载、上传、分享、链接 |
| 标记 | 五角星、书签、信息/提示、对勾 |
| 清单/条目 | 清单/条目 |
| 待核实 | 信息 |

选型顺序：**语义表 → index.json 关键词 → 高频取码**；命中不了用**默认表**（信息/检查/数据/图表/目标/团队/工具）轮换。

## 高频取码（压缩 SVG · 20，与 assets/icons/ 同源）

> 完整 48 见 `assets/icons/index.json`（关键词→图标映射 + 默认表）；归档旧目录 `../docs/archive/refs/icons-catalog.md` 仅备查。

**数据库**
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3"/></svg>
```

**柱状图**
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><rect x="7" y="12" width="3" height="6" rx="1"/><rect x="12" y="8" width="3" height="10" rx="1"/><rect x="17" y="4" width="3" height="14" rx="1"/></svg>
```

**趋势/折线**
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M7 14l4-4 3 3 5-6"/><path d="M15 7h4v4"/></svg>
```

**环形/占比**
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21.2 15.9A10 10 0 1 1 8 2.8"/><path d="M22 12A10 10 0 0 0 12 2v10z"/></svg>
```

**表格/网格**
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/></svg>
```

**仪表盘/效率**
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 15l3.5-5.5"/><path d="M20.2 15a8.5 8.5 0 1 0-16.4 0"/></svg>
```

**增长/上升**
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M22 7l-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/></svg>
```

**下降/回落**
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M22 17l-8.5-8.5-5 5L2 7"/><path d="M16 17h6v-6"/></svg>
```

**奖章/成果**
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="6"/><path d="M15.5 13 17 22l-5-3-5 3 1.5-9"/></svg>
```

**盾牌/安全**
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg>
```

**锁/权限**
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
```

**检查/对勾**
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 12.5l2.5 2.5L16 9.5"/></svg>
```

**警告**
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/></svg>
```

**用户/团队**
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
```

**架构/层级**
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="2" width="6" height="6" rx="1"/><rect x="2" y="16" width="6" height="6" rx="1"/><rect x="16" y="16" width="6" height="6" rx="1"/><path d="M12 8v4M5 12h14M5 12v4M19 12v4"/></svg>
```

**分支/流程**
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="8" r="3"/><path d="M6 9v6M18 11a9 9 0 0 1-9 4"/></svg>
```

**日历/计划**
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>
```

**闪电/高效**
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2 3 14h7l-1 8 10-12h-7l1-8z"/></svg>
```

**文档/报告**
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z"/><path d="M14 2v6h6"/><path d="M9 13h6M9 17h6"/></svg>
```

**搜索/洞察**
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
```
