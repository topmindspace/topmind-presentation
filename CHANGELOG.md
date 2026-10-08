# CHANGELOG

## [0.2.5] - 2026-10-08

> 0.2.4 → **0.2.5**（patch）。

### 优化

**规范与触发**

- `SKILL.md` frontmatter 对齐 Agent Skills 规范：顶层只留 `name / description / license / compatibility`，`version / author / updated / action_category / triggers` 移入 `metadata`（字符串值），`agentskills validate` 通过
- 触发词收窄：去掉 `报告`、`研究报告`、`白皮书`、`复盘`、`fast` 等泛词；description 改为「把已有材料做成正式商务演示与多页可视化报告」，架构图类限定为多页或要 PPTX 交付
- description 增加 Do NOT：找资料与核事实 → topmind-research，整理已存笔记与周复盘 → topmind-organize，工作区巡检与例行复盘 → topmind-loop，单张长图/信息图/榜单图 → topmind-poster，改写已有 PPT/Word → 官方 pptx/docx 技能
- `check_triggers.py` 只用 description 的正向部分计分，并增加兄弟技能分流检查：负例带分流线索时，Do NOT 里必须点名目标技能；触发评测补 N12–N17 六条负例（共 39 条）
- 标题改为 `topmind-presentation · 商务演示与可视化报告`，与技能名一致；增加「分工」说明（材料来自 topmind-research 时沿用其数字与来源）

**npm 与安装**

- `package.json` 增加 `files` 白名单，只发运行所需文件：npm 包从 266 个文件、解包 16.9 MB 降到 197 个文件、约 7.3 MB（压缩包 13.3 MB → 4.6 MB），`docs/`、`assets/showcase/`、`evals/` 不再进包
- README（中英）安装说明与发布流程一致：Release zip、git clone、`npx skills add`、npm 安装后用 `npx skills experimental_sync` 或手动复制进技能目录；删去与自动发 npm 矛盾的「不要 npm install」说法
- Release zip 补进 `assets/icons/`（48 个图标与 `index.json`），之前 zip 安装时图标库缺失
- `package-lock.json` 根版本与 `package.json` 对齐

**引用与 CI**

- `references/modes.md`、`design-system.md`、`tech-design.md`、`icons.md` 与 `scripts/build_examples.py` 里指向 `../docs/archive/` 的引用（文件在 topmind-writing-skills 仓库）改为固定提交 `9a37952` 的 GitHub 链接，标明仅维护者备查
- 新增 `scripts/check_repo.py`：版本六处一致、`SKILL.md` 与 references 不引用技能目录外的路径、npm 包内容符合白名单且不超过 10 MB；接入 `ci_skill_gates.sh`
- CI 与 Release 安装 `skills-ref`，门禁里跑 `agentskills validate`
- `SKILL.md`「版本口径」一节并入 `references/tech-design.md` 已有说明，入口文件保持在 13 KB 预算内

## [0.2.4] - 2026-10-01

> 0.2.3 → **0.2.4**（patch）。cover 按新版 cover 技能重生成（dark-saas 风格：深空黑 + 毛玻璃卡片 + 发光节点）。

## [0.2.3] - 2026-10-01

> 0.2.2 → **0.2.3**（patch）。README/落地页换上按 cover 技能配方新生成的白色清新 banner 封面（5:2）。

> 0.2.1 → **0.2.2**（patch）。独立建仓首个发布版。

- 本技能原为 `topmind-writing-skills`（原 `tms-skills`）monorepo 中的 `top-ppt-html`，
  现独立为 `topmind-presentation` 仓库并改名 **`topmind-presentation`**。
- 仓库即技能：技能文件（SKILL.md / assets / references / scripts / evals / agents）
  移到仓库根目录；docs 下落地页 / showcase / 风格画廊 / 行业研究一并迁移。
- 基础设施：根 `package.json`（`@topmindspace/topmind-presentation`，去 `private`）、
  CI（含 `--with-pptx` 门禁）/ Release workflow（tag v* → GitHub Release + npm）、
  `docs/PUBLISHING.md`、隐私扫描。
- 无引用 banner 图已删除；showcase.html 加历史样张声明。

## 0.2.1（monorepo 时代，见原仓库 CHANGELOG）
