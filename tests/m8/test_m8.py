#!/usr/bin/env python3
"""M8 遗留问题回归：脚手架默认无示例文字、HTML 热力图色阶图例、PPTX 图标跟随风格主色、image-size 已覆盖到安全版本。"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
fails = []


def ok(cond, msg):
    if not cond:
        fails.append(msg)


with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    # 1) 不加 --plan：默认只出空位骨架；--demo 才有示例正文
    for mode in ('presentation', 'research', 'architecture'):
        out = td / f'{mode}.html'
        r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'scaffold_report.py'), '--mode', mode, '--out', str(out)],
                           capture_output=True, text=True)
        ok(r.returncode == 0, f'scaffold {mode} 失败：{r.stderr[-300:]}')
        if out.exists():
            t = out.read_text(encoding='utf-8')
            m = json.loads(re.search(r'window\.REPORT_MODEL = (\{.*?\});\n', t, re.S).group(1))
            secs = m['sections']
            ok(all(s.get('draft') for s in secs), f'{mode}: 默认骨架仍含示例正文页')
            ok(not any(k in s for s in secs for k in ('chart', 'points', 'cards', 'metrics', 'items')),
               f'{mode}: 默认骨架模型里有示例数据')
            ok('一句话说明' not in t, f'{mode}: 收尾页仍是示例文字')
    demo = td / 'demo.html'
    subprocess.run([sys.executable, str(ROOT / 'scripts' / 'scaffold_report.py'), '--mode', 'presentation', '--demo',
                    '--out', str(demo)], capture_output=True, text=True)
    ok(demo.exists() and '一句话说明' in demo.read_text(encoding='utf-8'), '--demo 应保留示例骨架')

# 2) HTML 热力图：单元格分级着色 + 色阶图例（两端标数值）
import render_from_model as RM  # noqa: E402
h = RM.r_heatmap(1, {'type': 'heatmap', 'title': 't', 'rowHeads': ['a', 'b'], 'colHeads': ['x', 'y'],
                     'cells': [[10, 40], [70, 90]], 'unit': '分'})
ok('heat__legend' in h and h.count('heat__sw') == 4, 'HTML 热力图缺色阶图例')
ok('低 10分' in h and '高 90分' in h, 'HTML 热力图图例缺数值区间')
ok('heat__c--3' in h and 'heat__c--1' in h, 'HTML 热力图单元格未分级着色')

# 3) PPTX 图标跟随风格主色：调色板 PNG 重新着色
js = (ROOT / 'scripts' / 'build_pptx.js').read_text(encoding='utf-8')
a, b = js.index('function _normColor('), js.index('/** 取图标 PNG data URI')
src = ("const fs=require('fs');" + js[a:b] +
       "const buf=fs.readFileSync(process.argv[1]);const out=recolorPng(buf,'#D0021B');"
       "fs.writeFileSync(process.argv[2],out);")
icons = sorted((ROOT / 'assets' / 'icons').glob('*.png'))
with tempfile.TemporaryDirectory() as td:
    dst = Path(td) / 'r.png'
    r = subprocess.run(['node', '-e', src, str(icons[0]), str(dst)], capture_output=True, text=True)
    ok(r.returncode == 0, f'recolorPng 执行失败：{r.stderr[-300:]}')
    if dst.exists():
        try:
            from PIL import Image
            im = Image.open(dst).convert('RGBA')
            raw = im.tobytes()
            px = [tuple(raw[i:i + 4]) for i in range(0, len(raw), 4) if raw[i + 3] > 128]
            ok(px and all(abs(p[0] - 0xD0) < 3 and p[1] < 6 and abs(p[2] - 0x1B) < 3 for p in px),
               '图标未改成风格主色')
        except ImportError:
            ok(dst.read_bytes() != icons[0].read_bytes(), '图标未重新着色')

# 4) image-size 经 overrides 锁到不受影响的版本
pkg = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))
ok(pkg.get('overrides', {}).get('image-size', '').startswith('^2.0.'), 'package.json 缺 image-size overrides')
lock = json.loads((ROOT / 'package-lock.json').read_text(encoding='utf-8'))
v = lock['packages'].get('node_modules/image-size', {}).get('version', '0')
ok(tuple(int(x) for x in v.split('.')[:3]) >= (2, 0, 3), f'lock 里 image-size 仍是 {v}')

if fails:
    print('[m8] FAIL\n  ' + '\n  '.join(fails))
    sys.exit(1)
print('[m8] 自测 PASS（脚手架无示例文字 · 热力图色阶图例 · 图标随主色 · image-size 已覆盖）')
