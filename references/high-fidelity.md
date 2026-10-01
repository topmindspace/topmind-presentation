# 按需深度模式（高保真交付规范）

> **何时读本文**：用户提出「高保真 / 1:1 / 精确还原 / 按图还原 / 正式交付 / 不能偏移 / 像素级 / 严格对照 / 逐页验收」，
> 或页面含**复杂信息图**（桑基 / 流带 / 树图 / 马赛克 / 箱线 / 网络 / 玫瑰 / 径向条 / K 线 / 漏斗）时。
>
> **定位**：默认流程保持轻量（一次问询 + 自动生成 + 校验闭环）。深度模式是**自动升级**的加强档——
> 多跑三道检查（容器级溢出已默认开启，深度模式再加**连续文本流**与**空间锚点**）、产出 manifest、并准备渲染对照材料。
> **不引入** SHA-256 冻结签名与逐页人工验收确认（会显著拖慢生成，与本技能"一次问询 + 自动生成"的定位冲突）。

---

## 一、触发条件

| 触发 | 判据 |
|------|------|
| **用户明示** | 命中 `layout-constants.json` `deepMode.triggers`：高保真 / 1:1 / 一比一 / 精确还原 / 按图还原 / 正式交付 / 不能偏移 / 像素级 / 严格对照 / 逐页验收 |
| **内容含复杂信息图** | 页面用到 `deepMode.complexCharts` 中的图表类型（sankey / streamgraph / treemap / marimekko / boxplot / network / rose / radialbar / candlestick / funnel） |

命中任一 → 交付时按 §四 跑深度模式校验链。**不命中则不要跑**（保持轻量，避免无谓开销）。

---

## 二、深度模式多做的三件事

1. **连续文本流检查**（`CONTINUOUS_TEXT_FLOW`）：语义连续句不得拆成多个独立文本框。
2. **空间锚点注册**（`ANCHOR_TITLE_MISALIGNED`）：页头标题左边距必须对齐版心左边界。
3. **manifest + 渲染对照材料**：把可复现的事实登记下来，并准备人眼对照的产物。

> 容器级溢出（`CONTAINER_OVERFLOW`）、表格语义字号（`TABLE_SEMANTIC_TYPE`）、表格密度（`TABLE_DENSITY`）
> **默认就开启**（属交付基线，不属于深度模式）。

---

## 三、锚点容差（`layout-constants.json` `anchorTolerance`）

| 项 | 值 | 含义 |
|----|----|------|
| `centerPct` | 2.0 | 中心点偏差上限（占参考框局部宽高比例）——用于人眼对照时的判据 |
| `keyPx` | 6 | 关键锚点（图标 / 标签 / 箭头端点 / **页头标题左边距**）偏差上限（px @96dpi ≈ 0.0625in） |
| `exactPx` | 3 | 用户要求 1:1 时的上限 |

**优先级与容差**（人眼对照时按此判级）：

| 级别 | 元素 | 容差 | 超差等级 |
|------|------|------|---------|
| **P0** | 标题 / 主图 / so-what / 页脚 / 关键数字 / 核心面板 | 3px（最大 6px） | Critical |
| **P1** | 普通卡片 / 图标 / 标签 / 箭头 / 表格 / 分隔线 | 4px（最大 8px） | High（正式交付不得存在） |
| **P2** | 装饰线 / 点阵 / 纹理 / 重复刻度 / 背景纹样 | 6px（最大 12px） | Medium |

**自动化部分**：`validate_pptx.py --deep` 自动核对**页头标题锚点**（`ANCHOR_TITLE_MISALIGNED`）——
这是"相对位置还原"的确定性代理，不需要参考图即可复现；其余 P0/P1/P2 元素在渲染对照页上人眼核对。

---

## 四、深度模式校验链

```bash
# 1. 生成（同默认流程）
python scripts/extract_model.py "<输出目录>/YYYY-MM-DD-主题.html"
NODE_PATH=<pptxgenjs 所在 node_modules> <node> scripts/build_pptx.js "报告.pptx" --model="报告.model.json"

# 2. 深度校验（--deep 把连续文本流与空间锚点纳入 strict 门禁；--emit-manifest 产出登记）
python scripts/validate_pptx.py "报告.pptx" --strict --deep \
  --model="报告.model.json" --emit-manifest="报告.manifest.json"

# 3. 渲染对照（可选，缺 LibreOffice 自动跳过）
python scripts/render_compare.py "报告.pptx" --html "报告.html" --out "render-compare"
```

---

## 五、manifest 字段（`报告.manifest.json`）

| 字段 | 内容 | 用途 |
|------|------|------|
| `chartChannels` | `expectedNative` / `expectedShape` / `actualChartParts` / `nativeOk` | 原生通道图表是否真的落成 chart part（可编辑数据） |
| `dataTables` | 模型侧每个图表的 `pageType` / `chart` / `channel` / `dataTable` 策略 + PPTX 侧每页表格数 | 数据可追溯（非原生图表至少 `notes`） |
| `images` | `declared`（模型声明的真实图片数）/ `actual`（PPTX 实际图片数）/ `placeholders`（配图占位数）/ `layouts`（每页版式 / `fit` / 图数 / 是否占位） | 默认零图片、声明式放行；占位符走原生形状不计入图片数 |
| `anchors` | 每页 `title` / `left_in` / `expected_left_in` / `delta_in` / `tolerance_in` / `status` | 空间锚点注册（passed / failed / no-title-anchor） |
| `containers` | 每页 `text_shapes` + `min_pad_in` | 容器清单（配合 `CONTAINER_OVERFLOW` 判定） |
| `counts` | `errors` / `warnings` | 门禁结果摘要 |

