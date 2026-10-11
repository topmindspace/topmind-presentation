# 失败模式库（交付前自检）

> **何时读本文**：生成完成、跑完校验脚本后，若想确认"没有踩坑"，按本文**二十类**模式逐条对照；或当校验器报出某类问题时，查本文的**修复顺序铁律**（先改什么、不要改什么）。
> 本文与校验器一一对应：每类模式给出**识别信号 → 校验器错误码 → 修复动作**。
> F1–F14 为结构/导出/内容硬缺陷；F15–F16 为内容节奏与导出诚实性；F17 为 v9 截图级缺陷；F18 为截断/溢出/半空卡；F19 为几何叠印/同槽双条（PPTX 导出硬伤）；F20 为 Agenda 容量/图表退化/图标缺失。

## 一、二十类失败模式

### F1 内容不足 `underfill`

- **识别**：页面只有标题 + 一两行字；指标卡/图表缺失；so-what 空洞（"需要持续关注"）。
- **错误码**：`LOW_CONTENT_DENSITY` / `LOW_TEXT_DENSITY` / `EMPTY_OR_UNMEASURABLE_SLIDE`
- **根因**：材料没读透就动笔；或把论证该有的"证据 + 含义"省略了。
- **修复**：回 `outline-design.md` §二 的承载工具选型矩阵，给该页补上**证据**（数据/表/图）与**含义**（so-what）。不要用装饰补空白。

### F2 装饰替代 `decorative_substitution`

- **识别**：用大色块、无意义图标墙、渐变条、装饰圆点填版面；用"看起来丰富"代替"信息丰富"。
- **错误码**：`UNBALANCED_EMPTY_SPACE`（留白失衡）/ `LOW_TEXT_DENSITY`
- **根因**：内容不够但不想承认，用装饰充数。
- **修复**：删掉装饰，改**信息结构**——换更高密度的承载（列表→表→图），或合并到相邻页。

### F3 密度塌陷 `density_collapse`

- **识别**：表格字号没低于下限，但单元格大面积空洞、阅读重心塌陷、页面显空。
- **错误码**：`TABLE_DENSITY`
- **根因**：为了"塞下"而拆行/拆列，把一张密表摊成稀疏网格。
- **修复**：**合并行列**（同类项归并）、**提高信息粒度**（补关键列：同比/口径/结论）、或换承载形态（密表 → 指标墙 + 附录全量表）。

### F4 容器溢出 `container_overflow`

- **识别**：文字越过卡片/面板/结论条/表格单元格/so-what 框的边界——**即使没有超出页面画布**。
- **错误码**：`CONTAINER_OVERFLOW` / `TEXT_OVERFLOW_ESTIMATE` / `SHAPE_OUTSIDE_SLIDE`
- **根因**：按"页面够不够"判断，而不是按"归属容器够不够"；或内容未先列表化/精炼就硬塞。
- **修复顺序**（见 §二）：① 优化内容（列表化/精炼/合并）→ ② 调整容器尺寸/行宽/换行/分区 → ③ **有限缩字号**（`containers.fontShrink`：最多 4 档，floor presentation/arch 10pt、research 9pt）→ ④ 仍装不下拆页。禁止无限缩字号，也禁止为过检直接砍决策必需信息。

### F5 文本拆流 `split_flow`

- **识别**：语义连续的一句话被拆成多个独立文本框，产生异常空格、断句、基线漂移。
- **错误码**：`CONTINUOUS_TEXT_FLOW`（深度模式）
- **根因**：为了局部加粗/变色高亮，把一句话切成两个文本框。
- **修复**：合并为**同一文本框内的富文本**（HTML `<strong>`；PPTX 同一 `addText` 的多 run）。数字 + 单位 + 括号注释属同一语义单元，不得拆开。

### F6 图表降级 `chart_downgrade`

