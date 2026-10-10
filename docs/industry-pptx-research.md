# Industry Research: High-Fidelity HTML/Web Slide → Editable PPTX Export

> 备注（2026-10-01）：本研究写于技能独立建仓前，文中 `top-ppt-html`（原所在的
> `tms-skills` 仓库）均指现在的 `topmind-presentation`，内容原样保留。

**Context:** Skill generates HTML presentation reports; exports editable 16:9 PPTX via PptxGenJS.  
**Current pain:** charts overlap tables, table layout breaks, icons/SVGs disappear, text overflow, low fidelity vs HTML.  
**Goal:** industry-proven architecture and concrete fixes — not reinvention.

**Research method note:** Research used public documentation pages for each product and library. Search-engine results were low-signal for English technical queries, so product docs and official libraries were opened directly. Findings marked **[VERIFIED]** come from pages that were actually opened; **[INDUSTRY]** are well-established patterns inferred from product behavior and standard practice, not page-verified.

---

## 1. Taxonomy of Approaches (editable vs fidelity vs effort)

| Pattern | What it does | Fidelity | Editable | Effort | Who uses it |
|---|---|---|---|---|---|
| **A. Full rasterize** | Screenshot each HTML slide → one image per slide in PPTX | ★★★★★ perfect | ★☆☆☆☆ (crop notes only) | Low | Slidev `--format pptx`, Marp PPTX (image-based), reveal.js → PDF/print, many "export deck" tools |
| **B. Hybrid per-element** | Measure HTML in browser; rebuild text/shapes/tables as native PPTX; complex visuals (SVG/canvas/filters) stay as pictures | ★★★★☆ | ★★★★☆ (text/shapes edit) | High | **Slidev `pptx-editable`** (newest industry reference implementation) |
| **C. Native OOXML mapping** | Map DOM/CSS → OOXML shapes/charts/tables directly | ★★★☆☆ | ★★★★★ | Very high | PowerPoint itself (internal), python-pptx / PptxGenJS when authoring structured data (not arbitrary HTML) |
| **D. Template fill** | Pre-authored master/layouts; inject content into placeholders | ★★★★☆ (within template) | ★★★★★ | Medium | Consulting templates, corporate brand decks, python-pptx placeholders |
| **E. Coordinate region mapping** | CSS layout boxes → absolute EMU boxes; no flow reflow | ★★★☆☆ | ★★★☆☆ | Medium | Various HTML→PPT converters; PptxGenJS absolute `x,y,w,h` |
| **F. Semantic IR + renderer** | HTML → intermediate slide model → PPTX/PDF/HTML | ★★★★☆ | ★★★★☆ | High | Gamma/Tome/Beautiful.ai class (product IR, then multiple exporters) |

### Tradeoff summary

- **Perfect visual + zero editability:** A (rasterize). Use as *fallback*, not primary, if "editable PPTX" is a requirement.
- **Best balance for HTML-report → editable PPTX:** **B hybrid**, with C/D for known components (charts, tables, titles).
- **Do not** attempt full CSS→OOXML (gradients, blend modes, clip-path have no PPTX equivalent). Cut lossy features as images.

**Industry consensus (Slidev docs, VERIFIED):**  
> "all the slides in the PPTX file will be exported as images, so the text will not be selectable" (`--format pptx`)  
> "export it with native shapes instead of pictures… The slides are measured in the browser and rebuilt as PowerPoint shapes" (`--format pptx-editable`)  
> "What stays a picture: anything PowerPoint has no equivalent for… SVG… canvas… KaTeX… CSS gradients, filter, backdrop-filter, mix-blend-mode and clip-path. Only the element concerned becomes a picture, not the whole slide."

That is the architecture we should copy.

---

## 2. How Specific Products Handle HTML→PPTX

### 2.1 Slidev **[VERIFIED — best reference]**
Source: https://sli.dev/guide/exporting.html

| Mode | Mechanism |
|---|---|
| `export --format pptx` | Playwright/Chromium render → **image per slide** |
| `export --format pptx-editable` | **Measure in browser → rebuild as PowerPoint shapes**; per-element picture fallback |

