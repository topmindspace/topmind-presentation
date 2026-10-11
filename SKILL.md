---
name: topmind-presentation
description: "把已有材料做成正式商务演示与多页可视化报告：零外链可翻页 HTML + 可编辑 16:9 PPTX 双交付；三模式（A 演示 / B 研究型版式 / C 架构）× 9 风格。Use when 用户要做演示、汇报、PPT、PPTX、slides、deck、路演、答辩、培训课件、项目汇报，或把调研、评测、对标、经营分析、咨询报告、白皮书等已有材料排成可翻页 HTML、网页报告或可编辑 PPTX，或做多页或要 PPTX 交付的架构图、拓扑图、流程图、泳道图、方案图，或优化报告的排版/版式/配色/图文布局；说快速模式/直接生成/一键出稿/少问一句走 Fast Mode。Do NOT use for 找资料、核事实、写研究结论（→ topmind-research）、整理工作区已存笔记或周复盘（→ topmind-organize）、工作区巡检与例行复盘（→ topmind-loop）、单张长图/信息图/榜单图（→ topmind-poster）、文章封面配图（→ topmind-cover）、改写已有 PPT/Word 源文件（→ 官方 pptx/docx 技能）、纯代码工程、非报告类网页或应用开发、视频/图片生成。"
license: MIT
compatibility: "Python 3 stdlib for HTML generation; Node >=18 + pptxgenjs for PPTX; optional playwright for browser regression / theme captures."
metadata:
  version: "0.2.7"
  author: TopMindSpace
  updated: "2026-10-11"
  action_category: write
  triggers: 演示, 汇报, PPT, PPTX, slides, deck, 路演, 答辩, 培训课件, 可视化报告, 网页报告, 商务演示, 架构图, 流程图
---
# topmind-presentation · 商务演示与可视化报告

为**演示报告 / 正式商务演示**而生：**HTML + PPT 双交付**（日常可翻页 HTML；需要时导出可编辑 PPTX）。MD3 密度克制，一屏一重心。内容唯一源 `REPORT_MODEL`；**B 通道** `build_pptx.js` 交付，**A 通道**仅预览/`cross_verify`。

**分工**：只管版式与交付，不找资料、不核事实；材料来自 topmind-research 时沿用其数字与来源（铁律 10）。

## Gate 0 · 先给参考图（**标准模式**硬门禁）

用户表达做报告意向后，**第一件事**展示参考图，再进入六项问询：

| 给什么 | 路径 | 何时 |
|--------|------|------|
| 整体图（默认） | `assets/theme-overview.png` | 每次开场 |
| 按模式拆分 | 演示/研究/架构 → 整体图/`-research.png`/`-architecture.png` | 模式已明确 |
| 交互画廊 | `assets/style-gallery.html` | 用户想边看边挑 |

**标准模式**：跳过参考图直接问询 = 不合格。**Fast Mode**（下节）豁免 Gate 0 与六项。

## Fast Mode · 快速模式（用户显式 opt-in）

触发词即进入（**跳过 Gate 0 与六项**）：`快速模式` / `fast` / `直接生成` / `一键出稿` / `fast mode` / `少问一句`。

| 参数 | 默认 | 推断 |
|------|------|------|
| mode | **B** | 路演/汇报/发布/演讲/demo/融资/宣讲→A；架构/拓扑→C；未点明→B |
| style | B→mckinsey · A→business-blue · C→graphite-dark | |
| theme | light（graphite→dark） | |
| 篇幅 | A=10 / B=12 / C=6 | |
| format | **html only**（用户要 PPT/PPTX 才开 B 通道） | |

**跳过** Gate 0/六项/完整大纲；**仍须**最小大纲→模型单写→strict 0/0→`quality_gate --deliver`（反截断、图表多样、Mode A craft 不降）。L0+L1（A/Fast 可加 L1.5）；一行宣布「Fast 选用：…」→ playbook §二；声明已跳过参考图。**标准模式**仍强制 Gate 0 + 六项。

## 唯一入口流程

```
听意图 → [Fast? 快路径] : [Gate 0 → 六项（1 轮）→ 内容架构]
      → 起骨架 → 模型单写（禁改 HTML 正文）→ 脚本回填 → strict 0/0 → 交付
```

**预算（硬）**：交互轮次 **≤3**；**L0+L1 共 2 份**（本文件 + `playbook.md`）；A/Fast 可加 L1.5（`default-surface.md`+`presentation-craft.md`）。其余 L2 命中才读、不预读。

## 六项问询（标准模式 · 一次问完 · 唯一形式参数确认）

用户表达意图后**一次问完六项**，每项带意图推荐；用户不选即按推荐执行，不再追问。

