#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TopPPT HTML · 交付质量门禁（HTML/PPTX + Evals 确定性检查 + rubric 启发式）

用法:
    python scripts/quality_gate.py report.html
    # Mode A / presentation 自动对 validate_report 附加 --layout-qa
    python scripts/quality_gate.py report.html --pptx report.pptx --model report.model.json
    python scripts/quality_gate.py report.html --trace trace.json --json
    python scripts/quality_gate.py report.html --require-rubric 60
    python scripts/quality_gate.py report.html --deliver          # 末尾生成可粘贴的交付说明

定位:
    validate_* 回答「结构是否合格」；本脚本再合并：
    ① evals/run_evals.py 的确定性/效率检查
    ② 无 LLM 的 rubric 启发式（content/layout/chart/infographic/tone 五维）
    ③ --deliver：按 SKILL.md「交付说明」七要素（路径/字节数/模式/风格/篇幅/格式/校验+引用）
       生成结构化交付说明——七要素缺一即 gate FAIL，杜绝手拼遗漏
    交付时一键跑完；互不依赖的子进程门禁（HTML / PPTX / evals）并行执行以缩短墙钟。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
import checks_html  # noqa: E402  承载/多样性/组合版式单源

ROOT = Path(__file__).resolve().parent.parent
LC = json.loads((ROOT / 'scripts' / 'layout-constants.json').read_text(encoding='utf-8'))
RUBRIC_PATH = ROOT / 'evals' / 'rubric.schema.json'


def run(cmd: list[str]) -> tuple[int, str, float]:
    """带计时的子进程执行（elapsed 秒用于交付耗时基线，v8.3 起）。"""
    t0 = time.perf_counter()
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    out = (r.stdout or '') + (r.stderr or '')
    return r.returncode, out, time.perf_counter() - t0


def kb(n: int) -> str:
    return f'{n / 1024:.1f}KB'


def build_delivery(html: Path, pptx: Path | None, gates: list[dict], rubric: dict) -> dict:
    """SKILL.md「交付说明」七要素：路径 / 字节数 / 模式 / 风格 / 篇幅 / 格式 / 校验+引用。"""
    txt = html.read_text(encoding='utf-8')
    head = txt[:3000]

    def attr(name: str) -> str:
        m = re.search(rf'{name}="([^"]+)"', head)
        return m.group(1) if m else ''

    all_bands = bands(txt)
    content = checks_html.content_bands(txt)  # 与 composite_pages 同一口径（防两处维护）
    refs = sorted(set(re.findall(r'id="(ref-\d+)"', txt)), key=lambda s: int(s.split('-')[1]))
    note = {
        'file': str(html),
        'bytes': html.stat().st_size,
        'mode': attr('data-mode'),
        'style': attr('data-style'),
        'theme': attr('data-theme'),
        'pages': len(all_bands),
        'content_pages': len(content),
        'format': 'HTML' + (' + PPTX' if pptx else ''),
        'refs': len(refs),
        'validation': {g['name']: ('通过' if g['ok'] else '未通过') for g in gates},
        'rubric': rubric['score'],
    }
    if pptx and pptx.exists():
        note['pptx'] = {'file': str(pptx), 'bytes': pptx.stat().st_size}
    return note


def render_delivery(note: dict) -> str:
    lines = [
        f"- 文件：{note['file']}（{kb(note['bytes'])}）"
        + (f"；{note['pptx']['file']}（{kb(note['pptx']['bytes'])}）" if note.get('pptx') else ''),
        f"- 模式/风格/主题：{note['mode']} · {note['style']} · {note['theme']}",
        f"- 篇幅：{note['content_pages']} 内容页（全篇 {note['pages']} 屏）",
        f"- 交付格式：{note['format']}",
        '- 校验：' + ' · '.join(f"{k} {v}" for k, v in note['validation'].items())
        + f" · rubric {note['rubric']}",
        f"- 引用：{note['refs']} 条（参考资料双向对齐）",
    ]
    return '\n'.join(lines)


def delivery_complete(note: dict) -> tuple[bool, str]:
    """七要素齐备性：字段缺失/为空串即不完整（数值 0 是合法值，如无外部引用的 refs=0）。"""
    missing = [k for k in ('file', 'bytes', 'mode', 'style', 'theme', 'pages', 'format', 'refs')
               if note.get(k) in (None, '')]
    return (not missing), ('七要素齐备' if not missing else f'缺 {missing}')


def bands(txt: str) -> list[str]:
    return re.split(r'(?=<section class="band)', txt)[1:]


