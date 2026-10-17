/**
 * topmind-presentation · PPTX 精导（基于 PptxGenJS）
 *
 * 作用：把报告的「内容模型」（window.REPORT_MODEL，由 extract_model.py 抽取）导出为
 *       16:9 可编辑 PPTX（封面 / Agenda（architecture 可省）/ 章节页 / 收尾），与页面预览
 *       （assets/pptx-export.js，同一序列化语义）消费同一份 layout-constants.json 常量单源，
 *       产出一致。正式 PPTX 一律走本通道（页面不导出文件），strict 0/0 才交付。
 *
 * 用法：
 *   1) 抽模型：python scripts/extract_model.py "报告.html"（生成 报告.model.json）
 *   2) 生成：node scripts/build_pptx.js 报告.pptx --model="报告.model.json"
 *            （可选 --style=<风格> / --theme=light|dark 覆盖模型值）
 *   3) 质检（硬门禁）：python scripts/validate_pptx.py 报告.pptx --strict --model="报告.model.json"
 *
 * 章节页型（sections[].type，字段约束单源 scripts/model-schema.json，共 29 种）：
 *   points     要点列表 + 可选右侧指标列（默认）
 *   metrics    大指标带（4–6 个核心数字）
 *   kpi        大数指标页（hero=[值,标签,delta?] 巨号数字 + 右列支撑指标）
 *   table      对比表（head + rows）
 *   timeline   路线/阶段（phases: [label, 名称, 说明, done|now|'']）
 *   steps      步骤条（steps: [[标题,说明]…]，可选 groups 分组、accent 高亮步）
 *   bar        数据图表页（chart.type 见 model-schema.json chartTypes：30 类）
 *   donut      环形图页（原生数据图表 + 挖孔 + 中心合计 + 右侧数值图例）
 *   heatmap    热力矩阵（rowHeads × colHeads + cells 数值，4 级色阶）
 *   bullet     达成对比（items: [[标签,实际,目标]…]，底槽 + 实际条 + 目标刻度）
 *   pyramid    金字塔（levels: [[标题,说明]…] 自上而下逐层加宽）
 *   image      素材图片页（image:{src|items|placeholder, layout:full|half|bleed|grid|compare|wall,
 *              fit:cover|contain, caption}；src 仅 data:/相对路径；无图走原生配图占位）
 *   cards      卡片网格
 *   split      左文右图（left.points + right: chart/table/image；图表字段挂在 right 上）
 *   comparison 对比页（left/right 双面板 + 可选 verdict 结论条）
 *   quote      引用/金句页（主题一致强调带：accent-soft 底，浅色模式不再出深色页）
 *   diagram    分层架构（layers + legend，含层间连接；architecture 模式走全幅图页型）
 *   exhibit    Exhibit 编号图表页（research：exhibitNo + chart + soWhat + footnote）
 *   twocol     双栏论证页（research R1）
 *   threecol   三栏证据页（research R6）
 *   halftable  半表半图页（research R7：table + chart 对照）
 *   matrix     矩阵图页（research R8：rowHeads × colHeads + cells）
 *   lane       泳道页（architecture A2：lanes + steps）
 *   ── 复杂信息图专属页型（结构化载荷，不走 chart.type）──
 *   sankey     桑基图页（flows:[[源,汇,值]…]，分层节点 + 流带；≥16 采样点、双边界追踪）
 *   treemap    树图页（items:[[标签,值]…]，面积 ∝ 数值）
 *   boxplot    箱线图页（groups:[[标签,min,q1,中位,q3,max]…]）
 *   network    关系网络页（nodes:[[id,名称]…] + edges:[[源,汇]…]，确定性环形布局）
 *   marimekko  马赛克图页（cols + cells + legend，列宽 × 列高双重编码）
 *   streamgraph 流带图页（series + labels，基线居中，≥24 采样点）
 *   通用可选字段：soWhat（so-what 结论条）、footnote（页脚来源行）、
 *                flags（待核实标注清单 → accent 强调色清单条，提示用户二次确认）、image（素材图片）、
 *                exhibitNo（非 exhibit 页型也可带 Exhibit 帧头徽标，正文区自动下移让位）
 *
 * 图表双通道（charts.registry 四元组为唯一分派依据）：
 *   原生 16 类走 pptxgenjs addChart（chart part + 内嵌 Excel，双击可编辑数据）；
 *   形状 20 类走高保真形状还原（曲线用多段旋转矩形沿采样路径逼近，禁 preset 形状替代），
 *   并按 chart.dataTable 策略附数据表（notes 默认 / inline 页内表格）——数据可追溯。
 *
 * 版式纪律：所有几何常量取自 layout-constants.json（禁止在此手写坐标）；
 *   文本块按可用高度自适应字号/行距（fitFont），杜绝溢出——这是「每页高度稳定」的保障。
 */

/* eslint-disable */
let pptxgen;
try {
  pptxgen = require('pptxgenjs');
} catch (e) {
  console.error('[build_pptx] FAIL: 缺少依赖 pptxgenjs（' + (e && e.message) +
    '）。请在技能目录执行 npm install，或设置 NODE_PATH 指向其 node_modules。');
  process.exit(1);
}
const fs = require('fs');
const path = require('path');

/* ═══ CLI 参数 fail-fast（审计 中等-12）═══
 * 未知参数一律报错退出（exit 2），不再执行默认构建并写出文件；
 * --help / -h 打印用法并正常退出（exit 0）。
 * 位置参数只接受一个（输出文件名）。 */
(function failFastOnUnknownArgs() {
  const raw = process.argv.slice(2);
  if (raw.includes('--help') || raw.includes('-h')) {
    console.log(
`用法：
  node scripts/build_pptx.js [输出.pptx | --out=<输出.pptx>] --model=<模型.json> [--style=<风格>] [--theme=light|dark] [--strict]

  1) 抽模型：python scripts/extract_model.py <报告.html>（生成 <报告>.model.json）
  2) 生成：  node scripts/build_pptx.js 报告.pptx --model=报告.model.json
  3) 质检：  python scripts/validate_pptx.py 报告.pptx --strict --model=报告.model.json

参数：
  --model=<file>   内容模型 JSON（必填；由 extract_model.py 从 HTML 报告抽取。--demo 可显式生成内嵌示例）
  --out=<file>     输出路径（等价于位置参数；二者只能给一个）
  --strict         图标资产缺失（回落色块）时直接失败（exit 3）
  --demo           显式使用内嵌示例内容（仅调试）
  --style=<name>   覆盖模型的风格（9 套风格 token 见 scripts/layout-constants.json）
  --theme=light|dark  主题（--theme 覆盖 > 模型 theme > 默认 light）`);
    process.exit(0);
  }
  const known = /^(--model=|--style=|--theme=|--out=|--strict$|--demo$)/;
  let positional = 0;
  for (const a of raw) {
    if (a.startsWith('-')) {
      if (!known.test(a)) {
        console.error(`[build_pptx] FAIL: 未知参数 ${a} —— 拒绝执行（用 --help 查看用法）`);
        process.exit(2);
      }
    } else if (++positional > 1 || (positional === 1 && raw.some(x => x.startsWith('--out=')))) {
      console.error(`[build_pptx] FAIL: 多余的位置参数 ${a} —— 只接受一个输出文件名`);
      process.exit(2);
    }
  }
  if (!raw.some(x => x.startsWith('--model=')) && !raw.includes('--demo')) {
    console.error('[build_pptx] FAIL: 缺少 --model=<模型.json>。先跑 python scripts/extract_model.py <报告.html>；仅调试示例时显式加 --demo。');
    process.exit(2);
  }
})();

/* ══════════ 版式常量单源（scripts/layout-constants.json · 两通道共用，禁止在此手写常量） ══════════ */
/* 单源损坏（缺失/非 JSON）必须干净 FAIL，不得裸 SyntaxError 堆栈 */
let LC;
try {
  LC = JSON.parse(fs.readFileSync(path.join(__dirname, 'layout-constants.json'), 'utf-8'));
} catch (e) {
  console.error('[build_pptx] FAIL: 版式常量 layout-constants.json 读取失败（' + ((e && e.message) || e) + '）。请确认技能安装完整。');
  process.exit(1);
}
if (!LC || typeof LC !== 'object' || !LC.page || !LC.styles) {
  console.error('[build_pptx] FAIL: layout-constants.json 缺关键顶层键（page/styles），疑似损坏。');
  process.exit(1);
}
/* M12 页面装饰开关（lib_chrome.js）：默认无眉标、无页脚注释行、只留克制页码；腾出的高度在常量派生前交给正文区 */
const CHROME = require('./lib_chrome.js');
const CHROME_FLAGS = CHROME.chromeFlags(CHROME.peekModel());
const DENSE = require('./lib_dense.js');
const ICON_STYLE = (CHROME.peekModel() || {}).iconStyle === 'fill' ? 'fill' : 'line';   // M13：全篇统一图标风格
CHROME.applyChrome(LC, CHROME_FLAGS);
const STYLE_PRESETS = LC.styles;                      // 9 套风格 token（light）
const STYLE_PRESETS_DARK = LC.stylesDark || {};       // 9 套风格 token（dark）
const STYLE_DATA_COLORS = LC.styleDataColors || {};            // 9 套风格各自的编码色板（light）
const STYLE_DATA_COLORS_DARK = LC.styleDataColorsDark || {};   // 深色主题版（按 model.theme 选择）
const { pw: PW, ph: PH, mx: MX } = LC.page;           // 16:9，页边距
const CW = PW - 2 * MX;
const TS_BASE = LC.typeScale;                         // 排版比例尺基准（presentation pt）
const MTS = LC.modeTypeScale;                         // 三模式独立排版比例尺
const PT = LC.pageTypes;                              // 页型几何（含 layout / cover / closing / steps / heatmap / bullet / pyramid …）
const IMG = LC.imageSpec || {};                       // 图片规格与配图占位约定（双引擎同源）
const LAY = PT.layout || {};
const CONTENT_TOP = LAY.contentTop != null ? LAY.contentTop : 2.5;
const CONTENT_BOTTOM = LAY.contentBottom != null ? LAY.contentBottom : 6.9;
const CONTENT_BOTTOM_NOTE = LAY.contentBottomWithNote != null ? LAY.contentBottomWithNote : 6.4;
/* 页型布局区域 IR：语义槽位 → 英寸矩形（与 layout_slots.json 同源；未识别槽位时回落 PT 常量） */
const REGIONS = require('./lib_layout_regions.js');
/* M1 布局求解器（行高分配 / 字号放大 / 容量拆页；纯函数、与 HTML 端和测试共用） */
const SOLVER = require('./lib_solver.js');
CHROME.applyChrome(REGIONS.LC, CHROME_FLAGS);

/* ══ 语义图标真导出（SVG→PNG · scripts/icon-assets.json 预生成缓存）══
 * HTML .card__ico / .ul--ico 的 SVG 图标在此栅格化为 PNG 嵌入，不再用 accent 方块替代。
 * 图标图 objectName 统一 `icon:` 前缀 —— validate_pptx 单独计数，不进 pictures 内容图门禁。 */
const ICON_LIB = require('./icon_lib.js');
let ICON_ASSETS = { icons: {}, px: 64 };
/* 预生成缓存可选（scripts/icon-assets.json，需 sharp 离线生成）；缺省直接用包内 assets/icons/*.png，
   运行时不再隐式调用 sharp。 */
try {
  ICON_ASSETS = JSON.parse(fs.readFileSync(path.join(__dirname, 'icon-assets.json'), 'utf-8'));
} catch (e) { /* 走包内 PNG */ }
const STRICT = process.argv.includes('--strict');
const ICON_MISSES = [];
function _normColor(c) {
  if (typeof c !== 'string') return '#333333';
  let v = c.trim().toLowerCase();
  if (/^[0-9a-f]{6}$/.test(v)) v = '#' + v;
  if (/^[0-9a-f]{3}$/.test(v)) v = '#' + v;
  return v;
}
/* M8：图标跟随风格主色。包内 PNG 是调色板图（color type 3，透明度在 tRNS），
   单色线性图标只需把 PLTE 每个条目的 RGB 改成目标色、alpha 不动，即可无依赖重新着色。 */
const _CRC_T = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
function _crc32(buf) { let c = 0xffffffff; for (let i = 0; i < buf.length; i++) c = _CRC_T[(c ^ buf[i]) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; }
const _RECOLOR_CACHE = new Map();
function recolorPng(buf, colorHex) {
  const hex = _normColor(colorHex || '').replace('#', '');
  if (!/^[0-9a-f]{6}$/.test(hex) || buf.length < 33 || buf[25] !== 3) return buf;
  const key = hex + ':' + _crc32(buf);
  if (_RECOLOR_CACHE.has(key)) return _RECOLOR_CACHE.get(key);
  const rgb = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16));
  const out = Buffer.from(buf);
  let off = 8;
  while (off + 12 <= out.length) {
    const len = out.readUInt32BE(off);
    const type = out.toString('latin1', off + 4, off + 8);
    if (type === 'PLTE') {
      for (let i = 0; i + 2 < len; i += 3) { out[off + 8 + i] = rgb[0]; out[off + 9 + i] = rgb[1]; out[off + 10 + i] = rgb[2]; }
      out.writeUInt32BE(_crc32(out.subarray(off + 4, off + 8 + len)), off + 8 + len);
      break;
    }
    off += 12 + len;
  }
  _RECOLOR_CACHE.set(key, out);
  return out;
}
/** 取图标 PNG data URI；无缓存时按名挑色兜底（accent → 首色 → 包内 256px PNG → null） */
function iconPng(name, colorHex) {
  const n = name && ICON_ASSETS.icons[name] ? name : ICON_LIB.pickIconName(name, 0);
  const bag = ICON_ASSETS.icons[n];
  if (bag) {
    const want = _normColor(colorHex);
    if (bag[want]) return bag[want];
    const keys = Object.keys(bag);
    if (keys.length) return bag[keys[0]];
  }
  // 无 sharp / 无预生成资产时的可靠回落：包内 256px 预渲染 PNG（python-pptx/pptxgenjs 均可直接嵌入）
  try {
    const p = ICON_LIB.iconPngPath(n);
    if (p) return 'data:image/png;base64,' + recolorPng(fs.readFileSync(p), colorHex).toString('base64');
  } catch (e) { /* 继续回落 accent 方块 */ }
  return null;
}
/** 在指定盒内嵌图标（真导出）；无图标资产时回落 accent 小方块（可扫读路标） */
function addIcon(s, name, x, y, size, colorHex) {
  const uri = iconPng(name, colorHex || (STYLE && STYLE.accent) || '#1a56a8');
  if (uri) {
    try {
      s.addImage({ data: uri, x, y, w: size, h: size, objectName: 'icon:' + (name || 'icon') });
      return true;
    } catch (e) { /* 回落方块 */ }
  }
  s.addShape('roundRect', { x, y, w: size, h: size, rectRadius: 0.04,
    fill: { color: (STYLE && STYLE.accent) || '1A73E8' }, line: { type: 'none' },
    objectName: 'icon:' + (name || 'mark') });
  ICON_MISSES.push(name || '(unnamed)');
  return false;
}

/* M13 图标路标（与 HTML .ico--line / .ico--fill 同构）：line = 浅色底 + 强调色描边；fill = 强调色实底 + 反白描边。
   模型级 iconStyle 全篇统一（validate_pptx ICON_STYLE_MIXED 拦混用）。 */
function iconMark(s, name, x, y, size, opts) {
  opts = opts || {};
  const fill = (opts.fill != null ? opts.fill : ICON_STYLE === 'fill');
  s.addShape(opts.round ? 'ellipse' : 'roundRect', { x, y, w: size, h: size, rectRadius: rr(Math.min(0.12, size * 0.28)),
    fill: { color: fill ? STYLE.accent : STYLE.soft }, line: { type: 'none' }, objectName: opts.name || ('icontile:' + (fill ? 'fill' : 'line')) });
  const k = opts.round ? 0.46 : 0.56, is = size * k;
  addIcon(s, name, x + (size - is) / 2, y + (size - is) / 2, is, fill ? 'FFFFFF' : STYLE.accent);
}
/* M13 简单版式（focus）：一个放大的锚点 + 至多一个从属元素。与 HTML .focus--left / center / split 同构：
   left = 锚点占左 ~57%，从属文字在右下（细分隔线起头）；center = 居中；split = 左锚点 / 右文字（约 4:6）。
   装饰只用大号淡色序号（decoNo）与柔和圆形底，不铺满、不堆图标。 */
function focusPage(s, sec, y0, y1) {
  const k = DENSE.focusKind(sec), v = DENSE.focusVariant(sec);
  const H = y1 - y0, cy = y0 + H / 2;
  if (sec.decoNo) s.addText(String(sec.decoNo), { x: MX + CW - 4.2, y: y0 - 0.9, w: 4.2, h: 2.6, align: 'right', valign: 'top',
    fontFace: STYLE.fontDisplay, fontSize: 96, bold: true, color: STYLE.soft, margin: 0, objectName: 'focus:deco' });
  const sub = (txt, x, y, w, h, fz, opts) => txt && s.addText(String(txt), Object.assign({ x, y, w, h, fontFace: STYLE.font, fontSize: fz,
    color: STYLE.body, valign: 'top', margin: 0 }, opts || {}));
  if (k === 'number') {
    const n = DENSE.kv3(sec.number || []);
    const aw = CW * 0.57;
    s.addText(n[0], { x: MX, y: cy - 1.25, w: aw, h: 1.9, fontFace: STYLE.fontDisplay, fontSize: estLines(n[0], aw, 96) > 1 ? 52 : 96,
      bold: true, color: STYLE.accent, valign: 'bottom', margin: 0, objectName: 'focus:anchor' });
    sub(n[1], MX, cy + 0.75, aw, 0.6, sz(20), { color: STYLE.ink, bold: true });
    if (sec.text) {
      const bx = MX + aw + 0.5, bw = CW - aw - 0.5;
      s.addShape('line', { x: bx, y: cy + 0.15, w: bw, h: 0.0001, line: { color: STYLE.line, width: 1 } });
      sub(sec.text, bx, cy + 0.35, bw, Math.max(0.6, y1 - cy - 0.5), sz(15));
    }
  } else if (k === 'statement' || k === 'text') {
    const t = String(k === 'statement' ? sec.statement : sec.text || ''), aw = CW * (k === 'statement' ? 0.72 : 0.62);
    const fz = k === 'statement' ? [34, 30, 26].map(sz).find(f => estTextH(t, aw, f, 1.3) <= H * 0.55) || sz(24)
      : [22, 20, 18].map(sz).find(f => estTextH(t, aw, f, 1.5) <= H * 0.6) || sz(16);
    const th = estTextH(t, aw, fz, 1.5) + 0.3;
    const ty = y0 + Math.max(0.2, (H - th) * 0.42);
    s.addShape('rect', { x: MX, y: ty - 0.32, w: 0.6, h: 0.05, fill: { color: STYLE.accent }, line: { type: 'none' }, objectName: 'focus:rule' });
    s.addText(t, { x: MX, y: ty, w: aw, h: th, fontFace: k === 'statement' ? STYLE.fontDisplay : STYLE.font, fontSize: fz,
      bold: k === 'statement', color: k === 'statement' ? STYLE.ink : STYLE.body, valign: 'top', margin: 0, objectName: 'focus:anchor' });
    if (k === 'statement' && sec.text) {
      const bx = MX + aw + 0.45, bw = CW - aw - 0.45;
      if (bw > 1.6) { s.addShape('line', { x: bx, y: ty + th - 0.9, w: bw, h: 0.0001, line: { color: STYLE.line, width: 1 } });
        sub(sec.text, bx, ty + th - 0.72, bw, 1.2, sz(13)); }
      else sub(sec.text, MX, ty + th + 0.25, aw, 0.9, sz(14));
    }
  } else if (k === 'icon' || k === 'iconText') {
    const d = 2.1;
    if (v === 'center' || k === 'icon') {
      iconMark(s, sec.icon || sec.title, MX + (CW - d) / 2, y0 + Math.max(0.1, (H - d - 1.2) / 2), d, { round: true, name: 'focus:anchor' });
      const ly = y0 + Math.max(0.1, (H - d - 1.2) / 2) + d + 0.3;
      sub(sec.label, MX + CW * 0.2, ly, CW * 0.6, 0.45, sz(20), { align: 'center', bold: true, color: STYLE.ink });
      sub(sec.text, MX + CW * 0.2, ly + (sec.label ? 0.5 : 0), CW * 0.6, 0.8, sz(15), { align: 'center' });
    } else {
      const lw = CW * 0.4;
      iconMark(s, sec.icon || sec.title, MX + (lw - d) / 2, cy - d / 2, d, { round: true, name: 'focus:anchor' });
      const bx = MX + lw + 0.3, bw = CW - lw - 0.3;
      const lab = sec.label ? 0.55 : 0;
      const th = estTextH(sec.text || '', bw, sz(18), 1.5);
      const by = cy - (lab + th) / 2;
      sub(sec.label, bx, by, bw, 0.5, sz(22), { bold: true, color: STYLE.ink });
      sub(sec.text, bx, by + lab, bw, th + 0.1, sz(18));
    }
  } else if (k === 'twoText') {
    const ts = (sec.texts || []).slice(0, 2).map(DENSE.pt3), gap = 0.7, w = (CW - gap) / 2;
    const hs = ts.map(t => 0.55 + estTextH(t[1], w, sz(15), 1.5));
    const hh = Math.max(...hs), ty = y0 + Math.max(0.2, (H - hh) * 0.45);
    ts.forEach((t, i) => {
      const x = MX + i * (w + gap);
      s.addShape('rect', { x, y: ty, w, h: 0.035, fill: { color: STYLE.accent }, line: { type: 'none' }, objectName: 'focus:rule' });
      sub(t[0], x, ty + 0.2, w, 0.45, sz(20), { bold: true, color: STYLE.ink });
      sub(t[1], x, ty + 0.72, w, hh, sz(15));
    });
  } else if (k === 'chart') {
    const cw = Math.min(CW * 0.72, 9.0), cx = MX + (CW - cw) / 2;
    const th = sec.text ? 0.7 : 0, ch = Math.min(H - th - 0.2, 4.0), ty = y0 + Math.max(0.05, (H - ch - th) / 2);
    s.addShape('rect', { x: cx, y: ty - 0.25, w: 0.6, h: 0.05, fill: { color: STYLE.accent }, line: { type: 'none' }, objectName: 'focus:rule' });
    compChart(s, sec.chart, (sec.chart || {}).type === 'donut' ? 'donut' : 'bar', cx, ty, cw, ch);
    sub(sec.text, cx, ty + ch + 0.15, cw, 0.6, sz(14), { align: 'center' });
  }
}
/* 取 --name=value 参数值（路径里含 '=' 时 split('=')[1] 会截断，用 slice 精确取） */
const _argVal = (name) => {
  const a = process.argv.find(x => x.startsWith(name + '='));
  return a ? a.slice(name.length + 1) : undefined;
};
const modelArg = _argVal('--model');
let styleArg = _argVal('--style');
let themeArg = _argVal('--theme');
let STYLE;   // 在内容模型加载后确定（模型可带默认 style）
let THEME = 'light';   // 亮/暗主题（--theme= 覆盖 > 模型 theme > 默认 light）
let MODEL_DIR = null;  // 模型文件所在目录（素材图片相对路径以此为锚）

let MODE_NAME = 'presentation';   // 当前模式（加载模型后设置）
/* 三模式独立排版比例尺：基准 pt → 最接近 TS_BASE 角色 → MTS[mode][role]。
   research 是咨询密排比例尺（正文 10.5pt），不再是简单 ×0.8。保留 0.5pt 精度。
   未知模式回落 presentation 档（MTS 与 mode 取值同源于 model-schema.json 的 modes）。 */
const sz = (pt) => {
  const mts = (MTS && (MTS[MODE_NAME] || MTS.presentation)) || null;
  if (!mts) return Math.max(8.5, Math.round(pt * 2) / 2);
  let best = null, bd = 1e9;
  for (const k of Object.keys(TS_BASE)) {
    const d = Math.abs(TS_BASE[k] - pt);
    if (d < bd) { bd = d; best = mts[k]; }
  }
  return Math.max(8.5, Math.round((best == null ? pt : best) * 2) / 2);
};
/* M9：风格圆角——卡片 rectRadius 按 styleIdentity.radius / 16px 等比缩放（单源，已由 audit_styles 与 engine.css 对齐），
   让 12 套风格在 PPTX 里也有各自的「手感」：mckinsey 6px 方正克制、apple-mono / sky-airy 20px 圆润 */
const rr = (v) => { const id = (LC.styleIdentity || {})[styleArg] || {}; const px = parseFloat(id.radius); return +(v * (px ? px / 16 : 1)).toFixed(3); };
/* M9：按角色名取字号（chapterTitle / kpiCard 等），值仍出自 modeTypeScale，validate 比例尺照常生效 */
const roleSz = (role, base) => { const m = (MTS && (MTS[MODE_NAME] || MTS.presentation)) || {}; return m[role] != null ? m[role] : sz(base); };
/* 编码色板：9 套风格**各有自己的** c1–c5（单源 styleDataColors / styleDataColorsDark）。
   与 HTML 侧的 .f-c1~c5 语义类同源；结构色纪律不受影响——本表只用于数据系列。 */
const _dcWarned = new Set();
function dataColors(style) {
  const map = (THEME === 'dark' && Object.keys(STYLE_DATA_COLORS_DARK).length)
    ? STYLE_DATA_COLORS_DARK : STYLE_DATA_COLORS;
  const c = map[style];
  if ((!c || !c.length) && !_dcWarned.has(style)) {
    _dcWarned.add(style);
    /* 静默回落到单色会让多系列图表失去可区分性，但产物照样"合格"——必须出声 */
    console.warn(`[build_pptx] 风格 "${style}" 缺${THEME === 'dark' ? '深色' : ''}编码色板 c1–c5，` +
      '多系列图表将回落单色梯度（建议补 layout-constants.json 的 ' +
      (THEME === 'dark' ? 'styleDataColorsDark' : 'styleDataColors') + '）。');
  }
  return (c && c.length) ? c : null;
}
/* 单色风格的数据色板回落（多扇区/多系列页型） */
function donutColors(style) {
  return dataColors(style) || [STYLE.accent, STYLE.faint, STYLE.body, STYLE.line];
}

/* ══════════ 自适应排版工具（保证内容不溢出页面 —— 每页高度稳定的 PPTX 侧保障） ══════════ */
/* 文本度量单源：validate_pptx.py 的溢出估算读同一份，两侧同值才不会出现「引擎装得下、门禁判溢出」或反之 */
const TM = (LC.containers && LC.containers.textMetrics) || {};
const TM_LINE = TM.lineFactor != null ? TM.lineFactor : 1.45;
const TM_ASCII = TM.emAsciiRatio != null ? TM.emAsciiRatio : 0.52;
/* 估算文本行数：CJK 按 1em，拉丁/数字按 emAsciiRatio（保守偏大，宁可早换行） */
function estLines(text, widthIn, fontPt) {
  const usable = Math.max(24, widthIn * 72 - 8);
  let w = 0, lines = 1;
  const s = String(text == null ? '' : text);
  for (let i = 0; i < s.length; i++) {
    if (s[i] === '\n') { lines++; w = 0; continue; }
    const cw = /[\x00-\xff]/.test(s[i]) ? fontPt * TM_ASCII : fontPt;
    if (w + cw > usable) { lines++; w = cw; } else { w += cw; }
  }
  return lines;
}
function estTextH(text, widthIn, fontPt, lineFactor) {
  return estLines(text, widthIn, fontPt) * fontPt * (lineFactor || TM_LINE) / 72;
}
/* M12 行距单源（containers.lineSpacing）：正文级字号、至少两行的普通文本框默认行距 1.5×字号；
   估算装不下时降到 1.3×，不再更低（再装不下交给缩字号/拆页）。所有 addText 都经此统一，调用处不再手写行距。 */
const LS = (LC.containers && LC.containers.lineSpacing) || {};
const LS_DEF = LS.default || 1.5, LS_MIN = LS.min || 1.3, LS_BODY_MAX = LS.bodyMaxPt || 16;
const LS_STATS = { def: 0, min: 0 };
function _paraTexts(text) {
  if (!Array.isArray(text)) return String(text == null ? '' : text).split('\n');
  const out = ['']; let maxFz = 0;
  for (const r of text) {
    if (!r) continue;
    const t = typeof r === 'string' ? r : String(r.text == null ? '' : r.text);
    out[out.length - 1] += t;
    const o = (r && r.options) || {};
    if (o.fontSize) maxFz = Math.max(maxFz, o.fontSize);
    if (o.breakLine || o.bullet) out.push('');
  }
  if (out.length > 1 && out[out.length - 1] === '') out.pop();
  out.maxFz = maxFz;
  return out;
}
function lineSpacingFor(text, o) {
  if (!o || o.fit === 'shrink' || o.lineSpacingMultiple) return null;
  const paras = _paraTexts(text);
  const fz = Math.max(o.fontSize || 0, paras.maxFz || 0);
  if (!fz || fz > LS_BODY_MAX || typeof o.w !== 'number' || typeof o.h !== 'number') return null;
  const ml = Array.isArray(o.margin) ? o.margin : null;
  const w = o.w - (ml ? (ml[1] + ml[3]) / 72 : 0.1);
  let lines = 0;
  for (const p of paras) lines += estLines(p.split('\n').join(''), w, fz) + (p.split('\n').length - 1);
  if (lines < 2) return null;
  const gap = (o.paraSpaceBefore || 0) * Math.max(0, paras.length - 1) / 72;
  const avail = o.h - (ml ? (ml[0] + ml[2]) / 72 : 0.1);
  const need = (lf) => lines * fz * lf / 72 + gap;
  return need(LS_DEF) <= avail + 0.02 ? LS_DEF : LS_MIN;
}
/* 有限缩字号（v8.2）：优先取最大可装字号；内容偏多时允许阶梯下探。
   策略（containers.fontShrink 单源）：先优化内容/组合/拆页，最后才缩字号；
   maxShrinkSteps 限制相对首选档的下探步数，floorPt 为模式绝对下限。
   装不下时仍取下限——保证不越界；调用方应配合 validate 的内容预算与拆页建议。 */
const FS_POLICY = (function () {
  try {
    const raw = fs.readFileSync(path.join(__dirname, 'layout-constants.json'), 'utf-8');
    const p = (JSON.parse(raw).containers || {}).fontShrink || {};
    return {
      ladder: p.ladder || [15, 14, 13.5, 13, 12.5, 12, 11.5, 11, 10.5, 10, 9.5, 9, 8.5],
      maxShrinkSteps: p.maxShrinkSteps != null ? p.maxShrinkSteps : 4,
      floorPt: p.floorPt || { presentation: 10, research: 9, architecture: 10 },
      warnBelow: p.warnBelow != null ? p.warnBelow : 9.5,
    };
  } catch (e) {
    return {
      ladder: [15, 14, 13.5, 13, 12.5, 12, 11.5, 11, 10.5, 10, 9.5, 9, 8.5],
      maxShrinkSteps: 4,
      floorPt: { presentation: 10, research: 9, architecture: 10 },
      warnBelow: 9.5,
    };
  }
})();
const FONT_LADDER = FS_POLICY.ladder;
/* 大字档（原文锁定的短清单 / 陈述卡）：在常规阶梯上方加 24–16pt，供字号向上求解 */
const BIG_LADDER = [24, 22, 20, 18, 17, 16].concat(FS_POLICY.ladder);
/* 弹性文本单源（containers.adaptiveText · 0.2.0）：长标题/长列表/长表格单元格的降级规则。
   调用处只读 AT_* 与下列 helper，禁止手写字号/行距/阈值 magic number。 */
const AT = (LC.containers && LC.containers.adaptiveText) || {};
const AT_TITLE = AT.title || {}, AT_LIST = AT.list || {}, AT_TABLE = AT.table || {};
/* 标题字号上限：按字符数（CJK=1，拉丁/数字≈0.5，与 estLines 同口径）分档 */
function titleMaxFor(text) {
  const s = String(text == null ? '' : text);
  let units = 0;
  for (const ch of s) units += /[\x00-\xff]/.test(ch) ? 0.5 : 1;
  if (units >= (AT_TITLE.xlongChars != null ? AT_TITLE.xlongChars : 44)) return AT_TITLE.xlongMax || 20;
  if (units >= (AT_TITLE.longChars != null ? AT_TITLE.longChars : 28)) return AT_TITLE.longMax || 24;
  return AT_TITLE.base || 30;
}
/* 列表密集度：条目数达标 → 收紧字号上限/段间距/行距 */
function listFitOpts(n) {
  const dense = n >= (AT_LIST.denseItems != null ? AT_LIST.denseItems : 6);
  return {
    dense,
    max: dense ? (AT_LIST.denseMax || 12) : (AT_LIST.max || 14),
    gapFactor: dense ? (AT_LIST.denseGapFactor != null ? AT_LIST.denseGapFactor : 0.25)
                     : (AT_LIST.gapFactor != null ? AT_LIST.gapFactor : 0.5),
    lineFactor: dense ? (AT_LIST.denseLineFactor || 1.3) : (AT_LIST.lineFactor || 1.45),
  };
}
/* 缩字号触底记录：触底 = 内容量超出该版式承载力，是「该拆页/换组合」的信号，不得无声无息 */
const SHRINK_FLOOR_HITS = [];
function modeFloorPt() {
  const m = String((CONTENT && CONTENT.mode) || MODE_NAME || 'presentation');
  const f = FS_POLICY.floorPt[m];
  return f != null ? f : 10;
}
function snapFont(pt, ladder, floor) {
  /* Snap arbitrary pt to nearest ladder step (≥ floor). fitFont + callers (fz-1) must use this. */
  const lad = (ladder || FONT_LADDER).filter(v => v >= (floor == null ? 0 : floor));
  if (!lad.length) return floor == null ? pt : Math.max(floor, pt);
  let best = lad[0], bd = Math.abs(lad[0] - pt);
  for (let i = 1; i < lad.length; i++) {
    const d = Math.abs(lad[i] - pt);
    if (d < bd) { bd = d; best = lad[i]; }
  }
  return best;
}
/* 演讲者备注：模型自带的 speakerNotes 优先；原文锁定（美化路由）时只写原稿备注，不追加生成的口径说明 */
function mergeNotes(own, generated) {
  const g = (generated || '').trim();
  if (own == null || String(own).trim() === '') return g;
  return CONTENT.contentLocked || !g ? String(own) : String(own) + '\n' + g;
}
function fitFont(items, widthIn, availIn, opts) {
  opts = opts || {};
  const floor = opts.floor != null ? opts.floor : modeFloorPt();
  const maxSteps = opts.maxShrinkSteps != null ? opts.maxShrinkSteps : FS_POLICY.maxShrinkSteps;
  const raw = (opts.ladder || FONT_LADDER).filter(v => v <= (opts.max || 99) && v >= floor);
  const lineFactor = opts.lineFactor || TM_LINE;
  const pad = opts.pad || 0;
  const needH = (f, lf) => {
    let h = 0;
    for (const it of items) h += estTextH(it, widthIn, f, lf || lineFactor) + f * (opts.gapFactor || 0.5) / 72;
    return h + pad;
  };
  /* 首选：阶梯中最大且装得下的字号；M12：同一字号先试 1.5 倍行距，再试 1.3 倍（行距先让，字号后让） */
  for (const f of raw) {
    if (needH(f) <= availIn) return f;
    if (lineFactor > LS_MIN && needH(f, LS_MIN) <= availIn) return f;
  }
  /* 全装不下：在 maxShrinkSteps 内从「首选档」下探（首选=opts.max 或阶梯首档） */
  const preferred = raw.length ? raw[0] : floor;
  const prefIdx = (opts.ladder || FONT_LADDER).indexOf(preferred);
  const limited = (opts.ladder || FONT_LADDER)
    .slice(prefIdx, prefIdx + 1 + maxSteps)
    .filter(v => v >= floor && v <= (opts.max || 99));
  for (const f of limited) {
    if (needH(f, LS_MIN) <= availIn) return f;
  }
  /* 仍装不下：取 limited 最小（或 floor），宁可字号偏小也不越界；内容优化由上层负责 */
  const bottom = limited.length ? limited[limited.length - 1] : floor;
  SHRINK_FLOOR_HITS.push({ pt: bottom, sample: String(items[0] == null ? '' : items[0]).slice(0, 24) });
  return bottom;
}
/* 等分并限制下限的列宽 */
function cols(total, n, gap) {
  const w = (total - (n - 1) * (gap || 0)) / Math.max(1, n);
  return { w: w, step: w + (gap || 0) };
}
/* 行高收敛：在 [floor, pref] 内按可用高度取值。
   floor 是绝对硬下限（可低于几何里的软下限），保证条目数超容量时**宁可行高更小也不越界**。 */
function fitRowH(avail, n, pref, floor) {
  const lo = (floor == null) ? 0.22 : floor;
  return Math.max(lo, Math.min(pref, avail / Math.max(1, n)));
}

/* Exhibit 徽标文本：纯编号补 "Exhibit " 前缀（HTML 为 `Exhibit {no}` + CSS uppercase，视觉同 "EXHIBIT 1"）；
   调用方已带前缀的不重复 */
