#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fill placeholder chart SVGs from REPORT_MODEL (core types for showcase).

Used after render_from_model.py — follows extract_snippet chart patterns
(bar / hbar / line / area / donut / waterfall / stack). Not a public CLI.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from render_from_model import extract_model_span

_ICON_DIR = Path(__file__).resolve().parent.parent / 'assets' / 'icons'
_ICON_CACHE: dict[str, str] = {}


def _icon_svg(name: str) -> str | None:
    """取图标包 SVG（内联用）；缺图标返回 None（调用方保留原标记，由 validate WARN）。"""
    if name in _ICON_CACHE:
        return _ICON_CACHE[name]
    p = _ICON_DIR / f'{name}.svg'
    try:
        svg = p.read_text(encoding='utf-8').strip()
    except OSError:
        return None
    _ICON_CACHE[name] = svg
    return svg


# 手写 HTML 模板里的图标占位：<i data-icon="增长"></i> → 内联 SVG（currentColor 随主题变色）
# 未知图标名保留原标记（validate_report 报 WARN，不静默吞掉）
ICON_MARK_RE = re.compile(r'<i\s+data-icon="([^"]+)"\s*(?:/>|>\s*</i\s*>)')


def hydrate_icons(html: str) -> tuple[str, int, list[str]]:
    """内联 icon 标记。返回 (new_html, 成功替换数, 未知图标名列表)。"""
    unknown: list[str] = []
    replaced = [0]

    def repl(m):
        name = m.group(1)
        svg = _icon_svg(name)
        if svg is None:
            if name not in unknown:
                unknown.append(name)
            return m.group(0)
        replaced[0] += 1  # 只计真正替换的；未知名保留原标记，不计入
        return svg

    new_html, _ = ICON_MARK_RE.subn(repl, html)
    return new_html, replaced[0], unknown

PLACEHOLDER_SVG_RE = re.compile(
    r'<svg class="chart" data-chart="([^"]+)" viewBox="0 0 560 220">\s*'
    r'<!--[\s\S]*?-->\s*'
    r'<text[^>]*>[^<]*见模型数据</text>\s*'
    r'</svg>',
    re.M,
)


def esc(s) -> str:
    return (str(s)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))


def svg_bar(labels, values, max_v=None, unit='') -> str:
    max_v = float(max_v or max(values) * 1.15 or 1)
    n = len(labels)
    gap, left, right, base, top = 24, 60, 540, 170, 30
    usable = right - left
    bw = max(28, (usable - gap * (n - 1)) / n * 0.55)
    step = usable / n
    parts = [f'<line x1="46" y1="{base}" x2="540" y2="{base}" class="s-bds" stroke-width="1"/>']
    for i, (lb, v) in enumerate(zip(labels, values)):
        v = float(v)
        h = (v / max_v) * (base - top)
        x = left + i * step + (step - bw) / 2
        y = base - h
        cls = 'f-acc' if i >= n - 2 else 'f-s3'
        cx = x + bw / 2
        parts.append(
            f'<rect data-anim="grow" x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" '
            f'height="{h:.1f}" rx="6" class="{cls}"><title>{esc(lb)} {v:g}{esc(unit)}</title></rect>'
        )
        parts.append(
            f'<text data-anim="fade" x="{cx:.1f}" y="{base + 22}" text-anchor="middle" '
            f'class="f-txt3" font-size="11">{esc(lb)}</text>'
        )
        parts.append(
            f'<text data-anim="fade" x="{cx:.1f}" y="{y - 8:.1f}" text-anchor="middle" '
            f'class="f-txt2" font-size="12" font-weight="600">{v:g}{esc(unit)}</text>'
        )
    return ('<svg class="chart" data-chart="bar" viewBox="0 0 560 220">\n      '
            + '\n      '.join(parts) + '\n    </svg>')


