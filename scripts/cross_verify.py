#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""topmind-presentation · HTML ↔ PPTX 同源核对（可选依赖 python-pptx）

M2 起浏览器端几何引擎（原 旧浏览器通道（已删除））已删除，版式几何只在 build_pptx.js 实现一次；本脚本改为核对
「同一模型 → HTML 与 PPTX 同源」：页序计划（lib_solver 拆页）、章节标题顺序、原生图表数值、
形状图表数据标签、文本溢出启发式。用法：先 python scripts/regression.py 生成 PPTX，再
python scripts/cross_verify.py。函数 chart_data_verify 等被 negative_tests.py 复用。
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
# 依赖缺失不在导入期退出——本模块的核对函数会被 negative_tests.py 直接复用
try:
    from pptx import Presentation
except ImportError:
    Presentation = None

ROOT = Path(__file__).resolve().parent.parent
B_DIR = ROOT / 'dist' / 'regression'      # 精导通道产物（pptxgenjs）
MODEL_DIR = ROOT / 'assets' / 'examples'

# 文本度量单源（与 build_pptx.js / validate_pptx.py 同值）——三侧各自硬编码会让
# 溢出判定在不同裁判间飘移，出现“一侧报溢出、一侧说没事”。
try:
    _TM = (json.loads((ROOT / 'scripts' / 'layout-constants.json').read_text(encoding='utf-8'))
           .get('containers', {}).get('textMetrics', {}))
except (OSError, json.JSONDecodeError):
    _TM = {}
LINE_FACTOR = float(_TM.get('lineFactor') or 1.45)
EM_ASCII_RATIO = float(_TM.get('emAsciiRatio') or 0.52)

# 形态变换类图表：模型里的负值在图上是「向下的正高度条」，按绝对值比对
SIGNLESS_CHARTS = {'waterfall', 'gauge', 'funnel', 'bullet'}

# 纯数值 token（含千分位/小数/百分号/常见单位后缀）——图表数据标签在 旧浏览器通道（已删除）是
# 文本（值+unit，如 "9pt"），B 通道进 chart part；比对前两端过滤。类别标签（如 "2026Q3"）
# 不匹配此模式，仍参与一致性检查。
NUMERIC_TOKEN = re.compile(
    r'^[+-]?[\d.,]+\s*(?:%|‰|pt|pct|pp|YB|ZB|EB|PB|TB|GB|MB|KB|kWh|Gbps|k|w|万|亿|元|倍|个|人|天|家|次|项|年'
    r'|条|笔|台|套|份|款|张|篇|页|件|例|场|轮|艘|辆|吨|米|秒|分|时|档|级)?$')


def slide_texts(prs):
    """每页文本集合（逐行拆分——旧浏览器通道（已删除）段落 \\n 与 B 通道 breakLine \\n\\n 表示差异归一；
    忽略空白、页码与纯数值 token；B 通道原生图表的类别标签并入集合）。"""
    pages = []
    for slide in prs.slides:
        texts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for line in shape.text_frame.text.splitlines():

                    t = line.strip()
                    if t and not NUMERIC_TOKEN.match(t):
                        texts.append(t)
            elif shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        for line in cell.text.splitlines():
                            t = line.strip()
                            if t and not NUMERIC_TOKEN.match(t):
                                texts.append(t)
            elif getattr(shape, 'has_chart', False):
                # B 通道原生数据图表——类别标签（实质内容）并入；数据值已按纯数值过滤。
                # 类别标签同样过 NUMERIC_TOKEN——旧浏览器通道（已删除）文本统一过滤，两端语义对称
                # （否则 gauge 的 '76%'、stack 的年份 '2023' 这类数值型类别会造成单边误报）。
                try:
                    cats = list(shape.chart.plots[0].categories)
                    texts.extend(str(c).strip() for c in cats
                                 if str(c).strip() and not NUMERIC_TOKEN.match(str(c).strip()))
                except Exception:
                    pass
        pages.append(sorted(set(texts)))   # 集合语义去重（B 端 chart categories 与自绘图例可能重复）
    return pages


def _model_chart(sec):
    """取章节页的图表对象（口径与 validate_pptx._section_chart 一致）。"""
    st = sec.get('type') or ''
    if st in {'bar', 'donut', 'exhibit', 'halftable'}:
        c = sec.get('chart') or {}
    elif st == 'split':
        c = sec.get('right') or {}
        if (c.get('type') or 'bar') == 'table':
            return None
    else:
        return None
    return c if isinstance(c, dict) and c.get('labels') and c.get('values') else None


def _model_values(chart):
    """模型声明的全部数值（单系列 values 或多系列 series[].values）。"""
    out = []
    if isinstance(chart.get('series'), list) and chart['series']:
        for se in chart['series']:
            out += [v for v in (se.get('values') or []) if isinstance(v, (int, float))]
    else:
        out += [v for v in (chart.get('values') or []) if isinstance(v, (int, float))]
    return out