Documented limitations of editable path (transfer directly as our risk list):
1. **Fonts named, not embedded** — recipients need fonts installed or PowerPoint substitutes.
2. **PowerPoint text metrics ≠ browser metrics** — long paragraphs wrap to different line counts.
3. **`::before` / `::after` decorations in normal flow are dropped** (CSS counters for code line numbers included).
4. Unrebuildable slides fall back to **image export for that slide alone**, with a printed reason.
5. SVG (Mermaid/icons), canvas, iframe, video, KaTeX, CSS gradients/filters/blend/clip-path stay **pictures**.

### 2.2 Marp **[VERIFIED]**
Source: https://marp.app/docs/introduction/whats-marp  
- Goal: "PDF, PPTX, and HTML versions of your slides look exactly the same."  
- Export requires Chromium.  
- PPTX is explicitly for "if you want to add additional content manually in PowerPoint" → **image-first** path.  
- Architecture: Markdown → HTML/CSS → Chromium print/screenshot → PDF/PPTX.

### 2.3 reveal.js **[VERIFIED]**
Source: https://revealjs.com/pdf-export/  
- Official export is **PDF via print stylesheet** (`?print-pdf`), Chrome only.  
- No first-class editable PPTX. Community tools (decktape) also PDF-oriented.  
- Lesson: web-native deck tools often **give up on editable PPTX** and ship PDF/image PPTX.

### 2.4 PptxGenJS HTML feature **[VERIFIED]**
Source: https://gitbrent.github.io/PptxGenJS/html2pptx/  
- `tableToSlides(tableElementId)` converts **HTML `<table>` only** → slides (CSS copied into table, auto-paging).  
- **Not** a general HTML/CSS layout engine. Using it for full slide HTML is a category error.

### 2.5 Google Slides / PowerPoint HTML import / Canva / Gamma / Tome / Beautiful.ai **[INDUSTRY / partial]**
- **PowerPoint HTML import:** Word/HTML open path is layout-lossy (HTML tables→Word tables, absolute CSS lost). Not a production exporter. Office Open XML is the native path (PresentationML structure, VERIFIED via Microsoft Learn).
- **Canva / Gamma / Tome:** typically own **document IR** (cards/blocks), then exporters: native shapes + images for complex art; charts often native PowerPoint charts when the chart is a first-class IR object, else image. Export quality degrades on custom CSS. (Not page-verified this session; treat as product-class pattern.)
- **Beautiful.ai:** historically used / forked PptxGenJS (visible in search results: `beautifulai/PptxGenJS`) — confirms JS OOXML generation is industry-standard for web→PPTX.
- **Google Slides import of PPTX:** re-interprets OOXML; native charts may convert; freeform SVG-like art often becomes images or drops.

### 2.6 think-cell / Mekko Graphics **[INDUSTRY + think-cell public docs]**
Sources: https://think-cell.com/en/resources/kb , product pages  
- **Not HTML exporters** — PowerPoint **COM add-ins** that insert native chart objects with Excel data links.
- Fidelity strategy: (1) native PowerPoint chart XML / shape trees, (2) Excel-linked data, (3) their own label/layout engine on top of PowerPoint shapes (waterfall, Gantt, Mekko).
- KB evidence: Excel data links, “Convert to Office Open XML”, Google Slides “does not properly display think-cell charts” (KB0224) — proves they rely on **native PPT constructs**, not bitmaps.
- Takeaway for us: **for charts that must look consulting-grade AND stay editable, emit native OOXML charts (or PowerPoint shape-composed charts), not HTML screenshots.**

---

## 3. Recommended Hybrid Architecture (for our HTML-report → editable PPTX skill)

