#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TopPPT HTML · HTML 页高与容器裁切真值测量（可选 · 需 playwright）

静态估算（validate_report 页高溢出）是交付前硬门禁的保守近似，但它看不到
真实布局：「表格被半幅容器横向裁掉一列」这类缺陷在 strict 全绿时照样发生。
本脚本用无头浏览器量真实布局高度与容器裁切，供深度交付 / 排版争议时对照。

用法:
    python scripts/measure_height.py report.html
    python scripts/measure_height.py report.html --json
    python scripts/measure_height.py report.html --width 1920 --height 1080

缺 playwright / chromium 时打印指引并 exit 0（不阻断交付链）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def main() -> int:
    ap = argparse.ArgumentParser(description='HTML 页高真值测量（Playwright）')
    ap.add_argument('html', help='报告 HTML 路径')
    ap.add_argument('--width', type=int, default=1920)
    ap.add_argument('--height', type=int, default=1080)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--tolerance-px', type=int, default=8,
                    help='band 高度相对视口的容差（超过则记 overflow）')
    args = ap.parse_args()

    html = Path(args.html)
    if not html.exists():
        print(f'错误：HTML 不存在 {html}')
        return 2

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        # 托管 Python 可能未装 playwright；回落到本机已装 playwright 的解释器（不阻断）
        import shutil
        import subprocess
        candidates = []
        for name in ('python', 'python3', 'py'):
            exe = shutil.which(name)
            if exe:
                candidates.append(exe)
        # 常见用户安装路径不写死绝对盘符/用户名；仅用 PATH / py launcher
        for extra in (
            r'py',
        ):
            if Path(extra).exists() or shutil.which(extra):
                candidates.append(extra)
        alt = None
        for exe in candidates:
            try:
                probe = subprocess.run(
                    [exe, '-c', 'import playwright; print(1)'],
                    capture_output=True, text=True, timeout=8)
                if probe.returncode == 0 and '1' in (probe.stdout or ''):
                    alt = exe
                    break
            except Exception:
                continue
        if not alt:
            print('跳过：未安装 playwright（pip install playwright && playwright install chromium）')
            print('静态估算仍由 validate_report.py --strict 把关。')
            return 0
        # 用有 playwright 的解释器重跑本脚本（避免在无 playwright 的解释器里空转）
        import subprocess as sp
        cmd = [alt, str(Path(__file__).resolve()), str(html),
               '--width', str(args.width), '--height', str(args.height),
               '--tolerance-px', str(args.tolerance_px)]
        if args.json:
            cmd.append('--json')
        raise SystemExit(sp.call(cmd))

    url = html.resolve().as_uri()
    results = []
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as e:
            print(f'跳过：无法启动 chromium（{e}）。请执行 playwright install chromium。')
            return 0
        page = browser.new_page(viewport={'width': args.width, 'height': args.height})
        page.goto(url, wait_until='load', timeout=60000)
        # 关掉工具栏对页高的影响：尽量贴近演示全屏内容区
        page.evaluate("""() => {
          const bar = document.querySelector('.bar');
          if (bar) bar.style.display = 'none';
          document.documentElement.style.setProperty('--bar-h', '0px');
        }""")
        page.wait_for_timeout(200)
        bands = page.evaluate("""(tol) => {
          const vh = window.innerHeight;
          const nodes = [...document.querySelectorAll('section.band')];
          return nodes.map((el, i) => {
            const r = el.getBoundingClientRect();
            const h = Math.round(el.offsetHeight);
            const flow = el.classList.contains('band--flow');
            const id = el.id || ('band-' + (i + 1));
            return {
              index: i + 1,
              id,
              height: h,
              viewport: vh,
              overflow: !flow && h > vh + tol,
              flow,
              title: (el.querySelector('.shead__title, h1, h2')?.textContent || '').trim().slice(0, 40),
            };
          });
        }""", args.tolerance_px)
        # 容器级裁切真值：静态估算只看页高，看不到「表格/卡片被归属容器横向或纵向裁掉」——
        # 裁切比压缩更糟（数据直接不可见），且 strict 全绿时依然可能发生。
        clipped = page.evaluate("""() => {
          const sel = '.card,.panel,.metric,.sowhat,.exhibit,.kpi,.note,.tbl-wrap,td,th';
          const out = [];
          document.querySelectorAll(sel).forEach(el => {
            if (getComputedStyle(el).overflow === 'visible') return;
            const dw = el.scrollWidth - el.clientWidth;
            const dh = el.scrollHeight - el.clientHeight;
            if (dw > 3 || dh > 3) {
              const band = el.closest('section.band');
              out.push({
                container: (el.className || el.tagName).toString().slice(0, 30),
                page: band ? ([...document.querySelectorAll('section.band')].indexOf(band) + 1) : 0,
                overflowX: dw > 3 ? dw : 0,
                overflowY: dh > 3 ? dh : 0,
                text: (el.textContent || '').trim().slice(0, 24),
              });
            }
          });
          return out;
        }""")
        browser.close()

    over = [b for b in bands if b['overflow']]
    payload = {
        'file': str(html),
        'viewport': f'{args.width}x{args.height}',
        'bands': len(bands),
        'overflow_count': len(over),
        'overflow': over,
        'clipped_count': len(clipped),
        'clipped': clipped,
        'details': bands,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f'页高真值测量 · {html.name} @ {args.width}×{args.height}')
        print(f'  band 数 {len(bands)} · 超一屏 {len(over)} · 容器裁切 {len(clipped)}')
        for b in bands:
            mark = '✗' if b['overflow'] else ('·' if b['flow'] else '✓')
            print(f'  {mark} 第{b["index"]}页 {b["id"]:16} {b["height"]:4}px  {b["title"]}')
        if clipped:
            print('  ── 容器级裁切（内容越过归属容器，铁律 11）──')
            for c in clipped[:8]:
                axis = f'横向 {c["overflowX"]}px' if c['overflowX'] else f'纵向 {c["overflowY"]}px'
                print(f'  ✗ 第{c["page"]}页 {c["container"]} {axis}  「{c["text"]}」')
            print('  处理：换组合版式/减列/缩表 → 调容器宽度 → 拆页；不要靠容器滚动条遮掩')
        if over:
            print('  处理：列表化/精炼 → 压缩间距 → 多列 → 拆页；长结构页加 band--flow')
        if not over and not clipped:
            print('  结论：全部固定页高 band 未超视口，且无容器级裁切')
    return 0 if not over and not clipped else 1


if __name__ == '__main__':
    sys.exit(main())
