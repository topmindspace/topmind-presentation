#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TopPPT HTML · Evals 运行器（零依赖 · 确定性检查 + 效率度量 + rubric 落地）

用法:
    python evals/run_evals.py --list                  # 列出 prompt 集（显式/隐式/上下文/负对照）
    python evals/run_evals.py --budget                # 打印效率预算
    python evals/run_evals.py --score <报告.html> [--trace <trace.json>] [--json]
    python evals/run_evals.py --score <报告.html> --rubric <rubric.json>   # 并入定性评分

设计依据（OpenAI《Testing Agent Skills Systematically with Evals》）:
    一个 prompt → 一次被捕获的运行（trace + artifacts）→ 一小组检查 → 一个可随时间比较的分数。
    四类目标分别对应：结果（strict 0/0）· 过程（Gate 0 / 轮次）· 风格（rubric）· 效率（轮次 / 工具调用 / 读取字节）。

trace.json 格式（由宿主智能体在跑完一条 prompt 后填写；字段都可选）:
    {
      "turns": 3,                     # 交互轮次
      "toolCalls": 22,                # 工具调用次数（读文件 + 执行脚本）
      "bytesRead": 41000,             # 智能体读取的总字节数
      "readFiles": ["references/playbook.md", ...],
      "gate0ReferenceImage": true,    # 首次交互是否先给出 theme-overview 参考图
      "artifacts": ["2026-09-15-主题.html"]
    }
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
EVALS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
import checks_html  # noqa: E402  承载/多样性/组合版式单源

LC = json.loads((ROOT / 'scripts' / 'layout-constants.json').read_text(encoding='utf-8'))

# ── 效率预算（与 SKILL.md 的"预算（硬）"一致；audit_skill.py 校验声明存在） ──────
BUDGET = {'turns': 3, 'toolCalls': 25, 'bytesRead': 40 * 1024}

# ── 结果/风格检查（确定性部分） ────────────────────────────────────────────────
CHECK_NAMES = {
    'artifact': '产物存在且单文件零外链',
    'strict': 'validate_report --strict 0/0',
    'model': 'REPORT_MODEL 存在、合法 JSON、mode 一致',
    'variety': '图表多样性达下限（charts.variety）',
    'composite': '组合版式比例达下限（research）',
    'structure': '结构图形/信息图页型被使用（含结构类内容时）',
    'gate0': '过程：Gate 0 先给参考图',
    'efficiency': '效率：轮次 / 工具调用 / 读取字节在预算内',
}


def run_validate(html: Path) -> tuple[bool, str]:
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'validate_report.py'), str(html), '--strict'],
                       capture_output=True, text=True, encoding='utf-8')
    out = (r.stdout or '') + (r.stderr or '')
    tail = [ln for ln in out.splitlines() if ln.startswith('PASS ') or ln.startswith('结论')]
    return r.returncode == 0, (tail[-1] if tail else out[-200:])


def score_artifact(html: Path) -> dict:
    checks: list[dict] = []

    def add(cid: str, ok: bool, note: str) -> None:
        checks.append({'id': cid, 'name': CHECK_NAMES[cid], 'ok': ok, 'note': note})

    if not html.exists():
        add('artifact', False, '文件不存在')
        return {'artifact': str(html), 'pass': False, 'checks': checks}

    txt = html.read_text(encoding='utf-8')
    ext = re.findall(r'<(?:link|script|img)[^>]+(?:href|src)=["\']https?://', txt)
    add('artifact', not ext, f'{len(ext)} 处外链' if ext else f'{len(txt.encode("utf-8")) / 1024:.0f}KB 单文件')

    ok, note = run_validate(html)
    add('strict', ok, note)

    m = re.search(r'window\.REPORT_MODEL\s*=\s*(\{[\s\S]*?\})\s*;', txt)
    model = None
    if m:
        try:
            model = json.loads(m.group(1))
        except json.JSONDecodeError as e:
            model = None
            add('model', False, f'JSON 非法: {e}')
    if m and model is not None:
        dm = re.search(r'<html[^>]*data-mode="([^"]+)"', txt)
        consistent = (not model.get('mode')) or (not dm) or model['mode'] == dm.group(1)
        add('model', consistent, f"mode={model.get('mode')} / data-mode={dm.group(1) if dm else '?'}")
    elif not m:
        add('model', False, '未找到 window.REPORT_MODEL')

    mode = (model or {}).get('mode') or 'presentation'
    per_page = checks_html.chart_types_per_page(txt)
    used = checks_html.distinct_chart_types(txt)
    v = checks_html.chart_variety(LC)
    n_chart_pages = len([1 for ts in per_page if ts])
    if used:
        floor = checks_html.variety_floor(mode, n_chart_pages, v)
        add('variety', len(used) >= floor, f'{len(used)} 种 / 下限 {floor}: {used}')
    else:
        add('variety', True, '无图表页（不适用）')

    composite_ratio = checks_html.composite_required(mode, v)
    if composite_ratio > 0:
        multi, n_content = checks_html.composite_pages(txt)
        need = max(1, int(n_content * composite_ratio))
        add('composite', multi >= need, f'{multi}/{n_content} 页（下限 {need}）')

    # 结构图形/信息图：**只在 architecture 模式硬判**（模式 C 契约 = 图为王，必须有结构主图）；
    # 其余模式为**信息项**（ok=None，不计入 pass）——信息图页型族对 research/architecture 是
    # "可用"而非"必须"，纯演示稿/纯数据页没有结构素材，硬判会制造假阴性（属 rubric 的 C3 风格项）。
    struct_types = {'sankey', 'treemap', 'boxplot', 'network', 'marimekko', 'streamgraph',
                    'flow', 'tree', 'sequence', 'loop'}
    has_struct = bool(set(used) & struct_types) or ('class="arch' in txt) or ('class="lane' in txt)
    if mode == 'architecture':
        add('structure', has_struct, '架构模式图为王：'
            + ('已用结构主图' if has_struct else '未用（架构模式必须有分层带/泳道/结构图形）'))
    else:
        add('structure', None, '信息图/结构图形：' + ('有' if has_struct else '未使用') + '（本模式为信息项，不计入通过判定）')

    return {'artifact': str(html), 'mode': mode, 'checks': checks}


