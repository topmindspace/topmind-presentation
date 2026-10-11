#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""topmind-presentation · 技能分发包打包器（发布前完整性校验 + 发布清单）

用法:
    python scripts/package_skill.py            # 校验 → 打包 → 写发布清单
    python scripts/package_skill.py --check    # 只校验不打包（CI / 提交前自检）

产物:
    dist/topmind-presentation.zip            分发包（解压目录名 = 技能全名 topmind-presentation）
    dist/topmind-presentation.manifest.json  发布清单（版本 / 条目 / 大小 / SHA-256），随包留档

────────────────────────────────────────────────────────────────────────
进包（= 技能运行与维护所需的最小完备集，缺一即校验失败）
────────────────────────────────────────────────────────────────────────
    SKILL.md                       技能入口（frontmatter + 触发边界 + 工作流 + 铁律）
    README.md                      人类视角的简介 / 安装 / 开发 / 打包
    package.json                   Node 依赖声明（pptxgenjs）与常用命令
    assets/templates/              三份模式模板 + engine.css / ui.js（公共片段注入源）
    assets/icons/                  48 原创图标（SVG + PNG）+ index.json（render_from_model / icon_lib / validate_report 运行时读取）
    assets/examples/               ≥3 黄金样张（每模式 1）+ 可选产品 showcase HTML/model
    assets/pptx-export.js          PPTX 预览运行时（注入源）
    assets/style-gallery.html      风格 × 模式 × 亮暗主题交互画廊
    assets/theme-overview*.png     3 张主题参考图（整体 + research + architecture；演示态与整体图相同）
    references/*.md                规范全文（Batch3 起 ≥20 篇；playbook.md = L1；其余 L2 按需）
    scripts/                         生成 / 校验 / 回归 / 维护工具（py + js + json 单源）
    scripts/extract_snippet.py       L2 节级片段抽取（减少整读大规范）
    # layoutSlots 已并入 layout-constants.json（Batch 3）

────────────────────────────────────────────────────────────────────────
不进包（构建产物 / 本地状态 / 缓存，与 .gitignore 口径一致）
────────────────────────────────────────────────────────────────────────
    dist/                          分发包与回归产物本身
    report-assets/                 prepare_images.py 的产出（片段 / 模型对象）
    render-compare/                render_compare.py 的渲染对照产物
    node_modules/                  npm 依赖（安装期生成）
    __pycache__/                   Python 缓存
    IDE / 智能体本地状态目录                 IDE / 智能体本地状态（不入库、不分发）
    scripts/_*                     下划线开头的临时脚本（用后即删）

────────────────────────────────────────────────────────────────────────
发布前校验（任一不过 → 退出码 1，不产出 zip）
────────────────────────────────────────────────────────────────────────
    · SKILL.md frontmatter 含 name / description；name 与分发包目录名一致；
      description 为单行双引号字符串且 ≤ 1024 字符（平台截断阈值）
    · references（含 layout-grammar）、3 份模式模板 + engine.css / ui.js、≥3 组样张、3 张参考图齐全
    · 关键脚本齐全（单源注入 / 审计 / 示例重建 / 回归 / 双校验器 / 精导 / 打包）
"""
import fnmatch
import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
NAME = 'topmind-presentation'                       # 技能全名 = 分发包顶层目录名 = SKILL.md name
OUT = ROOT / 'dist' / f'{NAME}.zip'
MANIFEST = ROOT / 'dist' / f'{NAME}.manifest.json'
DESC_LIMIT = 1024
# 版本唯一事实源 = SKILL.md frontmatter `metadata.version`（须与 package.json version 一致，见 --check 比对）；
# 回退读 package.json。注意：layout-constants.json 的 `version` 是版式常量版本（0.1），不是技能版本，禁止用作技能版本。
try:
    VERSION = str(json.loads(
        (ROOT / 'package.json').read_text(encoding='utf-8')).get('version') or '0.0')
except (OSError, json.JSONDecodeError):
    VERSION = '0.0'

# 进包清单（显式枚举，缺一即失败）
INCLUDE = [
    'SKILL.md',
    'README.md',
    'package.json',
    'assets/pptx-export.js',
    'assets/style-gallery.html',
    'assets/theme-overview.png',
    'assets/theme-overview-research.png',
    'assets/theme-overview-architecture.png',
    'assets/templates/*',
    'assets/icons/*',
    'assets/examples/*',
    'assets/showcase/*',
    'references/*',
    'scripts/*',
    'evals/*',
    'agents/*',
]

# 出包规则（命中即跳过；与 .gitignore 口径一致）
EXCLUDE = [
    'scripts/_*',                 # 临时脚本
    'scripts/__pycache__/*',
    '**/__pycache__/*',
    '**/node_modules/*',
    '**/report-assets/*',
    '**/render-compare/*',
    '**/dist/*',
    '**/.codebuddy/*',
    '**/.h3caiwork/*',
    '**/.playwright-mcp/*',
    '**/.claude/*',
    '**/.agents/*',
    '**/.mimocode/*',
    '**/OPTIMIZATION-PLAN.md',
]

