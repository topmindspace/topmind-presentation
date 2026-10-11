/**
 * TopPPT HTML · 图标栅格化（SVG → PNG data URI）
 * 依赖 sharp（MIMO_NODE_MODULES / 技能目录 npm install）。
 * build_pptx.js 在嵌入前调用；同一 name+color+size 结果缓存。
 * 图标图 objectName 统一 `icon:` 前缀，validate_pptx 单独计数（不进 pictures 内容图门禁）。
 */
'use strict';

const path = require('path');
const { iconSvg, pickIconName, ICONS, ORDER } = require('./icon_lib.js');

let sharpLib = null;
function loadSharp() {
  if (sharpLib !== null) return sharpLib;
  try {
    sharpLib = require('sharp');
  } catch (e) {
    try {
      const roots = [];
      if (process.env.MIMO_NODE_MODULES) roots.push(process.env.MIMO_NODE_MODULES);
      roots.push(path.join(__dirname, '..', 'node_modules'));
      roots.push(path.join(__dirname, 'node_modules'));
      for (const r of roots) {
        try {
          sharpLib = require(path.join(r, 'sharp'));
          break;
        } catch (_) { /* next */ }
      }
    } catch (_) { /* fallthrough */ }
  }
  if (!sharpLib) sharpLib = false;
  return sharpLib;
}

const _cache = new Map();

/**
 * 生成图标 PNG data URI。
 * @param {string} name 图标名（icon_lib.ICONS 键）
 * @param {string} color 描边色 #rrggbb
 * @param {number} px 输出边长（默认 64 = 2× 于 24pt@96dpi 的 0.18in 图标）
 * @returns {Promise<string|null>} data:image/png;base64,... 或 null（无 sharp 时回落）
 */
async function iconDataUri(name, color, px) {
  const sharp = loadSharp();
  if (!sharp) return null;
  const size = Math.max(16, Math.min(256, px || 64));
  const key = `${name}|${color}|${size}`;
  if (_cache.has(key)) return _cache.get(key);
  const svg = iconSvg(name, color);
  try {
    const buf = await sharp(Buffer.from(svg), { density: 300 })
      .resize(size, size)
      .png()
      .toBuffer();
    const uri = 'data:image/png;base64,' + buf.toString('base64');
    _cache.set(key, uri);
    return uri;
  } catch (e) {
    if (typeof console !== 'undefined') {
      console.warn(`iconDataUri(${name}) 栅格化失败: ${e.message}`);
    }
    _cache.set(key, null);
    return null;
  }
}

/** 同步取缓存（须先 await 预热）；无缓存返回 null */
function iconDataUriCached(name, color, px) {
  return _cache.get(`${name}|${color}|${px || 64}`) || null;
}

/** 预热常用图标（卡片头 accent 色） */
async function prewarm(color, px) {
  const out = {};
  for (const n of ORDER) {
    out[n] = await iconDataUri(n, color, px);
  }
  return out;
}

function hasSharp() {
  return !!loadSharp();
}

module.exports = { iconDataUri, iconDataUriCached, prewarm, hasSharp, pickIconName, ICONS, ORDER };
