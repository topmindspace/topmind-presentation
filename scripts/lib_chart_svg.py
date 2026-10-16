#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""topmind-presentation · HTML 图表引擎（M3，唯一 HTML 图表实现）

数据驱动：输入 REPORT_MODEL 的 chart 字典（或信息图页 section），输出零外链内联 SVG。
与 PPTX 端（build_pptx.js）同一份数据、同一配色规则、同一标注层语义：

配色规则（references/charts-discipline.md）：
  · 单系列只用主色（f-acc）；声明了高亮时，被强调项主色实底、其余主色色调（f-accs2）；
  · 多系列从分类色板 c1..c5 依次取色，最多 6 色；负值用语义色 f-neg；
标注层（chart.annotations[] + chart.dataLabels）：
  · {"type":"target","value":60,"label":"目标"}   目标线
  · {"type":"highlight","index":2} / {"label":"Q4"}  高亮项（未声明 = 不高亮，单系列统一主色）
  · {"type":"note","index":3,"text":"新平台上线"}   注释气泡
  · dataLabels: "all"（默认）| "ends"（首尾）| "extreme"（极值）| "none"
图表皮肤（风格库 chartSkin）：grid（是否画网格线）、radius（柱圆角）。

只依赖标准库；所有坐标确定性计算（同输入同输出，便于金样）。
"""
from __future__ import annotations

import math
from html import escape as _esc

W, H = 900, 340


def esc(s) -> str:
    return _esc(str(s if s is not None else ''), quote=True)


def num(v) -> str:
    """数字显示：整数不带小数，千分位。"""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return esc(v)
    if abs(f - round(f)) < 1e-9:
        return f'{int(round(f)):,}'
    return f'{f:,.1f}'


def _f(x: float) -> str:
    return f'{x:.1f}'.rstrip('0').rstrip('.') if '.' in f'{x:.1f}' else f'{x:.1f}'


def _svg(kind: str, body: list, w=W, h=H, extra_cls='') -> str:
    cls = 'chart' + (f' {extra_cls}' if extra_cls else '')
    return (f'<svg class="{cls}" data-chart="{esc(kind)}" viewBox="0 0 {w} {h}" '
            f'role="img" preserveAspectRatio="xMidYMid meet">\n        '
            + '\n        '.join(body) + '\n      </svg>')


def _txt(x, y, s, cls='f-txt3', size=13, anchor='middle', weight=None, extra='') -> str:
    w = f' font-weight="{weight}"' if weight else ''
    return (f'<text x="{_f(x)}" y="{_f(y)}" text-anchor="{anchor}" class="{cls}" '
            f'font-size="{size}"{w}{extra}>{esc(s)}</text>')


def _vals(ch, key='values'):
    out = []
    for v in ch.get(key) or []:
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            out.append(0.0)
    return out


def highlight_set(ch, n) -> set:
    labels = [str(x) for x in (ch.get('labels') or [])]
    hs = set()
    declared = False
    for a in ch.get('annotations') or []:
        if not isinstance(a, dict) or a.get('type') != 'highlight':
            continue
        declared = True
        if isinstance(a.get('index'), int) and 0 <= a['index'] < n:
            hs.add(a['index'])
        elif a.get('label') is not None and str(a['label']) in labels:
            hs.add(labels.index(str(a['label'])))
    if not declared and isinstance(ch.get('highlight'), int):
        hs.add(ch['highlight'])
        declared = True
    return hs


def label_mask(ch, values) -> list:
    mode = (ch.get('dataLabels') or 'all').lower()
    n = len(values)
    if mode == 'none':
        return [False] * n
    if mode == 'ends':
        return [i in (0, n - 1) for i in range(n)]
    if mode == 'extreme':
        if not values:
            return []
        hi, lo = values.index(max(values)), values.index(min(values))
        return [i in (hi, lo, n - 1) for i in range(n)]
    return [True] * n


def _targets(ch):
    return [a for a in (ch.get('annotations') or []) if isinstance(a, dict) and a.get('type') == 'target'
            and a.get('value') is not None]


def _notes(ch):
    return [a for a in (ch.get('annotations') or []) if isinstance(a, dict) and a.get('type') == 'note'
            and a.get('text')]


def _note_bubble(x, y, text, w=W) -> list:
    tw = min(260, 14 * len(str(text)) + 24)
    bx = min(max(x - tw / 2, 8), w - tw - 8)
    by = max(y - 46, 4)
    return [f'<rect x="{_f(bx)}" y="{_f(by)}" width="{_f(tw)}" height="28" rx="14" class="f-accs"/>',
            f'<line x1="{_f(x)}" y1="{_f(by + 28)}" x2="{_f(x)}" y2="{_f(y - 4)}" class="s-acc" stroke-width="1.5"/>',
            _txt(bx + tw / 2, by + 19, text, 'f-txt', 12.5, weight=600)]


def _nice_max(vmax: float) -> float:
    if vmax <= 0:
        return 1.0
    e = 10 ** math.floor(math.log10(vmax))
    for m in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m * e >= vmax * 1.08:
            return m * e
    return 10 * e


def _grid(x0, x1, y0, y1, vmax, skin, unit='', ticks=4) -> list:
    out = []
    if not (skin or {}).get('grid', True):
        out.append(f'<line x1="{x0}" y1="{_f(y1)}" x2="{x1}" y2="{_f(y1)}" class="s-bd" stroke-width="1"/>')
        return out
    for k in range(ticks + 1):
        y = y1 - (y1 - y0) * k / ticks
        cls = 's-bd' if k == 0 else 's-bds'
        out.append(f'<line x1="{x0}" y1="{_f(y)}" x2="{x1}" y2="{_f(y)}" class="{cls}" stroke-width="1"/>')
        out.append(_txt(x0 - 10, y + 4, num(vmax * k / ticks), 'f-txt3', 11.5, 'end'))
    return out


# ── 核心图表 ────────────────────────────────────────────────────────────────
def grouped(ch, skin=None, w=W, h=H):
    """多系列分组柱：系列色 c1..c5，顶部图例；与 PPTX 原生簇状柱同一份数据。"""
    labels = list(ch.get('labels') or [])
    series = [s for s in (ch.get('series') or []) if isinstance(s, dict)][:6]
    unit = ch.get('unit') or ''
    allv = [float(v) for s in series for v in (s.get('values') or []) if v is not None]
    vmax = float(ch.get('max') or 0) or _nice_max(max(allv + [t['value'] for t in _targets(ch)] + [0]))
    x0, x1, y0, y1 = 64, w - 24, 52, h - 46
    body = _grid(x0, x1, y0, y1, vmax, skin)
    n, k = max(1, len(labels)), max(1, len(series))
    step = (x1 - x0) / n
    gw = min(150, step * 0.72)
    bw = gw / k
    rad = min(4, (skin or {}).get('radius', 6))
    for si, s in enumerate(series):
        cls = f'f-c{si % 5 + 1}'
        lx = x0 + si * 120
        body.append(f'<rect x="{_f(lx)}" y="12" width="12" height="12" rx="3" class="{cls}"/>')
        body.append(_txt(lx + 18, 22, s.get('name') or '', 'f-txt2', 12.5, 'start'))
        for i, v in enumerate(s.get('values') or []):
            if v is None or i >= n:
                continue
            hgt = max(0.0, float(v) / vmax * (y1 - y0))
            x = x0 + i * step + (step - gw) / 2 + si * bw
            body.append(f'<rect data-anim="grow" x="{_f(x + 1)}" y="{_f(y1 - hgt)}" width="{_f(bw - 2)}" height="{_f(hgt)}" '
                        f'rx="{rad}" class="{cls}"><title>{esc(s.get("name") or "")} {esc(labels[i] if i < len(labels) else "")} '
                        f'{num(v)}{esc(unit)}</title></rect>')
            body.append(_txt(x + bw / 2, y1 - hgt - 6, f'{num(v)}', 'f-txt2', 11.5, weight=600))
    for i, lb in enumerate(labels):
        body.append(_txt(x0 + i * step + step / 2, y1 + 24, lb, 'f-txt2', 13))
    body += _target_lines(ch, x0, x1, y0, y1, vmax)
    return _svg('bar', body, w, h)


def bar(ch, skin=None, w=W, h=H):
    if len([s for s in (ch.get('series') or []) if isinstance(s, dict)]) >= 2:
        return grouped(ch, skin, w, h)
    labels, values = list(ch.get('labels') or []), _vals(ch)
    n = max(1, len(values))
    unit = ch.get('unit') or ''
    vmax = float(ch.get('max') or 0) or _nice_max(max(values + [t['value'] for t in _targets(ch)] + [0]))
    x0, x1, y0, y1 = 64, w - 24, 40, h - 46
    body = _grid(x0, x1, y0, y1, vmax, skin)
    step = (x1 - x0) / n
    bw = min(96, step * 0.56)
    rad = (skin or {}).get('radius', 6)
    hs, mask = highlight_set(ch, n), label_mask(ch, values)
    for i, (lb, v) in enumerate(zip(labels, values)):
        hgt = max(0.0, abs(v) / vmax * (y1 - y0))
        x = x0 + i * step + (step - bw) / 2
        y = y1 - hgt if v >= 0 else y1
        cls = 'f-neg' if v < 0 else ('f-acc' if (i in hs or not hs) else 'f-accs2')
        body.append(f'<rect data-anim="grow" x="{_f(x)}" y="{_f(y)}" width="{_f(bw)}" height="{_f(hgt)}" '
                    f'rx="{rad}" class="{cls}"><title>{esc(lb)} {num(v)}{esc(unit)}</title></rect>')
        body.append(_txt(x + bw / 2, y1 + 24, lb, 'f-txt2', 13))
        if mask[i]:
            ly = (y if v >= 0 else y + hgt + 16) - 8
            if v >= 0:
                ly = _avoid(ly, ch, y0, y1, vmax)
            body.append(_txt(x + bw / 2, ly, f'{num(v)}{unit}',
                             'f-txt' if i in hs else 'f-txt2', 14, weight=600, extra=' data-anim="fade"'))
    body += _target_lines(ch, x0, x1, y0, y1, vmax)
    for a in _notes(ch):
        i = a.get('index', n - 1)
        if 0 <= i < n:
            v = values[i]
            body += _note_bubble(x0 + i * step + step / 2, y1 - abs(v) / vmax * (y1 - y0) - 26, a['text'], w)
    return _svg('bar', body, w, h)


def _avoid(ly, ch, y0, y1, vmax, size=14):
    """数值标签避让目标线：标签文字盒 [ly-size, ly+3] 与任一目标线相交时，整体抬到线上方。"""
    for t in _targets(ch):
        ty = y1 - float(t['value']) / vmax * (y1 - y0)
        if ly - size - 2 <= ty <= ly + 4:
            ly = ty - 7
    return max(y0 - 22 + size, ly)


def _target_lines(ch, x0, x1, y0, y1, vmax) -> list:
    out = []
    for t in _targets(ch):
        y = y1 - float(t['value']) / vmax * (y1 - y0)
        out.append(f'<line x1="{x0}" y1="{_f(y)}" x2="{x1}" y2="{_f(y)}" class="s-acc" '
                   f'stroke-width="1.5" stroke-dasharray="6 5"/>')
        # 标签放在左端：末项通常是最高柱（数值标签在右上），左端最不易相撞；label 自带数字时不再重复数值
        lab = str(t.get('label') or '目标')
        if not any(c.isdigit() for c in lab):
            lab = f'{lab} {num(t["value"])}{ch.get("unit") or ""}'
        out.append(_txt(x0 + 6, y - 8, lab, 'f-acc', 12.5, 'start', 600))
    return out


def hbar(ch, skin=None, w=W, h=H):
    labels, values = list(ch.get('labels') or []), _vals(ch)
    n = max(1, len(values))
    unit = ch.get('unit') or ''
    vmax = float(ch.get('max') or 0) or _nice_max(max(values + [0]))
    lw = min(200, 24 + 15 * max((len(str(x)) for x in labels), default=4))
    x0, x1, y0, y1 = lw, w - 90, 18, h - 18
    step = (y1 - y0) / n
    bh = min(44, step * 0.58)
    hs, mask = highlight_set(ch, n), label_mask(ch, values)
    body = []
    rad = (skin or {}).get('radius', 6)
    for i, (lb, v) in enumerate(zip(labels, values)):
        y = y0 + i * step + (step - bh) / 2
        bwid = max(0.0, v / vmax * (x1 - x0))
        body.append(f'<rect x="{x0}" y="{_f(y)}" width="{_f(x1 - x0)}" height="{_f(bh)}" rx="{rad}" class="f-s2"/>')
        cls = 'f-neg' if v < 0 else ('f-acc' if (i in hs or not hs) else 'f-accs2')
        body.append(f'<rect data-anim="grow" x="{x0}" y="{_f(y)}" width="{_f(bwid)}" height="{_f(bh)}" rx="{rad}" '
                    f'class="{cls}"><title>{esc(lb)} {num(v)}{esc(unit)}</title></rect>')
        body.append(_txt(x0 - 14, y + bh / 2 + 5, lb, 'f-txt2', 14, 'end', 500))
        if mask[i]:
            body.append(_txt(x0 + bwid + 10, y + bh / 2 + 5, f'{num(v)}{unit}',
                             'f-txt' if i in hs else 'f-txt2', 14, 'start', 600))
    for t in _targets(ch):
        x = x0 + float(t['value']) / vmax * (x1 - x0)
        body.append(f'<line x1="{_f(x)}" y1="{y0 - 6}" x2="{_f(x)}" y2="{y1 + 2}" class="s-acc" stroke-width="1.5" stroke-dasharray="6 5"/>')
        body.append(_txt(x + 6, y1 + 14, f'{t.get("label") or "目标"} {num(t["value"])}{unit}', 'f-acc', 12, 'start', 600))
    return _svg('hbar', body, w, h, 'chart--x')


def line(ch, skin=None, w=W, h=H, area=False):
    labels = list(ch.get('labels') or [])
    series = ch.get('series') or [{'name': ch.get('name') or '', 'values': ch.get('values') or []}]
    allv = [float(v) for s in series for v in (s.get('values') or [])]
    vmax = float(ch.get('max') or 0) or _nice_max(max(allv + [t['value'] for t in _targets(ch)] + [0]))
    x0, x1, y0, y1 = 64, w - 40, 40, h - 46
    body = _grid(x0, x1, y0, y1, vmax, skin)
    n = max(2, len(labels))
    xs = [x0 + (x1 - x0) * i / (n - 1) for i in range(len(labels))]
    for i, lb in enumerate(labels):
        body.append(_txt(xs[i], y1 + 24, lb, 'f-txt2', 13))
    multi = len(series) > 1
    for si, s in enumerate(series[:6]):
        vals = _vals(s)
        pts = [(xs[i], y1 - v / vmax * (y1 - y0)) for i, v in enumerate(vals[:len(xs)])]
        if not pts:
            continue
        col = f'c{si % 5 + 1}' if multi else 'acc'
        d = 'M' + ' L'.join(f'{_f(x)},{_f(y)}' for x, y in pts)
        if area:
            body.append(f'<path d="{d} L{_f(pts[-1][0])},{y1} L{_f(pts[0][0])},{y1} Z" class="f-{col if multi else "accs"}" opacity="{0.55 if multi else 1}"/>')
        body.append(f'<path d="{d}" fill="none" class="s-{col}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>')
        mask = label_mask(ch if not multi else {'dataLabels': 'ends'}, vals)
        for i, (x, y) in enumerate(pts):
            body.append(f'<circle cx="{_f(x)}" cy="{_f(y)}" r="5" class="f-{col if multi else "acc"}"/>')
            if mask[i]:
                body.append(_txt(x, _avoid(y - 12, ch, y0, y1, vmax, 13), f'{num(vals[i])}{ch.get("unit") or ""}', 'f-txt', 13, weight=600))
        if multi and s.get('name'):
            body.append(_txt(pts[-1][0] + 8, pts[-1][1] + 4, s['name'], 'f-txt2', 12, 'start', 600))
    body += _target_lines(ch, x0, x1, y0, y1, vmax)
    for a in _notes(ch):
        i = a.get('index', len(xs) - 1)
        if 0 <= i < len(xs):
            v = _vals(series[0])[i]
            body += _note_bubble(xs[i], y1 - v / vmax * (y1 - y0) - 14, a['text'], w)
    return _svg('area' if area else 'line', body, w, h)


def stack(ch, skin=None, w=W, h=H):
    labels = list(ch.get('labels') or [])
    series = ch.get('series') or []
    if not series:
        return bar(ch, skin, w, h)
    tot = [sum(float((s.get('values') or [0] * len(labels))[i]) for s in series) for i in range(len(labels))]
    vmax = float(ch.get('max') or 0) or _nice_max(max(tot + [0]))
    x0, x1, y0, y1 = 64, w - 150, 30, h - 46
    body = _grid(x0, x1, y0, y1, vmax, skin)
    n = max(1, len(labels))
    step = (x1 - x0) / n
    bw = min(90, step * 0.56)
    for i, lb in enumerate(labels):
        acc = y1
        x = x0 + i * step + (step - bw) / 2
        for si, s in enumerate(series[:6]):
            v = float((s.get('values') or [0] * n)[i])
            hh = v / vmax * (y1 - y0)
            body.append(f'<rect x="{_f(x)}" y="{_f(acc - hh)}" width="{_f(bw)}" height="{_f(hh)}" class="f-c{si % 5 + 1}">'
                        f'<title>{esc(s.get("name"))} {esc(lb)} {num(v)}</title></rect>')
            if hh > 22:
                body.append(_txt(x + bw / 2, acc - hh / 2 + 5, num(v), 't-on-inv', 12, weight=600))
            acc -= hh
        body.append(_txt(x + bw / 2, y1 + 24, lb, 'f-txt2', 13))
    body += _legend(series, x1 + 24, y0 + 10)
    return _svg('stack', body, w, h)


def _legend(series, x, y, dy=26) -> list:
    out = []
    for si, s in enumerate(series[:6]):
        name = s.get('name') if isinstance(s, dict) else s
        out.append(f'<rect x="{x}" y="{y + si * dy - 10}" width="12" height="12" rx="3" class="f-c{si % 5 + 1}"/>')
        out.append(_txt(x + 20, y + si * dy, name, 'f-txt2', 13, 'start'))
    return out


def donut(ch, skin=None, w=W, h=H, pie=False):
    labels, values = list(ch.get('labels') or []), _vals(ch)
    total = sum(values) or 1
    cx, cy, r = h / 2 + 30, h / 2, h / 2 - 22
    ri = 0 if pie else r * 0.6
    body, a0 = [], -math.pi / 2
    for i, v in enumerate(values):
        a1 = a0 + v / total * 2 * math.pi
        large = 1 if a1 - a0 > math.pi else 0
        p = lambda a, rr: (cx + rr * math.cos(a), cy + rr * math.sin(a))
        (xa, ya), (xb, yb) = p(a0, r), p(a1, r)
        if ri:
            (xc, yc), (xd, yd) = p(a1, ri), p(a0, ri)
            d = (f'M{_f(xa)},{_f(ya)} A{_f(r)},{_f(r)} 0 {large} 1 {_f(xb)},{_f(yb)} '
                 f'L{_f(xc)},{_f(yc)} A{_f(ri)},{_f(ri)} 0 {large} 0 {_f(xd)},{_f(yd)} Z')
        else:
            d = f'M{_f(cx)},{_f(cy)} L{_f(xa)},{_f(ya)} A{_f(r)},{_f(r)} 0 {large} 1 {_f(xb)},{_f(yb)} Z'
        body.append(f'<path d="{d}" class="f-c{i % 5 + 1}" stroke="var(--surface)" stroke-width="2">'
                    f'<title>{esc(labels[i] if i < len(labels) else "")} {num(v)}</title></path>')
        a0 = a1
    if ri:
        if ch.get('centerTotal', True) is not False:   # 美化路由：合计是派生数，原稿没有就不显示
            body.append(_txt(cx, cy + 4, num(total), 'f-txt', 34, weight=700))
        _cl = ch.get('centerLabel', '合计')   # 显式给空串 = 不加中心标签（美化路由不补字）
        if _cl:
            body.append(_txt(cx, cy + 30, _cl, 'f-txt3', 13))
    lx = cx + r + 60
    gap = min(52, (h - 40) / max(1, len(values)))
    y = cy - gap * (len(values) - 1) / 2
    for i, (lb, v) in enumerate(zip(labels, values)):
        yy = y + i * gap
        body.append(f'<rect x="{_f(lx)}" y="{_f(yy - 11)}" width="14" height="14" rx="4" class="f-c{i % 5 + 1}"/>')
        body.append(_txt(lx + 24, yy + 2, lb, 'f-txt', 15, 'start', 600))
        body.append(_txt(w - 30, yy + 2, f'{num(v)}{ch.get("unit") or ""} · {v / total * 100:.0f}%', 'f-txt2', 14, 'end'))
        body.append(f'<line x1="{_f(lx)}" y1="{_f(yy + gap / 2 - 2)}" x2="{w - 30}" y2="{_f(yy + gap / 2 - 2)}" class="s-bds"/>')
    return _svg('pie' if pie else 'donut', body, w, h)


def waterfall(ch, skin=None, w=W, h=H):
    labels, values = list(ch.get('labels') or []), _vals(ch)
    n = len(values)
    unit = ch.get('unit') or ''
    # 首项为基线；末项若等于基线 + 中间增减之和则视为合计柱
    is_total = [i == 0 for i in range(n)]
    if n >= 3 and abs(values[0] + sum(values[1:-1]) - values[-1]) < 1e-6:
        is_total[-1] = True
    run, tops = 0.0, []
    for i, v in enumerate(values):
        if is_total[i]:
            tops.append((0.0, v))
            run = v
        else:
            tops.append((run, run + v))
            run += v
    vmax = _nice_max(max(max(a, b) for a, b in tops) if tops else 1)
    x0, x1, y0, y1 = 64, w - 24, 40, h - 46
    body = _grid(x0, x1, y0, y1, vmax, skin)
    step = (x1 - x0) / max(1, n)
    bw = min(84, step * 0.56)
    Y = lambda v: y1 - v / vmax * (y1 - y0)
    for i, (lb, v) in enumerate(zip(labels, values)):
        a, b = tops[i]
        x = x0 + i * step + (step - bw) / 2
        top, bot = Y(max(a, b)), Y(min(a, b))
        cls = 'f-acc' if is_total[i] else ('f-neg' if v < 0 else 'f-accs2')
        body.append(f'<rect data-anim="grow" x="{_f(x)}" y="{_f(top)}" width="{_f(bw)}" height="{_f(max(1, bot - top))}" '
                    f'rx="4" class="{cls}"><title>{esc(lb)} {num(v)}{esc(unit)}</title></rect>')
        sign = '' if is_total[i] or v < 0 else '+'
        body.append(_txt(x + bw / 2, top - 8, f'{sign}{num(v)}{unit}', 'f-txt', 14, weight=600))
        body.append(_txt(x + bw / 2, y1 + 24, lb, 'f-txt2', 13))
        if i < n - 1:
            body.append(f'<line x1="{_f(x + bw)}" y1="{_f(Y(b))}" x2="{_f(x + step)}" y2="{_f(Y(b))}" '
                        f'class="s-bd" stroke-dasharray="3 3"/>')
    return _svg('waterfall', body, w, h)


def gantt(ch, skin=None, w=W, h=H):
    labels, dur = list(ch.get('labels') or []), _vals(ch)
    start = _vals(ch, 'start') or [sum(dur[:i]) for i in range(len(dur))]
    end = max((s + d for s, d in zip(start, dur)), default=1)
    lw = 150
    x0, x1, y0, y1 = lw, w - 30, 36, h - 14
    n = max(1, len(labels))
    step = (y1 - y0) / n
    bh = min(36, step * 0.56)
    X = lambda v: x0 + v / end * (x1 - x0)
    body = []
    ticks = int(min(10, end))
    for k in range(ticks + 1):
        v = end * k / ticks
        body.append(f'<line x1="{_f(X(v))}" y1="{y0 - 6}" x2="{_f(X(v))}" y2="{y1}" class="s-bds"/>')
        body.append(_txt(X(v), y0 - 14, num(v), 'f-txt3', 11.5))
    hs = highlight_set(ch, n)
    for i, lb in enumerate(labels):
        y = y0 + i * step + (step - bh) / 2
        cls = 'f-acc' if (i in hs or not hs) else 'f-accs2'
        body.append(f'<rect x="{_f(X(start[i]))}" y="{_f(y)}" width="{_f(X(start[i] + dur[i]) - X(start[i]))}" '
                    f'height="{_f(bh)}" rx="{bh / 2:.0f}" class="{cls}"/>')
        body.append(_txt(x0 - 16, y + bh / 2 + 5, lb, 'f-txt', 14, 'end', 600))
        body.append(_txt(X(start[i] + dur[i]) + 10, y + bh / 2 + 5, f'{num(dur[i])}{ch.get("unit") or ""}',
                         'f-txt2', 13, 'start', 600))
    return _svg('gantt', body, w, h, 'chart--x')


def funnel(ch, skin=None, w=W, h=H):
    labels, values = list(ch.get('labels') or []), _vals(ch)
    n = max(1, len(values))
    vmax = max(values + [1])
    cx, y0, y1 = w / 2 - 60, 16, h - 16
    step = (y1 - y0) / n
    body = []
    for i, (lb, v) in enumerate(zip(labels, values)):
        bw = max(60, v / vmax * (w - 320))
        y = y0 + i * step
        cls = 'f-acc' if i == 0 else ('f-accs2' if i < n - 1 else 'f-accs')
        body.append(f'<rect x="{_f(cx - bw / 2)}" y="{_f(y + 3)}" width="{_f(bw)}" height="{_f(step - 6)}" rx="8" class="{cls}"/>')
        body.append(_txt(cx, y + step / 2 + 5, lb, 't-on-inv' if i == 0 else 'f-txt', 14, weight=600))
        conv = f' · {v / values[i - 1] * 100:.0f}%' if i and values[i - 1] else ''
        body.append(_txt(w - 40, y + step / 2 + 5, f'{num(v)}{ch.get("unit") or ""}{conv}', 'f-txt2', 14, 'end', 600))
    return _svg('funnel', body, w, h)


def progress(ch, skin=None, w=W, h=H):
    c = dict(ch)
    c.setdefault('max', 100)
    return hbar(c, skin, w, h)


def vsbar(ch, skin=None, w=W, h=H):
    labels, values = list(ch.get('labels') or []), _vals(ch)
    m = max([abs(v) for v in values] + [1])
    lw = 170
    x0, x1, y0, y1 = lw, w - 40, 14, h - 14
    mid = (x0 + x1) / 2
    n = max(1, len(values))
    step = (y1 - y0) / n
    bh = min(38, step * 0.56)
    body = [f'<line x1="{_f(mid)}" y1="{y0}" x2="{_f(mid)}" y2="{y1}" class="s-bd" stroke-width="1.5"/>']
    for i, (lb, v) in enumerate(zip(labels, values)):
        y = y0 + i * step + (step - bh) / 2
        bwid = abs(v) / m * (x1 - mid - 60)
        x = mid if v >= 0 else mid - bwid
        body.append(f'<rect x="{_f(x)}" y="{_f(y)}" width="{_f(bwid)}" height="{_f(bh)}" rx="5" '
                    f'class="{"f-acc" if v >= 0 else "f-neg"}"/>')
        body.append(_txt(x0 - 14, y + bh / 2 + 5, lb, 'f-txt2', 14, 'end', 500))
        tx = x + bwid + 8 if v >= 0 else x - 8
        body.append(_txt(tx, y + bh / 2 + 5, f'{"+" if v > 0 else ""}{num(v)}{ch.get("unit") or ""}',
                         'f-txt', 13, 'start' if v >= 0 else 'end', 600))
    return _svg('vsbar', body, w, h, 'chart--x')


def rose(ch, skin=None, w=W, h=H):
    labels, values = list(ch.get('labels') or []), _vals(ch)
    n = max(1, len(values))
    vmax = float(ch.get('max') or 0) or max(values + [1])
    cx, cy, R = h / 2 + 20, h / 2, h / 2 - 18
    body = []
    for k in (0.25, 0.5, 0.75, 1):
        body.append(f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(R * k)}" fill="none" class="s-bds"/>')
    order = sorted(range(n), key=lambda i: -values[i])
    for i, v in enumerate(values):
        a0 = -math.pi / 2 + i * 2 * math.pi / n + 0.03
        a1 = a0 + 2 * math.pi / n - 0.06
        r = max(8, v / vmax * R)
        xa, ya = cx + r * math.cos(a0), cy + r * math.sin(a0)
        xb, yb = cx + r * math.cos(a1), cy + r * math.sin(a1)
        cls = 'f-acc' if i == order[0] else 'f-accs2'
        body.append(f'<path d="M{_f(cx)},{_f(cy)} L{_f(xa)},{_f(ya)} A{_f(r)},{_f(r)} 0 0 1 {_f(xb)},{_f(yb)} Z" class="{cls}"/>')
    # 右侧排名面板（与 PPTX rankPanel 同语义）
    lx, gap = cx + R + 70, min(50, (h - 30) / n)
    y = cy - gap * (n - 1) / 2
    for r_, i in enumerate(order):
        yy = y + r_ * gap
        body.append(_txt(lx, yy + 5, f'{r_ + 1:02d}', 'f-acc' if r_ == 0 else 'f-txt3', 14, 'start', 700))
        body.append(_txt(lx + 40, yy + 5, labels[i], 'f-txt', 15, 'start', 600))
        body.append(_txt(w - 30, yy + 5, f'{num(values[i])}{ch.get("unit") or ""}', 'f-txt2', 14, 'end', 600))
    return _svg('rose', body, w, h)


def candlestick(ch, skin=None, w=W, h=H):
    labels = list(ch.get('labels') or [])
    rows = [list(map(float, r)) for r in (ch.get('values') or []) if isinstance(r, (list, tuple)) and len(r) >= 4]
    lo = min((r[2] for r in rows), default=0)
    hi = max((r[1] for r in rows), default=1)
    lo, hi = math.floor(lo / 10) * 10, math.ceil(hi / 10) * 10
    x0, x1, y0, y1 = 64, w - 24, 24, h - 40
    Y = lambda v: y1 - (v - lo) / ((hi - lo) or 1) * (y1 - y0)
    body = []
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        body.append(f'<line x1="{x0}" y1="{_f(Y(v))}" x2="{x1}" y2="{_f(Y(v))}" class="s-bds"/>')
        body.append(_txt(x0 - 10, Y(v) + 4, num(v), 'f-txt3', 11.5, 'end'))
    step = (x1 - x0) / max(1, len(rows))
    bw = min(36, step * 0.5)
    for i, (o, hh, ll, c) in enumerate(rows):
        cx = x0 + i * step + step / 2
        up = c >= o
        # 涨跌不用红绿：阳线主色、阴线浅主色（与 PPTX 同口径）
        cls = 'acc' if up else 'accs2'
        wick = 's-acc' if up else 's-txt3'
        body.append(f'<line x1="{_f(cx)}" y1="{_f(Y(hh))}" x2="{_f(cx)}" y2="{_f(Y(ll))}" class="{wick}" stroke-width="2"/>')
        body.append(f'<rect x="{_f(cx - bw / 2)}" y="{_f(Y(max(o, c)))}" width="{_f(bw)}" '
                    f'height="{_f(max(2, abs(Y(o) - Y(c))))}" rx="3" class="f-{cls}"/>')
        if i < len(labels):
            body.append(_txt(cx, y1 + 22, labels[i], 'f-txt3', 12))
    return _svg('candlestick', body, w, h)


def scatter(ch, skin=None, w=W, h=H, bubble=False):
    pts = [p for p in (ch.get('points') or ch.get('values') or []) if isinstance(p, (list, tuple)) and len(p) >= 2]
    xs, ys = [float(p[0]) for p in pts] or [1], [float(p[1]) for p in pts] or [1]
    xm, ym = _nice_max(max(xs)), _nice_max(max(ys))
    x0, x1, y0, y1 = 64, w - 30, 24, h - 40
    body = _grid(x0, x1, y0, y1, ym, skin)
    for p in pts:
        r = 7 if not bubble or len(p) < 3 else 6 + 22 * math.sqrt(float(p[2]) / max(float(q[2]) for q in pts if len(q) > 2))
        cx, cy = x0 + float(p[0]) / xm * (x1 - x0), y1 - float(p[1]) / ym * (y1 - y0)
        body.append(f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r)}" class="f-acc" opacity=".75"/>')
        if len(p) > 3 or (not bubble and len(p) > 2):
            body.append(_txt(cx, cy - r - 6, p[-1], 'f-txt2', 12))
    return _svg('bubble' if bubble else 'scatter', body, w, h)


CHARTS = {
    'bar': bar, 'column': bar, 'hbar': hbar, 'line': line, 'stackline': line, 'dualline': line,
    'area': lambda c, s=None, w=W, h=H: line(c, s, w, h, area=True),
    'stack': stack, 'donut': donut, 'multidonut': donut, 'radialbar': donut,
    'pie': lambda c, s=None, w=W, h=H: donut(c, s, w, h, pie=True),
    'waterfall': waterfall, 'gantt': gantt, 'funnel': funnel, 'progress': progress, 'vsbar': vsbar,
    'rose': rose, 'candlestick': candlestick, 'scatter': scatter,
    'bubble': lambda c, s=None, w=W, h=H: scatter(c, s, w, h, bubble=True),
    'lollipop': hbar, 'dotplot': hbar, 'bulletchart': hbar, 'dumbbell': hbar, 'slope': line,
    'sparkline': line, 'pareto': bar, 'gauge': progress, 'waffle': donut, 'radar': rose,
}


def chart(ch: dict, skin=None, w=W, h=H) -> str:
    t = str((ch or {}).get('type') or 'bar').lower()
    return CHARTS.get(t, bar)(ch or {}, skin, w, h)


# ── 信息图页（section 级数据）──────────────────────────────────────────────
def sankey(sec, skin=None, w=W, h=H):
    flows = [f for f in (sec.get('flows') or []) if isinstance(f, (list, tuple)) and len(f) >= 3]
    unit = sec.get('unit') or ''
    # 分层：源 → 层号 = 最长前驱链
    nodes, level = [], {}
    for a, b, _ in flows:
        for x in (a, b):
            if x not in nodes:
                nodes.append(x)
    for _ in range(len(nodes)):
        for a, b, _v in flows:
            level[a] = level.get(a, 0)
            level[b] = max(level.get(b, 0), level[a] + 1)
    L = max(level.values(), default=0) + 1
    inflow = {x: 0.0 for x in nodes}
    outflow = {x: 0.0 for x in nodes}
    for a, b, v in flows:
        outflow[a] += float(v)
        inflow[b] += float(v)
    size = {x: max(inflow[x], outflow[x]) for x in nodes}
    cols = [[x for x in nodes if level[x] == k] for k in range(L)]
    pad, nw, x0, x1, y0, y1 = 18, 16, 120, w - 130, 20, h - 20
    scale = min(((y1 - y0) - pad * (len(c) - 1)) / (sum(size[x] for x in c) or 1) for c in cols if c)
    pos = {}
    for k, c in enumerate(cols):
        x = x0 + (x1 - x0) * k / max(1, L - 1)
        tot = sum(size[n] for n in c) * scale + pad * (len(c) - 1)
        y = y0 + ((y1 - y0) - tot) / 2
        for n in c:
            pos[n] = [x, y, size[n] * scale]
            y += size[n] * scale + pad
    off_out = {n: 0.0 for n in nodes}
    off_in = {n: 0.0 for n in nodes}
    lost = {'流失', '流出', '损耗', '退出'}
    body = []
    for a, b, v in flows:
        th = float(v) * scale
        xa, ya = pos[a][0] + nw, pos[a][1] + off_out[a]
        xb, yb = pos[b][0], pos[b][1] + off_in[b]
        off_out[a] += th
        off_in[b] += th
        mx = (xa + xb) / 2
        cls = 'f-s3' if b in lost else 'f-accs2'
        body.append(f'<path d="M{_f(xa)},{_f(ya)} C{_f(mx)},{_f(ya)} {_f(mx)},{_f(yb)} {_f(xb)},{_f(yb)} '
                    f'L{_f(xb)},{_f(yb + th)} C{_f(mx)},{_f(yb + th)} {_f(mx)},{_f(ya + th)} {_f(xa)},{_f(ya + th)} Z" '
                    f'class="{cls}" opacity=".85"><title>{esc(a)} → {esc(b)} {num(v)}{esc(unit)}</title></path>')
        if th >= 14:
            body.append(_txt(mx, (ya + yb) / 2 + th / 2 + 5, f'{num(v)}', 'f-txt', 12.5, weight=600))
    for n in nodes:
        x, y, hh = pos[n]
        body.append(f'<rect x="{_f(x)}" y="{_f(y)}" width="{nw}" height="{_f(max(2, hh))}" rx="3" '
                    f'class="{"f-txt3" if n in lost else "f-acc"}"/>')
        last = level[n] == L - 1
        tx = x + nw + 8 if (last or level[n] > 0) else x - 8
        anchor = 'start' if (last or level[n] > 0) else 'end'
        body.append(_txt(tx, y + hh / 2 + 5, f'{n} {num(size[n])}', 'f-txt', 13.5, anchor, 600))
    return _svg('sankey', body, w, h)


def _squarify(items, x, y, w, h):
    """确定性切片-切块：按面积交替横竖切分（排序后递归二分）。"""
    if not items:
        return []
    if len(items) == 1:
        return [(items[0], x, y, w, h)]
    tot = sum(v for _, v in items)
    acc, k = 0, 0
    for k, (_, v) in enumerate(items):
        acc += v
        if acc >= tot / 2:
            break
    a, b = items[:k + 1], items[k + 1:]
    if not b:
        a, b = items[:1], items[1:]
    fa = sum(v for _, v in a) / tot
    if w >= h:
        return _squarify(a, x, y, w * fa, h) + _squarify(b, x + w * fa, y, w * (1 - fa), h)
    return _squarify(a, x, y, w, h * fa) + _squarify(b, x, y + h * fa, w, h * (1 - fa))


def treemap(sec, skin=None, w=W, h=H):
    items = sorted([(str(i[0]), float(i[1])) for i in (sec.get('items') or []) if isinstance(i, (list, tuple))],
                   key=lambda t: -t[1])
    tot = sum(v for _, v in items) or 1
    body = []
    for idx, ((name, v), x, y, ww, hh) in enumerate(_squarify(items, 0, 0, w, h)):
        cls = ['f-acc', 'f-accs2', 'f-accs2', 'f-accs', 'f-accs'][min(idx, 4)]
        tcls = 't-on-inv' if idx == 0 else 'f-txt'
        body.append(f'<rect x="{_f(x + 2)}" y="{_f(y + 2)}" width="{_f(ww - 4)}" height="{_f(hh - 4)}" rx="10" class="{cls}"/>')
        if ww > 70 and hh > 44:
            body.append(_txt(x + 18, y + 34, name, tcls, 17 if idx == 0 else 15, 'start', 700))
            body.append(_txt(x + 18, y + 58, f'{num(v)}{sec.get("unit") or ""} · {v / tot * 100:.0f}%', tcls, 13, 'start'))
    return _svg('treemap', body, w, h)


def boxplot(sec, skin=None, w=W, h=H):
    groups = [g for g in (sec.get('groups') or []) if isinstance(g, (list, tuple)) and len(g) >= 6]
    lo = math.floor(min((float(g[1]) for g in groups), default=0) / 10) * 10
    hi = math.ceil(max((float(g[5]) for g in groups), default=100) / 10) * 10
    lw = 150
    x0, x1, y0, y1 = lw, w - 120, 20, h - 40
    X = lambda v: x0 + (float(v) - lo) / ((hi - lo) or 1) * (x1 - x0)
    body = []
    for k in range(6):
        v = lo + (hi - lo) * k / 5
        body.append(f'<line x1="{_f(X(v))}" y1="{y0}" x2="{_f(X(v))}" y2="{y1}" class="s-bds"/>')
        body.append(_txt(X(v), y1 + 22, num(v), 'f-txt3', 11.5))
    step = (y1 - y0) / max(1, len(groups))
    bh = min(40, step * 0.5)
    for i, g in enumerate(groups):
        name, mn, q1, md, q3, mx = g[0], *map(float, g[1:6])
        cy = y0 + i * step + step / 2
        body.append(f'<line x1="{_f(X(mn))}" y1="{_f(cy)}" x2="{_f(X(mx))}" y2="{_f(cy)}" class="s-txt3" stroke-width="1.5"/>')
        for v in (mn, mx):
            body.append(f'<line x1="{_f(X(v))}" y1="{_f(cy - bh / 3)}" x2="{_f(X(v))}" y2="{_f(cy + bh / 3)}" class="s-txt3" stroke-width="1.5"/>')
        body.append(f'<rect x="{_f(X(q1))}" y="{_f(cy - bh / 2)}" width="{_f(X(q3) - X(q1))}" height="{_f(bh)}" rx="6" class="f-accs2"/>')
        body.append(f'<line x1="{_f(X(md))}" y1="{_f(cy - bh / 2)}" x2="{_f(X(md))}" y2="{_f(cy + bh / 2)}" class="s-acc" stroke-width="3"/>')
        body.append(_txt(x0 - 16, cy + 5, name, 'f-txt', 14, 'end', 600))
        body.append(_txt(x1 + 16, cy + 5, f'中位 {num(md)}{sec.get("unit") or ""}', 'f-txt2', 13, 'start', 600))
    return _svg('boxplot', body, w, h)


def network(sec, skin=None, w=W, h=H):
    nodes = [n for n in (sec.get('nodes') or []) if isinstance(n, (list, tuple)) and len(n) >= 2]
    edges = [e for e in (sec.get('edges') or []) if isinstance(e, (list, tuple)) and len(e) >= 2]
    deg = {n[0]: 0 for n in nodes}
    for a, b, *_ in edges:
        deg[a] = deg.get(a, 0) + 1
        deg[b] = deg.get(b, 0) + 1
    order = sorted(nodes, key=lambda n: -deg.get(n[0], 0))
    hub, rest = order[0] if order else None, order[1:]
    cx, cy = w / 2, h / 2
    pos = {}
    if hub:
        pos[hub[0]] = (cx, cy)
    for i, n in enumerate(rest):
        a = -math.pi / 2 + i * 2 * math.pi / max(1, len(rest))
        pos[n[0]] = (cx + (w * 0.36) * math.cos(a), cy + (h * 0.36) * math.sin(a))
    body = []
    for a, b, *_ in edges:
        if a in pos and b in pos:
            (xa, ya), (xb, yb) = pos[a], pos[b]
            body.append(f'<line x1="{_f(xa)}" y1="{_f(ya)}" x2="{_f(xb)}" y2="{_f(yb)}" class="s-bd" stroke-width="2"/>')
    for n in nodes:
        x, y = pos[n[0]]
        main = hub and n[0] == hub[0]
        tw = 30 + 15 * len(str(n[1]))
        body.append(f'<rect x="{_f(x - tw / 2)}" y="{_f(y - 22)}" width="{_f(tw)}" height="44" rx="22" '
                    f'class="{"f-acc" if main else "f-accs"}"/>')
        body.append(_txt(x, y + 5, n[1], 't-on-inv' if main else 'f-txt', 15, weight=600))
        body.append(_txt(x, y + 40, f'{deg.get(n[0], 0)} 条连接', 'f-txt3', 11.5))
    return _svg('network', body, w, h)


def marimekko(sec, skin=None, w=W, h=H):
    cols = [c for c in (sec.get('cols') or []) if isinstance(c, (list, tuple)) and len(c) >= 2]
    cells = sec.get('cells') or []
    legend = sec.get('legend') or []
    tot = sum(float(c[1]) for c in cols) or 1
    x0, x1, y0, y1 = 20, w - 150, 16, h - 40
    body, x = [], x0
    for ci, c in enumerate(cols):
        cw = float(c[1]) / tot * (x1 - x0)
        row = [float(v) for v in (cells[ci] if ci < len(cells) else [])]
        s = sum(row) or 1
        y = y0
        for k, v in enumerate(row):
            hh = v / s * (y1 - y0)
            body.append(f'<rect x="{_f(x + 2)}" y="{_f(y + 1)}" width="{_f(cw - 4)}" height="{_f(hh - 2)}" rx="6" '
                        f'class="{"f-acc" if k == 0 else "f-accs2"}"/>')
            body.append(_txt(x + cw / 2, y + hh / 2 + 5, f'{num(v)}%', 't-on-inv' if k == 0 else 'f-txt', 14, weight=600))
            y += hh
        body.append(_txt(x + cw / 2, y1 + 24, f'{c[0]} · 规模 {num(c[1])}', 'f-txt2', 13))
        x += cw
    for k, name in enumerate(legend[:6]):
        body.append(f'<rect x="{x1 + 24}" y="{y0 + 10 + k * 28}" width="14" height="14" rx="4" class="{"f-acc" if k == 0 else "f-accs2"}"/>')
        body.append(_txt(x1 + 46, y0 + 22 + k * 28, name, 'f-txt2', 13, 'start'))
    return _svg('marimekko', body, w, h)


def streamgraph(sec, skin=None, w=W, h=H):
    labels = sec.get('labels') or []
    series = [s for s in (sec.get('series') or []) if isinstance(s, dict)]
    n = len(labels)
    tot = [sum(float((s.get('values') or [0] * n)[i]) for s in series) for i in range(n)]
    m = max(tot + [1])
    x0, x1, y0, y1 = 30, w - 170, 16, h - 40
    mid = (y0 + y1) / 2
    xs = [x0 + (x1 - x0) * i / max(1, n - 1) for i in range(n)]
    base = [mid - t / m * (y1 - y0) / 2 for t in tot]
    body = []
    for si, s in enumerate(series[:6]):
        vals = [float(v) for v in (s.get('values') or [0] * n)]
        top = base[:]
        bot = [top[i] + vals[i] / m * (y1 - y0) for i in range(n)]
        d = 'M' + ' L'.join(f'{_f(xs[i])},{_f(top[i])}' for i in range(n))
        d += ' L' + ' L'.join(f'{_f(xs[i])},{_f(bot[i])}' for i in reversed(range(n))) + ' Z'
        body.append(f'<path d="{d}" class="f-c{si % 5 + 1}" opacity=".9"><title>{esc(s.get("name"))}</title></path>')
        body.append(_txt(xs[-1] + 12, (top[-1] + bot[-1]) / 2 + 5, f'{s.get("name")} {num(vals[-1])}', 'f-txt', 13, 'start', 600))
        base = bot
    for i, lb in enumerate(labels):
        body.append(_txt(xs[i], y1 + 24, lb, 'f-txt2', 13))
    return _svg('streamgraph', body, w, h)


INFO = {'sankey': sankey, 'treemap': treemap, 'boxplot': boxplot, 'network': network,
        'marimekko': marimekko, 'streamgraph': streamgraph}
