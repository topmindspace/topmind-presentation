#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TopPPT HTML · 风格与单源质量审计工具：
① WCAG 对比度：9 风格 × light/dark 的关键 token 配对（MD3/WCAG 阈值）
② 双源一致性：engine.css（HTML 侧 token）vs layout-constants.json（PPTX 侧 token）
③ 单源完整性：styleAccents 覆盖各风格 light/dark 强调色；charts.minSize ⊆ charts.types；
   图表最小尺寸键名合法（pxWidthMin / vbHeightMin）
用法：python scripts/audit_styles.py（改任何风格色值或常量后必跑；退出码 0 = 全部通过）
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(__file__).resolve().parent.parent
CSS = (ROOT / 'assets' / 'templates' / 'engine.css').read_text(encoding='utf-8')
LC = json.loads((ROOT / 'scripts' / 'layout-constants.json').read_text(encoding='utf-8'))


def parse_block(block):
    toks = {}
    for m in re.finditer(r'--([\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})', block):
        toks[m.group(1)] = m.group(2).lower()
    return toks


def parse_css():
    """返回 {style: {'light': toks, 'dark': toks}}。
    9 套风格均有显式 html[data-style="X"]{...}（light）与
    html[data-style="X"][data-theme="dark"]{...}（dark）两块；:root 仅作无 data-style 时的默认值。"""
    styles = {}
    pat = re.compile(r'html\[data-style="([\w-]+)"\](?:\[data-theme="dark"\])?\{([\s\S]*?)\}')
    for m in pat.finditer(CSS):
        sid, body = m.group(1), m.group(2)
        sel = m.group(0).split('{', 1)[0]
        side = 'dark' if 'data-theme="dark"' in sel else 'light'
        # 同一 (风格, 主题) 可能由多个块叠加（基础 token 块 + 编码色板块）→ 合并而非覆盖
        styles.setdefault(sid, {}).setdefault(side, {}).update(parse_block(body))
    return styles


