# 发布与贡献规范

本仓库即技能 `topmind-presentation`（单技能仓库，无 monorepo 安装器）。

## 分发

| 通道 | 方式 | 特点 |
|------|------|------|
| **GitHub** | clone / 下载 Release zip | 跟 HEAD 或钉版本 |
| **npm** | 包 `@topmindspace/tms-presentation-skills` | 与 GitHub tag 同版本发布 |

- 包：<https://www.npmjs.com/package/@topmindspace/tms-presentation-skills>
- 仓库：<https://github.com/topmindspace/tms-presentation-skills>

## 版本策略（务必遵守）

- **默认只升 patch**（修 bug、改文案、小优化）；新能力升 minor；**major 仅用于破坏性变更**。
- `git tag vX.Y.Z` 的 `X.Y.Z` 必须等于根 `package.json` 的 `version`，
  同时与 `SKILL.md` frontmatter 的 `version` 同值（三处一致）。
- npm 版本发布后不可覆盖；有变更就要新号；禁止复用 tag 号。

## 发布流程

1. 更新 `CHANGELOG.md`。
2. bump 版本（三处同值：`package.json` / `SKILL.md` frontmatter / `README.md`）。
3. 门禁：
   ```bash
   bash scripts/ci_skill_gates.sh --with-pptx
   python3 scripts/ci_privacy_scan.py
   ```
4. 提交并打 tag：
   ```bash
   git tag vX.Y.Z
   git push origin main --tags
   ```

   Release workflow（`.github/workflows/release.yml`）按序执行：
   - **tag ↔ `package.json` 交叉校验**：不一致直接失败。
   - 门禁（含 `--with-pptx` 冒烟）→ `package_skill.py` 打包 → GitHub Release。
   - `npm publish`：先查 registry，版本已存在则跳过；**`NPM_TOKEN` 缺失 → 显式失败**；
     E409 / 版本冲突 → 显式失败（说明打 tag 前没 bump；禁止复用 tag 号）。
   - prune Releases（留最近 2 个；git tags 保留不删）。
5. 验证：`npm view @topmindspace/tms-presentation-skills version`

Secret **`NPM_TOKEN`**（granular，scope `@topmindspace` 写权限）配置在 GitHub Actions。

## 命名

| 面 | 规则 | 示例 |
|----|------|------|
| 技能 id / frontmatter `name` | kebab-case | `topmind-presentation` |
| 品牌展示名 | 简短 | `TopPPT HTML` |
| 环境变量 | `TOP_PPT_*` | `TOP_PPT_NODE_EXE` |
| 注入标记 | `__TOPPPT_*__` | `__TOPPPT_CONSTANTS__` |
| JS API | PascalCase | `TopPptHtml` |
| npm | `@topmindspace/*` | `@topmindspace/tms-presentation-skills` |

## 隐私检查清单

- [ ] 无绝对本地路径 / 用户名 / 主机名 / 凭据
- [ ] 无 IDE / 智能体本机状态、`node_modules`、`dist`
- [ ] `SKILL.md` description ≤ 1024，含「做什么 + 何时用 + 何时不用」

```bash
python3 scripts/ci_privacy_scan.py
```

## 历史

本技能 2026-10-01 前为 `tms-skills`（现 `topmind-writing-skills`）monorepo 中的
`top-ppt-html`，后独立为本仓库并改名 `topmind-presentation`。旧名仅出现在
CHANGELOG 历史与迁移说明中，新代码禁止使用。
