/* 技能安装器（npx topmind-presentation install）。
 * 三条规则（tests/install/test_install.js 覆盖，CI 硬门禁）：
 *   1. 默认直接升级：已装旧版（或读不到版本号）→ 直接覆盖，不备份；同版本 → 提示已是最新，--force 才重装。
 *   2. 不悄悄降级：已装版本比安装包新 → 报错退出，--force 才降级。
 *   3. 同名文件夹自动替换：目标目录是之前装的同一技能（SKILL.md 的 name 一致，或指向同一技能的符号链接）→ 直接替换；
 *      名字相同但内容无关（无 SKILL.md / name 不同 / 普通文件）→ 必须 --force，避免误删用户自己的文件夹。
 * 安装方式：默认复制（不随 npm 缓存清理而失效）；--link 改为符号链接到当前包目录（适合本地开发）。
 * 只借鉴 topmind-writing-skills 安装器的规则，不依赖它。 */
'use strict';
const fs = require('fs');
const path = require('path');
const os = require('os');

const SKILL_ID = 'topmind-presentation';
const SKIP = new Set(['node_modules', '.git', '.github', 'dist', 'tests', 'docs', 'evals', '__pycache__', '.DS_Store']);

class InstallError extends Error {}

function frontmatter(dir) {
  try {
    const t = fs.readFileSync(path.join(dir, 'SKILL.md'), 'utf8');
    const m = t.match(/^---\r?\n([\s\S]*?)\r?\n---/);
    return m ? m[1] : '';
  } catch { return ''; }
}
function readName(dir) {
  const m = frontmatter(dir).match(/^name:\s*["']?([^"'\s]+)/m);
  return m ? m[1] : '';
}
function readVersion(dir) {
  const fm = frontmatter(dir);
  const m = fm.match(/^[ \t]+version:\s*["']?([^"'\s]+)/m) || fm.match(/^version:\s*["']?([^"'\s]+)/m);
  return m ? m[1] : '';
}
function parseVer(v) {
  const m = String(v || '').replace(/^v/, '').match(/^(\d+)\.(\d+)\.(\d+)/);
  return m ? m.slice(1).map(Number) : null;
}
/* a>b → 1；相等 0；a<b → -1。读不到的版本视为最旧 */
function cmpVer(a, b) {
  const pa = parseVer(a), pb = parseVer(b);
  if (!pa && !pb) return 0;
  if (!pb) return 1;
  if (!pa) return -1;
  for (let i = 0; i < 3; i++) if (pa[i] !== pb[i]) return pa[i] > pb[i] ? 1 : -1;
  return 0;
}
function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const e of fs.readdirSync(src, { withFileTypes: true })) {
    if (SKIP.has(e.name) || e.name.endsWith('.pyc')) continue;
    const s = path.join(src, e.name), d = path.join(dest, e.name);
    if (e.isDirectory()) copyDir(s, d);
    else if (e.isFile()) fs.copyFileSync(s, d);
  }
}
function real(p) {
  let cur = path.resolve(p); const tail = [];
  for (;;) {
    try { return path.join(fs.realpathSync(cur), ...tail); } catch {
      const up = path.dirname(cur); if (up === cur) return path.join(cur, ...tail);
      tail.unshift(path.basename(cur)); cur = up;
    }
  }
}
function defaultTarget(cwd, home) {
  const c = [['.claude', 'skills'], ['.agents', 'skills'], ['.cursor', 'skills'], ['.codex', 'skills']];
  for (const base of [cwd, home]) {
    for (const seg of c) if (base && fs.existsSync(path.join(base, seg[0]))) return path.join(base, ...seg);
  }
  return path.join(home || cwd, '.claude', 'skills');
}

/* 返回 { action: 'installed'|'upgraded'|'downgraded'|'reinstalled'|'replaced'|'up-to-date', dest, from, to } */
function install({ src, targetRoot, force = false, link = false }) {
  src = path.resolve(src);
  const pkgVer = readVersion(src);
  if (readName(src) !== SKILL_ID) throw new InstallError(`安装源不是 ${SKILL_ID}：${src}`);
  const dest = path.join(path.resolve(targetRoot), SKILL_ID);
  /* 目标本身可能是指向源的旧链接：只解析父目录，不跟随 dest 自身 */
  const rs = real(src), rd = path.join(real(path.dirname(dest)), path.basename(dest));
  if (rd === rs || rd.startsWith(rs + path.sep)) {
    throw new InstallError(`拒绝安装到技能源目录内部：${rd}（换一个 --to 目录）`);
  }
  let st = null;
  try { st = fs.lstatSync(dest); } catch { /* 不存在 */ }
  let action = 'installed', from = '';
  if (st) {
    const isLink = st.isSymbolicLink();
    const same = (isLink || st.isDirectory()) && readName(dest) === SKILL_ID;
    if (!same) {
      if (!force) {
        throw new InstallError(`目标已存在且不是 ${SKILL_ID}：${dest}\n` +
          '  （没有 SKILL.md，或 name 不同）。确认可以删除后加 --force 替换，或用 --to 换目录。');
      }
      action = 'replaced';
    } else {
      from = readVersion(dest);
      const c = cmpVer(pkgVer, from);
      if (c === 0 && !force && !(link && !isLink) && !(!link && isLink)) {
        return { action: 'up-to-date', dest, from, to: pkgVer };
      }
      if (c < 0 && !force) {
        throw new InstallError(`已装 ${SKILL_ID} ${from} 比安装包 ${pkgVer} 新，不降级。确需降级请加 --force。`);
      }
      action = c > 0 ? 'upgraded' : (c < 0 ? 'downgraded' : 'reinstalled');
    }
    /* 符号链接只删链接本身，绝不跟进去删源目录 */
    if (isLink || st.isFile()) fs.unlinkSync(dest);
    else fs.rmSync(dest, { recursive: true, force: true });
  }
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  if (link) fs.symlinkSync(src, dest, process.platform === 'win32' ? 'junction' : 'dir');
  else copyDir(src, dest);
  return { action, dest, from, to: pkgVer };
}

function runCli(argv, { root }) {
  let to = null, force = false, link = false;
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--to' || a === '-t') to = argv[++i];
    else if (a.startsWith('--to=')) to = a.slice(5);
    else if (a === '--force' || a === '-f') force = true;
    else if (a === '--link') link = true;
    else if (a === '--copy') link = false;
    else { console.error(`未知参数：${a}`); return 2; }
  }
  const targetRoot = to || defaultTarget(process.cwd(), os.homedir());
  try {
    const r = install({ src: root, targetRoot, force, link });
    const msg = {
      'installed': `已安装 ${SKILL_ID} ${r.to}`,
      'upgraded': `已升级 ${SKILL_ID} ${r.from || '(未知版本)'} -> ${r.to}（旧版直接覆盖，未备份）`,
      'downgraded': `已降级 ${SKILL_ID} ${r.from} -> ${r.to}（--force）`,
      'reinstalled': `已重装 ${SKILL_ID} ${r.to}`,
      'replaced': `已替换无关的同名目录并安装 ${SKILL_ID} ${r.to}（--force）`,
      'up-to-date': `已是最新：${SKILL_ID} ${r.to}（加 --force 可重装）`,
    }[r.action];
    console.log(msg);
    console.log(`  位置：${r.dest}${to ? '' : '（未给 --to，自动探测）'}${link ? '  [符号链接]' : ''}`);
    if (r.action !== 'up-to-date') console.log('  下一步：导出 PPTX 需在该目录跑一次 npm install；然后重启智能体');
    return 0;
  } catch (e) {
    if (e instanceof InstallError) { console.error(`安装失败：${e.message}`); return 1; }
    throw e;
  }
}

module.exports = { install, runCli, cmpVer, readVersion, readName, InstallError, SKILL_ID };
