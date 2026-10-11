#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TopPPT HTML · 报告骨架生成器（零依赖 · 替代"整份复制模板"）

用法:
    python scripts/scaffold_report.py --mode research --style mckinsey --theme light \
           --title "报告标题" --subtitle "副标题" --sections 8 --out 2026-09-15-主题.html
    python scripts/scaffold_report.py --mode presentation --plan plan.json --out deck.html
    python scripts/scaffold_report.py --mode architecture --list-types     # 看可用页型

为什么存在它（第一性原理）:
    模式模板内联了引擎/UI/运行时，单份 ≈ 230KB。让智能体"复制模板"在实践中常变成"读模板"
    → 单次生成白烧 6 万 token 且极易丢标记块。**确定性的事交给脚本**：脚本读模板、锁风格与主题、
    生成封面/Agenda/内容页/收尾/参考资料骨架，并**预生成 window.REPORT_MODEL**。
    智能体此后只需做两件不确定的事：**填内容** + **按规划卡调版式组合**。

产出（单文件、零外链、可翻页、亮暗双主题）:
    · 全部 __TOPPPT_*__ 标记块原样保留（引擎/UI/运行时/常量/schema 注入位不被破坏）
    · 封面 + Agenda（architecture 内容页 ≤4 时省略）+ N 个内容页 + 收尾 + 参考资料 + 页脚
    · 每页按其页型给出**正确的锁定版式类名骨架**（§46 / §46b / §36d / §37–§38b / §71–§77）
    · window.REPORT_MODEL 骨架与正文一一对应（严格 JSON，可被 extract_model.py 直接抽取）

plan.json 格式（可选；不给则按模式默认序列）:
    [{"type": "exhibit", "eyebrow": "01 · 现状诊断", "title": "结论句（行动标题）"}, ...]
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
TPL = ROOT / 'assets' / 'templates'
LC = json.loads((ROOT / 'scripts' / 'layout-constants.json').read_text(encoding='utf-8'))

CONTENT_RE = re.compile(r'<!-- __TOPPPT_CONTENT_START__ -->[\s\S]*?<!-- __TOPPPT_CONTENT_END__ -->')
MODEL_RE = re.compile(r'window\.REPORT_MODEL = \{[\s\S]*?\};')
NAV_RE = re.compile(r'<nav class="nav">[\s\S]*?</nav>')
BRAND_RE = re.compile(r'(<div class="brand__title">)[^<]*(</div>\s*<div class="brand__sub">)[^<]*(</div>)')

TPL_DEFAULT_STYLE = {'presentation': 'business-blue', 'research': 'mckinsey', 'architecture': 'graphite-dark'}
TPL_TITLE_TAG = {'presentation': '报告标题', 'research': '研究报告标题', 'architecture': '架构标题'}
TPL_BRAND = {
    'presentation': ('主标题', '副标题 / 专题名'),
    'research': ('报告标题', '研究报告 · 专题名'),
    'architecture': ('架构标题', '方案架构 · 专题名'),
}
DEFAULT_PLAN = {
    'presentation': ['points', 'bar', 'metrics', 'split', 'comparison', 'timeline', 'quote', 'steps'],
    # research：图表页与论证页交替 + 结构/分布类页型穿插（同时满足图表多样性门禁与节奏规则）
    'research': ['exhibit', 'twocol', 'halftable', 'metrics', 'threecol', 'table',
                 'matrix', 'exhibit', 'boxplot', 'twocol'],
    'architecture': ['diagram', 'lane', 'diagram'],
}

# 黄金节奏包：整篇页型序列预设（治「全篇 points/bar 公式化」；--preset 取用）
GOLDEN_PLANS = {
    'pitch': {
        'mode': 'presentation',
        'title': '路演/发布节奏',
        'types': ['metrics', 'bar', 'split', 'comparison', 'steps', 'timeline', 'kpi', 'points'],
    },
    'ops-review': {
        'mode': 'presentation',
        'title': '经营复盘节奏',
        'types': ['kpi', 'metrics', 'bar', 'table', 'split', 'comparison', 'points', 'quote'],
    },
    'consulting': {
        'mode': 'research',
        'title': '咨询密排节奏',
        'types': ['exhibit', 'twocol', 'halftable', 'metrics', 'threecol', 'matrix',
                  'exhibit', 'boxplot', 'twocol', 'table'],
    },
    'diagnostic': {
        'mode': 'research',
        'title': '诊断分析节奏',
        'types': ['metrics', 'exhibit', 'twocol', 'halftable', 'exhibit', 'matrix',
                  'table', 'threecol', 'boxplot', 'twocol'],
    },
    'layered-arch': {
        'mode': 'architecture',
        'title': '分层架构节奏',
        'types': ['diagram', 'lane', 'diagram'],
    },
    'flow-arch': {
        'mode': 'architecture',
        'title': '流程/数据流节奏',
        'types': ['lane', 'diagram', 'steps'],
    },
}
# 页型 → 布局骨架（layout-grammar P1–P12）；生成时写入 data-skel，校验与填内容共用
PAGE_TO_PRESET = {
    'points': 'P4', 'cards': 'P5', 'metrics': 'P2', 'kpi': 'P3', 'table': 'P8',
    'bar': 'P8', 'donut': 'P3', 'exhibit': 'P8', 'twocol': 'P4', 'threecol': 'P5',
    'halftable': 'P8', 'matrix': 'P7', 'heatmap': 'P7', 'bullet': 'P8', 'pyramid': 'P3',
    'timeline': 'P2', 'steps': 'P2', 'comparison': 'P4', 'split': 'P1', 'quote': 'P3',
    'image': 'P1', 'diagram': 'P9', 'lane': 'P9',
    'sankey': 'P9', 'treemap': 'P9', 'boxplot': 'P9', 'network': 'P9',
    'marimekko': 'P9', 'streamgraph': 'P9',
}
# 默认生成面优先核心图表（P1 收敛）；高级类型按需 --chart 指定
CHART_CORE = ['bar', 'hbar', 'line', 'donut', 'progress', 'area', 'stack', 'dualline']
CHART_CYCLE = CHART_CORE  # 轮换默认序列（骨架示范「图要选对」）
# 图表骨架尺寸：唯一事实源 = layout-constants.json charts.scaffold（v8.3 起禁止本文件硬编码尺寸；
# sync_runtime.py 校验 scaffold 默认值 ≥ charts.minSize 同口径阈值）
_SCAFFOLD = (LC.get('charts') or {}).get('scaffold') or {}
if not _SCAFFOLD.get('viewBoxHeight') or not _SCAFFOLD.get('infoTypes'):
    # 启动自检：单源缺键时立刻失败，防「静默退回默认值 180」的窗口期
    print('错误：layout-constants.json 缺 charts.scaffold.viewBoxHeight/infoTypes'
          '（骨架尺寸单源不完整；补单源后先跑 sync_runtime.py）', file=sys.stderr)
    sys.exit(2)
