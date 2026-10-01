#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TopPPT HTML· HTML 报告质量校验（交付闭环）
用法:
    python validate_report.py <报告.html> [--strict] [--layout-qa] [--json]
    python validate_report.py --help

输出每项 PASS/FAIL，结尾给汇总与结论；任一 FAIL 时退出码为 1（--strict 时 WARN 也计失败）。
--json 以 JSON 输出全部检查结果（供脚本/流水线读取）。
Mode A / presentation + --strict：自动启用 --layout-qa（V 契约/截断/溢出未拆页/半空卡/对齐）；
research / architecture 仍须显式传 --layout-qa（不强制）。
生成流程：生成 → 跑本脚本 → 修复 FAIL → 再跑，直至全部 PASS 才交付。

阈值全部来自单源 scripts/layout-constants.json（checkBudgets / charts / styleAccents / aiFlavor），
本脚本不再内置任何风格色值或预算数字——改阈值只改 JSON。

检查面：
  结构闭合 / 主题风格 / 页面高度模型 / 宽屏翻页 / Agenda（architecture 极简形态可省略） / 粗体 /
  零外链 / 引用与锚点闭环 / 单一强调色 / 内联写死色 / 内容密度 / 单页文字与组件预算 /
  表格行数上限 / 页高溢出估算 / 去AI味 / 图表存在与动效 / 图表 data-chart 登记 / 图表最小尺寸 /
  模式版式特征（含新页型 steps/heatmap/bullet/pyramid/image 与 research/architecture 专属） /
  模型一致性（REPORT_MODEL ↔ 正文） / Exhibit 编号连续 / research so-what 与来源行 /
  强调带约束（band--deep 反相页 ≤ 上限且不作末页） / 待核实标注（.tbd ↔ .tbd-legend/.flagbar） /
  素材图片与配图占位（零外链 + alt + 内联体积 + 版式/比例锁定类对应 + 占位可见标签 + 模型对应） /
  PPTX 预览配套（预览按钮 + 模型 + 运行时，页面无导出按钮） /
  内容级质量（版式节奏连用上限 / 结论条实质与空洞套话 / research 标题含数字或判断词）
