/**
 * topmind-presentation · 页面装饰开关（M12）
 *
 * 默认不显示标题上方的小引导标题（eyebrow），也不显示页脚小字（footnote / note 注释行），
 * 只保留一个克制的页码。腾出的高度交给求解器分给正文。三个开关都写在模型顶层：
 *   showEyebrow   默认 false：true 时恢复标题上方的小引导标题
 *   showFootnotes 默认 false：true 时恢复页脚注释行（关闭时注释文字移入演讲者备注，不丢字）
 *   pageNumber    默认 true ：false 时连页码也不显示
 * 原文锁定（contentLocked，美化路由）时前两项默认 true：原稿上的字一个都不能少。
 * render_from_model.py 的 chrome_flags / strip_footnotes 与这里同口径。
 */
'use strict';
const fs = require('fs');

function chromeFlags(model) {
  const m = model || {};
  const locked = !!m.contentLocked;
  const pick = (k) => (m[k] === true || m[k] === false) ? m[k] : locked;
  return { showEyebrow: pick('showEyebrow'), showFootnotes: pick('showFootnotes'), pageNumber: m.pageNumber !== false };
}

/* 在常量派生之前偷看一眼模型开关（build_pptx 先读 LC 再读模型） */
function peekModel(argv) {
  const a = argv || process.argv;
  let p = null;
  for (let i = 0; i < a.length; i++) {
    if (a[i].startsWith('--model=')) p = a[i].slice(8);
    else if (a[i] === '--model' && a[i + 1]) p = a[i + 1];
  }
  if (!p) return {};
  try { return JSON.parse(fs.readFileSync(p, 'utf-8')) || {}; } catch (e) { return {}; }
}

/* 眉标关闭：标题、分隔线、导语整体上移 d（= headTitleY − headEyebrowY），正文区顶部同步上移；
   页型里落在正文区的绝对 y 按「底边不动、顶边上移」线性拉伸，贴底的注释带（距底 < 0.5in）不动。 */
const Y_KEY = /(^y$|^y\d$|Y$|Y\d$|^top$|Top$)/;
const FULL_PAGE = { common: 1, layout: 1, cover: 1, closing: 1, chapter: 1, quote: 1 };
function applyChrome(LC, flags) {
  if (!LC || !LC.pageTypes || LC.__chrome) return LC;
  LC.__chrome = flags;
  if (flags.showEyebrow) return LC;
  const C = LC.pageTypes.common, L = LC.pageTypes.layout;
  const d = C.headTitleY - C.headEyebrowY;
  const T = L.contentTop, B = L.contentBottom, T2 = T - d;
  const top = C.headRuleY;
  const mapY = (y) => (y >= T ? B - (B - y) * (B - T2) / (B - T) : y - d);
  C.headTitleY -= d; C.headRuleY -= d; C.leadY -= d; C.bodyY -= d; C.bodyYWithLead -= d;
  L.contentTop = T2;
  const walk = (o) => {
    if (!o || typeof o !== 'object') return;
    for (const k of Object.keys(o)) {
      const v = o[k];
      if (typeof v === 'number' && Y_KEY.test(k) && v >= top && v < B - 0.5) o[k] = Math.round(mapY(v) * 1000) / 1000;
      else if (v && typeof v === 'object') walk(v);
    }
  };
  for (const k of Object.keys(LC.pageTypes)) if (!FULL_PAGE[k] && k[0] !== '$') walk(LC.pageTypes[k]);
  return LC;
}

/* 页脚注释关闭：Exhibit 页的来源行仍归图表（source 缺省时取 footnote）；带 [n] 引用的来源注释照常显示；其余注释文字移入演讲者备注 */
const CITE = /\[\d+\]/;
function stripFootnotes(model, flags) {
  if (!model || flags.showFootnotes || !Array.isArray(model.sections)) return model;
  const out = Object.assign({}, model);
  out.sections = model.sections.map((sec) => {
    if (!sec || typeof sec !== 'object' || (sec.footnote == null && sec.note == null)) return sec;
    const s = Object.assign({}, sec);
    if (s.exhibitNo && !s.source && s.footnote) { s.source = s.footnote; delete s.footnote; }
    /* 带参考资料引用 [n] 的注释是来源行（证据链的一环），照常显示；其余移入备注 */
    const moved = [];
    for (const k of ['footnote', 'note']) {
      const t = s[k];
      if (t == null || String(t).trim() === '' || CITE.test(String(t))) continue;
      moved.push(String(t)); delete s[k];
    }
    if (moved.length) s.speakerNotes = [s.speakerNotes, moved.join('\n')].filter(Boolean).join('\n');
    return s;
  });
  return out;
}

module.exports = { chromeFlags, peekModel, applyChrome, stripFootnotes };
