/* TopPPT HTML · A 通道（预览序列化引擎）PPTX 产物生成器（回归内部质量路径）：
 * Node 加载浏览器预览运行时（assets/pptx-export.js，仅供页面 WYSIWYG 预览），
 * 用其 slidesOf/slideXml 序列化输出组装完整 PPTX 包（content types / presentation /
 * master / layout / theme / slides + store-only ZIP）。
 *
 * 为什么在这里组装：页面不再提供 PPTX 导出（仅预览 + 提示词），打包骨架从
 * 浏览器运行时移驻本脚本；A 通道产物仅供 regression.py / cross_verify.py 做
 * 「预览即交付」双裁判（strict + python-pptx + 与 B 通道逐页文本交叉一致）。
 * 用法：NODE_PATH=<pptxgenjs 所在 node_modules 可不需要> node scripts/gen_channel_a.js
 *       node scripts/gen_channel_a.js --model=<x.model.json> [--out=<dir>]   # 单模型（回归探针用）
 */
const fs = require('fs');
const path = require('path');
const TopPptHtml = require('../assets/pptx-export.js');
const EX = path.join(__dirname, '..', 'assets', 'examples');
const OUT = path.join(__dirname, '..', 'dist', 'regression-a');

/* ── 常量（与运行时注入块同值；仅打包用，页面几何以运行时为准） ── */
const PW = 13.333, PH = 7.5;
const EMU = 914400;
const E = (v) => Math.round(v * EMU);
const { NS, RT, esc, solid, PRESETS, PRESETS_DARK } = TopPptHtml;
const relsXml = TopPptHtml.relsXml;
const slideXml = TopPptHtml.slideXml;
const slidesOf = TopPptHtml.slidesOf;
const dataColors = TopPptHtml.dataColors;   /* 编码色板（单源 styleDataColors，裸 hex） */

