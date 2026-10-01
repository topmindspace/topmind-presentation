#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TopPPT HTML · 全链路回归（维护工具，与机器环境无关）

链路：
  ① validate_report.py --strict          每份示例 HTML（三模式预算 + 模型一致性 + 版式断言）
  ② extract_model.py → build_pptx.js → validate_pptx.py --strict --model   B 通道（交付通道）
  ③ gen_channel_a.js（页面预览同引擎产物）→ validate_pptx.py --strict --model --allow-shape-charts
  ④ probe_image_export.py（素材图片探针：示例矩阵零图片，真实素材路径/版式/门禁靠它覆盖）
  ⑤ 双区组合页探针（split 左区 = 图表）：scaffold → extract → B 通道 + A 通道，两通道都过 strict
  ⑥ cross_verify.py（python-pptx 第三方裁判，可选：未安装则 SKIP）——覆盖示例矩阵与 ⑤ 探针
  ⑦ negative_tests.py（故障注入：往合格产物里埋已知缺陷，断言门禁必须报错）
  ⑦-b 任务路由全量遍历（extract_snippet TASK_ROUTES 每条路由可实际抽取，防修复链路静默断裂）
  ⑧ 深色主题探针（research / presentation × dark：示例矩阵只有 architecture 是 dark，
     stylesDark / styleDataColorsDark 路径靠它覆盖）
  ⑨ measure_height.py（浏览器真值：页高与容器裁切，可选：无 playwright 则 SKIP）

用法：
    python scripts/regression.py [--only <示例名关键字>]

环境解析（全部自动探测，不绑定任何机器的固定路径）：
    Node 可执行文件：TOP_PPT_NODE_EXE > PATH 上的 node > 常见托管目录最新版
    pptxgenjs 所在 node_modules：TOP_PPT_NODE_PATH > 仓库内 node_modules > 逐级父目录 > 常见托管目录
    python-pptx：未安装时跳过交叉裁判（打印 SKIP，不计失败）

模板/常量/schema/运行时/示例任何改动后必跑。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from env_probe import (NODE_HINT, NODE_MODULES_HINT, find_node,  # noqa: E402
                       find_node_modules, has_python_pptx, node_env)

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / 'assets' / 'examples'
B_OUT = ROOT / 'dist' / 'regression'
A_OUT = ROOT / 'dist' / 'regression-a'
PY = sys.executable


# ── 执行 ─────────────────────────────────────────────────────────────────────

