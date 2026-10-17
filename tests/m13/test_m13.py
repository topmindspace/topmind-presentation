#!/usr/bin/env python3
"""M13 回归自测：高密度 / 简单页 / 图标 / 象形图 / 标题防孤字 / 拥挤门禁。

1. tests/m13/layouts.model.json 端到端全过（装了 playwright 时连双端保真一起跑）；
2. 标题平衡断行：两行标题在标点处断开，数字 + 单位不拆（JS 单源 lib_dense.balanceTitle；HTML 端 esc_title 包 .nw）；
3. 负例 PPTX：孤字标题 → TITLE_ORPHAN；卡片挤在一起 → CROWD_GAP；单页 9 个图标 → ICON_OVERUSE；
4. 负例 HTML：focus 页塞 300 字 → FOCUS_SPARSE；混用线性 / 填充图标 → ICON_STYLE_MIXED；
5. 象形图双端同几何；图标包 72 个、PNG 为单色调色板（换主色只改 PLTE）。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
S = ROOT / 'scripts'
sys.path.insert(0, str(S))
fails: list[str] = []


def ok(c, msg):
    if not c:
        fails.append(msg)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), **kw)


with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    # 1) 端到端
    has_pw = run(['node', '-e', "require.resolve('playwright')"]).returncode == 0   # CI 精简环境可能没装 devDependencies
    r = run([sys.executable, str(S / 'make_deck.py'), str(ROOT / 'tests/m13/layouts.model.json'), '--out', str(td / 'e2e')]
            + (['--fidelity'] if has_pw else []))
    ok(r.returncode == 0 and '全部通过' in r.stdout, 'layouts.model.json 端到端未全过：' + r.stdout[-400:])
    r = run([sys.executable, str(S / 'make_deck.py'), str(ROOT / 'tests/m13/simple.model.json'), '--out', str(td / 'simple')]
            + (['--fidelity'] if has_pw else []))
    ok(r.returncode == 0 and '全部通过' in r.stdout, 'simple.model.json（简单页 12 变体）端到端未全过：' + r.stdout[-400:])

    # 2) 标题平衡断行
    js = ("const D=require(process.argv[1]);"
          "console.log(JSON.stringify(['2027 年先做深 6 个站，再推广到 18 个','三阶段开店节奏：两年开到 120 家','短标题']"
          ".map(t=>D.balanceTitle(t,8.23,32,0.52))))")
    r = run(['node', '-e', js, str(S / 'lib_dense.js')])
    out = json.loads(r.stdout or '[]')
    ok(len(out) == 3 and out[0] == '2027 年先做深 6 个站，\n再推广到 18 个', f'balanceTitle 未在标点处断行：{out[:1]}')
    ok(len(out) == 3 and out[2] == '短标题', 'balanceTitle 不应改动单行标题')
    import render_from_model as R
    ok('<span class="nw">18 个</span>' in R.esc_title('再推广到 18 个'), 'esc_title 未把数字 + 单位包成 .nw')
    css = (ROOT / 'assets/templates/engine.css').read_text(encoding='utf-8')
    ok('text-wrap:balance' in css and '.nw{white-space:nowrap}' in css, 'engine.css 缺标题平衡断行规则')

    # 3) 负例 PPTX
    neg = td / 'neg.pptx'
    js = r"""
const P=require('pptxgenjs');const fs=require('fs');const p=new P();p.layout='LAYOUT_WIDE';
let s=p.addSlide();
s.addText('我们建议明年先把六个试点站做深再推广到十八个',{x:0.6,y:0.5,w:9.1,h:1.2,fontSize:32,bold:true});
s.addText('正文一段说明文字，用来让页面不至于是空页。',{x:0.6,y:2.2,w:6,h:0.5,fontSize:14});
s=p.addSlide();
s.addText('三张卡片挤在一起的页面',{x:0.6,y:0.5,w:10,h:0.8,fontSize:32,bold:true});
[0,1,2].forEach(i=>{s.addShape('roundRect',{x:0.6+i*4.03,y:2,w:4,h:2,rectRadius:0.1,fill:{color:'EEF2F8'},line:{type:'none'}});
 s.addText('卡片'+i+'：一段足够长的说明文字，避免触发空页门禁',{x:0.8+i*4.03,y:2.2,w:3.6,h:1.2,fontSize:14});});
