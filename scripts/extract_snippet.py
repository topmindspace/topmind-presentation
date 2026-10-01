#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TopPPT HTML · L2 节级片段抽取器（减少整读 components.md / charts.md 的上下文成本）

用法:
    python scripts/extract_snippet.py --list
    python scripts/extract_snippet.py --chart waterfall
    python scripts/extract_snippet.py --page-type exhibit
    python scripts/extract_snippet.py --file components.md --section 46
    python scripts/extract_snippet.py --task research-evidence
    python scripts/extract_snippet.py --task pptx-export

设计:
    智能体按「任务 → 只读相关节」取代码，而不是整文件读入 70KB+ 规范。
    节边界用标题行识别；--task 走内置路由表（与 playbook.md §十 同源）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / 'references'
LC = json.loads((ROOT / 'scripts' / 'layout-constants.json').read_text(encoding='utf-8'))
# §编号 → 物理文件（components/charts 拆分后逻辑路由；单源 scripts/section-file-map.json）
_SECTION_MAP_PATH = ROOT / 'scripts' / 'section-file-map.json'
try:
    SECTION_FILE_MAP = json.loads(_SECTION_MAP_PATH.read_text(encoding='utf-8'))
except (OSError, json.JSONDecodeError):
    SECTION_FILE_MAP = {}

# 任务 → 建议只读的文件与节（与 references/playbook.md §十 保持一致）
# 节号三种形态均可寻址：阿拉伯（46 / 46b / 8-1）、中文（三 / 一-b）、标题关键词（精导 / 速查）
TASK_ROUTES = {
    'research-evidence': {
        'desc': 'research 证据页 / Exhibit / 密表',
        'reads': [
            ('components.md', ['36d', '46', '46c']),
            ('playbook.md', ['三', '四']),
        ],
    },
    'presentation-combo': {
        'desc': '演示组合版式与卡片',
        'reads': [
            ('components.md', ['39', '40', '41', '42', '46', '46b', '46c']),
            ('playbook.md', ['三', '四']),
        ],
    },
    'architecture-diagram': {
        'desc': '架构/泳道/分层',
        'reads': [
            ('components.md', ['37', '38', '38b']),
            ('infographics.md', ['78', '79', '80']),
            ('playbook.md', ['三', '七']),
        ],
    },
    'chart-pick': {
        'desc': '选图与取图表代码',
        'reads': [
            ('playbook.md', ['五']),
            ('charts.md', ['16']),
        ],
    },
    'content-rules': {
        'desc': '密度/字数/去AI味/细节保全',
        'reads': [
            ('content-rules.md', ['四', '一']),
            ('playbook.md', ['六']),
        ],
    },
    'layout-grammar': {
        'desc': '布局骨架 P1–P12 / 元素排版 / 组合与留白',
        'reads': [
            ('layout-grammar.md', ['〇', '二', '三', '四']),
            ('playbook.md', ['〇']),
        ],
    },
    'model-render': {
        'desc': '模型驱动生成 / 单写路径',
        'reads': [
            ('pptx-export.md', ['内容模型']),
            ('content-rules.md', ['二-b']),
        ],
    },
    'pptx-export': {
        'desc': 'PPTX 精导与页型字段',
        'reads': [
            ('pptx-export.md', ['精导', '内容模型']),
            ('playbook.md', ['九']),
        ],
    },
    'high-fidelity': {
        'desc': '深度高保真/锚点/manifest',
        'reads': [
            ('high-fidelity.md', ['三', '四']),
        ],
    },
    'image-layout': {
        'desc': '素材图片六版式与配图占位',
        'reads': [
            ('components.md', ['11c']),
            ('playbook.md', ['三']),
        ],
    },
    'style-theme': {
        'desc': '配色/亮暗/风格选型',
        'reads': [
            ('styles.md', ['快速选型', '新增']),
            ('design-system.md', ['1a', '1b', '9']),
        ],
    },
    'icons': {
        'desc': '图标语义选型 / 禁区 / 尺寸 / 高频 SVG（完整枚举见归档，不预读）',
        'reads': [
            ('icons.md', ['使用准则', '速查', '高频取码']),
        ],
    },
}

