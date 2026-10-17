#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""topmind-presentation · 仓库一致性检查（0.2.5 起，CI 与 Release 共用，只用 Python 标准库）

    python3 scripts/check_repo.py            # 版本 + 引用 + npm 包内容
    python3 scripts/check_repo.py --no-pack  # 跳过 npm pack（本机没有 npm 时）

检查项：
  1. 版本一致：package.json、package-lock.json（根两处）、SKILL.md metadata.version、
     README.md / README.en.md 的「v X.Y.Z」、CHANGELOG 最近一个版本标题
  2. SKILL.md 与 references/*.md 不引用技能根目录之外的相对路径（../），
     Markdown 相对链接指向的文件必须存在
  3. npm pack 内容走 package.json 的 files 白名单：不含 docs/、assets/showcase/、evals/、
     dist/、node_modules/、__pycache__/，解包体积不超过 PACK_LIMIT
  4. docs/ 只放发布规范与迁移说明（DOCS_ALLOWED）：落地页、showcase、截图在 topmindspace.github.io 仓库，
     不再放进本仓库；README / README.en.md / docs/*.md 的相对链接也必须指向存在的文件
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
PACK_LIMIT = 10 * 1024 * 1024
PACK_FORBIDDEN = ('docs/', 'assets/showcase/', 'evals/', 'dist/', 'node_modules/', '__pycache__/')
DOCS_ALLOWED = re.compile(r'^(PUBLISHING|MIGRATION-[\w.\-]+)\.md$')
LINK_RE = re.compile(r'\]\(([^)\s]+)\)')


def versions() -> dict[str, str | None]:
    pkg = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))
    lock = json.loads((ROOT / 'package-lock.json').read_text(encoding='utf-8'))
    sk = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
    fm = re.match(r'^---\n(.*?)\n---', sk, re.S)
    meta = re.search(r'^\s+version:\s*"?([\w.\-]+)"?\s*$', fm.group(1), re.M) if fm else None
    out: dict[str, str | None] = {
        'package.json': pkg.get('version'),
        'package-lock.json version': lock.get('version'),
        'package-lock.json packages[""].version': (lock.get('packages') or {}).get('', {}).get('version'),
        'SKILL.md metadata.version': meta.group(1) if meta else None,
    }
    for name in ('README.md', 'README.en.md'):
        m = re.search(r'\*\*v(\d+\.\d+\.\d+)\*\*', (ROOT / name).read_text(encoding='utf-8'))
        out[name] = m.group(1) if m else None
    m = re.search(r'^##\s+\[?v?(\d+\.\d+\.\d+)', (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8'), re.M)
    out['CHANGELOG.md'] = m.group(1) if m else None
    return out


def check_refs() -> list[str]:
    errs: list[str] = []
    for f in [ROOT / 'SKILL.md', *sorted((ROOT / 'references').glob('*.md'))]:
        rel = f.relative_to(ROOT).as_posix()
        for no, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
            if re.search(r'(?<![\w/])\.\./', line):
                errs.append(f'{rel}:{no}: 引用了技能根目录之外的相对路径（../）')
            for target in LINK_RE.findall(line):
                if re.match(r'^(https?:|mailto:|#)', target):
                    continue
                path = target.split('#', 1)[0]
                if path and not (f.parent / path).exists():
                    errs.append(f'{rel}:{no}: 相对链接不存在：{target}')
    return errs


def check_docs() -> list[str]:
    """docs/ 白名单 + 人读文档（README 中英文、docs/*.md）的相对链接存在性。"""
    errs: list[str] = []
    docs = ROOT / 'docs'
    if docs.is_dir():
        for p in sorted(docs.rglob('*')):
            if p.is_file() and not (p.parent == docs and DOCS_ALLOWED.match(p.name)):
                errs.append(f'docs/ 只放 PUBLISHING.md 与 MIGRATION-*.md（落地页在 topmindspace.github.io 仓库）：'
                            f'{p.relative_to(ROOT).as_posix()}')
    for f in [ROOT / 'README.md', ROOT / 'README.en.md', *sorted(docs.glob('*.md'))]:
        if not f.exists():
            continue
        rel = f.relative_to(ROOT).as_posix()
        text = re.sub(r'```.*?```', '', f.read_text(encoding='utf-8'), flags=re.S)  # 代码块里的路径不是链接
        for target in LINK_RE.findall(text) + re.findall(r'(?:src|href)="([^"]+)"', text):
            if re.match(r'^(https?:|mailto:|#)', target):
                continue
            path = target.split('#', 1)[0]
            if path and not (f.parent / path).exists():
                errs.append(f'{rel}: 相对链接不存在：{target}')
    return errs


def check_pack() -> list[str]:
    npm = shutil.which('npm')
    if not npm:
        return ['找不到 npm（用 --no-pack 跳过）']
    r = subprocess.run([npm, 'pack', '--dry-run', '--json', '--ignore-scripts'], cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode != 0:
        return [f'npm pack 失败：{r.stderr.strip()[:300]}']
    info = json.loads(r.stdout)[0]
    errs = [f'npm 包含不应发布的文件：{f["path"]}' for f in info['files']
            if any(f['path'].startswith(p) or f'/{p}' in f['path'] for p in PACK_FORBIDDEN)]
    if info['unpackedSize'] > PACK_LIMIT:
        errs.append(f'npm 包解包 {info["unpackedSize"] / 1048576:.1f} MB，超过 {PACK_LIMIT / 1048576:.0f} MB')
    if not any(f['path'] == 'assets/icons/index.json' for f in info['files']):
        errs.append('npm 包缺 assets/icons/index.json（运行时需要）')
    print(f'  npm pack：{info["entryCount"]} 个文件，压缩 {info["size"] / 1048576:.1f} MB，'
          f'解包 {info["unpackedSize"] / 1048576:.1f} MB')
    return errs


def main() -> int:
    errs: list[str] = []
    v = versions()
    for k, val in v.items():
        print(f'  {k}: {val}')
    if None in v.values() or len(set(v.values())) != 1:
        errs.append('版本号不一致或缺失')
    errs += check_refs()
    errs += check_docs()
    if '--no-pack' not in sys.argv[1:]:
        errs += check_pack()
    if errs:
        print(f'FAIL: {len(errs)} 处')
        for e in errs:
            print(f'  ✗ {e}')
        return 1
    print('PASS: 版本一致、引用不出技能目录、docs/ 白名单与文档链接、npm 包内容符合白名单')
    return 0


if __name__ == '__main__':
    sys.exit(main())
