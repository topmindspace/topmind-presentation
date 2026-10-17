"""M13 高密度复合版式 · 双端同规则（与 build_pptx.js 的 densePlan / dashScale 同口径）。

dashboard（多图表综合页 / 仪表盘）：关键数字条（≤4，可带图标）+ 2–4 张图 + 解读行（≤3）。
magazine（杂志型图文穿插）：大图 + 观点句 + ≤2 个大数字 + ≤3 条带图标要点。

元素优先级（放不下时从低到高舍弃，舍弃项写进演讲者备注，不静默丢）：
  标题 > 图表 > 关键数字 > 解读 > 图标 > 图片说明
"""
from __future__ import annotations

import math

DASH_MAX_CHARTS = 4
DASH_MAX_KM = 4
DASH_MAX_PTS = 3
MAG_MAX_METRICS = 2
MAG_MAX_PTS = 3
SHARED_SCALE_TYPES = {'bar', 'hbar', 'line', 'stack', 'area', 'lollipop', 'dotplot'}
ORDINALS = '①②③④'


def nice_ceil(v: float) -> float:
    """共享坐标上限：取 1/2/2.5/5/10 × 10^k 中不小于 v 的最小值（与 JS niceCeil 一致）。"""
    if not v or v <= 0:
        return 0
    e = 10 ** math.floor(math.log10(v))
    for m in (1, 2, 2.5, 5, 10):
        if m * e >= v - 1e-9:
            r = round(m * e, 6)
            return int(r) if r == int(r) else r
    return round(10 * e, 6)


def dash_charts(sec: dict) -> list:
    """2–4 张图：同单位、同类数值图共享坐标上限（坐标对齐）；图注按叙事顺序编号 ①②③④。"""
    cs = [dict(c) for c in (sec.get('charts') or []) if isinstance(c, dict) and c.get('labels')][:DASH_MAX_CHARTS]
    if sec.get('sharedScale', True):
        groups: dict = {}
        for c in cs:
            if (c.get('type') or 'bar') in SHARED_SCALE_TYPES and c.get('max') is None:
                groups.setdefault(c.get('unit') or '', []).append(c)
        for g in groups.values():
            if len(g) < 2:
                continue
            vals = [abs(float(v)) for c in g for v in (c.get('values') or []) if isinstance(v, (int, float))]
            for c in g:
                for se in c.get('series') or []:
                    vals += [abs(float(v)) for v in se.get('values') or [] if isinstance(v, (int, float))]
            m = nice_ceil(max(vals) if vals else 0)
            if m:
                for c in g:
                    c['max'] = m
    for k, c in enumerate(cs):
        cap = str(c.get('cap') or '')
        c['cap'] = f'{ORDINALS[k]} {cap}'.strip() if sec.get('numbered', True) else cap
    return cs


def dash_legend(cs: list) -> list:
    """共用图例：所有多系列图的系列名一致时只画一次（返回系列名列表，否则 []）。"""
    names = [tuple(s.get('name') or '' for s in (c.get('series') or [])) for c in cs if c.get('series')]
    if len(names) >= 2 and len(set(names)) == 1 and all(names[0]):
        return list(names[0])
    return []


def kv3(m):
    """[值, 标签, 图标?] / {v,k,icon}"""
    if isinstance(m, (list, tuple)):
        return (str(m[0]) if m else ''), (str(m[1]) if len(m) > 1 else ''), (str(m[2]) if len(m) > 2 and m[2] else '')
    if isinstance(m, dict):
        return str(m.get('v') or m.get('value') or ''), str(m.get('k') or m.get('label') or ''), str(m.get('icon') or '')
    return str(m), '', ''


def pt3(p):
    """[要点, 说明, 图标?] / {k,v,icon} / 字符串"""
    if isinstance(p, (list, tuple)):
        return (str(p[0]) if p else ''), (str(p[1]) if len(p) > 1 else ''), (str(p[2]) if len(p) > 2 and p[2] else '')
    if isinstance(p, dict):
        return str(p.get('k') or p.get('t') or ''), str(p.get('v') or p.get('d') or ''), str(p.get('icon') or '')
    return str(p), '', ''


def overflow(sec: dict) -> list:
    """超出上限、被移到演讲者备注的元素（双端同口径；validate 用来确认没有静默丢弃）。"""
    t = sec.get('type')
    out = []
    if t == 'dashboard':
        out += [('chart', c.get('cap') or '') for c in (sec.get('charts') or [])[DASH_MAX_CHARTS:]]
        out += [('km', kv3(m)[0]) for m in (sec.get('keyMetrics') or [])[DASH_MAX_KM:]]
        out += [('pt', pt3(p)[0]) for p in (sec.get('points') or [])[DASH_MAX_PTS:]]
    elif t == 'magazine':
        out += [('km', kv3(m)[0]) for m in (sec.get('metrics') or [])[MAG_MAX_METRICS:]]
        out += [('pt', pt3(p)[0]) for p in (sec.get('points') or [])[MAG_MAX_PTS:]]
    return out


# ── M13 简单版式（focus）：一个锚点 + 至多一个从属元素，用留白、不对称和放大的锚点出设计感 ──
FOCUS_KINDS = ('icon', 'text', 'statement', 'number', 'chart', 'iconText', 'twoText')
FOCUS_VARIANTS = ('left', 'center', 'split')


def focus_kind(sec: dict) -> str:
    """按载荷推断简单页种类（显式 focus 优先）。"""
    k = sec.get('focus')
    if k in FOCUS_KINDS:
        return k
    if sec.get('chart'):
        return 'chart'
    if sec.get('number'):
        return 'number'
    if sec.get('texts') and len(sec.get('texts')) >= 2:
        return 'twoText'
    if sec.get('icon') and sec.get('text'):
        return 'iconText'
    if sec.get('icon'):
        return 'icon'
    if sec.get('statement'):
        return 'statement'
    return 'text'


def focus_variant(sec: dict) -> str:
    """选用规则：显式 variant 优先；数字 / 观点默认 left（不对称大锚点）；图标 + 文本、两段文本默认 split；
    单图标、单图表默认 center。"""
    v = sec.get('variant')
    if v in FOCUS_VARIANTS:
        return v
    k = focus_kind(sec)
    return {'number': 'left', 'statement': 'left', 'text': 'left', 'iconText': 'split',
            'twoText': 'split', 'icon': 'center', 'chart': 'center'}.get(k, 'left')