- **识别**：带数据的图表被做成"形状拼图"（不可编辑数据）；或非原生图表没有附数据表；或曲线语义图被矩形化。
- **错误码**：`MODEL_CHART_COUNT`（原生通道未落成 chart part）/ `MODEL_CHART_DATATABLE`（非原生图表无数据表）/ 校验器的图表登记与最小尺寸检查
- **根因**：为了省事把图表画成矩形条，或忘了 `chart.dataTable` 策略。
- **修复**：能原生的类型走 `addChart`（双击可"编辑数据"）；非原生类型按 `infographics.md` 的形状还原规则绘制（采样点 ≥16、双边界追踪、禁预设形状），并至少 `dataTable: notes`。

### F7 位置漂移 `position_drift`

- **识别**：页头标题没对齐版心左边界；同类元素跨页位置不一致；图标/标签相对节点偏移。
- **错误码**：`ANCHOR_TITLE_MISALIGNED`（深度模式）
- **根因**：用"目测居中"代替网格对齐；或复制上一页时忘了改坐标。
- **修复**：一切元素落在 12 列网格上（`design-system.md` §1e）；同类页型复用同一套 `pageTypes` 几何常量，不手写坐标。

### F8 主题 / 风格漂移 `theme_style_drift`

- **识别**：浅色报告末尾出现深色页；PPTX 底色与 HTML 主题不一致；同一页出现第二色相。
- **错误码**：`MODEL_THEME_BG_MISMATCH` / `band--deep` 约束检查 / 单一强调色检查
- **根因**：用 `band--deep` 作收尾页（浅色主题下渲染成深色）；手写 hex 色值绕过语义类。
- **修复**：收尾/CTA 用 `.band--accent`（accent-soft 底）；`band--deep` 仅作显式选择、全文 ≤1 处且不得作末页；颜色一律走 `.f-acc/.f-s*/.f-c*` 语义类与 `--accent*` token。

### F9 配图走样 `image_layout_drift`

- **识别**：HTML 里图是 16:9、PPTX 里被拉宽/压扁；图贴顶而下方大片留白；多图网格变成一张大图；预览里图位是空灰块；PPTX 打开后图片是灰框（回落了占位）。
- **错误码**：`IMAGE_LAYOUT_INVALID` / `IMAGE_FIT_INVALID` / `IMAGE_ITEMS_TOO_MANY` / `IMAGE_SRC_MISSING` / `IMAGE_SRC_EXTERNAL` / `PICTURES_NOT_DECLARED`；`validate_report` 的「模型图片版式 ↔ 正文版式类/比例锁定类对应」。
- **根因**：手写 `<img>` 却没挂 `.media--r*` 比例锁定类；`layout` 写了 `grid` 但正文还是单图；相对路径按 CWD 而非报告目录写；图片体积超限仍强行内联。
- **修复**：版式与比例一律取自 `imageSpec`（HTML 用 `ratioCssClass`、PPTX 用 `ratioDefault`）；多图用 `image.items` + `.media-grid/.media-compare/.media-wall`；相对路径以**模型/报告所在目录**为锚；体积超限改用相对路径（`prepare_images.py --mode path`）。
- **无素材时的正解**：不是"省略图"也不是"塞无关图"，而是 `image.placeholder` + `.media--ph`（版式/比例/图注位置一次锁死，交付前替换 `src`）。

### F10 空占位 `empty_placeholder`

- **识别**：页面上出现一个没有任何文字的虚线框；PPTX 里占位框没有标签。
- **错误码**：`validate_report` 的「配图占位含可见标签（.media__ph）」。
- **根因**：只加了 `.media--ph` 忘了 `.media__ph` 标签块（图标 + 「配图占位」+ 建议尺寸）。
- **修复**：补齐 `.media__ph`（`b` 标签 + `span` 尺寸提示）；标签串由双引擎按 `imageSpec.placeholderLabel` 自动拼装，不要手写别的文案（`TODO/TBD` 会被 `PLACEHOLDER_TEXT` 拦）。

### F11 单件页默认 `single_carrier_page`

