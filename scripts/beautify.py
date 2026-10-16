#!/usr/bin/env python3
"""已有 PPT 美化路由（Beautify）：解析 → 内容冻结 → 逐页诊断 → 映射版式库 → 重排 → 逐字核对 → 前后对照。

契约（硬门禁）：
  · 不改字：原稿每个文本段都被冻结（sha256），映射时只允许「整段搬运」或在记录在案的边界处切分
    （键值分隔符「：」、手打序号「1.」「一、」改由版式绘制、全角空格分隔的并列项）；不新增任何正文。
  · 数字一致：原稿每页出现的数字在新页逐个找回；图表类别 / 系列名 / 数值逐项比对 PPTX 原生图表。
  · 原文件不覆盖：输出目录不得包含原稿路径，输出文件一律新建。
  · 不支持的对象（SmartArt / OLE / 公式）原样记录在报告里，不重绘。

用法：
  python scripts/beautify.py in.pptx --out DIR [--style business-blue] [--theme light] [--no-render] [--compare]
产物（DIR 下）：source.json · freeze.json · diagnosis.json · plan.json · <stem>.model.json · <stem>.html ·
              <stem>.pptx · verify.json · report.md · compare.png（--compare，需 soffice + pdftoppm）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import ingest_pptx  # noqa: E402
import lib_layout_pick as PICK  # noqa: E402
import lib_solver  # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

WS = re.compile(r'\s+')
NUM = re.compile(r'\d+(?:[.,]\d+)*')
ORD = re.compile(r'^\s*((?:\d{1,2}[.、．)）])|(?:[一二三四五六七八九十]{1,3}、)|(?:[①②③④⑤⑥⑦⑧⑨⑩])|(?:第[一二三四五六七八九十\d]+步[：:]?))\s*')
CN_NUM = {c: i for i, c in enumerate('一二三四五六七八九十', 1)}
CLOSING_RE = re.compile(r'^(谢谢|感谢|致谢|Q\s*&\s*A|THANKS?)', re.I)
AGENDA_RE = re.compile(r'^(目录|议程|大纲|提纲|内容|CONTENTS?|AGENDA)\s*$', re.I)


def norm(s: str) -> str:
    return WS.sub('', str(s or ''))


def sha(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()[:16]


def fmt_num(v):
    if v is None:
        return None
    return int(v) if float(v).is_integer() else float(v)


# ── 1. 内容冻结 ──────────────────────────────────────────────────────────────
def freeze(src: dict) -> dict:
    out = []
    for sl in src['slides']:
        segs = []
        for si, sh in enumerate(sl['shapes']):
            if sh['kind'] == 'text':
                for pi, p in enumerate(sh['paras']):
                    segs.append({'id': f"{sl['no']}.{si}.{pi}", 'text': p['text'], 'sha': sha(p['text'])})
            elif sh['kind'] == 'table':
                for ri, r in enumerate(sh['rows']):
                    for ci, c in enumerate(r):
                        if c.strip():
                            segs.append({'id': f"{sl['no']}.{si}.r{ri}c{ci}", 'text': c, 'sha': sha(c)})
            elif sh['kind'] == 'chart':
                for ci, c in enumerate(sh['categories']):
                    segs.append({'id': f"{sl['no']}.{si}.cat{ci}", 'text': c, 'sha': sha(c), 'chart': True})
                for k, s in enumerate(sh['series']):
                    if len(sh['series']) > 1 and s['name']:
                        segs.append({'id': f"{sl['no']}.{si}.ser{k}", 'text': s['name'], 'sha': sha(s['name']), 'chart': True})
        out.append({'slide': sl['no'], 'segments': segs,
                    'numbers': sorted(NUM.findall(' '.join(x['text'] for x in segs)))})
    return {'source': src['source'], 'slides': out}


# ── 2. 诊断 ──────────────────────────────────────────────────────────────────
def diagnose(src: dict) -> list:
    res = []
    for sl in src['slides']:
        sizes, colors, issues = set(), set(), []
        nchar, nboxes = 0, 0
        for sh in sl['shapes']:
            if sh['kind'] == 'text':
                nboxes += 1
                for p in sh['paras']:
                    sizes.update(p['sizes'])
                    colors.update(p['colors'])
                    nchar += len(p['text'])
        if len(sizes) > 3:
            issues.append(f'字号混乱：{len(sizes)} 种字号 {sorted(sizes)}')
        if len(colors) > 2:
            issues.append(f'文字色过多：{len(colors)} 种 {sorted(colors)}')
        if any(c in colors for c in ('E01010', 'FF0000', '10A030', '00FF00')):
            issues.append('正文使用纯红 / 纯绿，状态色与强调色混用')
        if nchar > 160:
            issues.append(f'整页堆字：{nchar} 字')
        xs = sorted({round(sh['x'], 1) for sh in sl['shapes'] if sh['kind'] == 'text'})
        if len(xs) > 2 and nboxes > 3:
            issues.append(f'左边线不齐：{len(xs)} 条起点')
        for sh in sl['shapes']:
            if sh['kind'] == 'chart' and sh['chartType'] in ('donut',) and len(sh['categories']) > 5:
                issues.append('饼图分块过多')
            if sh['kind'] == 'chart':
                issues.append('图表沿用默认配色与图例，未突出结论')
            if sh['kind'] == 'picture' and sh['w'] * sh['h'] > src['slideW'] * src['slideH'] * 0.7:
                issues.append('整页图片（文字不可编辑）')
        if src['slideW'] / max(0.1, src['slideH']) < 1.5:
            issues.append('4:3 旧画幅，宽屏投影两侧留黑') if sl['no'] == 1 else None
        res.append({'slide': sl['no'], 'title': sl['title'], 'issues': issues})
    return res


# ── 3. 映射 ──────────────────────────────────────────────────────────────────
class Ledger:
    """切分账本：记录每个原稿段落在新模型里被切成了哪些片段（keep / ordinal / sep）。"""

    def __init__(self):
        self.rows = []

    def put(self, slide, text, parts):
        joined = ''.join(p[1] for p in parts)
        assert norm(joined) == norm(text), (text, parts)
        self.rows.append({'slide': slide, 'text': text, 'parts': parts})

    def whole(self, slide, text):
        self.put(slide, text, [('keep', text)])
        return text

    def kv(self, slide, text):
        """「键：值」→ [键, 值]（分隔符记 sep）；无分隔符返回 None。"""
        m = re.match(r'^(.{1,14}?)([：:])(.+)$', text)
        if not m:
            return None
        self.put(slide, text, [('keep', m.group(1)), ('sep', m.group(2)), ('keep', m.group(3))])
        return [m.group(1).strip(), m.group(3).strip()]

    def strip_ord(self, slide, text, k):
        m = ORD.match(text)
        if not m:
            return None
        self.put(slide, text, [('ordinal', text[:m.end()]), ('keep', text[m.end():])])
        return text[m.end():].strip()

    def metric(self, slide, text):
        m = re.match(r'^(\D*?)\s*([+\-−]?\d[\d.,]*\s*\S*)$', text)
        if not m or not m.group(1).strip():
            return None
        self.put(slide, text, [('keep', m.group(1)), ('keep', text[len(m.group(1)):])])
        return [text[len(m.group(1)):].strip(), m.group(1).strip()]


def _paras(sl, skip_title=True):
    out = []
    for si, sh in enumerate(sl['shapes']):
        if sh['kind'] != 'text' or (skip_title and si == sl['titleShape']):
            continue
        for p in sh['paras']:
            out.append({'text': p['text'], 'level': p['level'], 'box': si, 'bold': p['bold'],
                        'size': max(p['sizes'] or [0]), 'x': sh['x'], 'y': sh['y']})
    return out


def _boxes(sl):
    return [(si, sh) for si, sh in enumerate(sl['shapes']) if sh['kind'] == 'text' and si != sl['titleShape']]


def _is_metric(t):
    """「标签 + 一个数值（含单位）」：营收 3.2 亿元 / 同比增长 18%。含两个以上数字的句子不算。"""
    return len(t) <= 18 and len(NUM.findall(t)) == 1 and bool(re.match(r'^\D+\s*[+\-−]?\d[\d.,]*\s*\S{0,3}$', t))


def _rows_layout(sl):
    """总体架构式：同一行有「左标签框 + 右内容框」且 ≥3 行 → 分层图。"""
    bx = _boxes(sl)
    if len(bx) < 6 or len(bx) % 2:
        return None
    rows = {}
    for si, sh in bx:
        rows.setdefault(round(sh['y'], 1), []).append(sh)
    if len(rows) < 3 or any(len(v) != 2 for v in rows.values()):
        return None
    return [sorted(v, key=lambda s: s['x']) for _, v in sorted(rows.items())]


def _grid_steps(sl):
    """四宫格 / 横排框：每框「序号 + 标题」首段 + 说明 → 步骤。"""
    bx = _boxes(sl)
    if not 3 <= len(bx) <= 6:
        return None
    heads = [sh['paras'][0]['text'] for _, sh in bx]
    if not all(ORD.match(h) for h in heads) or not all(len(sh['paras']) >= 2 for _, sh in bx):
        return None
    def ordv(h):
        m = re.match(r'\s*(\d+)', h)
        return int(m.group(1)) if m else CN_NUM.get(h.strip()[:1], 99)
    return sorted([sh for _, sh in bx], key=lambda s: ordv(s['paras'][0]['text']))


def map_slide(sl, led: Ledger, style, history, n_slides):
    no, title = sl['no'], sl['title']
    paras = _paras(sl)
    charts = [s for s in sl['shapes'] if s['kind'] == 'chart']
    tables = [s for s in sl['shapes'] if s['kind'] == 'table']
    pics = [s for s in sl['shapes'] if s['kind'] == 'picture']
    T = led.whole(no, title) if title else ''
    texts = [p['text'] for p in paras if p['level'] == 0]

    def side_points():
        pts = []
        for p in paras:
            if p['level'] > 0 and pts:
                prev = pts[-1]
                pts[-1] = [prev if isinstance(prev, str) else prev[0], led.whole(no, p['text'])]
            else:
                pts.append(led.whole(no, p['text']))
        return pts

    if charts:
        c = charts[0]
        labels = [led.whole(no, x) for x in c['categories']]
        ser = c['series']
        for s in ser:
            if len(ser) > 1 and s['name']:
                led.whole(no, s['name'])
        chart = {'labels': labels}
        if len(ser) > 1:
            chart['series'] = [{'name': s['name'], 'values': [fmt_num(v) for v in s['values']]} for s in ser]
            chart['values'] = chart['series'][-1]['values']
        else:
            chart['values'] = [fmt_num(v) for v in ser[0]['values']]
        kind = c['chartType']
        if kind == 'hbar':
            chart['type'] = 'hbar'
        elif kind in ('line', 'area', 'stack'):
            chart['type'] = kind
        side = side_points() if paras else []
        if kind == 'donut':
            if side:
                lid = 'text-media'
                chart['centerLabel'] = ''
                chart['centerTotal'] = False
                sec = {'type': 'split', 'title': T, 'left': {'type': 'donut', **chart},
                       'right': {'type': 'points', 'points': side}}
            else:
                chart['centerLabel'] = ''
                chart['centerTotal'] = False
                lid, sec = 'composition', {'type': 'donut', 'title': T, 'chart': chart}
        elif side:
            lid = PICK.pick(['text-media', 'chart-full'], style, history) if len(side) == 1 else 'text-media'
            if lid == 'chart-full':
                sec = {'type': 'bar', 'title': T, 'chart': chart, 'note': side[0] if isinstance(side[0], str) else '　'.join(side[0])}
            else:
                sec = {'type': 'split', 'title': T, 'left': {'type': chart.get('type', 'bar'), **chart},
                       'right': {'type': 'points', 'points': side}}
        else:
            lid, sec = 'chart-full', {'type': 'bar', 'title': T, 'chart': chart}
        return lid, sec, 'data'

    if tables:
        rows = [[led.whole(no, c) if c.strip() else c for c in r] for r in tables[0]['rows']]
        sec = {'type': 'table', 'title': T, 'table': {'head': rows[0], 'rows': rows[1:]}}
        if paras:
            sp = side_points()
            sec['lead' if len(sp) == 1 and isinstance(sp[0], str) else 'note'] = sp[0] if len(sp) == 1 else '　'.join(
                x if isinstance(x, str) else '　'.join(x) for x in sp)
        return 'compare-table', sec, 'table'

    layers = _rows_layout(sl)
    if layers:
        ls = []
        for lab, body in layers:
            name = led.whole(no, lab['paras'][0]['text'])
            raw = body['paras'][0]['text']
            items = [x for x in re.split(r'[　\s]{1,}', raw) if x]
            led.put(no, raw, [('keep', x) if x.strip() else ('sep', x) for x in re.split(r'([　\s]+)', raw) if x])
            ls.append([name, [{'t': x} for x in items]])
        return 'layer-stack', {'type': 'diagram', 'title': T, 'layers': ls}, 'framework'

    grid = _grid_steps(sl)
    if grid:
        steps = []
        for k, sh in enumerate(grid, 1):
            head = led.strip_ord(no, sh['paras'][0]['text'], k)
            desc = '　'.join(led.whole(no, p['text']) for p in sh['paras'][1:])
            steps.append([head, desc])
        return PICK.pick(['steps-h'], style, history), {'type': 'steps', 'title': T, 'steps': steps}, 'process'

    if texts and 2 <= len(texts) <= 6 and all(_is_metric(t) for t in texts) and len(texts) == len(paras):
        ms = [led.metric(no, t) for t in texts]
        lid = PICK.pick(['kpi-wall', 'kpi-trend'], style, history)
        if lid == 'kpi-trend':
            return lid, {'type': 'kpi', 'title': T, 'hero': [ms[0][0], ms[0][1], ''], 'metrics': ms[1:]}, 'data'
        return lid, {'type': 'metrics', 'title': T, 'metrics': ms}, 'data'

    if texts and 3 <= len(texts) <= 6 and len(texts) == len(paras) and all(re.match(r'^.{1,14}?[：:].+$', t) for t in texts):
        kvs = [led.kv(no, t) for t in texts]
        cands = ['feature-cards', 'bento', 'argument-3'] if len(kvs) >= 3 else ['feature-cards', 'argument-3']
        lid = PICK.pick(cands, style, history)
        if lid == 'argument-3':
            return lid, {'type': 'points', 'title': T, 'points': kvs}, 'viewpoint'
        sec = {'type': 'cards', 'title': T, 'cards': [{'title': k, 'points': [v]} for k, v in kvs],
               'columns': min(4, len(kvs))}
        if lid == 'bento':
            sec['variant'] = 'bento-grid'
        return lid, sec, 'cards'

    if pics and paras and not charts and not tables:
        # 图文页：文字进左区要点，第一张图进右区（等比放入，不裁切）；其余图片仍列入报告
        return 'text-media', {'type': 'split', 'title': T,
                              'left': {'type': 'points', 'points': side_points()},
                              'right': {'type': 'image', 'image': {'src': 'media/' + pics[0]['file'], 'fit': 'contain',
                                                                    'alt': pics[0].get('alt') or ''}}}, 'media'
    if pics and not paras:
        return 'media-full', {'type': 'image', 'title': T, 'image': {'src': 'media/' + pics[0]['file'], 'layout': 'full'}}, 'media'

    pts = side_points()
    if 2 <= len(pts) <= 4:
        # 清单两种承载：要点列（argument-3）或卡片（每条一卡；短句作卡片标题，长句作卡片正文、标题留空）。
        # 原稿顺序不能动，所以由节奏规则在两者间交替，避免相邻同版式 / 同重量连排。
        # 要点列只在卡片类都会撞节奏时才用：短清单放进要点列字小、留白大，版面撑不起来
        lid = PICK.pick(['feature-cards', 'bento', 'argument-3'], style, history)
        if lid in ('feature-cards', 'bento'):
            short = all(len(x if isinstance(x, str) else x[0]) <= 12 for x in pts)
            cards = []
            for x in pts:
                head, sub = (x, None) if isinstance(x, str) else (x[0], x[1])
                if short:
                    cards.append({'title': head, 'points': [sub] if sub else []})
                else:
                    cards.append({'title': '', 'points': [head] + ([sub] if sub else [])})
            sec = {'type': 'cards', 'title': T, 'cards': cards, 'columns': len(cards)}
            if lid == 'bento':
                sec['variant'] = 'bento-grid'
            # 备选：要点列（中等重量）。后续页若被迫连排同重量，由 build_model 回头换成它
            sec['_alt'] = ('argument-3', {'type': 'points', 'title': T, 'points': pts}, 'viewpoint')
            return lid, sec, 'cards'
    return 'argument-3', {'type': 'points', 'title': T, 'points': pts}, 'viewpoint'


def build_model(src, style, theme):
    led = Ledger()
    slides = src['slides']
    plan, sections, history = [], [], []
    model = {'mode': 'presentation', 'style': style, 'theme': theme, 'contentLocked': True}
    # 封面：第 1 页；最大字号段 = 标题，其余按序为副标题 / 落款
    cov = slides[0]
    cps = sorted(_paras(cov, skip_title=False), key=lambda p: (-p['size'], p['y']))
    model['title'] = led.whole(1, cps[0]['text'])
    rest = sorted(cps[1:], key=lambda p: p['y'])
    if rest:
        model['subtitle'] = led.whole(1, rest[0]['text'])
    if len(rest) > 1:
        model['meta'] = '　'.join(led.whole(1, p['text']) for p in rest[1:])
    if cov.get('notes', '').strip():
        model['coverNotes'] = cov['notes']
    plan.append({'src': 1, 'role': 'cover', 'layout': 'cover'})
    history.append('cover')
    agenda_items = []
    agenda_title = ''
    closing = None
    for sl in slides[1:]:
        t = norm(sl['title'])
        if AGENDA_RE.match(t) and not agenda_items:
            agenda_title = led.whole(sl['no'], sl['title'])
            agenda_items = [led.whole(sl['no'], p['text']) for p in _paras(sl)]
            if sl.get('notes', '').strip():
                model['agendaNotes'] = sl['notes']
            plan.append({'src': sl['no'], 'role': 'agenda', 'layout': 'agenda'})
            history.append('agenda')
            continue
        if sl['no'] == len(slides) and CLOSING_RE.match(t):
            closing = {'title': led.whole(sl['no'], sl['title']), 'eyebrow': '',
                       'points': [led.whole(sl['no'], p['text']) for p in _paras(sl)]}
            if sl.get('notes', '').strip():
                closing['speakerNotes'] = sl['notes']
            plan.append({'src': sl['no'], 'role': 'closing', 'layout': 'closing'})
            continue
        lid, sec, intent = map_slide(sl, led, style, history, len(slides))
        sec['sourceSlide'] = sl['no']
        if sec.get('chart') and not sec.get('keyMetrics'):
            sec['compose'] = 'off'   # 美化只换承载不增文字：不自动派生关键数字（复合版式需原稿自带要点 / 数字）
        if sl.get('notes', '').strip():
            sec['speakerNotes'] = sl['notes']   # 原稿备注原样写回新稿（核对器逐页比对）
        sections.append(sec)
        history.append(lid)
        plan.append({'src': sl['no'], 'role': 'section', 'layout': lid, 'intent': intent})
    # 节奏回补：同重量连排超上限时，把段内可替换的清单页换成备选版式（原文不变，只换承载）
    cap = (PICK.RHYTHM.get('maxSameWeightRun') or {}).get('presentation', 2)
    sec_plan = [p for p in plan if p['role'] == 'section']
    wt = lambda lid: (PICK.BY_ID.get(lid) or {}).get('weight')
    for _ in range(len(sections)):
        lids = [p['layout'] for p in sec_plan]
        bad = None
        for i in range(len(lids)):
            j = i
            while j + 1 < len(lids) and wt(lids[j + 1]) == wt(lids[i]):
                j += 1
            if j - i + 1 > cap:
                bad = (i, j)
                break
        if not bad:
            break
        cand = [k for k in range(bad[0], bad[1] + 1) if sections[k].get('_alt') and wt(sections[k]['_alt'][0]) != wt(lids[k])]
        if not cand:
            break
        k = min(cand, key=lambda k: abs(k - (bad[0] + bad[1]) / 2))
        alid, asec, aint = sections[k].pop('_alt')
        asec['sourceSlide'] = sections[k]['sourceSlide']
        sections[k] = asec
        sec_plan[k]['layout'], sec_plan[k]['intent'] = alid, aint
    for sec in sections:
        sec.pop('_alt', None)
    # 章节：agenda 条目按出现顺序认领页面（标题含条目核心词即归入该章）
    def core(s):
        return re.sub(r'^[\s一二三四五六七八九十\d、.．]+', '', s)
    ch = -1
    for sec in sections:
        # 只向后认领：命中后续条目才换章，否则留在当前章（首页未命中时归第 1 章）
        for k in range(ch + 1, len(agenda_items)):
            c = core(agenda_items[k])
            bigram = any(c[j:j + 2] in sec['title'] for j in range(len(c) - 1))
            if c and (c in sec['title'] or sec['title'] in c or bigram
                      or len(set(c) & set(sec['title'])) >= max(2, len(c) // 2)):
                ch = k
                break
        ch = max(ch, 0)
        if agenda_items:
            # 章名与页标题实为同一句时只留章号，避免眉题与标题重复
            same = core(agenda_items[ch]) in sec['title'] or sec['title'] in agenda_items[ch]
            sec['eyebrow'] = f'{ch + 1:02d}' if same else f'{ch + 1:02d} · {agenda_items[ch]}'
    if agenda_items:
        model['agenda'] = [[f'{i:02d}', a, ''] for i, a in enumerate(agenda_items, 1)]
        model['agendaTitle'] = agenda_title
        model['agendaEyebrow'] = ''
    model['sections'] = sections
    model['closing'] = closing or {'title': sections[-1]['title'] if sections else model['title'], 'points': []}
    # 图片：只有满版图页会迁入；其余图片不丢弃、不重绘，列入 unsupported 让人工处理
    used = json.dumps(model, ensure_ascii=False)
    for sl in slides:
        for sh in sl['shapes']:
            if sh['kind'] == 'picture' and ('media/' + sh['file']) not in used:
                src['unsupported'].append({'slide': sl['no'], 'shape': sh.get('alt') or 'picture', 'type': 'PICTURE',
                                           'action': f"未迁入新版式；原图已导出到 media/{sh['file']}，需人工放回"})
    return model, plan, led


# ── 4. 渲染 ──────────────────────────────────────────────────────────────────
def render(model_path: Path, out_html: Path, out_pptx: Path, template: Path):
    shutil.copy(template, out_html)
    r = subprocess.run([sys.executable, str(HERE / 'render_from_model.py'), str(out_html), '--inplace',
                        '--model', str(model_path)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit('render_from_model 失败：\n' + r.stdout[-1500:] + r.stderr[-1500:])
    r = subprocess.run(['node', str(HERE / 'build_pptx.js'), f'--out={out_pptx}', f'--model={model_path}'],
                       capture_output=True, text=True, cwd=str(ROOT))
    if r.returncode:
        raise SystemExit('build_pptx 失败：\n' + r.stdout[-1500:] + r.stderr[-1500:])


# ── 5. 核对 ──────────────────────────────────────────────────────────────────
CHROME = [re.compile(p) for p in (r'^\d{1,3}/\d{1,3}$', r'^\d{2}$', r'^（续）$', r'^[·•→—\-]+$')]


def pptx_slide_texts(path):
    from pptx import Presentation
    out = []
    for sl in Presentation(str(path)).slides:
        parts = []
        for sh in sl.shapes:
            if sh.has_text_frame:
                parts += [p.text for p in sh.text_frame.paragraphs if p.text.strip()]
            if getattr(sh, 'has_table', False) and sh.has_table:
                parts += [c.text for r in sh.table.rows for c in r.cells if c.text.strip()]
        out.append(parts)
    return out


def pptx_chart_data(path):
    """逐个 chart part 取类别与数值（原生图表）。"""
    z = zipfile.ZipFile(str(path))
    res = []
    for n in sorted(x for x in z.namelist() if re.match(r'ppt/charts/chart\d+\.xml$', x)):
        xml = z.read(n).decode('utf-8')
        cats = re.findall(r'<c:cat>.*?</c:cat>', xml, re.S)
        cat = re.findall(r'<c:v>([^<]*)</c:v>', cats[0]) if cats else []
        vals = [[float(v) for v in re.findall(r'<c:v>([^<]*)</c:v>', blk)]
                for blk in re.findall(r'<c:val>.*?</c:val>', xml, re.S)]
        names = [re.sub(r'<[^>]+>', '', x) for x in re.findall(r'<c:tx>.*?<c:v>([^<]*)</c:v>.*?</c:tx>', xml, re.S)]
        res.append({'part': n, 'categories': cat, 'values': vals, 'names': names})
    return res


def pptx_chart_pages(path):
    """chart part → 所在幻灯片序号（0 起）。"""
    z = zipfile.ZipFile(str(path))
    res = {}
    for n in z.namelist():
        m = re.match(r'ppt/slides/_rels/slide(\d+)\.xml\.rels$', n)
        if not m:
            continue
        for t in re.findall(r'Target="(?:\.\./|/ppt/)charts/(chart\d+\.xml)"', z.read(n).decode('utf-8')):
            res['ppt/charts/' + t] = int(m.group(1)) - 1
    return res


def html_page_texts(path, with_svg=True):
    txt = Path(path).read_text(encoding='utf-8')
    body = txt.split('<main', 1)[-1] if '<main' in txt else txt
    body = body.split('</main>', 1)[0]
    body = re.sub(r'<script[\s\S]*?</script>|<style[\s\S]*?</style>', ' ', body)
    pages = re.split(r'(?=<section\b)', body)[1:]
    out = []
    for p in pages:
        p = p.split('</section>', 1)[0]   # 只取版块本体；页尾的工具栏 / 弹窗等界面文字不属于正文
        if not with_svg:
            # 图表 SVG 内是坐标刻度 / 数据标签 / 提示框（由数据计算，(d) 另行核对），不参与「新增文本」检查
            p = re.sub(r'<svg[\s\S]*?</svg>', ' ', p)
        t = re.sub(r'<[^>]+>', '\n', p)
        t = t.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")
        out.append([x for x in (s.strip() for s in t.split('\n')) if x])
    return out


def verify(src, frz, model, plan, led, pptx_path, html_path):
    split, _ = lib_solver.split_model(json.loads(json.dumps(model)))
    # 新页序：cover, agenda?, sections(拆页后), closing —— 每页记录来源页
    newsourceSlide = [1] + ([plan[1]['src']] if model.get('agenda') else [])
    for s in split['sections']:
        newsourceSlide.append(s.get('sourceSlide'))
    closingsourceSlide = next((p['src'] for p in plan if p['role'] == 'closing'), None)
    newsourceSlide.append(closingsourceSlide)
    ptx = pptx_slide_texts(pptx_path)
    # 原生图表的类别 / 系列名不在形状文本里：按图表出现顺序并入其所在页，再由 (d) 逐项核对数据
    out_charts = pptx_chart_data(pptx_path)
    chart_pages = pptx_chart_pages(pptx_path)
    for oc in out_charts:
        k = chart_pages.get(oc['part'])
        if k is not None and k < len(ptx):
            ptx[k] = ptx[k] + oc['categories'] + (oc['names'] if len(oc['names']) > 1 else [])
    htm = html_page_texts(html_path) if html_path else None
    report = {'pageMap': [], 'missing': [], 'numbers': [], 'charts': [], 'residual': [], 'boundaries': {},
              'pptxPages': len(ptx), 'expectedPages': len(newsourceSlide)}
    if len(ptx) != len(newsourceSlide):
        report['missing'].append(f'页数不一致：PPTX {len(ptx)} 页 ≠ 计划 {len(newsourceSlide)} 页')
    bysourceSlide = {}
    for k, s in enumerate(newsourceSlide):
        bysourceSlide.setdefault(s, []).append(k)
    for sl in frz['slides']:
        report['pageMap'].append({'src': sl['slide'], 'new': [k + 1 for k in bysourceSlide.get(sl['slide'], [])],
                                  'note': '内容超载拆页' if len(bysourceSlide.get(sl['slide'], [])) > 1 else ''})
    all_keep = {}
    for r in led.rows:
        for kind, frag in r['parts']:
            report['boundaries'][kind] = report['boundaries'].get(kind, 0) + 1
            if kind == 'keep' and norm(frag):
                all_keep.setdefault(r['slide'], []).append(norm(frag))
    # (a) 冻结段全部入账（无段落被丢弃）
    ledger_texts = {}
    for r in led.rows:
        ledger_texts.setdefault(r['slide'], []).append(norm(r['text']))
    for sl in frz['slides']:
        pool = list(ledger_texts.get(sl['slide'], []))
        for sg in sl['segments']:
            t = norm(sg['text'])
            if t in pool:
                pool.remove(t)
            else:
                report['missing'].append(f"原第 {sl['slide']} 页段落未入模型：{sg['text']}")
    # (b) 每个保留片段在新页（PPTX + HTML）逐字可见
    for chan, pages in (('PPTX', ptx), ('HTML', htm)):
        if pages is None:
            continue
        for s, idxs in bysourceSlide.items():
            if s is None:
                continue
            hay = ''.join(norm(x) for k in idxs if k < len(pages) for x in pages[k])
            for frag in all_keep.get(s, []):
                if frag not in hay and not any(frag in norm(x) for x in (model.get('title', ''),)):
                    report['missing'].append(f'{chan} 原第 {s} 页片段缺失：{frag}')
    # (c) 数字逐个找回（序号由版式绘制时以两位序号形式出现）
    for sl in frz['slides']:
        idxs = bysourceSlide.get(sl['slide'], [])
        hay = ' '.join(x for k in idxs if k < len(ptx) for x in ptx[k])
        got = NUM.findall(hay)
        for n in sl['numbers']:
            if n in got:
                got.remove(n)
            elif n.zfill(2) in got:
                got.remove(n.zfill(2))
            else:
                report['numbers'].append(f"原第 {sl['slide']} 页数字 {n} 未在新页找到")
    # (d) 图表数据逐项比对原生 chart part
    src_charts = [sh for sl in src['slides'] for sh in sl['shapes'] if sh['kind'] == 'chart']
    for i, sc in enumerate(src_charts):
        want_cat = sc['categories']
        want_vals = [[fmt_num(v) for v in s['values']] for s in sc['series']]
        match = None
        for oc in out_charts:
            for rev in (False, True):   # 横向条形图在原生图表里自下而上排列
                cats = oc['categories'][::-1] if rev else oc['categories']
                vals = [v[::-1] for v in oc['values']] if rev else oc['values']
                if cats == want_cat and all(any([fmt_num(x) for x in ov] == wv for ov in vals) for wv in want_vals):
                    match = oc['part'] + ('（自下而上）' if rev else '')
                    break
            if match:
                break
        report['charts'].append({'src': i + 1, 'categories': want_cat, 'series': want_vals, 'pptx': match or '未找到'})
        if not match:
            report['missing'].append(f'图表 {i + 1}（{"/".join(want_cat)}）数据未在原生图表中找到')
    # (e) 反向：新页上除原稿片段 / 原稿重复引用 / 版式序号与页码外，不得出现新正文
    src_all = set()
    for sl in frz['slides']:
        for sg in sl['segments']:
            src_all.add(norm(sg['text']))
    keep_all = set(f for v in all_keep.values() for f in v) | src_all
    htm_nosvg = html_page_texts(html_path, with_svg=False) if html_path else None
    pages_all = [('PPTX', k, parts) for k, parts in enumerate(ptx)] + \
        ([('HTML', k, parts) for k, parts in enumerate(htm_nosvg)] if htm_nosvg else [])
    for chan, k, parts in pages_all:
        for x in parts:
            t = norm(x)
            if not t or any(c.match(t) for c in CHROME):
                continue
            rest = t
            for f in sorted(keep_all, key=len, reverse=True):
                if f and f in rest:
                    rest = rest.replace(f, '')
            rest = re.sub(r'\d{2}|[·•　\s（续）/]', '', rest)
            if rest:
                report['residual'].append({'chan': chan, 'page': k + 1, 'text': x, 'extra': rest})
    # (f) 演讲者备注：原稿有备注的页，新稿对应首页的备注必须逐字一致
    from pptx import Presentation as _P
    new_notes = [(sl.notes_slide.notes_text_frame.text if sl.has_notes_slide and sl.notes_slide.notes_text_frame else '')
                 for sl in _P(str(pptx_path)).slides]
    report['notes'] = []
    for sl in src['slides']:
        want = (sl.get('notes') or '').strip()
        if not want:
            continue
        ks = bysourceSlide.get(sl['no'], [])
        got = new_notes[ks[0]].strip() if ks and ks[0] < len(new_notes) else None
        if norm(got or '') != norm(want):
            report['missing'].append(f"原第 {sl['no']} 页备注未原样写回（新稿：{(got or '无')[:30]}）")
        else:
            report['notes'].append(sl['no'])
    report['ok'] = not report['missing'] and not report['numbers'] and not report['residual']
    return report


# ── 6. 前后对照 ──────────────────────────────────────────────────────────────
def compare_image(src_pptx, new_pptx, page_map, out_png, workdir):
    from PIL import Image, ImageDraw, ImageFont
    wd = Path(workdir)
    wd.mkdir(parents=True, exist_ok=True)
    for f, tag in ((src_pptx, 'a'), (new_pptx, 'b')):
        d = wd / tag
        d.mkdir(exist_ok=True)
        shutil.copy(f, d / 'deck.pptx')
        subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', 'deck.pptx'], cwd=d, capture_output=True, timeout=180)
        subprocess.run(['pdftoppm', '-r', '40', '-png', 'deck.pdf', 'p'], cwd=d, capture_output=True)
    A = sorted((wd / 'a').glob('p-*.png'))
    B = sorted((wd / 'b').glob('p-*.png'))
    H = 300
    def load(p):
        im = Image.open(p).convert('RGB')
        return im.resize((int(im.width * H / im.height), H))
    try:
        font = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 18)
    except OSError:
        font = None
    rows = []
    for pm in page_map:
        a = load(A[pm['src'] - 1]) if pm['src'] - 1 < len(A) else None
        bs = [load(B[k - 1]) for k in pm['new'] if k - 1 < len(B)]
        rows.append((pm, a, bs))
    wa = max((a.width for _, a, _ in rows if a), default=400)
    wb = max((sum(b.width + 8 for b in bs) for *_, bs in rows), default=533)
    W = 20 + wa + 40 + wb + 20
    canvas = Image.new('RGB', (W, 50 + len(rows) * (H + 36)), 'white')
    dr = ImageDraw.Draw(canvas)
    dr.text((20, 12), '原稿', fill='black', font=font)
    dr.text((20 + wa + 40, 12), '美化后', fill='black', font=font)
    for i, (pm, a, bs) in enumerate(rows):
        y = 50 + i * (H + 36)
        dr.text((20, y), f"原第 {pm['src']} 页 → 新第 {', '.join(map(str, pm['new'])) or '—'} 页 {pm.get('note', '')}",
                fill=(90, 90, 90), font=font)
        if a:
            canvas.paste(a, (20, y + 26))
        x = 20 + wa + 40
        for b in bs:
            canvas.paste(b, (x, y + 26))
            x += b.width + 8
    canvas.save(out_png)


def write_report(out: Path, stem, src, diag, plan, ver):
    L = [f'# 美化报告：{src["source"]}', '',
         f'- 原稿 {len(src["slides"])} 页 → 新稿 {ver["pptxPages"]} 页；文本核对：'
         f'{"通过（差异 0）" if ver["ok"] else "未通过"}',
         f'- 切分边界：{json.dumps(ver["boundaries"], ensure_ascii=False)}（keep = 原样搬运的片段；sep = 「：」等分隔符改为版式分栏；'
         'ordinal = 手打序号改由版式绘制）',
         f'- 不支持对象：{len(src["unsupported"])} 个' + (''.join(f'\n  - 第 {u["slide"]} 页 {u["shape"]}（{u["type"]}）：{u["action"]}'
                                                       for u in src['unsupported'])), '',
         '## 逐页诊断与映射', '', '| 原页 | 标题 | 诊断 | 新版式 | 新页 |', '|---|---|---|---|---|']
    pm = {p['src']: p for p in ver['pageMap']}
    for d, p in zip(diag, sorted(plan, key=lambda x: x['src'])):
        L.append(f"| {d['slide']} | {d['title'] or '（无标题）'} | {'；'.join(d['issues']) or '—'} | `{p['layout']}` | "
                 f"{', '.join(map(str, pm[d['slide']]['new']))} |")
    L += ['', '## 图表数据核对', '']
    for c in ver['charts']:
        L.append(f"- 图表 {c['src']}：{' / '.join(c['categories'])} → {c['pptx']}")
    if ver['missing'] or ver['numbers'] or ver['residual']:
        L += ['', '## 差异', ''] + [f'- {x}' for x in ver['missing'] + ver['numbers']] + \
             [f"- 新第 {r['page']} 页多出文本：{r['text']}" for r in ver['residual']]
    (out / 'report.md').write_text('\n'.join(L) + '\n', encoding='utf-8')


def run(src_pptx, out_dir, style='business-blue', theme='light', do_render=True, do_compare=False):
    src_pptx, out = Path(src_pptx).resolve(), Path(out_dir).resolve()
    if out == src_pptx.parent or src_pptx.is_relative_to(out):
        raise SystemExit('输出目录不能是原稿所在目录（原文件不覆盖）')
    out.mkdir(parents=True, exist_ok=True)
    stem = src_pptx.stem + '.beautified'
    src = ingest_pptx.ingest(str(src_pptx), str(out / 'media'))
    frz = freeze(src)
    diag = diagnose(src)
    model, plan, led = build_model(src, style, theme)
    for name, obj in (('source.json', src), ('freeze.json', frz), ('diagnosis.json', diag), ('plan.json', plan)):
        (out / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding='utf-8')
    mpath = out / f'{stem}.model.json'
    mpath.write_text(json.dumps(model, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if not do_render:
        return model, None
    html, pptx = out / f'{stem}.html', out / f'{stem}.pptx'
    render(mpath, html, pptx, ROOT / 'assets' / 'templates' / 'presentation.html')
    ver = verify(src, frz, model, plan, led, pptx, html)
    (out / 'verify.json').write_text(json.dumps(ver, ensure_ascii=False, indent=1), encoding='utf-8')
    write_report(out, stem, src, diag, plan, ver)
    if do_compare:
        compare_image(src_pptx, pptx, ver['pageMap'], out / 'compare.png', out / '_render')
    return model, ver


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pptx')
    ap.add_argument('--out', required=True)
    ap.add_argument('--style', default='business-blue')
    ap.add_argument('--theme', default='light')
    ap.add_argument('--no-render', action='store_true')
    ap.add_argument('--compare', action='store_true')
    a = ap.parse_args()
    model, ver = run(a.pptx, a.out, a.style, a.theme, not a.no_render, a.compare)
    if ver is None:
        print(f'[beautify] 已生成模型（未渲染）：{a.out}')
        return 0
    print(f"[beautify] {Path(a.pptx).name}: 原 {len(ver['pageMap'])} 页 → 新 {ver['pptxPages']} 页 · "
          f"文本核对 {'PASS（差异 0）' if ver['ok'] else 'FAIL'} · 图表 {len(ver['charts'])} 张")
    for x in (ver['missing'] + ver['numbers'])[:20]:
        print('  [FAIL]', x)
    for r in ver['residual'][:20]:
        print(f"  [FAIL] {r['chan']} 新第 {r['page']} 页多出文本：{r['text']}（{r['extra']}）")
    return 0 if ver['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
