# TopPPT HTML 总体技术方案

> 本文是**总体技术方案**（架构 / 双单源 / 双通道 / 门禁 / 深度模式 / 工作流 / 演进）。
> 生成报告前不必读本文；**改动架构、导出机制、常量或校验体系前必读**。

## 一、一句话架构

**一套内容模型，两种交付形态，双单源，双通道，按需深度模式。**

```
用户意图 ──六项问询──> 模式 × 风格 × 亮暗主题 × 篇幅 × 交付格式
                          │
                          ▼
            内容架构（outline-design.md）
                          │
                          ▼
            scaffold_report.py 出骨架（data-skel / layoutPreset）
            → 只填 window.REPORT_MODEL（纯文本，[n] 引用）
            → render_from_model.py --inplace 回填 HTML（模型单写路径）
                          │
        ┌─────────────────┴──────────────────┐
   HTML（阅读/演示）                    PPTX（精导）
   validate_report --strict             extract_model → build_pptx
   LAYOUT_* / qualityGates               → validate_pptx --strict
```

## 二、双单源（唯一事实源）

| 单源 | 内容 | 消费方 |
|------|------|--------|
| `scripts/layout-constants.json` | 页面几何 `page` / **12 列网格 `grid`** / **语义字阶 `typography` C0–T14** / 三模式比例尺 `typeScale`+`modeTypeScale` / 页型几何 `pageTypes`+`pageTypeGeometry` / **9 风格 token `styles`+`stylesDark`+`styleAccents`** / **编码色板 `styleDataColors`+`styleDataColorsDark`（9 套 × 亮暗 × c1–c5）** / **图表登记四元组 `charts.registry`** / 图表最小尺寸 `charts.minSize` / **图表多样性预算 `charts.variety`** / **容器内边距 `containers`** / **锚点容差 `anchorTolerance`** / **图片准入门 `imageAdmission`** / **图片规格 `imageSpec`**（版式 `layouts` / 比例 `ratioDefault`+`ratioCssClass` / 建议尺寸 / 占位标签 / 体积上限） / **深度模式 `deepMode`** / 校验预算 `checkBudgets` / 强调带 `emphasis` / 待核实 `annotations` / 去AI味词 `aiFlavor` / **内容级质量 `contentQuality`**（版式节奏 / so-what 实质 / research 标题判断） | `build_pptx.js`（require）、`pptx-export.js`（注入常量块）、三模板、`style-gallery.html`、`validate_report.py`、`validate_pptx.py`、`audit_styles.py`、`audit_skill.py`、`prepare_images.py`、`evals/run_evals.py` |
| `scripts/model-schema.json` | 29 种页型的字段与必填约束 / **图表类型白名单 `chartTypes`（30 类：16 原生 + 14 形状）** / **数据表策略 `chartDataTable`** / 通用可选字段 `commonSectionFields` | `extract_model.py`（本地校验）、`pptx-export.js`（浏览器端 `validateModel`） |
| `layout-constants.json` → `layoutSlots` | **页型布局 IR（29 页型全量）**：语义槽位（head/primary/secondary/annotation + required）——双通道按同一槽位语义落位 | `sync_runtime.py`（完整性校验）；`lib_layout_regions.js`（槽位→英寸矩形）；`extract_snippet.py --page-type` |
| `scripts/icon_lib.js` | **语义图标库单源**（20 名 → 24×24 stroke SVG；与 `icons.md` 高频取码 / `render_from_model.ICONS` 同键） | `build_icon_assets.js`（栅格化）、`build_pptx.js`（真导出 PNG）、`icon_raster.js` |
| `scripts/icon-assets.json` | **图标 PNG 资产缓存**（`build_icon_assets.js` 生成 · sharp 栅格化 · 20 图标 × 各风格 accent 色；gitignore，可再生成） | `build_pptx.js`（同步读取；缺失时 execFileSync 自动补齐） |
| 交付一键 | `quality_gate.py` | `validate_report --strict` + 可选 `validate_pptx` + `evals --score` + **rubric 启发式五维**（content/layout/chart/infographic/tone） |

**纪律**：改常量只改 JSON，改 schema 只改 schema JSON，然后跑 `python scripts/sync_runtime.py`（注入 + 完整性校验 + 哈希摘要）。**禁止手改** `pptx-export.js` / 三模板 / `style-gallery.html` 的标记块。

