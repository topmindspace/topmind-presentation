#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TopPPT HTML · 文档一致性审计（规范与引用完整性 · 零依赖）

用法:
    python scripts/audit_docs.py            # 全量审计
    python scripts/audit_docs.py --quiet    # 仅打印结论

审计项（任一不过 → 退出码 1）:
  ① § 引用可解析性 —— references 采用**跨文件唯一稳定编号**（§1–§77），
     所有 `§数字` 引用必须能在三份组件/图表规范中解析到章节
     （白名单：`design-system.md` 自有子节 §1a–§1f / §9b–§9d）
  ② 文件前缀规范性 —— 引用组件/图表规范时须带正确文件名，且不出现
     重复前缀（`` `charts.md` charts.md §N ``）或裸前缀（`charts.md §N` 未加反引号）
  ③ §46 选型表覆盖度 —— 36 个登记图表类型与 29 个页型都必须在选型表出现
  ④ 图表代码节齐备 —— 每个登记图表类型都要在 charts.md / infographics.md 有 `data-chart` 代码节
  ⑤ 篇数与必需文件 —— references 篇数、SKILL.md frontmatter、进包必需文件齐全
  ⑥ 任务路由可解析性 —— extract_snippet.py 的 TASK_ROUTES 每条 (文件, 节) 必须可
     实际抽取（防「文字声明同源」漂移：路由声明的节在文件里找不到即失败；
     空节路由 = 该文件只能整读，≥20KB 的 L2 文件不允许）
   ⑦ 反引号引用可达 —— 反引号代码引用中的 `references/*.md` / `scripts/*`
     路径必须存在（审计 轻微-15 门禁盲区：①–⑥ 只查 [text](path) 形式，
     `references/pan-style.md` 曾漏网；glob/占位符写法跳过）

何时跑：改 `references/*`、拆分/新增规范文件、调整选型表后（与 regression.py 互补——
后者管交付物正确性，本工具管规范自洽性）。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from package_skill import DESC_LIMIT, NAME, REQUIRED  # noqa: E402  （复用进包清单，避免两处维护）
import extract_snippet as ES  # noqa: E402  （⑥ 任务路由审计复用同一解析器，避免第三源）

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / 'references'
QUIET = '--quiet' in sys.argv[1:]

# 组件/图表族物理文件（components.md / charts.md 为逻辑索引；§编号跨文件稳定）
COMPONENT_FILES = (
    'components.md', 'components-atoms.md', 'layouts-research.md',
    'layouts-architecture.md', 'layouts-combo.md',
)
CHART_FILES = (
    'charts.md', 'charts-basic.md', 'charts-extended.md', 'charts-discipline.md',
)
OWNER_SRC = tuple(
    [(fn, r'^## (\d+[a-z]?)\. ') for fn in COMPONENT_FILES + CHART_FILES]
    + [('infographics.md', r'^### (7[1-9]|8\d)\.? '),
       ('infographics-stats.md', r'^### (?:§)?(\d+[a-z]?)\.?\s'),
       ('infographics-structure.md', r'^### (?:§)?(\d+[a-z]?)\.?\s')]
)
# design-system.md 自有子节编号（不算悬空）
DS_OWN = {'1a', '1b', '1c', '1d', '1e', '1f', '9b', '9c', '9d'}
DUP_PRE = re.compile(r'`(components|charts|infographics)\.md`\s*[（(]?\s*`?\1\.md')
BARE_PRE = re.compile(r'(?<![`\w])(components|charts|infographics)\.md\s*§')
REF_ID = re.compile(r'§\s*(\d+[a-zA-Z]?)')  # 节号后缀大小写均收录（§38b / §46C 一并受审计）


def doc_files():
    files = ['SKILL.md', 'README.md']
    files += ['references/%s' % p.name for p in sorted(REF.glob('*.md'))]
    return files


