"""信息密度度量（单源）：页面构成、文字量、数据点、元素种类、低密度判定。

被 check_density.py（门禁）、render_from_model.py（选版升级提示）与 tests 共用。
口径：只看正文区——标题 / eyebrow / 页脚来源不计入文字量；注释与结论条单列为「辅助元素」，
不能顶替正文（「一图一句」= 图表 + 结论条/注释，没有解读要点、关键数字或表格）。
"""
from __future__ import annotations

import re

# 视觉证据页型（图表 / 信息图）
CHART_TYPES = {'bar', 'donut', 'exhibit', 'halftable', 'heatmap', 'treemap', 'marimekko',
               'streamgraph', 'sankey', 'boxplot', 'bullet'}
# 结构图页型（架构模式的拓扑 / 分层图）：要求配说明，不强求关键数字
DIAGRAM_TYPES = {'diagram', 'network', 'lane', 'pyramid', 'matrix'}
# 不参与密度门禁的页型（节奏页 / 引言页 / 纯指标页本身就是数字）
EXEMPT_TYPES = {'chapter', 'quote', 'cover', 'closing', 'info'}
# 图表数据可推导关键数字的子类型（单序列数值）
DERIVABLE_CHARTS = {'bar', 'hbar', 'donut', 'pie', 'line', 'area', 'lollipop', 'dotplot', 'rose',
                    'radialbar', 'funnel', 'vsbar'}

NUM_RE = re.compile(r'[-+]?\d+(?:[.,]\d+)?')

# 三种模式的分档阈值：body=正文区文字下限，max=上限（超过即提示拥挤），
# kinds=证据类元素种类下限，readout=图表页解读要点最少条数，data=图表页数据点下限
TIERS = {
    'presentation': {'body': 40, 'max': 320, 'kinds': 2, 'readout': 2, 'data': 3},
    'research':     {'body': 80, 'max': 900, 'kinds': 2, 'readout': 3, 'data': 3},
    'architecture': {'body': 50, 'max': 520, 'kinds': 2, 'readout': 2, 'data': 0},
}

SKIP_KEYS = {'type', 'title', 'eyebrow', 'id', 'anchor', 'variant', 'layoutPreset', 'exhibitNo',
             'footnote', 'source', 'note', 'soWhat', 'verdict', 'highlightCol', 'columns', 'max',
             'unit', 'flags', 'cap', 'scaleLabel', 'draft', 'icon', 's', 'state', 'colors',
             'dataTable', 'centerLabel', 'start', 'theme'}


def _strings(v, out, key=None):
    if key in SKIP_KEYS:
        return
    if isinstance(v, str):
        out.append(v)
    elif isinstance(v, (list, tuple)):
        for x in v:
            _strings(x, out)
    elif isinstance(v, dict):
        for k, x in v.items():
            _strings(x, out, k)


def _nums(v, acc):
    if isinstance(v, bool):
        return
    if isinstance(v, (int, float)):
        acc[0] += 1
    elif isinstance(v, (list, tuple)):
        for x in v:
            _nums(x, acc)
    elif isinstance(v, dict):
        for k, x in v.items():
            if k in ('values', 'cells', 'series', 'groups', 'flows', 'items', 'start', 'value', 'v'):
                _nums(x, acc)
            elif isinstance(x, (list, dict)):
                _nums(x, acc)


def readout_items(sec: dict) -> list:
    """图表页的解读要点：points（及其别名 readout）。"""
    r = sec.get('readout') or sec.get('points') or []
    return [x for x in r if x]


# ── M8：解读要点「复述数字」检测 ─────────────────────────────────────────────
# 解读 = 原因 / 影响 / 下一步；只把图上的数字换个说法再念一遍不算解读。
ECHO_STOP = ('最高', '最低', '最大', '最小', '增长', '下降', '提升', '上升', '降到', '降至', '升至', '增至', '增加', '减少',
             '合计', '同比', '环比', '百分点', '占比', '占', '比', '从', '到', '至', '由', '为', '达', '约', '近', '超',
             '共', '个', '项', '倍', '点', '年', '月', '季度', '期', '和', '与', '及', '的', '了', '是', '在', '相对',
             '对比', '变化', '分别', '其中', '仅', '只', '已', '再', '又', '均', '各',
             '领先', '跟进', '最弱', '居中', '垫底', '居首', '最多', '最快', '最慢', '最长', '最短', '唯一', '首次',
             '超过', '高于', '低于', '不到', '不足', '过半', '逐年', '持续', '见底', '回升', '新高', '收盘', '中位',
             '区间', '集中', '分散', '放行', '进入', '流失', '签下', '第', '单季', '单月', '每', '分', '家', '周',
             '名', '位', '高', '低', '多', '少', '大', '小', '上', '下', '前', '后', '之', '内', '外', '一', '二',
             '两', '三', '四', '五', '六', '七', '八', '九', '十')
