#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TopPPT HTML · 素材图片导出探针（维护工具，不进示例矩阵）

为什么单列探针：示例矩阵刻意保持「零图片全原生」基线（`pictures=0`），真实素材图片
（用户提供的位图）不在示例里长期携带。但图片路径必须被回归覆盖，否则「相对路径解析 /
pictures 声明式放行 / half·grid 版式几何 / 裁切策略」这类改动会静默退化。

本探针用 assets/ 下已有的主题总览图当素材，构造一个最小模型：
  · image.layout="half" + fit="contain"（左图右注，完整显示不裁切）
  · image.layout="grid" + fit="cover"（四图网格，裁切填满）
然后跑 build_pptx.js → validate_pptx.py --strict --model，断言 0/0 且 pictures == 声明数。

用法:
    python scripts/probe_image_export.py            # 用内置素材
    python scripts/probe_image_export.py <图片路径>  # 用指定素材（相对模型目录）

环境：需要 Node + pptxgenjs（自动探测 TOP_PPT_NODE_PATH / NODE_PATH / 常见托管目录）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from env_probe import find_node, find_node_modules, node_env  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'dist' / 'probe'
PY = sys.executable


def main() -> int:
    node, node_path = find_node(), find_node_modules()
    if not node or not node_path:
        print('SKIP：未找到 Node / pptxgenjs（本探针为维护工具，可跳过）。')
        return 0

    assets = ROOT / 'assets'
    picks = [Path(a) for a in sys.argv[1:]]
    if not picks:
        picks = [assets / 'theme-overview.png',
                 assets / 'theme-overview-research.png',
                 assets / 'theme-overview-architecture.png']
    missing = [str(p) for p in picks if not p.exists()]
    if missing:
        print(f'错误：素材缺失 {missing}')
        return 2

    OUT.mkdir(parents=True, exist_ok=True)
    model_path = OUT / 'image-probe.model.json'
    pptx_path = OUT / 'image-probe.pptx'
    # 相对路径以「模型目录」为锚（与 build_pptx.js 的 resolveImagePath 同规则）
    rel = [os.path.relpath(p, OUT).replace('\\', '/') for p in picks]
    grid = (rel * 4)[:4]

    model = {
        "mode": "presentation", "style": "business-blue", "theme": "light",
        "title": "素材图片导出探针：双通道落地与门禁",
        "subtitle": "half / grid 版式 · cover / contain 裁切 · 声明式放行",
        "meta": "维护工具 · 不进示例矩阵",
        "agenda": [["01", "图版", "半幅与网格"], ["02", "门禁", "声明式放行"]],
        "sections": [
            {"type": "image", "eyebrow": "01 · 图版",
             "title": "半幅图加右栏注解：左图右注的图文互证版式",
             "lead": "左侧锁定 4:3 素材图，右侧逐条给出读图要点。",
             "image": {"src": rel[0], "layout": "half", "fit": "contain",
                       "caption": "图 1：主题总览（contain 完整显示，不裁切）"},
             "points": [["版式", "左图右注，图宽占版心 56%，右侧逐条注解"],
                        ["裁切", "contain 完整显示不裁切；cover 裁切填满不留白"],
                        ["比例", "half 版式锁定 4:3，与 PPTX 几何同源"],
                        ["占位", "无图时同一几何出原生配图占位，交付前替换 src"]]},
            {"type": "image", "eyebrow": "01 · 图版",
             "title": "四图网格：同一套护栏下的四类业务现场互证",
             "lead": "四张等比例素材并排，图下小图注标明来源场景。",
             "image": {"layout": "grid", "fit": "cover",
                       "caption": "图 2–5：四类业务现场（建议 900×675px · 4:3）",
                       "items": [{"src": grid[0], "caption": "演示模式总览：封面与要点页节奏"},
                                 {"src": grid[1], "caption": "汇报模式：大数字与图表页对照"},
                                 {"src": grid[2], "caption": "研究模式：密排证据与 Exhibit 编号"},
                                 {"src": grid[3], "caption": "架构模式：全幅分层与泳道图"}]}},
            {"type": "image", "eyebrow": "02 · 门禁",
             "title": "配图占位：无素材时锁版式，交付前替换 src",
             "lead": "placeholder 出原生圆角框，pictures 不增。",
             "image": {"placeholder": True, "layout": "full",
                       "caption": "占位：建议 2400×800px · 3:1"},
             "note": "占位不算图片，不触发 PICTURES_* 门禁"},
        ],
        "closing": {"title": "探针结束：图片路径与门禁已被覆盖",
                    "points": [["路径", "相对模型目录解析，跨目录调用不失效"],
                               ["门禁", "pictures 数不得超过声明数"],
                               ["回落", "图片不可读时回落原生占位框，不留空洞"]]},
    }
    model_path.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding='utf-8')
    # 真实位图声明数（half 1 + grid 4）；占位不计入 pictures
    declared = 1 + len(model['sections'][1]['image']['items'])

    # 第二段：用户素材路径缺失 → build 不中断 + strict 报 IMAGE_SRC_MISSING + pictures 不虚增
    miss_model = dict(model)
    miss_model['sections'] = list(model['sections']) + [{
        "type": "image", "eyebrow": "02 · 门禁",
        "title": "相对路径缺失时回落占位，不留空洞",
        "lead": "IMAGE_SRC_MISSING 应回落原生占位框。",
        "image": {"src": "missing-user-photo.jpg", "layout": "half", "fit": "cover",
                  "caption": "用户素材（路径应以模型目录为锚）"},
        "note": "文件缺失回落占位，交付前修正路径",
    }]
    miss_model_path = OUT / 'image-probe-missing.model.json'
    miss_pptx_path = OUT / 'image-probe-missing.pptx'
    miss_model_path.write_text(json.dumps(miss_model, ensure_ascii=False, indent=2), encoding='utf-8')

    env = node_env(node_path)
    r = subprocess.run([node, str(ROOT / 'scripts' / 'build_pptx.js'), str(pptx_path),
                        '--model=' + str(model_path)],
                       capture_output=True, text=True, encoding='utf-8', env=env)
    if r.returncode != 0 or not pptx_path.exists():
        print('[FAIL] build_pptx 失败')
        print((r.stderr or r.stdout or '')[-900:])
        return 1
    print(f'[OK] build_pptx 生成 {pptx_path.name}（声明图片 {declared} 张）')

    r = subprocess.run([PY, str(ROOT / 'scripts' / 'validate_pptx.py'), str(pptx_path),
                        '--strict', '--model=' + str(model_path)],
                       capture_output=True, text=True, encoding='utf-8')
    report = {}
    try:
        report = json.loads(r.stdout or '{}')
    except json.JSONDecodeError:
        print('[FAIL] 无法解析 validate_pptx 报告')
        print((r.stdout or '')[-900:])
        return 1
    pics = int((report.get('summary') or {}).get('pictures', 0))
    errors = report.get('errors') or []
    warnings = report.get('warnings') or []
    print(f'[{"OK" if r.returncode == 0 else "FAIL"}] strict: '
          f'{len(errors)} errors / {len(warnings)} warnings · pictures={pics}/{declared}')
    for e in errors[:6]:
        print('   E', e.get('code'), str(e.get('message'))[:140])
    for w in warnings[:6]:
        print('   W', w.get('code'), str(w.get('message'))[:140])
    if r.returncode != 0:
        return 1
    if pics != declared:
        print(f'[FAIL] pictures={pics} != 声明数 {declared}（声明式放行门禁失效）')
        return 1

    # ── 缺失路径探针：build 成功 + strict 抓 IMAGE_SRC_MISSING + pictures 不虚增 ──
    r = subprocess.run([node, str(ROOT / 'scripts' / 'build_pptx.js'), str(miss_pptx_path),
                        '--model=' + str(miss_model_path)],
                       capture_output=True, text=True, encoding='utf-8', env=env)
    if r.returncode != 0 or not miss_pptx_path.exists():
        print('[FAIL] 缺失路径模型 build_pptx 应成功回落占位，却中断了')
        print((r.stderr or r.stdout or '')[-600:])
        return 1
    print('[OK] 缺失路径 build 成功（已回落占位框，未中断交付）')
    r = subprocess.run([PY, str(ROOT / 'scripts' / 'validate_pptx.py'), str(miss_pptx_path),
                        '--strict', '--model=' + str(miss_model_path)],
                       capture_output=True, text=True, encoding='utf-8')
    try:
        mreport = json.loads(r.stdout or '{}')
    except json.JSONDecodeError:
        print('[FAIL] 缺失路径 validate 报告不可解析')
        return 1
    mcodes = {(e or {}).get('code') for e in (mreport.get('errors') or [])}
    mpics = int((mreport.get('summary') or {}).get('pictures', 0))
    if 'IMAGE_SRC_MISSING' not in mcodes:
        print(f'[FAIL] 缺失路径应报 IMAGE_SRC_MISSING，实际 errors={mcodes}')
        return 1
    if mpics != declared:
        print(f'[FAIL] 缺失路径 pictures={mpics} != 有效声明 {declared}（缺失 src 不应计入图片数）')
        return 1
    print(f'[OK] 缺失路径 strict 抓到 IMAGE_SRC_MISSING · pictures={mpics}/{declared}')
    print('图片导出探针通过：真实素材按声明数落地、占位不增图、缺失路径回落且被门禁拦下。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
