#!/usr/bin/env python3
"""造 3 份「朴素、难看」的测试原稿（课件 / 经营汇报 / 方案），内容为自拟虚构数据，不含任何外部素材。

刻意保留常见毛病：字号混乱、彩色字、文本框随手摆、默认图表配色、整页堆字、编号手打。
用法：python tests/beautify/make_samples.py   → tests/beautify/samples/*.pptx（确定性输出）
"""
import os
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Inches, Pt

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'samples')
RED, GREEN, ORANGE, BLUE, PURPLE = (RGBColor(0xE0, 0x10, 0x10), RGBColor(0x10, 0xA0, 0x30),
                                    RGBColor(0xF0, 0x80, 0x00), RGBColor(0x00, 0x40, 0xFF), RGBColor(0x90, 0x20, 0xB0))


def deck():
    p = Presentation()
    p.slide_width, p.slide_height = Inches(10), Inches(7.5)   # 老式 4:3
    return p


def box(s, x, y, w, h, lines, size=18, color=None, bold=False, font='宋体'):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, ln in enumerate(lines):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        lvl = 0
        if isinstance(ln, tuple):
            ln, lvl = ln
        para.text = ln
        para.level = lvl
        for r in para.runs:
            r.font.size = Pt(size - 4 * lvl)
            r.font.name = font
            r.font.bold = bold
            if color is not None:
                r.font.color.rgb = color
    return tb


def title(s, t, color=RED, size=36):
    return box(s, 0.4, 0.3, 9.2, 1.0, [t], size=size, color=color, bold=True, font='Arial')


def blank(p):
    return p.slides.add_slide(p.slide_layouts[6])


def cover(p, t, sub, who):
    s = blank(p)
    box(s, 0.5, 2.2, 9, 1.4, [t], size=44, color=BLUE, bold=True, font='Arial')
    box(s, 0.5, 3.8, 9, 0.8, [sub], size=24, color=ORANGE)
    box(s, 0.5, 6.2, 9, 0.6, [who], size=14)


def agenda(p, items):
    s = blank(p)
    title(s, '目录')
    box(s, 1.0, 1.6, 8, 5, items, size=28, color=GREEN)


def bullets(p, t, lines, size=20, color=None):
    s = blank(p)
    title(s, t)
    box(s, 0.5, 1.5, 9, 5.6, lines, size=size, color=color)
    return s


def chart(p, t, kind, cats, series, extra=None):
    s = blank(p)
    title(s, t, color=PURPLE)
    cd = CategoryChartData()
    cd.categories = cats
    for name, vals in series:
        cd.add_series(name, vals)
    s.shapes.add_chart(kind, Inches(0.5), Inches(1.4), Inches(6.2 if extra else 9), Inches(5.2), cd)
    if extra:
        box(s, 6.9, 1.6, 2.9, 5, extra, size=16, color=RED)
    return s


def table(p, t, rows, extra=None):
    s = blank(p)
    title(s, t, color=GREEN)
    n, m = len(rows), len(rows[0])
    tb = s.shapes.add_table(n, m, Inches(0.5), Inches(1.5), Inches(9), Inches(0.5 * n)).table
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            tb.cell(i, j).text = v
    if extra:
        box(s, 0.5, 1.7 + 0.5 * n, 9, 1, extra, size=16, color=ORANGE)


def _sketch_png():
    import io
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (200, 150), 'white')
    d = ImageDraw.Draw(im)
    for i, hgt in enumerate((50, 90, 120)):
        d.rectangle([20 + i * 60, 140 - hgt, 60 + i * 60, 140], fill=(200, 60, 60))
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    buf.seek(0)
    return buf


def lecture():
    p = deck()
    cover(p, '数据可视化入门', '第 3 讲：选对图表，讲清一个结论', '主讲：信息设计教研组　2026 年秋季')
    agenda(p, ['一、为什么要可视化', '二、四类常用图表', '三、制图四步法', '四、常见误区'])
    s = bullets(p, '为什么要可视化', [
        '人眼对位置和长度的判断最准确', '同一组数据，表格要读 30 秒，柱状图只要 3 秒',
        '图表的任务是让读者一眼看到结论', '好图表 = 一个结论 + 最少的墨水'], size=24, color=BLUE)
    # 自绘一张小示意图（PIL 画的三根柱），用来验证「图片不丢、列入报告」
    s.shapes.add_picture(_sketch_png(), Inches(7.6), Inches(5.2), Inches(2.0), Inches(1.5))
    s = bullets(p, '四类常用图表', [
        '比较：柱状图、条形图', '趋势：折线图、面积图', '构成：饼图、堆叠柱', '分布：直方图、箱线图'], size=22)
    s = blank(p)
    title(s, '制图四步法')
    box(s, 0.4, 1.6, 4.4, 2.4, ['1. 明确结论', '先写下这张图要说的一句话'], size=20, color=RED)
    box(s, 5.1, 1.6, 4.4, 2.4, ['2. 选择图表', '按比较、趋势、构成、分布选型'], size=16, color=GREEN)
    box(s, 0.4, 4.2, 4.4, 2.4, ['3. 去掉干扰', '删网格、删阴影、删 3D 效果'], size=24, color=BLUE)
    box(s, 5.1, 4.2, 4.4, 2.4, ['4. 突出重点', '只给关键数据上强调色'], size=18, color=ORANGE)
    chart(p, '课堂调查：最常用的图表类型', XL_CHART_TYPE.COLUMN_CLUSTERED,
          ['柱状图', '折线图', '饼图', '条形图', '散点图'], [('人数', (46, 31, 27, 15, 6))],
          ['共回收问卷 125 份', '柱状图最受欢迎', '散点图使用最少'])
    bullets(p, '常见误区', [
        '饼图切成十几块，谁也看不清', '纵轴不从 0 开始，夸大差异', '一张图塞五种颜色',
        '用 3D 效果装饰数据'], size=26, color=RED)
    bullets(p, '谢谢！', ['课后作业：用柱状图重画一张你见过的糟糕图表'], size=20)
    p.save(os.path.join(OUT, 'lecture-dataviz.pptx'))