CHART_VIEWBOX = dict(_SCAFFOLD.get('viewBoxHeight') or {})
CHART_PX = dict(_SCAFFOLD.get('pxWidth') or {})
INFO_TYPES = {k: tuple(v) for k, v in (_SCAFFOLD.get('infoTypes') or {}).items()}


# ── 小工具 ────────────────────────────────────────────────────────────────────
def esc(s: str) -> str:
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def chart_svg(ct: str, idx: int) -> str:
    """最小合法图表骨架：data-chart 已登记 + viewBox 达标 + 指向代码节。"""
    vb_h = CHART_VIEWBOX.get(ct, 180)
    w = CHART_PX.get(ct)
    style = f' style="width:{w}px;margin-inline:auto"' if w else ''
    return (f'  <svg class="chart" data-chart="{ct}" viewBox="0 0 560 {vb_h}"{style}>\n'
            f'    <!-- TODO 图表代码：charts.md（按 data-chart 类型取对应节）；数据须与 REPORT_MODEL 一致 -->\n'
            f'    <text x="280" y="{vb_h // 2}" text-anchor="middle" class="f-txt3" font-size="12">'
            f'{ct} 图表占位 · 替换为真实图形</text>\n  </svg>')


def shead(eyebrow: str, title: str, lead: str = '') -> str:
    lead_html = f'\n    <p class="t-lead shead__desc">{esc(lead)}</p>' if lead else ''
    return (f'    <div class="shead rv">\n'
            f'      <div class="t-eyebrow">{esc(eyebrow)}</div>\n'
            f'      <h2 class="t-h1 shead__title">{esc(title)}</h2>{lead_html}\n    </div>')


def icon() -> str:
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round"><path d="M22 7l-8.5 8.5-5-5L2 17"/>'
            '<path d="M16 7h6v6"/></svg>')


# ── 页型骨架（HTML 版式 ↔ PPTX 页型同源）──────────────────────────────────────
def open_section(i, ptype, extra=''):
    """内容页 section 开标签 + 布局骨架标记（layout-grammar data-skel）。"""
    skel = PAGE_TO_PRESET.get(ptype, 'P4')
    return f'<section class="band" id="s{i}" data-skel="{skel}" data-page-type="{ptype}"{extra}>'


def pg_points(i, sec):
    html = f'''{open_section(i, 'points')}
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="grid g-2 rv a-start">
      <div class="card">
        <div class="card__hd"><div class="card__ico">{icon()}</div><h3 class="t-h3">要点一</h3></div>
        <ul class="ul"><li><strong>结论。</strong>一句话证据。</li><li><strong>结论。</strong>一句话证据。</li></ul>
      </div>
      <div class="card">
        <div class="card__hd"><div class="card__ico">{icon()}</div><h3 class="t-h3">要点二</h3></div>
        <ul class="ul"><li><strong>结论。</strong>一句话证据。</li><li><strong>结论。</strong>一句话证据。</li></ul>
      </div>
    </div>
  </div>
</section>'''
    return html, {'type': 'points', 'points': [['要点一', '一句话证据。'], ['要点二', '一句话证据。']]}


def pg_cards(i, sec):
    html = f'''<section class="band" id="s{i}">
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="grid g-3 rv">
      <div class="card"><div class="card__hd"><div class="card__ico">{icon()}</div><h3 class="t-h3">卡片一</h3></div>
        <p class="t-body">一句话说明。</p></div>
      <div class="card"><div class="card__hd"><div class="card__ico">{icon()}</div><h3 class="t-h3">卡片二</h3></div>
        <p class="t-body">一句话说明。</p></div>
      <div class="card"><div class="card__hd"><div class="card__ico">{icon()}</div><h3 class="t-h3">卡片三</h3></div>
        <p class="t-body">一句话说明。</p></div>
    </div>
  </div>
</section>'''
    # cards 契约：双引擎期望 {title, points[]}（见 build_pptx.js / pptx-export.js）；
    # 元组 [[k,v]] 会通过 schema 的 cards:array 却渲染空卡（v8.3 缺陷，v9 修复）。
    return html, {'type': 'cards', 'columns': 3,
                  'cards': [
                      {'title': '卡片一', 'points': [['要点', '一句话说明。']]},
                      {'title': '卡片二', 'points': [['要点', '一句话说明。']]},
                      {'title': '卡片三', 'points': [['要点', '一句话说明。']]}]}


def pg_metrics(i, sec):
    cards = ''.join(f'''
      <div class="metric"><div class="metric__v t-metric">{n}<small>%</small></div>
        <div class="metric__k">指标{n}</div><div class="metric__n">一行注解</div></div>'''
                     for n in (61, 18, 42, 76))
    html = f'''<section class="band band--top" id="s{i}">
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="grid g-4 rv">{cards}
    </div>
    <div class="row row-wrap rv" style="margin-top:var(--sp-5)">
      <div class="t-sm" style="color:var(--text-3)">口径：统计周期与样本说明<a class="cite" href="#ref-1">[1]</a></div>
    </div>
  </div>
</section>'''
    return html, {'type': 'metrics', 'metrics': [['61%', '指标1', '一行注解'], ['18%', '指标2', '一行注解'],
                                                 ['42%', '指标3', '一行注解'], ['76%', '指标4', '一行注解']]}


def pg_kpi(i, sec):
    html = f'''<section class="band" id="s{i}">
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="grid g-side rv" style="align-items:center">
      <div class="stack gap-3">
        <div class="t-metric" style="color:var(--accent);font-size:clamp(56px,7vh,76px)">61%</div>
        <div class="t-h3">核心指标名</div>
        <div class="t-sm" style="color:var(--accent);font-weight:600">▲ +6pt vs 上期</div>
      </div>
      <div class="grid g-3">
        <div class="metric"><div class="metric__v t-metric">18<small>%</small></div>
          <div class="metric__k">支撑指标</div><div class="metric__n">一行注解</div></div>
      </div>
    </div>
  </div>
</section>'''
    return html, {'type': 'kpi', 'hero': ['61%', '核心指标名', '▲ +6pt vs 上期'],
                  'metrics': [['18%', '支撑指标', '一行注解']]}


def pg_table(i, sec):
    rows = ''.join(f'\n        <tr><td class="k">对象 {n}</td><td class="num">{n * 7}%</td>'
                   f'<td><strong>结论</strong></td></tr>' for n in (1, 2, 3, 4))
    html = f'''<section class="band" id="s{i}">
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="tbl-wrap rv">
      <table>
        <thead><tr><th style="width:26%">维度</th><th style="width:24%">数值</th><th>结论</th></tr></thead>
        <tbody>{rows}
        </tbody>
      </table>
    </div>
  </div>
</section>'''
    return html, {'type': 'table',
                  'table': {'head': ['维度', '数值', '结论'],
                            'rows': [[f'对象 {n}', f'{n * 7}%', '结论'] for n in (1, 2, 3, 4)]}}


