#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TopPPT HTML · 内置图标包生成器（单源）

产出 assets/icons/：
  - <name>.svg   24×24 手绘线性图标（stroke=currentColor, 1.8, 圆角），HTML 内联用
  - <name>.png   512px 预渲染（cairosvg），PPTX 通道用（python-pptx 不认 SVG，见报告）
  - index.json   关键词→图标映射 + 默认图标表

用法:
  python scripts/make_icon_pack.py            # 写 SVG + index.json
  python scripts/make_icon_pack.py --png      # 另渲染 512px PNG（需 cairosvg）

图标全部手绘原创（24 网格），不复制第三方图标库。
其中 19 个沿用既有 icon_lib.js 的成熟路径（字节一致，现有渲染不变）；
流程 采用 references/icons.md 文档版（git-branch 式，与文档对齐）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'assets' / 'icons'

SVG_OPEN = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
            'stroke-linejoin="round">')

# name -> (inner_svg, label, keywords)
ICONS: dict[str, tuple[str, str, list[str]]] = {
    # ── 既有 19（与 icon_lib.js 现行字节一致） ──
    '增长': ('<path d="M22 7l-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>',
             '增长/上升', ['增长', '上升', '提升', '增加', 'up']),
    '下降': ('<path d="M22 17l-8.5-8.5-5 5L2 7"/><path d="M16 17h6v-6"/>',
             '下降/回落', ['下降', '回落', '减少', '降低', 'down']),
    '数据': ('<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3"/>',
             '数据库/底座', ['数据', '底座', 'database']),
    '图表': ('<path d="M3 3v18h18"/><rect x="7" y="12" width="3" height="6" rx="1"/><rect x="12" y="8" width="3" height="10" rx="1"/><rect x="17" y="4" width="3" height="14" rx="1"/>',
             '柱状图', ['图表', '柱状', 'bar']),
    '趋势': ('<path d="M3 3v18h18"/><path d="M7 14l4-4 3 3 5-6"/><path d="M15 7h4v4"/>',
             '趋势/折线', ['趋势', '折线', 'line']),
    '占比': ('<path d="M21.2 15.9A10 10 0 1 1 8 2.8"/><path d="M22 12A10 10 0 0 0 12 2v10z"/>',
             '环形/占比', ['占比', '环形', '份额', 'donut']),
    '表格': ('<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/>',
             '表格/网格', ['表格', '矩阵', 'table']),
    '效率': ('<path d="M12 15l3.5-5.5"/><path d="M20.2 15a8.5 8.5 0 1 0-16.4 0"/>',
             '仪表盘/效率', ['效率', '仪表盘', '性能', 'gauge']),
    '成果': ('<circle cx="12" cy="8" r="6"/><path d="M15.5 13 17 22l-5-3-5 3 1.5-9"/>',
             '奖章/成果', ['成果', '奖章', '奖项', 'medal']),
    '安全': ('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/>',
             '盾牌/安全', ['安全', '盾牌', 'shield']),
    '权限': ('<rect x="3" y="11" width="18" height="10" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
             '锁/权限', ['权限', '锁', 'lock']),
    '检查': ('<circle cx="12" cy="12" r="10"/><path d="M8 12.5l2.5 2.5L16 9.5"/>',
             '检查/对勾', ['检查', '对勾', '校验', 'check']),
    '风险': ('<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
             '警告/风险', ['风险', '警告', 'warning']),
    '团队': ('<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
             '用户/团队', ['团队', '人力', 'team']),
    '计划': ('<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
             '日历/计划', ['计划', '日历', '日程', 'calendar']),
    '智能': ('<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M9 9h6v6H9zM9 1v3M15 1v3M9 20v3M15 20v3M1 9h3M1 15h3M20 9h3M20 15h3"/>',
             '芯片/AI', ['智能', '芯片', 'AI', 'chip']),
    '洞察': ('<circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>',
             '搜索/洞察', ['洞察', '搜索', '分析', 'search']),
    '工具': ('<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
             '扳手/工具', ['工具', '扳手', 'tool']),
    '清单': ('<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
             '清单/条目', ['清单', '条目', 'checklist']),
    # ── 流程：采用 references/icons.md 文档版（git-branch 式） ──
    '流程': ('<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="8" r="3"/><path d="M6 9v6M18 11a9 9 0 0 1-9 4"/>',
             '分支/流程', ['流程', '分支', 'pipeline']),
    # ── 新增 28（手绘原创） ──
    '箭头': ('<path d="M4 12h15"/><path d="M13 6l6 6-6 6"/>',
             '右箭头', ['箭头', '指向', 'arrow']),
    '下载': ('<path d="M12 4v11"/><path d="M7 10.5l5 5 5-5"/><path d="M4 16v4h16v-4"/>',
             '下载', ['下载', 'download']),
    '上传': ('<path d="M12 20V9"/><path d="M7 13.5l5-5 5 5"/><path d="M4 16v4h16v-4"/>',
             '上传', ['上传', 'upload']),
    '分享': ('<circle cx="6" cy="12" r="2.5"/><circle cx="17.5" cy="5.5" r="2.5"/><circle cx="17.5" cy="18.5" r="2.5"/><path d="M8.3 10.9l6.9-4.2M8.3 13.1l6.9 4.2"/>',
             '分享', ['分享', 'share']),
    '循环': ('<path d="M20.5 15a8.5 8.5 0 1 1-2-8.9L21 8.5"/><path d="M21 3.5v5h-5"/>',
             '循环/刷新', ['循环', '刷新', '迭代', '飞轮', 'refresh']),
    '目标': ('<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><path d="M12 12h.01"/>',
             '同心圆靶心', ['目标', 'target']),
    '闪电': ('<path d="M13 2 3 14h7l-1 8 10-12h-7l1-8z"/>',
             '闪电/高效', ['闪电', '高效', '快速', '快捷']),
    '勾选': ('<path d="M4 12.5l5 5L20 6.5"/>',
             '对勾', ['勾选', '完成', 'done']),
    '用户': ('<circle cx="12" cy="8" r="4"/><path d="M4 21c0-3.5 3.6-5.5 8-5.5s8 2 8 5.5"/>',
             '单人/用户', ['用户', '客户', 'user']),
    '组织': ('<rect x="9" y="2" width="6" height="6" rx="1"/><rect x="2" y="16" width="6" height="6" rx="1"/><rect x="16" y="16" width="6" height="6" rx="1"/><path d="M12 8v4M5 12h14M5 12v4M19 12v4"/>',
             '组织架构/层级', ['组织', '层级', '架构', 'org']),
    '灯泡': ('<path d="M12 3a6 6 0 0 0-3.4 11c.7.5 1.4 1.3 1.4 2.5h4c0-1.2.7-2 1.4-2.5A6 6 0 0 0 12 3z"/><path d="M10 19.5h4"/><path d="M10.8 22h2.4"/>',
             '灯泡/创意', ['灯泡', '创意', '想法', 'idea']),
    '文档': ('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z"/><path d="M14 2v6h6"/><path d="M9 13h6M9 17h6"/>',
             '文档/报告', ['文档', '报告', '文件', 'doc']),
    '云': ('<path d="M7 18.5a4 4 0 0 1-.4-7.98A5.5 5.5 0 0 1 17.3 11 3.9 3.9 0 0 1 17 18.5H7z"/>',
           '云/平台', ['云', '平台', 'cloud']),
    '邮件': ('<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M2.5 7.5 12 13l9.5-5.5"/>',
             '信封/邮件', ['邮件', '邮箱', 'mail']),
    '手机': ('<rect x="7" y="2" width="10" height="20" rx="2.5"/><path d="M11 18.5h2"/>',
             '手机', ['手机', '移动', 'phone']),
    '对话': ('<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 16v4l4.5-4"/>',
             '对话框', ['对话', '沟通', 'chat']),
    '位置': ('<path d="M12 21.5s-7-5.3-7-11a7 7 0 0 1 14 0c0 5.7-7 11-7 11z"/><circle cx="12" cy="10.5" r="2.5"/>',
             '定位/地点', ['位置', '地点', 'pin']),
    '时间': ('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
             '时钟/时间', ['时间', '时钟', 'clock']),
    '金钱': ('<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2.8"/><path d="M5.5 12h.01M18.5 12h.01"/>',
             '纸币/财务', ['金钱', '成本', '财务', 'money']),
    '链接': ('<path d="M10 14a4.5 4.5 0 0 0 6.4.4l2.8-2.8a4.5 4.5 0 0 0-6.4-6.4l-1.6 1.6"/><path d="M14 10a4.5 4.5 0 0 0-6.4-.4l-2.8 2.8a4.5 4.5 0 0 0 6.4 6.4l1.6-1.6"/>',
             '链条/链接', ['链接', 'link']),
    '设置': ('<circle cx="12" cy="12" r="3.2"/><path d="M12 2.5v2.8M12 18.7v2.8M2.5 12h2.8M18.7 12h2.8M5.2 5.2l2 2M16.8 16.8l2 2M18.8 5.2l-2 2M7.2 16.8l-2 2"/>',
             '齿轮/设置', ['设置', '齿轮', '配置', 'setting']),
    '信息': ('<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 7.5h.01"/>',
             '信息/提示', ['信息', '提示', 'info']),
    '星标': ('<path d="m12 2.8 2.8 5.8 6.4.9-4.6 4.5 1.1 6.3-5.7-3-5.7 3 1.1-6.3L2.8 9.5l6.4-.9z"/>',
             '五角星', ['星标', '收藏', 'star']),
    '书签': ('<path d="M6.5 3h11V21l-5.5-3.8L6.5 21z"/>',
             '书签', ['书签', 'bookmark']),
    '文件夹': ('<path d="M3 7a2 2 0 0 1 2-2h4l2 2.5h8a2 2 0 0 1 2 2V18a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
               '文件夹/资产', ['文件夹', '资产', 'folder']),
    '火箭': ('<path d="M12 2.5c2.6 2.2 4 5.6 4 9.2l-4 2.8-4-2.8c0-3.6 1.4-7 4-9.2z"/><circle cx="12" cy="9" r="1.6"/><path d="M8.3 12.5 5 16.5l3.6-.6M15.7 12.5l3.3 4-3.6-.6"/><path d="M10.8 16.8c0 1.6.5 2.6 1.2 3.7.7-1.1 1.2-2.1 1.2-3.7"/>',
             '火箭/发射', ['火箭', '发射', 'rocket']),
    '旗帜': ('<path d="M5 21.5V4"/><path d="M5 4.5h12.5l-2.8 3.8 2.8 3.7H5"/>',
             '旗帜/里程碑', ['旗帜', '里程碑', 'flag']),
    '罗盘': ('<circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2.2 4.8-4.8 2.2 2.2-4.8z"/>',
             '罗盘/方向', ['罗盘', '方向', '导航', 'compass']),
}

