#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TopPPT HTML · 黄金样张维护

assets/examples/ 至少保留 3 份黄金样张（每模式 1）：
  presentation-business-blue · research-mckinsey · architecture-graphite-dark
另可含产品 showcase（如 2026-09-26-topmind-tms-skills-showcase），不替代黄金样张。

完整 9 风格染色矩阵旧实现：../docs/archive/build_examples.py.full
其余历史示例：../docs/archive/examples/
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / 'assets' / 'examples'

GOLDEN = [
    '2026-09-09-presentation-business-blue',
    '2026-09-09-research-mckinsey',
    '2026-09-09-architecture-graphite-dark',
]


def main() -> int:
    missing = []
    for stem in GOLDEN:
        for suf in ('.html', '.model.json'):
            path = EX / f'{stem}{suf}'
            if not path.exists():
                missing.append(str(path.relative_to(ROOT)))
    if missing:
        print('缺黄金样张:')
        for m in missing:
            print(' ', m)
        print('归档全量重建脚本: ../docs/archive/build_examples.py.full')
        return 1
    print(f'黄金样张齐全：{len(GOLDEN)} 组（html+model）')
    for stem in GOLDEN:
        html = EX / f'{stem}.html'
        model = EX / f'{stem}.model.json'
        try:
            json.loads(model.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            print(f'  FAIL {model.name}: {e}')
            return 1
        print(f'  OK {stem}  html={html.stat().st_size // 1024}KB  model={model.stat().st_size}B')
    print('提示：全矩阵重建请用 ../docs/archive/build_examples.py.full（维护向）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
