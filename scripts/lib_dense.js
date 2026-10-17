/* M13 高密度复合版式 / 简单版式 · 双端同规则（与 scripts/lib_dense.py 逐条一致） */
'use strict';
const DASH_MAX_CHARTS = 4, DASH_MAX_KM = 4, DASH_MAX_PTS = 3, MAG_MAX_METRICS = 2, MAG_MAX_PTS = 3;
const SHARED = new Set(['bar', 'hbar', 'line', 'stack', 'area', 'lollipop', 'dotplot']);
const ORD = '①②③④';
function niceCeil(v) {
  if (!v || v <= 0) return 0;
  const e = Math.pow(10, Math.floor(Math.log10(v)));
  for (const m of [1, 2, 2.5, 5, 10]) if (m * e >= v - 1e-9) return Math.round(m * e * 1e6) / 1e6;
  return 10 * e;
}
function dashCharts(sec) {
  const cs = (sec.charts || []).filter(c => c && typeof c === 'object' && c.labels).slice(0, DASH_MAX_CHARTS).map(c => Object.assign({}, c));
  if (sec.sharedScale !== false) {
    const g = {};
    cs.forEach(c => { if (SHARED.has(c.type || 'bar') && c.max == null) { const k = (c.unit || '') + '\u0001' + (c.type || 'bar'); (g[k] = g[k] || []).push(c); } });
    Object.entries(g).forEach(([key, grp]) => {
      if (grp.length < 2) return;
      const per = grp.map(c => { const vs = [];
        (c.values || []).forEach(v => { if (typeof v === 'number') vs.push(Math.abs(v)); });
        (c.series || []).forEach(se => (se.values || []).forEach(v => { if (typeof v === 'number') vs.push(Math.abs(v)); }));
        return vs.length ? Math.max(...vs) : 0; });
      if (!key.split('\u0001')[0] && (Math.min(...per) <= 0 || Math.max(...per) / Math.min(...per) > 5)) return;   // 无单位且量级差 >5 倍：不共享
      const m = niceCeil(Math.max(...per));
      if (m) grp.forEach(c => { c.max = m; });
    });
  }
  cs.forEach((c, k) => { const cap = String(c.cap || ''); c.cap = sec.numbered !== false ? (ORD[k] + ' ' + cap).trim() : cap; });
  return cs;
}
function dashLegend(cs) {
  const names = cs.filter(c => c.series).map(c => c.series.map(s => s.name || '').join('\u0001'));
  if (names.length >= 2 && new Set(names).size === 1 && names[0].split('\u0001').every(Boolean)) return names[0].split('\u0001');
  return [];
}
function kv3(m) {
  if (Array.isArray(m)) return [String(m[0] == null ? '' : m[0]), String(m[1] == null ? '' : m[1]), m[2] ? String(m[2]) : ''];
  if (m && typeof m === 'object') return [String(m.v || m.value || ''), String(m.k || m.label || ''), String(m.icon || '')];
  return [String(m), '', ''];
}
function pt3(p) {
  if (Array.isArray(p)) return [String(p[0] == null ? '' : p[0]), String(p[1] == null ? '' : p[1]), p[2] ? String(p[2]) : ''];
  if (p && typeof p === 'object') return [String(p.k || p.t || ''), String(p.v || p.d || ''), String(p.icon || '')];
  return [String(p), '', ''];
}
const KINDS = ['icon', 'text', 'statement', 'number', 'chart', 'iconText', 'twoText'];
function focusKind(sec) {
  if (KINDS.includes(sec.focus)) return sec.focus;
  if (sec.chart) return 'chart';
  if (sec.number) return 'number';
  if (sec.texts && sec.texts.length >= 2) return 'twoText';
  if (sec.icon && sec.text) return 'iconText';
  if (sec.icon) return 'icon';
  if (sec.statement) return 'statement';
  return 'text';
}
function focusVariant(sec) {
  if (['left', 'center', 'split'].includes(sec.variant)) return sec.variant;
  return { number: 'left', statement: 'left', text: 'left', iconText: 'split', twoText: 'split', icon: 'center', chart: 'center' }[focusKind(sec)] || 'left';
}
function overflow(sec) {
  const out = [];
  if (sec.type === 'dashboard') {
    (sec.charts || []).slice(DASH_MAX_CHARTS).forEach(c => out.push(['chart', c.cap || '']));
    (sec.keyMetrics || []).slice(DASH_MAX_KM).forEach(m => out.push(['km', kv3(m)[0] + ' ' + kv3(m)[1]]));
    (sec.points || []).slice(DASH_MAX_PTS).forEach(p => out.push(['pt', pt3(p)[0] + ' ' + pt3(p)[1]]));
  } else if (sec.type === 'magazine') {
    (sec.metrics || []).slice(MAG_MAX_METRICS).forEach(m => out.push(['km', kv3(m)[0] + ' ' + kv3(m)[1]]));
    (sec.points || []).slice(MAG_MAX_PTS).forEach(p => out.push(['pt', pt3(p)[0] + ' ' + pt3(p)[1]]));
  }
  return out;
}
module.exports = { DASH_MAX_CHARTS, DASH_MAX_KM, DASH_MAX_PTS, MAG_MAX_METRICS, MAG_MAX_PTS, niceCeil, dashCharts, dashLegend, kv3, pt3, focusKind, focusVariant, overflow };
/* M13 中文标题防孤字：按估算字宽模拟换行；两行时一律在「标点后 / 词边界」平衡断行（末行不留孤字）。
   数字与单位（18 个、3.2 天、+27%）、英文单词不拆开。返回带 \n 的标题；单行或已平衡时原样返回。 */
