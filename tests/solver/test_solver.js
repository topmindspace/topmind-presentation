#!/usr/bin/env node
/**
 * 布局求解器金样测试（M1）
 *   node tests/solver/test_solver.js            # 校验
 *   node tests/solver/test_solver.js --update   # 重写金样（须人工审阅 diff 后提交）
 * 覆盖：行高分配 / 字号求解 / 容量比 / 拆页 —— 10 个页型族 × 3 种模式；并断言同输入同输出。
 */
'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const S = require('../../scripts/lib_solver.js');

const GOLDEN = path.join(__dirname, 'golden.json');
const item = (i, len) => ['要点 ' + i, '说明文字'.repeat(len || 3)];
const FAMILIES = {
  points:   n => ({ type: 'points', title: 'P', points: Array.from({ length: n }, (_, i) => item(i)) }),
  cards:    n => ({ type: 'cards', title: 'C', cards: Array.from({ length: n }, (_, i) => item(i)) }),
  steps:    n => ({ type: 'steps', title: 'S', steps: Array.from({ length: n }, (_, i) => item(i)) }),
  timeline: n => ({ type: 'timeline', title: 'T', phases: Array.from({ length: n }, (_, i) => item(i)) }),
  table:    n => ({ type: 'table', title: 'TB', table: { head: ['a', 'b'], rows: Array.from({ length: n }, (_, i) => ['r' + i, 'v']) } }),
  twocol:   n => ({ type: 'twocol', title: '2C', paragraphs: Array.from({ length: n }, (_, i) => item(i, 6)) }),
  threecol: n => ({ type: 'threecol', title: '3C', paragraphs: Array.from({ length: n }, (_, i) => item(i, 4)) }),
  metrics:  n => ({ type: 'metrics', title: 'M', metrics: Array.from({ length: n }, (_, i) => ['指标' + i, String(i * 10)]) }),
  bullet:   n => ({ type: 'bullet', title: 'B', items: Array.from({ length: n }, (_, i) => '条目 ' + i) }),
  quote:    () => ({ type: 'quote', title: 'Q', quote: '金句' }),
};
const MODES = ['presentation', 'research', 'architecture'];
const SIZES = [3, 6, 12, 20];

function snapshot() {
  const out = { rows: {}, fitUp: {}, capacity: {}, split: {} };
  [[4.2, 3], [4.2, 6], [4.2, 12], [1.2, 6]].forEach(([a, n]) => {
    out.rows[`${a}x${n}`] = S.rows(a, n, { pref: 0.7, min: 0.3, max: 1.4, gap: 0.12 });
  });
  [0.8, 1.6, 3.2].forEach(av => {
    out.fitUp[av] = S.fitUp(f => S.estTextH('规模化落地需要技术、组织与经济三重门槛同时满足', 4, f, 1.45) * 2, av, { max: 24, min: 10 });
  });
  for (const mode of MODES) for (const [fam, mk] of Object.entries(FAMILIES)) for (const n of SIZES) {
    const sec = Object.assign(mk(n), { soWhat: '结论', footnote: '来源' });
    const key = `${mode}/${fam}/${n}`;
    out.capacity[key] = S.capacity(sec, mode);
    const r = S.splitModel({ mode, sections: [sec] });
    out.split[key] = r.model.sections.map(x => ({ title: x.title, soWhat: !!x.soWhat, footnote: !!x.footnote,
      n: JSON.stringify(x).length }));
  }
  return out;
}

/* 不变量 */
const a = snapshot(), b = snapshot();
assert.deepStrictEqual(a, b, '求解器必须确定性：同输入同输出');
for (const [k, pages] of Object.entries(a.split)) {
  const ratio = a.capacity[k];
  if (ratio > 1) {
    assert(pages.length >= 2, `${k} 容量 ${ratio} > 1 必须拆页`);
    assert(pages.slice(1).every(p => /（续）$/.test(p.title)), `${k} 续页标题须带（续）`);
    assert(pages.filter(p => p.soWhat).length === 1 && pages[0].soWhat, `${k} 结论只出现在首页`);
    assert(pages.filter(p => p.footnote).length === 1 && pages[pages.length - 1].footnote, `${k} 来源行只在末页`);
  } else {
    assert.strictEqual(pages.length, 1, `${k} 未超载不得拆页`);
  }
}
const r = S.rows(6, 2, { pref: 0.7, max: 1.5, gap: 0.2 });
assert(r.size === 1.5 && r.offset > 0, '富余空间：拉伸到上限后整组居中');
assert(S.rows(1, 6, { pref: 0.7, min: 0.1 }).size < 0.7, '紧张空间：行高压缩到首选以下');

if (process.argv.includes('--update')) {
  fs.writeFileSync(GOLDEN, JSON.stringify(a, null, 1) + '\n');
  console.log('[test_solver] 金样已更新：' + GOLDEN);
  process.exit(0);
}
const gold = JSON.parse(fs.readFileSync(GOLDEN, 'utf-8'));
try { assert.deepStrictEqual(a, gold); } catch (e) {
  console.error('[test_solver] FAIL: 求解结果与金样不一致（若为有意调整，--update 后审阅 diff 再提交）');
  console.error(String(e.message).slice(0, 1500));
  process.exit(1);
}
const nSplit = Object.values(a.split).filter(p => p.length > 1).length;
console.log(`[test_solver] PASS · ${Object.keys(a.capacity).length} 用例（10 页型族 × 3 模式 × 4 档）· 触发拆页 ${nSplit} 例 · 确定性 ✓`);