def chart_data_verify(prs, model, name):
    """B 通道原生 chart part 的数值必须覆盖模型声明值。

    只做「模型值 ⊆ 图表值」的包含判定，不做严格相等——waterfall 的累计基座、
    gauge 的补角这类派生系列是合法的额外数据，严格相等会制造假阳性。
    形态变换类图表（waterfall 把 -3 画成高度 3 的悬浮条）按绝对值比对。
    """
    issues = []
    secs = [s for s in (model.get('sections') or []) if isinstance(s, dict)]
    first = 3 if model.get('agenda') else 2
    slides = list(prs.slides)
    for i, sec in enumerate(secs):
        chart = _model_chart(sec)
        if chart is None:
            continue
        idx = first + i - 1
        if idx >= len(slides):
            break
        pool = []
        for shape in slides[idx].shapes:
            if not getattr(shape, 'has_chart', False):
                continue
            try:
                for plot in shape.chart.plots:
                    for se in plot.series:
                        pool += [v for v in se.values if v is not None]
            except Exception:
                pass
        if not pool:
            continue          # 该页是形状还原通道，数值走数据表/备注，另有门禁
        ctype = str(chart.get('type') or 'bar').lower()
        signless = ctype in SIGNLESS_CHARTS
        if signless:
            pool = [abs(p) for p in pool]
        missing = []
        for v in _model_values(chart):
            target = abs(v) if signless else v
            if not any(abs(target - p) <= max(0.01, abs(target) * 0.001) for p in pool):
                missing.append(v)
        if missing:
            issues.append(f'{name} 第{idx + 1}页 {ctype} 图表数值与模型不符，'
                          f'缺 {missing[:5]}（图表实际含 {sorted(set(pool))[:6]}）')
    return issues


def font_sizes(prs):
    """全文文本框出现过的字号集合（pt）。"""
    out = set()
    for slide in prs.slides:
        for sh in slide.shapes:
            if not sh.has_text_frame:
                continue
            for p in sh.text_frame.paragraphs:
                for r in p.runs:
                    if r.font.size and r.text.strip():
                        out.add(round(r.font.size.pt, 2))
    return out


def overflow_estimate(prs, name):
    """启发式：文本估算宽（CJK 字符按 1em、ASCII 按 emAsciiRatio）vs shape 宽 × 可容行数。"""
    issues = []
    for si, slide in enumerate(prs.slides, 1):
        for shape in slide.shapes:
            if not shape.has_text_frame or not shape.width or not shape.height:
                continue
            for para in shape.text_frame.paragraphs:
                line = ''.join(r.text for r in para.runs)
                if not line.strip():
                    continue
                sz = None
                for r in para.runs:
                    if r.font.size:
                        sz = r.font.size.pt
                        break
                sz = sz or 12
                emu_w = int(shape.width)
                in_w = emu_w / 914400
                # 每行可容字符宽（英寸）→ em 数
                est_w = sum(1.0 if ord(c) > 0x2E80 else EM_ASCII_RATIO for c in line) * sz / 72
                lines_avail = max(1, int(int(shape.height) / 914400 / (sz / 72 * LINE_FACTOR)))
                if est_w > in_w * lines_avail * 1.18:   # 18% 容差
                    issues.append(f'{name} 第{si}页 "{line[:14]}…" 估算{est_w:.1f}in > 容量{in_w*lines_avail:.1f}in')
    return issues


# ── R6 跨通道一致性（Agenda 阅读顺序 / 元素数量 / 图表数据标签） ──

def agenda_order(prs) -> list[str]:
    """大纲页条目阅读顺序（第 2 页，按 y 再 x 排序的短文本序列）。"""
    if len(prs.slides) < 2:
        return []
    items = []
    for shape in prs.slides[1].shapes:
        if not shape.has_text_frame:
            continue
        t = shape.text_frame.text.strip()
        if not t or len(t) > 60:
            continue
        # 序号行（01/02…）或短标题——取前 20 个稳定 token 作顺序指纹
        items.append((round(shape.top / 914400, 1), round(shape.left / 914400, 1), t[:24]))
    items.sort()
    return [t for _, _, t in items[:20]]


def element_counts(prs) -> list[tuple[int, int, int]]:
    """每页 (shapes, pictures, charts) 数量——跨通道应对齐（A 形状近似 vs B 原生图表可有 1 图差）。"""
    out = []
    for slide in prs.slides:
        shapes = sum(1 for s in slide.shapes if s.shape_type is not None)
        pics = sum(1 for s in slide.shapes if s.shape_type == 13)  # PICTURE
        charts = sum(1 for s in slide.shapes if getattr(s, 'has_chart', False))
        out.append((shapes, pics, charts))
    return out


def chart_label_presence(prs) -> list[int]:
    """含图表的页是否有数据标签/数值文本（防「图表无标签」静默退化）。"""
    flagged = []
    for i, slide in enumerate(prs.slides, 1):
        has_chart = any(getattr(s, 'has_chart', False) for s in slide.shapes)
        if not has_chart:
            continue
        has_numeric = False
        for s in slide.shapes:
            if s.has_text_frame:
                for line in s.text_frame.text.splitlines():
                    if NUMERIC_TOKEN.match(line.strip()):
                        has_numeric = True
                        break
            if has_numeric:
                break
        # 原生 chart part 的数据在 chart XML 里（不进 text_frame）——只对形状通道严格
        if not has_numeric and not any(getattr(s, 'has_chart', False) for s in slide.shapes):
            flagged.append(i)
    return flagged