# 节号：阿拉伯（8 / 8b / 8-1）或中文（一 / 一-b / 一-续 / 十），须带 .、． 分隔或后随空白；
# 无节号的二级标题也入节表（num=''，用标题关键词寻址——modes/icons/styles 等中文标题文件）
_SEC_NUM = r'(?:\d+(?:[a-z]|-\d+)?|[一二三四五六七八九十]{1,3}(?:-[a-z0-9续]+)?)'
HEADING_RE = re.compile(
    r'^(#{2,4})[ \t]+(?:§)?(%s)[.、．]?[ \t]*(.*)$' % _SEC_NUM, re.M)
HEADING_UNNUM_RE = re.compile(r'^(##)[ \t]+(.+)$', re.M)
# 任意级别标题行（extract_chart 定位代码节边界用——### 代码节不能再被 ## 回退错层）
_HEADING_ANY = re.compile(r'\n#{2,4}[ \t]')
_CODE_FENCE = re.compile(r'```[\s\S]*?```')

_TEXT_CACHE: dict[str, str] = {}


def _read(path: Path) -> str:
    """带缓存的读取（extract_section/_sections/extract_chart 共用，防同文件重复 IO）。"""
    key = str(path)
    if key not in _TEXT_CACHE:
        _TEXT_CACHE[key] = path.read_text(encoding='utf-8')
    return _TEXT_CACHE[key]


def _fence_spans(text: str) -> list[tuple[int, int]]:
    """代码围栏 ``` 区间（供 extract_chart 优先在代码内定位 data-chart）。"""
    return [(m.start(), m.end()) for m in _CODE_FENCE.finditer(text)]


def _sections(path: Path) -> list[tuple[str, str, int, int]]:
    """返回 [(编号, 标题, start, end), ...]

    编号节（## ~ ####）与无编号二级标题共同构成节边界；
    无编号节 num=''，仅供 extract_section 的标题关键词兜底命中。
    """
    text = _read(path)
    marks: list[tuple[str, str, int]] = []
    num_starts: set[int] = set()
    for m in HEADING_RE.finditer(text):
        marks.append((m.group(2), m.group(3).strip(), m.start()))
        num_starts.add(m.start())
    for m in HEADING_UNNUM_RE.finditer(text):
        if m.start() not in num_starts:  # 已被编号正则命中则跳过
            marks.append(('', m.group(2).strip(), m.start()))
    marks.sort(key=lambda t: t[2])
    out = []
    for i, (num, title, start) in enumerate(marks):
        end = marks[i + 1][2] if i + 1 < len(marks) else len(text)
        out.append((num, title, start, end))
    return out


def resolve_physical(filename: str, section: str | None = None) -> str:
    """逻辑文件名 → 物理文件名（components/charts 拆分后路由）。"""
    if not section:
        return filename
    mapping = SECTION_FILE_MAP.get(filename) or {}
    return mapping.get(str(section), filename)


def extract_section(filename: str, section: str, max_chars: int = 12000) -> str:
    physical = resolve_physical(filename, section)
    path = REF / physical
    if not path.exists():
        path = REF / filename
    if not path.exists():
        return f'错误：{path} 不存在'
    secs = _sections(path)
    # ① 精确节号优先；② 无精确命中才允许前缀（并提示，防敲错节号静默取错码）；③ 标题关键词兜底
    hits = [s for s in secs if s[0] == section]
    note = ''
    if not hits:
        prefix = [s for s in secs if s[0].startswith(section)]
        if prefix:
            hits = prefix[:1]
            note = (f'\n/* 提示：§{section} 无精确节号，已按前缀命中 §{hits[0][0]} '
                    f'（{hits[0][1][:24]}）；若非本意请用精确节号 */')
    if not hits:
        hits = [s for s in secs if section in s[1]]
    if not hits:
        seen: list[str] = []
        for s in secs:
            label = s[0] or (s[1][:10] + '…' if len(s[1]) > 10 else s[1])
            if label not in seen:
                seen.append(label)
        sample = '、'.join(seen[:12])
        return f'错误：{filename} 未找到 §{section}。可用节号/标题样例: {sample}'
    num, title, start, end = hits[0]
    body = _read(path)[start:end].rstrip()
    if len(body) > max_chars:
        body = body[:max_chars] + f'\n…（截断，全文见 references/{physical}）'
    return f'/* references/{physical} §{num} {title} */\n\n{body}{note}'


