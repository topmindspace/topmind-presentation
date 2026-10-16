#!/usr/bin/env python3
"""最低信息密度门禁（按 model.json 逐页检查；演示 / 研究 / 架构三档）。

用法：
  python3 scripts/check_density.py MODEL.json [MODEL2.json ...] [--strict] [--report]
--report 打印逐页构成表；--strict 下任一 FAIL 退出码 1。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_density as LD  # noqa: E402


def main(argv):
    files = [a for a in argv if not a.startswith('--')]
    strict, report = '--strict' in argv, '--report' in argv
    nfail = nwarn = 0
    for f in files:
        m = json.loads(Path(f).read_text(encoding='utf-8'))
        mode = m.get('mode') or 'presentation'
        print(f'== {Path(f).name} · {mode}')
        for i, sec in enumerate(m.get('sections') or []):
            a = LD.analyze_section(sec)
            low = LD.classify(a)
            if report:
                print(f'  p{i + 1:02d} {a["type"]:<11} 种类={len(a["kinds"])}{a["kinds"]} 文字={a["body_chars"]} '
                      f'数据点={a["data_points"]} 解读={a["readout_n"]}' + (f'  ⚠ {low}' if low else ''))
            for lv, rule, msg in LD.check_section(sec, mode):
                print(f'  [{lv}] p{i + 1:02d} {rule} {msg}')
                nfail += lv == 'FAIL'
                nwarn += lv == 'WARN'
    print(f'[density] FAIL {nfail} · WARN {nwarn}')
    return 1 if (strict and nfail) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
