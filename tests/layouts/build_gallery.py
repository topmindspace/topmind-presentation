#!/usr/bin/env python3
"""版式画廊：layoutLibrary 每个版式各取一页，生成 gallery-<mode>.model.json（golden 的输入）。

页面优先取自示例 model.json（真实内容），示例未用到的版式用下方 SYNTH 补齐。
用法：python tests/layouts/build_gallery.py   （写回 tests/layouts/）
"""
import copy, glob, json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import check_rhythm as C  # noqa: E402

SCHEMA = json.load(open(os.path.join(ROOT, 'scripts', 'model-schema.json'), encoding='utf-8'))['pageTypes']
PTS = [{'title': '统一入口', 'body': '一个入口承接全部请求，权限与审计在入口处一次完成。'},
       {'title': '分层治理', 'body': '按风险分级配置审批链路，低风险自动放行、高风险双人复核。'},
       {'title': '数据闭环', 'body': '运行数据回流到评估集，每周复盘一次并更新阈值。'}]
SYNTH = {
    'problem-solution': {'type': 'comparison', 'variant': 'problem-solution', 'title': '问题 → 方案：从人工巡检到自动告警',
                         'left': {'title': '现状问题', 'items': ['巡检靠人工，夜间无人值守', '告警阈值靠经验，误报率高', '故障复盘缺数据']},
                         'right': {'title': '改进方案', 'items': ['指标自动采集，分钟级巡检', '基线学习自动定阈值', '全链路日志留存 90 天']}},
    'funnel': {'type': 'bar', 'title': '转化漏斗：访问到签约逐级收窄', 'chart': {'type': 'funnel', 'labels': ['访问', '注册', '试用', '付费', '续约'], 'values': [100, 46, 21, 9, 6], 'unit': '%'}},
    'milestones-icon': {'type': 'timeline', 'variant': 'timeline', 'title': '四个里程碑：半年完成平台化',
                        'phases': [{'title': 'M1 试点', 'time': '1 月', 'body': '两条业务线跑通'}, {'title': 'M2 推广', 'time': '3 月', 'body': '覆盖八条业务线'},
                                   {'title': 'M3 平台', 'time': '5 月', 'body': '能力沉淀为平台'}, {'title': 'M4 运营', 'time': '6 月', 'body': '指标进入月度经营会'}]},
    'media-full': {'type': 'image', 'title': '满版配图：现场全景', 'image': {'placeholder': True, 'layout': 'full', 'caption': '配图占位（画廊样例）'}},
    'media-half': {'type': 'image', 'title': '左图右文：控制台界面', 'image': {'placeholder': True, 'layout': 'half', 'caption': '配图占位'},
                   'points': ['左侧导航按业务域分组', '右侧卡片显示实时指标', '异常项置顶并高亮']},
    'media-grid': {'type': 'image', 'title': '图片网格：四个场景', 'image': {'layout': 'grid', 'items': [{'placeholder': True, 'caption': c} for c in ('门店', '仓储', '客服', '财务')]}},
    'feature-2col': {'type': 'twocol', 'variant': '2-col-feature', 'title': '主张与细节：为什么先做数据底座',
                     'paragraphs': ['没有统一口径的数据，任何模型效果都无法被复核；底座先行能让后续每个场景的验收成本下降一半。',
                                    '底座包含三件事：指标字典、血缘追踪、质量监控。三件事都有现成工具，难点在组织上的口径共识。']},
}


def allowed(sec, mode):
    return mode in (SCHEMA.get(sec.get('type') or 'points', {}).get('modes') or [mode])


def main():
    picked = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'assets', 'examples', '*.model.json'))):
        m = json.load(open(f, encoding='utf-8'))
        for p in C.pages_of(m):
            if p['kind'] == 'section' and not p.get('cont') and p['layout'] not in picked:
                picked[p['layout']] = (copy.deepcopy(p['sec']), m['mode'])
    for lid, sec in SYNTH.items():
        picked.setdefault(lid, (copy.deepcopy(sec), 'research'))
    decks = {}
    for l in C.LAYOUTS:
        if l['id'] not in picked:
            continue  # cover/agenda/closing 由 deck 自身提供
        sec, mode = picked[l['id']]
        target = 'research' if allowed(sec, 'research') else mode
        sec['eyebrow'] = f"{l['family']} · {l['id']}"
        sec.pop('exhibitNo', None)
        decks.setdefault(target, []).append(sec)
    for mode, secs in decks.items():
        model = {'mode': mode, 'style': 'business-blue', 'theme': 'light', 'title': f'版式画廊 · {mode}',
                 'subtitle': 'layoutLibrary golden 输入（自动生成，勿手改）', 'date': '2026-10-16',
                 'agenda': ['结构', '观点', '数据', '框架', '流程', '媒体', '卡片', '表格', '其他'][:9],
                 'sections': secs, 'closing': {'title': '谢谢', 'body': '版式画廊结束'}}
        if mode == 'architecture':
            model['agenda'] = model['agenda'][:4]
        out = os.path.join(ROOT, 'tests', 'layouts', f'gallery-{mode}.model.json')
        with open(out, 'w', encoding='utf-8') as fh:
            json.dump(model, fh, ensure_ascii=False, indent=2)
            fh.write('\n')
        print(f'{out}: {len(secs)} 页')


if __name__ == '__main__':
    main()