# 必须齐全的关键文件（发布门禁）
REQUIRED = [
    'SKILL.md', 'README.md', 'package.json',
    'assets/pptx-export.js', 'assets/style-gallery.html',
    'assets/theme-overview.png',
    'assets/theme-overview-research.png', 'assets/theme-overview-architecture.png',
    'assets/templates/presentation.html', 'assets/templates/research.html',
    'assets/templates/architecture.html', 'assets/templates/engine.css',
    'assets/templates/ui.js',
    'assets/icons/index.json',
    'references/playbook.md',
    'references/layout-grammar.md',
    'references/default-surface.md',
    'references/presentation-craft.md',
    'references/illustration-layout.md',
    'references/page-type-matrix.md',
    'references/chart-decision-tree.md',
    'references/modes.md', 'references/outline-design.md', 'references/design-system.md',
    'references/styles.md', 'references/content-rules.md', 'references/components.md',
    'references/charts.md',
    'references/infographics.md', 'references/icons.md', 'references/pptx-export.md',
    'references/high-fidelity.md', 'references/failure-modes.md',
    'references/tech-design.md',
    'scripts/env_probe.py', 'scripts/audit_docs.py', 'scripts/audit_skill.py',
    'scripts/scaffold_report.py',
    'scripts/render_from_model.py',
    'scripts/recommend_layout.py',
    'scripts/sync_runtime.py', 'scripts/audit_styles.py', 'scripts/build_examples.py',
    'scripts/regression.py', 'scripts/validate_report.py', 'scripts/validate_pptx.py',
    'scripts/extract_model.py', 'scripts/build_pptx.js', 'scripts/gen_channel_a.js',
    'scripts/cross_verify.py', 'scripts/prepare_images.py', 'scripts/probe_image_export.py',
    'scripts/render_compare.py', 'scripts/capture_theme_overview.js', 'scripts/package_skill.py',
    'scripts/layout-constants.json', 'scripts/model-schema.json',
    'scripts/lib_layout_regions.js', 'scripts/extract_snippet.py', 'scripts/quality_gate.py',
    'scripts/icon_lib.js', 'scripts/icon_raster.js', 'scripts/build_icon_assets.js',
    'scripts/checks_html.py', 'scripts/section-file-map.json',
    'scripts/measure_height.py', 'scripts/audit_css.py', 'scripts/negative_tests.py',
    'references/components-atoms.md', 'references/layouts-research.md',
    'references/layouts-architecture.md', 'references/layouts-combo.md',
    'references/charts-basic.md', 'references/charts-extended.md', 'references/charts-discipline.md',
    'references/infographics-stats.md', 'references/infographics-structure.md',
    'evals/prompts.csv', 'evals/run_evals.py', 'evals/rubric.schema.json',
    'evals/trace.example.json',
    'evals/trigger-queries.json',
    'scripts/check_triggers.py',
]

# 必须达到最小数量的集合（名称含日期，故按数量校验）
MIN_COUNTS = {
    'assets/examples/*.html': 3,  # ≥3：每模式黄金样张；可另含 showcase
    'assets/examples/*.model.json': 3,
    'references/*.md': 25,  # + page-type-matrix + chart-decision-tree；≥25 防误删
}


def picked(rel: str) -> bool:
    return any(rel == p or _match(rel, p) for p in EXCLUDE)


def _match(rel: str, pat: str) -> bool:
    if fnmatch.fnmatch(rel, pat):
        return True
    # '**/x/*' 需匹配任意深度
    if pat.startswith('**/'):
        tail = pat[3:]
        return fnmatch.fnmatch(rel, tail) or fnmatch.fnmatch(rel, '*/' + tail)
    return False


