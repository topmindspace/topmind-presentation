# 从 0.x 升级到 1.0

1.0 仍未发布（当前 main 为 0.2.7 + M1–M5 改动）。下面列出升级时需要知道的变化。

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
| 版式库 | 8 家族 44 版式，`check_rhythm.py` 检查节奏；新页型 `chapter` |
| 自检 | `python3 scripts/doctor.py [--full]`，或 `npx topmind-presentation doctor` |
| 回归 | `scripts/pixel_regression.py`（PPTX 像素基线）、`scripts/smoke_pack.sh`（打包安装冒烟），均已接入 CI |

## 移除

| 移除 | 替代 |
|---|---|
| `assets/theme-overview-research.png`、`assets/theme-overview-architecture.png` | 一张 `assets/theme-overview.png` 展示 12 套风格；按模式看效果用 `assets/style-gallery.html` |
| `assets/showcase/`、`docs/showcase/` 截图包、`scripts/capture_showcase_pages.js` | 落地页 `docs/index.html` 与 `docs/showcase.html` |
| npm 包内的示例 HTML | 包内保留 `assets/examples/*.model.json`，一条 `render_from_model.py` 即可得到 HTML |

## 行为变化

- 渲染不再补占位字（如「要点一」「（待填）」「支撑。一句话。」）；模型没写的内容不会出现在页面上。
- 环图单位为 % 且合计为 100 时，中心不再显示「100%」，改为显示 `centerLabel`；图例不再重复一列占比。
- 演示模式整页短表（≤6 行）和 ≤3 张卡片的卡片页会放大行高与字号。
- npm 发布带 provenance（来源证明），包体约 1.1 MB。