def svg_hbar(labels, values, max_v=None, unit='') -> str:
    max_v = float(max_v or max(values) or 1)
    n = len(labels)
    row_h = min(36, 180 / max(n, 1))
    y0 = 16
    slot_x, slot_w = 130, 340
    parts = []
    for i, (lb, v) in enumerate(zip(labels, values)):
        v = float(v)
        y = y0 + i * row_h
        w = (v / max_v) * slot_w
        parts.append(f'<text x="0" y="{y + 14:.1f}" class="f-txt2" font-size="12">{esc(lb)}</text>')
        parts.append(
            f'<rect x="{slot_x}" y="{y + 4:.1f}" width="{slot_w}" height="15" rx="7.5" class="f-s2"/>'
        )
        parts.append(
            f'<rect data-anim="grow" x="{slot_x}" y="{y + 4:.1f}" width="{w:.1f}" height="15" '
            f'rx="7.5" class="f-acc"><title>{esc(lb)} {v:g}{esc(unit)}</title></rect>'
        )
        parts.append(
            f'<text x="{slot_x + slot_w + 12}" y="{y + 16:.1f}" class="f-txt" '
            f'font-size="12" font-weight="600">{v:g}{esc(unit)}</text>'
        )
    return ('<svg class="chart" data-chart="hbar" viewBox="0 0 560 220">\n      '
            + '\n      '.join(parts) + '\n    </svg>')


def svg_line(labels, values, max_v=None, unit='', area=False) -> str:
    max_v = float(max_v or max(values) * 1.2 or 1)
    n = len(labels)
    left, right, base, top = 60, 520, 180, 40
    xs = [left + i * (right - left) / max(n - 1, 1) for i in range(n)]
    ys = [base - (float(v) / max_v) * (base - top) for v in values]
    pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in zip(xs, ys))
    path = 'L'.join(f'{x:.1f},{y:.1f}' for x, y in zip(xs, ys))
    path = 'M' + path[1:] if path.startswith('L') else 'M' + path
    # fix: build properly
    path = 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in zip(xs, ys))
    ct = 'area' if area else 'line'
    parts = [
        f'<line x1="46" y1="{base}" x2="540" y2="{base}" class="s-bds" stroke-width="1"/>',
        f'<line x1="46" y1="130" x2="540" y2="130" class="s-bds" stroke-width="1" stroke-dasharray="3 5"/>',
        f'<line x1="46" y1="80" x2="540" y2="80" class="s-bds" stroke-width="1" stroke-dasharray="3 5"/>',
    ]
    if area:
        area_path = path + f' L{xs[-1]:.1f},{base} L{xs[0]:.1f},{base} Z'
        parts.append(f'<path d="{area_path}" class="f-acc" fill-opacity=".12"/>')
    parts.append(
        f'<path data-draw d="{path}" class="f-none s-acc" stroke-width="2.5" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
    )
    for i, (x, y, lb, v) in enumerate(zip(xs, ys, labels, values)):
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" class="f-acc">'
            f'<title>{esc(lb)} · {float(v):g}{esc(unit)}</title></circle>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{base + 20}" text-anchor="middle" '
            f'class="f-txt3" font-size="11">{esc(lb)}</text>'
        )
    return (f'<svg class="chart" data-chart="{ct}" viewBox="0 0 560 220">\n      '
            + '\n      '.join(parts) + '\n    </svg>')