1. **意图与模式**：演示/汇报→A；研究/调研→B；架构/拓扑→C；混合选主模式（判据见 `modes.md`）。
2. **篇幅**：A 8–15 页 / B 12–25 页 / C 6–8 页（1–3 张图）；有材料按材料量推荐。
3. **风格（始终选择）**：默认商务蓝；B 推荐麦肯锡/墨绿/暖沙金；C 推荐石墨深灰/商务蓝/彩色；拿不准看 Gate 0 参考图。
4. **亮暗主题（始终确认）**：浅色默认（打印/外发）/ 深色（大屏/发布会）；石墨深灰出厂深色；`REPORT_MODEL.theme` 贯穿 HTML 与导出。
5. **交付格式**：仅 HTML（默认）/ HTML+PPTX（**B 通道**）。
6. **参考图确认**：复述 Gate 0 路径，确认用户已看到。

**载体**：优先结构化选项卡一次收集，否则对话文本一次列全。此后形式层面不再反复确认；内容层面按需一次大纲确认。

## 两条路径（先判定，再动手）

| 路径 | 何时 | 多做什么 |
|------|------|---------|
| **轻量**（默认） | 页数不多、材料单一完整、关键判断已敲定 | 最小大纲 → 1 张规划卡（`outline-design.md`「轻量最小集」） |
| **完整** | 长篇、材料杂、含未敲定关键判断、用户要看框架 | 证据盘点 → 故事线 → 主张树 → 逐页规划卡 → 大纲确认（1 轮） |

精确判定条件与完整步骤详见 playbook §二。完整路径确认只做一次；确认后只改指定处。

## 变更与中断（过程可控 · 不重启六项问询）

| 情形 | 处理 |
|------|------|
| 只改风格/亮暗 | header 即切 → 同步 `REPORT_MODEL.style/theme` → 重跑校验；**不重写内容** |
| 加页/减页 | 只动受影响页 + Agenda + 编号 + 页码；重跑校验 |
| 换模式 A↔B↔C | 不可就地改：保留证据/数字/结论，按目标模式重排；仅重确认篇幅 |
| 对话中断后续写 | 用提取脚本取回模型后重渲染，**不要从零重写** |
| 校验不通过 | 按**修复指引**逐条改；2 轮不收敛才升级读 `failure-modes.md` |

## 阶段路由（渐进式披露）

> 披露分层（机器可读）：`L0=SKILL.md` · `L1=references/playbook.md` · `L2=按需`
>
> **纪律**：L0+L1 是默认全部所需；**只在命中"何时读"时才打开 L2，读完即执行、不预读**。取代码**一律** `extract_snippet.py`（`--list` / `--task` / `--chart` / `--page-type` / `--file --section`）。**整读大 L2 文件 = FAIL**（禁令清单见 playbook §十）。

**L2 索引**（命中条件与逐任务只读清单详见 playbook §十）：

- 模式契约与锁定版式 → `references/modes.md` · 完整路径七步 → `references/outline-design.md`
- A/Fast L1.5 → `default-surface.md` + `presentation-craft.md` · 骨架 `layout-grammar.md` · 插画规范 → `illustration-layout.md`
- 组件/版式**代码** → `components.md` · 页型表 `page-type-matrix.md` · 图表门面 `charts.md` + 决策树 `chart-decision-tree.md` · 信息图 → `infographics.md`
- 配色/主题/字阶 → `styles.md` + `design-system.md` · 写作 → `content-rules.md` · 图标语义 → `icons.md`（48 原创图标包 `assets/icons/`：HTML 内联 SVG / PPTX 用 PNG；`icon:<名>` 或 `data-icon`；按内容选图标，选不出用默认 7 个）
- 风格包 → `references/style-pack.md`（`layout-constants.json` token 单源）· 布局变体 → `references/layout-variants.md`（`layoutVariants` 注册表：`bento-grid` / `timeline` / `2-col-feature`，section 字段 `variant` 指定）
- PPTX 精导 → `references/pptx-export.md` · 深度高保真 → `references/high-fidelity.md` · 修复顺序 → `references/failure-modes.md` · 技能维护 → `references/tech-design.md`

**操作方式**：定模式/页型/组合/图 → 只读 `playbook.md`；取代码 → **必须** `extract_snippet.py`。整读 = FAIL：`layouts-combo` / `components-atoms` / `charts-basic` / `charts-extended` / `content-rules` 全文 / `pptx-export` / 模式模板 HTML（走 scaffold）。

## 铁律（12 条 · 交付硬门禁）

> 门禁语义；阈值见 playbook 与 layout 常量 JSON。**motion=none**（无炫技转场）。

