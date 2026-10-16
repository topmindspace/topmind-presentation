#!/usr/bin/env python3
"""版式库 golden：每个 layoutLibrary 版式至少一页，PPTX 几何指纹与 golden.json 一致。

指纹 = 该页所有形状（类型 + 位置尺寸，按 0.05in 取整）的有序列表的 sha1 前 12 位。
用法：python tests/layouts/test_layouts.py [--update]
"""
import hashlib, json, os, re, subprocess, sys, tempfile, zipfile
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import check_rhythm as C  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
GOLDEN = os.path.join(HERE, 'golden.json')
EMU = 914400 * 0.05
SHAPE = re.compile(r'<p:(sp|pic|graphicFrame|cxnSp)>.*?</p:\1>', re.S)
OFF = re.compile(r'<a:off x="(-?\d+)" y="(-?\d+)"/>\s*<a:ext cx="(\d+)" cy="(\d+)"/>')
GEOM = re.compile(r'<a:prstGeom prst="(\w+)"|<a:custGeom|<c:chart ')


def slide_fps(pptx):
    z = zipfile.ZipFile(pptx)
    names = sorted((n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)),
                   key=lambda n: int(re.findall(r'\d+', n)[0]))
    out = []
    for n in names:
        xml = z.read(n).decode('utf-8')
        sig = []
        for m in SHAPE.finditer(xml):
            body = m.group(0)
            o = OFF.search(body)
            g = GEOM.search(body)
            geo = (g.group(1) or ('cust' if 'custGeom' in g.group(0) else 'chart')) if g else '-'
            box = tuple(round(int(v) / EMU) for v in o.groups()) if o else ()
            sig.append(f"{m.group(1)}:{geo}:{box}")
        out.append({'fp': hashlib.sha1('|'.join(sig).encode()).hexdigest()[:12], 'shapes': len(sig)})
    return out


def run(update=False):
    fails, cur, covered = [], {}, set()
    for f in sorted(os.listdir(HERE)):
        if not (f.startswith('gallery-') and f.endswith('.model.json')):
            continue
        path = os.path.join(HERE, f)
        model = json.load(open(path, encoding='utf-8'))
        pages = C.pages_of(model)
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, 'g.pptx')
            r = subprocess.run(['node', os.path.join(ROOT, 'scripts', 'build_pptx.js'), f'--out={out}', '--strict', f'--model={path}'],
                               capture_output=True, text=True)
            if r.returncode:
                fails.append(f'{f}: build_pptx 失败\n{r.stdout[-800:]}{r.stderr[-800:]}')
                continue
            fps = slide_fps(out)
        if len(fps) != len(pages):
            fails.append(f'{f}: 幻灯片 {len(fps)} 页 ≠ 模型分页 {len(pages)} 页')
            continue
        rows = []
        for p, s in zip(pages, fps):
            covered.add(p['layout'])
            if p['layout'] == 'unknown':
                fails.append(f"{f}: 「{p['title']}」未匹配任何版式")
            if s['shapes'] < 2:
                fails.append(f"{f}: 「{p['title']}」({p['layout']}) 形状过少（{s['shapes']}）")
            rows.append({'layout': p['layout'], 'title': p['title'], **s})
        cur[f] = rows
    missing = [l['id'] for l in C.LAYOUTS if l['id'] not in covered]
    if missing:
        fails.append(f'版式缺 golden 页：{missing}')
    if update:
        json.dump(cur, open(GOLDEN, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'[layouts] golden 已更新：{sum(len(v) for v in cur.values())} 页 / {len(covered)} 版式')
    else:
        gold = json.load(open(GOLDEN, encoding='utf-8')) if os.path.exists(GOLDEN) else {}
        for f, rows in cur.items():
            g = gold.get(f, [])
            if len(g) != len(rows):
                fails.append(f'{f}: 页数与 golden 不一致（{len(rows)} vs {len(g)}），确认后 --update')
                continue
            for a, b in zip(rows, g):
                if (a['layout'], a['fp']) != (b['layout'], b['fp']):
                    fails.append(f"{f}: 「{a['title']}」{a['layout']} 几何漂移（{a['fp']} ≠ golden {b['fp']}）")
    for x in fails:
        print('  [FAIL]', x)
    n = len(C.LAYOUTS)
    print(f"[layouts] {len(covered & {l['id'] for l in C.LAYOUTS})}/{n} 版式覆盖 · {'PASS' if not fails else 'FAIL'}")
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(run('--update' in sys.argv))