def check_skill_md():
    """frontmatter 门禁：name / description 必需，name 与包名一致，description ≤ 上限。"""
    p = ROOT / 'SKILL.md'
    if not p.exists():
        return None, ['缺少 SKILL.md']
    txt = p.read_text(encoding='utf-8')
    if not txt.startswith('---'):
        return None, ['SKILL.md 未以 YAML frontmatter（---）开头']
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', txt, re.S)
    if not m:
        return None, ['SKILL.md frontmatter 未正确闭合']
    fm = m.group(1)
    errs = []
    name_m = re.search(r'^name:\s*(\S+)\s*$', fm, re.M)
    if not name_m:
        errs.append('frontmatter 缺 name')
    elif name_m.group(1) != NAME:
        errs.append(f'frontmatter name={name_m.group(1)!r} 与分发包目录名 {NAME!r} 不一致')
    desc_m = re.search(r'^description:\s*"(.*)"\s*$', fm, re.M)
    if not desc_m:
        errs.append('frontmatter 缺 description（须为单行双引号字符串）')
        desc = ''
    else:
        desc = desc_m.group(1)
        if len(desc) > DESC_LIMIT:
            errs.append(f'description {len(desc)} 字符 > {DESC_LIMIT}')
        if '<' in desc or '>' in desc:
            errs.append('description 含尖括号（部分平台会拒载）')
    # 0.2.5 起版本在 metadata.version（Agent Skills 规范），兼容旧的顶层 version
    ver_m = re.search(r'^\s*version:\s*"?([\w.\-]+)"?\s*$', fm, re.M)
    return {'name': NAME, 'description_len': len(desc),
            'version': ver_m.group(1) if ver_m else VERSION}, errs


def collect():
    seen, files = set(), []
    for pat in INCLUDE:
        for h in sorted(ROOT.glob(pat)):
            if not h.is_file():
                continue
            rel = h.relative_to(ROOT).as_posix()
            if rel in seen or picked(rel):
                continue
            seen.add(rel)
            files.append((rel, h))
    return files


def verify(files):
    errs = []
    have = {rel for rel, _ in files}
    for rel in REQUIRED:
        if rel not in have:
            errs.append(f'缺必需文件: {rel}')
    for pat, n in MIN_COUNTS.items():
        got = len([r for r in have if _match(r, pat) or r == pat])
        if got < n:
            errs.append(f'{pat} 数量 {got} < {n}')
    # 反向：不应出现的路径
    for rel in have:
        if rel.startswith('scripts/_') or '__pycache__' in rel or 'node_modules' in rel:
            errs.append(f'不应进包: {rel}')
    return errs


def main():
    check_only = '--check' in sys.argv[1:]

    files = collect()
    if not files:
        print('错误：未收集到任何文件')
        return 1
    errs = verify(files)
    meta, fm_errs = check_skill_md()
    errs += fm_errs

    print('── 发布前校验 ──')
    print(f'  技能名 {NAME} · 版本 {meta.get("version") if meta else "?"} · '
          f'description {meta.get("description_len") if meta else "?"} 字符')
    print(f'  进包文件 {len(files)} 个')
    if errs:
        print('  校验失败：')
        for e in errs:
            print(f'    ✗ {e}')
        return 1
    print('  校验通过：必需文件齐全 · frontmatter 合规 · 无临时/缓存路径')

    # P0-1 trigger heuristic gate（廉价、无 LLM）
    trig = ROOT / 'scripts' / 'check_triggers.py'
    if trig.exists():
        import subprocess
        r = subprocess.run([sys.executable, str(trig)], cwd=str(ROOT))
        if r.returncode != 0:
            print('  ✗ trigger coverage 失败（evals/trigger-queries.json）')
            return 1
        print('  ✓ trigger coverage 通过')

    if check_only:
        print('\n(--check 模式：仅校验，不打包)')
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel, h in files:
            z.write(h, f'{NAME}/{rel}')

    entries, total = [], 0
    for rel, h in files:
        raw = h.read_bytes()
        total += len(raw)
        entries.append({'path': rel, 'bytes': len(raw),
                        'sha256': hashlib.sha256(raw).hexdigest()})
    manifest = {
        'skill': NAME,
        'version': (meta or {}).get('version'),
        'descriptionLength': (meta or {}).get('description_len'),
        'builtAt': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'zip': f'dist/{NAME}.zip',
        'entries': len(entries),
        'totalBytes': total,
        'zipBytes': OUT.stat().st_size,
        'files': entries,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'\n── 打包完成 ──')
    print(f'  {OUT}')
    print(f'  条目 {len(entries)} 个 · 原始 {total/1024:.0f} KB · 压缩 {OUT.stat().st_size/1024:.0f} KB')
    print(f'  {MANIFEST}（版本 / 条目 / SHA-256，随包留档）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