DEFAULTS = ['信息', '检查', '数据', '图表', '目标', '团队', '工具']


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    assert len(ICONS) == 48, f'图标数应为 48，实际 {len(ICONS)}'
    assert all(d in ICONS for d in DEFAULTS), '默认图标必须在包内'
    index = {'version': '0.2.0', 'count': len(ICONS),
             'defaults': DEFAULTS, 'icons': {}}
    for name, (inner, label, keywords) in ICONS.items():
        svg = SVG_OPEN + inner + '</svg>'
        (OUT / f'{name}.svg').write_text(svg, encoding='utf-8')
        index['icons'][name] = {
            'file': f'{name}.svg',
            'png': f'{name}.png',
            'label': label,
            'keywords': keywords,
            'default': name in DEFAULTS,
        }
    (OUT / 'index.json').write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'[make_icon_pack] OK: {len(ICONS)} svg + index.json → {OUT}')
    if '--png' in sys.argv:
        try:
            import cairosvg
        except ImportError:
            print('[make_icon_pack] FAIL: 需 cairosvg（pip install cairosvg）才能渲染 PNG')
            return 1
        for name, (inner, _label, _kw) in ICONS.items():
            svg = SVG_OPEN.replace('currentColor', '#1a56a8') + inner + '</svg>'
            cairosvg.svg2png(bytestring=svg.encode('utf-8'),
                             write_to=str(OUT / f'{name}.png'),
                             output_width=512, output_height=512)
        print(f'[make_icon_pack] OK: {len(ICONS)} png(512px) → {OUT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