def score_trace(trace_path: Path) -> dict:
    t = json.loads(trace_path.read_text(encoding='utf-8'))
    out = []
    for key, limit in (('turns', BUDGET['turns']), ('toolCalls', BUDGET['toolCalls']),
                       ('bytesRead', BUDGET['bytesRead'])):
        v = t.get(key)
        if v is None:
            out.append({'id': key, 'ok': None, 'note': '未记录'})
            continue
        out.append({'id': key, 'ok': v <= limit, 'note': f'{v} / 上限 {limit}'})
    g0 = t.get('gate0ReferenceImage')
    out.append({'id': 'gate0', 'ok': g0 if g0 is not None else None,
                'note': '首次交互给出参考图' if g0 else ('未给出参考图' if g0 is False else '未记录')})
    return {'trace': str(trace_path), 'checks': out}


def main() -> int:
    ap = argparse.ArgumentParser(description='TopPPT HTML Evals 运行器')
    ap.add_argument('--list', action='store_true', help='列出 prompt 集')
    ap.add_argument('--budget', action='store_true', help='打印效率预算')
    ap.add_argument('--score', help='对一份报告产物跑确定性检查')
    ap.add_argument('--trace', help='过程/效率 trace JSON')
    ap.add_argument('--rubric', help='已填好的 rubric JSON（定性评分，见 rubric.schema.json）')
    ap.add_argument('--json', action='store_true', help='机器可读输出')
    args = ap.parse_args()

    if args.list:
        rows = list(csv.DictReader((EVALS / 'prompts.csv').read_text(encoding='utf-8').splitlines()))
        print(f'prompt 集 {len(rows)} 条（显式 / 隐式 / 上下文 / 负对照）\n')
        for r in rows:
            flag = '应触发' if r['should_trigger'] == 'true' else '不应触发'
            print(f"  {r['id']} [{r['kind']:<8}] {flag} · {r['prompt']}")
            print(f"        期望：{r['expect']}")
        n_neg = sum(1 for r in rows if r['should_trigger'] != 'true')
        print(f'\n负对照 {n_neg} 条（捕捉"过于急切地触发技能"的假阳性）')
        return 0

    if args.budget:
        print('效率预算（SKILL.md 的"预算（硬）"与 audit_skill.py 同源）:')
        print(f"  交互轮次 ≤ {BUDGET['turns']} · 工具调用 ≤ {BUDGET['toolCalls']} · "
              f"读取字节 ≤ {BUDGET['bytesRead'] // 1024}KB")
        print('  必读文件 = SKILL.md + references/playbook.md（L1）；L2 深度文件按需读、读完即停')
        return 0

    if not args.score:
        ap.print_help()
        return 2

    result = score_artifact(Path(args.score))
    if args.trace:
        result['process'] = score_trace(Path(args.trace))
    if args.rubric:
        result['rubric'] = json.loads(Path(args.rubric).read_text(encoding='utf-8'))

    def all_ok(checks):
        return all(c['ok'] for c in checks if c.get('ok') is not None)

    result['pass'] = all_ok(result['checks']) and (
        all_ok(result['process']['checks']) if 'process' in result else True)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['pass'] else 1

    print(f"Eval 计分 · {result['artifact']}  (mode={result.get('mode', '?')})")
    print('-' * 60)
    for c in result['checks']:
        mark = '✓' if c['ok'] else ('·' if c['ok'] is None else '✗')
        print(f"  {mark} [{c['id']}] {c['name']}：{c['note']}")
    if 'process' in result:
        print('  ── 过程与效率 ──')
        for c in result['process']['checks']:
            mark = '✓' if c['ok'] else ('·' if c['ok'] is None else '✗')
            print(f"  {mark} [{c['id']}] {c['note']}")
    if 'rubric' in result:
        r = result['rubric']
        print(f"  ── 定性 rubric ── 总分 {r.get('score')} · {'通过' if r.get('overall_pass') else '不通过'}")
        for c in r.get('checks', []):
            print(f"    {c.get('score'):>3} [{c.get('id')}] {c.get('notes', '')[:60]}")
    print('-' * 60)
    print('结论：' + ('通过' if result['pass'] else '未通过（见上方 ✗ 项）'))
    return 0 if result['pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