REASON_MARKERS = ('因为', '由于', '原因', '源于', '导致', '驱动', '带来', '拖累', '受益', '得益', '意味', '说明', '表明',
                  '所以', '因此', '于是', '影响', '风险', '代价', '建议', '下一步', '需要', '需', '应', '要先', '优先',
                  '关键', '瓶颈', '取决于', '前提', '若', '如果', '一旦', '才能', '可以', '可', '将', '会', '避免', '防止')
_PUNCT_RE = re.compile(r'[\s\W_]+', re.U)


def _point_text(p) -> str:
    if isinstance(p, (list, tuple)):
        return ' '.join(str(x) for x in p if isinstance(x, (str, int, float)))
    if isinstance(p, dict):
        return ' '.join(str(p.get(k) or '') for k in ('title', 'text', 'k', 'v', 'desc'))
    return str(p or '')


def _chart_tokens(sec: dict) -> list:
    toks = []
    for c in [sec.get('chart') or {}, sec.get('chart2') or {}] + list(sec.get('minis') or []):
        if isinstance(c, dict):
            for k in ('labels', 'series'):
                for x in (c.get(k) or []):
                    if isinstance(x, str):
                        toks.append(x)
                    elif isinstance(x, dict) and isinstance(x.get('name'), str):
                        toks.append(x['name'])
            if isinstance(c.get('unit'), str):
                toks.append(c['unit'])
    for k in ('rowHeads', 'colHeads', 'labels'):
        toks += [x for x in (sec.get(k) or []) if isinstance(x, str)]
    return sorted({t for t in toks if t}, key=len, reverse=True)


def echo_points(sec: dict) -> list:
    """返回只复述图表数字的要点序号：含数字、无原因/影响/下一步信号，
    去掉数字、图表标签、单位与复述用词后剩余实义字 < 6。"""
    toks = _chart_tokens(sec)
    out = []
    for i, p in enumerate(readout_items(sec)):
        t = _point_text(p)
        if not NUM_RE.search(t) or any(m in t for m in REASON_MARKERS):
            continue
        rest = NUM_RE.sub('', t)
        for tok in toks:
            rest = rest.replace(tok, '')
        for w in ECHO_STOP:
            rest = rest.replace(w, '')
        rest = re.sub(r'[%％a-zA-Z×→~～·]+', '', rest)
        if len(_PUNCT_RE.sub('', rest)) < 8:
            out.append(i)
    return out


def key_metrics(sec: dict) -> list:
    return [x for x in (sec.get('keyMetrics') or sec.get('metrics') or []) if x]


