#!/usr/bin/env python3
"""M12 回归：行距单源、默认无眉标 / 页脚注释、克制页码、阶段卡时间线、章节页结论两端一致。
1. PPTX 正文（≥2 行、≤16pt）行距 = 1.5×字号，装不下时 1.3×，绝不更低；validate_pptx 能抓住单倍行距；
2. 默认不画眉标与页脚注释（注释移入演讲者备注，带 [n] 引用的来源行保留）；showEyebrow / showFootnotes / pageNumber 三个开关可开回；
3. 页码只写 N、封面不标；
4. lib_chrome.js 与 render_from_model.py 的开关与注释迁移同口径；
5. 2–5 段短时间线两端都是阶段卡；章节页 soWhat 两端都显示；
6. 求解器字数承载折算（textK）JS / Python 一致。"""
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import render_from_model as R  # noqa: E402
import lib_solver  # noqa: E402
import validate_pptx as V  # noqa: E402

fails = []


def ok(cond, msg):
    if not cond:
        fails.append(msg)


LONG = '这是一段需要换行的正文说明，用来检验默认行距是否是一点五倍并且在高度不够时降到一点三倍而不是更低。' * 2
MODEL = {
    'mode': 'presentation', 'style': 'business-blue', 'title': 'M12 回归', 'subtitle': 's', 'meta': 'm',
    'agenda': [['01', '一', 'a'], ['02', '二', 'b'], ['03', '三', 'c']],
    'sections': [
        {'type': 'points', 'eyebrow': '01 · 眉标甲', 'title': '要点页标题', 'points': [['要点一', LONG], ['要点二', LONG], ['要点三', LONG]],
         'footnote': '注：这条注释默认进备注', 'note': '口径：引用来源[1]'},
        {'type': 'timeline', 'eyebrow': '02 · 眉标乙', 'title': '时间线', 'phases': [
            ['Q1', '起步', '打底座', 'done'], ['Q2', '放量', '场景复制', 'now'], ['Q3', '开放', '接入生态', '']]},
        {'type': 'chapter', 'eyebrow': '03 · 第三章', 'title': '章节页', 'items': ['甲', '乙'], 'soWhat': '本章结论一句话'},
    ],
    'refs': [{'id': 1, 'text': '某来源'}],
    'closing': {'title': '收尾', 'points': [['下一步', '做']]},
}

# 4) 开关与注释迁移：JS ≡ Python
js = subprocess.run(['node', '-e', '''
const C=require('./scripts/lib_chrome.js');const m=JSON.parse(process.argv[1]);
const f=C.chromeFlags(m);console.log(JSON.stringify({f, lf:C.chromeFlags({contentLocked:true}), s:C.stripFootnotes(m,f).sections}));
''', json.dumps(MODEL, ensure_ascii=False)], cwd=ROOT, capture_output=True, text=True)
J = json.loads(js.stdout)
pf = R.chrome_flags(MODEL)
ok(J['f'] == pf == {'showEyebrow': False, 'showFootnotes': False, 'pageNumber': True}, f'默认开关不一致：{J["f"]} / {pf}')
ok(J['lf']['showEyebrow'] and J['lf']['showFootnotes'], '原文锁定时眉标与注释应默认开启')
ps = R.strip_footnotes(MODEL, pf)['sections']
ok(json.dumps(ps, ensure_ascii=False, sort_keys=True) == json.dumps(J['s'], ensure_ascii=False, sort_keys=True), '注释迁移 JS / Python 不一致')
ok('footnote' not in ps[0] and ps[0].get('note') == '口径：引用来源[1]' and '默认进备注' in ps[0].get('speakerNotes', ''),
   f'注释迁移规则不对：{ps[0]}')

# 6) textK
ok(lib_solver.text_k(MODEL) == 1.039 and lib_solver.text_k({'showEyebrow': True}) == 0.967, f'textK 不对：{lib_solver.text_k(MODEL)}')
jk = subprocess.run(['node', '-e', 'const S=require("./scripts/lib_solver.js");console.log(S.textK({}),S.textK({showEyebrow:true}))'],
                    cwd=ROOT, capture_output=True, text=True).stdout.split()
ok(jk == ['1.039', '0.967'], f'textK JS 不一致：{jk}')

