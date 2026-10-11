/**
 * TopPPT HTML · 图标资产预生成（SVG → PNG base64）
 * 产出 scripts/icon-assets.json：{ "icons": { "<name>": { "<#color>": "data:image/png;base64,..." } } }
 * build_pptx.js 同步读取本文件；缺失时用 execFileSync 调本脚本补齐。
 * 由 sync_runtime.py / 首次 build 调用。依赖 sharp（MIMO_NODE_MODULES 或技能目录 node_modules）。
 *
 * 用法: node scripts/build_icon_assets.js [--out=scripts/icon-assets.json]
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { ICONS, ORDER, iconSvg } = require('./icon_lib.js');

function loadSharp() {
  const roots = [];
  if (process.env.MIMO_NODE_MODULES) roots.push(process.env.MIMO_NODE_MODULES);
  roots.push(path.join(__dirname, '..', 'node_modules'));
  roots.push(path.join(__dirname, 'node_modules'));
  for (const r of roots) {
    try { return require(path.join(r, 'sharp')); } catch (_) { /* next */ }
  }
  try { return require('sharp'); } catch (_) { return null; }
}

/** 需要预生成的描边色：9 套风格 light/dark 的 accent + 一个兜底深灰 */
function collectColors() {
  const colors = new Set(['#333333']);
  const add = (a) => {
    if (typeof a !== 'string') return;
    let v = a.trim();
    if (!v) return;
    if (/^[0-9a-fA-F]{6}$/.test(v)) v = '#' + v;
    if (/^[0-9a-fA-F]{3}$/.test(v)) v = '#' + v;
    if (/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(v)) colors.add(v.toLowerCase());
  };
  try {
    const lc = JSON.parse(fs.readFileSync(path.join(__dirname, 'layout-constants.json'), 'utf-8'));
    const grab = (obj) => {
      if (!obj || typeof obj !== 'object') return;
      for (const k of Object.keys(obj)) {
        const v = obj[k];
        if (v && typeof v === 'object') {
          add(v.accent);
          add(v.accentText || v['accent-text']);
        }
      }
    };
    grab(lc.styles);
    grab(lc.stylesDark);
  } catch (_) { /* 用兜底色 */ }
  return [...colors];
}

async function main() {
  const sharp = loadSharp();
  if (!sharp) {
    console.error('[build_icon_assets] FAIL: 未找到 sharp。请在技能目录 npm install，或设置 NODE_PATH/MIMO_NODE_MODULES。');
    process.exit(1);
  }
  const outArg = (process.argv.find(a => a.startsWith('--out=')) || '').split('=')[1];
  const outPath = outArg ? path.resolve(outArg) : path.join(__dirname, 'icon-assets.json');
  const colors = collectColors();
  const PX = 64;
  const icons = {};
  for (const name of ORDER) {
    icons[name] = {};
    for (const color of colors) {
      const svg = iconSvg(name, color);
      const buf = await sharp(Buffer.from(svg), { density: 300 })
        .resize(PX, PX)
        .png()
        .toBuffer();
      icons[name][color] = 'data:image/png;base64,' + buf.toString('base64');
    }
  }
  const payload = {
    version: 1,
    px: PX,
    generated: new Date().toISOString(),
    colors,
    icons,
  };
  fs.writeFileSync(outPath, JSON.stringify(payload), 'utf-8');
  const n = ORDER.length * colors.length;
  console.log(`[build_icon_assets] OK: ${ORDER.length} icons × ${colors.length} colors = ${n} PNGs → ${outPath}`);
}

main().catch((e) => {
  console.error('[build_icon_assets] FAIL:', e && e.message);
  process.exit(1);
});
