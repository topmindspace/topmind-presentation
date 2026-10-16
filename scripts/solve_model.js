#!/usr/bin/env node
/**
 * solve_model.js —— 内容模型容量求解与拆页（M1）
 *
 * 用法：node scripts/solve_model.js <in.model.json> [--write | --out=<out.json>] [--json]
 *   默认只报告各页容量比；--write 原地写回拆页后的模型；--out= 写到新文件。
 *   HTML（render_from_model.py）与 PPTX（build_pptx.js）都消费拆页后的同一份模型，保证两端页序一致。
 * 退出码：0 无超载或已写回；1 存在超载但未写回；2 参数错误。
 */
'use strict';
const fs = require('fs');
const S = require('./lib_solver.js');

const args = process.argv.slice(2);
const inPath = args.find(a => !a.startsWith('--'));
if (!inPath) { console.error('用法: node scripts/solve_model.js <in.model.json> [--write | --out=<out.json>] [--json]'); process.exit(2); }
const outArg = (args.find(a => a.startsWith('--out=')) || '').slice(6);
const model = JSON.parse(fs.readFileSync(inPath, 'utf-8'));
const mode = String(model.mode || 'presentation');
const rows = (model.sections || []).map((s, i) => ({ i, type: s.type, title: s.title, ratio: S.capacity(s, mode) }));
const { model: solved, log } = S.splitModel(model);
if (args.includes('--json')) {
  console.log(JSON.stringify({ mode, pages: rows, splits: log }, null, 2));
} else {
  rows.filter(r => r.ratio > 0).forEach(r =>
    console.log(`${r.ratio > 1 ? '✗' : '✓'} #${r.i + 1} ${r.type.padEnd(10)} 容量 ${String(Math.round(r.ratio * 100)).padStart(3)}%  ${r.title || ''}`));
  console.log(log.length ? `[solve_model] 超载 ${log.length} 页，拆页后共 ${solved.sections.length} 页` : '[solve_model] 无超载页');
}
const target = args.includes('--write') ? inPath : outArg;
if (target) { fs.writeFileSync(target, JSON.stringify(solved, null, 2) + '\n'); console.log(`[solve_model] 已写入 ${target}`); process.exit(0); }
process.exit(log.length ? 1 : 0);