**`sync_runtime.py` 的完整性校验**（任一不过即 PASS→WARN）：
1. 双端引用（`build_pptx.js` require 常量；`extract_model.py` 读 schema）
2. **页型四件套**：每个 schema 页型都有 `pageTypeGeometry` 几何映射
3. **图表登记四元组**：`charts.types` ↔ `charts.registry` 双向一致；`pptx` 通道合法；非原生图表 `dataTable` 不得为 off（登记表自身声明 off 的装饰微图豁免）；`schema.chartTypes` 是 registry 子集
4. **图表类型可达性不变量**：`registry.types == chartTypes ∪ 信息图专属页型`——每个登记类型都必须能由模型表达（作 `chart.type` 或作 `sections[].type`），否则双引擎实现沦为死代码（该不变量正是为拦住「登记 36 类但模型只能表达 16 类」这类漂移而加）；信息图页型清单亦单源于 `charts.scaffold.infoTypes`
5. **页型实现可达性（冒烟）**：schema 每个页型都应出现在 `build_pptx.js` 与 `pptx-export.js` 源码中（子串级，拦「schema 加了页型、引擎没实现」）
6. **骨架尺寸单源不变量**：`charts.scaffold`（scaffold_report.py 骨架尺寸唯一事实源）键 ⊆ registry，且默认值 ≥ `charts.minSize` 同口径阈值——拦「脚本硬编码第二源漂移」
7. **语义字阶**：每个 level 的 `role` 在 `modeTypeScale` 中存在
8. **页型布局 IR**：`layoutSlots（LC）` 每个页型在 schema 中存在，且含 head + primary 槽位

> **图表计数的两种口径**（同一事实的两种切法，勿混用）：`registry` 视角 **36 = 16 原生 + 20 形状**（SKILL.md 铁律 9 用此口径）；`chartTypes` 视角 **30 = 16 原生 + 14 形状**（可作 `chart.type` 的形状类，`pptx-export.md` 页型表用此口径）——差额 6 类是信息图专属页型（sankey/treemap/boxplot/network/marimekko/streamgraph），它们只作 `sections[].type`，不作 `chart.type`。

## 三、双通道（A 预览 / B 交付）

| | A 通道（`assets/pptx-export.js`） | B 通道（`scripts/build_pptx.js`） |
|---|---|---|
| 角色 | 页面「预览 PPTX」WYSIWYG + 回归双裁判 | **唯一交付通道** |
| 输出 | 手写 OOXML 形状/文本框/表格（零依赖，约 120KB） | pptxgenjs → 原生形状 + **原生数据图表**（chart part + 内嵌 Excel） |
| 图表 | 全部类型做**形状近似**（类别标签与数值都落为文本） | 原生通道走 `addChart`；形状通道走高保真形状还原 + 数据表；**已登记类型禁止静默回落**（`SHAPE_RENDERER_MISSING` / 原生调用失败即非 0） |
| 一致性 | 与 B 通道**逐页文本集合一致**（`cross_verify.py` 用 python-pptx 第三方裁判核对） | 同左 |

**为什么手写序列化而不内嵌 pptxgenjs**：pptxgenjs 浏览器版约 700KB，内嵌进每份单文件报告不可接受；手写运行时约 120KB 且与 B 通道消费同一份常量单源。**复用的是引擎与规范，自研的只是轻量序列化轮毂**。

**`cross_verify.py` 归一化三件事**（新增图表类型时必须同步扩展，否则误报）：
1. B 端 chart part 的 `plots[0].categories` 并入文本集
2. `NUMERIC_TOKEN` 纯数值 token（含枚举单位）两端对称过滤
3. `sorted(set(...))` 集合语义去重

## 四、门禁体系（分层）