/* ── 完整 PPTX 包组装（原浏览器 buildPptx 骨架，一字未改语义） ── */
function buildPptx(model) {
  /* theme="dark" 用 PRESETS_DARK（与 B 通道 build_pptx.js 同规则，保证双裁判一致） */
  const T = (model.theme === 'dark' && PRESETS_DARK && Object.keys(PRESETS_DARK).length)
    ? PRESETS_DARK : PRESETS;
  const S = T[model.style] || PRESETS['business-blue'];
  const slides = slidesOf(model, S);
  const files = {};
  /* 主题 accent2–accent5 取自该风格自己的编码色板 c2–c5（单源 styleDataColors，
     与 B 通道 dataColors() 同源）——不再硬编码某一套风格的数据色。 */
  const dc = (typeof dataColors === 'function')
    ? (dataColors(model.style, model.theme === 'dark' ? 'dark' : 'light') || []) : [];
  const A2 = dc[1] || S.faint, A3 = dc[2] || S.line, A4 = dc[3] || S.soft, A5 = dc[4] || S.body;

  const slideOverrides = slides.map((_, i) =>
    '<Override PartName="/ppt/slides/slide' + (i + 1) + '.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>').join('');
  files['[Content_Types].xml'] =
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' +
    '<Default Extension="xml" ContentType="application/xml"/>' +
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' +
    '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>' +
    '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>' +
    '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>' +
    '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>' +
    '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>' +
    '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>' +
    slideOverrides + '</Types>';

  files['_rels/.rels'] = relsXml([
    ['rId1', RT + 'officeDocument', 'ppt/presentation.xml'],
    ['rId2', 'http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties', 'docProps/core.xml'],
    ['rId3', RT + 'extended-properties', 'docProps/app.xml']
  ]);
  files['docProps/core.xml'] =
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" ' +
    'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" ' +
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">' +
    '<dc:title>' + esc(model.title || 'TopPPT HTML 报告') + '</dc:title>' +
    '<dc:creator>TopPPT HTML</dc:creator>' +
    '<dcterms:created xsi:type="dcterms:W3CDTF">' + new Date().toISOString() + '</dcterms:created></cp:coreProperties>';
  files['docProps/app.xml'] =
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">' +
    '<Application>TopPPT HTML</Application><Slides>' + slides.length + '</Slides></Properties>';

  const sldIds = slides.map((_, i) => '<p:sldId id="' + (256 + i) + '" r:id="rId' + (i + 2) + '"/>').join('');
  files['ppt/presentation.xml'] =
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<p:presentation xmlns:a="' + NS.a + '" xmlns:p="' + NS.p + '" xmlns:r="' + NS.r + '">' +
    '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>' +
    '<p:sldIdLst>' + sldIds + '</p:sldIdLst>' +
    '<p:sldSz cx="' + E(PW) + '" cy="' + E(PH) + '"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>';
  const presRels = [['rId1', RT + 'slideMaster', 'slideMasters/slideMaster1.xml']];
  slides.forEach((_, i) => presRels.push(['rId' + (i + 2), RT + 'slide', 'slides/slide' + (i + 1) + '.xml']));
  /* OPC 规范：part 的 rels 必须位于同目录 _rels/ 子目录（ppt/_rels/presentation.xml.rels）。
     python-pptx 严格按此路径解析（PowerPoint 宽容但规范路径才是正解）。 */
  files['ppt/_rels/presentation.xml.rels'] = relsXml(presRels);

  files['ppt/slideMasters/slideMaster1.xml'] =
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<p:sldMaster xmlns:a="' + NS.a + '" xmlns:p="' + NS.p + '" xmlns:r="' + NS.r + '">' +
    '<p:cSld><p:bg><p:bgPr>' + solid(S.bg) + '<a:effectLst/></p:bgPr></p:bg>' +
    '<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>' +
    '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>' +
    '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>' +
    '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>' +
    '<p:txStyles><p:titleStyle><a:lvl1pPr><a:defRPr sz="4400" b="1"/></a:lvl1pPr></p:titleStyle>' +
    '<p:bodyStyle><a:lvl1pPr><a:defRPr sz="1800"/></a:lvl1pPr></p:bodyStyle>' +
    '<p:otherStyle><a:lvl1pPr><a:defRPr sz="1800"/></a:lvl1pPr></p:otherStyle></p:txStyles></p:sldMaster>';
  files['ppt/slideMasters/_rels/slideMaster1.xml.rels'] = relsXml([
    ['rId1', RT + 'slideLayout', '../slideLayouts/slideLayout1.xml'],
    ['rId2', RT + 'theme', '../theme/theme1.xml']
  ]);
  files['ppt/slideLayouts/slideLayout1.xml'] =
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<p:sldLayout xmlns:a="' + NS.a + '" xmlns:p="' + NS.p + '" xmlns:r="' + NS.r + '" type="blank" preserve="1">' +
    '<p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>' +
    '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>' +
    '<p:clrMapOvr><a:overrideClrMapping bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/></p:clrMapOvr></p:sldLayout>';
  files['ppt/slideLayouts/_rels/slideLayout1.xml.rels'] = relsXml([
    ['rId1', RT + 'slideMaster', '../slideMasters/slideMaster1.xml']
  ]);
  files['ppt/theme/theme1.xml'] =
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<a:theme xmlns:a="' + NS.a + '" name="TopPPT HTML">' +
    '<a:themeElements><a:clrScheme name="TopPPT HTML">' +
    '<a:dk1><a:srgbClr val="' + S.ink + '"/></a:dk1><a:lt1><a:srgbClr val="' + S.bg + '"/></a:lt1>' +
    '<a:dk2><a:srgbClr val="' + S.body + '"/></a:dk2><a:lt2><a:srgbClr val="' + S.surface + '"/></a:lt2>' +
    '<a:accent1><a:srgbClr val="' + S.accent + '"/></a:accent1>' +
    '<a:accent2><a:srgbClr val="' + A2 + '"/></a:accent2><a:accent3><a:srgbClr val="' + A3 + '"/></a:accent3>' +
    '<a:accent4><a:srgbClr val="' + A4 + '"/></a:accent4><a:accent5><a:srgbClr val="' + A5 + '"/></a:accent5>' +
    '<a:accent6><a:srgbClr val="' + S.faint + '"/></a:accent6>' +
    '<a:hlink><a:srgbClr val="' + S.accent + '"/></a:hlink><a:folHlink><a:srgbClr val="' + S.faint + '"/></a:folHlink>' +
    '</a:clrScheme><a:fontScheme name="TopPPT HTML"><a:majorFont><a:latin typeface="' + S.fontDisplay + '"/><a:ea typeface="' + S.fontDisplay + '"/></a:majorFont>' +
    '<a:minorFont><a:latin typeface="' + S.font + '"/><a:ea typeface="' + S.font + '"/></a:minorFont></a:fontScheme>' +
    '<a:fmtScheme name="TopPPT HTML"><a:fillStyleLst>' + solid(S.accent) + solid(S.surface) + solid(S.soft) + '</a:fillStyleLst>' +
    '<a:lnStyleLst><a:ln w="9525">' + solid(S.line) + '</a:ln><a:ln w="25400">' + solid(S.line) + '</a:ln><a:ln w="38100">' + solid(S.line) + '</a:ln></a:lnStyleLst>' +
    '<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>' +
    '<a:bgFillStyleLst>' + solid(S.bg) + solid(S.surface) + solid(S.soft) + '</a:bgFillStyleLst></a:fmtScheme>' +
    '</a:themeElements></a:theme>';

  slides.forEach((sh, i) => {
    files['ppt/slides/slide' + (i + 1) + '.xml'] = slideXml(sh);
    files['ppt/slides/_rels/slide' + (i + 1) + '.xml.rels'] = relsXml([
      ['rId1', RT + 'slideLayout', '../slideLayouts/slideLayout1.xml']
    ]);
  });

  return zipStore(files);
}

