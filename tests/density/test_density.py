#!/usr/bin/env python3
"""M7 信息密度门禁自测：低密度页必拦、复合版式页放行、关键数字推导双端一致。"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import lib_density as LD  # noqa: E402

fails = []


def ok(cond, msg):
    if not cond:
        fails.append(msg)


bar = {'labels': ['2026Q3', 'Q4', '2027Q1', 'Q2'], 'values': [30, 45, 55, 60], 'unit': '%'}
cat = {'type': 'hbar', 'labels': ['客服', '财务', '营销', '研发'], 'values': [72, 57, 48, 38], 'unit': '%'}
donut = {'labels': ['A', 'B', 'C'], 'values': [70, 22, 8], 'unit': '%'}

# 1) 一图一句：图表 + 结论条 → FAIL（演示 / 研究都拦）
one = {'type': 'bar', 'title': '采纳率四步走至 60%', 'chart': bar, 'soWhat': '一句话结论'}
for mode in ('presentation', 'research'):
    rules = {r for lv, r, _ in LD.check_section(one, mode) if lv == 'FAIL'}
    ok('DENSITY_READOUT' in rules, f'{mode}: 一图一句未被拦截 {rules}')
wf = dict(one, chart={'type': 'waterfall', 'labels': ['基线', '增量', '现值'], 'values': [38, 14, 52], 'unit': 'pt'})
ok(LD.classify(LD.analyze_section(wf)) == 'one-chart-one-line', '一图一句分类错误')
# 可推导关键数字的图表：渲染时自动升级（加关键数字条），不再算「一图一句」，但缺解读仍 FAIL
ok(LD.classify(LD.analyze_section(one)) == '', '自动升级页分类错误')
ok(LD.classify(LD.analyze_section(one, derive=False)) == 'one-chart-one-line', '诊断口径（不推导）分类错误')

# 2) 图 + 薄文本框（1 条要点）→ 分类为 chart-plus-box，演示模式要求 ≥2 条
thin = dict(wf, points=[['只有一条', '说明']])
ok(LD.classify(LD.analyze_section(thin)) == 'chart-plus-box', '图+薄文本框分类错误')
ok(any(r == 'DENSITY_READOUT' for _, r, _ in LD.check_section(thin, 'presentation')), '薄文本框未被拦截')

# 3) 复合版式：解读 ≥2 + 可推导关键数字 → 通过
comp = dict(one, points=[['前两季爬坡最快', 'Q4 单季 +15pt'], ['之后放缓', 'Q1 +10pt、Q2 +5pt']])
ok(not [x for x in LD.check_section(comp, 'presentation') if x[0] == 'FAIL'], '复合版式被误拦')
ok(LD.compose_on(comp, 'bar')['form'] == 'side', '复合版式判定错误')

# 4) 研究模式解读要求更高（≥3 条）
ok(any(r == 'DENSITY_READOUT' for _, r, _ in LD.check_section(comp, 'research')), '研究模式 2 条解读应不足')

# 5) 关键数字推导：时间轴给首末变化，类别轴给极差，环形给占比；非数值不推导
ok(LD.derive_key_metrics(bar)[2] == ['+30pt', '2026Q3 → Q2'], f'时间轴推导错误 {LD.derive_key_metrics(bar)}')
ok(LD.derive_key_metrics(cat)[2] == ['34pt', '最高与最低之差'], f'类别轴推导错误 {LD.derive_key_metrics(cat)}')
ok(LD.derive_key_metrics(donut, 'donut')[0] == ['70%', 'A占比最高'], '环形推导错误')
ok(LD.derive_key_metrics({'type': 'candlestick', 'labels': ['a', 'b', 'c'], 'values': [[1, 2, 0, 1]] * 3}) == [],
   '非单序列不应推导')

# 6) 双端一致：build_pptx.js deriveKeyMetrics 与 Python 同口径
js = (ROOT / 'scripts' / 'build_pptx.js').read_text(encoding='utf-8')
a = js.index('function fmtK(')
b = js.index('function composeKM(')
src = js[a:b] + ("const DERIVABLE = new Set(['bar','hbar','donut','pie','line','area','lollipop','dotplot','rose','radialbar','funnel','vsbar']);"
                 "const cases = JSON.parse(process.argv[1]);"
                 "console.log(JSON.stringify(cases.map(c => deriveKeyMetrics(c[0], c[1]))));")
src = src.replace("const DERIVABLE = new Set(['bar', 'hbar', 'donut', 'pie', 'line', 'area', 'lollipop', 'dotplot', 'rose', 'radialbar', 'funnel', 'vsbar']);", '')
cases = [[bar, 'bar'], [cat, 'exhibit'], [donut, 'donut'], [{'labels': ['x', 'y', 'z'], 'values': [3, 9.5, 1], 'unit': '家'}, 'bar']]
try:
    out = subprocess.run(['node', '-e', src, json.dumps(cases, ensure_ascii=False)], capture_output=True, text=True, check=True).stdout
    ok(json.loads(out) == [LD.derive_key_metrics(c, t) for c, t in cases], f'JS/Python 推导不一致：{out.strip()}')
except (OSError, subprocess.CalledProcessError) as e:
    fails.append(f'node 执行失败：{e}')

# 7) 仓库示例全部通过密度门禁
for m in sorted((ROOT / 'assets' / 'examples').glob('*.model.json')):
    model = json.loads(m.read_text(encoding='utf-8'))
    for i, sec in enumerate(model['sections']):
        for lv, rule, msg in LD.check_section(sec, model.get('mode') or 'presentation'):
            ok(lv != 'FAIL', f'{m.name} p{i + 1} {rule} {msg}')

if fails:
    print('[density] FAIL\n  ' + '\n  '.join(fails))
    sys.exit(1)
print('[density] 自测 PASS（低密度拦截 · 复合版式放行 · 双端推导一致 · 示例全绿）')