"""
import sys
import re
import json
import base64
import hashlib
import html as _html
import unicodedata
from typing import Optional
from html.parser import HTMLParser
from pathlib import Path

# Windows GBK 控制台兜底：强制 UTF-8 输出（含 ↔ 等符号）
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
import checks_html  # noqa: E402  承载正则 / 图表通道 / 多样性 / 组合版式单源

VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta',
        'param', 'source', 'track', 'wbr'}

# ── 单源阈值（scripts/layout-constants.json）────────────────────────────────
_DEFAULTS = {
    'checkBudgets': {
        'presentation': dict(char=1500, unit=8, empty=80, fit=1000, wrap=1400, trow=8),
        'research': dict(char=3200, unit=12, empty=120, fit=2200, wrap=1240, trow=16),
        'architecture': dict(char=600, unit=3, empty=60, fit=600, wrap=1600, trow=6),
    },
    'charts': {'types': [], 'minSize': {}},
    'styleAccents': {},
    'aiFlavor': {'words': []},
    'imageSpec': {},
    'contentQuality': {},
}


def load_constants():
    path = Path(__file__).resolve().parent / 'layout-constants.json'
    try:
        lc = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        print(f'警告: 无法读取单源 {path}（{exc}），使用内置默认阈值。')
        return _DEFAULTS
    for key, fallback in _DEFAULTS.items():
        lc.setdefault(key, fallback)
    return lc


LC = load_constants()
MODE_BUDGETS = LC['checkBudgets']
CHART_TYPES = set(LC['charts'].get('types') or [])
CHART_MIN = LC['charts'].get('minSize') or {}
# 图表多样性预算（治「登记 36 种、实际只用 bar/line/donut」）
CHART_VARIETY = LC['charts'].get('variety') or {}
AI_FLAVOR = LC['aiFlavor'].get('words') or []
STYLE_ACCENTS = {k: {str(h).lower() for h in v}
                 for k, v in (LC['styleAccents'] or {}).items()
                 if not k.startswith('$') and isinstance(v, list)}
ALL_ACCENTS = set().union(*STYLE_ACCENTS.values()) if STYLE_ACCENTS else set()
# 图表登记四元组（charts.registry）与信息图页型（数据可追溯策略核对）
CHART_REG = {k: v for k, v in (LC['charts'].get('registry') or {}).items()
             if not str(k).startswith('$')}
INFO_PAGE_TYPES = {'sankey', 'treemap', 'boxplot', 'network', 'marimekko', 'streamgraph'}
# 素材图片规格与配图占位约定（单源 layout-constants.json imageSpec）
IMAGE_SPEC = LC.get('imageSpec') or {}
IMAGE_LAYOUTS = set(IMAGE_SPEC.get('layouts') or ['full', 'half', 'bleed', 'grid', 'compare', 'wall'])
IMAGE_MULTI_LAYOUTS = set(IMAGE_SPEC.get('multiLayouts') or ['grid', 'compare', 'wall'])
IMAGE_FIT = set(IMAGE_SPEC.get('fitEnum') or ['cover', 'contain'])
IMAGE_MAX_PER_PAGE = int(IMAGE_SPEC.get('maxPerPage') or 6)
IMAGE_MAX_INLINE = int(IMAGE_SPEC.get('maxInlineBytes') or 1572864)
IMAGE_MAX_TOTAL = int(IMAGE_SPEC.get('maxTotalInlineBytes') or 8388608)

AGENDA_SINGLE_MAX = int((((LC.get("contentQuality") or {}).get("agenda") or {}).get("singleMax")) or 8)  # 超过则须 agenda--2col
# 页高估算参数（单源 layout-constants.pageHeightEstimate）
_HE = LC.get('pageHeightEstimate') or {}
SCREEN_BUDGET_PX = int(_HE.get('screenBudgetPx') or 1000)
WRAP_INSET_PX = int(_HE.get('wrapInsetPx') or 112)
SHEAD_PX = int(_HE.get('sheadPx') or 190)
UNIT_PX = int(_HE.get('unitPx') or 170)
LINE_FACTOR = float(_HE.get('lineFactor') or 1.65)
STRUCT_PAGE_IDS = ('refs', 'appendix')


class Struct(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.err, self.mis = [], [], []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        else:
            try:
                i = len(self.stack) - 1 - self.stack[::-1].index(tag)
                self.mis.extend(self.stack[i:])
                self.stack = self.stack[:i]
            except ValueError:
                self.err.append(tag)


def _plain(html):
    return re.sub(r'<[^>]+>', ' ', html)


def _bands(txt):
    parts = re.split(r'(?=<section class="band)', txt)
    return [p for p in parts if p.startswith('<section class="band')]


def _band_units(b):
    """承载组件数：卡/指标/图/表 + 列表组/结构/步骤/媒体/矩阵（组合版式与 underfill 同口径）。"""
    return (len(re.findall(r'class="(?:card|metric)[\s"]', b)) +
            len(re.findall(r'class="fig[\s"]', b)) +
            len(re.findall(r'class="tbl-wrap', b)) +
            len(re.findall(r'class="(?:arch|lane|steps|heat|bul|pyr|media|matrix|exhibit)[\s"]', b)) +
            len(re.findall(r'class="ul[\s"]', b)) +
            len(re.findall(r'class="cols-[23]', b)))


def _band_heavy_units(b):
    """页高估算用「重承载行数」：卡/指标按栅格列数折行；图/表/结构各计 1 行级。"""
    cards = len(re.findall(r'class="(?:card|metric)[\s"]', b))
    figs = len(re.findall(r'class="fig[\s"]', b))
    tables = len(re.findall(r'class="tbl-wrap', b))
    structs = len(re.findall(r'class="(?:arch|lane|media|heat|exhibit)[\s"]', b))
    if re.search(r'class="[^"]*\bg-4\b', b):
        cols = 4
    elif re.search(r'class="[^"]*\bg-3\b', b):
        cols = 3
    elif re.search(r'class="[^"]*\b(?:g-2|g-side|g-hero|g-half)\b', b):
        cols = 2
    else:
        cols = 1
    card_rows = (cards + cols - 1) // cols if cards else 0
    return card_rows + figs + tables + structs


def _check_charts(txt, chk):
    """图表：存在性 / data-chart 登记 / 动效 / 最小尺寸。"""
    svgs = re.findall(r'<svg\b[^>]*>', txt)
    chart_tags = [t for t in svgs if 'class="chart' in t or "class='chart" in t or 'data-chart' in t]
    chk("含内联 SVG 图表/图形", len(svgs) >= 1, f"{len(svgs)} 个", level="WARN")
    if not chart_tags:
        return

    untyped = [t for t in chart_tags if 'data-chart' not in t]
    chk("图表 svg 均有 data-chart 类型标记", not untyped,
        f"{len(untyped)} 个未标记", level="WARN")

    # data-chart 类型须在登记表内（layout-constants.json charts.types）
    unknown = []
    if CHART_TYPES:
        for t in chart_tags:
            m = re.search(r'data-chart="([^"]+)"', t)
            if m and m.group(1) not in CHART_TYPES:
                unknown.append(m.group(1))
    chk("图表类型在登记表内（layout-constants.json charts.types）", not unknown,
        f"未登记: {sorted(set(unknown))}", level="WARN")

    has_io = 'IntersectionObserver' in txt
    has_anim = 'data-anim' in txt or 'data-draw' in txt or 'data-sweep' in txt or 'data-count' in txt
    chk("图表动效（IntersectionObserver + data-anim/draw/sweep/count）",
        has_io and has_anim,
        "" if (has_io and has_anim) else f"IO={'有' if has_io else '无'} anim={'有' if has_anim else '无'}",
        level="WARN")

    too_small, small_note = [], []
    for t in chart_tags:
        m = re.search(r'data-chart="([^"]+)"', t)
        ctype = m.group(1) if m else None
        rule = CHART_MIN.get(ctype, {}) if ctype else {}
        wm = re.search(r'style="[^"]*?width:\s*(\d+(?:\.\d+)?)px', t)
        vb = re.search(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"', t)
        if wm and rule.get('pxWidthMin'):
            w = float(wm.group(1))
            if w < rule['pxWidthMin']:
                too_small.append(f"{ctype} 宽{w:.0f}px<{rule['pxWidthMin']}px")
        if vb and rule.get('vbHeightMin'):
            h = float(vb.group(2))
            if h < rule['vbHeightMin']:
                small_note.append(f"{ctype} viewBox高{h:.0f}<{rule['vbHeightMin']}")
    chk("图表最小尺寸·硬下限（环形/雷达/仪表盘显示宽）", not too_small,
        "; ".join(too_small) if too_small else "")
    chk("图表最小尺寸·建议（通宽图 viewBox 高）", not small_note,
        "; ".join(small_note) if small_note else "", level="WARN")

    # R5：PPTX 还原度——low 图型在 PPTX 显著退化，仅提示不卡门禁（HTML 交付合法；
    # PPTX 交付时在选型决策树里改 bar/line/hbar 或 dataTable=inline）
    fidelity_map = (LC.get('charts') or {}).get('fidelityMap') or {}
    if fidelity_map:
        low_used = []
        for t in chart_tags:
            m = re.search(r'data-chart="([^"]+)"', t)
            if m and fidelity_map.get(m.group(1)) == 'low':
                low_used.append(m.group(1))
        if low_used:
            chk("图表 PPTX 还原度提示（low 图型 PPTX 会退化）", True,
                f"低还原度: {sorted(set(low_used))}——HTML 合法；PPTX 建议改 bar/line/hbar 或 dataTable=inline",
                level="WARN")


CARRIERS = checks_html.CARRIERS  # 单源 scripts/checks_html.py


def _check_chart_variety(txt, chk, mode):
    """图表与版式多样性（阈值单源 charts.variety；判定逻辑 checks_html）。

    多样性仍是特性：全部 data-chart（含 advanced）计入下限——用 advanced 不罚。
    preferCoreFirst：核图多样性不足却靠 advanced 撑场时 WARN（勿凑下限）。
    禁反模式由 layout-qa / sizeByComplexity / CHART_SKEW 另检。
    """
    v = CHART_VARIETY
    if not v:
        return
    per_page = checks_html.chart_types_per_page(txt)
    used = [t for ts in per_page for t in ts]
    if not used:
        return
    distinct = sorted(set(used))
    n_chart_pages = len([1 for ts in per_page if ts])

    floor = checks_html.variety_floor(mode, n_chart_pages, v)
    # advanced 与核图一并计入 distinct（不因用 advanced 受罚）
    chk("图表多样性（全篇不同 data-chart 类型数）", len(distinct) >= floor,
        f"{len(distinct)} 种 / 下限 {floor}（{n_chart_pages} 个图表页）: {distinct}")
    # preferCoreFirst WARN 仅 A/B：C 架构以结构/甘特等 advanced 为主属正常，不噪音
    if mode in ('presentation', 'research'):
        pref = checks_html.variety_core_preference(used, v)
        if pref:
            chk("图表多样性·核图优先（preferCoreFirst）", False, pref, level="WARN")

    if v.get('noRepeatAdjacent'):
        adj = checks_html.adjacent_same_type(per_page)
        chk("图表不连续同型（相邻图表页不得同 data-chart）", not adj,
            "; ".join(adj[:3]) if adj else "", level="WARN")

    ratio = checks_html.composite_required(mode, v)
    if ratio > 0:
        multi, n_content = checks_html.composite_pages(txt)
        need = max(1, int(n_content * ratio))
        chk("组合版式（内容页含 ≥2 种承载类型的比例）", multi >= need,
            f"{multi}/{n_content} 页（下限 {need}）——单件页是例外不是默认",
            level="WARN")


def _check_page_model(txt, chk, mode):
    """页面高度模型（每页高度稳定）：所有 .band 至少一屏高，长结构页显式 --flow 退出。"""
    has_model = ('--band-min' in txt) or ('calc(100svh - var(--bar-h))' in txt) or \
                ('min-height:calc(100vh - var(--bar-h))' in txt)
    chk("页面高度模型（--band-min / 一屏最小高度）", has_model,
        "缺少每页一屏的 min-height 机制（见 design-system.md §1c）")
    bands = _bands(txt)
    if not bands:
        return
    # 固定页高页（非 --flow）应占多数；长结构页才允许 flow
    flow_pages = []
    for i, b in enumerate(bands, 1):
        if 'band--flow' in b[:220]:
            flow_pages.append(i)
    bad_flow = []
    for i in flow_pages:
        b = bands[i - 1]
        if not any(f'id="{pid}"' in b for pid in STRUCT_PAGE_IDS):
            bad_flow.append(f"第{i}页")
    chk("band--flow 仅用于长结构页（参考资料/附录）", not bad_flow,
        f"{bad_flow} 使用 --flow 但非结构页（应改用默认一屏页）" if bad_flow else "", level="WARN")


def _check_bands(txt, chk, mode="presentation"):
    """单页预算与布局：文字量/组件数（防塞爆）· 过空页 · 页高溢出估算 · 混排对齐。"""
    B = MODE_BUDGETS.get(mode, MODE_BUDGETS['presentation'])
    bands = _bands(txt)
    over_chars, over_units, too_empty, fit_overload = [], [], [], []
    for i, b in enumerate(bands, 1):
        if 'id="refs"' in b or 'id="appendix"' in b:
            continue
        b_clean = re.sub(r'<script\b[\s\S]*?</script>', ' ', b)
        b_clean = re.sub(r'<style\b[\s\S]*?</style>', ' ', b_clean)
        plain_len = len(_plain(b_clean).strip())
        units = _band_units(b)
        if plain_len > B["char"]:
            over_chars.append(f"第{i}页 {plain_len}字")
        if units > B["unit"]:
            over_units.append(f"第{i}页 {units}个")
        head_tag = b[:220]
        is_fit = 'band--fit' in head_tag
        is_deep = 'band--deep' in head_tag
        if is_fit and plain_len > B["fit"]:
            fit_overload.append(f"第{i}页 {plain_len}字")
        if (not is_fit and not is_deep and units == 0 and plain_len < B["empty"]):
            too_empty.append(f"第{i}页 {plain_len}字")
    chk(f"单页文字量 ≤ {B['char']} 字（{mode} 模式 · 防溢出）", not over_chars,
        "; ".join(over_chars) if over_chars else "", level="WARN")
    chk(f"单页并列单元 ≤ {B['unit']} 个（{mode} 模式 · 防塞爆）", not over_units,
        "; ".join(over_units) if over_units else "", level="WARN")
    # v9：过空页升为 FAIL（截图级「只有标题」缺陷不得假过）
    chk(f"无过空页（{mode} 模式 · 普通页 ≥{B['empty']} 字或有组件；防大面积留白）", not too_empty,
        "; ".join(too_empty) if too_empty else "")
    chk(f"满屏居中页 band--fit 内容 ≤ {B['fit']} 字（{mode} 模式 · 防垂直溢出）", not fit_overload,
        "; ".join(fit_overload) if fit_overload else "", level="WARN")

    # 页高溢出静态估算：字数×行高 + 组件固定高 vs 一屏预算（参数单源 pageHeightEstimate / checkBudgets）。
    # 固定页高页（无 --flow）超预算即 FAIL——这是"每页高度稳定"的核心硬门禁。
    fs_px = int(B.get('bodyPx') or 17)
    wrap_px = int(B.get('wrap') or 1400) - WRAP_INSET_PX
    cpl = max(10, int(wrap_px / fs_px))
    est_over = []
    for i, b in enumerate(bands, 1):
        if 'id="refs"' in b or 'id="appendix"' in b:
            continue
        if 'band--flow' in b[:220]:
            continue
        b_clean = re.sub(r'<script\b[\s\S]*?</script>', ' ', b)
        b_clean = re.sub(r'<style\b[\s\S]*?</style>', ' ', b_clean)
        plen = len(_plain(b_clean).strip())
        u = _band_heavy_units(b)
        est_h = plen / cpl * fs_px * LINE_FACTOR + u * UNIT_PX + SHEAD_PX
        # 静态估算容差 8%（真值以浏览器为准；轻微超出仍按 FAIL 会误伤密排页）
        if est_h > SCREEN_BUDGET_PX * 1.08:
            est_over.append(f"第{i}页≈{est_h:.0f}px")
    chk(f"页高溢出估算（字×行高+组件 ≤ ~{SCREEN_BUDGET_PX}px/屏 · {mode}）", not est_over,
        ("; ".join(est_over) + "（按「重构承载→拆页/分章→换形态→有限 fontShrink」；禁静默截断；或长结构页加 band--flow）")
        if est_over else "")

    bad_grids = 0
    for m in re.finditer(r'<div class="grid[^"]*"([^>]*)>', txt):
        attrs = m.group(1)
        sec_end = txt.find('</section>', m.end())
        ahead = txt[m.end(): sec_end if sec_end != -1 else m.end() + 4000]
        if 'class="fig' in ahead and 'class="card' in ahead:
            aligned = ('align-items' in attrs or
                       re.search(r'\ba-(c|start|end)\b', m.group(0)))
            if not aligned:
                bad_grids += 1
    chk("混排栅格（图+卡）显式对齐（a-start/a-c 或 align-items）", bad_grids == 0,
        f"{bad_grids} 处未对齐" if bad_grids else "", level="WARN")


def _icon_pack_names():
    """图标包合法名集合（assets/icons/index.json）；读不到时返回 None（跳过存在性检查）。"""
    try:
        idx = json.loads((Path(__file__).resolve().parent.parent / 'assets' / 'icons'
                          / 'index.json').read_text(encoding='utf-8'))
        return set((idx.get('icons') or {}).keys())
    except OSError:
        return None


def _check_icon_refs(txt, chk):
    """图标引用存在性：data-icon / icon: 标记引用了包外图标 → WARN（不 FAIL）。"""
    names = _icon_pack_names()
    if names is None:
        return
    # 只扫渲染正文：去掉 script/style/注释与嵌入模型 JSON，避免代码与文档示例误报
    body = re.sub(r'<script[\s\S]*?</script>', '', txt, flags=re.I)
    body = re.sub(r'<style[\s\S]*?</style>', '', body, flags=re.I)
    body = re.sub(r'<!--[\s\S]*?-->', '', body)
    body = re.sub(r'window\.REPORT_MODEL\s*=\s*\{[\s\S]*?\n\};', '', body)
    refs = set(re.findall(r'data-icon="([^"]+)"', body))
    refs |= set(re.findall(r'icon:([\u4e00-\u9fa5A-Za-z0-9_-]+)', body))
    # 排除 hydrate 占位与 CSS 类名噪声：只看真实引用上下文
    bad = sorted(r for r in refs if r not in names and not r.startswith('{{'))
    chk("图标引用存在（assets/icons 包内）", not bad,
        f"未知图标: {', '.join(bad[:6])}{'…' if len(bad) > 6 else ''}（{len(bad)} 个）" if bad else "",
        level="WARN")


# ── 内容覆盖率（0.2.0）：版式不得以丢文字为代价美化 ──
# 口径：REPORT_MODEL 可见文本串（去重、归一化）有多少字符能在渲染后 HTML 可见文本中找到；
# <95% → WARN（只报告，不 FAIL；长串按 8 字窗口部分计分，避免数字重排/截断误杀）。
_COV_SKIP_KEYS = {
    # 元字段（不渲染为正文）
    "style", "theme", "mode", "type", "variant", "icon", "color", "colors",
    "src", "href", "id", "layout", "datatable", "dataTable", "font", "fontface",
    "exhibitno", "exhibitNo", "columns", "max", "min", "unit", "ratio", "fit",
    "align", "width", "height", "placeholder", "alt", "target", "rel", "dir",
    "lang", "charset", "defer", "async", "media",
    "hint",  # 搭建期给智能体的指令（如 image.hint），不是读者正文
}
_COV_URL_RE = re.compile(r'^(https?://|www\.|data:|#)', re.I)
_COV_COLOR_RE = re.compile(r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')
# 纯小写 ASCII 标识符（无空格/CJK/大写）：渲染器语义 flag（如 "focus"），不是正文
_COV_FLAG_RE = re.compile(r'^[a-z][a-z0-9_-]*$')
# 信息图页型（r_info 故意留"按 infographics 规格绘制"占位、PPTX 走形状通道）：
# 其 chart 数据子树不计入覆盖率（数据在模型与 PPTX 中完整，仅 HTML 待定制信息图）
_COV_INFO_TYPES = {'sankey', 'treemap', 'boxplot', 'network', 'marimekko', 'streamgraph'}
_COV_INFO_DATA_KEYS = {'chart', 'labels', 'values', 'groups', 'nodes', 'links', 'edges', 'data',
                       'series', 'dataset', 'cols', 'rows', 'cells'}
_COV_MIN_RATIO = 0.95  # 覆盖率下限（layout-constants qualityGates.contentCoverage 可覆写）


def _norm_cov(s: str) -> str:
    s = unicodedata.normalize('NFKC', s)
    s = re.sub(r'(?<=\d),(?=\d)', '', s)  # 千分位 1,000 → 1000（中文逗号保留）
    s = re.sub(r'\s+', '', s)
    # 标点不计入：内容在、标点异（： vs 无、（） vs 无）不算丢失；比的是信息不是排印
    s = ''.join(c for c in s if not unicodedata.category(c).startswith('P'))
    return s


def _model_cov_strings(model) -> list:
    """从 REPORT_MODEL 递归抽取候选正文串（去重、保序）。"""
    out, seen = [], set()

    def walk(node, skip_sub=False):
        if isinstance(node, dict):
            # 信息图页型：chart 数据子树是故意占位（r_info），不计入
            info_data = isinstance(node.get('type'), str) and node.get('type').lower() in _COV_INFO_TYPES
            for k, v in node.items():
                kl = str(k).lower()
                if kl in _COV_SKIP_KEYS or str(k).startswith('data-'):
                    continue
                if info_data and kl in _COV_INFO_DATA_KEYS:
                    continue
                walk(v)
        elif isinstance(node, (list, tuple)):
            for v in node:
                walk(v)
        elif isinstance(node, str):
            t = node.strip()
            if len(t) < 4 or _COV_URL_RE.match(t) or _COV_COLOR_RE.match(t):
                return
            if _COV_FLAG_RE.match(t):
                return  # 渲染器语义 flag（如 focus），非正文
            if t not in seen:
                seen.add(t)
                out.append(t)

    walk(model)
    return out


def _visible_cov_text(txt: str) -> str:
    """渲染后可见文本：剔 script（含 REPORT_MODEL JSON 本体）/style/注释/标签后归一化。"""
    t = re.sub(r'<script[\s\S]*?</script>', '', txt, flags=re.I)
    t = re.sub(r'<style[\s\S]*?</style>', '', t, flags=re.I)
    t = re.sub(r'<!--[\s\S]*?-->', '', t)
    t = re.sub(r'<[^>]+>', '', t)
    return _norm_cov(_html.unescape(t))


def _cov_credit(cand: str, rendered: str) -> float:
    """候选串的字符计分：整串命中按全长；否则按 8 字窗口命中率折算。"""
    n = _norm_cov(cand)
    if not n:
        return 0.0
    if n in rendered:
        return float(len(n))
    if len(n) <= 12:
        return 0.0
    win, hits, total = 8, 0, 0
    for i in range(0, len(n), win):
        total += 1
        if n[i:i + win] in rendered:
            hits += 1
    return len(n) * hits / total if total else 0.0


def _check_content_coverage(txt, chk, model) -> None:
    """模型文本 → 渲染文本覆盖率（只 WARN）。"""
    if not isinstance(model, dict):
        return
    try:
        min_ratio = float((load_constants().get("qualityGates") or {}).get("contentCoverage")
                          or _COV_MIN_RATIO)
    except Exception:
        min_ratio = _COV_MIN_RATIO
    cands = _model_cov_strings(model)
    if not cands:
        return
    rendered = _visible_cov_text(txt)
    total = sum(len(_norm_cov(c)) for c in cands)
    if not total:
        return
    miss = []
    got = 0.0
    for c in cands:
        cr = _cov_credit(c, rendered)
        got += cr
        if cr < len(_norm_cov(c)) * 0.5:
            miss.append(c[:24])
    ratio = got / total
    chk(f"内容覆盖率（模型文本→渲染文本 ≥{min_ratio:.0%}）", ratio >= min_ratio,
        f"覆盖率 {ratio:.1%}（{len(cands)} 串），疑似丢失: {'；'.join(miss[:3])}" if ratio < min_ratio else "",
        level="WARN")


def _check_icons(txt, chk):
    """图标使用：长报告不应全文无图标；含 ≥2 张卡的内容页应有 .card__ico（WARN）。"""
    if len(_bands(txt)) < 6:
        return
    has_icon = ('ul--ico' in txt or 'metric__ico' in txt or
                re.search(r'card__ico"[^>]*>\s*<svg', txt) or
                re.search(r'card__ico">\s*<svg', txt))
    chk("长报告（≥6页）要点卡/关键列表有图标", bool(has_icon),
        "全文未用图标（见 icons.md 使用准则）", level="WARN")
    # Soft gate: points/cards pages with ≥2 .card and zero .card__ico
    bare_card_pages = 0
    for m in re.finditer(r'<section\b([^>]*)>([\s\S]*?)</section>', txt):
        attrs, body = m.group(1), m.group(2)
        pt = re.search(r'data-page-type="([^"]+)"', attrs)
        page_type = (pt.group(1) if pt else '') or ''
        if page_type not in ('points', 'cards', 'split', 'comparison'):
            # Also catch sections that clearly use card grids
            if body.count('class="card') + body.count("class='card") < 2:
                continue
        n_cards = len(re.findall(r'class="[^"]*\bcard\b', body))
        if n_cards < 2:
            continue
        if 'card__ico' not in body:
            bare_card_pages += 1
    chk("要点/卡片页（≥2 卡）含 .card__ico", bare_card_pages == 0,
        f"{bare_card_pages} 页有多卡但无图标（见 icons.md 四正当位置）" if bare_card_pages else "",
        level="WARN")


def _check_table_rows(txt, chk, mode="presentation"):
    """表格行数上限（research 密表 ≤16 / presentation ≤8 / architecture ≤6；宁拆勿挤）。"""
    B = MODE_BUDGETS.get(mode, MODE_BUDGETS['presentation'])
    max_rows = B['trow']
    over = []
    for i, m in enumerate(re.finditer(r'<tbody>([\s\S]*?)</tbody>', txt), 1):
        n = len(re.findall(r'<tr', m.group(1)))
        if n > max_rows:
            over.append(f"表{i} {n}行")
    chk(f"表格行数 ≤ {max_rows} 行（{mode} 模式 · 宁拆勿挤）", not over,
        "; ".join(over) if over else "", level="WARN")


def _check_mode_layouts(txt, chk, mode):
    """模式版式特征：三模式独立体系，各自应有标志性组件。"""
    if mode == 'research':
        has = ('class="cols-2' in txt or 'class="exhibit' in txt or
               'class="cols-3' in txt or 'class="matrix' in txt)
        chk("research 版式特征（cols-2/cols-3/exhibit/matrix 至少一处）", has,
            "未见研究模式标志性组件", level="WARN")
    elif mode == 'architecture':
        has = ('class="arch' in txt or 'class="lane' in txt)
        chk("architecture 版式特征（arch/lane 至少一处）", has,
            "未见架构模式标志性组件", level="WARN")


# 页型 → 正文标志性版式特征（正则；模型-正文同源抽查，见 `components.md` §46/§46b）
TYPE_FEATURE = {
    'steps': r'class="[^"]*\bsteps\b',
    'heatmap': r'class="[^"]*\bheat\b',
    'bullet': r'class="[^"]*\bbul\b',
    'pyramid': r'class="[^"]*\bpyr\b',
    'image': r'class="[^"]*\bmedia\b|<img\b',
    'matrix': r'class="[^"]*\bmatrix\b',
    'exhibit': r'class="[^"]*\bexhibit\b',
    'twocol': r'class="[^"]*\bcols-2\b',
    'threecol': r'class="[^"]*\bcols-3\b',
    'halftable': r'class="[^"]*\bg-half\b',
    'split': r'class="[^"]*\bg-side\b',
    'diagram': r'class="[^"]*\barch\b',
    'lane': r'class="[^"]*\blane\b',
    'timeline': r'class="[^"]*\btl\b',
    'comparison': r'class="[^"]*\bg-half\b',
    'quote': r'band--accent|band--deep',
    'donut': r'data-chart="donut"',
    # 复杂信息图页型：正文以内联 SVG 承载（data-chart 登记与 charts.registry 同源）
    'sankey': r'data-chart="sankey"',
    'treemap': r'data-chart="treemap"',
    'boxplot': r'data-chart="boxplot"',
    'network': r'data-chart="network"',
    'marimekko': r'data-chart="marimekko"',
    'streamgraph': r'data-chart="streamgraph"',
}


def _check_type_features(txt, chk, model):
    """模型声明的页型应在正文找到对应版式组件（防"模型填了页型但正文用旧版式"）。"""
    if not model:
        return
    missing = []
    for sec in (model.get('sections') or []):
        t = (sec.get('type') or 'points')
        feat = TYPE_FEATURE.get(t)
        if feat and not re.search(feat, txt):
            missing.append(t)
    chk("模型页型 ↔ 正文版式组件对应", not missing,
        f"{len(missing)} 处: {missing[:4]}" if missing else "", level="WARN")


RUNTIME_SHA_RE = re.compile(r'/\* __TOPPPT_RUNTIME_SHA__:([0-9a-f]{16}) \*/')


def _pptx_export_source_sha() -> Optional[str]:
    """当前技能包 assets/pptx-export.js 的 sha256[:16]（与 sync_runtime 注入口径一致）。"""
    pe = Path(__file__).resolve().parent.parent / 'assets' / 'pptx-export.js'
    try:
        body = pe.read_text(encoding='utf-8').rstrip('\n')
    except OSError:
        return None
    return hashlib.sha256(body.encode('utf-8')).hexdigest()[:16]


def _check_pptx_export(txt, chk):
    """PPTX 预览配套：有预览按钮就必须有内容模型 + 预览运行时；页面不得残留导出按钮。
    另：内联运行时必须带 __TOPPPT_RUNTIME_SHA__ 且与当前 pptx-export.js 同源。"""
    has_btn = 'id="pptPreviewBtn"' in txt
    has_model = 'REPORT_MODEL' in txt
    has_runtime = ('g.TopPptHtml = api' in txt) and ('function slidesXml' in txt)
    if has_btn:
        chk("PPTX 预览按钮配套（REPORT_MODEL + 预览运行时）",
            has_model and has_runtime,
            f"model={'有' if has_model else '无'} runtime={'有' if has_runtime else '无'}")
    else:
        chk("含 PPTX 预览按钮与内容模型（建议保留）",
            has_model and has_runtime, "未集成预览按钮/模型", level="WARN")
    # 同版本戳：有运行时块时强制核对（缺戳或漂移 = FAIL）
    if has_runtime or '/* __TOPPPT_RUNTIME_START__ */' in txt:
        m = RUNTIME_SHA_RE.search(txt)
        expected = _pptx_export_source_sha()
        if not m:
            chk("运行时同版本戳（__TOPPPT_RUNTIME_SHA__）", False,
                "内联运行时缺戳；请跑 scripts/sync_runtime.py")
        elif expected is None:
            chk("运行时同版本戳（__TOPPPT_RUNTIME_SHA__）", False,
                "无法读取 assets/pptx-export.js 计算源哈希")
        else:
            got = m.group(1)
            chk("运行时同版本戳（__TOPPPT_RUNTIME_SHA__）", got == expected,
                f"stamp={got} ≠ source={expected}（模板未 sync 或源已改）")
    chk("页面无 PPTX 导出按钮（仅预览 + 提示词）",
        'id="pptxBtn"' not in txt and 'id="pptDownload"' not in txt,
        "残留导出按钮 pptxBtn/pptDownload", level="WARN")


def _extract_model(txt):
    m = re.search(r'window\.REPORT_MODEL\s*=\s*', txt)
    if not m:
        return None, "未找到 window.REPORT_MODEL（PPTX 双通道导出将不可用）"
    try:
        model, _end = json.JSONDecoder().raw_decode(txt[m.end():])
        return model, None
    except json.JSONDecodeError as e:
        return None, f"REPORT_MODEL 不是合法 JSON: {e}（必须双引号/无尾逗号/无注释）"


def _chart_channel(chart_type) -> str:
    """图表类型 → 交付通道（native / shape），与 charts.registry 同源（checks_html）。"""
    return checks_html.chart_channel(chart_type, CHART_REG)


def _chart_datatable_mode(chart: dict) -> str:
    """数据表策略：图表级 > 登记表默认（appendix 收敛为 inline）。"""
    return checks_html.chart_datatable_mode(chart, CHART_REG)


def _check_chart_datatable(chk, model) -> None:
    """数据可追溯：非原生（形状通道）图表与信息图页型的 dataTable 不得为 off。

    与 validate_pptx.py 的 MODEL_CHART_DATATABLE 同源，但提前到 HTML 阶段暴露——
    避免生成完 PPTX 才被拦（数据表策略是模型层决定，HTML 阶段即可判定）。
    """
    bad: list[str] = []
    for sec in (model.get('sections') or []):
        if not isinstance(sec, dict):
            continue
        st = sec.get('type') or ''
        if st in INFO_PAGE_TYPES:
            mode = str(((sec.get('chart') or {}).get('dataTable')) or 'notes').lower()
            if mode == 'off':
                bad.append(f'{st} 页信息图 dataTable=off')
            continue
        charts = []
        if st in ('bar', 'donut', 'exhibit', 'halftable'):
            c = sec.get('chart') or {}
            if isinstance(c, dict) and c.get('labels') and c.get('values'):
                charts.append(c)
        elif st == 'split':
            # 双区组合页：左/右两侧各可能是图表（left 缺省 points、right 缺省 bar）
            for side, dflt in (('left', 'points'), ('right', 'bar')):
                pane = sec.get(side) or {}
                if not isinstance(pane, dict):
                    continue
                if (pane.get('type') or dflt) in ('table', 'image', 'points'):
                    continue
                if pane.get('labels') and pane.get('values'):
                    charts.append(pane)
        for chart in charts:
            if _chart_channel(chart.get('type')) == 'shape' and _chart_datatable_mode(chart) == 'off':
                bad.append(f"{st} 页 {chart.get('type')} 图表 dataTable=off")
    chk("图表数据表策略（非原生图表不得 off，保证数据可追溯）", not bad,
        '；'.join(bad[:3]) if bad else "", level="WARN")


def _check_model_consistency(txt, chk, mode, style):
    """模型-正文一致性：JSON 合法 / mode·style·theme 一致 / 章节标题抽查 / agenda / 页数。"""
    model, err = _extract_model(txt)
    if err:
        chk("REPORT_MODEL 存在且为合法 JSON", False, err)
        return None
    chk("REPORT_MODEL 存在且为合法 JSON", True)
    mmode = model.get('mode')
    chk("REPORT_MODEL.mode 与 data-mode 一致", mmode == mode,
        f"model={mmode!r} 页面={mode!r}")
    mstyle = model.get('style')
    chk("REPORT_MODEL.style 与 data-style 一致", mstyle == style,
        f"model={mstyle!r} 页面={style!r}", level="WARN")
    mtheme = model.get('theme') or 'light'
    html_theme_m = re.search(r'<html[^>]*data-theme="([^"]+)"', txt)
    html_theme = html_theme_m.group(1) if html_theme_m else 'light'
    chk("REPORT_MODEL.theme 与 data-theme 一致（未声明默认 light）",
        mtheme in ('light', 'dark') and mtheme == html_theme,
        f"model={mtheme!r} 页面={html_theme!r}", level="WARN")
    secs = model.get('sections') or []
    chk("REPORT_MODEL.sections 非空（每章一页模型）", len(secs) >= 1,
        f"{len(secs)} 页", level="WARN")
    _check_chart_datatable(chk, model)
    plain = _plain(txt)
    missing = [str(s.get('title'))[:14] for s in secs
               if not s.get('title') or str(s.get('title')) not in plain]
    chk("模型章节标题均出现于正文（模型-正文同源）", not missing,
        f"{len(missing)} 个缺失: {missing[:3]}" if missing else "", level="WARN")
    n_html = txt.count('class="agenda__a"')
    n_model = len(model.get('agenda') or [])
    if n_html and n_model:
        chk("模型 agenda 条数与正文一致", n_html == n_model,
            f"model={n_model} 正文={n_html}", level="WARN")
    n_bands = len(_bands(txt))
    lo, hi = len(secs) + 3, len(secs) + 7
    chk("页数粗匹配（正文 band ≈ sections + 结构页）", lo <= n_bands <= hi,
        f"正文 {n_bands} 页 vs 模型 {len(secs)}+{lo - len(secs)}~{hi - len(secs)}", level="WARN")
    return model


def _check_anchors(txt, chk):
    """锚点闭环：Agenda / 导航 / 正文内部链接指向的 id 必须存在，且 id 全篇唯一。
    （重复 id 会让锚点跳到错误的页，且 HTML 规范不允许——硬拦。）"""
    # 只看正文：内联运行时/UI 脚本里有 `id="' + nid() + '"` 这类拼接，不能算重复 id
    body = re.sub(r'<script\b[\s\S]*?</script>', '', txt, flags=re.I)
    all_ids = re.findall(r'\sid="([^"]+)"', body)
    ids = set(all_ids)
    dup = sorted({i for i in all_ids if all_ids.count(i) > 1})
    chk("id 全篇唯一（无重复 id）", not dup,
        f"重复 id {dup[:5]}（锚点会跳到错误的页）" if dup else "")
    bad = []
    for href in set(re.findall(r'href="#([^"]+)"', body)):
        if href and href not in ids:
            bad.append('#' + href)
    chk("内部锚点闭环（agenda/nav/正文链接均有对应 id）", not bad,
        f"悬空锚点 {sorted(bad)[:5]}" if bad else "")


def _check_exhibits(txt, chk, mode):
    """Exhibit 编号体系：每个 .exhibit 框都有编号，且全篇连续 1..N 无跳号无重复。"""
    nos = [int(n) for n in re.findall(
        r'class="exhibit__no"[^>]*>\s*Exhibit\s*(\d+)', txt, re.I)]
    n_frame = len(re.findall(r'class="exhibit[\s"]', txt))
    if not nos:
        if mode == 'research':
            chk("Exhibit 编号体系（research 深报告建议建立）", False,
                "全文无 Exhibit 编号图表框", level="WARN")
        return
    # 只校验已编号者的连续性会漏掉「漏标编号的 exhibit 框」——先核框数再核编号。
    chk(f"Exhibit 框均已编号（{n_frame} 框）", n_frame == len(nos),
        f"{n_frame} 个 .exhibit 框但只有 {len(nos)} 个 .exhibit__no 编号" if n_frame != len(nos) else "")
    expected = list(range(1, len(nos) + 1))
    chk(f"Exhibit 编号连续（1..{len(nos)} 无跳号无重复）", sorted(nos) == expected,
        f"读到 {nos}")


def _check_research_extras(txt, chk, mode):
    """research 模式：so-what 连续性（>3 页无结论条）与 Exhibit 来源行。"""
    if mode != 'research':
        return
    bands = _bands(txt)
    streak = max_streak = 0
    for i, b in enumerate(bands, 1):
        if i <= 2 or 'id="agenda"' in b or 'id="refs"' in b:
            continue
        if 'class="sowhat' in b or 'class="note' in b:
            streak = 0
        else:
            streak += 1
            max_streak = max(max_streak, streak)
    chk("so-what 连续性（连续 ≤3 页无结论条）", max_streak <= 3,
        f"连续 {max_streak} 页无 .sowhat/.note" if max_streak > 3 else "", level="WARN")
    n_ex = len(re.findall(r'class="exhibit[\s"]', txt))
    n_src = txt.count('class="exhibit__src"')
    chk(f"Exhibit 图表框均有来源行（{n_ex} 框）", n_ex == n_src,
        f"{n_ex - n_src} 个缺 .exhibit__src" if n_ex != n_src else "", level="WARN")


def _check_emphasis(txt, chk):
    """强调带约束：band--deep 是反相强调页（浅色主题下渲染为深色）——
    全文受限使用，且不得作末页，否则浅色模式末尾会出现深色页（用户核心诉求）。"""
    em = LC.get('emphasis') or {}
    max_deep = em.get('deepMaxPages', 1)
    forbid_last = em.get('deepForbiddenLast', True)
    bands = _bands(txt)
    deep_idx = [i for i, b in enumerate(bands, 1) if 'band--deep' in b[:220]]
    chk(f"反相强调页 band--deep ≤ {max_deep} 页（浅色模式下渲染为深色）",
        len(deep_idx) <= max_deep,
        f"{len(deep_idx)} 页: {deep_idx}（收尾/金句页请用 band--accent）" if len(deep_idx) > max_deep else "",
        level="WARN")
    if forbid_last and bands:
        chk("末页非反相深色页（band--deep）",
            'band--deep' not in bands[-1][:220],
            "末页为 band--deep：浅色模式下会以深色收尾（改用 band--accent）", level="WARN")


def _layout_sig(band: str) -> str | None:
    """从 band HTML 提取版式签名（优先级从具体到宽泛）。
    图表类型并入签名：exhibit+sankey 与 exhibit+waterfall 视为不同版式。"""
    pats = (
        ('g-hero-full', r'g-hero-full'),
        ('g-mosaic', r'g-mosaic'),
        ('g-bento', r'g-bento'),
        ('g-aside', r'g-aside'),
        ('g-quad', r'g-quad'),
        ('g-211', r'g-211'),
        ('g-121', r'g-121'),
        ('g-side', r'g-side'),
        ('rows-2', r'rows-2'),
        ('rows-3', r'rows-3'),
        ('g-2', r'\bg-2\b'),
        ('g-3', r'\bg-3\b'),
        ('g-4', r'\bg-4\b'),
        ('g-5', r'\bg-5\b'),
        ('g-6', r'\bg-6\b'),
        ('cols-3', r'cols-3'),
        ('cols-2', r'cols-2'),
        ('exhibit', r'class="exhibit'),
        ('table', r'class="tbl-wrap'),
        ('metrics', r'class="metric'),
        ('arch', r'class="arch'),
        ('lane', r'class="lane'),
        ('matrix', r'class="matrix'),
        ('heat', r'class="heat'),
        ('bul', r'class="bul'),
        ('pyr', r'class="pyr'),
        ('steps', r'class="steps'),
        ('timeline', r'class="tl[\s"]'),
        ('media', r'class="media'),
        ('stagger', r'stagger'),
        ('quote', r'band--accent'),
        ('card', r'class="card[\s"]'),
    )
    base = None
    for name, pat in pats:
        if re.search(pat, band):
            base = name
            break
    if base is None:
        return None
    charts = re.findall(r'data-chart="([^"]+)"', band)
    if charts:
        # 去重保序，最多 2 类，避免顺序噪声
        seen, uniq = set(), []
        for c in charts:
            if c not in seen:
                seen.add(c)
                uniq.append(c)
        return f"{base}:{'+'.join(uniq[:2])}"
    return base


def _check_content_quality(txt, chk, mode, model):
    """内容级质量：版式节奏 / so-what 非空洞 / research 行动标题含判断。"""
    cq = LC.get('contentQuality') or {}
    bands = _bands(txt)
    skip = set((cq.get('rhythm') or {}).get('skipIds') or
               ['cover', 'agenda', 'refs', 'appendix', 'next'])

    # ① 版式节奏：同一签名不得连用超过上限
    max_streak = int((cq.get('rhythm') or {}).get('maxSameLayoutStreak') or 2)
    sigs: list[tuple[int, str]] = []
    for i, b in enumerate(bands, 1):
        head = b[:220]
        if any(f'id="{sid}"' in head for sid in skip):
            continue
        sig = _layout_sig(b)
        if sig:
            sigs.append((i, sig))
    streak_hits: list[str] = []
    run_sig, run_start, run_len = None, 0, 0
    for i, sig in sigs:
        if sig == run_sig:
            run_len += 1
        else:
            if run_sig and run_len > max_streak:
                streak_hits.append(f'{run_sig}×{run_len}（起第{run_start}页）')
            run_sig, run_start, run_len = sig, i, 1
    if run_sig and run_len > max_streak:
        streak_hits.append(f'{run_sig}×{run_len}（起第{run_start}页）')
    chk(f"版式节奏（同一版式签名连续 ≤{max_streak} 页）", not streak_hits,
        "; ".join(streak_hits[:3]) if streak_hits else "", level="WARN")

    # ② so-what 禁空洞套话 + 最短长度（HTML 与模型双侧）
    sw = cq.get('sowhat') or {}
    min_chars = int(sw.get('minChars') or 12)
    forbidden = list(sw.get('forbidden') or [])
    texts: list[tuple[str, str]] = []
    for m in re.finditer(r'class="sowhat__v"[^>]*>(.*?)</', txt, re.S):
        body = re.sub(r'<[^>]+>', '', m.group(1) or '').strip()
        if body:
            texts.append(('html', body))
    if model:
        for idx, sec in enumerate(model.get('sections') or [], 1):
            v = sec.get('soWhat')
            if isinstance(v, str) and v.strip():
                texts.append((f'model#{idx}', v.strip()))
    short, hollow = [], []
    for src, body in texts:
        if len(body) < min_chars:
            short.append(f'{src}:{body[:24]}')
        if any(f in body for f in forbidden):
            hollow.append(f'{src}:{body[:24]}')
    if texts:
        chk(f"结论条实质（长度 ≥{min_chars} 字且无空洞套话）", not short and not hollow,
            "; ".join((short + hollow)[:4]) if (short or hollow) else "", level="WARN")

    # ③ research 行动标题须含数字或判断词
    if mode == 'research':
        rt = cq.get('researchTitle') or {}
        if rt.get('requireDigitOrJudgment', True):
            jpat = rt.get('judgmentPattern') or r'[\d]|是|应|需|将'
            struct = ('报告大纲', '大纲', '参考资料', '数据来源', '下一步', '结论',
                      '全文核心', 'agenda', '附录', '收尾')
            h1s = re.findall(r'<h2 class="t-h1 shead__title"[^>]*>(.*?)</h2>', txt)
            titles = [re.sub(r'<[^>]+>', '', h).strip() for h in h1s]
            titles = [t for t in titles if len(t) >= 12 and
                      not t.lower().startswith(struct) and not any(s in t for s in struct)]
            no_judge = [t[:28] for t in titles if not re.search(jpat, t)]
            chk("research 行动标题含数字或判断词（标题即结论）", not no_judge,
                f"缺少判断信号: {no_judge[:3]}" if no_judge else "", level="WARN")


def _check_v9_hard_gates(txt, chk, model):
    """v9 硬门禁：标签泄漏 / 标题空页 / 极偏占比 / 简单图过大（治截图级缺陷）。"""
    import html as _html
    QG = LC.get('qualityGates') or {}
    patterns = QG.get('tagLeakPatterns') or [
        '<a ', '</a>', 'class="cite"', 'href=', '<strong', '</strong>'
    ]
    # ① HTML 标签泄漏进可见文本
    # 先抓「转义后当字面量显示」的（&lt;a class=…&gt;）：源码里就有实体
    leak_hits = []
    for i, b in enumerate(_bands(txt), 1):
        b2 = re.sub(r'<script\b[\s\S]*?</script>', ' ', b)
        b2 = re.sub(r'<style\b[\s\S]*?</style>', ' ', b2)
        # A. 转义标签字面量（用户截图形态：正文里直接可见 <a class="cite"…>）
        if re.search(r'&lt;/?[a-zA-Z][^&]{0,60}&gt;', b2):
            m = re.search(r'&lt;/?[a-zA-Z][^&]{0,60}&gt;', b2)
            leak_hits.append(f"第{i}页含转义标签字面量 `{m.group(0)[:40]}`")
            continue
        # B. 反转义后剥真标签，残留源码片段
        unesc = _html.unescape(b2)
        plain = _plain(unesc)
        for p in patterns:
            if p in plain:
                leak_hits.append(f"第{i}页可见文本含 `{p}`")
                break
    # C. REPORT_MODEL 字段内夹带 HTML 标签（在 <script> 里，正文剥离会漏掉）
    model_tag_hits = []
    mm = re.search(r'window\.REPORT_MODEL\s*=\s*(\{[\s\S]*?\})\s*;', txt)
    if mm:
        try:
            import json as _json
            mobj = _json.loads(mm.group(1))

            def _scan(o, path=''):
                if isinstance(o, dict):
                    for k, v in o.items():
                        _scan(v, f'{path}.{k}' if path else k)
                elif isinstance(o, list):
                    for i, v in enumerate(o):
                        _scan(v, f'{path}[{i}]')
                elif isinstance(o, str) and re.search(r'</?[a-zA-Z][^>]*>', o):
                    model_tag_hits.append(path or '(root)')
            _scan(mobj)
        except Exception:
            pass
    if model_tag_hits:
        leak_hits.append(f"REPORT_MODEL 字段夹带标签: {model_tag_hits[:3]}")
    chk("HTML_TAG_IN_TEXT 可见文本无 HTML 标签源码泄漏", not leak_hits,
        "; ".join(leak_hits[:5]) if leak_hits else "")

    # ② 标题空页 / 承载不足
    title_only, underfill = [], []
    to_min = int((QG.get('titleOnly') or {}).get('minBodyChars') or 40)
    uf = QG.get('underfill') or {}
    uf_min = int(uf.get('minCarriers') or 2)
    exempt = set(uf.get('exemptIds') or ['quote', 'cover', 'refs', 'appendix', 'next'])
    for i, b in enumerate(_bands(txt), 1):
        head = b[:240]
        bid_m = re.search(r'id="([^"]+)"', head)
        bid = bid_m.group(1) if bid_m else ''
        if bid in exempt or any(f'id="{e}"' in head for e in exempt):
            continue
        if 'band--deep' in head or 'band--accent' in head:
            continue
        b2 = re.sub(r'<script\b[\s\S]*?</script>', ' ', b)
        b2 = re.sub(r'<style\b[\s\S]*?</style>', ' ', b2)
        # 去掉 shead（eyebrow+标题+导语）后的正文
        body = re.sub(r'<div class="shead[\s\S]*?</div>\s*</div>', ' ', b2, count=1)
        body = re.sub(r'<div class="shead[\s\S]*?</h2>\s*</div>', ' ', b2, count=1)
        plain_body = _plain(body).strip()
        # 再去掉与标题重复的大标题串
        title_m = re.search(r'shead__title[^>]*>(.*?)</', b2)
        if title_m:
            plain_body = plain_body.replace(_plain(title_m.group(1)).strip(), '', 1).strip()
        carriers = _band_units(b)
        if len(plain_body) < to_min and carriers == 0:
            title_only.append(f"第{i}页正文{len(plain_body)}字")
        elif carriers < uf_min and len(plain_body) < to_min * 2:
            underfill.append(f"第{i}页承载{carriers}")
    chk(f"TITLE_ONLY_PAGE 非空页（去页头后正文 ≥{to_min} 字）", not title_only,
        "; ".join(title_only[:5]) if title_only else "")
    chk(f"UNDERFILL_PAGE 内容页承载 ≥{uf_min}（金句/章节幕豁免）", not underfill,
        "; ".join(underfill[:5]) if underfill else "")

    # ③ 极偏占比禁 donut/pie（治 0.5% vs 99.5% 环图叠字不可读）
    skew = QG.get('chartSkew') or {}
    skew_types = set(skew.get('types') or ['donut', 'pie', 'multidonut'])
    min_pct = float(skew.get('minSectorPct') or 5)
    max_ratio = float(skew.get('maxMinRatio') or 20)
    skew_hits = []
    if model and isinstance(model.get('sections'), list):
        for si, sec in enumerate(model['sections'], 1):
            if not isinstance(sec, dict):
                continue
            ch = sec.get('chart') or {}
            ctype = str(ch.get('type') or sec.get('type') or '').lower()
            if sec.get('type') == 'donut':
                ctype = 'donut'
            if ctype not in skew_types:
                continue
            try:
                vals = [float(v) for v in (ch.get('values') or []) if v is not None]
            except (TypeError, ValueError):
                skew_hits.append(f"第{si}章 {ctype} values 含非数值（图表数据非法，无法判定占比）")
                continue
            vals = [v for v in vals if v >= 0]
            if len(vals) < 2:
                continue
            total = sum(vals) or 1
            pcts = [v / total * 100 for v in vals]
            mn, mx = min(pcts), max(pcts)
            ratio = (mx / mn) if mn > 0 else 999
            if mn < min_pct or ratio > max_ratio:
                skew_hits.append(
                    f"第{si}章 {ctype} 最小扇区 {mn:.1f}%（比 {ratio:.0f}:1）应改 KPI/进度/对比条")
    chk(f"CHART_SKEW_INVALID 占比图最小扇区 ≥{min_pct:.0f}% 且 max/min ≤{max_ratio:.0f}",
        not skew_hits, "; ".join(skew_hits[:4]) if skew_hits else "")

    # ④ 简单图过大（类别≤2 或 数据点≤3 却近乎独占内容区）
    ov = QG.get('chartOversize') or {}
    simple_cats = int(ov.get('simpleMaxCats') or 2)
    simple_pts = int(ov.get('simpleMaxPts') or 3)
    max_pct_area = float(ov.get('maxContentAreaPct') or 55)
    oversize = []
    for i, b in enumerate(_bands(txt), 1):
        for m in re.finditer(
                r'<svg\b[^>]*data-chart="([^"]+)"[^>]*style="([^"]*)"[^>]*>',
                b):
            ctype, style = m.group(1), m.group(2)
            # 解析 width / height（px 或 %）
            wm = re.search(r'width:\s*(\d+(?:\.\d+)?)px', style)
            hm = re.search(r'height:\s*(\d+(?:\.\d+)?)px', style)
            vw = re.search(r'viewBox="0 0 (\d+(?:\.\d+)?) (\d+(?:\.\d+)?)"', m.group(0))
            # 从 svg 块粗数数据点/类别
            svg_end = b.find('</svg>', m.end())
            block = b[m.start():svg_end if svg_end > 0 else m.end() + 800]
            n_labels = len(re.findall(r'<text\b', block))
            n_rects = len(re.findall(r'<rect\b', block))
            n_circles = len(re.findall(r'<circle\b', block))
            n_pts = max(n_labels, n_rects, n_circles)
            is_simple = n_labels <= simple_cats or n_pts <= simple_pts
            if not is_simple:
                continue
            # 简单图接近通宽且高度大 → 视为「简单大图」
            h_px = float(hm.group(1)) if hm else (float(vw.group(2)) if vw else 0)
            if h_px >= 320 or (not hm and not vw and 'width:100%' in style and 'height' not in style):
                # 无显式高度的通宽简单图
                if h_px >= 320 or ('width:100%' in style and n_pts <= simple_pts):
                    oversize.append(f"第{i}页 {ctype} 简单图过大（{n_pts} 点/标记）")
    chk(f"CHART_OVERSIZE 简单图（≤{simple_cats} 类或 ≤{simple_pts} 点）勿独占版面（上限 {max_pct_area:.0f}%）",
        not oversize, "; ".join(oversize[:4]) if oversize else "")



def _class_tokens(tag_or_html: str) -> set[str]:
    """Extract HTML class tokens from class="..." attributes."""
    out: set[str] = set()
    for m in re.finditer(r'class="([^"]*)"', tag_or_html):
        out.update(m.group(1).split())
    return out


def _mixed_grid_needs_align(band: str) -> bool:
    """True when a grid/g-* region pairs media with cards/lists (token-exact; no t-metric / data-chart false hits)."""
    def has_media(classes: set[str], chunk: str) -> bool:
        if classes & {'fig', 'media', 'chart'}:
            return True
        if any(c.startswith('media') or c.startswith('fig') for c in classes):
            return True
        return 'data-chart=' in chunk

    def has_cards(classes: set[str]) -> bool:
        if classes & {'card', 'ul', 'metric'}:
            return True
        return any(
            c.startswith('ul--') or c.startswith('card') or c.startswith('metric__')
            for c in classes)

    # Find each grid opening and inspect following chunk
    for m in re.finditer(r'<div class="([^"]*)"', band):
        classes_on_grid = set(m.group(1).split())
        if not (classes_on_grid & {'grid'} or any(re.fullmatch(r'g-\d+', c) or c.startswith('g-') for c in classes_on_grid)):
            # allow g-hero / g-side / g-2 etc
            if not any(c == 'grid' or c.startswith('g-') for c in classes_on_grid):
                continue
        chunk = band[m.start(): m.start() + 4500]
        classes = _class_tokens(chunk)
        if has_media(classes, chunk) and has_cards(classes):
            return True
    return False


def _check_layout_grammar(txt, chk, mode):
    """布局语法门禁：骨架类 / 单一重心 / 混排对齐 / 间距 token / 图标尺寸 / 标签防换行。"""
    LS = LC.get('layoutSystem') or {}
    presets = LS.get('presets') or {}
    elem = LS.get('elements') or {}
    mf = LS.get('multiFocus') or {}
    align_cfg = LS.get('align') or {}
    fill_t = (LS.get('fillTarget') or {}).get(mode) or [62, 78]
    icon_sizes = set(elem.get('icon', {}).get('sizesPx') or [16, 18, 20, 24])
    chart_w_pct = float(mf.get('chartWidthPct') or 55)
    metric_fz = float(mf.get('metricFontPx') or 40)

    # 收集预设骨架对应 class
    skeleton_classes = set()
    for p in (presets or {}).values():
        for c in (p.get('html') or []):
            skeleton_classes.add(c)
    # 附加常见栅格类（grammar 白名单）
    skeleton_classes.update({
        'g-2', 'g-3', 'g-4', 'g-5', 'g-6', 'g-hero', 'g-hero--rev', 'g-side', 'g-side--rev',
        'g-31', 'g-13', 'g-41', 'g-14', 'g-211', 'g-121', 'g-quad', 'g-aside', 'g-bento',
        'g-hero-full', 'g-mosaic', 'rows-2', 'rows-3', 'stagger', 'media-grid', 'media-compare',
    })

    no_skel, multi_focus, align_miss, off_token = [], [], [], []
    icon_bad, label_collapse = [], []
    fill_low, fill_high = [], []
    mixed_need = bool(align_cfg.get('requireOnMixed', True))
    align_tokens = set(align_cfg.get('mixedGridClasses') or ['a-start', 'a-c', 'align-items'])

    for i, b in enumerate(_bands(txt), 1):
        head = b[:240]
        # intentional whitespace：封面/章节幕/金句/收尾等休止页不参与 FILL 门禁
        if any(f'id="{x}' in head for x in (
                'refs', 'appendix', 'cover', 'agenda', 'quote',
                'closing', 'section', 'chapter', 'next')):
            continue
        if 'band--flow' in head:
            continue
        # 轻量合法页：金句/强调带/大数压场（fill 目标放宽）
        is_light = ('band--fit' in head or 'band--accent' in head or
                    'band--deep' in head or 'quote' in head)

        # ① 骨架类（或 data-skel 标记）
        has_skel = ('data-skel="' in b) or any(
            re.search(rf'class="[^"]*\b{re.escape(c)}\b', b) for c in skeleton_classes)
        # 手写 inline grid 且无预设类
        inline_grid = re.findall(r'style="[^"]*display:\s*grid[^"]*"', b)
        if not has_skel and inline_grid:
            no_skel.append(f"第{i}页 inline grid 无 P1–P12 骨架类")

        # ② 单一视觉重心（粗启发式）
        n_big = 0
        for m in re.finditer(r'<svg\b[^>]*>', b):
            tag = m.group(0)
            wm = re.search(r'width:\s*(\d+(?:\.\d+)?)px', tag)
            wrap = int((re.search(r'--wrap:\s*(\d+)', txt) or [0, 1400])[1] or 1400) if False else 1400
            if wm and float(wm.group(1)) / wrap * 100 >= chart_w_pct:
                n_big += 1
            if re.search(r'width:\s*100%', tag) and 'data-chart' in tag:
                # 通宽图记 1 大件
                n_big += 1
        for m in re.finditer(r'font-size:\s*clamp\(\s*(\d+)px', b):
            if float(m.group(1)) >= metric_fz:
                n_big += 1
                break
        if re.search(r'class="[^"]*media--(?:full|bleed)', b):
            n_big += 1
        if n_big >= 2:
            multi_focus.append(f"第{i}页大件×{n_big}")

        # ③ 混排对齐（grid 内同时有图/媒体与卡/列表；token 精确）
        mixed = _mixed_grid_needs_align(b)
        if mixed and mixed_need:
            if not any(re.search(r'\b' + re.escape(tok) + r'\b', b) for tok in align_tokens):
                align_miss.append(f"第{i}页图卡混排缺 a-start/a-c")

        # ④ 间距写死（margin/padding/gap 非 token / 非 clamp；≤8px 微调白名单）
        for m in re.finditer(r'(?:margin|padding|gap)(?:-[a-z]+)?\s*:\s*([^;"]+)', b):
            val = m.group(1).strip()
            if not val or val.startswith('var(') or val.startswith('clamp(') or val.startswith('0'):
                continue
            if re.fullmatch(r'auto|inherit|initial|unset|normal', val):
                continue
            px_vals = [float(x) for x in re.findall(r'(\d+(?:\.\d+)?)px', val)]
            if px_vals and all(v <= 8 for v in px_vals) and 'clamp' not in val and 'var(' not in val:
                continue  # 4–8px 光学微调允许
            if px_vals and 'clamp' not in val and 'var(' not in val:
                off_token.append(f"第{i}页 `{val[:24]}`")

        # ⑤ 图标尺寸
        for m in re.finditer(
                r'<svg\b[^>]*(?:class="[^"]*(?:ico|icon)[^"]*"|metric__ico|card__ico)[^>]*>',
                b, re.I):
            tag = m.group(0)
            sm = re.search(r'width:\s*["\']?(\d+)', tag) or re.search(r'width="(\d+)"', tag)
            if sm and int(sm.group(1)) not in icon_sizes:
                icon_bad.append(f"第{i}页 {sm.group(1)}px")

        # ⑥ 图表标签防换行（短盒 + 长 text）
        for m in re.finditer(r'<text[^>]*width="(\d+)"[^>]*>([^<]{8,})</text>', b):
            if int(m.group(1)) < 48:
                label_collapse.append(f"第{i}页标签盒宽{m.group(1)}")

        # ⑦ 结构图禁裸文字箭头（F13）
        if re.search(r'class="[^"]*lane__arr[^"]*"[^>]*>\s*→', b) or re.search(
                r'lane__arr">→', b):
            label_collapse.append(f"第{i}页泳道裸文字→（改 .lane__arr）")

        # ⑧ 填充率粗估（去空白字符 + 组件；轻量页不判过空）
        b2 = re.sub(r'<script\b[\s\S]*?</script>', ' ', b)
        b2 = re.sub(r'<style\b[\s\S]*?</style>', ' ', b2)
        plen = len(re.sub(r'\s+', '', _plain(b2)))
        units = _band_units(b)
        budget = MODE_BUDGETS.get(mode, MODE_BUDGETS['presentation'])
        est = (plen / max(1, budget['fit']) * 55) + (units / max(1, budget['unit']) * 45)
        est = max(0, min(100, est))
        lo_t = fill_t[0] * 0.55
        hi_t = min(95, fill_t[1] * 1.15)
        if (not is_light) and est < lo_t and units == 0 and plen < budget['empty']:
            fill_low.append(f"第{i}页≈{est:.0f}%")
        elif est > hi_t and not is_light:
            fill_high.append(f"第{i}页≈{est:.0f}%")

    chk(f"LAYOUT_NO_SKELETON 内容页使用 P1–P12 骨架类（layout-grammar）", not no_skel,
        "; ".join(no_skel[:4]) if no_skel else "")
    chk(f"LAYOUT_MULTI_FOCUS 一屏一视觉重心（大件 ≤{mf.get('maxPrimary', 1)}）", not multi_focus,
        "; ".join(multi_focus[:4]) if multi_focus else "")
    chk("LAYOUT_ALIGN_DRIFT 图卡混排显式对齐（a-start / a-c）", not align_miss,
        "; ".join(align_miss[:4]) if align_miss else "")
    chk("LAYOUT_SPACING_OFF_TOKEN 间距走 --sp-*/gap/clamp（禁游离 px）", not off_token,
        "; ".join(off_token[:4]) if off_token else "", level="WARN")
    chk("LAYOUT_ICON_SIZE 图标 ∈ {16,18,20,24}px", not icon_bad,
        "; ".join(icon_bad[:4]) if icon_bad else "", level="WARN")
    chk("LAYOUT_LABEL_COLLIDE 图表标签盒足够宽 / 结构图无裸文字箭头", not label_collapse,
        "; ".join(label_collapse[:4]) if label_collapse else "")
    chk(f"LAYOUT_FILL 填充率目标 {fill_t[0]}–{fill_t[1]}%（{mode}）",
        not fill_low and not fill_high,
        ("过空: " + "; ".join(fill_low[:3]) if fill_low else "") +
        ((" 过满: " + "; ".join(fill_high[:3])) if fill_high else ""))


def _check_annotations(txt, chk, model):
    """待核实标注：.tbd 内联标色须配 .tbd-legend / .flagbar 说明；单页数量上限。"""
    an = LC.get('annotations') or {}
    max_per_page = an.get('flagMaxPerPage', 12)
    require_legend = an.get('requireLegend', True)
    tbd_re = re.compile(r'class="tbd(?:\s|")')
    no_legend, over = [], []
    for i, b in enumerate(_bands(txt), 1):
        n = len(tbd_re.findall(b))
        if n and require_legend and ('tbd-legend' not in b and 'flagbar' not in b):
            no_legend.append(f"第{i}页")
        if n > max_per_page:
            over.append(f"第{i}页 {n}处")
    chk("待核实标注 .tbd 均配 .tbd-legend/.flagbar 说明", not no_legend,
        f"{no_legend} 有标色项但无说明（用户不知为何标色）" if no_legend else "", level="WARN")
    chk(f"单页待核实标注 ≤ {max_per_page} 处（过密则转 .flagbar 清单）", not over,
        "; ".join(over) if over else "", level="WARN")
    if model:
        mflags = [s for s in (model.get('sections') or []) if s.get('flags')]
        if mflags and 'flagbar' not in txt and 'tbd-legend' not in txt:
            chk("模型 flags ↔ 正文待核实条对应", False,
                f"{len(mflags)} 页模型含 flags，正文无 .flagbar/.tbd-legend", level="WARN")


def _img_holders(sec):
    """页内可能承载素材图片的容器（image 页型 / split 右栏）。"""
    out = []
    if isinstance(sec.get('image'), dict):
        out.append(sec['image'])
    right = sec.get('right')
    if isinstance(right, dict) and isinstance(right.get('image'), dict):
        out.append(right['image'])
    return out


def _img_srcs(img):
    """图片对象的全部真实 src（image.src + image.items[].src），排除占位符。"""
    if img.get('placeholder'):
        return []
    srcs = []
    if isinstance(img.get('src'), str) and img['src'].strip():
        srcs.append(img['src'])
    for it in (img.get('items') or []):
        if isinstance(it, dict) and isinstance(it.get('src'), str) and it['src'].strip():
            srcs.append(it['src'])
        elif isinstance(it, str) and it.strip():
            srcs.append(it)
    return srcs


def _img_alt_ok(tag: str) -> bool:
    """alt 存在且非空（alt="" 视为缺失）。"""
    m = re.search(r'alt\s*=\s*("([^"]*)"|\'([^\']*)\')', tag)
    if not m:
        return False
    val = m.group(2) if m.group(2) is not None else m.group(3)
    return bool(val and val.strip())


def _data_uri_bytes(tag: str):
    """解码 data: URI 的实际字节数；非 base64 或解码失败时回落为载荷字符数。"""
    m = (re.search(r'src\s*=\s*"data:[^"\',]*,([^"]*)"', tag)
         or re.search(r"src\s*=\s*'data:[^\"\',]*,([^']*)'", tag))
    if not m:
        return None
    payload = re.sub(r'\s', '', m.group(1))
    try:
        return len(base64.b64decode(payload))
    except Exception:
        return len(payload)


def _check_media(txt, chk, model):
    """素材图片与配图占位：零外链铁律（<img> 只允许 data: 内联或相对路径）；
    alt 可访问性；配图占位必须有可见标签；模型 image 三选一（src/items/placeholder）
    与正文版式、数量、裁切策略一一对应。"""
    imgs = re.findall(r'<img\b[^>]*>', txt)
    if imgs:
        bad = [t for t in imgs if re.search(r'src\s*=\s*["\']\s*(?:https?:)?//', t)]
        chk("图片源无外链（data: 内联或相对路径，零外链铁律）", not bad,
            f"{len(bad)} 处外链图片" if bad else "")
        noalt = [t for t in imgs if not _img_alt_ok(t)]
        chk("图片均带 alt（可访问性）", not noalt,
            f"{len(noalt)} 处缺 alt（含空 alt)" if noalt else "", level="WARN")
        data_imgs = [t for t in imgs if re.search(r'src\s*=\s*["\']\s*data:', t)]
        data_sizes = [(_data_uri_bytes(t), t) for t in data_imgs]
        max_bytes = max((b or 0 for b, _ in data_sizes), default=0)
        inline_bytes = sum(b if b is not None else len(t) for b, t in data_sizes)
        chk("单图 data: 内联体积在上限内", all((b or 0) <= IMAGE_MAX_INLINE for b, _ in data_sizes),
            f"最大 {max_bytes // 1024}KB > 上限 {IMAGE_MAX_INLINE // 1024}KB（按解码后字节计）",
            level="WARN")
        chk("报告内联图片总量在上限内", inline_bytes <= IMAGE_MAX_TOTAL,
            f"{inline_bytes // 1024}KB > 上限 {IMAGE_MAX_TOTAL // 1024}KB（改用相对路径）",
            level="WARN")
    ph_blocks = re.findall(r'class="[^"]*\bmedia--ph\b[^"]*"', txt)
    if ph_blocks:
        chk("配图占位含可见标签（.media__ph）", 'media__ph' in txt,
            f"{len(ph_blocks)} 处 .media--ph 缺 .media__ph 标签（空占位 = 不合格）")
    if not model:
        return
    holders = [(i, img) for i, s in enumerate(model.get('sections') or [])
               if isinstance(s, dict) for img in _img_holders(s)]
    if not holders:
        return
    bad_src, bad_layout, bad_fit, too_many = [], [], [], []
    n_declared = 0
    n_ph = 0
    for idx, img in holders:
        srcs = _img_srcs(img)
        n_declared += len(srcs)
        if img.get('placeholder'):
            n_ph += 1
        for s in srcs:
            if re.match(r'\s*(?:https?:)?//', str(s)):
                bad_src.append(f"sections[{idx}]")
        layout = str(img.get('layout') or ('grid' if len(img.get('items') or []) > 1 else 'full')).lower()
        if layout not in IMAGE_LAYOUTS:
            bad_layout.append(f"sections[{idx}]:{layout}")
        if img.get('fit') and str(img['fit']).lower() not in IMAGE_FIT:
            bad_fit.append(f"sections[{idx}]:{img['fit']}")
        items = img.get('items') or []
        if len(items) > IMAGE_MAX_PER_PAGE:
            too_many.append(f"sections[{idx}]={len(items)}")
        if layout in IMAGE_MULTI_LAYOUTS and not img.get('placeholder') and len(items) < 2:
            too_many.append(f"sections[{idx}] {layout} 需 ≥2 张图（当前 {len(items)}）")
    chk("模型 image.src 非外链（data:/相对路径）", not bad_src,
        f"{len(bad_src)} 处外链 src" if bad_src else "")
    chk("模型 image.layout 合法（imageSpec.layouts）", not bad_layout,
        f"非法版式 {sorted(set(bad_layout))}" if bad_layout else "")
    chk("模型 image.fit 合法（cover/contain）", not bad_fit,
        f"非法裁切 {sorted(set(bad_fit))}" if bad_fit else "")
    chk("单页图片数/多图版式图数合规（imageSpec.maxPerPage · 多图版式 ≥2 张）", not too_many,
        f"{too_many}" if too_many else "", level="WARN")
    layout_class = {'grid': 'media-grid', 'compare': 'media-compare', 'wall': 'media-wall',
                    'bleed': 'media--bleed', 'ph': 'media--ph'}
    ratio_css = IMAGE_SPEC.get('ratioCssClass') or {}
    miss_cls = []
    for idx, img in holders:
        lay = str(img.get('layout') or ('grid' if len(img.get('items') or []) > 1 else 'full')).lower()
        cls = layout_class.get(lay)
        if cls and cls not in txt:
            miss_cls.append(f"sections[{idx}]:{lay}→.{cls}")
        # 比例锁定类：HTML 与 PPTX 用同一份 imageSpec.ratioCssClass，缺了就会出现"比例走样"
        rcls = ratio_css.get(lay)
        if rcls and ('.' + rcls) not in txt:
            miss_cls.append(f"sections[{idx}]:{lay}→.{rcls}（比例未锁定）")
        if img.get('placeholder') and 'media--ph' not in txt:
            miss_cls.append(f"sections[{idx}]:placeholder→.media--ph")
    chk("模型图片版式 ↔ 正文版式类/比例锁定类对应", not miss_cls,
        f"缺 {sorted(set(miss_cls))}" if miss_cls else "", level="WARN")
    if n_declared and len(imgs) < n_declared:
        chk("模型 image ↔ 正文图片数量对应", False,
            f"模型声明 {n_declared} 张但正文仅 {len(imgs)} 个 <img>", level="WARN")
    if n_ph and not ph_blocks:
        chk("模型配图占位 ↔ 正文 .media--ph 对应", False,
            f"{n_ph} 页模型声明 image.placeholder 但正文无 .media--ph", level="WARN")

    # 配图页 caption / so-what（廉价 WARN）；近邻主张/导语亦可
    bands = re.split(r'(?=<section\b)', txt)
    miss_cap = []
    near_empty = []
    for i, b in enumerate(bands):
        if not re.search(r'class="[^"]*\bmedia\b|<img\b|class="[^"]*media--', b):
            continue
        if len(b) < 80:
            continue
        has_cap = bool(re.search(
            r'class="[^"]*(?:fig__cap|media__cap|media__ph|caption|exhibit__src|footnote|so-what|lead)', b)
            or re.search(r'<figcaption\b|class="[^"]*\bsoWhat\b', b))
        if not has_cap:
            miss_cap.append(f'band[{i}]')
        # 近图过空：有 media 但正文文本极少且无要点/指标（WARN）
        textish = re.sub(r'<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>', ' ', b)
        textish = re.sub(r'\s+', ' ', textish).strip()
        has_points = bool(re.search(r'class="[^"]*(?:points|bullets|kpi|metrics|card)', b))
        if len(textish) < 40 and not has_points and not re.search(r'media--ph', b):
            near_empty.append(f'band[{i}]')
    chk("配图页含 caption/图注（IMAGE_CAPTION）", not miss_cap,
        f"{len(miss_cap)} 处配图区缺 .fig__cap/.media__cap/.footnote/so-what 等图注" if miss_cap else "",
        level="WARN")
    chk("配图页近邻过空（IMAGE_NEAR_EMPTY）", not near_empty,
        f"{len(near_empty)} 处配图页几乎无注解/要点（补 caption 或要点条）" if near_empty else "",
        level="WARN")


# 失败检查项 → 失败模式 / 处置动作 / 精确取码命令。
# 目的：校验失败时直接给出「改什么、按什么顺序改、去哪取代码」，
# 使智能体不必整读 references/failure-modes.md（17KB）就能收敛。
# 关键词按检查项名称匹配；新增检查项时同步在此登记，否则只回落通用处置顺序。
FIX_GUIDE = [
    (("页高", "溢出", "满屏", "文字预算"), "F4 容器溢出",
     "① 列表化/精炼 ② 升级承载形态 ③ 换/扩组合版式 ④ 分区 ⑤ 拆页 ⑥ 最后才有限缩字号",
     "--task content-rules"),
    (("过空", "内容不足", "密度"), "F1 内容不足 / F3 密度塌陷",
     "补证据与含义（数字+口径+so-what），不要用装饰或放大字号填空",
     "--task content-rules"),
    (("图表", "多样性", "登记"), "F6 图表降级 / F12 图表单一",
     "换图表类型拉开多样性；连续两页不得同型；类型须在 charts.registry 登记",
     "--task chart-pick"),
    (("最小尺寸",), "图表尺寸不足",
     "把 svg 的 viewBox 高/显示宽度提到 charts.minSize 之上（尺寸问题改尺寸，不要靠换图型回避）",
     "--task chart-pick"),
    (("Exhibit",), "研究模式证据编号",
     "每个 .exhibit 框都要有 .exhibit__no（Exhibit N，全篇连续）与 .exhibit__src 来源行",
     "--task research-evidence"),
    (("引用", "参考资料", "锚点"), "引用闭环",
     "正文 [n] 上标与文末条目双向对齐且编号从 1 连续；ref-link 带 target/rel",
     "--file components-atoms.md --section 7"),
    (("待核实", "tbd"), "待核实标注",
     "每处 .tbd 必须配 .tbd-legend 或 .flagbar 说明口径，只标色不解释即不合格",
     "--file components-atoms.md --section 11b"),
    (("强调", "风格", "主题", "配色"), "F8 主题/风格漂移",
     "风格是皮肤不是解药：末页禁 band--deep，收尾用 band--accent；单一强调色",
     "--file components-atoms.md --section 11"),
    (("so-what", "结论", "标题"), "F15 空洞结论",
     "research 主标题须是结论句（≥12 字含数字或判断词）；so-what 禁套话",
     "--task content-rules"),
    (("版式", "节奏", "组合"), "F11 单件页默认",
     "默认一页=主件+从件+注释；同一版式不连用超 2 页，密度 L/M/H 交替",
     "--task presentation-combo"),
    (("图片", "占位", "media"), "F9 配图走样 / F10 空占位",
     "无素材用 image.placeholder + .media--ph 锁版式；路径以模型目录为锚；禁外链",
     "--task image-layout"),
    (("AI", "去AI味"), "文风",
     "改写命中的高危词；大段文字转列表",
     "--task content-rules"),
]


def _print_fix_guide(results, strict, width):
    """校验未通过时输出定向修复指引（只列命中的失败模式，不做全量倾倒）。"""
    failed = [(lv, nm, nt) for lv, nm, ok, nt in results
              if not ok and (lv == "FAIL" or strict)]
    if not failed:
        return
    seen, guides = set(), []
    for _, name, _ in failed:
        nl = name.lower()
        # 最长关键词优先（而非首个命中即 break）：避免「图表最小尺寸」被泛化的
        #「图表」关键词抢走、误路由到「换图表类型」
        best = None
        for keys, mode, action, cmd in FIX_GUIDE:
            hit = max((len(k) for k in keys if k.lower() in nl), default=0)
            if hit and (best is None or hit > best[0]):
                best = (hit, mode, action, cmd)
        if best and best[1] not in seen:
            seen.add(best[1])
            guides.append((best[1], best[2], best[3]))
    print("-" * width)
    print("修复指引（按下列顺序改；跳步直接缩字号/砍内容会把问题推给下一环）：")
    if guides:
        for i, (mode, action, cmd) in enumerate(guides, 1):
            print(f"  {i}. [{mode}] {action}")
            print(f"     取码: python scripts/extract_snippet.py {cmd}")
    else:
        print("  未匹配到已登记的失败模式，按通用顺序处置：")
        print("  ① 重构承载（列表/卡/表/图）② 拆页/分章 ③ 换布局形态 "
              "④ 有限缩字号 ⑤ 禁止静默截断/砍 so-what")
    print("  完整失败模式库与错误解释纠正表: references/failure-modes.md")



def _check_layout_qa(txt, chk, mode, model):
    """布局 QA（--layout-qa；presentation+--strict 自动开）：
    V 契约 / 极偏环图 / 骨架连用 / 缺 data-skel / 简单全幅 /
    截断迹象 / 溢出未拆页 / 半空卡 / 列对齐节奏。
    """
    bands = _bands(txt)
    skip_ids = {'cover', 'agenda', 'refs', 'appendix', 'next', 'quote'}
    content = []
    for i, b in enumerate(bands, 1):
        head = b[:240]
        if any(f'id="{sid}"' in head for sid in skip_ids):
            continue
        if 'band--deep' in head or 'band--accent' in head:
            # 金句/强调带允许无骨架
            if 'data-skel=' not in b and not re.search(r'class="[^"]*\bP\d+\b', b):
                continue
        content.append((i, b, head))

    # ① 缺 data-skel：若全文已出现 data-skel（scaffold/render 管线），则内容页必须都有
    has_any_skel = 'data-skel="' in txt
    missing = []
    if has_any_skel:
        for i, b, head in content:
            if 'data-skel="' not in b and not re.search(r'class="[^"]*\bP\d+\b', b):
                missing.append(f"第{i}页")
    chk("LAYOUT_QA_MISSING_SKEL 内容页须带 data-skel（管线产物）",
        not missing,
        ("缺骨架: " + "; ".join(missing[:5])) if missing else
        ("（全文无 data-skel，跳过——手写示例豁免；scaffold/render 会写入）" if not has_any_skel else ""))

    # ② 连续 ≥3 页同一 data-skel（或同一 layout 签名）
    skels = []
    for i, b, head in content:
        m = re.search(r'data-skel="(P\d+)"', b)
        if m:
            skels.append((i, m.group(1)))
        else:
            sig = _layout_sig(b)
            if sig:
                skels.append((i, f"sig:{sig}"))
    streak_hits = []
    run_v, run_s, run_n = None, 0, 0
    for i, v in skels:
        if v == run_v:
            run_n += 1
        else:
            if run_v and run_n >= 3:
                streak_hits.append(f"{run_v}×{run_n}（起第{run_s}页）")
            run_v, run_s, run_n = v, i, 1
    if run_v and run_n >= 3:
        streak_hits.append(f"{run_v}×{run_n}（起第{run_s}页）")
    chk("LAYOUT_QA_SKEL_STREAK 同一 data-skel/版式签名连续 <3 页",
        not streak_hits, "; ".join(streak_hits[:3]) if streak_hits else "")

    # ③ 极偏仍用 donut/pie（模型侧；与 CHART_SKEW 互补，专打 layout-qa 关键字）
    skew_hits = []
    sections = (model or {}).get('sections') or []
    for si, sec in enumerate(sections, 1):
        if not isinstance(sec, dict):
            continue
        ch = sec.get('chart') if isinstance(sec.get('chart'), dict) else {}
        ctype = str(ch.get('type') or (sec.get('type') if sec.get('type') in
                                         ('donut', 'pie', 'multidonut') else '') or '').lower()
        if sec.get('type') == 'donut':
            ctype = 'donut'
        if ctype not in ('donut', 'pie', 'multidonut'):
            continue
        vals = [float(v) for v in (ch.get('values') or []) if isinstance(v, (int, float))]
        vals = [v for v in vals if v >= 0]
        if len(vals) < 2:
            continue
        total = sum(vals) or 1.0
        pcts = [v / total * 100 for v in vals]
        mn, mx = min(pcts), max(pcts)
        ratio = (mx / mn) if mn > 0 else 999
        if mn < 5.0 or ratio > 20:
            skew_hits.append(f"sections[{si}] {ctype} 最小{mn:.1f}% 比{ratio:.0f}:1 → 改 V3/KPI")
    chk("LAYOUT_QA_SKEW_DONUT 极偏占比禁用 donut/pie（改 V3 KPI）",
        not skew_hits, "; ".join(skew_hits[:3]) if skew_hits else "")

    # ④ 演示模式：简单图（≤2 类）却近全幅（svg height≥320 或 width:100% 无注解带）
    bleed_hits = []
    if mode == 'presentation':
        for i, b, head in content:
            for m in re.finditer(
                    r'<svg\b[^>]*data-chart="([^"]+)"[^>]*style="([^"]*)"[^>]*>', b):
                ctype, style = m.group(1), m.group(2)
                svg_end = b.find('</svg>', m.end())
                block = b[m.start():svg_end if svg_end > 0 else m.end() + 600]
                n_lab = len(re.findall(r'<text\b', block))
                n_pts = max(n_lab, len(re.findall(r'<rect\b', block)),
                            len(re.findall(r'<circle\b', block)))
                hm = re.search(r'height:\s*(\d+(?:\.\d+)?)px', style)
                h_px = float(hm.group(1)) if hm else 0
                simple = n_lab <= 2 or n_pts <= 3
                full = h_px >= 320 or ('width:100%' in style and h_px >= 240)
                has_anno = bool(re.search(r'class="[^"]*(?:sowhat|anno|points|callout)', b))
                if simple and full and not has_anno:
                    bleed_hits.append(f"第{i}页 {ctype} 简单全幅无注解")
    chk("LAYOUT_QA_SIMPLE_FULLBLEED 演示页简单图禁全幅无注解（用 V1–V4）",
        not bleed_hits, "; ".join(bleed_hits[:3]) if bleed_hits else "")

    # ⑤ V 契约：演示页 data-v / data-skel 与内容复杂度粗检
    v_hits = []
    if mode == 'presentation' and sections:
        for si, sec in enumerate(sections, 1):
            if not isinstance(sec, dict):
                continue
            pt = str(sec.get('type') or '')
            if pt in ('cover', 'agenda', 'closing', 'quote'):
                continue
            ch = sec.get('chart') if isinstance(sec.get('chart'), dict) else {}
            vals = ch.get('values') or []
            n = len(vals) if vals else len(sec.get('points') or sec.get('items') or [])
            skel = str(sec.get('layoutPreset') or '')
            # 极偏却仍 donut
            if pt == 'donut' or ch.get('type') in ('donut', 'pie'):
                if vals:
                    nums = [float(v) for v in vals if isinstance(v, (int, float)) and v >= 0]
                    if len(nums) >= 2:
                        total = sum(nums) or 1
                        pcts = [v / total * 100 for v in nums]
                        if min(pcts) < 5:
                            v_hits.append(f"sections[{si}] 极偏仍 {pt or ch.get('type')}（应 V3/kpi）")
            # 简单 1–2 点却声明 V1 全幅主视觉（layoutPreset P1 + 简单）
            if skel == 'P1' and n <= 2 and (pt in ('bar', 'donut') or ch.get('type')):
                v_hits.append(f"sections[{si}] P1+简单{n}点（应 V3/P3 或加注解）")
    chk("LAYOUT_QA_V_CONTRACT 演示 V1–V4 与复杂度匹配",
        not v_hits, "; ".join(v_hits[:3]) if v_hits else "")

    # ⑥ 截断迹象：正文/列表项以省略号截断充数（antiTruncation）
    at = (LC.get('qualityGates') or {}).get('antiTruncation') or {}
    trunc_hits = []
    if at.get('forbidEllipsisTruncate', True):
        patterns = list(at.get('ellipsisPatterns') or ['…', '...', '……'])
        for i, b, head in content:
            plain_parts = re.findall(r'<(?:li|p)[^>]*>([\s\S]*?)</(?:li|p)>', b)
            plain_parts += re.findall(
                r'class="[^"]*(?:card__b|sowhat__v|point)[^"]*"[^>]*>([\s\S]*?)</',
                b)
            for raw in plain_parts:
                plain = _plain(raw).strip()
                if len(plain) < 8:
                    continue
                for pat in patterns:
                    if plain.endswith(pat) or plain.endswith(pat + '。'):
                        # 排除「等…」短收口
                        if re.search(r'等[…\.]{1,3}$', plain) and len(plain) <= 16:
                            continue
                        trunc_hits.append(f"第{i}页「{plain[:18]}」")
                        break
    chk("LAYOUT_QA_TRUNCATION 禁静默截断（列表/卡/结论勿以省略号砍义）",
        not trunc_hits, "; ".join(trunc_hits[:4]) if trunc_hits else "")

    # ⑦ 溢出却无拆页策略：页高估算超预算，且无 band--flow / 续页标记 / 多部分 title
    overflow_hits = []
    if at.get('overflowNoSplitFail', True):
        B = MODE_BUDGETS.get(mode, MODE_BUDGETS['presentation'])
        fs_px = int(B.get('bodyPx') or 17)
        wrap_px = int(B.get('wrap') or 1400) - WRAP_INSET_PX
        cpl = max(10, int(wrap_px / fs_px))
        for i, b, head in content:
            if 'band--flow' in head:
                continue
            # 已有拆页/续页信号则豁免
            if re.search(r'(续|续表|01[ab]|02[ab]|part\s*[12]|跟进|详见下页)', b, re.I):
                continue
            b_clean = re.sub(r'<script\b[\s\S]*?</script>', ' ', b)
            b_clean = re.sub(r'<style\b[\s\S]*?</style>', ' ', b_clean)
            plen = len(_plain(b_clean).strip())
            u = _band_heavy_units(b)
            est_h = plen / cpl * fs_px * LINE_FACTOR + u * UNIT_PX + SHEAD_PX
            if est_h > SCREEN_BUDGET_PX * 1.08:
                overflow_hits.append(f"第{i}页≈{est_h:.0f}px 无拆页/换形态信号")
    chk("LAYOUT_QA_OVERFLOW_NO_SPLIT 溢出须拆页/换形态（禁硬塞）",
        not overflow_hits, "; ".join(overflow_hits[:3]) if overflow_hits else "")

    # ⑧ 半空卡 vs 塞爆：同页多卡时过半卡正文过短
    he = (LC.get('qualityGates') or {}).get('halfEmpty') or {}
    half_hits = []
    min_cards = int(he.get('minCards') or 3)
    short_n = int(he.get('shortPlainChars') or 12)
    max_ratio = float(he.get('maxShortRatio') or 0.5)
    for i, b, head in content:
        cards = re.findall(r'class="[^"]*\bcard\b[^"]*"[^>]*>([\s\S]*?)(?=<div class="[^"]*\bcard\b|</section>|$)', b)
        if len(cards) < min_cards:
            # also count .card blocks via simpler split
            cards = re.split(r'class="[^"]*\bcard\b', b)[1:]
        if len(cards) < min_cards:
            continue
        shorts = 0
        for c in cards:
            plen = len(_plain(c[:800]).strip())
            if plen < short_n:
                shorts += 1
        if shorts / max(len(cards), 1) > max_ratio and shorts >= 2:
            half_hits.append(f"第{i}页半空卡 {shorts}/{len(cards)}")
    chk("LAYOUT_QA_HALF_EMPTY 半空卡过多（与塞爆同样不合格）",
        not half_hits, "; ".join(half_hits[:3]) if half_hits else "",
        level="WARN")

    # ⑨ 列对齐节奏：同页多个 grid 混排却完全无对齐 token（加强 LAYOUT_ALIGN）
    align_cfg = (LC.get('layoutSystem') or {}).get('align') or {}
    rhythm_hits = []
    if align_cfg.get('requireColumnRhythm', True):
        tokens = set(align_cfg.get('mixedGridClasses') or ['a-start', 'a-c', 'a-end'])
        for i, b, head in content:
            mixed = _mixed_grid_needs_align(b)
            has_align = any(re.search(r'\b' + re.escape(tok) + r'\b', b) for tok in tokens)
            if mixed and not has_align:
                rhythm_hits.append(f"第{i}页混排缺对齐类")
    chk("LAYOUT_QA_ALIGN_RHYTHM 混排列节奏/共享对齐类",
        not rhythm_hits, "; ".join(rhythm_hits[:3]) if rhythm_hits else "")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    if sys.argv[1] in ('-h', '--help'):
        print(__doc__)
        return 0
    path = Path(sys.argv[1])
    strict = '--strict' in sys.argv
    as_json = '--json' in sys.argv
    layout_qa = '--layout-qa' in sys.argv
    # Mode A / presentation：--strict 隐含 --layout-qa（正式演示交付不漏 V 契约）
    # research/architecture 不自动开启，避免污染密排/架构路径
    if not path.exists():
        print(f"文件不存在: {path}")
        return 2
    try:
        txt = path.read_text(encoding='utf-8')
    except UnicodeDecodeError as e:
        print(f"文件不是合法 UTF-8: {path}（{e}）")
        return 2
    except OSError as e:
        print(f"无法读取文件: {path}（{e}）")
        return 2

    v = Struct()
    v.feed(txt)

    results = []

    def chk(name, ok, note="", level="FAIL"):
        results.append((level, name, bool(ok), note))

    # ── 结构 ──
    chk("HTMLParser 结构 0 未闭合", not v.stack, f"剩余 {v.stack}" if v.stack else "")
    chk("HTMLParser 0 失配/游离", not v.mis and not v.err,
        f"mis={v.mis} err={v.err}" if (v.mis or v.err) else "")

    # ── 主题与风格 ──
    chk("data-style 已指定风格", 'data-style="' in txt)
    chk('data-theme="light" + dark 变量块',
        'data-theme="light"' in txt and '[data-theme="dark"]' in txt)
    chk("主题切换按钮 + localStorage + prefers-color-scheme",
        'id="themeBtn"' in txt and 'localStorage' in txt and 'prefers-color-scheme' in txt)

    # ── 模式 ──
    mode_m = re.search(r'<html[^>]*data-mode="([^"]+)"', txt)
    mode = mode_m.group(1) if mode_m else None
    chk("data-mode 已声明模式（presentation/research/architecture）",
        mode in MODE_BUDGETS,
        f"读到 {mode!r}（未声明按 presentation 处理）" if mode not in MODE_BUDGETS else "",
        level="WARN" if mode is None else "FAIL")
    mode = mode if mode in MODE_BUDGETS else 'presentation'
    if strict and mode == 'presentation' and not layout_qa:
        layout_qa = True  # presentation + --strict → 自动 layout-qa

    # ── 宽屏与页面高度模型 ──
    B0 = MODE_BUDGETS[mode]
    _w = B0['wrap']
    chk(f"版心 --wrap: {_w}px（{mode} 模式）",
        f'--wrap:{_w}px' in txt or f'--wrap: {_w}px' in txt)
    _check_page_model(txt, chk, mode)
    chk("scroll-snap 翻页停靠", 'scroll-snap-type' in txt)

    # ── 翻页与大纲 ──
    chk("翻页 JS（方向键 + scrollIntoView）",
        'scrollIntoView' in txt and 'ArrowRight' in txt)
    chk("页码指示 pager", 'pager__dot' in txt and 'id="pagerDots"' in txt)
    has_agenda = 'id="agenda"' in txt
    if mode == 'architecture':
        # architecture 极简形态：内容页 ≤4 时省略 Agenda 合法（封面/收尾/参考资料不计内容页）
        struct_ids = ('agenda', 'next', 'refs', 'appendix')
        bands_a = _bands(txt)
        content_n = 0
        for i, b in enumerate(bands_a):
            if i == 0:
                continue
            if any(f'id="{sid}"' in b[:220] for sid in struct_ids):
                continue
            content_n += 1
        if content_n > 4:
            chk("存在 Agenda 大纲页（architecture 内容页 >4 时建议补）", has_agenda,
                f"内容页 {content_n} 页无 Agenda", level="WARN")
    else:
        chk("存在 Agenda 大纲页", has_agenda)
    if has_agenda:
        band_secs = [m.start() for m in re.finditer(r'<section class="band', txt)]
        agenda_pos = txt.find('id="agenda"')
        second_band_pos = band_secs[1] if len(band_secs) > 1 else -1
        ok_second = (second_band_pos != -1 and
                     band_secs[0] < agenda_pos < (band_secs[2] if len(band_secs) > 2 else len(txt)))
        chk("Agenda 位于第二页", ok_second,
            f"共{len(band_secs)}页 agenda@{agenda_pos} 第2页@{second_band_pos}")
        n_items = txt.count('class="agenda__a"')
        chk("Agenda 条目可点击跳转 (≥4)", n_items >= 4, f"{n_items} 条")
        if n_items > AGENDA_SINGLE_MAX:
            # 只认大纲元素 class（禁被 engine.css 的 .agenda--2col 选择器误伤）
            has_2col = bool(re.search(
                r'<ol\b[^>]*class="[^"]*\bagenda--2col\b', txt)) or bool(re.search(
                r'<ol\b[^>]*class="[^"]*\bagenda\b[^"]*\bagenda--2col\b', txt))
            chk(f"Agenda >{AGENDA_SINGLE_MAX} 条时已用 agenda--2col 双列",
                has_2col, f"{n_items} 条未双列（大纲很多→两排/两列，禁单列撑爆一屏）", level="WARN")
        # R4：Agenda 容量契约——条数超上限须分页/章节级大纲；单条标题限长
        ag_cfg = (LC.get('contentQuality') or {}).get('agenda') or {}
        split_max = int(ag_cfg.get('splitMax') or 16)
        title_max = int(ag_cfg.get('titleMaxChars') or 36)
        chk(f"Agenda 条数 ≤{split_max}（大纲=章，3–7 条；超出说明在列页，请归并回章）",
            n_items <= split_max,
            f"{n_items} 条超上限——PPTX 已自动分页，HTML 会撑出一屏，建议改章节级大纲 6–8 条")
        long_titles = re.findall(r'class="agenda__t"[^>]*>([^<]{%d,})' % (title_max + 1), txt)
        chk(f"Agenda 单条标题 ≤{title_max} 字", not long_titles,
            f"{len(long_titles)} 条超长：{long_titles[:3]}…" if long_titles else "", level="WARN")

    # ── 主标题粗体 ──
    chk("主标题粗体 --fw-title/--fw-display",
        ('--fw-title' in txt and 'font-weight:var(--fw-title)' in txt) or
        re.search(r'\.t-h1\{[^}]*font-weight:\s*(600|700)', txt))

    # ── 零外链 ──
    ext = re.findall(r'<(?:link|script)[^>]+(?:href|src)=["\']https?://[^"\']+', txt)
    chk("无 <link>/<script src> 外链", not ext, f"{len(ext)} 处" if ext else "")
    img_ext = re.findall(r'<img[^>]+src=["\']https?://', txt)
    chk("无外链图片", not img_ext, f"{len(img_ext)} 处" if img_ext else "")

    # ── 引用与锚点闭环 ──
    # 编号须匹配多位数：`ref-\d` 会让 ref-10 及以后的条目在两侧同时落空，
    # 使双向对齐检查在 ≥10 条引用时静默通过（假阴性）。
    cites = re.findall(r'class="cite" href="#(ref-\d+)"', txt)
    refs = re.findall(r'id="(ref-\d+)"', txt)
    if cites or refs:
        chk("引用标记 ↔ 参考资料条目 双向对齐", set(cites) == set(refs),
            f"引用{sorted(set(cites))} 条目{sorted(set(refs))}")
        nums = sorted(int(r.split('-')[1]) for r in set(refs))
        chk(f"参考资料编号连续（1..{len(nums)} 无跳号）", nums == list(range(1, len(nums) + 1)),
            f"读到 {nums}" if nums != list(range(1, len(nums) + 1)) else "")
    else:
        chk("引用标记 ↔ 参考资料条目 双向对齐", True, "（无外部引用）", level="WARN")
    bad_links = re.findall(r'<a class="ref-link"(?![^>]*target="_blank")[^>]*>', txt) + \
                re.findall(r'<a class="ref-link"(?![^>]*rel="noopener")[^>]*>', txt)
    chk('.ref-link 均带 target="_blank" rel="noopener"', not bad_links,
        f"{len(bad_links)} 处" if bad_links else "")
    _check_anchors(txt, chk)

    # ── 单一强调色（色值表来自 layout-constants.json styleAccents 单源） ──
    style_m = re.search(r'<html[^>]*data-style="([^"]+)"', txt)
    style = style_m.group(1) if style_m else 'business-blue'
    body_txt = txt[txt.find('</style>'):] if '</style>' in txt else txt
    body_txt = re.sub(r'<script\b[\s\S]*?</script>', ' ', body_txt)
    if STYLE_ACCENTS:
        own = STYLE_ACCENTS.get(style, set())
        others = ALL_ACCENTS - own
        bad_hues = [h for h in others if h in body_txt.lower()]
        if style == 'spectrum':
            chk("彩色模块边界（spectrum：数据色限 c1–c5，无其它风格强调色）", not bad_hues,
                f"残留 {bad_hues}" if bad_hues else "")
        else:
            chk(f"单一强调色（{style}，正文无第二色相）", not bad_hues,
                f"残留 {bad_hues}" if bad_hues else "")

    hard_hex = re.findall(r'style="[^"]*(?:color|background|border-color|fill|stroke)\s*:\s*#',
                          body_txt)
    chk("正文无内联写死 hex 色（用 var()/语义类）", not hard_hex,
        f"{len(hard_hex)} 处" if hard_hex else "", level="WARN")

    # ── 内容与密度 ──
    paras = re.findall(r'<p class="t-body"[^>]*>(.*?)</p>', txt, re.S)
    long_paras = [x for x in paras if len(re.sub(r'<[^>]+>', '', x).strip()) > 110]
    chk("卡片内无超 110 字纯段落（应转列表）", not long_paras,
        f"{len(long_paras)} 段" if long_paras else "")
    _check_bands(txt, chk, mode)
    _check_table_rows(txt, chk, mode)
    _check_mode_layouts(txt, chk, mode)
    if mode != 'architecture':
        _check_icons(txt, chk)
        _check_icon_refs(txt, chk)
    _check_pptx_export(txt, chk)
    model = _check_model_consistency(txt, chk, mode, style)
    _check_content_coverage(txt, chk, model)
    _check_type_features(txt, chk, model)
    _check_exhibits(txt, chk, mode)
    _check_research_extras(txt, chk, mode)
    _check_emphasis(txt, chk)
    _check_annotations(txt, chk, model)
    _check_media(txt, chk, model)

    if mode == 'research':
        STRUCT = ('报告大纲', '大纲', '参考资料', '数据来源', '下一步', '结论', '全文核心', 'agenda', '附录')
        h1s = re.findall(r'<h2 class="t-h1 shead__title"[^>]*>(.*?)</h2>', txt)
        short = [re.sub(r'<[^>]+>', '', h).strip() for h in h1s]
        short = [h for h in short if 0 < len(h) < 12 and not h.lower().startswith(STRUCT)]
        chk("research 行动标题（章节主标题 ≥12 字，标题即结论）", not short,
            f"过短: {short[:3]}" if short else "", level="WARN")

    if mode == 'presentation':
        # Mode A：主张/行动句标题（action title）；纯话题标签 WARN（硬 FAIL 过脆）
        STRUCT_A = ('报告大纲', '大纲', '议程', 'Agenda', '参考资料', '下一步', '结论',
                    '封面', '目录', '附录', '谢谢', 'Thank', 'Q&A', '问答')
        TOPIC_ONLY = (
            '现状分析', '市场格局', '风险与挑战', '背景介绍', '项目概述', '总结',
            '概览', '概述', '简介', '背景', '方案', '规划', '进展', '回顾',
            '分析', '对比', '数据', '附录', '下一步计划', '内容', '主题',
        )
        h1s_a = re.findall(r'<h2 class="t-h1 shead__title"[^>]*>(.*?)</h2>', txt)
        titles_a = [re.sub(r'<[^>]+>', '', h).strip() for h in h1s_a]
        topic_hits = []
        for h in titles_a:
            if not h or any(h.startswith(s) or h == s for s in STRUCT_A):
                continue
            # 纯话题：命中话题词表，或极短且无判断/数字/动词痕迹
            if h in TOPIC_ONLY or (len(h) <= 6 and not re.search(
                    r'\d|是|应|须|将|已|要|可|能|达|超|降|升|破|卡|成|未|无|有', h)):
                topic_hits.append(h)
        chk("presentation 主张/行动标题（禁纯话题标签）", not topic_hits,
            f"话题式: {topic_hits[:4]}" if topic_hits else "", level="WARN")

    _check_content_quality(txt, chk, mode, model)
    _check_v9_hard_gates(txt, chk, model)
    _check_layout_grammar(txt, chk, mode)
    if layout_qa:
        _check_layout_qa(txt, chk, mode, model)

    # ── 去AI味（词表来自单源） ──
    body_plain = _plain(body_txt)
    hits = [w for w in AI_FLAVOR if re.search(w, body_plain)]
    chk("去AI味（无高危 AI 腔词汇）", not hits, f"命中 {hits}" if hits else "", level="WARN")

    # ── 图表 ──
    _check_charts(txt, chk)
    _check_chart_variety(txt, chk, mode)

    # ── 汇总 ──
    n_fail = sum(1 for lv, _, ok, _ in results if not ok and lv == "FAIL")
    n_warn = sum(1 for lv, _, ok, _ in results if not ok and lv == "WARN")
    n_pass = sum(1 for _, _, ok, _ in results if ok)
    verdict = "通过，可交付" if n_fail == 0 and (not strict or n_warn == 0) else \
              ("有警告" if n_fail == 0 else "不通过，需修复后重跑")
    exit_code = 1 if (n_fail > 0 or (strict and n_warn > 0)) else 0

    if as_json:
        print(json.dumps({
            "file": str(path),
            "strict": strict,
            "pass": n_pass, "warn": n_warn, "fail": n_fail,
            "verdict": verdict,
            "checks": [{"level": lv, "name": nm, "ok": ok, "note": nt}
                       for lv, nm, ok, nt in results],
        }, ensure_ascii=False, indent=2))
        return exit_code

    W = 68
    print("=" * W)
    print(f"TopPPT HTML· 质量校验 {LC.get('version', '')}  {'[STRICT]' if strict else ''}")
    print(f"文件: {path.name}  ({len(txt.encode('utf-8'))/1024:.1f} KB)")
    print("=" * W)
    for level, name, ok, note in results:
        tag = "PASS" if ok else ("WARN" if level == "WARN" else "FAIL")
        line = f"[{tag}] {name}"
        if note and not ok:
            line += f"  -> {note}"
        print(line)
    print("-" * W)
    print(f"PASS {n_pass}  WARN {n_warn}  FAIL {n_fail}")
    print(f"结论: {verdict}")
    if exit_code != 0:
        _print_fix_guide(results, strict, W)
    print("=" * W)
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
