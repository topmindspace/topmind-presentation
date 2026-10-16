#!/usr/bin/env node
/* topmind-presentation · HTML 侧版面采样（供 check_fidelity.py 与 PPTX 逐页比对）
 * 用法：node scripts/fidelity_html.js 报告.html 输出.json [--shots=目录]
 * 输出：每个内容页（main section）的文字块：文本、相对页宽的位置 / 尺寸、字号（相对页宽）、颜色、行数、字体族。
 * 浏览器：TOP_PPT_BROWSER_PATH → /usr/bin/google-chrome → Playwright 自带 chromium。 */
'use strict';
const fs = require('fs');
const path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) {
  console.error('fidelity_html: 缺少 playwright（npm ci 安装 devDependencies 后重试）'); process.exit(2);
}
(async () => {
  const [src, out] = process.argv.slice(2);
  const shots = (process.argv.find((a) => a.startsWith('--shots=')) || '').slice(8);
  if (!src || !out) { console.error('用法：node scripts/fidelity_html.js 报告.html 输出.json [--shots=目录]'); process.exit(2); }
  const cands = [process.env.TOP_PPT_BROWSER_PATH, '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'];
  const exe = cands.find((p) => p && fs.existsSync(p));
  const browser = await chromium.launch(exe ? { executablePath: exe } : {});
  const page = await browser.newPage({ viewport: { width: 1440, height: 810 } });
  await page.goto('file://' + path.resolve(src));
  await page.waitForTimeout(300);
  await page.addStyleTag({ content: '.rv,[data-anim]{opacity:1!important;transform:none!important;transition:none!important}' +
    '.topbar,.toolsbar,.dots,.pnav,header.top{display:none!important}' });
  await page.evaluate(() => document.querySelectorAll('.chart').forEach((c) => c.classList.add('in')));
  const data = await page.evaluate(() => {
    const INLINE = new Set(['SPAN', 'B', 'STRONG', 'EM', 'I', 'SMALL', 'SUP', 'SUB', 'A', 'CODE', 'BR', 'MARK', 'svg', 'SVG', 'IMG', 'KBD', 'ABBR', 'TIME']);
    const secs = [...document.querySelectorAll('main section, section.band')];
    return secs.map((s, si) => {
      const sb = s.getBoundingClientRect();
      const W = sb.width || 1;
      const items = [];
      s.querySelectorAll('*').forEach((el) => {
        if (el.closest('svg') || INLINE.has(el.tagName)) return;
        if (!(el.textContent || '').trim()) return;
        if ([...el.children].some((c) => !INLINE.has(c.tagName))) return;
        const r = el.getBoundingClientRect();
        if (!r.width || !r.height) return;
        const cs = getComputedStyle(el);
        if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0) return;
        const fs = parseFloat(cs.fontSize);
        const lh = parseFloat(cs.lineHeight) || fs * 1.4;
        const range = document.createRange(); range.selectNodeContents(el);
        const ys = new Set([...range.getClientRects()].filter((q) => q.width > 1).map((q) => Math.round(q.top)));
        items.push({ text: el.innerText.replace(/\s+/g, ' ').trim(), x: (r.left - sb.left) / W, y: (r.top - sb.top) / W,
          w: r.width / W, h: r.height / W, fs: fs / W, color: cs.color, weight: +cs.fontWeight || 400,
          lines: Math.max(1, ys.size || Math.round(r.height / lh)), font: cs.fontFamily });
      });
      // SVG 图表里的文字（坐标轴 / 数据标签 / 节点名）也是正文，单独采样
      s.querySelectorAll('svg text').forEach((el) => {
        const r = el.getBoundingClientRect();
        const t = (el.textContent || '').trim();
        if (!t || !r.width) return;
        const cs = getComputedStyle(el);
        items.push({ text: t, x: (r.left - sb.left) / W, y: (r.top - sb.top) / W, w: r.width / W, h: r.height / W,
          fs: (parseFloat(cs.fontSize) * (el.getScreenCTM() ? el.getScreenCTM().a : 1)) / W,
          color: cs.fill && cs.fill.startsWith('rgb') ? cs.fill : cs.color, weight: +cs.fontWeight || 400, lines: 1,
          font: cs.fontFamily, svg: true });
      });
      return { index: si + 1, id: s.id || '', w: W, h: sb.height, items };
    });
  });
  if (shots) {
    fs.mkdirSync(shots, { recursive: true });
    const secs = await page.$$('main section, section.band');
    for (let i = 0; i < secs.length; i++) await secs[i].screenshot({ path: path.join(shots, `s-${String(i + 1).padStart(2, '0')}.png`) });
  }
  fs.writeFileSync(out, JSON.stringify(data));
  await browser.close();
  console.log(`fidelity_html: ${data.length} 页 → ${out}`);
})().catch((e) => { console.error('fidelity_html: ' + e.message); process.exit(1); });