- **识别**：整份报告几乎每页只有"一个件"（一张图 / 一张表 / 一列卡片），内容不穷但读起来平；research 报告尤其明显。
- **错误码**：`validate_report` 的「组合版式（内容页含 ≥2 种承载类型的比例）」（阈值单源 `charts.variety.compositeMinRatio`）。
- **根因**：把"一页一件"当成默认。丰富感被误解为"给图加标题 / 加一条 so-what"，而不是**主件 + 从件 + 注释层**的组合。
- **修复**：按 `references/playbook.md` §四 与 `components.md` §46c 的组合矩阵改造——主件（图表/密表/结构图/图片）+ 从件（要点/表格/指标）+ 注释层（so-what / 来源行 / flags）。**先组合，再考虑拆页**。

### F12 图表单一 `chart_monotony`

- **识别**：全篇图表都是 bar / line / donut；相邻两页出现同一图型；有"分布/流向/层级/分布"类内容却仍用柱状图。
- **错误码**：`validate_report` 的「图表多样性（类型数下限）」与「图表不连续同型」；阈值单源 `charts.variety`。
- **根因**：选型靠"最省力的默认图型"，而不是靠**分析意图**（谁大谁小 / 怎么变 / 占比 / 分布 / 归因 / 流向）。
- **修复**：走 `references/playbook.md` §五 的选型决策树（22 条「意图 → 图型 → 禁用条件」）；误用反例见 `charts.md` §66；`charts.md` §16–§31、§35、§52–§70 有全部可复制代码。

### F13 结构图退化 `structure_placeholder`

- **识别**：架构/流程内容被压成"矩阵方块 + 文字 `→`"；分支、判断、汇合、异常路径、层级、时序全部丢失；层间只有小色块没有箭头。
- **错误码**：`validate_report` 的「结构图形/信息图页型被使用」（含结构类内容时）+ 人工对照 `infographics.md` §82；泳道裸 `→` 文本 → `LAYOUT`/人工（v9：用 `.lane__arr` / `.arch__conn` 正交箭头）。
- **根因**：只会用 `.arch` 分层带 / `.lane` 泳道，遇到"要分支的流程"就退化成文字箭头；或连接件画成两小块矩形。
- **修复**：按 `infographics.md` §78–§81 画**结构图形**——流程图 `flow`（菱形判断 + 分支标签 + 异常虚线）、层级树 `tree`（正交连接 + 同层等高）、时序图 `sequence`（生命线 + 激活条）、闭环 `loop`（方向一致的箭头 + 中心结论）。泳道/层间连接一律 **线段+箭头**（HTML `.lane__arr`/`.arch__conn`，PPTX `rect+triangle`）。PPTX 侧映射 `diagram` / `steps` 页型，分支细节写 `note`。

### F14 风格集漂移 `style_set_drift`

- **识别**：文档里写"18 套风格"而单源只有 9 套；画廊卡片数 ≠ 单源风格数；参考图与当前风格集不符；PPTX 导出找不到某风格的 token。
- **错误码**：`audit_styles.py`（双源逐字段 + 编码色板 9×2×5 + ui.js 色板）、`capture_theme_overview.js`（卡片数 ≠ 单源风格数即抛错）。
- **根因**：风格集是**五张单源表 × 亮暗 + engine.css 块 + ui.js 色板 + 画廊 + 参考图**的多点结构，改一处忘一处。
- **修复**：改风格**只改 `layout-constants.json`** → 跑 `sync_runtime.py` → `audit_styles.py` → `build_examples.py` → 需要时 `node scripts/capture_theme_overview.js` → `regression.py`。**新增风格先过 `styles.md` §10 的三条门槛**（新色族 + 新语汇 + 场景缺口）。

### F15 内容节奏塌陷 / 空洞结论 `content_rhythm_hollow`

- **识别**：连续 3 页同一版式签名（如全是 `g-side`）；so-what 是「需要持续关注 / 值得进一步研究」等套话；research 标题只有主题词没有数字或判断。
- **错误码**：`validate_report` 的「版式节奏（同一版式签名连续 ≤N 页）」「so-what 实质（长度与空洞套话）」「research 行动标题含数字或判断词」；阈值单源 `layout-constants.json` `contentQuality`。
- **根因**：结构门禁只查「有没有 so-what / 标题够不够长」，不查「像不像专业材料」；节奏靠自觉而无脚本。
- **修复**：① 换节奏包或调整页型序列（`scaffold_report.py --preset consulting|diagnostic|pitch|ops-review`）；② so-what 写清**行动含义**（谁在什么条件下做什么，带对象与优先级）；③ research 标题改成含数字/判断的结论句（见 `content-rules.md` 与 `outline-design.md`）。**禁止**为过检只加空话修饰词。