SIDE_NOTES = '''      <div class="stack gap-4">
        <h3 class="t-h3">怎么读这张图</h3>
        <ul class="ul">
          <li><strong>结论一。</strong>一句话（≤45 字）。</li>
          <li><strong>结论二。</strong>一句话（≤45 字）。</li>
          <li><strong>结论三。</strong>一句话（≤45 字）。</li>
        </ul>
      </div>'''


def pg_chart(i, sec):
    """P8 主区+注解列：主图 + 侧栏要点 + so-what（禁「一张图+标题」独页）。"""
    ct = sec.get('chart', 'hbar')
    html = f'''{open_section(i, 'bar')}
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="grid g-side rv a-start">
      <div class="fig">
        <div class="fig__cap">图表标题（写结论）</div>
{chart_svg(ct, i)}
      </div>
{SIDE_NOTES}
    </div>
    <div class="sowhat rv"><span class="sowhat__v">一行含义（≤60 字）。</span></div>
  </div>
</section>'''
    return html, {'type': 'bar', 'chart': {'type': ct, 'labels': ['A', 'B', 'C'], 'values': [42, 61, 35],
                                           'dataTable': 'notes'},
                  'soWhat': '一行含义（≤60 字）。'}


def pg_donut(i, sec):
    """P3/V3：简单占比配侧栏图例说明，禁止弧上叠标签。"""
    html = f'''{open_section(i, 'donut')}
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="grid g-side rv a-start">
      <div class="fig rv" style="text-align:center">
        <div class="fig__cap">构成占比</div>
{chart_svg('donut', i)}
      </div>
{SIDE_NOTES}
    </div>
    <div class="sowhat rv"><span class="sowhat__v">一行含义（≤60 字）。</span></div>
  </div>
</section>'''
    return html, {'type': 'donut', 'chart': {'labels': ['A', 'B', 'C'], 'values': [45, 35, 20],
                                             'dataTable': 'notes'},
                  'soWhat': '一行含义（≤60 字）。'}


def pg_exhibit(i, sec):
    ct = sec.get('chart', 'bar')
    html = f'''{open_section(i, 'exhibit')}
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="grid g-side rv a-start">
      <div class="exhibit rv">
        <div class="exhibit__hd"><span class="exhibit__no">Exhibit {sec.get('exhibitNo', 1)}</span>
          <span class="exhibit__t">图表标题（结论式）</span></div>
{chart_svg(ct, i)}
        <div class="exhibit__src">来源：<真实来源名>，YYYY-MM；口径说明<a class="cite" href="#ref-1">[1]</a></div>
      </div>
{SIDE_NOTES}
    </div>
    <div class="sowhat rv">
      <span class="sowhat__v">一行含义或建议（≤60 字）。</span>
    </div>
  </div>
</section>'''
    return html, {'type': 'exhibit', 'exhibitNo': sec.get('exhibitNo', 1),
                  'chart': {'type': ct, 'labels': ['A', 'B', 'C'], 'values': [42, 61, 35],
                            'dataTable': 'notes'},
                  'soWhat': '一行含义或建议（≤60 字）。',
                  'footnote': '来源：<真实来源名>，YYYY-MM；口径说明'}


def pg_twocol(i, sec):
    html = f'''<section class="band" id="s{i}">
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="cols-2 rv">
      <p class="t-body"><strong>发现。</strong>直接陈述数据与事实，≤200 字。</p>
      <p class="t-body"><strong>证据。</strong>引用口径与对照数据，外部数据带 [n]。</p>
      <p class="t-body"><strong>含义。</strong>这一发现意味着什么、下一步动作。</p>
    </div>
    <div class="footnote">注：口径与样本说明一行。</div>
  </div>
</section>'''
    return html, {'type': 'twocol', 'paragraphs': [['发现', '直接陈述数据与事实，≤200 字。'],
                                                   ['证据', '引用口径与对照数据。'],
                                                   ['含义', '这一发现意味着什么、下一步动作。']]}


def pg_threecol(i, sec):
    html = f'''<section class="band" id="s{i}">
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="cols-3 rv">
      <p class="t-body"><strong>论点一。</strong>第一栏论述，每栏 ≤150 字。</p>
      <p class="t-body"><strong>论点二。</strong>第二栏论述，与第一栏并列推进。</p>
      <p class="t-body"><strong>论点三。</strong>第三栏论述，收束到本页结论。</p>
    </div>
    <div class="footnote">注：三方口径与样本说明一行。</div>
  </div>
</section>'''
    return html, {'type': 'threecol', 'paragraphs': [['论点一', '第一栏论述，每栏 ≤150 字。'],
                                                     ['论点二', '第二栏论述，与第一栏并列推进。'],
                                                     ['论点三', '第三栏论述，收束到本页结论。']]}


def pg_halftable(i, sec):
    ct = sec.get('chart', 'hbar')
    rows = ''.join(f'\n        <tr><td class="k">对象 {n}</td><td class="num">{n * 7}%</td>'
                   f'<td><strong>+{n}pt</strong></td></tr>' for n in (1, 2, 3))
    html = f'''<section class="band" id="s{i}">
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="grid g-half rv" style="align-items:start">
      <div class="tbl-wrap">
        <table>
          <thead><tr><th style="width:30%">对象</th><th>数值</th><th>变化</th></tr></thead>
          <tbody>{rows}
          </tbody>
        </table>
      </div>
      <div class="exhibit">
        <div class="exhibit__hd"><span class="exhibit__no">Exhibit {sec.get('exhibitNo', 1)}</span>
          <span class="exhibit__t">右栏图表标题（结论式）</span></div>
{chart_svg(ct, i)}
        <div class="exhibit__src">来源：<真实来源名>，YYYY-MM；口径说明<a class="cite" href="#ref-1">[1]</a></div>
      </div>
    </div>
  </div>
</section>'''
    return html, {'type': 'halftable', 'exhibitNo': sec.get('exhibitNo', 1),
                  'table': {'head': ['对象', '数值', '变化'],
                            'rows': [[f'对象 {n}', f'{n * 7}%', f'+{n}pt'] for n in (1, 2, 3)]},
                  'chart': {'type': ct, 'labels': ['A', 'B', 'C'], 'values': [42, 61, 35],
                            'dataTable': 'notes'}}


def pg_matrix(i, sec):
    html = f'''<section class="band" id="s{i}">
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="matrix rv">
      <div class="matrix__grid" style="--mx-cols:3">
        <div></div>
        <div class="matrix__h">列一 · 低</div><div class="matrix__h">列二 · 中</div><div class="matrix__h">列三 · 高</div>
        <div class="matrix__rh">行一 · 高</div>
        <div class="matrix__c matrix__c--a"><b>单元</b>说明</div>
        <div class="matrix__c"><b>单元</b>说明</div>
        <div class="matrix__c"><b>单元</b>说明</div>
        <div class="matrix__rh">行二 · 中</div>
        <div class="matrix__c"><b>单元</b>说明</div>
        <div class="matrix__c"><b>单元</b>说明</div>
        <div class="matrix__c matrix__c--a"><b>单元</b>说明</div>
      </div>
      <div class="matrix__note">图例：强调单元 = 优先投入项。</div>
    </div>
  </div>
</section>'''
    return html, {'type': 'matrix', 'rowHeads': ['行一 · 高', '行二 · 中'],
                  'colHeads': ['列一 · 低', '列二 · 中', '列三 · 高'],
                  'cells': [['单元 说明', '单元 说明', '单元 说明'],
                            ['单元 说明', '单元 说明', {'t': '单元 说明', 'accent': True}]]}