| 层 | 工具 | 通过标准 |
|----|------|---------|
| HTML | `validate_report.py` | 全 PASS（模式预算 + 页高溢出估算 + 模型一致性 + 图表数据表策略 + **图表多样性（类型数下限 / 不连续同型）** + **组合版式比例（research）** + **内容级质量（版式节奏连用 / so-what 实质 / research 标题含判断）** + 页型↔版式对应 + 锚点闭环 + 图表登记与最小尺寸 + Exhibit 连续性 + 强调带/待核实/**素材图片与配图占位**（零外链·alt·版式与比例锁定类对应·占位可见标签·内联体积）+ 预览配套断言） |
| PPTX（交付基线） | `validate_pptx.py --strict --model=` | 0 errors / 0 warnings：模型往返保真 + 按类型原生图表断言 + 数据表落位 + 容器级溢出 + 表格语义字号与密度 + 越界/文本溢出/字号下限/未声明图片 + **图片版式·裁切·多图数量·相对路径文件存在性** |
| PPTX（深度模式） | 加 `--deep` | 再把**连续文本流**与**空间锚点**纳入 strict |
| 双裁判 | `cross_verify.py`（python-pptx） | A/B 产物均可严格解析 + 逐页文本一致 + 溢出启发式 |
| 素材图片 | `probe_image_export.py` | 真实位图 build→strict 0/0 且 `pictures == 声明数`（示例矩阵刻意零图片，真实素材路径/版式/门禁靠它覆盖） |
| 风格与单源 | `audit_styles.py` | 9 风格 × light/dark × 8 组 WCAG 配对 + engine.css ↔ JSON 双源逐字段一致 + **编码色板 9×2×5（双源 + 对 bg 对比 ≥3.0 + 同套两两可区分）** + ui.js 色板一致 + 单源完整性 |
| 技能工程 | `audit_skill.py` | 体积预算（SKILL.md ≤13KB / L1 playbook / 单份 reference / 模板）+ description 软硬上限 + **三档披露（L0/L1/L2）** + **Gate 0 位于六项问询之前** + 交互轮次与必读文件预算声明 + 引用完整性 + **内容重复（SKILL.md↔references 归一化滑窗 ≥20 字含 CJK）** |
| 文档一致性 | `audit_docs.py` | § 引用可解析（含大写后缀）+ 文件前缀规范 + §46 覆盖 36 图表/29 页型 + 图表代码节齐备 + 元数据与必需文件 + **任务路由可解析（TASK_ROUTES 每条实际抽取）** |
| CSS 覆盖率 | `audit_css.py` | engine.css 选择器类 ↔ 消费方语料（剔除注入镜像）；**报告制**（列出疑似死类，不设门禁） |
| 单源注入 | `sync_runtime.py` | 注入成功 + 完整性校验（①–⑪：双端引用 / 页型四件套 / 图表登记四元组 / 可达性 / 实现冒烟 / **骨架尺寸单源 7d** / 语义字阶 / 布局 IR / **版本一致性**）PASS + 哈希摘要一致 |
| 反向验证 | `negative_tests.py` | 14 例故障注入（编号/引用/备注/数值/标题/字号/登记/多样性/外链/tbd 图例/主题与模式矛盾/锚点）→ 校验器必须报错 |
| Eval（四类目标） | `evals/run_evals.py` | 结果（零外链 / strict 0/0 / 模型一致）+ 风格（图表多样性 / 组合版式 / 结构图形）+ 过程（Gate 0）+ 效率（轮次 ≤3 / 工具调用 ≤25 / 读取 ≤40KB）；定性部分用 `evals/rubric.schema.json` |
| 全链路 | `regression.py` | 以上全部 + 9 示例端到端 + **任务路由全量遍历**（与 audit_docs ⑥ 共用 `verify_routes`） |

## 五、按需深度模式

**触发**：用户明示「高保真 / 1:1 / 精确还原 / 正式交付…」（`deepMode.triggers`）或页面含复杂信息图（`deepMode.complexCharts`）。

**多做的三件事**：
1. `validate_pptx.py --strict --deep` → 连续文本流 + 空间锚点（页头标题对齐版心左边界，容差 `anchorTolerance.keyPx`）纳入 strict
2. `--emit-manifest=<path>` → 机器可验证的 manifest（锚点注册 / 容器清单 / 数据表清单 / 图表通道清单 / 图片资产登记 / 门禁计数）
3. `render_compare.py` → 渲染对照材料（PPTX→PDF→位图 + HTML/PPTX 并排对照页 + 自动偏差登记），**缺依赖自动跳过**

**明确不引入**：SHA-256 冻结签名、逐页人工验收确认、ImageGen 逐页蓝图、PowerPoint COM 硬门禁（详见 `high-fidelity.md` §八）。

## 六、工作流

```
听意图 → Gate 0 先给参考图（theme-overview*.png）
      → 六项问询一次收集（形式参数：模式/篇幅/风格/主题/交付格式/参考图）
      → 按路径分流：轻量路径（1 张规划卡）/ 完整路径（内容架构七步法 + 按需大纲确认）
      → scaffold_report.py 起骨架（锁模式/风格/主题 + 预生成 REPORT_MODEL，不读模板全文）
      → 照规划卡填内容（每页 = 主件 + 从件 + 注释层）→ 自校验自修复 → 交付
      → [深度模式] --deep --emit-manifest + render_compare
```

**效率预算（硬）**：交互轮次 ≤3；必读 = `SKILL.md`（L0）+ `references/playbook.md`（L1）共 2 份；L2 深度文件按需读、读完即停。
**断点可恢复**：`REPORT_MODEL` 即恢复锚点——上下文中断后重跑 `extract_model.py` → `build_pptx.js` 即恢复，无需重新生成内容。

## 七、发布态与兼容

- **发布版**：**v0.1**（布局语法 + 模型单写 + 硬门禁 + 风格语汇层）。**双版本口径**：npm / `metadata.version` = **semver（0.1.x）**；`layout-constants.json` `version` = **布局语法 schema 线（`0.1`）**——`model-schema.json` / `layoutSlots` 同步 schema 线，`sync_runtime.py` 校验 `package.json` 对齐 `0.1.x`。变更流水见仓库根 `CHANGELOG.md`。
- **兼容回落**：排版比例尺只有 `modeTypeScale` 一套；未知模式回落 `presentation` 档。环境变量 `TOP_PPT_NODE_EXE` / `TOP_PPT_NODE_PATH`（旧名已移除）。
- **文档分工**：本文件管架构与机制；日常规范见 `references/*`，业界对标依据见 `../docs/archive/refs/industry-benchmark.md`。

## 八、目录职责

| 路径 | 职责 |
|------|------|
| `SKILL.md` | **L0** 路由与门禁：触发边界、**Gate 0 参考图先行**、三模式速选、六项问询、两条路径、**12 条铁律**、阶段路由（L0/L1/L2）、效率预算 |
| `references/playbook.md` | **L1 唯一常读入口（决策层）**：三模式契约、两条路径、页型选型、**组合版式矩阵**、**图表选型决策树**、内容规则 Top-12、信息图页型族、配色与主题、校验命令 |
| `references/modes.md` | 三模式密度契约与锁定版式（L2：定模式细节时读） |
| `references/outline-design.md` | 内容架构七步法 + 跨页叙事节奏 + 细节保全 |
| `references/design-system.md` | MD3 对齐、设计原理（CRAP/7:2:1/字体矩阵）、页高模型、12 列网格、语义字阶、SVG 语义类（生成时主读） |
| `../docs/archive/refs/design-system-engine.md` | 顶栏/卡片/列表/表格/页脚/动效等 CSS 类实现目录（维护者；生成时勿读） |
| `references/styles.md` | 9 套风格定义与选型 |
| `references/content-rules.md` | 页内写作规则、密度三档、表格语义字号、容器内边距、连续文本流 |
| `references/components.md` | 结构组件与锁定版式（`components.md` §1–§15c、§32–§50）+ 版式选型表 + **组合版式矩阵（§46c）** |
| `references/charts.md` | 图表全库（`charts.md` §16–§31、§29b、§35、§52–§70）+ **误用反例与多样性纪律（§66）** |
| `references/infographics.md` | 信息图铁律与边界（逻辑入口）；代码在 `infographics-stats.md` / `infographics-structure.md` |
| `references/icons.md` | 内联 SVG 图标库与使用准则 |
| `references/pptx-export.md` | PPTX 导出通道、模型字段、双单源、29 页型、图表双通道 |
| `references/high-fidelity.md` | 按需深度模式规范（触发、容差、manifest、渲染对照） |
| `references/failure-modes.md` | 十四类失败模式 + 修复顺序铁律 + 错误解释纠正表 |
| `../docs/archive/refs/industry-benchmark.md` | 业界对标与采纳/不采纳决策依据 |
| `scripts/*` | 校验器、**骨架生成器 `scaffold_report.py`**、注入器、回归、**三项审计（styles / docs / skill）**、打包（全部标准库；PPTX 精导需 Node + pptxgenjs） |
| `evals/*` | Eval 框架：`prompts.csv`（14 条，含负对照）+ `rubric.schema.json`（风格目标评分契约）+ `run_evals.py`（结果/过程/风格/效率四类目标） |
| `assets/templates/*` | 三模式模板 + 公共引擎/UI（标记块由 `sync_runtime.py` 注入） |
| `assets/examples/*` | 示例矩阵（含信息图页型与原生图表技巧） |

## 附：第三方校验与实验 frontmatter

- **主门禁**：`audit_skill.py` / `package_skill.py --check`（体积、披露、Gate0、触发覆盖）。
- **可选**：`npx --yes skills-ref@0.1.5 validate .`（Agent Skills 开放标准；本技能已通过）。**不**作为 CI 硬依赖。
- **不启用**：Claude-only `when_to_use`（会破坏严格 allowlist）；跨端 `allowed-tools`（宿主语法分叉）——需要时由宿主侧实验，不进本仓库 frontmatter。
