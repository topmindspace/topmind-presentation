# topmind-presentation

[English](./README.en.md) | 中文

[![Release](https://img.shields.io/github/v/release/topmindspace/topmind-presentation?style=flat-square&color=blue)](https://github.com/topmindspace/topmind-presentation/releases)
[![npm](https://img.shields.io/npm/v/@topmindspace/topmind-presentation?style=flat-square)](https://www.npmjs.com/package/@topmindspace/topmind-presentation)
[![CI](https://img.shields.io/github/actions/workflow/status/topmindspace/topmind-presentation/ci.yml?style=flat-square&label=CI)](https://github.com/topmindspace/topmind-presentation/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)

一个给智能体用的演示文稿技能：把材料做成**可翻页的单文件 HTML**，需要时再导出**可编辑的 16:9 PPTX**。两份交付出自同一份内容模型，配色、版式和数字一致。也能把已有的 PPTX 原文不动地重新排版。

- 版本：**v0.2.10**
- 智能体从 `SKILL.md` 进入；本 README 写给安装和维护的人

<p align="center">
  <img src="assets/theme-overview.png" alt="12 套风格总览" width="860" /><br/>
  <sub>12 套风格 · 每套都有浅色与深色 · 交互版见 <a href="./assets/style-gallery.html">风格画廊</a></sub>
</p>

## 能做什么

| | |
|---|---|
| 交付 | 单文件 HTML（零外链、方向键翻页、亮暗切换、风格切换）+ 可编辑 PPTX（原生图表可双击改数据） |
| 三种模式 | 演示汇报 · 研究报告（高密度、带来源）· 架构图（分层 / 泳道 / 流程 / 拓扑） |
| 12 套风格 | 清新蓝白（默认）、优雅黑白、麦肯锡咨询、品牌红、暖沙金、墨绿、石墨深灰、靛紫、光谱彩色、学术墨蓝、活力珊瑚、晴空课件 |
| 版式与图表 | 8 个家族 51 个版式；37 种图表，其中 20 种导出为原生 PPT 图表 |
| 高密度与简单页 | 仪表盘（2–4 图共用配色、坐标与图例）、杂志版（大图 + 金句 + 数字 + 要点）；简单页 12 种变体（一个数字 / 一句观点 / 一个图标 / 一张图），过密拆页、过空有门禁 |
| 插图 | 图文混排（满版 / 左图右文 / 出血 / 网格 / 对比 / Logo 墙）；分层图、泳道、流程、拓扑在 PPTX 里是可编辑的原生形状 |
| 已有 PPT 美化 | 原稿只读，逐字逐数、图片与演讲者备注核对一致后出新稿；一页多图走仪表盘 / 双图对照，表 + 图走半表半图（[前后对比](./docs/site-assets/beautify-before-after.jpg)） |
| 质量门禁 | HTML 与 PPTX 各自 strict 0 错误 0 警告才交付；双端逐页保真比对；渲染后检查填充率、重心和像素回归 |
| 版面 | 正文行距默认 1.5 倍（放不下降到 1.3 倍）；默认不放眉标和页脚小字，只留页码，省下的空间给正文（`showEyebrow` / `showFootnotes` / `pageNumber` 可开关） |
| 复杂信息图 | 复合版式、双图对照、小图组、图文混排的写法与 PPTX 边界见 [`references/infographics-guide.md`](./references/infographics-guide.md) |
| 可扩展 | 规则内自定义版式、风格、图表的扩展点见 [`references/extending.md`](./references/extending.md) |

## 五条路线

智能体先判断属于哪条路线，再只读对应的食谱（`recipes/`）。

| 你说 / 你给 | 路线 | 得到 |
|---|---|---|
| 「把这份调研做成汇报」 | 从零生成 | 先看一版只有标题的草稿，确认后出 HTML（可加 PPTX） |
| 「快速模式，直接生成」 | 快速出稿 | 不问问题，按默认值直接出 HTML |
| 一份旧 .pptx +「美化一下」 | 美化 | 新目录里的新稿，每个字、每个数、图片和演讲者备注都与原稿核对一致 |
| 公司模板 +「按这个配色做」 | 套模板 | 取模板的主题色和字体，选最接近的内置风格出稿 |
| 「画一下系统架构，要 PPT」 | 架构图 | 1–8 页图解优先的架构演示文稿 |

## 安装

技能目录里要能看到 `topmind-presentation/SKILL.md`。推荐用安装命令：

```bash
npx @topmindspace/topmind-presentation install                    # 自动探测 ./.claude、./.agents、./.cursor、./.codex，再找用户目录
npx @topmindspace/topmind-presentation install --to ~/.claude/skills
npx @topmindspace/topmind-presentation@latest install             # 升级：旧版直接覆盖
npx @topmindspace/topmind-presentation@0.2.7 install --force       # 降级必须加 --force
npx @topmindspace/topmind-presentation install --link             # 开发用：符号链接到包目录，而不是复制
```

安装规则（`tests/install/test_install.js` 覆盖，CI 硬门禁）：

1. **默认直接升级**：已装版本比安装包旧（或读不到版本号）时直接覆盖，不备份；版本相同提示「已是最新」，加 `--force` 才重装。
2. **不会悄悄降级**：已装版本比安装包新时报错退出，只有加 `--force` 才降级。
3. **同名文件夹自动替换**：默认安装方式（复制）下，目标目录如果是之前装的同一技能（`SKILL.md` 的 name 是 `topmind-presentation`，或是指向它的符号链接），直接替换，不用 `--force`；名字相同但内容无关的文件夹（没有 SKILL.md、name 不同）必须加 `--force` 才会被替换。符号链接只删链接本身，不会删到它指向的目录。

其他装法：


```bash
# Release zip（推荐，版本固定）
unzip topmind-presentation.zip -d ~/.claude/skills/

# 跟随仓库最新
git clone --depth 1 https://github.com/topmindspace/topmind-presentation.git ~/.claude/skills/topmind-presentation

# npm（包约 1.1 MB，带来源证明）。装到 node_modules 后复制到技能目录
npm i @topmindspace/topmind-presentation
cp -r "$(npx topmind-presentation path)" ~/.claude/skills/topmind-presentation
```

装完跑一次自检：

```bash
cd ~/.claude/skills/topmind-presentation
npm install                 # 只有导出 PPTX 需要（pptxgenjs）
python3 scripts/doctor.py   # 或 npx topmind-presentation doctor；加 --full 实际渲染一份样张
```

依赖：HTML 生成和全部校验只用 Python 3.8+ 标准库；PPTX 需要 Node 18+ 与 pptxgenjs；美化路线需要 python-pptx；渲染对照图和像素回归需要 LibreOffice 与 poppler。doctor 会逐项告诉你缺什么。

## 手动跑一遍

```bash
python3 scripts/render_from_model.py assets/examples/2026-09-09-presentation-business-blue.model.json \
  --template presentation --out demo.html
python3 scripts/validate_report.py demo.html --strict
node scripts/build_pptx.js demo.pptx --model=assets/examples/2026-09-09-presentation-business-blue.model.json
python3 scripts/validate_pptx.py demo.pptx --strict --model=assets/examples/2026-09-09-presentation-business-blue.model.json

# 一条命令：渲染 → 双端 strict → 密度 → 保真
npx topmind-presentation build assets/examples/2026-09-09-research-mckinsey.model.json --out out --fidelity

# 美化已有 PPTX（原稿只读）
python3 scripts/beautify.py 旧稿.pptx --out 美化结果 --style business-blue --compare
```

## 目录

```
SKILL.md            智能体入口：路线表、门禁、铁律（≤300 行）
recipes/            五条路线的食谱，选定路线后只读一份
references/         深度规范，命中条件才读
assets/templates/   三种模式的 HTML 模板（引擎、样式、运行时内联）
assets/examples/    三份黄金样张 + 一份 22 页高密度示例（城市公交电动化复盘）的 model.json（npm 包内只含模型，HTML 可一键渲染）
assets/icons/       72 个原创图标（SVG + 256px 单色 PNG，用法见 references/icons.md）
scripts/            渲染、导出、校验、美化、doctor、回归
tests/              美化样例、版式 golden、像素基线
evals/  docs/       评测集与落地页（不进包）
```

## 维护

```bash
bash scripts/ci_skill_gates.sh --with-pptx   # CI 同款全部门禁
python3 scripts/pixel_regression.py          # 像素回归；有意改版式后加 --update 重建基线
bash scripts/smoke_pack.sh                   # 打包 → 安装 → doctor --full
python3 scripts/sync_runtime.py              # 改了 layout-constants.json / model-schema.json 后必跑
npm run capture-themes                       # 重拍本页的风格总览图（需 playwright）
```

从旧版升级到 0.2.8 的变化见 [`docs/MIGRATION-0.2.8.md`](./docs/MIGRATION-0.2.8.md)，逐版记录见 [`CHANGELOG.md`](./CHANGELOG.md)。

## 许可证

MIT © TopMindspace — [LICENSE](./LICENSE)