> manifest 只登记**可复现的事实**，不做签名冻结——需要复核时重跑即可得到同样结果。

---

## 六、渲染对照（`scripts/render_compare.py`）

**产物**（默认输出到 `<pptx 同目录>/render-compare/`）：

| 文件 | 内容 |
|------|------|
| `deck.pdf` | LibreOffice 渲染的 PPTX PDF（`soffice --headless --convert-to pdf`） |
| `page-01.png …` | PDF 逐页位图（需 `pdftoppm` / `mutool` / `magick` 之一） |
| `compare.html` | **并排对照页**：左栏 HTML 报告（iframe）、右栏 PPTX（PDF 内嵌或位图）、上方自动偏差登记表 |
| `deviations.json` | 自动可算偏差（页数区间 / 页数差 / 图表通道） |

**依赖与降级**：

- 无 LibreOffice → 跳过渲染，打印安装指引（可用 `SOFFICE` 环境变量指定可执行文件），**不阻断交付**。
- 无 PDF 位图工具 → 保留 PDF，对照页右栏内嵌 PDF。
- **视觉语义（底色系统 / 图表形态 / 留白节奏 / 曲线几何）仍需人眼在对照页上逐页确认**——脚本负责准备材料与算可量化偏差，不假装能自动判断"好不好看"。

---

## 七、人眼对照清单（渲染对照页上逐页过）

- [ ] **底色系统**：页面底色 / 面板底色 / 结论条底色 / 页脚底色是否与 HTML 一致？有没有把内容区默认变成大面积纯白卡片？
- [ ] **主图形态**：图表类型是否与 HTML 一致（柱是柱、环是环、流带是流带）？有没有被矩形化？
- [ ] **曲线几何**：桑基流带 / 流带图的弯曲幅度与上下边界是否贴合？双边界是否都在（不是只画中心线）？
- [ ] **标签避让**：标签有没有压住图标 / 节点 / 箭头 / 曲线 / 圆环？
- [ ] **锚点位置**：页头标题、主图区、so-what、页脚是否落在与 HTML 相同的位置（P0 ≤3px、P1 ≤4px）？
- [ ] **容器边界**：文字有没有越过卡片 / 单元格 / 结论条（不是只看页面边）？
- [ ] **密度节奏**：整篇有没有连续 3 页同密度 / 同版式？
- [ ] **可编辑性**：双击原生图表能"编辑数据"；非原生图表的数据表在备注或页内表格里。

---

## 八、明确不采纳（及原因）

| 业界做法 | 不采纳原因 |
|---------|-----------|
| ImageGen 逐页蓝图（生成 16:9 位图再逐页还原） | 环境依赖重；且与「单文件零外链 + pictures=0 默认」冲突。本技能以「锁定版式 + 常量单源 + 形状还原规则」达成同等的版式可复现性。 |
| PowerPoint COM 渲染回归作为**硬门禁** | 需本机 PowerPoint；降级为可选路径（本文 §六），日常由 A 通道预览 + python-pptx 双裁判覆盖。 |
| SHA-256 冻结签名 + 逐页人工验收确认 | 交互轮次与耗时显著增加，与「一次问询 + 自动生成 + 校验闭环」定位冲突；改为 manifest 登记（可复现、无需冻结）。 |
| 禁止 `python-pptx`（必须只用 pptxgenjs） | 本技能用 pptxgenjs 做**生成**，用 python-pptx 做**第三方裁判**（`cross_verify.py`）——职责分离比"单一引擎"更能暴露问题（实测抓出两处 OOXML 规范缺陷）。 |
| 联网检索素材（web_search 脚本） | 越出"报告生成"边界；外部数据由用户提供或由 AI 在对话中检索，来源须可追溯（`[n]` + 参考资料）。 |

---

## 九、已落地的高保真增强（对照业界混合通道）

| 增强 | 做法 | 业界参照 |
|------|------|---------|
| **图标真导出** | `icon_lib.js` + sharp 栅格化 PNG，`objectName: icon:*`，`icon_pictures` 单独计数 | Slidev `pptx-editable`：SVG/canvas 按元素降级为图，整页不动 |
| **发射前叠印断言** | `assertNoOverlap` / `rectsOverlap` 在 addShape 前自检组合布局（图表∩inline 数据表等），计入 `OVERLAP_PREEMIT` | IR band allocator；事后裁判（`ELEMENT_OVERLAP`）仍保留 |
| **表格行高自适应** | `addTable` 超容量压到 hardFloor / 整体缩放；表头独立 `headRowH`；`fit:'shrink'` | Measured `colW[]`/`rowH[]`；文本 `fit:'shrink'` |
| **图表区对齐版心** | `regionOf('bar')` 纠正 chartX/chartW 双偏移，与标题/表格左边距一致 | 坐标区域映射的静默漂移防护 |
| **图例收进图高** | waffle/marimekko/slope 图例带含在 `h` 内，与 inline 数据表留间隙 | 几何铁律②「类目标签含在图高 h 内」 |
| **文本自动收缩** | 标题/卡片/结论条/页脚加 `fit:'shrink'`（PowerPoint 字体度量 ≠ 浏览器） | `fit:'shrink'` + 高度余量 |