def pg_heatmap(i, sec):
    html = f'''<section class="band" id="s{i}">
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="heat rv">
      <div class="heat__grid" style="--heat-cols:4;--heat-label:132px">
        <div></div>
        <div class="heat__h">列一</div><div class="heat__h">列二</div><div class="heat__h">列三</div><div class="heat__h">列四</div>
        <div class="heat__rh">行一</div>
        <div class="heat__c heat__c--3">78<small>高</small></div>
        <div class="heat__c heat__c--1">46<small>中</small></div>
        <div class="heat__c heat__c--2">63<small>中高</small></div>
        <div class="heat__c">38<small>低</small></div>
      </div>
      <div class="heat__legend"><span>就绪度</span>
        <span class="heat__sw" style="background:var(--surface-1)"></span>
        <span class="heat__sw" style="background:var(--accent-soft)"></span>
        <span class="heat__sw" style="background:var(--accent-soft-2)"></span>
        <span class="heat__sw" style="background:var(--accent)"></span>
        <span>低 → 高（单位：分）</span></div>
    </div>
    <div class="footnote">口径：评分来源与样本说明。</div>
  </div>
</section>'''
    return html, {'type': 'heatmap', 'rowHeads': ['行一'], 'colHeads': ['列一', '列二', '列三', '列四'],
                  'cells': [[78, 46, 63, 38]], 'unit': '分',
                  'scaleLabel': ['低', '中', '中高', '高']}


def pg_bullet(i, sec):
    html = f'''<section class="band" id="s{i}">
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="bul rv" style="--bul-label:minmax(0,2.4fr)">
      <div class="bul__row"><div class="bul__k">场景覆盖</div>
        <div class="bul__track"><div class="bul__fill" style="width:61%"></div>
          <div class="bul__tgt" style="left:80%"></div></div>
        <div class="bul__v"><b>61%</b> / 80%</div></div>
      <div class="bul__row bul__row--warn"><div class="bul__k">治理就绪</div>
        <div class="bul__track"><div class="bul__fill" style="width:34%"></div>
          <div class="bul__tgt" style="left:75%"></div></div>
        <div class="bul__v"><b>34%</b> / 75%</div></div>
    </div>
  </div>
</section>'''
    return html, {'type': 'bullet', 'unit': '%', 'max': 100,
                  'items': [['场景覆盖', 61, 80], ['治理就绪', 34, 75]]}


def pg_pyramid(i, sec):
    html = f'''<section class="band" id="s{i}">
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="pyr rv">
      <div class="pyr__lvl" style="--w:42%"><div class="pyr__t">顶层</div><div class="pyr__d">说明 ≤24 字</div></div>
      <div class="pyr__lvl pyr__lvl--a" style="--w:72%"><div class="pyr__t">中层</div><div class="pyr__d">说明 ≤24 字</div></div>
      <div class="pyr__lvl" style="--w:100%"><div class="pyr__t">底层</div><div class="pyr__d">说明 ≤24 字</div></div>
    </div>
  </div>
</section>'''
    return html, {'type': 'pyramid', 'levels': [['顶层', '说明'], ['中层', '说明'], ['底层', '说明']]}


def pg_timeline(i, sec):
    html = f'''<section class="band" id="s{i}">
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="fig rv" style="padding:clamp(24px,2.4vw,36px)">
      <div class="tl">
        <div class="tl__i tl__i--done"><div class="tl__d"></div>
          <div class="tl__l">2026 Q3</div><div class="tl__t">阶段一</div>
          <p class="t-body">≤2 行说明。</p></div>
        <div class="tl__i tl__i--now"><div class="tl__d"></div>
          <div class="tl__l">2026 Q4</div><div class="tl__t">阶段二</div>
          <p class="t-body">≤2 行说明。</p></div>
        <div class="tl__i"><div class="tl__d"></div>
          <div class="tl__l">2027 Q1</div><div class="tl__t">阶段三</div>
          <p class="t-body">≤2 行说明。</p></div>
      </div>
    </div>
  </div>
</section>'''
    return html, {'type': 'timeline', 'phases': [['2026 Q3', '阶段一', '≤2 行说明。'],
                                                 ['2026 Q4', '阶段二', '≤2 行说明。'],
                                                 ['2027 Q1', '阶段三', '≤2 行说明。']]}


def pg_steps(i, sec):
    html = f'''{open_section(i, 'steps')}
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="steps__phase rv">第一阶段 · 打基础</div>
    <div class="steps rv">
      <div class="step"><div class="step__n">01</div><div class="step__t">步骤一</div>
        <div class="step__d">动作说明 ≤30 字</div></div>
      <div class="step step--a"><div class="step__n">02</div><div class="step__t">步骤二</div>
        <div class="step__d">关键步高亮（≤2 处）</div></div>
      <div class="step"><div class="step__n">03</div><div class="step__t">步骤三</div>
        <div class="step__d">动作说明 ≤30 字</div></div>
    </div>
    <div class="flow-rail rv">
      <div class="flow-box flow-box--end">开始</div>
      <span class="lane__arr" aria-hidden="true"></span>
      <div class="flow-dia"><svg viewBox="0 0 72 72" aria-hidden="true"><polygon points="36,4 68,36 36,68 4,36" class="f-none s-acc" stroke-width="2"/></svg><span>判断</span></div>
      <span class="lane__arr" aria-hidden="true"></span>
      <div class="flow-box flow-box--a">关键步</div>
      <span class="lane__arr" aria-hidden="true"></span>
      <div class="flow-box flow-box--ex">异常</div>
    </div>
  </div>
</section>'''
    return html, {'type': 'steps', 'steps': [['步骤一', '动作说明'], ['步骤二', '关键步'], ['步骤三', '动作说明']]}


def pg_comparison(i, sec):
    html = f'''<section class="band" id="s{i}">
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="grid g-half rv">
      <div class="card"><h3 class="t-h3">现状</h3>
        <ul class="ul"><li><strong>要点。</strong>一句话。</li><li><strong>要点。</strong>一句话。</li></ul></div>
      <div class="card" style="background:var(--accent-soft);border-color:transparent">
        <h3 class="t-h3" style="color:var(--accent)">目标</h3>
        <ul class="ul"><li><strong>要点。</strong>一句话。</li><li><strong>要点。</strong>一句话。</li></ul></div>
    </div>
    <div class="sowhat rv"><span class="sowhat__v">一行结论（≤60 字）。</span></div>
  </div>
</section>'''
    return html, {'type': 'comparison',
                  'left': {'title': '现状', 'points': [['要点', '一句话。'], ['要点', '一句话。']]},
                  'right': {'title': '目标', 'points': [['要点', '一句话。'], ['要点', '一句话。']]},
                  'verdict': '一行结论（≤60 字）。'}


