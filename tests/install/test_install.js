#!/usr/bin/env node
/* 安装器三条规则回归：默认升级（不备份）· 拒绝静默降级（--force 才降）· 同名目录（同一技能）自动替换、无关目录需 --force。
 * 另测：同版本不动、符号链接只删链接不删源、拒绝装进源目录、CLI 退出码。 */
'use strict';
const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawnSync } = require('child_process');
const { install, InstallError, readVersion } = require('../../scripts/lib_install');

const ROOT = path.resolve(__dirname, '..', '..');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'tp-install-'));
let fails = 0, n = 0;
function t(name, fn) {
  n++;
  try { fn(); console.log(`  ✓ ${name}`); } catch (e) { fails++; console.log(`  ✗ ${name}\n      ${e.message}`); }
}
function eq(a, b, m) { if (a !== b) throw new Error(`${m}：期望 ${JSON.stringify(b)}，实际 ${JSON.stringify(a)}`); }
function throwsInstall(fn, re) {
  try { fn(); } catch (e) {
    if (!(e instanceof InstallError)) throw e;
    if (re && !re.test(e.message)) throw new Error('报错文案不符：' + e.message);
    return;
  }
  throw new Error('应当报错但没有');
}
function fakePkg(ver) {
  const d = path.join(tmp, 'pkg-' + ver + '-' + Math.random().toString(36).slice(2, 7));
  fs.mkdirSync(path.join(d, 'scripts'), { recursive: true });
  fs.writeFileSync(path.join(d, 'SKILL.md'), `---\nname: topmind-presentation\nmetadata:\n  version: "${ver}"\n---\n# x\n`);
  fs.writeFileSync(path.join(d, 'scripts', `v${ver}.txt`), ver);
  fs.mkdirSync(path.join(d, 'node_modules', 'junk'), { recursive: true });
  return d;
}
const target = () => fs.mkdtempSync(path.join(tmp, 'skills-'));

