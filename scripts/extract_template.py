#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""topmind-presentation · 模板路线：从参考 PPTX 提取主题色与字体，映射到最接近的内置风格

只读参考文件，不复制其版式或素材。输出：
    template.json  品牌色（dk1/lt1/accent1–6）、标题/正文字体、明暗倾向、
                   最接近的内置风格（按 accent 色差排序前 3）和建议写入 model 的字段
用法：
    python3 scripts/extract_template.py 参考.pptx [--out template.json]
说明：本技能不做自定义品牌引擎。品牌色只做记录与选型依据；交付仍用 12 套风格之一，
确需精确品牌色时在交付说明里注明差异，由用户决定是否接受。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
NS_A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'


def _hex(s: str) -> tuple[int, int, int]:
    s = s.lstrip('#')
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def _lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    def lin(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def delta_e(a: str, b: str) -> float:
    la, lb = _lab(_hex(a)), _lab(_hex(b))
    return sum((p - q) ** 2 for p, q in zip(la, lb)) ** 0.5


def luminance(h: str) -> float:
    r, g, b = _hex(h)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def read_theme(pptx: Path) -> dict:
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(pptx) as z:
        names = sorted(n for n in z.namelist() if re.match(r'ppt/theme/theme\d+\.xml$', n))
        if not names:
            raise SystemExit('错误：文件里没有 ppt/theme/theme*.xml，不是有效的 PPTX')
        root = ET.fromstring(z.read(names[0]))
    colors: dict[str, str] = {}
    scheme = root.find(f'.//{NS_A}clrScheme')
    if scheme is not None:
        for el in scheme:
            tag = el.tag.replace(NS_A, '')
            srgb = el.find(f'{NS_A}srgbClr')
            sys_ = el.find(f'{NS_A}sysClr')
            if srgb is not None:
                colors[tag] = srgb.get('val', '').upper()
            elif sys_ is not None:
                colors[tag] = (sys_.get('lastClr') or '').upper()
    fonts = {}
    for kind in ('majorFont', 'minorFont'):
        el = root.find(f'.//{NS_A}{kind}')
        if el is not None:
            lat = el.find(f'{NS_A}latin')
            ea = el.find(f'{NS_A}ea')
            fonts[kind] = {'latin': lat.get('typeface') if lat is not None else '',
                           'ea': ea.get('typeface') if ea is not None else ''}
    return {'colors': colors, 'fonts': fonts}


def nearest_styles(accent: str) -> list[dict]:
    consts = json.loads((ROOT / 'scripts' / 'layout-constants.json').read_text(encoding='utf-8'))
    out = []
    for sid, tok in consts['styles'].items():
        if sid.startswith('$') or not isinstance(tok, dict) or 'accent' not in tok:
            continue
        out.append({'style': sid, 'accent': tok['accent'].lstrip('#').upper(),
                    'deltaE': round(delta_e(accent, tok['accent']), 1)})
    return sorted(out, key=lambda d: d['deltaE'])[:3]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('pptx')
    ap.add_argument('--out', default='template.json')
    a = ap.parse_args()
    src = Path(a.pptx)
    if not src.exists():
        print(f'错误：找不到 {src}')
        return 2
    th = read_theme(src)
    c = th['colors']
    accent = c.get('accent1') or '1A73E8'
    bg = c.get('lt1') or 'FFFFFF'
    near = nearest_styles(accent)
    res = {
        'source': src.name,
        'brandColors': c,
        'fonts': th['fonts'],
        'themeHint': 'dark' if luminance(bg) < 0.35 else 'light',
        'nearestStyles': near,
        'suggest': {'style': near[0]['style'] if near else 'business-blue',
                    'theme': 'dark' if luminance(bg) < 0.35 else 'light'},
        'note': ('品牌主色与最接近风格色差 ΔE=%.1f；ΔE≤10 视为同色系，>10 请在交付说明里写明差异。'
                 % (near[0]['deltaE'] if near else -1)),
    }
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'品牌主色 #{accent} → 建议风格 {res["suggest"]["style"]}（ΔE {near[0]["deltaE"] if near else "?"}）· 主题 {res["suggest"]["theme"]}')
    print(f'已写出 {a.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
