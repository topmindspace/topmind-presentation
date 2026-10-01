#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TopPPT HTML · 单源注入器（版式常量 + DSL schema · 三模板公共片段统一注入）
用法:
    python scripts/sync_runtime.py

职责（消除"多处手动同步"债务）:
  1. 读 scripts/layout-constants.json（唯一事实源：页面几何 / 12 列网格 / 语义字阶 C0–T14 / 三模式独立比例尺
     / 页型几何 / 9 风格 token / 图表登记四元组 / 容器内边距 / 锚点容差 / 图片准入门
     / 校验预算 / 强调色表 / 去AI味词表 / 深度模式配置）
  2. 读 scripts/model-schema.json（DSL schema 单源：页型字段与必填约束 + 图表类型白名单 + 数据表策略）
     → 注入 assets/pptx-export.js 的 __TOPPPT_SCHEMA__ 标记块（浏览器端 validateModel 消费）
  3. 重新生成 assets/pptx-export.js 与 assets/style-gallery.html 的 __TOPPPT_CONSTANTS__ 标记块
     （含 GRID/TYPO/CONT/REG/DEEP、MTS 三模式比例尺、PRESETS/PRESETS_DARK——画廊配色即由此派生，不再手抄色值）
  4. 对 assets/templates/ 三份模式模板注入公共片段（避免三份漂移）:
       __TOPPPT_ENGINE__  ← assets/templates/engine.css（公共样式引擎）
       __TOPPPT_UI__      ← assets/templates/ui.js（公共 UI 脚本：主题/工具组/翻页/动效/预览模态）
       __TOPPPT_RUNTIME__ ← assets/pptx-export.js（PPTX 预览运行时内联副本）
  5. 校验双端单源引用：scripts/build_pptx.js 引用 layout-constants.json（Node require）；
     scripts/extract_model.py 引用 model-schema.json（本地校验同一份 schema）
  6. 校验「页型四件套」完整性：schema 每个页型都要在 layout-constants.json 的 pageTypeGeometry 有几何映射
  7. 校验「图表登记四元组」完整性：charts.types ↔ charts.registry 双向一致、pptx 通道合法、
     非原生图表 dataTable 不得为 off、schema.chartTypes 必须是 registry 子集
  7b. 校验「图表类型可达性」不变量：每个 registry 类型必须可作 chart.type（schema.chartTypes）
      或可作 sections[].type（信息图专属页型）——否则模型无法表达、双引擎实现沦为死代码
  7c. 校验「页型实现可达性」冒烟：schema 每个页型都应出现在 build_pptx.js 与 pptx-export.js 中
      （子串级检查，拦「schema 加了页型、引擎没实现」的静默退化）
  7d. 校验「骨架尺寸单源」不变量：charts.scaffold 键 ⊆ registry，且默认值 ≥ charts.minSize
      同口径阈值（拦「scaffold 硬编码第二源漂移」；信息图页型清单亦单源于此）
  8. 校验语义字阶：每个 level 的 role 必须在 modeTypeScale 中存在
  9. 打印常量摘要哈希，供各方核对（pptx-export.js / 三模板 / 画廊 / build_pptx.js）

模式模板（生成时确定形态，非运行时切换）:
  templates/presentation.html · templates/research.html · templates/architecture.html
  各模板自带：模式密度层 + 模式专属组件 + 模式骨架章节 + REPORT_MODEL（mode 已锁定）
