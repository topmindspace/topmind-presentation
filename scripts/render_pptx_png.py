#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""topmind-presentation · PPTX 逐页渲染成 PNG（看图复核 / 像素回归共用）

    python3 scripts/render_pptx_png.py 报告.pptx --out 预览目录 [--dpi 60]
产出 预览目录/p-01.png …；需要 LibreOffice（soffice）与 poppler（pdftoppm）。
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def render(pptx: Path, out: Path, dpi: int = 60) -> list[Path]:
    soffice = shutil.which('soffice') or shutil.which('libreoffice')
    if not soffice or not shutil.which('pdftoppm'):
        raise RuntimeError('需要 LibreOffice（soffice）和 poppler（pdftoppm）')
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob('p-*.png'):
        old.unlink()
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        shutil.copy(pptx, d / 'deck.pptx')
        env = dict(os.environ, HOME=str(d))  # 独立用户目录，避免与正在运行的 soffice 冲突
        subprocess.run([soffice, '--headless', '--convert-to', 'pdf', 'deck.pptx'], cwd=d,
                       capture_output=True, timeout=300, env=env)
        if not (d / 'deck.pdf').exists():
            raise RuntimeError('soffice 转 PDF 失败')
        subprocess.run(['pdftoppm', '-r', str(dpi), '-png', 'deck.pdf', 'p'], cwd=d, capture_output=True, check=True)
        pages = sorted(d.glob('p-*.png'), key=lambda p: int(p.stem.split('-')[-1]))
        res = []
        for i, p in enumerate(pages, 1):
            dst = out / f'p-{i:02d}.png'
            shutil.move(str(p), dst)
            res.append(dst)
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description='PPTX → 逐页 PNG')
    ap.add_argument('pptx')
    ap.add_argument('--out', required=True)
    ap.add_argument('--dpi', type=int, default=60)
    a = ap.parse_args()
    try:
        pages = render(Path(a.pptx), Path(a.out), a.dpi)
    except Exception as e:
        print(f'错误：{e}')
        return 2
    print(f'已渲染 {len(pages)} 页 → {a.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