s=p.addSlide();
s.addText('九个图标堆满一页',{x:0.6,y:0.5,w:10,h:0.8,fontSize:32,bold:true});
const png=fs.readFileSync(process.argv[2]).toString('base64');
for(let i=0;i<9;i++){s.addImage({data:'data:image/png;base64,'+png,x:0.6+i*1.3,y:2.5,w:0.8,h:0.8,objectName:'icon:数据'});
 s.addText('说明'+i,{x:0.6+i*1.3,y:3.4,w:1.2,h:0.4,fontSize:12});}
p.writeFile({fileName:process.argv[1]}).then(()=>console.log('ok'));
"""
    r = run(['node', '-e', js, str(neg), str(ROOT / 'assets/icons/数据.png')])
    ok(neg.exists(), '负例 PPTX 生成失败：' + r.stderr[-300:])
    if neg.exists():
        r = run([sys.executable, str(S / 'validate_pptx.py'), str(neg)])
        codes = set(re.findall(r'"code": "([A-Z_]+)"', r.stdout))
        for c in ('TITLE_ORPHAN', 'CROWD_GAP', 'ICON_OVERUSE'):
            ok(c in codes, f'负例未触发 {c}（得到 {sorted(codes)[:12]}）')

    # 4) 负例 HTML
    html = next((td / 'e2e').glob('*.html'))
    txt = html.read_text(encoding='utf-8')
    m = re.search(r'(<section[^>]*band--focus[^>]*>[\s\S]*?class="focus__para[^"]*"[^>]*>)', txt)
    if m:
        bad = txt.replace(m.group(1), m.group(1) + '这是一段被硬塞进简单页的长文字。' * 20, 1)
        p2 = td / 'bad.html'; p2.write_text(bad, encoding='utf-8')
        r = run([sys.executable, str(S / 'validate_report.py'), str(p2), '--strict'])
        ok('[FAIL] FOCUS_SPARSE' in r.stdout, 'focus 页塞 300 字未触发 FOCUS_SPARSE')
    else:
        fails.append('e2e HTML 里找不到 focus__para 段（负例无法构造）')
    bad = txt.replace('</section>', '<i class="ico--fill"></i><i class="ico--line"></i></section>', 1)
    p3 = td / 'mixed.html'; p3.write_text(bad, encoding='utf-8')
    r = run([sys.executable, str(S / 'validate_report.py'), str(p3), '--strict'])
    ok('[FAIL] ICON_STYLE_MIXED' in r.stdout, '混用图标风格未触发 ICON_STYLE_MIXED')

    # 5) 象形图同几何 · 图标包
    import lib_chart_svg as L
    js = ("const n=+process.argv[1],w=+process.argv[2],h=+process.argv[3],leg=h*30/340;let b=[0,0,0];"
          "[...new Set([Math.min(n,10),Math.ceil(n/2)])].sort((a,b)=>a-b).forEach(c=>{const r=Math.ceil(n/c),ce=Math.min(w/c,(h-leg)/r);if(ce>b[2]+1e-6)b=[c,r,ce];});"
          "console.log(b[0]+','+b[1]);")
    for n, w, h in ((10, 900, 340), (12, 900, 340), (10, 300, 340)):
        py = L.pictogram_geom(n, w, h, 30)
        r = run(['node', '-e', js, str(n), str(w), str(h)])
        ok(r.stdout.strip() == f'{py[0]},{py[1]}', f'象形图几何双端不一致 n={n}: py={py[:2]} js={r.stdout.strip()}')
    bjs = (S / 'build_pptx.js').read_text(encoding='utf-8')
    ok("Math.min(n, 10), Math.ceil(n / 2)" in bjs, 'build_pptx.js shapePictogram 与 pictogram_geom 口径不一致')
    idx = json.loads((ROOT / 'assets/icons/index.json').read_text(encoding='utf-8'))
    ok(len(idx.get('icons', idx)) >= 72, '图标包少于 72 个')
    from PIL import Image
    im = Image.open(ROOT / 'assets/icons/数据.png')
    ok(im.mode == 'P', f'图标 PNG 不是调色板模式（{im.mode}），PPTX 无法按主色换色')

if fails:
    print('[m13] FAIL\n  ' + '\n  '.join(fails))
    sys.exit(1)
print('[m13] 自测 PASS（端到端 · 标题防孤字 · 负例门禁 · 象形图同几何 · 图标包）')