def verify_routes() -> list[str]:
    """遍历 TASK_ROUTES，返回不可解析/空路由问题清单（audit_docs ⑥ 与 regression ⑦-b 共用同一实现）。"""
    bad: list[str] = []
    for task, r in TASK_ROUTES.items():
        for fn, secs in r['reads']:
            if not secs:
                bad.append(f'{task}:{fn} 空路由')
                continue
            for sec in secs:
                if extract_section(fn, sec, max_chars=200).startswith('错误'):
                    bad.append(f'{task}:{fn} §{sec}')
    return bad


def extract_chart(chart_type: str, max_chars: int = 14000) -> str:
    chart_type = (chart_type or '').strip().lower()
    reg = ((LC.get('charts') or {}).get('registry') or {}).get(chart_type)
    if not reg:
        known = sorted((LC.get('charts') or {}).get('registry') or {})
        return f'错误：未登记图表 {chart_type!r}。可用: {", ".join(known)}'
    info_types = set(((LC.get('charts') or {}).get('scaffold') or {}).get('infoTypes') or {})
    key = f'data-chart="{chart_type}"'
    candidates = (
        [REF / 'infographics-stats.md', REF / 'infographics-structure.md', REF / 'infographics.md']
        if chart_type in info_types
        else [REF / 'charts-basic.md', REF / 'charts-extended.md',
              REF / 'charts-discipline.md', REF / 'charts.md']
    )
    path = next((p for p in candidates if p.exists() and key in _read(p)), None)
    if path is None:
        names = ', '.join(p.name for p in candidates if p.exists())
        return f'错误：未找到 {key}（检索: {names}）'
    text = _read(path)
    # 优先取**代码围栏内**的 data-chart 出现位置——概述散文里的首个出现不是代码节
    fences = _fence_spans(text)
    idx = -1
    pos = text.find(key)
    while pos >= 0:
        if any(a <= pos < b for a, b in fences):
            idx = pos
            break
        pos = text.find(key, pos + 1)
    if idx < 0:
        idx = text.find(key)  # 无围栏命中时退回首现
    # 回退到该代码块前最近的标题（任意级别——### 代码节不能被 ## 回退错层）
    prev_head = None
    for m in _HEADING_ANY.finditer(text, 0, idx + 1):
        prev_head = m
    head = prev_head.start() if prev_head else max(0, idx - 200)
    # 前进到下一个任意级别标题或文件尾
    nxt = _HEADING_ANY.search(text, idx)
    end = nxt.start() if nxt else len(text)
    body = text[head:end].rstrip()
    if len(body) > max_chars:
        body = body[:max_chars] + f'\n…（截断，全文见 {path.name}）'
    meta = (f'/* chart={chart_type} · pptx={reg.get("pptx")} · '
            f'dataTable={reg.get("dataTable")} · 来源 references/{path.name} */')
    return f'{meta}\n\n{body}'


