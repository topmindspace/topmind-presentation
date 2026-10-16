#!/usr/bin/env node
/* topmind-presentation 命令行入口：npx topmind-presentation <build|doctor|path|help> */
'use strict';
const path = require('path');
const { spawnSync } = require('child_process');
const ROOT = path.resolve(__dirname, '..');
const cmd = process.argv[2] || 'help';
const rest = process.argv.slice(3);
function py() {
  for (const c of [process.env.PYTHON, 'python3', 'python']) {
    if (c && spawnSync(c, ['--version']).status === 0) return c;
  }
  console.error('未找到 Python 3（需要 ≥3.8）');
  process.exit(1);
}
if (cmd === 'doctor') {
  const r = spawnSync(py(), [path.join(ROOT, 'scripts', 'doctor.py'), ...rest], { stdio: 'inherit' });
  process.exit(r.status === null ? 1 : r.status);
} else if (cmd === 'build') {
  const r = spawnSync(py(), [path.join(ROOT, 'scripts', 'make_deck.py'), ...rest], { stdio: 'inherit' });
  process.exit(r.status === null ? 1 : r.status);
} else if (cmd === 'path') {
  console.log(ROOT);
} else {
  console.log('用法：topmind-presentation build 稿件.model.json [--out 目录] [--fidelity]   一条命令出 HTML + PPTX 并跑完门禁\n      topmind-presentation doctor [--full]   自检运行环境与技能包\n      topmind-presentation path              打印技能目录（把它交给智能体，入口是 SKILL.md）');
  process.exit(cmd === 'help' || cmd === '--help' ? 0 : 1);
}
