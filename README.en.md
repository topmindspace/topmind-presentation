# topmind-presentation

English | [中文](./README.md)

[![Release](https://img.shields.io/github/v/release/topmindspace/topmind-presentation?style=flat-square&color=blue)](https://github.com/topmindspace/topmind-presentation/releases)
[![npm](https://img.shields.io/npm/v/@topmindspace/topmind-presentation?style=flat-square)](https://www.npmjs.com/package/@topmindspace/topmind-presentation)
[![CI](https://img.shields.io/github/actions/workflow/status/topmindspace/topmind-presentation/ci.yml?style=flat-square&label=CI)](https://github.com/topmindspace/topmind-presentation/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)

An agent skill for presentations. It turns your material into a **single-file, page-turning HTML deck** and, when needed, an **editable 16:9 PPTX**. Both come from one content model, so colours, layouts and numbers match. It can also re-lay-out an existing PPTX without changing a word.

- Version: **v0.2.7** (1.0.0 pending release)
- Agents start at `SKILL.md`; this README is for people installing and maintaining the skill
- The generated content and the skill's own docs are in Chinese

<p align="center">
  <img src="assets/theme-overview.png" alt="Overview of the 12 styles" width="860" /><br/>
  <sub>12 styles, each with light and dark themes · interactive version: <a href="./assets/style-gallery.html">style gallery</a></sub>
</p>

## What it does

| | |
|---|---|
| Deliverables | Single-file HTML (no external links, arrow-key paging, light/dark and style switcher) + editable PPTX (native charts you can double-click to edit) |
| Three modes | Presentation · Research report (dense, sourced) · Architecture (layers / swimlanes / flows / topology) |
| 12 styles | business-blue (default), apple-mono, mckinsey, brand-red, warm-sand, deep-teal, graphite-dark, indigo-violet, spectrum, ink-academic, coral-launch, sky-airy |
| Layouts & charts | 44 layouts in 8 families; 36 chart types, 20 exported as native PowerPoint charts |
| Quality gates | HTML and PPTX must each pass strict with 0 errors and 0 warnings; rendered pages are checked for fill, balance and pixel regressions |

## Five routes

The agent first decides the route, then reads only that route's recipe (`recipes/`).

| You say / give | Route | You get |
|---|---|---|
| "Turn this research into a briefing" | Generate | A titles-only draft to confirm, then HTML (optionally PPTX) |
| "Fast mode, just make it" | Fast | No questions; HTML with sensible defaults |
| An old .pptx + "make it look better" | Beautify | A new deck in a new folder; every word, number, image and speaker note is checked against the original |
| A company template + "use these colours" | Template | Theme colours and fonts extracted; the closest built-in style is used |
| "Draw our system architecture as slides" | Architecture | A 1–8 page, diagram-first deck |

## Install

Your agent's skills folder must contain `topmind-presentation/SKILL.md`. Pick one:

```bash
# Release zip (recommended, pinned version)
unzip topmind-presentation.zip -d ~/.claude/skills/

# Track the repository
git clone --depth 1 https://github.com/topmindspace/topmind-presentation.git ~/.claude/skills/topmind-presentation

# npm (about 1.1 MB, published with provenance), then copy it into the skills folder
npm i @topmindspace/topmind-presentation
cp -r "$(npx topmind-presentation path)" ~/.claude/skills/topmind-presentation
```

Then run the self-check:

```bash
cd ~/.claude/skills/topmind-presentation
npm install                 # only needed for PPTX export (pptxgenjs)
python3 scripts/doctor.py   # or: npx topmind-presentation doctor; add --full to render a sample
```

Requirements: HTML generation and all validators use only the Python 3.8+ standard library. PPTX needs Node 18+ and pptxgenjs; the beautify route needs python-pptx; comparison images and pixel regression need LibreOffice and poppler. `doctor` tells you exactly what is missing.

## Try it by hand

```bash
python3 scripts/render_from_model.py assets/examples/2026-09-09-presentation-business-blue.model.json \
  --template presentation --out demo.html
python3 scripts/validate_report.py demo.html --strict
node scripts/build_pptx.js demo.pptx --model=assets/examples/2026-09-09-presentation-business-blue.model.json
python3 scripts/validate_pptx.py demo.pptx --strict --model=assets/examples/2026-09-09-presentation-business-blue.model.json

# Beautify an existing PPTX (the original is read-only)
python3 scripts/beautify.py old.pptx --out beautified --style business-blue --compare
```

## Layout

```
SKILL.md            agent entry: route table, gates, rules (≤300 lines)
recipes/            one recipe per route; only the chosen one is read
references/         in-depth specs, read only when needed
assets/templates/   HTML templates for the three modes (engine, styles, runtime inlined)
assets/examples/    model.json for three golden samples (npm ships models only; HTML renders in one command)
assets/icons/       48 original line icons
scripts/            render, export, validate, beautify, doctor, regression
tests/              beautify samples, layout goldens, pixel baselines
evals/  docs/       eval set and landing page (not packaged)
```

## Maintenance

```bash
bash scripts/ci_skill_gates.sh --with-pptx   # every gate CI runs
python3 scripts/pixel_regression.py          # pixel regression; add --update after intentional layout changes
bash scripts/smoke_pack.sh                   # pack → install → doctor --full
python3 scripts/sync_runtime.py              # required after editing layout-constants.json / model-schema.json
npm run capture-themes                       # re-capture the style overview above (needs playwright)
```

Changes from 0.x to 1.0: [`docs/MIGRATION-1.0.md`](./docs/MIGRATION-1.0.md). Release notes: [`CHANGELOG.md`](./CHANGELOG.md).

## License

MIT © TopMindspace — [LICENSE](./LICENSE)