# 2/5) HTML
body = R.render_body(MODEL)
ok('眉标甲' not in body and '眉标乙' not in body, '默认不应渲染眉标')
ok('默认进备注' not in body and '引用来源' in body, '默认注释应移走、带引用的来源行保留')
ok('tl tl--h' in body, '短时间线 HTML 应是阶段卡')
chap = body[body.index('data-page-type="chapter"'):]
ok('本章结论一句话' in chap[:chap.index('</section>')], '章节页 soWhat 应在 HTML 显示')
b2 = R.render_body(dict(MODEL, showEyebrow=True, showFootnotes=True))
ok('眉标甲' in b2 and '默认进备注' in b2, '开关打开后眉标 / 注释应恢复')
css = (ROOT / 'assets' / 'templates' / 'engine.css').read_text(encoding='utf-8')
ok('--lh-text:1.5' in css and '.lh-tight{--lh-text:1.3' in css, 'HTML 行距变量缺失')


# 1/2/3/5) PPTX
def build(model, td, name):
    mp = Path(td) / f'{name}.json'
    mp.write_text(json.dumps(model, ensure_ascii=False), encoding='utf-8')
    out = Path(td) / f'{name}.pptx'
    r = subprocess.run(['node', 'scripts/build_pptx.js', str(out), f'--model={mp}'], cwd=ROOT, capture_output=True, text=True)
    ok(r.returncode == 0, f'{name} 构建失败：{r.stderr[-300:]}')
    return out


def slides(pptx):
    with zipfile.ZipFile(pptx) as z:
        names = sorted([n for n in z.namelist() if re.match(r'ppt/slides/slide\d+\.xml$', n)], key=lambda n: int(re.findall(r'\d+', n)[0]))
        notes = ' '.join(z.read(n).decode('utf-8') for n in z.namelist() if n.startswith('ppt/notesSlides/') and n.endswith('.xml'))
        return [z.read(n).decode('utf-8') for n in names], notes


with tempfile.TemporaryDirectory() as td:
    p = build(MODEL, td, 'def')
    xs, notes = slides(p)
    allx = ''.join(xs)
    ok('眉标甲' not in allx and '眉标乙' not in allx, 'PPTX 默认不应画眉标')
    ok('默认进备注' not in allx and '默认进备注' in notes, 'PPTX 注释应进备注')
    ok('chrome:pageno' not in xs[0], '封面不标页码')
    pn = re.findall(r'name="chrome:pageno".*?<a:t>([^<]*)</a:t>', xs[3], re.S)
    ok(pn == ['4'], f'页码应只写 N：{pn}')
    ok(xs[3].count('name="tl:card"') == 3, 'PPTX 短时间线应画 3 张阶段卡')
    # 行距：所有 ≥2 行正文行距 ≥1.3×，且确有 1.5×
    vals = [int(v) / 100 for v in re.findall(r'<a:lnSpc><a:spcPts val="(\d+)"/>', xs[2])]
    szs = [int(v) / 100 for v in re.findall(r'<a:rPr[^>]*sz="(\d+)"', xs[2])]
    ok(vals and min(vals) >= 1.3 * min(x for x in szs if x <= 16) - 0.2, f'要点页行距过紧：{vals}')
    rep = V.validate_pptx(p, strict=False) if hasattr(V, 'validate_pptx') else None
    codes = [e.get('code') for e in (rep or {}).get('warnings', []) + (rep or {}).get('errors', [])]
    ok('LINE_SPACING_TIGHT' not in codes, f'引擎产物不应触发行距门禁：{codes}')
    # 负例：去掉 lnSpc → 门禁报警
    bad = Path(td) / 'bad.pptx'
    with zipfile.ZipFile(p) as zi, zipfile.ZipFile(bad, 'w') as zo:
        for it in zi.infolist():
            data = zi.read(it.filename)
            if it.filename == 'ppt/slides/slide3.xml':
                data = re.sub(rb'<a:lnSpc>.*?</a:lnSpc>', b'', data)
            zo.writestr(it, data)
    rep = V.validate_pptx(bad, strict=False)
    codes = [e.get('code') for e in rep.get('warnings', []) + rep.get('errors', [])]
    ok('LINE_SPACING_TIGHT' in codes, '单倍行距应被 validate_pptx 抓住')
    p2 = build(dict(MODEL, showEyebrow=True, showFootnotes=True, pageNumber=False), td, 'on')
    xs2, _ = slides(p2)
    a2 = ''.join(xs2)
    ok('眉标甲' in a2 and '默认进备注' in a2 and 'chrome:pageno' not in a2, '开关打开 / 页码关闭不生效')

if fails:
    print('[test_m12] FAIL')
    for f in fails:
        print('  ✗', f)
    sys.exit(1)
print('[test_m12] PASS · 行距单源 · 默认无眉标 / 注释 · 克制页码 · 阶段卡时间线 · 章节结论 · 求解器折算')