def svg_donut(labels, values, center_label='合计', unit='') -> str:
    total = sum(float(v) for v in values) or 1
    # multi-segment donut: layered sweeps (simplified visual with chips)
    # Use concentric accent arc for first + legend chips for all (presentation craft)
    r, cx, cy, circ = 54, 70, 70, 339.3
    parts = [
        f'<circle cx="{cx}" cy="{cy}" r="{r}" class="f-none s-bds" stroke-width="15"/>'
    ]
    # Draw up to 3 sweeps stacked by offset — for clarity use primary accent for largest
    ordered = sorted(zip(labels, values), key=lambda x: -float(x[1]))
    offset = 0.0
    colors = ['s-acc', 's-txt2', 's-txt3', 's-bds']
    for i, (lb, v) in enumerate(ordered):
        p = float(v) / total
        dash = circ * p
        gap = circ - dash
        rot = -90 + offset * 360
        cls = colors[i % len(colors)]
        parts.append(
            f'<circle data-sweep data-circ="{circ}" data-p="{p:.4f}" cx="{cx}" cy="{cy}" r="{r}" '
            f'class="f-none {cls}" stroke-width="15" stroke-dasharray="{dash:.1f} {gap:.1f}" '
            f'stroke-linecap="butt" transform="rotate({rot:.1f} {cx} {cy})">'
            f'<title>{esc(lb)} {float(v):g}{esc(unit)}</title></circle>'
        )
        offset += p
    top = ordered[0]
    pct = float(top[1]) / total * 100
    parts.append(
        f'<text x="{cx}" y="68" text-anchor="middle" class="f-txt" font-size="22" '
        f'font-weight="600" data-count="{pct:.0f}" data-suffix="%">{pct:.0f}%</text>'
    )
    parts.append(
        f'<text x="{cx}" y="88" text-anchor="middle" class="f-txt3" font-size="11">'
        f'{esc(center_label)}</text>'
    )
    # viewBox larger with legend beside — keep 560x220 and center the donut
    inner = '\n        '.join(parts)
    return (
        f'<svg class="chart" data-chart="donut" viewBox="0 0 560 220">\n'
        f'      <g transform="translate(210,40)">\n        {inner}\n      </g>\n'
        f'    </svg>'
    )


def svg_waterfall(labels, values, unit='') -> str:
    # values: start, deltas..., end (end should equal start+sum(deltas))
    n = len(labels)
    if n < 2:
        return svg_bar(labels, values, unit=unit)
    start = float(values[0])
    end = float(values[-1])
    mids = [float(v) for v in values[1:-1]]
    # running level after each step
    levels = [start]
    cur = start
    for d in mids:
        cur += d
        levels.append(cur)
    levels.append(end)
    max_v = max(levels) * 1.15 or 1
    min_v = min(0, min(levels))
    span = max_v - min_v or 1
    left, right, base, top = 50, 540, 190, 30
    usable = right - left
    bw = min(70, usable / n * 0.55)
    step = usable / n

    def y_of(val):
        return base - ((val - min_v) / span) * (base - top)

    parts = [f'<line x1="40" y1="{base}" x2="540" y2="{base}" class="s-bds" stroke-width="1"/>']
    # start bar
    y1, y0 = y_of(start), base
    h = abs(y0 - y1)
    x = left + (step - bw) / 2
    parts.append(
        f'<rect data-anim="grow" x="{x:.1f}" y="{min(y0,y1):.1f}" width="{bw:.1f}" '
        f'height="{h:.1f}" rx="5" class="f-s3"/>'
    )
    parts.append(
        f'<text x="{x + bw/2:.1f}" y="{min(y0,y1) - 8:.1f}" text-anchor="middle" '
        f'class="f-txt2" font-size="12" font-weight="600">{start:g}{esc(unit)}</text>'
    )
    parts.append(
        f'<text x="{x + bw/2:.1f}" y="{base + 16}" text-anchor="middle" '
        f'class="f-txt3" font-size="11">{esc(labels[0])}</text>'
    )
    prev = start
    for i, d in enumerate(mids):
        idx = i + 1
        nxt = prev + d
        ya, yb = y_of(prev), y_of(nxt)
        x = left + idx * step + (step - bw) / 2
        top_y, bot_y = min(ya, yb), max(ya, yb)
        cls = 'f-acc' if d >= 0 else 'f-txt3'
        sign = f'+{d:g}' if d >= 0 else f'{d:g}'
        parts.append(
            f'<rect data-anim="grow" x="{x:.1f}" y="{top_y:.1f}" width="{bw:.1f}" '
            f'height="{max(bot_y - top_y, 2):.1f}" rx="5" class="{cls}"/>'
        )
        parts.append(
            f'<text x="{x + bw/2:.1f}" y="{top_y - 8:.1f}" text-anchor="middle" '
            f'class="{cls}" font-size="12" font-weight="600">{sign}{esc(unit)}</text>'
        )
        parts.append(
            f'<text x="{x + bw/2:.1f}" y="{base + 16}" text-anchor="middle" '
            f'class="f-txt3" font-size="11">{esc(labels[idx])}</text>'
        )
        # connector
        if i < len(mids):
            parts.append(
                f'<line x1="{x - (step - bw)/2:.1f}" y1="{ya:.1f}" '
                f'x2="{x:.1f}" y2="{ya:.1f}" class="s-bds" stroke-width="1" stroke-dasharray="3 3"/>'
            )
        prev = nxt
    # end bar
    x = left + (n - 1) * step + (step - bw) / 2
    ye = y_of(end)
    parts.append(
        f'<rect data-anim="grow" x="{x:.1f}" y="{ye:.1f}" width="{bw:.1f}" '
        f'height="{base - ye:.1f}" rx="5" class="f-acc"/>'
    )
    parts.append(
        f'<text x="{x + bw/2:.1f}" y="{ye - 8:.1f}" text-anchor="middle" '
        f'class="f-txt2" font-size="12" font-weight="600">{end:g}{esc(unit)}</text>'
    )
    parts.append(
        f'<text x="{x + bw/2:.1f}" y="{base + 16}" text-anchor="middle" '
        f'class="f-txt3" font-size="11">{esc(labels[-1])}</text>'
    )
    return ('<svg class="chart" data-chart="waterfall" viewBox="0 0 560 220">\n      '
            + '\n      '.join(parts) + '\n    </svg>')