```
HTML slide (fixed 16:9 viewport)
        │
        ▼
┌───────────────────────────────────────┐
│ 1. Headless Chromium measure pass     │
│    - document.fonts.ready             │
│    - getBoundingClientRect() per node │
│    - computed styles (font, color,    │
│      border, background, overflow)    │
│    - z-order / stacking context       │
│    - semantic tags: data-pptx=        │
│      chart|table|title|body|icon|…    │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│ 2. Slide IR (JSON)                    │
│    page: 13.333in × 7.5in (16:9)      │
│    layers[] with role + bbox + style  │
└───────────────────────────────────────┘
        │
        ├──────────────────┬──────────────────┐
        ▼                  ▼                  ▼
  Native PPTX         Native PPTX        Picture layer
  text/shapes         charts/tables      SVG, canvas,
  (absolute EMU)      (addChart/         complex CSS,
                      addTable)          icons fallback
        │                  │                  │
        └──────────────────┴──────────────────┘
                           ▼
                    PptxGenJS 16:9 deck
                    (or OOXML if needed)
```

### Rules (mirror Slidev hybrid)

1. **Per-element, not per-slide, fallback.** Only the hard element becomes an image; the rest stays editable.
2. **Whole-slide image fallback** only when the slide is mostly untranslatable (log the reason).
3. **Charts:**  
   - Simple bar/line/pie/doughnut with clean series → `slide.addChart` (native, editable data).  
   - Overlapping/annotated/custom (ECharts, mixed dual-axis with callouts) → **high-DPI PNG/SVG snapshot** of that chart region only.  
   - Never place a native chart and a table in the same absolute band without reserved regions.