### F17 标签泄漏 / 标题空页 / 极偏大图（v9 截图级硬缺陷）

- **识别**：正文或模型里出现 `<a class="cite">` 字面量；整页只有标题；0.5% vs 99.5% 还用 donut；简单 2 类图占满整页。
- **错误码**：`HTML_TAG_IN_TEXT` / `TITLE_ONLY_PAGE` / `UNDERFILL_PAGE` / `CHART_SKEW_INVALID` / `CHART_OVERSIZE` / `TEXT_INCOMPLETE`
- **根因**：双写未净化（标签进模型）；过空页只 WARN；图表面积与信息复杂度脱钩；极偏数据误用占比图。
- **修复**：① 模型字段纯文本，引用写 `[n]`；② 空页补证据与承载或并页；③ 极偏改 V3（KPI/进度/对比条）；④ 简单图缩到 18–28% 高并配注解带（V1–V4）。详见 `layout-constants.qualityGates` 与 `playbook.md` §三-b。

### F16 已登记图表静默降级 `chart_fallback_forgery`

- **识别**：形状通道类型在 PPTX 里变成通用比例条；原生图表调用失败后被悄悄画成柱状图——页面像过了，双击却不可编辑或型不对。
- **错误码**：`build_pptx.js` 抛 `SHAPE_RENDERER_MISSING` / 原生 `chartTry` 失败即非 0 退出；`validate_pptx` 的 `MODEL_CHART_COUNT`。
- **根因**：为「绝不中断交付」静默回落，把实现缺口伪装成成功产物。
- **修复**：补专属渲染器或修正 `charts.registry`；**禁止**再加静默回落。回归必跑 `regression.py`（含双裁判）。

## 二、修复顺序铁律（先改什么，不要改什么）

> 报告不合格时，**按下面顺序改**。跳过前序步骤直接缩字号 / 砍内容 / 换风格，都会把问题推给下一环。

```
① 先补证据与含义（内容层）
   ↓ 内容确实够了但放不下
② 再优化内容形态：列表化 / 精炼措辞 / 合并同类项
   ↓ 形态已最优仍放不下
③ 再换承载形态（文字 → 表 → 图；普通图表 → 信息图页型；升级/扩组合版式）
   ↓ 承载已是最优形态
④ 再调容器与网格（改容器尺寸 / 行宽 / 分区，落在 12 列网格上）
   ↓ 容器已到极限
⑤ 有限缩字号（fontShrink：最多 4 档，模式 floor 见 layout-constants）
   ↓ 仍装不下
⑥ 最后拆页（宁拆勿挤；拆页后重复 eyebrow 标注「续」）
   ────────────────────────────────────────
   全程禁止：
   ✗ 无限缩字号 / 压到模式 floor 以下
   ✗ 把精简当第一手段砍口径列 / 时间列
   ✗ 换风格掩盖版式问题（风格是皮肤，不是解药）
   ✗ 用装饰补空白
   ✗ 把主要信息做成图片
```

## 三、错误解释纠正表（常见自我说服 vs 正确做法）

