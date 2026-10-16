#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""topmind-presentation · PPTX 像素回归

把三份黄金样张的 PPTX 逐页渲染，缩成 48×27 灰度缩略图，与 tests/pixel/baselines/ 比较。
缩略图只看版面结构（块的位置、明暗分布），对不同机器的字体细节不敏感。
    python3 scripts/pixel_regression.py            # 比较（CI 使用）
    python3 scripts/pixel_regression.py --update   # 版式有意改动后重建基线
判定：单页平均灰度差 > 阈值（默认 2.5/255）或页数变化即失败；失败页的对照图写到 tests/pixel/_diff/。
无 PIL / soffice / pdftoppm / Node 时 SKIP（退出 0），CI 环境里都装了。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
BASE = ROOT / 'tests' / 'pixel' / 'baselines'
DIFF = ROOT / 'tests' / 'pixel' / '_diff'
STEMS = ['2026-09-09-presentation-business-blue', '2026-09-09-research-mckinsey', '2026-09-09-architecture-graphite-dark']
W, H = 48, 27
THRESH = 2.5  # CI 实测跨机噪声 ≤1.2；一次表格行高调整约 3.4


def thumbs(pngs):
    from PIL import Image
    out = []
    for p in pngs:
        im = Image.open(p).convert('L').resize((W, H), Image.BOX)
        out.append(list(im.tobytes()))
    return out


def main() -> int:
    update = '--update' in sys.argv
    try:
        import PIL  # noqa: F401
        import env_probe
        from render_pptx_png import render
    except Exception as e:
        print(f'pixel_regression: SKIP（{e}）')
        return 0
    node, nm = env_probe.resolve()
    if not (node and nm):
        print('pixel_regression: SKIP（缺 Node / pptxgenjs）')
        return 0
    BASE.mkdir(parents=True, exist_ok=True)
    fails = []
    for stem in STEMS:
        model = ROOT / 'assets' / 'examples' / f'{stem}.model.json'
        with tempfile.TemporaryDirectory() as td:
            pptx = Path(td) / f'{stem}.pptx'
            r = subprocess.run([node, str(ROOT / 'scripts' / 'build_pptx.js'), str(pptx), f'--model={model}'],
                               capture_output=True, text=True, env=env_probe.node_env(nm))
            if r.returncode or not pptx.exists():
                print(f'  [FAIL] {stem}: build_pptx 失败 {r.stderr[-200:]}')
                fails.append(stem)
                continue
            try:
                pages = render(pptx, Path(td) / 'png', dpi=30)
            except RuntimeError as e:
                print(f'pixel_regression: SKIP（{e}）')
                return 0
            cur = thumbs(pages)
            bfile = BASE / f'{stem}.json'
            if update or not bfile.exists():
                bfile.write_text(json.dumps({'w': W, 'h': H, 'pages': cur}), encoding='utf-8')
                print(f'  [BASE] {stem}: 写入 {len(cur)} 页基线')
                continue
            base = json.loads(bfile.read_text(encoding='utf-8'))['pages']
            if len(base) != len(cur):
                print(f'  [FAIL] {stem}: 页数 {len(base)} → {len(cur)}')
                fails.append(stem)
                continue
            worst = 0.0
            for i, (a, b) in enumerate(zip(base, cur), 1):
                d = sum(abs(x - y) for x, y in zip(a, b)) / len(a)
                worst = max(worst, d)
                if d > THRESH:
                    fails.append(f'{stem}#{i}')
                    DIFF.mkdir(parents=True, exist_ok=True)
                    from PIL import Image
                    im = Image.new('L', (W * 2 + 2, H))
                    im.paste(Image.frombytes('L', (W, H), bytes(a)), (0, 0))
                    im.paste(Image.frombytes('L', (W, H), bytes(b)), (W + 2, 0))
                    im.resize(((W * 2 + 2) * 8, H * 8), Image.NEAREST).save(DIFF / f'{stem}-p{i:02d}.png')
                    print(f'  [FAIL] {stem} 第 {i} 页：平均差 {d:.1f} > {THRESH}')
            print(f'  [{"OK" if worst <= THRESH else "FAIL"}] {stem}: {len(cur)} 页，最大平均差 {worst:.2f}')
    if fails:
        print(f'pixel_regression: FAIL {len(fails)} 处（对照图见 tests/pixel/_diff/；若是有意改版式，跑 --update 重建基线）')
        return 1
    print('pixel_regression: OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