function balanceTitle(text, widthIn, fontPt, asciiRatio) {
  const t = String(text == null ? '' : text);
  if (t.includes('\n') || !t) return t;
  const ar = asciiRatio || 0.55, usable = Math.max(24, widthIn * 72 - 8);
  const cw = ch => (/[\x00-\xff]/.test(ch) ? fontPt * ar : fontPt);
  const total = [...t].reduce((a, c) => a + cw(c), 0);
  // 估算字宽比真实排版略窄（字距 / 字体回退），留 8% 余量：贴边的「刚好一行」实际常被挤出孤字
  if (total <= usable * 0.92) return t;
  // 不可拆分段：数字 + 可选空格 + 单位、连续拉丁字母
  const glue = new Array(t.length).fill(false);
  const re = /[+\-]?\d[\d.,]*\s*(?:%|倍|个|家|万|亿|元|年|月|天|人|次|份|项|款|座|台|pt|×)?|[A-Za-z][A-Za-z0-9\-]*/g;
  let m;
  while ((m = re.exec(t))) for (let i = m.index + 1; i < m.index + m[0].length; i++) glue[i] = true;
  const lines = Math.ceil(total / (usable * 0.92));
  if (lines > 2) return t;            // 三行以上交给字号阶梯，不硬断
  // 两行标题一律平衡断行：估算字宽与真实排版有误差，按估算「刚好不孤字」的标题实际仍可能把「18 个」拆开
  // 在 [35%, 65%] 宽度区间找断点：优先标点后，其次非粘连处，越接近一半越好
  let acc = 0, best = -1, bestScore = 1e9;
  for (let i = 1; i < t.length; i++) {
    acc += cw(t[i - 1]);
    const r = acc / total;
    if (r < 0.35 || r > 0.65 || glue[i] || acc > usable || total - acc > usable) continue;
    const punct = /[，、：；。,:;！？—）)]/.test(t[i - 1]);
    const score = Math.abs(r - 0.5) - (punct ? 0.2 : 0);
    if (score < bestScore) { bestScore = score; best = i; }
  }
  if (best < 0) return t;
  return t.slice(0, best).replace(/\s+$/, '') + '\n' + t.slice(best).replace(/^\s+/, '');
}
module.exports.balanceTitle = balanceTitle;
