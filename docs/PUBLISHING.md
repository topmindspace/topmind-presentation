# 发布与贡献规范

本仓库即技能 `topmind-presentation`（单技能仓库，无 monorepo 安装器）。

## 分发

| 通道 | 方式 | 特点 |
|------|------|------|
| **GitHub** | clone / 下载 Release zip | 跟 HEAD 或钉版本 |
| **npm** | 包 `@topmindspace/topmind-presentation` | 与 GitHub tag 同版本发布；内容按 `package.json` 的 `files` 白名单（只含运行所需文件）；推荐 `npx @topmindspace/topmind-presentation install` 直接装进技能目录；只 `npm i` 时包在 `node_modules` 里，要再复制进技能目录宿主才能发现 |

- 包：<https://www.npmjs.com/package/@topmindspace/topmind-presentation>
- 仓库：<https://github.com/topmindspace/topmind-presentation>

## 版本策略（务必遵守）

- **默认只升 patch**（修 bug、改文案、小优化）；新能力升 minor；**major 仅用于破坏性变更**。
- `git tag vX.Y.Z` 的 `X.Y.Z` 必须等于根 `package.json` 的 `version`，
  同时与 `SKILL.md` 的 `metadata.version`、`package-lock.json` 根版本、README 中英文的版本号同值，
  由 `scripts/check_repo.py` 校验。
- npm 版本发布后不可覆盖；有变更就要新号；禁止复用 tag 号。

## 发布流程

1. 更新 `CHANGELOG.md`。
2. bump 版本（`package.json` / `package-lock.json` / `SKILL.md` metadata.version / `README.md` / `README.en.md` 同值）。
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
5. 验证：`npm view @topmindspace/topmind-presentation version`

Secret **`NPM_TOKEN`**（granular，scope `@topmindspace` 写权限）配置在 GitHub Actions。

## 落地页（站点）

- 线上地址：<https://topmindspace.github.io/presentation/>。页面源码、截图与中英文文案都在 **topmindspace/topmindspace.github.io** 仓库（`presentation/index.html`、`assets/img/presentation/`、`i18n/zh.json` / `i18n/en.json`），由该仓库的 GitHub Pages 发布。
- 本仓库**没有**开 GitHub Pages，`docs/` 只放本文件和 `MIGRATION-0.2.8.md`，不要再往这里放落地页、showcase 或截图。
- 风格画廊仍是本仓库的 `assets/style-gallery.html`（随包分发）；README 与 Gate 0 用 `assets/theme-overview.png`。
- 刷新站点截图（站点仓库与本仓库并排克隆时）：
  ```bash
  # 风格总览：直接输出到站点仓库，再转成站点用的 JPG
  node scripts/capture_theme_overview.js --out=../topmindspace.github.io/assets/img/presentation
  python3 -c "from PIL import Image;p='../topmindspace.github.io/assets/img/presentation/theme-overview';Image.open(p+'.png').convert('RGB').save(p+'.jpg',quality=85,optimize=True,progressive=True)"
  rm ../topmindspace.github.io/assets/img/presentation/theme-overview.png
  ```
  其余截图（示例页、高密度页、简单页、美化前后对比）用 `make_deck.py` / `beautify.py` 出稿后截取，存成 JPG 放进同一目录；改了图片尺寸要同步 `presentation/index.html` 里的 `width` / `height`。
- 站点要求：蓝白 MD3 风格，中英文、明暗主题都要正常；全站不写版本号（站点仓库 `scripts/check_no_versions.py` 会拦）；安装命令用 `npx @topmindspace/topmind-presentation install`。站点仓库在 main 上提交并 push，不强推；push 后等 Pages 部署完成，再用线上页面截图核对。

## 命名

| 面 | 规则 | 示例 |
|----|------|------|
| 技能 id / frontmatter `name` | kebab-case | `topmind-presentation` |
| 品牌展示名 | 简短 | `topmind-presentation` |
| 环境变量 | `TOP_PPT_*` | `TOP_PPT_NODE_EXE` |
| 注入标记 | `__TOPPPT_*__` | `__TOPPPT_CONSTANTS__` |
| JS API | PascalCase | `TopPptHtml` |
| npm | `@topmindspace/*` | `@topmindspace/topmind-presentation` |

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