/* M9：Exhibit 行 = 品牌色编号 + 墨色图题（与 HTML .exhibit__no / 图题同构），不再整行品牌色 */
function exhibitRuns(no, cap, size) {
  const base = { fontFace: STYLE.font, fontSize: size, bold: true };
  const r = [{ text: exhibitBadge(no), options: Object.assign({}, base, { color: STYLE.accent, charSpacing: 2 }) }];
  if (cap) r.push({ text: '　' + cap, options: Object.assign({}, base, { color: STYLE.ink }) });
  return r;
}
function exhibitBadge(no) {
  const t = String(no == null ? '' : no).trim();
  if (!t) return t;
  return /^exhibit[\s\-:]*/i.test(t) ? t.toUpperCase() : ('EXHIBIT ' + t.toUpperCase());
}
/* ══════════ 内容模型 ══════════
 * 从 --model=<file.json> 读取（推荐：由 extract_model.py 从 HTML 报告抽取，
 * 保证 PPTX 与页面同源）；未提供时使用下方内嵌 CONTENT 示例。 */
let CONTENT;
if (modelArg) {
  /* 模型读取失败必须显式中断：静默回落内嵌示例会产出一份「看起来正常但内容全错」的 PPTX */
  let raw;
  try {
    raw = fs.readFileSync(modelArg, 'utf-8');
  } catch (e) {
    console.error(`[build_pptx] FAIL: 无法读取模型文件 ${modelArg}：${e && e.message}`);
    console.error('  提示：路径是否正确？模型通常由 python scripts/extract_model.py <报告.html> 生成。');
    process.exit(1);
  }
  try {
    CONTENT = JSON.parse(raw);
  } catch (e) {
    console.error(`[build_pptx] FAIL: 模型不是合法 JSON（${modelArg}）：${e && e.message}`);
    process.exit(1);
  }
  if (!CONTENT || typeof CONTENT !== 'object' || Array.isArray(CONTENT)) {
    console.error(`[build_pptx] FAIL: 模型根节点必须是对象（${modelArg}）。`);
    process.exit(1);
  }
  CONTENT = CHROME.stripFootnotes(CONTENT, CHROME_FLAGS);
  /* M1 容量求解：超载页（条目/字数超过该页型承载力）必须拆成续页，禁止硬塞或静默截断。
     --strict：拒绝出稿并提示先跑 solve_model.js（让 HTML 与 PPTX 同源拆页）；非 strict：自动拆页并告警。 */
  const sp = require('./lib_solver.js').splitModel(CONTENT);
  if (sp.log.length) {
    const desc = sp.log.map(l => `「${l.title}」(${l.type} 容量 ${Math.round(l.ratio * 100)}% → ${l.parts} 页)`).join('、');
    if (process.argv.includes('--strict')) {
      console.error(`[build_pptx] FAIL: 页面超载 ${desc}`);
      console.error(`  请先运行 node scripts/solve_model.js "${modelArg}" --write，再同源渲染 HTML 与 PPTX。`);
      process.exit(4);
    }
    console.warn(`[build_pptx] 警告：页面超载已自动拆页 ${desc}（HTML 端请同步运行 solve_model.js）`);
    CONTENT = sp.model;
  }
  MODEL_DIR = path.dirname(path.resolve(modelArg));   // 素材图片相对路径锚点
  if (CONTENT.style && !styleArg) styleArg = CONTENT.style;   // 模型里的风格作为默认
} else {
  /* 未传 --model：按内嵌示例生成演示 PPTX。必须出声——静默产出会让人误以为是真实报告
     （读模型失败时本脚本选择硬中断，此处同理不得静默）。 */
  console.warn('[build_pptx] 警告：未传 --model=<模型.json>，将按内嵌示例内容生成演示 PPTX（非真实报告内容）。');
  console.warn('  真实交付请先跑 python scripts/extract_model.py <报告.html>，再用 --model=<报告.model.json> 重跑。');
CONTENT = {
  title: '让想法被看见',
  subtitle: 'topmind-presentation 示例 · 16:9 可编辑 PPTX',
  meta: '示例内容 · 请用 --model= 传入真实模型',
  mode: 'presentation',
  style: 'business-blue',
  theme: 'light',
  agenda: [
    ['01', '问题与背景', '为什么现在要谈这件事'],
    ['02', '现状基线', '三组数字勾勒起点'],
    ['03', '方案对比', '两条路径的分野'],
    ['04', '落地路线', '四个季度四步走'],
  ],
  sections: [
    {
      type: 'points',
      eyebrow: '01 · 问题与背景',
      title: '把想法说清楚，比把话说满更重要',
      lead: '一页一个主张，一屏一个结论。',
      points: [
        ['结论前置', '每页标题就是该页最重要的那句话。'],
        ['证据支撑', '数据、图表、案例三选一，不堆砌。'],
        ['细节分层', '放不下的细节沉到图注、来源行与演讲者备注。'],
      ],
      metrics: [['1', '个核心主张/页'], ['29', '种锁定页型']],
    },
    {
      type: 'metrics',
      eyebrow: '02 · 现状基线',
      title: '三组数字勾勒起点',
      lead: '指标带页兼作节奏休止页。',
      metrics: [['62TB', '数据规模'], ['4,662', '入湖表'], ['31%', '使用率'], ['0%', '契约覆盖']],
    },
    {
      type: 'bar',
      eyebrow: '04 · 落地路线',
      title: '可信数据消费率：四个季度四步走',
      chart: { labels: ['2026Q3', 'Q4', '2027Q1', 'Q2'], values: [30, 45, 55, 60], max: 100, unit: '%' },
      note: '口径：被 BI / ChatBI / Agent 调用的可信数据集占比',
    },
    // 更多页型示例见 references/pptx-export.md 的页型表与 references/`components.md` §46 选型速查
  ],
  closing: {
    title: '把「治数据」变成消费飞轮的一部分',
    points: [
      ['指标中心', '统一口径，BI / ChatBI / Agent 共用一套定义'],
      ['数据契约', '上下游变更纳入契约，消费前有 SLA'],
      ['治理 Agent', '清洗 / 校验 / 血缘核验自动化'],
    ],
  },
};
}

THEME = (themeArg === 'dark' || themeArg === 'light') ? themeArg
  : (CONTENT.theme === 'dark' ? 'dark' : 'light');
/* 模型形状早校验：缺 sections/closing 时后面收尾页会以 TypeError 裸崩（堆栈不可读）。
   这里给干净 FAIL（schema 顶层必填：title / sections:array / closing.title / closing.points:array）。 */
if (!Array.isArray(CONTENT.sections) || !CONTENT.sections.length) {
  console.error('[build_pptx] FAIL: 模型缺少 sections 数组（' + (modelArg || '内嵌示例') + '）：无法生成章节页。');
  process.exit(1);
}
if (!CONTENT.closing || typeof CONTENT.closing !== 'object' || Array.isArray(CONTENT.closing)) {
  console.error('[build_pptx] FAIL: 模型缺少 closing 对象（收尾页必填：closing.title / closing.points）。');
  process.exit(1);
}
STYLE = (THEME === 'dark' ? (STYLE_PRESETS_DARK[styleArg] || STYLE_PRESETS[styleArg])
                          : STYLE_PRESETS[styleArg]) || STYLE_PRESETS['business-blue'];
MODE_NAME = CONTENT.mode || 'presentation';
/* M10：风格气质（stylePptx 单源）——标题字族 / 字重 / 标题装饰 / 卡片与表格质感 */
const SP = Object.assign({ display: 'sans', titleBold: true, rule: 'bar', card: 'tonal', table: 'tonal', lineW: 0.75 },
  ((LC.stylePptx || {})[STYLE_PRESETS[styleArg] ? styleArg : 'business-blue']) || {});
const FONT_PAIRS = (LC.stylePptx || {}).fontPairs || {};
STYLE = Object.assign({}, STYLE);
if (SP.display === 'serif' && FONT_PAIRS.serif) STYLE.fontDisplay = FONT_PAIRS.serif.latin;
if (styleArg && !STYLE_PRESETS[styleArg]) {
  console.warn('未知风格 "' + styleArg + '"，回退 business-blue。可选：' + Object.keys(STYLE_PRESETS).join(' / '));
}
if (THEME === 'dark' && styleArg && !STYLE_PRESETS_DARK[styleArg]) {
  console.warn('风格 "' + styleArg + '" 无 dark token，回退该风格 light token（建议补 layout-constants.json stylesDark）。');
}

/* ══════════ 生成 ══════════ */
const pptx = new pptxgen();
pptx.defineLayout({ name: 'W16x9', width: PW, height: PH });
pptx.layout = 'W16x9';
/* M10：语言标记。pptxgenjs 默认每个运行写 lang="en-US"，中文运行在 PowerPoint 里会被当英文做拼写检查、
   断行与中西文间距按西文规则处理。含汉字的运行改写 lang="zh-CN" altLang="en-US"（pptxgenjs 遇 lang 自动补 altLang）。 */
const _HAN = /[\u3400-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef]/;
/* M10：表格质感按风格。首行视为表头。
   zebra 斑马纹 · rule 只留横线（表头下 1pt 墨线）· three-line 三线表（顶/底粗线 + 表头下细线，无填充） */
function tableSkin(rows, opts) {
  const mode = SP.table || 'tonal';
  if (mode === 'tonal' || !Array.isArray(rows) || !rows.length) return [rows, opts];
  const N = { type: 'none' }, hair = { type: 'solid', pt: 0.5, color: STYLE.line };
  const ink = (pt) => ({ type: 'solid', pt, color: STYLE.ink });
  const last = rows.length - 1;
  const out = rows.map((r, ri) => (r || []).map(c => {
    const cell = (c && typeof c === 'object') ? Object.assign({}, c, { options: Object.assign({}, c.options || {}) }) : { text: String(c == null ? '' : c), options: {} };
    const o = cell.options, isHl = o.fill && o.fill.color === STYLE.soft && ri > 0;
    if (mode === 'zebra') {
      if (ri > 0 && !isHl) o.fill = { color: ri % 2 === 0 ? STYLE.surface : STYLE.bg };
      return cell;
    }
    if (ri === 0) { o.fill = { color: STYLE.bg }; o.color = STYLE.ink; o.bold = true; }
    else if (!isHl) o.fill = { color: STYLE.bg };
    if (mode === 'rule') o.border = [N, N, ri === 0 ? ink(1) : hair, N];
    else o.border = [ri === 0 ? ink(1.5) : N, N, ri === 0 ? ink(0.75) : (ri === last ? ink(1.5) : N), N];
    return cell;
  }));
  return [out, Object.assign({}, opts || {}, mode === 'zebra' ? {} : { border: { type: 'none' } })];
}
function _langify(text, opts) {
  if (Array.isArray(text)) return text.map(r => (r && typeof r === 'object' && _HAN.test(String(r.text || '')))
    ? Object.assign({}, r, { options: Object.assign({ lang: 'zh-CN' }, r.options || {}) }) : r);
  return text;
}
{
  const _addSlide = pptx.addSlide.bind(pptx);
  pptx.addSlide = function (...a) {
    const sl = _addSlide(...a);
    const _t = sl.addText.bind(sl), _tb = sl.addTable.bind(sl);
    const _sh = sl.addShape.bind(sl);
    /* M10：卡片质感——色块卡（surface 填充的圆角矩形）按风格改为 outline / hairline */
    sl.addShape = (type, o) => {
      if (type === 'roundRect' && o && o.fill && o.fill.color === STYLE.surface && SP.card !== 'tonal' && !(o.objectName && /^(mini|treemap|boxplot|network|matrix)/.test(o.objectName))) {
        o = Object.assign({}, o, { fill: { color: STYLE.bg }, line: { color: STYLE.line, width: SP.card === 'hairline' ? 0.5 : (SP.lineW || 0.75) } });
      }
      return _sh(type, o);
    };
    sl.addText = (text, opts) => {
      const lf = lineSpacingFor(text, opts);
      if (lf) {
        const fz = Math.max((opts && opts.fontSize) || 0, (_paraTexts(text).maxFz) || 0);
        opts = Object.assign({}, opts, { lineSpacing: Math.round(fz * lf * 10) / 10 });
        LS_STATS[lf === LS_DEF ? 'def' : 'min']++;
      }
      return _t(_langify(text), (typeof text === 'string' && _HAN.test(text)) ? Object.assign({ lang: 'zh-CN' }, opts || {}) : opts);
    };
    sl.addTable = (rows, opts) => { [rows, opts] = tableSkin(rows, opts); return _tb((rows || []).map(r => (r || []).map(c => {
      if (c && typeof c === 'object' && _HAN.test(String(c.text || ''))) return Object.assign({}, c, { options: Object.assign({ lang: 'zh-CN' }, c.options || {}) });
      if (typeof c === 'string' && _HAN.test(c)) return { text: c, options: { lang: 'zh-CN' } };
      return c;
    })), opts); };
    return sl;
  };
}
pptx.title = CONTENT.title || 'topmind-presentation';
pptx.subject = CONTENT.subtitle || '';
pptx.author = 'topmind-presentation';
pptx.company = 'TopMindspace';

function base() {
  const s = pptx.addSlide();
  s.background = { color: STYLE.bg };
  s.addShape('rect', { x: 0, y: 0, w: PW, h: PH, fill: { color: STYLE.bg }, line: { type: 'none' } });
  return s;
}
/* M10：标题下装饰按风格：bar 短条 / bar-thick 粗短条 / long 通栏细线（咨询、学术）/ none（极简） */
function headRule(s, x, y, w) {
  if (SP.rule === 'none') return;
  if (SP.rule === 'long') { s.addShape('rect', { x, y: y + 0.01, w, h: 0.014, fill: { color: STYLE.ink }, line: { type: 'none' }, objectName: 'head:rule' }); return; }
  const thick = SP.rule === 'bar-thick';
  s.addShape('rect', { x, y, w: thick ? 1.2 : 0.9, h: thick ? 0.07 : 0.045, fill: { color: STYLE.accent }, line: { type: 'none' }, objectName: 'head:rule' });
}
/* M13：标题防孤字（lib_dense.balanceTitle 单源）：两行标题在标点 / 词边界平衡断行，数字 + 单位不拆 */
function BT(t, w, pt) { return DENSE.balanceTitle(t, w, pt, TM_ASCII); }
function head(s, eyebrow, title, lead) {
  const H = REGIONS.regionOf('head', 'head') || {
    x: MX, y: PT.common.headEyebrowY, w: CW, h: 0.4,
    titleY: PT.common.headTitleY, ruleY: PT.common.headRuleY, leadY: PT.common.leadY,
  };
  /* M12：眉标默认关闭（showEyebrow 开启才画）；关闭时 applyChrome 已把标题 / 分隔线 / 导语整体上移 */
  if (!CHROME_FLAGS.showEyebrow) eyebrow = '';
  if (eyebrow) s.addText(eyebrow, { x: H.x, y: H.y, w: H.w, h: 0.4, fontFace: STYLE.font,
    fontSize: sz(11), bold: true, color: STYLE.accent, charSpacing: 2 });
  /* 主标题自适应（adaptiveText.title 单源）：先按字符数分档定上限，再按高度验算降一档，避免压到分隔线 */
  const titleH = H.ruleY - H.titleY - 0.06;
  const tMax = titleMaxFor(title);
  const tSize = sz(estTextH(BT(title, H.w, sz(tMax)), CW, sz(tMax), 1.25) > titleH ? Math.min(tMax, AT_TITLE.step1 || 24) : tMax);
  s.addText(BT(title, H.w, tSize), { x: H.x, y: H.titleY, w: H.w, h: Math.max(0.6, titleH),
    fontFace: STYLE.fontDisplay, fontSize: tSize, bold: SP.titleBold !== false, color: STYLE.ink, fit: 'shrink' });
  headRule(s, H.x, H.ruleY, H.w);
  if (lead) s.addText(lead, { x: H.x, y: H.leadY || PT.common.leadY, w: H.w, h: 0.5, fontFace: STYLE.font,
    fontSize: sz(14), color: STYLE.body });
}
/* M12：页脚只留一个克制的页码（不写总页数，封面不标）；pageNumber:false 时不画 */
function footer(s, n, total) {
  if (!CHROME_FLAGS.pageNumber || n === 1) return;
  s.addText(String(n), { x: PW - 1.4, y: LAY.pageNumY != null ? LAY.pageNumY : PH - 0.5,
    w: 0.9, h: 0.3, align: 'right', fontFace: STYLE.font, fontSize: sz(9), color: STYLE.faint, objectName: 'chrome:pageno' });
}
/* so-what 结论条（research 通用可选件，与 HTML .sowhat 同源） */
/* 容器语义名（p:cNvPr@name）：供 validate_pptx 按 containers.pad 分型扣内边距。
   文本框坐标已由引擎 inset，校验器不再对无名 shape 二次扣大 pad。 */
function trName(kind) { return 'tr:' + kind; }
/* 发射前矩形相交断言：组合布局（图表+数据表/图例+标签）在 addShape/addText 前自检，
   发现叠印立刻 console.warn 并计入 OVERLAP_PREEMIT（validate_pptx 的 ELEMENT_OVERLAP 是事后裁判）。 */
function rectsOverlap(a, b, slack) {
  const s = slack != null ? slack : 0.02;
  return (a.x < b.x + b.w - s && b.x < a.x + a.w - s &&
          a.y < b.y + b.h - s && b.y < a.y + a.h - s);
}
const OVERLAP_PREEMIT = [];
function assertNoOverlap(tag, a, b) {
  if (rectsOverlap(a, b)) {
    OVERLAP_PREEMIT.push({ tag, a, b });
    if (typeof console !== 'undefined') {
      console.warn(`[build_pptx] PREEMIT_OVERLAP ${tag}: ` +
        `(${a.x.toFixed(2)},${a.y.toFixed(2)},${a.w.toFixed(2)}×${a.h.toFixed(2)}) ` +
        `∩ (${b.x.toFixed(2)},${b.y.toFixed(2)},${b.w.toFixed(2)}×${b.h.toFixed(2)})`);
    }
    return false;
  }
  return true;
}
/* 双形态载荷判定：[[t,d]…] 数组 vs [{t,d,accent}…] 记录。
   typeof [] === 'object'，绝不能用 typeof 区分——否则数组形态的 t/d 被读成 undefined 静默丢字。 */
function isRec(v) { return !!v && typeof v === 'object' && !Array.isArray(v); }
/* 条目归一化：与 HTML 侧 render_from_model 同口径（数组 | 字典 | 纯字符串）。
   PPTX 分支此前多处只认数组——字典条目会落成 "undefined" 文本，字符串会被按字符切片。
   pointKV: [k,v] | {k|t, v|d} | str（对齐 pts_list）
   metricKV: [v,k] | {v|value, k}（对齐 metrics_row）
   bulletKV: [k,a,t] | {k,a,t}（对齐 r_bullet；缺省保持 undefined 以便调用方判空）
   phaseKV: [label,name,desc,state,icon?] | {label,name,d,s,icon?}（对齐 r_timeline；icon 为变体 timeline 节点图标）
   paraKV: [title,text] | str（对齐 r_twocol；str 为无加粗标题的正文段） */
function pointKV(p) {
  if (Array.isArray(p)) return [String(p[0] == null ? '' : p[0]), String(p[1] == null ? '' : p[1])];
  if (isRec(p)) return [String(p.k || p.t || ''), String(p.v || p.d || '')];
  return ['', String(p == null ? '' : p)];
}
function metricKV(m) {
  if (Array.isArray(m)) return [String(m[0] == null ? '' : m[0]), String(m[1] == null ? '' : m[1])];
  if (isRec(m)) return [String(m.v || m.value || ''), String(m.k || '')];
  return [String(m == null ? '' : m), ''];
}
function bulletKV(it) {
  if (Array.isArray(it)) return [it[0], it[1], it[2]];
  if (isRec(it)) return [it.k || '', it.a, it.t];
  return [String(it == null ? '' : it), undefined, undefined];
}
function phaseKV(ph) {
  // 第 5 元 = icon（变体 timeline 的节点图标；缺省 ''，渲染回落圆点）
  if (Array.isArray(ph)) return [ph[0] || '', ph[1] || '', ph[2] || '', ph[3] || '', ph[4] || ''];
  if (isRec(ph)) return [ph.label || '', ph.name || '', ph.d || '', ph.s || '', ph.icon || ''];
  return [String(ph == null ? '' : ph), '', '', '', ''];
}
function paraKV(p) {
  if (Array.isArray(p)) return [p[0] || '', p[1] || ''];
  if (isRec(p)) return [p.title || '', p.text || p.d || ''];
  return ['', String(p == null ? '' : p)];
}
/* M10：复合 band 页注释带重排（与 HTML 同序：图 → 来源行 → 解读带 → 结论条），每页开头复位 */
let ANNOT = null;
function soWhatBar(s, text) {
  const R = (ANNOT && ANNOT.soWhat) || REGIONS.regionOf('exhibit', 'annotation') ||
    { x: MX, y: PT.exhibit.soWhatY, w: CW, h: 0.62 };
  /* MD3 结论条：tonal soft 满铺 + 舒适字阶；禁止左 accent 装饰轨（anti-AI-flavor） */
  const padX = 0.28, padY = 0.10;
  const bodyW = Math.max(2.5, R.w - padX * 2);
  const fzB = fitFont([String(text || '')], bodyW, R.h - padY * 2, { max: 15, gapFactor: 0.2, maxShrinkSteps: 3 });
  s.addShape('rect', { x: R.x, y: R.y, w: R.w, h: R.h, fill: { color: STYLE.soft }, line: { type: 'none' }, objectName: trName('soWhat') });
  s.addText(String(text || ''), {
    x: R.x + padX, y: R.y + padY, w: R.w - padX * 2, h: R.h - padY * 2,
    fontFace: STYLE.font, fontSize: sz(fzB), bold: true, color: STYLE.ink, valign: 'middle',
    objectName: trName('soWhat'), fit: 'shrink',
  });
}
function footnoteLine(s, text) {
  const R = (ANNOT && ANNOT.foot) || REGIONS.regionOf('exhibit', 'footnote') ||
    { x: MX, y: PT.exhibit.footnoteY, w: CW - 1.2, h: 0.32 };
  s.addText(text, { x: R.x, y: R.y, w: R.w, h: R.h,
    fontFace: STYLE.font, fontSize: sz(9.5), color: STYLE.body, objectName: trName('footnote'), fit: 'shrink' });
}
/* R2：sec.note 与 sec.footnote 共用注释带末行（footnoteY=6.72）。
   note.y=6.55 会压进 so-what 带——同页二者合并为一行。 */
function noteOrFootnote(s, sec) {
  const parts = [];
  if (sec && sec.note) parts.push(String(sec.note));
  if (sec && sec.footnote) parts.push(String(sec.footnote));
  if (!parts.length) return;
  footnoteLine(s, parts.join('　·　'));
}
/* 待核实清单条（accent 强调色标注 · 与 HTML .flagbar 同源）
 * 底对齐 contentBottom，正文区在调用点按 flagH 让位。 */
function flagBar(s, items, yTop) {
  const F = PT.flagbar || { hdH: 0.26, rowH: 0.24, maxRows: 3, gap: 0.12 };
  const list = (items || []).slice(0, F.maxRows).map(String);
  if (!list.length) return 0;
  const h = F.hdH + list.length * F.rowH + 0.06;
  const y = (yTop != null) ? yTop : (CONTENT_BOTTOM - h);
  s.addShape('rect', { x: MX, y, w: CW, h, fill: { color: STYLE.soft }, line: { type: 'none' }, objectName: trName('band') });
  s.addShape('rect', { x: MX, y, w: 0.055, h, fill: { color: STYLE.accent }, line: { type: 'none' } });
  s.addText('待核实 · 需二次确认', { x: MX + 0.22, y: y + 0.02, w: CW - 0.44, h: F.hdH,
    fontFace: STYLE.font, fontSize: sz(9.5), bold: true, color: STYLE.accent, charSpacing: 1, objectName: trName('band') });
  list.forEach((t, i) => {
    s.addText('· ' + t, { x: MX + 0.24, y: y + F.hdH + i * F.rowH, w: CW - 0.5, h: F.rowH,
      fontFace: STYLE.font, fontSize: sz(9.5), color: STYLE.body, valign: 'middle', objectName: trName('band') });
  });
  return h;
}
/* 素材图片 / 配图占位（src 仅允许 data: 内联或相对路径；fit = cover 裁切填满 / contain 完整显示）。
   无图或显式 placeholder 时**不静默跳过**，改画原生占位框（圆角矩形 + 虚线 + 居中标签文本）——
   占位符是原生形状而非图片，pictures 不增，且标签串与 HTML 端逐字一致（cross_verify 逐页比对）。 */
function imgPlaceholderLabel(layout, multi) {
  const label = IMG.placeholderLabel || '配图占位';
  if (multi) return label;
  const size = (IMG.recommendedSizePx || {})[layout];
  if (!size) return label;
  return label + ' · ' + (IMG.placeholderHintPrefix || '建议 ') + size + (IMG.placeholderHintSuffix || 'px');
}
function addImageEl(s, src, x, y, w, h, radius, opts) {
  opts = opts || {};
  const ph = !!opts.placeholder || !src;
  if (ph) {
    s.addShape('roundRect', { x, y, w, h, rectRadius: radius || 0.09,
      fill: { color: STYLE.surface }, line: { color: STYLE.line, width: 1, dashType: 'dash' } });
    s.addText(imgPlaceholderLabel(opts.layout || 'full', !!opts.multi),
      { x: x + 0.08, y: y + h / 2 - 0.22, w: Math.max(0.4, w - 0.16), h: 0.44,
        fontFace: STYLE.font, fontSize: sz(11), bold: true, color: STYLE.faint,
        align: 'center', valign: 'middle' });
    return;
  }
  const fit = String(opts.fit || IMG.fitDefault || 'cover').toLowerCase() === 'contain' ? 'contain' : 'cover';
  const o = { x, y, w, h, sizing: { type: fit, w, h } };
  if (/^data:/i.test(src)) {
    o.data = src;
  } else {
    const resolved = resolveImagePath(src);
    /* 写出阶段才会读盘——路径不存在必须在此拦截，否则 pptxgenjs write 时 ENOENT 中断交付 */
    let exists = false;
    try { exists = fs.existsSync(resolved); } catch (e) { exists = false; }
    if (!exists) {
      console.warn(`[build_pptx] 图片路径不存在，已回落占位框: ${String(src).slice(0, 60)}`);
      addImageEl(s, '', x, y, w, h, radius, { placeholder: true, layout: opts.layout, multi: opts.multi });
      return;
    }
    o.path = resolved;
    /* contain：pptxgenjs 的 sizing.contain 实际会裁切——按图片真实宽高自行等比缩放并居中，不裁一像素 */
    if (fit === 'contain') {
      const dim = imagePixelSize(resolved);
      if (dim) {
        const k = Math.min(w / dim[0], h / dim[1]);
        o.w = dim[0] * k; o.h = dim[1] * k; o.x = x + (w - o.w) / 2; o.y = y + (h - o.h) / 2;
        delete o.sizing;
      }
    }
  }
  /* pptxgenjs 的 rounding 是椭圆遮罩（不是圆角），cover 时会把照片裁成椭圆、丢掉四角内容——M11 起一律不加，保持直角 */
  try { s.addImage(o); }
  catch (e) {
    delete o.rounding;
    try { s.addImage(o); }
    catch (e2) {
      /* 图片不可读（路径失效 / 数据损坏）→ 回落原生占位框，不留空洞、不阻断交付 */
      console.warn(`[build_pptx] 图片不可读，已回落占位框: ${src.slice(0, 60)}`);
      addImageEl(s, '', x, y, w, h, radius, { placeholder: true, layout: opts.layout, multi: opts.multi });
    }
  }
}
/* 读 PNG / JPEG 像素尺寸（只读文件头，不引入依赖）；读不出返回 null */
function imagePixelSize(file) {
  try {
    const b = fs.readFileSync(file);
    if (b.length > 24 && b.readUInt32BE(0) === 0x89504e47) return [b.readUInt32BE(16), b.readUInt32BE(20)];
    if (b[0] === 0xff && b[1] === 0xd8) {
      let i = 2;
      while (i < b.length - 9) {
        if (b[i] !== 0xff) { i++; continue; }
        const m = b[i + 1], len = b.readUInt16BE(i + 2);
        if (m >= 0xc0 && m <= 0xcf && m !== 0xc4 && m !== 0xc8 && m !== 0xcc) return [b.readUInt16BE(i + 7), b.readUInt16BE(i + 5)];
        i += 2 + len;
      }
    }
  } catch (e) { /* ignore */ }
  return null;
}
/* 相对路径解析：pptxgenjs 的 image.path 按 process.cwd() 解析，跨目录调用会失败。
   这里以**模型文件所在目录**为锚（模型与报告同目录，报告里的相对路径即相对该目录），
   再回落到 CWD——保证 `--model=some/dir/x.model.json` 时图片仍能按报告口径找到。 */
function resolveImagePath(src) {
  const raw = String(src || '');
  if (!raw) return raw;
  if (path.isAbsolute(raw)) return raw;
  const cands = [];
  if (MODEL_DIR) cands.push(path.resolve(MODEL_DIR, raw));
  cands.push(path.resolve(process.cwd(), raw));
  for (const c of cands) {
    try { if (fs.existsSync(c)) return c; } catch (e) { /* ignore */ }
  }
  return cands[0] || raw;
}
/* 版式比例（imageSpec.ratioDefault 或 image.ratio，形如 "3:1"）→ 数值宽高比。
   双引擎同源：HTML 用同比例的 .media--r* 锁定类，PPTX 用本函数算高度，版式才一致。 */
function imgRatio(layout, img) {
  const raw = String((img && img.ratio) || (IMG.ratioDefault || {})[layout] || '3:1');
  const m = raw.match(/^\s*(\d+(?:\.\d+)?)\s*[:/×x]\s*(\d+(?:\.\d+)?)/);
  if (!m) return 3;
  const a = parseFloat(m[1]), b = parseFloat(m[2]);
  return (a > 0 && b > 0) ? a / b : 3;
}
/* 图片版式族（与 HTML .media / .media-grid / .media-compare / .media-wall 同源）：
   full 版心全宽｜half 左图右注｜bleed 通栏出血｜grid 多图网格｜compare 双图对比｜wall Logo 墙。
   每版式按 imageSpec.ratioDefault 锁定比例；空间不足时按可用高度收敛并**垂直居中**。
   返回图注基准 Y。占位符走原生形状（pictures 不增）。 */
function imageLayoutShapes(s, layout, img, items, points, isPh, fit, y0, y1) {
  const IM = PT.image || {};
  const gap = IM.gridGap || 0.16;
  const iy = y0;
  const ih = Math.max(1.0, y1 - iy);
  let capY = iy + ih;
  const ratio = imgRatio(layout, img);
  const one = (x, y, w, h, it, multi) => {
    addImageEl(s, (it && it.src) || '', x, y, w, h, IM.radius,
      { placeholder: isPh || !(it && it.src), layout, multi, fit });
  };
  if (layout === 'grid' && items.length) {
    const n = Math.min(items.length, IMG.maxPerPage || 6);
    const colsN = (IM.gridCols || {})[String(n)] || Math.min(3, n);
    const rowsN = Math.max(1, Math.ceil(n / colsN));
    const capH = IM.gridCapH || 0.28;
    const cellW = (CW - (colsN - 1) * gap) / colsN;
    const capRows = rowsN * (capH + 0.04);
    const cellH = Math.min(cellW / ratio, Math.max(0.5, (ih - (rowsN - 1) * gap - capRows) / rowsN));
    const blockH = rowsN * cellH + (rowsN - 1) * gap + capRows;
    const gy = iy + Math.max(0, (ih - blockH) / 2);
    items.slice(0, n).forEach((it, i) => {
      const cx = MX + (i % colsN) * (cellW + gap);
      const cy = gy + Math.floor(i / colsN) * (cellH + gap + capH + 0.04);
      const cap = (it && it.caption) || '';
      one(cx, cy, cellW, cellH, it, true);
      if (cap) s.addText(cap, { x: cx, y: cy + cellH + 0.02, w: cellW, h: capH,
        fontFace: STYLE.font, fontSize: sz(10), color: STYLE.faint, align: 'center' });
    });
    capY = gy + blockH;
  } else if (layout === 'compare' && items.length >= 2) {
    const cgap = IM.compareGap || 0.3;
    const cw2 = (CW - cgap) / 2;
    const capH2 = 0.34;
    const ih2 = Math.min(cw2 / ratio, Math.max(0.5, ih - capH2));
    const cy2 = iy + Math.max(0, (ih - ih2 - capH2) / 2);
    [0, 1].forEach((i) => {
      const it = items[i] || {};
      const cx2 = MX + i * (cw2 + cgap);
      one(cx2, cy2, cw2, ih2, it, true);
      const cap2 = it.caption || '';
      if (cap2) s.addText(cap2, { x: cx2, y: cy2 + ih2 + 0.02, w: cw2, h: 0.3,
        fontFace: STYLE.font, fontSize: sz(10), color: STYLE.faint, align: 'center' });
    });
    capY = cy2 + ih2 + capH2;
  } else if (layout === 'wall' && items.length) {
    const wgap = IM.wallGap || 0.18;
    const wn = Math.min(items.length, 12);
    const rowsW = Math.max(1, Math.min(IM.wallMaxRows || 2, Math.ceil(wn / 6)));
    const perRow = Math.max(1, Math.ceil(wn / rowsW));
    const cellW2 = (CW - (perRow - 1) * wgap) / perRow;
    const cellH2 = Math.min(IM.wallCellH || 0.92, cellW2 / ratio,
      Math.max(0.4, (ih - (rowsW - 1) * wgap) / rowsW));
    const blockH2 = rowsW * cellH2 + (rowsW - 1) * wgap;
    const wy = iy + Math.max(0, (ih - blockH2) / 2);
    items.slice(0, wn).forEach((it, i) => {
      const cx3 = MX + (i % perRow) * (cellW2 + wgap);
      const cy3 = wy + Math.floor(i / perRow) * (cellH2 + wgap);
      one(cx3, cy3, cellW2, cellH2, it, true);
    });
    capY = wy + blockH2;
  } else if (layout === 'half') {
    const iw = CW * (IM.halfW || 0.56);
    const ihh = Math.min(iw / ratio, ih);
    one(MX, iy, iw, ihh, img, false);
    const rxI = MX + iw + CW * (IM.halfGap || 0.06);
    const rwI = CW - iw - CW * (IM.halfGap || 0.06);
    const ptsI = (points || []).filter(Boolean).map(pointKV);  // M11：纯字符串要点此前被按字符拆成「标题 / 正文」
    const rowHI = fitRowH(ih - 0.1, ptsI.length, IM.noteRowH || 0.62, 0.3);
    const fzI = fitFont(ptsI.map(p => (p[0] || '') + (p[1] || '')), rwI - 0.3, ih, { max: 14, gapFactor: 0.6 });
    const fz = sz(fzI), fzSm = sz(snapFont(fzI - 1));
    ptsI.forEach((pt, i) => {
      const lyI = iy + i * rowHI;
      s.addShape('rect', { x: rxI, y: lyI + rowHI / 2 - 0.06, w: 0.12, h: 0.12,
        fill: { color: STYLE.accent }, line: { type: 'none' } });
      s.addText([
        { text: pt[0] ? pt[0] + '　' : '', options: { fontSize: fz, bold: true, color: STYLE.ink } },
        { text: pt[1] || '', options: { fontSize: pt[0] ? fzSm : fz, color: pt[0] ? STYLE.body : STYLE.ink } },
      ], { x: rxI + 0.26, y: lyI, w: rwI - 0.3, h: rowHI - 0.04, fontFace: STYLE.font, valign: 'top' });
    });
    capY = iy + Math.max(ihh, ih * 0.5);
  } else if (layout === 'bleed') {
    const bh = Math.min(ih, PW / ratio);
    const by = iy + Math.max(0, (ih - bh) / 2);
    one(0, by, PW, bh, img, false);
    capY = by + bh;
  } else {
    /* full：图在上、要点在下（HTML half 版式有「图+注」，full 无注；B 通道补齐要点以过保真门禁） */
    const ptsF = (points || []).filter(Boolean);
    const pfRowH = 0.5;
    const pfH = ptsF.length ? Math.min(ptsF.length * pfRowH, Math.max(0, ih - 1.8)) : 0;
    const fh = Math.max(1.0, Math.min(ih - pfH, CW / ratio));
    const fy = iy + Math.max(0, (ih - pfH - fh) / 2);
    one(MX, fy, CW, fh, img, false);
    const pfCap = Math.max(0, Math.floor(pfH / pfRowH));
    ptsF.slice(0, pfCap).forEach((pt, i) => {
      const kk = Array.isArray(pt) ? String(pt[0] || '') : String((pt && pt.t) || '');
      const vv = Array.isArray(pt) ? String(pt[1] || '')
        : (pt && typeof pt === 'object' ? String(pt.d || '') : String(pt == null ? '' : pt));
      const ly = fy + fh + 0.08 + i * pfRowH;
      s.addShape('rect', { x: MX, y: ly + pfRowH / 2 - 0.06, w: 0.12, h: 0.12,
        fill: { color: STYLE.accent }, line: { type: 'none' } });
      s.addText([
        { text: kk + (kk && vv ? '　' : ''), options: { fontSize: sz(12), bold: true, color: STYLE.ink } },
        { text: vv, options: { fontSize: sz(11), color: STYLE.body } },
      ], { x: MX + 0.26, y: ly, w: CW - 0.32, h: pfRowH - 0.04,
        fontFace: STYLE.font, valign: 'middle' });
    });
    capY = fy + fh + pfH;
  }
  return capY;
}
/* 数据图表上下文（供备注与自适应使用） */
function chartBottom(hasSoWhat, hasFootnote) {
  /* 取最紧下界：so-what / footnote / contentBottomWithNote 并存时不得短路（D8）。
   * 与 ~1630 flagY 的 Math.min 让位同口径；withNote 时对齐 regionOf 的 contentBottomWithNote。 */
  let bot = CONTENT_BOTTOM;
  if (hasSoWhat) bot = Math.min(bot, PT.exhibit.soWhatY - 0.20);
  if (hasFootnote) bot = Math.min(bot, PT.exhibit.footnoteY - 0.12);
  if (hasSoWhat || hasFootnote) bot = Math.min(bot, CONTENT_BOTTOM_NOTE);
  /* 无注释页：图形框（原生图表 / 形状）也不贴到版心底——留 0.25in 呼吸，避免压进注释带安全网 */
  else bot = Math.min(bot, CONTENT_BOTTOM_NOTE + 0.25);
  return bot;
}