class ChartDataError(ValueError):
    """图表数据非法：调用方应捕获并输出干净 FAIL（不打 Traceback）。"""


def _coerce_values(values, ctx: str) -> list:
    out = []
    for i, v in enumerate(values):
        try:
            f = float(v)
        except (TypeError, ValueError):
            raise ChartDataError(f'{ctx}: values[{i}] 非数字（{str(v)[:40]!r}），无法绘制')
        if f != f or f in (float('inf'), float('-inf')):
            raise ChartDataError(f'{ctx}: values[{i}] 非有限数字，无法绘制')
        out.append(f)
    return out


def validate_payload(chart: dict, ctx: str) -> tuple:
    """校验图表数据：空数据/长度不一致/非数字一律干净报错，禁静默截断。"""
    ct = (chart.get('type') or 'bar').lower()
    labels = chart.get('labels') or []
    values = chart.get('values') or []
    if not labels or not values:
        raise ChartDataError(
            f'{ctx}: labels/values 为空（labels={len(labels)} values={len(values)}），无法绘制 {ct} 图')
    if len(labels) != len(values):
        raise ChartDataError(
            f'{ctx}: labels({len(labels)}) 与 values({len(values)}) 长度不一致，'
            f'拒绝静默截断（{ct} 图）')
    return list(labels), _coerce_values(values, ctx)


def build_svg(chart: dict, ctx: str = '') -> str:
    ct = (chart.get('type') or 'bar').lower()
    labels, values = validate_payload(chart, ctx or f'图表({ct})')
    unit = chart.get('unit') or ''
    max_v = chart.get('max')
    if ct == 'hbar':
        return svg_hbar(labels, values, max_v, unit)
    if ct == 'line':
        return svg_line(labels, values, max_v, unit, area=False)
    if ct == 'area':
        return svg_line(labels, values, max_v, unit, area=True)
    if ct == 'donut' or ct == 'pie':
        return svg_donut(labels, values, chart.get('centerLabel') or '合计', unit)
    if ct == 'waterfall':
        return svg_waterfall(labels, values, unit)
    return svg_bar(labels, values, max_v, unit)


