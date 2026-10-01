#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TopPPT HTML · 门禁反向验证（故障注入）

校验器最容易退化成「只会说 OK 的摆设」。本脚本往合格产物里**注入已知缺陷**，
断言对应门禁必须报错——门禁抓不到即视为失败。

覆盖：
  N1  Exhibit 框漏编号（旧实现只校验已编号者的连续性 → 静默通过）
  N2  参考资料两位数编号错配（旧正则 `ref-\\d` 两侧同时落空 → 静默通过）
  N3  参考资料编号跳号
  N4  PPTX 演讲者备注被剔离（dataTable=notes 声称数据入备注，不核对就只是一句承诺）
  N5  模型图表数值篡改（cross_verify 数值核对）
  N6  行动标题判断词鉴别力（正则本身）
  N7  PPTX 字号越出比例尺
  N8  data-chart 未登记类型（登记表白名单）
  N9  图表多样性塌陷（全篇压成同型 → 不同类型数 < 模式下限）
  N10 图片外链（零外链铁律）
  N11 待核实有标色无图例（.tbd 必须配 .tbd-legend/.flagbar）
  N12 模型 theme 与 data-theme 矛盾
  N13 模型 mode 与 data-mode 矛盾
  N14 内部锚点断裂（链接目标 id 不存在）
  N19 运行时同版本戳被篡改（__TOPPPT_RUNTIME_SHA__）
  L4  截断迹象（列表项省略号砍义）
  L5  溢出未拆页
  L6  混排缺对齐（ALIGN_RHYTHM）
  N18 配图页缺 caption/图注（IMAGE_CAPTION）

用法: python scripts/negative_tests.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'dist' / 'negtest'
PY = sys.executable


