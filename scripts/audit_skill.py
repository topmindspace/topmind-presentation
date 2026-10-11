#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TopPPT HTML · 技能工程审计（零依赖 · 体积预算 / 渐进式披露 / 触发门禁 / 冗余）

用法:
    python scripts/audit_skill.py            # 全量审计
    python scripts/audit_skill.py --quiet    # 仅打印结论
    python scripts/audit_skill.py --json     # 机器可读

为什么需要它（第一性原理）:
    技能的成本 = **加载进上下文的字节数** + **必须执行的步骤数**。这两项在 v7.1 完全无预算、
    无门禁，导致"技能越做越全 → 单次生成越慢越贵"。本脚本把「效率目标」变成可检查项。

审计项（任一不过 → 退出码 1）:
  ① 体积预算   —— SKILL.md / 常读入口 playbook.md / 单份 reference / 模式模板 的上限
  ② 元数据     —— frontmatter name 与技能名一致；description ≤ DESC_HARD/SOFT；可选 license/compatibility/metadata（开放标准）
  ③ 披露分层   —— SKILL.md 必须声明 L0/L1/L2 三档，且 L1（常读入口）恰好 1 份
  ④ 交互门禁   —— SKILL.md 必须含「Gate 0 参考图先行」，且其出现位置在「六项问询」之前；若声明 Fast Mode，须同时有豁免句且标准路径仍为硬门禁
  ⑤ 效率预算   —— SKILL.md 必须显式声明交互轮次上限与必读文件数上限
  ⑥ 引用完整性 —— SKILL.md 与 playbook.md 提到的 references/*.md 必须存在
  ⑦ 冗余报告   —— SKILL.md ↔ 全部 references（含 playbook）的归一化共同片段
                 （≥20 字含 CJK；命令行/路径等纯 ASCII 重复豁免）
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from package_skill import DESC_LIMIT, NAME  # noqa: E402  复用进包门禁的同一常量

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / 'references'
TPL = ROOT / 'assets' / 'templates'
QUIET = '--quiet' in sys.argv[1:]
AS_JSON = '--json' in sys.argv[1:]

# ── 效率预算（唯一来源；调整预算改这里）──────────────────────────────────
BUDGET = {
    'skill_md': 13 * 1024,        # 入口路由：加载即占上下文，必须瘦（v8.3 从 16KB 收紧：SKILL.md 瘦身后 12.4KB + 余量）
    'playbook': 22 * 1024,        # 唯一常读入口（决策层：模式/版式/图表/配色/校验）
    'reference': 96 * 1024,       # 单份深度文件上限
    'template': 320 * 1024,       # 模式模板（引擎+运行时内联，天然大；靠 scaffold 脚本避免被读）
    'desc_soft': 700,             # description 软上限（触发精度）
    'desc_hard': DESC_LIMIT,      # description 硬上限（宿主规范）
    'l1_files': 1,                # 常读入口份数
}
PLAYBOOK = REF / 'playbook.md'

# 「内容两处维护」检测：归一化滑窗子串（v8.3 起）。
# 旧实现只切 ≥40 字整句且**排除 playbook** —— 表格行/公式/判定条件全部漏检。
# 新实现：整库归一化（去空白与 markdown 修饰符）后做滑窗子串匹配，
# 窗口须含 CJK（纯 ASCII 的命令行/路径重复属工具语义，豁免）。
_NORM_STRIP = re.compile(r'[`*_#>\[\]()|:：,，。;；\s·—\-–/\\="「」『』（）]')
_CJK = re.compile(r'[\u4e00-\u9fff]')
DUP_WIN = 20       # 共同片段最小归一化长度（<20 的短语级重合属合理摘要，放行）
DUP_MAX = 0        # 允许的重复片段上限（S2-1 瘦身后应为 0）


def norm_text(text: str) -> str:
    return _NORM_STRIP.sub('', text)


def dup_spans(sk_text: str, refs_text: str) -> list[str]:
    """返回 SKILL.md 与 references 的共同归一化片段（合并相邻窗口）。"""
    a, b = norm_text(sk_text), norm_text(refs_text)
    ranges: list[tuple[int, int]] = []
    i = 0
    while i + DUP_WIN <= len(a):
        w = a[i:i + DUP_WIN]
        if _CJK.search(w) and w in b:
            p = b.find(w)
            lo, hi = i, i + DUP_WIN
            # 命中后向两侧扩展到最长共同片段（闭合步长 4 的对齐缺口）
            while lo > 0 and p > 0 and a[lo - 1] == b[p - 1]:
                lo -= 1
                p -= 1
            hi_b = p + DUP_WIN
            while hi < len(a) and hi_b < len(b) and a[hi] == b[hi_b]:
                hi += 1
                hi_b += 1
            if ranges and lo <= ranges[-1][1]:
                ranges[-1] = (ranges[-1][0], hi)
            else:
                ranges.append((lo, hi))
            i = hi  # 跳过已覆盖区间（顺带提速）
        else:
            i += 4
    return [a[lo:hi] for lo, hi in ranges]


def kb(n: int) -> str:
    return f'{n / 1024:.1f}KB'


def main() -> int:
    errs: list[str] = []
    notes: list[str] = []
    rows: list[tuple[str, bool, str]] = []

    def chk(name: str, ok: bool, bad_detail: str, ok_detail: str | None = None,
            fatal: bool = True) -> None:
        """bad_detail 用于失败说明；ok_detail 用于通过说明（缺省复用 bad_detail）。"""
        detail = (ok_detail if (ok and ok_detail is not None) else bad_detail)
        rows.append((name, ok, detail))
        if not ok:
            (errs if fatal else notes).append(f'{name}: {bad_detail}')

    sk_path = ROOT / 'SKILL.md'
    sk = sk_path.read_text(encoding='utf-8')

    # ① 体积预算
    sk_size = sk_path.stat().st_size
    chk('① SKILL.md 体积', sk_size <= BUDGET['skill_md'],
        f'{kb(sk_size)} / 上限 {kb(BUDGET["skill_md"])}')

    pb_size = PLAYBOOK.stat().st_size if PLAYBOOK.exists() else -1
    chk('① 常读入口 playbook.md', 0 < pb_size <= BUDGET['playbook'],
        f'{kb(pb_size)} / 上限 {kb(BUDGET["playbook"])}' if pb_size > 0
        else f'缺失（应存在且 ≤ {kb(BUDGET["playbook"])}）')

    over_ref = [(p.name, p.stat().st_size) for p in sorted(REF.glob('*.md'))
                if p.stat().st_size > BUDGET['reference']]
    chk('① 单份 reference 体积', not over_ref,
        '; '.join(f'{n} {kb(s)}' for n, s in over_ref) or
        f'最大 {kb(max((p.stat().st_size for p in REF.glob("*.md")), default=0))} / 上限 {kb(BUDGET["reference"])}')

    over_tpl = [(p.name, p.stat().st_size) for p in sorted(TPL.glob('*.html'))
                if p.stat().st_size > BUDGET['template']]
    chk('① 模式模板体积', not over_tpl,
        '; '.join(f'{n} {kb(s)}' for n, s in over_tpl) or
        f'最大 {kb(max((p.stat().st_size for p in TPL.glob("*.html")), default=0))} / 上限 {kb(BUDGET["template"])}')

    # ② 元数据
    d = re.search(r'^description:\s*"(.*)"\s*$', sk, re.M)
    dlen = len(d.group(1)) if d else -1
    nm = re.search(r'^name:\s*(\S+)\s*$', sk, re.M)
    chk('② name 一致', bool(nm) and nm.group(1) == NAME,
        f'name={nm.group(1) if nm else "缺失"}（应为 {NAME}）')
    chk('② description 硬上限', 0 < dlen <= BUDGET['desc_hard'],
        f'{dlen} / 上限 {BUDGET["desc_hard"]}')
    chk('② description 软上限（触发精度）', 0 < dlen <= BUDGET['desc_soft'],
        f'{dlen} / 建议 ≤ {BUDGET["desc_soft"]}')

    # ②b 开放标准可选 frontmatter（允许额外键；校验存在与粗约束）
    lic = re.search(r'^license:\s*(.+)$', sk, re.M)
    chk('② license', bool(lic) and 'MIT' in (lic.group(1) if lic else ''),
        '缺 license: MIT（开放标准可选，本技能应对齐 package.json）',
        'license=MIT')
    compat = re.search(r'^compatibility:\s*"(.*)"\s*$', sk, re.M | re.S)
    clen = len(compat.group(1)) if compat else -1
    chk('② compatibility', 0 < clen <= 500,
        f'compatibility 缺失或超 500 字符（{clen}）',
        f'{clen} 字符')
    meta_ver = re.search(r'^\s*version:\s*"?([\w.\-]+)"?\s*$', sk, re.M)
    meta_author = re.search(r'^\s*author:\s*(\S+)\s*$', sk, re.M)
    pkg_ver = ''
    try:
        import json as _json
        pkg_ver = str(_json.loads((ROOT / 'package.json').read_text(encoding='utf-8')).get('version') or '')
    except Exception:
        pass
    chk('② metadata.version', bool(meta_ver) and (not pkg_ver or meta_ver.group(1) == pkg_ver),
        f'metadata.version 缺失或与 package.json 不一致（fm={meta_ver.group(1) if meta_ver else None} pkg={pkg_ver})',
        f'{meta_ver.group(1) if meta_ver else "?"}')
    chk('② metadata.author', bool(meta_author),
        '缺 metadata.author',
        meta_author.group(1) if meta_author else '')

    # ③ 渐进式披露分层（机器可读标记：L0=… · L1=… · L2=…）
    # Prefer machine-readable disclosure marker `L1=references/...`（忽略正文「L0+L1 共 2」等）
    m_l1 = re.search(r'L1\s*=\s*`?(references/[a-z0-9\-./]+\.md)`?', sk)
    if not m_l1:
        m_l1 = re.search(r'L1\s*=\s*`?([^`\s·|]+)`?', sk)
    has_l0 = bool(re.search(r'L0\s*=\s*`?SKILL', sk)) or bool(re.search(r'`L0=SKILL', sk))
    has_l2 = bool(re.search(r'L2\s*=', sk))
    l1_files = [f.strip() for f in re.split(r'[,、]', m_l1.group(1)) if f.strip()] if m_l1 else []
    chk('③ 披露分层 L0/L1/L2', has_l0 and has_l2 and len(l1_files) == BUDGET['l1_files'],
        f'L0={has_l0} L1={l1_files} L2={has_l2}（L1 须恰好 {BUDGET["l1_files"]} 份）')
    chk('③ 常读入口存在', bool(l1_files) and all((ROOT / f).exists() for f in l1_files),
        f'L1={l1_files} 不存在', f'{l1_files} 存在')

    # ④ Gate 0（参考图先行）——标准路径硬门禁；Fast Mode 可声明豁免
    g0 = sk.find('Gate 0')
    ask = sk.find('六项问询')
    has_fast = bool(re.search(r'Fast\s*Mode|快速模式', sk))
    chk('④ Gate 0 存在', g0 >= 0, '未找到「Gate 0」标记', '已就位')
    chk('④ Gate 0 在问询之前', g0 >= 0 and ask >= 0 and g0 < ask,
        f'Gate0@{g0} 未在六项问询@{ask} 之前', f'位置正确（{g0} < {ask}）')
    if has_fast:
        ok_exempt = bool(re.search(
            r'(?:Fast\s*Mode|快速模式).{0,400}(?:跳过|豁免).{0,120}(?:Gate\s*0|参考图|六项)',
            sk, re.S)) or bool(re.search(
            r'(?:跳过|豁免).{0,60}(?:Gate\s*0|参考图|六项问询)', sk))
        chk('④ Fast Mode 豁免声明', ok_exempt,
            '有 Fast Mode 但未声明 Gate 0/六项豁免', '已声明豁免')
        ok_std = bool(re.search(r'标准.{0,24}(?:硬门禁|强制)|Gate\s*0.{0,48}硬门禁', sk))
        chk('④ 标准路径 Gate 0 仍为硬门禁', ok_std,
            '有 Fast Mode 但标准路径未保留 Gate 0 硬门禁表述', '已保留')

    # ⑤ 效率预算声明
    chk('⑤ 交互轮次预算', bool(re.search(r'交互轮次|轮次上限|≤\s*3\s*轮', sk)),
        'SKILL.md 未声明交互轮次上限', '已声明（≤3 轮）')
    chk('⑤ 必读文件预算', bool(re.search(r'必读.{0,6}上限|必读文件数|只读当前需要的|不预读', sk)),
        'SKILL.md 未声明必读文件预算/不预读纪律', '已声明（不预读纪律）')
    # ⑤b 反过读硬门禁文案（整读大 L2 = FAIL）+ B 通道交付口径
    ok_snip = bool(re.search(r'extract_snippet', sk)) and bool(
        re.search(r'整读.{0,40}(?:FAIL|不合格)|(?:FAIL|不合格).{0,40}整读', sk))
    chk('⑤ extract_snippet 整读=FAIL', ok_snip,
        'SKILL.md 须同时声明 extract_snippet 与「整读…FAIL/不合格」',
        '已声明 FAIL 口径')
    ok_b = bool(re.search(r'B\s*通道|build_pptx', sk)) and bool(
        re.search(r'A\s*通道|pptx-export|cross_verify', sk))
    chk('⑤ B 通道交付 / A 预览', ok_b,
        'SKILL.md 须区分 B 通道交付与 A 通道预览/cross_verify',
        '已区分')

    # ⑥ 引用完整性
    missing: list[str] = []
    n_refs = 0
    for src, text in (('SKILL.md', sk),
                      ('references/playbook.md',
                       PLAYBOOK.read_text(encoding='utf-8') if PLAYBOOK.exists() else '')):
        for rel in sorted(set(re.findall(r'references/([a-z0-9\-]+\.md)', text))):
            n_refs += 1
            if not (REF / rel).exists():
                missing.append(f'{src} → references/{rel}')
    chk('⑥ 引用文件存在', not missing, '; '.join(missing),
        f'{n_refs} 处引用全部存在')

    # ⑦ 冗余报告（SKILL.md ↔ 全部 references，含 playbook；归一化滑窗子串）
    refs_all = '\n'.join(p.read_text(encoding='utf-8') for p in sorted(REF.glob('*.md')))
    dup = dup_spans(sk, refs_all)
    chk('⑦ 内容重复（SKILL.md ↔ references · 归一化 ≥%d 字）' % DUP_WIN,
        len(dup) <= DUP_MAX,
        f'{len(dup)} 处重复' + (f'：{dup[0][:40]}…' if dup else ''),
        f'0 处重复（≥{DUP_WIN} 字归一化片段）')

    # ── 输出 ────────────────────────────────────────────────────────────────
    if AS_JSON:
        print(json.dumps({'rows': [{'item': r[0], 'ok': r[1], 'detail': r[2]} for r in rows],
                          'errors': errs, 'notes': notes}, ensure_ascii=False, indent=2))
        return 1 if errs else 0
    if not QUIET:
        print('技能工程审计 · 效率预算与门禁\n' + '-' * 56)
        for n, ok, det in rows:
            print(f'  {"✓" if ok else "✗"} {n}：{det}')
        if notes:
            print('\n提示（不判失败）：')
            for n in notes:
                print(f'  · {n}')
        print('-' * 56)
    if errs:
        print(f'技能工程审计未通过：{len(errs)} 项')
        for e in errs:
            print(f'  ✗ {e}')
        return 1
    print('技能工程审计通过：体积达标 · 元数据合规 · 三档披露 · Gate 0 就位 · 预算已声明')
    return 0


if __name__ == '__main__':
    sys.exit(main())
