# CHANGELOG

## [Unreleased] 独立建仓（2026-10-01，未发版）

- 本技能原为 `topmind-writing-skills`（原 `tms-skills`）monorepo 中的 `top-ppt-html`，
  现独立为 `topmind-presentation` 仓库并改名 **`topmind-presentation`**。
- 仓库即技能：技能文件（SKILL.md / assets / references / scripts / evals / agents）
  移到仓库根目录；docs 下落地页 / showcase / 风格画廊 / 行业研究一并迁移。
- 基础设施：根 `package.json`（`@topmindspace/topmind-presentation`，去 `private`）、
  CI（含 `--with-pptx` 门禁）/ Release workflow（tag v* → GitHub Release + npm）、
  `docs/PUBLISHING.md`、隐私扫描。
- 技能版本沿用 **0.2.1**；npm 包首次发布将从本仓库 tag 打起。

## 0.2.1（monorepo 时代，见原仓库 CHANGELOG）