4. **Tables:** always native `addTable` with explicit `colW[]` + `rowH[]` from measured HTML `<table>`.
5. **Icons:** never rely on SVG in PPTX. Convert SVG → **PNG @ 2–3× DPR** (or font-icon → rasterize). Optional: simple geometric icons → `addShape`.
6. **Text:** map CSS `font-size/line-height/font-weight/color/align` → PptxGenJS text props; set `fit: 'shrink'` + generous `h` to fight overflow; pre-shrink long strings in IR if measured height > box height.
7. **Layout:** absolute positioning in inches/percent. **Do not** use PPTX tables as a layout grid for the whole slide (that's what breaks when charts mix in).
8. **Masters:** use `defineSlideMaster` for brand chrome (logo, page number, footer); leave body region free for measured content.

### Why not pure OOXML / pure rasterize?
- Pure OOXML from arbitrary HTML = rewrite a browser layout engine (years).
- Pure rasterize = fails the "editable" requirement.
- Hybrid is what Slidev shipped after the same problem statement.

---

## 4. Concrete Technical Fixes (map to our 4 bugs)

### 4.1 Charts overlap tables

**Root causes**
- Both placed with overlapping absolute `x,y,w,h` (HTML flex/grid reflowed; PPTX does not).
- `addChart` default legend/title inflate visual bounds beyond declared `w,h`.
- Auto-paged tables start at a y that still collides with the chart.

**Fixes**
1. **Reserved-region layout in IR:** for each slide, compute content bands (title / chart / table / notes). Enforce non-overlap in the IR compiler (assert `rect.intersects`).
2. **Explicit chart plot padding:** use `layout: { x, y, w, h }` (0–1 within chart) so the plot fills the intended box; set `legendPos`, `showTitle: false` if title is already a text box.
3. **Stack order:** emit table first, chart second only if intentional overlay; otherwise sort by `y` and give each its own band.
4. **Table auto-page:** `autoPage: true`, `newSlideStartY` set *below* chrome; never auto-page a table that shares a slide with a chart that must stay — instead **truncate table + "continued" slide** with the chart repeated or omitted by policy.
5. **Visual QA gate:** after export, render PPTX→PNG (LibreOffice/PowerPoint automation) and IoU-compare against HTML screenshot; fail CI if chart/table bounding boxes overlap.

**PptxGenJS notes [VERIFIED]**  
- Chart `x,y,w,h` in inches or `'50%'` percent strings.  
- Combo charts need `catAxes`/`valAxes` pairs; hide secondary cat axis with `catAxisHidden: true`.

### 4.2 Table layout breaks

**Root causes**
- Relying on content-sized rows (`omit rowH`) while HTML had fixed heights.
- Column widths from CSS `width: %` not converted to absolute `colW[]`.
- Cell padding/margin units mixed (CSS px vs PPT points).
- Text wraps more in PowerPoint than Chromium (Slidev documents this).

**Fixes**
1. From measured HTML table:  
   `colW[i] = cellWidthPx / htmlWidthPx * tableW_inches`  
   `rowH[j] = rowHeightPx / htmlHeightPx * tableH_inches` **or** measured px→inches directly.
2. Always pass **`colW` as an array** (never rely on auto-fit).  
3. Use `rowH` array for multi-row tables; use `h` only when rows should divide evenly.
4. Cell-level options: `{ text, options: { fill, color, bold, align, valign, margin, colspan, rowspan } }`.  
   Map CSS padding → `margin` (points). Docs: *"ProTip: use the same value from CSS padding"* — but **convert px→pt** (`pt = px * 0.75` at 96dpi).
5. For dense tables that still overflow: enable `autoPage: true`, tune `autoPageCharWeight` / `autoPageLineWeight` (docs admit this is heuristic). Prefer shrinking font 0.5–1pt in IR before paging.
6. Borderless modern tables: `border: { type: 'none' }` then draw separators as lines (more control).

### 4.3 Icons / SVGs disappear

**Root cause [VERIFIED]**  
PptxGenJS Images docs: *"SVG images: supported in the newest version of desktop PowerPoint or Microsoft 365/Office365"* — older PowerPoint, LibreOffice, Google Slides import often drop or blank SVG. Font icons (Font Awesome/Ligatures) also break if the font isn't installed.

**Fixes (priority order)**
1. **Always rasterize SVG → PNG** at 2–3× the layout box (e.g. 0.3" icon → 128–256px). Pre-encode base64 (`data: "image/png;base64,..."`) — docs recommend this for performance.
2. Icon pipeline: SVG sprite / Lucide / Heroicons → `sharp` / `resvg` / browser canvas → PNG buffer → base64.
3. Font icons: render glyph to canvas with the icon font loaded in Chromium, then export PNG. Do **not** emit private-use Unicode codepoints as text.
4. Simple monochrome icons may map to `addShape(pres.ShapeType.*)` when a matching preset exists (~200 shapes).
5. Optional dual-emit: PNG for compatibility + set `altText` for accessibility.

### 4.4 Text overflow

**Root causes**
- Browser line-breaking ≠ PowerPoint line-breaking (Slidev documents this explicitly).
- No autofit; box height from HTML can be too small after font substitution.
- Missing `wrap`, wrong `inset`/`margin`, CJK line-breaking differences.

**Fixes [VERIFIED PptxGenJS API]**
1. `fit: 'shrink'` on body text (also `fit: 'resize'` | `none`); legacy `autoFit: true` ("Fit to Shape").
2. `wrap: true`, `valign: 'top'`, `isTextBox: true` for true text boxes.
3. Set `h` with **10–15% slack** over measured HTML height; let shrink/fit absorb wrap differences.
4. `margin`/`inset` from CSS padding (px→inches for `inset`, px→pt for `margin`).
5. `lineSpacingMultiple` or `lineSpacing` from CSS `line-height`.
6. `paraSpaceBefore` / `paraSpaceAfter` from CSS margins between `<p>`.
7. CJK: set `lang: 'zh-CN'` and a font that exists on target machines (e.g. `Microsoft YaHei` / `Noto Sans SC`); list fonts used in export report (Slidev prints referenced font families).
8. Pre-pass in browser: if `scrollHeight > clientHeight`, reduce `fontSize` in IR until it fits (mimic PowerPoint shrink) — more predictable than PPT autofit alone.
9. Prefer `\n` / `breakLine: true` for intentional breaks; `softBreakBefore` for shift-enter.

### 4.5 Coordinate mapping HTML → PPTX

**Units [VERIFIED via Microsoft OOXML + PptxGenJS]**
| Unit | Value |
|---|---|
| 1 inch | 914,400 EMU |
| 1 point | 12,700 EMU |
| 1 px (96dpi) | 9,525 EMU ≈ 0.0104167 in |
| 16:9 slide | **12,192,000 × 6,858,000 EMU** = **13.333in × 7.5in** |
| 4:3 default sample | `cx="9144000" cy="6858000"` (10×7.5 in) |

PptxGenJS accepts **inches** (number) or **percent** (`'50%'`) for `x,y,w,h` — prefer inches from:
```
inches = px / htmlSlideWidthPx * 13.333
```
Keep one source of truth: measure at a fixed viewport (e.g. 1280×720 or 1920×1080 CSS px) matching 16:9.

**Masters / placeholders**
- PresentationML: `presentation → sldMaster → sldLayout → sld` + theme (VERIFIED structure).
- Use masters for repeated chrome only; freeform report content should be **absolute shapes on the slide**, not layout placeholders (placeholders fight absolute positioning).
- python-pptx: `prs.slide_layouts[6]` blank is the usual base for generated decks.

**Other pitfalls**
- Z-order = add order in PptxGenJS; emit background → chrome → content → overlays.
- Charts/tables are `graphicFrame`-like; they don't clip like CSS overflow.
- Never mix `%` and inch coordinates without converting against slide size.
- Validate OOXML: "Needs Repair" = schema violation (PptxGenJS troubleshooting guide) — isolate slide/feature when it happens.

---

## 5. PptxGenJS Best Practices (complex layouts)

| Concern | Recommendation | Source |
|---|---|---|
| Layout | Absolute `x,y,w,h` (in or %); one IR band per element; assert no overlap | API PositionProps |
| Charts | `addChart(pres.ChartType.*, data, opts)` for standard types; `layout` to fill plot area; `showLegend`/`showTitle` explicit | api-charts |
| Fancy charts | PNG snapshot of chart region | hybrid rule |
| Tables | `addTable(rows, { colW[], rowH[], margin, valign })` | api-tables |
| Table paging | `autoPage`, `autoPageRepeatHeader`, `newSlideStartY`, tune char/line weights | api-tables |
| Images | PNG/JPG; SVG only new Office — **rasterize**; pre-encode base64 | api-images |
| Text fit | `fit: 'shrink'`, `wrap`, `isTextBox`, `margin`/`inset` | api-text |
| Icons | PNG 2–3× or shapes; no font-icon codepoints | images + practice |
| Masters | `defineSlideMaster` for brand; body free | usage docs |
| Performance | Pre-encode images; avoid huge base64 charts | api-images |
| Debug | Slide-by-slide binary search on "Needs Repair" | needs-repair-errors |

**addChart vs shapes:**  
- Data-driven, user will edit numbers → native chart.  
- One-off infographic / heavily annotated → shapes or image.  
- Combo: `slide.addChart([{ type, data, options }, ...], { catAxes, valAxes, secondaryValAxis })`.

---

## 6. Open-Source Landscape

| Project | Role | Notes |
|---|---|---|
| **PptxGenJS** | JS OOXML generator | Primary tool for us. HTML feature is table-only. MIT. |
| **python-pptx** | Python OOXML | Placeholders, charts, tables; `Inches`/`Pt`/EMU. Good for backend pipelines. |
| **officegen** | Node OOXML | PptxGenJS borrowed some shape/XML definitions from it (credited in README). |
| **Slidev** | Markdown deck | **Best open reference for hybrid `pptx-editable` measurement→shapes.** |
| **Marp / Marpit** | Markdown deck | Image-faithful PDF/PPTX via Chromium. |
| **reveal.js** | HTML deck | PDF print export only. |
| **html2pptx (tableToSlides)** | PptxGenJS built-in | HTML table → slides only. |
| **html2pptx (various npm/PyPI)** | Ad hoc converters | Usually thin wrappers over screenshot or PptxGenJS; quality varies; none replace a measured IR. |
| **LibreOffice / unoconv** | Conversion | HTML→PPT fidelity poor; useful for PPTX→PNG QA. |

---

## 7. Action Plan (prioritized)

### P0 — stop the bleeding
1. **SVG/icon rasterization pipeline** (2–3× PNG, base64). Biggest visible win.
2. **IR non-overlap assertion** for chart/table bands.
3. **Table `colW[]` + `rowH[]` always explicit** from measured HTML.
4. **Text `fit: 'shrink'` + height slack** on all body text.

### P1 — hybrid architecture
5. Chromium measure pass → slide IR (role-tagged nodes via `data-pptx`).
6. Emit: native text/shapes/tables; native charts only for simple types; images for SVG/canvas/filters.
7. Per-element image fallback + whole-slide fallback with reason log.

### P2 — fidelity & QA
8. PPTX→PNG visual diff vs HTML screenshot (LibreOffice headless or PowerPoint COM).
9. Font inventory + export report of referenced families.
10. Chart policy: simple→`addChart`; complex→high-DPI image of that region.
11. Optional: template masters for brand chrome.

### P3 — polish
12. CJK line-break tuning; `lang` + safe font stack.
13. Notes pages (`addNotes`) from HTML speaker notes.
14. 16:9 constants centralized: `SLIDE_W_IN = 13.333`, `SLIDE_H_IN = 7.5`, `EMU_PER_IN = 914400`.

---

## 8. Source URLs

### Primary (opened in this research)
| Topic | URL |
|---|---|
| Slidev exporting (pptx vs pptx-editable hybrid) | https://sli.dev/guide/exporting.html |
| Marp intro (export PDF/PPTX/HTML) | https://marp.app/docs/introduction/whats-marp |
| reveal.js PDF export | https://revealjs.com/pdf-export/ |
| PptxGenJS intro + HTML tableToSlides | https://gitbrent.github.io/PptxGenJS/docs/introduction/ |
| PptxGenJS HTML-to-PPTX feature | https://gitbrent.github.io/PptxGenJS/html2pptx/ |
| PptxGenJS Charts API | https://gitbrent.github.io/PptxGenJS/docs/api-charts/ |
| PptxGenJS Tables API (rowH/colW/autoPage) | https://gitbrent.github.io/PptxGenJS/docs/api-tables/ |
| PptxGenJS Images API (SVG caveat) | https://gitbrent.github.io/PptxGenJS/docs/api-images/ |
| PptxGenJS Text API (fit/autoFit/wrap) | https://gitbrent.github.io/PptxGenJS/docs/api-text/ |
| PptxGenJS Shapes API | https://gitbrent.github.io/PptxGenJS/docs/api-shapes/ |
| PptxGenJS Needs Repair troubleshooting | https://gitbrent.github.io/PptxGenJS/docs/needs-repair-errors/ |
| python-pptx home / feature list | https://python-pptx.readthedocs.io/en/latest/ |
| python-pptx shapes (EMUs, shape types) | https://python-pptx.readthedocs.io/en/latest/user/understanding-shapes.html |
| python-pptx quickstart (tables/charts) | https://python-pptx.readthedocs.io/en/latest/user/quickstart.html |
| Microsoft PresentationML structure (sldSz EMU) | https://learn.microsoft.com/en-us/office/open-xml/presentation/structure-of-a-presentationml-document |
| Open XML SDK PresentationPart | https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.packaging.presentationpart?view=openxml-3.0.1 |
| think-cell knowledge base | https://think-cell.com/en/resources/kb |
| think-cell developer blog | https://think-cell.com/en/career/devblog |

### Secondary / search-discovered (not fully opened)
| Topic | URL |
|---|---|
| PptxGenJS GitHub | https://github.com/gitbrent/PptxGenJS |
| Beautiful.ai fork of PptxGenJS | https://github.com/beautifulai/PptxGenJS |
| officegen | https://github.com/Ziv-Barber/officegen |
| decktape (reveal.js→PDF) | https://github.com/astefanutti/decktape |
| ISO/IEC 29500 (OOXML) | https://www.iso.org/standard/71691.html |

---

## 9. Direct Answer to Our Failure Modes

| Symptom | Industry diagnosis | Fix |
|---|---|---|
| Charts overlap tables | Absolute boxes without reserved bands; chart chrome (legend/title) expands | IR band allocator; `layout` on charts; no shared band |
| Table layout breaks | Auto column widths + PPT wrap ≠ CSS wrap | Measured `colW[]`/`rowH[]`; px→pt margins; autoPage weights |
| Icons/SVG disappear | SVG only in newest Office; font icons need fonts | Rasterize SVG→PNG 2–3×; no PUA glyphs |
| Text overflow | Font metric mismatch browser vs PPT | `fit: 'shrink'`, height slack, pre-shrink in measure pass, font inventory |
| Low overall fidelity | Trying to map all CSS to OOXML | Hybrid: native for text/table/simple chart; picture for the rest; slide-image fallback |

**Bottom line:** Adopt **Slidev-style hybrid export** (measure in Chromium → rebuild as shapes; picture only unsupported elements) on top of **PptxGenJS**, with a strict **IR non-overlap + measured table geometry + SVG rasterization** pipeline. That is the industry-proven path — not a pure HTML parser, and not full-slide screenshots (unless the user opts into "presentation-only" mode).

---

## 10. Gap Analysis vs `top-ppt-html` Skill (T6 整改对照)

The current skill (`topmind-presentation`, formerly `top-ppt-html`) already implements most of the industry hybrid pattern. Mapping:

| Research recommendation | Skill status | Evidence | Remaining work |
|---|---|---|---|
| Hybrid per-element (not full rasterize) | **Done** | Dual channel: native `addChart` + shape renderers; zero-image default (`pictures=0`) | — |
| Native charts for simple types | **Done** | 16 native types → chart part + embedded Excel; `MODEL_CHART_COUNT` gate | — |
| Complex charts as image/shape | **Done** | 20 shape-channel types + 6 infographics; `fidelityMap` high/medium/low | Optional: low-fidelity types → high-DPI PNG (industry Slidev path) when user prioritizes visual over editability |
| Tables: measured `colW[]`/`rowH[]` | **Done** | `addTable` with `colW`/`rowH`/`fitRowH`; `TABLE_DENSITY`/`TABLE_SEMANTIC_TYPE` | Keep enforcing `autoPage: false` + explicit geometry (already in `build_pptx.js`) |
| Icons: do not trust SVG in PPTX | **Done (policy)** | `icons.md`: “内联 SVG 不跨通道；PPTX 用 accent 小方块路标” | Optional enhancement: SVG→PNG 2–3× when user wants HTML-parity icons (breaks `pictures=0` purity — keep opt-in) |
| Chart/table non-overlap bands | **Mostly done** | F19 geometry rules; `severe-overlap` safety net; `CONTAINER_OVERFLOW` | Harden: IR-level `rect.intersects` assert before emit (currently validated post-hoc in `validate_pptx.py`) |
| Text overflow / fit | **Done** | `fontShrink` floor; `CONTAINER_OVERFLOW` / `TEXT_OVERFLOW_ESTIMATE`; venue `modeTypeScale` | — |
| Font inventory in export report | **Partial** | Fonts are semantic tokens from styles | Optional: emit referenced font family list (Slidev practice) for handoff |
| PPTX→PNG visual QA | **Partial** | `render_compare.py` + `--deep` | Keep as optional deep mode; not default |
| Template masters / brand chrome | **Done** | `defineSlideMaster` path in export doc | — |

**T6 conclusion:** Architecture is industry-aligned (better than generic HTML→PPTX converters: model-first IR, native charts, shape infographics, hard gates). Remaining gaps are **optional fidelity upgrades** (icon PNG path, low-chart PNG fallback, pre-emit overlap assert, font inventory) — not architectural rewrites. Prefer keeping the zero-image / fully-editable default and adding those as explicit opt-ins.
