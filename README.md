# topmind-presentation · TopPPT HTML

[English](./README.en.md) | 中文

[![Release](https://img.shields.io/github/v/release/topmindspace/topmind-presentation?style=flat-square&color=blue)](https://github.com/topmindspace/topmind-presentation/releases)
[![npm](https://img.shields.io/npm/v/@topmindspace/topmind-presentation?style=flat-square)](https://www.npmjs.com/package/@topmindspace/topmind-presentation)
[![CI](https://img.shields.io/github/actions/workflow/status/topmindspace/topmind-presentation/ci.yml?style=flat-square&label=CI)](https://github.com/topmindspace/topmind-presentation/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)

**让 idea 飞，好想法被看见。** 为**演示报告 / 正式商务演示**而生的高品质演示文稿技能：**HTML + PPT 双交付**——日常用可翻页 HTML 等同幻灯片；需要时再导出**版式保真可编辑 PPTX**。参考 **MD3**：合适信息密度、克制文字/图形/颜色。核心工艺是版式、排版、色彩与内容组织——不是 gadget 堆砌。

- 技能标识：`topmind-presentation`；品牌名：**TopPPT HTML**
- 版本：**v0.2.5**（独立仓库，版本独立演进）
- **智能体入口**：`SKILL.md` → `references/playbook.md`（L1）→ L2 按需
- **人类维护者**：本 README（安装 / 命令 / 目录）；勿把本文件当生成规范
- 仓库即技能：本仓库根目录就是技能本体（SKILL.md + assets + references + scripts），没有 monorepo 安装器

<p align="center">
  <img src="docs/assets/presentation-cover.png" alt="topmind-presentation · 正式商务演示" width="960" />
</p>

### 主题总览（Gate 0）

<p align="center">
  <img src="assets/theme-overview.png" alt="演示模式 · business-blue 主题总览" width="860" /><br/>
  <sub>演示 · business-blue（默认）· 另见 <a href="./assets/style-gallery.html">style-gallery</a> · <a href="./assets/theme-overview-research.png">研究</a> · <a href="./assets/theme-overview-architecture.png">架构</a></sub>
</p>

**在线体验** · [落地页](https://topmindspace.github.io/topmind-presentation/) · [Showcase 演示文稿](https://topmindspace.github.io/topmind-presentation/showcase.html) · [风格画廊](https://topmindspace.github.io/topmind-presentation/style-gallery.html)

- 交互画廊（仓库内）：[`assets/style-gallery.html`](./assets/style-gallery.html)
- 产品 Showcase（仓库内）：[`assets/examples/2026-09-26-topmind-tms-skills-showcase.html`](./assets/examples/2026-09-26-topmind-tms-skills-showcase.html)（Mode A · 双交付叙事 · **5 种图表** · Header 工具栏）
- 大图集：[`docs/showcase/`](./docs/showcase/)（不进技能 zip）

## 一、技能简介（人类速览）

| 维度 | 能力 |
|------|------|
| 产出 | **双交付**：日常 HTML 可翻页演示 + 按需 16:9 可编辑 PPTX；亮暗双主题 · **Header 工具栏 T/P/H/F/B + 9 风格** |
| 定位 | 正式商务演示 · MD3 密度克制 · 非 gadget |
| 三模式 | A 演示 · B 研究 · C 架构（页型/字号/密度契约见 `playbook.md` §一） |
| 风格 | 9 套（`styles.md`）；编码色板 c1–c5 随风格 |
| 图表 | 核图 8 默认 + registry 全量；多样性 / 反截断 / Mode A 工艺见 playbook + `presentation-craft.md` |
| 质量 | `validate_report --strict`（A 隐含 layout-qa）· `validate_pptx --strict` · `quality_gate --deliver` |

## HTML Header 工具栏

打开交付的 HTML 即可使用顶栏快捷操作（产品 Showcase 有专页演示）：

| 控件 | 快捷键 | 行为 |
|------|--------|------|
| 亮暗主题 | **T** | 浅色外发 / 深色大屏；**按文件记忆**；同步 `REPORT_MODEL.theme` |
| 风格选择 | 9 套下拉 | 九风格实时切换（纯视觉，不动内容）；交付前 `data-style` = `REPORT_MODEL.style` |
| 预览 PPTX | **P** | 页序列所见即所得；可复制提示词回对话走精导 |
| PPT 生成指引 | **H** | 双通道说明与环境依赖（与 `?` 同效） |
| 全屏 | **F** | 沉浸演示 |
| 收起工具栏 | **B** | 折叠为迷你条；锚点自适应并按文件记忆 |

另：方向键翻页；**Esc** 关闭预览/帮助模态。风格或主题变更后须重跑 `validate_report --strict`（不重写内容）。

生成规范、页型/图表穷举、铁律 **不在本文件**——智能体读 `SKILL.md` / playbook；选型大表见 `page-type-matrix.md` / `chart-decision-tree.md`。

**核心架构**：HTML 与 PPTX 出自同一内容模型 `window.REPORT_MODEL`（唯一事实源）；页面只预览不导出，PPTX 由智能体走「精导通道」生成（extract → build → strict 校验）。阈值与几何全部单源化：`scripts/layout-constants.json`（常量）+ `scripts/model-schema.json`（页型 DSL）。

## 二、安装与使用

### 安装

仓库即技能：宿主要能在技能目录里看到 `topmind-presentation/SKILL.md`。四种装法任选：

```bash
# 1. 钉版本（推荐）：下载对应 Release 的 topmind-presentation.zip，解压到技能目录
unzip topmind-presentation.zip -d ~/.claude/skills/

# 2. 跟仓库 HEAD
git clone --depth 1 https://github.com/topmindspace/topmind-presentation.git ~/.claude/skills/topmind-presentation

# 3. skills CLI（vercel-labs/skills，需要 Node.js 22+；会把整个仓库含 docs/ 复制进去）
npx skills add topmindspace/topmind-presentation --agent claude-code -g

# 4. npm：包只进 node_modules，宿主发现不了，装完要再同步或复制一次
npm i @topmindspace/topmind-presentation
npx skills experimental_sync -a claude-code -y     # 实验性命令；或手动：
cp -r node_modules/@topmindspace/topmind-presentation ~/.claude/skills/topmind-presentation
```

npm 包 [`@topmindspace/topmind-presentation`](https://www.npmjs.com/package/@topmindspace/topmind-presentation) 随 GitHub tag 自动发布（版本号与 tag 一致），内容与 Release zip 同为运行所需文件（`package.json` 的 `files` 白名单），不含 `docs/` 落地页、截图和评测集。npm 上没有不带 scope 的 `topmind-presentation` 包，不要装错。

**依赖**：HTML 生成与全部校验脚本零第三方依赖（Python 标准库）。只有「生成 PPTX」需要 Node + pptxgenjs：

```bash
cd topmind-presentation
npm install                  # 依 package.json 安装 pptxgenjs（^4）
```

脚本会自动探测 Node 与 node_modules（`TOP_PPT_NODE_EXE` / `TOP_PPT_NODE_PATH` 环境变量 > `PATH` > 常见托管目录），不绑定任何机器的固定路径。参考图刷新（可选，非交付依赖）另需 playwright。

### 最小示例（复制即跑 · 约 3 分钟）

```bash
cd topmind-presentation
python3 scripts/scaffold_report.py --mode research --style mckinsey \
  --title "示例报告" --sections 8 --out report.html
# 用浏览器打开 report.html，只填 window.REPORT_MODEL（内容唯一事实源），然后：
python3 scripts/render_from_model.py report.html --inplace
python3 scripts/validate_report.py report.html --strict   # 0 errors / 0 warnings 才交付
# 要 PPTX 时（先 npm install 装好 pptxgenjs）：
python3 scripts/extract_model.py report.html report.model.json
node scripts/build_pptx.js report.pptx --model=report.model.json
python3 scripts/validate_pptx.py report.pptx --strict --model=report.model.json
```

三模式速换：`--mode presentation --style business-blue`（A 演示）/ `--mode architecture --style graphite-dark`（C 架构）。完整工作流与门禁见「智能体视角」与 `references/playbook.md`。

### 用户视角（三步走）

1. 对智能体说出意图（例：「帮我把这份调研做成一份咨询风格的研究报告」）
2. 回答一次**六项问询**（全部带推荐，不选即按推荐走）：①模式 ②篇幅 ③风格 ④亮暗主题 ⑤交付格式（仅 HTML / HTML+PPTX）⑥参考图
3. 收到交付：HTML 落到指定输出目录（默认当前工作目录）；需要 PPTX 时智能体走精导通道一并生成——或事后打开报告页面点「预览 PPTX」复制提示词回对话补生成

### 智能体视角（工作流）

```
听意图 → Gate 0 参考图 → 六项问询 → 路径判定（轻量默认 / 完整走 outline-design.md 七步法）
→ scaffold_report.py 起骨架（勿整读/复制模板）→ **只填 window.REPORT_MODEL** → `render_from_model.py --inplace`
→ validate_report.py --strict 全 PASS → 交付（默认 HTML）
→（用户要 PPTX 时 · **仅 B 通道**）extract_model.py → build_pptx.js --model → validate_pptx.py --strict 0/0
```

渐进式披露：`L0` = `SKILL.md`（路由 + 门禁 + 铁律）；`L1` = `references/playbook.md`（唯一常读入口）；`L2` = 深度规范，**只在命中条件时读、读完即停**；取码必须 `extract_snippet.py`（整读大 L2 = FAIL）。

## 三、目录结构

```
topmind-presentation/          # 仓库即技能：根目录就是技能本体
├─ SKILL.md                     # 智能体入口：触发描述 + 工作流 + 铁律
├─ README.md                    # 本文件：人类视角的简介/开发/打包
├─ package.json                 # Node 依赖（pptxgenjs）与常用命令
├─ agents/openai.yaml           # Codex / ChatGPT Skills UI 元数据
├─ assets/                      # 模板 + 引擎/UI + 示例 + 主题参考图
│  ├─ templates/                #   三份模式模板（presentation/research/architecture）
│  ├─ examples/                 #   3 黄金样张 + showcase（HTML+model）
│  ├─ style-gallery.html        #   风格 × 模式 × 亮暗主题交互画廊
│  └─ theme-overview*.png       #   3 张主题参考图（Gate 0）
├─ references/                  # 规范（L1 常读 1 篇 + L2 按需；components/charts 已按族拆分）
│  └─ playbook.md               #   ★ L1 唯一常读入口
├─ evals/                       # Eval 框架（结果/过程/风格/效率四类目标）
├─ docs/                        # 落地页 / showcase / 风格画廊（Pages 源）· 行业研究
├─ scripts/                      # 生成/校验/回归/维护工具（见下表）
├─ .gitignore                   # 出库规则
└─ dist/                        # 构建与回归产物 + 分发包 zip + 发布清单  ← 不进包、不入库
```

---

## 常用命令（细节见 `references/playbook.md`）

```bash
# 标准 / Fast 共用链（模型单写）
python scripts/scaffold_report.py --mode research --style mckinsey --theme light \
  --title "标题" --sections 8 --out report.html
# 只填 window.REPORT_MODEL 后：
python scripts/render_from_model.py report.html --inplace
python scripts/validate_report.py report.html --strict --layout-qa
python scripts/quality_gate.py report.html --deliver

# 布局建议 / PPTX
python scripts/recommend_layout.py --mode B --intent "经营分析" --pages 10 --json
python scripts/extract_model.py report.html report.model.json
node scripts/build_pptx.js report.pptx --model=report.model.json
python scripts/validate_pptx.py report.pptx --strict --model=report.model.json
bash scripts/smoke_pptx.sh

# 门禁
python scripts/package_skill.py --check
python scripts/audit_skill.py && python scripts/audit_docs.py
python scripts/audit_styles.py && python scripts/audit_css.py
python scripts/negative_tests.py
python scripts/check_triggers.py
```

完整规范索引见 playbook §十。

## 许可证

MIT © TopMindspace — [LICENSE](./LICENSE)