def run_validate(path: Path) -> tuple[int, str]:
    r = subprocess.run([PY, str(ROOT / 'scripts' / 'validate_report.py'), str(path), '--strict'],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def expect_fail(name: str, path: Path, keyword: str) -> bool:
    code, out = run_validate(path)
    # --strict 下 WARN 同样计失败（退出码 1），故 [WARN] 行也算「门禁抓到」
    hit = [ln for ln in out.splitlines()
           if keyword in ln and ('[FAIL]' in ln or '[WARN]' in ln)]
    ok = code != 0 and bool(hit)
    print(f'  [{"OK" if ok else "FAIL"}] {name}')
    if hit:
        print(f'        抓到: {hit[0].strip()[:120]}')
    elif not ok:
        print(f'        门禁未触发（期望 FAIL 含「{keyword}」）')
    return ok



def expect_layout_qa_fail(name: str, path: Path, keyword: str) -> bool:
    """Run validate_report --strict --layout-qa and require FAIL containing keyword."""
    r = subprocess.run(
        [PY, str(ROOT / 'scripts' / 'validate_report.py'), str(path),
         '--strict', '--layout-qa'],
        capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = (r.stdout or '') + (r.stderr or '')
    hit = [ln for ln in out.splitlines()
           if keyword in ln and ('[FAIL]' in ln or 'FAIL' in ln)]
    ok = r.returncode != 0 and bool(hit)
    print(f'  [{"OK" if ok else "FAIL"}] {name}')
    if hit:
        print(f'        抓到: {hit[0].strip()[:120]}')
    elif not ok:
        print(f'        layout-qa 未触发（期望含「{keyword}」）')
    return ok


def _runtime_stamp_case() -> bool:
    """N19：篡改 __TOPPPT_RUNTIME_SHA__ → validate_report 必须 FAIL。"""
    base = ROOT / 'assets' / 'examples' / '2026-09-09-research-mckinsey.html'
    if not base.exists():
        print('  [SKIP] N19 运行时同版本戳（基准示例缺失）')
        return True
    txt = base.read_text(encoding='utf-8')
    m = re.search(r'/\* __TOPPPT_RUNTIME_SHA__:([0-9a-f]{16}) \*/', txt)
    if not m:
        print('  [SKIP] N19 运行时同版本戳（示例尚未 sync 出戳；先跑 sync_runtime）')
        return True
    OUT.mkdir(parents=True, exist_ok=True)
    bad = txt[:m.start()] + '/* __TOPPPT_RUNTIME_SHA__:deadbeefdeadbeef */' + txt[m.end():]
    out = OUT / 'N19-bad-runtime-sha.html'
    out.write_text(bad, encoding='utf-8')
    return expect_fail('N19 运行时同版本戳被篡改', out, '运行时同版本戳')



def main() -> int:
    base = ROOT / 'assets' / 'examples' / '2026-09-09-research-mckinsey.html'
    if not base.exists():
        print(f'SKIP：基准示例缺失 {base}')
        return 0
    txt = base.read_text(encoding='utf-8')
    OUT.mkdir(parents=True, exist_ok=True)

    code, out = run_validate(base)
    if code != 0:
        print('[FAIL] 基准示例本身未通过 strict，反向验证失去意义')
        return 1
    print('基准示例 strict 通过，开始故障注入：')

    cases: list[tuple[str, str, str]] = []

    # N1 抹掉一个 Exhibit 编号（框仍在）
    cases.append(('N1 Exhibit 框漏编号',
                  txt.replace('class="exhibit__no"', 'class="exhibit__no--x"', 1),
                  'Exhibit 框均已编号'))

    # N2 参考资料改成两位数编号，与正文引用错配
    cases.append(('N2 引用编号两位数错配',
                  re.sub(r'id="ref-1"', 'id="ref-10"', txt, count=1),
                  '双向对齐'))

    # N3 编号跳号（两侧同时改，集合仍对齐，但 1..N 不连续）
    t3 = txt.replace('ref-2"', 'ref-9"')
    cases.append(('N3 参考资料编号跳号', t3, '编号连续'))

    # N8 data-chart 用了登记表外的类型
    cases.append(('N8 图表类型未登记',
                  txt.replace('data-chart="hbar"', 'data-chart="hbarx"', 1),
                  '登记表内'))

    # N9 图表多样性塌陷（全部压成 bar → 不同类型数 1 < research 下限 6）
    t9 = txt
    for ct in ('hbar', 'donut', 'waterfall', 'sankey', 'treemap', 'boxplot',
               'network', 'marimekko', 'streamgraph', 'gantt', 'rose', 'candlestick'):
        t9 = t9.replace(f'data-chart="{ct}"', 'data-chart="bar"')
    cases.append(('N9 图表多样性塌陷', t9, '图表多样性'))

    # N10 外链图片（零外链铁律）
    cases.append(('N10 图片外链',
                  txt.replace('</body>',
                              '<img src="https://example.com/x.png" alt="外链注入"></body>', 1),
                  '图片源无外链'))

    # N11 待核实有标色无图例（改名不得包含原串——校验是子串判断）
    t11 = txt.replace('tbd-legend', 'tbd-leg').replace('flagbar', 'flag-bar')
    cases.append(('N11 待核实无图例', t11, '待核实标注'))

    # N12 模型 theme 与页面 data-theme 矛盾
    cases.append(('N12 模型主题不一致',
                  txt.replace('"theme": "light"', '"theme": "dark"', 1),
                  'data-theme 一致'))

    # N13 模型 mode 与页面 data-mode 矛盾
    cases.append(('N13 模型模式不一致',
                  txt.replace('"mode": "research"', '"mode": "presentation"', 1),
                  'data-mode 一致'))

    # N14 内部锚点断裂（链接目标 id 不存在）
    cases.append(('N14 锚点断裂',
                  txt.replace('href="#s1"', 'href="#s404"'),
                  '锚点闭环'))

    # N15 HTML 标签泄漏进可见文本（截图级：转义标签当字面量显示）
    cases.append(('N15 标签泄漏',
                  txt.replace('</p>',
                              ' &lt;a class="cite" href="#ref-1"&gt;[1]&lt;/a&gt;。</p>', 1),
                  'HTML_TAG_IN_TEXT'))

    # N16 极偏 donut（0.5% vs 99.5% 应改 KPI，禁环图）
    t16 = txt
    if '"type": "donut"' in t16 or '"type":"donut"' in t16:
        t16 = re.sub(
            r'("type"\s*:\s*"donut"[\s\S]{0,200}?"values"\s*:\s*\[)[^\]]*(\])',
            r'\g<1>0.5, 99.5\g<2>', t16, count=1)
        cases.append(('N16 极偏 donut', t16, 'CHART_SKEW'))

    # N17 模型字段夹带 HTML 标签（extract 净化 + validate 扫描 REPORT_MODEL）
    t17 = re.sub(
        r'("soWhat"\s*:\s*")',
        r'\g<1><a class=\\"cite\\" href=\\"#ref-1\\">[1]</a> ',
        txt, count=1)
    if t17 == txt:
        t17 = txt.replace(
            '"footnote":',
            '"footnote": "<strong>x</strong> ', 1)
    cases.append(('N17 模型夹带标签', t17, 'HTML_TAG_IN_TEXT'))

    # N18 配图页缺 caption（有 <img>/media 无图注类）
    t18 = txt.replace(
        '</body>',
        '<section class="band" data-page-type="image">'
        '<div class="media media--full">'
        '<img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" alt="注入无图注">'
        '</div></section></body>', 1)
    cases.append(('N18 配图缺 caption', t18, 'IMAGE_CAPTION'))

    ok = True
    for name, content, keyword in cases:
        if content == txt:
            print(f'  [SKIP] {name}（基准示例无对应结构）')
            continue
        p = OUT / (name.split()[0] + '.html')
        p.write_text(content, encoding='utf-8')
        ok = expect_fail(name, p, keyword) and ok


    # ── Batch 2 · layout-qa 专用负例 ─────────────────────────────────────
    # L1 管线产物缺 data-skel：先造带 skel 的页，再撕掉其中一页的标记
    import tempfile
    scaf = OUT / 'L1-scaffold.html'
    subprocess.run(
        [PY, str(ROOT / 'scripts' / 'scaffold_report.py'),
         '--mode', 'presentation', '--style', 'business-blue', '--theme', 'light',
         '--title', 'LayoutQA Neg', '--sections', '5', '--out', str(scaf)],
        capture_output=True, text=True)
    if scaf.exists() and 'data-skel="' in scaf.read_text(encoding='utf-8'):
        t_l1 = scaf.read_text(encoding='utf-8')
        # 撕掉第一个内容页的 data-skel
        t_l1b = re.sub(r'(id="s1") data-skel="P\d+"', r'\1', t_l1, count=1)
        p_l1 = OUT / 'L1-missing-skel.html'
        p_l1.write_text(t_l1b, encoding='utf-8')
        ok = expect_layout_qa_fail('L1 缺 data-skel', p_l1, 'LAYOUT_QA_MISSING_SKEL') and ok
        # L2 连续 3 页同一 skel
        t_l2 = t_l1
        # force s1,s2,s3 all P4
        t_l2 = re.sub(r'(id="s1"[^>]*data-skel=")P\d+"', r'\1P4"', t_l2, count=1)
        t_l2 = re.sub(r'(id="s2"[^>]*data-skel=")P\d+"', r'\1P4"', t_l2, count=1)
        t_l2 = re.sub(r'(id="s3"[^>]*data-skel=")P\d+"', r'\1P4"', t_l2, count=1)
        # also rewrite if attribute order is data-skel before id
        t_l2 = re.sub(r'(data-skel=")P\d+(" data-page-type="[^"]+" id="s1")', r'\1P4\2', t_l2)
        t_l2 = re.sub(r'(data-skel=")P\d+("([^>]*) id="s1")', r'\1P4\2', t_l2)
        # simpler: replace first three data-skel values
        def _force_p4(src, n=3):
            out, c = [], 0
            for part in re.split(r'(data-skel="P\d+")', src):
                if part.startswith('data-skel="') and c < n:
                    out.append('data-skel="P4"'); c += 1
                else:
                    out.append(part)
            return ''.join(out)
        t_l2 = _force_p4(t_l1, 3)
        p_l2 = OUT / 'L2-skel-streak.html'
        p_l2.write_text(t_l2, encoding='utf-8')
        ok = expect_layout_qa_fail('L2 连续同 skel', p_l2, 'LAYOUT_QA_SKEL_STREAK') and ok
        # L3 极偏 donut in REPORT_MODEL
        t_l3 = t_l1
        if 'window.REPORT_MODEL' in t_l3:
            # inject a skewed donut section into model JSON
            inj = (
                '{"type":"donut","title":"极偏环",'
                '"chart":{"type":"donut","labels":["A","B"],"values":[0.5,99.5]}},'
            )
            t_l3 = re.sub(r'("sections"\s*:\s*\[)', r'\1' + inj, t_l3, count=1)
            p_l3 = OUT / 'L3-skew-donut.html'
            p_l3.write_text(t_l3, encoding='utf-8')
            ok = expect_layout_qa_fail('L3 极偏 donut', p_l3, 'LAYOUT_QA_SKEW_DONUT') and ok

        # L4 截断迹象：列表项以省略号砍义
        t_l4 = t_l1
        inj4 = '<div class="card"><ul><li class="card__li">这项证据其实很长但被故意截断了…</li></ul></div>'
        t_l4 = re.sub(r'(id="s1"[^>]*>)', lambda m: m.group(1) + inj4, t_l4, count=1)
        p_l4 = OUT / 'L4-truncation.html'
        p_l4.write_text(t_l4, encoding='utf-8')
        ok = expect_layout_qa_fail('L4 截断迹象', p_l4, 'LAYOUT_QA_TRUNCATION') and ok

        # L5 溢出未拆页：塞入超长正文使页高估算爆掉且无续页信号
        t_l5 = t_l1
        wall = '论证要点' + ('详细证据与口径说明，必须完整保留不得删减。' * 40)
        t_l5 = re.sub(
            r'(id="s1"[^>]*>)',
            lambda m: m.group(1) + '<div class="card"><p>' + wall + '</p></div>'
                 + '<div class="card"><p>' + wall + '</p></div>'
                 + '<div class="card"><p>' + wall + '</p></div>',
            t_l5, count=1)
        p_l5 = OUT / 'L5-overflow-nosplit.html'
        p_l5.write_text(t_l5, encoding='utf-8')
        ok = expect_layout_qa_fail('L5 溢出未拆页', p_l5, 'LAYOUT_QA_OVERFLOW_NO_SPLIT') and ok

        # L6 混排缺对齐：图+卡同页但无对齐类
        t_l6 = t_l1
        inj6 = (
            '<div class="grid g-2">'
            '<div class="fig"><svg class="chart" data-chart="bar" style="height:200px"></svg></div>'
            '<div class="card"><ul><li>证据甲</li><li>证据乙</li></ul></div>'
            '</div>'
        )
        t_l6 = re.sub(r'(id="s1"[^>]*>)', lambda m: m.group(1) + inj6, t_l6, count=1)
        # 撕掉 s1 段内对齐类，确保 ALIGN_RHYTHM 能抓住
        def _strip_align_s1(src: str) -> str:
            m = re.search(r'(<section[^>]*id="s1"[^>]*>)([\s\S]*?)(</section>)', src)
            if not m:
                # attribute order may be data-skel before id
                m = re.search(r'(<section[^>]*id="s1"[^>]*>)([\s\S]*?)(</section>)', src)
            if not m:
                return src
            body = m.group(2)
            body = re.sub(r'\ba-start\b', '', body)
            body = re.sub(r'\ba-c\b', '', body)
            body = re.sub(r'\ba-end\b', '', body)
            body = body.replace('align-items:start', '').replace('align-items: center', '')
            return src[:m.start()] + m.group(1) + body + m.group(3) + src[m.end():]
        t_l6 = _strip_align_s1(t_l6)
        p_l6 = OUT / 'L6-align-rhythm.html'
        p_l6.write_text(t_l6, encoding='utf-8')
        ok = expect_layout_qa_fail('L6 混排缺对齐', p_l6, 'LAYOUT_QA_ALIGN_RHYTHM') and ok

    else:
        print('  [SKIP] layout-qa 负例（scaffold 未产出 data-skel）')

    ok = _pptx_notes_case() and ok
    ok = _chart_data_case() and ok
    ok = _title_pattern_case() and ok
    ok = _font_scale_case() and ok
    ok = _runtime_stamp_case() and ok

    print('反向验证通过：注入的缺陷都被门禁抓住。' if ok
          else '反向验证失败：存在抓不到的缺陷，门禁有假阴性。')
    return 0 if ok else 1


def _ensure_regression_fixture(name: str = '2026-09-09-research-mckinsey') -> Path | None:
    """Lightweight CI fixture: build one PPTX into dist/regression/ if missing.
    Avoids full regression.py; enough for N4/N5/N7."""
    dest_dir = ROOT / 'dist' / 'regression'
    pptx = dest_dir / f'{name}.pptx'
    if pptx.exists():
        return pptx
    model = ROOT / 'assets' / 'examples' / f'{name}.model.json'
    if not model.exists():
        print(f'  [SKIP] regression fixture（缺 model {model.name}）')
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    build = ROOT / 'scripts' / 'build_pptx.js'
    if not build.exists():
        print('  [SKIP] regression fixture（缺 build_pptx.js）')
        return None
    import os
    env = os.environ.copy()
    nm = ROOT / 'node_modules'
    if nm.is_dir():
        env['NODE_PATH'] = str(nm) + (os.pathsep + env['NODE_PATH'] if env.get('NODE_PATH') else '')
    r = subprocess.run(['node', str(build), str(pptx), f'--model={model}'],
                       cwd=str(ROOT), env=env, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0 or not pptx.exists():
        print('  [SKIP] regression fixture（build_pptx 失败）')
        err = (r.stderr or r.stdout or '')[:200]
        if err:
            print(f'        {err}')
        return None
    print(f'  [OK] 轻量 regression fixture → {pptx.relative_to(ROOT)}')
    return pptx



def _font_scale_case() -> bool:
    """N7：往 PPTX 里塞一个比例尺外的字号 → FONT_SIZE_OFF_SCALE 必须报。"""
    name = '2026-09-09-research-mckinsey'
    src = _ensure_regression_fixture(name)
    model = ROOT / 'assets' / 'examples' / f'{name}.model.json'
    if src is None or not model.exists():
        print('  [SKIP] N7 字号越出比例尺（需先跑 regression / 缺 node+pptxgenjs）')
        return True
    out = OUT / 'N7-off-scale.pptx'
    patched = False
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if not patched and item.filename == 'ppt/slides/slide4.xml':
                text = data.decode('utf-8')
                new = re.sub(r'sz="\d+"', 'sz="1234"', text, count=1)  # 12.34pt：任何档位都没有
                if new != text:
                    data = new.encode('utf-8')
                    patched = True
            zout.writestr(item, data)
    if not patched:
        print('  [SKIP] N7 字号越出比例尺（未找到可改写的 sz 属性）')
        return True
    report = OUT / 'N7.json'
    subprocess.run([PY, str(ROOT / 'scripts' / 'validate_pptx.py'), str(out),
                    '--strict', '--model=' + str(model), '--json-out', str(report)],
                   capture_output=True, text=True, encoding='utf-8', errors='replace')
    try:
        data = json.loads(report.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        print('  [FAIL] N7 字号越出比例尺：校验报告不可解析')
        return False
    codes = {i.get('code') for i in (data.get('errors') or []) + (data.get('warnings') or [])}
    ok = 'FONT_SIZE_OFF_SCALE' in codes
    print(f'  [{"OK" if ok else "FAIL"}] N7 字号越出比例尺')
    if not ok:
        print(f'        门禁未触发（期望 FONT_SIZE_OFF_SCALE，实际 {sorted(codes)[:6]}）')
    return ok


def _title_pattern_case() -> bool:
    """N6：主题词式长标题必须被判为「无判断信号」，结论句标题必须放行。"""
    lc = json.loads((ROOT / 'scripts' / 'layout-constants.json').read_text(encoding='utf-8'))
    pat = ((lc.get('contentQuality') or {}).get('researchTitle') or {}).get('judgmentPattern')
    if not pat:
        print('  [SKIP] N6 行动标题判断词（未配置 judgmentPattern）')
        return True
    topic = ['智能体平台的应用架构与技术选型说明', '关于数据治理需求的整体情况介绍',
             '企业知识库建设的相关背景与范围', '平台能力地图与模块组成一览表',
             '项目实施过程中的应急预案汇总', '面向未来的技术路线图规划说明']
    claim = ['投入产出比在第 3 季度首次转正', '三成团队已把智能体纳入日常流程',
             '数据质量是当前最大的落地瓶颈', '推理成本一年内下降 62%',
             '从试点到规模化：关键卡在治理', '自建方案的总成本高于采购方案']
    leaked = [t for t in topic if re.search(pat, t)]
    hurt = [t for t in claim if not re.search(pat, t)]
    ok = not leaked and not hurt
    print(f'  [{"OK" if ok else "FAIL"}] N6 行动标题判断词鉴别力'
          f'（漏放主题词 {len(leaked)}/{len(topic)} · 误伤结论句 {len(hurt)}/{len(claim)}）')
    for t in (leaked + hurt)[:3]:
        print(f'        {t}')
    return ok


def _chart_data_case() -> bool:
    """N5：篡改模型里的图表数值 → cross_verify 的数值核对必须报不符。"""
    name = '2026-09-09-research-mckinsey'
    pptx = _ensure_regression_fixture(name)
    mp = ROOT / 'assets' / 'examples' / f'{name}.model.json'
    if pptx is None or not mp.exists():
        print('  [SKIP] N5 图表数值篡改（需先跑 regression / 缺 node+pptxgenjs）')
        return True
    sys.path.insert(0, str(ROOT / 'scripts'))
    try:
        from pptx import Presentation           # noqa: PLC0415
        import cross_verify as CV               # noqa: PLC0415
    except ImportError:
        print('  [SKIP] N5 图表数值篡改（python-pptx 未安装）')
        return True
    model = json.loads(mp.read_text(encoding='utf-8'))
    touched = False
    for sec in (model.get('sections') or []):
        c = CV._model_chart(sec) if isinstance(sec, dict) else None
        if c and isinstance(c.get('values'), list) and c['values']:
            c['values'] = [(v + 777) if isinstance(v, (int, float)) else v for v in c['values']]
            touched = True
            break
    if not touched:
        print('  [SKIP] N5 图表数值篡改（基准模型无可改图表）')
        return True
    issues = CV.chart_data_verify(Presentation(str(pptx)), model, name)
    ok = bool(issues)
    print(f'  [{"OK" if ok else "FAIL"}] N5 模型图表数值被篡改')
    if ok:
        print(f'        抓到: {issues[0][:120]}')
    else:
        print('        门禁未触发（数值核对形同虚设）')
    return ok


def _pptx_notes_case() -> bool:
    """N4：剥离演讲者备注 → dataTable=notes 的图表数据不可追溯，必须被 strict 抓住。"""
    name = '2026-09-09-research-mckinsey'
    src = _ensure_regression_fixture(name)
    model = ROOT / 'assets' / 'examples' / f'{name}.model.json'
    if src is None or not model.exists():
        print('  [SKIP] N4 备注剥离（需先跑 regression / 缺 node+pptxgenjs）')
        return True
    stripped = OUT / 'N4-no-notes.pptx'
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(stripped, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename.startswith('ppt/notesSlides/'):
                continue
            zout.writestr(item, zin.read(item.filename))
    report = OUT / 'N4.json'
    subprocess.run([PY, str(ROOT / 'scripts' / 'validate_pptx.py'), str(stripped),
                    '--strict', '--model=' + str(model), '--json-out', str(report)],
                   capture_output=True, text=True, encoding='utf-8', errors='replace')
    try:
        data = json.loads(report.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        print('  [FAIL] N4 备注剥离：校验报告不可解析')
        return False
    codes = {i.get('code') for i in (data.get('errors') or []) + (data.get('warnings') or [])}
    ok = 'MODEL_CHART_NOTES_MISSING' in codes
    print(f'  [{"OK" if ok else "FAIL"}] N4 演讲者备注被剥离')
    if not ok:
        print(f'        门禁未触发（期望 MODEL_CHART_NOTES_MISSING，实际 {sorted(codes)[:6]}）')
    return ok


if __name__ == '__main__':
    sys.exit(main())
