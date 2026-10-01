#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TopPPT HTML · 图标包校验（assets/icons/）

检查：
  1. 每个 *.svg 合法 XML；根为 svg；viewBox 恰为 "0 0 24 24"
  2. 描边风格统一：fill="none"、stroke="currentColor"、stroke-width="1.8"、
     stroke-linecap/linejoin="round"（同家族铁律）
  3. 只含允许元素（path/circle/rect/ellipse/line/polyline/polygon），无 <text>/<image>，
     无 fill="#..." 彩色填充（禁三方彩色标），无外链
  4. index.json 一致性：icons 键 ↔ <name>.svg 文件一一对应；defaults 5~8 个且都在包内；
     keywords 非空且含自身名
  5. 每个图标有同名 512px PNG（PPTX 通道预渲染）

用法: python scripts/check_icons.py [--strict]
退出码：0=通过；1=有 FAIL；2=仅 WARN（--strict 下也按 1 处理）
"""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICON_DIR = ROOT / 'assets' / 'icons'
ALLOWED = {'path', 'circle', 'rect', 'ellipse', 'line', 'polyline', 'polygon'}


def main() -> int:
    strict = '--strict' in sys.argv
    fails: list[str] = []
    warns: list[str] = []

    idx_path = ICON_DIR / 'index.json'
    if not idx_path.exists():
        print('FAIL: assets/icons/index.json 缺失')
        return 1
    index = json.loads(idx_path.read_text(encoding='utf-8'))
    icons_meta = index.get('icons') or {}
    if index.get('count') != len(icons_meta):
        fails.append(f"index.json count={index.get('count')} 与实际条目 {len(icons_meta)} 不一致")

    svg_names = {p.stem for p in ICON_DIR.glob('*.svg')}
    meta_names = set(icons_meta)
    for n in sorted(meta_names - svg_names):
        fails.append(f'index.json 有条目但缺文件: {n}.svg')
    for n in sorted(svg_names - meta_names):
        warns.append(f'有 SVG 文件但 index.json 未登记: {n}.svg')

    defaults = index.get('defaults') or []
    if not 5 <= len(defaults) <= 8:
        fails.append(f'defaults 应 5~8 个，实际 {len(defaults)} 个')
    for d in defaults:
        if d not in icons_meta:
            fails.append(f'default 图标不在包内: {d}')

    for name, meta in icons_meta.items():
        kws = meta.get('keywords') or []
        if not kws:
            warns.append(f'{name}: keywords 为空')
        elif name not in kws:
            warns.append(f'{name}: keywords 未含自身名')
        png = ICON_DIR / f'{name}.png'
        if not png.exists():
            fails.append(f'缺预渲染 PNG: {name}.png')
        elif png.stat().st_size < 1024:
            warns.append(f'{name}.png 疑似过小（{png.stat().st_size}B）')

    for name in sorted(svg_names):
        p = ICON_DIR / f'{name}.svg'
        try:
            root = ET.fromstring(p.read_text(encoding='utf-8'))
        except ET.ParseError as e:
            fails.append(f'{name}.svg XML 非法: {e}')
            continue
        tag = root.tag.split('}')[-1]
        if tag != 'svg':
            fails.append(f'{name}.svg 根元素不是 svg: {tag}')
            continue
        if root.get('viewBox') != '0 0 24 24':
            fails.append(f"{name}.svg viewBox={root.get('viewBox')!r}（必须 '0 0 24 24'）")
        style = {
            'fill': root.get('fill'), 'stroke': root.get('stroke'),
            'stroke-width': root.get('stroke-width'),
            'stroke-linecap': root.get('stroke-linecap'),
            'stroke-linejoin': root.get('stroke-linejoin'),
        }
        want = {'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '1.8',
                'stroke-linecap': 'round', 'stroke-linejoin': 'round'}
        if style != want:
            fails.append(f'{name}.svg 风格属性偏离家族规范: {style}')
        for el in root.iter():
            t = el.tag.split('}')[-1]
            if t == 'svg':
                continue
            if t not in ALLOWED:
                fails.append(f'{name}.svg 含非法元素 <{t}>（禁 text/image/彩色填充）')
            for k, v in el.attrib.items():
                if k == 'fill' and v not in ('none',):
                    fails.append(f'{name}.svg <{t}> 有彩色填充 fill={v}')
                if isinstance(v, str) and v.startswith('http'):
                    fails.append(f'{name}.svg 含外链: {v[:60]}')

    for w in warns:
        print(f'WARN: {w}')
    for f in fails:
        print(f'FAIL: {f}')
    print(f'[check_icons] {len(svg_names)} svg / {len(icons_meta)} index / '
          f'{len(defaults)} defaults: {"OK" if not fails else "FAIL"}')
    if fails:
        return 1
    if warns and strict:
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
