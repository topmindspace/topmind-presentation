#!/usr/bin/env python3
"""M9：复述检测小样本评测（8 条复述 + 8 条真解读，人工标注）。要求检出 ≥7/8、误报 ≤1/8。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import lib_density as LD  # noqa: E402

bar = {'type': 'bar', 'title': '研发域一年内有望反超', 'chart': {'labels': ['客服', '财务', '营销', '研发'], 'values': [9, 11, 13, 15], 'unit': 'pt'}}
tm = {'type': 'treemap', 'title': '规模化企业行业构成', 'unit': '家', 'items': [['制造', 3], ['金融', 2], ['互联网', 2]]}
hm = {'type': 'heatmap', 'rowHeads': ['金融', '制造'], 'colHeads': ['客服', '研发', '供应链'], 'cells': [[78, 46, 38], [44, 29, 57]]}
ECHO = [(bar, ['研发 15pt 领先', '客服 9pt，相差 6pt']), (bar, ['四域都在增长', '研发 15、营销 13、财务 11、客服 9']),
        (tm, ['制造 3 家居首', '金融、互联网各 2 家']), (tm, ['制造 3 家', '说明制造 3 家']),
        (hm, ['金融客服 78 最高', '供应链 38 最低']), (hm, ['制造供应链 57', '是制造五域中最高，研发仅 29']),
        (bar, ['研发增幅 15pt', '因此研发 15pt 最高']), (hm, ['金融：客服 78 领先', '研发 46、供应链 38'])]
INSIGHT = [(bar, ['差距 6pt', '按当前增幅差推算，研发域在工具链补齐后有望一年内反超客服']), (bar, ['研发 15pt', '单任务成本须低于人工基线 30%']),
           (tm, ['制造与金融合计 5 家', '共同点是流程标准、容错边界清晰，可以直接复制']), (tm, ['互联网 2 家', '规模化并不局限于传统强流程行业']),
           (hm, ['金融客服 78 分', '话术可沉淀，是最容易复制的样板']), (hm, ['制造研发 29 分', '工具链缺口是主因，先补工具链再谈放量']),
           (bar, ['四域均为正增长', '增长不靠单一业务域拉动']), (hm, ['供应链 38 最弱', '数据接口分散，先做主数据治理'])]


def hit(sec, p):
    return LD.echo_points(dict(sec, points=[p])) == [0]


tp = sum(hit(s, p) for s, p in ECHO)
fp = sum(hit(s, p) for s, p in INSIGHT)
print(f'[echo-eval] 复述检出 {tp}/{len(ECHO)} · 误报 {fp}/{len(INSIGHT)}')
sys.exit(0 if tp >= 7 and fp <= 1 else 1)