1. **单文件零外链**——无 CDN/外部字体/外部图片；图形一律内联 SVG；`<img src>` 仅 `data:` 或带 `alt` 的相对路径（单图 ≤1.5MB、全篇 ≤8MB）；无素材图用配图占位（`components.md` §11c-3），不留空。
2. **模式先定后写**——从对应模式模板起步；`data-mode` = `REPORT_MODEL.mode`；页面无模式切换；PPTX 字号走三模式独立比例尺。
3. **亮暗双主题一致**——CSS 变量整块换肤 + header 切换 + 文件级记忆；`REPORT_MODEL.theme` 与页面一致，PPTX 同主题导出；强调带只用 accent 家族；**末页禁 `band--deep`**。
4. **每页一屏 + 高度稳定**——`section.band` ≥ 一屏；主内容不得溢出画布或压进结论条/注释带。放不下按「重构承载 → 拆页/分章 → 换布局形态 → 有限缩字号」；**禁**静默截断或为疏朗删结论条/证据。**大纲 = 3–7 章（每章 1+ 页），禁逐页标题罗列**。结论条 = MD3 tonal surface（无「So what」标签、**无左侧 accent 轨**）。**内容覆盖率**：模型文本 → 渲染文本 ≥95%（`validate_report.py` WARN；标点不计，8 字窗口部分计分）；**PPTX 弹性文本**：长标题/列表/表格按 `layout-constants.json → containers.adaptiveText` 单源规则自动收紧字号/间距（标题按字符量分档、列表按条目数、表格有字号上限与行高下限）。
5. **PPT 式翻页 + 骨架固定**——`section.band` 即一页；方向键翻页、页码可点；Agenda 第二页（arch 内容页 ≤4 可省）；页头只留 eyebrow+标题+可选导语，页脚全文一个。
6. **标题与字号**——主标题粗体；research=结论句（≥12 字）；**presentation=主张/行动句**（禁话题标签）；字号随模式，`clamp()`；图表不缩水。
7. **组合版式 + 细节保全**——默认一页 = 主件+从件+注释层；先判定决策必需信息再定形态，**禁砍口径列/时间列/维度**；密度 L/M/H 禁连续 3 页同档；同一版式不连用超 2 页。
8. **列表优先 + 去 AI 味 + 图标克制**——大段文字转列表（research 双/三栏正文除外）；`aiFlavor` 词表零命中；图标每屏 3–8 个；**按内容选图标**（`assets/icons/` 48 个，`icon_lib.js` 按关键词/标签匹配），选不出用 7 个默认图标；**只在必须/有必要用图标的场景使用，不要为装饰而堆图标**。
9. **图表够大 + 够多样 + 双通道**——尺寸 ≥ `charts.minSize`；`data-chart` 须在 `charts.registry`（36 种）登记；多样性下限与相邻不同型按 `charts.variety`（playbook §五）；原生通道 `addChart` 双击可编辑数据，形状通道按登记策略附数据表。
10. **引用与待核实**——外部数据 `[n]` + 文末参考资料（来源+时间+口径）双向对齐；**只列真实来源，无则省略整节，禁占位**；research 关键图表 Exhibit N 连续编号 + 来源行；`.tbd` 强调色必须配图例，单页 ≤12 处；只标色不解释即不合格。
11. **容器级门禁 + 语义字号**——溢出按**归属容器**判定，越过容器即失败；容器保留内边距，不缩字号解溢出；表格正文用 `body`，`micro` 只给轴标签/单位/短标签；连续句不拆文本框。
12. **双单源 + 校验闭环**——schema 只改 `scripts/model-schema.json`，其余常量只改 `scripts/layout-constants.json`，改后必跑 `sync_runtime.py`（禁手改注入副本）；**HTML strict 0/0 才交付**；带 PPTX 加验 `validate_pptx.py --strict --model=` 0/0；页面只提供「预览 PPTX」与提示词，不做文件导出。

## 交付物与验收

- **HTML**：零外链可翻页、每页一屏。Header 工具栏：**T** 亮暗（按文件记忆，同步 `REPORT_MODEL.theme`）/ 9 套风格（实时换肤，交付前写回 `REPORT_MODEL.style`）/ **P** 预览 PPTX（页序列+精导提示词）/ **H** 生成指引 / **F** 全屏 / **B** 折叠。改风格/主题后同步 `REPORT_MODEL` 并重跑校验（不重写）。
- **PPTX（B 通道）**：`extract_model` → `build_pptx.js` → `validate_pptx --strict`；16:9 可编辑。**A 不交付**（仅预览/`cross_verify`；playbook §九）。
- **验收**：HTML strict 0/0；含 PPTX 再加 PPTX 0/0；失败给定向修复指引。
- **交付说明**：`quality_gate.py --deliver`（PPTX 带 `--pptx/--model`）出七要素，缺一 FAIL。

## 环境依赖

- **零依赖可用**：HTML 与全部 Python 脚本仅用标准库。
- **PPTX 精导**：Node + pptxgenjs（`TOP_PPT_NODE_EXE`/`TOP_PPT_NODE_PATH`；见 `pptx-export.md`）。
- **硬门禁**：标签泄漏/空页/极偏图/简单大图 → `layout-constants.json` + `failure-modes.md`。
- **可选**：参考图重生成需 playwright（`regression.py` 探测，缺失跳过）。
- **回归/自检**：`regression.py`、`audit_*.py`。
