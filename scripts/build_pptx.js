/**
 * TopPPT HTML· PPTX 精导（基于 PptxGenJS）
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
  node scripts/build_pptx.js [输出.pptx] --model=<模型.json> [--style=<风格>] [--theme=light|dark]

  1) 抽模型：python scripts/extract_model.py <报告.html>（生成 <报告>.model.json）
  2) 生成：  node scripts/build_pptx.js 报告.pptx --model=报告.model.json
  3) 质检：  python scripts/validate_pptx.py 报告.pptx --strict --model=报告.model.json

参数：
  --model=<file>   内容模型 JSON（推荐：由 extract_model.py 从 HTML 报告抽取；缺省用内嵌示例）
  --style=<name>   覆盖模型的风格（9 套风格 token 见 scripts/layout-constants.json）
  --theme=light|dark  主题（--theme 覆盖 > 模型 theme > 默认 light）`);
    process.exit(0);
  }
  const known = /^(--model=|--style=|--theme=)/;
  let positional = 0;
  for (const a of raw) {
    if (a.startsWith('-')) {
      if (!known.test(a)) {
        console.error(`[build_pptx] FAIL: 未知参数 ${a} —— 拒绝执行（用 --help 查看用法）`);
        process.exit(2);
      }
    } else if (++positional > 1) {
      console.error(`[build_pptx] FAIL: 多余的位置参数 ${a} —— 只接受一个输出文件名`);
      process.exit(2);
    }
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

/* ══ 语义图标真导出（SVG→PNG · scripts/icon-assets.json 预生成缓存）══
 * HTML .card__ico / .ul--ico 的 SVG 图标在此栅格化为 PNG 嵌入，不再用 accent 方块替代。
 * 图标图 objectName 统一 `icon:` 前缀 —— validate_pptx 单独计数，不进 pictures 内容图门禁。 */