| 错误解释（自我说服） | 正确做法 |
|---------------------|---------|
| "字号小一点但内容都放下了" | 可接受但非首选。先列表化/精炼/换组合；仍偏多时按 `fontShrink` **有限**下探（不超 4 档、不低于模式 floor）。无限缩字号仍不合格。 |
| "文字没超出页面，所以不算溢出" | 错。**越过归属容器即失败**（卡片/面板/单元格/结论条/so-what）。 |
| "一句话拆成多个文本框方便高亮" | 错。连续语义文本必须保持连续流（同一文本框内富文本）。 |
| "表格字号没低于下限，所以布局空也可以" | 错。表格密度必须匹配内容（大面积空洞 → `TABLE_DENSITY`）。 |
| "图表看起来复杂，保留为图片就行" | 错。简单图表（柱/折线/坐标轴/标签/对比条/基础表格）必须原生重建。 |
| "只要主标题可编辑就行" | 错。正文、关键数字、图表标签、注释、页脚、so-what 同样必须可编辑。 |
| "为了 pictures=0，把流线/曲线图改成矩形条" | 错。曲线语义图必须按采样规则精确还原（≥16 点、双边界追踪）。 |
| "校验器 strict 过了，所以视觉也合格" | 错。strict 查结构与门禁；视觉语义（底色系统、图表形态、留白节奏）需按本文与 `infographics.md` 自检。 |
| "先批量生成整篇，最后统一补检查" | 错。逐页自检成本远低于整篇返工；校验闭环按页跑。 |
| "数据只在图上就够了，不用附数据表" | 错。非原生图表至少 `dataTable: notes`（数据写入演讲者备注）。 |
| "没有素材图就先不配图" | 错。用 `image.placeholder` + `.media--ph` 出配图占位，把版式/比例/图注位置一次锁死（交付前替换 `src` 即可）。 |
| "图先随便放，比例让 PPTX 自己适配" | 错。版式与比例取自 `imageSpec`（`ratioDefault` / `ratioCssClass`），HTML 与 PPTX 必须同比例——否则预览与交付不一致。 |
| "图片路径写 `assets/x.png` 就行" | 半对。相对路径以**模型/报告所在目录**为锚（`resolveImagePath`）；跨目录调用要按此口径写，缺失会报 `IMAGE_SRC_MISSING`。 |
| "图片直接贴外链更省事" | 错。零外链铁律：`<img src>` 只允许 data: 内联或相对路径（外链报 `IMAGE_SRC_EXTERNAL`）。 |
| "占位框就是留个空框，不用写字" | 错。空占位会被校验器拦；必须带 `.media__ph`（图标 + 配图占位 + 建议尺寸），PPTX 侧同串标签。 |
| "节点/系列太多，缩字号硬塞进一页" | 错。按上限**拆页**（`infographics.md` §二 上限表）。 |
| "配色不够丰富，再加一个强调色" | 错。除 spectrum 外只有**一个**强调色；层次靠表面明度差 + 1px 边框。 |

## 四、校验器对应速查

| 失败模式 | 主要校验器 / 错误码 | 门禁级别 |
|---------|-------------------|---------|
| F1 内容不足 | `validate_report.py`（内容密度）/ `validate_pptx.py` `LOW_TEXT_DENSITY` | strict |
| F2 装饰替代 | `UNBALANCED_EMPTY_SPACE` / `LOW_TEXT_DENSITY` | strict |
| F3 密度塌陷 | `TABLE_DENSITY` | strict |
| F4 容器溢出 | `CONTAINER_OVERFLOW` / `TEXT_OVERFLOW_ESTIMATE` / `SHAPE_OUTSIDE_SLIDE` | strict |
| F5 文本拆流 | `CONTINUOUS_TEXT_FLOW` | 深度模式（`--deep`） |
| F6 图表降级 | `MODEL_CHART_COUNT` / `MODEL_CHART_DATATABLE` / `MODEL_CHART_NOTES_MISSING` | strict（交付通道） |
| F7 位置漂移 | `ANCHOR_TITLE_MISALIGNED` | 深度模式（`--deep`） |
| F8 主题风格漂移 | `MODEL_THEME_BG_MISMATCH` / 单一强调色检查 / 强调带约束 | strict |
| F9 配图走样 | `IMAGE_LAYOUT_INVALID` / `IMAGE_FIT_INVALID` / `IMAGE_ITEMS_TOO_MANY` / `IMAGE_SRC_MISSING` / `IMAGE_SRC_EXTERNAL` / `PICTURES_NOT_DECLARED` / `PICTURES_UNDER_DECLARED` | strict |
| F10 空占位 | `validate_report` 配图占位可见标签（`.media__ph`） | strict |
| F11 单件页默认 | `validate_report` 组合版式比例（`charts.variety.compositeMinRatio`） | strict（research） |
| F12 图表单一 | `validate_report` 图表多样性 + 不连续同型（`charts.variety`） | strict |
| F13 结构图退化 | `validate_report` 结构图形/信息图页型使用 + `infographics.md` §82 人工对照 | strict（含结构类内容时） |
| F14 风格集漂移 | `audit_styles.py`（双源 + 编码色板）/ `capture_theme_overview.js`（卡片数 ≠ 单源即抛错） | 维护时 |
| F15 节奏塌陷/空洞结论 | `validate_report` `contentQuality`（so-what 禁空洞套话 / 版式连用上限 / research 标题判断词） | strict |
| F16 登记图表静默降级 | `validate_pptx.py` `SHAPE_RENDERER_MISSING` / 原生调用失败即非 0 | strict（交付通道） |