/* ── store-only ZIP（无压缩、合法、PowerPoint 可开；Node 版，逻辑与原浏览器实现一致） ── */
const CRC_T = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
    t[n] = c >>> 0;
  }
  return t;
})();
function crc32(buf) {
  let c = 0xFFFFFFFF;
  for (let i = 0; i < buf.length; i++) c = CRC_T[(c ^ buf[i]) & 0xFF] ^ (c >>> 8);
  return (c ^ 0xFFFFFFFF) >>> 0;
}
function zipStore(files) {
  const enc = new TextEncoder();
  const names = Object.keys(files);
  const chunks = [], central = [];
  let offset = 0;
  names.forEach((name) => {
    const nb = enc.encode(name), data = enc.encode(files[name]);
    const crc = crc32(data);
    const lh = new DataView(new ArrayBuffer(30));
    lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true); lh.setUint16(6, 0x0800, true);
    lh.setUint16(8, 0, true); lh.setUint16(10, 0, true); lh.setUint16(12, 0x21, true);
    lh.setUint32(14, crc, true); lh.setUint32(18, data.length, true); lh.setUint32(22, data.length, true);
    lh.setUint16(26, nb.length, true); lh.setUint16(28, 0, true);
    chunks.push(new Uint8Array(lh.buffer), nb, data);
    const ch = new DataView(new ArrayBuffer(46));
    ch.setUint32(0, 0x02014b50, true); ch.setUint16(4, 20, true); ch.setUint16(6, 20, true);
    ch.setUint16(8, 0x0800, true); ch.setUint16(10, 0, true); ch.setUint16(12, 0, true);
    ch.setUint16(14, 0x21, true); ch.setUint32(16, crc, true);
    ch.setUint32(20, data.length, true); ch.setUint32(24, data.length, true);
    ch.setUint16(28, nb.length, true); ch.setUint32(42, offset, true);
    central.push(new Uint8Array(ch.buffer), nb);
    offset += 30 + nb.length + data.length;
  });
  const cdSize = central.reduce((a, c) => a + c.length, 0);
  const end = new DataView(new ArrayBuffer(22));
  end.setUint32(0, 0x06054b50, true);
  end.setUint16(8, names.length, true); end.setUint16(10, names.length, true);
  end.setUint32(12, cdSize, true); end.setUint32(16, offset, true);
  const total = offset + cdSize + 22;
  const out = new Uint8Array(total);
  let pos = 0;
  chunks.concat(central, [new Uint8Array(end.buffer)]).forEach((c) => {
    out.set(c, pos); pos += c.length;
  });
  return out;
}

/* ── 输入 / 输出 ──
   默认：示例矩阵（assets/examples/*.model.json）→ dist/regression-a/。
   --model=<file> [--out=<dir>]：对任意模型跑 A 通道，供回归探针（split 组合页）与
   cross_verify.py 复用同一套「预览即交付」双裁判。 */
const argv = process.argv.slice(2);
/* 取 --name=value 参数值（路径里含 '=' 时 split('=')[1] 会截断，用 slice 精确取） */
const _argVal = (name) => {
  const a = argv.find((x) => x.startsWith(name + '='));
  return a ? a.slice(name.length + 1) : undefined;
};
const modelArg = _argVal('--model');
const outArg = _argVal('--out');
const OUT_DIR = outArg ? path.resolve(outArg) : OUT;
/* 输出目录延迟到首次成功写盘前再建：模型读取失败时不留下空目录（原子性） */
let outDirReady = false;
function ensureOutDir() {
  if (outDirReady) return;
  try {
    fs.mkdirSync(OUT_DIR, { recursive: true });
  } catch (e) {
    console.error('[gen_channel_a] FAIL: 无法创建输出目录 ' + OUT_DIR + '：' + (e && e.message));
    process.exit(1);
  }
  outDirReady = true;
}

let jobs;
try {
  jobs = modelArg
    ? [[path.resolve(modelArg), path.basename(modelArg).replace(/\.model\.json$/, '.pptx')]]
    : fs.readdirSync(EX).filter((f) => f.endsWith('.model.json')).sort()
        .map((f) => [path.join(EX, f), f.replace('.model.json', '.pptx')]);
} catch (e) {
  console.error('[gen_channel_a] FAIL: 无法列出模型目录 ' + (modelArg || EX) + '：' + (e && e.message));
  process.exit(1);
}

let failed = 0;
for (const [src, name] of jobs) {
  let model;
  try {
    model = JSON.parse(fs.readFileSync(src, 'utf-8'));
  } catch (e) {
    console.error('[gen_channel_a] FAIL: 模型读取失败 ' + src + '：' + (e && e.message));
    failed++;
    continue;
  }
  let bytes;
  try {
    bytes = buildPptx(model);
  } catch (e) {
    console.error('[gen_channel_a] FAIL: A 通道组装失败 ' + src + '：' + (e && e.message));
    failed++;
    continue;
  }
  const out = path.join(OUT_DIR, name);
  try {
    ensureOutDir();
    fs.writeFileSync(out, Buffer.from(bytes));
  } catch (e) {
    console.error('[gen_channel_a] FAIL: 写入失败 ' + out + '：' + (e && e.message));
    failed++;
    continue;
  }
  console.log('A-channel:', path.basename(out), Math.round(bytes.length / 1024) + 'KB');
}
process.exit(failed ? 1 : 0);
