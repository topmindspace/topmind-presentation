#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""topmind-presentation · HTML ↔ PPTX 高保真比对（门禁）

逐页把 HTML 渲染出的文字块与 PPTX 里的文本框按文字内容配对，量化五类差异：
  位置   左上角偏移（相对页宽）
  字号   HTML 字号 / 页宽  vs  PPTX 字号 / 页宽（比值）
  颜色   文字颜色 ΔE（CIE76）
  换行   HTML 行数 vs PPTX 在 LibreOffice 渲染后的行数
  字体   PPTX 每个文字运行须同时给出西文与中文字体（PowerPoint 回退可控）

用法：
    python3 scripts/check_fidelity.py 报告.html 报告.pptx [--json 输出.json] [--strict]
    python3 scripts/check_fidelity.py --examples [--strict]        # 跑四份示例（CI）
依赖：Node + playwright（devDependencies）、Chrome/Chromium、LibreOffice、poppler；缺任一项时 SKIP（退出 0）。
判定阈值见 THRESH；失败时逐页列出差异最大的文字块和修法提示。
"""
from __future__ import annotations

import argparse
import json
import os
import math
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EMU = 914400
NS = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'}

# 整稿阈值（比例按「配上的文字块」计）
THRESH = {
    'match': 0.80,       # PPTX 文本框能在 HTML 找到同文的比例下限
    'font_bad': 0.15,    # 字号层级偏差（相对整稿中位比值超出 [0.8, 1.25]）的比例上限
    'color_bad': 0.08,   # 颜色 ΔE > 12 的比例上限
    'wrap_bad': 0.20,    # 行数差 ≥2 的比例上限
    'pos_p90': 0.12,     # 位置偏移 90 分位上限（相对页宽）
    'font_missing': 0,   # 缺中文或西文字体声明的文字运行数
}
# 按模式放宽的项（须有理由并在 CHANGELOG 记为遗留）：research 的 HTML 图卡比 PPTX 图区高约 35%
# （网页无 16:9 高度上限），复杂信息图的标签纵向位置系统性偏移；字号 / 颜色 / 配对不放宽。


DECOR_RE = re.compile(r'\d{1,2}\s*/\s*\d{1,3}|\d{1,2}|[A-Z ]{3,12}')   # 页码 / 序号 / 英文装饰标签不计入


def _norm(t: str) -> str:
    t = re.sub(r'^[·•\-–—\s]+', '', t or '')
    return re.sub(r'[\s·•。，、；：:;,.（）()“”"]+', '', t)


def _rgb(s):
    m = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', s or '')
    if m:
        return tuple(int(x) for x in m.groups())
    if s and re.fullmatch(r'[0-9A-Fa-f]{6}', s):
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
    return None


def _lab(c):
    def f(u):
        u /= 255
        return ((u + 0.055) / 1.055) ** 2.4 if u > 0.04045 else u / 12.92
    r, g, b = (f(x) for x in c)
    X, Y, Z = (r * .4124 + g * .3576 + b * .1805) / .95047, r * .2126 + g * .7152 + b * .0722, (r * .0193 + g * .1192 + b * .9505) / 1.08883
    h = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    return 116 * h(Y) - 16, 500 * (h(X) - h(Y)), 200 * (h(Y) - h(Z))


def delta_e(c1, c2):
    if not c1 or not c2:
        return 0.0
    return math.dist(_lab(c1), _lab(c2))


def pptx_boxes(pptx: Path):
    import xml.etree.ElementTree as ET
    z = zipfile.ZipFile(pptx)
    pres = ET.fromstring(z.read('ppt/presentation.xml'))
    sz = pres.find('p:sldSz', NS)
    SW, SH = int(sz.get('cx')), int(sz.get('cy'))
    names = sorted((n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)),
                   key=lambda n: int(re.findall(r'\d+', n)[0]))
    slides = []
    for n in names:
        root = ET.fromstring(z.read(n))
        boxes = []
        for sp in root.iter('{%s}sp' % NS['p']):
            tx = sp.find('p:txBody', NS)
            off = sp.find('.//a:xfrm/a:off', NS)
            ext = sp.find('.//a:xfrm/a:ext', NS)
            if tx is None or off is None:
                continue
            geo = {'x': int(off.get('x')) / SW, 'y': int(off.get('y')) / SW,
                   'w': int(ext.get('cx')) / SW, 'h': int(ext.get('cy')) / SW,
                   'box_pt': [int(off.get(k)) / EMU * 72 for k in ('x', 'y')] + [int(ext.get(k)) / EMU * 72 for k in ('cx', 'cy')]}
            # 比对单位 = 段落；字号 / 颜色取段内字数最多的那个运行（避免「大数字 + 小说明」混在一框时取错）
            for para in tx.findall('a:p', NS):
                runs = para.findall('a:r', NS)
                text = ''.join((r.findtext('a:t', '', NS) or '') for r in runs)
                if not text.strip() or DECOR_RE.fullmatch(text.strip()):
                    continue
                missing, main, best = 0, None, -1
                for r in runs:
                    rp = r.find('a:rPr', NS)
                    t = r.findtext('a:t', '', NS) or ''
                    if rp is None or rp.find('a:latin', NS) is None or rp.find('a:ea', NS) is None:
                        missing += 1
                    if rp is not None and len(t.strip()) > best:
                        best, main = len(t.strip()), rp
                pt = int(main.get('sz')) / 100 if main is not None and main.get('sz') else None
                c = main.find('a:solidFill/a:srgbClr', NS) if main is not None else None
                # 多色段落（如「编号 + 图题」「标题 + 说明」）：任一运行色与 HTML 一致即算同色
                alt = [x.get('val') for x in (r.find('a:rPr/a:solidFill/a:srgbClr', NS) for r in runs) if x is not None]
                boxes.append(dict(geo, text=text, pt=pt, color=c.get('val') if c is not None else None, colors=alt, font_missing=missing))
        slides.append(boxes)
    return slides, SW / EMU * 72


def pdf_lines(pptx: Path, td: Path):
    """LibreOffice 渲染后每页的文字行（pdftotext -bbox-layout）：[(x0,y0,x1,y1,text)]"""
    import xml.etree.ElementTree as ET
    subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', str(td), str(pptx)],
                   capture_output=True, timeout=240)
    pdf = td / (pptx.stem + '.pdf')
    if not pdf.exists():
        return None
    html = td / 'bbox.html'
    subprocess.run(['pdftotext', '-bbox-layout', str(pdf), str(html)], capture_output=True)
    txt = html.read_text(encoding='utf-8', errors='replace')
    txt = re.sub(r'<!DOCTYPE[^>]*>', '', txt).replace('xmlns="http://www.w3.org/1999/xhtml"', '')
    root = ET.fromstring(txt)
    pages = []
    for pg in root.iter('page'):
        lines = []
        for ln in pg.iter('line'):
            words = [w.text or '' for w in ln.iter('word')]
            lines.append((float(ln.get('xMin')), float(ln.get('yMin')), float(ln.get('xMax')), float(ln.get('yMax')), ''.join(words)))
        pages.append(lines)
    return pages


def _pptx_line_count(box, lines):
    x, y, w, h = box['box_pt']
    ys = set()
    for (x0, y0, x1, y1, t) in lines:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if x - 2 <= cx <= x + w + 2 and y - 2 <= cy <= y + h + 2 and t.strip() and _norm(t) in _norm(box['text']):
            ys.add(round(cy / 3))
    return len(ys) or None


def compare(html_json: Path, pptx: Path, td: Path):
    H = json.loads(html_json.read_text(encoding='utf-8'))
    slides, SWpt = pptx_boxes(pptx)
    plines = pdf_lines(pptx, td)
    pages, agg = [], {'n': 0, 'matched': 0, 'font_bad': 0, 'color_bad': 0, 'wrap_bad': 0, 'wrap_n': 0, 'pos': [], 'font_missing': 0}
    for i, boxes in enumerate(slides):
        hp = [it for it in (H[i]['items'] if i < len(H) else []) if not DECOR_RE.fullmatch(it['text'].strip())]
        hidx = {}
        for it in hp:
            hidx.setdefault(_norm(it['text']), []).append(it)
        rows = []
        for b in boxes:
            agg['n'] += 1
            agg['font_missing'] += b['font_missing']
            key = _norm(b['text'])
            cand = hidx.get(key)
            if not cand and len(key) >= 6:
                cand = [it for it in hp if len(_norm(it['text'])) >= 6 and (key in _norm(it['text']) or _norm(it['text']) in key)]
            if not cand:
                rows.append({'text': b['text'][:40], 'match': False})
                continue
            it = min(cand, key=lambda c: abs(c['x'] - b['x']) + abs(c['y'] - b['y']))
            agg['matched'] += 1
            pos = math.hypot(it['x'] - b['x'], it['y'] - b['y'])
            fr = (b['pt'] / SWpt) / it['fs'] if b['pt'] and it['fs'] else 1.0
            de = min([delta_e(_rgb(it['color']), _rgb(x)) for x in (b.get('colors') or [])] + [delta_e(_rgb(it['color']), _rgb(b['color']))])
            pl = _pptx_line_count(b, plines[i]) if plines and i < len(plines) else None
            wrap = abs(pl - it['lines']) if pl else 0
            agg['pos'].append(pos)
            agg['font_bad'] += not (0.75 <= fr <= 1.33)
            agg['color_bad'] += de > 12
            if pl:
                agg['wrap_n'] += 1
                agg['wrap_bad'] += wrap >= 2
            rows.append({'text': b['text'][:40], 'match': True, 'pos': round(pos, 3), 'dxy': [round(b['x'] - it['x'], 3), round(b['y'] - it['y'], 3)], 'font_ratio': round(fr, 2),
                         'dE': round(de, 1), 'lines': [it['lines'], pl], 'c': [it['color'], b['color']], 'px_pt': [round(it['fs'] * 1440, 1), b['pt']]})
        pages.append({'page': i + 1, 'rows': rows})
    # 字号按「整稿中位比值」归一：PPTX 为投影放大一档是设计意图，比的是字级层级是否一致
    allr = sorted(r['font_ratio'] for p in pages for r in p['rows'] if r.get('match'))
    med = allr[len(allr) // 2] if allr else 1.0
    agg['font_bad'] = 0
    for p in pages:
        for r in p['rows']:
            if r.get('match'):
                r['font_rel'] = round(r['font_ratio'] / med, 2)
                agg['font_bad'] += not (0.8 <= r['font_rel'] <= 1.25)
    m = max(1, agg['matched'])
    pos = sorted(agg['pos'])
    summary = {
        'font_scale': round(med, 2), 'boxes': agg['n'], 'match': round(agg['matched'] / max(1, agg['n']), 3),
        'font_bad': round(agg['font_bad'] / m, 3), 'color_bad': round(agg['color_bad'] / m, 3),
        'wrap_bad': round(agg['wrap_bad'] / max(1, agg['wrap_n']), 3),
        'pos_p90': round(pos[int(len(pos) * 0.9)] if pos else 0, 3), 'font_missing': agg['font_missing'],
    }
    return summary, pages


def verdict(s):
    bad = []
    if s['match'] < THRESH['match']:
        bad.append(f"文字配对率 {s['match']:.0%} < {THRESH['match']:.0%}：PPTX 里有 HTML 没有的文字（或反之），检查两端是否同读 model")
    for k, lab, fix in (('font_bad', '字级层级偏差', '同一角色两端字级要成比例：对照 layout-constants.json typeScale 与 engine.css --fs-*'),
                        ('color_bad', '颜色偏差', '文字色必须取 STYLE token（body / muted / accent），不要写死十六进制'),
                        ('wrap_bad', '换行偏差', '文本框宽度或字号与 HTML 不一致；先查该页 regions 宽度')):
        if s[k] > THRESH[k]:
            bad.append(f"{lab} {s[k]:.0%} > {THRESH[k]:.0%}：{fix}")
    pos_lim = THRESH['pos_p90']  # M10：研究模式不再放宽，四模式统一阈值
    if s['pos_p90'] > pos_lim:
        bad.append(f"位置偏移 p90 {s['pos_p90']} > {pos_lim}：该页 PPTX 版式与 HTML 不是同一骨架，查 lib_layout_regions")
    if s['font_missing'] > THRESH['font_missing']:
        bad.append(f"{s['font_missing']} 个文字运行缺中文 / 西文字体声明：addText 统一走 STYLE.font（build_pptx 会补 ea 字体）")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description='HTML ↔ PPTX 高保真比对')
    ap.add_argument('html', nargs='?')
    ap.add_argument('pptx', nargs='?')
    ap.add_argument('--examples', action='store_true', help='跑 assets/examples 下四份示例')
    ap.add_argument('--json', help='逐页明细写到这里')
    ap.add_argument('--strict', action='store_true', help='超阈值即退出 1')
    a = ap.parse_args()
    for tool in ('node', 'soffice', 'pdftotext'):
        if not shutil.which(tool):
            print(f'[fidelity] SKIP：缺 {tool}（CI 已装；本地装 LibreOffice / poppler 后重跑）')
            return 0
    pairs = []
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        if a.examples:
            for m in sorted((ROOT / 'assets' / 'examples').glob('*.model.json')):
                stem = m.name[:-len('.model.json')]
                html = ROOT / 'assets' / 'examples' / f'{stem}.html'
                pptx = td / f'{stem}.pptx'
                r = subprocess.run(['node', str(ROOT / 'scripts' / 'build_pptx.js'), str(pptx), f'--model={m}'],
                                   capture_output=True, text=True)
                if r.returncode != 0 or not html.exists():
                    print(f'[fidelity] FAIL {stem}: build_pptx 失败\n{r.stderr[-400:]}')
                    return 1
                pairs.append((stem, html, pptx))
        elif a.html and a.pptx:
            pairs.append((Path(a.pptx).stem, Path(a.html), Path(a.pptx)))
        else:
            ap.print_help()
            return 2
        report, failed = {}, False
        for stem, html, pptx in pairs:
            hj = td / f'{stem}.html.json'
            r = subprocess.run(['node', str(ROOT / 'scripts' / 'fidelity_html.js'), str(html), str(hj)], capture_output=True, text=True)
            if r.returncode == 2 or not hj.exists():
                print(f'[fidelity] SKIP {stem}：{(r.stderr or r.stdout).strip()[:200]}')
                if os.environ.get('CI') and a.strict:   # CI 里不允许静默跳过
                    failed = True
                continue
            sub = td / stem
            sub.mkdir()
            s, pages = compare(hj, pptx, sub)
            _m = re.search(r'data-mode="(\w+)"', html.read_text(encoding='utf-8', errors='ignore')[:4000])
            s['mode'] = _m.group(1) if _m else ''
            bad = verdict(s)
            report[stem] = {'summary': s, 'pages': pages, 'fails': bad}
            print(f"[fidelity] {'FAIL' if bad else 'PASS'} {stem}: 配对 {s['match']:.0%} · 字号比 ×{s['font_scale']} · 字级偏差 {s['font_bad']:.0%} · "
                  f"颜色偏差 {s['color_bad']:.0%} · 换行偏差 {s['wrap_bad']:.0%} · 位置 p90 {s['pos_p90']} · 缺字体 {s['font_missing']}")
            for b in bad:
                print('    - ' + b)
            failed |= bool(bad)
        if a.json:
            Path(a.json).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    return 1 if (failed and a.strict) else 0


if __name__ == '__main__':
    sys.exit(main())
