#!/usr/bin/env python3
"""Python 求解器 ↔ JS 金样一致性（HTML 与 PPTX 拆页同源的保证）。"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import lib_solver as S  # noqa: E402

gold = json.loads((Path(__file__).parent / 'golden.json').read_text(encoding='utf-8'))
item = lambda i, n=3: ['要点 ' + str(i), '说明文字' * n]
F = {
    'points': lambda n: {'type': 'points', 'title': 'P', 'points': [item(i) for i in range(n)]},
    'cards': lambda n: {'type': 'cards', 'title': 'C', 'cards': [item(i) for i in range(n)]},
    'steps': lambda n: {'type': 'steps', 'title': 'S', 'steps': [item(i) for i in range(n)]},
    'timeline': lambda n: {'type': 'timeline', 'title': 'T', 'phases': [item(i) for i in range(n)]},
    'table': lambda n: {'type': 'table', 'title': 'TB', 'table': {'head': ['a', 'b'], 'rows': [['r' + str(i), 'v'] for i in range(n)]}},
    'twocol': lambda n: {'type': 'twocol', 'title': '2C', 'paragraphs': [item(i, 6) for i in range(n)]},
    'threecol': lambda n: {'type': 'threecol', 'title': '3C', 'paragraphs': [item(i, 4) for i in range(n)]},
    'metrics': lambda n: {'type': 'metrics', 'title': 'M', 'metrics': [['指标' + str(i), str(i * 10)] for i in range(n)]},
    'bullet': lambda n: {'type': 'bullet', 'title': 'B', 'items': ['条目 ' + str(i) for i in range(n)]},
    'quote': lambda n: {'type': 'quote', 'title': 'Q', 'quote': '金句'},
}
bad = []
for mode in ('presentation', 'research', 'architecture'):
    for fam, mk in F.items():
        for n in (3, 6, 12, 20):
            sec = dict(mk(n), soWhat='结论', footnote='来源')
            k = f'{mode}/{fam}/{n}'
            if S.capacity(sec, mode) != gold['capacity'][k]:
                bad.append((k, 'capacity', S.capacity(sec, mode), gold['capacity'][k]))
            m, _ = S.split_model({'mode': mode, 'sections': [sec]})
            got = [{'title': x['title'], 'soWhat': bool(x.get('soWhat')), 'footnote': bool(x.get('footnote')),
                    'n': S._js_len(x)} for x in m['sections']]
            if got != gold['split'][k]:
                bad.append((k, 'split', got, gold['split'][k]))
for key, v in gold['rows'].items():
    a, n = key.split('x')
    r = S.rows(float(a), int(n), pref=0.7, mn=0.3, mx=1.4, gap=0.12)
    if r != v:
        bad.append((key, 'rows', r, v))
if bad:
    print('[test_solver_py] FAIL：Python 与 JS 求解不一致', len(bad))
    for b in bad[:6]:
        print('  ', b)
    sys.exit(1)
print(f"[test_solver_py] PASS · {len(gold['capacity'])} 用例与 JS 金样逐值一致（HTML/PPTX 拆页同源）")
