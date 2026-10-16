#!/usr/bin/env python3
"""M11 回归：全新主题试跑中发现并修掉的问题。
1. 美化路由在 12 套风格下逐字核对都 PASS（此前 ink-academic 因渲染器自加「。」FAIL）；
2. 研究模式写了任意 exhibitNo 即按手写编号，不再与自动号撞车；
3. 复合版式的关键数字条 / 解读栏计入承载件；
4. make_deck 认 `--out 目录`（空格写法）。"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import render_from_model as R  # noqa: E402
import checks_html  # noqa: E402

fails = []


def ok(cond, msg):
    if not cond:
        fails.append(msg)


# 2) 手写编号优先
m = {'mode': 'research', 'style': 'mckinsey', 'title': 't', 'sections': [
    {'type': 'bar', 'title': 'a', 'exhibitNo': '1', 'chart': {'labels': ['x', 'y', 'z'], 'values': [1, 2, 3]}},
    {'type': 'donut', 'title': 'b', 'chart': {'labels': ['x', 'y', 'z'], 'values': [1, 2, 3]}},
    {'type': 'bar', 'title': 'c', 'exhibitNo': '2', 'chart': {'labels': ['x', 'y', 'z'], 'values': [1, 2, 3]}}]}
body = R.render_body(m)
import re  # noqa: E402
nos = re.findall(r'class="exhibit__no"[^>]*>\s*Exhibit\s*(\d+)', body)
ok(nos == ['1', '2'], f'手写 exhibitNo 时不应再自动编号：{nos}')
m2 = json.loads(json.dumps(m))
for s in m2['sections']:
    s.pop('exhibitNo', None)
nos2 = re.findall(r'class="exhibit__no"[^>]*>\s*Exhibit\s*(\d+)', R.render_body(m2))
ok(nos2 == ['1', '2', '3'], f'未写 exhibitNo 时应自动连续编号：{nos2}')

# 1') 写稿模式键后补「。」，美化模式不补
R._LOCKED = False
ok('<strong>键。</strong>' in R.kp('键', '值'), '写稿模式应在键后补「。」')
ok('<strong>键：</strong>' in R.kp('键：', '值'), '键已有收尾标点时不应再补「。」')
R.render_body({'contentLocked': True, 'sections': []})
ok('。' not in R.kp('键', '值'), '美化模式不得新增标点')
R._LOCKED = False

# 3) 复合版式承载件
band = '<section class="band"><div class="kstrip x"></div><svg class="chart" data-chart="bar"></svg><ol class="readout"></ol></section>'
ok(checks_html.carrier_count(band) >= 3, '关键数字条 / 解读栏应计入承载件')

# 4) make_deck --out 空格写法 + 1) 美化 12 套风格
with tempfile.TemporaryDirectory() as td:
    r = subprocess.run([sys.executable, 'scripts/make_deck.py', 'assets/examples/2026-09-09-presentation-business-blue.model.json',
                        '--out', td], cwd=ROOT, capture_output=True, text=True)
    ok('TypeError' not in r.stderr and (Path(td) / '2026-09-09-presentation-business-blue.html').exists(),
       f'make_deck --out 目录 写法失败：{r.stderr[-300:]}')
    try:
        import pptx  # noqa: F401
        has_pptx = True
    except ImportError:
        has_pptx = False
    if has_pptx and (ROOT / 'node_modules' / 'pptxgenjs').exists():
        styles = [k for k in json.loads((ROOT / 'scripts' / 'layout-constants.json').read_text(encoding='utf-8'))['styles']]
        for st in styles:
            out = Path(td) / f'b-{st}'
            r = subprocess.run([sys.executable, 'scripts/beautify.py', 'tests/beautify/samples/business-q3.pptx', '--out', str(out),
                                '--style', st], cwd=ROOT, capture_output=True, text=True)
            ok('文本核对 PASS' in r.stdout, f'美化 {st}：{(r.stdout + r.stderr)[-200:]}')
    else:
        print('test_m11: 缺 python-pptx / pptxgenjs，跳过美化 12 风格核对')

if fails:
    print('test_m11: FAIL')
    for f in fails:
        print('  -', f)
    sys.exit(1)
print('test_m11: PASS')
