#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TopPPT HTML · 深度模式渲染对照（可选工具，缺失依赖自动跳过）

按需深度模式的「渲染对照闭环」：把交付 PPTX 渲染成可逐页对照的产物，并生成
一张并排对照页与一份**自动可算的偏差登记**（deviations.json）。

设计取舍（为什么不做成硬门禁）：
  · 渲染依赖外部程序（LibreOffice / PowerPoint COM / poppler），不是每台机器都有；
    本脚本在缺失依赖时**跳过并打印安装指引**，绝不阻断交付。
  · 视觉语义的最终判定仍需人眼——脚本负责把"对照材料"准备好并把可量化偏差算出来，
    而不是假装能自动判断"好不好看"。

用法：
    python scripts/render_compare.py <报告.pptx> [--html <报告.html>] [--out <输出目录>] [--dpi 96]

产物（默认输出到 <pptx 同目录>/render-compare/）：
    deck.pdf             PPTX 渲染的 PDF（soffice --convert-to pdf）
    page-01.png …        PDF 逐页位图（需 poppler/pdftoppm、mutool 或 ImageMagick 之一）
    compare.html         左 HTML / 右 PPTX 的并排对照页（无位图时右栏退化为 PDF 内嵌）
    deviations.json      自动可算的偏差登记（页数/主题/图表通道/数据表/图片/锚点）
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
LC_PATH = ROOT / 'scripts' / 'layout-constants.json'
NS = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
}


def load_constants() -> dict:
    try:
        return json.loads(LC_PATH.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}


def find_soffice() -> str | None:
    import os
    for var in ('SOFFICE', 'LIBREOFFICE', 'TOP_PPT_SOFFICE'):
        val = os.environ.get(var)
        if val and Path(val).exists():
            return val
    for name in ('soffice', 'soffice.exe', 'libreoffice'):
        found = shutil.which(name)
        if found:
            return found
    for cand in (r'C:\Program Files\LibreOffice\program\soffice.exe',
                 r'C:\Program Files (x86)\LibreOffice\program\soffice.exe',
                 '/Applications/LibreOffice.app/Contents/MacOS/soffice'):
        if Path(cand).exists():
            return cand
    return None


def find_pdf_rasterizer() -> tuple[str, str] | None:
    """返回 (可执行文件, 类型)：pdftoppm / mutool / magick。"""
    for name, kind in (('pdftoppm', 'pdftoppm'), ('mutool', 'mutool'),
                       ('magick', 'magick'), ('convert', 'magick')):
        found = shutil.which(name)
        if found:
            return found, kind
    return None


def pptx_metrics(pptx: Path) -> dict:
    """从 PPTX 包内直接读结构指标（零依赖，与 validate_pptx 同口径的轻量版）。"""
    import zipfile
    out = {'slide_count': 0, 'charts': 0, 'tables': 0, 'pictures': 0, 'themes': []}
    try:
        with zipfile.ZipFile(pptx) as zf:
            names = [n for n in zf.namelist() if re.match(r'ppt/slides/slide\d+\.xml$', n)]
            out['slide_count'] = len(names)
            for name in sorted(names, key=lambda n: int(re.search(r'(\d+)', n.split('/')[-1]).group(1))):
                root = ET.fromstring(zf.read(name))
                out['charts'] += len(root.findall('.//c:chart', NS))
                out['tables'] += len(root.findall('.//a:tbl', NS))
                out['pictures'] += len(root.findall('.//p:pic', NS))
    except (OSError, zipfile.BadZipFile, ET.ParseError, AttributeError):
        pass
    return out


def html_metrics(html: Path) -> dict:
    """HTML 侧结构指标：band 数 / data-theme / data-mode / 图表标记数。"""
    try:
        txt = html.read_text(encoding='utf-8')
    except OSError:
        return {}
    theme = re.search(r'<html[^>]*data-theme="([^"]+)"', txt)
    mode = re.search(r'<html[^>]*data-mode="([^"]+)"', txt)
    model = re.search(r'window\.REPORT_MODEL\s*=\s*(\{[\s\S]*?\})\s*;', txt)
    sections = 0
    if model:
        try:
            sections = len((json.loads(model.group(1)).get('sections') or []))
        except json.JSONDecodeError:
            sections = 0
    return {
        'bands': len(re.findall(r'<section[^>]*class="[^"]*\bband\b', txt)),
        'theme': theme.group(1) if theme else None,
        'mode': mode.group(1) if mode else None,
        'sections': sections,
        'charts': len(re.findall(r'data-chart="', txt)),
    }


