#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""视觉填充率与重心门禁（VISUAL_FILL / VISUAL_EMPTY_BLOCK / VISUAL_OFF_CENTER）

为什么需要：几何门禁只看形状包围盒，文本框很宽但字很少、卡片固定高度留下半页空白时会「全绿但很空」。
本门禁看渲染后的像素：PPTX → LibreOffice → PDF → PNG，在版心正文区（标题带以下、页脚以上）
划 24×12 栅格，统计有墨水的格子。

判定（内容页；封面 / 大纲 / 章节扉页 / 收尾页豁免）：
  - VISUAL_FILL        有墨格占比 < fillMin（默认 0.20）
  - VISUAL_EMPTY_BLOCK 最大连续空白矩形 ≥ emptyMax（默认 0.30 正文区）
  - VISUAL_OFF_CENTER  墨水重心偏离正文区中心 > centerMax（默认 0.20，按宽/高归一）
阈值单源：scripts/layout-constants.json → qa.visualFill（缺省用上面的默认值）。

用法：
  python scripts/check_visual_fill.py deck.pptx --model=deck.model.json [--strict] [--keep=DIR]
  python scripts/check_visual_fill.py --png-dir=DIR --model=deck.model.json   # 已有逐页 PNG（p-01.png…）
退出码：strict 下有任一问题 → 1；渲染环境缺失（无 soffice/pdftoppm）→ 2（CI 必须装好，不得静默跳过）。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULTS = {"fillMin": 0.20, "emptyMax": 0.30, "centerMax": 0.20,
            "grid": [24, 12], "body": [0.27, 0.90, 0.05, 0.95], "inkDelta": 30, "cellInk": 0.003,
            "dpi": 50}


def load_cfg() -> dict:
    cfg = dict(DEFAULTS)
    try:
        lc = json.loads((ROOT / "scripts" / "layout-constants.json").read_text(encoding="utf-8"))
        cfg.update(((lc.get("qa") or {}).get("visualFill") or {}))
    except (OSError, json.JSONDecodeError):
        pass
    return cfg


def render(pptx: Path, out: Path, dpi: int) -> list[Path]:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice or not shutil.which("pdftoppm"):
        print("[visual_fill] FAIL: 缺 LibreOffice(soffice) 或 poppler(pdftoppm)，无法渲染。", file=sys.stderr)
        sys.exit(2)
    subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(out), str(pptx)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
    pdf = out / (pptx.stem + ".pdf")
    subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(pdf), str(out / "p")], check=True, timeout=300)
    return sorted(Path(p) for p in glob.glob(str(out / "p-*.png")))


def grid_of(png: Path, cfg: dict):
    import numpy as np
    from PIL import Image
    im = np.asarray(Image.open(png).convert("RGB")).astype(int)
    H, W, _ = im.shape
    bg = np.median(im.reshape(-1, 3), axis=0)
    ink = np.abs(im - bg).sum(2) > cfg["inkDelta"]
    y0, y1, x0, x1 = cfg["body"]
    b = ink[int(H * y0):int(H * y1), int(W * x0):int(W * x1)]
    h, w = b.shape
    gx, gy = cfg["grid"]
    return np.array([[b[i * h // gy:(i + 1) * h // gy, j * w // gx:(j + 1) * w // gx].mean() > cfg["cellInk"]
                      for j in range(gx)] for i in range(gy)])


def max_empty_rect(o) -> float:
    e = ~o
    H, W = e.shape
    hist = [0] * W
    best = 0
    for i in range(H):
        for j in range(W):
            hist[j] = hist[j] + 1 if e[i, j] else 0
        st: list[int] = []
        for j in range(W + 1):
            cur = hist[j] if j < W else 0
            while st and hist[st[-1]] >= cur:
                hh = hist[st.pop()]
                left = st[-1] + 1 if st else 0
                best = max(best, hh * (j - left))
            st.append(j)
    return best / float(H * W)


def structural_pages(model: dict | None, n: int) -> set[int]:
    """1-based 页号：封面、大纲（若有）、收尾页；参考资料页（若渲染）在收尾前同样豁免。"""
    if not model:
        return {1, n}
    s = {1, n}
    if model.get("agenda"):
        s.add(2)
    expected = 1 + (1 if model.get("agenda") else 0) + len(model.get("sections") or []) + 1
    for k in range(expected, n):  # 多出来的尾页（refs 等）
        s.add(k)
    # 章节扉页（chapter）是结构页：大号章节号 + 留白是设计本意，与封面同口径豁免
    off = 1 + (1 if model.get("agenda") else 0)
    for i, sec in enumerate(model.get("sections") or []):
        if isinstance(sec, dict) and sec.get("type") == "chapter":
            s.add(off + i + 1)
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx", nargs="?")
    ap.add_argument("--model")
    ap.add_argument("--png-dir")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--keep")
    a = ap.parse_args()
    cfg = load_cfg()
    model = json.loads(Path(a.model).read_text(encoding="utf-8")) if a.model else None
    if a.png_dir:
        pngs = sorted(Path(p) for p in glob.glob(os.path.join(a.png_dir, "p-*.png")))
    elif a.pptx:
        out = Path(a.keep) if a.keep else Path(tempfile.mkdtemp(prefix="vfill-"))
        out.mkdir(parents=True, exist_ok=True)
        pngs = render(Path(a.pptx).resolve(), out, int(cfg["dpi"]))
    else:
        ap.error("需要 pptx 或 --png-dir")
    if not pngs:
        print("[visual_fill] FAIL: 无渲染页", file=sys.stderr)
        return 1
    skip = structural_pages(model, len(pngs))
    issues = []
    for i, p in enumerate(pngs, 1):
        if i in skip:
            continue
        o = grid_of(p, cfg)
        fill = float(o.mean())
        empty = max_empty_rect(o)
        import numpy as np
        ys, xs = np.nonzero(o)
        cx = (xs.mean() + .5) / o.shape[1] - .5 if len(xs) else 0.0
        cy = (ys.mean() + .5) / o.shape[0] - .5 if len(ys) else 0.0
        tag = f"第{i}页 fill={fill:.2f} maxEmpty={empty:.2f} 重心=({cx:+.2f},{cy:+.2f})"
        bad = []
        if fill < cfg["fillMin"]:
            bad.append(("VISUAL_FILL", f"正文区有墨格 {fill:.0%} < {cfg['fillMin']:.0%}"))
        if empty >= cfg["emptyMax"]:
            bad.append(("VISUAL_EMPTY_BLOCK", f"最大连续空白 {empty:.0%} ≥ {cfg['emptyMax']:.0%}"))
        if abs(cx) > cfg["centerMax"] or abs(cy) > cfg["centerMax"]:
            bad.append(("VISUAL_OFF_CENTER", f"重心偏移 ({cx:+.2f},{cy:+.2f}) > {cfg['centerMax']}"))
        print(("  [FAIL] " if bad else "  [PASS] ") + tag)
        for code, msg in bad:
            print(f"         {code}: {msg}")
            issues.append((i, code))
    print(f"[visual_fill] 内容页 {len(pngs) - len(skip)} 页 · 问题 {len(issues)} 处"
          + (f"（页 {sorted({i for i, _ in issues})}）" if issues else ""))
    return 1 if (issues and a.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
