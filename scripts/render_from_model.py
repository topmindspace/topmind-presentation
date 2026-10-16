#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""topmind-presentation · 模型驱动生成 HTML（消灭双写）

用法:
    python scripts/render_from_model.py report.model.json --template research.html --out report.html
    python scripts/render_from_model.py report.html --inplace     # 用内嵌 REPORT_MODEL 重渲染正文区
    python scripts/render_from_model.py report.model.json --body-only > body.html

定位:
    REPORT_MODEL 是内容唯一事实源。本脚本按锁定版式（layout-grammar P1–P12 / scaffold 同源类名）
    从模型字段渲染 HTML 正文——智能体只填模型，不再手写正文与模型两份。
    引擎标记块（__TOPPPT_*__）原样保留；正文区由模型重建。

纪律:
    · 模型字符串字段必须是纯文本（引用写 [n]）；本脚本负责转义
    · 版式类名与 scaffold_report / components 锁定版式一致，禁止临场发明
    · 渲染后必须跑 validate_report --strict
"""
from __future__ import annotations

import argparse
import json
import html
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / 'assets' / 'templates'
LC = json.loads((ROOT / 'scripts' / 'layout-constants.json').read_text(encoding='utf-8'))
PAGE_TO_PRESET = ((LC.get('layoutSystem') or {}).get('pageToPreset') or {})
IMAGE_SPEC = LC.get('imageSpec') or {}
sys.path.insert(0, str(ROOT / 'scripts'))
import lib_chart_svg as LCS  # noqa: E402
import lib_density as LD  # noqa: E402
SKIN: dict = {}

CONTENT_RE = re.compile(
    r'(<!-- __TOPPPT_CONTENT_START__ -->)[\s\S]*?(<!-- __TOPPPT_CONTENT_END__ -->)')
MODEL_RE = re.compile(r'window\.REPORT_MODEL\s*=\s*')


def _strict_decoder():
    """标准 JSON 解码器：拒绝 NaN/Infinity（与 Node JSON.parse 同口径）。"""
    def _reject_const(x):
        raise ValueError(f'非法 JSON 常量 {x}')
    return json.JSONDecoder(parse_constant=_reject_const)


def extract_model_span(txt: str):
    """括号感知抽取 window.REPORT_MODEL：返回 (start, end, model)。

    start/end 是 JSON 文本在 txt 中的起止下标（含首尾花括号，不含末尾分号）。
    用 JSONDecoder.raw_decode 而非正则 `\\{[\\s\\S]*?\\}`——模型字符串里若含 `};`
   （如标题含代码片段），正则会提前截断导致解析失败或 --inplace 写坏文件。
    """
    m = MODEL_RE.search(txt)
    if not m:
        return None
    try:
        model, end = _strict_decoder().raw_decode(txt, m.end())
    except json.JSONDecodeError as e:
        raise SystemExit(f'REPORT_MODEL 不是合法 JSON: {e}（必须双引号/无尾逗号/无注释）')
    except ValueError as e:
        raise SystemExit(f'REPORT_MODEL 不是合法 JSON: {e}（必须双引号/无尾逗号/无注释）')
    return m.start(), end, model


def replace_model_json(txt: str, model: dict) -> str:
    """把 txt 内 REPORT_MODEL 的 JSON 原子替换为 model（起止下标精确定位，不误伤正文）。"""
    span = extract_model_span(txt)
    if not span:
        raise SystemExit('未找到 window.REPORT_MODEL')
    start, end, _ = span
    return (txt[:start] + 'window.REPORT_MODEL = '
            + json.dumps(model, ensure_ascii=False, indent=2) + ';' + txt[end:])


def esc(s) -> str:
    return (str(s or '')
            .replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;'))


def cite(text: str) -> str:
    """模型里 [n] → HTML 上标引用（模型保持纯文本）。"""
    return re.sub(r'\[(\d+)\]',
                  r'<a class="cite" href="#ref-\1">[\1]</a>',
                  esc(text))


def kp(k, v) -> str:
    k, v = esc(k), cite(v) if isinstance(v, str) else esc(v)
    return f'<li><strong>{k}。</strong>{v}</li>' if k else f'<li>{v}</li>'


def sec_anchor(i: int, sec: dict) -> str:
    """页锚点 id：模型 anchor 优先，否则 s{i}（agenda 链接与 open_sec 同源，禁各写一份）。"""
    a = str((sec or {}).get('anchor') or '').strip()
    if re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', a):
        return a
    return f's{i}'


def open_sec(i: int, ptype: str, extra: str = '', sec: dict = None) -> str:
    skel = PAGE_TO_PRESET.get(ptype, 'P4')
    sid = sec_anchor(i, sec)
    # extra 里的裸 band--* 类名并入 class（此前会被写成无效属性）
    toks = extra.split(' ') if extra else []
    cls_extra = [t for t in toks if t.startswith('band--') and '=' not in t]
    attr = ' '.join(t for t in toks if t and t not in cls_extra)
    cls = ' '.join(['band'] + cls_extra)
    return (f'<section class="{cls}" id="{sid}" data-skel="{skel}" '
            f'data-page-type="{ptype}"' + (' ' + attr if attr else '') + '>')


def shead(sec: dict) -> str:
    lead = sec.get('lead') or ''
    lead_html = f'\n    <p class="t-lead shead__desc">{cite(lead)}</p>' if lead else ''
    return (f'    <div class="shead rv">\n'
            f'      <div class="t-eyebrow">{esc(sec.get("eyebrow") or "")}</div>\n'
            f'      <h2 class="t-h1 shead__title">{esc(sec.get("title") or "")}</h2>'
            f'{lead_html}\n    </div>')


def sowhat(sec: dict) -> str:
    t = sec.get('soWhat')
    if not t:
        return ''
    return (f'    <div class="sowhat rv"><span class="sowhat__v">{cite(t)}</span></div>\n')


def footnote(sec: dict) -> str:
    # footnote 与 note 共用来源行（与 build_pptx 注释带同口径：两者都不丢）
    t = sec.get('footnote')
    n = sec.get('note')
    parts = []
    if t:
        parts.append(cite(t))
    if n and n != t:
        parts.append(f'注：{cite(n)}')
    if not parts:
        return ''
    return f'    <div class="footnote">{" ".join(parts)}</div>\n'


def flags_block(sec: dict) -> str:
    fl = sec.get('flags') or []
    if not fl:
        return ''
    items = '\n'.join(f'      <li>{cite(x)}</li>' for x in fl)
    return (f'    <div class="flagbar rv"><div class="flagbar__hd">待核实</div>\n'
            f'      <ul>\n{items}\n      </ul>\n    </div>\n')


def wrap(i: int, ptype: str, body: str, sec: dict, extra: str = '') -> str:
    if ptype in ('heatmap', 'bullet', 'halftable', 'lane', 'pyramid', 'matrix', 'metrics'):
        C = LD.compose_on(sec, ptype)
        if C and C['form'] == 'band':
            body = body + _readout_row(C['km'][:2], C['pts'][:3])
    return (f'{open_sec(i, ptype, extra, sec)}\n  <div class="wrap">\n'
            f'{shead(sec)}\n{body}{sowhat(sec)}{footnote(sec)}{flags_block(sec)}'
            f'  </div>\n</section>')


# ── 语义图标库（单源：assets/icons/ + index.json；与 icon_lib.js / PPTX 真导出同源）──
_ICON_DIR = Path(__file__).resolve().parent.parent / 'assets' / 'icons'
_ICON_INDEX: dict = {}
try:
    _ICON_INDEX = json.loads((_ICON_DIR / 'index.json').read_text(encoding='utf-8'))
except OSError:
    _ICON_INDEX = {}


def _load_icons() -> 'dict[str, str]':
    out: dict[str, str] = {}
    for name in (_ICON_INDEX.get('icons') or {}):
        try:
            out[name] = (_ICON_DIR / f'{name}.svg').read_text(encoding='utf-8').strip()
        except OSError:
            continue
    return out


ICONS: dict[str, str] = _load_icons()
_ICONS_ORDER = list(ICONS.keys())
_ICON_DEFAULTS = [n for n in (_ICON_INDEX.get('defaults') or []) if n in ICONS] or _ICONS_ORDER


def pick_icon(title: str = '', idx: int = 0) -> str:
    """按标题语义挑图标 SVG；未命中则在默认表内轮换（选不出用默认，不盲目轮换全量）。"""
    return ICONS[pick_icon_name(title, idx)]


def pick_icon_name(title: str = '', idx: int = 0) -> str:
    """图标名（与 icon_lib.js / PPTX 真导出同名；关键词来自 index.json）。"""
    t = str(title or '')
    meta = _ICON_INDEX.get('icons') or {}
    for key in _ICONS_ORDER:
        kws = (meta.get(key) or {}).get('keywords') or [key]
        if any(kw and kw in t for kw in kws):
            return key
    return _ICON_DEFAULTS[idx % len(_ICON_DEFAULTS)]


def card_head(title: str, idx: int = 0, icon_name: str | None = None) -> str:
    """卡片头：图标路标 + 标题（与 scaffold 的 .card__hd + .card__ico 同源）。
    icon_name 写入 data-icon，供 extract_model / build_pptx 真导出同名图标。"""
    name = icon_name or pick_icon_name(title, idx)
    return (f'<div class="card__hd"><div class="card__ico" data-icon="{esc(name)}">{pick_icon(title, idx)}</div>'
            f'<h3 class="t-h3">{esc(title)}</h3></div>')


def pts_list(points) -> str:
    if not points:
        return '<ul class="ul"><li>（待填）</li></ul>'
    lis = []
    for p in points:
        if isinstance(p, (list, tuple)) and len(p) >= 2:
            lis.append(kp(p[0], p[1]))
        elif isinstance(p, dict):
            lis.append(kp(p.get('k') or p.get('t') or '', p.get('v') or p.get('d') or ''))
        else:
            lis.append(f'<li>{cite(p)}</li>')
    return '<ul class="ul">' + ''.join(lis) + '</ul>'


def chart_svg(chart: dict, idx: int, force_type: str | None = None, w: int = 900, h: int = 340) -> str:
    """HTML 图表 = lib_chart_svg（数据驱动，与 PPTX 同一份 chart 数据、同一配色与标注层语义）。"""
    ch = dict(chart or {})
    if force_type:
        ch['type'] = force_type
    return '      ' + LCS.chart(ch, SKIN, w, h) + '\n'


def r_points(i, sec):
    pts = sec.get('points') or []
    half = (len(pts) + 1) // 2 or 1
    col1, col2 = pts[:half], pts[half:]
    # 要点分两栏无标题卡承载；不足两组时单卡——不再补「要点一 / 要点二 / （第二组要点）」占位字
    cols = [c for c in (col1, col2) if c] or [pts]
    body = (f'    <div class="grid {"g-2" if len(cols) > 1 else "g-1"} rv a-start">\n'
            + '\n'.join(f'      <div class="card">\n        {pts_list(c)}</div>' for c in cols) + '\n'
            + '    </div>\n')
    if sec.get('metrics'):
        body += metrics_row(sec['metrics'])
    return wrap(i, 'points', body, sec)


def metrics_row(metrics) -> str:
    cells = []
    for m in (metrics or [])[:6]:
        if isinstance(m, (list, tuple)):
            val, key = m[0], m[1] if len(m) > 1 else ''
            note = m[2] if len(m) > 2 else ''
        else:
            val, key, note = m.get('v') or m.get('value') or '', m.get('k') or '', m.get('n') or ''
        cells.append(
            f'      <div class="metric"><div class="metric__v t-metric">{esc(val)}</div>'
            f'<div class="metric__k">{esc(key)}</div>'
            f'<div class="metric__n">{cite(note)}</div></div>')
    return f'    <div class="grid g-4 rv a-start">\n' + '\n'.join(cells) + '\n    </div>\n'


def r_metrics(i, sec):
    # M9：独立指标页用「主视觉」变体——卡片撑高、数字居中放大，与 PPTX 指标页同构，不再顶部一条、下半页空
    row = metrics_row(sec.get('metrics')).replace('<div class="grid g-4 rv a-start">', '<div class="grid g-4 rv a-stretch metrics-hero">', 1)
    return wrap(i, 'metrics', row, sec, ' band--top')


def r_kpi(i, sec):
    # 大数指标页：hero 大数字 + 支撑指标行（metrics，可选）+ 要点；三者缺一不丢其余
    hero = sec.get('hero') or []
    val = hero[0] if hero else ''
    lab = hero[1] if len(hero) > 1 else ''
    delta = hero[2] if len(hero) > 2 else ''
    left = ''
    if val or lab:
        left = (
            '      <div class="stack gap-3"><div class="t-metric" style="color:var(--accent)">'
            f'{esc(val)}</div>'
            f'<div class="t-h3">{esc(lab)}</div>'
            + (f'<div class="t-sm" style="color:var(--accent);font-weight:600">{esc(delta)}</div>' if delta else '')
            + '</div>\n')
    if left:
        # hero 放进 tonal 面板，与 PPTX 大数面板同构
        left = ('      <div class="kpi-hero" style="background:var(--accent-soft);border-radius:var(--radius-lg,20px);'
                'padding:clamp(24px,3vw,44px)">\n' + left + '      </div>\n')
    mets = ''
    if sec.get('metrics'):
        # 支撑指标竖排（右列窄，4 列横排会把「5.8 年」挤成两行）
        cells = []
        for m in sec['metrics'][:4]:
            val, key = (m[0], m[1] if len(m) > 1 else '') if isinstance(m, (list, tuple)) else (m.get('v') or '', m.get('k') or '')
            cells.append(f'        <div class="metric">'
                         f'<div class="metric__v t-h2">{esc(val)}</div><div class="metric__k">{esc(key)}</div></div>')
        mets = '      <div class="stack gap-2">\n' + '\n'.join(cells) + '\n      </div>\n'
    pts = sec.get('points') or []   # 不补占位要点：没有就不渲染这一块
    body = (
        '    <div class="grid g-hero rv a-c">\n'
        + left + mets
        + '    </div>\n'
        + ('    <div class="grid g-2">\n' + pts_list(pts) + '\n    </div>\n' if pts else ''))
    return wrap(i, 'kpi', body, sec)


def r_table(i, sec):
    tbl = sec.get('table') or {}
    head = tbl.get('head') or []
    rows = tbl.get('rows') or []
    hl = sec.get('highlightCol') if sec.get('variant') == 'highlight' else None
    hl = hl if isinstance(hl, int) else None
    cls = lambda j: ' class="is-hl"' if j == hl else ''
    th = ''.join(f'<th{cls(j)}>{esc(h)}</th>' for j, h in enumerate(head))
    trs = []
    for row in rows:
        tds = ''.join(f'<td{cls(j)}>{cite(c)}</td>' for j, c in enumerate(row))
        trs.append(f'<tr>{tds}</tr>')
    tcls = ' tbl--hl' if hl is not None else ''
    body = (f'    <div class="tbl-wrap{tcls} rv"><table><thead><tr>' + th +
            '</tr></thead><tbody>' + ''.join(trs) + '</tbody></table></div>\n')
    extra = ' data-variant="highlight"' if hl is not None else ''
    return wrap(i, 'table', body, sec, extra)


def _km_tiles(km, cls='kstrip') -> str:
    cells = []
    for m in km:
        if isinstance(m, (list, tuple)):
            v, k = m[0], m[1] if len(m) > 1 else ''
        else:
            v, k = m.get('v') or m.get('value') or '', m.get('k') or ''
        cells.append(f'<div class="kstrip__c"><div class="kstrip__v">{esc(v)}</div><div class="kstrip__k">{cite(k)}</div></div>')
    return f'    <div class="{cls} rv" style="--n:{max(1, len(km))}">' + ''.join(cells) + '</div>\n'


def _kv(p):
    if isinstance(p, (list, tuple)):
        return (str(p[0]) if p else ''), (str(p[1]) if len(p) > 1 else '')
    if isinstance(p, dict):
        return str(p.get('k') or p.get('t') or ''), str(p.get('v') or p.get('d') or '')
    return '', str(p)


def _readout(pts) -> str:
    lis = []
    for n, p in enumerate(pts[:5], 1):
        k, v = _kv(p)
        lis.append(f'<li><span class="readout__n">{n}</span><div><div class="readout__k">{cite(k)}</div>'
                   + (f'<p class="readout__v">{cite(v)}</p>' if v else '') + '</div></li>')
    return '<ol class="readout">' + ''.join(lis) + '</ol>'


def _readout_row(km, pts) -> str:
    """band 形态：关键数字卡 + 解读卡同一行（与 PPTX readoutRow 同构）。"""
    cells = []
    for m in km:
        v, k = _kv(m)
        cells.append(f'<div class="cband__km"><div class="kstrip__v">{esc(v)}</div><div class="kstrip__k">{cite(k)}</div></div>')
    for p in pts[:4]:
        k, v = _kv(p)
        cells.append(f'<div class="cband__p"><div class="readout__k">{cite(k)}</div>'
                     + (f'<p class="readout__v">{cite(v)}</p>' if v else '') + '</div>')
    if not cells:
        return ''
    cols = ' '.join(['minmax(0,.62fr)'] * len(km) + ['minmax(0,1fr)'] * len(pts[:4]))
    return (f'    <div class="cband rv" style="grid-template-columns:{cols}">'
            + ''.join(cells) + '</div>\n')


def _mini_fig(m, i) -> str:
    cap = m.get('cap') or ''
    t = 'donut' if m.get('type') == 'donut' else None
    return (f'      <div class="mini">' + (f'<div class="fig__cap">{esc(cap)}</div>' if cap else '')
            + chart_svg(m, i, t, 440, 160) + (f'<div class="mini__n">{cite(m["note"])}</div>' if m.get('note') else '')
            + '</div>\n')


def compose_body(i, sec, ptype, fig_html):
    """M7 复合版式（信息密度）：论点（标题）+ 证据（主图）+ 解读（要点）+ 关键数字。
    side：关键数字条 + 主图 | 解读栏；chart2 → 双图对照 + 解读行；minis → 主图 + 小图组。
    band：主图 + 底部「关键数字 + 解读」带。返回 None 表示不升级（保持原版式）。"""
    C = LD.compose_on(sec, ptype)
    if not C:
        return None
    km, pts = C['km'], C['pts']
    if C['form'] == 'band':
        return fig_html + _readout_row(km[:2], pts[:3])
    out = _km_tiles(km) if km else ''
    if sec.get('chart2'):
        c2 = sec['chart2']
        fig2 = _exhibit_box({'cap': c2.get('cap') or ''}, chart_svg(c2, i * 10 + 1, None, 640, 320), i)
        out += '    <div class="grid g-2 rv a-start">\n' + fig_html + fig2 + '    </div>\n'
        if pts:
            out += _readout_row([], pts)
        return out
    minis = [m for m in (sec.get('minis') or []) if isinstance(m, dict) and m.get('labels')][:2]
    if minis:
        out += ('    <div class="grid g-side rv a-start">\n' + fig_html
                + '      <div class="minis">\n' + ''.join(_mini_fig(m, i * 10 + k) for k, m in enumerate(minis))
                + '      </div>\n    </div>\n')
        if pts:
            out += _readout_row([], pts)
        return out
    if pts:
        out += ('    <div class="grid g-comp rv a-stretch">\n' + fig_html
                + f'      {_readout(pts)}\n    </div>\n')
    else:
        out += fig_html
    return out


def _fig_with_side(i, sec, ptype, fig_html):
    """图 + 解读：命中复合版式时走 compose_body；否则主图满宽（低密度，check_density 会拦）。"""
    if sec.get('exhibitNo') and not sec.get('source') and sec.get('footnote'):
        sec = dict(sec)
        sec.pop('footnote')  # 已进 Exhibit 来源行
    body = compose_body(i, sec, ptype, fig_html)
    if body is None:
        body = fig_html
    return wrap(i, ptype, body, sec)


def _exhibit_box(sec, svg, i):
    """带编号 → Exhibit 框（编号 + 标题 + 来源行，research 规范）；否则轻量 .fig（可选图注）。
    来源行取 sec.source（缺省回退 footnote，由调用方从页脚移除避免重复）。"""
    no = sec.get('exhibitNo')
    cap = sec.get('cap') or (sec.get('chart') or {}).get('cap') or ''
    if not no:
        capd = f'<div class="fig__cap">{esc(cap)}</div>\n' if cap else ''
        return f'      <div class="fig rv">{capd}{svg}      </div>\n'
    no_s = str(no)
    if not no_s.lower().startswith('exhibit'):
        no_s = f'Exhibit {no_s}'
    src = sec.get('source') or sec.get('footnote') or ''
    return ('      <div class="exhibit rv">\n'
            f'        <div class="exhibit__hd"><span class="exhibit__no">{esc(no_s)}</span>'
            + (f'<span class="exhibit__t">{esc(cap)}</span>' if cap else '') + '</div>\n'
            + svg
            + (f'        <div class="exhibit__src">{cite(src)}</div>\n' if src else '')
            + '      </div>\n')


def r_bar(i, sec):
    ch = sec.get('chart') or {}
    return _fig_with_side(i, sec, 'bar', _exhibit_box(sec, chart_svg(ch, i), i))


def r_donut(i, sec):
    ch = dict(sec.get('chart') or {})
    ch['type'] = 'donut'
    return _fig_with_side(i, sec, 'donut', _exhibit_box(sec, chart_svg(ch, i), i))


def r_exhibit(i, sec):
    ch = dict(sec.get('chart') or {})
    st = (sec.get('type') or '').lower()
    if not ch.get('type'):
        ch['type'] = 'donut' if st == 'donut' else 'bar'
    return _fig_with_side(i, sec, st or 'exhibit', _exhibit_box(sec, chart_svg(ch, i), i))


def r_twocol(i, sec):
    paras = sec.get('paragraphs') or []
    variant = sec.get('variant') or ''
    cols = []
    for pi, p in enumerate(paras):
        if isinstance(p, (list, tuple)) and len(p) >= 2:
            cols.append(f'      <p class="t-body"><strong>{esc(p[0])}。</strong>{cite(p[1])}</p>')
        else:
            cols.append(f'      <p class="t-body">{cite(p)}</p>')
    # 变体 2-col-feature：首栏为特性栏（MD3 tonal 底 + 加粗标题，无左侧竖条）
    extra = ''
    if variant == '2-col-feature' and cols:
        cols[0] = cols[0].replace('class="t-body"', 'class="t-body col--feature"', 1)
        extra = ' data-variant="2-col-feature"'
    body = '    <div class="cols-2 rv">\n' + '\n'.join(cols) + '\n    </div>\n'
    return wrap(i, 'twocol', body, sec, extra)


def r_threecol(i, sec):
    paras = sec.get('paragraphs') or []
    cols = []
    for pi, p in enumerate(paras[:6]):
        if isinstance(p, (list, tuple)) and len(p) >= 2:
            cols.append(f'      <div class="card">{card_head(str(p[0]), pi, p[2] if len(p) > 2 else None)}'
                        f'<p class="t-body">{cite(p[1])}</p></div>')
        else:
            cols.append(f'      <div class="card"><p class="t-body">{cite(p)}</p></div>')
    # cols-3 供校验「模型页型 ↔ 版式组件」对齐（TYPE_FEATURE.threecol）
    body = ('    <div class="cols-3 grid g-3 rv a-start">\n' + '\n'.join(cols) + '\n    </div>\n')
    return wrap(i, 'threecol', body, sec)


def r_cards(i, sec):
    cards = sec.get('cards') or []
    variant = sec.get('variant') or ''
    n = int(sec.get('columns') or min(3, max(1, len(cards))))
    cls = {1: 'g-2', 2: 'g-2', 3: 'g-3', 4: 'g-4'}.get(n, 'g-3')
    # 纯卡片栅格强制等高（g-2--equal / g-3--equal），与 CSS / layout-grammar「同行卡片 stretch」一致
    if cls in ('g-2', 'g-3', 'g-4'):
        cls = f'{cls} {cls}--equal'
    extra = ''
    if variant == 'bento-grid':
        # 变体 bento-grid：首卡跨 2 列（.card--lead），复用 .card 组件
        cls, extra = 'g-bento g-bento--cards', ' data-variant="bento-grid"'
    blocks = []
    for ci, cd in enumerate(cards):
        if isinstance(cd, dict):
            title = cd.get('title')
            points = cd.get('points') or []
            icon_name = cd.get('icon')
        elif isinstance(cd, (list, tuple)) and len(cd) > 1:
            title, points, icon_name = cd[0], [['', cd[1]]], None
        else:
            title, points, icon_name = (cd or ''), [], None
        lead_cls = ' card--lead' if (variant == 'bento-grid' and ci == 0) else ''
        if variant == 'bento-grid' and ci == len(cards) - 1 and ci > 0:
            # 末行补齐：槽位 = 卡数 + 1（首卡跨 2），余数由尾卡吃掉，不留空洞
            rest = -(len(cards) + 1) % 3
            if rest:
                lead_cls += f' card--fill{rest + 1}'
        if not str(title or '').strip() and points:
            # 陈述卡（无标题，正文即原句——美化路由）：首句放大作卡片主体，其余作补充
            first = points[0] if isinstance(points[0], str) else ' '.join(str(x) for x in points[0])
            rest = pts_list(points[1:]) if len(points) > 1 else ''
            blocks.append(
                f'      <div class="card card--stmt{lead_cls}">\n        <p class="t-lead card__stmt">{cite(first)}</p>{rest}</div>')
            continue
        blocks.append(
            f'      <div class="card{lead_cls}">{card_head(str(title), ci, icon_name)}\n'
            f'        {pts_list(points) if points else ""}</div>')
    # 短内容卡片页（≤4 卡、每卡正文平均 ≤60 字）：放大字号并让卡片撑到约半屏，避免下半页空白
    def _clen(cd):
        pts = (cd.get('points') if isinstance(cd, dict) else []) or []
        return sum(len(p if isinstance(p, str) else ''.join(str(x) for x in p)) for p in pts)
    if cards and len(cards) <= 4 and variant != 'bento-grid' and \
            sum(_clen(c) for c in cards) / len(cards) <= 60:
        cls += ' cards--roomy'
    body = f'    <div class="grid {cls} rv">\n' + '\n'.join(blocks) + '\n    </div>\n'
    return wrap(i, 'cards', body, sec, extra)


def r_split(i, sec):
    def zone(el, side):
        if not el:
            return '      <div></div>'
        t = (el.get('type') or ('points' if el.get('points') else 'bar'))
        if t == 'table':
            return ('      <div class="tbl-wrap"><table><thead><tr>' +
                    ''.join(f'<th>{esc(h)}</th>' for h in (el.get('head') or [])) +
                    '</tr></thead><tbody>' +
                    ''.join('<tr>' + ''.join(f'<td>{cite(c)}</td>' for c in row) + '</tr>'
                            for row in (el.get('rows') or [])) +
                    '</tbody></table></div>')
        if t == 'image':
            im = el.get('image') or {}
            cap = im.get('caption') or ''
            src = im.get('src') or ''
            ph = bool(im.get('placeholder')) or not src
            fit = im.get('fit') or (IMAGE_SPEC or {}).get('fitDefault') or 'cover'
            fig = _media_figure(src, 'half', fit, '', placeholder=ph,
                                ratio_cls=(IMAGE_SPEC or {}).get('ratioCssClass', {}).get('half') or 'media--r4-3')
            return fig + (f'\n      <div class="media__cap--below">{esc(cap)}</div>' if cap else '')
        if t == 'points' or el.get('points') and t not in ('bar', 'line', 'donut', 'hbar'):
            return f'      <div class="stack gap-4">{pts_list(el.get("points"))}</div>'
        return _exhibit_box({'cap': el.get('cap')}, chart_svg(el, i, w=560, h=360), i).rstrip('\n')
    body = ('    <div class="grid g-side rv a-start">\n'
            f'{zone(sec.get("left"), "L")}\n{zone(sec.get("right"), "R")}\n'
            '    </div>\n')
    return wrap(i, 'split', body, sec)


def r_comparison(i, sec):
    def panel(d, accent=False):
        style = ' style="background:var(--accent-soft);border-color:transparent"' if accent else ''
        tcol = ' style="color:var(--accent)"' if accent else ''
        return (f'      <div class="card"{style}><h3 class="t-h3"{tcol}>{esc((d or {}).get("title") or "")}</h3>\n'
                f'        {pts_list((d or {}).get("points"))}</div>')
    ps = sec.get('variant') == 'problem-solution'
    if ps:
        # 版式 problem-solution：问题（中性面板）→ 方案（主题色调面板），中间方向箭头
        arrow = ('      <div class="cmp-arrow" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" '
                 'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                 '<path d="M5 12h14M13 6l6 6-6 6"/></svg></div>')
        body = ('    <div class="grid g-ps g-half rv">\n' + panel(sec.get('left')) + '\n' + arrow + '\n'
                + panel(sec.get('right'), True) + '\n    </div>\n')
    else:
        body = ('    <div class="grid g-half g-2 rv a-start">\n'
                + panel(sec.get('left')) + '\n' + panel(sec.get('right'), True) + '\n'
                + '    </div>\n')
    has_verdict = bool(sec.get('verdict'))
    if has_verdict:
        body += (f'    <div class="sowhat rv"><span class="sowhat__v">{cite(sec["verdict"])}</span></div>\n')
    sec = dict(sec)
    sec.pop('verdict', None)
    # R2：verdict 与 soWhat 共用 .sowhat 槽位——verdict 已渲染时移除 soWhat，禁止同槽双条
    if has_verdict:
        sec.pop('soWhat', None)
    return wrap(i, 'comparison', body, sec, ' data-variant="problem-solution"' if ps else '')


def r_quote(i, sec):
    # M0：不画装饰大引号；metrics（2–4 个证据数字）渲染为证据行，避免空金句页
    mets = []
    for m in (sec.get('metrics') or [])[:4]:
        if isinstance(m, (list, tuple)):
            mets.append((str(m[0] if len(m) > 0 else ''), str(m[1] if len(m) > 1 else '')))
        elif isinstance(m, dict):
            mets.append((str(m.get('v') or m.get('value') or ''), str(m.get('k') or m.get('label') or '')))
    ev = ''
    if mets:
        ev = ('    <div class="grid g-%d rv" style="margin-top:var(--sp-6)">\n' % max(2, min(4, len(mets)))
              + ''.join(f'      <div class="metric"><div class="metric__v t-metric">{esc(v)}</div>'
                        f'<div class="metric__k">{cite(k)}</div></div>\n' for v, k in mets)
              + '    </div>\n')
    body = (
        '    <div class="shead shead--center rv">\n'
        f'      <p class="t-lead" style="max-width:860px;margin-inline:auto;font-weight:600">{cite(sec.get("quote") or "")}</p>\n'
        f'      <p class="t-sm" style="color:var(--accent-text)">—— {esc(sec.get("author") or "")}'
        + (f' · {esc(sec.get("context"))}' if sec.get('context') else '')
        + '</p>\n    </div>\n' + ev)
    return wrap(i, 'quote', body, sec, ' band--accent band--fit')


def _img_ph_label(layout: str, multi: bool = False) -> str:
    """占位标签串——与 PPTX imgPlaceholderLabel 同源（imageSpec 常量拼接，cross_verify 逐页比对）。"""
    spec = IMAGE_SPEC or {}
    label = spec.get('placeholderLabel') or '配图占位'
    if multi:
        return label
    size = (spec.get('recommendedSizePx') or {}).get(layout)
    if not size:
        return label
    prefix = spec.get('placeholderHintPrefix') or '建议 '
    suffix = spec.get('placeholderHintSuffix') or 'px'
    return f'{label} · {prefix}{size}{suffix}'


def _media_figure(src: str, layout: str, fit: str, caption: str = '',
                  placeholder: bool = False, multi: bool = False, ratio_cls: str = '') -> str:
    """单张图 / 占位框（与 PPTX addImageEl 同源：比例锁定 + fit + 占位三要素标签）。"""
    spec = IMAGE_SPEC or {}
    ratio_map = spec.get('ratioCssClass') or {}
    rc = ratio_cls or ratio_map.get(layout) or 'media--r3-1'
    fit_cls = ' media--contain' if str(fit or '').lower() == 'contain' else ''
    if placeholder or not src:
        ph_text = _img_ph_label(layout, multi)
        # 与 PPTX 同串：bold=配图占位，span=建议 …px（单串合并输出，保证 A/B 文本一致）
        parts = ph_text.split(' · ', 1)
        b = esc(parts[0])
        span = esc(parts[1]) if len(parts) > 1 else ''
        inner = f'<div class="media__ph"><b>{b}</b><span>{span}</span></div>'
        return f'<figure class="media {rc} media--ph">{inner}</figure>'
    alt = caption or '配图'
    img = f'<img src="{esc(src)}" alt="{esc(alt)}">'
    cap_html = f'<figcaption class="media__cap--below">{cite(caption)}</figcaption>' if caption else ''
    return f'<figure class="media {rc}{fit_cls}">{img}{cap_html}</figure>'


def r_image(i, sec):
    im = sec.get('image') or {}
    layout = (im.get('layout') or 'full').lower()
    fit = im.get('fit') or (IMAGE_SPEC or {}).get('fitDefault') or 'cover'
    cap = im.get('caption') or ''
    items = im.get('items') or []
    multi_layouts = (IMAGE_SPEC or {}).get('multiLayouts') or ['grid', 'compare', 'wall']

    def one(src, placeholder=False, multi=False, ratio_cls=''):
        return _media_figure(src, layout, fit, cap if not multi else '',
                             placeholder=placeholder, multi=multi, ratio_cls=ratio_cls)

    if layout in multi_layouts and items:
        # 多图版式：grid / compare / wall（与 PPTX imageLayoutShapes 同源）
        cells = []
        ratio_map = (IMAGE_SPEC or {}).get('ratioCssClass') or {}
        for it in items[:6]:
            if not isinstance(it, dict):
                it = {'src': str(it)}
            it_src = it.get('src') or ''
            it_ph = bool(it.get('placeholder')) or not it_src
            it_cap = it.get('caption') or ''
            fig = one(it_src, placeholder=it_ph, multi=True,
                      ratio_cls=ratio_map.get(layout) or 'media--r4-3')
            if it_cap:
                fig += f'    <p class="media__src">{cite(it_cap)}</p>\n'
            cells.append(fig)
        n = len(cells)
        if layout == 'compare':
            grid_cls = 'media-compare'
        elif layout == 'wall':
            grid_cls = 'media-wall'
        else:
            grid_cls = f'media-grid media-grid--{min(4, max(2, n))}'
        media = f'    <div class="{grid_cls} rv">\n' + '\n'.join(cells) + '\n    </div>\n'
        # 组 caption（图编号）：多图版式同样渲染，与 PPTX img.caption 同口径（此前仅单图分支渲染）
        if cap:
            media += f'    <p class="media__src">{cite(cap)}</p>\n'
    else:
        src = im.get('src') or ''
        ph = bool(im.get('placeholder')) or not src
        media = one(src, placeholder=ph)
        if cap:
            media += f'    <p class="media__src">{cite(cap)}</p>\n'
    body = media
    if layout == 'half' and sec.get('points'):
        body = ('    <div class="grid g-side rv a-start">\n' + media +
                f'      <div class="stack gap-4">{pts_list(sec.get("points"))}</div>\n    </div>\n')
    return wrap(i, 'image', body, sec)


def r_diagram(i, sec):
    layers = sec.get('layers') or []
    rows = []
    for li, lay in enumerate(layers):
        name = lay[0] if lay else ''
        nodes = lay[1] if len(lay) > 1 else []
        focus = len(lay) > 2 and lay[2] == 'focus'
        nds = []
        for nd in nodes[:8]:
            if isinstance(nd, dict):
                acc = ' arch__node--accent' if nd.get('accent') else ''
                nds.append(f'          <div class="arch__node{acc}"><div class="arch__nt">{esc(nd.get("t") or "")}</div>'
                           f'<div class="arch__nd">{esc(nd.get("d") or "")}</div></div>')
            elif isinstance(nd, (list, tuple)):
                # [标题, 注解] 数组形态（scaffold_report 发射；不处理会原样打出 "['a', 'b']"）
                t = nd[0] if len(nd) > 0 else ""
                d = nd[1] if len(nd) > 1 else ""
                nds.append(f'          <div class="arch__node"><div class="arch__nt">{esc(t)}</div>'
                           f'<div class="arch__nd">{esc(d)}</div></div>')
            else:
                nds.append(f'          <div class="arch__node"><div class="arch__nt">{esc(nd)}</div></div>')
        rows.append(
            f'      <div class="arch__layer{" arch__layer--focus" if focus else ""}">\n'
            f'        <div class="arch__lname">{esc(name)}</div>\n'
            f'        <div class="arch__nodes">\n' + '\n'.join(nds) + '\n        </div>\n      </div>')
        if li < len(layers) - 1:
            rows.append('      <div class="arch__conn" aria-hidden="true">'
                        '<svg width="18" height="22" viewBox="0 0 18 22" fill="none" stroke="currentColor" '
                        'stroke-width="2"><path d="M9 2v14"/><path d="M4 12l5 6 5-6"/></svg></div>')
    legend = ''.join(f'<span class="chip">{esc(x)}</span>' for x in (sec.get('legend') or []))
    arch = '    <div class="arch rv">\n' + '\n'.join(rows) + '\n    </div>\n'
    aside = sec.get('aside') or {}
    if aside:
        # 横切能力列（治理 / 安全 / 可观测）：贯穿所有层，表达「护栏内嵌」而非某一层
        lis = ''.join(f'<li>{cite(x)}</li>' for x in (aside.get('items') or [])[:6])
        arch = ('    <div class="arch-wrap">\n' + arch +
                f'      <aside class="arch__aside rv"><div class="arch__aname">{esc(aside.get("title") or "")}</div>'
                f'<ul>{lis}</ul></aside>\n    </div>\n')
    body = (arch
            + (f'    <div class="arch__legend">{legend}</div>\n' if legend else ''))
    return wrap(i, 'diagram', body, sec, ' band--fit')


def r_lane(i, sec):
    lanes = sec.get('lanes') or []
    rows = []
    for ln in lanes:
        hd = ln[0] if ln else ''
        steps = ln[1] if len(ln) > 1 else []
        parts = []
        for si, st in enumerate(steps):
            if isinstance(st, dict):
                cls = 'lane__step lane__step--a' if st.get('accent') else 'lane__step'
                parts.append(f'<span class="{cls}">{esc(st.get("t") or "")}</span>')
            else:
                parts.append(f'<span class="lane__step">{esc(st)}</span>')
            if si < len(steps) - 1:
                parts.append('<span class="lane__arr" aria-hidden="true"></span>')
        rows.append(f'      <div class="lane"><div class="lane__hd">{esc(hd)}</div>'
                    f'<div class="lane__body">' + ''.join(parts) + '</div></div>')
    body = '    <div class="stack rv gap-3">\n' + '\n'.join(rows) + '\n    </div>\n'
    return wrap(i, 'lane', body, sec, ' band--fit')


def r_timeline(i, sec):
    items = []
    variant = sec.get('variant') or ''
    for ph in (sec.get('phases') or []):
        if isinstance(ph, (list, tuple)):
            lab, name, desc = (list(ph) + ['', '', ''])[:3]
            state = ph[3] if len(ph) > 3 else ''
            icon_name = ph[4] if len(ph) > 4 else ''
        else:
            lab, name, desc, state = ph.get('label', ''), ph.get('name', ''), ph.get('d', ''), ph.get('s', '')
            icon_name = ph.get('icon', '')
        cls = 'tl__i'
        if state == 'done':
            cls += ' tl__i--done'
        elif state == 'now':
            cls += ' tl__i--now'
        # 变体 timeline：节点图标（icon:<name>，无图标回落圆点）
        dot = '<div class="tl__d"></div>'
        if variant == 'timeline' and icon_name and icon_name in ICONS:
            dot = (f'<div class="tl__ico" data-icon="{esc(icon_name)}">'
                   f'{ICONS[icon_name]}</div>')
        items.append(
            f'        <div class="{cls}">{dot}'
            f'<div class="tl__l">{esc(lab)}</div><div class="tl__t">{esc(name)}</div>'
            f'<p class="t-body">{cite(desc)}</p></div>')
    _phs = sec.get('phases') or []
    def _d(ph):
        return (ph[2] if isinstance(ph,(list,tuple)) and len(ph)>2 else (ph.get('d','') if isinstance(ph,dict) else '')) or ''
    tl_cls = 'tl'
    if 2 <= len(_phs) <= 5 and variant != 'timeline' and all(len(str(_d(p))) <= 40 for p in _phs):
        tl_cls = f'tl tl--h" style="--n:{len(_phs)}'
    body = f'    <div class="fig rv"><div class="{tl_cls}">\n' + '\n'.join(items) + '\n    </div></div>\n'
    extra = ' data-variant="timeline"' if variant == 'timeline' else ''
    return wrap(i, 'timeline', body, sec, extra)


def r_steps(i, sec):
    items = []
    for si, st in enumerate((sec.get('steps') or [])[:6]):
        if isinstance(st, (list, tuple)):
            t, d = (list(st) + ['', ''])[:2]
            acc = False
        else:
            t, d, acc = st.get('t', ''), st.get('d', ''), bool(st.get('accent'))
        cls = 'step step--a' if acc else 'step'
        items.append(f'      <div class="{cls}"><div class="step__n">{si + 1:02d}</div>'
                     f'<div class="step__t">{esc(t)}</div><div class="step__d">{cite(d)}</div></div>')
    _st = (sec.get('steps') or [])[:6]
    def _sd(st):
        return str((st[1] if len(st) > 1 else '') if isinstance(st, (list, tuple)) else st.get('d', ''))
    roomy = ' steps--roomy' if _st and len(_st) <= 5 and all(len(_sd(x)) <= 40 for x in _st) else ''
    body = f'    <div class="steps{roomy} rv">\n' + '\n'.join(items) + '\n    </div>\n'
    return wrap(i, 'steps', body, sec)


def _heat_level(v, vmin, vmax):
    """与 build_pptx 同口径的 4 级色阶：0 底色 · 1 浅 · 2 中 · 3 主色。"""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    p = (x - vmin) / (vmax - vmin) if vmax > vmin else 0.5
    return 3 if p >= 0.86 else (2 if p >= 0.55 else (1 if p >= 0.25 else 0))


def r_heatmap(i, sec):
    rows, cols, cells = sec.get('rowHeads') or [], sec.get('colHeads') or [], sec.get('cells') or []
    unit = sec.get('unit') or ''
    flat = []
    for r in cells:
        for v in (r or []):
            try:
                flat.append(float(v))
            except (TypeError, ValueError):
                pass
    vmin, vmax = (min(flat), max(flat)) if flat else (0.0, 1.0)
    body = f'    <div class="heat rv" style="--heat-cols:{max(1, len(cols))}"><div class="heat__grid">\n'
    body += '      <div></div>' + ''.join(f'<div class="heat__h">{esc(c)}</div>' for c in cols) + '\n'
    for ri, rh in enumerate(rows):
        body += f'      <div class="heat__rh">{esc(rh)}</div>'
        row = cells[ri] if ri < len(cells) else []
        for ci in range(len(cols)):
            v = row[ci] if ci < len(row) else ''
            lv = _heat_level(v, vmin, vmax)
            cls = f' heat__c--{lv}' if lv else ''
            txt = (f'{v}{unit}' if lv is not None else (v if v not in ('', None) else '—'))
            body += f'<div class="heat__c{cls}">{esc(txt)}</div>'
        body += '\n'
    body += '    </div>\n'
    # M8：色阶图例（与 PPTX 同 4 级；两端标数值区间，scaleLabel 可覆盖文字）
    lg = sec.get('scaleLabel') or ['低', '高']
    def _fmt(x):
        return (str(int(x)) if float(x).is_integer() else f'{x:g}') + unit
    lo = f'{esc(lg[0])} {_fmt(vmin)}' if flat else esc(lg[0])
    hi = f'{esc(lg[1] if len(lg) > 1 else "高")} {_fmt(vmax)}' if flat else esc(lg[1] if len(lg) > 1 else '高')
    body += ('    <div class="heat__legend" aria-label="色阶图例"><span>' + lo + '</span>'
             + ''.join(f'<i class="heat__sw heat__c--{k}"></i>' for k in range(4))
             + '<span>' + hi + '</span></div>\n')
    body += '    </div>\n'
    return wrap(i, 'heatmap', body, sec)


def r_bullet(i, sec):
    items = sec.get('items') or []
    rows = []
    for it in items:
        if isinstance(it, (list, tuple)):
            k, a, t = (list(it) + ['', 0, 0])[:3]
        else:
            k, a, t = it.get('k', ''), it.get('a', 0), it.get('t', 0)
        mx = float(sec.get('max') or 100) or 100
        fw = max(0, min(100, float(a or 0) / mx * 100))
        tw = max(0, min(100, float(t or 0) / mx * 100))
        rows.append(
            f'      <div class="bul__row"><div class="bul__k">{esc(k)}</div>'
            f'<div class="bul__track"><div class="bul__fill" style="width:{fw}%"></div>'
            f'<div class="bul__tgt" style="left:{tw}%"></div></div>'
            f'<div class="bul__v"><b>{esc(a)}</b> / {esc(t)}</div></div>')
    body = '    <div class="bul rv">\n' + '\n'.join(rows) + '\n    </div>\n'
    return wrap(i, 'bullet', body, sec)


def r_pyramid(i, sec):
    levels = sec.get('levels') or []
    n = max(1, len(levels))
    rows = []
    for i2, lv in enumerate(levels):
        if isinstance(lv, (list, tuple)):
            t, d = (list(lv) + ['', ''])[:2]
        else:
            t, d = lv.get('t', ''), lv.get('d', '')
        w = 40 + int(60 * (i2 + 1) / n)
        rows.append(f'      <div class="pyr__lvl" style="--w:{w}%">'
                    f'<div class="pyr__t">{esc(t)}</div><div class="pyr__d">{cite(d)}</div></div>')
    body = '    <div class="pyr rv">\n' + '\n'.join(rows) + '\n    </div>\n'
    return wrap(i, 'pyramid', body, sec)


def r_halftable(i, sec):
    """半表半图：g-half 左表右图（校验 TYPE_FEATURE.halftable）。
    research 模式带 exhibitNo 时：右图按 Exhibit 规范加编号徽标与来源行，表侧不丢
    （此前 research 统一走 r_exhibit 会静默丢弃 table——内容覆盖率门禁捕获）。"""
    tbl = sec.get('table') or {}
    ch = sec.get('chart') or {}
    head = tbl.get('head') or []
    rows = tbl.get('rows') or []
    th = ''.join(f'<th>{esc(h)}</th>' for h in head)
    trs = ''.join('<tr>' + ''.join(f'<td>{cite(c)}</td>' for c in row) + '</tr>' for row in rows)
    fig = _exhibit_box(sec, chart_svg(ch, i, w=560, h=340), i)
    body = (
        '    <div class="grid g-half g-2 rv a-start">\n'
        f'      <div class="tbl-wrap"><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>\n'
        f'{fig}'
        '    </div>\n')
    return wrap(i, 'halftable', body, sec)


def r_matrix(i, sec):
    rows, cols, cells = sec.get('rowHeads') or [], sec.get('colHeads') or [], sec.get('cells') or []
    body = f'    <div class="matrix heat rv" style="--heat-cols:{max(1, len(cols))}"><div class="heat__grid">\n'
    body += '      <div></div>' + ''.join(f'<div class="heat__h">{esc(c)}</div>' for c in cols) + '\n'
    for ri, rh in enumerate(rows):
        body += f'      <div class="heat__rh">{esc(rh)}</div>'
        row = cells[ri] if ri < len(cells) else []
        for ci in range(len(cols)):
            v = row[ci] if ci < len(row) else ''
            if isinstance(v, dict):
                v = v.get('t') or v.get('v') or ''
            body += f'<div class="heat__c">{esc(v)}</div>'
        body += '\n'
    body += '    </div></div>\n'
    return wrap(i, 'matrix', body, sec)


def r_info(i, sec):
    t = (sec.get('type') or 'sankey').lower()
    svg = '      ' + LCS.INFO[t](sec, SKIN) + '\n'
    return _fig_with_side(i, sec, t, _exhibit_box(sec, svg, i))


def r_chapter(i, sec):
    """章节扉页：大号章节号 + 章标题 + 导语 + 本章看点（结构家族，节奏锚点）。"""
    m = re.match(r'^\s*(\d{1,2})', str(sec.get('eyebrow') or ''))
    num = str(sec.get('number') or (m.group(1) if m else '')).zfill(2)
    eb = re.sub(r'^\s*\d{1,2}\s*[·・\-—]\s*', '', str(sec.get('eyebrow') or '')) or f'第 {num} 章'
    items = ''.join(f'<li><span class="chap__i">{k:02d}</span>{cite(t)}</li>'
                    for k, t in enumerate((sec.get('items') or [])[:5], 1))
    sid = sec_anchor(i, sec)
    return (f'<section class="band band--chapter" id="{sid}" data-skel="P3" data-page-type="chapter">\n'
            '  <div class="wrap chap rv">\n'
            f'    <div class="chap__no" aria-hidden="true">{esc(num)}</div>\n'
            '    <div class="chap__body">\n'
            f'      <div class="t-eyebrow">{esc(eb)}</div>\n'
            f'      <h2 class="t-display shead__title">{esc(sec.get("title") or "")}</h2>\n'
            + (f'      <p class="t-lead">{cite(sec.get("lead"))}</p>\n' if sec.get('lead') else '')
            + (f'      <ol class="chap__list">{items}</ol>\n' if items else '')
            + '    </div>\n  </div>\n</section>')


RENDERERS = {
    'chapter': r_chapter,
    'points': r_points, 'metrics': r_metrics, 'kpi': r_kpi, 'table': r_table,
    'bar': r_bar, 'donut': r_donut, 'exhibit': r_exhibit, 'twocol': r_twocol,
    'threecol': r_threecol, 'cards': r_cards, 'split': r_split, 'comparison': r_comparison,
    'quote': r_quote, 'image': r_image, 'diagram': r_diagram, 'lane': r_lane,
    'timeline': r_timeline, 'steps': r_steps, 'heatmap': r_heatmap, 'bullet': r_bullet,
    'pyramid': r_pyramid, 'halftable': r_halftable, 'matrix': r_matrix,
    'sankey': r_info, 'treemap': r_info, 'boxplot': r_info, 'network': r_info,
    'marimekko': r_info, 'streamgraph': r_info,
}


def _fill_chrome(t: str, model: dict, body: str) -> str:
    """从模板新建时，顶栏品牌、<title> 与章节导航换成模型内容（模板自带「主标题 / 章节一」等占位不得外泄）。"""
    title = model.get('title') or ''
    sub = model.get('subtitle') or model.get('meta') or ''
    t = re.sub(r'<title>[^<]*</title>', f'<title>{esc(title)}</title>', t, count=1)
    t = re.sub(r'(<div class="brand__title">)[^<]*(</div>\s*<div class="brand__sub">)[^<]*(</div>)',
               lambda m: f'{m.group(1)}{esc(title)}{m.group(2)}{esc(sub)}{m.group(3)}', t)
    t = t.replace('<div class="t-xs">密级说明</div>', f'<div class="t-xs">{esc(model.get("meta") or "")}</div>')
    links = re.findall(r'<a class="agenda__a" href="#(s\d+)">[\s\S]*?class="agenda__t">([^<]+)<', body)
    nav = '\n'.join(f'      <a href="#{sid}">{esc(html.unescape(tt)[:10])}</a>' for sid, tt in links[:5])
    if 'id="refs"' in body:
        nav += '\n      <a href="#refs">参考资料</a>'
    t = re.sub(r'<nav class="nav">[\s\S]*?</nav>', lambda m: f'<nav class="nav">\n{nav}\n    </nav>', t, count=1)
    return t


def render_body(model: dict) -> str:
    parts = []
    # 封面
    parts.append(f'''<!-- 封面 -->
<section class="band band--fit band--accent--solid band--cover" id="cover">
  <div class="wrap cover">
    <div class="t-eyebrow cover__meta">{esc(model.get("meta") or "")}</div>
    <div class="cover__main rv">
      <h1 class="t-display cover__title">{esc(model.get("title") or "")}</h1>
      <p class="t-lead cover__sub">{esc(model.get("subtitle") or "")}</p>
    </div>
  </div>
</section>''')
    agenda = model.get('agenda') or []
    secs = [s for s in (model.get('sections') or []) if isinstance(s, dict)]

    def _chapter_key(sec, idx):
        """从 eyebrow 的 `NN ·` 前缀或 chapter 字段取章键；无则退回页码。"""
        ch = sec.get('chapter')
        if ch not in (None, ''):
            return str(ch)
        eb = (sec.get('eyebrow') or '').strip()
        m = re.match(r'^(\d{1,2})\s*[·・\-—]', eb)
        if m:
            return m.group(1).zfill(2)
        return f'{idx:02d}'

    def _chapter_title(sec):
        """章标题 = eyebrow 去掉 `NN ·` 前缀；无则退回页标题。"""
        eb = (sec.get('eyebrow') or '').strip()
        m = re.match(r'^\d{1,2}\s*[·・\-—]\s*(.+)$', eb)
        if m and m.group(1).strip():
            return m.group(1).strip()
        return sec.get('title') or ''

    # Agenda = 章节大纲（3–7 章），不是逐页标题罗列。
    # 模型给了合法 agenda（≤8 条）就原样用；否则按 eyebrow 章前缀归并，而不是按页重建。
    MAX_CH = 8
    if not agenda or len(agenda) > MAX_CH or len(agenda) == len(secs) and len(secs) > MAX_CH:
        chapters = {}
        order = []
        for i, s in enumerate(secs, 1):
            key = _chapter_key(s, i)
            if key not in chapters:
                chapters[key] = {'num': key, 'title': _chapter_title(s), 'desc': (s.get('eyebrow') or ''),
                                 'first': i, 'pages': 0}
                order.append(key)
            chapters[key]['pages'] += 1
        model['agenda'] = [[c['num'], c['title'], c['desc']] for c in (chapters[k] for k in order)]
        agenda = model['agenda']
        chapter_first = {c['num']: c['first'] for c in (chapters[k] for k in order)}
    else:
        # 模型 agenda 已是章级：锚点落到该章第一页（按 eyebrow 对齐）
        chapter_first = {}
        for i, s in enumerate(secs, 1):
            key = _chapter_key(s, i)
            chapter_first.setdefault(key, i)
            # 同时用序号兜底
            chapter_first.setdefault(f'{i:02d}', i)
        for gi, ag in enumerate(agenda, 1):
            if isinstance(ag, (list, tuple)) and ag:
                num = str(ag[0]).zfill(2) if str(ag[0]).isdigit() else str(ag[0])
                chapter_first.setdefault(num, gi)

    if agenda or not (model.get('mode') == 'architecture' and len(secs) <= 4):
        lis = []
        for gi, ag in enumerate(agenda, 1):
            num = ag[0] if isinstance(ag, (list, tuple)) and ag else f'{gi:02d}'
            title = ag[1] if isinstance(ag, (list, tuple)) and len(ag) > 1 else ''
            desc = ag[2] if isinstance(ag, (list, tuple)) and len(ag) > 2 else ''
            href_i = chapter_first.get(str(num).zfill(2)) or chapter_first.get(str(num)) or gi
            # 锚点与 open_sec 同源：该页有 anchor 则链到命名锚点
            href_id = sec_anchor(href_i, secs[href_i - 1] if 0 < href_i <= len(secs) else {})
            lis.append(
                f'      <li class="agenda__i"><a class="agenda__a" href="#{href_id}">'
                f'<span class="agenda__n">{esc(num)}</span>'
                f'<span><span class="agenda__t">{esc(title)}</span>'
                f'<div class="agenda__d">{esc(desc)}</div></span></a></li>')
        _aeb = model.get('agendaEyebrow', '目录')
        ag_eb = f'<div class="shead rv"><div class="t-eyebrow">{esc(_aeb)}</div>\n      ' if _aeb else '<div class="shead rv">'
        parts.append(f'''<section class="band band--top" id="agenda">
  <div class="wrap">
    {ag_eb}<h2 class="t-h1 shead__title">{esc(model.get("agendaTitle") or "报告大纲")}</h2></div>
    <ol class="agenda{" agenda--2col" if len(lis) > 8 else ""} rv">{''.join(lis)}</ol>
  </div>
</section>''')
    ex_n = 0
    for i, sec in enumerate(secs, 1):
        t = (sec.get('type') or 'points').lower()
        if model.get('mode') == 'research' and (t in ('exhibit', 'bar', 'halftable', 'donut') or t in LCS.INFO):
            ex_n += 1
            if not sec.get('exhibitNo'):
                sec = dict(sec)
                sec['exhibitNo'] = ex_n
        fn = RENDERERS.get(t, r_points)
        try:
            parts.append(fn(i, sec))
        except Exception as e:
            parts.append(wrap(i, t, f'    <p class="t-body">渲染失败 {esc(e)}</p>', sec))
    closing = model.get('closing') or {}
    cpts = closing.get('points') or []
    # 收尾要点可为空（美化路由：原稿收尾页只有一句致谢时不补任何文字）；eyebrow 可由模型关闭
    # M9：与 PPTX 收尾页同构——每条要点一张卡（标题 + 一句），不再是一条孤零零的列表
    def _ckv(pt):
        if isinstance(pt, (list, tuple)):
            return str(pt[0] if pt else ''), str(pt[1] if len(pt) > 1 else '')
        if isinstance(pt, dict):
            return str(pt.get('title') or pt.get('k') or ''), str(pt.get('text') or pt.get('v') or '')
        return str(pt), ''
    if cpts:
        cards = ''.join(f'      <div class="card closing__c"><h3 class="t-h3 closing__k">{esc(k)}</h3>'
                        + (f'<p class="t-body closing__v">{esc(v)}</p>' if v else '') + '</div>\n'
                        for k, v in (_ckv(x) for x in cpts[:4]))
        body = f'    <div class="grid g-{min(4, max(2, len(cpts[:4])))} rv a-stretch">\n{cards}    </div>\n'
    else:
        body = ''
    _ceb = closing.get('eyebrow', '下一步')
    ceb = f'<div class="t-eyebrow">{esc(_ceb)}</div>' if _ceb else ''
    parts.append(f'''<section class="band band--accent" id="closing">
  <div class="wrap">
    <div class="shead rv">{ceb}
      <h2 class="t-h1 shead__title">{esc(closing.get("title") or "收尾")}</h2></div>
{body}  </div>
</section>''')
    # 参考资料：只列模型给的真实来源；无真实来源整节省略（禁止占位条目）
    refs_src = model.get('refs') or model.get('references') or []
    real_refs = []
    for r in refs_src:
        if isinstance(r, dict):
            name = (r.get('name') or r.get('title') or '').strip()
            time_ = (r.get('time') or r.get('date') or '').strip()
            caliber = (r.get('caliber') or r.get('note') or '').strip()
            url = (r.get('url') or r.get('link') or '').strip()
        elif isinstance(r, (list, tuple)) and r:
            name = str(r[0]).strip() if r[0] else ''
            time_ = str(r[1]).strip() if len(r) > 1 and r[1] else ''
            caliber = str(r[2]).strip() if len(r) > 2 and r[2] else ''
            url = str(r[3]).strip() if len(r) > 3 and r[3] else ''
        else:
            name = str(r or '').strip()
            time_ = caliber = url = ''
        # 拦占位串：宁缺毋假
        if not name or any(p in name for p in ('来源名称', '替换为真实来源', '来源 N', '某行业报告')):
            continue
        if time_ and any(p in time_ for p in ('YYYY-MM', 'YYYY', '2026-01；口径')):
            time_ = ''
        real_refs.append((name, time_, caliber, url))
    if real_refs:
        ext = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
               'stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
               '<path d="M15 3h6v6M10 14 21 3"/></svg>')
        rows = []
        for n, (name, time_, caliber, url) in enumerate(real_refs, 1):
            label = esc(name)
            if url and url.startswith(('http://', 'https://', './', '../')) and 'example.com' not in url:
                label = (f'<a class="ref-link" href="{esc(url)}" target="_blank" rel="noopener">'
                         f'{esc(name)}{ext}</a>')
            rows.append(f'          <tr id="ref-{n}"><td class="k">[{n}]</td><td>{label}</td>'
                        f'<td>{esc(time_)}</td><td>{esc(caliber)}</td></tr>')
        parts.append(f'''<section class="band band--tint" id="refs">
  <div class="wrap">
    <div class="shead rv"><div class="t-eyebrow">参考资料</div>
      <h2 class="t-h1 shead__title">{esc(model.get("refsTitle") or "数据来源与口径说明")}</h2></div>
    <div class="tbl-wrap rv">
      <table>
        <thead><tr><th style="width:6%">编号</th><th style="width:30%">来源</th>
          <th style="width:14%">时间</th><th>口径说明</th></tr></thead>
        <tbody>
{chr(10).join(rows)}
        </tbody>
      </table>
    </div>
  </div>
</section>''')
    # 无真实来源 → 不渲染 #refs 整节（也不写占位）
    return '\n\n'.join(parts)


def load_model(path: Path) -> dict:
    try:
        txt = path.read_text(encoding='utf-8')
    except FileNotFoundError:
        raise SystemExit(f'模型文件不存在: {path}')
    except UnicodeDecodeError as e:
        raise SystemExit(f'模型文件不是合法 UTF-8: {path}（{e}）')
    except OSError as e:
        raise SystemExit(f'模型文件读取失败: {path}（{e}）')
    if path.suffix.lower() == '.json':
        try:
            model = _strict_decoder().decode(txt)
        except json.JSONDecodeError as e:
            raise SystemExit(f'模型不是合法 JSON: {path}（{e}）')
        except ValueError as e:
            raise SystemExit(f'模型不是合法 JSON: {path}（{e}）')
        if not isinstance(model, dict):
            raise SystemExit(f'模型根节点必须是对象: {path}（得到 {type(model).__name__}）')
        return model
    span = extract_model_span(txt)
    if not span:
        raise SystemExit('未找到 window.REPORT_MODEL')
    if not isinstance(span[2], dict):
        raise SystemExit(f'REPORT_MODEL 根节点必须是对象（得到 {type(span[2]).__name__}）')
    return span[2]


def _sync_html_attrs(html: str, model: dict) -> str:
    """<html> 的 data-style / data-theme / data-density 与模型同源（换风格 = 换 token + 密度档）。"""
    st = model.get('style')
    sg = ((LC.get('styleGrammar') or {}).get('styles') or {}).get(st or '') or {}
    m = re.search(r'<html\b[^>]*>', html)
    if not m:
        return html
    tag = m.group(0)
    for k, v in (('data-style', st), ('data-theme', model.get('theme')), ('data-density', sg.get('density'))):
        if not v:
            continue
        if re.search(rf'\s{k}="[^"]*"', tag):
            tag = re.sub(rf'\s{k}="[^"]*"', f' {k}="{v}"', tag)
        else:
            tag = tag[:-1] + f' {k}="{v}">'
    return html[:m.start()] + tag + html[m.end():]


def _strip_refs_nav(html: str, body: str) -> str:
    """无真实来源（正文不含 #refs 节）时，摘掉导航/收尾的「参考资料」入口，避免悬空锚点。"""
    if 'id="refs"' in body:
        return html
    html = re.sub(r'\s*<a[^>]*href="#refs"[^>]*>[\s\S]*?</a>', '', html)
    return html


