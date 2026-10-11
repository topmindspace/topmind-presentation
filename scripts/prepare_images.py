#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TopPPT HTML · 用户图片素材准备

把用户提供的图片处理成**可直接放进报告**的素材：
  ① 读尺寸/格式/体积（纯标准库解析 PNG/JPEG/GIF/WebP/SVG 头部，无需第三方依赖）；
  ② 按 imageSpec.recommendedSizePx 检查是否够大（不足会提示，避免放大糊）；
  ③ 需要时缩放/压缩（检测到 Pillow 才启用，缺失自动跳过并给出建议）；
  ④ 生成两种落地形态：**data: 内联**（单文件零外链，随报告走）或 **相对路径**（体积大时推荐）；
  ⑤ 直接产出可粘贴的 HTML 片段与 REPORT_MODEL 的 image 对象片段。

用法:
    python scripts/prepare_images.py <图片|目录> [更多图片…]
        [--layout full|half|bleed|grid|compare|wall]   默认 full
        [--out <目录>]        输出目录（默认当前目录下的 report-assets/）
        [--mode inline|path]  inline=base64 内联（默认，受体积上限约束）；path=复制到 out 并用相对路径
        [--max-bytes N]       单图内联上限（默认取 layout-constants.json imageSpec.maxInlineBytes）
        [--json]              只打印机器可读 JSON
        [--no-resize]         禁用缩放（即使 Pillow 可用）

产出（写到 --out 目录）:
    images-snippets.html   HTML 图片片段（.media 族，含占位示例）
    images-model.json      REPORT_MODEL 的 image 对象片段（可直接并入 sections[]）

依赖：仅标准库；可选 Pillow（有则缩放/压缩，无则原样内联并提示）。
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
LC_PATH = Path(__file__).resolve().parent / 'layout-constants.json'
IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg'}
MIME = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.webp': 'image/webp', '.gif': 'image/gif', '.svg': 'image/svg+xml'}


