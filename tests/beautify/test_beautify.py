#!/usr/bin/env python3
"""M4 已有 PPT 美化：三份朴素样例端到端 + 篡改负例。

断言：
  1. 三份样例（课件 / 经营汇报 / 方案）verify 全 PASS：文本差异 0、数字全部找回、图表数据与原生 chart XML 一致；
  2. 原文件字节不变；输出落在新目录；
  3. 未迁入的对象（样例里的自绘图片）必须列入报告；
  4. 产物过 validate_pptx / validate_report / check_rhythm 三道 strict；
  5. 负例：改模型里一个字 / 一个图表数值后重新渲染，verify 必须 FAIL。
"""
import hashlib, json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import beautify  # noqa: E402

SAMPLES = ROOT / 'tests' / 'beautify' / 'samples'
NAMES = ['lecture-dataviz', 'business-q3', 'proposal-callcenter']


def h(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def reverify(src_pptx, out, mutate):
    """在已有输出上篡改模型 → 重新渲染 → 用原稿冻结结果核对。"""
    src = beautify.ingest_pptx.ingest(str(src_pptx), str(out / 'media'))
    frz = beautify.freeze(src)
    model, plan, led = beautify.build_model(src, 'business-blue', 'light')
    mutate(model)
    mp = out / 'tamper.model.json'
    mp.write_text(json.dumps(model, ensure_ascii=False), encoding='utf-8')
    html, pptx = out / 'tamper.html', out / 'tamper.pptx'
    beautify.render(mp, html, pptx, ROOT / 'assets' / 'templates' / 'presentation.html')
    return beautify.verify(src, frz, model, plan, led, pptx, html)


def tamper_text(model):
    s = json.dumps(model['sections'], ensure_ascii=False)
    # 把正文里第一个「的」换成「之」——单字改动
    i = s.find('的')
    assert i > 0
    model['sections'] = json.loads(s[:i] + '之' + s[i + 1:])


def tamper_chart(model):
    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get('values'), list) and o['values'] and isinstance(o['values'][0], (int, float)):
                o['values'][0] = o['values'][0] + 1
                return True
            return any(walk(v) for v in o.values())
        if isinstance(o, list):
            return any(walk(v) for v in o)
        return False
    assert walk(model['sections']), '样例里应有图表数值'


def main():
    fails = []
    tmp = Path(tempfile.mkdtemp(prefix='m4-beautify-'))
    try:
        for n in NAMES:
            src = SAMPLES / f'{n}.pptx'
            before = h(src)
            out = tmp / n
            _, ver = beautify.run(src, out)
            n_src = sum(1 for sl in beautify.ingest_pptx.ingest(str(src), str(tmp / 'm'))['slides'] for sh in sl['shapes'] if sh['kind'] == 'chart')
            ok_charts = len(ver['charts']) == n_src and all(c.get('pptx') for c in ver['charts'])
            print(f"  [{n}] verify={'PASS' if ver['ok'] else 'FAIL'} 图表 {len(ver['charts'])} 张 一致={ok_charts}")
            if not ver['ok'] or not ok_charts:
                fails.append(f'{n}: verify 未通过')
            if h(src) != before:
                fails.append(f'{n}: 原文件被改动')
            for f in (f'{n}.beautified.html', f'{n}.beautified.pptx', 'verify.json', 'report.md'):
                if not (out / f).exists():
                    fails.append(f'{n}: 缺输出 {f}')
            stem = out / f'{n}.beautified'
            if n == 'lecture-dataviz' and 'PICTURE' not in (out / 'report.md').read_text(encoding='utf-8'):
                fails.append(f'{n}: 未迁入的图片没有列入报告')
            for cmd in ([sys.executable, 'scripts/validate_pptx.py', f'{stem}.pptx', '--strict', f'--model={stem}.model.json'],
                        [sys.executable, 'scripts/validate_report.py', f'{stem}.html', '--strict'],
                        [sys.executable, 'scripts/check_rhythm.py', f'{stem}.model.json', '--strict']):
                if subprocess.run(cmd, cwd=ROOT, capture_output=True).returncode != 0:
                    fails.append(f'{n}: {cmd[1]} --strict 未通过')
            try:
                beautify.run(src, SAMPLES, do_render=False)
                fails.append(f'{n}: 允许输出到原稿目录')
            except SystemExit:
                pass
        # 负例
        src = SAMPLES / 'business-q3.pptx'
        out = tmp / 'business-q3'
        v1 = reverify(src, out, tamper_text)
        v2 = reverify(src, out, tamper_chart)
        print(f"  [负例] 改一个字 → {'FAIL（已拦住）' if not v1['ok'] else 'PASS（漏检！）'}；"
              f"改一个图表数值 → {'FAIL（已拦住）' if not v2['ok'] else 'PASS（漏检！）'}")
        if v1['ok']:
            fails.append('负例：改字未被发现')
        if v2['ok']:
            fails.append('负例：图表数值改动未被发现')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if fails:
        print('test_beautify: FAIL'); [print('  -', f) for f in fails]
        return 1
    print('test_beautify: OK（3 份样例差异 0 · 原稿不变 · 2 类篡改均被拦住）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