def main() -> int:
    errs: list[str] = []
    lc = json.loads((ROOT / 'scripts' / 'layout-constants.json').read_text(encoding='utf-8'))
    ms = json.loads((ROOT / 'scripts' / 'model-schema.json').read_text(encoding='utf-8'))

    owner: dict[str, str] = {}
    for f, pat in OWNER_SRC:
        p = REF / f
        if not p.exists():
            continue
        for m in re.finditer(pat, p.read_text(encoding='utf-8'), re.M):
            owner[m.group(1)] = f

    # ① § 引用可解析性
    dangling = 0
    for rel in doc_files():
        for i, ln in enumerate((ROOT / rel).read_text(encoding='utf-8').splitlines()):
            for m in REF_ID.finditer(ln):
                i_d = m.group(1)
                if i_d in owner or i_d in DS_OWN:
                    continue
                dangling += 1
                errs.append(f'悬空引用 {rel} L{i+1}: §{i_d}')
    print(f'① § 引用可解析性：悬空 {dangling} 处（编号空间 {len(owner)} 项）')

    # ② 文件前缀规范性
    prefix_bad = 0
    for rel in doc_files():
        for i, ln in enumerate((ROOT / rel).read_text(encoding='utf-8').splitlines()):
            if DUP_PRE.search(ln):
                prefix_bad += 1
                errs.append(f'重复文件前缀 {rel} L{i+1}')
            if BARE_PRE.search(ln):
                prefix_bad += 1
                errs.append(f'裸文件前缀 {rel} L{i+1}')
    print(f'② 文件前缀规范性：异常 {prefix_bad} 处')

    # ③ §46 选型表覆盖度（物理文件 layouts-combo.md；逻辑名 components.md 亦可）
    combo = REF / 'layouts-combo.md'
    if not combo.exists():
        combo = REF / 'components.md'
    comp = combo.read_text(encoding='utf-8')
    sec46 = re.search(r'## 46\. .*?\n(.*?)\n## 46b\.', comp, re.S)
    table = sec46.group(1) if sec46 else ''
    chart_types = lc['charts']['types']
    page_types = [k for k in ms['pageTypes'] if not k.startswith('$')]
    miss_chart = [t for t in chart_types if t not in table]
    miss_page = [t for t in page_types if ('`%s`' % t) not in table]
    if miss_chart:
        errs.append(f'§46 未覆盖图表类型：{miss_chart}')
    if miss_page:
        errs.append(f'§46 未覆盖页型：{miss_page}')
    print(f'③ §46 选型表覆盖：图表 {len(chart_types) - len(miss_chart)}/{len(chart_types)} · '
          f'页型 {len(page_types) - len(miss_page)}/{len(page_types)}')

    # ④ 图表代码节齐备（拆分后的 charts-* + infographics）
    charts_txt = ''
    for fn in CHART_FILES + ('infographics.md', 'infographics-stats.md', 'infographics-structure.md'):
        p = REF / fn
        if p.exists():
            charts_txt += p.read_text(encoding='utf-8')
    no_code = [t for t in chart_types
               if not re.search(r'data-chart="%s"' % re.escape(t), charts_txt)]
    if no_code:
        errs.append(f'缺代码节的图表类型：{no_code}')
    print(f'④ 图表代码节：{len(chart_types) - len(no_code)}/{len(chart_types)} 齐备')

    # ⑤ 篇数与必需文件
    n_ref = len(list(REF.glob('*.md')))
    sk = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
    d = re.search(r'^description:\s*"(.*)"\s*$', sk, re.M)
    dlen = len(d.group(1)) if d else -1
    nm = re.search(r'^name:\s*(\S+)\s*$', sk, re.M)
    missing = [r for r in REQUIRED if not (ROOT / r).exists()]
    if dlen < 0 or dlen > DESC_LIMIT:
        errs.append(f'SKILL.md description 长度异常：{dlen}（上限 {DESC_LIMIT}）')
    if not nm or nm.group(1) != NAME:
        errs.append(f'SKILL.md name 与技能名 {NAME} 不一致')
    if missing:
        errs.append(f'缺必需文件：{missing}')
    print(f'⑤ 规范篇数 {n_ref} · description {dlen} 字符 · 必需文件缺 {len(missing)} 项')

    # ⑥ 任务路由可解析性（--task 与 validate_report FIX_GUIDE 的修复链路依赖它；
    #    实现与 regression ⑦-b 共用 ES.verify_routes，防两处维护）
    route_bad = ES.verify_routes()
    unresolved = [x for x in route_bad if not x.endswith('空路由')]
    empty_routes = [x for x in route_bad if x.endswith('空路由')]
    if unresolved:
        errs.append(f'任务路由不可解析（--task/FIX_GUIDE 修复链路断裂）：{unresolved}')
    if empty_routes:
        errs.append(f'任务路由空节（整读大文件，应补节号或标题关键词）：{empty_routes}')
    print(f'⑥ 任务路由可解析性：{len(ES.TASK_ROUTES)} 条路由 · 不可解析 {len(unresolved)} · 空节 {len(empty_routes)}')

    # ⑦ 反引号引用可达（审计 轻微-15 门禁盲区：`references/pan-style.md` 曾漏网；
    #    glob/占位符写法（* ? < > |）跳过；先按引用文件所在目录解析，再回落技能根）
    bt_path = re.compile(r'(references|scripts)/([\w.\-/]+)')
    bt_suffix = re.compile(r':\d+(?:-\d+)?$')
    backtick_bad = 0
    for rel in doc_files():
        mp = ROOT / rel
        text = mp.read_text(encoding='utf-8')
        for span in set(re.findall(r'`([^`]+)`', text)):
            for kind, p in bt_path.findall(span):
                p = bt_suffix.sub('', p)
                if not p or any(c in p for c in '*?<>|'):
                    continue
                tgt = mp.parent / kind / p
                if not tgt.exists():
                    tgt = ROOT / kind / p
                if not tgt.exists():
                    backtick_bad += 1
                    errs.append(f'反引号引用不可达 {rel}: `{kind}/{p}`')
    print(f'⑦ 反引号引用可达：异常 {backtick_bad} 处')

    print()
    if errs:
        print('审计未通过：')
        for e in errs:
            print(f'  ✗ {e}')
        return 1
    print('文档一致性审计通过：引用可解析 · 前缀规范 · 选型表全覆盖 · 代码节齐备 · 元数据合规')
    return 0


if __name__ == '__main__':
    sys.exit(main())
