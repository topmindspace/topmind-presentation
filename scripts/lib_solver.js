/**
 * topmind-presentation · 布局求解器（M1）
 *
 * 纯函数、零依赖、确定性（同输入 → 同输出），HTML / PPTX 两端与测试共用。
 * 职责：
 *   1. rows()      —— 行/卡/泳道高度分配：先满足首选高度，空间富余时按 grow 上限拉伸，
 *                    仍有余量则给出整体垂直居中偏移（不再「挤在顶部、下半页空白」）。
 *   2. fitUp()     —— 字号求解：在阶梯内取「装得下的最大字号」，允许在稀疏时向上放大到 max。
 *   3. capacity()  —— 按页型估算内容量 / 版式承载力（>1 即超载）。
 *   4. splitModel()—— 超载页按条目拆成「续页」，标题加「（续）」，禁止静默截断。
 *   5. grid12()    —— 12 列网格列宽换算。
 * 几何单位：英寸（PPTX）；HTML 端按 px/in 比例换算即可。
 */
'use strict';

const LADDER = [32, 28, 24, 22, 20, 18, 17, 16, 15, 14, 13.5, 13, 12.5, 12, 11.5, 11, 10.5, 10, 9.5, 9, 8.5];

/** 行高分配。返回 { size, gap, offset, used }，offset 为整组垂直居中偏移。 */
function rows(avail, n, opts) {
  opts = opts || {};
  const k = Math.max(1, n | 0);
  const gap = opts.gap != null ? opts.gap : 0;
  const min = opts.min != null ? opts.min : 0.22;
  const pref = opts.pref != null ? opts.pref : min;
  const max = opts.max != null ? opts.max : pref * 1.8;
  const room = Math.max(0, avail - gap * (k - 1));
  const even = room / k;
  let size;
  if (even <= pref) size = Math.max(min, even);        // 紧张：压缩到 [min, pref]
  else size = Math.min(max, even);                     // 富余：拉伸到 max 为止
  const used = size * k + gap * (k - 1);
  const offset = opts.center === false ? 0 : Math.max(0, (avail - used) / 2);
  return { size: round(size), gap, offset: round(offset), used: round(used) };
}

/** 字号求解：needH(f) → 英寸；返回阶梯内装得下的最大字号（∈[min,max]），都装不下返回 min。 */
function fitUp(needH, avail, opts) {
  opts = opts || {};
  const max = opts.max != null ? opts.max : 16;
  const min = opts.min != null ? opts.min : 10;
  const lad = (opts.ladder || LADDER).filter(f => f <= max && f >= min);
  for (const f of lad) if (needH(f) <= avail) return f;
  return min;
}

/** 文本行数估算（CJK 计 1 字宽，拉丁计 0.55 字宽）——与 build_pptx estLines 同口径的近似。 */
function estLines(text, widthIn, pt) {
  const s = String(text == null ? '' : text);
  let units = 0;
  for (const ch of s) units += /[\u0000-\u00ff]/.test(ch) ? 0.55 : 1;
  const perLine = Math.max(1, Math.floor((widthIn * 72) / pt));
  return Math.max(1, Math.ceil(units / perLine));
}
function estTextH(text, widthIn, pt, lf) { return estLines(text, widthIn, pt) * pt * (lf || 1.45) / 72; }