/* ═══ 原生数据图表（pptxgenjs addChart → 真 chart part + 内嵌 Excel 工作簿）═══
 * PowerPoint / WPS 中双击图表即可"编辑数据"——带数据的图表一律走此通道，不再用形状拼图。
 * 几何取自 layout-constants 页型几何；单系列按数据点着色（峰值 accent、其余中性）。
 * chart.type: bar（默认竖柱）/ hbar（横条）/ line / dualline / area / stack / donut
 * chart.series（可选）：[{name, values}…] 多系列（dualline / stack 用） */
function chartSeries(c) {
  const labels = (c.labels || []).map(String);
  /* 非数值警告：Number('x') → NaN 会导致图表数据为空；提醒用户检查模型（不中断构建） */
  const warnBad = (vals, where) => {
    const bad = (vals || []).filter(v => typeof v !== 'number' || !isFinite(v));
    if (bad.length) console.warn(`[build_pptx] 警告：${where} 含 ${bad.length} 个非数值（${JSON.stringify(bad.slice(0, 3))}），图表该系列数据将为空`);
  };
  if (Array.isArray(c.series) && c.series.length) {
    return c.series.map((se, i) => {
      warnBad(se.values, `series[${i}]${se.name ? '(' + se.name + ')' : ''}`);
      return {
        name: se.name || ('系列' + (i + 1)),
        labels: labels,
        values: (se.values || []).map(Number),
      };
    });
  }
  warnBad(c.values, 'chart.values');
  return [{ name: '数值', labels: labels, values: (c.values || []).map(Number) }];
}
/* ══ 图表登记（单源 scripts/layout-constants.json · charts.registry）══
 * type → { pptx: 'native'|'shape', nativeType, nativeTrick, dataTable }
 * 原生通道：pptxgenjs addChart（真 chart part + 内嵌 Excel 工作簿，双击可编辑数据）
 * 形状通道：shapeChart()（高保真形状还原 + 按 dataTable 策略附数据表，保证数据可追溯） */
const CHART_REG = (LC.charts && LC.charts.registry) || {};
function chartReg(t) { return CHART_REG[String(t || 'bar').toLowerCase()] || CHART_REG.bar || {}; }
function isNativeChart(t) { return chartReg(t).pptx === 'native'; }
/* 数据表策略：图表级覆盖 > 登记表默认（appendix 收敛为页内表格，保持页数稳定） */
function dataTableMode(c) {
  const m = (c && c.dataTable) || chartReg(c && c.type).dataTable || 'notes';
  return m === 'appendix' ? 'inline' : m;
}
function dataTableRows(c) {
  const labels = (c.labels || []).map(String);
  const unit = c.unit ? '（' + c.unit + '）' : '';
  if (Array.isArray(c.series) && c.series.length) {
    return [['项目'].concat(c.series.map((se, i) => se.name || ('系列' + (i + 1))))]
      .concat(labels.map((lb, i) => [lb].concat(c.series.map(se => {
        const v = (se.values || [])[i]; return v == null ? '' : String(v);
      }))));
  }
  return [['项目', '数值' + unit]]
    .concat(labels.map((lb, i) => { const v = (c.values || [])[i]; return [lb, v == null ? '' : String(v)]; }));
}
function dataTableText(c) { return dataTableRows(c).map(r => r.join(' | ')).join('\n'); }

/* 原生图表基础选项（位置由调用点附加） */
/* 数据标签小数位：按模型数值实际小数位（上限 2 位）生成 format code。
   原 '0"单位"' 会把 1.2 显示成 1（像素级数值失真）；无单位且无小数时保持 General。 */
function chartDecimals(c) {
  let d = 0;
  const scan = (v) => {
    if (typeof v === 'number' && isFinite(v)) {
      const s = String(v), i = s.indexOf('.');
      if (i >= 0) d = Math.max(d, Math.min(2, s.length - i - 1));
    }
  };
  (c.values || []).forEach(scan);
  (c.series || []).forEach(se => (se.values || []).forEach(scan));
  (c.points || []).forEach(p => { if (Array.isArray(p)) p.forEach(scan); else scan(p); });
  (c.start || []).forEach(scan); (c.target || []).forEach(scan);
  return d;
}
function chartBaseOpts(c, colors, multi, kind) {
  const isLine = (kind === 'line' || kind === 'area');
  const _dec = chartDecimals(c), _ds = _dec ? '.' + '0'.repeat(_dec) : '';
  const opts = {
    /* 分组柱点数不多（≤12）时也标数值——值轴隐藏，不标数就读不出数（与 HTML grouped() 一致） */
    showValue: !isLine && (!multi || (c.series || []).reduce((n, se) => n + (se.values || []).length, 0) <= 12),
    dataLabelPosition: 'outEnd',
    dataLabelColor: STYLE.body, dataLabelFontSize: sz(11.5), dataLabelFontFace: STYLE.font,
    dataLabelFormatCode: c.unit ? '0' + _ds + '"' + c.unit + '"' : (_dec ? '0' + _ds : 'General'),
    catAxisLabelColor: STYLE.faint, catAxisLabelFontSize: sz(10.5), catAxisLabelFontFace: STYLE.font,
    valAxisHidden: true, valAxisLineShow: false, catAxisLineShow: false,
    catGridLine: { style: 'none' }, valGridLine: { style: 'none' },
    valAxisMinVal: 0,
    showLegend: !!multi, legendPos: 'b', legendColor: STYLE.body,
    legendFontSize: sz(10.5), legendFontFace: STYLE.font,
    showTitle: false,
  };
  if (c._mini) {   /* M7 小图组（small multiples）：字号降一档，保证 1in 高的小图可读 */
    opts.dataLabelFontSize = sz(9); opts.catAxisLabelFontSize = sz(9);
    opts.dataLabelFormatCode = _dec ? '0' + _ds : '0';   // 单位写在小图标题里，标签只留数字（避免折行）
    const vs = (c.values || []).filter(v => typeof v === 'number');
    if (!c.max && vs.length) opts.valAxisMaxVal = Math.max.apply(null, vs) * 1.18;
  }
  if (colors) opts.chartColors = colors;
  if (c.max) opts.valAxisMaxVal = c.max;
  return opts;
}
/* addChart 失败即失败：禁止静默回落为柱状图（会造成「过了 strict 但图表类型假象」）。
 * 严格解析/第三方裁判可暴露该失败；交付通道必须诚实报错。 */
function chartTry(s, ctype, data, opts, c) {
  try { s.addChart(ctype, data, opts); }
  catch (e) {
    console.error(`[build_pptx] FAIL: 原生图表 ${ctype} 调用失败（禁止回落）: ${e && e.message}`);
    process.exitCode = 1;
    throw e;
  }
}
function chartSkin() {
  const G = (LC.styleGrammar && LC.styleGrammar.styles) || {};
  return ((G[styleArg] || G[(LC.styleGrammar || {}).default] || {}).chartSkin) || {};
}
/* 标注层工具：高亮下标（显式 highlight 注记 / chart.highlight；未声明 = 不高亮，单系列统一主色） */
function annHighlight(c, ann) {
  const labels = (c.labels || []).map(String), n = labels.length, out = [];
  ann.filter(a => a.type === 'highlight').forEach(a => {
    if (Number.isInteger(a.index) && a.index >= 0 && a.index < n) out.push(a.index);
    else if (a.label != null && labels.indexOf(String(a.label)) >= 0) out.push(labels.indexOf(String(a.label)));
  });
  if (!out.length && Number.isInteger(c.highlight)) out.push(c.highlight);
  return out;
}
function mixHex(a, b, t) {
  const pa = [0, 2, 4].map(i => parseInt(String(a).slice(i, i + 2), 16));
  const pb = [0, 2, 4].map(i => parseInt(String(b).slice(i, i + 2), 16));
  return pa.map((v, i) => Math.round(v * (1 - t) + pb[i] * t).toString(16).padStart(2, '0')).join('').toUpperCase();
}
/* 原生数据图表（pptxgenjs 原生 10 类 + 3 类原生技巧：waterfall / gauge / pareto） */
function nativeChart(s, c, x, y, w, h, dcols) {
  const t = String(c.type || 'bar').toLowerCase();
  const reg = chartReg(t);
  const kind = reg.nativeType || 'bar';
  const trick = reg.nativeTrick || '';
  const vals = (c.values || []).map(Number);
  const top = vals.length ? Math.max.apply(null, vals) : 0;
  const multi = Array.isArray(c.series) && c.series.length > 0;
  const colors = (dcols && dcols.length) ? dcols
    : (multi ? null : vals.map(v => (v === top ? STYLE.accent : STYLE.faint)));
  const pos = { x: x, y: y, w: w, h: h };
  /* M0：单系列图表（柱/条/线/面积）统一主色——按数据点轮换色板会出现「彩虹柱」，违反克制原则。
     多系列仍取风格编码色板；显式 chart.colors 尊重作者。饼/环按类目编码，不受此限。 */
  const singleSeriesMono = !multi && !(c.colors && c.colors.length) && kind !== 'doughnut' && kind !== 'pie';
  let colorsEff = singleSeriesMono ? [STYLE.accent] : colors;
  /* M3 标注层（chart.annotations[] / chart.dataLabels）——与 HTML lib_chart_svg 同语义：
     highlight：被强调项主色实底、其余主色色调（单系列不再按序号轮换颜色）；
     target：原生组合图里的虚线目标系列（可编辑数据）；dataLabels:none 关闭数据标签。 */
  const ann = Array.isArray(c.annotations) ? c.annotations.filter(a => a && typeof a === 'object') : [];
  const hlIdx = annHighlight(c, ann);
  if (singleSeriesMono && hlIdx.length && (kind === 'bar')) {
    const tone = mixHex(STYLE.accent, STYLE.bg, 0.55);
    colorsEff = vals.map((_, i) => (hlIdx.indexOf(i) >= 0 ? STYLE.accent : tone));
  }

  /* ── 原生技巧 ── */
  if (trick.indexOf('stacked+hiddenBase') === 0) { waterfallChart(s, c, pos); return; }
  if (trick.indexOf('doughnut+firstSliceAng') === 0) { gaugeChart(s, c, pos); return; }
  if (trick.indexOf('multiType') === 0) { paretoChart(s, c, pos); return; }
  if (trick.indexOf('rows:') === 0) { rowsNativeChart(s, c, pos, trick.slice(5)); return; }

  /* ── 饼 / 环 ── */
  if (kind === 'doughnut' || kind === 'pie') {
    const opts = Object.assign(chartBaseOpts(c, colors || donutColors(styleArg), false, kind), pos, {
      /* M7：值与百分比二选一（此前同时显示，标签成「70 / 1%」两行乱码）——单位为 % 时只显示值 */
      showValue: String(c.unit || '') === '%', dataLabelPosition: 'ctr',
      dataLabelColor: STYLE.onAccent, showPercent: String(c.unit || '') !== '%',
      showLegend: true, legendPos: 'r',
      dataBorder: { pt: 1.5, color: STYLE.bg },
    });
    if (kind === 'doughnut') opts.holeSize = 55;
    chartTry(s, kind === 'pie' ? pptx.ChartType.pie : pptx.ChartType.doughnut, chartSeries(c), opts, c);
    return;
  }
  /* ── 散点 / 气泡（XY 型） ── */
  if (kind === 'scatter' || kind === 'bubble') { xyChart(s, c, pos, kind, colors); return; }
  /* ── 雷达 ── */
  if (kind === 'radar') {
    const opts = Object.assign(chartBaseOpts(c, colors, multi, kind), pos, {
      radarStyle: 'marker', valAxisHidden: false, valAxisLineShow: true, catAxisLineShow: true,
      valGridLine: { style: 'solid', color: STYLE.line }, showValue: false,
    });
    chartTry(s, pptx.ChartType.radar, chartSeries(c), opts, c);
    return;
  }
  /* ── 柱族（bar / hbar / stack / stackline）与线 / 面积 ── */
  const opts = Object.assign(chartBaseOpts(c, colorsEff, multi, kind), pos);
  /* 浅色数值网格线：给读数参照，也避免量程留白显得「图浮在半空」 */
  /* M3 风格库 chartSkin：网格线开关 / 数据标签策略随风格（HTML lib_chart_svg 同一份皮肤） */
  const skin = chartSkin();
  if ((kind === 'bar' || kind === 'line' || kind === 'area') && skin.grid !== false && !c._mini)
    opts.valGridLine = { style: 'solid', color: STYLE.line, size: 0.5 };
  if (kind === 'bar') {
    opts.barDir = (t === 'hbar') ? 'bar' : 'col';
    opts.barGapWidthPct = (t === 'hbar') ? 45 : 55;
    if (t === 'stack') { opts.barGrouping = 'stacked'; opts.showValue = false; }
    if (t === 'stackline') { opts.barGrouping = 'percentStacked'; opts.showValue = false; }
  }
  if (kind === 'line' || kind === 'area') {
    opts.lineSize = 2.5; opts.lineSmooth = false;
    opts.lineDataSymbol = 'circle'; opts.lineDataSymbolSize = 6;
  }
  const ctype = kind === 'line' ? pptx.ChartType.line
    : kind === 'area' ? pptx.ChartType.area : pptx.ChartType.bar;
  if (String(c.dataLabels || skin.dataLabels || '').toLowerCase() === 'none') opts.showValue = false;
  if (!multi && singleSeriesMono && hlIdx.length && kind === 'bar') opts.chartColors = colorsEff;
  let cdata = chartSeries(c);
  const targets = ann.filter(a => a.type === 'target' && isFinite(Number(a.value)));
  if (targets.length && t === 'bar' && !multi) {
    const labels = (c.labels || []).map(String);
    const tv = Number(targets[0].value);
    if (!c.max) opts.valAxisMaxVal = undefined;
    try {
      s.addChart([
        { type: pptx.ChartType.bar, data: cdata, options: Object.assign({}, opts, { barDir: 'col' }) },
        { type: pptx.ChartType.line, data: [{ name: (/\d/.test(String(targets[0].label || '')) ? String(targets[0].label) : (targets[0].label || '目标') + ' ' + tv + (c.unit || '')),
            labels: labels, values: labels.map(() => tv) }],
          options: { lineSize: 1.75, lineDash: 'dash', lineDataSymbol: 'none', chartColors: [STYLE.accent], showValue: false } },
      ], Object.assign({}, opts, pos, { showLegend: true, legendPos: 't', legendColor: STYLE.body }));
    } catch (e) { chartTry(s, ctype, cdata, opts, c); }
    return;
  }
  if (t === 'hbar') {
    /* 条形图（barDir=bar）类目轴自下而上绘制：反转数据使首项居顶，
       与 HTML svg-hbar 及 HTML 端 hbarRows 同序（标签-数值配对不变） */
    cdata = cdata.map(se => ({ name: se.name,
      labels: (se.labels || []).slice().reverse(), values: (se.values || []).slice().reverse() }));
    /* 单系列：颜色跟随数据点一起反转（高亮项仍落在原数据项上）；未高亮 = 统一主色 */
    if (!multi && colorsEff && colorsEff.length > 1) {
      const _n = Math.max(1, (cdata[0].values || []).length);
      opts.chartColors = (cdata[0].values || []).map((_, i) => colorsEff[(_n - 1 - i) % colorsEff.length]);
    }
  }
  chartTry(s, ctype, cdata, opts, c);
}
/* 散点（X/Y 双系列）/ 气泡（{x,y,w} 单系列）；labels 解析为 x，values 为 y */
function xyChart(s, c, pos, kind, colors) {
  const labels = (c.labels || []);
  const vals = (c.values || []).map(Number);
  const pts = Array.isArray(c.points) ? c.points : null;
  const opts = Object.assign(chartBaseOpts(c, colors, false, kind), pos, {
    showValue: false, showLegend: false,
    valAxisHidden: false, valAxisLineShow: true, catAxisLineShow: true,
    catGridLine: { style: 'solid', color: STYLE.line }, valGridLine: { style: 'solid', color: STYLE.line },
  });
  try {
    if (kind === 'bubble') {
      const raw = pts ? pts : labels.map((lb, i) => [i + 1, vals[i], 1]);
      const data = [{ name: c.unit || '规模',
        values: raw.map(p => ({ x: Number(p[0]) || 0, y: Number(p[1]) || 0, w: Number(p[2]) || 1 })) }];
      s.addChart(pptx.ChartType.bubble, data, opts);
    } else {
      const xs = pts ? pts.map(p => Number(p[0]) || 0)
        : labels.map(lb => { const n = parseFloat(String(lb).replace(/[^\d.\-]/g, '')); return isNaN(n) ? 0 : n; });
      const ys = pts ? pts.map(p => Number(p[1]) || 0) : vals;
      s.addChart(pptx.ChartType.scatter, [{ name: 'X', values: xs }, { name: 'Y', values: ys }], opts);
    }
  } catch (e) {
    console.error(`[build_pptx] FAIL: 原生 ${kind} 调用失败（禁止回落 bar）: ${e && e.message}`);
    process.exitCode = 1;
    throw e;
  }
}
/* 瀑布图（原生技巧）：隐藏基底 + 增减堆叠柱，叠加累计折线作连接线 */
/* M2：行式图表改原生可编辑（横向条形图 + 隐形基底技巧），替代原形状拼图。
 *   gantt    ：基底 = 起点（隐形）+ 时长；数值轴 = 时间刻度
 *   progress ：完成值 + 剩余轨道（surface 色）堆叠到 max（默认 100）
 *   funnel   ：两侧对称隐形基底 + 值，居中成漏斗
 *   vsbar    ：簇状条形，负值向左、正值向右（0 轴居中）
 * 数值并入类目标签（「标签 · 值」），PowerPoint/WPS 里双击即可改数据。 */
function rowsNativeChart(s, c, pos, kind) {
  const labels = (c.labels || []).map(String);
  const vals = (c.values || []).map(v => Number(v) || 0);
  const u = c.unit || '';
  const fmt = (v) => (Math.round(v * 10) / 10) + u;
  let series, colors, extra = {};
  if (kind === 'gantt') {
    const st = labels.map((_, i) => (c.start && Number(c.start[i])) || 0);
    const span = Number(c.max) || Math.max(1, ...st.map((v, i) => v + vals[i]));
    const cats = labels.map((lb, i) => lb + ' · ' + fmt(vals[i]));
    series = [{ name: '起点', labels: cats, values: st }, { name: '时长', labels: cats, values: vals }];
    colors = [STYLE.bg, STYLE.accent];
    extra = { valAxisHidden: false, valAxisMaxVal: span, valAxisMinVal: 0,
      valGridLine: { style: 'solid', color: STYLE.line, size: 0.5 },
      valAxisLabelColor: STYLE.faint, valAxisLabelFontSize: sz(9.5) };
  } else if (kind === 'progress') {
    const mx = Number(c.max) || 100;
    const cats = labels.map((lb, i) => lb + ' · ' + fmt(vals[i]));
    series = [{ name: '完成', labels: cats, values: vals }, { name: '剩余', labels: cats, values: vals.map(v => Math.max(0, mx - v)) }];
    colors = [STYLE.accent, STYLE.surface];
    extra = { valAxisMaxVal: mx, valAxisMinVal: 0 };
  } else if (kind === 'funnel') {
    const vmax = Math.max(1, ...vals);
    const cats = labels.map((lb, i) => lb + ' · ' + fmt(vals[i]));
    const pad = vals.map(v => (vmax - v) / 2);
    series = [{ name: '左', labels: cats, values: pad }, { name: '值', labels: cats, values: vals }, { name: '右', labels: cats, values: pad }];
    colors = [STYLE.bg, STYLE.accent, STYLE.bg];
    extra = { valAxisMaxVal: vmax, valAxisMinVal: 0 };
  } else {
    const cats = labels.map((lb, i) => lb + ' · ' + fmt(vals[i]));
    series = [{ name: c.name || '差值', labels: cats, values: vals }];
    colors = [STYLE.accent];
    extra = { barGrouping: 'clustered', invertIfNegative: false, catAxisLabelPos: 'low',
      valGridLine: { style: 'solid', color: STYLE.line, size: 0.5 } };
  }
  const opts = Object.assign({
    barDir: 'bar', barGrouping: 'stacked', barGapWidthPct: kind === 'funnel' ? 12 : 55,
    showValue: false, showLegend: false, showTitle: false,
    chartColors: colors, catAxisOrientation: 'maxMin',
    catAxisLabelColor: STYLE.body, catAxisLabelFontSize: sz(11), catAxisLabelFontFace: STYLE.font,
    catAxisLineShow: false, valAxisHidden: true, valAxisLineShow: false,
    catGridLine: { style: 'none' }, valGridLine: { style: 'none' },
  }, extra, pos);
  chartTry(s, pptx.ChartType.bar, series, opts, c);
}
function waterfallChart(s, c, pos) {
  const labels = (c.labels || []).map(String);
  const deltas = (c.values || []).map(Number);
  let run = 0;
  const bases = [], ups = [], downs = [], cum = [], tots = [];
  /* 末项等于前项之和 → 视为「合计柱」（从 0 起），否则会被当增量累加、整图失真 */
  const sumPrev = deltas.slice(0, -1).reduce((a, b) => a + b, 0);
  const lastIsTotal = deltas.length > 2 && Math.abs(deltas[deltas.length - 1] - sumPrev) < 1e-6;
  deltas.forEach((d, i) => {
    /* M10：首柱（基线）与末项合计柱单列「合计」系列——与 HTML f-acc 实色一致；中间增量走品牌浅调（f-accs2），减量走 --neg */
    if (lastIsTotal && i === deltas.length - 1) { bases.push(0); tots.push(d); ups.push(0); downs.push(0); cum.push(d); return; }
    if (i === 0 && d >= 0) { bases.push(0); tots.push(d); ups.push(0); downs.push(0); run += d; cum.push(run); return; }
    const b = d >= 0 ? run : run + d;
    bases.push(b); tots.push(0); ups.push(d >= 0 ? d : 0); downs.push(d < 0 ? -d : 0);
    run += d; cum.push(run);
  });
  const series = [
    { name: '基底', labels: labels, values: bases },
    { name: '合计', labels: labels, values: tots },
    { name: '增量', labels: labels, values: ups },
    { name: '减量', labels: labels, values: downs },
  ];
  const NEG = STYLE.neg || (THEME === 'dark' ? 'F28B82' : 'C5221F');
  const inner = {
    barDir: 'col', barGrouping: 'stacked', showValue: false, showLegend: false,
    chartColors: [STYLE.bg, STYLE.accent, mixHex(STYLE.soft, STYLE.accent, 0.22), NEG],
    catAxisLabelColor: STYLE.faint, catAxisLabelFontSize: sz(10.5), catAxisLabelFontFace: STYLE.font,
    valAxisHidden: true, valAxisLineShow: false, catAxisLineShow: false,
    catGridLine: { style: 'none' }, valGridLine: { style: 'none' }, valAxisMinVal: 0, showTitle: false,
  };
  const outer = Object.assign({}, inner, pos);
  /* M1：去掉累计折线叠加（组合图在 LibreOffice/WPS 下坐标轴错位，首柱被画成负向）；
     纯堆叠柱 + 隐形基底即标准瀑布，数值标签由下方文本行给出 */
  try {
    const n = labels.length;
    const vmax = Math.ceil(Math.max(1e-9, ...cum, ...bases.map((b, i) => b + tots[i] + ups[i] + downs[i])) * 1.12);
    outer.valAxisMaxVal = vmax;
    s.addChart(pptx.ChartType.bar, series, outer);
    const plotTop = pos.y + 0.12, plotH = pos.h - 0.55;
    labels.forEach((lb, i) => {
      const top = bases[i] + tots[i] + ups[i] + downs[i];
      const cw = pos.w / n;
      const ty = plotTop + plotH * (1 - top / vmax) - 0.3;
      const d = deltas[i];
      const isTot = (lastIsTotal && i === n - 1) || i === 0;
      s.addText((isTot || d < 0 ? '' : '+') + d + (c.unit || ''), { x: pos.x + cw * i, y: Math.max(pos.y - 0.1, ty), w: cw, h: 0.26,
        align: 'center', fontFace: STYLE.font, fontSize: sz(10.5), bold: true, color: STYLE.ink });  // M10：与 HTML 同为墨色 600，正负靠柱色区分
    });
  } catch (e) {
    /* 组合图失败：单柱降级必须可观测，禁止静默空白 */
    console.error(`[build_pptx] WARN: waterfall 组合图失败，降级为堆叠柱: ${e && e.message}`);
    try {
      s.addChart(pptx.ChartType.bar, series, outer);
    } catch (e2) {
      console.error(`[build_pptx] FAIL: waterfall 降级柱图仍失败: ${e2 && e2.message}`);
      process.exitCode = 1;
      throw e2;
    }
  }
}
/* 仪表盘（原生技巧）：270° 扇形环，剩余扇区以底色隐藏 */
function gaugeChart(s, c, pos) {
  const v = Number((c.values || [0])[0]) || 0;
  const max = Number(c.max) || 100;
  const ratio = Math.max(0, Math.min(1, v / max));
  const sweep = ratio * 270;
  /* 类别标签用数值（达成值 / 剩余值）——cross_verify 按纯数值 token 过滤，A/B 文本集合一致 */
  const _u = c.unit || '';
  try {
    s.addChart(pptx.ChartType.doughnut,
      [{ name: '达成', labels: [String(v) + _u, String(Math.max(0, max - v)) + _u], values: [sweep, 360 - sweep] }],
      Object.assign({}, pos, {
        holeSize: 68, firstSliceAng: 225,
        chartColors: [STYLE.accent, STYLE.surface],
        dataBorder: { pt: 1, color: STYLE.bg },
        showLegend: false, showValue: false, showPercent: false, showTitle: false,
      }));
  } catch (e) {
    console.error(`[build_pptx] FAIL: 原生 gauge 调用失败（禁止静默）: ${e && e.message}`);
    process.exitCode = 1;
    throw e;
  }
}
/* 帕累托（原生技巧）：柱（数值）+ 折线（累计占比），多类型组合 */
function paretoChart(s, c, pos) {
  const labels = (c.labels || []).map(String);
  const vals = (c.values || []).map(Number);
  const total = vals.reduce((a, b) => a + b, 0) || 1;
  let run = 0;
  const cum = vals.map(v => { run += v; return Math.round(run / total * 1000) / 10; });
  const barOpts = {
    barDir: 'col', showValue: false, showLegend: true, legendPos: 'b',
    chartColors: [STYLE.accent],
    catAxisLabelColor: STYLE.faint, catAxisLabelFontSize: sz(10.5), catAxisLabelFontFace: STYLE.font,
    valAxisHidden: true, valAxisLineShow: false, catAxisLineShow: false,
    catGridLine: { style: 'none' }, valGridLine: { style: 'none' }, valAxisMinVal: 0, showTitle: false,
  };
  try {
    s.addChart([
      { type: pptx.ChartType.bar,
        data: [{ name: c.unit ? '数值（' + c.unit + '）' : '数值', labels: labels, values: vals }], options: barOpts },
      { type: pptx.ChartType.line, data: [{ name: '累计占比', labels: labels, values: cum }],
        options: { lineSize: 2, lineSmooth: false, lineDataSymbol: 'circle', lineDataSymbolSize: 6, chartColors: [STYLE.body] } },
    ], Object.assign({}, barOpts, pos));
  } catch (e) { chartTry(s, pptx.ChartType.bar, chartSeries(c), Object.assign({}, barOpts, pos), c); }
}
function nativeDonutChart(s, dcn, dcols, bottomY, topY) {
  const d = PT.donut;
  /* 有结论条/脚注时压半径，避免环图底边压进 soWhatY（D11）。
     M1：给出 topY 时按版心求解——圆心取版心垂直中点，半径撑满（上限 2.1in），不再固定 1.6in 下沉 */
  let r = d.r;
  let cy = d.centerY;
  if (topY != null && bottomY != null) {
    cy = (topY + bottomY) / 2;
    r = Math.max(0.9, Math.min(2.1, (bottomY - topY) / 2 - 0.06));
  } else if (bottomY != null && cy + r > bottomY) {
    r = Math.max(0.9, bottomY - cy - 0.04);
  }
  d._cy = cy;
  s.addChart(pptx.ChartType.doughnut, chartSeries(dcn), {
    x: d.centerX - r, y: cy - r, w: r * 2, h: r * 2,
    holeSize: Math.round((d.holeR / d.r) * 100),
    chartColors: dcols,
    showLegend: false, showValue: false, showPercent: false, showTitle: false,
    dataBorder: { pt: 1.5, color: STYLE.bg },
  });
  return r;
}
/* ═══ 形状通道图表（非原生类型的高保真形状还原）═══
 * 与 HTML 端（assets/pptx-export.js 的 chartShapes）语义一致：类别标签与数值都落为文本，
 * 保证 cross_verify 逐页文本集合一致（数值 token 由 cross_verify 过滤）。
 * 复杂信息图（sankey/treemap/boxplot/network/marimekko/streamgraph）请用专属页型承载。 */
function shapeChart(s, c, x, y, w, h, dcols) {
  const t = String(c.type || 'bar').toLowerCase();
  if (t === 'radialbar') { shapeRows(s, c, x, y, w, h, dcols, 'radialbar'); return; }
  if (t === 'dumbbell') { shapeRows(s, c, x, y, w, h, dcols, 'dumbbell'); return; }
  if (t === 'lollipop') { shapeRows(s, c, x, y, w, h, dcols, 'lollipop'); return; }
  if (t === 'dotplot') { shapeRows(s, c, x, y, w, h, dcols, 'dotplot'); return; }
  if (t === 'bulletchart') { shapeRows(s, c, x, y, w, h, dcols, 'bullet'); return; }
  if (t === 'sparkline') { shapeSpark(s, c, x, y, w, h, dcols); return; }
  if (t === 'slope') { shapeSlope(s, c, x, y, w, h, dcols); return; }
  if (t === 'waffle') { shapeWaffle(s, c, x, y, w, h, dcols); return; }
  if (t === 'rose') { shapeRose(s, c, x, y, w, h, dcols); return; }
  if (t === 'candlestick') { shapeCandlestick(s, c, x, y, w, h, dcols); return; }
  /* 已登记形状通道类型必须命中专属渲染器——命中通用回落 = 实现缺口，硬失败 */
  const reg = chartReg(t);
  if (reg && reg.pptx === 'shape') {
    console.error(`[build_pptx] FAIL: 形状通道类型 ${t} 已登记但缺专属渲染器，拒绝通用比例条回落`);
    process.exitCode = 1;
    throw new Error(`SHAPE_RENDERER_MISSING: ${t}`);
  }
  /* 未登记类型：仅在模型非法时走到这里（schema/校验应已拦截）——留痕便于定位 */
  console.warn(`[build_pptx] 未登记图表类型 ${t} 使用通用比例条（模型应先过 schema）。`);
  shapeProportion(s, c, x, y, w, h, dcols);
}
/* 形状图表通用排版量 */
function shapeMetrics(c, w, h) {
  const labels = (c.labels || []).map(String);
  const values = (c.values || []).map(Number);
  const n = Math.max(1, labels.length);
  const labelW = Math.min(2.4, w * 0.24);
  const valW = 0.9;
  const vmax = c.max || Math.max.apply(null, values.concat([1]));
  const top = values.length ? Math.max.apply(null, values) : 0;
  return { labels: labels, values: values, n: n, labelW: labelW, valW: valW, vmax: vmax, top: top };
}
function shapeLabel(s, t, x, y, w, h, col, bold) {
  s.addText(t, { x: x, y: y, w: w, h: h, fontFace: STYLE.font, fontSize: sz(bold ? 11.5 : 11),
    bold: !!bold, color: col || STYLE.body, valign: 'middle' });
}
function shapeValue(s, c, v, x, y, w, h, hot) {
  s.addText(String(v) + (c.unit || ''), { x: x, y: y, w: w, h: h, fontFace: STYLE.font,
    fontSize: sz(11.5), bold: true, color: hot ? STYLE.accent : STYLE.body, align: 'right', valign: 'middle' });
}
/* 玫瑰图（rose）：等角扇区、半径 ∝ 数值（南丁格尔玫瑰）。
 * 扇区用「多段旋转矩形」沿角向铺贴逼近（每扇区 ≥16 段，双边界分别取弧长），
 * 不使用 preset pie/arc 替代曲线语义；标签与数值走底部图例行（文本与 HTML 端一致）。 */
/* M1 组合规则「主图 + 排序面板」：方形图（玫瑰/网络）放在宽版心里会两侧大片留白，
   改为左图右表——右侧按数值排序的条目列表（色点 + 标签 + 数值 + 比例条），全部取自数据本身，不编造文案。 */
function rankPanel(s, items, x, y, w, h, fmt) {
  y += 0.12; h -= 0.24;   /* 底板外扩 0.12 留在给定区域内（不压注释带） */
  const list = items.slice().sort((a, b) => b.value - a.value);
  const vmax = Math.max(1e-9, ...list.map(i => Math.abs(i.value)));
  const sol = SOLVER.rows(h, list.length, { pref: 0.5, min: 0.3, max: 0.78, gap: 0.08 });
  s.addShape('roundRect', { x: x, y: y + sol.offset - 0.12, w: w, h: sol.used + 0.24, rectRadius: rr(0.1),
    fill: { color: STYLE.surface }, line: { type: 'none' }, objectName: 'rank:bg' });
  list.forEach((it, i) => {
    const ry = y + sol.offset + i * (sol.size + sol.gap);
    const fz = sol.size >= 0.6 ? 12.5 : 11;
    s.addShape('ellipse', { x: x + 0.2, y: ry + sol.size * 0.32 - 0.06, w: 0.12, h: 0.12, fill: { color: it.color }, line: { type: 'none' } });
    s.addText(it.label, { x: x + 0.4, y: ry, w: w - 1.6, h: sol.size * 0.64, valign: 'middle',
      fontFace: STYLE.font, fontSize: sz(fz), bold: !!it.hl, color: STYLE.ink });
    s.addText(fmt(it.value), { x: x + w - 1.25, y: ry, w: 1.05, h: sol.size * 0.64, align: 'right', valign: 'middle',
      fontFace: STYLE.font, fontSize: sz(fz), bold: true, color: it.hl ? STYLE.accent : STYLE.body });
    const bw = w - 0.6, by = ry + sol.size * 0.7;
    s.addShape('rect', { x: x + 0.4, y: by, w: bw - 0.2, h: 0.06, fill: { color: STYLE.line }, line: { type: 'none' } });
    s.addShape('rect', { x: x + 0.4, y: by, w: Math.max(0.04, (bw - 0.2) * Math.abs(it.value) / vmax), h: 0.06,
      fill: { color: it.color }, line: { type: 'none' } });
  });
}
function shapeRose(s, c, x, y, w, h, dcols) {
  const M = shapeMetrics(c, w, h);
  const side = w / Math.max(0.1, h) > 1.6 && M.n <= 10;
  if (side) {
    const pw = Math.min(w * 0.5, h * 1.25);
    shapeRoseCore(s, c, M, x + (w * 0.5 - pw) / 2, y, pw, h, h, dcols, false);
    rankPanel(s, M.labels.map((lb, i) => ({ label: lb, value: M.values[i] || 0,
      color: dcols ? dcols[i % dcols.length] : (M.values[i] === M.top ? STYLE.accent : STYLE.faint), hl: M.values[i] === M.top })),
      x + w * 0.54, y, w * 0.46, h, v => String(v) + (c.unit || ''));
    return;
  }
  shapeRoseCore(s, c, M, x, y, w, h, null, dcols, true);
}
function shapeRoseCore(s, c, M, x, y, w, h, plotHFix, dcols, withLegend) {
  const legendH = withLegend ? Math.min(0.72, Math.max(0.3, h * 0.18)) : 0;
  const plotH = plotHFix || Math.max(0.6, h - legendH - 0.08);
  const cx = x + w / 2, cy = y + plotH / 2;
  const R = Math.max(0.4, Math.min(w, plotH) / 2 - 0.08);
  const rMin = R * 0.2;
  const step = 360 / M.n;
  const gapDeg = M.n > 1 ? 1.6 : 0;
  const vmax = M.vmax || 1;
  M.labels.forEach((lb, i) => {
    const v = M.values[i] || 0;
    const r = rMin + (R - rMin) * Math.max(0.05, Math.min(1, Math.abs(v) / vmax));
    const a1 = -90 + i * step + gapDeg / 2;
    const a2 = -90 + (i + 1) * step - gapDeg / 2;
    const segs = Math.max(16, Math.round((a2 - a1) / 5));
    const dc = dcols ? dcols[i % dcols.length] : (v === M.top ? STYLE.accent : STYLE.faint);
    for (let k = 0; k < segs; k++) {
      const t0 = (a1 + (a2 - a1) * (k / segs)) * Math.PI / 180;
      const t1 = (a1 + (a2 - a1) * ((k + 1) / segs)) * Math.PI / 180;
      const tm = (t0 + t1) / 2;
      const chord = Math.max(0.02, r * Math.abs(t1 - t0));
      s.addShape('rect', {
        x: cx + Math.cos(tm) * (r / 2) - chord / 2, y: cy + Math.sin(tm) * (r / 2) - r / 2,
        w: chord, h: r, rotate: Math.round((tm * 180 / Math.PI + 90) * 10) / 10,
        fill: { color: dc }, line: { type: 'none' } });
    }
  });
  if (!withLegend) return;
  /* 底部图例：色块 + 标签 + 数值 */
  const itemW = Math.max(0.9, w / M.n);
  M.labels.forEach((lb, i) => {
    const dc = dcols ? dcols[i % dcols.length] : (M.values[i] === M.top ? STYLE.accent : STYLE.faint);
    const lx = x + i * itemW;
    const ly = y + plotH + 0.08;
    s.addShape('rect', { x: lx, y: ly + 0.04, w: 0.11, h: 0.11, fill: { color: dc }, line: { type: 'none' } });
    s.addText(lb, { x: lx + 0.15, y: ly - 0.02, w: Math.max(0.3, itemW - 0.85), h: 0.24,
      fontFace: STYLE.font, fontSize: sz(10.5), color: STYLE.body, valign: 'middle' });
    shapeValue(s, c, M.values[i] || 0, lx + itemW - 0.7, ly - 0.02, 0.66, 0.24, M.values[i] === M.top);
  });
}
/* K 线（candlestick）：values = [[开,高,低,收]…]；实体 = 开收，须 = 高低。
 * 上涨用 accent、下跌用中性线色（不引入红绿第二色相）；文本 = 标签 + 收盘值。 */