"""
import json
import re
import hashlib
import sys
from pathlib import Path

# Windows GBK 控制台兜底：强制 UTF-8 输出
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
LC = ROOT / 'scripts' / 'layout-constants.json'
MS = ROOT / 'scripts' / 'model-schema.json'
PE = ROOT / 'assets' / 'pptx-export.js'
GALLERY = ROOT / 'assets' / 'style-gallery.html'
TPL_DIR = ROOT / 'assets' / 'templates'
ENGINE = TPL_DIR / 'engine.css'
UI = TPL_DIR / 'ui.js'
TEMPLATES = [TPL_DIR / 'presentation.html',
             TPL_DIR / 'research.html',
             TPL_DIR / 'architecture.html']
EXAMPLES = sorted((ROOT / 'assets' / 'examples').glob('*.html')) if (ROOT / 'assets' / 'examples').is_dir() else []
BJ = ROOT / 'scripts' / 'build_pptx.js'
EM = ROOT / 'scripts' / 'extract_model.py'

CONST_PAT = re.compile(r'/\* __TOPPPT_CONSTANTS_START__ \*/[\s\S]*?/\* __TOPPPT_CONSTANTS_END__ \*/')
SCHEMA_PAT = re.compile(r'/\* __TOPPPT_SCHEMA_START__ \*/[\s\S]*?/\* __TOPPPT_SCHEMA_END__ \*/')
ENGINE_PAT = re.compile(r'/\* __TOPPPT_ENGINE_START__ \*/[\s\S]*?/\* __TOPPPT_ENGINE_END__ \*/')
UI_PAT = re.compile(r'/\* __TOPPPT_UI_START__ \*/[\s\S]*?/\* __TOPPPT_UI_END__ \*/')
RUNTIME_PAT = re.compile(r'/\* __TOPPPT_RUNTIME_START__ \*/[\s\S]*?/\* __TOPPPT_RUNTIME_END__ \*/')


def _strip_comments(obj):
    """递归剔除 JSON 对象里的 $comment 键（注入 JS 常量用）。"""
    if isinstance(obj, dict):
        return {k: _strip_comments(v) for k, v in obj.items() if not k.startswith('$')}
    if isinstance(obj, list):
        return [_strip_comments(v) for v in obj]
    return obj


def build_const_block(lc: dict) -> str:
    page, pt = lc['page'], lc['pageTypes']
    styles = _strip_comments(lc['styles'])
    styles_dark = _strip_comments(lc.get('stylesDark') or {})
    ts = _strip_comments(lc['typeScale'])
    mts = _strip_comments(lc['modeTypeScale'])
    def _presets_js(var_name, styles_dict):
        if not styles_dict:
            return 'var %s = {};' % var_name
        return 'var %s = {\n' % var_name + ',\n'.join(
            "  '%s': { accent:'%s', ink:'%s', body:'%s', faint:'%s', bg:'%s', surface:'%s', line:'%s', soft:'%s', onAccent:'%s', font:'%s', fontDisplay:'%s' }" % (
                k, v['accent'], v['ink'], v['body'], v['faint'], v['bg'], v['surface'], v['line'], v['soft'],
                v['onAccent'], v['font'], v['fontDisplay'])
            for k, v in styles_dict.items()) + '\n};'
    presets_js = _presets_js('PRESETS', styles)
    presets_dark_js = _presets_js('PRESETS_DARK', styles_dark)
    ts_js = 'var TS_BASE = ' + json.dumps(ts, separators=(',', ':')) + ';'
    mts_js = 'var MTS = ' + json.dumps(mts, separators=(',', ':')) + ';'
    pt_js = 'var PT = ' + json.dumps(_strip_comments(pt), ensure_ascii=False, separators=(',', ':')) + ';'
    colors_js = 'var STYLE_DATA_COLORS = ' + json.dumps(
        _strip_comments(lc.get('styleDataColors') or {}), separators=(',', ':')) + ';'
    colors_dark_js = 'var STYLE_DATA_COLORS_DARK = ' + json.dumps(
        _strip_comments(lc.get('styleDataColorsDark') or {}), separators=(',', ':')) + ';'
    # 12 列网格 / 语义字阶 / 容器内边距 / 图表登记四元组 / 深度模式配置
    grid_js = 'var GRID = ' + json.dumps(_strip_comments(lc['grid']), separators=(',', ':')) + ';'
    typo_js = 'var TYPO = ' + json.dumps(_strip_comments(lc['typography']), ensure_ascii=False,
                                         separators=(',', ':')) + ';'
    cont_js = 'var CONT = ' + json.dumps(_strip_comments(lc['containers']), ensure_ascii=False,
                                         separators=(',', ':')) + ';'
    reg_js = 'var REG = ' + json.dumps(_strip_comments((lc.get('charts') or {}).get('registry') or {}),
                                       ensure_ascii=False, separators=(',', ':')) + ';'
    deep_js = 'var DEEP = ' + json.dumps(_strip_comments(lc['deepMode']), ensure_ascii=False,
                                         separators=(',', ':')) + ';'
    # 图片规格与配图占位约定（双引擎拼同一占位文本，cross_verify 逐页文本一致）
    img_js = 'var IMG = ' + json.dumps(_strip_comments(lc.get('imageSpec') or {}), ensure_ascii=False,
                                       separators=(',', ':')) + ';'
    # 页型布局区域 IR（与 scripts/lib_layout_regions.js 同源公式；浏览器端 A 通道消费）
    # Batch 3: layoutSlots 单源 = layout-constants.json（不再读独立 layout_slots.json）
    slots = lc.get('layoutSlots') or {}
    if not slots:
        slots_path = ROOT / 'scripts' / 'layout_slots.json'  # 兼容过渡
        if slots_path.exists():
            try:
                slots = json.loads(slots_path.read_text(encoding='utf-8'))
            except json.JSONDecodeError:
                slots = {}
    slots_js = 'var LAYOUT_SLOTS = ' + json.dumps(_strip_comments(slots), ensure_ascii=False,
                                                  separators=(',', ':')) + ';'
    region_fn = r'''
/* regionOf(pageType, slotId, opts) — 页型布局区域 IR（与 scripts/lib_layout_regions.js 同源） */
function regionOf(pageType, slotId, opts) {
  var type = String(pageType || 'points'), slot = String(slotId || '');
  opts = opts || {};
  var L = PT.layout || {}, C = PT.common || {};
  var topDefault = C.bodyY || 2.5;
  var bottomDefault = opts.withNote ? (L.contentBottomWithNote || 6.4) : (L.contentBottom || 6.9);
  if (slot === 'head' || slot === 'chrome') {
    return { x: MX, y: C.headEyebrowY || 0.55, w: CW,
      h: Math.max(0.4, (C.headRuleY || 1.95) - (C.headEyebrowY || 0.55)),
      titleY: C.headTitleY, ruleY: C.headRuleY, leadY: C.leadY, bodyY: C.bodyY };
  }
  if (slot === 'annotation' || slot === 'soWhat') {
    var sy = (PT.exhibit && PT.exhibit.soWhatY != null) ? PT.exhibit.soWhatY : 6.05;
    return { x: MX, y: sy, w: CW, h: 0.62 };
  }
  if (slot === 'footnote') {
    var fy = (PT.exhibit && PT.exhibit.footnoteY != null) ? PT.exhibit.footnoteY : ((PT.note && PT.note.y) || 6.55);
    return { x: MX, y: fy, w: CW - 1.2, h: (PT.note && PT.note.h) || 0.32 };
  }
  var P = PT[type] || {};
  if (type === 'exhibit' && slot === 'primary') {
    var ey = P.chartY || 2.95;
    return { x: MX, y: ey, w: CW, h: Math.max(1.2, (L.contentBottomWithNote || 6.4) - ey), badgeY: P.badgeY };
  }
  if (type === 'metrics' && slot === 'primary') {
    return { x: MX, y: P.bandY || 3.1, w: CW, h: P.cardH || 2.3, gap: P.gap, maxW: P.maxW,
      valY: P.valY, valH: P.valH, capY: P.capY, capH: P.capH };
  }
  if (type === 'table' && slot === 'primary') {
    var ty = P.y || topDefault;
    return { x: MX, y: ty, w: CW, h: Math.max(1, (opts.bottom != null ? opts.bottom : bottomDefault) - ty) };
  }
  if (type === 'bar' && slot === 'primary') {
    var by = P.chartY || 2.95;
    var bb = opts.bottom != null ? opts.bottom : bottomDefault;
    /* chartX/chartW 历史误用已纠正：与 donut/table/hbar/exhibit 同口径，图表盒对齐版心 (MX, CW) */
    return { x: MX, y: by, w: CW, h: Math.max(1.2, bb - by) };
  }
  if (type === 'bar' && slot === 'hbar') {
    var y0 = P.hbarY0 || 2.6;
    var y1 = opts.bottom != null ? opts.bottom : (P.hbarY1 || 6.25);
    return { x: MX, y: y0, w: CW, h: Math.max(1.2, y1 - y0) };
  }
  if (type === 'points' && (slot === 'primary' || slot === 'list')) {
    var ly = P.listY || topDefault;
    return { x: MX, y: ly, w: CW, h: Math.max(0.8, (opts.bottom != null ? opts.bottom : bottomDefault) - ly) };
  }
  if (type === 'split' && (slot === 'left' || slot === 'right')) {
    var st = P.chartY || topDefault;
    var sb = opts.bottom != null ? opts.bottom : bottomDefault;
    if (slot === 'left') return { x: MX, y: st, w: CW * (P.leftW || 0.55), h: Math.max(1.2, sb - st) };
    return { x: MX + CW * (P.rightX != null ? P.rightX : 0.585), y: st, w: CW * (P.rightW || 0.415), h: Math.max(1.2, sb - st) };
  }
  if (type === 'twocol' && (slot === 'primary' || slot === 'left' || slot === 'right')) {
    var gap = P.colGap || 0.5, colW = (CW - gap) / 2;
    var tt = opts.top != null ? opts.top : topDefault;
    var tb = opts.bottom != null ? opts.bottom : bottomDefault;
    if (slot === 'right') return { x: MX + colW + gap, y: tt, w: colW, h: Math.max(1, tb - tt) };
    return { x: MX, y: tt, w: colW, h: Math.max(1, tb - tt) };
  }
  if ((type === 'diagram' || type === 'lane') && slot === 'primary') {
    var arch = PT.arch || {};
    var dy = (opts.mode === 'architecture' && arch.fullStartY != null) ? arch.fullStartY : (P.bodyStartY || 2.9);
    var db = (opts.mode === 'architecture' && arch.fullEndY != null) ? arch.fullEndY
      : (opts.bottom != null ? opts.bottom : bottomDefault);
    return { x: MX, y: dy, w: CW, h: Math.max(1.2, db - dy) };
  }
  if (type === 'kpi' && (slot === 'hero' || slot === 'primary')) {
    return { x: MX, y: P.heroY || 2.9, w: CW * (P.heroW || 0.52), h: P.heroH || 1.6,
      dividerX: P.dividerX, metricY0: P.metricY0, metricRowH: P.metricRowH };
  }
  /* R3：kpi 支撑指标列——落在 dividerX 右侧（默认全宽返回会压住 hero） */
  if (type === 'kpi' && slot === 'metrics') {
    var dxK = P.dividerX != null ? P.dividerX : 0.56;
    return {
      x: MX + CW * dxK + 0.35, y: P.metricY0 || 2.95,
      w: CW * (1 - dxK) - 0.5,
      h: Math.max(0.6, bottomDefault - (P.metricY0 || 2.95)),
    };
  }
  if (type === 'comparison' && (slot === 'left' || slot === 'primary' || slot === 'right')) {
    var cg = P.panelGap || 0.4, pw = (CW - cg) / 2;
    if (slot === 'right') return { x: MX + pw + cg, y: P.panelY || 2.55, w: pw, h: P.panelH || 3.4 };
    return { x: MX, y: P.panelY || 2.55, w: pw, h: P.panelH || 3.4 };
  }
  if (type === 'quote' && slot === 'primary') {
    return { x: MX + 1.05, y: P.textY || 2.7, w: CW - 2.1, h: P.textH || 2.3 };
  }
  if (type === 'heatmap' && slot === 'primary') {
    var hy = P.y || 2.6;
    return { x: MX, y: hy, w: CW, h: Math.max(1, (opts.bottom != null ? opts.bottom : bottomDefault) - hy) };
  }
  if (type === 'bullet' && slot === 'primary') {
    var uy = P.y || 2.6;
    return { x: MX, y: uy, w: CW, h: Math.max(1, (opts.bottom != null ? opts.bottom : bottomDefault) - uy) };
  }
  if (type === 'pyramid' && slot === 'primary') {
    var py2 = P.y || 2.35;
    return { x: MX, y: py2, w: CW, h: Math.max(1, (opts.bottom != null ? opts.bottom : bottomDefault) - py2) };
  }
  if (type === 'steps' && slot === 'primary') {
    return { x: MX, y: P.y || 3.05, w: CW, h: P.barH || 1.35 };
  }
  if (type === 'cards' && slot === 'primary') {
    var cy2 = P.startY || 3.0;
    return { x: MX, y: cy2, w: CW, h: Math.max(1, (opts.bottom != null ? opts.bottom : bottomDefault) - cy2) };
  }
  if (type === 'timeline' && slot === 'primary') {
    return { x: MX, y: P.labelY || 2.95, w: CW, h: Math.max(1, bottomDefault - (P.labelY || 2.95)) };
  }
  if (type === 'image' && slot === 'primary') {
    var iy2 = Math.max(P.y || 2.3, opts.top || 0);
    /* R2：有图注时图片不得越过 contentBottomWithNote（图注落注释带，属 annotation self） */
    var iBottom = (opts.bottom != null) ? opts.bottom
      : (opts.caption ? (L.contentBottomWithNote || 6.4) : bottomDefault);
    return { x: MX, y: iy2, w: CW, h: Math.max(1.2, Math.min(P.h || 4.2, iBottom - iy2)) };
  }
  if ((type === 'halftable') && (slot === 'left' || slot === 'primary')) {
    var rs = PT.research || {};
    var ht = opts.top != null ? opts.top : topDefault;
    var hb = opts.bottom != null ? opts.bottom : bottomDefault;
    return { x: MX, y: ht, w: CW * (rs.halfTableW || 0.52), h: Math.max(1, hb - ht) };
  }
  if ((type === 'halftable') && (slot === 'right' || slot === 'secondary')) {
    var rs2 = PT.research || {};
    var ht2 = opts.top != null ? opts.top : topDefault;
    var hb2 = opts.bottom != null ? opts.bottom : bottomDefault;
    return { x: MX + CW * (rs2.halfChartX || 0.57), y: ht2, w: CW * (rs2.halfChartW || 0.43), h: Math.max(1, hb2 - ht2) };
  }
  if (type === 'matrix' && slot === 'primary') {
    var rm = PT.research || {};
    var my = rm.matrixY || 2.3;
    return { x: MX, y: my, w: CW, h: Math.max(1, (opts.bottom != null ? opts.bottom : bottomDefault) - my) };
  }
  var INFO = { sankey:1, treemap:1, boxplot:1, network:1, marimekko:1, streamgraph:1 };
  if (INFO[type] && slot === 'primary') {
    var iy3 = P.y || topDefault;
    var ih3 = Math.max(1.2, Math.min(P.h || 4.1, (opts.bottom != null ? opts.bottom : bottomDefault) - iy3));
    return { x: MX, y: iy3, w: CW, h: ih3 };
  }
  return { x: MX, y: topDefault, w: CW, h: Math.max(0.8, bottomDefault - topDefault) };
}
'''
    return '\n'.join([
        '/* __TOPPPT_CONSTANTS_START__ */',
        '/* ── 由 scripts/sync_runtime.py 从 scripts/layout-constants.json 注入 · 禁止手改 ── */',
        '/* MTS = 三模式独立排版比例尺（按模式取 pt；基准 TS_BASE = presentation 档） */',
        '/* PRESETS_DARK = 风格 dark token（REPORT_MODEL.theme="dark" 时导出深色版）*/',
        '/* GRID = 12 列网格；TYPO = 语义字阶 C0–T14；CONT = 容器内边距；REG = 图表登记四元组；DEEP = 深度模式配置 */',
        '/* IMG = 素材图片规格与配图占位约定（版式/裁切/建议尺寸/占位标签，双引擎同源） */',
        '/* STYLE_DATA_COLORS(_DARK) = 9 套风格各自的编码色板 c1–c5（数据系列；结构色纪律不变） */',
        '/* LAYOUT_SLOTS + regionOf = 页型布局区域 IR（与 scripts/lib_layout_regions.js 同源） */',
        'var PW = %s, PH = %s, MX = %s, CW = PW - 2 * MX, EMU = %s;'
        % (page['pw'], page['ph'], page['mx'], page['emu']),
        ts_js, mts_js, pt_js, presets_js, presets_dark_js, colors_js, colors_dark_js,
        grid_js, typo_js, cont_js, reg_js, deep_js, img_js, slots_js, region_fn,
        '/* __TOPPPT_CONSTANTS_END__ */'])


def build_schema_block(ms: dict) -> str:
    return '\n'.join([
        '/* __TOPPPT_SCHEMA_START__ */',
        '/* ── 由 scripts/sync_runtime.py 从 scripts/model-schema.json 注入 · 禁止手改 ── */',
        '/* DSL schema 单源：浏览器端 validateModel 与 scripts/extract_model.py 消费同一份定义 */',
        'var MODEL_SCHEMA = ' + json.dumps(_strip_comments(ms), ensure_ascii=False, separators=(',', ':')) + ';',
        '/* __TOPPPT_SCHEMA_END__ */'])


def inject(path: Path, pat: re.Pattern, repl: str, label: str) -> bool:
    try:
        src = path.read_text(encoding='utf-8')
    except OSError as e:
        print(f'错误： 无法读取 {path.name}: {e}')
        return False
    if not pat.search(src):
        print(f'错误： {path.name} 缺少 {label} 标记块')
        return False
    path.write_text(pat.sub(lambda m: repl, src, count=1), encoding='utf-8')
    return True


def main() -> int:
    if not LC.exists():
        print(f'错误： 找不到 {LC}')
        return 2
    try:
        lc = json.loads(LC.read_text(encoding='utf-8'))
    except UnicodeDecodeError as e:
        print(f'错误： {LC.name} 不是合法 UTF-8: {e}')
        return 2
    except json.JSONDecodeError as e:
        print(f'错误： {LC.name} 不是合法 JSON: {e}')
        return 2
    except OSError as e:
        print(f'错误： 无法读取 {LC}: {e}')
        return 2
    if not MS.exists():
        print(f'错误： 找不到 {MS}（DSL schema 单源）')
        return 2
    try:
        ms = json.loads(MS.read_text(encoding='utf-8'))
    except UnicodeDecodeError as e:
        print(f'错误： {MS.name} 不是合法 UTF-8: {e}')
        return 2
    except json.JSONDecodeError as e:
        print(f'错误： {MS.name} 不是合法 JSON: {e}')
        return 2
    except OSError as e:
        print(f'错误： 无法读取 {MS}: {e}')
        return 2
    ok = True

    # ① 重新生成 pptx-export.js 常量块 + schema 块
    try:
        src = PE.read_text(encoding='utf-8')
    except OSError as e:
        print(f'错误： 无法读取 {PE}: {e}')
        return 1
    if not CONST_PAT.search(src):
        print('错误： assets/pptx-export.js 缺少 __TOPPPT_CONSTANTS__ 标记块')
        return 1
    if not SCHEMA_PAT.search(src):
        print('错误： assets/pptx-export.js 缺少 __TOPPPT_SCHEMA__ 标记块')
        return 1
    block = build_const_block(lc)
    PE.write_text(CONST_PAT.sub(lambda m: block, src), encoding='utf-8')
    src = PE.read_text(encoding='utf-8')
    schema_block = build_schema_block(ms)
    PE.write_text(SCHEMA_PAT.sub(lambda m: schema_block, src), encoding='utf-8')

    # ①-b 风格画廊：同一份常量块注入（画廊配色改为从 PRESETS/PRESETS_DARK 派生，消除第四处手抄色值）
    if GALLERY.exists():
        gsrc = GALLERY.read_text(encoding='utf-8')
        if CONST_PAT.search(gsrc):
            GALLERY.write_text(CONST_PAT.sub(lambda m: block, gsrc), encoding='utf-8')
        else:
            print('警告: assets/style-gallery.html 缺少 __TOPPPT_CONSTANTS__ 标记块（画廊配色无法单源化）')
            ok = False

    # ② 公共片段源
    if not ENGINE.exists() or not UI.exists():
        print(f'错误： 缺少公共片段 {ENGINE} / {UI}')
        return 1
    engine_css = ENGINE.read_text(encoding='utf-8').rstrip('\n')
    ui_js = UI.read_text(encoding='utf-8').rstrip('\n')
    runtime = PE.read_text(encoding='utf-8').rstrip('\n')

    engine_repl = ('/* __TOPPPT_ENGINE_START__ */\n'
                   '/* ══ TopPPT HTML 公共样式引擎（assets/templates/engine.css 的内联副本 · 由 scripts/sync_runtime.py 注入，禁止手改） ══ */\n'
                   + engine_css + '\n/* __TOPPPT_ENGINE_END__ */')
    ui_repl = ('/* __TOPPPT_UI_START__ */\n'
               '/* ══ TopPPT HTML 公共 UI 脚本（assets/templates/ui.js 的内联副本 · 由 scripts/sync_runtime.py 注入，禁止手改） ══ */\n'
               + ui_js + '\n/* __TOPPPT_UI_END__ */')
    # 运行时同版本戳：对注入源 assets/pptx-export.js（rstrip 后）取 sha256[:16]，
    # 写入模板内联块，供 validate_report 比对防「模板未 sync」漂移。
    runtime_sha = hashlib.sha256(runtime.encode('utf-8')).hexdigest()[:16]
    runtime_repl = ('/* __TOPPPT_RUNTIME_START__ */\n'
                    '/* ══ PPTX 导出运行时（assets/pptx-export.js 的内联副本 · 由 scripts/sync_runtime.py 注入，禁止手改） ══ */\n'
                    f'/* __TOPPPT_RUNTIME_SHA__:{runtime_sha} */\n'
                    + runtime + '\n/* __TOPPPT_RUNTIME_END__ */')

    # ③ 注入三份模式模板 + 黄金样张（样张也内联运行时，须同戳）
    inject_targets = list(TEMPLATES) + list(EXAMPLES)
    for tpl in inject_targets:
        if not tpl.exists():
            print(f'警告: 模板/样张不存在 {tpl}')
            ok = False
            continue
        ok = inject(tpl, ENGINE_PAT, engine_repl, '__TOPPPT_ENGINE__') and ok
        ok = inject(tpl, UI_PAT, ui_repl, '__TOPPPT_UI__') and ok
        ok = inject(tpl, RUNTIME_PAT, runtime_repl, '__TOPPPT_RUNTIME__') and ok

    # ④ 校验双端单源引用（build_pptx.js → layout-constants.json；extract_model.py → model-schema.json）
    if BJ.exists():
        bj = BJ.read_text(encoding='utf-8')
        if 'layout-constants.json' not in bj:
            print('警告: scripts/build_pptx.js 未引用 layout-constants.json（常量可能漂移）')
            ok = False
    else:
        print('警告: scripts/build_pptx.js 不存在')
        ok = False
    if EM.exists():
        em = EM.read_text(encoding='utf-8')
        if 'model-schema.json' not in em:
            print('警告: scripts/extract_model.py 未引用 model-schema.json（schema 可能漂移）')
            ok = False
    else:
        print('警告: scripts/extract_model.py 不存在')
        ok = False

    # ⑤ 页型四件套完整性：schema 每个页型都要有几何映射，且映射指向存在的几何组
    pt = lc.get('pageTypes') or {}
    p2g = lc.get('pageTypeGeometry') or {}
    geom_keys = {k for k in pt if not k.startswith('$')}
    schema_types = [k for k in (ms.get('pageTypes') or {}) if not k.startswith('$')]
    for t in schema_types:
        g = p2g.get(t)
        if not g:
            print(f'警告: 页型 {t!r} 在 model-schema.json 中，但 layout-constants.json 的 pageTypeGeometry 缺映射')
            ok = False
        elif g not in geom_keys:
            print(f'警告: 页型 {t!r} 映射到不存在的几何组 {g!r}')
            ok = False
    orphan = [t for t in p2g if not t.startswith('$') and t not in schema_types]
    if orphan:
        print(f'警告: pageTypeGeometry 含未登记页型 {orphan}（schema 与几何不同步）')
        ok = False

    # ⑥ 图表登记四元组完整性：charts.types 与 charts.registry 双向一致，且 registry 条目字段齐全
    chart_types = [t for t in ((lc.get('charts') or {}).get('types') or [])]
    registry = (lc.get('charts') or {}).get('registry') or {}
    for t in chart_types:
        if t not in registry:
            print(f'警告: 图表类型 {t!r} 在 charts.types 中，但 charts.registry 缺登记')
            ok = False
    for t, spec in registry.items():
        if t.startswith('$'):
            continue
        if t not in chart_types:
            print(f'警告: charts.registry 含未登记类型 {t!r}（types 与 registry 不同步）')
            ok = False
        if spec.get('pptx') not in ('native', 'shape'):
            print(f'警告: 图表 {t!r} 的 pptx 通道非法（应为 native / shape）')
            ok = False
        if not spec.get('dataTable'):
            print(f'警告: 图表 {t!r} 缺 dataTable 策略')
            ok = False
        if spec.get('pptx') == 'shape' and spec.get('dataTable') == 'off' and t != 'sparkline':
            print(f'警告: 非原生图表 {t!r} 的 dataTable 不得为 off（数据可追溯铁律）')
            ok = False

    # ⑦ 图表类型白名单 ↔ 登记表一致（schema.chartTypes 必须是 registry 的子集）
    schema_charts = [c for c in (ms.get('chartTypes') or [])]
    unknown_charts = [c for c in schema_charts if c not in registry]
    if unknown_charts:
        print(f'警告: model-schema.json chartTypes 含 registry 未登记类型 {unknown_charts}')
        ok = False

    # ⑦-b 可达性不变量：每个 registry 类型都必须「模型可表达」，否则双引擎实现是死代码。
    #   可达 = 可作 chart.type（在 schema.chartTypes）∪ 可作 sections[].type（信息图专属页型）。
    #   信息图页型清单单源 = charts.scaffold.infoTypes（scaffold/extract_snippet 同源消费）。
    scaff = (lc.get('charts') or {}).get('scaffold') or {}
    info_page_types = set(scaff.get('infoTypes') or {})
    unreachable = [t for t in chart_types if t not in schema_charts and t not in info_page_types]
    if unreachable:
        print(f'警告: 图表类型 {unreachable} 既不在 schema.chartTypes 也不是信息图专属页型 —— '
              '模型无法表达，双引擎实现将成为死代码')
        ok = False
    ghost_pages = sorted(t for t in info_page_types if t not in schema_types)
    if ghost_pages:
        print(f'警告: 信息图页型 {ghost_pages} 未登记在 schema.pageTypes（可达性口径失效）')
        ok = False
    for t in info_page_types:
        if t in schema_charts:
            print(f'警告: 信息图页型 {t!r} 同时出现在 chartTypes —— 二者载荷不同，'
                  '会造成 chart 对象字段歧义')
            ok = False

    # ⑦-d 骨架尺寸单源不变量：charts.scaffold 是 scaffold_report.py 骨架尺寸的唯一事实源——
    #   ① 键必须 ⊆ registry（防孤儿尺寸）② 默认值 ≥ charts.minSize 同口径阈值（防骨架天生不达标）
    if not scaff:
        print('警告: layout-constants.json 缺 charts.scaffold（骨架尺寸退回脚本硬编码第二源）')
        ok = False
    else:
        min_size = (lc.get('charts') or {}).get('minSize') or {}
        legal = set(chart_types)
        for caliber, key in (('viewBoxHeight', 'vbHeightMin'), ('pxWidth', 'pxWidthMin')):
            for t, v in (scaff.get(caliber) or {}).items():
                if t not in legal:
                    print(f'警告: charts.scaffold.{caliber} 含 registry 未登记类型 {t!r}')
                    ok = False
                floor = (min_size.get(t) or {}).get(key)
                if floor is not None and v < floor:
                    print(f'警告: charts.scaffold.{caliber}[{t!r}]={v} < minSize.{key}={floor}'
                          '（骨架默认值天生不达标）')
                    ok = False
        orphan_info = sorted(t for t in info_page_types if t not in legal)
        if orphan_info:
            print(f'警告: charts.scaffold.infoTypes 含 registry 未登记类型 {orphan_info}')
            ok = False

    # ⑦-c 页型实现可达性（冒烟）：schema 的每个页型都应在双引擎源码中出现，
    #   否则「schema 加了页型、引擎没实现」会静默退化为默认版式。
    #   注：这是子串级冒烟检查（不解析 AST），只能拦住「完全没提」的漏实现。
    for eng_name, eng_path in (('scripts/build_pptx.js', ROOT / 'scripts' / 'build_pptx.js'),
                               ('assets/pptx-export.js', ROOT / 'assets' / 'pptx-export.js')):
        try:
            eng_txt = eng_path.read_text(encoding='utf-8')
        except OSError:
            print(f'警告: 无法读取 {eng_name}，跳过页型实现核查')
            ok = False
            continue
        eng_missing = [t for t in schema_types if t not in eng_txt]
        if eng_missing:
            print(f'警告: {eng_name} 未见页型 {eng_missing}（schema 已登记但引擎未提及）')
            ok = False

    # ⑧ 语义字阶完整性：每个 level 的 role 必须在 modeTypeScale 的角色集合中存在
    mts = lc['modeTypeScale']
    mts_roles = {k for k in (mts.get('presentation') or {})}
    for lv in (lc.get('typography') or {}).get('levels') or []:
        if lv.get('role') not in mts_roles:
            print(f'警告: 语义字阶 {lv.get("id")} 指向不存在的比例尺角色 {lv.get("role")!r}')
            ok = False

    # ⑨ 图片系统完整性：imageSpec 版式在双引擎可表达 + 占位标签三要素齐全 +
    #   image 页型三选一必填口径（src/items/placeholder）。拦「schema 放宽了、引擎没实现」
    #   与「占位文本拼不出来」两类静默退化。
    img = lc.get('imageSpec') or {}
    img_layouts = [x for x in (img.get('layouts') or [])]
    if not img_layouts:
        print('警告: layout-constants.json 缺 imageSpec.layouts（素材图片版式无单源）')
        ok = False
    for key in ('placeholderLabel', 'placeholderHintPrefix', 'placeholderHintSuffix', 'recommendedSizePx'):
        if not img.get(key):
            print(f'警告: imageSpec 缺 {key}（配图占位文本无法由双引擎同源拼接）')
            ok = False
    for lay in img_layouts:
        if lay not in (img.get('recommendedSizePx') or {}):
            print(f'警告: imageSpec.recommendedSizePx 缺版式 {lay!r} 的建议尺寸')
            ok = False
    # 版式比例：每个版式都要有 ratioDefault（双引擎据此算高度）+ ratioCssClass（HTML 锁比例类）
    ratio_def = img.get('ratioDefault') or {}
    ratio_css = img.get('ratioCssClass') or {}
    engine_css = (TPL_DIR / 'engine.css').read_text(encoding='utf-8') if (TPL_DIR / 'engine.css').exists() else ''
    for lay in img_layouts:
        if not ratio_def.get(lay):
            print(f'警告: imageSpec.ratioDefault 缺版式 {lay!r} 的比例（HTML/PPTX 版式会不一致）')
            ok = False
        cls = ratio_css.get(lay)
        if not cls:
            print(f'警告: imageSpec.ratioCssClass 缺版式 {lay!r} 的锁定类')
            ok = False
        elif engine_css and ('.' + cls) not in engine_css:
            print(f'警告: engine.css 缺图片比例锁定类 .{cls}（HTML 侧无法锁定 {lay} 版式比例）')
            ok = False
    img_def = (ms.get('pageTypes') or {}).get('image') or {}
    if not any(str(s).startswith('anyof:') for s in (img_def.get('required') or [])):
        print('警告: model-schema.json 的 image 页型未用 anyof 三选一（src/items/placeholder）')
        ok = False
    for eng_name, eng_path in (('scripts/build_pptx.js', ROOT / 'scripts' / 'build_pptx.js'),
                               ('assets/pptx-export.js', ROOT / 'assets' / 'pptx-export.js')):
        try:
            eng_txt = eng_path.read_text(encoding='utf-8')
        except OSError:
            continue
        eng_missing_lay = [lay for lay in img_layouts
                           if lay not in ('full', 'half') and ("'%s'" % lay) not in eng_txt]
        if eng_missing_lay:
            print(f'警告: {eng_name} 未见图片版式 {eng_missing_lay}（imageSpec 已登记但引擎未提及）')
            ok = False

    # ⑩ 页型布局 IR（LC.layoutSlots）：高频页型槽位完整性
    n_slots = 0
    slots_doc = lc.get('layoutSlots') or {}
    if not slots_doc.get('pageTypes'):
        print('警告: layout-constants.json 缺 layoutSlots.pageTypes（页型布局 IR 单源）')
        ok = False
    else:
        try:
            slots_pages = slots_doc.get('pageTypes') or {}
            for pt_name, pt_def in slots_pages.items():
                if pt_name not in schema_types:
                    print(f'警告: layoutSlots 页型 {pt_name!r} 不在 schema.pageTypes')
                    ok = False
                slot_list = pt_def.get('slots') or []
                if not slot_list:
                    print(f'警告: layoutSlots 页型 {pt_name!r} 无槽位定义')
                    ok = False
                    continue
                ids = [s.get('id') for s in slot_list]
                if 'head' not in ids or not any(s.get('role') == 'primary' for s in slot_list):
                    print(f'警告: layoutSlots 页型 {pt_name!r} 缺 head 或 primary 槽位')
                    ok = False
            n_slots = len(slots_pages)
            # 布局 IR 模块存在性（B 通道 require）
            ir_mod = ROOT / 'scripts' / 'lib_layout_regions.js'
            if not ir_mod.exists():
                print('警告: 缺 scripts/lib_layout_regions.js（布局区域 IR 模块）')
                ok = False
            else:
                ir_txt = ir_mod.read_text(encoding='utf-8')
                for key in ('regionOf', 'layoutSlots', 'layout-constants.json'):
                    if key not in ir_txt:
                        print(f'警告: lib_layout_regions.js 缺少 {key!r} 引用')
                        ok = False
                # 布局 IR 烟测：regionOf 与 pageTypes 常量一致（防公式漂移）
                try:
                    import subprocess as _sp
                    smoke_js = r'''
const R = require("./scripts/lib_layout_regions.js");
const LC = R.LC;
const cases = [
  ["exhibit","primary", LC.pageTypes.exhibit.chartY],
  ["metrics","primary", LC.pageTypes.metrics.bandY],
  ["head","head", LC.pageTypes.common.headEyebrowY],
  ["bar","primary", LC.pageTypes.bar.chartY],
  ["table","primary", LC.pageTypes.table.y],
];
let bad = 0;
for (const [t,s,expectY] of cases) {
  const r = R.regionOf(t, s, {});
  if (!r || Math.abs(r.y - expectY) > 0.001) {
    console.error("IR drift", t, s, r && r.y, expectY);
    bad++;
  }
}
process.exit(bad ? 1 : 0);
'''
                    node = None
                    try:
                        sys.path.insert(0, str(ROOT / 'scripts'))
                        from env_probe import find_node  # noqa: E402
                        node = find_node()
                    except Exception:
                        node = None
                    if node:
                        rsm = _sp.run([node, '-e', smoke_js], cwd=str(ROOT),
                                      capture_output=True, text=True)
                        if rsm.returncode != 0:
                            print('警告: lib_layout_regions regionOf 烟测失败（与 pageTypes 不一致）')
                            print((rsm.stderr or rsm.stdout or '')[:400])
                            ok = False
                except Exception as exc:
                    print(f'警告: 布局 IR 烟测未执行: {exc}')
        except json.JSONDecodeError as exc:
            print(f'警告: layoutSlots 解析失败: {exc}')
            ok = False
            n_slots = 0

    # ⑪ 版本单源一致性：layout-constants.json `version` 是唯一事实源；
    #     model-schema / layout_slots / package.json（npm 语义化 x.y.z）漂移即 WARN
    #     （v8.3 教训：SKILL.md frontmatter 移除 version 后，五处版本一度只有一处升级）
    ver = lc.get('version')
    if not ver:
        print('警告: layout-constants.json 缺 version（版本唯一事实源）')
        ok = False
    else:
        if ms.get('version') != ver:
            print(f'警告: model-schema.json version={ms.get("version")!r} ≠ layout-constants.json {ver!r}')
            ok = False
        slots_ver = (lc.get('layoutSlots') or {}).get('version')
        if slots_ver and slots_ver != ver:
            print(f'警告: layoutSlots.version={slots_ver!r} ≠ layout-constants {ver!r}')
            ok = False
        try:
            pj_ver = json.loads((ROOT / 'package.json').read_text(encoding='utf-8')).get('version')
            if not str(pj_ver or '').startswith(f'{ver}.'):
                print(f'警告: package.json version={pj_ver!r} 未对齐 {ver}.x（npm 语义化）')
                ok = False
        except (OSError, json.JSONDecodeError):
            pass

    # ⑤ 摘要哈希（各方核对用）
    raw = LC.read_text(encoding='utf-8')
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]
    ms_raw = MS.read_text(encoding='utf-8')
    ms_digest = hashlib.sha256(ms_raw.encode('utf-8')).hexdigest()[:16]
    n_styles = len(lc['styles'])
    n_pt = len([k for k in lc['pageTypes'] if not k.startswith('$')])
    n_schema_pt = len([k for k in ms['pageTypes'] if not k.startswith('$')])
    n_charts = len((lc.get('charts') or {}).get('types') or [])
    reg = (lc.get('charts') or {}).get('registry') or {}
    n_native = len([t for t, s in reg.items() if not t.startswith('$') and s.get('pptx') == 'native'])
    n_shape = len([t for t, s in reg.items() if not t.startswith('$') and s.get('pptx') == 'shape'])
    n_typo = len((lc.get('typography') or {}).get('levels') or [])
    print('单源注入完成:')
    print(f'  layout-constants.json  sha256[:16] = {digest}')
    print(f'  model-schema.json      sha256[:16] = {ms_digest}  · 页型 {n_schema_pt} 种')
    print(f'  风格 token {n_styles} 套 · 三模式独立比例尺 {len([k for k in lc["modeTypeScale"] if not k.startswith("$")])} 套 · 页型几何 {n_pt} 组')
    print(f'  图表登记 {n_charts} 种（原生 {n_native} / 形状 {n_shape}） · 语义字阶 {n_typo} 级 · 12 列网格 {lc["grid"]["columns"]} 列 · 布局 IR {n_slots} 页型')
    print('  已刷新: assets/pptx-export.js（常量块 + schema 块） · assets/style-gallery.html（常量块） · templates/{presentation,research,architecture}.html + assets/examples/*.html（引擎/UI/运行时内联副本，含 __TOPPPT_RUNTIME_SHA__）')
    print(f'  双端单源引用校验: {"PASS" if ok else "WARN（build_pptx 应 require layout-constants.json；extract_model 应读 model-schema.json；页型四件套与图表登记须完整）"}')
    print(f'  说明: 页型几何 {n_pt} 组（多页型共享几何组） · schema 页型 {n_schema_pt} 种')
    return 0


if __name__ == '__main__':
    sys.exit(main())
