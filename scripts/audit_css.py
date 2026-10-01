#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TopPPT HTML · CSS 类覆盖率审计（engine.css ↔ 消费方语料 · 零依赖 · 报告制）

用法:
    python scripts/audit_css.py            # 输出未引用类清单与占比（仅报告，不影响退出码）
    python scripts/audit_css.py --json     # 机器可读

为什么需要它:
    engine.css（≈53KB）是三模板与全部交付报告的样式单源。新增版式/组件后旧类
    可能不再被任何模板、示例或运行时引用——这类「视觉债」此前无任何工具度量。
    本脚本做**报告制**审计（不设门禁）：列出疑似未引用类，供维护者决策
    「删除 / 保留（如为未来预留）/ 标注豁免」。

口径（刻意宽松，宁可漏报不可误报）:
    · 类「已使用」= 类名以子串形式出现在任一消费方文本中（模板/示例/运行时 JS/画廊/
      build_examples 内容包）——JS 动态拼接的类名片段也能命中
    · engine.css 侧只统计**选择器位置的类**（块内属性值如 `.5em` 不算；类名以字母开头）
    · 明确豁免：engine.css 自身注释中提到的类、以 `--` 开头的 CSS 变量名（非类）

何时跑：删除/新增 engine.css 规则、清理模板示例之后（与 audit_styles 互补——
后者管 token 双源一致性，本工具管选择器死活）。
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
ENGINE = ROOT / 'assets' / 'templates' / 'engine.css'

# 消费方语料（模板含 engine.css 注入副本，组装时剔除 __TOPPPT_ENGINE__ 镜像块防自命中）
# references/*.md 计入消费方：其中的代码配方是交付报告类名的合法来源（智能体照文档写报告）
CONSUMERS = (
    list((ROOT / 'assets' / 'templates').glob('*.html'))
    + list((ROOT / 'assets' / 'examples').glob('*.html'))
    + [ROOT / 'assets' / 'pptx-export.js', ROOT / 'assets' / 'style-gallery.html',
       ROOT / 'assets' / 'templates' / 'ui.js']
    + [ROOT / 'scripts' / 'build_examples.py', ROOT / 'scripts' / 'build_pptx.js',
       ROOT / 'scripts' / 'scaffold_report.py']
    + sorted((ROOT / 'references').glob('*.md'))
)

SELECTOR_CLASS = re.compile(r'\.([a-zA-Z][-\w]*)')
# 模板/示例内嵌的 engine.css 注入镜像块——语料必须剔除，否则所有类名自命中、审计恒空
_ENGINE_MIRROR = re.compile(r'/\* __TOPPPT_ENGINE_START__ \*/[\s\S]*?/\* __TOPPPT_ENGINE_END__ \*/')


def strip_engine_mirror(text: str) -> str:
    return _ENGINE_MIRROR.sub('', text)


def strip_blocks(css: str) -> str:
    """去掉 {...} 声明块，只留选择器区（注释一并去掉；块替换为空格防相邻选择器拼接）。"""
    css = re.sub(r'/\*[\s\S]*?\*/', '', css)
    # 循环剥嵌套块（@media 外层块的声明块在首轮被替换后，外层变空壳再剥一次）
    for _ in range(3):
        new = re.sub(r'\{[^{}]*\}', ' ', css)
        if new == css:
            break
        css = new
    return css


def main() -> int:
    if not ENGINE.exists():
        print('错误： 缺 assets/templates/engine.css')
        return 2

    selector_zone = strip_blocks(ENGINE.read_text(encoding='utf-8'))
    classes: list[str] = sorted(set(SELECTOR_CLASS.findall(selector_zone)))

    corpus = '\n'.join(
        strip_engine_mirror(p.read_text(encoding='utf-8'))
        for p in CONSUMERS if p and p.exists())

    unused = [c for c in classes if c not in corpus]
    used = len(classes) - len(unused)

    if '--json' in sys.argv[1:]:
        print(json.dumps({'total': len(classes), 'used': used,
                          'unused': unused,
                          'coverage': round(used / len(classes), 4) if classes else 1.0},
                         ensure_ascii=False, indent=2))
        return 0

    print('CSS 类覆盖率审计 · engine.css（报告制 · 不设门禁）')
    print('-' * 56)
    print(f'  选择器类总数：{len(classes)} · 被消费方引用：{used}'
          f'（覆盖率 {used / max(1, len(classes)):.0%}）')
    if unused:
        print(f'  疑似未引用（{len(unused)} 个，请逐个判断 删除/保留/豁免）：')
        for c in unused:
            print(f'    · .{c}')
        print('  注意：JS 变量拼接类名的极端形态可能漏判，删除前先全局搜一遍。')
    else:
        print('  未发现未引用类。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