def extract_page_type(page_type: str, max_chars: int = 10000) -> str:
    ms = json.loads((ROOT / 'scripts' / 'model-schema.json').read_text(encoding='utf-8'))
    pages = ms.get('pages') or ms.get('pageTypes') or ms
    # schema 结构：可能是 {pages: {type: {...}}} 或顶层
    entry = None
    if isinstance(pages, dict) and page_type in pages:
        entry = pages[page_type]
    elif isinstance(ms.get('sections'), dict) and page_type in ms['sections']:
        entry = ms['sections'][page_type]
    # 兜底：递归找 type
    if entry is None:
        def find(obj):
            if isinstance(obj, dict):
                if obj.get('type') == page_type or page_type in obj and isinstance(obj[page_type], dict):
                    return obj.get(page_type, obj)
                for v in obj.values():
                    r = find(v)
                    if r is not None:
                        return r
            return None
        entry = find(ms)
    if entry is None:
        return f'错误：model-schema.json 未找到页型 {page_type!r}'
    # 选型表提示
    hint = extract_section('components.md', '46', max_chars=4000)
    schema_txt = json.dumps({page_type: entry}, ensure_ascii=False, indent=2)
    return (f'/* pageType={page_type} · schema 字段（scripts/model-schema.json） */\n'
            f'{schema_txt}\n\n'
            f'/* 选型表摘要（components.md §46，完整表见原文） */\n'
            f'{hint}')


def main() -> int:
    ap = argparse.ArgumentParser(description='L2 节级片段抽取')
    ap.add_argument('--list', action='store_true', help='列出任务路由与已登记图表')
    ap.add_argument('--task', help='任务路由名（research-evidence / chart-pick / …）')
    ap.add_argument('--chart', help='图表类型，从 charts.md / infographics.md 抽代码节')
    ap.add_argument('--page-type', dest='page_type', help='页型名，输出 schema 字段 + 选型提示')
    ap.add_argument('--file', help='references 下文件名，如 components.md')
    ap.add_argument('--section', help='节编号，如 46 / 11c / 36d')
    ap.add_argument('--max-chars', type=int, default=12000)
    args = ap.parse_args()

    if args.list:
        print('任务路由：')
        for name, r in TASK_ROUTES.items():
            print(f'  {name:22} {r["desc"]}')
            for fn, secs in r['reads']:
                sec = ('§' + ' §'.join(secs)) if secs else '（全文按需）'
                print(f'      · references/{fn} {sec}')
        print('\n已登记图表：')
        reg = (LC.get('charts') or {}).get('registry') or {}
        for t, meta in sorted(reg.items()):
            if t.startswith('$') or not isinstance(meta, dict):
                continue
            print(f'  {t:14} pptx={meta.get("pptx")} dataTable={meta.get("dataTable")}')
        print('\n用法示例：')
        print('  python scripts/extract_snippet.py --task research-evidence')
        print('  python scripts/extract_snippet.py --chart waterfall')
        print('  python scripts/extract_snippet.py --page-type exhibit')
        print('  python scripts/extract_snippet.py --file components.md --section 46c')
        return 0

    if args.task:
        r = TASK_ROUTES.get(args.task)
        if not r:
            print(f'错误：未知任务 {args.task!r}。用 --list 查看。')
            return 2
        print(f'# 任务：{args.task} — {r["desc"]}\n')
        print('## 建议只读（读完即停，不预读下一份）\n')
        for fn, secs in r['reads']:
            sec = ('§' + '、'.join(secs)) if secs else '全文按需'
            print(f'- references/{fn} — {sec}')
        print('\n## 片段\n')
        for fn, secs in r['reads']:
            for sec in secs[:2]:  # 每文件最多抽 2 节，防上下文爆
                print(extract_section(fn, sec, args.max_chars))
                print('\n---\n')
        return 0

    if args.chart:
        print(extract_chart(args.chart, args.max_chars))
        return 0
    if args.page_type:
        print(extract_page_type(args.page_type, args.max_chars))
        return 0
    if args.file and args.section:
        print(extract_section(args.file, args.section, args.max_chars))
        return 0

    ap.print_help()
    return 2


if __name__ == '__main__':
    sys.exit(main())