console.log('test_install:');
t('全新安装：复制、不带 node_modules', () => {
  const T = target(); const r = install({ src: fakePkg('0.2.7'), targetRoot: T });
  eq(r.action, 'installed', 'action');
  eq(readVersion(path.join(T, 'topmind-presentation')), '0.2.7', '版本');
  eq(fs.existsSync(path.join(T, 'topmind-presentation', 'node_modules')), false, '不应复制 node_modules');
});
t('规则 1：有新版本直接覆盖旧版，不备份、不残留旧文件', () => {
  const T = target();
  install({ src: fakePkg('0.2.7'), targetRoot: T });
  const r = install({ src: fakePkg('0.2.8'), targetRoot: T });
  eq(r.action, 'upgraded', 'action'); eq(r.from, '0.2.7', 'from');
  const D = path.join(T, 'topmind-presentation');
  eq(readVersion(D), '0.2.8', '版本');
  eq(fs.existsSync(path.join(D, 'scripts', 'v0.2.7.txt')), false, '旧文件应被清掉');
  eq(fs.readdirSync(T).length, 1, '目标目录下不应有备份目录');
});
t('规则 1：读不到版本号的旧安装视为旧版，直接升级', () => {
  const T = target(); const D = path.join(T, 'topmind-presentation');
  fs.mkdirSync(D); fs.writeFileSync(path.join(D, 'SKILL.md'), '---\nname: topmind-presentation\n---\n');
  eq(install({ src: fakePkg('0.2.8'), targetRoot: T }).action, 'upgraded', 'action');
});
t('同版本：不动，提示已是最新；--force 重装', () => {
  const T = target(); const P = fakePkg('0.2.8');
  install({ src: P, targetRoot: T });
  eq(install({ src: P, targetRoot: T }).action, 'up-to-date', '同版本');
  eq(install({ src: P, targetRoot: T, force: true }).action, 'reinstalled', '--force');
});
t('规则 2：已装版本比安装包新 → 报错不降级', () => {
  const T = target();
  install({ src: fakePkg('0.2.9'), targetRoot: T });
  throwsInstall(() => install({ src: fakePkg('0.2.8'), targetRoot: T }), /不降级.*--force/);
  eq(readVersion(path.join(T, 'topmind-presentation')), '0.2.9', '拒绝后已装版本不变');
});
t('规则 2：加 --force 才降级', () => {
  const T = target();
  install({ src: fakePkg('0.2.9'), targetRoot: T });
  const r = install({ src: fakePkg('0.2.8'), targetRoot: T, force: true });
  eq(r.action, 'downgraded', 'action'); eq(readVersion(path.join(T, 'topmind-presentation')), '0.2.8', '版本');
});
t('规则 3：同名文件夹是之前装的同一技能 → 无需 --force 直接替换', () => {
  const T = target(); const D = path.join(T, 'topmind-presentation');
  fs.mkdirSync(D); fs.writeFileSync(path.join(D, 'SKILL.md'), '---\nname: topmind-presentation\nmetadata:\n  version: "0.1.0"\n---\n');
  fs.writeFileSync(path.join(D, 'stale.txt'), 'x');
  eq(install({ src: fakePkg('0.2.8'), targetRoot: T }).action, 'upgraded', 'action');
  eq(fs.existsSync(path.join(D, 'stale.txt')), false, '旧内容应被替换');
});
t('规则 3：同名符号链接指向同一技能 → 直接替换，且只删链接、不删源', () => {
  const T = target(); const old = fakePkg('0.2.7'); const D = path.join(T, 'topmind-presentation');
  fs.symlinkSync(old, D, 'dir');
  eq(install({ src: fakePkg('0.2.8'), targetRoot: T }).action, 'upgraded', 'action');
  eq(fs.lstatSync(D).isSymbolicLink(), false, '默认复制方式应换成真实目录');
  eq(fs.existsSync(path.join(old, 'SKILL.md')), true, '链接原指向的目录不能被删');
});
t('规则 3：同名但无关的文件夹 → 没有 --force 拒绝，内容保持原样', () => {
  const T = target(); const D = path.join(T, 'topmind-presentation');
  fs.mkdirSync(D); fs.writeFileSync(path.join(D, 'mine.txt'), '用户自己的');
  throwsInstall(() => install({ src: fakePkg('0.2.8'), targetRoot: T }), /--force/);
  eq(fs.readFileSync(path.join(D, 'mine.txt'), 'utf8'), '用户自己的', '无关目录不能被动');
});
t('规则 3：name 不同的别的技能 → 同样需要 --force', () => {
  const T = target(); const D = path.join(T, 'topmind-presentation');
  fs.mkdirSync(D); fs.writeFileSync(path.join(D, 'SKILL.md'), '---\nname: other-skill\n---\n');
  throwsInstall(() => install({ src: fakePkg('0.2.8'), targetRoot: T }), /--force/);
});
t('规则 3：无关文件夹加 --force 后替换', () => {
  const T = target(); const D = path.join(T, 'topmind-presentation');
  fs.mkdirSync(D); fs.writeFileSync(path.join(D, 'mine.txt'), 'x');
  eq(install({ src: fakePkg('0.2.8'), targetRoot: T, force: true }).action, 'replaced', 'action');
  eq(readVersion(D), '0.2.8', '版本');
});
t('--link：建符号链接；再次默认安装替换为复制', () => {
  const T = target(); const P = fakePkg('0.2.8'); const D = path.join(T, 'topmind-presentation');
  install({ src: P, targetRoot: T, link: true });
  eq(fs.lstatSync(D).isSymbolicLink(), true, '应为链接');
  install({ src: P, targetRoot: T });
  eq(fs.lstatSync(D).isSymbolicLink(), false, '应换成目录'); eq(fs.existsSync(path.join(P, 'SKILL.md')), true, '源仍在');
});
t('拒绝装进技能源目录内部', () => {
  const P = fakePkg('0.2.8');
  throwsInstall(() => install({ src: P, targetRoot: path.join(P, 'sub') }), /源目录/);
});
t('CLI：真实包升级 / 拒绝降级的退出码与提示', () => {
  const T = target(); const D = path.join(T, 'topmind-presentation');
  fs.mkdirSync(D); fs.writeFileSync(path.join(D, 'SKILL.md'), '---\nname: topmind-presentation\nmetadata:\n  version: "0.0.1"\n---\n');
  let r = spawnSync('node', [path.join(ROOT, 'scripts', 'cli.js'), 'install', '--to', T], { encoding: 'utf8' });
  eq(r.status, 0, '升级退出码'); if (!/已升级/.test(r.stdout)) throw new Error('缺升级提示：' + r.stdout);
  if (!fs.existsSync(path.join(D, 'scripts', 'build_pptx.js'))) throw new Error('真实包未复制完整');
  if (fs.existsSync(path.join(D, 'tests'))) throw new Error('不应复制 tests/');
  fs.writeFileSync(path.join(D, 'SKILL.md'), '---\nname: topmind-presentation\nmetadata:\n  version: "99.0.0"\n---\n');
  r = spawnSync('node', [path.join(ROOT, 'scripts', 'cli.js'), 'install', '--to', T], { encoding: 'utf8' });
  eq(r.status, 1, '拒绝降级退出码'); if (!/不降级/.test(r.stderr)) throw new Error('缺降级提示：' + r.stderr);
});

fs.rmSync(tmp, { recursive: true, force: true });
console.log(fails ? `test_install: FAIL ${fails}/${n}` : `test_install: PASS ${n}/${n}`);
process.exit(fails ? 1 : 0);
