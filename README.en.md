# topmind-presentation · TopPPT HTML

**[中文](./README.md)** | English

[![Release](https://img.shields.io/github/v/release/topmindspace/topmind-presentation?style=flat-square&color=blue)](https://github.com/topmindspace/topmind-presentation/releases)
[![npm](https://img.shields.io/npm/v/@topmindspace/topmind-presentation?style=flat-square)](https://www.npmjs.com/package/@topmindspace/topmind-presentation)
[![CI](https://img.shields.io/github/actions/workflow/status/topmindspace/topmind-presentation/ci.yml?style=flat-square&label=CI)](https://github.com/topmindspace/topmind-presentation/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)

**Let ideas fly — make good thinking visible.** A high-craft skill for **demo reports / formal business presentations**: **HTML + PPT dual delivery** — day-to-day, present with paginated HTML like slides; export **layout-faithful editable PPTX** when needed. **MD3-inspired**: fitting information density, restrained type / shapes / color. Core craft is layout, typography, color, and content structure — not gadget soup.

- Skill id: `topmind-presentation`; brand: **TopPPT HTML**
- Version: **v0.2.7** (standalone repo, independently versioned)
- **Agent entry**: `SKILL.md` → `references/playbook.md` (L1) → L2 on demand
- **Human maintainers**: this README (install / commands / layout); do not treat it as the generation spec
- The repo is the skill: the repo root is the skill body (SKILL.md + assets + references + scripts)

<p align="center">
  <img src="docs/assets/presentation-cover.png" alt="topmind-presentation · formal business presentations" width="960" />
</p>

### Theme overview (Gate 0)

<p align="center">
  <img src="assets/theme-overview.png" alt="Presentation · business-blue" width="860" /><br/>
  <sub>Presentation · business-blue (default) · also <a href="./assets/style-gallery.html">style-gallery</a> · <a href="./assets/theme-overview-research.png">research</a> · <a href="./assets/theme-overview-architecture.png">architecture</a></sub>
</p>

**Online** · [Landing](https://topmindspace.github.io/presentation/) (the showcase deck and style gallery are the in-repo files below)

- In-repo gallery: [`assets/style-gallery.html`](./assets/style-gallery.html)
- Product showcase: [`assets/examples/2026-10-11-topmind-presentation-showcase.html`](./assets/examples/2026-10-11-topmind-presentation-showcase.html) (Mode A · dual-delivery narrative · **5 chart types** · toolbar page · install and distribution)
- Repo shot pack: [`docs/showcase/`](./docs/showcase/)

## Skill snapshot

| Dimension | Capability |
|-----------|------------|
| Output | Single-file HTML (paginated, light/dark, **header toolbar T/P/H/F/B + 9 styles**) + 16:9 editable PPTX |
| Positioning | Formal business · dual delivery · MD3-inspired density |
| Modes | A Presentation · B Research · C Architecture |
| Styles | 9 packs (`styles.md`) |
| Charts | Core 8 by default + full registry; variety / anti-truncation / Mode A craft |
| Quality | `validate_report --strict` · `validate_pptx --strict` · `quality_gate --deliver` |

## HTML header toolbar

| Control | Shortcut | Behavior |
|---------|----------|----------|
| Theme toggle | **T** | Light / dark; per-file memory; syncs `REPORT_MODEL.theme` |
| Style picker | 9 styles | Live visual skins; write back `REPORT_MODEL.style` before deliver |
| PPTX preview | **P** | WYSIWYG sequence + copyable agent prompt |
| Generation guide | **H** | Dual-channel + environment notes |
| Fullscreen | **F** | Immersive present |
| Collapse toolbar | **B** | Mini bar; remembers per file |

Also: arrow-key paging; **Esc** closes modals. After style/theme change, re-run `validate_report --strict` (do not rewrite content).

## Install

The repo is the skill: your host must see `topmind-presentation/SKILL.md` inside its skills directory. Pick one:

```bash
# 1. pinned (recommended): unzip topmind-presentation.zip from a GitHub Release
unzip topmind-presentation.zip -d ~/.claude/skills/

# 2. track HEAD
git clone --depth 1 https://github.com/topmindspace/topmind-presentation.git ~/.claude/skills/topmind-presentation

# 3. skills CLI (vercel-labs/skills, Node.js 22+; copies the whole repo including docs/)
npx skills add topmindspace/topmind-presentation --agent claude-code -g

# 4. npm: the package lands in node_modules only, so sync or copy it afterwards
npm i @topmindspace/topmind-presentation
npx skills experimental_sync -a claude-code -y     # experimental; or copy by hand:
cp -r node_modules/@topmindspace/topmind-presentation ~/.claude/skills/topmind-presentation
```

The npm package [`@topmindspace/topmind-presentation`](https://www.npmjs.com/package/@topmindspace/topmind-presentation) is published automatically for each GitHub tag. Like the Release zip it ships only runtime files (the `files` whitelist in `package.json`); the `docs/` site, screenshots and evals stay out. There is no unscoped `topmind-presentation` package on npm.

PPTX needs `npm install` in this folder (pptxgenjs). HTML generation: Python stdlib only.

### Minimal example (~3 min)

```bash
cd topmind-presentation
python3 scripts/scaffold_report.py --mode research --style mckinsey \
  --title "Sample report" --sections 8 --out report.html
# Open report.html, fill in window.REPORT_MODEL only (single source of truth), then:
python3 scripts/render_from_model.py report.html --inplace
python3 scripts/validate_report.py report.html --strict   # ship only at 0 errors / 0 warnings
# For PPTX (after npm install):
python3 scripts/extract_model.py report.html report.model.json
node scripts/build_pptx.js report.pptx --model=report.model.json
python3 scripts/validate_pptx.py report.pptx --strict --model=report.model.json
```

Swap modes: `--mode presentation --style business-blue` (A) / `--mode architecture --style graphite-dark` (C).

Full Chinese maintainer docs (directory map, command cookbook): see [`README.md`](./README.md). Agent rules live in `SKILL.md` / `playbook.md`.

## License

MIT © TopMindspace — [LICENSE](./LICENSE)