def business():
    p = deck()
    cover(p, '2026 年三季度经营汇报', '华东区域销售中心', '汇报人：经营分析部　2026-10-10')
    agenda(p, ['核心指标', '月度营收', '渠道结构', '区域表现', '问题与下一步'])
    bullets(p, '核心指标', ['营收 3.2 亿元', '同比增长 18%', '毛利率 34.5%', '新客户 126 家'], size=32, color=BLUE)
    chart(p, '三季度月度营收（万元）', XL_CHART_TYPE.COLUMN_CLUSTERED, ['7 月', '8 月', '9 月'],
          [('2025 年', (8200, 8900, 9300)), ('2026 年', (9800, 10600, 11600))])
    chart(p, '渠道营收占比', XL_CHART_TYPE.PIE, ['直销', '经销', '线上'], [('占比', (52, 30, 18))],
          ['线上渠道占比首次超过 15%', '经销渠道同比下降 4 个百分点'])
    table(p, '区域表现', [['区域', '营收（万元）', '同比', '完成率'], ['上海', '12800', '+21%', '104%'],
                         ['江苏', '9600', '+15%', '98%'], ['浙江', '7100', '+19%', '101%'], ['安徽', '2500', '+9%', '87%']],
          ['安徽区域完成率低于 90%，需要重点跟进'])
    bullets(p, '存在的问题', ['安徽区域新客户开发偏慢', '9 月回款周期拉长到 52 天', ('其中经销渠道回款 61 天', 1),
                          '线上渠道客服响应超时较多'], size=22, color=RED)
    bullets(p, '下一步工作', ['十月底前完成安徽区域渠道复盘', '回款周期压回 45 天以内', '线上客服增配 6 人'],
            size=22, color=GREEN)
    bullets(p, '谢谢', ['欢迎批评指正'], size=24)
    p.save(os.path.join(OUT, 'business-q3.pptx'))


def proposal():
    p = deck()
    cover(p, '客服中心智能化改造方案', '从人工坐席到人机协同', '信息技术部　2026 年 10 月')
    agenda(p, ['现状与问题', '改造目标', '总体架构', '实施计划', '投入预算'])
    bullets(p, '现状与问题', ['日均来电 1.8 万通，高峰排队超过 6 分钟', '70% 的问题属于重复咨询',
                          '坐席流失率 28%，培训周期 3 周', '知识库分散在 4 个系统中'], size=20)
    bullets(p, '改造目标', ['自助解决率从 22% 提升到 55%', '平均等待时间降到 60 秒以内', '坐席人均处理量提升 40%'],
            size=28, color=BLUE)
    s = blank(p)
    title(s, '总体架构')
    for i, (layer, items) in enumerate([('渠道层', '电话　在线客服　小程序'), ('能力层', '语音识别　意图理解　知识检索'),
                                        ('数据层', '统一知识库　工单系统　客户画像')]):
        box(s, 0.4, 1.6 + i * 1.8, 2.0, 1.4, [layer], size=24, color=RED, bold=True)
        box(s, 2.6, 1.6 + i * 1.8, 7.0, 1.4, [items], size=18)
    table(p, '实施计划', [['阶段', '时间', '主要工作'], ['一期', '2026 年 11 月—12 月', '知识库整合与智能问答上线'],
                         ['二期', '2027 年 1 月—3 月', '语音机器人接入电话渠道'], ['三期', '2027 年 4 月—6 月', '坐席辅助与质检全面推广']])
    chart(p, '投入预算（万元）', XL_CHART_TYPE.BAR_CLUSTERED, ['软件平台', '硬件设备', '实施服务', '培训运营'],
          [('预算', (380, 120, 210, 90))], ['合计 800 万元', '软件平台占比最高'])
    bullets(p, '谢谢', ['请各位领导审议'], size=24)
    p.save(os.path.join(OUT, 'proposal-callcenter.pptx'))


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    lecture(); business(); proposal()
    print('samples ->', OUT)