def pg_split(i, sec):
    """双区组合页：默认「左文右图」；规划卡写 left_type='chart' 时「左图右文」（走 split 左区图表路径）。"""
    ct = sec.get('chart', 'bar')
    left_is_chart = (sec.get('left_type') == 'chart')
    fig = f'''      <div class="fig">
        <div class="fig__cap">图表标题</div>
{chart_svg(ct, i)}
      </div>'''
    pts = '''      <div class="stack gap-5">
        <h3 class="t-h3">怎么读这张图</h3>
        <ul class="ul">
          <li><strong>结论一。</strong>一句话。</li>
          <li><strong>结论二。</strong>一句话。</li>
          <li><strong>结论三。</strong>一句话。</li>
        </ul>
        <div class="note"><i class="note__ico">i</i><div><p class="t-body">可选强调。</p></div></div>
      </div>'''
    left, right = (fig, pts) if left_is_chart else (pts, fig)
    html = f'''<section class="band" id="s{i}">
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="grid g-side rv" style="align-items:start">
{left}
{right}
    </div>
  </div>
</section>'''
    m_pts = {'points': [['结论一', '一句话。'], ['结论二', '一句话。'], ['结论三', '一句话。']]}
    m_chart = {'type': ct, 'cap': '图表标题', 'labels': ['A', 'B', 'C'], 'values': [42, 61, 35],
               'dataTable': 'notes'}
    return html, {'type': 'split',
                  'left': m_chart if left_is_chart else m_pts,
                  'right': m_pts if left_is_chart else m_chart}


def pg_quote(i, sec):
    html = f'''<section class="band band--accent--solid band--fit" id="s{i}">
  <div class="wrap">
    <div class="shead shead--center rv">
      <div class="t-eyebrow">{esc(sec['eyebrow'])}</div>
      <h2 class="t-h1 shead__title">{esc(sec['title'])}</h2>
      <p class="t-lead" style="max-width:860px;margin-inline:auto;font-weight:600">一句金句（≤40 字）。</p>
      <p class="t-sm" style="margin-top:var(--sp-4)">—— 出处 / 样本</p>
    </div>
  </div>
</section>'''
    return html, {'type': 'quote', 'quote': '一句金句（≤40 字）。', 'author': '出处 / 样本'}


def pg_image(i, sec):
    html = f'''<section class="band" id="s{i}">
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <figure class="media media--r3-1 media--ph rv">
      <div class="media__ph">
        <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2"/>
          <circle cx="9" cy="10" r="1.6"/><path d="m3 18 5-5 4 3.4 3-2.6 6 5.2"/></svg>
        <b>配图占位</b><span>建议 2400×800px · 3:1 · 替换 image.src 即可</span>
      </div>
    </figure>
    <p class="media__src">图 1：图注（占位；交付前替换为真实素材）</p>
  </div>
</section>'''
    return html, {'type': 'image', 'image': {'placeholder': True, 'layout': 'full',
                                             'caption': '图 1：图注', 'hint': '建议 2400×800px'}}


def pg_diagram(i, sec):
    conn = ('<div class="arch__conn" aria-hidden="true">'
            '<svg width="18" height="22" viewBox="0 0 18 22" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M9 2v14"/><path d="M4 12l5 6 5-6"/></svg></div>')
    html = f'''{open_section(i, 'diagram', ' band--fit')}
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="arch rv">
      <div class="arch__layer arch__layer--focus">
        <div class="arch__lname">应用层</div>
        <div class="arch__nodes">
          <div class="arch__node arch__node--accent"><div class="arch__nt">节点一</div><div class="arch__nd">一行注</div></div>
          <div class="arch__node"><div class="arch__nt">节点二</div><div class="arch__nd">一行注</div></div>
        </div>
      </div>
      {conn}
      <div class="arch__layer">
        <div class="arch__lname">服务层</div>
        <div class="arch__nodes">
          <div class="arch__node"><div class="arch__nt">节点三</div><div class="arch__nd">一行注</div></div>
        </div>
      </div>
    </div>
    <div class="arch__legend">
      <span class="chip chip--accent">当前建设焦点</span><span class="chip">已有能力</span>
    </div>
  </div>
</section>'''
    return html, {'type': 'diagram', 'layers': [['应用层', [['节点一', '一行注'], ['节点二', '一行注']]],
                                                ['服务层', [['节点三', '一行注']]]],
                  'legend': ['当前建设焦点', '已有能力']}


def pg_lane(i, sec):
    """泳道：CSS 正交箭头（.lane__arr 线段+箭头），禁裸文字 →。"""
    def arr(last=False):
        return '' if last else '<span class="lane__arr" aria-hidden="true"></span>'
    html = f'''{open_section(i, 'lane', ' band--fit')}
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="stack rv gap-3">
      <div class="lane"><div class="lane__hd">业务域</div>
        <div class="lane__body">
          <span class="lane__step">提需求</span>{arr()}
          <span class="lane__step">确认口径</span>{arr()}
          <span class="lane__step lane__step--a">Agent 取数</span>{arr()}
          <span class="lane__step">验收结果</span>{arr(True)}
        </div>
      </div>
      <div class="lane"><div class="lane__hd">数据平台</div>
        <div class="lane__body">
          <span class="lane__step">契约校验</span>{arr()}
          <span class="lane__step">指标服务</span>{arr()}
          <span class="lane__step">审计留痕</span>{arr(True)}
        </div>
      </div>
    </div>
    <div class="arch__legend">
      <span class="chip chip--accent">关键步骤</span><span class="chip">常规步骤</span>
    </div>
  </div>
</section>'''
    return html, {'type': 'lane', 'lanes': [['业务域', ['提需求', '确认口径', {'t': 'Agent 取数', 'accent': True}, '验收结果']],
                                            ['数据平台', ['契约校验', '指标服务', '审计留痕']]]}