function shapeCandlestick(s, c, x, y, w, h, dcols) {
  const labels = (c.labels || []).map(String);
  const rows = (c.values || []).filter(r => Array.isArray(r) && r.length >= 4)
    .map(r => r.slice(0, 4).map(Number));
  const n = Math.max(1, rows.length);
  const axisH = 0.26;
  const plotH = Math.max(0.5, h - axisH - 0.1);
  const flat = [];
  rows.forEach(r => r.forEach(v => { if (!isNaN(v)) flat.push(v); }));
  const lo = flat.length ? Math.min.apply(null, flat) : 0;
  const hi = flat.length ? Math.max.apply(null, flat) : 1;
  const span = (hi - lo) || 1;
  const yFor = (v) => y + 0.06 + (1 - (v - lo) / span) * plotH;
  const step = w / n;
  const bw = Math.min(0.42, step * 0.5);
  s.addShape('rect', { x: x, y: y + 0.06 + plotH, w: w, h: 0.015, fill: { color: STYLE.line }, line: { type: 'none' } });
  rows.forEach((r, i) => {
    const [o, hiP, loP, cl] = r;
    const cxp = x + step * i + step / 2;
    const up = cl >= o;
    const bodyCol = up ? STYLE.accent : mixHex(STYLE.soft, STYLE.accent, 0.12);  // M9：下跌实体与 HTML f-accs2 同色系，不用灰线色
    s.addShape('rect', { x: cxp - 0.011, y: yFor(hiP), w: 0.022, h: Math.max(0.02, yFor(loP) - yFor(hiP)),
      fill: { color: STYLE.faint }, line: { type: 'none' } });
    s.addShape('rect', { x: cxp - bw / 2, y: yFor(Math.max(o, cl)), w: bw,
      h: Math.max(0.04, Math.abs(yFor(cl) - yFor(o))),
      fill: { color: bodyCol }, line: { type: 'none' } });
    if (labels[i]) {
      s.addText(labels[i], { x: cxp - step / 2, y: y + plotH + axisH - 0.06, w: step, h: 0.24,
        align: 'center', fontFace: STYLE.font, fontSize: sz(10), color: STYLE.faint });
    }
    shapeValue(s, c, cl, cxp - step / 2, yFor(hiP) - 0.26, step, 0.24, up);
  });
}
/* 通用回落：标签 + 比例条 + 数值——**仅**未登记/非法类型可用。
 * 已登记形状类型命中此处会由 shapeChart 抛 SHAPE_RENDERER_MISSING。 */
function shapeProportion(s, c, x, y, w, h, dcols) {
  const M = shapeMetrics(c, w, h);
  const rowH = Math.max(0.22, Math.min(0.52, h / M.n));
  const trackX = x + M.labelW + 0.08;
  const trackW = w - M.labelW - M.valW - 0.2;
  const barH = Math.max(0.12, rowH * 0.52);
  M.labels.forEach((lb, i) => {
    const v = M.values[i] || 0;
    const ry = y + i * rowH;
    const hot = v === M.top;
    const dc = dcols ? dcols[i % dcols.length] : null;
    shapeLabel(s, lb, x, ry, M.labelW - 0.06, rowH, STYLE.body);
    s.addShape('rect', { x: trackX, y: ry + (rowH - barH) / 2, w: trackW, h: barH,
      fill: { color: STYLE.surface }, line: { color: STYLE.line, width: 0.5 } });
    s.addShape('rect', { x: trackX, y: ry + (rowH - barH) / 2,
      w: Math.max(0.02, Math.abs(v) / M.vmax * trackW), h: barH,
      fill: { color: dc || (hot ? STYLE.accent : STYLE.faint) }, line: { type: 'none' } });
    shapeValue(s, c, v, trackX + trackW + 0.06, ry, M.valW, rowH, hot);
  });
}
/* 行式标记图：progress / radialbar / dumbbell / lollipop / dotplot / bullet */
function shapeRows(s, c, x, y, w, h, dcols, variant) {
  const M = shapeMetrics(c, w, h);
  const rowH = Math.max(0.24, Math.min(0.6, h / M.n));
  const trackX = x + M.labelW + 0.08;
  const trackW = w - M.labelW - M.valW - 0.2;
  const th = Math.max(0.1, rowH * (variant === 'bullet' ? 0.42 : 0.28));
  M.labels.forEach((lb, i) => {
    const v = M.values[i] || 0;
    const ry = y + i * rowH;
    const cy = ry + rowH / 2;
    const hot = v === M.top;
    const dc = dcols ? dcols[i % dcols.length] : null;
    const col = dc || (hot ? STYLE.accent : STYLE.faint);
    shapeLabel(s, lb, x, ry, M.labelW - 0.06, rowH, STYLE.body);
    const frac = Math.max(0, Math.min(1, v / M.vmax));
    if (variant === 'progress' || variant === 'radialbar') {
      s.addShape('roundRect', { x: trackX, y: cy - th / 2, w: trackW, h: th,
        rectRadius: 0.04, fill: { color: STYLE.surface }, line: { type: 'none' } });
      s.addShape('roundRect', { x: trackX, y: cy - th / 2, w: Math.max(0.03, frac * trackW), h: th,
        rectRadius: 0.04, fill: { color: col }, line: { type: 'none' } });
    } else if (variant === 'dumbbell') {
      const base = Math.max(0, Math.min(1, (M.values[i] || 0) / M.vmax));
      const other = Math.max(0, Math.min(1, ((c.series && c.series[0] && c.series[0].values[i]) || M.vmax * 0.6) / M.vmax));
      const x1 = trackX + Math.min(base, other) * trackW, x2 = trackX + Math.max(base, other) * trackW;
      s.addShape('rect', { x: x1, y: cy - 0.015, w: Math.max(0.02, x2 - x1), h: 0.03,
        fill: { color: STYLE.line }, line: { type: 'none' } });
      s.addShape('ellipse', { x: x1 - 0.055, y: cy - 0.055, w: 0.11, h: 0.11, fill: { color: STYLE.faint }, line: { type: 'none' } });
      s.addShape('ellipse', { x: x2 - 0.055, y: cy - 0.055, w: 0.11, h: 0.11, fill: { color: col }, line: { type: 'none' } });
    } else if (variant === 'lollipop' || variant === 'dotplot') {
      const px = trackX + frac * trackW;
      if (variant === 'lollipop') {
        s.addShape('rect', { x: px - 0.012, y: cy, w: 0.024, h: (y + h) - cy - 0.06,
          fill: { color: STYLE.line }, line: { type: 'none' } });
      }
      s.addShape('ellipse', { x: px - 0.07, y: cy - 0.07, w: 0.14, h: 0.14, fill: { color: col }, line: { type: 'none' } });
    } else {   /* bullet：底槽 + 实际条 + 目标刻度 */
      s.addShape('rect', { x: trackX, y: cy - th / 2, w: trackW, h: th,
        fill: { color: STYLE.surface }, line: { color: STYLE.line, width: 0.5 } });
      s.addShape('rect', { x: trackX, y: cy - th / 2, w: Math.max(0.03, frac * trackW), h: th,
        fill: { color: col }, line: { type: 'none' } });
      const tgt = Math.max(0, Math.min(1, ((c.target && c.target[i]) || M.vmax * 0.8) / M.vmax));
      s.addShape('rect', { x: trackX + tgt * trackW - 0.015, y: cy - th * 0.8, w: 0.03, h: th * 1.6,
        fill: { color: STYLE.ink }, line: { type: 'none' } });
    }
    shapeValue(s, c, v, trackX + trackW + 0.06, ry, M.valW, rowH, hot);
  });
}
/* 迷你折线（sparkline）：无轴，仅趋势线 + 端点 */
function shapeSpark(s, c, x, y, w, h, dcols) {
  const M = shapeMetrics(c, w, h);
  const stepX = M.n > 1 ? w / (M.n - 1) : 0;
  const baseY = y + h - 0.06;
  const plotH = Math.max(0.2, h - 0.18);
  let px = 0, py = 0;
  M.values.forEach((v, i) => {
    const cx = x + i * stepX;
    const cy = baseY - Math.max(0.02, (v / M.vmax) * plotH);
    if (i > 0) {
      s.addShape('rect', { x: Math.min(px, cx), y: (py + cy) / 2 - 0.012, w: Math.abs(cx - px), h: 0.024,
        fill: { color: STYLE.accent }, line: { type: 'none' } });
    }
    px = cx; py = cy;
  });
  s.addText(String(M.values[M.values.length - 1] != null ? M.values[M.values.length - 1] : '') + (c.unit || ''),
    { x: x, y: y, w: w, h: 0.3, fontFace: STYLE.font, fontSize: sz(11.5), bold: true,
      color: STYLE.accent, align: 'right' });
}
/* 斜率图（slope）：两点之间的连线 + 端点标签 */
function shapeSlope(s, c, x, y, w, h, dcols) {
  const M = shapeMetrics(c, w, h);
  const leftX = x + 0.5, rightX = x + w - 0.5;
  const plotH = Math.max(0.3, h - 0.3);
  const yFor = (v) => y + 0.15 + (1 - Math.max(0, Math.min(1, v / M.vmax))) * plotH;
  const other = (c.series && c.series[0] && c.series[0].values) || M.values.map(v => v * 0.7);
  M.labels.forEach((lb, i) => {
    const y1 = yFor(M.values[i]), y2 = yFor(Number(other[i]) || 0);
    s.addShape('rect', { x: leftX, y: (y1 + y2) / 2 - 0.012, w: rightX - leftX, h: 0.024,
      fill: { color: STYLE.line }, line: { type: 'none' } });
    s.addShape('ellipse', { x: leftX - 0.06, y: y1 - 0.06, w: 0.12, h: 0.12, fill: { color: STYLE.faint }, line: { type: 'none' } });
    s.addShape('ellipse', { x: rightX - 0.06, y: y2 - 0.06, w: 0.12, h: 0.12, fill: { color: STYLE.accent }, line: { type: 'none' } });
    s.addText(lb, { x: x, y: y1 - 0.14, w: 0.62, h: 0.28,
      fontFace: STYLE.font, fontSize: sz(10.5), color: STYLE.body, align: 'right', valign: 'middle' });
    shapeValue(s, c, M.values[i], x + 0.66, y1 - 0.14, 0.52, 0.28, true);
    shapeValue(s, c, Number(other[i]) || 0, rightX + 0.1, y2 - 0.14, 0.62, 0.28, false);
  });
}
/* 华夫图（waffle）：10×N 点阵按占比填充；图例含在图高 h 内（几何铁律②，防与 inline 数据表叠印） */
function shapeWaffle(s, c, x, y, w, h, dcols) {
  const M = shapeMetrics(c, w, h);
  const cols = 10, rows = 10;
  /* 图例带收在 h 内：网格只用 h-legendH，图例贴在网格下方 */
  const legendH = 0.30;
  const plotH = Math.max(0.6, h - legendH);
  const cell = Math.min(w / cols, plotH / rows);
  const total = M.values.reduce((a, b) => a + b, 0) || 1;
  const units = 100;
  let filled = 0;
  const alloc = M.values.map(v => Math.round(v / total * units));
  M.labels.forEach((lb, i) => {
    const dc = dcols ? dcols[i % dcols.length] : (i === 0 ? STYLE.accent : STYLE.faint);
    for (let k = 0; k < alloc[i] && filled < units; k++, filled++) {
      const r = Math.floor(filled / cols), cc = filled % cols;
      s.addShape('roundRect', { x: x + cc * cell, y: y + r * cell, w: cell * 0.82, h: cell * 0.82,
        rectRadius: 0.02, fill: { color: dc }, line: { type: 'none' } });
    }
  });
  let lx = x;
  const legendY = y + Math.min(plotH, rows * cell) + 0.02;
  M.labels.forEach((lb, i) => {
    const dc = dcols ? dcols[i % dcols.length] : (i === 0 ? STYLE.accent : STYLE.faint);
    s.addShape('ellipse', { x: lx, y: legendY + 0.04, w: 0.1, h: 0.1, fill: { color: dc }, line: { type: 'none' } });
    s.addText(lb, { x: lx + 0.14, y: legendY, w: 0.9, h: 0.24,
      fontFace: STYLE.font, fontSize: sz(10.5), color: STYLE.body, valign: 'middle' });
    s.addText(String(M.values[i] != null ? M.values[i] : '') + (c.unit || ''),
      { x: lx + 1.06, y: legendY, w: 0.66, h: 0.24, fontFace: STYLE.font, fontSize: sz(10.5),
        bold: true, color: STYLE.body, valign: 'middle' });
    lx += 1.9;
  });
}
/* 图表 + 数据表组合块：inline 策略在图表下方附原生小字号表格（压缩图表高度，不越界） */
function chartBlock(s, c, x, y, w, h, dcols) {
  const dm = dataTableMode(c);
  let chH = h;
  const hasData = (c.labels || []).length > 0;
  if (dm === 'inline' && hasData) {
    const rowsData = dataTableRows(c);
    const n = rowsData.length;
    const tH = Math.min(h * 0.44, Math.max(0.44, n * 0.22 + 0.06));
    chH = Math.max(0.85, h - tH - 0.1);
    const rowH = Math.max(0.15, (tH - 0.04) / Math.max(1, n));
    const dense = rowH < 0.26;
    const fs = sz(dense ? 9 : 10.5);
    const rows = rowsData.map((r, ri) => r.map(cell => ({
      text: String(cell),
      options: {
        fontSize: fs, fontFace: STYLE.font, valign: 'middle',
        bold: ri === 0, color: ri === 0 ? STYLE.ink : STYLE.body,
        fill: { color: ri === 0 ? STYLE.soft : STYLE.bg },
      },
    })));
    const tblBox = { x: x, y: y + chH + 0.1, w: w, h: tH };
    const chartBox = { x: x, y: y, w: w, h: chH };
    assertNoOverlap('chartBlock:chart∩inlineTable', chartBox, tblBox);
    s.addTable(rows, { x: tblBox.x, y: tblBox.y, w: tblBox.w, h: tblBox.h, rowH: rowH, autoPage: false,
      border: { pt: 0.5, color: STYLE.line }, margin: dense ? 1 : 3, fit: 'shrink', valign: 'middle' });
  }
  if (isNativeChart(c.type)) nativeChart(s, c, x, y, w, chH, dcols);
  else shapeChart(s, c, x, y, w, chH, dcols);
}
/* ═══ 复杂信息图页型（形状通道：高保真形状还原 + 数据表可追溯）═══
 * 复杂曲线 / 流带一律用「多段旋转矩形」沿采样路径逼近（采样点 ≥16，上下边界分别追踪），
 * 不使用 preset shape（pie / arc / blockArc / chord / moon / wave）替代；
 * 与 HTML 端（assets/pptx-export.js）同规则、文本集合一致（cross_verify 逐页比对）。 */
const INFO_MIN_SAMPLES = 16;
function sstep(t) { return t * t * (3 - 2 * t); }
/* 沿采样路径铺贴多段旋转矩形：pts[i] = [x, yTop, yBottom]（双边界分别追踪） */
function ribbonRects(s, pts, color) {
  for (let i = 0; i < pts.length - 1; i++) {
    const a = pts[i], b = pts[i + 1];
    const ca = (a[1] + a[2]) / 2, cb = (b[1] + b[2]) / 2;
    const dx = b[0] - a[0], dy = cb - ca;
    const len = Math.sqrt(dx * dx + dy * dy);
    /* 厚度取绝对值：sankey 按 [x,上,下]、streamgraph 按 [x,下,上] 传参（y 向下），
       符号不应影响厚度（原 (a[2]-a[1]) 在 streamgraph 为负 → th 恒 0.02，流带变细线） */
    const th = Math.max(0.02, Math.abs(((a[1] - a[2]) + (b[1] - b[2])) / 2));
    const ang = Math.atan2(dy, dx) * 180 / Math.PI;
    /* 相邻 quad 沿走向微叠 0.02in：消除拼接处的抗锯齿发丝缝（streamgraph/sankey 像素级瑕疵） */
    const ov = 0.02;
    s.addShape('rect', { x: (a[0] + b[0]) / 2 - len / 2 - ov, y: (ca + cb) / 2 - th / 2,
      w: Math.max(0.02, len) + ov * 2, h: th, rotate: Math.round(ang * 10) / 10,
      fill: { color: color }, line: { type: 'none' } });
  }
}
/* 信息图页型的数据表策略与行（默认 notes：数据入演讲者备注；inline：页内附原生表格） */
function infoDataTableMode(sec) {
  const m = String(((sec.chart || {}).dataTable) || 'notes').toLowerCase();
  const mode = m === 'appendix' ? 'inline' : m;
  /* M1 容量规则：内联数据表行高下限 0.26in、最多占绘图区 40%（≈1.4in）——装不下时转入备注，
     不再把 0.15in 的挤压表格压进结论条（LibreOffice/WPS 实际行高会撑开越界） */
  if (mode === 'inline') {
    const rows = infoTableRows(sec);
    if (rows && rows.length * 0.26 > 1.4) {
      if (!sec._dtWarned) { console.warn(`[build_pptx] 提示：「${sec.title || sec.type}」内联数据表 ${rows.length} 行超出承载，已转入演讲者备注`); sec._dtWarned = true; }
      return 'notes';
    }
  }
  return mode;
}
function infoTableRows(sec) {
  const t = sec.type || '';
  const u = sec.unit ? '（' + sec.unit + '）' : '';
  if (t === 'sankey') return [['源', '汇', '流量' + u]].concat((sec.flows || []).map(f => [String(f[0]), String(f[1]), String(f[2])]));
  if (t === 'treemap') return [['项目', '数值' + u]].concat((sec.items || []).map(it => [String(it[0]), String(it[1])]));
  if (t === 'boxplot') return [['分组', '最小', 'Q1', '中位', 'Q3', '最大']].concat((sec.groups || []).map(g => g.map(String)));
  if (t === 'network') return [['节点', '名称']].concat((sec.nodes || []).map(n => [String(n[0]), String(n[1])]));
  if (t === 'marimekko') {
    const head = ['列', '总量' + u].concat((sec.legend || []).map(String));
    return [head].concat((sec.cols || []).map((c, i) => [String(c[0]), String(c[1])]
      .concat(marimekkoSegs((sec.cells || [])[i], 99).map(sg => sg.label != null ? sg.label + ' ' + sg.value : String(sg.value)))));
  }
  if (t === 'streamgraph') {
    return [['系列'].concat((sec.labels || []).map(String))]
      .concat((sec.series || []).map(se => [String(se.name || '')].concat((se.values || []).map(String))));
  }
  return null;
}
function infoTable(s, rows, x, y, w, h) {
  const n = rows.length;
  const rowH = Math.max(0.15, Math.min(0.26, h / Math.max(1, n)));
  const dense = rowH < 0.24;
  const fs = sz(dense ? 9 : 10.5);
  const tbl = rows.map((r, ri) => r.map(cell => ({ text: String(cell), options: {
    fontSize: fs, fontFace: STYLE.font, valign: 'middle', bold: ri === 0,
    color: ri === 0 ? STYLE.ink : STYLE.body,
    fill: { color: ri === 0 ? STYLE.soft : STYLE.bg } } })));
  s.addTable(tbl, { x: x, y: y, w: w, rowH: rowH, autoPage: false,
    border: { pt: 0.5, color: STYLE.line }, margin: dense ? 1 : 3 });
}
/* 信息图页型的公共外壳：算绘图区（inline 数据表占位则压缩绘图区） */
function infoPlot(sec, y0, y1) {
  const rows = infoTableRows(sec);
  const inline = (infoDataTableMode(sec) === 'inline') && rows && rows.length;
  if (!inline) return { y0: y0, y1: y1, rows: rows };
  const tH = Math.min((y1 - y0) * 0.4, Math.max(0.44, rows.length * 0.22 + 0.06));
  return { y0: y0, y1: y1 - tH - 0.1, rows: rows, table: { y: y1 - tH, h: tH } };
}
/* 桑基图（M3 重写）：分层节点 + 三次贝塞尔流带（custGeom，一条流 = 一个可编辑形状）。
 * 与 HTML 端 lib_chart_svg.sankey 同一算法：全局比例尺 = 各层 (可用高 / 层流量和) 的最小值，
 * 节点高 = 流量 × 比例尺、整层垂直居中；流带厚 = 流量 × 比例尺，出入口各自累加偏移，
 * 因此流带与节点严丝合缝（旧实现按全局总流量估厚度，流带与节点不对齐）。流向「流失」类节点用灰。 */
function fmtNum(v) { const n = Number(v); if (!isFinite(n)) return String(v); return Math.abs(n - Math.round(n)) < 1e-9 ? Math.round(n).toLocaleString('en-US') : n.toFixed(1); }
const SANKEY_LOSS = ['流失', '流出', '损耗', '退出'];
function ribbonGeom(s, x0, ya, x1, yb, th, color, transp) {
  const top = Math.min(ya, yb), h = Math.abs(yb - ya) + th, w = Math.max(0.02, x1 - x0);
  const A = ya - top, B = yb - top, mx = w / 2;
  s.addShape('custGeom', { x: x0, y: top, w: w, h: h, fill: { color: color, transparency: transp || 0 },
    line: { type: 'none' }, points: [
      { x: 0, y: A },
      { x: w, y: B, curve: { type: 'cubic', x1: mx, y1: A, x2: mx, y2: B } },
      { x: w, y: B + th },
      { x: 0, y: A + th, curve: { type: 'cubic', x1: mx, y1: B + th, x2: mx, y2: A + th } },
      { close: true }] });
}
function infoSankey(s, sec, y0, y1) {
  const G = PT.sankey;
  const P = infoPlot(sec, y0, y1);
  if (P.table) infoTable(s, P.rows, MX, P.table.y, CW, P.table.h);
  const flows = (sec.flows || []).filter(f => f && f.length >= 3);
  const nodes = [], idx = {};
  flows.forEach(f => [f[0], f[1]].forEach(n => { if (idx[n] == null) { idx[n] = nodes.length; nodes.push(n); } }));
  if (!nodes.length) return;
  const level = nodes.map(() => 0);
  for (let iter = 0; iter < nodes.length + 1; iter++) {
    let ch = false;
    flows.forEach(f => { const a = idx[f[0]], b = idx[f[1]]; if (level[b] < level[a] + 1) { level[b] = level[a] + 1; ch = true; } });
    if (!ch) break;
  }
  const maxLv = Math.max.apply(null, level.concat([0]));
  const outSum = {}, inSum = {};
  flows.forEach(f => { outSum[f[0]] = (outSum[f[0]] || 0) + Number(f[2]); inSum[f[1]] = (inSum[f[1]] || 0) + Number(f[2]); });
  const size = (n) => Math.max(inSum[n] || 0, outSum[n] || 0);
  const plotH = P.y1 - P.y0;
  const gap = G.nodeGap;
  const cols = [];
  for (let l = 0; l <= maxLv; l++) cols.push(nodes.filter((n, i) => level[i] === l));
  const scale = Math.min.apply(null, cols.filter(c => c.length).map(c =>
    (plotH - gap * (c.length - 1)) / (c.reduce((a, n) => a + size(n), 0) || 1)));
  const labelW = Math.min(G.labelW, 1.5);
  const xL = MX + labelW + 0.1, xR = MX + CW - labelW - 0.1 - G.nodeW;
  const geo = {};
  cols.forEach((c, l) => {
    const tot = c.reduce((a, n) => a + size(n) * scale, 0) + gap * (c.length - 1);
    let cy = P.y0 + (plotH - tot) / 2;
    c.forEach(n => {
      const h = Math.max(0.04, size(n) * scale);
      geo[n] = { x: xL + (xR - xL) * (maxLv ? l / maxLv : 0), y: cy, h: h, lv: l, oo: 0, oi: 0 };
      cy += h + gap;
    });
  });
  const isLoss = (n) => SANKEY_LOSS.indexOf(String(n)) >= 0;
  const labels = [];
  flows.forEach(f => {
    const a = geo[f[0]], b = geo[f[1]];
    if (!a || !b) return;
    const v = Number(f[2]) || 0, th = Math.max(0.02, v * scale);
    const ya = a.y + a.oo, yb = b.y + b.oi;
    a.oo += th; b.oi += th;
    const x0 = a.x + G.nodeW, x1 = b.x;
    ribbonGeom(s, x0, ya, x1, yb, th, isLoss(f[1]) ? STYLE.line : STYLE.soft, 0);
    if (th >= 0.18) labels.push([v, x0, x1, ya, yb, th]);
  });
  labels.forEach(([v, x0, x1, ya, yb, th]) => s.addText(fmtNum(v), {
    x: (x0 + x1) / 2 - 0.5, y: (ya + yb) / 2 + th / 2 - 0.13, w: 1.0, h: 0.26,
    align: 'center', valign: 'middle', fontFace: STYLE.font, fontSize: sz(11.5), bold: true, color: STYLE.ink }));
  nodes.forEach(n => {
    const g = geo[n];
    s.addShape('rect', { x: g.x, y: g.y, w: G.nodeW, h: g.h, fill: { color: isLoss(n) ? STYLE.faint : STYLE.accent }, line: { type: 'none' } });
    const first = g.lv === 0;
    s.addText(String(n) + ' ' + fmtNum(size(n)), { x: first ? (g.x - labelW - 0.08) : (g.x + G.nodeW + 0.08), y: g.y + g.h / 2 - 0.16,
      w: labelW, h: 0.32, align: first ? 'right' : 'left', valign: 'middle',
      fontFace: STYLE.font, fontSize: sz(11), bold: true, color: STYLE.ink });
  });
}
/* 树图：按面积编码的矩形切分（递归二分，面积严格成比例） */
function tmSplit(items, x, y, w, h, out) {
  if (!items.length) return;
  if (items.length === 1) { out.push({ it: items[0], x: x, y: y, w: w, h: h }); return; }
  const total = items.reduce((a, i) => a + i.v, 0) || 1;
  let acc = 0, k = 0;
  for (; k < items.length - 1; k++) { acc += items[k].v; if (acc >= total / 2) break; }
  const first = items.slice(0, k + 1), second = items.slice(k + 1);
  const r = first.reduce((a, i) => a + i.v, 0) / total;
  if (w >= h) {
    tmSplit(first, x, y, w * r, h, out);
    tmSplit(second, x + w * r, y, w * (1 - r), h, out);
  } else {
    tmSplit(first, x, y, w, h * r, out);
    tmSplit(second, x, y + h * r, w, h * (1 - r), out);
  }
}
function infoTreemap(s, sec, y0, y1) {
  const G = PT.treemap;
  const P = infoPlot(sec, y0, y1);
  if (P.table) infoTable(s, P.rows, MX, P.table.y, CW, P.table.h);
  const items = (sec.items || []).map(it => ({ label: String(it[0]), v: Math.max(0, Number(it[1]) || 0) }))
    .filter(i => i.v > 0).sort((a, b) => b.v - a.v).slice(0, G.maxLeaves);
  if (!items.length) return;
  const out = [];
  tmSplit(items, MX, P.y0, CW, P.y1 - P.y0, out);
  const maxV = items[0].v || 1;
  const total = items.reduce((a, i) => a + i.v, 0) || 1;
  /* M9：灰阶与 HTML 一致——三级都在品牌色系内（主色 / 中间调 / 浅调），不再出现灰色 STYLE.line 块；
     标签带占比，字号与 HTML 同比例 */
  const bg = STYLE.bg || 'FFFFFF';
  const tone = [null, mixHex(STYLE.soft, bg, 0.35), mixHex(STYLE.soft, STYLE.accent, 0.1), STYLE.accent];  // 浅调从 soft 出发，避免深品牌色与白混出灰
  out.forEach(o => {
    const p = o.it.v / maxV;
    const lvl = o.it === items[0] ? 3 : (p >= 0.5 ? 2 : 1);  // 只有最大块用主色，与 HTML 一致
    const fill = tone[lvl];
    const onAcc = lvl >= 3;
    s.addShape('rect', { x: o.x + G.gap / 2, y: o.y + G.gap / 2,
      w: Math.max(0.05, o.w - G.gap), h: Math.max(0.05, o.h - G.gap),
      fill: { color: fill }, line: { color: bg, width: 0.75 }, objectName: 'treemap:leaf' });
    if (o.h >= G.labelMinH) {
      s.addText(o.it.label, { x: o.x + 0.12, y: o.y + 0.08, w: Math.max(0.2, o.w - 0.24), h: 0.34,
        fontFace: STYLE.font, fontSize: sz(13), bold: true, color: onAcc ? STYLE.onAccent : STYLE.ink });
      const share = Math.round(o.it.v / total * 100);
      s.addText(String(o.it.v) + (sec.unit || '') + ' · ' + share + '%', { x: o.x + 0.12, y: o.y + 0.42, w: Math.max(0.2, o.w - 0.24), h: 0.3,
        fontFace: STYLE.font, fontSize: sz(11), color: onAcc ? STYLE.onAccent : STYLE.body });
    }
  });
}
/* 箱线图（M9 重写为横向，与 HTML lib_chart_svg.boxplot 同构）：每组一行，左侧组名、
 * 横轴取整到 10 的刻度网格；须线 + 端帽 + 品牌浅调箱体 + 主色中位线，右侧「中位 N」标注。
 * 全部是原生线/矩形/文本框，可编辑。 */
function infoBoxplot(s, sec, y0, y1) {
  const G = PT.boxplot;
  const P = infoPlot(sec, y0, y1);
  if (P.table) infoTable(s, P.rows, MX, P.table.y, CW, P.table.h);
  const groups = (sec.groups || []).filter(g => g && g.length >= 6).slice(0, G.maxGroups);
  if (!groups.length) return;
  const unit = sec.unit || '';
  const lo = Math.floor(Math.min.apply(null, groups.map(g => Number(g[1]))) / 10) * 10;
  const hi = Math.ceil(Math.max.apply(null, groups.map(g => Number(g[5]))) / 10) * 10;
  const span = (hi - lo) || 1;
  const labW = Math.min(G.labelW, CW * 0.16), medW = 1.2;
  const ax0 = MX + labW + 0.15, ax1 = MX + CW - medW - 0.1;
  const top = P.y0 + 0.05, axisY = P.y1 - 0.32;
  const X = v => ax0 + (Number(v) - lo) / span * (ax1 - ax0);
  for (let k = 0; k <= 5; k++) {
    const v = lo + span * k / 5, x = X(v);
    s.addShape('line', { x, y: top, w: 0.005, h: axisY - top, line: { color: STYLE.line, width: 0.5 } });
    s.addText(fmtNum(v), { x: x - 0.4, y: axisY + 0.04, w: 0.8, h: 0.24, align: 'center', margin: 0,
      fontFace: STYLE.font, fontSize: sz(9.5), color: STYLE.faint });
  }
  const step = (axisY - top) / groups.length;
  const bh = Math.min(0.42, step * 0.5);
  const boxFill = mixHex(STYLE.soft, STYLE.accent, 0.12);
  groups.forEach((g, i) => {
    const mn = Number(g[1]), q1 = Number(g[2]), md = Number(g[3]), q3 = Number(g[4]), mx = Number(g[5]);
    const cy = top + step * i + step / 2;
    s.addShape('line', { x: X(mn), y: cy, w: Math.max(0.01, X(mx) - X(mn)), h: 0.005, line: { color: STYLE.faint, width: 1.25 } });
    [mn, mx].forEach(v => s.addShape('line', { x: X(v), y: cy - bh / 3, w: 0.005, h: bh * 2 / 3, line: { color: STYLE.faint, width: 1.25 } }));
    s.addShape('roundRect', { x: X(q1), y: cy - bh / 2, w: Math.max(0.05, X(q3) - X(q1)), h: bh, rectRadius: rr(0.06),
      fill: { color: boxFill }, line: { type: 'none' }, objectName: 'boxplot:box' });
    s.addShape('line', { x: X(md), y: cy - bh / 2, w: 0.005, h: bh, line: { color: STYLE.accent, width: 2.5 } });
    s.addText(String(g[0]), { x: MX, y: cy - 0.17, w: labW, h: 0.34, align: 'right', valign: 'middle', margin: 0,
      fontFace: STYLE.font, fontSize: sz(11.5), bold: true, color: STYLE.ink });
    s.addText('中位 ' + fmtNum(md) + unit, { x: ax1 + 0.12, y: cy - 0.16, w: medW, h: 0.32, valign: 'middle', margin: 0,
      fontFace: STYLE.font, fontSize: sz(11), bold: true, color: STYLE.body });
  });
}
/* 关系网络：确定性环形布局（同环按输入顺序）+ 直连边 */
function infoNetwork(s, sec, y0, y1) {
  const G = PT.network;
  const P = infoPlot(sec, y0, y1);
  if (P.table) infoTable(s, P.rows, MX, P.table.y, CW, P.table.h);
  const nodes = (sec.nodes || []).slice(0, G.maxNodes);
  if (!nodes.length) return;
  const edges = (sec.edges || []).slice(0, G.maxEdges);
  /* M9：与 HTML（lib_chart_svg.network）同一画法——连接度最高的节点居中，其余按椭圆环绕；
     节点是胶囊（文字在内，可编辑），下方标「N 条连接」；连线用原生直线。不再另画右侧排序面板。 */
  const degOf = (id) => edges.filter(e => String(e[0]) === id || String(e[1]) === id).length;
  const order = nodes.slice().sort((p1, p2) => degOf(String(p2[0])) - degOf(String(p1[0])));
  const hub = order[0], rest = order.slice(1);
  const plotH = P.y1 - P.y0;
  const cx = MX + CW / 2, cy = P.y0 + plotH / 2;
  const pos = {};
  pos[String(hub[0])] = { x: cx, y: cy };
  rest.forEach((nd, i) => {
    const a = -Math.PI / 2 + i * 2 * Math.PI / Math.max(1, rest.length);
    pos[String(nd[0])] = { x: cx + CW * 0.36 * Math.cos(a), y: cy + plotH * 0.36 * Math.sin(a) };
  });
  edges.forEach(e => {
    const a = pos[String(e[0])], b = pos[String(e[1])];
    if (!a || !b) return;
    s.addShape('line', { x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), w: Math.max(0.01, Math.abs(b.x - a.x)), h: Math.max(0.01, Math.abs(b.y - a.y)),
      flipH: (b.x < a.x) !== (b.y < a.y), line: { color: STYLE.line, width: 1.5 }, objectName: 'network:edge' });
  });
  const pillH = Math.min(0.54, plotH * 0.15);
  nodes.forEach((nd) => {
    const id = String(nd[0]), p = pos[id], main = id === String(hub[0]);
    const label = String(nd[1] != null ? nd[1] : nd[0]);
    const pw = Math.min(G.labelMaxW + 0.8, 0.5 + 0.22 * label.length);
    s.addText(label, { x: p.x - pw / 2, y: p.y - pillH / 2, w: pw, h: pillH, shape: 'roundRect', rectRadius: pillH / 2,
      fill: { color: main ? STYLE.accent : STYLE.soft }, line: { type: 'none' }, align: 'center', valign: 'middle', margin: 0,
      fontFace: STYLE.font, fontSize: sz(15), bold: true, color: main ? (STYLE.onAccent || 'FFFFFF') : STYLE.ink,
      objectName: 'network:node' });
    s.addText(degOf(id) + ' 条连接', { x: p.x - 0.8, y: p.y + pillH / 2 + 0.03, w: 1.6, h: 0.3, align: 'center', valign: 'top',
      margin: 0, fontFace: STYLE.font, fontSize: sz(12), color: STYLE.faint });
  });
}
/* marimekko 单元格归一化：裸数值 [70,25,5] 或 [标签,数值] 对 [["<50ms",70],…]
   （与 cols/flows/groups 的 [标签,值] 惯例一致）；非数值 → 0，零值段过滤 */
