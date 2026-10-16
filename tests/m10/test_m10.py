#!/usr/bin/env python3
"""M10 回归：12 套风格 PPTX 气质全覆盖、衬线回退链、HTML 表格质感与 PPTX 同源、
研究模式不再放宽保真阈值、中文文字运行带 lang="zh-CN"、矩阵强调格两端一致。"""
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
fails = []


def ok(cond, msg):
    if not cond:
        fails.append(msg)


LC = json.loads((ROOT / 'scripts' / 'layout-constants.json').read_text(encoding='utf-8'))
CSS = (ROOT / 'assets' / 'templates' / 'engine.css').read_text(encoding='utf-8')
styles = set(LC['styles'])
SP = {k: v for k, v in LC['stylePptx'].items() if not k.startswith('$') and k != 'fontPairs'}

# 1) stylePptx 覆盖全部 12 套风格，字段取值合法
ok(len(styles) == 12, f'styles 应为 12 套，实为 {len(styles)}')
ok(set(SP) == styles, f'stylePptx 与 styles 不一致：缺 {sorted(styles - set(SP))} 多 {sorted(set(SP) - styles)}')
ALLOWED = {'display': {'serif', 'sans'}, 'rule': {'none', 'long', 'bar', 'bar-thick'},
           'card': {'tonal', 'outline', 'hairline'}, 'table': {'tonal', 'rule', 'three-line', 'zebra'}}
for st, cfg in SP.items():
    for k, vals in ALLOWED.items():
        ok(cfg.get(k) in vals, f'{st}.{k}={cfg.get(k)!r} 不在 {sorted(vals)}')
    ok(isinstance(cfg.get('titleBold'), bool), f'{st}.titleBold 必须是布尔')
    ok(isinstance(cfg.get('lineW'), (int, float)) and 0.25 <= cfg['lineW'] <= 2, f'{st}.lineW 越界')
ok(LC['stylePptx']['fontPairs']['serif'] == {'latin': 'Georgia', 'ea': 'SimSun'}, '衬线字体对应为 Georgia + SimSun')

# 2) HTML 衬线回退链 + 表格质感与 PPTX 同源
CHAIN = '"Georgia","Noto Serif SC","Source Han Serif SC","Songti SC","STSong","SimSun","Noto Serif CJK SC",serif'
for st, cfg in SP.items():
    m = re.search(r'html\[data-style="%s"\]\{([^}]*)\}' % re.escape(st), CSS)
    if cfg['display'] == 'serif':
        ok(m and CHAIN in m.group(1), f'{st}: --font-display 未使用统一衬线回退链')
    sel = f'html[data-style="{st}"]'
    if cfg['table'] == 'three-line':
        ok(f'{sel} table{{border-top:1.5px' in CSS, f'{st}: HTML 缺三线表样式')
    elif cfg['table'] in ('rule', 'zebra'):
        pat = 'thead th{background:transparent' if cfg['table'] == 'rule' else 'tbody tr:nth-child(even) td{background'
        ok(any(sel in line and pat in line for line in CSS.splitlines()), f'{st}: HTML 缺 {cfg["table"]} 表格样式')

# 3) 保真门禁四模式统一阈值
fid = (ROOT / 'scripts' / 'check_fidelity.py').read_text(encoding='utf-8')
ok('MODE_THRESH' not in fid, 'check_fidelity.py 仍有研究模式放宽（MODE_THRESH）')

# 4) 矩阵 accent 格 HTML 高亮（与 PPTX 一致）
import render_from_model as R  # noqa: E402
html = R.r_matrix(0, {'type': 'matrix', 'title': 't', 'rowHeads': ['a'], 'colHeads': ['x', 'y'],
                      'cells': [[{'t': '重点', 'accent': True}, '普通']]})
ok('class="heat__c heat__c--1">重点' in html and 'class="heat__c">普通' in html, '矩阵 accent 格 HTML 未高亮')

# 5) PPTX：中文运行 lang="zh-CN"、纯西文运行不标；衬线风格 latin Georgia + ea SimSun
if (ROOT / 'node_modules' / 'pptxgenjs').exists():
    model = json.loads((ROOT / 'assets' / 'examples' / '2026-09-09-presentation-business-blue.model.json').read_text(encoding='utf-8'))
    model['style'] = 'mckinsey'
    with tempfile.TemporaryDirectory() as td:
        mp, out = Path(td) / 'm.json', Path(td) / 'o.pptx'
        mp.write_text(json.dumps(model, ensure_ascii=False), encoding='utf-8')
        r = subprocess.run(['node', str(ROOT / 'scripts' / 'build_pptx.js'), str(out), f'--model={mp}'],
                           capture_output=True, text=True, cwd=ROOT,
                           env={**__import__('os').environ, 'NODE_PATH': str(ROOT / 'node_modules')})
        ok(r.returncode == 0 and out.exists(), f'build_pptx 失败：{r.stderr[-300:]}')
        if out.exists():
            z = zipfile.ZipFile(out)
            han_ok = han_bad = lat_bad = serif = 0
            for n in z.namelist():
                if not re.match(r'ppt/slides/slide\d+\.xml$', n):
                    continue
                x = z.read(n).decode('utf-8')
                for rpr, txt in re.findall(r'<a:r>(<a:rPr[^>]*?(?:/>|>.*?</a:rPr>))<a:t>([^<]*)</a:t>', x, re.S):
                    has_han = bool(re.search(r'[\u4e00-\u9fff]', txt))
                    is_zh = 'lang="zh-CN"' in rpr
                    if has_han:
                        han_ok += is_zh
                        han_bad += not is_zh
                    elif txt.strip() and is_zh:
                        lat_bad += 1
                    if 'typeface="Georgia"' in rpr:
                        serif += 1
                        ok('<a:ea typeface="SimSun"' in rpr, f'{n}: Georgia 运行未配 SimSun 东亚字体')
            ok(han_ok > 20 and han_bad == 0, f'含中文运行缺 lang="zh-CN"：{han_bad} 处（已标 {han_ok}）')
            ok(lat_bad == 0, f'纯西文运行误标 zh-CN：{lat_bad} 处')
            ok(serif > 0, 'mckinsey 衬线风格没有 Georgia 运行')
            print(f'test_m10: 中文运行 {han_ok} 处均带 zh-CN；Georgia 运行 {serif} 处')
else:
    print('test_m10: 未安装 pptxgenjs，跳过 PPTX XML 检查')

if fails:
    print('test_m10: FAIL')
    for f in fails:
        print('  -', f)
    sys.exit(1)
print("test_m10: PASS")
