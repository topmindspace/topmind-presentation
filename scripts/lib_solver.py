# -*- coding: utf-8 -*-
"""topmind-presentation · 布局求解器 Python 端（M2，与 scripts/lib_solver.js 逐值同口径）

HTML 渲染（render_from_model.py）与 PPTX 渲染（build_pptx.js）必须对同一模型做出**同样的**
容量判断与拆页结果，否则两端页序漂移。本模块是 JS 版的逐行移植，tests/solver/test_solver_py.py
用 JS 生成的同一份金样（tests/solver/golden.json）校验两端一致。改一端必须同步改另一端。
"""
import json
import math

CAP = {
    'presentation': {'points': 6, 'cards': 6, 'steps': 6, 'table': 8, 'comparison': 5, 'timeline': 6, 'bullet': 7, 'twocol': 6, 'threecol': 9, 'metrics': 6},
    'research':     {'points': 8, 'cards': 8, 'steps': 7, 'table': 14, 'comparison': 7, 'timeline': 7, 'bullet': 10, 'twocol': 8, 'threecol': 12, 'metrics': 6},
    'architecture': {'points': 7, 'cards': 6, 'steps': 7, 'table': 10, 'comparison': 5, 'timeline': 6, 'bullet': 8, 'twocol': 6, 'threecol': 9, 'metrics': 6},
}


def _r(v):
    return math.floor(v * 1000 + 0.5) / 1000


def _set(key):
    def f(s, a):
        n = dict(s)
        n[key] = a
        if key == 'steps':
            n.pop('groups', None)
        return n
    return f


def _set_table(s, a):
    n = dict(s)
    t = dict(s.get('table') or {})
    t['rows'] = a
    n['table'] = t
    return n


LISTS = {
    'points': (lambda s: s.get('points'), _set('points')),
    'cards': (lambda s: s.get('cards'), _set('cards')),
    'steps': (lambda s: s.get('steps'), _set('steps')),
    'timeline': (lambda s: s.get('phases'), _set('phases')),
    'bullet': (lambda s: s.get('items'), _set('items')),
    'metrics': (lambda s: s.get('metrics'), _set('metrics')),
    'twocol': (lambda s: s.get('paragraphs'), _set('paragraphs')),
    'threecol': (lambda s: s.get('paragraphs'), _set('paragraphs')),
    'table': (lambda s: (s.get('table') or {}).get('rows'), _set_table),
}


def _js_len(obj):
    """等价于 JS 的 JSON.stringify(obj).length（UTF-16 码元计数）。"""
    s = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    return sum(2 if ord(ch) > 0xFFFF else 1 for ch in s)


def rows(avail, n, pref=None, mn=0.22, mx=None, gap=0.0, center=True):
    k = max(1, int(n))
    pref = mn if pref is None else pref
    mx = pref * 1.8 if mx is None else mx
    room = max(0.0, avail - gap * (k - 1))
    even = room / k
    size = max(mn, even) if even <= pref else min(mx, even)
    used = size * k + gap * (k - 1)
    off = max(0.0, (avail - used) / 2) if center else 0.0
    return {'size': _r(size), 'gap': gap, 'offset': _r(off), 'used': _r(used)}


# M3 密度档（风格库 styleGrammar 镜像；test_solver_py 校验与 layout-constants 一致）
DENSITY_K = {"airy": 0.9, "normal": 1.0, "dense": 1.12}
STYLE_DENSITY = {"business-blue": "normal", "apple-mono": "airy", "mckinsey": "dense", "brand-red": "normal", "warm-sand": "airy", "deep-teal": "normal", "graphite-dark": "dense", "indigo-violet": "normal", "spectrum": "dense", "ink-academic": "dense", "coral-launch": "airy", "sky-airy": "airy"}


def density_k(model):
    d = (model or {}).get('density') or STYLE_DENSITY.get((model or {}).get('style') or '') or 'normal'
    return DENSITY_K.get(d, 1)


LS_DEFAULT, LS_BASE, CHROME_GAIN = 1.5, 1.45, 1.075


def text_k(model):
    """M12：与 lib_solver.js textK 同口径（行距 1.5 折算 × 眉标关闭腾出的正文高度）。"""
    return _r((LS_BASE / LS_DEFAULT) * (1 if (model or {}).get('showEyebrow') else CHROME_GAIN))


def capacity(sec, mode, k=1, tk=1):
    t = (sec or {}).get('type')
    acc = LISTS.get(t)
    if not acc:
        return 0
    arr = acc[0](sec) or []
    cap = CAP.get(mode, CAP['presentation']).get(t, 99) * (k or 1)
    chars = _js_len(arr)
    char_cap = cap * (90 if mode == 'research' else 70) * (tk or 1)
    return _r(max(len(arr) / cap, chars / char_cap))


def split_model(model):
    mode = str(model.get('mode') or 'presentation')
    k = density_k(model)
    tk = text_k(model)
    out, log = [], []
    for sec in model.get('sections') or []:
        ratio = capacity(sec, mode, k, tk)
        acc = LISTS.get((sec or {}).get('type'))
        arr = (acc[0](sec) or []) if acc else []
        if not acc or ratio <= 1 or len(arr) < 2:
            out.append(sec)
            continue
        parts = min(len(arr), math.ceil(ratio))
        per = math.ceil(len(arr) / parts)
        for p in range(parts):
            sl = arr[p * per:(p + 1) * per]
            if not sl:
                continue
            ns = acc[1](sec, sl)
            if p > 0:
                ns = dict(ns)
                ns['title'] = str(sec.get('title') or '') + '（续）'
                ns.pop('soWhat', None)
                ns.pop('verdict', None)
            elif parts > 1:
                ns.pop('footnote', None)
            if 0 < p < parts - 1:
                ns.pop('footnote', None)
            out.append(ns)
        log.append({'title': sec.get('title'), 'type': sec.get('type'), 'ratio': ratio, 'parts': parts})
    m = dict(model)
    m['sections'] = out
    return m, log