def derive_key_metrics(chart: dict, ptype: str = '') -> list:
    """从图表数据推导关键数字（只做算术，不编造）：最高 / 最低（或前两项合计）/ 首末变化。
    返回 [[值, 标签], ...]；数据不足或非单序列数值时返回 []。与 build_pptx.js deriveKeyMetrics 同口径。"""
    ch = chart or {}
    t = str(ch.get('type') or 'bar').lower()
    if ptype == 'donut':
        t = 'donut'
    labels, values = ch.get('labels') or [], ch.get('values') or []
    if t not in DERIVABLE_CHARTS or len(labels) < 3 or len(values) != len(labels):
        return []
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
        return []
    unit = str(ch.get('unit') or '')

    def fmt(v, u=unit):
        s = f'{v:.1f}'.rstrip('0').rstrip('.') if abs(v - round(v)) > 1e-9 else str(int(round(v)))
        return s + u

    out = []
    imax = max(range(len(values)), key=lambda i: values[i])
    if t in ('donut', 'pie'):
        tot = sum(values) or 1
        share = values[imax] / tot * 100
        out.append([fmt(values[imax]) if unit == '%' else f'{share:.0f}%', f'{labels[imax]}占比最高'])
        order = sorted(range(len(values)), key=lambda i: -values[i])
        top2 = (values[order[0]] + values[order[1]]) / tot * 100
        out.append([f'{top2:.0f}%', f'前两项合计（{labels[order[0]]}、{labels[order[1]]}）'])
        out.append([str(len(values)), '构成项'])
        return out
    imin = min(range(len(values)), key=lambda i: values[i])
    out.append([fmt(values[imax]), f'最高 · {labels[imax]}'])
    out.append([fmt(values[imin]), f'最低 · {labels[imin]}'])
    a, b = values[0], values[-1]
    temporal = all(re.search(r'\d', str(x)) for x in labels)
    if not temporal:
        # 类别轴：首末变化无意义 → 给极差
        out.append([fmt(values[imax] - values[imin], 'pt' if unit == '%' else unit), '最高与最低之差'])
    elif unit == '%':
        d = b - a
        out.append([('+' if d >= 0 else '') + fmt(d, 'pt'), f'{labels[0]} → {labels[-1]}'])
    elif a:
        out.append([f'{b / a:.1f}×'.replace('.0×', '×'), f'{labels[-1]} 相对 {labels[0]}'])
    return out


def analyze_section(sec: dict, derive: bool = True) -> dict:
    """derive=False：不计渲染期自动推导的关键数字（用于诊断 M7 之前的产出）。"""
    t = sec.get('type') or 'points'
    texts: list = []
    _strings(sec, texts)
    body = ''.join(texts)
    acc = [0]
    _nums(sec, acc)
    data = acc[0] + len(NUM_RE.findall(body))
    kinds = set()
    ch = sec.get('chart') or {}
    if t in CHART_TYPES or ch.get('labels') or ch.get('values'):
        kinds.add('chart')
    if sec.get('chart2'):
        kinds.add('chart2')
    if sec.get('minis'):
        kinds.add('minis')
    if t in DIAGRAM_TYPES or sec.get('layers') or sec.get('lanes') or sec.get('nodes'):
        kinds.add('diagram')
    if key_metrics(sec) or sec.get('hero'):
        kinds.add('metrics')
    elif derive and sec.get('compose') != 'off' and derive_key_metrics(ch, t):
        kinds.add('metrics')   # 渲染时自动推导的关键数字条（复合版式升级）
    ro = readout_items(sec)
    if ro or sec.get('paragraphs') or sec.get('aside') or sec.get('legend'):
        kinds.add('readout')
    if sec.get('table'):
        kinds.add('table')
    if sec.get('cards'):
        kinds.add('cards')
    if sec.get('steps') or sec.get('phases'):
        kinds.add('sequence')
    if sec.get('left') and sec.get('right'):
        kinds.add('compare')
    if sec.get('image') or sec.get('images'):
        kinds.add('image')
    if sec.get('quote'):
        kinds.add('quote')
    support = set()
    if sec.get('soWhat') or sec.get('verdict'):
        support.add('conclusion')
    if sec.get('footnote') or sec.get('note') or sec.get('source'):
        support.add('note')
    if (ch.get('annotations')):
        support.add('annotation')
    return {'type': t, 'kinds': sorted(kinds), 'support': sorted(support),
            'body_chars': len(body), 'data_points': data, 'readout_n': len(ro),
            'is_chart': 'chart' in kinds and t not in DIAGRAM_TYPES,
            'derivable': bool(derive_key_metrics(ch, t))}


def classify(a: dict) -> str:
    """低密度类别：one-chart-one-line（一图一句）/ chart-plus-box（图 + 薄文本框）/ ''。"""
    if not a['is_chart']:
        return ''
    ev = set(a['kinds']) - {'chart'}
    if not ev:
        return 'one-chart-one-line'
    if ev <= {'readout'} and (a['readout_n'] <= 2):
        return 'chart-plus-box'
    return ''