function marimekkoSegs(arr, maxSegs) {
  return ((arr || []).slice(0, maxSegs == null ? 99 : maxSegs)).map(el => {
    const pair = Array.isArray(el);
    const v = Number(pair ? el[1] : el);
    return { label: pair ? String(el[0]) : null, value: isFinite(v) ? v : 0 };
  }).filter(sg => sg.value > 0);
}
/* 马赛克图：列宽按列总量、列高按 100% 构成的双重编码 */
function infoMarimekko(s, sec, y0, y1) {
  const G = PT.marimekko;
  const P = infoPlot(sec, y0, y1);
  if (P.table) infoTable(s, P.rows, MX, P.table.y, CW, P.table.h);
  const cols = (sec.cols || []).slice(0, G.maxCols);
  if (!cols.length) return;
  const legend = (sec.legend || []).map(String);
  const cells = sec.cells || [];
  const total = cols.reduce((a, c) => a + (Number(c[1]) || 0), 0) || 1;
  /* 图例收在 P.y1 底带；列标签在图区下沿之上——二者留 0.12in 间隙，禁叠印（几何铁律②） */
  const legendH = Math.max(0.28, G.legendH || 0.32);
  const plotH = Math.max(0.5, (P.y1 - P.y0) - legendH - 0.40);
  const labelY = P.y0 + plotH + 0.04;
  const legendY = P.y1 - 0.22;
  const availW = CW - G.colGap * Math.max(0, cols.length - 1);
  /* M9：与 HTML f-acc / f-accs2 同色系——主色 + 品牌浅调梯度，不用灰 */
  const palette = [STYLE.accent, mixHex(STYLE.soft, STYLE.accent, 0.12), mixHex(STYLE.soft, STYLE.accent, 0.45), STYLE.soft];
  let cx0 = MX;
  cols.forEach((c, i) => {
    const cw = Math.max(0.2, (Number(c[1]) || 0) / total * availW);
    const segs = marimekkoSegs(cells[i], G.maxSegs);
    const sum = segs.reduce((a, sg) => a + sg.value, 0) || 1;
    let cy0 = P.y0;
    segs.forEach((sg, k) => {
      const v = sg.value;
      const sh = Math.max(0.02, v / sum * plotH);
      s.addShape('rect', { x: cx0, y: cy0, w: cw, h: sh,
        fill: { color: palette[k % palette.length] }, line: { color: STYLE.bg, width: 0.75 } });
      /* 有标签用标签（"<50ms"），裸数值沿用旧行为（值 + 单位） */
      const segLabel = sg.label != null ? sg.label : (String(v) + (sec.unit || ''));
      s.addText(segLabel, { x: cx0, y: cy0 + sh / 2 - 0.13, w: cw, h: 0.26, align: 'center',
        fontFace: STYLE.font, fontSize: sz(11.5), bold: true, fit: 'shrink',
        color: k === 0 ? STYLE.onAccent : STYLE.ink });
      cy0 += sh;
    });
    s.addText(String(c[0]), { x: cx0, y: labelY, w: cw, h: 0.28, align: 'center',
      fontFace: STYLE.font, fontSize: sz(12), bold: true, color: STYLE.body, fit: 'shrink' });
    cx0 += cw + G.colGap;
  });
  let lx = MX;
  legend.forEach((lg, k) => {
    s.addShape('rect', { x: lx, y: legendY + 0.06, w: 0.12, h: 0.12,
      fill: { color: palette[k % palette.length] }, line: { type: 'none' } });
    s.addText(lg, { x: lx + 0.16, y: legendY, w: 1.5, h: 0.24,
      fontFace: STYLE.font, fontSize: sz(11.5), color: STYLE.body, valign: 'middle', fit: 'shrink' });
    lx += 1.75;
  });
}
/* 流带图：基线居中的堆叠平滑带（带边界上下分别采样，采样点 ≥24） */
function infoStreamgraph(s, sec, y0, y1) {
  const G = PT.streamgraph;
  const P = infoPlot(sec, y0, y1);
  if (P.table) infoTable(s, P.rows, MX, P.table.y, CW, P.table.h);
  const series = (sec.series || []).slice(0, G.maxSeries);
  if (!series.length) return;
  const labels = sec.labels || [];
  const nPts = labels.length || ((series[0].values || []).length);
  if (nPts < 2) return;
  const values = series.map(se => (se.values || []).map(v => Math.max(0, Number(v) || 0)));
  const totals = [];
  for (let i = 0; i < nPts; i++) {
    let t = 0;
    values.forEach(v => { t += (v[i] || 0); });
    totals.push(t);
  }
  const maxTot = Math.max.apply(null, totals.concat([1]));
  /* M7 修复：此前流带总厚度只用了 plotH/2（图只占上半区，下半空白），图例竖排又吃掉一大块；
     现在流带铺满 plotH，年份轴在图下，图例单行横排。 */
  const legH = 0.3, axisH = 0.26;
  // Reserve legend INSIDE the plot region (legH + axisH) so nothing spills below y1
  const plotBottom = P.y1 - legH - axisH;
  const plotH = Math.max(0.6, plotBottom - P.y0);
  const cyMid = P.y0 + plotH / 2;
  const xAt = (i) => MX + (nPts > 1 ? i / (nPts - 1) : 0.5) * CW;
  const yAt = (i) => cyMid - (totals[i] / maxTot) * plotH / 2;
  /* M9：与 HTML f-c1…c5 同源（风格编码色板），不再用灰阶 */
  const palette = (dataColors(styleArg) || [STYLE.accent, mixHex(STYLE.soft, STYLE.accent, 0.45), mixHex(STYLE.soft, STYLE.accent, 0.12)]).slice(0, 5);
  const n = Math.max(24, Math.round(CW / 0.1));
  let base = [];
  for (let i = 0; i < nPts; i++) base.push(yAt(i));
  let lx = MX;
  series.forEach((se, si) => {
    const upper = [];
    for (let i = 0; i < nPts; i++) upper.push(base[i] + (values[si][i] || 0) / maxTot * plotH);
    const pts = [];
    for (let k = 0; k <= n; k++) {
      const t = k / n * (nPts - 1);
      const i0 = Math.min(nPts - 2, Math.floor(t)), f = t - i0;
      const x = MX + (k / n) * CW;
      const bt = base[i0] + (base[i0 + 1] - base[i0]) * sstep(f);
      const ut = upper[i0] + (upper[i0 + 1] - upper[i0]) * sstep(f);
      pts.push([x, ut, bt]);
    }
    ribbonRects(s, pts, palette[si % palette.length]);
    const name = String(se.name || ('系列' + (si + 1)));
    const lw = 0.3 + Math.min(2.4, estLines(name, 99, sz(10)) * 0 + name.length * 0.16);
    s.addShape('rect', { x: lx, y: plotBottom + axisH + 0.09, w: 0.12, h: 0.12,
      fill: { color: palette[si % palette.length] }, line: { type: 'none' } });
    s.addText(name, { x: lx + 0.16, y: plotBottom + axisH + 0.05, w: lw, h: 0.2,
      fontFace: STYLE.font, fontSize: sz(11.5), color: STYLE.body, valign: 'middle' });
    lx += lw + 0.35;
    base = upper;
  });
  labels.forEach((lb, i) => {
    const w0 = 0.8, x0 = Math.max(MX, Math.min(MX + CW - w0, xAt(i) - w0 / 2));
    s.addText(String(lb), { x: x0, y: plotBottom + 0.03, w: w0, h: 0.2, align: i === 0 ? 'left' : (i === labels.length - 1 ? 'right' : 'center'),
      fontFace: STYLE.font, fontSize: sz(11), color: STYLE.faint });
  });
}
/* 表格：行高按可用高度自适应；行数×minRowH 超高时压到 hardFloor 并告警，禁止溢出注释带 */
function addTable(s, tbl, x, y, w, availH, opts) {
  opts = opts || {};
  const rowsIn = tbl.rows || [];
  const head = tbl.head || [];
  const n = rowsIn.length + 1;
  /* 美化路由短表（≤6 行正文）：行高与字号放大，表格撑满主体区而不是缩在页面上沿 */
  const roomy = (!!CONTENT.contentLocked || !!opts.roomy) && rowsIn.length <= 6 && opts.maxRowH == null;
  const maxRowH = opts.maxRowH != null ? opts.maxRowH : (roomy ? 0.72 : PT.table.rowH);
  const minRowH = opts.minRowH != null ? opts.minRowH : PT.table.rowHMin;
  const headRowH = opts.headRowH != null ? opts.headRowH : (PT.table.headRowH || minRowH);
  /* 行数超过容量时优先压行高到 hardFloor，仍放不下则整体缩放到 availH（禁溢出） */
  const hardFloor = Math.min(minRowH, AT_TABLE.rowFloorIn != null ? AT_TABLE.rowFloorIn : 0.22);
  const ideal = availH / Math.max(1, n);
  let rowH = Math.min(maxRowH, Math.max(hardFloor, ideal));
  if (n * rowH > availH + 0.01) {
    rowH = availH / Math.max(1, n);
    if (typeof console !== 'undefined') {
      console.warn(`addTable: ${n} 行×${rowH.toFixed(3)}in 仍超 availH=${availH.toFixed(2)}，已压到可用高度`);
    }
  }
  /* 行多则同步收字号（research 密排允许更小；句子单元格仍走语义字号门禁） */
  const dense = rowH < 0.42;
  const headSz = sz(roomy ? 15 : dense ? 11 : Math.min(13, AT_TABLE.headMax || 12));
  const bodySz = sz(roomy ? 15 : dense ? 10 : Math.min(12.5, AT_TABLE.cellMax || 13));
  const hRowH = roomy ? Math.min(0.62, rowH) : Math.min(headRowH, Math.max(hardFloor, rowH * 1.15));
  /* 内容高度预估：逐格用 estTextH 估算，超出行高则全表收字号 ——
     禁依赖 fit:'shrink' 或渲染引擎自动撑高（PowerPoint/LibreOffice 会按内容增高行，压住脚注） */
  const ncolsT = Math.max(head.length, 1, ...rowsIn.map(r => r.length));
  const effColW = (Array.isArray(tbl.colW) && tbl.colW.length >= ncolsT) ? tbl.colW.slice(0, ncolsT)
    : Array.from({ length: ncolsT }, () => w / ncolsT);
  const cellPadIn = (dense ? 2 : 5) / 72;
  /* 长表格单元格适配（adaptiveText.table 单源）：逐格估算，超出行高则全表收字号；
     floor 取模式下限与表格下限之大者——表格不得突破模式可读性底线 */
  const fitCellSz = (text, cw, availHh, maxSz) => fitFont([String(text == null ? '' : text)],
    Math.max(0.5, cw - cellPadIn * 2), Math.max(0.2, availHh - cellPadIn * 2),
    { max: maxSz, maxShrinkSteps: 6, floor: Math.max(modeFloorPt(), AT_TABLE.cellFloor || 0) });
  let bodySzF = bodySz, headSzF = headSz;
  rowsIn.forEach(r => r.forEach((c, j) => {
    const f = fitCellSz(c, effColW[j] != null ? effColW[j] : effColW[0], rowH, bodySz);
    if (f < bodySzF) bodySzF = f;
  }));
  head.forEach((h, j) => {
    const f = fitCellSz(h, effColW[j] != null ? effColW[j] : effColW[0], hRowH, headSz);
    if (f < headSzF) headSzF = f;
  });
  /* 字号触底仍装不下 → 显式告警（内容超承载，建议拆页/精简；行高不再自动撑高） */
  const stillOver = (text, cw, availHh, f) =>
    estTextH(String(text == null ? '' : text), Math.max(0.5, cw - cellPadIn * 2), f, TM_LINE) >
    Math.max(0.2, availHh - cellPadIn * 2);
  let overCells = 0;
  rowsIn.forEach(r => r.forEach((c, j) => {
    if (stillOver(c, effColW[j] != null ? effColW[j] : effColW[0], rowH, bodySzF)) overCells++;
  }));
  head.forEach((h, j) => {
    if (stillOver(h, effColW[j] != null ? effColW[j] : effColW[0], hRowH, headSzF)) overCells++;
  });
  if (overCells > 0 && typeof console !== 'undefined')
    console.warn(`addTable: ${overCells} 个单元格在字号下限（正文 ${bodySzF}pt/表头 ${headSzF}pt）仍超出分配行高 —— ` +
      '内容超承载，建议拆页/精简文案（行高已锁定，防压脚注）');
  /* M9：表头改 tonal（品牌浅底 + 墨色粗体），与 HTML 表头同一层级；整条实色表头在密表里过重 */
  const rows = [head.map(h => ({ text: h, options: { bold: true, color: STYLE.ink,
      fill: { color: STYLE.soft }, fontSize: headSzF, fontFace: STYLE.font, valign: 'middle' } }))]
    .concat(rowsIn.map((r, ri) => r.map((c, j) => {
      /* M3 版式 compare-table-hl：高亮列（推荐方案）= 主题色调底 + 加粗；其余行斑马纹 */
      const hl = opts.highlightCol != null && j === opts.highlightCol;
      return { text: String(c), options: { fontSize: bodySzF, bold: hl || (j === 0 && opts.highlightCol != null),
        color: hl ? STYLE.ink : STYLE.body, fontFace: STYLE.font, valign: 'middle',
        fill: { color: hl ? STYLE.soft : (opts.highlightCol != null && ri % 2 ? STYLE.surface : STYLE.bg) } } };
    })));
  /* rowH 数组：表头略高、正文均分剩余（pptxgenjs 支持逐行 rowH） */
  const rowHeights = [hRowH].concat(rowsIn.map(() => rowH));
  s.addTable(rows, { x, y, w, colW: tbl.colW, border: { pt: 0.75, color: STYLE.line },
    rowH: rowHeights, autoPage: false, margin: dense ? 2 : 5,
    /* 文本框自动收缩：PowerPoint 字体度量 ≠ 浏览器，宁可缩字号也不溢出 */
    fit: 'shrink', valign: 'middle' });
  return hRowH + rowsIn.length * rowH;
}

/* 封面 */
(function cover() {
  const s = base();
  const C = PT.cover;
  /* 深色主题：主色 30% 混入底色（与 HTML [data-theme=dark] .band--cover 同式），文字走 ink/body */
  const _mix = (a, b, t) => { const h = x => [0, 2, 4].map(i => parseInt(String(x).replace('#', '').substr(i, 2), 16));
    const A = h(a), B = h(b); return A.map((v, i) => Math.round(v * t + B[i] * (1 - t)).toString(16).padStart(2, '0')).join('').toUpperCase(); };
  const darkCover = THEME === 'dark';
  const cvFill = darkCover ? _mix(STYLE.accent, STYLE.bg, 0.3) : STYLE.accent;
  const cvTitle = darkCover ? STYLE.ink : STYLE.onAccent;
  const cvSub = darkCover ? STYLE.body : STYLE.soft;
  s.addShape('rect', { x: 0, y: 0, w: PW, h: PH, fill: { color: cvFill }, line: { type: 'none' } });
  s.addText(CONTENT.meta || '', { x: MX, y: C.metaY, w: CW, h: 0.4, fontFace: STYLE.font,
    fontSize: sz(11), color: darkCover ? STYLE.accent : STYLE.soft });
  const _ct = roleSz('coverHero', 44);  /* M9：封面主标题与 HTML 主视觉同比例（短标题用 coverHero 档，长标题回落 44 / 36） */
  const tSize = estTextH(CONTENT.title, CW - 1, _ct, 1.2) <= C.titleH ? _ct : (estTextH(CONTENT.title, CW - 1, sz(44), 1.25) > C.titleH ? sz(36) : sz(44));
  s.addText(BT(CONTENT.title, CW - 1, tSize), { x: MX, y: C.titleY, w: CW - 1, h: C.titleH, fontFace: STYLE.fontDisplay,
    fontSize: tSize, bold: SP.titleBold !== false, color: cvTitle });
  s.addText(CONTENT.subtitle || '', { x: MX, y: C.subtitleY, w: CW - 1, h: C.subtitleH,
    fontFace: STYLE.font, fontSize: sz(18), color: cvSub });
  const _cn = mergeNotes(CONTENT.coverNotes, [CONTENT.subtitle, CONTENT.meta].filter(Boolean).join('\n'));
  if (_cn) s.addNotes(_cn);
})();

/* Agenda（architecture 极简形态可省略 agenda → 不产出大纲页；
   >8 条自动双列；>12 条自动分页 Agenda I/II；长标题截断+全称入 notes；
   行高自适应防溢出；列填充与 HTML 统一为列优先） */
(function agenda() {
  if (!Array.isArray(CONTENT.agenda) || !CONTENT.agenda.length) return;
  const items = CONTENT.agenda;
  /* R4：单页容量 = 双列 × 每列最多 6 行（行高 ≥0.55in 可读） */
  const ROWS_PER_PAGE = 12;
  const pages = [];
  for (let i = 0; i < items.length; i += ROWS_PER_PAGE) pages.push(items.slice(i, i + ROWS_PER_PAGE));
  pages.forEach((pageItems, pi) => {
    const s = base();
    const sub = pages.length > 1 ? `（${pi + 1}/${pages.length}）` : '';
    head(s, CONTENT.agendaEyebrow != null ? CONTENT.agendaEyebrow : '目录', (CONTENT.agendaTitle || '报告大纲') + sub);
    const colN = pageItems.length > 8 ? 2 : 1;
    const perCol = Math.ceil(pageItems.length / colN);
    /* 预留 0.25in，避免末行底边落入 severe-overlap 安全网 */
    const availH = CONTENT_BOTTOM - CONTENT_TOP - 0.25;
    const rowH = Math.min(1.05, availH / Math.max(1, perCol));
    const numSize = rowH >= 0.85 ? sz(30) : (rowH >= 0.65 ? sz(22) : sz(18));
    const tSize = rowH >= 0.85 ? sz(16) : sz(14);
    const dSize = rowH >= 0.85 ? sz(12) : sz(11);
    const notes = [];
    pageItems.forEach((it, i) => {
      /* 列优先：先填左列再填右列（与 HTML grid-auto-flow:column 一致） */
      const col = Math.floor(i / perCol), row = i % perCol;
      const x = MX + col * (CW / colN), y = CONTENT_TOP + row * rowH;
      /* R4：标题按盒宽估算折行，超 1 行则截断并把全称沉 notes */
      const titleBoxW = CW / colN - 1.15;
      const rawTitle = String(it[1] || '');
      const titleEstW = estTextH(rawTitle, titleBoxW, tSize, 1.2);
      const maxTitleH = rowH * 0.55;
      let title = rawTitle;
      if (titleEstW > maxTitleH) {
        const maxChars = Math.max(10, Math.floor(rawTitle.length * (maxTitleH / titleEstW)));
        if (rawTitle.length > maxChars) {
          title = rawTitle.slice(0, maxChars - 1) + '…';
          notes.push(`条目 ${it[0]} 全称：${rawTitle}`);
        }
      }
      s.addText(it[0], { x, y, w: 0.9, h: rowH - 0.05, fontFace: STYLE.font, fontSize: numSize,
        bold: true, color: STYLE.accent, valign: 'top' });
      s.addText([
        { text: title + '\n', options: { fontSize: tSize, bold: true, color: STYLE.ink } },
        { text: it[2] || '', options: { fontSize: dSize, color: STYLE.body } },
      ], { x: x + 1.0, y: y + 0.03, w: titleBoxW, h: rowH - 0.08, fontFace: STYLE.font,
        valign: 'top', lineSpacing: tSize + 5 });
    });
    const _an = mergeNotes(pi === 0 ? CONTENT.agendaNotes : null, notes.join('\n'));
    if (_an) s.addNotes(_an);
  });
})();

/* ═══ M7 复合版式（信息密度）：论点（标题）+ 证据（图表）+ 解读（要点）+ 关键数字 ═══
 * 与 render_from_model.compose_* / lib_density 同口径：
 *  side 形态（bar / donut / exhibit）：顶部关键数字条 + 左主图 + 右解读栏；chart2 → 双图对照；minis → 主图 + 小图组
 *  band 形态（其余图表 / 信息图）：主图保持原几何，底部「关键数字 + 解读」带
 * keyMetrics 缺省时从单序列图表数据推导（只做算术，不编造）。compose:'off' 关闭。 */
const COMPOSE_SIDE = new Set(['bar', 'donut', 'exhibit']);
const COMPOSE_TOP = PT.common.headRuleY + 0.22;   // 复合页正文起点：分隔线下 0.22in（M10：从 0.33 收紧，高度还给主图）
const COMPOSE_BAND = new Set(['halftable', 'heatmap', 'bullet', 'treemap', 'marimekko', 'streamgraph', 'sankey', 'boxplot',
  'network', 'lane', 'pyramid', 'matrix', 'metrics']);
const DERIVABLE = new Set(['bar', 'hbar', 'donut', 'pie', 'line', 'area', 'lollipop', 'dotplot', 'rose', 'radialbar', 'funnel', 'vsbar']);
function fmtK(v, u) {
  const s = Math.abs(v - Math.round(v)) > 1e-9 ? v.toFixed(1).replace(/\.?0+$/, '') : String(Math.round(v));
  return s + (u || '');
}
function deriveKeyMetrics(ch, ptype) {
  ch = ch || {};
  let t = String(ch.type || 'bar').toLowerCase();
  if (ptype === 'donut') t = 'donut';
  const L = ch.labels || [], V = ch.values || [];
  if (!DERIVABLE.has(t) || L.length < 3 || V.length !== L.length) return [];
  if (!V.every(v => typeof v === 'number' && isFinite(v))) return [];
  const u = String(ch.unit || '');
  let imax = 0; V.forEach((v, i) => { if (v > V[imax]) imax = i; });
  if (t === 'donut' || t === 'pie') {
    const tot = V.reduce((a, b) => a + b, 0) || 1;
    const ord = V.map((v, i) => i).sort((a, b) => V[b] - V[a]);
    const top2 = (V[ord[0]] + V[ord[1]]) / tot * 100;
    return [[u === '%' ? fmtK(V[imax], u) : Math.round(V[imax] / tot * 100) + '%', L[imax] + '占比最高'],
      [Math.round(top2) + '%', '前两项合计（' + L[ord[0]] + '、' + L[ord[1]] + '）'],
      [String(V.length), '构成项']];
  }
  let imin = 0; V.forEach((v, i) => { if (v < V[imin]) imin = i; });
  const out = [[fmtK(V[imax], u), '最高 · ' + L[imax]], [fmtK(V[imin], u), '最低 · ' + L[imin]]];
  const a = V[0], b = V[V.length - 1];
  const temporal = L.every(x => /\d/.test(String(x)));
  if (!temporal) out.push([fmtK(V[imax] - V[imin], u === '%' ? 'pt' : u), '最高与最低之差']);
  else if (u === '%') out.push([(b - a >= 0 ? '+' : '') + fmtK(b - a, 'pt'), L[0] + ' → ' + L[L.length - 1]]);
  else if (a) out.push([(b / a).toFixed(1).replace(/\.0$/, '') + '×', L[L.length - 1] + ' 相对 ' + L[0]]);
  return out;
}
function composeKM(sec, type) {
  if (sec.compose === 'off') return [];
  const km = (sec.keyMetrics || []).filter(Boolean).map(metricKV);
  if (km.length) return km.slice(0, 4);
  if (type === 'halftable' || (sec.metrics && sec.metrics.length)) return [];
  return deriveKeyMetrics(sec.chart, type).slice(0, 3);
}
function composeOn(sec, type) {
  if (sec.compose === 'off') return null;
  const pts = (sec.points || sec.readout || []).filter(Boolean);
  const km = composeKM(sec, type);
  const extra = !!(sec.chart2 || (sec.minis && sec.minis.length));
  if (COMPOSE_SIDE.has(type) && (pts.length || km.length || extra)) return { form: 'side', pts: pts.map(pointKV), km };
  if (COMPOSE_BAND.has(type) && (pts.length || km.length)) return { form: 'band', pts: pts.map(pointKV), km };
  return null;
}
/* 关键数字条：n 张 tonal 卡横排 */
function kmStrip(s, km, x, y, w, h) {
  const n = km.length, gap = 0.2, cw = (w - gap * (n - 1)) / n;
  km.forEach((m, i) => {
    const cx = x + i * (cw + gap);
    s.addShape('roundRect', { x: cx, y, w: cw, h, rectRadius: rr(0.1), fill: { color: STYLE.surface },
      line: { type: 'none' }, objectName: 'km:card' });
    s.addText([
      { text: m[0], options: { fontFace: STYLE.fontDisplay, fontSize: sz(26), bold: true, color: STYLE.accent, breakLine: true } },
      { text: m[1], options: { fontFace: STYLE.font, fontSize: sz(11), color: STYLE.body } },
    ], { x: cx + 0.2, y: y + 0.04, w: cw - 0.4, h: h - 0.08, valign: 'middle' });
  });
}
/* 解读栏：编号要点，行高按估高分配 */
function readoutPanel(s, pts, x, y, w, h, opts) {
  opts = opts || {};
  s.addShape('roundRect', { x, y, w, h, rectRadius: 0.12, fill: { color: STYLE.soft }, line: { type: 'none' }, objectName: 'readout:bg' });
  const n = Math.max(1, pts.length), pad = 0.22, iw = w - pad * 2 - 0.42;
  const need = f => pts.reduce((a, p) => a + SOLVER.estTextH(p[0], iw, f + 1, 1.3) + SOLVER.estTextH(p[1], iw, f, 1.45) + 0.16, 0);
  const fz = snapFont(SOLVER.fitUp(need, (h - pad * 2) * 0.92, { max: opts.max || (MODE_NAME === 'presentation' ? 14 : 12), min: 10.5 }));
  /* 按每条估高排布，余量均分为条间距（整栏铺满、不顶部堆叠） */
  const hs = pts.map(p => estTextH(p[0], iw, sz(fz + 1), 1.35) + estTextH(p[1], iw, sz(fz), 1.5) + 0.16);
  const spare = Math.max(0, h - pad * 2 - hs.reduce((a2, b2) => a2 + b2, 0));
  const gapY = spare / (n + 1);
  let ry = y + pad + gapY * 0.6;
  pts.forEach((p, i) => {
    s.addShape('ellipse', { x: x + pad, y: ry + 0.04, w: 0.3, h: 0.3, fill: { color: STYLE.accent }, line: { type: 'none' } });
    s.addText(String(i + 1), { x: x + pad, y: ry + 0.04, w: 0.3, h: 0.3, align: 'center', valign: 'middle',
      fontFace: STYLE.font, fontSize: sz(10.5), bold: true, color: STYLE.onAccent || 'FFFFFF' });
    s.addText([
      { text: p[0], options: { fontSize: sz(fz + 1), bold: true, color: STYLE.ink, breakLine: !!p[1] } },
      { text: p[1], options: { fontSize: sz(fz), color: STYLE.body } },
    ], { x: x + pad + 0.42, y: ry, w: iw, h: hs[i], valign: 'top', fontFace: STYLE.font,
      lineSpacing: sz(fz * 1.45), paraSpaceBefore: 2, margin: 0 });
    ry += hs[i] + gapY;
  });
}
/* 解读横排卡（band 形态 / 双图对照下方）：关键数字卡 + 要点卡同一行 */
function readoutRow(s, km, pts, x, y, w, h) {
  const cells = km.map(m => ({ km: m })).concat(pts.map(p => ({ p })));
  if (!cells.length) return;
  const gap = 0.2;
  const kmW = km.length ? Math.min(1.9, w * 0.15) : 0;
  const ptW = pts.length ? (w - km.length * (kmW + gap) - gap * (pts.length - 1)) / pts.length : 0;
  let cx = x;
  const fz = snapFont(SOLVER.fitUp(f => Math.max(0, ...pts.map(p => SOLVER.estTextH(p[0], ptW - 0.4, f + 1, 1.3) +
    SOLVER.estTextH(p[1], ptW - 0.4, f, 1.4))) + 0.2, h, { max: 13.5, min: 10 }));
  cells.forEach(c => {
    const cw = c.km ? kmW : ptW;
    s.addShape('roundRect', { x: cx, y, w: cw, h, rectRadius: rr(0.1), fill: { color: c.km ? STYLE.surface : STYLE.soft },
      line: { type: 'none' }, objectName: c.km ? 'km:card' : 'readout:card' });
    if (c.km) {
      s.addText([
        { text: c.km[0], options: { fontFace: STYLE.fontDisplay, fontSize: (estTextH(c.km[0], cw - 0.28, roleSz('kpiCard', 24), 1.1) > 0.5 ? sz(18) : roleSz('kpiCard', 24)),  /* M9：卡内大数不随研究模式缩到正文级 */ bold: true, color: STYLE.accent, breakLine: true } },
        { text: c.km[1], options: { fontFace: STYLE.font, fontSize: sz(10), color: STYLE.body } },
      ], { x: cx + 0.14, y: y + 0.04, w: cw - 0.28, h: h - 0.08, valign: 'middle' });
    } else {
      s.addText([
        { text: c.p[0], options: { fontSize: sz(fz + 1), bold: true, color: STYLE.ink, breakLine: !!c.p[1] } },
        { text: c.p[1], options: { fontSize: sz(fz), color: STYLE.body } },
      ], { x: cx + 0.2, y: y + 0.06, w: cw - 0.4, h: h - 0.12, valign: 'middle', fontFace: STYLE.font, lineSpacing: sz(fz * 1.4) });
    }
    cx += cw + gap;
  });
}
function compChart(s, c, ptype, x, y, w, h) {
  const cc = Object.assign({}, c || {});
  if (ptype === 'donut' && !cc.type) cc.type = 'donut';
  if (!(cc.labels && cc.values)) return;
  chartBlock(s, cc, x, y, w, h, cc.colors || (cc.type === 'donut' ? donutColors(styleArg) : dataColors(styleArg)));
}
function capText(s, t, x, y, w) {
  if (t) s.addText(String(t), { x, y, w, h: 0.3, fontFace: STYLE.font, fontSize: sz(12), bold: true, color: STYLE.ink, valign: 'middle' });
}
function composeSide(s, sec, type, C, y0, y1) {
  let y = y0;
  if (C.km.length) { kmStrip(s, C.km, MX, y, CW, 0.85); y += 0.85 + 0.22; }
  const H = y1 - y;
  if (sec.chart2) {
    const rowH = C.pts.length ? Math.min(1.25, H * 0.32) : 0;
    const gw = (CW - 0.4) / 2, ch = H - rowH - (rowH ? 0.22 : 0) - 0.34;
    [[sec.chart, sec.cap || (sec.chart || {}).cap], [sec.chart2, (sec.chart2 || {}).cap]].forEach((cp, i) => {
      const gx = MX + i * (gw + 0.4);
      capText(s, cp[1], gx, y, gw);
      compChart(s, cp[0], i === 0 ? type : 'bar', gx, y + 0.34, gw, ch);
    });
    if (rowH) readoutRow(s, [], C.pts, MX, y1 - rowH, CW, rowH);
    return;
  }
  const minis = (sec.minis || []).filter(m => m && m.labels).slice(0, 2);
  const sideW = minis.length ? CW * 0.38 : Math.min(4.6, CW * 0.38);
  const mainW = CW - sideW - 0.3;
  if (!C.pts.length && !minis.length) { compChart(s, sec.chart, type, MX, y, CW, H); return; }
  if (minis.length) {
    /* 主图 + 解读行在左，小图组占右列全高（小图越高越可读） */
    const rowH = C.pts.length ? Math.min(1.1, H * 0.3) : 0;
    const mh = H - rowH - (rowH ? 0.2 : 0);
    compChart(s, sec.chart, type, MX, y, mainW, mh);
    if (rowH) readoutRow(s, [], C.pts.slice(0, 3), MX, y + mh + 0.2, mainW, rowH);
    const each = (H - 0.16 * (minis.length - 1)) / minis.length;
    minis.forEach((m, i) => {
      const my = y + i * (each + 0.16), mx = MX + mainW + 0.3;
      s.addShape('roundRect', { x: mx, y: my, w: sideW, h: each, rectRadius: rr(0.1), fill: { color: STYLE.surface }, line: { type: 'none' }, objectName: 'mini:bg' });
      capText(s, (m.cap || '') + (m.unit ? '（' + m.unit + '）' : ''), mx + 0.15, my + 0.04, sideW - 0.3);
      compChart(s, Object.assign({}, m, { _mini: true }), m.type === 'donut' ? 'donut' : 'bar', mx + 0.1, my + 0.32, sideW - 0.2, Math.max(0.6, each - 0.38));
    });
    return;
  }
  compChart(s, sec.chart, type, MX, y, mainW, H);
  readoutPanel(s, C.pts.slice(0, 5), MX + mainW + 0.3, y, sideW, H);
}