def heuristic_rubric(html: Path) -> dict:
    """五维启发式评分（0–100）。与 evals/rubric.schema.json 字段对齐，便于 LLM 复评时同构。"""
    txt = html.read_text(encoding='utf-8')
    mode_m = re.search(r'data-mode="([^"]+)"', txt)
    mode = mode_m.group(1) if mode_m else 'presentation'
    content_bands = checks_html.content_bands(txt)  # 与 composite_pages/delivery 同一口径

    checks = []

    def add(cid: str, score: int, ok: bool, notes: str) -> None:
        checks.append({'id': cid, 'score': max(0, min(100, int(score))),
                       'pass': bool(ok), 'notes': notes})

    # ── content ──
    n_sec = len(content_bands)
    n_sowhat = txt.count('class="sowhat')
    n_points = len(re.findall(r'<li\b', txt))
    n_refs = len(set(re.findall(r'id="(ref-\d+)"', txt)))
    n_tbd = len(re.findall(r'class="tbd(?:\s|")', txt))
    c_score = 50
    c_notes = [f'{n_sec} 内容页']
    if n_sec >= 6:
        c_score += 15
    if n_sowhat >= max(1, n_sec // 4):
        c_score += 15
        c_notes.append(f'结论条 {n_sowhat}')
    else:
        c_notes.append(f'结论条偏少({n_sowhat})')
    if n_points >= n_sec * 2:
        c_score += 10
    if n_refs:
        c_score += 10
        c_notes.append(f'引用 {n_refs}')
    else:
        c_notes.append('无外部引用')
    if n_tbd and 'tbd-legend' not in txt and 'flagbar' not in txt:
        c_score -= 10
        c_notes.append('tbd 缺图例')
    add('content', c_score, c_score >= 60, '；'.join(c_notes))

    # ── layout ──
    v = checks_html.chart_variety(LC)
    multi, n_content = checks_html.composite_pages(txt)
    ratio = (multi / n_content) if n_content else 0
    l_score = 50 + int(ratio * 40)
    if 'g-side' in txt or 'g-211' in txt or 'g-hero' in txt:
        l_score += 10
    add('layout', l_score, l_score >= 60,
        f'组合版式 {multi}/{n_content}（{ratio:.0%}）')

    # ── chart ──
    used = checks_html.distinct_chart_types(txt)
    n_chart_pages = len([1 for b in content_bands if re.search(r'data-chart="', b)])
    ch_score = 40
    ch_notes = [f'{len(used)} 型 / {n_chart_pages} 图表页']
    if used:
        floor = checks_html.variety_floor(mode, n_chart_pages, v)
        if len(used) >= floor:
            ch_score += 40
        else:
            ch_score += int(40 * len(used) / max(1, floor))
        ch_notes.append(f'下限 {floor}')
        if n_chart_pages >= 2:
            ch_score += 10
    else:
        ch_notes.append('无图表')
    add('chart', ch_score, ch_score >= 60, '；'.join(ch_notes))

    # ── infographic ──
    info = set(((LC.get('charts') or {}).get('scaffold') or {}).get('infoTypes') or {})
    has_info = bool(set(used) & info)
    has_struct = has_info or ('class="arch' in txt) or ('class="lane' in txt)
    if mode == 'architecture':
        i_score = 80 if has_struct else 30
        i_notes = '架构模式结构主图：' + ('有' if has_struct else '缺')
    else:
        i_score = 70 if has_info else 55
        i_notes = '信息图页型：' + ('有' if has_info else '未用（非必须）')
    add('infographic', i_score, i_score >= 50, i_notes)

    # ── tone ──
    words = (LC.get('aiFlavor') or {}).get('words') or []
    plain = re.sub(r'<[^>]+>', ' ', re.sub(r'<script\b[\s\S]*?</script>', ' ', txt))
    hits = [w for w in words if re.search(w, plain)]
    t_score = 100 if not hits else max(0, 100 - 15 * len(hits))
    # 标题过短/空洞 so-what 轻微扣分
    hollow = ((LC.get('contentQuality') or {}).get('sowhat') or {}).get('forbidden') or []
    if any(h in txt for h in hollow):
        t_score -= 15
    add('tone', t_score, t_score >= 60,
        'AI 腔命中 ' + (', '.join(hits[:3]) if hits else '无'))

    total = round(sum(c['score'] for c in checks) / len(checks))
    overall = all(c['pass'] for c in checks)
    return {
        'overall_pass': overall,
        'score': total,
        'checks': checks,
        '$source': 'heuristic (quality_gate.py) · 可用 LLM 按 rubric.schema.json 复评',
    }


def main() -> int:
    ap = argparse.ArgumentParser(description='TopPPT HTML 交付质量门禁')
    ap.add_argument('html', help='报告 HTML 路径')
    ap.add_argument('--pptx', help='可选：PPTX 路径（跑 validate_pptx --strict）')
    ap.add_argument('--model', help='可选：model.json（PPTX 往返保真）')
    ap.add_argument('--trace', help='可选：过程 trace JSON（并入 evals）')
    ap.add_argument('--require-rubric', type=int, default=60,
                    help='启发式 rubric 总分下限（默认 60；传 0 表示只报告不卡死）')
    ap.add_argument('--deliver', action='store_true',
                    help='生成 SKILL.md「交付说明」七要素（缺一即 gate FAIL）')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()

    html = Path(args.html)
    if not html.exists():
        print(f'错误：HTML 不存在 {html}')
        return 2

    result: dict = {'html': str(html), 'gates': []}

    def gate(name: str, ok: bool, note: str = '', elapsed: float = 0.0) -> None:
        entry = {'name': name, 'ok': bool(ok), 'note': note}
        if elapsed:
            entry['elapsed_s'] = round(elapsed, 2)
        result['gates'].append(entry)
        mark = '✓' if ok else '✗'
        tail = f' · {elapsed:.1f}s' if elapsed else ''
        print(f'  {mark} {name}' + (f' — {note}' if note else '') + tail)

    print(f'交付质量门禁 · {html.name}')
    print('-' * 60)

    # ①–③ 互不依赖子进程并行（HTML strict / PPTX strict / evals）
    head_snip = html.read_text(encoding='utf-8')[:2500]
    mode_m = re.search(r'data-mode="([^"]+)"', head_snip)
    mode = mode_m.group(1) if mode_m else 'presentation'
    jobs: list[tuple[str, list[str], str | None]] = []
    # (name, cmd, fixed_note) — fixed_note 非空则覆盖尾部摘要
    vcmd = [sys.executable, str(ROOT / 'scripts' / 'validate_report.py'), str(html), '--strict']
    if mode == 'presentation':
        vcmd.append('--layout-qa')
    gate_html = 'validate_report --strict' + (' --layout-qa' if mode == 'presentation' else '')
    jobs.append((gate_html, vcmd, None))
    if args.pptx:
        pcmd = [sys.executable, str(ROOT / 'scripts' / 'validate_pptx.py'), args.pptx, '--strict']
        if args.model:
            pcmd += ['--model=' + args.model]
        jobs.append(('validate_pptx --strict', pcmd, None))
    ecmd = [sys.executable, str(ROOT / 'evals' / 'run_evals.py'), '--score', str(html)]
    if args.trace:
        ecmd += ['--trace', args.trace]
    jobs.append(('evals --score', ecmd, '确定性 + 效率检查'))

    results: dict[str, tuple[int, str, float, str | None]] = {}
    with ThreadPoolExecutor(max_workers=max(1, len(jobs))) as pool:
        futs = {pool.submit(run, cmd): (name, note) for name, cmd, note in jobs}
        for fut in as_completed(futs):
            name, note = futs[fut]
            rc, out, el = fut.result()
            results[name] = (rc, out, el, note)

    # 按 jobs 声明顺序输出（稳定可读；墙钟已并行）
    for name, _cmd, _note in jobs:
        rc, out, el, note = results[name]
        if note is not None:
            gate(name, rc == 0, note, el)
        else:
            tail = [ln for ln in out.splitlines() if ln.startswith('PASS ') or ln.startswith('结论')]
            gate(name, rc == 0, tail[-1] if tail else f'exit {rc}', el)

    # ④ rubric 启发式
    rubric = heuristic_rubric(html)
    result['rubric'] = rubric
    print(f'  · rubric 启发式总分 {rubric["score"]} · '
          f'{"通过" if rubric["overall_pass"] else "未通过"}')
    for c in rubric['checks']:
        mark = '✓' if c['pass'] else '✗'
        print(f'    {mark} [{c["id"]}] {c["score"]:>3}  {c["notes"][:70]}')
    if args.require_rubric and args.require_rubric > 0:
        gate(f'rubric ≥ {args.require_rubric}', rubric['score'] >= args.require_rubric,
             f'{rubric["score"]}')
    else:
        print('  · rubric 仅报告（--require-rubric=0）')

    # ⑤ 交付说明（SKILL.md 七要素 · 缺一即 FAIL）
    if args.deliver:
        note = build_delivery(html, Path(args.pptx) if args.pptx else None,
                              result['gates'], rubric)
        complete, why = delivery_complete(note)
        gate('交付说明七要素', complete, why)
        result['delivery'] = note
        print('\n── 交付说明（可直接粘贴）──────────────────────')
        print(render_delivery(note))
        print('──────────────────────────────────────────────')

    ok = all(g['ok'] for g in result['gates'])
    result['pass'] = ok
    print('-' * 60)
    print('结论：' + ('可交付' if ok else '不可交付（修复后重跑）'))

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
