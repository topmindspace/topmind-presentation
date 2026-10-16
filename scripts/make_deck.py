#!/usr/bin/env python3
"""一条命令：model.json → HTML + PPTX + 全部交付门禁。

用法：
    python3 scripts/make_deck.py 稿件.model.json [--out 目录] [--no-pptx] [--fidelity] [--keep-going]

步骤（任一步失败即停，并打印「怎么修」）：
    1 渲染 HTML        render_from_model.py（模式模板按 model.mode 自动选）
    2 HTML 质检        validate_report.py --strict
    3 信息密度         check_density.py --strict（复述 / 缺解读 / 小图过多）
    4 生成 PPTX        build_pptx.js --strict
    5 PPTX 质检        validate_pptx.py --strict --model（往返保真 + 字号比例尺 + 越界）
    6 双端保真（可选）  check_fidelity.py --strict（需 playwright + Chrome）
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable or 'python3'

# 常见失败 → 下一步怎么做（按输出关键字匹配，命中即提示）
HINTS = [
    ('FONT_SIZE_OFF_SCALE', '字号不在模式比例尺内：改用 sz() / roleSz()，或把新角色写进 layout-constants.json modeTypeScale'),
    ('DENSITY_ECHO', '解读在复述图上数字：每条 points 写「事实 → 原因 / 影响 / 下一步」，数字只引用不重复'),
    ('DENSITY_NO_INSIGHT', '图表页缺解读：补 points（演示 ≥2、研究 ≥3）与 keyMetrics 2–4 个'),
    ('DENSITY_MINIS_MAX', '小图最多 2 个：其余挪到下一页或改 chart2 双图对照'),
    ('INVALID_SHAPE_BOUNDS', '有形状宽或高为 0：线段请给 0.005in 以上的厚度'),
    ('OVERFLOW', '文字超出容器：精简文案，或把长表拆页（不要靠缩字号硬塞）'),
    ('PICTURES_NOT_DECLARED', '出现未声明的图片：内容图必须写在 section.image 里'),
    ('IMAGE_SRC_EXTERNAL', '图片用了外链：改成相对路径或 data: 内联（零外链）'),
    ('agenda', 'agenda 条目 = 章：3–7 条，sections[].eyebrow 的「NN ·」前缀要能对上'),
    ('playwright', '保真门禁需要 playwright：在技能目录执行 npm ci（含 devDependencies）'),
    ('soffice', '缺 LibreOffice：PPTX 渲染类门禁会跳过；正式交付前请装 libreoffice-impress'),
]


def hint_for(text: str) -> list[str]:
    return [h for k, h in HINTS if k in text]


def run(step: int, name: str, cmd: list[str], env=None) -> tuple[bool, str, float]:
    t0 = time.time()
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    out = (r.stdout or '') + (r.stderr or '')
    dt = time.time() - t0
    ok = r.returncode == 0
    print(f"[{step}] {'✓' if ok else '✗'} {name}  ({dt:.1f}s)")
    if not ok:
        lines = out.strip().splitlines()
        # 只摘失败行（各门禁统一用 [FAIL] / "code": / ERROR 标记），找不到再退回末尾 12 行
        bad = [l for l in lines if '[FAIL]' in l or '"code"' in l or 'ERROR' in l or 'FAIL ' in l[:12] or l.startswith('    - ')]
        show = (bad or lines[-12:])[:15]
        print('    ' + '\n    '.join(x.strip() for x in show))
        for h in hint_for('\n'.join(bad or lines)):
            print(f'    → 怎么修：{h}')
    return ok, out, dt


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith('--')]
    flags = {a.split('=')[0]: (a.split('=', 1)[1] if '=' in a else True) for a in argv if a.startswith('--')}
    if not args or '--help' in flags:
        print(__doc__)
        return 0 if '--help' in flags else 2
    model = Path(args[0]).resolve()
    if not model.exists():
        print(f'找不到模型文件：{model}\n→ 怎么修：先用 scaffold_report.py --plan 生成骨架，或检查路径')
        return 2
    try:
        m = json.loads(model.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        print(f'model.json 不是合法 JSON：第 {e.lineno} 行第 {e.colno} 列 {e.msg}\n→ 怎么修：常见是多了尾逗号或中文引号')
        return 2
    mode = m.get('mode') or 'presentation'
    stem = model.name[:-len('.model.json')] if model.name.endswith('.model.json') else model.stem
    out = Path(flags.get('--out') or model.parent).resolve()
    out.mkdir(parents=True, exist_ok=True)
    html, pptx = out / f'{stem}.html', out / f'{stem}.pptx'
    keep = '--keep-going' in flags
    env = dict(os.environ, NODE_PATH=str(ROOT / 'node_modules') + (os.pathsep + os.environ['NODE_PATH'] if os.environ.get('NODE_PATH') else ''))

    steps = [
        ('渲染 HTML', [PY, 'scripts/render_from_model.py', str(model), '--template', mode, '--out', str(html)]),
        ('HTML 质检', [PY, 'scripts/validate_report.py', str(html), '--strict']),
        ('信息密度', [PY, 'scripts/check_density.py', str(model), '--strict']),
    ]
    if '--no-pptx' not in flags:
        if not shutil.which('node'):
            print('缺 Node.js（≥18）：PPTX 步骤跳过。→ 怎么修：安装 Node 后在技能目录执行 npm ci')
        else:
            steps += [
                ('生成 PPTX', ['node', 'scripts/build_pptx.js', str(pptx), f'--model={model}', '--strict']),
                ('PPTX 质检', [PY, 'scripts/validate_pptx.py', str(pptx), '--strict', f'--model={model}']),
            ]
            if '--fidelity' in flags:
                steps.append(('双端保真', [PY, 'scripts/check_fidelity.py', str(html), str(pptx), '--strict']))
    total, failed = 0.0, []
    if '"placeholder": true' in model.read_text(encoding='utf-8').replace(' ', '').replace('"placeholder":true', '"placeholder": true'):
        print('⚠ 模型里还有配图占位（image.placeholder）：交付前换成真图，或改用可编辑示意图（diagram / steps / network）')
    print(f'make_deck：{model.name} · 模式 {mode} · 输出 {out}')
    for i, (name, cmd) in enumerate(steps, 1):
        ok, _, dt = run(i, name, cmd, env)
        total += dt
        if not ok:
            failed.append(name)
            if not keep:
                break
    print(f"\n{'全部通过' if not failed else '未通过：' + '、'.join(failed)} · 共 {len(steps)} 步 · {total:.1f}s")
    if not failed:
        print(f'  HTML  {html}')
        if pptx.exists() and '--no-pptx' not in flags:
            print(f'  PPTX  {pptx}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