def rel_lum(hexc):
    h = hexc.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    def f(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = f(r), f(g), f(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = rel_lum(a), rel_lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def hex2rgb(h):
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb2hls(r, g, b):
    """返回 (色相°, 饱和, 明度) —— 用于编码色板两两可区分性判定。"""
    r, g, b = r / 255, g / 255, b / 255
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2
    if mx == mn:
        return 0.0, 0.0, l
    d = mx - mn
    s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
    if mx == r:
        h = ((g - b) / d) % 6
    elif mx == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    return h * 60, s, l


CHECKS = [
    # (名称, token对, 阈值)  阈值依据：WCAG AA 正文 4.5 / 大字与图形 3.0
    ('正文 text / bg',            ('text', 'bg'),           4.5),
    ('次级 text-2 / bg',          ('text-2', 'bg'),         4.5),
    ('弱化 text-3 / bg（注解）',   ('text-3', 'bg'),         3.0),
    ('强调文字 accent-text / bg',  ('accent-text', 'bg'),    4.5),
    ('强调色 accent / bg（图形）', ('accent', 'bg'),         3.0),
    ('按钮文字 accent-on / accent', ('accent-on', 'accent'), 4.5),
    ('正文 text / surface-1',     ('text', 'surface-1'),    4.5),
    ('次级 text-2 / surface-1',   ('text-2', 'surface-1'),  4.5),
]


def audit_contrast(styles):
    fails = []
    for sid in sorted(styles):
        for theme in ('light', 'dark'):
            t = styles[sid].get(theme)
            if not t or 'bg' not in t:
                continue
            for name, (fg, bg), th in CHECKS:
                if fg not in t or bg not in t:
                    continue
                c = contrast(t[fg], t[bg])
                if c < th:
                    fails.append(f'{sid}.{theme}: {name} = {c:.2f} < {th} ({t[fg]} on {t[bg]})')
    return fails


def audit_consistency(styles, lc_styles, side='light', lc_key='styles'):
    """PPTX 常量（layout-constants.json）与 CSS token 的映射对照（归一化 # 前缀与 3 位缩写）。
    side='dark' 时对照 stylesDark ↔ engine.css 深色块（PPTX 深色导出与 HTML 深色主题同源）。"""
    def norm(v):
        v = (v or '').lower().lstrip('#')
        if len(v) == 3:
            v = ''.join(c * 2 for c in v)
        return v
    MAP = [('ink', 'text'), ('body', 'text-2'), ('faint', 'text-3'),
           ('bg', 'bg'), ('surface', 'surface-1'), ('line', 'border'),
           ('accent', 'accent'), ('onAccent', 'accent-on'), ('soft', 'accent-soft')]
    diffs = []
    for sid, pt in lc_styles.items():
        css = styles.get(sid, {}).get(side, {})
        for jk, ck in MAP:
            jv, cv = norm(pt.get(jk)), norm(css.get(ck))
            if jv and cv and jv != cv:
                diffs.append(f'{sid}.{side}: JSON.{jk}={jv} != CSS.{ck}={cv}')
            elif jv and not cv:
                diffs.append(f'{sid}.{side}: CSS 缺 {ck}')
    if not lc_styles:
        diffs.append(f'layout-constants.json 缺 {lc_key}（起 PPTX 深色导出依赖它）')
    return diffs


def audit_data_palette(styles):
    """编码色板审计：9 套风格 × light/dark，各 5 色。
    ① 覆盖完整（styleDataColors / styleDataColorsDark 与 styles / stylesDark 键集一致）
    ② 每套 5 色、与 engine.css 覆盖块逐值一致（双源）
    ③ 每个色对所在主题 bg 的对比度 ≥ 3.0（图形元素可辨下限）
    ④ 同套内两两可区分（色相差 ≥25° 或明度差 ≥0.12）"""
    diffs = []
    for key, theme in (('styleDataColors', 'light'), ('styleDataColorsDark', 'dark')):
        table = {k: v for k, v in (LC.get(key) or {}).items() if not k.startswith('$')}
        base = {k: v for k, v in (LC.get('styles' if theme == 'light' else 'stylesDark') or {}).items()
                if not k.startswith('$')}
        for sid in base:
            if sid not in table:
                diffs.append(f'{key} 缺风格 {sid}')
        for sid, cols in table.items():
            if len(cols) != 5:
                diffs.append(f'{key}.{sid} 色数 {len(cols)} != 5')
                continue
            css = styles.get(sid, {}).get(theme, {})
            for i, c in enumerate(cols, 1):
                if c.startswith('#'):
                    diffs.append(f'{key}.{sid}.c{i}={c} 不得带 # 前缀（会原样流入 OOXML srgbClr val）')
                    continue
                cv = (css.get(f'c{i}') or '').lower().lstrip('#')
                if not cv:
                    diffs.append(f'{key}.{sid}.c{i} 未在 engine.css {theme} 块中定义')
                elif cv != c.lower().lstrip('#'):
                    diffs.append(f'{key}.{sid}.c{i}={c} != engine.css {cv}')
            bg = (base.get(sid) or {}).get('bg') or ('#ffffff' if theme == 'light' else '#000000')
            if not bg.startswith('#'):
                bg = '#' + bg
            for c in cols:
                if contrast(c if c.startswith('#') else '#' + c, bg) < 3.0:
                    diffs.append(f'{key}.{sid}: {c} 对 bg {bg} 对比 {contrast(c, bg):.2f} < 3.0')
            hls = [rgb2hls(*hex2rgb(c)) for c in cols]
            for i in range(5):
                for j in range(i + 1, 5):
                    dh = abs(hls[i][0] - hls[j][0]) % 360
                    dh = min(dh, 360 - dh)
                    if dh < 25 and abs(hls[i][2] - hls[j][2]) < 0.12:
                        diffs.append(f'{key}.{sid}: c{i + 1}/c{j + 1} 不可区分（Δh={dh:.0f}°）')
    return diffs


def audit_style_identity(styles):
    """风格语汇审计：每套风格的 HTML 身份 token 必须落地（字体栈 / 圆角 / 字阶微调 / 链接色）。
    与 layout-constants.json 的 styleIdentity 清单逐项对照，拦「styles.md 写了、engine.css 没落」的漂移。"""
    diffs = []
    ident = {k: v for k, v in (LC.get('styleIdentity') or {}).items() if not k.startswith('$')}
    if not ident:
        return ['layout-constants.json 缺 styleIdentity（风格语汇清单）']
    for sid, rule in ident.items():
        css = styles.get(sid, {}).get('light', {})
        if not css:
            diffs.append(f'styleIdentity.{sid}: engine.css 缺 light 覆盖块')
            continue
        raw = re.search(
            r'html\[data-style="%s"\]\{([\s\S]*?)\}' % re.escape(sid), CSS)
        body = raw.group(1) if raw else ''
        if '--font-body' not in body:
            diffs.append(f'{sid}: 缺 --font-body（风格字体栈未落地）')
        if '--font-display' not in body:
            diffs.append(f'{sid}: 缺 --font-display（标题字体栈未落地）')
        radius = str(rule.get('radius') or '')
        if radius and f'--radius:{radius}' not in body.replace(' ', ''):
            # 允许 --radius: 16px 带空格
            if not re.search(r'--radius:\s*%s' % re.escape(radius), body):
                diffs.append(f'{sid}: --radius 未设为 {radius}')
        if rule.get('serifDisplay'):
            fd = re.search(r'--font-display:\s*([^;]+);', body)
            if not fd or 'serif' not in fd.group(1).lower():
                diffs.append(f'{sid}: serifDisplay=true 但 --font-display 非 serif 栈')
        if rule.get('typeBoost') and '--fs-display' not in body:
            diffs.append(f'{sid}: typeBoost=true 但未覆盖 --fs-display')
        if rule.get('link'):
            if '--link' not in body:
                diffs.append(f'{sid}: 声明 link 但缺 --link token')
            else:
                lv = re.search(r'--link:\s*([^;]+);', body)
                if lv and lv.group(1).strip().lower() != str(rule['link']).lower():
                    diffs.append(f'{sid}: --link={lv.group(1).strip()} != styleIdentity {rule["link"]}')
        le = rule.get('letterEyebrow')
        if le and f'--letter-eyebrow:{le}' not in body.replace(' ', ''):
            if not re.search(r'--letter-eyebrow:\s*%s' % re.escape(le), body):
                diffs.append(f'{sid}: --letter-eyebrow 未设为 {le}')
    for sid in (LC.get('styles') or {}):
        if sid.startswith('$'):
            continue
        if sid not in ident:
            diffs.append(f'styleIdentity 缺风格 {sid}')
    return diffs


def audit_ui_palette():
    """ui.js 的 header 风格下拉色板必须与 layout-constants.json 的 accent 一致
    （ui.js 在运行时块之前执行，无法直接读 PRESETS，故用审计兜住这最后一处手写色值）。"""
    ui = ROOT / 'assets' / 'templates' / 'ui.js'
    if not ui.exists():
        return ['assets/templates/ui.js 不存在']
    txt = ui.read_text(encoding='utf-8')
    m = re.search(r'var STYLES=\[([\s\S]*?)\];', txt)
    if not m:
        return ['ui.js 未找到 var STYLES 色板数组']
    diffs = []
    pairs = re.findall(r"\[\s*'([\w-]+)'\s*,\s*'[^']*'\s*,\s*'(#[0-9a-fA-F]{3,8})'\s*\]", m.group(1))
    if not pairs:
        return ['ui.js STYLES 色板解析失败（格式变化？）']
    for sid, hexv in pairs:
        acc = str(((LC.get('styles') or {}).get(sid) or {}).get('accent') or '')
        if not acc:
            diffs.append(f'ui.js 色板含未知风格 {sid}')
        elif acc.lower().lstrip('#') != hexv.lower().lstrip('#'):
            diffs.append(f'ui.js 色板 {sid} = {hexv} != layout-constants accent #{acc}')
    missing = [s for s in (LC.get('styles') or {}) if s not in {p[0] for p in pairs}]
    for s in missing:
        diffs.append(f'ui.js 色板缺风格 {s}')
    return diffs


def audit_single_source():
    """单源完整性：styleAccents 覆盖 / charts 登记表自洽 / 图表最小尺寸键名合法。"""
    diffs = []
    accents = {k: v for k, v in (LC.get('styleAccents') or {}).items() if not k.startswith('$')}
    for key, side in (('styles', 'light'), ('stylesDark', 'dark')):
        for sid, toks in (LC.get(key) or {}).items():
            acc = str(toks.get('accent') or '').lower().lstrip('#')
            have = {str(x).lower().lstrip('#') for x in (accents.get(sid) or [])}
            if acc and acc not in have:
                diffs.append(f'styleAccents.{sid} 未收录 {side} 强调色 #{acc}（单一强调色检查会漏判）')
    missing = [s for s in (LC.get('styles') or {}) if s not in accents]
    for s in missing:
        diffs.append(f'styleAccents 缺风格 {s}')
    charts = LC.get('charts') or {}
    types = set(charts.get('types') or [])
    for t, rule in (charts.get('minSize') or {}).items():
        if types and t not in types:
            diffs.append(f'charts.minSize.{t} 未登记在 charts.types')
        for k in (rule or {}):
            if k not in ('pxWidthMin', 'vbHeightMin'):
                diffs.append(f'charts.minSize.{t}.{k} 键名非法（应为 pxWidthMin / vbHeightMin）')
    for t in types:
        if t not in (charts.get('minSize') or {}):
            diffs.append(f'charts.types.{t} 缺最小尺寸登记（校验器将跳过该类型）')
    for key in ('checkBudgets', 'styleAccents', 'aiFlavor', 'pageTypeGeometry',
                'styleDataColors', 'styleDataColorsDark'):
        if key not in LC:
            diffs.append(f'layout-constants.json 缺 {key}（validate_report.py 依赖它做单源校验）')
    return diffs


css_styles = parse_css()
n_styles = len(css_styles)
print(f'解析到 {n_styles} 套风格（CSS 侧）')
c_fails = audit_contrast(css_styles)
print('\n── WCAG 对比度审计 ──')
if c_fails:
    for f in c_fails:
        print('  [FAIL]', f)
else:
    print(f'  全部通过（{n_styles} 风格 × light/dark × {len(CHECKS)} 组配对 ≥ WCAG 阈值）')

d_fails = audit_consistency(css_styles, LC['styles'], 'light', 'styles')
print('\n── 双源 token 一致性 · 浅色（engine.css ↔ layout-constants.json styles）──')
if d_fails:
    for f in d_fails:
        print('  [DIFF]', f)
else:
    print(f'  全部一致（{n_styles} 风格 × 9 字段）')

dd_fails = audit_consistency(css_styles, LC.get('stylesDark') or {}, 'dark', 'stylesDark')
print('\n── 双源 token 一致性 · 深色（engine.css dark 块 ↔ layout-constants.json stylesDark）──')
if dd_fails:
    for f in dd_fails:
        print('  [DIFF]', f)
else:
    print(f'  全部一致（{n_styles} 风格 × 9 字段 · PPTX 深色导出与 HTML 深色主题同源）')

s_fails = audit_single_source()
print('\n── 单源完整性（styleAccents / charts 登记表 / 校验预算键）──')
if s_fails:
    for f in s_fails:
        print('  [DIFF]', f)
else:
    n_charts = len((LC.get('charts') or {}).get('types') or [])
    n_acc = len([k for k in (LC.get('styleAccents') or {}) if not k.startswith('$')])
    print(f'  全部一致（强调色表 {n_acc} 套 · 图表登记 {n_charts} 种 · 校验预算 {len([k for k in (LC.get("checkBudgets") or {}) if not k.startswith("$")])} 模式）')

dp_fails = audit_data_palette(css_styles)
print('\n── 编码色板（9 风格 × light/dark × c1–c5 · 双源 + 对比度 + 可区分性）──')
if dp_fails:
    for f in dp_fails:
        print('  [DIFF]', f)
else:
    print(f'  全部通过（{len([k for k in (LC.get("styleDataColors") or {}) if not k.startswith("$")])} 套 × 2 主题 × 5 色）')

u_fails = audit_ui_palette()
print('\n── ui.js 风格下拉色板 ↔ layout-constants.json accent ──')
if u_fails:
    for f in u_fails:
        print('  [DIFF]', f)
else:
    print(f'  全部一致（{n_styles} 套色板 = {n_styles} 套 accent）')

id_fails = audit_style_identity(css_styles)
print('\n── 风格语汇（font / radius / typeBoost / serifDisplay / link · engine.css ↔ styleIdentity）──')
if id_fails:
    for f in id_fails:
        print('  [DIFF]', f)
else:
    n_id = len([k for k in (LC.get('styleIdentity') or {}) if not k.startswith('$')])
    print(f'  全部落地（{n_id} 套风格语汇与 engine.css 覆盖块一致）')

sys.exit(1 if (c_fails or d_fails or dd_fails or s_fails or dp_fails or u_fails or id_fails) else 0)