def pg_info(i, sec):
    t = sec['type']
    w, h = INFO_TYPES[t]
    cap = {'sankey': '流向与流量（带宽 ∝ 流量）', 'treemap': '层级构成（面积 ∝ 数值）',
           'boxplot': '分组分布（箱体 = Q1–Q3，中线 = 中位，须 = 极值）',
           'network': '节点-边拓扑（节点半径 ∝ 连接度）',
           'marimekko': '双重编码（列宽 ∝ 规模，列高 = 构成占比）',
           'streamgraph': '构成演变（基线居中 · 带宽 ∝ 规模）'}[t]
    # 信息图页承载在 .fig 里（不是 .exhibit 框）→ 来源行走 .footnote，避免与 Exhibit 来源行统计混淆
    src = ('    <div class="footnote">来源：<真实来源名>，YYYY-MM；口径说明'
           '<a class="cite" href="#ref-1">[1]</a></div>\n')
    html = f'''<section class="band" id="s{i}">
  <div class="wrap">
{shead(sec['eyebrow'], sec['title'], sec.get('lead', ''))}
    <div class="fig rv">
      <div class="fig__cap">{cap}</div>
      <svg class="chart" data-chart="{t}" viewBox="0 0 {w} {h}">
        <!-- TODO 信息图写法：infographics.md §71–§77（统计图形）/ §78–§81（结构图形） -->
        <text x="{w // 2}" y="{h // 2}" text-anchor="middle" class="f-txt3" font-size="13">{t} 信息图占位</text>
      </svg>
    </div>
{src}    <div class="sowhat rv"><span class="sowhat__v">一行含义（≤60 字）。</span></div>
  </div>
</section>'''
    model = {'type': t}
    if t == 'sankey':
        model['flows'] = [['A', 'B', 100], ['B', 'C', 60], ['B', '流失', 40]]
    elif t == 'treemap':
        model['items'] = [['A', 38], ['B', 27], ['C', 21], ['D', 14]]
    elif t == 'boxplot':
        model['groups'] = [['A 线', 12, 28, 35, 48, 62], ['B 线', 18, 30, 34, 40, 46]]
    elif t == 'network':
        model['nodes'] = [['n1', '核心'], ['n2', '订单'], ['n3', '结算']]
        model['edges'] = [['n1', 'n2'], ['n1', 'n3'], ['n2', 'n3']]
    elif t == 'marimekko':
        model['cols'] = [['2024', 130], ['2025', 165]]
        model['cells'] = [[52, 48], [61, 39]]
        model['legend'] = ['线上', '线下']
    elif t == 'streamgraph':
        model['labels'] = ['2024', '2025']
        model['series'] = [{'name': '订阅', 'values': [52, 68]}, {'name': '服务', 'values': [34, 30]}]
    model['chart'] = {'dataTable': 'notes'}
    model['soWhat'] = '一行含义（≤60 字）。'
    return html, model


BUILDERS = {
    'points': pg_points, 'cards': pg_cards, 'metrics': pg_metrics, 'kpi': pg_kpi, 'table': pg_table,
    'bar': pg_chart, 'donut': pg_donut, 'exhibit': pg_exhibit, 'twocol': pg_twocol,
    'threecol': pg_threecol, 'halftable': pg_halftable, 'matrix': pg_matrix, 'heatmap': pg_heatmap,
    'bullet': pg_bullet, 'pyramid': pg_pyramid, 'timeline': pg_timeline, 'steps': pg_steps,
    'comparison': pg_comparison, 'split': pg_split, 'quote': pg_quote, 'image': pg_image,
    'diagram': pg_diagram, 'lane': pg_lane,
    'sankey': pg_info, 'treemap': pg_info, 'boxplot': pg_info, 'network': pg_info,
    'marimekko': pg_info, 'streamgraph': pg_info,
}


SOWHAT_BLOCK = '''    <div class="sowhat rv">
      <span class="sowhat__v">这一页的含义或下一步建议（≤60 字）。</span>
    </div>
'''
HAS_NOTE = re.compile(r'class="(?:sowhat|note)\b')


def inject_sowhat(h: str) -> str:
    """research 节奏兜底：连续 2 页无结论条时补一条（校验器要求 ≤3 页无 .sowhat/.note）。"""
    i = h.rfind('  </div>\n</section>')
    return h if i < 0 else h[:i] + SOWHAT_BLOCK + h[i:]


# ── 页面骨架：封面 / Agenda / 收尾 / 参考资料 / 页脚 ────────────────────────────
def cover(mode, title, subtitle, meta):
    return f'''<!-- 封面 -->
<section class="band band--fit" id="cover">
  <div class="wrap">
    <div class="shead rv">
      <div class="t-eyebrow">{esc(meta)}</div>
      <h1 class="t-display shead__title">{esc(title)}</h1>
      <p class="t-lead shead__desc">{esc(subtitle)}</p>
    </div>
  </div>
</section>'''


def agenda(mode, items):
    lis = '\n'.join(
        f'''      <li class="agenda__i"><a class="agenda__a" href="#{sid}">
        <span class="agenda__n">{n:02d}</span>
        <span><span class="agenda__t">{esc(t)}</span><div class="agenda__d">{esc(d)}</div></span>
        <span class="agenda__go"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
          stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></span>
      </a></li>''' for n, (sid, t, d) in enumerate(items, 1))
    cls = 'agenda agenda--2col' if len(items) > 8 else 'agenda'
    return f'''<!-- Agenda（第二页） -->
<section class="band band--tint" id="agenda">
  <div class="wrap">
    <div class="shead rv">
      <div class="t-eyebrow">Agenda</div>
      <h2 class="t-h1 shead__title">报告大纲</h2>
      <p class="t-lead shead__desc">点击任意条目跳转。</p>
    </div>
    <ol class="{cls} rv">
{lis}
    </ol>
  </div>
</section>'''


def closing(mode, title, points):
    cards = '\n'.join(f'''      <div class="card"><h3 class="t-h3" style="margin-bottom:var(--sp-2)">{esc(k)}</h3>
        <p class="t-body">{esc(v)}</p></div>''' for k, v in points)
    return f'''<!-- 收尾（主题一致强调带：不用 band--deep） -->
<section class="band band--accent band--fit" id="next">
  <div class="wrap">
    <div class="shead shead--center rv">
      <div class="t-eyebrow">下一步</div>
      <h2 class="t-h1 shead__title">{esc(title)}</h2>
      <p class="t-lead shead__desc">收尾页必须回应封面提出的问题。</p>
    </div>
    <div class="grid g-3 rv">
{cards}
    </div>
  </div>
</section>'''


def refs(mode, items):
    """参考资料：只列真实来源条目；无真实来源时整节省略（禁止占位条目误导读者）。
    items 元素 = (来源名, 时间；口径) 且来源名必须是真实机构/报告/文档名。"""
    if not items:
        # 宁缺毋假：scaffold 不生成假「参考资料」页；正文无 [n] 时也不需要该节
        return ''
    body = ('    <ul class="ul ul--num rv">\n' + '\n'.join(
        f'''        <li id="ref-{n}">{esc(s)}　<span class="t-xs" style="color:var(--text-3)">{esc(t)}</span></li>'''
        for n, (s, t) in enumerate(items, 1)) + '\n    </ul>')
    return f'''<!-- 参考资料（只列真实来源；无真实来源请整节删除并去掉正文 [n] 与导航入口） -->
<section class="band band--tint" id="refs">
  <div class="wrap">
    <div class="shead rv">
      <div class="t-eyebrow">参考资料</div>
      <h2 class="t-h1 shead__title">参考资料：来源、时间与统计口径</h2>
    </div>
{body}
  </div>
</section>'''