/* 章节页 · 按页型分发 */
/* M11：research 模式自动 Exhibit 编号与 HTML 同规则——作者一个 exhibitNo 都没写时，图表 / 信息图页按序编号 */
if (MODE_NAME === 'research' && !CONTENT.sections.some(x => x && x.exhibitNo)) {
  let exN = 0;
  const EXT = new Set(['exhibit', 'bar', 'halftable', 'donut', 'boxplot', 'marimekko', 'network', 'sankey', 'streamgraph', 'treemap']);
  CONTENT.sections.forEach((x) => { if (x && EXT.has(String(x.type || '').toLowerCase())) x.exhibitNo = ++exN; });
}
CONTENT.sections.forEach((sec) => {
  const type = sec.type || 'points';
  // Batch 2: honor layoutPreset (scaffold/recommend_layout → PPTX IR alignment)
  if (!sec.layoutPreset) {
    const _p2p = (LC.layoutSystem && LC.layoutSystem.pageToPreset) || {};
    if (_p2p[type]) sec.layoutPreset = _p2p[type];
  }
  /* M3：source（图表出处）与 cap（图题）同 HTML 一并落版——source 走来源行，cap 并入 Exhibit 帧头 */
  if (sec.source && !sec.footnote) sec.footnote = String(sec.source);
  const s = base();
  if (type !== 'quote' && type !== 'chapter') head(s, sec.eyebrow, sec.title, sec.lead);

  /* 正文区起点 / 终点（含 lead 与 so-what / 来源行 / 待核实条占位） */
  /* 非 exhibit 页型也可带 Exhibit 编号（帧头徽标；正文区下移让位，避免与主图重叠） */
  /* M7：复合版式页（图 + 解读 + 关键数字）正文区上提到分隔线下方，把纵向空间留给证据，而不是标题下的空带 */
  ANNOT = null;
  const _C = composeOn(sec, type);
  const exBadge = ((type !== 'exhibit' || _C) && sec.exhibitNo) ? exhibitBadge(sec.exhibitNo) + (sec.cap ? '　' + sec.cap : '') : null;
  const bodyY0 = sec.lead ? PT.common.bodyYWithLead : (_C ? COMPOSE_TOP : CONTENT_TOP);
  /* M12：半表半图页的 Exhibit 帧头归右侧图表（与 HTML .exhibit 框同构），左侧表格从正文顶开始 */
  const exRight = !!exBadge && type === 'halftable' && (!_C || _C.form === 'band');
  const bodyY = exBadge && !exRight ? bodyY0 + (_C ? 0.34 : 0.42) : bodyY0;  // M10：复合页 Exhibit 行与主图间距收紧
  if (exBadge && !exRight) {
    s.addText(exhibitRuns(sec.exhibitNo, sec.cap, sz(11.5)), { x: MX, y: bodyY0 - 0.06, w: CW, h: 0.3 });
  }
  const flagItems = Array.isArray(sec.flags) ? sec.flags.filter(Boolean) : [];
  const _F = PT.flagbar || { hdH: 0.26, rowH: 0.24, maxRows: 3, gap: 0.12 };
  const flagH = flagItems.length
    ? (_F.hdH + Math.min(_F.maxRows, flagItems.length) * _F.rowH + 0.06) : 0;
  let bodyBottom = chartBottom(!!sec.soWhat, !!(sec.footnote || sec.note));
  let flagY = 0;
  if (flagH) {
    /* 待核实条底对齐 contentBottom；与来源行 / so-what 同页时上移让位（不重叠） */
    flagY = CONTENT_BOTTOM - flagH;
    if (sec.footnote) flagY = Math.min(flagY, PT.exhibit.footnoteY - flagH - 0.06);
    if (sec.soWhat) flagY = Math.min(flagY, PT.exhibit.soWhatY - flagH - 0.06);
    /* withNote 时 flag 底不得越过 contentBottomWithNote（与 chartBottom / regionOf 同口径） */
    if (sec.footnote || sec.soWhat) flagY = Math.min(flagY, CONTENT_BOTTOM_NOTE - flagH);
    bodyBottom = Math.min(bodyBottom, flagY - (_F.gap || 0.12));
  }

  /* M7：复合版式（信息密度）——side 形态整页接管；band 形态先画底部解读带、收窄正文区再交给原页型 */
  if (_C && _C.form === 'band') {
    const bandH = Math.min(1.05, Math.max(0.85, (bodyBottom - bodyY) * 0.26));  // M9：解读带收一点，把高度还给图
    const hasFoot = !!(sec.footnote || sec.note);
    if (!flagH && (sec.soWhat || hasFoot)) {
      /* M10：结论条落到页底（底边让开页码 pageNumY），来源行贴在图下——与 HTML 的 figure 内来源行同序，图区多出 ~0.2in */
      const BA = PT.composeAnnot || { soWhatY: 6.4, soWhatH: 0.56, footH: 0.28 };
      const bandBot = sec.soWhat ? BA.soWhatY - 0.18 : CONTENT_BOTTOM_NOTE + 0.3;
      const bandTop = bandBot - bandH;
      readoutRow(s, _C.km.slice(0, 2), _C.pts.slice(0, 3), MX, bandTop, CW, bandH);
      ANNOT = { soWhat: sec.soWhat ? { x: MX, y: BA.soWhatY, w: CW, h: BA.soWhatH } : null,
        foot: hasFoot ? { x: MX, y: bandTop - 0.12 - BA.footH, w: CW - 1.2, h: BA.footH } : null };
      bodyBottom = hasFoot ? ANNOT.foot.y - 0.06 : bandTop - 0.2;
    } else if (type === 'metrics') {
      /* M12：指标页的解读带紧跟指标卡（HTML 是卡片行 + 解读行顺排），不再沉到页底留出大空档 */
      const mTop = bodyY + 0.15, mH = Math.min(2.3, Math.max(1.6, (bodyBottom - mTop - bandH - 0.25) * 0.62));
      readoutRow(s, _C.km.slice(0, 2), _C.pts.slice(0, 3), MX, mTop + mH + 0.25, CW, bandH);
      bodyBottom = mTop + mH;
    } else {
      readoutRow(s, _C.km.slice(0, 2), _C.pts.slice(0, 3), MX, bodyBottom - bandH, CW, bandH);
      bodyBottom -= bandH + 0.2;
    }
  }
  if (_C && _C.form === 'side') {
    composeSide(s, sec, type, _C, bodyY, Math.min(bodyBottom, CONTENT_BOTTOM_NOTE + 0.3));
  } else if (type === 'metrics') {
    const M = PT.metrics;
    const reg = Object.assign({}, REGIONS.regionOf('metrics', 'primary') ||
      { x: MX, y: M.bandY, w: CW, h: M.cardH });
    const ms = (sec.metrics || []).map(metricKV);
    const n = Math.max(1, ms.length);
    const g = cols(reg.w, n, M.gap);
    const mw = Math.min(M.maxW, g.w);
    const gx = reg.x + (reg.w - n * mw - (n - 1) * M.gap) / 2;
    if (_C) reg.y = Math.min(reg.y, bodyY + 0.15);
    const cardH = _C ? Math.min(2.3, bodyBottom - reg.y) : Math.min(reg.h, CONTENT_BOTTOM - reg.y);
    /* M7：带解读带时卡片收矮，数值与说明在卡内整体居中 */
    const vY = _C ? reg.y + Math.max(0.1, (cardH - M.valH - M.capH) / 2) : M.valY;
    const cY = _C ? vY + M.valH : M.capY;
    ms.forEach((m, i) => {
      const x = gx + i * (mw + M.gap);
      s.addShape('roundRect', { x, y: reg.y, w: mw, h: cardH, rectRadius: 0.09,
        fill: { color: STYLE.surface }, line: { color: STYLE.line, width: 0.75 } });
      const vSize = estTextH(m[0], mw - 0.2, roleSz('kpiHero', 36), 1.1) > cardH * 0.5 ? sz(28) : roleSz('kpiHero', 36);  // M9：与 HTML --fs-metric 同比例
      s.addText(m[0], { x, y: vY, w: mw, h: M.valH, align: 'center', fontFace: STYLE.fontDisplay,
        fontSize: vSize, bold: true, color: STYLE.accent });
      s.addText(m[1], { x: x + 0.15, y: cY, w: mw - 0.3, h: _C ? Math.min(M.capH, reg.y + cardH - cY - 0.06) : M.capH, align: 'center',
        fontFace: STYLE.font, fontSize: sz(11.5), color: STYLE.body });
    });
  } else if (type === 'dashboard') {
    /* M13 多图表综合页：关键数字条（可带图标）→ 2–4 张图（共用配色 / 坐标上限 / 图例，①②③④）→ 解读行 */
    const cs = DENSE.dashCharts(sec), n = Math.max(1, cs.length), leg = DENSE.dashLegend(cs);
    const km = (sec.keyMetrics || []).slice(0, DENSE.DASH_MAX_KM).map(DENSE.kv3);
    const pts = (sec.points || []).slice(0, DENSE.DASH_MAX_PTS).map(DENSE.pt3).map(p => [p[0], p[1]]);
    let y = bodyY + 0.05, yb = bodyBottom;
    if (km.length) {
      const kh = 0.86, gap = 0.2, cw = (CW - gap * (km.length - 1)) / km.length;
      km.forEach((m, i) => {
        const cx = MX + i * (cw + gap);
        s.addShape('roundRect', { x: cx, y, w: cw, h: kh, rectRadius: rr(0.1), fill: { color: STYLE.surface }, line: { type: 'none' }, objectName: 'km:card' });
        const ix = m[2] ? 0.62 : 0;
        if (m[2]) iconMark(s, m[2], cx + 0.18, y + (kh - 0.44) / 2, 0.44);
        s.addText([
          { text: m[0], options: { fontFace: STYLE.fontDisplay, fontSize: 24, bold: true, color: STYLE.accent, breakLine: true } },
          { text: m[1], options: { fontFace: STYLE.font, fontSize: sz(11), color: STYLE.body } },
        ], { x: cx + 0.18 + ix, y: y + 0.04, w: cw - 0.36 - ix, h: kh - 0.08, valign: 'middle', margin: 0 });
      });
      y += kh + 0.22;
    }
    if (leg.length) {
      const dc = dataColors(styleArg);
      s.addText(leg.map((nm, k) => ({ text: '■ ' + nm + '    ', options: { color: dc[k % dc.length] } })),
        { x: MX, y, w: CW, h: 0.28, fontFace: STYLE.font, fontSize: sz(10.5), margin: 0, objectName: 'dash:legend' });
      y += 0.34;
    }
    if (pts.length) { const rh = 0.98; readoutRow(s, [], pts, MX, yb - rh, CW, rh); yb -= rh + 0.2; }
    const colsN = n, rowsN = 1, gap = 0.22;   // M13：2–4 张图一行排开（坐标底边对齐，四张也不叠两行——两行时每张不足 1.2in，原生图表读不清）
    const cw = (CW - gap * (colsN - 1)) / colsN, ch = (yb - y - gap * (rowsN - 1)) / rowsN;
    cs.forEach((c, k) => {
      const cx = MX + (k % colsN) * (cw + gap), cy = y + Math.floor(k / colsN) * (ch + gap);
      s.addShape('roundRect', { x: cx, y: cy, w: cw, h: ch, rectRadius: rr(0.1), fill: { color: STYLE.surface }, line: { type: 'none' }, objectName: 'dash:cell' });
      s.addText(c.cap || '', { x: cx + 0.18, y: cy + 0.1, w: cw - 0.36, h: 0.3, align: 'center', fontFace: STYLE.font, fontSize: sz(11.5), bold: true, color: STYLE.faint, margin: 0 });
      const cc = Object.assign({}, c, leg.length ? { legend: false } : {});
      compChart(s, cc, cc.type === 'donut' ? 'donut' : 'bar', cx + 0.12, cy + 0.44, cw - 0.24, ch - 0.54);
    });
  } else if (type === 'magazine') {
    /* M13 杂志型：左大图（≈54%）+ 右栏「观点 → 大数字 → 带图标要点」，右栏整体垂直居中 */
    const im = sec.image || {};
    const iw = CW * 0.535, gap = 0.4, rx = MX + iw + gap, rw = CW - iw - gap;
    const top = bodyY + 0.05, h = bodyBottom - top;
    addImageEl(s, im.src || '', MX, top, iw, h, PT.image && PT.image.radius, { placeholder: !!im.placeholder || !im.src, layout: 'half', fit: im.fit });
    const ms = (sec.metrics || []).slice(0, DENSE.MAG_MAX_METRICS).map(DENSE.kv3);
    const pts = (sec.points || []).slice(0, DENSE.MAG_MAX_PTS).map(DENSE.pt3);
    const fzPull = sz(17), fzK = sz(13), fzV = sz(11.5);
    const pullH = sec.pull ? estTextH(sec.pull, rw, fzPull, 1.5) + 0.1 : 0;
    const mH = ms.length ? 0.95 : 0;
    const ptH = pts.map(p => Math.max(0.5, estTextH(p[0], rw - 0.62, fzK, 1.3) + (p[1] ? estTextH(p[1], rw - 0.62, fzV, 1.5) : 0) + 0.06));
    const blockH = pullH + (pullH ? 0.3 : 0) + mH + (mH ? 0.3 : 0) + ptH.reduce((a, b) => a + b, 0) + Math.max(0, pts.length - 1) * 0.18;
    let y = top + Math.max(0, (h - blockH) / 2);
    if (sec.pull) { s.addText(sec.pull, { x: rx, y, w: rw, h: pullH, fontFace: STYLE.fontDisplay, fontSize: fzPull, bold: true, color: STYLE.ink, valign: 'top', margin: 0 }); y += pullH + 0.3; }
    if (ms.length) {
      const mw = (rw - 0.2 * (ms.length - 1)) / ms.length;
      ms.forEach((m, i) => {
        const mx = rx + i * (mw + 0.2);
        s.addShape('roundRect', { x: mx, y, w: mw, h: mH, rectRadius: rr(0.1), fill: { color: STYLE.surface }, line: { type: 'none' }, objectName: 'km:card' });
        const ix = m[2] ? 0.56 : 0;
        if (m[2]) iconMark(s, m[2], mx + 0.16, y + (mH - 0.4) / 2, 0.4);
        s.addText([
          { text: m[0], options: { fontFace: STYLE.fontDisplay, fontSize: 32, bold: true, color: STYLE.accent, breakLine: true } },
          { text: m[1], options: { fontFace: STYLE.font, fontSize: sz(10.5), color: STYLE.body } },
        ], { x: mx + 0.16 + ix, y: y + 0.04, w: mw - 0.3 - ix, h: mH - 0.08, valign: 'middle', margin: 0 });
      });
      y += mH + 0.3;
    }
    pts.forEach((p, i) => {
      iconMark(s, p[2] || p[0], rx, y + 0.02, 0.42);
      s.addText([
        { text: p[0], options: { fontSize: fzK, bold: true, color: STYLE.ink, breakLine: !!p[1] } },
        ...(p[1] ? [{ text: p[1], options: { fontSize: fzV, color: STYLE.body } }] : []),
      ], { x: rx + 0.6, y, w: rw - 0.62, h: ptH[i], fontFace: STYLE.font, valign: 'top', margin: 0 });
      y += ptH[i] + 0.18;
    });
  } else if (type === 'focus') {
    focusPage(s, sec, bodyY, bodyBottom);
  } else if (type === 'kpi') {
    const K = PT.kpi;
    const hreg = REGIONS.regionOf('kpi', 'hero') ||
      { x: MX, y: K.heroY, w: CW * K.heroW, h: K.heroH };
    const hro = sec.hero || [];
    const kpiBottom = chartBottom(!!sec.soWhat, !!(sec.footnote || sec.note)) - 0.05;
    const kdivX = MX + CW * K.dividerX;
    /* M0：hero 落在与正文等高的 MD3 tonal 卡片内（垂直居中），替代「巨号数字 + 竖分隔线」——
       原版下半页大面积空白、重心偏上 */
    const hTop = bodyY, hBot = Math.min(kpiBottom, CONTENT_BOTTOM_NOTE + 0.3);
    const hCardW = kdivX - MX - 0.1;
    s.addShape('roundRect', { x: MX, y: hTop, w: hCardW, h: hBot - hTop, rectRadius: 0.12,
      fill: { color: STYLE.soft }, line: { type: 'none' } });
    const hBlockH = hreg.h + 1.15;
    const hy = hTop + Math.max(0.2, ((hBot - hTop) - hBlockH) / 2);
    s.addText(String(hro[0] || ''), { x: MX + 0.4, y: hy, w: hCardW - 0.8, h: hreg.h,
      fontFace: STYLE.fontDisplay, fontSize: sz(64), bold: true, color: STYLE.accent });
    s.addText(String(hro[1] || ''), { x: MX + 0.45, y: hy + hreg.h - 0.1, w: hCardW - 0.9, h: 0.55,
      fontFace: STYLE.font, fontSize: sz(15), bold: true, color: STYLE.ink });
    if (hro[2]) s.addText('▲ ' + hro[2], { x: MX + 0.45, y: hy + hreg.h + 0.5, w: hCardW - 0.9, h: 0.4,
      fontFace: STYLE.font, fontSize: sz(12), bold: true, color: STYLE.accent });
    const mreg = { x: kdivX + 0.35, y: hTop, w: PW - MX - (kdivX + 0.35), h: hBot - hTop };
    const kAvail = Math.max(0.8, hBot - mreg.y);
    const kmets = sec.metrics || [];
    /* 容量按最小允许行高判断，行高按全部指标自适应压缩 ——
       原 kCap 用默认行高先截断，导致第 N+1 个指标被静默丢弃（禁静默丢数据） */
    const K_MINROWH = 0.42;
    const kCap = Math.max(1, Math.floor(kAvail / K_MINROWH));
    const kRows = Math.min(kmets.length, kCap);
    if (kRows < kmets.length)
      console.warn(`[build_pptx] 警告：KPI 页「${sec.title || ''}」支撑指标 ${kmets.length} 个超出容量（${kAvail.toFixed(2)}in），` +
        `仅渲染前 ${kRows} 个 —— 建议拆页`);
    const kHasPts = (sec.points || []).filter(Boolean).length > 0;
    const kRowH = kHasPts ? fitRowH(kAvail, kRows, K.metricRowH, K_MINROWH)
      : Math.max(K_MINROWH, Math.min(1.4, kAvail / Math.max(1, kRows)));
    kmets.slice(0, kRows).map(metricKV).forEach((m, i) => {
      const ky = mreg.y + i * kRowH;
      if (i > 0) s.addShape('rect', { x: mreg.x, y: ky - 0.05, w: mreg.w, h: 0.01,
        fill: { color: STYLE.line }, line: { type: 'none' } });
      s.addText(m[0], { x: mreg.x, y: ky, w: mreg.w, h: Math.min(0.55, kRowH * 0.62),
        fontFace: STYLE.fontDisplay, fontSize: sz(22), bold: true, color: STYLE.accent });
      s.addText(m[1], { x: mreg.x, y: ky + Math.min(0.55, kRowH * 0.62), w: mreg.w,
        h: Math.max(0.24, kRowH - Math.min(0.55, kRowH * 0.62)), fontFace: STYLE.font,
        fontSize: sz(10.5), color: STYLE.faint });
    });
    /* 要点：指标行下方续排，k/v 双色（与 bar 侧栏同口径）；容量不足时显式告警（禁静默丢数据） */
    const kpts = (sec.points || []).filter(Boolean);
    const kpRowH = 0.5;
    const kpY0 = mreg.y + kRows * kRowH + 0.12;
    const kpCap = Math.max(0, Math.floor((hBot - kpY0) / kpRowH));
    if (kpts.length > kpCap)
      console.warn(`[build_pptx] 警告：KPI 页「${sec.title || ''}」要点 ${kpts.length} 条超出容量，仅渲染前 ${kpCap} 条 —— 建议拆页`);
    kpts.slice(0, kpCap).forEach((p, i) => {
      const kv = pointKV(p), kk = kv[0], vv = kv[1];
      const ky = kpY0 + i * kpRowH;
      s.addShape('rect', { x: mreg.x, y: ky + kpRowH / 2 - 0.06, w: 0.12, h: 0.12,
        fill: { color: STYLE.accent }, line: { type: 'none' } });
      s.addText([
        { text: kk + (kk && vv ? '　' : ''), options: { fontSize: sz(12), bold: true, color: STYLE.ink } },
        { text: vv, options: { fontSize: sz(11), color: STYLE.body } },
      ], { x: mreg.x + 0.26, y: ky, w: mreg.w - 0.32, h: kpRowH - 0.04,
        fontFace: STYLE.font, valign: 'middle' });
    });
  } else if (type === 'comparison') {
    const C2 = PT.comparison;
    const lreg = REGIONS.regionOf('comparison', 'left') ||
      { x: MX, y: C2.panelY, w: (CW - C2.panelGap) / 2, h: C2.panelH };
    const rreg = REGIONS.regionOf('comparison', 'right') ||
      { x: MX + (CW + C2.panelGap) / 2, y: C2.panelY, w: (CW - C2.panelGap) / 2, h: C2.panelH };
    if (sec.variant === 'problem-solution') {   /* 箭头通道 0.9in */
      const g = 0.9, pw = (lreg.w + rreg.w + (rreg.x - lreg.x - lreg.w) - g) / 2;
      rreg.x = lreg.x + pw + g; lreg.w = pw; rreg.w = pw;
    }
    const cw2 = lreg.w;
    const cpy = lreg.y, cph = lreg.h;
    const rx2 = rreg.x;
    s.addShape('roundRect', { x: lreg.x, y: cpy, w: cw2, h: cph, rectRadius: 0.09,
      fill: { color: STYLE.surface }, line: { color: STYLE.line, width: 0.75 } });
    s.addShape('roundRect', { x: rx2, y: cpy, w: cw2, h: cph, rectRadius: 0.09,
      fill: { color: STYLE.soft }, line: { type: 'none' } });
    [{ x: lreg.x, d: sec.left || {} }, { x: rx2, d: sec.right || {} }].forEach((sd) => {
      const isRight = sd.x === rx2;
      const pts = (sd.d.points || []).map(pointKV);
      /* 行高按面板可用高度自适应 */
      const avail = cph - C2.titleH - 0.34;
      const rowH = fitRowH(avail, pts.length, C2.rowH, 0.34);
      const fzBase = rowH < 0.5 ? 11.5 : 13;   /* 基准 pt（presentation 比例尺） */
      const fz = sz(fzBase), fzSm = sz(fzBase - 1);   /* 各映射一次，避免二次缩放 */
      s.addText(sd.d.title || '', { x: sd.x + 0.22, y: cpy + 0.18, w: cw2 - 0.44, h: C2.titleH,
        fontFace: STYLE.font, fontSize: sz(15), bold: true, color: isRight ? STYLE.accent : STYLE.ink });
      pts.forEach((p, pi) => {
        const py = cpy + 0.18 + C2.titleH + 0.16 + pi * rowH;
        s.addShape('rect', { x: sd.x + 0.24, y: py + rowH / 2 - 0.06, w: 0.12, h: 0.12,
          fill: { color: isRight ? STYLE.accent : STYLE.faint }, line: { type: 'none' } });
        s.addText([
          { text: p[0] + '　', options: { fontSize: fz, bold: true, color: STYLE.ink } },
          { text: p[1], options: { fontSize: fzSm, color: STYLE.body } },
        ], { x: sd.x + 0.5, y: py, w: cw2 - 0.75, h: rowH - 0.04, fontFace: STYLE.font, valign: 'top' });
      });
    });
    /* M3 版式 problem-solution：两面板之间放方向箭头（原生 rightArrow，可编辑） */
    if (sec.variant === 'problem-solution') {
      const ax = lreg.x + cw2, aw = rx2 - ax;
      s.addShape('rightArrow', { x: ax + aw * 0.12, y: cpy + cph / 2 - 0.22, w: aw * 0.76, h: 0.44,
        fill: { color: STYLE.accent }, line: { type: 'none' } });
    }
    /* R2：verdict 与 soWhat 共用 annotation 槽位——只画一个（verdict 优先，语义更具体）。
       两者同页必须互斥，否则结论条整条叠印。 */
    if (sec.verdict) {
      const vreg = REGIONS.regionOf('exhibit', 'annotation') ||
        { x: MX, y: PT.exhibit.soWhatY, w: CW, h: 0.62 };
      /* M9：与 HTML .sowhat 同为 tonal 满铺（soft 底 + ink 字），不加「结论」标签 */
      s.addShape('rect', { x: vreg.x, y: vreg.y, w: vreg.w, h: vreg.h,
        fill: { color: STYLE.soft }, line: { type: 'none' }, objectName: trName('soWhat') });
      s.addText([
        { text: sec.verdict, options: { fontSize: sz(12.5), bold: true, color: STYLE.ink } },
      ], { x: vreg.x + 0.22, y: vreg.y + 0.06, w: vreg.w - 0.44, h: vreg.h - 0.12, fontFace: STYLE.font,
        valign: 'middle', objectName: trName('soWhat') });
    }
  } else if (type === 'chapter') {
    /* M3 章节扉页（结构家族）：主题色调满铺 + 超大章节号 + 章标题 / 导语 + 本章看点清单。
       无左侧竖条、无装饰引号；本章看点 = 本章各页的结论式标题（≤5 条），扫读即知本章要回答什么。 */
    const num = String(sec.number || (String(sec.eyebrow || '').match(/^\s*(\d{1,2})/) || [])[1] || '').padStart(2, '0');
    s.addShape('rect', { x: 0, y: 0, w: PW, h: PH, fill: { color: STYLE.soft }, line: { type: 'none' } });
    const CH = PT.chapter, nW = CH.numW;
    if (num !== '00' && num) s.addText(num, { x: MX - 0.08, y: CH.numY, w: nW, h: 2.6, fontFace: STYLE.fontDisplay,
      fontSize: (MTS[MODE_NAME] || MTS.presentation).chapterNum || 96, bold: true, color: STYLE.accent, valign: 'top', margin: 0 });
    const tx = MX + nW + 0.3, tw = CW - nW - 0.3;
    const ebText = String(sec.eyebrow || '').replace(/^\s*\d{1,2}\s*[·・\-—]\s*/, '') || ('第 ' + num + ' 章');
    s.addText(ebText, { x: tx, y: CH.titleY - 0.42, w: tw, h: 0.4, fontFace: STYLE.font, fontSize: sz(11), bold: true,
      color: STYLE.accent, charSpacing: 2 });
    s.addText(BT(sec.title || '', tw, roleSz('chapterTitle', 32)), { x: tx, y: CH.titleY, w: tw, h: 1.25, fontFace: STYLE.fontDisplay, fontSize: roleSz('chapterTitle', 32),
      bold: SP.titleBold !== false, color: STYLE.ink, valign: 'top', fit: 'shrink' });
    let cy = 3.0;
    if (sec.lead) {
      s.addText(sec.lead, { x: tx, y: cy, w: tw, h: 0.8, fontFace: STYLE.font, fontSize: sz(15), color: STYLE.body, valign: 'top' });
      cy += 0.9;
    }
    const items = (sec.items || []).slice(0, CH.maxItems);
    if (items.length) {
      const rowH = Math.min(CH.itemRowH, (CONTENT_BOTTOM - cy) / items.length);
      items.forEach((it, k) => {
        const y = cy + k * rowH;
        s.addShape('rect', { x: tx, y: y, w: tw, h: 0.01, fill: { color: STYLE.line }, line: { type: 'none' } });
        s.addText(String(k + 1).padStart(2, '0'), { x: tx, y: y, w: 0.6, h: rowH, fontFace: STYLE.font,
          fontSize: sz(12), bold: true, color: STYLE.accent, valign: 'middle' });
        s.addText(String(it), { x: tx + 0.6, y: y, w: tw - 0.6, h: rowH, fontFace: STYLE.font,
          fontSize: sz(13.5), color: STYLE.ink, valign: 'middle' });
      });
    }
  } else if (type === 'quote') {
    const Q = PT.quote;
    const qreg = REGIONS.regionOf('quote', 'primary') ||
      { x: MX + 1.05, y: Q.textY, w: CW - 2.1, h: Q.textH };
    /* 金句页用主题一致强调带（accent-soft 底）——浅色主题下不再出现深色页 */
    s.addShape('rect', { x: 0, y: 0, w: PW, h: PH, fill: { color: STYLE.soft }, line: { type: 'none' } });
    if (CHROME_FLAGS.showEyebrow && sec.eyebrow) s.addText(sec.eyebrow, { x: MX, y: PT.common.headEyebrowY, w: CW, h: 0.4,
      fontFace: STYLE.font, fontSize: sz(11), bold: true, color: STYLE.accent, charSpacing: 2 });
    s.addText(BT(sec.title, CW, sz(30)), { x: MX, y: PT.common.headTitleY, w: CW, h: 1.0,
      fontFace: STYLE.fontDisplay, fontSize: sz(30), bold: true, color: STYLE.ink });
    s.addShape('rect', { x: MX, y: PT.common.headRuleY, w: 0.9, h: 0.045, fill: { color: STYLE.accent }, line: { type: 'none' } });
    /* M0：去掉装饰大引号；金句页必须带证据（metrics：2–4 个支撑数字），否则 strict 门禁拦截。
       有证据时：金句居上、证据卡片行居下，整页一屏、无空页。 */
    const qm = (sec.metrics || []).map(metricKV).slice(0, 4);
    const qBot = Math.min(chartBottom(!!sec.soWhat, !!(sec.footnote || sec.note)) - 0.05, CONTENT_BOTTOM_NOTE + 0.3);
    const evH = qm.length ? 1.45 : 0;
    const qTop = bodyY;
    const qTextH = qm.length ? Math.max(1.0, (qBot - qTop) - evH - 0.95) : qreg.h;
    const qY = qm.length ? qTop : qreg.y;
    /* M12：有证据时金句框左右各收 1.7in（对齐 HTML 金句 max-width 居中框），文字居中 */
    const qW = qm.length ? CW - 3.4 : qreg.w, qX = qm.length ? MX + 1.7 : qreg.x;
    const qSize = qm.length
      ? ([26, 22, 20].map(sz).find(f => estLines(sec.quote, qW, f) === 1) ||   /* M12：能一行放下就取一行的最大字号，避免两行末尾孤字 */
         [26, 22, 20, 16].map(sz).find(f => estTextH(sec.quote, qW, f, 1.4) <= qTextH) || sz(16))
      : (estTextH(sec.quote, qreg.w, sz(20), 1.4) > qTextH ? sz(16) : sz(20));
    /* M12：金句与署名居中（与 HTML .shead--center 同构）；有证据时「金句 → 署名 → 出处 → 证据卡」顺排成一组，
       整组在正文区垂直居中（HTML band--fit 同理），不再把金句框撑满、证据卡沉底 */
    const qH = qm.length ? Math.min(qTextH, estTextH(sec.quote, qW, qSize, 1.4) + 0.2) : qTextH;
    const blockH = qH + 0.47 + (sec.context ? 0.42 : 0) + 0.35 + evH;
    const qY2 = qm.length ? qTop + Math.max(0, (qBot - qTop - blockH) / 2) : qY;
    s.addText(sec.quote, { x: qX, y: qY2, w: qW, h: qH, align: qm.length ? 'center' : 'left',
      fontFace: STYLE.fontDisplay, fontSize: qSize, bold: true, color: STYLE.ink, valign: 'middle' });
    const authY = qm.length ? qY2 + qH + 0.02 : Q.authorY;
    if (sec.author) s.addText('—— ' + sec.author, { x: qm.length ? qX : qreg.x, y: authY, w: qm.length ? qW : qreg.w, h: 0.45, align: qm.length ? 'center' : 'right',
      fontFace: STYLE.font, fontSize: sz(13), bold: true, color: STYLE.accent });
    if (sec.context) s.addText(sec.context, { x: qm.length ? qX : qreg.x, y: qm.length ? authY + 0.45 : Q.contextY, w: qm.length ? qW : qreg.w, h: 0.4, align: qm.length ? 'center' : 'right',
      fontFace: STYLE.font, fontSize: sz(11), color: STYLE.faint });
    const evY = authY + 0.47 + (sec.context ? 0.42 : 0) + 0.33;
    if (qm.length) {
      const g = cols(CW, qm.length, 0.25);
      const ey = Math.min(qBot - evH, evY);
      qm.forEach((m, i) => {
        const ex = MX + i * g.step;
        s.addShape('roundRect', { x: ex, y: ey, w: g.w, h: evH, rectRadius: 0.09,
          fill: { color: STYLE.bg }, line: { type: 'none' } });
        s.addText(m[0], { x: ex + 0.25, y: ey + 0.12, w: g.w - 0.5, h: 0.7,
          fontFace: STYLE.fontDisplay, fontSize: sz(28), bold: true, color: STYLE.accent, valign: 'bottom' });
        s.addText(m[1], { x: ex + 0.25, y: ey + 0.84, w: g.w - 0.5, h: evH - 0.96,
          fontFace: STYLE.font, fontSize: sz(11), color: STYLE.body, valign: 'top' });
      });
    }
  } else if (type === 'image') {
    /* 素材图片页：full 版心全宽 / half 左图右注 / bleed 通栏出血 / grid 多图网格 /
       compare 双图对比 / wall Logo 墙；无图（image.placeholder）走原生占位框 + 标签文本 */
    const IM = PT.image;
    const img = sec.image || {};
    const items = Array.isArray(img.items) ? img.items.filter(Boolean) : [];
    const layout = String(img.layout || (items.length > 1 ? 'grid' : 'full')).toLowerCase();
    const fit = String(img.fit || IMG.fitDefault || 'cover').toLowerCase();
    const isPh = !!img.placeholder;
    /* R6：图片区须按注释带感知下界收敛——so-what/来源行并存时图片底边不得越过注释带顶
      （ANNOTATION_BAND_OVERLAP）；有图注时图注沉底注释带，图片区上界取 min。 */
    const iBottom = img.caption ? Math.min(bodyBottom, CONTENT_BOTTOM_NOTE) : bodyBottom;
    const ireg = REGIONS.regionOf('image', 'primary',
      { top: bodyY, caption: !!img.caption, bottom: iBottom }) ||
      { x: MX, y: Math.max(IM.y, bodyY), w: CW, h: IM.h };
    const iy = ireg.y;
    const capH = img.caption ? 0.32 : 0;
    const ih = Math.max(1.2, ireg.h);
    const capYImg = imageLayoutShapes(s, layout, img, items, sec.points || [], isPh, fit, iy, iy + ih);
    /* 图注沉底注释带（annotation self 豁免位）；要点存在时不随之上移，避免被判侵入注释带 */
    if (img.caption) s.addText(img.caption, { x: MX, y: Math.max(capYImg + 0.04, CONTENT_BOTTOM_NOTE + 0.03),
      w: CW, h: capH, fontFace: STYLE.font, fontSize: sz(10.5), color: STYLE.faint });
  } else if (type === 'donut') {
    const dcn = sec.chart || {};
    if (dcn.labels && dcn.values) {
      const d = PT.donut;
      const dcols = dcn.colors || donutColors(styleArg);
      const usedR = nativeDonutChart(s, dcn, dcols, Math.min(bodyBottom, CONTENT_BOTTOM_NOTE + 0.3), bodyY) || d.r;
      const dcy = d._cy || d.centerY;
      const holeR = d.holeR * (usedR / d.r);
      const hb = holeR * 2;
      let total = 0; dcn.values.forEach(v => { total += Math.max(0, v); });
      const totalStr = (Math.round(total * 10) / 10) + (dcn.unit || '');
      /* 单位是 % 且合计≈100：中心写「100%」没有信息量 → 中心标签升为主文字；图例不再重复一列占比 */
      const pctIsUnit = (dcn.unit || '') === '%' && Math.abs(total - 100) < 0.5 && dcn.centerTotal !== true;
      if (pctIsUnit && dcn.centerLabel) {
        s.addText(String(dcn.centerLabel), { x: d.centerX - holeR, y: dcy - 0.3, w: hb, h: 0.6, align: 'center',
          fontFace: STYLE.fontDisplay, fontSize: sz(15), bold: true, color: STYLE.ink, valign: 'middle', fit: 'shrink' });
      }
      if (dcn.centerTotal !== false && !pctIsUnit) s.addText(totalStr, { x: d.centerX - holeR, y: dcy - 0.42, w: hb, h: 0.5, align: 'center',
        fontFace: STYLE.fontDisplay, fontSize: sz(20), bold: true, color: STYLE.ink, valign: 'middle' });
      const _cl = dcn.centerLabel != null ? dcn.centerLabel : '合计';
      if (_cl && !pctIsUnit) s.addText(_cl, { x: d.centerX - holeR, y: dcy + 0.08, w: hb, h: 0.35, align: 'center',
        fontFace: STYLE.font, fontSize: sz(9.5), color: STYLE.faint, valign: 'middle' });
      const n = Math.max(1, dcn.labels.length);
      const maxLegH = Math.max(1.2, bodyBottom - (d.centerY - 1.7));
      /* 要点：与图例共用右列。有要点时右列改顶对齐堆叠（图例行高压缩 + 要点续排），
         顶锚取 bodyY 以吃满纵向空间；无要点时保持原有环图居中图例（不改变现有版式）。 */
      const dpts = (sec.points || []).filter(Boolean);
      const dpRowH = 0.5;
      let legRowH, legY0;
      if (dpts.length) {
        const colAvail = Math.max(1.5, bodyBottom - bodyY - 0.04);
        const ptsH = dpts.length * dpRowH;
        legRowH = Math.max(0.32, Math.min(d.legendRowH, (colAvail - 0.1 - ptsH) / n));
        legY0 = bodyY;
      }
      /* M1：无要点时图例改为「图例卡」——行高由求解器撑满右列（每行一张 tonal 卡），不再三行小字挤在中部 */
      let legGap = 0;
      if (!dpts.length) {
        const lsol = SOLVER.rows(Math.min(bodyBottom, CONTENT_BOTTOM_NOTE + 0.3) - bodyY, n, { pref: d.legendRowH, min: 0.3, max: 1.1, gap: 0.16 });
        legRowH = lsol.size; legGap = lsol.gap; legY0 = bodyY + lsol.offset;
        dcn.labels.forEach((lb, i) => s.addShape('roundRect', { x: d.legendX - 0.2, y: legY0 + i * (legRowH + legGap),
          w: d.legendPctX + d.legendPctW - d.legendX + 0.4, h: legRowH, rectRadius: rr(0.1),
          fill: { color: STYLE.surface }, line: { type: 'none' }, objectName: 'legend:card' }));
      }
      const sum2 = total || 1;
      dcn.labels.forEach((lb, i) => {
        const v = dcn.values[i] || 0;
        const y = legY0 + i * (legRowH + legGap);
        s.addShape('ellipse', { x: d.legendX, y: y + legRowH / 2 - 0.08, w: 0.16, h: 0.16,
          fill: { color: dcols[i % dcols.length] }, line: { type: 'none' } });
        s.addText(lb, { x: d.legendX + 0.3, y, w: pctIsUnit ? 3.2 : d.legendLabelW, h: legRowH, valign: 'middle',
          fontFace: STYLE.font, fontSize: sz(12), bold: true, color: STYLE.ink });
        s.addText(String(v) + (dcn.unit || ''), { x: pctIsUnit ? d.legendPctX : d.legendX + 3.8, y,
          w: pctIsUnit ? d.legendPctW : d.legendValW, h: legRowH, align: 'right',
          valign: 'middle', fontFace: STYLE.font, fontSize: sz(12), bold: true, color: STYLE.body });
        if (pctIsUnit) {
          /* 占比本身就是数值：中间放一条细占比条代替重复的百分比列 */
          const bx = d.legendX + 3.6, bw = d.legendPctX - bx - 0.1, bh = 0.1, by = y + legRowH / 2 - bh / 2;
          s.addShape('rect', { x: bx, y: by, w: bw, h: bh, fill: { color: STYLE.line }, line: { type: 'none' } });
          s.addShape('rect', { x: bx, y: by, w: Math.max(0.02, bw * Math.max(0, v) / 100), h: bh,
            fill: { color: dcols[i % dcols.length] }, line: { type: 'none' } });
        }
        if (!pctIsUnit) s.addText((Math.round(v / sum2 * 1000) / 10) + '%', { x: d.legendPctX, y, w: d.legendPctW, h: legRowH,
          align: 'right', valign: 'middle', fontFace: STYLE.font, fontSize: sz(10.5), color: STYLE.faint });
      });
      const dpY0 = legY0 + n * (legRowH + legGap) + 0.1;
      const dpCap = Math.max(0, Math.floor((bodyBottom - dpY0) / dpRowH));
      dpts.slice(0, dpCap).forEach((p, i) => {
        const kk = Array.isArray(p) ? String(p[0] || '') : String((p && p.t) || '');
        const vv = Array.isArray(p) ? String(p[1] || '')
          : (p && typeof p === 'object' ? String(p.d || '') : String(p == null ? '' : p));
        const py = dpY0 + i * dpRowH;
        s.addShape('rect', { x: d.legendX, y: py + dpRowH / 2 - 0.06, w: 0.12, h: 0.12,
          fill: { color: STYLE.accent }, line: { type: 'none' } });
        s.addText([
          { text: kk + (kk && vv ? '　' : ''), options: { fontSize: sz(12), bold: true, color: STYLE.ink } },
          { text: vv, options: { fontSize: sz(11), color: STYLE.body } },
        ], { x: d.legendX + 0.26, y: py, w: d.legendLabelW + d.legendValW - 0.3, h: dpRowH - 0.04,
          fontFace: STYLE.font, valign: 'middle' });
      });
    }
  } else if (type === 'heatmap') {
    /* 热力矩阵：行 × 列 + 4 级色阶（surface-1 → accent-soft → accent-soft-2 → accent） */
    const H = PT.heatmap;
    const hreg = Object.assign({}, REGIONS.regionOf('heatmap', 'primary', { bottom: bodyBottom }) ||
      { x: MX, y: H.y, w: CW, h: bodyBottom - H.y });
    /* M7：带解读带时上移到正文起点，并为色阶图例预留高度（此前图例与下方元素叠印） */
    if (_C) { const top = Math.min(hreg.y, bodyY); hreg.h = bodyBottom - top - 0.42; hreg.y = top; }
    const rowsH = sec.rowHeads || [], colsH = sec.colHeads || [];
    const cells = sec.cells || [];
    const nR = Math.max(1, rowsH.length), nC = Math.max(1, colsH.length);
    const availH = hreg.h;
    const rowH = fitRowH(availH - H.headH, nR, H.cellH, 0.24);
    const gridW = hreg.w - H.labelW;
    const cw = (gridW - (nC - 1) * H.cellGap) / nC;
    const flat = cells.flat().map(Number).filter(v => !isNaN(v));
    const vmax = flat.length ? Math.max.apply(null, flat) : 1;
    const vmin = flat.length ? Math.min.apply(null, flat) : 0;
    const levels = [STYLE.surface, STYLE.soft, mixHex(STYLE.soft, STYLE.accent, 0.3), STYLE.accent];  // M9：第 3 级与 HTML accent-soft-2 同色系，不再落到灰线色
    colsH.forEach((ch, ci) => {
      s.addText(ch, { x: hreg.x + H.labelW + ci * (cw + H.cellGap), y: hreg.y, w: cw, h: H.headH,
        align: 'center', valign: 'middle', fontFace: STYLE.font, fontSize: sz(11), bold: true, color: STYLE.body });
    });
    const rowsUse = Math.min(nR, cells.length);
    for (let ri = 0; ri < rowsUse; ri++) {
      const y = hreg.y + H.headH + 0.08 + ri * (rowH + H.cellGap);
      s.addText(rowsH[ri] || '', { x: hreg.x, y, w: H.labelW - 0.15, h: rowH, align: 'right', valign: 'middle',
        fontFace: STYLE.font, fontSize: sz(11), bold: true, color: STYLE.body });
      for (let ci = 0; ci < nC; ci++) {
        const v = Number((cells[ri] || [])[ci]);
        const has = !isNaN(v);
        const p = (has && vmax > vmin) ? (v - vmin) / (vmax - vmin) : 0.5;
        const lvl = p >= 0.86 ? 3 : (p >= 0.55 ? 2 : (p >= 0.25 ? 1 : 0));
        const onAcc = lvl >= 3;
        s.addShape('roundRect', { x: hreg.x + H.labelW + ci * (cw + H.cellGap), y, w: cw, h: rowH,
          rectRadius: 0.05, fill: { color: levels[lvl] },
          line: lvl === 0 ? { color: STYLE.line, width: 0.75 } : { type: 'none' } });
        s.addText(has ? (String(v) + (sec.unit || '')) : '—',
          { x: hreg.x + H.labelW + ci * (cw + H.cellGap), y, w: cw, h: rowH, align: 'center', valign: 'middle',
            fontFace: STYLE.font, fontSize: sz(11.5), bold: lvl >= 2, color: onAcc ? STYLE.onAccent : STYLE.body });
      }
    }
    const lg = sec.scaleLabel || ['低', '高'];
    s.addText(lg[0] || '低', { x: hreg.x, y: hreg.y + H.headH + 0.08 + rowsUse * (rowH + H.cellGap) + 0.06,
      w: 0.6, h: 0.3, fontFace: STYLE.font, fontSize: sz(9.5), color: STYLE.faint });
    for (let i = 0; i < 4; i++) {
      s.addShape('rect', { x: hreg.x + 0.45 + i * 0.3, y: hreg.y + H.headH + 0.08 + rowsUse * (rowH + H.cellGap) + 0.1,
        w: 0.28, h: 0.16, fill: { color: levels[i] }, line: i === 0 ? { color: STYLE.line, width: 0.5 } : { type: 'none' } });
    }
    s.addText(lg[1] || '高', { x: hreg.x + 1.75, y: hreg.y + H.headH + 0.08 + rowsUse * (rowH + H.cellGap) + 0.06,
      w: 0.6, h: 0.3, fontFace: STYLE.font, fontSize: sz(9.5), color: STYLE.faint });
  } else if (type === 'bullet') {
    /* 达成对比：底槽 + 实际条 + 目标刻度 + 数值（实际/目标） */
    const B = PT.bullet;
    const breg = REGIONS.regionOf('bullet', 'primary', { bottom: bodyBottom }) ||
      { x: MX, y: B.y, w: CW, h: bodyBottom - B.y };
    const items = (sec.items || []).map(bulletKV);
    const n = Math.max(1, items.length);
    const availH = breg.h;
    const rowH = fitRowH(availH, n, B.rowH, 0.26);
    const trackX = breg.x + B.labelW + 0.15;
    const trackW = breg.w - B.labelW - B.valW - 0.3;
    const nums = items.map(it => Number(it[1])).filter(v => !isNaN(v));
    const vmax = sec.max || (nums.length ? Math.max.apply(null, nums) : 1);
    items.forEach((it, i) => {
      const y = breg.y + i * rowH + rowH / 2 - B.barH / 2;
      const v = Number(it[1]) || 0, tgt = Number(it[2]);
      const hit = !isNaN(tgt) && v >= tgt;
      s.addText(String(it[0]), { x: breg.x, y: breg.y + i * rowH, w: B.labelW, h: rowH, valign: 'middle',
        fontFace: STYLE.font, fontSize: sz(12), bold: true, color: STYLE.ink });
      s.addShape('roundRect', { x: trackX, y, w: trackW, h: B.barH, rectRadius: 0.5, fill: { color: STYLE.surface }, line: { color: STYLE.line, width: 0.75 } });
      const fw = Math.max(0.02, Math.min(1, v / (vmax || 1)) * trackW);
      s.addShape('roundRect', { x: trackX, y, w: fw, h: B.barH, rectRadius: 0.5,
        fill: { color: hit ? STYLE.accent : mixHex(STYLE.soft, STYLE.accent, 0.45) }, line: { type: 'none' } });  // M9：未达标仍是品牌色浅一级，不用灰
      if (!isNaN(tgt)) {
        const tx = trackX + Math.min(1, tgt / (vmax || 1)) * trackW;
        s.addShape('rect', { x: tx - 0.01, y: y - 0.07, w: 0.02, h: B.barH + 0.14, fill: { color: STYLE.body }, line: { type: 'none' } });
      }
      s.addText([{ text: String(it[1]) + (sec.unit || ''), options: { fontSize: sz(12), bold: true, color: hit ? STYLE.accent : STYLE.body } },
                 { text: isNaN(tgt) ? '' : ' / ' + tgt + (sec.unit || ''), options: { fontSize: sz(10), color: STYLE.faint } }],
        { x: trackX + trackW + 0.12, y: breg.y + i * rowH, w: B.valW, h: rowH, align: 'right', valign: 'middle', fontFace: STYLE.font });
    });
  } else if (type === 'pyramid') {
    /* 金字塔：自上而下逐层加宽；顶层最窄，accent 层强调 */
    const P = PT.pyramid;
    const preg = REGIONS.regionOf('pyramid', 'primary', { bottom: bodyBottom }) ||
      { x: MX, y: P.y, w: CW, h: bodyBottom - P.y };
    const lv = sec.levels || [];
    const n = Math.max(1, lv.length);
    const availH = preg.h;
    /* M1：层高由求解器分配，富余时拉伸到 1.35in，余量整体垂直居中 */
    const pyS = SOLVER.rows(availH, n, { pref: P.rowH, min: 0.26, max: 1.35, gap: P.gap });
    const rowH = pyS.size;
    lv.forEach((l, i) => {
      const frac = P.minW + (1 - P.minW) * (n === 1 ? 1 : i / (n - 1));
      const w = preg.w * frac;
      const x = preg.x + (preg.w - w) / 2;
      const y = preg.y + pyS.offset + i * (rowH + P.gap);
      const acc = isRec(l) && l.accent;
      const lt = isRec(l) ? (l.t || '') : String(l[0] || '');
      const ld = isRec(l) ? (l.d || '') : String(l[1] || '');
      s.addShape('roundRect', { x, y, w, h: rowH, rectRadius: rr(0.07),
        fill: { color: acc ? STYLE.soft : STYLE.surface },
        line: acc ? { type: 'none' } : { color: STYLE.line, width: 0.75 } });
      /* 标题列宽按层内宽比例分配（labelFrac≈0.3）；顶层窄时固定 3.2in 会把说明压成竖列叠印 →
         改为标题上、说明下的单框混排（与 HTML .pyr__t/.pyr__d 同语义） */
      const lwP = Math.min(P.labelW, (w - 0.44) * (P.labelFrac == null ? 0.32 : P.labelFrac));
      const descW = w - 0.44 - lwP;
      /* 窄层判定：说明列 < 1.2in，或标题在标题列内放不下单行（会中部换行）→
         标题上、说明下单框混排（与 HTML 窄屏 .pyr__lvl 单列同语义） */
      const narrowP = descW < 1.2 || (ld && estLines(lt, lwP, 13.5) > 1) || (!ld && estLines(lt, w - 0.44, 13.5) > 1);
      if (narrowP) {
        s.addText(lt, { x: x + 0.22, y: y + 0.03, w: w - 0.44, h: 0.30, valign: 'middle',
          fontFace: STYLE.font, fontSize: sz(12.5), bold: true, color: acc ? STYLE.accent : STYLE.ink, fit: 'shrink' });
        s.addText(ld, { x: x + 0.22, y: y + 0.33, w: w - 0.44, h: Math.max(0.2, rowH - 0.36), valign: 'middle',
          fontFace: STYLE.font, fontSize: sz(10.5), color: STYLE.faint, fit: 'shrink' });
      } else {
        s.addText(lt, { x: x + 0.22, y, w: lwP, h: rowH, valign: 'middle',
          fontFace: STYLE.font, fontSize: sz(13.5), bold: true, color: acc ? STYLE.accent : STYLE.ink, fit: 'shrink' });
        if (ld) s.addText(ld, { x: x + 0.22 + lwP, y, w: descW, h: rowH,
          valign: 'middle', fontFace: STYLE.font, fontSize: sz(11), color: STYLE.faint, fit: 'shrink' });
      }
    });
  } else if (type === 'steps') {
    /* 步骤条：N 步横排 + 箭头；超 maxPerRow 折行；groups 分组标签 */
    const S2 = PT.steps;
    const sreg = REGIONS.regionOf('steps', 'primary') ||
      { x: MX, y: S2.y, w: CW, h: S2.barH };
    const st = sec.steps || [];
    const maxPer = S2.maxPerRow || 6;
    const groups = sec.groups || [];
    /* 按分组切片（groups = [[标签, 步数]…]；缺省全为一段） */
    const chunks = [];
    if (groups.length) {
      let k = 0;
      groups.forEach(g => { const cnt = Number(g[1]) || 0; chunks.push({ label: g[0], items: st.slice(k, k + cnt) }); k += cnt; });
      if (k < st.length) chunks.push({ label: '', items: st.slice(k) });
    } else {
      for (let i = 0; i < st.length; i += maxPer) chunks.push({ label: '', items: st.slice(i, i + maxPer) });
    }
    const rowsN = chunks.length;
    const availH = bodyBottom - sreg.y;
    /* M0：单行步骤卡按可用高度拉伸（上限 3.0in），不再固定 1.35in 让下半页空白 */
    const rowH = fitRowH(availH - (rowsN - 1) * 0.3, rowsN, Math.max(sreg.h || S2.barH, Math.min(3.0, (availH - (rowsN - 1) * 0.3) / rowsN)), 0.3);
    let cy = sreg.y;
    chunks.forEach((ck) => {
      if (ck.label) {
        s.addText(ck.label, { x: sreg.x, y: cy - 0.02, w: sreg.w, h: 0.26, fontFace: STYLE.font,
          fontSize: sz(10), bold: true, color: STYLE.faint, charSpacing: 1 });
        cy += 0.28;
      }
      const n = Math.max(1, ck.items.length);
      const g = cols(sreg.w, n, S2.gap + S2.arrowW);
      ck.items.forEach((it, i) => {
        const acc = isRec(it) && it.accent;
        const t = isRec(it) ? (it.t || '') : String(it[0] || '');
        const d = isRec(it) ? (it.d || '') : String(it[1] || '');
        const x = sreg.x + i * g.step;
        s.addShape('roundRect', { x, y: cy, w: g.w, h: rowH, rectRadius: rr(0.07),
          fill: { color: acc ? STYLE.soft : STYLE.surface },
          line: acc ? { type: 'none' } : { color: STYLE.line, width: 0.75 } });
        const pd = S2.pad, numH = S2.numH, ttlH = S2.titleH;
        const bigNum = rowH >= 2.2;
        s.addText(String(i + 1).padStart(2, '0'), { x: x + 0.14, y: cy + pd, w: g.w - 0.28, h: bigNum ? 0.7 : numH,
          fontFace: bigNum ? STYLE.fontDisplay : STYLE.font, fontSize: bigNum ? sz(28) : sz(10), bold: true, color: STYLE.accent });
        const nH = bigNum ? 0.8 : numH;
        s.addText(t, { x: x + 0.14, y: cy + pd + nH, w: g.w - 0.28, h: bigNum ? 0.45 : ttlH,
          fontFace: STYLE.font, fontSize: bigNum ? sz(15) : sz(13), bold: true, color: acc ? STYLE.accent : STYLE.ink });
        const tH = bigNum ? 0.55 : ttlH;
        if (d) s.addText(d, { x: x + 0.14, y: cy + pd + nH + tH, w: g.w - 0.28,
          h: Math.max(0.2, rowH - pd * 2 - nH - tH),
          fontFace: STYLE.font, fontSize: bigNum ? sz(12) : sz(10), color: bigNum ? STYLE.body : STYLE.faint, valign: 'top' });
        if (i < n - 1) {
          s.addText('→', { x: x + g.w, y: cy, w: S2.arrowW + S2.gap, h: rowH, align: 'center', valign: 'middle',
            fontFace: STYLE.font, fontSize: sz(12), color: STYLE.faint });
        }
      });
      cy += rowH + 0.3;
    });
  } else if (type === 'table') {
    const treg = REGIONS.regionOf('table', 'primary', { bottom: bodyBottom }) ||
      { x: MX, y: CONTENT_TOP, w: CW, h: bodyBottom - CONTENT_TOP };
    const hlc = sec.variant === 'highlight' ? Number(sec.highlightCol != null ? sec.highlightCol : (sec.table || {}).highlightCol) : null;
    /* 美化路由：表格可用高度放到主体区底部（短表行高放大，见 addTable roomy） */
    /* 演示模式整页短表同样放大（M5 评审：5 行表只占上半页） */
    const tRoomy = MODE_NAME === 'presentation' && (sec.table.rows || []).length <= 6;
    let tAvail = (CONTENT.contentLocked || tRoomy) ? Math.max(treg.h, bodyBottom - treg.y - 0.2) : treg.h;
    /* M12 试跑：表格页的 points 与 HTML 同构，表下一行解读卡（≤3 条）；此前 PPTX 静默丢弃 */
    const tPts = (sec.readout || sec.points || []).filter(Boolean).slice(0, 3)
      .map(p => Array.isArray(p) ? [String(p[0] || ''), String(p[1] || '')] : [String(p), '']);
    const tRowH = tPts.length ? 1.05 : 0;
    if (tRowH) tAvail = Math.min(tAvail, bodyBottom - treg.y - tRowH - 0.3);
    addTable(s, sec.table, treg.x, treg.y, treg.w, tAvail, { highlightCol: isFinite(hlc) ? hlc : null, roomy: tRoomy });
    if (tRowH) readoutRow(s, [], tPts, treg.x, bodyBottom - tRowH, treg.w, tRowH);
  } else if (type === 'timeline') {
    const T = PT.timeline;
    const treg = REGIONS.regionOf('timeline', 'primary') ||
      { x: MX, y: T.labelY, w: CW, h: T.descY + T.descH - T.labelY };
    const ps = (sec.phases || []).map(phaseKV);
    const n = Math.max(1, ps.length);
    const stepW = (treg.w - 1.0) / n;
    /* M12 阶段卡（与 HTML .tl--h 同条件、同结构）：2–5 个阶段、非图标变体、每段说明 ≤40 字时，
       轴线在上、每个阶段一张色调卡（时间标签 + 阶段名 + 说明，顶对齐），进行中的一张用强调底色。三种模式一致。 */
    const tlCards = n >= 2 && n <= 5 && sec.variant !== 'timeline' && ps.every(p => String(p[2] || '').length <= 40);
    const big = MODE_NAME === 'presentation';
    if (tlCards) {
      const gap = 0.22, cW = (treg.w - gap * (n - 1)) / n;
      const axisY = bodyY + 0.12, cTop = axisY + 0.42;
      const cH = Math.max(1.6, Math.min(bodyBottom - 0.1 - cTop, PH * 0.42));
      const fzName = big ? roleSz('stepTitle', 22) : sz(17), fzDesc = sz(big ? 14.5 : 12);
      s.addShape('line', { x: treg.x + 0.1, y: axisY, w: treg.w - 0.2, h: 0.02, line: { color: STYLE.line, width: 1.5 } });
      ps.forEach((p, i) => {
        const cx = treg.x + i * (cW + gap);
        const on = p[3] === 'done' || p[3] === 'now', now = p[3] === 'now';
        s.addShape('ellipse', { x: cx + 0.22, y: axisY - T.dotR / 2, w: T.dotR, h: T.dotR,
          fill: { color: on ? STYLE.accent : STYLE.bg }, line: { color: on ? STYLE.accent : STYLE.line, width: 1.5 } });
        s.addShape('roundRect', { x: cx, y: cTop, w: cW, h: cH, rectRadius: rr(0.1),
          fill: { color: now ? STYLE.soft : STYLE.surface }, line: { color: STYLE.line, width: 0.75 }, objectName: 'tl:card' });
        const ix = cx + 0.24, iw = cW - 0.48;
        s.addText(p[0], { x: ix, y: cTop + 0.22, w: iw, h: 0.32, fontFace: STYLE.font,
          fontSize: sz(11), bold: true, color: STYLE.accent, charSpacing: 1, margin: 0 });
        s.addText(p[1], { x: ix, y: cTop + 0.6, w: iw, h: 0.5, fontFace: STYLE.fontDisplay,
          fontSize: fzName, bold: true, color: now ? STYLE.accent : STYLE.ink, valign: 'top', margin: 0 });
        s.addText(p[2] || '', { x: ix, y: cTop + 1.18, w: iw, h: Math.max(0.4, cH - 1.32), fontFace: STYLE.font,
          fontSize: fzDesc, color: STYLE.body, valign: 'top', margin: 0 });
      });
    } else {
    const fzLab = 11, fzName = 17, fzDesc = 12;
    const TY = { labelY: T.labelY, axisY: T.axisY, dotY: T.dotY, nameY: T.nameY, descY: T.descY };
    s.addShape('line', { x: treg.x + 0.2, y: TY.axisY, w: treg.w - 0.4, h: 0.02, line: { color: STYLE.line, width: 1.5 } });
    ps.forEach((p, i) => {
      const x = treg.x + 0.2 + i * stepW;
      const on = p[3] === 'done' || p[3] === 'now';
      // 变体 timeline：节点图标（icon:<name>）；无图标回落圆点
      const wantIcon = (sec.variant === 'timeline') && p[4];
      if (wantIcon) {
        addIcon(s, p[4], x - 0.13, TY.dotY - 0.06, 0.26, on ? STYLE.accent : STYLE.body);
      } else {
        s.addShape('ellipse', { x: x - T.dotR / 2, y: TY.dotY, w: T.dotR, h: T.dotR,
          fill: { color: on ? STYLE.accent : STYLE.line }, line: { type: 'none' } });
      }
      s.addText(p[0], { x: x - 0.1, y: TY.labelY, w: stepW - 0.2, h: 0.4, fontFace: STYLE.font,
        fontSize: sz(fzLab), bold: true, color: STYLE.accent, charSpacing: 1 });
      s.addText(p[1], { x: x - 0.1, y: TY.nameY, w: stepW - 0.2, h: 0.5, fontFace: STYLE.fontDisplay,
        fontSize: sz(fzName), bold: true, color: p[3] === 'now' ? STYLE.accent : STYLE.ink });
      s.addText(p[2] || '', { x: x - 0.1, y: TY.descY, w: stepW - 0.25, h: Math.max(T.descH, bodyBottom - TY.descY - 0.1), fontFace: STYLE.font,
        fontSize: sz(fzDesc), color: STYLE.body, valign: 'top' });
    });
    }
  } else if (type === 'bar') {
    const c = sec.chart || {};
    const dcols = c.colors || dataColors(styleArg);
    const bot = chartBottom(!!sec.soWhat, !!(sec.footnote || sec.note)) - 0.05;
    const isH = c.type === 'hbar';
    const reg = REGIONS.regionOf('bar', isH ? 'hbar' : 'primary', { bottom: bot }) ||
      { x: MX, y: isH ? PT.bar.hbarY0 : PT.bar.chartY, w: CW, h: 3 };
    const pts = (sec.points || []).filter(Boolean);
    let cx = reg.x, cw = reg.w;
    if (pts.length && !isH) {
      const sideW = Math.min(3.6, Math.max(2.6, reg.w * 0.30));
      cw = Math.max(3.2, reg.w - sideW - 0.28);
      const sx = reg.x + cw + 0.28;
      const rowH = Math.min(0.72, (reg.h - 0.1) / Math.max(1, pts.length));
      pts.slice(0, 6).forEach((p, i) => {
        const kv = pointKV(p), k = kv[0], v = kv[1];
        const y = reg.y + i * rowH;
        s.addShape('rect', { x: sx, y: y + 0.12, w: 0.08, h: 0.08,
          fill: { color: STYLE.accent }, line: { type: 'none' } });
        s.addText([
          { text: k + (v ? '　' : ''), options: { fontSize: sz(12), bold: true, color: STYLE.ink } },
          { text: v, options: { fontSize: sz(11), color: STYLE.body } },
        ], { x: sx + 0.2, y, w: sideW - 0.25, h: rowH, fontFace: STYLE.font, valign: 'middle' });
      });
    }
    if (isH) {
      chartBlock(s, c, cx, reg.y, cw, reg.h, dcols);
    } else {
      chartBlock(s, c, cx, reg.y, cw, Math.max(1.5, reg.h), dcols);
    }
  } else if (type === 'twocol' || type === 'threecol') {
    const ps = (sec.paragraphs || []).map(paraKV);
    const nCol = (type === 'threecol') ? 3 : 2;
    const gap = (type === 'threecol') ? PT.research.col3Gap : PT.twocol.colGap;
    /* R3：多栏均分必须用版心全宽。regionOf('twocol','primary') 返回的是「单栏宽」，
       直接当总宽再 cols() 会把三栏压成 1.69in、右侧 55% 全空。 */
    const treg = { x: MX, y: bodyY, w: CW, h: bodyBottom - bodyY };
    const g = cols(treg.w, nCol, gap);
    const per = Math.ceil(ps.length / nCol);
    const availH = treg.h;
    const groups = [];
    for (let i = 0; i < nCol; i++) groups.push(ps.slice(i * per, (i + 1) * per));
    /* 自适应：按各栏文本估算高度选字号 */
    const longest = groups.reduce((a, g2) => Math.max(a, g2.map(p => (p[1] || '').length).reduce((x, y) => x + y, 0)), 0);
    const items = []; for (let i = 0; i < longest / 120; i++) items.push('x'.repeat(120));
    /* M1：稀疏时字号向上求解（上限 presentation 17 / 其他 15），余量再均分到段间距——不再顶部一小块、下半页空白 */
    const colNeed = (f) => Math.max(...groups.map(gc => gc.reduce((h, p) =>
      h + SOLVER.estTextH((p[0] || '') + '　' + (p[1] || ''), g.w, f, 1.5) + f * 1.2 / 72, 0)));
    const fz0 = fitFont(items.length ? items : ['x'.repeat(longest)], g.w, availH, { max: 13.5, gapFactor: 1.2 });
    const fz = Math.max(fz0, snapFont(SOLVER.fitUp(colNeed, availH * 0.82, { max: MODE_NAME === 'presentation' ? 17 : 15, min: fz0 })));
    const maxPer = Math.max(1, ...groups.map(gc => gc.length));
    const spareIn = Math.max(0, availH * 0.9 - colNeed(fz));
    const paraGapPt = Math.min(30, Math.round(7 + (spareIn * 72) / maxPer));
    /* M1 组合规则：内容稀疏（估高 < 版心 55%）时改为「段落卡片网格」——每段一张 MD3 tonal 卡，
       行高由求解器撑满版心；标签作卡标题、正文在下，避免顶部一小块文字 + 下半页空白。 */
    /* M12：与 HTML r_twocol 同条件——≤6 段、每段有标签且正文 ≤60 字 → 段落卡片网格（行优先） */
    const sparse = sec.variant !== '2-col-feature' && ps.length > 0 && ps.length <= 6 &&
      ps.every(p => p[0] && String(p[1] || '').length <= 60);
    if (sparse) {
      const cardSol = SOLVER.rows(availH - 0.05, maxPer, { pref: 1.0, min: 0.5, max: 2.2, gap: 0.2, center: false });
      const cardFz = snapFont(SOLVER.fitUp(f => Math.max(...ps.map(p =>
        SOLVER.estTextH(p[0] || '', g.w - 0.5, f + 1.5, 1.3) + SOLVER.estTextH(p[1] || '', g.w - 0.5, f, 1.45))) + 0.36,
        cardSol.size, { max: MODE_NAME === 'presentation' ? 16 : 14, min: fz0 }));
      /* M9：卡片网格按行优先排（与 HTML grid 自然流向一致：第一行先读完再换行） */
      ps.forEach((p, k) => {
        const ci = k % nCol, ri = Math.floor(k / nCol);
        const cx2 = treg.x + ci * g.step, cy2 = treg.y + ri * (cardSol.size + cardSol.gap);
        s.addShape('roundRect', { x: cx2, y: cy2, w: g.w, h: cardSol.size, rectRadius: rr(0.1),
          fill: { color: STYLE.surface }, line: { type: 'none' }, objectName: 'para:card' });
        s.addText([
          { text: p[0] || '', options: { fontSize: sz(cardFz + 1.5), bold: true, color: STYLE.ink, breakLine: true } },
          { text: p[1] || '', options: { fontSize: sz(cardFz), color: STYLE.body } },
        ], { x: cx2 + 0.25, y: cy2 + 0.12, w: g.w - 0.5, h: cardSol.size - 0.24, valign: 'middle',
          fontFace: STYLE.font, lineSpacing: sz(cardFz * 1.5), paraSpaceBefore: 4 });
      });
    }
    if (!sparse) groups.forEach((col, ci) => {
      if (!col.length) return;
      const colX = treg.x + ci * g.step;
      // 变体 2-col-feature：首栏特性栏（MD3 tonal 底 + 标题放大一档）
      const isFeature = (sec.variant === '2-col-feature') && ci === 0 && nCol === 2;
      const fx = isFeature ? colX + 0.14 : colX;
      const fw = isFeature ? g.w - 0.14 : g.w;
      if (isFeature) {
        /* M0：特性栏改为 MD3 tonal 底（无左侧装饰竖条），按首段文本估高 */
        const p0 = col[0] || ['', ''];
        const boxH = Math.min(availH,
          estTextH(p0[0] + '　', fw, sz(fz + 1), 1.5) +
          estTextH(p0[1] || '', fw, sz(fz - 1), 1.5) + sz(7) / 72 + 0.2);
        s.addShape('roundRect', { x: colX, y: treg.y - 0.08, w: g.w, h: Math.max(0.3, boxH), rectRadius: rr(0.08),
          fill: { color: STYLE.soft }, line: { type: 'none' }, objectName: 'feature:bg' });
      }
      const runs = col.map(p => ([
        { text: p[0] + '　', options: { fontSize: sz(isFeature ? fz + 1 : fz), bold: true, color: STYLE.ink } },
        { text: p[1] + '\n', options: { fontSize: sz(fz - 1), color: STYLE.body, breakLine: true } },
      ])).flat();
      s.addText(runs, { x: fx, y: treg.y, w: fw, h: availH, fontFace: STYLE.font,
        valign: 'top', lineSpacing: sz(fz * 1.5), paraSpaceBefore: paraGapPt });
    });
  } else if (type === 'halftable') {
    let yH = sec.lead ? PT.common.bodyYWithLead : PT.research.denseTableY;
    /* 徽标占位：exhibitNo 徽标占 CONTENT_TOP-0.06 起 0.3 高；bodyY 已含 +0.42 让位，
       表格/图顶取 max 不得压入徽标（否则 Exhibit 编号与表头叠印） */
    if (exBadge) yH = Math.max(yH, bodyY);
    const lwH = CW * PT.research.halfTableW;
    if (sec.table && sec.table.head) {
      addTable(s, sec.table, MX, yH, lwH, bodyBottom - yH,
        { maxRowH: PT.research.denseRowH + 0.1, minRowH: 0.28 });
    }
    const ecH = sec.chart || {};
    if (ecH.labels && ecH.values) {
      const rxH = MX + CW * PT.research.halfChartX;
      const rwH = CW * PT.research.halfChartW;
      let cyH = yH;
      if (exRight) {
        s.addText(exhibitRuns(sec.exhibitNo, sec.cap, sz(11.5)), { x: rxH, y: yH - 0.04, w: rwH, h: 0.3 });
        cyH = yH + 0.38;
      }
      /* 帧头在右时来源行也归右栏，贴在图下（HTML .exhibit__src 同位） */
      const srcIn = exRight && (sec.footnote || sec.note);
      const chH = Math.max(1.2, bodyBottom - cyH - (srcIn ? 0.36 : 0));
      chartBlock(s, ecH, rxH, cyH, rwH, chH, (ecH.colors || dataColors(styleArg)));
      if (srcIn) ANNOT = Object.assign({}, ANNOT || {}, { foot: { x: rxH, y: cyH + chH + 0.04, w: rwH, h: 0.3 } });
    }
  } else if (type === 'matrix') {
    const rhH = sec.rowHeads || [], chH = sec.colHeads || [];
    const mY = PT.research.matrixY, mLW = PT.research.matrixLabelW;
    const rowsC = sec.cells || [];
    const nR = Math.max(1, rowsC.length);
    const availH = bodyBottom - mY - 0.42;
    /* M1：矩阵格高由求解器分配，富余时拉伸到 1.6in（格子撑满版心，不再悬在中部） */
    const mCH = SOLVER.rows(availH, nR, { pref: PT.research.matrixCellH, min: 0.3, max: 1.6, center: false }).size;
    const mW = (CW - mLW) / Math.max(1, chH.length);
    chH.forEach((ch2, ci) => {
      s.addText(ch2, { x: MX + mLW + ci * mW, y: mY, w: mW, h: 0.34, align: 'center',
        fontFace: STYLE.font, fontSize: sz(11), bold: true, color: STYLE.body });
    });
    rowsC.forEach((rowC, ri) => {
      const y2 = mY + 0.42 + ri * mCH;
      s.addText(rhH[ri] || '', { x: MX, y: y2 + (mCH - 0.5) / 2, w: mLW - 0.15, h: 0.5, align: 'right',
        fontFace: STYLE.font, fontSize: sz(11), bold: true, color: STYLE.body });
      rowC.forEach((cell, ci) => {
        const acc = isRec(cell) && cell.accent;
        const txt = isRec(cell) ? (cell.t || '') : String(cell);
        const cx = MX + mLW + ci * mW;
        s.addShape('roundRect', { x: cx + 0.04, y: y2, w: mW - 0.08, h: mCH - 0.1, rectRadius: 0.05,
          fill: { color: acc ? STYLE.soft : STYLE.surface }, line: { type: 'none' }, objectName: 'matrix:cell' });
        /* M10：与 HTML .heat__c 同构——tonal 实底无描边、文字居中；字重 600；accent 格 = heat__c--1（浅调底 + 品牌字） */
        s.addText(txt, { x: cx + 0.14, y: y2 + 0.08, w: mW - 0.28, h: mCH - 0.26,
          fontFace: STYLE.font, fontSize: sz(11), valign: 'middle', align: 'center', bold: true,
          color: acc ? STYLE.accent : STYLE.body });
      });
    });
  } else if (type === 'lane') {
    const lnS = sec.lanes || [];
    const n = Math.max(1, lnS.length);
    const start = sec.lead ? PT.common.bodyYWithLead : PT.arch.fullStartY;
    const availH = Math.min(bodyBottom, CONTENT_BOTTOM_NOTE + 0.3) - start;
    /* M1：泳道高度由求解器分配（富余时拉伸到 1.5in，仍有余量整组垂直居中） */
    const lnSol = SOLVER.rows(availH, n, { pref: PT.arch.laneH, min: 0.3, max: n <= 2 ? 2.4 : 1.5, gap: PT.arch.laneGap });
    const lnH = lnSol.size;
    const lnGap = PT.arch.laneGap, lnHW = PT.arch.laneHeadW;
    lnS.forEach((ln, li) => {
      const y3 = start + lnSol.offset + li * (lnH + lnGap);
      s.addShape('roundRect', { x: MX, y: y3, w: CW, h: lnH, rectRadius: rr(0.07),
        fill: { color: STYLE.surface }, line: { color: STYLE.line, width: 0.75 } });
      s.addShape('rect', { x: MX, y: y3, w: lnHW, h: lnH,
        fill: { color: STYLE.surface }, line: { color: STYLE.line, width: 0.75 } });
      s.addText(ln[0], { x: MX + 0.08, y: y3, w: lnHW - 0.16, h: lnH, align: 'center', valign: 'middle',
        fontFace: STYLE.font, fontSize: sz(11), bold: true, color: STYLE.body });
      const steps = ln[1] || [];
      const stepW = Math.min(PT.arch.stepMaxW, (CW - lnHW - 0.4 - (steps.length - 1) * PT.arch.stepGap) / Math.max(1, steps.length));
      steps.forEach((st, si) => {
        const stAcc = isRec(st) && st.accent;
        const stT = isRec(st) ? st.t : st;
        const sx = MX + lnHW + 0.2 + si * (stepW + PT.arch.stepGap);
        s.addShape('roundRect', { x: sx, y: y3 + 0.13, w: stepW, h: lnH - 0.26, rectRadius: rr(0.06),
          fill: { color: stAcc ? STYLE.soft : STYLE.bg },
          line: stAcc ? { type: 'none' } : { color: STYLE.line, width: 0.75 } });
        s.addText(stT, { x: sx + 0.06, y: y3 + 0.13, w: stepW - 0.12, h: lnH - 0.26,
          align: 'center', valign: 'middle', fontFace: STYLE.font, fontSize: sz(11),
          bold: !!stAcc, color: stAcc ? STYLE.accent : STYLE.ink });
        if (si < steps.length - 1) {
          /* 正交箭头（线段+三角头），替代裸文字 → */
          const ax = sx + stepW + 0.02, ay = y3 + lnH / 2, aw = PT.arch.stepGap - 0.04;
          s.addShape('rect', { x: ax, y: ay - 0.01, w: Math.max(0.06, aw * 0.55), h: 0.02,
            fill: { color: STYLE.faint }, line: { type: 'none' } });
          s.addShape('triangle', { x: ax + aw * 0.55, y: ay - 0.05, w: 0.1, h: 0.1, rotate: 90,
            fill: { color: STYLE.faint }, line: { type: 'none' } });
        }
      });
    });
  } else if (type === 'cards') {
    const cdC = PT.cards;
    const creg = Object.assign({}, REGIONS.regionOf('cards', 'primary', { bottom: bodyBottom }) ||
      { x: MX, y: cdC.startY, w: CW, h: bodyBottom - cdC.startY });
    const cds = (sec.cards || []).map(cd =>
      /* 与 r_cards 同口径：{title,points,icon} 字典 | [标题, 描述] 数组 | 纯字符串标题 */
      isRec(cd) ? cd
        : (Array.isArray(cd)
          ? { title: cd[0] || '', points: cd.length > 1 ? [['', cd[1]]] : [] }
          : { title: String(cd == null ? '' : cd), points: [] }));
    if (creg.y > bodyY + 0.3) { creg.h += creg.y - bodyY; creg.y = bodyY; }
    const isBento = (sec.variant === 'bento-grid') && cds.length >= 3;
    const c = isBento ? 3 : Math.min(sec.columns || 3, cds.length || 1);
    // bento-grid：首卡占 2 个槽位（跨 2 列），其余顺排；槽位数 = 卡数 + 1
    const r = isBento ? Math.ceil((cds.length + 1) / c) : Math.ceil((cds.length || 1) / c);
    const gw = (creg.w - (c - 1) * cdC.gap) / c;
    /* M0：卡片高度随版心拉伸（上限 3.4in），不再固定 2.0in 让下半页空白 */
    const gh = fitRowH(creg.h - (r - 1) * cdC.gap, r, Math.max(cdC.maxH, Math.min(3.4, (creg.h - (r - 1) * cdC.gap) / r)), 0.6);
    /* points 文本归一化（scaffold v9 契约 {title, points:[[k,v]]} 兼容三种形态） */
    const cardPtText = (pt) => {
      if (Array.isArray(pt)) {
        const k = pt[0] == null ? '' : String(pt[0]);
        const v = pt[1] == null ? '' : String(pt[1]);
        return k && v ? ('· ' + k + '　' + v) : ('· ' + (k || v));
      }
      if (pt && typeof pt === 'object') {
        const t = String(pt.k || pt.t || '');
        const d = String(pt.v || pt.d || '');
        return '· ' + t + (d ? '　' + d : '');
      }
      return '· ' + String(pt == null ? '' : pt);
    };
    /* 有限缩字号：按最拥挤卡片的要点文本量统一选档（12 起阶梯下探），行距随字号等比；
       取代无脑 autofit shrink，保证估算口径与渲染一致（TEXT_OVERFLOW_VERTICAL） */
    const ptsBoxH = Math.max(0.4, gh - cdC.titleH - 0.34);
    /* 陈述卡（全部卡无标题，正文即原稿整句——美化路由常见）：字号向上求解到 h2 档、去掉项目符号、垂直居中 */
    const statement = !!CONTENT.contentLocked && cds.length > 0 && cds.every(cd => !String(cd.title || '').trim());
    /* 陈述卡用整张卡作文本区（不留标题行、不放图标），字号上限放到 22pt，全卡统一取最小可容纳档 */
    const STMT_PAD = 0.28;
    /* 美化路由的有标题卡：标题与正文都上调一档，短内容不再缩在卡片左上角 */
    /* 短内容卡片页（≤4 卡、每卡正文平均 ≤60 字）同样上调字号：与 HTML .cards--roomy 同判据 */
    const _cl = cd => (cd.points || []).map(p => cardPtText(p)).join('').length;
    const roomyCards = MODE_NAME === 'presentation' && cds.length > 0 && cds.length <= 4 && !isBento &&
      cds.reduce((a, cd) => a + _cl(cd), 0) / cds.length <= 64;
    const lockedCards = !statement && (!!CONTENT.contentLocked || roomyCards);
    const ptsFzB = cds.length ? Math.min(...cds.map((cd, i) => statement
      ? fitFont((cd.points || []).map(String), (isBento && i === 0 ? 2 * gw + cdC.gap : gw) - 2 * STMT_PAD, gh - 2 * STMT_PAD,
        { max: 22, lineFactor: 1.45, gapFactor: 0.3, ladder: BIG_LADDER })
      : fitFont((cd.points || []).map(cardPtText), gw - 0.36, ptsBoxH - (lockedCards ? 0.2 : 0),
        lockedCards ? { max: 18, lineFactor: 1.5, gapFactor: 0, ladder: BIG_LADDER } : { max: 14, lineFactor: 1.5, gapFactor: 0 }))) : 12;
    const ptsFz = sz(ptsFzB);
    cds.forEach((cd, i) => {
      let col = i % c, row = Math.floor(i / c), span = 1;
      if (isBento) {
        // 首卡跨 2 列：槽位 = i===0 ? [0,1] : i+1
        const slot = i === 0 ? 0 : i + 1;
        if (i === 0) span = 2;
        /* 末行补齐：尾卡吃掉末行剩余槽位，不留空洞（与 HTML .card--fill2 同规则） */
        if (i === cds.length - 1 && i > 0) span = Math.max(1, r * c - (cds.length + 1) + 1);
        col = slot % c; row = Math.floor(slot / c);
      }
      const cw = span * gw + (span - 1) * cdC.gap;
      const x = creg.x + col * (gw + cdC.gap), y = creg.y + row * (gh + cdC.gap);
      s.addShape('roundRect', { x, y, w: cw, h: gh, rectRadius: rr(0.08),
        fill: { color: STYLE.surface }, line: { color: STYLE.line, width: 0.75 } });
      if (statement) {
        const lines = (cd.points || []).map(t => String(cardPtText(t)).replace(/^· /, ''));
        s.addText(lines.map((t, li) => ({ text: t + (li < lines.length - 1 ? '\n' : ''),
            options: { fontSize: li === 0 ? ptsFz : sz(Math.max(12, ptsFzB - 4)), color: li === 0 ? STYLE.ink : STYLE.body,
              bold: li === 0, fontFace: STYLE.font, breakLine: li < lines.length - 1 } })),
          { x: x + STMT_PAD, y: y + STMT_PAD, w: cw - 2 * STMT_PAD, h: gh - 2 * STMT_PAD,
            fontFace: STYLE.font, valign: 'middle', lineSpacing: ptsFz * 1.45 });
        return;
      }
      /* 卡片头路标：真导出语义图标（SVG→PNG），与 HTML .card__ico 同源；无资产时回落 accent 方块 */
      const ico = lockedCards ? 0.26 : 0.18;
      const icoName = cd.icon || ICON_LIB.pickIconName(cd.title || '', i);
      /* 短内容卡：标题 + 正文作为一组在卡内垂直居中，卡片仍铺满栅格（色调面撑起版面） */
      const ptLines0 = (cd.points || []).map(cardPtText);
      const estPts = ptLines0.reduce((a, t) => a + estTextH(t, cw - 0.36, ptsFz, 1.5), 0) + 0.1 * ptLines0.length;
      /* 同一行卡片共用同一偏移（按最长一张算），标题保持对齐 */
      const estMax = Math.max(...cds.map(c2 => (c2.points || []).map(cardPtText)
        .reduce((a, t) => a + estTextH(t, cw - 0.36, ptsFz, 1.5), 0) + 0.1 * (c2.points || []).length));
      const yOff = roomyCards ? Math.max(0, (gh - (0.14 + cdC.titleH + 0.2 + estMax + 0.2)) / 2) : 0;
      const y0 = y + yOff;
      addIcon(s, icoName, x + 0.18, y0 + (lockedCards ? 0.17 : 0.2), ico, STYLE.accent);
      s.addText(cd.title || '', { x: x + 0.18 + ico + 0.1, y: y0 + 0.14, w: cw - 0.36 - ico - 0.1, h: cdC.titleH, fontFace: STYLE.font,
        fontSize: sz(lockedCards ? 18 : 15), bold: true, color: STYLE.ink, fit: 'shrink' });
      /* points 兼容：[[k,v]…] | [str…] | [{t,d}…]（scaffold v9 契约 {title, points:[[k,v]]}） */
      const ptLines = (cd.points || []).map(cardPtText).map(t => statement ? t.replace(/^· /, '') : t);
      s.addText(ptLines.map((t, li) => ({ text: t + '\n',
          options: { fontSize: ptsFz, color: statement && li === 0 ? STYLE.ink : STYLE.body, bold: statement && li === 0,
            fontFace: STYLE.font, breakLine: true } })),
        { x: x + 0.18, y: y0 + 0.14 + cdC.titleH + (lockedCards ? 0.2 : 0.06), w: cw - 0.36,
          h: roomyCards ? Math.min(ptsBoxH - 0.14, estPts + 0.3) : ptsBoxH - (lockedCards ? 0.14 : 0),
          fontFace: STYLE.font, valign: statement ? 'middle' : 'top', lineSpacing: ptsFz * 1.5 });
    });
  } else if (type === 'split') {
    /* 双区自由组合页：左区与右区各可为 要点 / 图表 / 表格 / 图片。
       left.type / right.type = 'points'(默认) | 'table' | 'image' | 图表类型名（bar/line/…）。
       缺省 left=points、right=bar —— 向后兼容 v7 模型（只写 left.points 的旧模型行为不变）。 */
    const SP = PT.split;
    const lreg = REGIONS.regionOf('split', 'left', { bottom: bodyBottom }) ||
      { x: MX, y: SP.chartY, w: CW * SP.leftW, h: bodyBottom - SP.chartY };
    const rreg = REGIONS.regionOf('split', 'right', { bottom: bodyBottom }) ||
      { x: MX + CW * SP.rightX, y: SP.chartY, w: CW * SP.rightW, h: bodyBottom - SP.chartY };
    const lw = lreg.w, rw = rreg.w, rx = rreg.x;
    const lt = (sec.left && sec.left.type) || 'points';
    /* 要点区渲染（左右两区共用；v8 起 right.type='points' 也可用——修正 v7 只在 schema 声明却未实现的问题） */
    const drawPoints = (el, x, w) => {
      const pts = ((el && el.points) || []).map(pointKV);
      const ly0 = bodyY, availP = bodyBottom - ly0;
      const rowH = fitRowH(availP, pts.length, SP.rowH, 0.3);
      const big = !!CONTENT.contentLocked && pts.length <= 4;
      const fzB = fitFont(pts.map(p => (p[0] || '') + (p[1] || '')), w - 0.4, availP,
        { max: big ? 18 : 14, gapFactor: 0.6, ladder: big ? BIG_LADDER : undefined });
      const fz = sz(fzB), fzSm = sz(snapFont(fzB - 1));
      pts.forEach((pt, i) => {
        const ly = ly0 + i * rowH;
        s.addShape('rect', { x, y: ly + rowH / 2 - 0.06, w: 0.12, h: 0.12, fill: { color: STYLE.accent }, line: { type: 'none' } });
        s.addText([
          { text: pt[0] ? pt[0] + (pt[1] ? '　' : '') : '', options: { fontSize: fz, bold: true, color: STYLE.ink } },
          { text: pt[1], options: { fontSize: pt[0] ? fzSm : fz, color: pt[0] ? STYLE.body : STYLE.ink } },
        ], { x: x + 0.28, y: ly, w: w - 0.4, h: rowH - 0.04, fontFace: STYLE.font, valign: big ? 'middle' : 'top' });
      });
    };
    if (lt === 'table') {
      addTable(s, { head: sec.left.head, rows: sec.left.rows, colW: sec.left.colW },
        lreg.x, SP.tableY, lw, bodyBottom - SP.tableY, { maxRowH: SP.tableRowH, minRowH: 0.3 });
    } else if (lt === 'image') {
      const imL = (sec.left && sec.left.image) || {};
      addImageEl(s, imL.src, lreg.x, SP.chartY, lw, Math.max(1.4, bodyBottom - SP.chartY), 0.09,
        { placeholder: !!imL.placeholder || !imL.src, layout: 'half', multi: false, fit: imL.fit });
      if (imL.caption) s.addText(imL.caption, { x: lreg.x, y: SP.capY, w: lw, h: 0.35, align: 'center',
        fontFace: STYLE.font, fontSize: sz(11), color: STYLE.faint });
    } else if (lt !== 'points') {
      const lc = sec.left;
      chartBlock(s, lc, lreg.x, SP.chartY, lw, Math.max(1.4, Math.min(bodyBottom, CONTENT_BOTTOM_NOTE) - SP.chartY - (lc.cap ? 0.1 : 0)),
        lc.colors || dataColors(styleArg));
      if (lc.cap) s.addText(lc.cap, { x: lreg.x, y: SP.capY, w: lw, h: 0.35, align: 'center',
        fontFace: STYLE.font, fontSize: sz(12), color: STYLE.body });
    } else {
      drawPoints(sec.left, lreg.x, lw);
    }
    /* 右区只给 points 未写 type 时按要点渲染（此前默认 bar → 用空数据画出一张空图） */
    const rt = (sec.right && sec.right.type) || (sec.right && sec.right.points && !sec.right.values ? 'points' : 'bar');
    if (rt === 'table') {
      addTable(s, { head: sec.right.head, rows: sec.right.rows, colW: sec.right.colW },
        rx, SP.tableY, rw, bodyBottom - SP.tableY, { maxRowH: SP.tableRowH, minRowH: 0.3 });
    } else if (rt === 'image') {
      const im = (sec.right && sec.right.image) || {};
      addImageEl(s, im.src, rx, SP.chartY, rw, Math.max(1.4, bodyBottom - SP.chartY), 0.09,
        { placeholder: !!im.placeholder || !im.src, layout: 'half', multi: false, fit: im.fit });
      if (im.caption) s.addText(im.caption, { x: rx, y: SP.capY, w: rw, h: 0.35, align: 'center',
        fontFace: STYLE.font, fontSize: sz(11), color: STYLE.faint });
    } else if (rt === 'points') {
      drawPoints(sec.right, rx, rw);
    } else {
      const bc = sec.right;
      const dcols = bc.colors || dataColors(styleArg);
      chartBlock(s, bc, rx, SP.chartY, rw, Math.max(1.4, Math.min(bodyBottom, CONTENT_BOTTOM_NOTE) - SP.chartY - (bc.cap ? 0.1 : 0)), dcols);
      if (bc.cap) s.addText(bc.cap, { x: rx, y: SP.capY, w: rw, h: 0.35, align: 'center',
        fontFace: STYLE.font, fontSize: sz(12), color: STYLE.body });
    }
  } else if (type === 'diagram') {
    const D = PT.diagram;
    const dreg = REGIONS.regionOf('diagram', 'primary', {
      mode: MODE_NAME, bottom: bodyBottom,
    }) || { x: MX, y: D.bodyStartY, w: CW, h: bodyBottom - D.bodyStartY,
            layerBarW: D.layerBarW, layerGap: D.layerGap, maxLayerH: D.maxLayerH };
    const lys = sec.layers || [];
    const dStart = dreg.y;
    /* 图例按注释带口径落在 contentBottomWithNote 之上，图层与横切列整体让位（不压注释带） */
    const hasLeg = !!(sec.legend && sec.legend.length);
    const legBot = Math.min(bodyBottom, CONTENT_BOTTOM_NOTE);
    const dEnd = hasLeg ? Math.min(dreg.y + dreg.h, legBot - 0.4) : dreg.y + dreg.h;
    const n = Math.max(1, lys.length);
    /* M3：层高交给求解器（富余时拉伸到 1.6× 首选并整组居中，不再「挤在顶部」） */
    const lr = SOLVER.rows(dEnd - dStart, n, { pref: dreg.maxLayerH || D.maxLayerH, min: 0.5,
      max: (dreg.maxLayerH || D.maxLayerH) * 1.6, gap: D.layerGap });
    const lh = lr.size;
    /* 横切能力列（sec.aside：治理 / 安全 / 可观测）贯穿所有层，占右侧 asideW */
    const aside = isRec(sec.aside) ? sec.aside : null;
    const asideW = aside ? Math.min(2.4, CW * 0.2) : 0;
    const asideGap = aside ? 0.2 : 0;
    const dTop = dStart + lr.offset;
    lys.forEach((lay, li) => {
      const y = dTop + li * (lh + D.layerGap);
      const focus = lay[2] === 'focus';
      s.addShape('roundRect', { x: dreg.x, y, w: D.layerBarW, h: lh, rectRadius: 0.05,
        fill: { color: focus ? STYLE.soft : STYLE.surface }, line: focus ? { color: STYLE.accent, width: 1 } : { color: STYLE.line, width: 0.75 } });  // M9：焦点层用浅底 + 品牌字，与 HTML 一致
      s.addText(lay[0], { x: dreg.x + 0.1, y: y + 0.1, w: D.layerBarW - 0.2, h: lh - 0.2, align: 'center', valign: 'middle',
        fontFace: STYLE.font, fontSize: sz(10.5), bold: true, color: focus ? STYLE.accent : STYLE.faint });
      const nodes = lay[1] || [];
      const nn = Math.max(1, nodes.length);
      const availW = CW - D.layerBarW - 0.2 - asideW - asideGap;
      const nw = (availW - (nn - 1) * D.nodeGap) / nn;   /* 节点铺满整行（旧 nodeMaxW 上限留出右侧空洞） */
      nodes.forEach((nd, ni) => {
        const x = MX + D.layerBarW + 0.2 + ni * (nw + D.nodeGap);
        /* 节点三形态：{t,d,accent} 字典 | [标题, 注解] 数组 | 纯字符串
           （scaffold_report 发射数组形态；不归一化则 addText 收数组直接抛 TypeError） */
        const _nd = Array.isArray(nd) ? { t: nd[0], d: nd[1] } : nd;
        const acc = isRec(_nd) && _nd.accent;
        const ntt = String(isRec(_nd) ? (_nd.t || '') : (_nd == null ? '' : _nd));
        const nds = String(isRec(_nd) ? (_nd.d || '') : '');
        s.addShape('roundRect', { x, y, w: nw, h: lh, rectRadius: rr(0.06),
          fill: { color: acc ? STYLE.soft : STYLE.surface }, line: { color: STYLE.line, width: 0.75 } });
        /* 节点内标题/注解：注解底对齐会「浮回」标题上（R1）。改为标题顶对齐 + 注解钳在标题下边；
           空间不足时降级为单框混排（标题粗体 + 注解小字），禁止叠印。 */
        const padX = 0.12, padY = 0.10;
        const innerW = nw - padX * 2;
        const titleH = 0.32, noteH = 0.34, gapTN = 0.04;
        const needH = titleH + gapTN + (nds ? noteH : 0) + padY * 2;
        if (!nds || lh >= needH) {
          const tY = y + padY;
          s.addText(ntt, { x: x + padX, y: nds ? tY : y + lh / 2 - 0.18, w: innerW, h: titleH,
            fontFace: STYLE.font, fontSize: sz(nds ? 12 : 12.5), bold: true,
            color: acc ? STYLE.accent : STYLE.ink, valign: 'middle' });
          if (nds) {
            const nY = Math.max(tY + titleH + gapTN, y + lh - padY - noteH);
            s.addText(nds, { x: x + padX, y: nY, w: innerW, h: Math.min(noteH, y + lh - padY - nY),
              fontFace: STYLE.font, fontSize: sz(10), color: STYLE.faint, valign: 'top' });
          }
        } else {
          /* 空间不足：单框混排（同一文本框内富文本，禁拆两框叠印） */
          s.addText([
            { text: ntt, options: { fontSize: sz(11), bold: true, color: acc ? STYLE.accent : STYLE.ink, breakLine: true } },
            { text: nds, options: { fontSize: sz(9), color: STYLE.faint } },
          ], { x: x + padX, y: y + padY * 0.5, w: innerW, h: lh - padY,
            fontFace: STYLE.font, valign: 'top', lineSpacing: sz(11 * 1.25) });
        }
      });
      if (li < lys.length - 1) {
        const cy = y + lh + D.layerGap / 2;
        const cxm = MX + D.layerBarW / 2;
        /* 层间正交连接：竖线 + 箭头（替代两小块矩形） */
        s.addShape('rect', { x: cxm - 0.01, y: cy - 0.1, w: 0.02, h: 0.14,
          fill: { color: focus ? STYLE.accent : STYLE.line }, line: { type: 'none' } });
        s.addShape('triangle', { x: cxm - 0.06, y: cy + 0.02, w: 0.12, h: 0.1, rotate: 180,
          fill: { color: focus ? STYLE.accent : STYLE.line }, line: { type: 'none' } });
      }
    });
    if (aside) {
      const ax = MX + CW - asideW, ay = dTop, ah = n * lh + (n - 1) * D.layerGap;
      s.addShape('roundRect', { x: ax, y: ay, w: asideW, h: ah, rectRadius: rr(0.08),
        fill: { color: STYLE.soft }, line: { type: 'none' } });
      s.addText(String(aside.title || ''), { x: ax + 0.15, y: ay + 0.12, w: asideW - 0.3, h: 0.36,
        fontFace: STYLE.font, fontSize: sz(12.5), bold: true, color: STYLE.accent, valign: 'middle' });
      const its = (aside.items || []).slice(0, 6);
      const ir = SOLVER.rows(ah - 0.6, Math.max(1, its.length), { pref: 0.42, min: 0.3, max: 0.7, gap: 0.1 });
      its.forEach((it, k) => {
        const iy = ay + 0.55 + ir.offset + k * (ir.size + 0.1);
        s.addShape('roundRect', { x: ax + 0.12, y: iy, w: asideW - 0.24, h: ir.size, rectRadius: 0.05,
          fill: { color: STYLE.bg }, line: { type: 'none' } });
        s.addText(String(it), { x: ax + 0.2, y: iy, w: asideW - 0.4, h: ir.size, fontFace: STYLE.font,
          fontSize: sz(11), color: STYLE.ink, valign: 'middle' });
      });
    }
    if (sec.legend) {
      /* R2：图例进图区底部（与 HTML .arch__legend 同源），禁用 PH-0.62 固定偏移——
         那会压到来源行(6.72)与页码(7.0)。图例条自适应行内均分，右对齐。 */
      const lgH = 0.28;
      const lgY = Math.max(dStart, legBot - lgH - 0.02);
      const nLg = Math.max(1, sec.legend.length);
      const step = Math.min(2.4, CW / nLg);
      sec.legend.forEach((lg, li) => {
        /* 图例色点与图中编码一致：首项 = 强调色节点（当前焦点），其余 = 常规节点描边色 */
        s.addText([{ text: '● ', options: { color: li === 0 ? STYLE.accent : STYLE.line } },
          { text: String(lg), options: { color: STYLE.faint } }], { x: MX + CW - nLg * step + li * step, y: lgY, w: step - 0.05, h: lgH,
          fontFace: STYLE.font, fontSize: sz(10), align: 'left' });
      });
    }
  } else if (type === 'exhibit') {
    const ec = sec.chart || {};
    /* 主图区走布局 IR（layout_slots.json 的 primary 槽位），未命中时回落 PT.exhibit */
    const reg = REGIONS.regionOf('exhibit', 'primary', { withNote: !!(sec.soWhat || sec.footnote) })
      || { x: MX, y: PT.exhibit.chartY, w: CW, h: PT.exhibit.chartH };
    if (sec.exhibitNo) {
      s.addText(exhibitRuns(sec.exhibitNo, sec.cap, sz(11.5)), { x: MX, y: PT.exhibit.badgeY, w: CW, h: 0.35 });
    }
    if (ec.labels && ec.values) {
      const edcols = ec.colors || dataColors(styleArg);
      const h = Math.max(1.2, chartBottom(!!sec.soWhat, !!(sec.footnote || sec.note)) - reg.y - 0.05);
      if (ec.type === 'hbar') {
        chartBlock(s, ec, reg.x, reg.y, reg.w, h, edcols);
      } else {
        chartBlock(s, ec, reg.x + 0.4, reg.y - 0.1, reg.w - 0.8, h + 0.15, edcols);
      }
    }
  } else if (type === 'sankey') {
    infoSankey(s, sec, bodyY, bodyBottom);
  } else if (type === 'treemap') {
    infoTreemap(s, sec, bodyY, bodyBottom);
  } else if (type === 'boxplot') {
    infoBoxplot(s, sec, bodyY, bodyBottom);
  } else if (type === 'network') {
    infoNetwork(s, sec, bodyY, bodyBottom);
  } else if (type === 'marimekko') {
    infoMarimekko(s, sec, bodyY, bodyBottom);
  } else if (type === 'streamgraph') {
    infoStreamgraph(s, sec, bodyY, bodyBottom);
  } else {
    /* points（默认）：要点列表 + 可选右侧指标列（文本区与指标列严格分区，不重叠） */
    const P = PT.points;
    const pts = (sec.points || []).map(pointKV);
    const hasMetrics = !!(sec.metrics && sec.metrics.length);
    /* 指标列最多 3 个，列宽按剩余空间收敛，保证文本区不被侵占（原重叠缺陷） */
    const nM = hasMetrics ? Math.min(sec.metrics.length, 3) : 0;
    /* M0：指标列改为右侧纵向 MD3 tonal 卡片，与要点区等高；原「指标浮在右下角」造成上半页空洞 */
    const mcw = hasMetrics ? Math.min(3.4, Math.max(2.4, CW * 0.3)) : 0;
    const textW = hasMetrics ? Math.max(4.2, CW - mcw - 0.5) - 0.32 : CW - 0.4;
    /* 无注释带时主内容可用到 withNote+0.3（validate_pptx 安全网 0.35in）*/
    const avail = Math.min(bodyBottom, CONTENT_BOTTOM_NOTE + 0.3) - bodyY;
    /* 行高按可用高度均分（上限 1.25in），条目之间用细分隔线——少条目时不再挤在顶部 */
    const rowH = Math.max(0.3, Math.min(1.25, avail / Math.max(1, pts.length)));
    const _lo = listFitOpts(pts.length);
    /* 原文锁定的短清单（≤4 条）：字号放到 22pt 上限，行内垂直居中，撑满版心而不是缩在顶部 */
    const bigList = !!CONTENT.contentLocked && pts.length <= 4 && !hasMetrics;
    const fzB = fitFont(pts.map(p => (p[0] || '') + (p[1] || '')), textW - 0.32, avail,
      { max: bigList ? 22 : Math.min(15, _lo.max), gapFactor: _lo.gapFactor, lineFactor: _lo.lineFactor, ladder: bigList ? BIG_LADDER : undefined });
    const fz = sz(fzB), fzSm = sz(snapFont(fzB - 1));
    pts.forEach((p, i) => {
      const y = bodyY + i * rowH;
      s.addShape('rect', { x: MX, y: bigList ? y + (rowH - 0.1) / 2 - P.markSize / 2 : y + 0.16, w: P.markSize, h: P.markSize,
        fill: { color: STYLE.accent }, line: { type: 'none' } });
      s.addText([
        /* 纯字符串要点（pointKV 落在 p[1]）按主句排：主字号 + 墨色，不再前缀全角空格 */
        { text: p[0] ? p[0] + (p[1] ? '　' : '') : '', options: { fontSize: fz, bold: true, color: STYLE.ink } },
        { text: p[1], options: { fontSize: p[0] ? fzSm : fz, color: p[0] ? STYLE.body : STYLE.ink, bold: !p[0] && bigList } },
      ], { x: MX + 0.32, y, w: textW, h: rowH - 0.1, fontFace: STYLE.font, valign: bigList ? 'middle' : 'top' });
      if (i < pts.length - 1 && rowH >= 0.6)
        s.addShape('rect', { x: MX, y: y + rowH - 0.06, w: textW + 0.32, h: 0.01,
          fill: { color: STYLE.line }, line: { type: 'none' } });
    });
    if (hasMetrics) {
      const gx = PW - MX - mcw;
      const mGap = 0.2;
      const mh = (avail - (nM - 1) * mGap) / nM;
      const vSize = nM >= 3 ? sz(28) : sz(34);
      sec.metrics.slice(0, nM).map(metricKV).forEach((m, i) => {
        const y = bodyY + i * (mh + mGap);
        s.addShape('roundRect', { x: gx, y, w: mcw, h: mh, rectRadius: 0.09,
          fill: { color: STYLE.soft }, line: { type: 'none' } });
        s.addText(m[0], { x: gx + 0.25, y: y + 0.12, w: mcw - 0.5, h: Math.min(P.metricValH, mh * 0.55),
          fontFace: STYLE.fontDisplay, fontSize: vSize, bold: true, color: STYLE.accent, valign: 'bottom' });
        s.addText(m[1], { x: gx + 0.25, y: y + 0.12 + Math.min(P.metricValH, mh * 0.55), w: mcw - 0.5,
          h: Math.max(0.3, mh - 0.24 - Math.min(P.metricValH, mh * 0.55)),
          fontFace: STYLE.font, fontSize: sz(11), color: STYLE.body, valign: 'top' });
      });
    }
  }
  /* research 通用可选件：so-what 结论条 + 页脚来源行 + 待核实条（所有页型共用同一槽位） */
  /* R2：verdict 已占 annotation 槽位时跳过 soWhat，禁止同槽双条叠印 */
  if (sec.soWhat && !sec.verdict) soWhatBar(s, sec.soWhat);
  /* R2：note 与 footnote 共用注释带末行（禁 note.y=6.55 压 so-what） */
  noteOrFootnote(s, sec);
  if (flagH) flagBar(s, flagItems, flagY);
  /* 演讲者备注（口径/含义/来源沉 notes，不堆版面） */
  const _notes = [];
  if (sec.lead) _notes.push('导语：' + sec.lead);
  if (sec.chart && (sec.chart.unit || sec.chart.max != null)) {
    _notes.push('图表口径：单位 ' + (sec.chart.unit || '无') + '，量程 ' + (sec.chart.max != null ? sec.chart.max : '自动'));
  }
  /* 数据表：notes 策略把数据写入备注，保证图表数据可追溯（inline 策略已在页内附原生表格） */
  const _chartData = sec.chart || ((sec.right && sec.right.labels && sec.right.values) ? sec.right : null);
  if (_chartData && _chartData.labels && _chartData.values) {
    if (dataTableMode(_chartData) === 'notes') {
      _notes.push('数据表（' + (_chartData.type || 'bar') + '）：\n' + dataTableText(_chartData));
    }
  }
  /* 信息图页型：notes 策略把页型数据表写入备注，保证数据可追溯 */
  const _infoRows = infoTableRows(sec);
  if (_infoRows && _infoRows.length && infoDataTableMode(sec) === 'notes') {
    _notes.push('数据表（' + type + '）：\n' + _infoRows.map(r => r.join(' | ')).join('\n'));
  }
  if (sec.steps) _notes.push('步骤：' + sec.steps.map(st => {
    const t = isRec(st) ? st.t : (Array.isArray(st) ? st[0] : st);
    return t || '';
  }).join(' → '));
  if (sec.items) _notes.push('达成对比：' + sec.items.map(it => {
    const b = bulletKV(it);
    return String(b[0] || '') + (b[1] == null ? '' : ' ' + b[1]) + (b[2] == null ? '' : '/' + b[2]);
  }).join('；'));
  if (sec.levels) _notes.push('层级：' + sec.levels.map(l => (isRec(l) ? l.t : l[0]) || '').join(' → '));
  DENSE.overflow(sec).forEach(o => _notes.push('（版面上限外，移入备注）' + o[1]));
  if (sec.soWhat) _notes.push('结论：' + sec.soWhat);
  if (sec.layoutPreset) _notes.push('布局骨架：' + sec.layoutPreset);
  if (flagItems.length) _notes.push('待核实（需二次确认）：' + flagItems.join('；'));
  if (sec.note) _notes.push('注：' + sec.note);
  if (sec.footnote) _notes.push('来源：' + sec.footnote);
  if (sec.image && sec.image.caption) _notes.push('图片说明：' + sec.image.caption);
  if (sec.image && sec.image.placeholder) {
    const _size = (IMG.recommendedSizePx || {})[String(sec.image.layout || 'full').toLowerCase()] || '';
    _notes.push('配图占位（交付前建议替换）：' + (sec.image.hint || ('建议 ' + _size + 'px，替换 image.src 或 image.items 即可')));
  }
  if (sec.image && Array.isArray(sec.image.items) && sec.image.items.length) {
    _notes.push('图片清单：' + sec.image.items.map((it, i) => (i + 1) + '.' + ((it && (it.caption || it.alt)) || '（待补说明）')).join('；'));
  }
  const _sn = mergeNotes(/（续）$/.test(String(sec.title || '')) ? null : sec.speakerNotes, _notes.join('\n'));
  if (_sn) s.addNotes(_sn);
});