> **深度模式**：用户明示「高保真 / 1:1 / 精确还原 / 正式交付」或页面含复杂信息图时启用——
> `python scripts/validate_pptx.py <pptx> --strict --deep --model=<model.json>`。

## 五、rubric 弱项自检（分数「过线但不高」时先查这三处）

`quality_gate.py` 五维启发式里最常拖后腿的两维：**infographic**（典型 70）与 **layout**（组合版式 50%–60%）。strict 0/0 只证明「合格」，不证明「丰富」——按下面顺序自查：

1. **infographic 弱（信息图页型未用 / 少用）**
   - 全篇是否有 ≥1 页「一图说清一整套结构」？适用而未用的信号：流程用编号列表讲（→ `flow`）、层级用多级 bullet 讲（→ `tree`）、构成 + 流向混合用两张图讲（→ `sankey`）。
   - 取码：`--chart sankey|treemap|network`；边界判据「普通图表答一个数，信息图答一套结构」见 `infographics.md` §一。
   - 注意：**不为凑分硬上**——简单占比加 `sankey` 是 F6 图表降级的新变体。
2. **layout 弱（组合版式比例 50%–60%，research 下限 30% 但优秀线 ≈70%）**
   - 找出所有「单张大图 + 标题」或「一张密表 + 标题」的页 → 补从件（要点 3–4 条 / 小指标带）与注释层（so-what / 口径行），落 `exhibit`/`split`/`halftable`。
   - 组合矩阵与「从件必须承载主件表达不了的信息」纪律见 `playbook.md` §四。
3. **tone/content 弱（多为次生）**
   - so-what 连续 3 页空缺或套话（→ F15）；引用 0 条且内容含外部数字（→ §五 引用纪律，补 `[n]` 或标 `.tbd`）。

> 自查后重跑 `quality_gate.py`；rubric 启发式只覆盖可静态判定的部分，最终以 LLM 按 `evals/rubric.schema.json` 复评或人眼对照为准。

## F18 · 长文截断 / 溢出未拆页 / 半空卡（v9.1）

| 信号 | 错误码 | 修复 |
|------|--------|------|
| 列表/卡/结论以「…」砍义 | `LAYOUT_QA_TRUNCATION` | 恢复完整表述；改列表化/拆卡/拆页，禁止省略号充数 |
| 页高溢出且无续页/换形态信号 | `LAYOUT_QA_OVERFLOW_NO_SPLIT` | 按 overflowRule：重构→拆页→换形态→fontShrink |
| 同页多卡过半正文过短 | `LAYOUT_QA_HALF_EMPTY` | 减卡高/改列数，或合并卡；勿留凑数半空卡 |
| 图卡混排无对齐类 | `LAYOUT_QA_ALIGN_RHYTHM` | 加 `a-start` / `a-c`；共享左缘顶边 |
| PPTX 页脚 y 跨页漂移 | `CHROME_DRIFT` | 锁死 chrome 槽位几何（pageTypes） |

反模式：为稀疏 demo 感删证据 / so-what。原则见 `presentation-craft.md`「长文与信息承载」。

## F19 · 几何叠印 / 同槽双条 / 注释带侵入（v9.2 · PPTX 导出硬伤）