def main() -> int:
    ap = argparse.ArgumentParser(description='从 REPORT_MODEL 渲染 HTML 正文（模型驱动生成）')
    ap.add_argument('src', help='model.json 或含 REPORT_MODEL 的 .html')
    ap.add_argument('--template', help='模式模板名 presentation|research|architecture 或路径')
    ap.add_argument('--out', help='输出 HTML')
    ap.add_argument('--inplace', action='store_true', help='就地替换 src 的 CONTENT 区')
    ap.add_argument('--body-only', action='store_true', help='只打印正文片段')
    ap.add_argument('--model', help='配合 --inplace：以该 model.json 为唯一事实源重渲染 src（示例再生用）')
    args = ap.parse_args()

    src = Path(args.src)
    model = load_model(Path(args.model) if args.model else src)
    # M2 同源求解：与 build_pptx.js 共用容量模型（lib_solver.py ≡ lib_solver.js，金样校验）。
    # 超载页先拆续页再渲染，HTML 与 PPTX 页序一致；拆页后的模型同时写回 REPORT_MODEL。
    sys.path.insert(0, str(ROOT / 'scripts'))
    import lib_solver  # noqa: E402
    model, split_log = lib_solver.split_model(model)
    for lg in split_log:
        print(f'[render_from_model] 超载拆页：「{lg["title"]}」({lg["type"]} 容量 {round(lg["ratio"] * 100)}% → {lg["parts"]} 页)',
              file=sys.stderr)
    global SKIN
    sg = ((LC.get('styleGrammar') or {}).get('styles') or {}).get(model.get('style') or '') or {}
    SKIN = dict(sg.get('chartSkin') or {})
    body = render_body(model)
    # M7 信息密度：低密度页在渲染时就提示（门禁 = check_density.py --strict）
    _mode = model.get('mode') or 'presentation'
    for _i, _sec in enumerate(model.get('sections') or []):
        for _lv, _rule, _msg in LD.check_section(_sec, _mode):
            print(f'[render_from_model] 信息密度 {_lv} p{_i + 1}「{(_sec.get("title") or "")[:18]}」{_rule}：{_msg}',
                  file=sys.stderr)

    if args.body_only:
        sys.stdout.write(body)
        return 0

    if args.inplace:
        t = src.read_text(encoding='utf-8')
        if not CONTENT_RE.search(t):
            print('错误：--inplace 需要 __TOPPPT_CONTENT__ 标记', file=sys.stderr)
            return 2
        t = CONTENT_RE.sub(
            r'\1\n' + body.replace('\\', '\\\\') + r'\n\2', t, count=1)
        # 同步模型（确保与渲染源一致；span 精确定位，模型字符串含 `};` 也不写坏）
        t = replace_model_json(t, model)
        t = _strip_refs_nav(t, body)
        t = _sync_html_attrs(t, model)
        # 顶栏 / 页脚仍是模板占位（主标题、章节一、报告名、密级说明）时一并换成模型内容；作者自定义过的不动
        if re.search(r'>(主标题|报告名|报告标题|架构标题)</div>|>章节一</a>|>密级说明<', t):
            t = _fill_chrome(t, model, body)
        try:
            src.write_text(t, encoding='utf-8')
        except OSError as e:
            print(f'错误：--inplace 写回失败 {src}（{e}）', file=sys.stderr)
            return 1
        if args.model:
            Path(args.model).write_text(json.dumps(model, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'已按模型重渲染正文：{src}（{len(body)} 字符）')
        print(f'  下一步: python scripts/validate_report.py "{src}" --strict')
        return 0

    mode = model.get('mode') or 'presentation'
    tpl = args.template or mode
    tpl_path = Path(tpl) if Path(tpl).exists() else TPL / f'{tpl}.html'
    if not tpl_path.exists():
        print(f'错误：模板不存在 {tpl_path}', file=sys.stderr)
        return 2
    t = tpl_path.read_text(encoding='utf-8')
    if not CONTENT_RE.search(t):
        print('错误：模板缺少 CONTENT 标记', file=sys.stderr)
        return 2
    t = CONTENT_RE.sub(r'\1\n' + body.replace('\\', '\\\\') + r'\n\2', t, count=1)
    t = replace_model_json(t, model)
    t = _strip_refs_nav(t, body)
    t = _sync_html_attrs(t, model)
    t = _fill_chrome(t, model, body)
    out = Path(args.out or (src.with_suffix('.html')))
    try:
        out.write_text(t, encoding='utf-8')
    except OSError as e:
        print(f'错误：输出写入失败 {out}（{e}）', file=sys.stderr)
        return 1
    print(f'已从模型生成：{out}  sections={len(model.get("sections") or [])}')
    print(f'  下一步: python scripts/validate_report.py "{out}" --strict')
    return 0


if __name__ == '__main__':
    sys.exit(main())