/* 收尾 */
(function closing() {
  const s = base();
  const C = PT.closing;
  /* 收尾页用主题一致强调带（accent-soft 底 + 常规文字）——浅色主题下不再出现深色收尾页 */
  s.addShape('rect', { x: 0, y: 0, w: PW, h: PH, fill: { color: STYLE.soft }, line: { type: 'none' } });
  s.addShape('rect', { x: MX, y: C.eyebrowY, w: 0.9, h: 0.045, fill: { color: STYLE.accent }, line: { type: 'none' } });
  const cEb = !CHROME_FLAGS.showEyebrow ? '' : (CONTENT.closing.eyebrow != null ? CONTENT.closing.eyebrow : '下一步');
  if (cEb) s.addText(cEb, { x: MX, y: C.eyebrowY + 0.16, w: CW, h: 0.4, fontFace: STYLE.font,
    fontSize: sz(11), bold: true, color: STYLE.accent, charSpacing: 2 });
  s.addText(BT(CONTENT.closing.title, CW - 1, sz(30)), { x: MX, y: C.titleY, w: CW - 1, h: C.titleH, fontFace: STYLE.fontDisplay,
    fontSize: sz(30), bold: true, color: STYLE.ink });
  /* 要点可为字符串（美化路由原样搬运）：统一成 [主句, 说明] */
  const pts = (CONTENT.closing.points || []).map(p => Array.isArray(p) ? p : [String(p), '']);
  const n = Math.max(1, pts.length);
  const cw3 = (CW - (n - 1) * 0.3) / n;
  pts.forEach((p, i) => {
    const x = MX + i * (cw3 + 0.3);
    if (!p[1]) {
      /* 只有主句（美化原文常见「欢迎批评指正」）：卡片贴合文字高度，主句放大居中，不留半张空卡 */
      const hh = 1.05;
      s.addShape('roundRect', { x, y: C.pointsY - 0.2, w: cw3, h: hh, rectRadius: 0.09,
        fill: { color: STYLE.surface }, line: { color: STYLE.line, width: 0.75 } });
      s.addText(p[0], { x: x + 0.28, y: C.pointsY - 0.2, w: cw3 - 0.56, h: hh, fontFace: STYLE.font,
        fontSize: sz(String(p[0]).length > 28 ? 17 : 20), bold: true, color: STYLE.accent, valign: 'middle' });
      return;
    }
    s.addShape('roundRect', { x, y: C.pointsY - 0.2, w: cw3, h: C.pointTitleH + C.pointBodyH + 0.32,
      rectRadius: 0.09, fill: { color: STYLE.surface }, line: { color: STYLE.line, width: 0.75 } });
    s.addText(p[0], { x: x + 0.18, y: C.pointsY, w: cw3 - 0.36, h: C.pointTitleH, fontFace: STYLE.font,
      fontSize: sz(17), bold: true, color: STYLE.accent });
    s.addText(p[1], { x: x + 0.18, y: C.pointsY + C.pointTitleH, w: cw3 - 0.36, h: C.pointBodyH, fontFace: STYLE.font,
      fontSize: sz(12.5), color: STYLE.body });
  });
  const _cln = mergeNotes(CONTENT.closing.speakerNotes, pts.map(p => '· ' + p[0] + (p[1] ? '：' + p[1] : '')).join('\n'));
  if (_cln) s.addNotes(_cln);
})();