/* ── 容量模型：每种列表型页型的「条目承载上限」，按模式区分 ── */
const CAP = {
  presentation: { points: 6, cards: 6, steps: 6, table: 8, comparison: 5, timeline: 6, bullet: 7, twocol: 6, threecol: 9, metrics: 6 },
  research:     { points: 8, cards: 8, steps: 7, table: 14, comparison: 7, timeline: 7, bullet: 10, twocol: 8, threecol: 12, metrics: 6 },
  architecture: { points: 7, cards: 6, steps: 7, table: 10, comparison: 5, timeline: 6, bullet: 8, twocol: 6, threecol: 9, metrics: 6 },
};
/** 按页型取「可拆的条目数组」的访问器：get(sec) → array；set(sec, arr) → 新 sec */
const LISTS = {
  points:     { get: s => s.points, set: (s, a) => Object.assign({}, s, { points: a }) },
  cards:      { get: s => s.cards, set: (s, a) => Object.assign({}, s, { cards: a }) },
  steps:      { get: s => s.steps, set: (s, a) => Object.assign({}, s, { steps: a, groups: undefined }) },
  timeline:   { get: s => s.phases, set: (s, a) => Object.assign({}, s, { phases: a }) },
  bullet:     { get: s => s.items, set: (s, a) => Object.assign({}, s, { items: a }) },
  metrics:    { get: s => s.metrics, set: (s, a) => Object.assign({}, s, { metrics: a }) },
  twocol:     { get: s => s.paragraphs, set: (s, a) => Object.assign({}, s, { paragraphs: a }) },
  threecol:   { get: s => s.paragraphs, set: (s, a) => Object.assign({}, s, { paragraphs: a }) },
  table:      { get: s => s.table && s.table.rows,
                set: (s, a) => Object.assign({}, s, { table: Object.assign({}, s.table, { rows: a }) }) },
};

/** M3 密度档（风格库 styleGrammar 的镜像；test_solver 校验与 layout-constants 一致）：
 *  紧凑风格一页多装、舒展风格少装——换风格同时换承载节奏。 */
const DENSITY_K = {"airy": 0.9, "normal": 1.0, "dense": 1.12};
const STYLE_DENSITY = {"business-blue": "normal", "apple-mono": "airy", "mckinsey": "dense", "brand-red": "normal", "warm-sand": "airy", "deep-teal": "normal", "graphite-dark": "dense", "indigo-violet": "normal", "spectrum": "dense", "ink-academic": "dense", "coral-launch": "airy", "sky-airy": "airy"};
function densityK(model) {
  const d = (model && (model.density || STYLE_DENSITY[model.style])) || 'normal';
  return DENSITY_K[d] || 1;
}

/** 容量比：条目数 / 上限（文字很长时按字数加权）。>1 = 超载。k = 密度系数。 */
function capacity(sec, mode, k) {
  const t = sec && sec.type;
  const acc = LISTS[t];
  if (!acc) return 0;
  const arr = acc.get(sec) || [];
  const cap = ((CAP[mode] || CAP.presentation)[t] || 99) * (k || 1);
  const chars = JSON.stringify(arr).length;
  const charCap = cap * (mode === 'research' ? 90 : 70);
  return round(Math.max(arr.length / cap, chars / charCap));
}

/** 超载页拆成续页。返回新 model（不改原对象）与拆页日志。 */
function splitModel(model, opts) {
  opts = opts || {};
  const mode = String(model.mode || 'presentation');
  const k = densityK(model);
  const out = [];
  const log = [];
  for (const sec of model.sections || []) {
    const ratio = capacity(sec, mode, k);
    const acc = LISTS[sec && sec.type];
    const arr = acc ? (acc.get(sec) || []) : [];
    if (!acc || ratio <= 1 || arr.length < 2) { out.push(sec); continue; }
    const parts = Math.min(arr.length, Math.ceil(ratio));
    const per = Math.ceil(arr.length / parts);
    for (let p = 0; p < parts; p++) {
      const slice = arr.slice(p * per, (p + 1) * per);
      if (!slice.length) continue;
      let ns = acc.set(sec, slice);
      if (p > 0) {
        ns = Object.assign({}, ns, { title: String(sec.title || '') + '（续）' });
        delete ns.soWhat; delete ns.verdict;            // 结论只在首页出现一次
      } else if (parts > 1) {
        delete ns.footnote;                             // 来源行放在最后一页
      }
      if (p > 0 && p < parts - 1) delete ns.footnote;
      out.push(ns);
    }
    log.push({ title: sec.title, type: sec.type, ratio, parts });
  }
  return { model: Object.assign({}, model, { sections: out }), log };
}

/** 12 列网格：span 列宽（含列间距）。 */
function grid12(totalW, span, gutter) {
  const g = gutter != null ? gutter : 0.25;
  const col = (totalW - g * 11) / 12;
  return round(col * span + g * (span - 1));
}

function round(v) { return Math.round(v * 1000) / 1000; }

module.exports = { rows, fitUp, estLines, estTextH, capacity, splitModel, grid12, densityK, CAP, LADDER, DENSITY_K, STYLE_DENSITY };