def run(cmd: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', env=env)


def main() -> int:
    ap = argparse.ArgumentParser(description='TopPPT HTML 全链路回归')
    ap.add_argument('--only', help='只跑名字含该关键字的示例')
    args = ap.parse_args()

    node = find_node()
    node_path = find_node_modules()
    if not node:
        print('错误： ' + NODE_HINT)
        return 2
    if not node_path:
        print('错误： ' + NODE_MODULES_HINT)
        return 2
    env = node_env(node_path)
    print(f'Node: {node}')
    print(f'NODE_PATH: {node_path}')
    print(f'python-pptx 第三方裁判: {"可用" if has_python_pptx() else "未安装（交叉裁判将跳过）"}')

    B_OUT.mkdir(parents=True, exist_ok=True)
    fails: list[str] = []
    skipped: list[str] = []

    examples = sorted(EX.glob('*.html'))
    if args.only:
        examples = [h for h in examples if args.only in h.stem]
    if not examples:
        print('错误： assets/examples/ 下没有可回归的示例。')
        return 2

    for html in examples:
        stem = html.stem
        model = html.with_suffix('.model.json')
        print(f'=== {stem}')
        r0 = run([PY, str(ROOT / 'scripts' / 'validate_report.py'), str(html), '--strict'])
        print('  [validate_report --strict]', 'OK' if r0.returncode == 0 else 'FAIL')
        if r0.returncode != 0:
            fails.append(stem + ':report')
            print((r0.stdout or '')[-800:])
            continue
        r1 = run([PY, str(ROOT / 'scripts' / 'extract_model.py'), str(html)])
        if r1.returncode != 0:
            fails.append(stem + ':extract')
            print((r1.stdout or '')[-500:])
            continue
        bp = B_OUT / (stem + '.pptx')
        r2 = run([node, str(ROOT / 'scripts' / 'build_pptx.js'), str(bp), '--model=' + str(model)], env=env)
        if r2.returncode != 0 or not bp.exists():
            fails.append(stem + ':build')
            print((r2.stderr or r2.stdout or '')[-800:])
            continue
        r3 = run([PY, str(ROOT / 'scripts' / 'validate_pptx.py'), str(bp), '--strict', '--model=' + str(model)])
        print('  [B 通道 strict]', 'OK (0/0)' if r3.returncode == 0 else f'FAIL exit={r3.returncode}')
        if r3.returncode != 0:
            fails.append(stem + ':pptx-b')
            for line in (r3.stdout or '').splitlines()[-14:]:
                print('   ', line)

    print('\n=== A 通道（页面预览序列化引擎产物 · gen_channel_a 组装）')
    rA = run([node, str(ROOT / 'scripts' / 'gen_channel_a.js')], env=env)
    if rA.returncode != 0:
        fails.append('A:generate')
        print((rA.stderr or rA.stdout or '')[-800:])
    else:
        ppx_ok = has_python_pptx()
        for ap in sorted(A_OUT.glob('*.pptx')):
            model = EX / (ap.stem + '.model.json')
            if not model.exists():
                # 非示例产物（如 ⑤ 探针的 probe-split.pptx）由探针段单独校验，跳过避免误判
                continue
            # A 通道（预览引擎）图表为形状近似渲染，豁免 MODEL_CHART_COUNT（交付通道 B 不豁免）
            r = run([PY, str(ROOT / 'scripts' / 'validate_pptx.py'), str(ap), '--strict',
                     '--model=' + str(model), '--allow-shape-charts'])
            ok = r.returncode == 0
            ppx = 'SKIP'
            if ppx_ok:
                p = run([PY, '-c',
                         'import sys;from pptx import Presentation;'
                         'print(len(list(Presentation(sys.argv[1]).slides)))', str(ap)])
                ppx = 'OK' if p.returncode == 0 else 'FAIL'
            print(f'  {ap.name}: strict={"OK" if ok else "FAIL"} python-pptx={ppx}')
            if not ok:
                fails.append(ap.stem + ':pptx-a')
                for line in (r.stdout or '').splitlines()[-10:]:
                    print('   ', line)
            if ppx == 'FAIL':
                fails.append(ap.stem + ':ppx-a')
            if ppx == 'SKIP':
                skipped.append(ap.stem + ':ppx-a')

    # ④ 素材图片导出探针：示例矩阵刻意零图片，真实素材路径/版式/门禁靠探针覆盖
    r5 = run([PY, str(ROOT / 'scripts' / 'probe_image_export.py')], env=env)
    print('  [probe_image_export]', 'OK' if r5.returncode == 0 else 'FAIL')
    if r5.returncode != 0:
        fails.append('probe-image')
        for line in (r5.stdout or '').splitlines()[-8:]:
            print('   ', line)

    # ⑤ 双区组合页探针（split 左区 = 图表）：示例矩阵只覆盖"左文右图"缺省路径，
    #    左区图表/表格/图片三个变体靠脚手架生成一次走完整交付链路（v8 新增能力）；
    #    B 通道 + A 通道（同一模型）都跑，产物同名落两目录 → ⑥ 交叉裁判可逐页比对。
    print('\n=== 双区组合页探针（split 左区 = 图表）')
    probe_plan = B_OUT / 'probe-split.plan.json'
    probe_html = B_OUT / 'probe-split.html'
    probe_model = B_OUT / 'probe-split.model.json'
    probe_pptx = B_OUT / 'probe-split.pptx'
    probe_plan.write_text(json.dumps(
        [{'type': 'points', 'eyebrow': '01 · 前置', 'title': '前置要点页（探针占位）'},
         {'type': 'split', 'left_type': 'chart', 'eyebrow': '02 · 组合版式',
          'title': '双区组合页探针：左图右文（左区图表路径）'}], ensure_ascii=False), encoding='utf-8')
    ok6, why6 = False, ''
    r6 = run([PY, str(ROOT / 'scripts' / 'scaffold_report.py'), '--mode', 'presentation',
              '--plan', str(probe_plan), '--out', str(probe_html)])
    if r6.returncode != 0:
        why6 = 'scaffold'
    else:
        r7 = run([PY, str(ROOT / 'scripts' / 'extract_model.py'), str(probe_html), str(probe_model)])
        if r7.returncode != 0:
            why6 = 'extract'
        else:
            r8 = run([node, str(ROOT / 'scripts' / 'build_pptx.js'), str(probe_pptx),
                      '--model=' + str(probe_model)], env=env)
            if r8.returncode != 0 or not probe_pptx.exists():
                why6 = 'build'
            else:
                r9 = run([PY, str(ROOT / 'scripts' / 'validate_pptx.py'), str(probe_pptx),
                          '--strict', '--model=' + str(probe_model)])
                ok6 = r9.returncode == 0
                if not ok6:
                    why6 = 'validate_pptx_b'
                    for line in (r9.stdout or '').splitlines()[-10:]:
                        print('   ', line)
                else:
                    # A 通道同模型（预览序列化引擎）：产物同名落 dist/regression-a/
                    probe_pptx_a = A_OUT / 'probe-split.pptx'
                    if probe_pptx_a.exists():
                        probe_pptx_a.unlink()
                    r10 = run([node, str(ROOT / 'scripts' / 'gen_channel_a.js'),
                               '--model=' + str(probe_model), '--out=' + str(A_OUT)], env=env)
                    if r10.returncode != 0 or not probe_pptx_a.exists():
                        ok6, why6 = False, 'channel_a'
                        print((r10.stderr or r10.stdout or '')[-400:])
                    else:
                        # 预览引擎图表为形状近似 → 豁免 MODEL_CHART_COUNT（同示例矩阵口径）
                        r11 = run([PY, str(ROOT / 'scripts' / 'validate_pptx.py'), str(probe_pptx_a),
                                   '--strict', '--model=' + str(probe_model),
                                   '--allow-shape-charts'])
                        if r11.returncode != 0:
                            ok6, why6 = False, 'validate_pptx_a'
                            for line in (r11.stdout or '').splitlines()[-10:]:
                                print('   ', line)
    print('  [split 左区图表 B/A 双通道]', 'OK' if ok6 else f'FAIL({why6})')
    if not ok6:
        fails.append('probe-split')

    # ⑥b 深色主题导出探针：示例矩阵只有 architecture/graphite-dark 是 dark，
    #     research / presentation 的 stylesDark + styleDataColorsDark 路径此前零覆盖。
    print('\n=== 深色主题导出探针（research / presentation × dark）')
    dark_fail = []
    for stem in ('2026-09-09-research-mckinsey', '2026-09-09-presentation-business-blue'):
        src_model = EX / f'{stem}.model.json'
        if not src_model.exists():
            continue
        dm = B_OUT / f'{stem}-dark.model.json'
        dp = B_OUT / f'{stem}-dark.pptx'
        data = json.loads(src_model.read_text(encoding='utf-8'))
        data['theme'] = 'dark'
        dm.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        rb = run([node, str(ROOT / 'scripts' / 'build_pptx.js'), str(dp),
                  '--model=' + str(dm)], env=env)
        if rb.returncode != 0 or not dp.exists():
            dark_fail.append(stem + ':build')
            print((rb.stderr or rb.stdout or '')[-300:])
            continue
        rv = run([PY, str(ROOT / 'scripts' / 'validate_pptx.py'), str(dp),
                  '--strict', '--model=' + str(dm)])
        print(f'  {stem} dark:', 'OK' if rv.returncode == 0 else 'FAIL')
        if rv.returncode != 0:
            dark_fail.append(stem + ':validate')
            for line in (rv.stdout or '').splitlines()[-8:]:
                print('   ', line)
    if dark_fail:
        fails.append('dark-theme')

    # ⑥ 双通道交叉裁判（python-pptx）：放在探针之后，A/B 产物齐全时才逐页比对
    r4 = run([PY, str(ROOT / 'scripts' / 'cross_verify.py')] + (['--full-ab'] if '--full-ab' in sys.argv else []))
    if r4.returncode == 2:
        print('  [cross_verify] SKIP（python-pptx 未安装，可选第三方裁判）')
        skipped.append('cross-verify')
    else:
        print('  [cross_verify]', 'OK' if r4.returncode == 0 else 'FAIL')
        if r4.returncode != 0:
            fails.append('cross-verify')
            print((r4.stdout or '')[-600:])

    # ⑦ 门禁反向验证（故障注入）：正向全绿只能证明“没误报”，这里证明“真能报”
    r12 = run([PY, str(ROOT / 'scripts' / 'negative_tests.py')])
    print('  [negative_tests]', 'OK' if r12.returncode == 0 else 'FAIL')
    if r12.returncode != 0:
        fails.append('negative-tests')
        print((r12.stdout or '')[-600:])

    # ⑦-b 任务路由全量遍历：--task 与 validate_report FIX_GUIDE 的修复链路不得静默断裂
    #     （v8.3 前教训：中文节号不被解析，7/11 修复命令执行即报错且无任何审计覆盖；
    #      实现与 audit_docs ⑥ 共用 ES.verify_routes，防两处维护）
    try:
        import extract_snippet as ES  # noqa: PLC0415
        route_bad = ES.verify_routes()
        print('  [task_routes]', 'OK' if not route_bad else f'FAIL {route_bad}')
        if route_bad:
            fails.append('task-routes')
    except ImportError:
        print('  [task_routes] FAIL（extract_snippet 不可导入）')
        fails.append('task-routes')

    # ⑧ 浏览器真值测量（可选）：静态估算看不到「表格被半幅容器横向裁掉一列」这类真实布局缺陷。
    #    当前解释器可能未装 playwright（托管运行时常见）；measure_height.py 会自动回落到
    #    本机已装 playwright 的解释器，因此这里只要能跑 measure_height 就不再跳过。
    mh_fail = []
    for html in examples:
        r13 = run([PY, str(ROOT / 'scripts' / 'measure_height.py'), str(html)])
        out = (r13.stdout or '') + (r13.stderr or '')
        if r13.returncode != 0:
            mh_fail.append(html.stem)
            print(out[-500:])
        elif '跳过：' in out and 'playwright' in out.lower():
            # 解释器与回落链都找不到 playwright → 整批跳过（可选依赖）
            print('  [measure_height] SKIP（playwright 未安装，可选真值裁判）')
            skipped.append('measure-height')
            mh_fail = []
            break
    if 'measure-height' not in skipped:
        print('  [measure_height 页高/容器裁切真值]', 'OK' if not mh_fail else f'FAIL {mh_fail}')
        if mh_fail:
            fails.append('measure-height')

    print('=' * 56)
    if skipped:
        print('跳过（可选依赖缺失）:', sorted(set(skipped)))
    if fails:
        print('回归失败:', fails)
        return 1
    print('全链路回归通过：HTML strict + B 通道精导 strict 0/0 + A 通道（预览同引擎产物）strict 0/0'
          + ' + 双区组合页双通道探针 + 深色主题探针 + 门禁反向验证 + 任务路由全量遍历'
          + ('' if 'measure-height' in skipped else ' + 浏览器页高/裁切真值')
          + (' + python-pptx 双裁判 + 双通道交叉一致' if 'cross-verify' not in skipped else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
