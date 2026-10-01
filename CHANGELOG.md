# CHANGELOG

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
