# 食谱 · 从零生成

**什么时候用**：用户有材料（调研、数据、提纲或口述），要一份正式演示文稿或多页报告，没有说「快速」。

| 输入 | 保留什么 | 产出 |
|---|---|---|
| 材料、用途、听众；可选篇幅/风格偏好 | 材料里的数字、来源、结论原样沿用，不补编 | `报告.html`（零外链、可翻页）；选了 PPTX 再加 `报告.pptx` + `报告.model.json`；交付说明 |

## 步骤

1. **Gate 0 参考图**：先给 `assets/theme-overview.png`（12 套风格总览），想边看边挑给 `assets/style-gallery.html`。
2. **六项问询（一轮问完）**：模式 / 篇幅 / 风格 / 亮暗 / 交付格式 / 已看参考图。每项带推荐，用户不选就按推荐。
3. **幽灵稿（只有标题）**：初稿每页正文是「【待填】」空位，strict 校验会报 UNDERFILL，属预期；先写 3–7 章、每页一句主张式标题，用页型规划生成只含标题的骨架给用户看一眼：
   `python3 scripts/scaffold_report.py --mode presentation --plan plan.json --out 草稿.html`
   `plan.json` 每项 `{"type","eyebrow","title"}`；页型列表 `--list-types`。用户确认或改标题后再写内容，只确认这一轮。
4. **方向样张（可选）**：用户在两三套风格之间拿不准时，用同一份模型各渲染封面和一张内容页并排给他挑，不要为此多问。
5. **模型单写**：内容只写进 `REPORT_MODEL`（model.json），不手改 HTML 正文。版式按 `references/layout-library.md` 挑，同一版式不连用超过 2 页，密度 L/M/H 不连续 3 页同档。**每页 = 论点 + 证据 + 解读**：图表页写 `points`（演示 ≥2 条、研究 ≥3 条，写含义不复述数字）和 `keyMetrics`（2–4 个关键数字），需要对照用 `chart2`、看分组用 `minis`（`references/density.md`）。
6. **渲染**：`python3 scripts/render_from_model.py 报告.model.json --template presentation --out 报告.html`
7. **校验**：`python3 scripts/check_density.py 报告.model.json --strict`（信息密度 FAIL 0）；`python3 scripts/validate_report.py 报告.html --strict` 必须 0/0。PPTX：
   `node scripts/build_pptx.js 报告.pptx --model=报告.model.json` → `python3 scripts/validate_pptx.py 报告.pptx --strict --model=报告.model.json` 0/0。
8. **看图复核（五维）**：把每页渲染成图逐页看（`python3 scripts/render_pptx_png.py 报告.pptx --out 预览/`），按 统一性 / 层级感 / 细节精度 / 信息传达 / 排版节奏 五维各记 Keep 与 Fix。空洞、拥挤、字太小、图表太小、版式重复，就地改模型重渲染，最多 2 轮。
9. **交付**：`python3 scripts/quality_gate.py 报告.html --deliver [--pptx 报告.pptx --model 报告.model.json]` 出交付说明。

需要更多：完整七步大纲 `references/outline-design.md`；演示模式工艺 `references/presentation-craft.md`；图表选型 `references/chart-decision-tree.md`。
