#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""topmind-presentation · 版式归类 + 节奏 / 家族覆盖 / 反模式门禁（M3）

用法:
    python scripts/check_rhythm.py report.model.json [--strict] [--json]
    python scripts/check_rhythm.py report.html          # 读内嵌 REPORT_MODEL

规则单源 = layout-constants.json → layoutLibrary（rhythm / antiPatterns / layouts）。
页序与 PPTX / HTML 同源：先用 lib_solver.split_model 拆续页，再逐页归入唯一版式（最具体匹配优先）。

节奏（FAIL）:
  · 相邻两页不得是同一版式（续页豁免）；
  · 同一视觉重量（accent / light / medium / dense）最多连续 maxSameWeightRun 页——密、疏、强调交替；
  · 内容页 ≥ minFamiliesFromPages 时至少覆盖 minFamilies 个家族；
  · 内容页 ≥ chapterAnchorFromPages 时应有章节扉页（chapter）作锚点（WARN）。
反模式（FAIL）:
  · 文案出现「So what」类标签；金句页没有证据数字；
  · 单页图标 > maxIconsPerPage；单图系列色 > maxSeriesColors；同构卡片 > maxCardsSameShape。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import lib_solver  # noqa: E402

LC = json.loads((ROOT / 'scripts' / 'layout-constants.json').read_text(encoding='utf-8'))
LIB = LC['layoutLibrary']
LAYOUTS = LIB['layouts']
BY_ID = {l['id']: l for l in LAYOUTS}


def load(path: Path) -> dict:
    if path.suffix.lower() == '.json':
        return json.loads(path.read_text(encoding='utf-8'))
    from render_from_model import load_model
    return load_model(path)


def _specificity(m: dict) -> int:
    # compose（复合版式）比单纯页型 / 图表子类型更具体：命中即优先
    return sum(3 if k == 'compose' else 1 for k in m if k not in ('maxItems', 'minItems'))


def compose_form(sec: dict) -> str:
    """复合版式形态（与 render_from_model / build_pptx 同口径）：side | dual | minis | band | ''。"""
    import lib_density as LD
    t = (sec.get('type') or 'points').lower()
    C = LD.compose_on(sec, t)
    if not C:
        return ''
    if C['form'] == 'side':
        return 'dual' if sec.get('chart2') else ('minis' if sec.get('minis') else 'side')
    return 'band'


def classify(page: dict, no_compose: bool = False) -> str:
    """page: {'kind': cover|agenda|closing|section, 'sec': dict, 'n': agenda 条数}"""
    best, score = None, -1
    for l in LAYOUTS:
        m = l['match']
        if 'kind' in m:
            if page['kind'] != m['kind']:
                continue
            n = page.get('n', 0)
            if 'maxItems' in m and n > m['maxItems']:
                continue
            if 'minItems' in m and n < m['minItems']:
                continue
        else:
            if page['kind'] != 'section':
                continue
            sec = page['sec']
            t = (sec.get('type') or 'points').lower()
            if 'compose' in m:
                if no_compose:
                    continue
                if compose_form(sec) != m['compose']:
                    continue
            elif m.get('type') != t:
                continue
            if 'variant' in m and (sec.get('variant') or '') != m['variant']:
                continue
            if 'chart' in m and str((sec.get('chart') or {}).get('type') or '').lower() != m['chart']:
                continue
            if 'image' in m:
                img = sec.get('image') or {}
                lay = str(img.get('layout') or ('grid' if len(img.get('items') or []) > 1 else 'full')).lower()
                if lay != m['image']:
                    continue
        sc = _specificity(m)
        if sc > score:
            best, score = l['id'], sc
    return best or 'unknown'


def pages_of(model: dict) -> list:
    m, _ = lib_solver.split_model(json.loads(json.dumps(model)))
    agenda = m.get('agenda') or []
    out = [{'kind': 'cover', 'title': m.get('title') or '', 'sec': {}}]
    if agenda:
        out.append({'kind': 'agenda', 'title': '大纲', 'n': len(agenda), 'sec': {}})
    for s in m.get('sections') or []:
        if isinstance(s, dict):
            out.append({'kind': 'section', 'title': s.get('title') or '', 'sec': s,
                        'cont': str(s.get('title') or '').endswith('（续）')})
    if m.get('closing'):
        out.append({'kind': 'closing', 'title': (m.get('closing') or {}).get('title') or '', 'sec': {}})
    for p in out:
        p['layout'] = classify(p)
        lay = BY_ID.get(p['layout'], {})
        p['family'] = lay.get('family', '?')
        p['weight'] = lay.get('weight', 'medium')
        p['sig'] = p['layout']
        if p['layout'] == 'chart-band':
            # 底部解读带保留主图自身几何：相邻判定与视觉重量按主图版式算
            base = classify(p, no_compose=True)
            p['sig'] = 'chart-band:' + base
            p['weight'] = BY_ID.get(base, {}).get('weight', p['weight'])
    return out


