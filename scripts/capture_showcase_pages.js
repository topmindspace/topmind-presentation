#!/usr/bin/env node
/**
 * Capture every band section of showcase + golden examples into docs/showcase/*.
 * Usage: node scripts/capture_showcase_pages.js
 */
const path = require('path');
const fs = require('fs');
const { pathToFileURL } = require('url');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..');
const REPO = path.resolve(ROOT, '..');
const VIEW = { width: 1440, height: 810 }; // 16:9-ish at common laptop

const JOBS = [
  {
    html: path.join(ROOT, 'assets/examples/2026-09-26-topmind-tms-skills-showcase.html'),
    outDir: path.join(REPO, 'docs/showcase/topmind-showcase'),
    prefix: 'showcase',
    sections: ['cover', 'agenda', 's1', 's2', 's3', 's4', 's5', 's6', 's7', 's8', 's9', 's10', 's11', 's12', 'closing'],
    aliases: {
      cover: [
        path.join(ROOT, 'assets/showcase/showcase-cover.png'),
        path.join(REPO, 'docs/site-assets/showcase-cover.png'),
      ],
      s1: [
        path.join(ROOT, 'assets/showcase/showcase-positioning.png'),
      ],
      s3: [
        path.join(ROOT, 'assets/showcase/showcase-split.png'),
      ],
      s4: [
        path.join(ROOT, 'assets/showcase/showcase-modes.png'),
        path.join(REPO, 'docs/site-assets/showcase-modes.png'),
      ],
      s5: [
        path.join(ROOT, 'assets/showcase/showcase-charts.png'),
      ],
      s6: [
        path.join(REPO, 'docs/site-assets/showcase-s6.png'),
      ],
      s4_alt: null,
      s8: [
        path.join(ROOT, 'assets/showcase/showcase-gates.png'),
        path.join(REPO, 'docs/site-assets/showcase-gates.png'),
      ],
      s11: [
        path.join(ROOT, 'assets/showcase/showcase-toolbar.png'),
      ],
    },
  },
  {
    html: path.join(ROOT, 'assets/examples/2026-09-09-presentation-business-blue.html'),
    outDir: path.join(REPO, 'docs/showcase/presentation-business-blue'),
    prefix: 'bizblue',
    sections: ['cover', 'agenda', 's1', 's3', 'closing'],
    styleCover: path.join(ROOT, 'assets/showcase/style-business-blue-cover.png'),
  },
  {
    html: path.join(ROOT, 'assets/examples/2026-09-09-research-mckinsey.html'),
    outDir: path.join(REPO, 'docs/showcase/research-mckinsey'),
    prefix: 'mckinsey',
    sections: ['cover', 'agenda', 's1', 's2', 'closing'],
    // also try a donut section if present
    extraFind: { donut: 'svg[data-chart="donut"]' },
    styleCover: path.join(ROOT, 'assets/showcase/style-mckinsey-cover.png'),
  },
  {
    html: path.join(ROOT, 'assets/examples/2026-09-09-architecture-graphite-dark.html'),
    outDir: path.join(REPO, 'docs/showcase/architecture-graphite-dark'),
    prefix: 'graphite',
    sections: ['cover', 'agenda', 's1', 'closing'],
    styleCover: path.join(ROOT, 'assets/showcase/style-graphite-cover.png'),
  },
];

async function captureSection(page, sectionId) {
  const el = await page.$(`section#${sectionId}`);
  if (!el) return null;
  await el.scrollIntoViewIfNeeded();
  await page.waitForTimeout(120);
  return el.screenshot({ type: 'png' });
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: VIEW,
    deviceScaleFactor: 1.25,
  });
  const page = await ctx.newPage();

  for (const job of JOBS) {
    fs.mkdirSync(job.outDir, { recursive: true });
    const url = pathToFileURL(job.html).href;
    console.log('open', path.basename(job.html));
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    // hide sticky bar for cleaner section shots when present
    await page.addStyleTag({ content: '.bar{opacity:0!important;pointer-events:none!important}' });
    await page.waitForTimeout(400);

    for (const sid of job.sections) {
      const buf = await captureSection(page, sid);
      if (!buf) {
        console.warn('  MISSING section', sid);
        continue;
      }
      const out = path.join(job.outDir, `${job.prefix}-${sid}.png`);
      fs.writeFileSync(out, buf);
      console.log('  wrote', path.relative(REPO, out));
      if (job.aliases && job.aliases[sid]) {
        for (const alias of job.aliases[sid]) {
          fs.mkdirSync(path.dirname(alias), { recursive: true });
          fs.copyFileSync(out, alias);
          console.log('  alias', path.relative(REPO, alias));
        }
      }
      if (sid === 'cover' && job.styleCover) {
        fs.copyFileSync(out, job.styleCover);
        console.log('  styleCover', path.relative(REPO, job.styleCover));
      }
    }

    if (job.extraFind) {
      for (const [name, sel] of Object.entries(job.extraFind)) {
        const el = await page.$(sel);
        if (!el) { console.warn('  MISSING', name, sel); continue; }
        // nearest section
        const sec = await el.evaluateHandle(node => node.closest('section'));
        if (!sec) continue;
        await sec.asElement().scrollIntoViewIfNeeded();
        await page.waitForTimeout(100);
        const buf = await sec.asElement().screenshot({ type: 'png' });
        const out = path.join(job.outDir, `${job.prefix}-${name}.png`);
        fs.writeFileSync(out, buf);
        console.log('  wrote', path.relative(REPO, out));
      }
    }
  }

  await browser.close();
  console.log('done');
}

run().catch(err => { console.error(err); process.exit(1); });