def iter_chart_payloads(model: dict):
    """Yield (chart dict, context str) in document order (sections + split sides)."""
    for si, sec in enumerate(model.get('sections') or []):
        st = (sec.get('type') or '').lower()
        sctx = f'第{si + 1}节[{sec.get("title") or st}]'
        if st in ('bar', 'donut', 'exhibit', 'halftable') and sec.get('chart'):
            ch = dict(sec['chart'])
            if st == 'donut':
                ch.setdefault('type', 'donut')
            elif not ch.get('type'):
                ch['type'] = 'bar'
            yield ch, f'{sctx} 主图表'
        for side in ('left', 'right'):
            el = sec.get(side)
            if isinstance(el, dict) and el.get('labels') and el.get('values') is not None:
                ch = {
                    'type': el.get('type') or 'bar',
                    'labels': el.get('labels'),
                    'values': el.get('values'),
                    'unit': el.get('unit') or '',
                    'max': el.get('max'),
                    'centerLabel': el.get('centerLabel'),
                }
                yield ch, f'{sctx} {side}区图表'


def hydrate(html: str, model: dict) -> str:
    """占位 SVG → 真实图表 SVG。
    弹性（0.2.0）：单图数据非法只留占位并记入 errors，不中断整份报告其余图的水合。"""
    payloads = list(iter_chart_payloads(model))
    idx = 0
    errors: list = []

    def repl(m):
        nonlocal idx
        if idx >= len(payloads):
            return m.group(0)
        ch, ctx = payloads[idx]
        idx += 1
        try:
            return build_svg(ch, ctx)
        except ChartDataError as e:
            errors.append(str(e))
            return m.group(0)

    new_html, n = PLACEHOLDER_SVG_RE.subn(repl, html)
    return new_html, n, idx, len(payloads), errors


def main() -> int:
    if len(sys.argv) < 2:
        print('usage: _hydrate_charts.py <report.html>')
        return 2
    path = Path(sys.argv[1])
    try:
        html = path.read_text(encoding='utf-8')
    except FileNotFoundError:
        print(f'FAIL: 文件不存在 {path}')
        return 1
    except UnicodeDecodeError as e:
        print(f'FAIL: 文件不是合法 UTF-8 {path}（{e}）')
        return 1
    except OSError as e:
        print(f'FAIL: 读取失败 {path}（{e}）')
        return 1
    # 括号感知抽取（模型字符串含 `};` 时正则会提前截断；非法 JSON 走干净 FAIL）
    try:
        span = extract_model_span(html)
    except SystemExit as e:
        print(f'FAIL: {e}')
        return 1
    if not span:
        print('FAIL: no REPORT_MODEL')
        return 1
    model = span[2]
    if not isinstance(model, dict):
        print(f'FAIL: REPORT_MODEL 根节点必须是对象（得到 {type(model).__name__}）')
        return 1
    try:
        new_html, n_ph, used, total, chart_errors = hydrate(html, model)
    except ChartDataError as e:
        # 防御：hydrate 内部已按图捕获，此处仅兜底批量抽取阶段的非法数据
        print(f'FAIL: 图表数据非法——{e}')
        return 1
    for e in chart_errors:
        print(f'FAIL: 图表数据非法——{e}（该图保留占位，其余图已水合）')
    rc = 1 if chart_errors else 0
    new_html, n_icon, unknown_icons = hydrate_icons(new_html)
    if unknown_icons:
        print(f'WARN: 未知图标名（已保留原标记）: {", ".join(unknown_icons)}')
    path.write_text(new_html, encoding='utf-8')
    left = new_html.count('见模型数据')
    print(f'hydrated placeholders={n_ph} icons={n_icon} used_payloads={used}/{total} remaining_placeholder={left}')
    if rc:
        return rc  # 有图表数据非法：文件已落盘（坏图留占位），但以非零码报告
    return 0 if left == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