def deviations(pptx_m: dict, html_m: dict, lc: dict) -> list[dict]:
    """自动可算的偏差登记（人眼判定之外的可量化部分）。"""
    devs: list[dict] = []
    if not html_m:
        return devs
    bands, sections = html_m.get('bands', 0), html_m.get('sections', 0)
    if bands and sections:
        expected_lo, expected_hi = sections + 3, sections + 7
        if not (expected_lo <= bands <= expected_hi):
            devs.append({'kind': 'page-count', 'severity': 'medium',
                         'detail': f'HTML band {bands} 不在模型 {sections} 章的预期区间 '
                                   f'[{expected_lo},{expected_hi}]（与 validate_report 同口径）'})
    # 允许 PPTX 与 HTML 相差 1 页（architecture 可省 Agenda；声明式图片不增页）
    if pptx_m.get('slide_count') and bands and abs(pptx_m['slide_count'] - bands) > 1:
        devs.append({'kind': 'page-count-mismatch', 'severity': 'medium',
                     'detail': f'PPTX {pptx_m["slide_count"]} 页 vs HTML {bands} 页（差 >1，需逐页核对）'})
    n_charts = html_m.get('charts', 0)
    if n_charts and pptx_m.get('charts', 0) == 0:
        devs.append({'kind': 'chart-channel', 'severity': 'high',
                     'detail': f'HTML 有 {n_charts} 个图表标记，但 PPTX 无 chart part——'
                               '若为形状通道图表属预期（需附数据表），否则应走原生通道'})
    return devs


def write_compare_html(out: Path, pptx: Path, html: Path | None,
                       pdf: Path | None, pngs: list[Path], devs: list[dict],
                       pptx_m: dict, html_m: dict) -> Path:
    def rows() -> str:
        if not devs:
            return '<tr><td colspan="3">自动可算项未发现偏差（视觉语义仍需人眼逐页对照）</td></tr>'
        return ''.join(
            f'<tr><td>{d["kind"]}</td><td>{d["severity"]}</td><td>{d["detail"]}</td></tr>'
            for d in devs)

    def png_gallery() -> str:
        if not pngs:
            return '<p class="note">未找到 PDF 位图工具（pdftoppm / mutool / magick）——右栏退化为 PDF 内嵌。</p>'
        return ''.join(f'<figure><img src="{p.name}" alt="page"><figcaption>{p.stem}</figcaption></figure>'
                       for p in pngs)

    left = (f'<iframe src="{html.resolve().as_uri()}" title="HTML 报告"></iframe>' if html
            else '<p class="note">未提供 --html，无法并排对照 HTML 侧。</p>')
    right = (f'<embed src="{pdf.name}" type="application/pdf" />' if pdf
             else '<p class="note">未渲染 PDF（缺 LibreOffice）。</p>')
    doc = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>渲染对照 · {pptx.name}</title>
