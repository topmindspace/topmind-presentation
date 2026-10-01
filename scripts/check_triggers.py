#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TopPPT HTML · description trigger coverage (keyword/heuristic, no LLM).

Gates regressions when SKILL.md description drifts away from eval queries.
See evals/trigger-queries.json → how_to_extend.

Usage:
    python3 scripts/check_triggers.py
    python3 scripts/check_triggers.py --json
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

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / 'SKILL.md'
QUERIES = ROOT / 'evals' / 'trigger-queries.json'

# Tokens that, if present in a query AND in description (or Do-NOT zone for negatives),
# count toward a hit. Multi-char CJK / ASCII keywords preferred over single chars.
POS_KEYWORDS = [
    '报告', '演示', '汇报', '路演', '调研', '白皮书', '评测', '对标', '经营分析', '复盘',
    'PPT', 'PPTX', 'pptx', 'slides', 'deck', 'HTML', '网页报告',
    '架构图', '拓扑', '流程图', '泳道', '方案图',
    '排版', '版式', '配色', '图文',
    '快速模式', 'fast', '一键出稿', '直接生成', '少问一句',
    '可视化', '高保真', '可编辑',
    '咨询报告', '分析报告', '研究报告', '项目汇报', '商务',
]

# Negative-zone cues in description (Do NOT …) — if a miss-query matches these
# boundary phrases more than positive product cues, treat as correctly excluded.
NEG_BOUNDARY = [
    '纯代码', '代码工程', '非报告类', '视频', '图片生成',
    'Word', '源文件', '应用开发', 'coding', 'Do NOT',
]

# Extra strong negative query cues (if query has these AND lacks report cues → expect miss)
NEG_QUERY_CUES = [
    'react', '组件', '单测', 'debug', 'python 报错', '视频', 'mp4', 'midjourney',
    '海报图', '已有的 pptx', '已有 pptx', 'word 文档', '电商官网', 'sql',
    'nginx', 'refactor', 'typescript', '剪辑', '录像', '字幕', '迁移脚本',
]


def load_description() -> str:
    txt = SKILL.read_text(encoding='utf-8')
    m = re.search(r'^description:\s*"(.*)"\s*$', txt, re.M)
    if not m:
        raise SystemExit('SKILL.md missing description frontmatter')
    return m.group(1)


def tokenize_hits(query: str, desc: str) -> list[str]:
    q_low = query.lower()
    d_low = desc.lower()
    hits = []
    for kw in POS_KEYWORDS:
        if kw.lower() in q_low and kw.lower() in d_low:
            hits.append(kw)
    return hits


def looks_negative_query(query: str) -> bool:
    q = query.lower()
    return any(c in q for c in NEG_QUERY_CUES)


def boundary_covered(desc: str) -> bool:
    return sum(1 for b in NEG_BOUNDARY if b.lower() in desc.lower()) >= 2


def evaluate(desc: str, data: dict) -> tuple[list[dict], int, int]:
    rows = []
    fails = 0
    for bucket, default_expect in (('positive', 'hit'), ('negative', 'miss')):
        for item in data.get(bucket, []):
            q = item['query']
            expect = item.get('expect', default_expect)
            hits = tokenize_hits(q, desc)
            if expect == 'hit':
                ok = len(hits) >= 1
                detail = f'keywords={hits}' if ok else 'no shared trigger keyword with description'
            else:
                # miss: either no positive keyword overlap, OR query is clearly
                # out-of-scope and description has Do-NOT boundaries.
                ok = (len(hits) == 0) or (
                    looks_negative_query(q) and boundary_covered(desc) and len(hits) <= 1
                )
                # Stricter: if query is a known out-of-scope cue, require miss even
                # when a weak overlapping token exists (e.g. "pptx" in "改已有 pptx").
                if looks_negative_query(q) and boundary_covered(desc):
                    ok = True
                detail = (
                    f'miss-ok boundary; weak_hits={hits}' if ok
                    else f'unexpected trigger overlap={hits}'
                )
            rows.append({
                'id': item.get('id'),
                'expect': expect,
                'ok': ok,
                'query': q,
                'detail': detail,
            })
            if not ok:
                fails += 1
    return rows, fails, len(rows)


def main() -> int:
    as_json = '--json' in sys.argv
    if not QUERIES.exists():
        print(f'MISSING {QUERIES}')
        return 1
    try:
        data = json.loads(QUERIES.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f'错误：无法解析 {QUERIES}: {e}')
        return 2
    try:
        desc = load_description()
    except (OSError, SystemExit) as e:
        print(f'错误：{e}')
        return 2
    rows, fails, total = evaluate(desc, data)
    n_pos = sum(1 for r in rows if r['expect'] == 'hit')
    n_neg = sum(1 for r in rows if r['expect'] == 'miss')
    if as_json:
        print(json.dumps({
            'total': total, 'fails': fails,
            'positive': n_pos, 'negative': n_neg,
            'description_chars': len(desc),
            'rows': rows,
        }, ensure_ascii=False, indent=2))
    else:
        print(f'trigger coverage · {total - fails}/{total}  '
              f'(+{n_pos} / −{n_neg}) · description {len(desc)} chars')
        for r in rows:
            mark = 'OK' if r['ok'] else 'FAIL'
            print(f'  [{mark}] {r["id"]} expect={r["expect"]}  {r["detail"]}')
            if not r['ok']:
                print(f'         Q: {r["query"]}')
        if fails:
            print(f'\nFAILED {fails} query(ies). Extend keywords in SKILL description '
                  f'or adjust evals/trigger-queries.json (see how_to_extend).')
        else:
            print('\nAll trigger heuristics passed.')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
