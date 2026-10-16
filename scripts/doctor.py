#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""topmind-presentation · doctor 自检

逐项检查运行环境与技能包完整性，给出 OK / WARN / FAIL 和修复提示。
    python3 scripts/doctor.py           # 环境 + 包完整性（数秒）
    python3 scripts/doctor.py --full    # 另用内置样张实际渲染一次 HTML + PPTX 并跑校验
    npm run doctor / npx topmind-presentation doctor
退出码：有 FAIL 为 1，否则 0（WARN 只是可选能力缺失）。
"""
from __future__ import annotations

import re
import shutil
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
import env_probe  # noqa: E402

RESULTS: list[tuple[str, str, str]] = []


def rec(level: str, item: str, msg: str) -> None:
    RESULTS.append((level, item, msg))
    print(f'  [{level:4}] {item}：{msg}')


def ver(cmd: list[str]) -> str | None:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout.strip() or None
    except Exception:
        return None


def check_env() -> tuple[str | None, str | None]:
    print('运行环境')
    py = sys.version_info
    rec('OK' if py >= (3, 8) else 'FAIL', 'Python', f'{py.major}.{py.minor}.{py.micro}' + ('' if py >= (3, 8) else '（需要 ≥3.8）'))
    node, nm = env_probe.resolve()
    if not node:
        rec('FAIL', 'Node', '未找到。安装 Node ≥18，或设 TOP_PPT_NODE_EXE')
    else:
        v = ver([node, '--version']) or '?'
        major = int(re.sub(r'\D.*', '', v.lstrip('v')) or 0)
        rec('OK' if major >= 18 else 'FAIL', 'Node', f'{v}（{node}）' + ('' if major >= 18 else '，需要 ≥18'))
    if nm:
        rec('OK', 'pptxgenjs', nm)
    else:
        rec('FAIL', 'pptxgenjs', '未找到。在技能目录执行 npm install，或设 TOP_PPT_NODE_PATH')
    rec('OK' if env_probe.has_python_pptx() else 'WARN', 'python-pptx',
        '已安装' if env_probe.has_python_pptx() else '未安装（beautify 路线与第三方 PPTX 复核需要：pip install python-pptx）')
    soffice = shutil.which('soffice') or shutil.which('libreoffice')
    rec('OK' if soffice else 'WARN', 'LibreOffice', soffice or '未安装（PPTX 渲染比对 / 像素回归需要）')
    rec('OK' if shutil.which('pdftoppm') else 'WARN', 'poppler', '已安装' if shutil.which('pdftoppm') else '未安装（PPTX→PNG 需要 pdftoppm）')
    return node, nm


REQUIRED = [
    'SKILL.md', 'package.json', 'assets/pptx-export.js', 'assets/style-gallery.html', 'assets/theme-overview.png',
    'assets/templates/presentation.html', 'assets/templates/research.html', 'assets/templates/architecture.html',
    'assets/templates/engine.css', 'assets/templates/ui.js', 'assets/icons/index.json',
    'scripts/build_pptx.js', 'scripts/render_from_model.py', 'scripts/validate_report.py', 'scripts/validate_pptx.py',
    'scripts/layout-constants.json', 'scripts/model-schema.json',
    'recipes/generate.md', 'recipes/fast.md', 'recipes/beautify.md', 'recipes/template.md', 'recipes/architecture.md',
]


def check_pkg() -> None:
    print('技能包完整性')
    miss = [p for p in REQUIRED if not (ROOT / p).exists()]
    rec('FAIL' if miss else 'OK', '关键文件', ('缺 ' + '、'.join(miss)) if miss else f'{len(REQUIRED)} 个齐全')
    shas = {}
    for t in ('presentation', 'research', 'architecture'):
        p = ROOT / 'assets' / 'templates' / f'{t}.html'
        if p.exists():
            m = re.search(r'__TOPPPT_RUNTIME_SHA__:([0-9a-f]+)', p.read_text(encoding='utf-8'))
            shas[t] = m.group(1) if m else None
    vals = set(shas.values())
    if None in vals or len(vals) != 1:
        rec('FAIL', '运行时戳', f'三份模板引擎副本不一致 {shas}，执行 python3 scripts/sync_runtime.py')
    else:
        rec('OK', '运行时戳', f'三模板一致（{vals.pop()[:10]}）')
    bom = [str(p.relative_to(ROOT)) for p in list((ROOT / 'scripts').glob('*.py')) + list((ROOT / 'scripts').glob('*.js'))
           if p.read_bytes()[:3] == b'\xef\xbb\xbf']
    rec('FAIL' if bom else 'OK', '无 BOM', ('含 BOM：' + '、'.join(bom)) if bom else '脚本均为纯 UTF-8')
    lines = (ROOT / 'SKILL.md').read_text(encoding='utf-8').count('\n') if (ROOT / 'SKILL.md').exists() else 0
    rec('OK' if 0 < lines <= 300 else 'WARN', 'SKILL.md', f'{lines} 行')


def check_full(node: str | None, nm: str | None) -> None:
    print('实际渲染（--full）')
    models = sorted((ROOT / 'assets' / 'examples').glob('*presentation*.model.json'))
    if not models:
        rec('FAIL', '样张', '找不到 assets/examples/*presentation*.model.json')
        return
    m = models[0]
    with tempfile.TemporaryDirectory() as td:
        html, pptx = Path(td) / 'doctor.html', Path(td) / 'doctor.pptx'
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/render_from_model.py'), str(m), '--template', 'presentation', '--out', str(html)],
                           capture_output=True, text=True)
        if r.returncode or not html.exists():
            rec('FAIL', 'HTML 渲染', (r.stderr or r.stdout)[-300:])
            return
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_report.py'), str(html), '--strict'], capture_output=True, text=True)
        summ = [l for l in r.stdout.splitlines() if re.match(r'PASS \d+', l.strip())]
        rec('OK' if r.returncode == 0 else 'FAIL', 'HTML 校验', (summ[-1].strip() if summ else r.stdout.strip()[-200:]))
        if not (node and nm):
            rec('WARN', 'PPTX 渲染', '跳过（缺 Node / pptxgenjs）')
            return
        r = subprocess.run([node, str(ROOT / 'scripts/build_pptx.js'), str(pptx), f'--model={m}'],
                           capture_output=True, text=True, env=env_probe.node_env(nm))
        if r.returncode or not pptx.exists():
            rec('FAIL', 'PPTX 渲染', (r.stderr or r.stdout)[-300:])
            return
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_pptx.py'), str(pptx), '--strict', f'--model={m}'], capture_output=True, text=True)
        rec('OK' if r.returncode == 0 else 'FAIL', 'PPTX 校验', 'strict 0 错误 0 警告' if r.returncode == 0 else r.stdout.strip()[-300:])


def main() -> int:
    print(f'topmind-presentation doctor · {ROOT}')
    node, nm = check_env()
    check_pkg()
    if '--full' in sys.argv:
        check_full(node, nm)
    fails = sum(1 for r in RESULTS if r[0] == 'FAIL')
    warns = sum(1 for r in RESULTS if r[0] == 'WARN')
    print(f'结论：{"可以使用" if not fails else "有问题需修复"}（FAIL {fails} · WARN {warns}）')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