def footer(title, subtitle, meta):
    return f'''<footer class="foot">
  <div class="wrap foot__in">
    <div class="brand">
      <div class="brand__mark">R</div>
      <div class="brand__txt">
        <div class="brand__title">{esc(title)}</div>
        <div class="brand__sub">{esc(subtitle)} · {esc(meta)}</div>
      </div>
    </div>
    <div class="t-xs">密级：内部</div>
  </div>
</footer>'''


# ── 主流程 ────────────────────────────────────────────────────────────────────
def build_plan(mode: str, n: int, plan: list | None, preset: str | None = None) -> list[dict]:
    if plan:
        out = []
        for k, it in enumerate(plan):
            s = dict(it)
            s.setdefault('type', 'points')
            s.setdefault('eyebrow', f'{k + 1:02d} · 章节')
            s.setdefault('title', f'第 {k + 1} 页行动标题（结论句）')
            out.append(s)
        return out
    seq = DEFAULT_PLAN[mode]
    if preset:
        gp = GOLDEN_PLANS.get(preset)
        if not gp:
            print(f'警告：未知节奏包 {preset!r}，回落默认序列')
        else:
            if gp['mode'] != mode:
                print(f'警告：节奏包 {preset} 属于 {gp["mode"]}，与 --mode {mode} 不一致；'
                      f'将自动切换 mode={gp["mode"]}')
            seq = gp['types']
            mode = gp['mode']
    out = []
    for k in range(n):
        t = seq[k % len(seq)]
        out.append({'type': t, 'eyebrow': f'{k + 1:02d} · 章节', 'title': f'第 {k + 1} 页行动标题（结论句）'})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description='TopPPT HTML 报告骨架生成器')
    ap.add_argument('--mode', default='presentation', choices=['presentation', 'research', 'architecture'])
    ap.add_argument('--style', default=None, help='9 套风格之一（默认取模板出厂风格）')
    ap.add_argument('--theme', default=None, choices=['light', 'dark'],
                    help='默认 light；石墨深灰（graphite-dark）默认 dark（深色优先风格）')
    ap.add_argument('--title', default='报告标题')
    ap.add_argument('--subtitle', default='副标题 / 范围口径')
    ap.add_argument('--meta', default='2026-01-01 · 内部')
    ap.add_argument('--sections', type=int, default=None, help='内容页数（不给则按模式默认）')
    ap.add_argument('--plan', help='页型规划 JSON 文件：[{"type","eyebrow","title"}…]')
    ap.add_argument('--preset', help='黄金节奏包名：pitch/ops-review/consulting/diagnostic/layered-arch/flow-arch')
    ap.add_argument('--out', help='输出 HTML 路径')
    ap.add_argument('--list-types', action='store_true', help='列出可用页型与节奏包后退出')
    args = ap.parse_args()

    if args.list_types:
        print('可用页型（' + str(len(BUILDERS)) + '）：')
        print('  ' + ' · '.join(sorted(BUILDERS)))
        print('\n默认序列：')
        for m, seq in DEFAULT_PLAN.items():
            print(f'  {m}: ' + ' → '.join(seq))
        print('\n黄金节奏包（--preset）：')
        for name, gp in GOLDEN_PLANS.items():
            print(f'  {name:14} [{gp["mode"]}] {gp["title"]}: ' + ' → '.join(gp['types']))
        return 0

    if not args.out:
        print('错误：需要 --out <输出.html>')
        return 2

    mode = args.mode
    if args.preset and args.preset in GOLDEN_PLANS and GOLDEN_PLANS[args.preset]['mode'] != mode:
        mode = GOLDEN_PLANS[args.preset]['mode']
        print(f'提示：按节奏包 {args.preset} 切换 mode={mode}')
    tpl_path = TPL / f'{mode}.html'
    if not tpl_path.exists():
        print(f'错误：模板不存在 {tpl_path}')
        return 2
    t = tpl_path.read_text(encoding='utf-8')

    style = args.style or TPL_DEFAULT_STYLE[mode]
    # 风格早校验：未知风格现在拦下（干净报错），而不是生成一份后续 validate 才判 FAIL 的 HTML
    _lc_styles = None
    try:
        _lc = json.loads((ROOT / 'scripts' / 'layout-constants.json').read_text(encoding='utf-8'))
        _lc_styles = sorted(k for k in (_lc.get('styles') or {}) if not str(k).startswith('$'))
    except (OSError, ValueError):
        _lc_styles = None  # 单源读不到时不拦（校验门禁兜底）
    if _lc_styles and style not in _lc_styles:
        print(f'错误：未知风格 {style!r}（可选：{" / ".join(_lc_styles)}）')
        return 2
    theme = args.theme or ('dark' if style == 'graphite-dark' else 'light')
    n = args.sections if args.sections is not None else {'presentation': 8, 'research': 10, 'architecture': 3}[mode]
    if n < 0:
        print(f'错误：--sections 必须 ≥ 0（得到 {n}）')
        return 2
    plan = None
    if args.plan:
        plan_path = Path(args.plan)
        try:
            plan_text = plan_path.read_text(encoding='utf-8')
        except FileNotFoundError:
            print(f'错误：--plan 文件不存在 {plan_path}')
            return 2
        except UnicodeDecodeError as e:
            print(f'错误：--plan 不是合法 UTF-8 {plan_path}: {e}')
            return 2
        except OSError as e:
            print(f'错误：无法读取 --plan {plan_path}: {e}')
            return 2
        try:
            plan = json.loads(plan_text)
        except json.JSONDecodeError as e:
            print(f'错误：--plan 不是合法 JSON {plan_path}: {e}')
            return 2
        if not isinstance(plan, list):
            print(f'错误：--plan 根节点必须是数组（得到 {type(plan).__name__}）')
            return 2
        bad_items = [k for k, it in enumerate(plan) if not isinstance(it, dict)]
        if bad_items:
            print(f'错误：--plan 第 {", ".join(str(k + 1) for k in bad_items)} 项不是对象（每项应为 {{"type","eyebrow","title"}}）')
            return 2
        n = len(plan)
    pages = build_plan(mode, n, plan, preset=args.preset)

    # ① 风格 / 主题 / 标题 / 品牌
    t = t.replace(f'data-style="{TPL_DEFAULT_STYLE[mode]}"', f'data-style="{style}"', 1)
    t = re.sub(r'(<html[^>]*data-theme=")[^"]*(")', r'\g<1>' + theme + r'\g<2>', t, count=1)
    assert f'data-mode="{mode}" data-style="{style}" data-theme="{theme}"' in t, \
        '主题/风格注入失败（模板 html 标签与预期不一致）'
    t = t.replace(f'<title>{TPL_TITLE_TAG[mode]}</title>', f'<title>{esc(args.title)}</title>', 1)
    old_t, old_s = TPL_BRAND[mode]
    assert BRAND_RE.search(t), '模板缺少品牌标题结构'
    t = BRAND_RE.sub(lambda m: m.group(1) + esc(args.title) + m.group(2) + esc(args.subtitle) + m.group(3),
                     t, count=1)

    # ② 正文区
    html_parts, model_secs, agenda_items = [], [], []
    exhibit_no = 1
    chart_i = 0
    since_note = 0
    for k, p in enumerate(pages, 1):
        p.setdefault('type', 'points')
        b = BUILDERS.get(p['type'])
        if b is None:
            print(f'警告：未知页型 {p["type"]!r}，回落到 points')
            b = pg_points
        if p['type'] in ('bar', 'exhibit', 'halftable', 'split'):
            p.setdefault('chart', CHART_CYCLE[chart_i % len(CHART_CYCLE)])
            chart_i += 1
        if p['type'] in ('exhibit', 'halftable'):
            p['exhibitNo'] = exhibit_no
            exhibit_no += 1
        h, m = b(k, p)
        # 布局骨架标记（layout-grammar）：无则补 data-skel / data-page-type
        skel = PAGE_TO_PRESET.get(p['type'], 'P4')
        if 'data-skel=' not in h:
            h = re.sub(
                r'<section class="band([^"]*)" id="s' + str(k) + r'"',
                f'<section class="band\\1" id="s{k}" data-skel="{skel}" data-page-type="{p["type"]}"',
                h, count=1)
        m['layoutPreset'] = skel
        has_note = bool(HAS_NOTE.search(h))
        if not has_note and since_note >= 2:      # research 节奏：≤2 页无结论条
            h = inject_sowhat(h)
            has_note = True
        since_note = 0 if has_note else since_note + 1
        html_parts.append(h)
        m.update({'eyebrow': p['eyebrow'], 'title': p['title']})
        if p.get('lead'):
            m['lead'] = p['lead']
        model_secs.append(m)

    # Agenda = 章节大纲（3–7 章），不是逐页标题罗列：按 eyebrow 的 `NN ·` 前缀归并
    def _chap_key(eb, idx):
        mm = re.match(r'^(\d{1,2})\s*[·・\-—]', (eb or '').strip())
        return mm.group(1).zfill(2) if mm else f'{idx:02d}'

    def _chap_title(eb, title):
        mm = re.match(r'^\d{1,2}\s*[·・\-—]\s*(.+)$', (eb or '').strip())
        return mm.group(1).strip() if mm and mm.group(1).strip() else (title or '')

    chapters, ch_order = {}, []
    for i, p in enumerate(pages, 1):
        key = _chap_key(p.get('eyebrow', ''), i)
        if key not in chapters:
            chapters[key] = {'num': key, 'title': _chap_title(p.get('eyebrow', ''), p['title']),
                             'desc': p.get('eyebrow', ''), 'first': i}
            ch_order.append(key)
    agenda_items = [(f's{chapters[k]["first"]}', chapters[k]['title'], chapters[k]['desc'])
                    for k in ch_order]

    show_agenda = not (mode == 'architecture' and len(pages) <= 4)
    closing_points = [['动作一', '一句话说明。'], ['动作二', '一句话说明。'], ['动作三', '一句话说明。']]

    body = [cover(mode, args.title, args.subtitle, args.meta)]
    if show_agenda:
        body.append(agenda(mode, agenda_items))
    body += html_parts
    body.append(closing(mode, '收尾主张（回应封面问题）', closing_points))
    head = '\n\n'.join(body)

    # 参考资料：只在有真实来源条目时生成；scaffold 不再写「来源 N（替换为真实来源名称）」占位
    # 交付前由内容作者补 model.refs = [[来源名, 时间；口径]…]（真实机构/报告/文档名），再跑 render_from_model
    ref_ids = sorted(set(re.findall(r'class="cite" href="#(ref-\d)"', head)))
    ref_items = []  # 真实来源由内容作者填入；空 = 不生成参考资料节（宁缺毋假）
    content = head
    if ref_items:
        content = head + '\n\n' + refs(mode, ref_items)
    content = content + '\n\n' + footer(args.title, args.subtitle, args.meta)

    assert CONTENT_RE.search(t), f'{tpl_path.name} 缺少 __TOPPPT_CONTENT__ 标记'
    t = CONTENT_RE.sub('<!-- __TOPPPT_CONTENT_START__ -->\n' + content +
                       '\n<!-- __TOPPPT_CONTENT_END__ -->', t, count=1)

    # ③ 顶栏导航与 Agenda 锚点一致（章级，不是逐页标题）
    nav_links = '\n'.join(
        f'      <a href="#s{chapters[k]["first"]}">{esc(chapters[k]["title"][:10])}</a>'
        for k in ch_order[:5])
    assert NAV_RE.search(t), '模板缺少顶栏导航'
    nav_extra = '\n      <a href="#refs">参考资料</a>' if ref_items else ''
    t = NAV_RE.sub(f'<nav class="nav">\n{nav_links}{nav_extra}\n    </nav>', t, count=1)

    # ④ REPORT_MODEL 骨架（与正文一一对应 · 严格 JSON）
    model = {
        'mode': mode, 'style': style, 'theme': theme,
        'title': args.title, 'subtitle': args.subtitle, 'meta': args.meta,
        'agenda': [[chapters[k]['num'], chapters[k]['title'], chapters[k]['desc']]
                   for k in ch_order] if show_agenda else [],
        'sections': model_secs,
        'closing': {'title': '收尾主张（回应封面问题）',
                    'points': [list(x) for x in closing_points]},
    }
    assert MODEL_RE.search(t), f'{tpl_path.name} 缺少 REPORT_MODEL 块'
    t = MODEL_RE.sub('window.REPORT_MODEL = ' + json.dumps(model, ensure_ascii=False, indent=2) + ';', t, count=1)
    assert f'"mode": "{mode}"' in t and f'data-mode="{mode}"' in t, 'mode 注入不一致'
    assert 'g.TopPptHtml = api' in t and 'function slidesXml' in t, '预览运行时缺失（标记块被破坏）'

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        out.write_text(t, encoding='utf-8')
    except OSError as e:
        print(f'错误：输出写入失败 {out}（{e}）', file=sys.stderr)
        return 1
    print(f'已生成骨架：{out}  {len(t)} 字符')
    print(f'  模式 {mode} · 风格 {style} · 主题 {theme} · 内容页 {len(pages)}'
          f'（{"含" if show_agenda else "省略"} Agenda'
          + (f' · 节奏包 {args.preset}' if args.preset else '') + '）')
    print('  页型序列：' + ' → '.join(p['type'] for p in pages))
    print('  布局骨架：' + ' → '.join(PAGE_TO_PRESET.get(p['type'], 'P4') for p in pages))
    print('下一步：')
    print('  1) 按 references/layout-grammar.md 选/核对骨架 P__，再按 playbook §三/§四 填内容（主件+从件+注释层）')
    print('  2) 同步更新 window.REPORT_MODEL（字段见 scripts/model-schema.json；模型字段纯文本，引用写 [n]）')
    print(f'  3) python scripts/validate_report.py "{out}" --strict   → 0/0 才交付')
    return 0


if __name__ == '__main__':
    sys.exit(main())