def load_image_spec() -> dict:
    try:
        lc = json.loads(LC_PATH.read_text(encoding='utf-8'))
        spec = lc.get('imageSpec') or {}
        return spec if isinstance(spec, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


SPEC = load_image_spec()


def ratio_num(spec: str) -> float:
    """'3:1' → 3.0；非法返回 0。"""
    m = re.match(r'\s*(\d+(?:\.\d+)?)\s*[:/×x]\s*(\d+(?:\.\d+)?)', str(spec or ''))
    if not m:
        return 0.0
    a, b = float(m.group(1)), float(m.group(2))
    return a / b if a > 0 and b > 0 else 0.0


def target_width(layout: str) -> int:
    """imageSpec.recommendedSizePx 形如 '2000×1125' → 2000。"""
    raw = str((SPEC.get('recommendedSizePx') or {}).get(layout) or '2000×1125')
    m = re.match(r'\s*(\d+)', raw)
    return int(m.group(1)) if m else 2000


def read_size(path: Path) -> tuple[int, int] | None:
    """纯标准库读位图尺寸（PNG/JPEG/GIF/WebP）；SVG 走文本解析。"""
    try:
        data = path.read_bytes()[:65536]
    except OSError:
        return None
    if len(data) < 16:
        return None
    # PNG
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')
    # GIF
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return int.from_bytes(data[6:8], 'little'), int.from_bytes(data[8:10], 'little')
    # JPEG：扫描 SOF 段
    if data[:2] == b'\xff\xd8':
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            if marker == 0xD9:
                break
            seg_len = int.from_bytes(data[i + 2:i + 4], 'big')
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                h = int.from_bytes(data[i + 5:i + 7], 'big')
                w = int.from_bytes(data[i + 7:i + 9], 'big')
                return w, h
            i += 2 + max(2, seg_len)
        return None
    # WebP
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        chunk = data[12:16]
        if chunk == b'VP8X' and len(data) >= 30:
            w = int.from_bytes(data[24:27], 'little') + 1
            h = int.from_bytes(data[27:30], 'little') + 1
            return w, h
        if chunk == b'VP8 ' and len(data) >= 30:
            w = int.from_bytes(data[26:28], 'little') & 0x3FFF
            h = int.from_bytes(data[28:30], 'little') & 0x3FFF
            return w, h
        if chunk == b'VP8L' and len(data) >= 25:
            bits = int.from_bytes(data[21:25], 'little')
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return None


def read_svg_size(path: Path) -> tuple[int, int] | None:
    try:
        head = path.read_text(encoding='utf-8', errors='replace')[:2048]
    except OSError:
        return None
    w = re.search(r'width\s*=\s*["\']?\s*(\d+(?:\.\d+)?)', head)
    h = re.search(r'height\s*=\s*["\']?\s*(\d+(?:\.\d+)?)', head)
    if w and h:
        return int(float(w.group(1))), int(float(h.group(1)))
    vb = re.search(r'viewBox\s*=\s*["\']([\d.\-\s,]+)["\']', head)
    if vb:
        nums = re.split(r'[\s,]+', vb.group(1).strip())
        if len(nums) == 4:
            return int(float(nums[2])), int(float(nums[3]))
    return None


def ratio_label(w: int, h: int) -> str:
    if not w or not h:
        return '未知'
    from math import gcd
    g = gcd(w, h) or 1
    a, b = w // g, h // g
    if a > 40 or b > 40:
        return f'{w / h:.2f}:1'
    return f'{a}:{b}'


def try_resize(src: Path, dst: Path, want_w: int) -> bool:
    """有 Pillow 时缩放/压缩；无则返回 False（调用方回落原图）。"""
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return False
    try:
        with Image.open(src) as im:
            im.load()
            w, h = im.size
            if w > want_w:
                im = im.resize((want_w, max(1, round(h * want_w / w))), Image.LANCZOS)
            if dst.suffix.lower() in ('.jpg', '.jpeg'):
                if im.mode in ('RGBA', 'P', 'LA'):
                    bg = Image.new('RGB', im.size, (255, 255, 255))
                    bg.paste(im.convert('RGBA'), mask=im.convert('RGBA').split()[-1])
                    im = bg
                else:
                    im = im.convert('RGB')
                im.save(dst, 'JPEG', quality=82, optimize=True, progressive=True)
            else:
                im.save(dst, optimize=True)
        return True
    except Exception:
        return False


def collect_inputs(args_paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for raw in args_paths:
        p = Path(raw)
        if p.is_dir():
            out.extend(sorted(q for q in p.rglob('*') if q.suffix.lower() in IMAGE_EXT))
        elif p.is_file():
            out.append(p)
        else:
            print(f'[跳过] 不存在: {raw}')
    seen, uniq = set(), []
    for p in out:
        if p.resolve() not in seen:
            seen.add(p.resolve())
            uniq.append(p)
    return uniq


def main() -> int:
    ap = argparse.ArgumentParser(description='TopPPT HTML 用户图片素材准备')
    ap.add_argument('paths', nargs='+', help='图片文件或目录（可多个）')
    ap.add_argument('--layout', default='full', choices=list(SPEC.get('layouts') or
                    ['full', 'half', 'bleed', 'grid', 'compare', 'wall']))
    ap.add_argument('--out', default=None, help='输出目录（默认 ./report-assets）')
    ap.add_argument('--mode', default='inline', choices=['inline', 'path'])
    ap.add_argument('--max-bytes', type=int, default=int(SPEC.get('maxInlineBytes') or 1572864))
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--no-resize', action='store_true')
    args = ap.parse_args()

    files = collect_inputs(args.paths)
    if not files:
        print('没有可处理的图片（支持 ' + '/'.join(sorted(e.lstrip(".") for e in IMAGE_EXT)) + '）。')
        return 2

    out_dir = Path(args.out) if args.out else Path.cwd() / 'report-assets'
    out_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = out_dir / 'assets'
    want_w = target_width(args.layout)
    max_total = int(SPEC.get('maxTotalInlineBytes') or 8388608)

    rows, html_bits, model_items, notes = [], [], [], []
    total_inline = 0
    for src in files:
        ext = src.suffix.lower()
        size = read_svg_size(src) if ext == '.svg' else read_size(src)
        w, h = size if size else (0, 0)
        work = src
        resized = False
        if not args.no_resize and w > want_w and ext != '.svg':
            cand = out_dir / (src.stem + f'-{want_w}' + ('.jpg' if ext in ('.jpg', '.jpeg') else ext))
            if try_resize(src, cand, want_w):
                work, resized = cand, True
                size = read_size(cand)
                w, h = size if size else (w, h)
        nbytes = work.stat().st_size
        if not resized and w and w < want_w * 0.75:
            notes.append(f'{src.name}: 宽 {w}px < 建议 {want_w}px（放大易糊；请换更高分辨率原图或改小版式）')
        want_ratio = ratio_num((SPEC.get('ratioDefault') or {}).get(args.layout) or '')
        fit_cls = ''
        if w and h and want_ratio:
            got = w / h
            if abs(got - want_ratio) / want_ratio > 0.25:
                fit_cls = ' media--contain'   # 比例差得多 → HTML 也用 contain，与模型 fit 保持一致
                notes.append(f'{src.name}: 实际比例 {got:.2f}:1 与 {args.layout} 版式锁定比例 '
                             f'{want_ratio:.2f}:1 相差较大 → 已按 fit:"contain" 输出（完整显示留白）；'
                             f'若希望裁切填满请换更贴合比例的版式/素材')
        if ext == '.svg':
            notes.append(f'{src.name}: SVG 为矢量（好）；注意外链字体/图片需内联，否则破坏零外链铁律')

        use_path = args.mode == 'path' or nbytes > args.max_bytes
        if use_path:
            assets_dir.mkdir(parents=True, exist_ok=True)
            dst = assets_dir / work.name
            if work.resolve() != dst.resolve():
                shutil.copy2(work, dst)
            url = f'assets/{dst.name}'
            form = '相对路径'
        else:
            b64 = base64.b64encode(work.read_bytes()).decode('ascii')
            url = f'data:{MIME.get(ext, "image/png")};base64,{b64}'
            form = 'data: 内联'
            total_inline += len(url)
        if nbytes > args.max_bytes and args.mode != 'path':
            notes.append(f'{src.name}: {nbytes // 1024}KB > 内联上限 {args.max_bytes // 1024}KB → 已改用相对路径')

        rows.append({'file': src.name, 'w': w, 'h': h, 'ratio': ratio_label(w, h),
                     'kb': nbytes // 1024, 'form': form, 'url': url,
                     'targetW': want_w, 'resized': resized})
        lock_cls = (SPEC.get('ratioCssClass') or {}).get(args.layout) or f'media--r{ratio_class(w, h)}'
        html_bits.append(
            f'<figure class="media {lock_cls}{fit_cls} rv">\n'
            f'  <img src="{url}" '
            f'alt="{src.stem}">\n'
            f'  <figcaption class="media__cap--below">图：{src.stem}（{w}×{h} · {ratio_label(w, h)}）</figcaption>\n'
            f'</figure>')
        model_items.append({'src': url, 'alt': src.stem, 'caption': f'图：{src.stem}'})

    if total_inline > max_total:
        notes.append(f'内联总量 {total_inline // 1024}KB > 上限 {max_total // 1024}KB：'
                     '建议部分图片改用 --mode path（相对路径）')

    layout = args.layout
    if len(model_items) > 1 and layout not in (SPEC.get('multiLayouts') or ['grid', 'compare', 'wall']):
        notes.append(f'共 {len(model_items)} 张图但 layout={layout}（单图版式）→ 多图请用 grid/compare/wall')
    want_ratio = ratio_num((SPEC.get('ratioDefault') or {}).get(layout) or '')
    fit = SPEC.get('fitDefault') or 'cover'
    if want_ratio and any(r['w'] and r['h'] and abs(r['w'] / r['h'] - want_ratio) / want_ratio > 0.25
                          for r in rows):
        fit = 'contain'   # 比例差得多时默认完整显示，避免 cover 切掉关键内容
    image_model = {'layout': layout, 'fit': fit,
                   'caption': f'图：{model_items[0]["alt"]}' if model_items else ''}
    if len(model_items) == 1:
        image_model['src'] = model_items[0]['src']
        image_model['alt'] = model_items[0]['alt']
    else:
        image_model['items'] = model_items

    (out_dir / 'images-snippets.html').write_text('\n\n'.join(html_bits), encoding='utf-8')
    (out_dir / 'images-model.json').write_text(
        json.dumps(image_model, ensure_ascii=False, indent=2), encoding='utf-8')

    if args.json:
        print(json.dumps({'layout': layout, 'out': str(out_dir), 'images': rows, 'notes': notes},
                         ensure_ascii=False, indent=2))
        return 0

    print(f'图片素材准备 · layout={layout} · 建议宽 {want_w}px · 共 {len(rows)} 张')
    print(f'{"文件":<28}{"尺寸":<14}{"比例":<10}{"体积":<10}形态')
    for r in rows:
        dim = f'{r["w"]}×{r["h"]}' if r['w'] else '未知'
        print(f'{r["file"][:26]:<28}{dim:<14}{r["ratio"]:<10}{str(r["kb"]) + "KB":<10}{r["form"]}'
              + ('（已缩放）' if r['resized'] else ''))
    if notes:
        print('\n提示:')
        for n in notes:
            print('  · ' + n)
    print(f'\n已写出:\n  {out_dir / "images-snippets.html"}  （HTML .media 片段，粘进对应 section.band）')
    print(f'  {out_dir / "images-model.json"}      （REPORT_MODEL 的 image 对象，并入 sections[]）')
    if args.mode == 'inline':
        print('  说明: 内联形态保持「单文件零外链」；体积大时改用 --mode path 并把 assets/ 目录随报告一起交付。')
    print('  占位: 暂无图时先在模型写 image.placeholder=true（正文用 .media--ph），交付前替换 src 即可。')
    return 0


def ratio_class(w: int, h: int) -> str:
    """把实际比例归一到 .media--r* 锁定类（16-9 / 4-3 / 3-2 / 1-1 / 21-9）。"""
    if not w or not h:
        return '16-9'
    r = w / h
    for name, val in (('21-9', 21 / 9), ('16-9', 16 / 9), ('3-2', 1.5), ('4-3', 4 / 3), ('1-1', 1.0)):
        if abs(r - val) / val <= 0.06:
            return name
    return '16-9' if r > 1.4 else ('1-1' if r > 0.9 else '4-3')


if __name__ == '__main__':
    sys.exit(main())