def _all_text(o) -> str:
    if isinstance(o, str):
        return o
    if isinstance(o, dict):
        return ' '.join(_all_text(v) for v in o.values())
    if isinstance(o, (list, tuple)):
        return ' '.join(_all_text(v) for v in o)
    return ''


def check(model: dict) -> dict:
    R, A = LIB['rhythm'], LIB['antiPatterns']
    pages = pages_of(model)
    fails, warns = [], []
    # 节奏
    for i in range(1, len(pages)):
        a, b = pages[i - 1], pages[i]
        if R.get('forbidAdjacentSameLayout') and a.get('sig', a['layout']) == b.get('sig', b['layout']) and not b.get('cont'):
            fails.append(f'第 {i}–{i + 1} 页同一版式「{BY_ID.get(b["layout"], {}).get("name", b["layout"])}」相邻（换同家族其它版式或调整顺序）')
    maxrun = R.get('maxSameWeightRun', 2)
    if isinstance(maxrun, dict):
        maxrun = maxrun.get(model.get('mode') or 'presentation', maxrun.get('default', 2))
    i = 0
    while i < len(pages):
        j = i
        while j + 1 < len(pages) and (pages[j + 1]['weight'] == pages[i]['weight'] or pages[j + 1].get('cont')):
            j += 1
        if j - i + 1 > maxrun:
            fails.append(f'第 {i + 1}–{j + 1} 页连续 {j - i + 1} 页视觉重量都是「{pages[i]["weight"]}」'
                         f'（上限 {maxrun}；密 → 疏 → 强调交替，插入章节扉页 / 大数字 / 金句页打断）')
        i = j + 1
    content = [p for p in pages if p['kind'] == 'section']
    fams = sorted({p['family'] for p in content})
    if len(content) >= R.get('minFamiliesFromPages', 8) and len(fams) < R.get('minFamilies', 5):
        fails.append(f'{len(content)} 个内容页只用了 {len(fams)} 个版式家族（{"、".join(LIB["families"].get(f, f) for f in fams)}），至少 {R["minFamilies"]} 个')
    if len(content) >= R.get('chapterAnchorFromPages', 14) and not any(p['layout'] == 'chapter' for p in content):
        warns.append(f'{len(content)} 个内容页但没有章节扉页（chapter）作锚点')
    # 反模式
    banned = A.get('bannedText') or []
    for i, p in enumerate(pages, 1):
        sec = p['sec']
        txt = _all_text(sec)
        for b in banned:
            if b in txt:
                fails.append(f'第 {i} 页出现禁用标签「{b}」')
        t = (sec.get('type') or '').lower()
        if A.get('quoteNeedsEvidence') and t == 'quote' and len(sec.get('metrics') or []) < 2:
            fails.append(f'第 {i} 页金句页没有 ≥2 个证据数字（空金句页）')
        icons = len(re.findall(r'"icon"\s*:', json.dumps(sec, ensure_ascii=False)))
        if icons > A.get('maxIconsPerPage', 6):
            fails.append(f'第 {i} 页图标 {icons} 个 > {A["maxIconsPerPage"]}')
        for ch in (sec.get('chart'), sec.get('left'), sec.get('right')):
            if isinstance(ch, dict) and len(ch.get('series') or []) > A.get('maxSeriesColors', 6):
                fails.append(f'第 {i} 页图表系列 {len(ch["series"])} 个 > {A["maxSeriesColors"]} 色')
        if t == 'cards' and len(sec.get('cards') or []) > A.get('maxCardsSameShape', 8):
            fails.append(f'第 {i} 页同构卡片 {len(sec["cards"])} 张 > {A["maxCardsSameShape"]}')
    return {'pages': [{k: p[k] for k in ('kind', 'title', 'layout', 'family', 'weight')} for p in pages],
            'families': fams, 'fails': fails, 'warns': warns}


def main() -> int:
    ap = argparse.ArgumentParser(description='版式归类 + 节奏 / 家族 / 反模式门禁')
    ap.add_argument('src')
    ap.add_argument('--strict', action='store_true', help='WARN 也算失败')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    r = check(load(Path(a.src)))
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        seq = ' '.join({'accent': '◆', 'light': '○', 'medium': '◐', 'dense': '●'}.get(p['weight'], '?') for p in r['pages'])
        print(f'[check_rhythm] {Path(a.src).name}: {len(r["pages"])} 页 · 家族 {len(r["families"])} 个 · 节奏 {seq}')
        for p in r['fails']:
            print('  [FAIL]', p)
        for p in r['warns']:
            print('  [WARN]', p)
        if not r['fails'] and not r['warns']:
            print('  [PASS] 节奏 / 家族覆盖 / 反模式')
    bad = r['fails'] or (a.strict and r['warns'])
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