const ICON_LIB = require('./icon_lib.js');
let ICON_ASSETS = { icons: {}, px: 64 };
try {
  ICON_ASSETS = JSON.parse(fs.readFileSync(path.join(__dirname, 'icon-assets.json'), 'utf-8'));
} catch (e) {
  try {
    const { execFileSync } = require('child_process');
    execFileSync(process.execPath, [path.join(__dirname, 'build_icon_assets.js')],
      { env: process.env, stdio: 'pipe' });
    ICON_ASSETS = JSON.parse(fs.readFileSync(path.join(__dirname, 'icon-assets.json'), 'utf-8'));
  } catch (e2) {
    console.warn('[build_pptx] 图标资产缺失且生成失败，卡片头回落 accent 方块：' + (e2 && e2.message));
  }
}
function _normColor(c) {
  if (typeof c !== 'string') return '#333333';
  let v = c.trim().toLowerCase();
  if (/^[0-9a-f]{6}$/.test(v)) v = '#' + v;
  if (/^[0-9a-f]{3}$/.test(v)) v = '#' + v;
  return v;
}
/** 取图标 PNG data URI；无缓存时按名挑色兜底（accent → 首色 → 包内 512px PNG → null） */
function iconPng(name, colorHex) {
  const n = name && ICON_ASSETS.icons[name] ? name : ICON_LIB.pickIconName(name, 0);
  const bag = ICON_ASSETS.icons[n];
  if (bag) {
    const want = _normColor(colorHex);
    if (bag[want]) return bag[want];
    const keys = Object.keys(bag);
    if (keys.length) return bag[keys[0]];
  }
  // 无 sharp / 无预生成资产时的可靠回落：包内 512px 预渲染 PNG（python-pptx/pptxgenjs 均可直接嵌入）
  try {
    const p = ICON_LIB.iconPngPath(n);
    if (p) return 'data:image/png;base64,' + fs.readFileSync(p).toString('base64');
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
  return false;
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
function fitFont(items, widthIn, availIn, opts) {
  opts = opts || {};
  const floor = opts.floor != null ? opts.floor : modeFloorPt();
  const maxSteps = opts.maxShrinkSteps != null ? opts.maxShrinkSteps : FS_POLICY.maxShrinkSteps;
  const raw = (opts.ladder || FONT_LADDER).filter(v => v <= (opts.max || 99) && v >= floor);
  const lineFactor = opts.lineFactor || TM_LINE;
  const pad = opts.pad || 0;
  const needH = (f) => {
    let h = 0;
    for (const it of items) h += estTextH(it, widthIn, f, lineFactor) + f * (opts.gapFactor || 0.5) / 72;
    return h + pad;
  };
  /* 首选：阶梯中最大且装得下的字号 */
  for (const f of raw) {
    if (needH(f) <= availIn) return f;
  }
  /* 全装不下：在 maxShrinkSteps 内从「首选档」下探（首选=opts.max 或阶梯首档） */
  const preferred = raw.length ? raw[0] : floor;
  const prefIdx = (opts.ladder || FONT_LADDER).indexOf(preferred);
  const limited = (opts.ladder || FONT_LADDER)
    .slice(prefIdx, prefIdx + 1 + maxSteps)
    .filter(v => v >= floor && v <= (opts.max || 99));
  for (const f of limited) {
    if (needH(f) <= availIn) return f;
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
  MODEL_DIR = path.dirname(path.resolve(modelArg));   // 素材图片相对路径锚点
  if (CONTENT.style && !styleArg) styleArg = CONTENT.style;   // 模型里的风格作为默认
} else {
  /* 未传 --model：按内嵌示例生成演示 PPTX。必须出声——静默产出会让人误以为是真实报告
     （读模型失败时本脚本选择硬中断，此处同理不得静默）。 */
  console.warn('[build_pptx] 警告：未传 --model=<模型.json>，将按内嵌示例内容生成演示 PPTX（非真实报告内容）。');
  console.warn('  真实交付请先跑 python scripts/extract_model.py <报告.html>，再用 --model=<报告.model.json> 重跑。');
CONTENT = {
  title: '让想法被看见',
  subtitle: 'TopPPT HTML 报告生成示例 · 16:9 可编辑 PPTX',
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
pptx.title = CONTENT.title || 'TopPPT HTML 报告';
pptx.subject = CONTENT.subtitle || '';
pptx.author = 'TopPPT HTML';
pptx.company = 'TopMindspace';

function base() {
  const s = pptx.addSlide();
  s.background = { color: STYLE.bg };
  s.addShape('rect', { x: 0, y: 0, w: PW, h: PH, fill: { color: STYLE.bg }, line: { type: 'none' } });
  return s;
}
function head(s, eyebrow, title, lead) {
  const H = REGIONS.regionOf('head', 'head') || {
    x: MX, y: PT.common.headEyebrowY, w: CW, h: 0.4,
    titleY: PT.common.headTitleY, ruleY: PT.common.headRuleY, leadY: PT.common.leadY,
  };
  if (eyebrow) s.addText(eyebrow, { x: H.x, y: H.y, w: H.w, h: 0.4, fontFace: STYLE.font,
    fontSize: sz(13), bold: true, color: STYLE.accent, charSpacing: 2 });
  /* 主标题自适应（adaptiveText.title 单源）：先按字符数分档定上限，再按高度验算降一档，避免压到分隔线 */
  const titleH = eyebrow ? (H.ruleY - H.titleY - 0.06) : 1.6 - 0.6;
  const tMax = titleMaxFor(title);
  const tSize = sz(estTextH(title, CW, sz(tMax), 1.25) > titleH ? Math.min(tMax, AT_TITLE.step1 || 24) : tMax);
  s.addText(title, { x: H.x, y: eyebrow ? H.titleY : 0.6, w: H.w, h: Math.max(0.6, titleH),
    fontFace: STYLE.fontDisplay, fontSize: tSize, bold: true, color: STYLE.ink, fit: 'shrink' });
  s.addShape('rect', { x: H.x, y: eyebrow ? H.ruleY : 1.6, w: 0.9, h: 0.045, fill: { color: STYLE.accent }, line: { type: 'none' } });
  if (lead) s.addText(lead, { x: H.x, y: H.leadY || PT.common.leadY, w: H.w, h: 0.5, fontFace: STYLE.font,
    fontSize: sz(14), color: STYLE.body });
}
function footer(s, n, total) {
  s.addText(`${n} / ${total}`, { x: PW - 1.4, y: LAY.pageNumY != null ? LAY.pageNumY : PH - 0.5,
    w: 0.9, h: 0.3, align: 'right', fontFace: STYLE.font, fontSize: sz(10), color: STYLE.faint });
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
function soWhatBar(s, text) {
  const R = REGIONS.regionOf('exhibit', 'annotation') ||
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
  const R = REGIONS.regionOf('exhibit', 'footnote') ||
    { x: MX, y: PT.exhibit.footnoteY, w: CW - 1.2, h: 0.32 };
  s.addText(text, { x: R.x, y: R.y, w: R.w, h: R.h,
    fontFace: STYLE.font, fontSize: sz(9.5), color: STYLE.faint, objectName: trName('footnote'), fit: 'shrink' });
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
   占位符是原生形状而非图片，pictures 不增，且标签串与 A 通道逐字一致（cross_verify 逐页比对）。 */
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
  }
  if (radius) o.rounding = true;
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
    const ptsI = points || [];
    const rowHI = fitRowH(ih - 0.1, ptsI.length, IM.noteRowH || 0.62, 0.3);
    const fzI = fitFont(ptsI.map(p => (p[0] || '') + (p[1] || '')), rwI - 0.3, ih, { max: 14, gapFactor: 0.6 });
    const fz = sz(fzI), fzSm = sz(snapFont(fzI - 1));
    ptsI.forEach((pt, i) => {
      const lyI = iy + i * rowHI;
      s.addShape('rect', { x: rxI, y: lyI + rowHI / 2 - 0.06, w: 0.12, h: 0.12,
        fill: { color: STYLE.accent }, line: { type: 'none' } });
      s.addText([
        { text: (pt[0] || '') + '　', options: { fontSize: fz, bold: true, color: STYLE.ink } },
        { text: pt[1] || '', options: { fontSize: fzSm, color: STYLE.body } },
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
    showValue: !isLine && !multi,
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

  /* ── 原生技巧 ── */
  if (trick.indexOf('stacked+hiddenBase') === 0) { waterfallChart(s, c, pos); return; }
  if (trick.indexOf('doughnut+firstSliceAng') === 0) { gaugeChart(s, c, pos); return; }
  if (trick.indexOf('multiType') === 0) { paretoChart(s, c, pos); return; }

  /* ── 饼 / 环 ── */
  if (kind === 'doughnut' || kind === 'pie') {
    const opts = Object.assign(chartBaseOpts(c, colors || donutColors(styleArg), false, kind), pos, {
      showValue: true, dataLabelPosition: 'ctr',
      dataLabelColor: STYLE.onAccent, showPercent: true,
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
  const opts = Object.assign(chartBaseOpts(c, colors, multi, kind), pos);
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
  let cdata = chartSeries(c);
  if (t === 'hbar') {
    /* 条形图（barDir=bar）类目轴自下而上绘制：反转数据使首项居顶，
       与 HTML svg-hbar 及 A 通道 hbarRows 同序（标签-数值配对不变） */
    cdata = cdata.map(se => ({ name: se.name,
      labels: (se.labels || []).slice().reverse(), values: (se.values || []).slice().reverse() }));
    /* 单系列时颜色按数据点分配：颜色跟随数据走，与 A 通道 dcols[j%5] 同归属 */
    if (!multi && colors && colors.length) {
      const _n = Math.max(1, (cdata[0].values || []).length);
      opts.chartColors = (cdata[0].values || []).map((_, i) => colors[(_n - 1 - i) % colors.length]);
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
function waterfallChart(s, c, pos) {
  const labels = (c.labels || []).map(String);
  const deltas = (c.values || []).map(Number);
  let run = 0;
  const bases = [], ups = [], downs = [], cum = [];
  deltas.forEach(d => {
    const b = d >= 0 ? run : run + d;
    bases.push(b); ups.push(d >= 0 ? d : 0); downs.push(d < 0 ? -d : 0);
    run += d; cum.push(run);
  });
  const series = [
    { name: '基底', labels: labels, values: bases },
    { name: '增量', labels: labels, values: ups },
    { name: '减量', labels: labels, values: downs },
  ];
  const inner = {
    barDir: 'col', barGrouping: 'stacked', showValue: false, showLegend: false,
    chartColors: [STYLE.bg, STYLE.accent, STYLE.faint],
    catAxisLabelColor: STYLE.faint, catAxisLabelFontSize: sz(10.5), catAxisLabelFontFace: STYLE.font,
    valAxisHidden: true, valAxisLineShow: false, catAxisLineShow: false,
    catGridLine: { style: 'none' }, valGridLine: { style: 'none' }, valAxisMinVal: 0, showTitle: false,
  };
  const outer = Object.assign({}, inner, pos);
  try {
    s.addChart([
      { type: pptx.ChartType.bar, data: series, options: inner },
      { type: pptx.ChartType.line, data: [{ name: '累计', labels: labels, values: cum }],
        options: { lineSize: 1.25, lineSmooth: false, lineDataSymbol: 'none', chartColors: [STYLE.body] } },
    ], outer);
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
function nativeDonutChart(s, dcn, dcols, bottomY) {
  const d = PT.donut;
  /* 有结论条/脚注时压半径，避免环图底边压进 soWhatY（D11） */
  let r = d.r;
  const cy = d.centerY;
  if (bottomY != null && cy + r > bottomY) {
    r = Math.max(0.9, bottomY - cy - 0.04);
  }
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
 * 与 A 通道（assets/pptx-export.js 的 chartShapes）语义一致：类别标签与数值都落为文本，
 * 保证 cross_verify 逐页文本集合一致（数值 token 由 cross_verify 过滤）。
 * 复杂信息图（sankey/treemap/boxplot/network/marimekko/streamgraph）请用专属页型承载。 */
function shapeChart(s, c, x, y, w, h, dcols) {
  const t = String(c.type || 'bar').toLowerCase();
  if (t === 'funnel') { shapeFunnel(s, c, x, y, w, h, dcols); return; }
  if (t === 'progress') { shapeRows(s, c, x, y, w, h, dcols, 'progress'); return; }
  if (t === 'radialbar') { shapeRows(s, c, x, y, w, h, dcols, 'radialbar'); return; }
  if (t === 'dumbbell') { shapeRows(s, c, x, y, w, h, dcols, 'dumbbell'); return; }
  if (t === 'lollipop') { shapeRows(s, c, x, y, w, h, dcols, 'lollipop'); return; }
  if (t === 'dotplot') { shapeRows(s, c, x, y, w, h, dcols, 'dotplot'); return; }
  if (t === 'bulletchart') { shapeRows(s, c, x, y, w, h, dcols, 'bullet'); return; }
  if (t === 'gantt') { shapeGantt(s, c, x, y, w, h, dcols); return; }
  if (t === 'vsbar') { shapeVsbar(s, c, x, y, w, h, dcols); return; }
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
 * 不使用 preset pie/arc 替代曲线语义；标签与数值走底部图例行（文本与 A 通道一致）。 */
function shapeRose(s, c, x, y, w, h, dcols) {
  const M = shapeMetrics(c, w, h);
  const legendH = Math.min(0.72, Math.max(0.3, h * 0.18));
  const plotH = Math.max(0.6, h - legendH - 0.08);
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
    const bodyCol = up ? STYLE.accent : STYLE.line;
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
/* 漏斗：逐层收窄的梯形行（用宽度递减的矩形近似，保留标签与数值） */
function shapeFunnel(s, c, x, y, w, h, dcols) {
  const M = shapeMetrics(c, w, h);
  const rowH = Math.max(0.26, Math.min(0.72, h / M.n));
  M.labels.forEach((lb, i) => {
    const v = M.values[i] || 0;
    const ry = y + i * rowH;
    const hot = v === M.top;
    const dc = dcols ? dcols[i % dcols.length] : null;
    const frac = Math.max(0.06, v / M.vmax);
    const bw = Math.max(0.4, (w - M.valW - 0.2) * frac);
    const bx = x + (w - M.valW - 0.2 - bw) / 2;
    s.addShape('rect', { x: bx, y: ry + 0.02, w: bw, h: rowH - 0.06,
      fill: { color: dc || (hot ? STYLE.accent : STYLE.faint) }, line: { type: 'none' } });
    s.addText(lb, { x: bx, y: ry + 0.02, w: bw, h: rowH - 0.06,
      fontFace: STYLE.font, fontSize: sz(11.5), bold: true, color: STYLE.onAccent, align: 'center', valign: 'middle' });
    shapeValue(s, c, v, x + w - M.valW, ry, M.valW, rowH, hot);
  });
}
/* 甘特 / 路线：行 = 标签 + 偏移起点 + 时长条 */
function shapeGantt(s, c, x, y, w, h, dcols) {
  const M = shapeMetrics(c, w, h);
  const rowH = Math.max(0.24, Math.min(0.6, h / M.n));
  const trackX = x + M.labelW + 0.08;
  const trackW = w - M.labelW - M.valW - 0.2;
  /* 时间轴跨度 = 显式 max，或所有条目的「起点 + 时长」最大值（原按「时长最大值」
   * 导致 start 偏移超出轨道、形状越界的缺陷） */
  let span = Number(c.max) || 0;
  if (!span) {
    M.values.forEach((dur, i) => {
      const st = (c.start && Number(c.start[i])) || 0;
      span = Math.max(span, st + (Number(dur) || 0));
    });
  }
  span = span || 1;
  M.labels.forEach((lb, i) => {
    const start = (c.start && Number(c.start[i])) || 0;
    const dur = M.values[i] || 0;
    const ry = y + i * rowH;
    const hot = dur === M.top;
    const dc = dcols ? dcols[i % dcols.length] : null;
    shapeLabel(s, lb, x, ry, M.labelW - 0.06, rowH, STYLE.body);
    s.addShape('rect', { x: trackX, y: ry + rowH * 0.3, w: trackW, h: rowH * 0.36,
      fill: { color: STYLE.surface }, line: { type: 'none' } });
    s.addShape('rect', { x: trackX + (start / span) * trackW, y: ry + rowH * 0.3,
      w: Math.max(0.05, (dur / span) * trackW), h: rowH * 0.36,
      fill: { color: dc || (hot ? STYLE.accent : STYLE.faint) }, line: { type: 'none' } });
    shapeValue(s, c, dur, trackX + trackW + 0.06, ry, M.valW, rowH, hot);
  });
}
/* 双向对比条（vsbar）：以中线为轴向左/右展开（正值向右、负值向左） */
function shapeVsbar(s, c, x, y, w, h, dcols) {
  const M = shapeMetrics(c, w, h);
  const rowH = Math.max(0.24, Math.min(0.6, h / M.n));
  const labelW = M.labelW;
  const halfW = (w - labelW - M.valW - 0.2) / 2;
  const midX = x + labelW + 0.08 + halfW;
  const barH = Math.max(0.14, rowH * 0.5);
  M.labels.forEach((lb, i) => {
    const v = M.values[i] || 0;
    const ry = y + i * rowH;
    const cy = ry + rowH / 2;
    const hot = v === M.top;
    shapeLabel(s, lb, x, ry, labelW - 0.06, rowH, STYLE.body);
    const bw = Math.max(0.03, Math.abs(v) / M.vmax * halfW);
    const bx = v >= 0 ? midX : midX - bw;
    s.addShape('rect', { x: bx, y: cy - barH / 2, w: bw, h: barH,
      fill: { color: hot ? STYLE.accent : STYLE.faint }, line: { type: 'none' } });
    s.addShape('rect', { x: midX - 0.008, y: ry + 0.04, w: 0.016, h: rowH - 0.08,
      fill: { color: STYLE.line }, line: { type: 'none' } });
    shapeValue(s, c, v, midX + halfW + 0.06, ry, M.valW, rowH, hot);
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
        bold: ri === 0, color: ri === 0 ? STYLE.onAccent : STYLE.body,
        fill: { color: ri === 0 ? STYLE.accent : STYLE.bg },
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
 * 与 A 通道（assets/pptx-export.js）同规则、文本集合一致（cross_verify 逐页比对）。 */
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
  return m === 'appendix' ? 'inline' : m;
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
    color: ri === 0 ? STYLE.onAccent : STYLE.body,
    fill: { color: ri === 0 ? STYLE.accent : STYLE.bg } } })));
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
/* 桑基图：分层节点 + 流带（流量线性编码；流带上下边界分别采样，采样点 ≥16） */
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
  const thr = (n) => Math.max(inSum[n] || 0, outSum[n] || 0);
  const totalFlow = flows.reduce((a, f) => a + Number(f[2]), 0) || 1;
  const plotH = P.y1 - P.y0;
  const colW = CW / (maxLv + 1);
  const geo = {};
  for (let l = 0; l <= maxLv; l++) {
    const lv = nodes.filter((n, i) => level[i] === l);
    const sum = lv.reduce((a, n) => a + thr(n), 0) || 1;
    const availH = plotH - G.nodeGap * Math.max(0, lv.length - 1);
    let cy = P.y0;
    lv.forEach(n => {
      const h = Math.max(G.minBandH, thr(n) / sum * availH);
      geo[n] = { x: MX + l * colW + colW * 0.5 - G.nodeW / 2, y: cy, h: h, lv: l };
      cy += h + G.nodeGap;
    });
  }
  const used = {};
  flows.forEach(f => {
    const a = geo[f[0]], b = geo[f[1]];
    if (!a || !b) return;
    const v = Number(f[2]) || 0;
    const w = Math.max(0.03, v / totalFlow * plotH * 0.55);
    used[f[0]] = (used[f[0]] || 0) + w; used[f[1]] = (used[f[1]] || 0) + w;
    const yA = a.y + used[f[0]] - w / 2, yB = b.y + used[f[1]] - w / 2;
    const x0 = a.x + G.nodeW, x1 = b.x;
    const n = Math.max(INFO_MIN_SAMPLES, Math.round((x1 - x0) / 0.1));
    const pts = [];
    for (let i = 0; i <= n; i++) {
      const t = i / n, e = sstep(t);
      const x = x0 + (x1 - x0) * t;
      const cyy = yA + (yB - yA) * e;
      pts.push([x, cyy - w / 2, cyy + w / 2]);
    }
    ribbonRects(s, pts, STYLE.soft);
    s.addText(String(v) + (sec.unit || ''), { x: (x0 + x1) / 2 - 0.5, y: (yA + yB) / 2 - 0.14, w: 1.0, h: 0.28,
      align: 'center', fontFace: STYLE.font, fontSize: sz(9.5), color: STYLE.faint });
  });
  nodes.forEach(n => {
    const g = geo[n];
    s.addShape('rect', { x: g.x, y: g.y, w: G.nodeW, h: g.h, fill: { color: STYLE.accent }, line: { type: 'none' } });
    const lw = Math.min(G.labelW, colW * 0.6);
    const last = (g.lv === maxLv);
    s.addText(n, { x: last ? (g.x - lw - 0.06) : (g.x + G.nodeW + 0.06), y: g.y, w: lw,
      h: Math.max(0.24, g.h), align: last ? 'right' : 'left', valign: 'middle',
      fontFace: STYLE.font, fontSize: sz(10.5), bold: true, color: STYLE.body });
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
  out.forEach(o => {
    const p = o.it.v / maxV;
    const lvl = p >= 0.66 ? 3 : (p >= 0.33 ? 2 : 1);
    const fill = [STYLE.surface, STYLE.soft, STYLE.line, STYLE.accent][lvl];
    const onAcc = lvl >= 3;
    s.addShape('rect', { x: o.x + G.gap / 2, y: o.y + G.gap / 2,
      w: Math.max(0.05, o.w - G.gap), h: Math.max(0.05, o.h - G.gap),
      fill: { color: fill }, line: { color: STYLE.bg, width: 0.75 } });
    if (o.h >= G.labelMinH) {
      s.addText(o.it.label, { x: o.x + 0.1, y: o.y + 0.06, w: Math.max(0.2, o.w - 0.2), h: 0.3,
        fontFace: STYLE.font, fontSize: sz(10.5), bold: true, color: onAcc ? STYLE.onAccent : STYLE.ink });
      s.addText(String(o.it.v) + (sec.unit || ''), { x: o.x + 0.1, y: o.y + 0.34, w: Math.max(0.2, o.w - 0.2), h: 0.28,
        fontFace: STYLE.font, fontSize: sz(10), color: onAcc ? STYLE.onAccent : STYLE.body });
    }
  });
}
/* 箱线图：分组箱体（min/q1/median/q3/max）+ 须线端帽 */
function infoBoxplot(s, sec, y0, y1) {
  const G = PT.boxplot;
  const P = infoPlot(sec, y0, y1);
  if (P.table) infoTable(s, P.rows, MX, P.table.y, CW, P.table.h);
  const groups = (sec.groups || []).filter(g => g && g.length >= 6).slice(0, G.maxGroups);
  if (!groups.length) return;
  const nums = groups.map(g => g.slice(1, 6).map(Number));
  const lo = Math.min.apply(null, nums.map(n => n[0]));
  const hi = Math.max.apply(null, nums.map(n => n[4]));
  const span = (hi - lo) || 1;
  const plotH = P.y1 - P.y0 - 0.5;
  const yFor = (v) => P.y0 + (1 - (v - lo) / span) * plotH;
  const step = CW / groups.length;
  const bw = Math.min(G.boxMaxW, step * 0.5);
  s.addShape('rect', { x: MX, y: P.y0 + plotH, w: CW, h: 0.015, fill: { color: STYLE.line }, line: { type: 'none' } });
  groups.forEach((g, i) => {
    const mn = Number(g[1]), q1 = Number(g[2]), md = Number(g[3]), q3 = Number(g[4]), mx = Number(g[5]);
    const cx = MX + step * i + step / 2;
    s.addShape('rect', { x: cx - 0.012, y: yFor(mx), w: 0.024, h: Math.max(0.02, yFor(mn) - yFor(mx)),
      fill: { color: STYLE.faint }, line: { type: 'none' } });
    s.addShape('rect', { x: cx - G.whiskerCapW / 2, y: yFor(mx), w: G.whiskerCapW, h: 0.022, fill: { color: STYLE.faint }, line: { type: 'none' } });
    s.addShape('rect', { x: cx - G.whiskerCapW / 2, y: yFor(mn) - 0.022, w: G.whiskerCapW, h: 0.022, fill: { color: STYLE.faint }, line: { type: 'none' } });
    s.addShape('rect', { x: cx - bw / 2, y: yFor(q3), w: bw, h: Math.max(0.05, yFor(q1) - yFor(q3)),
      fill: { color: STYLE.soft }, line: { color: STYLE.accent, width: 1 } });
    s.addShape('rect', { x: cx - bw / 2, y: yFor(md) - 0.015, w: bw, h: 0.03, fill: { color: STYLE.accent }, line: { type: 'none' } });
    s.addText(String(g[0]), { x: cx - step / 2, y: P.y1 - 0.42, w: step, h: 0.3, align: 'center',
      fontFace: STYLE.font, fontSize: sz(10.5), color: STYLE.body });
    s.addText(String(md) + (sec.unit || ''), { x: cx - step / 2, y: yFor(md) - 0.42, w: step, h: 0.26, align: 'center',
      fontFace: STYLE.font, fontSize: sz(10), bold: true, color: STYLE.accent });
    /* min 标签默认在须线帽下方；mn 贴轴时会被组标签带（P.y1-0.42 起）压住 →
       翻到帽上方，同时避开箱体下沿（几何铁律②：禁叠印） */
    let mnY = yFor(mn) + 0.03;
    if (mnY + 0.24 > P.y1 - 0.42) mnY = Math.min(yFor(mn) - 0.28, yFor(q1) - 0.30);
    s.addText(String(mn) + (sec.unit || ''), { x: cx - step / 2, y: mnY, w: step, h: 0.24, align: 'center',
      fontFace: STYLE.font, fontSize: sz(9.5), color: STYLE.faint });
    s.addText(String(mx) + (sec.unit || ''), { x: cx - step / 2, y: yFor(mx) - 0.28, w: step, h: 0.24, align: 'center',
      fontFace: STYLE.font, fontSize: sz(9.5), color: STYLE.faint });
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
  const n = nodes.length;
  const cx = MX + CW / 2, cy = (P.y0 + P.y1) / 2;
  const r = Math.min(CW / 2, (P.y1 - P.y0) / 2) - G.labelMaxW * 0.55;
  const pos = {};
  nodes.forEach((nd, i) => {
    const a = -Math.PI / 2 + i * 2 * Math.PI / n;
    pos[String(nd[0])] = { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
  });
  edges.forEach(e => {
    const a = pos[String(e[0])], b = pos[String(e[1])];
    if (!a || !b) return;
    const dx = b.x - a.x, dy = b.y - a.y;
    const len = Math.sqrt(dx * dx + dy * dy);
    const ang = Math.atan2(dy, dx) * 180 / Math.PI;
    s.addShape('rect', { x: (a.x + b.x) / 2 - len / 2, y: (a.y + b.y) / 2 - 0.008, w: len, h: 0.016,
      rotate: Math.round(ang * 10) / 10, fill: { color: STYLE.line }, line: { type: 'none' } });
  });
  nodes.forEach((nd, i) => {
    const p = pos[String(nd[0])];
    const deg = edges.filter(e => String(e[0]) === String(nd[0]) || String(e[1]) === String(nd[0])).length;
    const rr = Math.max(G.nodeRMin, Math.min(G.nodeR, G.nodeRMin + deg * 0.03));
    s.addShape('ellipse', { x: p.x - rr, y: p.y - rr, w: rr * 2, h: rr * 2,
      fill: { color: deg ? STYLE.accent : STYLE.faint }, line: { color: STYLE.bg, width: 1 } });
    const outward = p.x >= cx;
    s.addText(String(nd[1] != null ? nd[1] : nd[0]),
      { x: outward ? p.x + rr + 0.05 : p.x - rr - 0.05 - G.labelMaxW, y: p.y - 0.14, w: G.labelMaxW, h: 0.28,
        align: outward ? 'left' : 'right', valign: 'middle', fontFace: STYLE.font, fontSize: sz(10), color: STYLE.body });
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
  const palette = [STYLE.accent, STYLE.faint, STYLE.body, STYLE.line];
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
        fontFace: STYLE.font, fontSize: sz(10), bold: true, fit: 'shrink',
        color: k === 0 ? STYLE.onAccent : STYLE.ink });
      cy0 += sh;
    });
    s.addText(String(c[0]), { x: cx0, y: labelY, w: cw, h: 0.28, align: 'center',
      fontFace: STYLE.font, fontSize: sz(10.5), bold: true, color: STYLE.body, fit: 'shrink' });
    cx0 += cw + G.colGap;
  });
  let lx = MX;
  legend.forEach((lg, k) => {
    s.addShape('rect', { x: lx, y: legendY + 0.06, w: 0.12, h: 0.12,
      fill: { color: palette[k % palette.length] }, line: { type: 'none' } });
    s.addText(lg, { x: lx + 0.16, y: legendY, w: 1.5, h: 0.24,
      fontFace: STYLE.font, fontSize: sz(10), color: STYLE.body, valign: 'middle', fit: 'shrink' });
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
  /* Reserve legend INSIDE the plot box — 6 series must not crush the annotation band. */
  const legH = Math.min(1.2, Math.max(0.28, series.length * 0.22 + 0.08));
  const plotBottom = P.y1 - legH;
  const plotH = Math.max(0.6, plotBottom - P.y0);
  const cyMid = P.y0 + plotH / 2;
  const xAt = (i) => MX + (nPts > 1 ? i / (nPts - 1) : 0.5) * CW;
  const yAt = (i) => cyMid - (totals[i] / maxTot) * plotH / 2;
  const palette = [STYLE.accent, STYLE.faint, STYLE.body, STYLE.line, STYLE.soft, STYLE.surface];
  const n = Math.max(24, Math.round(CW / 0.1));
  let base = [];
  for (let i = 0; i < nPts; i++) base.push(yAt(i));
  series.forEach((se, si) => {
    const upper = [];
    for (let i = 0; i < nPts; i++) upper.push(base[i] + (values[si][i] || 0) / maxTot * plotH / 2);
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
    const lx = MX;
    s.addShape('rect', { x: lx, y: plotBottom + 0.04 + si * 0.2, w: 0.12, h: 0.12,
      fill: { color: palette[si % palette.length] }, line: { type: 'none' } });
    s.addText(String(se.name || ('系列' + (si + 1))), { x: lx + 0.16, y: plotBottom + 0.02 + si * 0.2, w: 1.5, h: 0.2,
      fontFace: STYLE.font, fontSize: sz(10), color: STYLE.body, valign: 'middle' });
    base = upper;
  });
  labels.forEach((lb, i) => {
    s.addText(String(lb), { x: xAt(i) - 0.4, y: plotBottom - 0.22, w: 0.8, h: 0.2, align: 'center',
      fontFace: STYLE.font, fontSize: sz(9.5), color: STYLE.faint });
  });
}
/* 表格：行高按可用高度自适应；行数×minRowH 超高时压到 hardFloor 并告警，禁止溢出注释带 */
function addTable(s, tbl, x, y, w, availH, opts) {
  opts = opts || {};
  const rowsIn = tbl.rows || [];
  const head = tbl.head || [];
  const n = rowsIn.length + 1;
  const maxRowH = opts.maxRowH != null ? opts.maxRowH : PT.table.rowH;
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
  const headSz = sz(dense ? 11 : Math.min(13, AT_TABLE.headMax || 12));
  const bodySz = sz(dense ? 10 : Math.min(12.5, AT_TABLE.cellMax || 13));
  const hRowH = Math.min(headRowH, Math.max(hardFloor, rowH * 1.15));
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
  const rows = [head.map(h => ({ text: h, options: { bold: true, color: STYLE.onAccent,
      fill: { color: STYLE.accent }, fontSize: headSzF, fontFace: STYLE.font, valign: 'middle' } }))]
    .concat(rowsIn.map(r => r.map(c => ({ text: String(c), options: { fontSize: bodySzF,
      color: STYLE.body, fontFace: STYLE.font, valign: 'middle', fill: { color: STYLE.bg } } }))));
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
  s.addShape('rect', { x: 0, y: 0, w: PW, h: PH, fill: { color: STYLE.accent }, line: { type: 'none' } });
  s.addText(CONTENT.meta || '', { x: MX, y: C.metaY, w: CW, h: 0.4, fontFace: STYLE.font,
    fontSize: sz(12), color: STYLE.soft });
  const tSize = estTextH(CONTENT.title, CW - 1, sz(44), 1.25) > C.titleH ? sz(36) : sz(44);
  s.addText(CONTENT.title, { x: MX, y: C.titleY, w: CW - 1, h: C.titleH, fontFace: STYLE.fontDisplay,
    fontSize: tSize, bold: true, color: STYLE.onAccent });
  s.addText(CONTENT.subtitle || '', { x: MX, y: C.subtitleY, w: CW - 1, h: C.subtitleH,
    fontFace: STYLE.font, fontSize: sz(18), color: STYLE.soft });
  s.addNotes([CONTENT.subtitle, CONTENT.meta].filter(Boolean).join('\n'));
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
    head(s, 'AGENDA', '报告大纲' + sub);
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
    if (notes.length) s.addNotes(notes.join('\n'));
  });
})();

/* 章节页 · 按页型分发 */
CONTENT.sections.forEach((sec) => {
  const type = sec.type || 'points';
  // Batch 2: honor layoutPreset (scaffold/recommend_layout → PPTX IR alignment)
  if (!sec.layoutPreset) {
    const _p2p = (LC.layoutSystem && LC.layoutSystem.pageToPreset) || {};
    if (_p2p[type]) sec.layoutPreset = _p2p[type];
  }
  const s = base();
  if (type !== 'quote') head(s, sec.eyebrow, sec.title, sec.lead);

  /* 正文区起点 / 终点（含 lead 与 so-what / 来源行 / 待核实条占位） */
  /* 非 exhibit 页型也可带 Exhibit 编号（帧头徽标；正文区下移让位，避免与主图重叠） */
  const exBadge = (type !== 'exhibit' && sec.exhibitNo) ? exhibitBadge(sec.exhibitNo) : null;
  const bodyY0 = sec.lead ? PT.common.bodyYWithLead : CONTENT_TOP;
  const bodyY = exBadge ? bodyY0 + 0.42 : bodyY0;
  if (exBadge) {
    s.addText(exBadge, { x: MX, y: CONTENT_TOP - 0.06, w: CW, h: 0.3, fontFace: STYLE.font,
      fontSize: sz(11.5), bold: true, color: STYLE.accent, charSpacing: 2 });
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

  if (type === 'metrics') {
    const M = PT.metrics;
    const reg = REGIONS.regionOf('metrics', 'primary') ||
      { x: MX, y: M.bandY, w: CW, h: M.cardH };
    const ms = (sec.metrics || []).map(metricKV);
    const n = Math.max(1, ms.length);
    const g = cols(reg.w, n, M.gap);
    const mw = Math.min(M.maxW, g.w);
    const gx = reg.x + (reg.w - n * mw - (n - 1) * M.gap) / 2;
    const cardH = Math.min(reg.h, CONTENT_BOTTOM - reg.y);
    ms.forEach((m, i) => {
      const x = gx + i * (mw + M.gap);
      s.addShape('roundRect', { x, y: reg.y, w: mw, h: cardH, rectRadius: 0.09,
        fill: { color: STYLE.surface }, line: { color: STYLE.line, width: 0.75 } });
      const vSize = estTextH(m[0], mw - 0.2, sz(40), 1.1) > cardH * 0.5 ? sz(30) : sz(40);
      s.addText(m[0], { x, y: M.valY, w: mw, h: M.valH, align: 'center', fontFace: STYLE.fontDisplay,
        fontSize: vSize, bold: true, color: STYLE.accent });
      s.addText(m[1], { x: x + 0.15, y: M.capY, w: mw - 0.3, h: M.capH, align: 'center',
        fontFace: STYLE.font, fontSize: sz(11.5), color: STYLE.body });
    });
  } else if (type === 'kpi') {
    const K = PT.kpi;
    const hreg = REGIONS.regionOf('kpi', 'hero') ||
      { x: MX, y: K.heroY, w: CW * K.heroW, h: K.heroH };
    const hro = sec.hero || [];
    s.addText(String(hro[0] || ''), { x: hreg.x, y: hreg.y, w: hreg.w, h: hreg.h,
      fontFace: STYLE.fontDisplay, fontSize: sz(64), bold: true, color: STYLE.accent });
    s.addText(String(hro[1] || ''), { x: hreg.x + 0.05, y: hreg.y + 1.5, w: hreg.w - 0.4, h: 0.55,
      fontFace: STYLE.font, fontSize: sz(15), bold: true, color: STYLE.ink });
    if (hro[2]) s.addText('▲ ' + hro[2], { x: hreg.x + 0.05, y: hreg.y + 2.1, w: hreg.w - 0.4, h: 0.4,
      fontFace: STYLE.font, fontSize: sz(12), bold: true, color: STYLE.accent });
    const kdivX = MX + CW * K.dividerX;
    /* R6：竖分隔线高度取原设计值与注释带感知下界的较小者——写死 3.1 会在
       so-what/来源行并存时越过注释带顶（ANNOTATION_BAND_OVERLAP），而无注释时
       不得比原设计更长（回归：smoke business-blue fixture slide 7）。 */
    const kpiBottom = chartBottom(!!sec.soWhat, !!(sec.footnote || sec.note)) - 0.05;
    s.addShape('rect', { x: kdivX, y: K.heroY + 0.15, w: 0.025,
      h: Math.min(3.1, Math.max(0.6, kpiBottom - (K.heroY + 0.15))),
      fill: { color: STYLE.line }, line: { type: 'none' } });
    /* 右列：支撑指标行在上、要点在下，共用注释带感知高度；禁越过注释带顶 */
    const mreg = REGIONS.regionOf('kpi', 'metrics') ||
      { x: kdivX + 0.35, y: K.metricY0, w: CW * (1 - K.dividerX) - 0.5, h: CONTENT_BOTTOM - K.metricY0 };
    const kAvail = Math.max(0.8, kpiBottom - mreg.y);
    const kmets = sec.metrics || [];
    /* 容量按最小允许行高判断，行高按全部指标自适应压缩 ——
       原 kCap 用默认行高先截断，导致第 N+1 个指标被静默丢弃（禁静默丢数据） */
    const K_MINROWH = 0.42;
    const kCap = Math.max(1, Math.floor(kAvail / K_MINROWH));
    const kRows = Math.min(kmets.length, kCap);
    if (kRows < kmets.length)
      console.warn(`[build_pptx] 警告：KPI 页「${sec.title || ''}」支撑指标 ${kmets.length} 个超出容量（${kAvail.toFixed(2)}in），` +
        `仅渲染前 ${kRows} 个 —— 建议拆页`);
    const kRowH = fitRowH(kAvail, kRows, K.metricRowH, K_MINROWH);
    kmets.slice(0, kRows).map(metricKV).forEach((m, i) => {
      const ky = mreg.y + i * kRowH;
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
    const kpCap = Math.max(0, Math.floor((kpiBottom - kpY0) / kpRowH));
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
    /* R2：verdict 与 soWhat 共用 annotation 槽位——只画一个（verdict 优先，语义更具体）。
       两者同页必须互斥，否则结论条整条叠印。 */
    if (sec.verdict) {
      const vreg = REGIONS.regionOf('exhibit', 'annotation') ||
        { x: MX, y: PT.exhibit.soWhatY, w: CW, h: 0.62 };
      s.addShape('rect', { x: vreg.x, y: vreg.y, w: vreg.w, h: vreg.h,
        fill: { color: STYLE.accent }, line: { type: 'none' }, objectName: trName('soWhat') });
      s.addText([
        { text: '结论　', options: { fontSize: sz(11), bold: true, color: STYLE.onAccent, charSpacing: 1.5 } },
        { text: sec.verdict, options: { fontSize: sz(12.5), bold: true, color: STYLE.onAccent } },
      ], { x: vreg.x + 0.22, y: vreg.y + 0.06, w: vreg.w - 0.44, h: vreg.h - 0.12, fontFace: STYLE.font,
        valign: 'middle', objectName: trName('soWhat') });
    }
  } else if (type === 'quote') {
    const Q = PT.quote;
    const qreg = REGIONS.regionOf('quote', 'primary') ||
      { x: MX + 1.05, y: Q.textY, w: CW - 2.1, h: Q.textH };
    /* 金句页用主题一致强调带（accent-soft 底）——浅色主题下不再出现深色页 */
    s.addShape('rect', { x: 0, y: 0, w: PW, h: PH, fill: { color: STYLE.soft }, line: { type: 'none' } });
    if (sec.eyebrow) s.addText(sec.eyebrow, { x: MX, y: PT.common.headEyebrowY, w: CW, h: 0.4,
      fontFace: STYLE.font, fontSize: sz(13), bold: true, color: STYLE.accent, charSpacing: 2 });
    s.addText(sec.title, { x: MX, y: PT.common.headTitleY, w: CW, h: 1.0,
      fontFace: STYLE.fontDisplay, fontSize: sz(30), bold: true, color: STYLE.ink });
    s.addShape('rect', { x: MX, y: PT.common.headRuleY, w: 0.9, h: 0.045, fill: { color: STYLE.accent }, line: { type: 'none' } });
    s.addText('「', { x: MX + 0.05, y: Q.markY, w: 1.2, h: 1.1,
      fontFace: STYLE.fontDisplay, fontSize: sz(60), bold: true, color: STYLE.accent });
    const qSize = estTextH(sec.quote, qreg.w, sz(20), 1.4) > qreg.h ? sz(16) : sz(20);
    s.addText(sec.quote, { x: qreg.x, y: qreg.y, w: qreg.w, h: qreg.h,
      fontFace: STYLE.fontDisplay, fontSize: qSize, bold: true, color: STYLE.ink, valign: 'middle' });
    s.addText('—— ' + sec.author, { x: qreg.x, y: Q.authorY, w: qreg.w, h: 0.45, align: 'right',
      fontFace: STYLE.font, fontSize: sz(13), bold: true, color: STYLE.accent });
    if (sec.context) s.addText(sec.context, { x: qreg.x, y: Q.contextY, w: qreg.w, h: 0.4, align: 'right',
      fontFace: STYLE.font, fontSize: sz(11), color: STYLE.faint });
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
      const usedR = nativeDonutChart(s, dcn, dcols, bodyBottom) || d.r;
      const holeR = d.holeR * (usedR / d.r);
      const hb = holeR * 2;
      let total = 0; dcn.values.forEach(v => { total += Math.max(0, v); });
      const totalStr = (Math.round(total * 10) / 10) + (dcn.unit || '');
      s.addText(totalStr, { x: d.centerX - holeR, y: d.centerY - 0.42, w: hb, h: 0.5, align: 'center',
        fontFace: STYLE.fontDisplay, fontSize: sz(20), bold: true, color: STYLE.ink, valign: 'middle' });
      s.addText(dcn.centerLabel || '合计', { x: d.centerX - holeR, y: d.centerY + 0.08, w: hb, h: 0.35, align: 'center',
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
      } else {
        legRowH = Math.min(d.legendRowH, maxLegH / n, 3.4 / n);
        legY0 = Math.min(d.centerY - (n * legRowH) / 2 + 0.1, bodyBottom - n * legRowH - 0.04);
      }
      const sum2 = total || 1;
      dcn.labels.forEach((lb, i) => {
        const v = dcn.values[i] || 0;
        const y = legY0 + i * legRowH;
        s.addShape('ellipse', { x: d.legendX, y: y + 0.08, w: 0.16, h: 0.16,
          fill: { color: dcols[i % dcols.length] }, line: { type: 'none' } });
        s.addText(lb, { x: d.legendX + 0.3, y, w: d.legendLabelW, h: legRowH, valign: 'middle',
          fontFace: STYLE.font, fontSize: sz(12), bold: true, color: STYLE.ink });
        s.addText(String(v) + (dcn.unit || ''), { x: d.legendX + 3.8, y, w: d.legendValW, h: legRowH, align: 'right',
          valign: 'middle', fontFace: STYLE.font, fontSize: sz(12), bold: true, color: STYLE.body });
        s.addText((Math.round(v / sum2 * 1000) / 10) + '%', { x: d.legendPctX, y, w: d.legendPctW, h: legRowH,
          align: 'right', valign: 'middle', fontFace: STYLE.font, fontSize: sz(10.5), color: STYLE.faint });
      });
      const dpY0 = legY0 + n * legRowH + 0.1;
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
    const hreg = REGIONS.regionOf('heatmap', 'primary', { bottom: bodyBottom }) ||
      { x: MX, y: H.y, w: CW, h: bodyBottom - H.y };
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
    const levels = [STYLE.surface, STYLE.soft, STYLE.line, STYLE.accent];
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
        fill: { color: hit ? STYLE.accent : STYLE.faint }, line: { type: 'none' } });
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
    const rowH = fitRowH(availH - (n - 1) * P.gap, n, P.rowH, 0.26);
    lv.forEach((l, i) => {
      const frac = P.minW + (1 - P.minW) * (n === 1 ? 1 : i / (n - 1));
      const w = preg.w * frac;
      const x = preg.x + (preg.w - w) / 2;
      const y = preg.y + i * (rowH + P.gap);
      const acc = isRec(l) && l.accent;
      const lt = isRec(l) ? (l.t || '') : String(l[0] || '');
      const ld = isRec(l) ? (l.d || '') : String(l[1] || '');
      s.addShape('roundRect', { x, y, w, h: rowH, rectRadius: 0.07,
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
    const rowH = fitRowH(availH - (rowsN - 1) * 0.3, rowsN, sreg.h || S2.barH, 0.3);
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
        s.addShape('roundRect', { x, y: cy, w: g.w, h: rowH, rectRadius: 0.07,
          fill: { color: acc ? STYLE.soft : STYLE.surface },
          line: acc ? { type: 'none' } : { color: STYLE.line, width: 0.75 } });
        const pd = S2.pad, numH = S2.numH, ttlH = S2.titleH;
        s.addText(String(i + 1).padStart(2, '0'), { x: x + 0.14, y: cy + pd, w: g.w - 0.28, h: numH,
          fontFace: STYLE.font, fontSize: sz(10), bold: true, color: STYLE.accent });
        s.addText(t, { x: x + 0.14, y: cy + pd + numH, w: g.w - 0.28, h: ttlH,
          fontFace: STYLE.font, fontSize: sz(13), bold: true, color: acc ? STYLE.accent : STYLE.ink });
        if (d) s.addText(d, { x: x + 0.14, y: cy + pd + numH + ttlH, w: g.w - 0.28,
          h: Math.max(0.2, rowH - pd * 2 - numH - ttlH),
          fontFace: STYLE.font, fontSize: sz(10), color: STYLE.faint });
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
    addTable(s, sec.table, treg.x, treg.y, treg.w, treg.h);
  } else if (type === 'timeline') {
    const T = PT.timeline;
    const treg = REGIONS.regionOf('timeline', 'primary') ||
      { x: MX, y: T.labelY, w: CW, h: T.descY + T.descH - T.labelY };
    const ps = (sec.phases || []).map(phaseKV);
    const n = Math.max(1, ps.length);
    const stepW = (treg.w - 1.0) / n;
    s.addShape('line', { x: treg.x + 0.2, y: T.axisY, w: treg.w - 0.4, h: 0.02, line: { color: STYLE.line, width: 1.5 } });
    ps.forEach((p, i) => {
      const x = treg.x + 0.2 + i * stepW;
      const on = p[3] === 'done' || p[3] === 'now';
      // 变体 timeline：节点图标（icon:<name>）；无图标回落圆点
      const wantIcon = (sec.variant === 'timeline') && p[4];
      if (wantIcon) {
        addIcon(s, p[4], x - 0.13, T.dotY - 0.06, 0.26, on ? STYLE.accent : STYLE.body);
      } else {
        s.addShape('ellipse', { x: x - T.dotR / 2, y: T.dotY, w: T.dotR, h: T.dotR,
          fill: { color: on ? STYLE.accent : STYLE.line }, line: { type: 'none' } });
      }
      s.addText(p[0], { x: x - 0.1, y: T.labelY, w: stepW - 0.2, h: 0.4, fontFace: STYLE.font,
        fontSize: sz(12), bold: true, color: STYLE.accent, charSpacing: 1 });
      s.addText(p[1], { x: x - 0.1, y: T.nameY, w: stepW - 0.2, h: 0.5, fontFace: STYLE.fontDisplay,
        fontSize: sz(17), bold: true, color: p[3] === 'now' ? STYLE.accent : STYLE.ink });
      s.addText(p[2] || '', { x: x - 0.1, y: T.descY, w: stepW - 0.25, h: T.descH, fontFace: STYLE.font,
        fontSize: sz(12), color: STYLE.body, lineSpacing: sz(18) });
    });
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
    const fz = fitFont(items.length ? items : ['x'.repeat(longest)], g.w, availH, { max: 13.5, gapFactor: 1.2 });
    groups.forEach((col, ci) => {
      if (!col.length) return;
      const colX = treg.x + ci * g.step;
      // 变体 2-col-feature：首栏特性栏（accent 左线 + 标题放大一档）
      const isFeature = (sec.variant === '2-col-feature') && ci === 0 && nCol === 2;
      const fx = isFeature ? colX + 0.14 : colX;
      const fw = isFeature ? g.w - 0.14 : g.w;
      if (isFeature) {
        // 特性栏 accent 左线：高度按首段实际文本估算（不用整栏 availH，避免无墨水区压进注释带触发 severe 门禁）
        const p0 = col[0] || ['', ''];
        const barH = Math.min(availH,
          estTextH(p0[0] + '　', fw, sz(fz + 1), 1.5) +
          estTextH(p0[1] || '', fw, sz(fz - 1), 1.5) + sz(7) / 72 + 0.06);
        s.addShape('rect', { x: colX, y: treg.y, w: 0.045, h: Math.max(0.2, barH),
          fill: { color: STYLE.accent }, line: { type: 'none' }, objectName: 'feature:bar' });
      }
      const runs = col.map(p => ([
        { text: p[0] + '　', options: { fontSize: sz(isFeature ? fz + 1 : fz), bold: true, color: STYLE.ink } },
        { text: p[1] + '\n', options: { fontSize: sz(fz - 1), color: STYLE.body, breakLine: true } },
      ])).flat();
      s.addText(runs, { x: fx, y: treg.y, w: fw, h: availH, fontFace: STYLE.font,
        valign: 'top', lineSpacing: sz(fz * 1.5), paraSpaceBefore: sz(7) });
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
      chartBlock(s, ecH, rxH, yH, rwH, Math.max(1.2, bodyBottom - yH), (ecH.colors || dataColors(styleArg)));
    }
  } else if (type === 'matrix') {
    const rhH = sec.rowHeads || [], chH = sec.colHeads || [];
    const mY = PT.research.matrixY, mLW = PT.research.matrixLabelW;
    const rowsC = sec.cells || [];
    const nR = Math.max(1, rowsC.length);
    const availH = bodyBottom - mY - 0.42;
    const mCH = fitRowH(availH, nR, PT.research.matrixCellH, 0.3);
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
          fill: { color: acc ? STYLE.soft : STYLE.surface },
          line: acc ? { type: 'none' } : { color: STYLE.line, width: 0.75 } });
        s.addText(txt, { x: cx + 0.14, y: y2 + 0.08, w: mW - 0.28, h: mCH - 0.26,
          fontFace: STYLE.font, fontSize: sz(11), valign: 'middle',
          color: acc ? STYLE.accent : STYLE.body });
      });
    });
  } else if (type === 'lane') {
    const lnS = sec.lanes || [];
    const n = Math.max(1, lnS.length);
    const start = sec.lead ? PT.common.bodyYWithLead : PT.arch.fullStartY;
    const availH = bodyBottom - start;
    const lnH = fitRowH(availH - (n - 1) * PT.arch.laneGap, n, PT.arch.laneH, 0.3);
    const lnGap = PT.arch.laneGap, lnHW = PT.arch.laneHeadW;
    lnS.forEach((ln, li) => {
      const y3 = start + li * (lnH + lnGap);
      s.addShape('roundRect', { x: MX, y: y3, w: CW, h: lnH, rectRadius: 0.07,
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
        s.addShape('roundRect', { x: sx, y: y3 + 0.13, w: stepW, h: lnH - 0.26, rectRadius: 0.06,
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
    const creg = REGIONS.regionOf('cards', 'primary', { bottom: bodyBottom }) ||
      { x: MX, y: cdC.startY, w: CW, h: bodyBottom - cdC.startY };
    const cds = (sec.cards || []).map(cd =>
      /* 与 r_cards 同口径：{title,points,icon} 字典 | [标题, 描述] 数组 | 纯字符串标题 */
      isRec(cd) ? cd
        : (Array.isArray(cd)
          ? { title: cd[0] || '', points: cd.length > 1 ? [['', cd[1]]] : [] }
          : { title: String(cd == null ? '' : cd), points: [] }));
    const isBento = (sec.variant === 'bento-grid') && cds.length >= 3;
    const c = isBento ? 3 : Math.min(sec.columns || 3, cds.length || 1);
    // bento-grid：首卡占 2 个槽位（跨 2 列），其余顺排；槽位数 = 卡数 + 1
    const r = isBento ? Math.ceil((cds.length + 1) / c) : Math.ceil((cds.length || 1) / c);
    const gw = (creg.w - (c - 1) * cdC.gap) / c;
    const gh = fitRowH(creg.h - (r - 1) * cdC.gap, r, cdC.maxH, 0.6);
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
    const ptsFzB = cds.length ? Math.min(...cds.map(cd =>
      fitFont((cd.points || []).map(cardPtText), gw - 0.36, ptsBoxH,
        { max: 12, lineFactor: 1.5, gapFactor: 0 }))) : 12;
    const ptsFz = sz(ptsFzB);
    cds.forEach((cd, i) => {
      let col = i % c, row = Math.floor(i / c), span = 1;
      if (isBento) {
        // 首卡跨 2 列：槽位 = i===0 ? [0,1] : i+1
        const slot = i === 0 ? 0 : i + 1;
        if (i === 0) span = 2;
        col = slot % c; row = Math.floor(slot / c);
      }
      const cw = span * gw + (span - 1) * cdC.gap;
      const x = creg.x + col * (gw + cdC.gap), y = creg.y + row * (gh + cdC.gap);
      s.addShape('roundRect', { x, y, w: cw, h: gh, rectRadius: 0.08,
        fill: { color: STYLE.surface }, line: { color: STYLE.line, width: 0.75 } });
      /* 卡片头路标：真导出语义图标（SVG→PNG），与 HTML .card__ico 同源；无资产时回落 accent 方块 */
      const ico = 0.18;
      const icoName = cd.icon || ICON_LIB.pickIconName(cd.title || '', i);
      addIcon(s, icoName, x + 0.18, y + 0.2, ico, STYLE.accent);
      s.addText(cd.title || '', { x: x + 0.18 + ico + 0.1, y: y + 0.14, w: cw - 0.36 - ico - 0.1, h: cdC.titleH, fontFace: STYLE.font,
        fontSize: sz(15), bold: true, color: STYLE.ink, fit: 'shrink' });
      /* points 兼容：[[k,v]…] | [str…] | [{t,d}…]（scaffold v9 契约 {title, points:[[k,v]]}） */
      const ptLines = (cd.points || []).map(cardPtText);
      s.addText(ptLines.map(t => ({ text: t + '\n',
          options: { fontSize: ptsFz, color: STYLE.body, fontFace: STYLE.font, breakLine: true } })),
        { x: x + 0.18, y: y + 0.14 + cdC.titleH + 0.06, w: cw - 0.36, h: ptsBoxH,
          fontFace: STYLE.font, valign: 'top', lineSpacing: ptsFz * 1.5 });
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
      const fzB = fitFont(pts.map(p => (p[0] || '') + (p[1] || '')), w - 0.4, availP, { max: 14, gapFactor: 0.6 });
      const fz = sz(fzB), fzSm = sz(snapFont(fzB - 1));
      pts.forEach((pt, i) => {
        const ly = ly0 + i * rowH;
        s.addShape('rect', { x, y: ly + rowH / 2 - 0.06, w: 0.12, h: 0.12, fill: { color: STYLE.accent }, line: { type: 'none' } });
        s.addText([
          { text: pt[0] + '　', options: { fontSize: fz, bold: true, color: STYLE.ink } },
          { text: pt[1], options: { fontSize: fzSm, color: STYLE.body } },
        ], { x: x + 0.28, y: ly, w: w - 0.4, h: rowH - 0.04, fontFace: STYLE.font, valign: 'top' });
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
      chartBlock(s, lc, lreg.x, SP.chartY, lw, Math.max(1.4, bodyBottom - SP.chartY - (lc.cap ? 0.1 : 0)),
        lc.colors || dataColors(styleArg));
      if (lc.cap) s.addText(lc.cap, { x: lreg.x, y: SP.capY, w: lw, h: 0.35, align: 'center',
        fontFace: STYLE.font, fontSize: sz(12), color: STYLE.body });
    } else {
      drawPoints(sec.left, lreg.x, lw);
    }
    const rt = (sec.right && sec.right.type) || 'bar';
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
      chartBlock(s, bc, rx, SP.chartY, rw, Math.max(1.4, bodyBottom - SP.chartY - (bc.cap ? 0.1 : 0)), dcols);
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
    const dEnd = dreg.y + dreg.h;
    const n = Math.max(1, lys.length);
    const lh = Math.max(0.5, Math.min(dreg.maxLayerH || D.maxLayerH, (dEnd - dStart) / n - D.layerGap));
    lys.forEach((lay, li) => {
      const y = dStart + li * (lh + D.layerGap);
      const focus = lay[2] === 'focus';
      s.addShape('roundRect', { x: dreg.x, y, w: D.layerBarW, h: lh, rectRadius: 0.05,
        fill: { color: focus ? STYLE.accent : STYLE.surface }, line: focus ? { type: 'none' } : { color: STYLE.line, width: 0.75 } });
      s.addText(lay[0], { x: dreg.x + 0.1, y: y + 0.1, w: D.layerBarW - 0.2, h: lh - 0.2, align: 'center', valign: 'middle',
        fontFace: STYLE.font, fontSize: sz(12), bold: true, color: focus ? STYLE.onAccent : STYLE.body });
      const nodes = lay[1] || [];
      const nn = Math.max(1, nodes.length);
      const availW = CW - D.layerBarW - 0.2;
      const nw = Math.min(D.nodeMaxW, (availW - (nn - 1) * D.nodeGap) / nn);
      nodes.forEach((nd, ni) => {
        const x = MX + D.layerBarW + 0.2 + ni * (nw + D.nodeGap);
        /* 节点三形态：{t,d,accent} 字典 | [标题, 注解] 数组 | 纯字符串
           （scaffold_report 发射数组形态；不归一化则 addText 收数组直接抛 TypeError） */
        const _nd = Array.isArray(nd) ? { t: nd[0], d: nd[1] } : nd;
        const acc = isRec(_nd) && _nd.accent;
        const ntt = String(isRec(_nd) ? (_nd.t || '') : (_nd == null ? '' : _nd));
        const nds = String(isRec(_nd) ? (_nd.d || '') : '');
        s.addShape('roundRect', { x, y, w: nw, h: lh, rectRadius: 0.06,
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
    if (sec.legend) {
      /* R2：图例进图区底部（与 HTML .arch__legend 同源），禁用 PH-0.62 固定偏移——
         那会压到来源行(6.72)与页码(7.0)。图例条自适应行内均分，右对齐。 */
      const lgH = 0.28;
      const lgY = Math.max(dStart, bodyBottom - lgH - 0.02);
      const nLg = Math.max(1, sec.legend.length);
      const step = Math.min(2.4, CW / nLg);
      sec.legend.forEach((lg, li) => {
        s.addText('● ' + lg, { x: MX + CW - nLg * step + li * step, y: lgY, w: step - 0.05, h: lgH,
          fontFace: STYLE.font, fontSize: sz(10), color: STYLE.faint, align: 'left' });
      });
    }
  } else if (type === 'exhibit') {
    const ec = sec.chart || {};
    /* 主图区走布局 IR（layout_slots.json 的 primary 槽位），未命中时回落 PT.exhibit */
    const reg = REGIONS.regionOf('exhibit', 'primary', { withNote: !!(sec.soWhat || sec.footnote) })
      || { x: MX, y: PT.exhibit.chartY, w: CW, h: PT.exhibit.chartH };
    if (sec.exhibitNo) {
      s.addText(exhibitBadge(sec.exhibitNo), { x: MX, y: PT.exhibit.badgeY, w: CW, h: 0.35,
        fontFace: STYLE.font, fontSize: sz(11.5), bold: true, color: STYLE.accent, charSpacing: 2 });
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
    const mw = hasMetrics ? Math.min(P.metricW, Math.max(1.6, (CW - 4.8) / nM)) : 0;
    const textW = hasMetrics
      ? Math.max(4.2, (PW - MX - nM * mw) - MX - 0.35)
      : CW - 0.4;
    const avail = bodyBottom - bodyY;
    const rowH = fitRowH(avail, pts.length, P.rowH, 0.3);
    /* 长列表收紧（adaptiveText.list 单源）：条目多时降字号上限/段间距/行距，仍装不下由 fitFont 阶梯下探 */
    const _lo = listFitOpts(pts.length);
    const fzB = fitFont(pts.map(p => (p[0] || '') + (p[1] || '')), textW - 0.32, avail,
      { max: Math.min(15, _lo.max), gapFactor: _lo.gapFactor, lineFactor: _lo.lineFactor });
    const fz = sz(fzB), fzSm = sz(snapFont(fzB - 1));
    pts.forEach((p, i) => {
      const y = bodyY + i * rowH;
      s.addShape('rect', { x: MX, y: y + rowH / 2 - P.markSize / 2, w: P.markSize, h: P.markSize,
        fill: { color: STYLE.accent }, line: { type: 'none' } });
      s.addText([
        { text: p[0] + '　', options: { fontSize: fz, bold: true, color: STYLE.ink } },
        { text: p[1], options: { fontSize: fzSm, color: STYLE.body } },
      ], { x: MX + 0.32, y, w: textW, h: rowH - 0.04, fontFace: STYLE.font, valign: 'top' });
    });
    if (hasMetrics) {
      const gx = PW - MX - nM * mw;
      const vSize = nM >= 3 ? sz(28) : sz(34);
      sec.metrics.slice(0, nM).map(metricKV).forEach((m, i) => {
        const x = gx + i * mw;
        s.addText(m[0], { x, y: P.metricY, w: mw - 0.2, h: P.metricValH, fontFace: STYLE.fontDisplay,
          fontSize: vSize, bold: true, color: STYLE.accent });
        s.addText(m[1], { x, y: P.metricCapY, w: mw - 0.2, h: 0.9, fontFace: STYLE.font, fontSize: sz(11), color: STYLE.faint });
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
  if (_notes.length) s.addNotes(_notes.join('\n'));
});

/* 收尾 */
(function closing() {
  const s = base();
  const C = PT.closing;
  /* 收尾页用主题一致强调带（accent-soft 底 + 常规文字）——浅色主题下不再出现深色收尾页 */
  s.addShape('rect', { x: 0, y: 0, w: PW, h: PH, fill: { color: STYLE.soft }, line: { type: 'none' } });
  s.addShape('rect', { x: MX, y: C.eyebrowY, w: 0.9, h: 0.045, fill: { color: STYLE.accent }, line: { type: 'none' } });
  s.addText('下一步', { x: MX, y: C.eyebrowY + 0.16, w: CW, h: 0.4, fontFace: STYLE.font,
    fontSize: sz(13), bold: true, color: STYLE.accent, charSpacing: 2 });
  s.addText(CONTENT.closing.title, { x: MX, y: C.titleY, w: CW - 1, h: C.titleH, fontFace: STYLE.fontDisplay,
    fontSize: sz(30), bold: true, color: STYLE.ink });
  const pts = CONTENT.closing.points || [];
  const n = Math.max(1, pts.length);
  const cw3 = (CW - (n - 1) * 0.3) / n;
  pts.forEach((p, i) => {
    const x = MX + i * (cw3 + 0.3);
    s.addShape('roundRect', { x, y: C.pointsY - 0.2, w: cw3, h: C.pointTitleH + C.pointBodyH + 0.32,
      rectRadius: 0.09, fill: { color: STYLE.surface }, line: { color: STYLE.line, width: 0.75 } });
    s.addText(p[0], { x: x + 0.18, y: C.pointsY, w: cw3 - 0.36, h: C.pointTitleH, fontFace: STYLE.font,
      fontSize: sz(17), bold: true, color: STYLE.accent });
    s.addText(p[1], { x: x + 0.18, y: C.pointsY + C.pointTitleH, w: cw3 - 0.36, h: C.pointBodyH, fontFace: STYLE.font,
      fontSize: sz(12.5), color: STYLE.body });
  });
  s.addNotes((CONTENT.closing.points || []).map(p => '· ' + p[0] + '：' + p[1]).join('\n'));
})();

/* 页码 */
pptx._slides.forEach((s, i) => footer(s, i + 1, pptx._slides.length));

const out = process.argv.slice(2).find(a => !a.startsWith('--')) || 'TopPPT HTML 报告.pptx';
pptx.writeFile({ fileName: out }).then(() => {
  console.log('已生成: ' + out + '  (风格: ' + (STYLE_PRESETS[styleArg] ? styleArg : 'business-blue') +
    ' · 主题: ' + (THEME === 'dark' ? '深色 dark' : '浅色 light') + ' · 模式: ' + MODE_NAME + ')');
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