def check_section(sec: dict, mode: str) -> list:
    """返回 [(级别, 规则, 说明)]；级别 FAIL / WARN。"""
    t = sec.get('type') or 'points'
    if t in EXEMPT_TYPES or sec.get('draft'):
        return []
    tier = TIERS.get(mode, TIERS['presentation'])
    a = analyze_section(sec)
    out = []
    if a['is_chart']:
        has_km = bool(key_metrics(sec)) or a['derivable'] or t in ('halftable',) or bool(sec.get('table'))
        if a['readout_n'] < tier['readout'] and not sec.get('paragraphs'):
            out.append(('FAIL', 'DENSITY_READOUT',
                        f'图表页缺解读要点（{a["readout_n"]}/{tier["readout"]} 条）：补 points 写「看到什么 → 意味着什么」'))
        if not has_km:
            out.append(('FAIL', 'DENSITY_KEYNUM', '图表页缺关键数字：补 keyMetrics（或用可推导的单序列图表）'))
        ech = echo_points(sec)
        if ech and len(ech) * 2 >= max(1, a['readout_n']):
            out.append(('WARN', 'DENSITY_ECHO',
                        f'解读要点第 {"、".join(str(k + 1) for k in ech)} 条只是复述图上数字：改写成原因 / 影响 / 下一步（只用已有事实）'))
        pts = readout_items(sec)
        if pts and not any(any(m in _point_text(p) for m in REASON_MARKERS) for p in pts):
            out.append(('WARN', 'DENSITY_NO_INSIGHT',
                        '解读要点没有一条讲原因 / 影响 / 下一步：至少一条写「为什么」或「所以要做什么」'))
        if len(sec.get('minis') or []) > 2:
            out.append(('FAIL', 'DENSITY_MINIS_MAX', f'小图组最多 2 张（现 {len(sec["minis"])} 张）：多出的拆页或并入主图'))
        if a['data_points'] < tier['data']:
            out.append(('WARN', 'DENSITY_DATA', f'数据点 {a["data_points"]} 少于 {tier["data"]}'))
    elif t in DIAGRAM_TYPES:
        if 'readout' not in a['kinds'] and a['body_chars'] < tier['body'] * 2:
            out.append(('WARN', 'DENSITY_DIAGRAM', '结构图缺说明栏（aside / legend / points）'))
    if a['body_chars'] < tier['body'] and (a['is_chart'] or a['data_points'] < 6):
        out.append(('FAIL', 'DENSITY_TEXT', f'正文区文字 {a["body_chars"]} 字，低于 {mode} 下限 {tier["body"]}'))
    C = compose_on(sec, t)
    if C and C['form'] == 'band' and (len(C['km']) > 2 or len(C['pts']) > 3):
        out.append(('WARN', 'DENSITY_BAND_CAP', '解读带最多 2 个关键数字 + 3 条要点，多出的不会渲染：请精简或拆页'))
    if a['body_chars'] > tier['max']:
        out.append(('WARN', 'DENSITY_CROWD', f'正文区文字 {a["body_chars"]} 字，超过 {mode} 上限 {tier["max"]}，注意留白'))
    return out


COMPOSE_SIDE = {'bar', 'donut', 'exhibit'}
COMPOSE_BAND = {'halftable', 'heatmap', 'bullet', 'treemap', 'marimekko', 'streamgraph', 'sankey', 'boxplot',
                'network', 'lane', 'pyramid', 'matrix', 'metrics'}


def compose_km(sec: dict, ptype: str) -> list:
    if sec.get('compose') == 'off':
        return []
    km = [x for x in (sec.get('keyMetrics') or []) if x]
    if km:
        return km[:4]
    if ptype == 'halftable' or sec.get('metrics'):
        return []
    return derive_key_metrics(sec.get('chart') or {}, ptype)[:3]


def compose_on(sec: dict, ptype: str):
    """复合版式判定（与 build_pptx.js composeOn 同口径）：返回 None | {'form','pts','km'}。"""
    if sec.get('compose') == 'off':
        return None
    pts = readout_items(sec)
    km = compose_km(sec, ptype)
    extra = bool(sec.get('chart2') or sec.get('minis'))
    if ptype in COMPOSE_SIDE and (pts or km or extra):
        return {'form': 'side', 'pts': pts, 'km': km}
    if ptype in COMPOSE_BAND and (pts or km):
        return {'form': 'band', 'pts': pts, 'km': km}
    return None