/* 页码 */
pptx._slides.forEach((s, i) => footer(s, i + 1, pptx._slides.length));

if (ICON_MISSES.length) {
  console.error('[build_pptx] 图标资产缺失 ' + ICON_MISSES.length + ' 处（已回落色块）：' + ICON_MISSES.slice(0, 8).join('、'));
  if (STRICT) { console.error('[build_pptx] FAIL: --strict 下图标缺失不得交付'); process.exit(3); }
}
const out = _argVal('--out') || process.argv.slice(2).find(a => !a.startsWith('-')) || 'topmind-presentation-demo.pptx';
/* M10：字体回退链落到 XML——pptxgenjs 的 fontFace 会把同一字体写进 latin / ea / cs；
   衬线标题需要「西文 Georgia + 中文 SimSun」分开声明，写盘前对每页 XML 改写 ea / cs。 */
async function writeWithFontPairs(file) {
  const pairs = Object.values(FONT_PAIRS).filter(p => p && p.latin && p.ea && p.latin !== p.ea);
  if (!pairs.length) return pptx.writeFile({ fileName: file });
  const JSZip = require('jszip');
  const buf = await pptx.write({ outputType: 'nodebuffer' });
  const zip = await JSZip.loadAsync(buf);
  for (const name of Object.keys(zip.files).filter(n => /^ppt\/(slides\/slide\d+|notesSlides\/notesSlide\d+)\.xml$/.test(n))) {
    let xml = await zip.file(name).async('string');
    for (const p of pairs) {
      const L = p.latin.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      xml = xml.replace(new RegExp('(<a:latin typeface="' + L + '"[^>]*/>)<a:ea typeface="' + L + '"([^>]*)/><a:cs typeface="' + L + '"', 'g'),
        '$1<a:ea typeface="' + p.ea + '"$2/><a:cs typeface="' + p.ea + '"');
    }
    zip.file(name, xml);
  }
  fs.writeFileSync(file, await zip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE' }));
}
writeWithFontPairs(out).then(() => {
  console.log('已生成: ' + out + '  (风格: ' + (STYLE_PRESETS[styleArg] ? styleArg : 'business-blue') +
    ' · 主题: ' + (THEME === 'dark' ? '深色 dark' : '浅色 light') + ' · 模式: ' + MODE_NAME + ')');
  console.log(`[build_pptx] 行距：1.5× ${LS_STATS.def} 处 · 1.3× ${LS_STATS.min} 处（containers.lineSpacing）`);
  if (SHRINK_FLOOR_HITS.length) {
    const low = SHRINK_FLOOR_HITS.filter(h => h.pt <= (FS_POLICY.warnBelow || 9.5));
    console.warn('[build_pptx] 注意：' + SHRINK_FLOOR_HITS.length + ' 处文本缩字号已触底' +
      (low.length ? '（其中 ' + low.length + ' 处 ≤ ' + (FS_POLICY.warnBelow || 9.5) + 'pt）' : '') +
      '——该页内容超出版式承载力。');
    SHRINK_FLOOR_HITS.slice(0, 5).forEach(h =>
      console.warn('    · ' + h.pt + 'pt：“' + h.sample + '…”'));
    console.warn('  处置顺序：①列表化/精炼 ②升级承载形态 ③换/扩组合版式 ④分区 ⑤拆页（不要靠继续缩字号硬塞）。');
  }
  console.log('下一步（质检硬门禁，本技能内置脚本；--model 启用模型往返保真检查）:');
  console.log('  python scripts/validate_pptx.py "' + out + '" --strict' + (modelArg ? ' --model="' + modelArg + '"' : ' --model="<报告.model.json>"'));
  if (OVERLAP_PREEMIT.length) {
    console.warn('[build_pptx] PREEMIT_OVERLAP 共 ' + OVERLAP_PREEMIT.length + ' 处（发射前几何自检，详见上方 warn）——请先修区域分配再交付。');
  }
}).catch((e) => {
  /* 写盘失败（无权限/磁盘满/路径非法）必须干净报错，不得 unhandled rejection 裸堆栈 */
  console.error('[build_pptx] FAIL: 写入 PPTX 失败 ' + out + '：' + (e && e.message));
  process.exit(1);
});