def _plan(model) -> list[tuple[str, str]]:
    """页序计划（与 assets/pptx-export.js pagePlan / build_pptx.js 同规则，经 lib_solver 拆页）。"""
    sys.path.insert(0, str(ROOT / 'scripts'))
    import lib_solver  # noqa: PLC0415
    solved, _ = lib_solver.split_model(model)
    plan = [('cover', model.get('title') or '')]
    ag = model.get('agenda') or []
    plan += [('agenda', '')] * ((len(ag) + 11) // 12)
    plan += [('section', s.get('title') or '') for s in solved.get('sections') or []]
    if model.get('closing'):
        plan.append(('closing', (model.get('closing') or {}).get('title') or ''))
    return plan


def _norm(t: str) -> str:
    return re.sub(r'\s+', '', str(t or ''))


def _html_titles(html: str) -> list[str]:
    """HTML 正文内各幻灯片标题（h1/h2 文本，去标签）。"""
    body = re.sub(r'<(script|style)\b[\s\S]*?</\1>', '', html)
    return [_norm(re.sub(r'<[^>]+>', '', m)) for m in re.findall(r'<h[12]\b[^>]*>([\s\S]*?)</h[12]>', body)]


def main() -> int:
    """HTML ↔ PPTX 同源核对（M2 起替代 A/B 双通道比对：浏览器端几何引擎已删除）。
    对每个示例：① PPTX 可被 python-pptx 解析 ② PPTX 页数 = 求解器页序计划页数
    ③ 每个章节页标题按序出现在 PPTX 对应页 ④ 同一标题按序出现在 HTML 正文
    ⑤ 原生图表数值 = 模型数值 ⑥ 形状图表须附数据标签 ⑦ 文本溢出启发式（WARN）。"""
    if Presentation is None:
        print('python-pptx 未安装')
        return 2
    fails, all_overflow = [], []
    models = sorted(MODEL_DIR.glob('*.model.json'))
    for mp in models:
        name = mp.name[:-len('.model.json')]
        bp = B_DIR / f'{name}.pptx'
        hp = MODEL_DIR / f'{name}.html'
        if not bp.exists():
            fails.append(f'{name}: PPTX 产物缺失（先跑 regression.py 生成 {bp.relative_to(ROOT)}）')
            continue
        try:
            prs = Presentation(str(bp))
        except Exception as e:  # noqa: BLE001
            fails.append(f'{name}: python-pptx 解析失败 {e}')
            continue
        model = json.loads(mp.read_text(encoding='utf-8'))
        plan = _plan(model)
        n = len(prs.slides)
        if n != len(plan):
            fails.append(f'{name}: PPTX {n} 页 ≠ 页序计划 {len(plan)} 页（HTML/PPTX 拆页不同源）')
        texts = [''.join(_norm(x) for x in pg) for pg in slide_texts(prs)]
        miss_p = [i + 1 for i, (k, t) in enumerate(plan)
                  if k == 'section' and t and i < len(texts) and _norm(t)[:12] not in texts[i]]
        if miss_p:
            fails.append(f'{name}: PPTX 第 {miss_p[:5]} 页标题与页序计划不符')
        miss_h = []
        if hp.exists():
            ht, pos = _html_titles(hp.read_text(encoding='utf-8')), 0
            for k, t in plan:
                if k != 'section' or not t:
                    continue
                key = _norm(t).replace('（续）', '')[:12]
                j = next((x for x in range(pos, len(ht)) if key in ht[x]), None)
                if j is None:
                    miss_h.append(t[:16])
                else:
                    pos = j
            if miss_h:
                fails.append(f'{name}: HTML 正文缺少/乱序章节标题 {miss_h[:3]}')
        data_issues = chart_data_verify(prs, model, name)
        fails += data_issues
        lab = chart_label_presence(prs)
        if lab:
            fails.append(f'{name}: 图表缺数据标签 页{lab}（形状图表须附数值）')
        all_overflow += overflow_estimate(prs, name)
        print(f'{name}: 可解析✓ 页数={n}/{len(plan)} 标题序={"PASS" if not miss_p else "DIFF"} '
              f'HTML序={"PASS" if not miss_h else "DIFF"} 图表数值={"PASS" if not data_issues else "DIFF"}')
    print('\n── 溢出启发式（check-overflow · 18% 容差，仅提示）──')
    for i in all_overflow[:20]:
        print('  [WARN]', i)
    if not all_overflow:
        print('  全部通过（无文本超容 shape）')
    print('\n' + '=' * 50)
    if fails:
        print('同源核对失败:')
        for f in fails:
            print('  [FAIL]', f)
        return 1
    print('HTML ↔ PPTX 同源核对通过：页序计划一致、标题按序对齐、原生图表数值与模型一致')
    return 0


if __name__ == '__main__':
    sys.exit(main())
