#!/usr/bin/env python3
"""自动选版：在「内容允许的候选版式」里，按风格偏好 + 节奏规则挑一个。

单源：layout-constants.json → layoutLibrary（版式 / 重量 / 节奏）与 styleGrammar（preferLayouts / preferFamilies）。
被 beautify.py（美化路由映射）与 recommend_layout.py（--style）共用。

评分（越高越好）：
  +3  版式在该风格 preferLayouts 里（越靠前越高，最多 +3）
  +1  版式家族在该风格 preferFamilies 里
  -4  与上一页同版式（forbidAdjacentSameLayout）
  -3  会让同重量连排超过上限（maxSameWeightRun）
  候选自身的先后顺序作为最后的平局裁决（内容最贴切者在前）。
"""
from __future__ import annotations

import json
from pathlib import Path

LC = json.loads((Path(__file__).resolve().parent / 'layout-constants.json').read_text(encoding='utf-8'))
LIB = LC['layoutLibrary']
BY_ID = {l['id']: l for l in LIB['layouts']}
GRAMMAR = (LC.get('styleGrammar') or {}).get('styles') or {}
RHYTHM = LIB.get('rhythm') or {}


def style_prefs(style: str) -> tuple[list, list]:
    g = GRAMMAR.get(style) or GRAMMAR.get('business-blue') or {}
    return list(g.get('preferLayouts') or []), list(g.get('preferFamilies') or [])


def score(lid: str, style: str, history: list, mode: str = 'presentation') -> float:
    pl, pf = style_prefs(style)
    lay = BY_ID.get(lid) or {}
    sc = 0.0
    if lid in pl:
        sc += 3 - min(2, pl.index(lid)) * 0.5
    if lay.get('family') in pf:
        sc += 1
    if history:
        if RHYTHM.get('forbidAdjacentSameLayout', True) and history[-1] == lid:
            sc -= 4
        cap = (RHYTHM.get('maxSameWeightRun') or {}).get(mode, 2)
        w = lay.get('weight')
        run = 0
        for h in reversed(history):
            if (BY_ID.get(h) or {}).get('weight') == w:
                run += 1
            else:
                break
        if run >= cap:
            sc -= 3
    return sc


def pick(candidates: list, style: str, history: list, mode: str = 'presentation') -> str:
    """candidates: 版式 id 列表（按内容贴切度排序）；返回得分最高者（平局取靠前）。"""
    best, best_sc = candidates[0], None
    for i, c in enumerate(candidates):
        sc = score(c, style, history, mode) - i * 0.01
        if best_sc is None or sc > best_sc:
            best, best_sc = c, sc
    return best
