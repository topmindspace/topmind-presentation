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
    cs.forEach(c => { if (SHARED.has(c.type || 'bar') && c.max == null) (g[c.unit || ''] = g[c.unit || ''] || []).push(c); });
    Object.values(g).forEach(grp => {
      if (grp.length < 2) return;
      const vals = [];
      grp.forEach(c => { (c.values || []).forEach(v => { if (typeof v === 'number') vals.push(Math.abs(v)); });
        (c.series || []).forEach(se => (se.values || []).forEach(v => { if (typeof v === 'number') vals.push(Math.abs(v)); })); });
      const m = niceCeil(vals.length ? Math.max(...vals) : 0);
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
