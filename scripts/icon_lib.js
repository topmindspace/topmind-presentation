/**
 * TopPPT HTML · 语义图标库（48 · 24×24 · stroke 1.8 圆角线帽 · currentColor）
 * 单源：assets/icons/<name>.svg + assets/icons/index.json（关键词映射 + 默认表）。
 * 由 scripts/make_icon_pack.py 生成。HTML 内联 / build_pptx.js PNG 真导出共用。
 * 图标图 objectName 统一 `icon:` 前缀，validate_pptx 单独计数，不进 pictures 内容图门禁。
 */
'use strict';

const fs = require('fs');
const path = require('path');

const ICON_DIR = path.join(__dirname, '..', 'assets', 'icons');
const SVG_OPEN = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">';

let ICONS = {};
let ORDER = [];
let INDEX = { defaults: [], icons: {} };

function _load() {
  try {
    INDEX = JSON.parse(fs.readFileSync(path.join(ICON_DIR, 'index.json'), 'utf-8'));
  } catch (e) {
    INDEX = { defaults: [], icons: {} };
  }
  const names = Object.keys(INDEX.icons || {});
  for (const name of names) {
    try {
      ICONS[name] = fs.readFileSync(path.join(ICON_DIR, `${name}.svg`), 'utf-8').trim();
    } catch (e) { /* 缺文件则跳过，validate 会 WARN */ }
  }
  ORDER = Object.keys(ICONS);
  if (!ORDER.length) {
    // 极端回落：包不可读时给一个空壳，避免调用方崩溃
    ICONS = { '信息': SVG_OPEN + '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 7.5h.01"/></svg>' };
    ORDER = ['信息'];
  }
}
_load();

/** 默认图标表（index.json defaults；选不出语义图标时轮换） */
function defaultNames() {
  const ds = (INDEX.defaults || []).filter((n) => ICONS[n]);
  return ds.length ? ds : ORDER;
}

/**
 * 按标题语义挑图标名：关键词命中 → 默认表轮换（不盲目轮换全量 48）。
 * 与 render_from_model.pick_icon_name 同策略（同读 index.json）。
 */
function pickIconName(title, idx) {
  const t = String(title || '');
  const meta = INDEX.icons || {};
  for (const name of ORDER) {
    const kws = (meta[name] && meta[name].keywords) || [name];
    for (const kw of kws) {
      if (kw && t.includes(kw)) return name;
    }
  }
  const ds = defaultNames();
  return ds[(idx || 0) % ds.length];
}

/** 渲染为带指定描边色的 SVG 字符串（currentColor → 目标色） */
function iconSvg(name, color) {
  const raw = ICONS[name] || ICONS[defaultNames()[0]] || ICONS[ORDER[0]];
  const c = color || '#1a56a8';
  return raw.replace('stroke="currentColor"', `stroke="${c}"`);
}

/** 预渲染 PNG（512px）文件路径；无 sharp 环境下 PPTX 通道的可靠回落 */
function iconPngPath(name) {
  const n = ICONS[name] ? name : pickIconName(name, 0);
  const p = path.join(ICON_DIR, `${n}.png`);
  try {
    fs.accessSync(p, fs.constants.R_OK);
    return p;
  } catch (e) {
    return null;
  }
}

module.exports = { ICONS, ORDER, INDEX, pickIconName, iconSvg, iconPngPath, SVG_OPEN, defaultNames };