<style>
:root{{--bd:#dadce0;--tx:#202124;--bg:#fff;--sf:#f8f9fa}}
*{{box-sizing:border-box}}body{{margin:0;font:14px/1.6 system-ui,"Microsoft YaHei",sans-serif;color:var(--tx);background:var(--bg)}}
header{{padding:16px 24px;border-bottom:1px solid var(--bd)}}
h1{{margin:0 0 4px;font-size:18px}}
.meta{{color:#5f6368;font-size:13px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--bd);height:70vh}}
.grid>div{{background:var(--bg);overflow:auto}}
iframe,embed{{width:100%;height:100%;border:0;display:block}}
table{{border-collapse:collapse;width:100%;margin:16px 0}}
th,td{{border:1px solid var(--bd);padding:8px 10px;text-align:left;vertical-align:top;font-size:13px}}
th{{background:var(--sf)}}
.gallery{{display:flex;flex-wrap:wrap;gap:12px;padding:0 24px 24px}}
figure{{margin:0;width:320px}}img{{width:100%;border:1px solid var(--bd);border-radius:6px}}
figcaption{{font-size:12px;color:#5f6368;padding-top:4px}}
.note{{padding:16px 24px;color:#5f6368}}
section{{padding:0 24px 8px}}
</style></head><body>
<header><h1>渲染对照 · {pptx.name}</h1>
<div class="meta">PPTX {pptx_m.get('slide_count', 0)} 页 · chart part {pptx_m.get('charts', 0)} · 表格 {pptx_m.get('tables', 0)} · 图片 {pptx_m.get('pictures', 0)}
{' · HTML ' + str(html_m.get('bands', 0)) + ' 页（' + str(html_m.get('mode') or '?') + '/' + str(html_m.get('theme') or '?') + '）' if html_m else ''}</div></header>
<section><h2 style="font-size:15px;margin:16px 0 0">自动可算偏差登记</h2></section>
<table><thead><tr><th>类型</th><th>严重度</th><th>说明</th></tr></thead><tbody>{rows()}</tbody></table>
<div class="grid"><div>{left}</div><div>{right}</div></div>
<section><h2 style="font-size:15px">PPTX 逐页位图</h2></section>
<div class="gallery">{png_gallery()}</div>
</body></html>'''
    target = out / 'compare.html'
    target.write_text(doc, encoding='utf-8')
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='TopPPT HTML 深度模式渲染对照（可选工具）')
    parser.add_argument('pptx', help='交付 PPTX 路径')
    parser.add_argument('--html', help='对应 HTML 报告路径（可选，用于并排对照）')
    parser.add_argument('--out', help='输出目录（默认 <pptx 同目录>/render-compare）')
    parser.add_argument('--dpi', type=int, default=96, help='位图 DPI（默认 96）')
    args = parser.parse_args(argv)

    pptx = Path(args.pptx).resolve()
    if not pptx.exists():
        print(f'错误： 找不到 {pptx}')
        return 2
    out = Path(args.out).resolve() if args.out else pptx.parent / 'render-compare'
    out.mkdir(parents=True, exist_ok=True)

    lc = load_constants()
    pptx_m = pptx_metrics(pptx)
    html_path = Path(args.html).resolve() if args.html else None
    html_m = html_metrics(html_path) if html_path and html_path.exists() else {}
    devs = deviations(pptx_m, html_m, lc)

    pdf: Path | None = None
    pngs: list[Path] = []
    soffice = find_soffice()
    if soffice:
        print(f'LibreOffice: {soffice}')
        try:
            subprocess.run([soffice, '--headless', '--norestore', '--convert-to', 'pdf',
                            '--outdir', str(out), str(pptx)],
                           check=True, capture_output=True, timeout=300)
            cand = out / (pptx.stem + '.pdf')
            pdf = cand if cand.exists() else None
            print(f'  已渲染: {pdf.name}' if pdf else '  渲染完成但未找到 PDF 产物')
        except (subprocess.SubprocessError, OSError) as exc:
            print(f'  渲染失败（跳过，不阻断交付）: {exc}')
    else:
        print('未找到 LibreOffice（soffice）——跳过 PPTX 渲染。')
        print('  安装后可重跑：Windows https://www.libreoffice.org/download/ ；')
        print('  或用环境变量 SOFFICE 指定 soffice 可执行文件路径。')

    raster = find_pdf_rasterizer()
    if pdf and raster:
        exe, kind = raster
        try:
            if kind == 'pdftoppm':
                subprocess.run([exe, '-r', str(args.dpi), '-png', str(pdf), str(out / 'page')],
                               check=True, capture_output=True, timeout=300)
            elif kind == 'mutool':
                subprocess.run([exe, 'draw', '-r', str(args.dpi), '-o', str(out / 'page-%02d.png'), str(pdf)],
                               check=True, capture_output=True, timeout=300)
            else:
                subprocess.run([exe, '-density', str(args.dpi), str(pdf), str(out / 'page-%02d.png')],
                               check=True, capture_output=True, timeout=300)
            pngs = sorted(out.glob('page*.png'))
            print(f'  逐页位图: {len(pngs)} 张')
        except (subprocess.SubprocessError, OSError) as exc:
            print(f'  位图化失败（跳过）: {exc}')
    elif pdf:
        print('未找到 PDF 位图工具（pdftoppm / mutool / magick）——保留 PDF，对照页右栏内嵌 PDF。')

    compare = write_compare_html(out, pptx, html_path, pdf, pngs, devs, pptx_m, html_m)
    (out / 'deviations.json').write_text(
        json.dumps({'pptx': pptx_m, 'html': html_m, 'deviations': devs}, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8')
    print(f'对照页: {compare}')
    print(f'偏差登记: {out / "deviations.json"}（{len(devs)} 项自动可算偏差）')
    print('提示：视觉语义（底色系统 / 图表形态 / 留白节奏）仍需人眼在对照页上逐页确认。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
