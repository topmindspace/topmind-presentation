# 从 0.2.7 及更早版本升级到 0.2.8

0.2.8 汇总了 0.2.7 之后 M1–M11 的全部改动。下面列出升级时需要知道的变化；逐条记录见 `CHANGELOG.md`。

## 不需要改的

- `REPORT_MODEL` / model.json 的已有字段全部兼容；0.x 的模型可以直接渲染。
- 命令行入口不变：`render_from_model.py`、`build_pptx.js`、`validate_report.py`、`validate_pptx.py`、`quality_gate.py`。
- 风格 id 不变；`business-blue` 仍是默认，只是中文名改为「清新蓝白」。

## 新增

| 变化 | 说明 |
|---|---|
| 五条路线 + `recipes/` | 生成 / 快速 / 美化 / 套模板 / 架构图，SKILL.md 顶部路线表判定后只读一份食谱 |
| 美化已有 PPTX | `scripts/beautify.py`；模型新增 `contentLocked`、`coverNotes`、`agendaNotes`、`sections[].speakerNotes` 等字段（均可选） |
| 套模板 | `scripts/extract_template.py` 从参考 PPTX 取主题色与字体，映射到最接近的内置风格 |
| 风格 | 新增 `ink-academic`、`coral-launch`、`sky-airy`，共 12 套 |
| 版式库 | 8 家族 48 版式（含复合版式 chart-readout / chart-dual / chart-minis / chart-band），`check_rhythm.py` 检查节奏；新页型 `chapter` |
| 自检 | `python3 scripts/doctor.py [--full]`，或 `npx topmind-presentation doctor` |
| 回归 | `scripts/pixel_regression.py`（PPTX 像素基线）、`scripts/smoke_pack.sh`（打包安装冒烟），均已接入 CI |
| 安装命令 | `npx @topmindspace/topmind-presentation install [--to 目录] [--force] [--link]`：旧版直接覆盖升级、拒绝静默降级、同一技能的同名目录自动替换 |
| 一条命令出稿 | `npx topmind-presentation build 稿件.model.json [--out 目录] [--fidelity]`（`make_deck.py`）：渲染 → HTML strict → 密度 → PPTX → PPTX strict → 双端保真 |
| 双端保真门禁 | `scripts/check_fidelity.py`：逐页比对 HTML 与 PPTX 的文字配对、字级层级、颜色、换行、位置，四模式统一阈值 |
| 信息密度 | 图表页 `keyMetrics` / `points` / `chart2` / `minis` 自动升级为复合版式；`check_density.py` 门禁 |
| 风格气质 | `stylePptx`：12 套风格各自的标题字体、字重、标题线、卡片与表格质感；衬线风格 Georgia + SimSun |
| 扩展点 | `references/extending.md`：写稿时可组合的字段、维护者如何加风格 / 版式 / 图表，以及刻意不开放的部分 |

## 移除

| 移除 | 替代 |
|---|---|
| `assets/theme-overview-research.png`、`assets/theme-overview-architecture.png` | 一张 `assets/theme-overview.png` 展示 12 套风格；按模式看效果用 `assets/style-gallery.html` |
| `assets/showcase/`、`docs/showcase/` 截图包、`scripts/capture_showcase_pages.js` | 落地页 https://topmindspace.github.io/presentation/（0.2.11 起由 topmindspace.github.io 仓库维护，本仓库不再放 `docs/index.html` / `docs/showcase.html`） |
| npm 包内的示例 HTML | 包内保留 `assets/examples/*.model.json`，一条 `render_from_model.py` 即可得到 HTML |

## 行为变化

- 渲染不再补占位字（如「要点一」「（待填）」「支撑。一句话。」）；模型没写的内容不会出现在页面上。
- 环图单位为 % 且合计为 100 时，中心不再显示「100%」，改为显示 `centerLabel`；图例不再重复一列占比。
- 演示模式整页短表（≤6 行）和 ≤3 张卡片的卡片页会放大行高与字号。
- npm 发布带 provenance（来源证明），包体约 1.1 MB。
- 研究模式：一个 `exhibitNo` 都不写时 HTML 与 PPTX 同样自动编号；写了任意一个即全按手写编号（此前自动号会与手写号重复）。
- 研究模式版心 1240px → 1320px；复合 band 页主图限高，整页收在一屏内。
- PPTX 图片不再加椭圆遮罩（pptxgenjs 的 rounding 实为椭圆），照片四角不再被裁掉。
- 含中文的文字运行标注 `lang="zh-CN"`。