| 信号 | 错误码 | 修复 |
|------|--------|------|
| 元素两两重叠 ≥0.05in² | `ELEMENT_OVERLAP` | 错开坐标或合并为同一文本框；同页 >3 处=几何算法脱钩，需重构布局 |
| 架构节点标题/注解叠印 | （R1 根因） | 注解钳制在标题下边；节点高不足降级单框混排（双引擎已修，自定义几何勿回退） |
| verdict 与 soWhat 同页双填叠印 | `MODEL_VERDICT_SOWHAT_CONFLICT`（extract_model WARN） | **二选一**：comparison 填 `verdict` 就不要填 `soWhat`；渲染器自动去重但模型侧应只给一个 |
| 图例/类目标签压 so-what/来源行 | `ANNOTATION_BAND_OVERLAP` | 图例落图区底部（`bodyBottom-0.28`）；类目标签含在图高 `h` 内；禁 `PH-0.62` 固定偏移 |
| `sec.note` 压 so-what 带 | （R2 根因） | `note` 与 `footnote` 共用注释带末行 `footnoteY=6.72`，同页自动合并；禁用 `note.y=6.55` |
| 版心填充 <55%（宽/高任一轴） | `LAYOUT_FILL` | 多栏按版心全宽推导列宽；低密度页补从件（指标/小图/对照表） |

**根因**：几何算法与内容量脱钩（固定偏移、单栏宽当总宽、同槽位无仲裁）。**门禁**：`validate_pptx.py --strict` 已含 `ELEMENT_OVERLAP` / `LAYOUT_FILL` / `ANNOTATION_BAND_OVERLAP`；`cross_verify` 比对 Agenda 阅读顺序、图片数、图表数据标签。

## F20 · Agenda 溢出 / 图表退化 / 图标跨通道（v9.2 · 容量与跨通道）

| 信号 | 错误码 | 修复 |
|------|--------|------|
| Agenda 列成页目录（>8 条） | `Agenda 条数 ≤16`（validate_report）；`contentQuality.agenda.chapterMax=7` | 按 eyebrow 章前缀归并回章（3–7 条）；禁止逐页标题当大纲 |
| Agenda 单条标题 >36 字 | `Agenda 单条标题 ≤36 字`（WARN） | 截断+全称沉 notes；或精炼标题 |
| Agenda 两通道阅读顺序不一致 | `Agenda序=DRIFT`（cross_verify） | 列优先（先左列后右列）；HTML 用 `column-count`，PPTX 用列填充 |
| low 图型无数据表 | `图表 PPTX 还原度提示`（WARN） | area/radar/treemap/sankey/streamgraph/marimekko/boxplot/network 在 PPTX 显著退化——改 bar/line/hbar/donut 或 `dataTable=inline` |
| ≥2 卡且无 `.card__ico` | `要点/卡片页含 .card__ico`（WARN） | 从 `icons.md` 取语义图标（`render_from_model.py` 已内置 `card_head()` 自动出图标 + `data-icon`） |
| PPTX 卡片头是方块不是图标 | `icon_pictures=0`（validate_pptx summary） | 跑 `node scripts/build_icon_assets.js` 生成 `icon-assets.json`（需 sharp）；确认模型 `cards[].icon` 有值。缺资产时引擎回落 accent 方块（可扫读，但非真图标） |
| 图标 PNG 进了内容图门禁 | `PICTURES_NOT_DECLARED` 误报 | 图标 `objectName` 必须以 `icon:` 开头；`validate_pptx` 按前缀分流到 `icon_pictures` |
| 图片占位标签 A/B 不同串 | `图片数=DRIFT` / 文本覆盖不足 | 占位标签由 `imageSpec` 同源拼接；`render_from_model` 与 PPTX `imgPlaceholderLabel` 必须同串 |

**根因**：页型容量契约缺失 + 图表双通道无还原度约定 + 图标/占位文本两处手写。**门禁**：`contentQuality.agenda`（singleMax/splitMax/titleMaxChars/chapterMax）、`charts.fidelityMap`、`cross_verify --full-ab`、`icon_pictures` 分流计数。

