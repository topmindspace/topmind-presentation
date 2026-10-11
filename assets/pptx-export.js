/* ═══════════════════════════════════════════════════════════════════════════
 * TopPPT HTML· 浏览器端 PPTX 预览运行时
 * 零依赖、随报告单文件分发；OOXML 序列化器（仅供预览，页面不导出文件）。
 *
 * 定位：HTML 是阅读与演示界面，PPTX 是协作与修改格式——两者来自同一内容模型
 * （window.REPORT_MODEL）。页面只提供「预览 PPTX」（WYSIWYG 模态，与智能体精导通道
 * 同一序列化引擎）与可复制 AI 提示词；正式 PPTX 一律由本地智能体走精导通道
 * （build_pptx.js）生成并过 strict 硬门禁，浏览器端导出达不到该质量标准。
 *
 * API：
 *   TopPptHtml.slidesXml(model)           → string[]（每页 slide XML，预览模态渲染用）
 *   TopPptHtml.validateModel(model)       → {ok, missing[], warnings[], pages}（schema 单源驱动）
 *   TopPptHtml.slidesOf / slideXml / relsXml / NS / PRESETS
 *                                       → 供 scripts/gen_channel_a.js 在 Node 侧组装完整
 *                                         PPTX 包（回归双裁判内部质量路径，页面不使用）
 *
 * model = window.REPORT_MODEL（JSON，与页面正文同源）：
 *   { mode, style, theme(light|dark：PPTX 按此选亮/暗 token，默认 light),
 *     title, subtitle, meta, agenda:[[num,标题,说明]…](architecture 可省),
 *     sections:[{type: points|metrics|kpi|table|timeline|steps|bar|donut|heatmap|bullet|pyramid|
 *                     image|cards|split|comparison|quote|diagram|exhibit|twocol|threecol|halftable|
 *                     matrix|lane, soWhat?, footnote?, flags?, image?, …}],
 *     closing:{title,points} }
 *   通用可选字段：soWhat（结论条）/ footnote（来源行）/ flags（待核实清单 → accent 强调色条）
 *                / image（素材图片或配图占位，{src|items|placeholder, layout, fit, caption, alt, hint}，
 *                  src 仅 data: 或相对路径；layout ∈ full/half/bleed/grid/compare/wall，见 layout-constants.json imageSpec）。
 *   页型字段定义（29 种）与 chart.type 白名单（30 类）的唯一事实源：scripts/model-schema.json。
 *
 * ★ 单源机制（scripts/sync_runtime.py 注入，标记块内禁止手改）：
 *   - 版式常量：scripts/layout-constants.json → __TOPPPT_CONSTANTS__ 块；
 *     通道 B（build_pptx.js）require 同一份 JSON，两通道产出一致。
 *   - DSL schema：scripts/model-schema.json → __TOPPPT_SCHEMA__ 块；
 *     scripts/extract_model.py 读同一份文件，双端校验同源。
 * ★ 三模式独立排版比例尺（MTS）——research 咨询密排 / architecture 全幅图页型；
 *   modeSize() 把调用点的 presentation 基准 pt 映射到当前模式比例尺。
 * ★ 本运行时只做「预览与回归裁判」：图表为形状近似渲染（交付通道 B 用原生数据图表，
 *   可在 PowerPoint 中"编辑数据"）；文本与版式几何两通道同源，cross_verify 逐页比对。
 * ═══════════════════════════════════════════════════════════════════════════ */
(function (g) {
'use strict';
/* 双形态载荷判定：[[t,d]…] 数组 vs [{t,d,accent}…] 记录。typeof [] === 'object'。 */
function isRec(v) { return !!v && typeof v === 'object' && !Array.isArray(v); }

/* __TOPPPT_CONSTANTS_START__ */
/* ── 由 scripts/sync_runtime.py 从 scripts/layout-constants.json 注入 · 禁止手改 ── */
/* MTS = 三模式独立排版比例尺（按模式取 pt；基准 TS_BASE = presentation 档） */
/* PRESETS_DARK = 风格 dark token（REPORT_MODEL.theme="dark" 时导出深色版）*/
/* GRID = 12 列网格；TYPO = 语义字阶 C0–T14；CONT = 容器内边距；REG = 图表登记四元组；DEEP = 深度模式配置 */
/* IMG = 素材图片规格与配图占位约定（版式/裁切/建议尺寸/占位标签，双引擎同源） */
/* STYLE_DATA_COLORS(_DARK) = 9 套风格各自的编码色板 c1–c5（数据系列；结构色纪律不变） */
/* LAYOUT_SLOTS + regionOf = 页型布局区域 IR（与 scripts/lib_layout_regions.js 同源） */
var PW = 13.333, PH = 7.5, MX = 0.6, CW = PW - 2 * MX, EMU = 914400;
var TS_BASE = {"coverTitle":44,"coverSub":18,"h1":30,"h2":17,"lead":14,"body":13,"caption":11,"micro":10};
var MTS = {"presentation":{"coverTitle":44,"coverSub":18,"h1":30,"h2":17,"lead":14,"body":13,"caption":11,"micro":10},"research":{"coverTitle":36,"coverSub":14,"h1":22,"h2":13.5,"lead":11.5,"body":10.5,"caption":9,"micro":8.5},"architecture":{"coverTitle":44,"coverSub":19,"h1":30,"h2":17,"lead":14,"body":13,"caption":11,"micro":10}};
var PT = {"layout":{"contentTop":2.35,"contentBottom":6.9,"contentBottomWithNote":6.4,"pageNumY":7.0},"common":{"headEyebrowY":0.48,"headTitleY":0.82,"headRuleY":1.72,"leadY":1.88,"bodyY":2.35,"bodyYWithLead":2.55,"pagerY":7.0},"cover":{"metaY":0.7,"titleY":2.4,"titleH":2.0,"subtitleY":4.5,"subtitleH":0.8},"closing":{"eyebrowY":0.7,"titleY":1.2,"titleH":1.2,"pointsY":3.0,"pointTitleH":0.6,"pointBodyH":1.2},"points":{"listY":2.5,"rowH":0.72,"rowHMin":0.5,"markSize":0.14,"metricY":4.7,"metricW":2.6,"metricValH":0.9,"metricCapY":5.6},"metrics":{"bandY":3.1,"cardH":2.3,"valY":3.45,"valH":1.1,"capY":4.55,"capH":0.7,"gap":0.3,"maxW":2.9},"table":{"y":2.5,"rowH":0.55,"rowHMin":0.32,"headRowH":0.5},"bar":{"hbarY0":2.6,"hbarY1":6.25,"chartX":0.6,"chartY":2.95,"chartW":1.2,"chartH":3.35,"noteY":6.55},"note":{"y":6.55,"h":0.4},"exhibit":{"badgeY":2.35,"chartY":2.75,"chartH":3.25,"soWhatY":6.05,"footnoteY":6.72},"twocol":{"colGap":0.5,"bodyH":3.6,"rowHMin":0.5},"hbar":{"labelW":1.9,"valW":1.0,"rowH":0.55,"barRatio":0.5},"diagram":{"layerBarW":1.35,"layerGap":0.15,"nodeGap":0.15,"bodyStartY":2.9,"maxLayerH":1.15,"nodeMaxW":2.2},"split":{"leftW":0.55,"rightW":0.415,"rightX":0.585,"pointsY":2.7,"rowH":0.78,"capY":2.55,"chartY":3.0,"chartH":3.7,"tableY":2.7,"tableRowH":0.5},"cards":{"startY":3.0,"gap":0.25,"maxH":2.0,"titleH":0.4},"timeline":{"labelY":2.95,"axisY":3.58,"dotY":3.51,"dotR":0.18,"nameY":3.9,"descY":4.45,"descH":1.2},"research":{"col3Gap":0.38,"matrixLabelW":1.5,"matrixCellH":0.85,"matrixY":2.2,"denseTableY":2.2,"denseRowH":0.42,"halfTableW":0.52,"halfChartX":0.57,"halfChartW":0.43},"arch":{"fullStartY":2.1,"fullEndY":6.9,"laneH":0.72,"laneHMin":0.5,"laneGap":0.14,"laneHeadW":1.3,"stepGap":0.12,"stepMaxW":1.9},"kpi":{"heroY":2.9,"heroW":0.52,"heroH":1.6,"dividerX":0.56,"metricY0":2.95,"metricRowH":0.85},"comparison":{"panelGap":0.4,"panelY":2.55,"panelH":3.4,"titleH":0.45,"rowH":0.62},"quote":{"markY":1.75,"textY":2.7,"textH":2.3,"authorY":5.25,"contextY":5.8},"donut":{"centerX":3.05,"centerY":4.6,"r":1.6,"holeR":0.95,"legendX":5.6,"legendRowH":0.55,"legendLabelW":3.4,"legendValW":1.3,"legendPctX":10.8,"legendPctW":1.3},"steps":{"y":3.05,"barH":1.35,"gap":0.12,"arrowW":0.3,"numH":0.3,"titleH":0.34,"pad":0.08,"maxPerRow":6},"heatmap":{"y":2.6,"labelW":1.7,"headH":0.42,"cellH":0.6,"cellGap":0.06,"legendW":1.6},"pyramid":{"y":2.35,"rowH":0.72,"gap":0.08,"minW":0.34,"labelW":3.2},"bullet":{"y":2.6,"rowH":0.8,"labelW":2.4,"valW":1.7,"barH":0.26},"image":{"y":2.3,"h":4.2,"halfW":0.56,"halfGap":0.06,"capY":6.6,"capH":0.3,"radius":0.09,"noteRowH":0.62,"gridGap":0.16,"gridCols":{"2":2,"3":3,"4":4,"6":3},"gridCapH":0.28,"compareGap":0.3,"compareTagH":0.26,"wallCellH":0.92,"wallGap":0.18,"wallMaxRows":2},"flagbar":{"hdH":0.26,"rowH":0.24,"maxRows":3,"gap":0.12},"sankey":{"y":2.45,"h":4.1,"nodeW":0.32,"nodeGap":0.14,"labelW":1.55,"minBandH":0.22,"maxNodes":12,"maxFlows":24},"treemap":{"y":2.45,"h":4.1,"gap":0.05,"labelMinH":0.34,"maxLeaves":16,"maxDepth":3},"boxplot":{"y":2.7,"h":3.7,"labelW":1.5,"groupGap":0.3,"boxMaxW":0.9,"whiskerCapW":0.34,"maxGroups":8},"network":{"y":2.4,"h":4.2,"nodeR":0.28,"nodeRMin":0.18,"labelMaxW":1.4,"maxNodes":18,"maxEdges":30},"marimekko":{"y":2.6,"h":3.75,"labelW":1.55,"colGap":0.06,"legendH":0.42,"maxCols":6,"maxSegs":4},"streamgraph":{"y":2.6,"h":3.75,"labelW":1.4,"bandMinH":0.12,"maxSeries":6}};
var PRESETS = {
  'business-blue': { accent:'1A73E8', ink:'202124', body:'5F6368', faint:'80868B', bg:'FFFFFF', surface:'F8F9FA', line:'DADCE0', soft:'E8F0FE', onAccent:'FFFFFF', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'apple-mono': { accent:'1D1D1F', ink:'1D1D1F', body:'6E6E73', faint:'86868B', bg:'FFFFFF', surface:'F5F5F7', line:'D2D2D7', soft:'F5F5F7', onAccent:'FFFFFF', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'mckinsey': { accent:'003A70', ink:'101828', body:'475467', faint:'667085', bg:'FFFFFF', surface:'F2F4F7', line:'D0D5DD', soft:'EEF4FB', onAccent:'FFFFFF', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'brand-red': { accent:'D0021B', ink:'1F1A1B', body:'5D5456', faint:'8A8083', bg:'FFFFFF', surface:'FAF7F7', line:'E2D9DA', soft:'FBECEC', onAccent:'FFFFFF', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'warm-sand': { accent:'96681F', ink:'2A2521', body:'6B5F52', faint:'93836F', bg:'FBF9F6', surface:'F6F2EC', line:'E0D7C9', soft:'F3ECDD', onAccent:'FFFFFF', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'deep-teal': { accent:'0F6B5C', ink:'14201E', body:'4A5A57', faint:'73837F', bg:'FFFFFF', surface:'F2F6F5', line:'CFDEDC', soft:'E4F1EE', onAccent:'FFFFFF', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'graphite-dark': { accent:'0369A1', ink:'1A1D21', body:'4B5158', faint:'767C84', bg:'F4F5F7', surface:'ECEEF1', line:'CED1D6', soft:'E2EFF7', onAccent:'FFFFFF', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'indigo-violet': { accent:'5B5BD6', ink:'1B1A2E', body:'52506B', faint:'7A779A', bg:'FFFFFF', surface:'F4F4FB', line:'D7D7E8', soft:'ECECF9', onAccent:'FFFFFF', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'spectrum': { accent:'4563EF', ink:'171A21', body:'4D5566', faint:'7B8494', bg:'FBFCFE', surface:'F4F6FA', line:'D6DCE6', soft:'ECEEFF', onAccent:'FFFFFF', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' }
};
var PRESETS_DARK = {
  'business-blue': { accent:'8AB4F8', ink:'E8EAED', body:'ADB4BD', faint:'868D96', bg:'0D0F13', surface:'191D23', line:'2F353D', soft:'16243A', onAccent:'0D1B2E', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'apple-mono': { accent:'F5F5F7', ink:'F5F5F7', body:'A1A1A6', faint:'86868B', bg:'000000', surface:'161617', line:'38383D', soft:'1D1D1F', onAccent:'000000', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'mckinsey': { accent:'7FB2E5', ink:'E4E7EC', body:'AAB3C2', faint:'8A94A6', bg:'0C1116', surface:'12181F', line:'2A3342', soft:'12233A', onAccent:'0C1A2E', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'brand-red': { accent:'FF5A66', ink:'F3ECEC', body:'C4B6B7', faint:'9A8D8E', bg:'130D0E', surface:'1A1213', line:'37272A', soft:'331518', onAccent:'2A0D10', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'warm-sand': { accent:'D9B36A', ink:'ECE5DB', body:'C4B8A8', faint:'9B8D7A', bg:'15120E', surface:'1D1913', line:'3A3128', soft:'2E2417', onAccent:'2A1F10', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'deep-teal': { accent:'4FC3B0', ink:'E2ECEA', body:'B3C2BF', faint:'86948F', bg:'0D1312', surface:'131B1A', line:'293834', soft:'12312C', onAccent:'0C2420', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'graphite-dark': { accent:'4DA3FF', ink:'EEF2F6', body:'B9C2CD', faint:'85909D', bg:'0B0E12', surface:'171D24', line:'2B3540', soft:'132841', onAccent:'07182B', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'indigo-violet': { accent:'A5A4F0', ink:'E6E5F5', body:'B6B4D4', faint:'8B89B0', bg:'100F1C', surface:'171629', line:'322F52', soft:'232146', onAccent:'171631', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'spectrum': { accent:'8BA0F8', ink:'E8EBF2', body:'A7AFBF', faint:'7E8798', bg:'0E1116', surface:'171C26', line:'2B3342', soft:'1B2242', onAccent:'141A38', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' }
};
var STYLE_DATA_COLORS = {"business-blue":["1a73e8","3526bb","21a199","b77148","99983d"],"apple-mono":["1d1d1f","0071e3","0f7b6c","c2410c","7c3aed"],"mckinsey":["003a70","2826bb","21a18e","b76848","99903d"],"brand-red":["d0021b","bb6326","d634ae","40a182","438aa8"],"warm-sand":["96681f","839324","cf3b3e","4d88b2","4a47a4"],"deep-teal":["0f6b5c","2683bb","22aa3e","b74870","a85c43"],"graphite-dark":["0369a1","2637bb","1f9977","b75948","a18a40"],"indigo-violet":["5b5bd6","7432ae","4197c8","a08f4b","7ca04b"],"spectrum":["4563ef","5b26bb","269ebb","af8746","83993d"]};
var STYLE_DATA_COLORS_DARK = {"business-blue":["8ab4f8","7966e0","88e7e5","d4ad91","cbce83"],"apple-mono":["f5f5f7","2997ff","2dd4bf","ff9f0a","bf5af2"],"mckinsey":["7fb2e5","6f6bdb","8ce3d8","d1a694","cbc586"],"brand-red":["ff5a66","e09e66","e788cb","91d4c2","83b4ce"],"warm-sand":["d9b36a","c2d571","df9391","97b5ce","8e89c7"],"deep-teal":["4fc3b0","7aaecd","97d8a4","c99cac","c29c8f"],"graphite-dark":["4da3ff","6c66e0","88e7dc","d4a691","cec983"],"indigo-violet":["a5a4f0","a967e0","89c3e7","d3c792","aece83"],"spectrum":["8ba0f8","9066e0","88d6e7","d4ba91","bdce83"]};
var GRID = {"columns":12,"gutter":0.16,"colW":0.8644,"x":[0.6,1.6244,2.6488,3.6732,4.6976,5.722,6.7464,7.7708,8.7952,9.8196,10.844,11.8684,12.733],"y":[2.35,3.27,4.19,5.11,6.03,6.9],"safe":{"top":0.4,"bottom":0.4,"left":0.6,"right":0.6}};
var TYPO = {"levels":[{"id":"C0","name":"封面/章节幕标题","role":"coverTitle","usage":"封面主标题、章节幕标题"},{"id":"T1","name":"页码/章节徽章","role":"caption","usage":"页码徽章、章节编号"},{"id":"T2","name":"页面主标题/结论标题","role":"h1","usage":"每页顶部结论句（research 行动标题）"},{"id":"T3","name":"副标题/语境说明","role":"lead","usage":"主标题下方导语"},{"id":"T4","name":"模块标题/图表标题","role":"h2","usage":"卡片标题、图表标题、面板标题"},{"id":"T5","name":"证据编号/轻量标签","role":"micro","usage":"Exhibit 编号、状态标签"},{"id":"T6","name":"证据块标题/小节标题","role":"h2","usage":"分栏小标题、证据块标题"},{"id":"T7","name":"正文解释段落","role":"body","usage":"证据解释、管理解读正文、表格正文"},{"id":"T8","name":"结论条文字","role":"body","usage":"结论条、核心结论框"},{"id":"T9","name":"结论条标签（可选·默认隐藏）","role":"caption","usage":"结论条可选标签（默认不显示）"},{"id":"T10","name":"结论条正文/业务含义","role":"body","usage":"结论条正文、行动含义、表格行动项"},{"id":"T11","name":"图表轴/图例/刻度/微标签","role":"micro","usage":"坐标轴、图例、刻度、单位（禁用于表格正文与完整短句）"},{"id":"T12","name":"图表数据标签","role":"caption","usage":"折线点值、柱形标签、百分比标注"},{"id":"T13","name":"关键 KPI 大数字","role":"h1","usage":"KPI 大数字、hero 数值"},{"id":"T14","name":"注释/口径/来源/页脚","role":"micro","usage":"footnote、来源行、页脚、小页码"}],"tableSemanticRule":{"body":["T7","T10"],"microAllowed":["T11"],"microForbiddenFor":["表格正文","行动项","风险项","解释句","建议句","长项目符号","完整短句"]}};
var CONT = {"pad":{"card":0.18,"panel":0.2,"cell":0.08,"band":0.16,"soWhat":0.16,"kpi":0.18,"chart":0.1,"head":0.05,"footer":0.05,"node":0.06},"minPad":0.06,"textMetrics":{"lineFactor":1.45,"emAsciiRatio":0.52},"overflowRule":"溢出处置优先级（禁静默截断）：① 重构承载（列表/卡片/表/图/组合版式）→ ② 拆页/分章（议程→主张→证据卡→明细；01a/01b；信息须完整）→ ③ 换布局形态（V1–V4/多列/卡栅格）→ ④ 有限 fontShrink（阶梯内、模式 floor 以上、最多 4 档）→ ⑤ 禁止：静默截断、砍 so-what/证据/口径、为审美稀疏删决策必需信息。单页字数预算是预警不是删字许可证。","fontShrink":{"ladder":[15,14,13.5,13,12.5,12,11.5,11,10.5,10,9.5,9,8.5],"maxShrinkSteps":4,"floorPt":{"presentation":10,"research":9,"architecture":10},"preferContentFirst":true,"warnBelow":9.5},"continuousTextRule":"语义连续的一句话 / so-what 主句 / 结论句 / 表格单元格正文不得拆成多个独立文本框（避免异常空格、断句、基线漂移）；局部加粗高亮必须用同一文本框内富文本。","adaptiveText":{"title":{"base":30,"step1":24,"longChars":28,"longMax":24,"xlongChars":44,"xlongMax":20},"list":{"denseItems":6,"gapFactor":0.5,"denseGapFactor":0.25,"lineFactor":1.45,"denseLineFactor":1.3,"max":14,"denseMax":12},"table":{"cellMax":12.5,"cellFloor":9,"headMax":13,"longCellChars":24,"rowFloorIn":0.22,"cellPadIn":0.07}}};
var REG = {"bar":{"html":"svg-bars","pptx":"native","nativeType":"bar","dataTable":"notes","min":{"vbHeightMin":160}},"hbar":{"html":"svg-hbars","pptx":"native","nativeType":"bar","dataTable":"notes","min":{"vbHeightMin":100}},"stack":{"html":"svg-stack","pptx":"native","nativeType":"bar","dataTable":"notes","min":{"vbHeightMin":160},"nativeOpt":{"barGrouping":"stacked"}},"stackline":{"html":"svg-stackline","pptx":"native","nativeType":"bar","dataTable":"notes","min":{"vbHeightMin":40},"nativeOpt":{"barGrouping":"percentStacked"}},"line":{"html":"svg-line","pptx":"native","nativeType":"line","dataTable":"notes","min":{"vbHeightMin":160}},"dualline":{"html":"svg-dualline","pptx":"native","nativeType":"line","dataTable":"notes","min":{"vbHeightMin":160}},"area":{"html":"svg-area","pptx":"native","nativeType":"area","dataTable":"notes","min":{"vbHeightMin":160}},"donut":{"html":"svg-donut","pptx":"native","nativeType":"doughnut","dataTable":"notes","min":{"pxWidthMin":140}},"multidonut":{"html":"svg-mdonut","pptx":"native","nativeType":"doughnut","dataTable":"notes","min":{"pxWidthMin":140}},"pie":{"html":"svg-pie","pptx":"native","nativeType":"pie","dataTable":"notes","min":{"pxWidthMin":140}},"radar":{"html":"svg-radar","pptx":"native","nativeType":"radar","dataTable":"notes","min":{"pxWidthMin":220}},"scatter":{"html":"svg-scatter","pptx":"native","nativeType":"scatter","dataTable":"notes","min":{"vbHeightMin":180}},"bubble":{"html":"svg-bubble","pptx":"native","nativeType":"bubble","dataTable":"notes","min":{"vbHeightMin":180}},"waterfall":{"html":"svg-wf","pptx":"native","nativeType":"bar","dataTable":"notes","min":{"vbHeightMin":170},"nativeTrick":"stacked+hiddenBase+connector"},"gauge":{"html":"svg-gauge","pptx":"native","nativeType":"doughnut","dataTable":"notes","min":{"pxWidthMin":180},"nativeTrick":"doughnut+firstSliceAng+hiddenRemainder"},"pareto":{"html":"svg-pareto","pptx":"native","nativeType":"bar","dataTable":"notes","min":{"vbHeightMin":180},"nativeTrick":"multiType+bar+line"},"gantt":{"html":"svg-gantt","pptx":"shape","dataTable":"notes","min":{"vbHeightMin":130},"path":{"forbidPresetShapes":true}},"vsbar":{"html":"svg-vsbar","pptx":"shape","dataTable":"notes","min":{"vbHeightMin":100},"path":{"forbidPresetShapes":true}},"progress":{"html":"svg-progress","pptx":"shape","dataTable":"notes","min":{"vbHeightMin":100},"path":{"forbidPresetShapes":true}},"sparkline":{"html":"svg-spark","pptx":"shape","dataTable":"off","min":{"vbHeightMin":20},"path":{"forbidPresetShapes":true}},"funnel":{"html":"svg-funnel","pptx":"shape","dataTable":"notes","min":{"vbHeightMin":160},"path":{"minSamplePoints":8,"forbidPresetShapes":true}},"treemap":{"html":"svg-treemap","pptx":"shape","dataTable":"appendix","min":{"vbHeightMin":170},"path":{"forbidPresetShapes":true}},"marimekko":{"html":"svg-marimekko","pptx":"shape","dataTable":"appendix","min":{"vbHeightMin":160},"path":{"forbidPresetShapes":true}},"boxplot":{"html":"svg-boxplot","pptx":"shape","dataTable":"appendix","min":{"vbHeightMin":180},"path":{"forbidPresetShapes":true}},"network":{"html":"svg-network","pptx":"shape","dataTable":"appendix","min":{"vbHeightMin":200},"path":{"forbidPresetShapes":true}},"sankey":{"html":"svg-sankey","pptx":"shape","dataTable":"appendix","min":{"vbHeightMin":200},"path":{"minSamplePoints":16,"trackBothEdges":true,"forbidPresetShapes":true}},"streamgraph":{"html":"svg-stream","pptx":"shape","dataTable":"appendix","min":{"vbHeightMin":160},"path":{"minSamplePoints":24,"trackBothEdges":true,"forbidPresetShapes":true}},"slope":{"html":"svg-slope","pptx":"shape","dataTable":"notes","min":{"vbHeightMin":180},"path":{"forbidPresetShapes":true}},"dumbbell":{"html":"svg-dumbbell","pptx":"shape","dataTable":"notes","min":{"vbHeightMin":160},"path":{"forbidPresetShapes":true}},"lollipop":{"html":"svg-lollipop","pptx":"shape","dataTable":"notes","min":{"vbHeightMin":140},"path":{"forbidPresetShapes":true}},"dotplot":{"html":"svg-dotplot","pptx":"shape","dataTable":"notes","min":{"vbHeightMin":120},"path":{"forbidPresetShapes":true}},"bulletchart":{"html":"svg-bullet","pptx":"shape","dataTable":"notes","min":{"vbHeightMin":140},"path":{"forbidPresetShapes":true}},"waffle":{"html":"svg-waffle","pptx":"shape","dataTable":"notes","min":{"vbHeightMin":160},"path":{"forbidPresetShapes":true}},"radialbar":{"html":"svg-radialbar","pptx":"shape","dataTable":"notes","min":{"pxWidthMin":200},"path":{"minSamplePoints":16,"forbidPresetShapes":true}},"rose":{"html":"svg-rose","pptx":"shape","dataTable":"notes","min":{"pxWidthMin":180},"path":{"minSamplePoints":16,"forbidPresetShapes":true}},"candlestick":{"html":"svg-candle","pptx":"shape","dataTable":"appendix","min":{"vbHeightMin":180},"path":{"forbidPresetShapes":true}}};
var DEEP = {"triggers":["高保真","1:1","一比一","精确还原","按图还原","正式交付","不能偏移","像素级","严格对照","逐页验收"],"complexCharts":["sankey","streamgraph","treemap","marimekko","boxplot","network","rose","radialbar","candlestick","funnel"],"checks":{"anchors":true,"containerOverflow":true,"renderCompare":true,"manifest":true},"renderCompare":{"engine":"soffice","fallback":"powerpoint-com","skipIfMissing":true,"dpi":96}};
var IMG = {"layouts":["full","half","bleed","grid","compare","wall"],"multiLayouts":["grid","compare","wall"],"fitEnum":["cover","contain"],"fitDefault":"cover","formats":["png","jpeg","jpg","webp","svg"],"ratioDefault":{"full":"3:1","half":"4:3","bleed":"21:9","grid":"4:3","compare":"4:3","wall":"1:1"},"ratioCssClass":{"full":"media--r3-1","half":"media--r4-3","bleed":"media--r21-9","grid":"media--r4-3","compare":"media--r4-3","wall":"media--r1-1"},"recommendedSizePx":{"full":"2400×800","half":"1400×1050","bleed":"2560×1100","grid":"900×675","compare":"1400×1050","wall":"480×480"},"maxInlineBytes":1572864,"maxTotalInlineBytes":8388608,"maxPerPage":6,"placeholderLabel":"配图占位","placeholderHintPrefix":"建议 ","placeholderHintSuffix":"px","zeroExternal":true,"qualityRule":"位图优先提供 ≥2× 显示尺寸；截图用 16:9 或 4:3 锁定比例；数据图不要用截图（应用内联 SVG 图表，可随主题变色）。"};
var LAYOUT_SLOTS = {"version":"0.1","pageTypes":{"points":{"mode":["presentation","research","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".grid.g-2 / .card / .ul","pptx":"points columns","minUnits":1},{"id":"annotation","role":"annotation","required":false,"html":".sowhat / .note","pptx":"soWhatBar / footnoteLine"}]},"metrics":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".metric","pptx":"metric row","minUnits":4},{"id":"annotation","role":"annotation","required":false,"html":"口径行 / .sowhat","pptx":"footnoteLine / soWhatBar"}]},"kpi":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"hero","role":"primary","required":true,"html":".t-metric hero","pptx":"hero number"},{"id":"metrics","role":"secondary","required":false,"html":".metric","pptx":"support metrics"},{"id":"annotation","role":"annotation","required":false,"html":".sowhat / .note","pptx":"soWhatBar"}]},"exhibit":{"mode":["research","presentation"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead / .exhibit__hd","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"svg[data-chart] / .exhibit","pptx":"nativeChart | shapeChart","channel":"registry"},{"id":"secondary","role":"secondary","required":false,"html":"要点列表","pptx":"side bullets"},{"id":"annotation","role":"annotation","required":true,"html":".exhibit__src / .sowhat","pptx":"footnoteLine / soWhatBar / notes"}]},"split":{"mode":["presentation","research","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"left","role":"primary","required":true,"html":"左区（points/table/image/chart）","pptx":"left zone"},{"id":"right","role":"secondary","required":true,"html":"右区（points/table/image/chart）","pptx":"right zone"},{"id":"annotation","role":"annotation","required":false,"html":".sowhat / .note","pptx":"soWhatBar"}]},"table":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".tbl-wrap table","pptx":"addTable","maxRows":{"presentation":8,"research":16}},{"id":"annotation","role":"annotation","required":false,"html":".sowhat / .note","pptx":"soWhatBar / footnoteLine"}]},"bar":{"mode":["presentation","research","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"svg[data-chart]","pptx":"nativeChart | shapeChart","channel":"registry"},{"id":"annotation","role":"annotation","required":true,"html":"note / dataTable","pptx":"footnoteLine / notes / inline table"}]},"donut":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"svg[data-chart=donut]","pptx":"addChart doughnut"},{"id":"annotation","role":"annotation","required":false,"html":"中心合计 / 图例 / .note","pptx":"center label / legend / notes"}]},"twocol":{"mode":["research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".cols-2","pptx":"two text columns"},{"id":"annotation","role":"annotation","required":false,"html":".sowhat","pptx":"soWhatBar"}]},"threecol":{"mode":["research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".cols-3","pptx":"three text columns"},{"id":"annotation","role":"annotation","required":false,"html":".sowhat","pptx":"soWhatBar"}]},"halftable":{"mode":["research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"左表","pptx":"addTable left"},{"id":"secondary","role":"secondary","required":true,"html":"右图","pptx":"chart right"},{"id":"annotation","role":"annotation","required":false,"html":".sowhat","pptx":"soWhatBar"}]},"matrix":{"mode":["research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".matrix","pptx":"matrix cells"},{"id":"annotation","role":"annotation","required":false,"html":".sowhat","pptx":"soWhatBar"}]},"comparison":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"left","role":"primary","required":true,"html":"左面板","pptx":"left panel"},{"id":"right","role":"secondary","required":true,"html":"右面板","pptx":"right panel"},{"id":"annotation","role":"annotation","required":false,"html":"verdict / .sowhat","pptx":"verdict bar"}]},"quote":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"金句正文","pptx":"quote text"}]},"timeline":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".tl","pptx":"timeline axis"}]},"steps":{"mode":["presentation","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".steps","pptx":"step row"}]},"cards":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".card grid","pptx":"card grid"}]},"heatmap":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".heat","pptx":"heat cells"}]},"bullet":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".bul","pptx":"bullet rows"}]},"pyramid":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".pyr","pptx":"pyramid layers"}]},"image":{"mode":["presentation","research","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".media*","pptx":"imageLayoutShapes"}]},"diagram":{"mode":["architecture","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".arch / layers","pptx":"layered nodes + edges","maxNodes":24,"maxLayers":4},{"id":"annotation","role":"annotation","required":false,"html":".arch__legend / .note","pptx":"legend chips / notes"}]},"lane":{"mode":["architecture","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".lane","pptx":"lanes + steps"}]},"sankey":{"mode":["research","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"svg[data-chart=sankey]","pptx":"infoSankey","maxNodes":12},{"id":"annotation","role":"annotation","required":true,"html":"dataTable / .note","pptx":"notes"}]},"treemap":{"mode":["research","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"svg[data-chart=treemap]","pptx":"infoTreemap"},{"id":"annotation","role":"annotation","required":true,"html":"dataTable / .note","pptx":"notes"}]},"boxplot":{"mode":["research","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"svg[data-chart=boxplot]","pptx":"infoBoxplot"},{"id":"annotation","role":"annotation","required":true,"html":"dataTable / .note","pptx":"notes"}]},"network":{"mode":["research","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"svg[data-chart=network]","pptx":"infoNetwork"},{"id":"annotation","role":"annotation","required":true,"html":"dataTable / .note","pptx":"notes"}]},"marimekko":{"mode":["research","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"svg[data-chart=marimekko]","pptx":"infoMarimekko"},{"id":"annotation","role":"annotation","required":true,"html":"dataTable / .note","pptx":"notes"}]},"streamgraph":{"mode":["research","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"svg[data-chart=streamgraph]","pptx":"infoStreamgraph"},{"id":"annotation","role":"annotation","required":true,"html":"dataTable / .note","pptx":"notes"}]}}};

/* regionOf(pageType, slotId, opts) — 页型布局区域 IR（与 scripts/lib_layout_regions.js 同源） */
function regionOf(pageType, slotId, opts) {
  var type = String(pageType || 'points'), slot = String(slotId || '');
  opts = opts || {};
  var L = PT.layout || {}, C = PT.common || {};
  var topDefault = C.bodyY || 2.5;
  var bottomDefault = opts.withNote ? (L.contentBottomWithNote || 6.4) : (L.contentBottom || 6.9);
  if (slot === 'head' || slot === 'chrome') {
    return { x: MX, y: C.headEyebrowY || 0.55, w: CW,
      h: Math.max(0.4, (C.headRuleY || 1.95) - (C.headEyebrowY || 0.55)),
      titleY: C.headTitleY, ruleY: C.headRuleY, leadY: C.leadY, bodyY: C.bodyY };
  }
  if (slot === 'annotation' || slot === 'soWhat') {
    var sy = (PT.exhibit && PT.exhibit.soWhatY != null) ? PT.exhibit.soWhatY : 6.05;
    return { x: MX, y: sy, w: CW, h: 0.62 };
  }
  if (slot === 'footnote') {
    var fy = (PT.exhibit && PT.exhibit.footnoteY != null) ? PT.exhibit.footnoteY : ((PT.note && PT.note.y) || 6.55);
    return { x: MX, y: fy, w: CW - 1.2, h: (PT.note && PT.note.h) || 0.32 };
  }
  var P = PT[type] || {};
  if (type === 'exhibit' && slot === 'primary') {
    var ey = P.chartY || 2.95;
    return { x: MX, y: ey, w: CW, h: Math.max(1.2, (L.contentBottomWithNote || 6.4) - ey), badgeY: P.badgeY };
  }
  if (type === 'metrics' && slot === 'primary') {
    return { x: MX, y: P.bandY || 3.1, w: CW, h: P.cardH || 2.3, gap: P.gap, maxW: P.maxW,
      valY: P.valY, valH: P.valH, capY: P.capY, capH: P.capH };
  }
  if (type === 'table' && slot === 'primary') {
    var ty = P.y || topDefault;
    return { x: MX, y: ty, w: CW, h: Math.max(1, (opts.bottom != null ? opts.bottom : bottomDefault) - ty) };
  }
  if (type === 'bar' && slot === 'primary') {
    var by = P.chartY || 2.95;
    var bb = opts.bottom != null ? opts.bottom : bottomDefault;
    /* chartX/chartW 历史误用已纠正：与 donut/table/hbar/exhibit 同口径，图表盒对齐版心 (MX, CW) */
    return { x: MX, y: by, w: CW, h: Math.max(1.2, bb - by) };
  }
  if (type === 'bar' && slot === 'hbar') {
    var y0 = P.hbarY0 || 2.6;
    var y1 = opts.bottom != null ? opts.bottom : (P.hbarY1 || 6.25);
    return { x: MX, y: y0, w: CW, h: Math.max(1.2, y1 - y0) };
  }
  if (type === 'points' && (slot === 'primary' || slot === 'list')) {
    var ly = P.listY || topDefault;
    return { x: MX, y: ly, w: CW, h: Math.max(0.8, (opts.bottom != null ? opts.bottom : bottomDefault) - ly) };
  }
  if (type === 'split' && (slot === 'left' || slot === 'right')) {
    var st = P.chartY || topDefault;
    var sb = opts.bottom != null ? opts.bottom : bottomDefault;
    if (slot === 'left') return { x: MX, y: st, w: CW * (P.leftW || 0.55), h: Math.max(1.2, sb - st) };
    return { x: MX + CW * (P.rightX != null ? P.rightX : 0.585), y: st, w: CW * (P.rightW || 0.415), h: Math.max(1.2, sb - st) };
  }
  if (type === 'twocol' && (slot === 'primary' || slot === 'left' || slot === 'right')) {
    var gap = P.colGap || 0.5, colW = (CW - gap) / 2;
    var tt = opts.top != null ? opts.top : topDefault;
    var tb = opts.bottom != null ? opts.bottom : bottomDefault;
    if (slot === 'right') return { x: MX + colW + gap, y: tt, w: colW, h: Math.max(1, tb - tt) };
    return { x: MX, y: tt, w: colW, h: Math.max(1, tb - tt) };
  }
  if ((type === 'diagram' || type === 'lane') && slot === 'primary') {
    var arch = PT.arch || {};
    var dy = (opts.mode === 'architecture' && arch.fullStartY != null) ? arch.fullStartY : (P.bodyStartY || 2.9);
    var db = (opts.mode === 'architecture' && arch.fullEndY != null) ? arch.fullEndY
      : (opts.bottom != null ? opts.bottom : bottomDefault);
    return { x: MX, y: dy, w: CW, h: Math.max(1.2, db - dy) };
  }
  if (type === 'kpi' && (slot === 'hero' || slot === 'primary')) {
    return { x: MX, y: P.heroY || 2.9, w: CW * (P.heroW || 0.52), h: P.heroH || 1.6,
      dividerX: P.dividerX, metricY0: P.metricY0, metricRowH: P.metricRowH };
  }
  /* R3：kpi 支撑指标列——落在 dividerX 右侧（默认全宽返回会压住 hero） */
  if (type === 'kpi' && slot === 'metrics') {
    var dxK = P.dividerX != null ? P.dividerX : 0.56;
    return {
      x: MX + CW * dxK + 0.35, y: P.metricY0 || 2.95,
      w: CW * (1 - dxK) - 0.5,
      h: Math.max(0.6, bottomDefault - (P.metricY0 || 2.95)),
    };
  }
  if (type === 'comparison' && (slot === 'left' || slot === 'primary' || slot === 'right')) {
    var cg = P.panelGap || 0.4, pw = (CW - cg) / 2;
    if (slot === 'right') return { x: MX + pw + cg, y: P.panelY || 2.55, w: pw, h: P.panelH || 3.4 };
    return { x: MX, y: P.panelY || 2.55, w: pw, h: P.panelH || 3.4 };
  }
  if (type === 'quote' && slot === 'primary') {
    return { x: MX + 1.05, y: P.textY || 2.7, w: CW - 2.1, h: P.textH || 2.3 };
  }
  if (type === 'heatmap' && slot === 'primary') {
    var hy = P.y || 2.6;
    return { x: MX, y: hy, w: CW, h: Math.max(1, (opts.bottom != null ? opts.bottom : bottomDefault) - hy) };
  }
  if (type === 'bullet' && slot === 'primary') {
    var uy = P.y || 2.6;
    return { x: MX, y: uy, w: CW, h: Math.max(1, (opts.bottom != null ? opts.bottom : bottomDefault) - uy) };
  }
  if (type === 'pyramid' && slot === 'primary') {
    var py2 = P.y || 2.35;
    return { x: MX, y: py2, w: CW, h: Math.max(1, (opts.bottom != null ? opts.bottom : bottomDefault) - py2) };
  }
  if (type === 'steps' && slot === 'primary') {
    return { x: MX, y: P.y || 3.05, w: CW, h: P.barH || 1.35 };
  }
  if (type === 'cards' && slot === 'primary') {
    var cy2 = P.startY || 3.0;
    return { x: MX, y: cy2, w: CW, h: Math.max(1, (opts.bottom != null ? opts.bottom : bottomDefault) - cy2) };
  }
  if (type === 'timeline' && slot === 'primary') {
    return { x: MX, y: P.labelY || 2.95, w: CW, h: Math.max(1, bottomDefault - (P.labelY || 2.95)) };
  }
  if (type === 'image' && slot === 'primary') {
    var iy2 = Math.max(P.y || 2.3, opts.top || 0);
    /* R2：有图注时图片不得越过 contentBottomWithNote（图注落注释带，属 annotation self） */
    var iBottom = (opts.bottom != null) ? opts.bottom
      : (opts.caption ? (L.contentBottomWithNote || 6.4) : bottomDefault);
    return { x: MX, y: iy2, w: CW, h: Math.max(1.2, Math.min(P.h || 4.2, iBottom - iy2)) };
  }
  if ((type === 'halftable') && (slot === 'left' || slot === 'primary')) {
    var rs = PT.research || {};
    var ht = opts.top != null ? opts.top : topDefault;
    var hb = opts.bottom != null ? opts.bottom : bottomDefault;
    return { x: MX, y: ht, w: CW * (rs.halfTableW || 0.52), h: Math.max(1, hb - ht) };
  }
  if ((type === 'halftable') && (slot === 'right' || slot === 'secondary')) {
    var rs2 = PT.research || {};
    var ht2 = opts.top != null ? opts.top : topDefault;
    var hb2 = opts.bottom != null ? opts.bottom : bottomDefault;
    return { x: MX + CW * (rs2.halfChartX || 0.57), y: ht2, w: CW * (rs2.halfChartW || 0.43), h: Math.max(1, hb2 - ht2) };
  }
  if (type === 'matrix' && slot === 'primary') {
    var rm = PT.research || {};
    var my = rm.matrixY || 2.3;
    return { x: MX, y: my, w: CW, h: Math.max(1, (opts.bottom != null ? opts.bottom : bottomDefault) - my) };
  }
  var INFO = { sankey:1, treemap:1, boxplot:1, network:1, marimekko:1, streamgraph:1 };
  if (INFO[type] && slot === 'primary') {
    var iy3 = P.y || topDefault;
    var ih3 = Math.max(1.2, Math.min(P.h || 4.1, (opts.bottom != null ? opts.bottom : bottomDefault) - iy3));
    return { x: MX, y: iy3, w: CW, h: ih3 };
  }
  return { x: MX, y: topDefault, w: CW, h: Math.max(0.8, bottomDefault - topDefault) };
}

/* __TOPPPT_CONSTANTS_END__ */

/* __TOPPPT_SCHEMA_START__ */
/* ── 由 scripts/sync_runtime.py 从 scripts/model-schema.json 注入 · 禁止手改 ── */
/* DSL schema 单源：浏览器端 validateModel 与 scripts/extract_model.py 消费同一份定义 */
var MODEL_SCHEMA = {"version":"0.1","modes":["presentation","research","architecture"],"model":{"required":["title","sections:array","closing.title","closing.points:array"],"optional":["mode","style","theme","subtitle","meta","agenda:array"],"agendaMin":{"presentation":3,"research":3,"architecture":0},"agendaMax":7,"agendaMaxWithRefs":8,"agendaHint":"agenda 条目 = 章（篇/section），3–7 条；每章可含多页（sections[] 按页建模）。禁止把逐页标题当大纲。sections[].eyebrow 的 `NN ·` 前缀 = 章键，须与某条 agenda 对应；跳转锚点 = 该章第一页。含「参考资料」条目时 +1 仍 ≤8。","sectionsMin":1,"sectionsRecommended":3,"agendaComfortMax":8},"commonSectionFields":["eyebrow","title","lead","soWhat","footnote","note","flags","image","exhibitNo","layoutPreset","variant","anchor"],"mutualExclusionHint":"verdict 与 soWhat 互斥：二者共用 annotation 结论条槽位，同页双填必叠印。comparison 页填 verdict 时不要再填 soWhat（渲染器已自动二选一，但模型侧应只给一个）。","flagsHint":"flags = 待核实/待二次修改条目字符串数组（如 '2027 增速 xx%（口径未定）'）；渲染为 accent 强调色标注行，提示用户核对。","imageHint":"image = 素材图片/配图占位对象。三选一必填：src（用户图，data: 内联或相对路径，零外链铁律禁 http(s)）｜items（多图版式：grid/compare/wall，元素 {src?, alt?, caption?, placeholder?}）｜placeholder:true（无图时出配图占位，原生形状渲染、pictures 不增）。其余可选：layout（full/half/bleed/grid/compare/wall，见 layout-constants.json imageSpec.layouts）、fit（cover 默认 / contain）、caption、alt、hint、ratio。","imageLayoutHint":"layout 与 HTML 版式对应：full=版心全宽图｜half=左图右注（points 为右栏注解）｜bleed=通栏出血｜grid=多图网格（items 2/3/4/6 张）｜compare=双图 A/B 对比（items 2 张）｜wall=Logo 墙（items 3–12 张小图）。占位符标签文本由双引擎按 imageSpec 拼同一串，保证 A/B 通道逐页文本一致。","chartTypes":["bar","hbar","stack","stackline","line","dualline","area","donut","multidonut","pie","radar","scatter","bubble","waterfall","gauge","pareto","funnel","gantt","vsbar","progress","sparkline","slope","dumbbell","lollipop","dotplot","bulletchart","waffle","radialbar","rose","candlestick"],"chartTypesHint":"chart.type 可取值 = 本表（30 类：16 原生 + 14 形状还原）。其余 6 类复杂信息图（sankey/treemap/boxplot/network/marimekko/streamgraph）是**专属页型**而非 chart.type——它们要按列/段/节点等结构化载荷表达，故走 sections[].type。不变量：charts.registry.types == chartTypes ∪ 上述 6 类页型（sync_runtime.py 校验）。","chartDataTable":{"enum":["notes","inline","appendix","off"],"default":"notes","rule":"非原生图表（registry.pptx=shape）的 dataTable 不得为 off；缺失时按 registry 默认值补齐。"},"pageTypes":{"points":{"label":"要点列表页","modes":["presentation","research","architecture"],"required":["points:array"],"optional":["metrics:array"]},"metrics":{"label":"指标带页（4–6 个核心数字）","modes":["presentation","research"],"required":["metrics:array"]},"kpi":{"label":"大数指标页（hero 大数字 + 支撑指标行）","modes":["presentation","research"],"required":["hero:array"],"optional":["metrics:array"]},"table":{"label":"对比表页","modes":["presentation","research","architecture"],"required":["table.head:array","table.rows:array"],"optional":["table.colW:array"]},"timeline":{"label":"时间线 / 路线页","modes":["presentation","research"],"required":["phases:array"]},"steps":{"label":"步骤条页（N 步横排 + 箭头，可分组）","modes":["presentation","research","architecture"],"required":["steps:array"],"optional":["groups:array","note"]},"bar":{"label":"图表页（chart.type 见 chartTypes；native 通道走原生数据图表，shape 通道走高保真形状还原 + 数据表）","modes":["presentation","research"],"required":["chart.labels:array","chart.values:array"],"optional":["chart.type","chart.series:array","chart.points:array","chart.max","chart.unit","chart.colors:array","chart.start:array","chart.target:array","chart.dataTable","note"]},"donut":{"label":"环形图页（原生 pie 楔形 + 图例）","modes":["presentation","research"],"required":["chart.labels:array","chart.values:array"],"optional":["chart.unit","chart.centerLabel","chart.colors:array","chart.dataTable","note"]},"heatmap":{"label":"热力矩阵页（行 × 列 + 强度色阶）","modes":["presentation","research"],"required":["rowHeads:array","colHeads:array","cells:array"],"optional":["unit","scaleLabel:array","note"]},"bullet":{"label":"达成对比页（实际 vs 目标条）","modes":["presentation","research"],"required":["items:array"],"optional":["unit","max","note"]},"pyramid":{"label":"金字塔页（层级递进，顶层最窄）","modes":["presentation","research","architecture"],"required":["levels:array"],"optional":["note"]},"image":{"label":"素材图片页（full/half/bleed/grid/compare/wall，效果与位置锁定；支持配图占位）","modes":["presentation","research","architecture"],"required":["anyof:image.src:str|image.items:array|image.placeholder"],"optional":["image.caption","image.alt","image.layout","image.fit","image.ratio","image.hint","points:array","note"]},"cards":{"label":"卡片网格页（cards 元素须为 {title, points:[[k,v]…], icon?}，不接受元组）","modes":["presentation","research"],"required":["cards:array"],"optional":["columns"],"cardItemHint":"cards[] 元素：{title:str, points:[[k,v]…]|[{t,d}…]|[str…], icon?:str}。icon = 语义图标名（icon_lib.js 键：增长/下降/数据/图表/趋势/占比/表格/效率/成果/安全/权限/检查/风险/团队/流程/计划/智能/洞察/工具/清单），HTML 与 PPTX 同名真导出；缺省按标题语义自动挑选。"},"split":{"label":"双区组合页（left / right 各可为 要点｜图表｜表格｜图片：type = points（默认）| table | image | 图表类型名；图表/表格字段直接挂在对应侧）","modes":["presentation","research"],"required":["anyof:left.points:array|left.type:str"],"optional":["left.cap","left.image","left.labels:array","left.values:array","left.series:array","left.points:array","left.max","left.unit","left.colors:array","left.dataTable","left.head:array","left.rows:array","left.colW:array","right.type","right.cap","right.image","right.labels:array","right.values:array","right.series:array","right.points:array","right.max","right.unit","right.colors:array","right.dataTable","right.head:array","right.rows:array","right.colW:array"]},"comparison":{"label":"对比页（左右双栏 + 可选结论条）","modes":["presentation","research"],"required":["left.title","left.points:array","right.title","right.points:array"],"optional":["verdict"]},"quote":{"label":"引用 / 金句页（深色全幅）","modes":["presentation","research"],"required":["quote","author"],"optional":["context"]},"diagram":{"label":"分层架构页（architecture 模式走全幅几何）","modes":["presentation","research","architecture"],"required":["layers:array"],"optional":["legend:array"]},"exhibit":{"label":"Exhibit 编号图表页（research R2）","modes":["research"],"required":["chart.labels:array","chart.values:array"],"optional":["exhibitNo","chart.type","chart.series:array","chart.points:array","chart.max","chart.unit","chart.colors:array","chart.dataTable","note"]},"twocol":{"label":"双栏论证页（research R1）","modes":["research"],"required":["paragraphs:array"]},"threecol":{"label":"三栏证据页（research R6）","modes":["research"],"required":["paragraphs:array"]},"halftable":{"label":"半表半图页（research R7）","modes":["research"],"required":["table.head:array","table.rows:array","chart.labels:array","chart.values:array"],"optional":["table.colW:array","chart.type","chart.series:array","chart.points:array","chart.max","chart.unit","chart.colors:array","chart.dataTable","note"]},"matrix":{"label":"矩阵图页（research R8）","modes":["research"],"required":["rowHeads:array","colHeads:array","cells:array"]},"lane":{"label":"泳道页（architecture A2）","modes":["architecture"],"required":["lanes:array"]},"sankey":{"label":"桑基图页（节点-流带，流向与流量）","modes":["research","architecture"],"required":["flows:array"],"optional":["unit","chart.dataTable","note"]},"treemap":{"label":"树图页（面积编码的层级构成）","modes":["research","architecture"],"required":["items:array"],"optional":["unit","chart.dataTable","note"]},"boxplot":{"label":"箱线图页（分布对比：min/q1/median/q3/max）","modes":["research","architecture"],"required":["groups:array"],"optional":["unit","chart.dataTable","note"]},"network":{"label":"关系网络页（节点-边拓扑）","modes":["research","architecture"],"required":["nodes:array","edges:array"],"optional":["chart.dataTable","note"]},"marimekko":{"label":"马赛克图页（列宽 × 列高双重编码）","modes":["research","architecture"],"required":["cols:array","cells:array"],"optional":["unit","chart.dataTable","note"]},"streamgraph":{"label":"流带图页（时间上的构成演变）","modes":["research","architecture"],"required":["series:array"],"optional":["labels:array","chart.dataTable","note"]}}};
/* __TOPPPT_SCHEMA_END__ */

var _mode = 'presentation';   /* 当前模式（slidesOf 里按 model.mode 设置） */
/* 三模式独立排版比例尺：调用点给 presentation 基准 pt → 取最接近的 TS_BASE 角色 →
   查 MTS[mode][role]。research 是咨询密排比例尺（正文 10.5pt），不再是简单 ×0.8。
   未知模式回落 presentation 档（MTS 与 mode 取值同源于 model-schema.json 的 modes）。 */
function modeSize(base) {
  var mts = (typeof MTS !== 'undefined' && MTS) ? (MTS[_mode] || MTS.presentation) : null;
  if (!mts) return base;
  var best = null, bd = 1e9;
  for (var k in TS_BASE) {
    if (!TS_BASE.hasOwnProperty(k)) continue;
    var d = Math.abs(TS_BASE[k] - base);
    if (d < bd) { bd = d; best = mts[k]; }
  }
  /* 钳制与取整必须与 build_pptx.js 的 sz() 逐字一致——同一张表配不同后处理 = 两通道字号漂移 */
  return Math.max(8.5, Math.round((best == null ? base : best) * 2) / 2);
}
/* 编码色板：9 套风格**各有自己的** c1–c5（单源 styleDataColors / styleDataColorsDark）。
   与 HTML 侧的 .f-c1~c5 语义类同源；结构色纪律不受影响——本表只用于数据系列。 */
function dataColors(style, theme) {
  var dark = (theme === 'dark');
  var map = (dark && typeof STYLE_DATA_COLORS_DARK !== 'undefined' && STYLE_DATA_COLORS_DARK)
    ? STYLE_DATA_COLORS_DARK
    : (typeof STYLE_DATA_COLORS !== 'undefined' ? STYLE_DATA_COLORS : null);
  if (!map) return null;
  var c = map[style];
  return (c && c.length) ? c : null; // null = 用 S 的中性色（在调用处映射）
}

/* ── 版式安全边界（与 build_pptx.js 同一常量单源） ── */
var LAY = PT.layout || {};
var CONTENT_TOP = (LAY.contentTop != null) ? LAY.contentTop : 2.5;
var CONTENT_BOTTOM = (LAY.contentBottom != null) ? LAY.contentBottom : 6.9;
var CONTENT_BOTTOM_NOTE = (LAY.contentBottomWithNote != null) ? LAY.contentBottomWithNote : 6.4;

/* ── 自适应排版工具（与 build_pptx.js 同算法，保证两通道字号/换行一致） ── */
function estLines(text, widthIn, fontPt) {
  var usable = Math.max(24, widthIn * 72 - 8), w = 0, lines = 1;
  var s = String(text == null ? '' : text);
  for (var i = 0; i < s.length; i++) {
    if (s[i] === '\n') { lines++; w = 0; continue; }
    var cw = /[\x00-\xff]/.test(s[i]) ? fontPt * 0.52 : fontPt;
    if (w + cw > usable) { lines++; w = cw; } else { w += cw; }
  }
  return lines;
}
function estTextH(text, widthIn, fontPt, lineFactor) {
  return estLines(text, widthIn, fontPt) * fontPt * (lineFactor || 1.45) / 72;
}
var FONT_LADDER = [15, 14, 13.5, 13, 12.5, 12, 11.5, 11, 10.5, 10, 9.5, 9, 8.5];
/* 有限缩字号（v8.2，与 build_pptx.js 同策略）：先优化内容/组合/拆页，最后才缩字号。
   maxShrinkSteps 限制下探步数；floorPt 按模式绝对下限。 */
function modeFloorPtA(mode) {
  var floors = (typeof CONT !== 'undefined' && CONT && CONT.fontShrink && CONT.fontShrink.floorPt) ||
    { presentation: 10, research: 9, architecture: 10 };
  var m = String(mode || 'presentation');
  return (floors[m] != null) ? floors[m] : 10;
}
function snapFont(pt, ladder, floor) {
  var lad = (ladder || FONT_LADDER).filter(function (v) { return v >= (floor == null ? 0 : floor); });
  if (!lad.length) return floor == null ? pt : Math.max(floor, pt);
  var best = lad[0], bd = Math.abs(lad[0] - pt);
  for (var i = 1; i < lad.length; i++) {
    var d = Math.abs(lad[i] - pt);
    if (d < bd) { bd = d; best = lad[i]; }
  }
  return best;
}
function fitFont(items, widthIn, availIn, opts) {
  opts = opts || {};
  var max = (opts.max == null) ? 99 : opts.max, lf = opts.lineFactor || 1.45;
  var gapF = (opts.gapFactor == null) ? 0.5 : opts.gapFactor;
  var mode = (typeof CONTENT !== 'undefined' && CONTENT && CONTENT.mode) ||
    (typeof TOPPPT_MODE !== 'undefined' ? TOPPPT_MODE : 'presentation');
  var floor = (opts.floor != null) ? opts.floor : modeFloorPtA(mode);
  var maxSteps = (opts.maxShrinkSteps != null) ? opts.maxShrinkSteps
    : ((typeof CONT !== 'undefined' && CONT && CONT.fontShrink && CONT.fontShrink.maxShrinkSteps != null)
      ? CONT.fontShrink.maxShrinkSteps : 4);
  var baseLadder = (typeof CONT !== 'undefined' && CONT && CONT.fontShrink && CONT.fontShrink.ladder) || FONT_LADDER;
  var raw = baseLadder.filter(function (v) { return v <= max && v >= floor; });
  var needH = function (f) {
    var h = 0;
    for (var i = 0; i < items.length; i++) h += estTextH(items[i], widthIn, f, lf) + f * gapF / 72;
    return h + (opts.pad || 0);
  };
  for (var li = 0; li < raw.length; li++) {
    if (needH(raw[li]) <= availIn) return raw[li];
  }
  var preferred = raw.length ? raw[0] : floor;
  var prefIdx = baseLadder.indexOf(preferred);
  var limited = baseLadder.slice(prefIdx, prefIdx + 1 + maxSteps)
    .filter(function (v) { return v >= floor && v <= max; });
  for (var lj = 0; lj < limited.length; lj++) {
    if (needH(limited[lj]) <= availIn) return limited[lj];
  }
  if (limited.length) return limited[limited.length - 1];
  return floor;
}
function cols(total, n, gap) {
  var w = (total - (n - 1) * (gap || 0)) / Math.max(1, n);
  return { w: w, step: w + (gap || 0) };
}
/* 行高收敛：与 build_pptx.js 同算法（宁可行高更小也不越界） */
function fitRowH(avail, n, pref, floor) {
  var lo = (floor == null) ? 0.22 : floor;
  return Math.max(lo, Math.min(pref, avail / Math.max(1, n)));
}
function chartBottom(hasSoWhat, hasFootnote) {
  /* D8: tightest of soWhat/footnote/contentBottomWithNote — no short-circuit */
  var bot = CONTENT_BOTTOM;
  if (hasSoWhat) bot = Math.min(bot, PT.exhibit.soWhatY - 0.20);
  if (hasFootnote) bot = Math.min(bot, PT.exhibit.footnoteY - 0.12);
  if (hasSoWhat || hasFootnote) bot = Math.min(bot, CONTENT_BOTTOM_NOTE);
  return bot;
}

/* ── XML 工具 ── */
function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&apos;');
}
function E(v) { return Math.round(v * EMU); }
function solid(hex) { return '<a:solidFill><a:srgbClr val="' + hex + '"/></a:solidFill>'; }

var _id = 10;
function nid() { return ++_id; }

/* 文本框：paras = [[{t,b,sz,col,font,spc}…]…]（每个内层数组=一段，可混排多 run）
   opts.lineSpacing / opts.spaceBefore 为基准 pt（与 build_pptx.js 的 lineSpacing/paraSpaceBefore 同源），
   序列化时统一过 modeSize 映射，保证两通道行距一致。 */
function txSp(x, y, w, h, paras, opts) {
  opts = opts || {};
  var pPr = '';
  if (opts.lineSpacing) pPr += '<a:lnSpc><a:spcPts val="' + Math.round(modeSize(opts.lineSpacing) * 100) + '"/></a:lnSpc>';
  if (opts.spaceBefore) pPr += '<a:spcBef><a:spcPts val="' + Math.round(modeSize(opts.spaceBefore) * 100) + '"/></a:spcBef>';
  var pPrXml = (opts.align || pPr)
    ? '<a:pPr' + (opts.align ? ' algn="' + opts.align + '"' : '') + '>' + pPr + '</a:pPr>'
    : '';
  var body = paras.map(function (runs) {
    var rs = runs.map(function (r) {
      var pr = '<a:rPr lang="zh-CN" sz="' + Math.round(modeSize(r.sz) * 100) + '"' +
        (r.b ? ' b="1"' : '') + (r.spc ? ' spc="' + r.spc + '"' : '') + '>' +
        solid(r.col) +
        '<a:latin typeface="' + esc(r.font) + '"/><a:ea typeface="' + esc(r.font) + '"/></a:rPr>';
      return '<a:r>' + pr + '<a:t>' + esc(r.t) + '</a:t></a:r>';
    }).join('');
    return '<a:p>' + pPrXml + rs + '</a:p>';
  }).join('');
  var fill = opts.fill ? solid(opts.fill) : '<a:noFill/>';
  return '<p:sp><p:nvSpPr><p:cNvPr id="' + nid() + '" name="tx"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>' +
    '<p:spPr><a:xfrm><a:off x="' + E(x) + '" y="' + E(y) + '"/><a:ext cx="' + E(w) + '" cy="' + E(h) + '"/></a:xfrm>' +
    '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>' + fill + '<a:ln><a:noFill/></a:ln></p:spPr>' +
    '<p:txBody><a:bodyPr wrap="square" anchor="' + (opts.anchor || 't') + '"><a:normAutofit/></a:bodyPr><a:lstStyle/>' +
    body + '</p:txBody></p:sp>';
}

/* 形状：rect / roundRect / ellipse / pie（opts.av = avLst 原始内联 XML，供 donut 楔形角度） */
function shape(geom, x, y, w, h, fillHex, opts) {
  opts = opts || {};
  var av;
  if (opts.av) av = '<a:avLst>' + opts.av + '</a:avLst>';
  else if (geom === 'roundRect') av = '<a:avLst><a:gd name="adj" fmla="val ' + (opts.adj || 8000) + '"/></a:avLst>';
  else av = '<a:avLst/>';
  var ln = opts.line
    ? '<a:ln w="9525">' + (opts.dash ? '<a:prstDash val="dash"/>' : '') + solid(opts.line) + '</a:ln>'
    : '<a:ln><a:noFill/></a:ln>';
  return '<p:sp><p:nvSpPr><p:cNvPr id="' + nid() + '" name="' + (opts.name || 'sh') + '"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>' +
    '<p:spPr><a:xfrm><a:off x="' + E(x) + '" y="' + E(y) + '"/><a:ext cx="' + E(Math.max(w, 0.01)) + '" cy="' + E(Math.max(h, 0.01)) + '"/></a:xfrm>' +
    '<a:prstGeom prst="' + geom + '">' + av + '</a:prstGeom>' + solid(fillHex) + ln + '</p:spPr>' +
    '<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr lang="zh-CN"/></a:p></p:txBody></p:sp>';
}
/* pie 楔形 avLst：角度（度）× 60000；donut 页型两通道共用同一角度拆分规则 */
function pieAv(a1, a2) {
  return '<a:gd name="adj1" fmla="val ' + Math.round(a1 * 60000) + '"/>' +
         '<a:gd name="adj2" fmla="val ' + Math.round(a2 * 60000) + '"/>';
}
/* 环形图（donut 页型）：原生 pie 楔形 + 背景色圆（挖孔）+ 中心文字 + 右侧图例。
   角度约定：12 点钟（270°）起顺时针；跨 360° 的楔形拆成两段（≤359.9 封顶）。 */
function donutWedges(labels, values) {
  var total = 0;
  (values || []).forEach(function (v) { total += Math.max(0, v); });
  var segs = [], a = 270;
  (values || []).forEach(function (v, i) {
    var frac = total > 0 ? Math.max(0, v) / total : 0;
    var b = a + frac * 360;
    var s = a % 360, e = b % 360;
    if (frac <= 0) { a = b; return; }
    if (b - a >= 359.9) { segs.push([0, 359.9, i]); }
    else if (b <= 360) { segs.push([a, Math.min(b, 359.9), i]); }
    else { segs.push([a, 359.9, i]); if (e > 0.1) segs.push([0, e, i]); }
    a = b;
  });
  return segs;
}
function donutChart(sh, ec, S, dcols, bottomY) {
  var d = PT.donut, labels = ec.labels || [], values = ec.values || [];
  var segs = donutWedges(labels, values);
  var r = d.r;
  if (bottomY != null && d.centerY + r > bottomY) {
    r = Math.max(0.9, bottomY - d.centerY - 0.04);
  }
  var holeR = d.holeR * (r / d.r);
  var bx = d.centerX - r, by = d.centerY - r, bw = r * 2;
  segs.forEach(function (sg) {
    sh.push(shape('pie', bx, by, bw, bw, dcols[sg[2] % dcols.length], { av: pieAv(sg[0], sg[1]) }));
  });
  var hb = holeR * 2;
  sh.push(shape('ellipse', d.centerX - holeR, d.centerY - holeR, hb, hb, S.bg));
  var total = 0; values.forEach(function (v) { total += Math.max(0, v); });
  var totalStr = (Math.round(total * 10) / 10) + (ec.unit || '');
  sh.push(txSp(d.centerX - holeR, d.centerY - 0.42, hb, 0.5,
    [[{ t: totalStr, sz: 20, b: 1, col: S.ink, font: S.fontDisplay }]], { align: 'ctr', anchor: 'ctr' }));
  sh.push(txSp(d.centerX - holeR, d.centerY + 0.08, hb, 0.35,
    [[{ t: ec.centerLabel || '合计', sz: 9.5, col: S.faint, font: S.font }]], { align: 'ctr', anchor: 'ctr' }));
  var n = Math.max(1, labels.length);
  var maxLegH = (bottomY != null) ? Math.max(1.2, bottomY - (d.centerY - 1.7)) : 3.4;
  var rowH = Math.min(d.legendRowH, maxLegH / n, 3.4 / n);
  var ly0 = d.centerY - (n * rowH) / 2 + 0.1;
  if (bottomY != null) ly0 = Math.min(ly0, bottomY - n * rowH - 0.04);
  var sum2 = total || 1;
  labels.forEach(function (lb, i) {
    var v = values[i] || 0;
    var y = ly0 + i * rowH;
    sh.push(shape('ellipse', d.legendX, y + 0.08, 0.16, 0.16, dcols[i % dcols.length]));
    sh.push(txSp(d.legendX + 0.3, y, d.legendLabelW, rowH,
      [[{ t: lb, sz: 12, b: 1, col: S.ink, font: S.font }]], { anchor: 'ctr' }));
    sh.push(txSp(d.legendX + 3.8, y, d.legendValW, rowH,
      [[{ t: String(v) + (ec.unit || ''), sz: 12, b: 1, col: S.body, font: S.font }]], { align: 'r', anchor: 'ctr' }));
    sh.push(txSp(d.legendPctX, y, d.legendPctW, rowH,
      [[{ t: (Math.round(v / sum2 * 1000) / 10) + '%', sz: 10.5, col: S.faint, font: S.font }]], { align: 'r', anchor: 'ctr' }));
  });
}
function donutColors(style, S, theme) {
  var d = dataColors(style, theme);
  return d || [S.accent, S.faint, S.body, S.line];
}

/* 表格（graphicFrame + a:tbl）；rows[0]=表头；行高按可用高度自适应（与 B 通道同规则） */
function table(x, y, w, colW, rows, S, opts) {
  opts = opts || {};
  var n = rows.length;
  var maxRowH = (opts.maxRowH == null) ? PT.table.rowH : opts.maxRowH;
  var minRowH = (opts.minRowH == null) ? PT.table.rowHMin : opts.minRowH;
  var availH = (opts.availH == null) ? (CONTENT_BOTTOM - y) : opts.availH;
  var rowH = Math.max(minRowH, Math.min(maxRowH, availH / Math.max(1, n)));
  var dense = rowH < 0.42;
  var total = colW.reduce(function (a, b) { return a + b; }, 0);
  var grid = colW.map(function (cw) { return '<a:gridCol w="' + E(cw) + '"/>'; }).join('');
  var trs = rows.map(function (row, ri) {
    var tcs = row.map(function (cell) {
      var isHead = ri === 0;
      var fz = isHead ? (dense ? 11 : 13) : (dense ? 10 : 12.5);
      return '<a:tc><a:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r>' +
        '<a:rPr lang="zh-CN" sz="' + Math.round(modeSize(fz) * 100) + '"' + (isHead ? ' b="1"' : '') + '>' +
        solid(isHead ? S.onAccent : S.body) +
        '<a:latin typeface="' + S.font + '"/><a:ea typeface="' + S.font + '"/></a:rPr>' +
        '<a:t>' + esc(cell) + '</a:t></a:r></a:p></a:txBody>' +
        '<a:tcPr marL="91440" marR="91440" marT="45720" marB="45720" anchor="ctr">' +
        solid(isHead ? S.accent : S.bg) + '</a:tcPr></a:tc>';
    }).join('');
    return '<a:tr h="' + E(rowH) + '">' + tcs + '</a:tr>';
  }).join('');
  /* OOXML 规范：p:graphicFrame 的 graphic 子元素属 DrawingML 命名空间（a:graphic，与 pptxgenjs 一致） */
  return '<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="' + nid() + '" name="tbl"/>' +
    '<p:cNvGraphicFramePr><a:graphicFrameLocks noGrp="1"/></p:cNvGraphicFramePr><p:nvPr/></p:nvGraphicFramePr>' +
    '<p:xfrm><a:off x="' + E(x) + '" y="' + E(y) + '"/><a:ext cx="' + E(w) + '" cy="' + E(rowH * rows.length) + '"/></p:xfrm>' +
    '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">' +
    '<a:tbl><a:tblPr firstRow="1" bandRow="0"/><a:tblGrid>' + grid + '</a:tblGrid>' + trs + '</a:tbl>' +
    '</a:graphicData></a:graphic></p:graphicFrame>';
}

/* so-what 结论条 / 页脚来源行（research 页通用可选件，与 HTML 同源版式；区域走布局 IR） */
function soWhatBar(sh, text, S) {
  var R = (typeof regionOf === 'function') ? regionOf('exhibit', 'annotation')
    : { x: MX, y: PT.exhibit.soWhatY, w: CW, h: 0.62 };
  /* MD3 结论条：tonal soft 满铺 + 舒适字阶；禁止左 accent 装饰轨（anti-AI-flavor） */
  var padX = 0.28, padY = 0.10;
  var bodyW = Math.max(2.5, R.w - padX * 2);
  var fzB = fitFont([String(text || '')], bodyW, R.h - padY * 2, { max: 15, gapFactor: 0.2, maxShrinkSteps: 3 });
  sh.push(shape('rect', R.x, R.y, R.w, R.h, S.soft));
  sh.push(txSp(R.x + padX, R.y + padY, R.w - padX * 2, R.h - padY * 2,
    [[{ t: String(text || ''), sz: fzB, b: 1, col: S.ink, font: S.font }]], { anchor: 'ctr' }));
}
function footnoteLine(sh, text, S) {
  var R = (typeof regionOf === 'function') ? regionOf('exhibit', 'footnote')
    : { x: MX, y: PT.exhibit.footnoteY, w: CW - 1.2, h: 0.32 };
  sh.push(txSp(R.x, R.y, R.w, R.h,
    [[{ t: text, sz: 9.5, col: S.faint, font: S.font }]]));
}
/* R2：sec.note 与 sec.footnote 共用注释带末行（footnoteY=6.72）。
   note.y=6.55 会压进 so-what 带（6.05–6.67）——同页二者必须合并为一行。 */
function noteOrFootnote(sh, sec, S) {
  var parts = [];
  if (sec && sec.note) parts.push(String(sec.note));
  if (sec && sec.footnote) parts.push(String(sec.footnote));
  if (!parts.length) return;
  footnoteLine(sh, parts.join('　·　'), S);
}
/* 待核实清单条（accent 强调色标注 · 与 build_pptx.js / HTML .flagbar 同源） */
function flagBar(sh, items, S, yTop) {
  var F = PT.flagbar || { hdH: 0.26, rowH: 0.24, maxRows: 3, gap: 0.12 };
  var list = (items || []).slice(0, F.maxRows).map(String);
  if (!list.length) return 0;
  var h = F.hdH + list.length * F.rowH + 0.06;
  var y = (yTop != null) ? yTop : (CONTENT_BOTTOM - h);
  sh.push(shape('rect', MX, y, CW, h, S.soft));
  sh.push(shape('rect', MX, y, 0.055, h, S.accent));
  sh.push(txSp(MX + 0.22, y + 0.02, CW - 0.44, F.hdH,
    [[{ t: '待核实 · 需二次确认', sz: 9.5, b: 1, col: S.accent, font: S.font, spc: 100 }]]));
  list.forEach(function (t, i) {
    sh.push(txSp(MX + 0.24, y + F.hdH + i * F.rowH, CW - 0.5, F.rowH,
      [[{ t: '· ' + t, sz: 9.5, col: S.body, font: S.font }]], { anchor: 'ctr' }));
  });
  return h;
}
/* 素材图片：预览引擎只产出 slide XML（无 media part）→ 以中性图位块表示；
   配图占位（placeholder）额外发射标签文本——标签串由 imageSpec 常量拼接，与 B 通道**同串**
   （cross_verify 逐页比对）。真实图片不发射任何文本，保证 A/B 文本集合一致。 */
function imgPlaceholderLabel(layout, multi) {
  var IS = (typeof IMG !== 'undefined' && IMG) || {};
  var label = IS.placeholderLabel || '配图占位';
  if (multi) return label;
  var size = (IS.recommendedSizePx || {})[layout];
  if (!size) return label;
  return label + ' · ' + (IS.placeholderHintPrefix || '建议 ') + size + (IS.placeholderHintSuffix || 'px');
}
function addImageEl(sh, src, S, x, y, w, h, opts) {
  opts = opts || {};
  var ph = !!opts.placeholder || !src;
  /* name="img"/"imgph"：预览模态据此把图位替换为真实图片（ui.js renderSlide），
     不影响文本集合（cross_verify 只比文本）。 */
  sh.push(shape('roundRect', x, y, w, h, S.surface,
    { line: S.line, dash: ph, adj: 4000, name: ph ? 'imgph' : 'img' }));
  if (ph) {
    sh.push(txSp(x + 0.08, y + h / 2 - 0.22, Math.max(0.4, w - 0.16), 0.44,
      [[{ t: imgPlaceholderLabel(opts.layout || 'full', !!opts.multi), sz: 11, b: 1, col: S.faint, font: S.font }]],
      { align: 'ctr', anchor: 'ctr' }));
  }
}
/* 版式比例（imageSpec.ratioDefault 或 image.ratio，形如 "3:1"）→ 数值宽高比。
   双引擎同源：HTML 用同比例的 .media--r* 锁定类，PPTX 用本函数算高度，版式才一致。 */
function imgRatio(layout, img) {
  var IS = (typeof IMG !== 'undefined' && IMG) || {};
  var raw = String((img && img.ratio) || (IS.ratioDefault || {})[layout] || '3:1');
  var m = raw.match(/^\s*(\d+(?:\.\d+)?)\s*[:/×x]\s*(\d+(?:\.\d+)?)/);
  if (!m) return 3;
  var a = parseFloat(m[1]), b = parseFloat(m[2]);
  return (a > 0 && b > 0) ? a / b : 3;
}
/* 图片版式族（与 HTML .media / .media-grid / .media-compare / .media-wall 同源）：
   full 版心全宽｜half 左图右注｜bleed 通栏出血｜grid 多图网格｜compare 双图对比｜wall Logo 墙。
   每版式按 imageSpec.ratioDefault 锁定比例；空间不足时按可用高度收敛并**垂直居中**
   （避免"图贴顶、下方大片留白"）。返回图注基准 Y。占位符走原生形状，pictures 不增。 */
function imageLayoutShapes(sh, S, layout, img, items, points, isPh, fit, y0, y1) {
  var IM = PT.image || {};
  var gap = IM.gridGap || 0.16;
  var iy = y0;
  var ih = Math.max(1.0, y1 - iy);
  var capY = iy + ih;
  var ratio = imgRatio(layout, img);
  function one(x, y, w, h, it, multi) {
    var ph = isPh || !(it && it.src);
    addImageEl(sh, (it && it.src) || '', S, x, y, w, h,
      { placeholder: ph, layout: layout, multi: multi, fit: fit });
  }
  if (layout === 'grid' && items.length) {
    var n = Math.min(items.length, (IMG && IMG.maxPerPage) || 6);
    var colsN = (IM.gridCols || {})[String(n)] || Math.min(3, n);
    var rowsN = Math.max(1, Math.ceil(n / colsN));
    var capH = IM.gridCapH || 0.28;
    var cellW = (CW - (colsN - 1) * gap) / colsN;
    var capRows = rowsN * (capH + 0.04);
    var cellH = Math.min(cellW / ratio, Math.max(0.5, (ih - (rowsN - 1) * gap - capRows) / rowsN));
    var blockH = rowsN * cellH + (rowsN - 1) * gap + capRows;
    var gy = iy + Math.max(0, (ih - blockH) / 2);
    items.slice(0, n).forEach(function (it, i) {
      var cx = MX + (i % colsN) * (cellW + gap);
      var cy = gy + Math.floor(i / colsN) * (cellH + gap + capH + 0.04);
      var cap = (it && it.caption) || '';
      one(cx, cy, cellW, cellH, it, true);
      if (cap) sh.push(txSp(cx, cy + cellH + 0.02, cellW, capH,
        [[{ t: cap, sz: 10, col: S.faint, font: S.font }]], { align: 'ctr' }));
    });
    capY = gy + blockH;
  } else if (layout === 'compare' && items.length >= 2) {
    var cgap = IM.compareGap || 0.3;
    var cw2 = (CW - cgap) / 2;
    var capH2 = 0.34;
    var ih2 = Math.min(cw2 / ratio, Math.max(0.5, ih - capH2));
    var cy2 = iy + Math.max(0, (ih - ih2 - capH2) / 2);
    [0, 1].forEach(function (i) {
      var it = items[i] || {};
      var cx2 = MX + i * (cw2 + cgap);
      one(cx2, cy2, cw2, ih2, it, true);
      var cap2 = it.caption || '';
      if (cap2) sh.push(txSp(cx2, cy2 + ih2 + 0.02, cw2, 0.3,
        [[{ t: cap2, sz: 10, col: S.faint, font: S.font }]], { align: 'ctr' }));
    });
    capY = cy2 + ih2 + capH2;
  } else if (layout === 'wall' && items.length) {
    var wgap = IM.wallGap || 0.18;
    var wn = Math.min(items.length, 12);
    var rowsW = Math.max(1, Math.min(IM.wallMaxRows || 2, Math.ceil(wn / 6)));
    var perRow = Math.max(1, Math.ceil(wn / rowsW));
    var cellW2 = (CW - (perRow - 1) * wgap) / perRow;
    var cellH2 = Math.min(IM.wallCellH || 0.92, cellW2 / ratio,
      Math.max(0.4, (ih - (rowsW - 1) * wgap) / rowsW));
    var blockH2 = rowsW * cellH2 + (rowsW - 1) * wgap;
    var wy = iy + Math.max(0, (ih - blockH2) / 2);
    items.slice(0, wn).forEach(function (it, i) {
      var cx3 = MX + (i % perRow) * (cellW2 + wgap);
      var cy3 = wy + Math.floor(i / perRow) * (cellH2 + wgap);
      one(cx3, cy3, cellW2, cellH2, it, true);
    });
    capY = wy + blockH2;
  } else if (layout === 'half') {
    var iw = CW * (IM.halfW || 0.56);
    var ihh = Math.min(iw / ratio, ih);
    one(MX, iy, iw, ihh, img, false);
    var rxI = MX + iw + CW * (IM.halfGap || 0.06);
    var rwI = CW - iw - CW * (IM.halfGap || 0.06);
    var ptsI = points || [];
    var rowHI = fitRowH(ih - 0.1, ptsI.length, IM.noteRowH || 0.62, 0.3);
    var fzI = fitFont(ptsI.map(function (p) { return (p[0] || '') + (p[1] || ''); }), rwI - 0.3, ih,
      { max: 14, gapFactor: 0.6 });
    ptsI.forEach(function (pt, i) {
      var lyI = iy + i * rowHI;
      sh.push(shape('rect', rxI, lyI + rowHI / 2 - 0.06, 0.12, 0.12, S.accent));
      sh.push(txSp(rxI + 0.26, lyI, rwI - 0.3, rowHI - 0.04,
        [[{ t: (pt[0] || '') + '　', sz: fzI, b: 1, col: S.ink, font: S.font },
          { t: pt[1] || '', sz: snapFont(fzI - 1), col: S.body, font: S.font }]], { anchor: 't' }));
    });
    capY = iy + Math.max(ihh, ih * 0.5);
  } else if (layout === 'bleed') {
    var bh = Math.min(ih, PW / ratio);
    var by = iy + Math.max(0, (ih - bh) / 2);
    one(0, by, PW, bh, img, false);
    capY = by + bh;
  } else {
    var fh = Math.min(ih, CW / ratio);
    var fy = iy + Math.max(0, (ih - fh) / 2);
    one(MX, fy, CW, fh, img, false);
    capY = fy + fh;
  }
  return capY;
}

/* ══ 图表形状渲染（预览/回归用近似版；交付通道 B 用原生可编辑数据图表） ══
   A/B 两通道的「文本集合」必须一致（cross_verify 逐页比对）：
   类别标签 + 数值标签都渲染为文本，数值标签由 cross_verify 的数值 token 规则过滤。 */
function valText(v, unit) { return String(v) + (unit || ''); }
/* 横向条形（hbar / halftable / exhibit hbar） */
function hbarRows(sh, ec, S, y0, y1, dcols, x0, w) {
  x0 = (x0 == null) ? MX : x0;
  w = (w == null) ? CW : w;
  var labels = ec.labels || [], values = ec.values || [];
  var n = Math.max(1, labels.length);
  var rowH = Math.min(PT.hbar.rowH, (y1 - y0) / n);
  var barH = Math.max(0.16, rowH * (PT.hbar.barRatio || 0.5));
  var labelW = PT.hbar.labelW, valW = PT.hbar.valW;
  var trackX = x0 + labelW + 0.1, trackW = w - labelW - valW - 0.2;
  var vmax = ec.max || Math.max.apply(null, values.concat([1]));
  var top = values.length ? Math.max.apply(null, values) : 0;
  labels.forEach(function (lb, i) {
    var v = values[i] || 0;
    var y = y0 + i * rowH + (rowH - barH) / 2;
    var hot = v === top;
    var dc = dcols ? dcols[i % 5] : null;
    sh.push(txSp(x0, y - 0.06, labelW - 0.05, barH + 0.12,
      [[{ t: lb, sz: 11, col: S.body, font: S.font }]], { anchor: 'ctr' }));
    sh.push(shape('rect', trackX, y, trackW, barH, S.surface, { line: S.line }));
    var bw2 = Math.max(0.02, v / vmax * trackW);
    sh.push(shape('rect', trackX, y, bw2, barH, dc || (hot ? S.accent : S.faint)));
    sh.push(txSp(trackX + trackW + 0.08, y - 0.06, valW, barH + 0.12,
      [[{ t: valText(v, ec.unit), sz: 11.5, b: 1, col: hot ? S.accent : S.body, font: S.font }]], { anchor: 'ctr' }));
  });
}
/* 竖柱 / 堆叠柱 */
function vbarShapes(sh, ec, S, x, y, w, h, dcols) {
  /* Multi-series aware (mirrors lineShapes): ec.series[{name,values}] or single ec.values. */
  var labels = ec.labels || [];
  var series = (ec.series && ec.series.length)
    ? ec.series
    : [{ name: '数值', values: ec.values || [] }];
  var nb = Math.max(1, labels.length);
  var ns = Math.max(1, series.length);
  /* R2：类目标签带必须含在 h 内（原 baseY+0.08 画在图区外，会压进 so-what/来源行） */
  var labelH = 0.36;
  var baseY = y + Math.max(0.6, h - labelH), plotW = w, step = plotW / nb;
  var cluster = Math.min(1.1, step * (ns > 1 ? 0.78 : 0.55));
  var bw = cluster / ns;
  var all = [];
  series.forEach(function (se) {
    (se.values || []).forEach(function (v) { all.push(Number(v) || 0); });
  });
  var vmax = ec.max || Math.max.apply(null, all.concat([1]));
  var top = all.length ? Math.max.apply(null, all) : 0;
  var plotH = Math.max(0.35, baseY - y);
  sh.push(shape('rect', x, baseY, plotW, 0.02, S.line));
  series.forEach(function (se, si) {
    var vals = se.values || [];
    var col = dcols ? dcols[si % 5] : (si === 0 ? S.accent : S.faint);
    vals.forEach(function (v, i) {
      var num = Number(v) || 0;
      var hh = Math.max(0.05, num / vmax * (plotH - 0.35));
      var bx = x + i * step + (step - cluster) / 2 + si * bw;
      var hot = ns === 1 && num === top;
      sh.push(shape('roundRect', bx, baseY - hh, Math.max(0.04, bw * 0.92), hh,
        hot ? (dcols ? dcols[i % 5] : S.accent) : col, { adj: 6000 }));
      if (ns === 1) {
        sh.push(txSp(bx - 0.3, baseY - hh - 0.36, bw + 0.6, 0.30,
          [[{ t: valText(num, ec.unit), sz: 12.5, b: 1, col: hot ? S.accent : S.body, font: S.font }]], { align: 'ctr' }));
      }
    });
  });
  labels.forEach(function (lb, i) {
    var lx = x + i * step;
    sh.push(txSp(lx, baseY + 0.06, step, labelH - 0.08,
      [[{ t: lb, sz: 10.5, col: S.faint, font: S.font }]], { align: 'ctr' }));
  });
  /* Multi-series legend along top of plot (keeps category labels; avoids blank chart). */
  if (ns > 1) {
    var lx2 = x;
    series.forEach(function (se, si) {
      var col2 = dcols ? dcols[si % 5] : (si === 0 ? S.accent : S.faint);
      sh.push(shape('rect', lx2, y, 0.12, 0.12, col2));
      sh.push(txSp(lx2 + 0.16, y - 0.02, 1.4, 0.24,
        [[{ t: String(se.name || ('系列' + (si + 1))), sz: 10, col: S.body, font: S.font }]]));
      lx2 += 1.6;
    });
  }
}
/* 折线 / 双折线 / 面积 */
function lineShapes(sh, ec, S, x, y, w, h, dcols) {
  var labels = ec.labels || [];
  var series = (ec.series && ec.series.length) ? ec.series : [{ name: '数值', values: ec.values || [] }];
  var n = Math.max(1, labels.length);
  var all = [];
  series.forEach(function (se) { (se.values || []).forEach(function (v) { all.push(Number(v) || 0); }); });
  var vmax = ec.max || Math.max.apply(null, all.concat([1]));
  /* R2：类目标签带含在 h 内，禁画到图区外压 so-what */
  var labelH = 0.36;
  var baseY = y + Math.max(0.6, h - labelH);
  var plotH = Math.max(0.35, baseY - y - 0.2);
  sh.push(shape('rect', x, baseY, w, 0.02, S.line));
  var stepX = n > 1 ? w / (n - 1) : 0;
  series.forEach(function (se, si) {
    var col = dcols ? dcols[si % 5] : (si === 0 ? S.accent : S.faint);
    var pts = (se.values || []).map(function (v, i) {
      var px = x + (n > 1 ? i * stepX : w / 2);
      var py = baseY - Math.max(0.02, (Number(v) || 0) / vmax * plotH);
      return [px, py];
    });
    if (!pts.length) return;
    for (var i = 0; i < pts.length - 1; i++) {
      sh.push(lineSeg(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], col, 2.5));
    }
    pts.forEach(function (p) {
      sh.push(shape('ellipse', p[0] - 0.055, p[1] - 0.055, 0.11, 0.11, col));
    });
  });
  labels.forEach(function (lb, i) {
    var px = x + (n > 1 ? i * stepX : w / 2);
    sh.push(txSp(px - 0.5, baseY + 0.06, 1.0, labelH - 0.08,
      [[{ t: lb, sz: 10.5, col: S.faint, font: S.font }]], { align: 'ctr' }));
  });
}
/* 直线段（用细长矩形近似，避免自定义几何——两通道渲染一致） */
function lineSeg(x1, y1, x2, y2, hex, thick) {
  var dx = x2 - x1, dy = y2 - y1;
  var len = Math.sqrt(dx * dx + dy * dy);
  var ang = Math.atan2(dy, dx) * 180 / Math.PI;
  var cx = (x1 + x2) / 2, cy = (y1 + y2) / 2;
  var t = thick / 72;
  var rot = '<a:xfrm rot="' + Math.round(ang * 60000) + '">';
  return '<p:sp><p:nvSpPr><p:cNvPr id="' + nid() + '" name="ln"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>' +
    '<p:spPr>' + rot + '<a:off x="' + E(cx - len / 2) + '" y="' + E(cy - t / 2) + '"/>' +
    '<a:ext cx="' + E(len) + '" cy="' + E(t) + '"/></a:xfrm>' +
    '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>' + solid(hex) + '<a:ln><a:noFill/></a:ln></p:spPr>' +
    '<p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp>';
}
/* 散点 / 气泡（A 通道近似）：只画点、不产文本——与 B 通道 XY 图表（类别为数值，过滤后为空）一致 */
function xyDots(sh, ec, S, x, y, w, h) {
  var values = (ec.values || []).map(Number);
  var pts = (ec.points && ec.points.length) ? ec.points : null;
  var n = pts ? pts.length : Math.max(1, values.length);
  var vmax = ec.max || Math.max.apply(null, values.concat([1]));
  var baseY = y + h, plotH = Math.max(0.3, h - 0.3);
  var stepX = n > 1 ? w / (n - 1) : 0;
  sh.push(shape('rect', x, baseY, w, 0.02, S.line));
  for (var i = 0; i < n; i++) {
    var px = pts ? x + (Number(pts[i][0]) || 0) / vmax * w : x + i * stepX;
    var py = pts ? baseY - (Number(pts[i][1]) || 0) / vmax * plotH : baseY - (values[i] || 0) / vmax * plotH;
    sh.push(shape('ellipse', px - 0.07, py - 0.07, 0.14, 0.14, S.accent));
  }
}
/* 仪表盘（A 通道近似）：270° 弧段 + 数值（B 通道 gauge 的类别为数值，过滤后两端一致，故此处不产标签文本） */
function gaugeApprox(sh, ec, S, x, y, w, h) {
  var v = Number((ec.values || [0])[0]) || 0;
  var max = Number(ec.max) || 100;
  var frac = Math.max(0, Math.min(1, v / max));
  var r = Math.min(w, h) / 2 - 0.12;
  var cx = x + w / 2, cy = y + h / 2;
  var steps = 40, startA = Math.PI * 0.75, sweep = Math.PI * 1.5;
  var px = null, py = null;
  for (var i = 0; i <= steps; i++) {
    var a = startA + sweep * (i / steps);
    var qx = cx + r * Math.cos(a), qy = cy + r * Math.sin(a);
    if (px !== null) sh.push(lineSeg(px, py, qx, qy, (i / steps) <= frac ? S.accent : S.line, 5));
    px = qx; py = qy;
  }
  sh.push(txSp(x, cy - 0.2, w, 0.42,
    [[{ t: String(v) + (ec.unit || ''), sz: 18, b: 1, col: S.accent, font: S.fontDisplay }]], { align: 'ctr', anchor: 'ctr' }));
}
/* 饼 / 环（A 通道近似）：横向占比条 + 图例（类别标签为文本，数值由 cross_verify 过滤） */
function pieApprox(sh, ec, S, x, y, w, h, dcols) {
  var labels = ec.labels || [], values = (ec.values || []).map(Number);
  var total = values.reduce(function (a, b) { return a + b; }, 0) || 1;
  var barH = Math.max(0.32, Math.min(0.62, h * 0.22));
  var barY = y + h / 2 - barH / 2 - 0.2;
  var cx0 = x;
  labels.forEach(function (lb, i) {
    var bw = (values[i] || 0) / total * w;
    sh.push(shape('rect', cx0, barY, bw, barH,
      dcols ? dcols[i % dcols.length] : (i === 0 ? S.accent : S.faint)));
    cx0 += bw;
  });
  var lx = x;
  labels.forEach(function (lb, i) {
    sh.push(shape('ellipse', lx, barY + barH + 0.16, 0.1, 0.1,
      dcols ? dcols[i % dcols.length] : (i === 0 ? S.accent : S.faint)));
    sh.push(txSp(lx + 0.14, barY + barH + 0.12, 1.2, 0.24, [[{ t: lb, sz: 10.5, col: S.body, font: S.font }]]));
    sh.push(txSp(lx + 1.36, barY + barH + 0.12, 0.8, 0.24,
      [[{ t: String(values[i] != null ? values[i] : '') + (ec.unit || ''), sz: 10.5, b: 1, col: S.body, font: S.font }]]));
    lx += 2.3;
  });
}
/* 迷你折线（A 近似）：无轴无标签，仅趋势线 + 末值（与 B 的 shapeSpark 同文本集） */
function sparkApprox(sh, ec, S, x, y, w, h) {
  var vals = (ec.values || []).map(Number);
  var vmax = ec.max || Math.max.apply(null, vals.concat([1]));
  var n = vals.length;
  var stepX = n > 1 ? w / (n - 1) : 0;
  var baseY = y + h - 0.06, plotH = Math.max(0.2, h - 0.18);
  var px = 0, py = 0;
  vals.forEach(function (v, i) {
    var cx = x + i * stepX, cy = baseY - Math.max(0.02, (v / vmax) * plotH);
    if (i > 0) sh.push(lineSeg(px, py, cx, cy, S.accent, 2));
    px = cx; py = cy;
  });
  sh.push(txSp(x, y, w, 0.3, [[{ t: String(vals[n - 1] != null ? vals[n - 1] : '') + (ec.unit || ''),
    sz: 11.5, b: 1, col: S.accent, font: S.font }]], { align: 'r' }));
}
/* K 线（A 近似）：实体 + 须，标签 + 收盘值（与 B 的 shapeCandlestick 同文本集） */
function candleApprox(sh, ec, S, x, y, w, h) {
  var labels = ec.labels || [];
  var rows = (ec.values || []).filter(function (r) { return r && r.length >= 4; })
    .map(function (r) { return r.slice(0, 4).map(Number); });
  var n = Math.max(1, rows.length);
  var flat = [];
  rows.forEach(function (r) { r.forEach(function (v) { if (!isNaN(v)) flat.push(v); }); });
  var lo = flat.length ? Math.min.apply(null, flat) : 0;
  var hi = flat.length ? Math.max.apply(null, flat) : 1;
  var span = (hi - lo) || 1;
  var axisH = 0.26, plotH = Math.max(0.5, h - axisH - 0.1);
  var yFor = function (v) { return y + 0.06 + (1 - (v - lo) / span) * plotH; };
  var step = w / n, bw = Math.min(0.42, step * 0.5);
  sh.push(shape('rect', x, y + 0.06 + plotH, w, 0.015, S.line));
  rows.forEach(function (r, i) {
    var o = r[0], hiP = r[1], loP = r[2], cl = r[3];
    var cxp = x + step * i + step / 2;
    var up = cl >= o;
    sh.push(shape('rect', cxp - 0.011, yFor(hiP), 0.022, Math.max(0.02, yFor(loP) - yFor(hiP)), S.faint));
    sh.push(shape('rect', cxp - bw / 2, yFor(Math.max(o, cl)), bw,
      Math.max(0.04, Math.abs(yFor(cl) - yFor(o))), up ? S.accent : S.line));
    if (labels[i]) {
      sh.push(txSp(cxp - step / 2, y + plotH + axisH - 0.06, step, 0.24,
        [[{ t: String(labels[i]), sz: 10, col: S.faint, font: S.font }]], { align: 'ctr' }));
    }
    sh.push(txSp(cxp - step / 2, yFor(hiP) - 0.26, step, 0.24,
      [[{ t: String(cl) + (ec.unit || ''), sz: 11.5, b: 1, col: up ? S.accent : S.body, font: S.font }]],
      { align: 'r' }));
  });
}
/* 通用形状近似（与 build_pptx.js 的 shapeProportion 同文本：标签 + 数值） */
function shapeProportion(sh, ec, S, x, y, w, h, dcols) {
  var labels = ec.labels || [], values = (ec.values || []).map(Number);
  var n = Math.max(1, labels.length);
  var labelW = Math.min(2.4, w * 0.24), valW = 0.9;
  var vmax = ec.max || Math.max.apply(null, values.concat([1]));
  var top = values.length ? Math.max.apply(null, values) : 0;
  var rowH = Math.max(0.22, Math.min(0.52, h / n));
  var trackX = x + labelW + 0.08, trackW = w - labelW - valW - 0.2;
  var barH = Math.max(0.12, rowH * 0.52);
  labels.forEach(function (lb, i) {
    var v = values[i] || 0, ry = y + i * rowH, hot = v === top;
    sh.push(txSp(x, ry, labelW - 0.06, rowH, [[{ t: lb, sz: 11, col: S.body, font: S.font }]], { anchor: 'ctr' }));
    sh.push(shape('rect', trackX, ry + (rowH - barH) / 2, trackW, barH, S.surface, { line: S.line }));
    sh.push(shape('rect', trackX, ry + (rowH - barH) / 2, Math.max(0.02, Math.abs(v) / vmax * trackW), barH,
      dcols ? dcols[i % dcols.length] : (hot ? S.accent : S.faint)));
    sh.push(txSp(trackX + trackW + 0.06, ry, valW, rowH,
      [[{ t: String(v) + (ec.unit || ''), sz: 11.5, b: 1, col: hot ? S.accent : S.body, font: S.font }]],
      { align: 'right', anchor: 'ctr' }));
  });
}
/* 数据表行（与 build_pptx.js 的 dataTableRows 同规则） */
function dataTableRows(ec) {
  var labels = (ec.labels || []).map(String);
  var unit = ec.unit ? '（' + ec.unit + '）' : '';
  if (ec.series && ec.series.length) {
    var out = [['项目'].concat(ec.series.map(function (se, i) { return se.name || ('系列' + (i + 1)); }))];
    labels.forEach(function (lb, i) {
      out.push([lb].concat(ec.series.map(function (se) {
        var v = (se.values || [])[i]; return v == null ? '' : String(v);
      })));
    });
    return out;
  }
  var out2 = [['项目', '数值' + unit]];
  labels.forEach(function (lb, i) {
    var v = (ec.values || [])[i];
    out2.push([lb, v == null ? '' : String(v)]);
  });
  return out2;
}
/* 数据表策略（与 build_pptx.js 的 dataTableMode 同规则） */
function dataTableModeOf(ec) {
  var t = (ec.type || 'bar').toLowerCase();
  var reg = (typeof REG !== 'undefined' && REG && REG[t]) ? REG[t] : null;
  var m = ec.dataTable || (reg && reg.dataTable) || 'notes';
  return m === 'appendix' ? 'inline' : m;
}
/* 图表 + 数据表组合（与 build_pptx.js 的 chartBlock 同策略：inline 在图表下方附原生表格） */
function chartBlockShapes(sh, ec, S, x, y, w, h, dcols) {
  var dm = dataTableModeOf(ec);
  var chH = h;
  if (dm === 'inline' && (ec.labels || []).length) {
    var rowsData = dataTableRows(ec);
    var n = rowsData.length;
    var tH = Math.min(h * 0.44, Math.max(0.44, n * 0.22 + 0.06));
    chH = Math.max(0.85, h - tH - 0.1);
    var colW = rowsData[0].map(function () { return w / rowsData[0].length; });
    sh.push(table(x, y + chH + 0.1, w, colW, rowsData, S, { availH: tH, maxRowH: 0.24, minRowH: 0.14 }));
  }
  chartShapes(sh, ec, S, x, y, w, chH, dcols);
}
/* ══ 复杂信息图页型（A 通道形状近似：文本集合与 B 通道严格一致，cross_verify 逐页比对）══ */
function infoTableRows(sec) {
  var t = sec.type || '';
  var u = sec.unit ? '（' + sec.unit + '）' : '';
  if (t === 'sankey') return [['源', '汇', '流量' + u]].concat((sec.flows || []).map(function (f) { return [String(f[0]), String(f[1]), String(f[2])]; }));
  if (t === 'treemap') return [['项目', '数值' + u]].concat((sec.items || []).map(function (it) { return [String(it[0]), String(it[1])]; }));
  if (t === 'boxplot') return [['分组', '最小', 'Q1', '中位', 'Q3', '最大']].concat((sec.groups || []).map(function (g) { return g.map(String); }));
  if (t === 'network') return [['节点', '名称']].concat((sec.nodes || []).map(function (n) { return [String(n[0]), String(n[1])]; }));
  if (t === 'marimekko') {
    var head = ['列', '总量' + u].concat((sec.legend || []).map(String));
    return [head].concat((sec.cols || []).map(function (c, i) {
      return [String(c[0]), String(c[1])].concat((((sec.cells || [])[i] || []).map(function (el) {
        return Array.isArray(el) ? String(el[0]) + ' ' + el[1] : String(el);
      })));
    }));
  }
  if (t === 'streamgraph') {
    return [['系列'].concat((sec.labels || []).map(String))]
      .concat((sec.series || []).map(function (se) {
        return [String(se.name || '')].concat((se.values || []).map(String));
      }));
  }
  return null;
}
function infoDataTableMode(sec) {
  var m = String(((sec.chart || {}).dataTable) || 'notes').toLowerCase();
  return m === 'appendix' ? 'inline' : m;
}
function infoPlotA(sec, y0, y1) {
  var rows = infoTableRows(sec);
  var inline = (infoDataTableMode(sec) === 'inline') && rows && rows.length;
  if (!inline) return { y0: y0, y1: y1, rows: rows };
  var tH = Math.min((y1 - y0) * 0.4, Math.max(0.44, rows.length * 0.22 + 0.06));
  return { y0: y0, y1: y1 - tH - 0.1, rows: rows, table: { y: y1 - tH, h: tH } };
}
function tmSplitA(items, x, y, w, h, out) {
  if (!items.length) return;
  if (items.length === 1) { out.push({ it: items[0], x: x, y: y, w: w, h: h }); return; }
  var total = items.reduce(function (a, i) { return a + i.v; }, 0) || 1;
  var acc = 0, k = 0;
  for (; k < items.length - 1; k++) { acc += items[k].v; if (acc >= total / 2) break; }
  var first = items.slice(0, k + 1), second = items.slice(k + 1);
  var r = first.reduce(function (a, i) { return a + i.v; }, 0) / total;
  if (w >= h) {
    tmSplitA(first, x, y, w * r, h, out);
    tmSplitA(second, x + w * r, y, w * (1 - r), h, out);
  } else {
    tmSplitA(first, x, y, w, h * r, out);
    tmSplitA(second, x, y + h * r, w, h * (1 - r), out);
  }
}
/* 信息图近似渲染：按页型画形状 + 落同样的标签文本 */
function infoApprox(sh, sec, S, y0, y1) {
  var t = sec.type || '';
  var P = infoPlotA(sec, y0, y1);
  if (P.table) {
    var colW = P.rows[0].map(function () { return CW / P.rows[0].length; });
    sh.push(table(MX, P.table.y, CW, colW, P.rows, S, { availH: P.table.h, maxRowH: 0.24, minRowH: 0.15 }));
  }
  var palette = [S.accent, S.faint, S.body, S.line];
  if (t === 'sankey') {
    var flows = (sec.flows || []).filter(function (f) { return f && f.length >= 3; });
    var nodes = [], idx = {};
    flows.forEach(function (f) {
      [f[0], f[1]].forEach(function (n) { if (idx[n] == null) { idx[n] = nodes.length; nodes.push(String(n)); } });
    });
    var level = nodes.map(function () { return 0; });
    for (var it2 = 0; it2 < nodes.length + 1; it2++) {
      var ch = false;
      flows.forEach(function (f) {
        var a = idx[f[0]], b = idx[f[1]];
        if (level[b] < level[a] + 1) { level[b] = level[a] + 1; ch = true; }
      });
      if (!ch) break;
    }
    var maxLv = Math.max.apply(null, level.concat([0]));
    var colW2 = CW / (maxLv + 1);
    var geo = {};
    for (var l = 0; l <= maxLv; l++) {
      var lv = nodes.filter(function (n, i) { return level[i] === l; });
      var rowH2 = Math.max(0.24, (P.y1 - P.y0) / Math.max(1, lv.length));
      lv.forEach(function (n, k2) { geo[n] = { x: MX + l * colW2 + colW2 * 0.5 - 0.16, y: P.y0 + k2 * rowH2, h: rowH2 * 0.7 }; });
    }
    flows.forEach(function (f) {
      var a = geo[f[0]], b = geo[f[1]];
      if (!a || !b) return;
      sh.push(lineSeg(a.x + 0.32, a.y + a.h / 2, b.x, b.y + b.h / 2, S.soft, 8));
      /* 流量标签：与 B 通道同文本（数值 + 单位，由 cross_verify 过滤） */
      sh.push(txSp((a.x + b.x) / 2 - 0.5, (a.y + b.y) / 2 - 0.14, 1.0, 0.28,
        [[{ t: String(f[2]) + (sec.unit || ''), sz: 9.5, col: S.faint, font: S.font }]], { align: 'ctr' }));
    });
    nodes.forEach(function (n) {
      var g = geo[n];
      sh.push(shape('rect', g.x, g.y, 0.32, g.h, S.accent));
      sh.push(txSp(g.x + 0.38, g.y, Math.min(1.4, colW2 * 0.5), g.h,
        [[{ t: n, sz: 10.5, b: 1, col: S.body, font: S.font }]], { anchor: 'ctr' }));
    });
    return;
  }
  if (t === 'treemap') {
    var items = (sec.items || []).map(function (it) { return { label: String(it[0]), v: Math.max(0, Number(it[1]) || 0) }; })
      .filter(function (i) { return i.v > 0; }).sort(function (a, b) { return b.v - a.v; });
    var out = [];
    tmSplitA(items, MX, P.y0, CW, P.y1 - P.y0, out);
    out.forEach(function (o) {
      sh.push(shape('rect', o.x + 0.03, o.y + 0.03, Math.max(0.05, o.w - 0.06), Math.max(0.05, o.h - 0.06), S.surface, { line: S.line }));
      sh.push(txSp(o.x + 0.1, o.y + 0.06, Math.max(0.2, o.w - 0.2), 0.28, [[{ t: o.it.label, sz: 10.5, b: 1, col: S.ink, font: S.font }]]));
      sh.push(txSp(o.x + 0.1, o.y + 0.32, Math.max(0.2, o.w - 0.2), 0.26,
        [[{ t: String(o.it.v) + (sec.unit || ''), sz: 10, col: S.body, font: S.font }]]));
    });
    return;
  }
  if (t === 'boxplot') {
    var groups = (sec.groups || []).filter(function (g) { return g && g.length >= 6; });
    var step = CW / Math.max(1, groups.length);
    var plotH = (P.y1 - P.y0) - 0.4;
    groups.forEach(function (g, i) {
      var cx = MX + step * i + step / 2;
      var bw = Math.min(0.9, step * 0.5);
      sh.push(shape('rect', cx - 0.012, P.y0, 0.024, plotH, S.faint));
      sh.push(shape('rect', cx - bw / 2, P.y0 + plotH * 0.2, bw, plotH * 0.6, S.soft, { line: S.accent }));
      sh.push(shape('rect', cx - bw / 2, P.y0 + plotH * 0.48, bw, 0.03, S.accent));
      sh.push(txSp(cx - step / 2, P.y1 - 0.34, step, 0.28,
        [[{ t: String(g[0]), sz: 10.5, col: S.body, font: S.font }]], { align: 'ctr' }));
    });
    return;
  }
  if (t === 'network') {
    var nds = sec.nodes || [];
    var n2 = Math.max(1, nds.length);
    var cx0 = MX + CW / 2, cy0 = (P.y0 + P.y1) / 2;
    var r = Math.min(CW / 2, (P.y1 - P.y0) / 2) - 1.0;
    var pos = {};
    nds.forEach(function (nd, i) {
      var a = -Math.PI / 2 + i * 2 * Math.PI / n2;
      pos[String(nd[0])] = { x: cx0 + r * Math.cos(a), y: cy0 + r * Math.sin(a) };
    });
    (sec.edges || []).forEach(function (e) {
      var a = pos[String(e[0])], b = pos[String(e[1])];
      if (!a || !b) return;
      sh.push(lineSeg(a.x, a.y, b.x, b.y, S.line, 1.5));
    });
    nds.forEach(function (nd) {
      var p = pos[String(nd[0])];
      sh.push(shape('ellipse', p.x - 0.26, p.y - 0.26, 0.52, 0.52, S.accent));
      var outward = p.x >= cx0;
      sh.push(txSp(outward ? p.x + 0.32 : p.x - 0.32 - 1.4, p.y - 0.14, 1.4, 0.28,
        [[{ t: String(nd[1] != null ? nd[1] : nd[0]), sz: 10, col: S.body, font: S.font }]],
        { align: outward ? 'l' : 'r', anchor: 'ctr' }));
    });
    return;
  }
  if (t === 'marimekko') {
    var cols = sec.cols || [];
    var legend = (sec.legend || []).map(String);
    var total = cols.reduce(function (a, c) { return a + (Number(c[1]) || 0); }, 0) || 1;
    var plotH2 = (P.y1 - P.y0) - 0.6;
    var availW = CW - 0.06 * Math.max(0, cols.length - 1);
    var cx1 = MX;
    cols.forEach(function (c, i) {
      var cw = Math.max(0.2, (Number(c[1]) || 0) / total * availW);
      /* 单元格兼容 [标签,数值] 对（与 B 通道 marimekkoSegs 同规则）；非数值 → 0 */
      var shares = ((sec.cells || [])[i] || []).map(function (el) {
        var v = Number(Array.isArray(el) ? el[1] : el);
        return isFinite(v) ? v : 0;
      });
      var sum = shares.reduce(function (a, b) { return a + b; }, 0) || 1;
      var cy = P.y0;
      shares.forEach(function (v, k) {
        var shh = Math.max(0.02, v / sum * plotH2);
        sh.push(shape('rect', cx1, cy, cw, shh, palette[k % palette.length]));
        cy += shh;
      });
      sh.push(txSp(cx1, P.y0 + plotH2 + 0.06, cw, 0.28,
        [[{ t: String(c[0]), sz: 10.5, b: 1, col: S.body, font: S.font }]], { align: 'ctr' }));
      cx1 += cw + 0.06;
    });
    var lx = MX;
    legend.forEach(function (lg, k) {
      sh.push(shape('rect', lx, P.y1 - 0.2, 0.12, 0.12, palette[k % palette.length]));
      sh.push(txSp(lx + 0.16, P.y1 - 0.26, 1.5, 0.26, [[{ t: lg, sz: 10, col: S.body, font: S.font }]], { anchor: 'ctr' }));
      lx += 1.75;
    });
    return;
  }
  if (t === 'streamgraph') {
    var series = sec.series || [];
    var labels = sec.labels || [];
    var nPts = labels.length || ((series[0] && series[0].values || []).length);
    if (nPts >= 2) {
      var values = series.map(function (se) {
        return (se.values || []).map(function (v) { return Math.max(0, Number(v) || 0); });
      });
      var totals = [];
      for (var i2 = 0; i2 < nPts; i2++) {
        var tt = 0;
        values.forEach(function (v) { tt += (v[i2] || 0); });
        totals.push(tt);
      }
      var maxTot = Math.max.apply(null, totals.concat([1]));
      /* Reserve legend INSIDE the plot box so 6-series pages do not crush the annotation band. */
      var legH = Math.min(1.2, Math.max(0.28, series.length * 0.22 + 0.08));
      var plotBottom = P.y1 - legH;
      var plotH3 = Math.max(0.6, plotBottom - P.y0);
      var cyMid = P.y0 + plotH3 / 2;
      var base = totals.map(function (tv) { return cyMid - tv / maxTot * plotH3 / 2; });
      series.forEach(function (se, si) {
        var upper = base.map(function (bv, i3) { return bv + (values[si][i3] || 0) / maxTot * plotH3 / 2; });
        var stepX = CW / (nPts - 1);
        for (var i4 = 0; i4 < nPts - 1; i4++) {
          var hgt = Math.max(0.04, ((upper[i4] - base[i4]) + (upper[i4 + 1] - base[i4 + 1])) / 2);
          sh.push(shape('rect', MX + i4 * stepX, (base[i4] + base[i4 + 1]) / 2, stepX, hgt, palette[si % palette.length]));
        }
        base = upper;
        sh.push(shape('rect', MX, plotBottom + 0.04 + si * 0.2, 0.12, 0.12, palette[si % palette.length]));
        sh.push(txSp(MX + 0.16, plotBottom + 0.02 + si * 0.2, 1.5, 0.2,
          [[{ t: String(se.name || ('系列' + (si + 1))), sz: 10, col: S.body, font: S.font }]], { anchor: 'ctr' }));
      });
      labels.forEach(function (lb, i5) {
        sh.push(txSp(MX + (nPts > 1 ? i5 / (nPts - 1) : 0.5) * CW - 0.4, plotBottom - 0.22, 0.8, 0.2,
          [[{ t: String(lb), sz: 9.5, col: S.faint, font: S.font }]], { align: 'ctr' }));
      });
    }
    return;
  }
}
/* 统一图表分发（与 scripts/layout-constants.json 的 charts.registry 同分派规则）
 * A 通道为形状近似：类别标签与数值都落为文本，数值 token 由 cross_verify 过滤；
 * 复杂信息图（sankey / treemap / boxplot / network / marimekko / streamgraph）请用专属页型承载。 */
function chartShapes(sh, ec, S, x, y, w, h, dcols) {
  var t = (ec.type || 'bar').toLowerCase();
  var reg = (typeof REG !== 'undefined' && REG && REG[t]) ? REG[t] : null;
  if (t === 'hbar') { hbarRows(sh, ec, S, y, y + h, dcols, x, w); return; }
  if (t === 'line' || t === 'dualline' || t === 'area') { lineShapes(sh, ec, S, x, y, w, h, dcols); return; }
  if (t === 'scatter' || t === 'bubble') { xyDots(sh, ec, S, x, y, w, h); return; }
  if (t === 'gauge') { gaugeApprox(sh, ec, S, x, y, w, h); return; }
  if (t === 'pie' || t === 'donut' || t === 'multidonut') { pieApprox(sh, ec, S, x, y, w, h, dcols); return; }
  /* sparkline / candlestick 的文本集须与 B 通道专属渲染器一致（否则 cross_verify 误报） */
  if (t === 'sparkline') { sparkApprox(sh, ec, S, x, y, w, h); return; }
  if (t === 'candlestick') { candleApprox(sh, ec, S, x, y, w, h); return; }
  if (reg && reg.pptx === 'shape') { shapeProportion(sh, ec, S, x, y, w, h, dcols); return; }
  vbarShapes(sh, ec, S, x, y, w, h, dcols);
}

/* 区域 IR 取用（与 scripts/lib_layout_regions.js 同源；未注入时回落 null） */
function regOf(type, slot, opts) {
  return (typeof regionOf === 'function') ? regionOf(type, slot, opts) : null;
}

/* ── 幻灯片生成（版式常量同 build_pptx.js · 同一 layout-constants.json） ── */
function slidesOf(model, S) {
  var slides = [];
  _mode = model.mode || 'presentation';
  function head(sh, eyebrow, title, lead) {
    var H = (typeof regionOf === 'function') ? regionOf('head', 'head') : {
      x: MX, y: PT.common.headEyebrowY, w: CW,
      titleY: PT.common.headTitleY, ruleY: PT.common.headRuleY, leadY: PT.common.leadY,
    };
    if (eyebrow) sh.push(txSp(H.x, H.y, H.w, 0.4, [[{ t: eyebrow, sz: 13, b: 1, col: S.accent, font: S.font, spc: 200 }]]));
    var titleH = eyebrow ? (H.ruleY - H.titleY - 0.06) : 1.0;
    var tSize = estTextH(title, CW, 30, 1.25) > titleH ? 24 : 30;
    sh.push(txSp(H.x, eyebrow ? H.titleY : 0.6, H.w, Math.max(0.6, titleH), [[{ t: title, sz: tSize, b: 1, col: S.ink, font: S.fontDisplay }]]));
    sh.push(shape('rect', H.x, eyebrow ? H.ruleY : 1.6, 0.9, 0.045, S.accent));
    if (lead) sh.push(txSp(H.x, H.leadY || PT.common.leadY, H.w, 0.5, [[{ t: lead, sz: 14, col: S.body, font: S.font }]]));
  }

  /* 封面 */
  var CV = PT.cover;
  var c = [shape('rect', 0, 0, PW, PH, S.accent)];
  c.push(txSp(MX, CV.metaY, CW, 0.4, [[{ t: model.meta || '', sz: 12, col: S.soft, font: S.font }]]));
  var cTSize = estTextH(model.title, CW - 1, 44, 1.25) > CV.titleH ? 36 : 44;
  c.push(txSp(MX, CV.titleY, CW - 1, CV.titleH, [[{ t: model.title, sz: cTSize, b: 1, col: S.onAccent, font: S.fontDisplay }]]));
  c.push(txSp(MX, CV.subtitleY, CW - 1, CV.subtitleH, [[{ t: model.subtitle || '', sz: 18, col: S.soft, font: S.font }]]));
  slides.push(c);

  /* Agenda（>8 条自动双列；>12 条自动分页；长标题截断+全称入 notes；列优先与 HTML 一致） */
  var items = model.agenda || [];
  if (items.length) {
    var ROWS_PER_PAGE = 12;
    var agPages = [];
    for (var ai = 0; ai < items.length; ai += ROWS_PER_PAGE) agPages.push(items.slice(ai, ai + ROWS_PER_PAGE));
    agPages.forEach(function (pageItems, pi) {
      var ag = [];
      var sub = agPages.length > 1 ? '（' + (pi + 1) + '/' + agPages.length + '）' : '';
      head(ag, 'AGENDA', '报告大纲' + sub);
      var colN = pageItems.length > 8 ? 2 : 1;
      var perCol = Math.ceil(pageItems.length / colN) || 1;
      var rowH = Math.min(1.05, (CONTENT_BOTTOM - CONTENT_TOP - 0.25) / Math.max(1, perCol));
      var numSz = rowH >= 0.85 ? 30 : (rowH >= 0.65 ? 22 : 18);
      var tSz = rowH >= 0.85 ? 16 : 14, dSz = rowH >= 0.85 ? 12 : 11;
      var agNotes = [];
      pageItems.forEach(function (it, i) {
        var col = Math.floor(i / perCol), row = i % perCol;
        var x = MX + col * (CW / colN), y = CONTENT_TOP + row * rowH;
        var titleBoxW = CW / colN - 1.15;
        var rawTitle = String(it[1] || '');
        var titleEstW = estTextH(rawTitle, titleBoxW, tSz, 1.2);
        var maxTitleH = rowH * 0.55;
        var title = rawTitle;
        if (titleEstW > maxTitleH) {
          var maxChars = Math.max(10, Math.floor(rawTitle.length * (maxTitleH / titleEstW)));
          if (rawTitle.length > maxChars) {
            title = rawTitle.slice(0, maxChars - 1) + '…';
            agNotes.push('条目 ' + it[0] + ' 全称：' + rawTitle);
          }
        }
        ag.push(txSp(x, y, 0.9, Math.min(0.9, rowH), [[{ t: it[0], sz: numSz, b: 1, col: S.accent, font: S.font }]]));
        ag.push(txSp(x + 1.0, y + 0.03, titleBoxW, Math.min(0.95, rowH),
          [[{ t: title, sz: tSz, b: 1, col: S.ink, font: S.font }],
           [{ t: it[2] || '', sz: dSz, col: S.body, font: S.font }]], { lineSpacing: tSz + 5 }));
      });
      slides.push(ag);
    });
  }

  /* Exhibit 徽标文本：纯编号补 "Exhibit " 前缀（HTML 为 `Exhibit {no}` + CSS uppercase）；
   调用方已带前缀的不重复（与 B 通道 exhibitBadge 同规则） */
function exhibitBadge(no) {
  var t = String(no == null ? '' : no).trim();
  if (!t) return t;
  return /^exhibit[\s\-:]*/i.test(t) ? t.toUpperCase() : ('EXHIBIT ' + t.toUpperCase());
}
/* 章节页 */
  (model.sections || []).forEach(function (sec) {
    var type = sec.type || 'points';
    var sh = [];
    if (type !== 'quote') head(sh, sec.eyebrow, sec.title, sec.lead);
    /* 非 exhibit 页型也可带 Exhibit 编号（帧头徽标；正文区下移让位，与 B 通道同规则） */
    var exBadge = (type !== 'exhibit' && sec.exhibitNo) ? exhibitBadge(sec.exhibitNo) : null;
    var bodyY0 = sec.lead ? PT.common.bodyYWithLead : CONTENT_TOP;
    var bodyY = exBadge ? bodyY0 + 0.42 : bodyY0;
    if (exBadge) {
      sh.push(txSp(MX, CONTENT_TOP - 0.06, CW, 0.3,
        [[{ t: exBadge, sz: 11.5, b: 1, col: S.accent, font: S.font, spc: 200 }]]));
    }
    var flagItems = Array.isArray(sec.flags) ? sec.flags.filter(Boolean) : [];
    var _F = PT.flagbar || { hdH: 0.26, rowH: 0.24, maxRows: 3, gap: 0.12 };
    var flagH = flagItems.length
      ? (_F.hdH + Math.min(_F.maxRows, flagItems.length) * _F.rowH + 0.06) : 0;
    var bodyBottom = chartBottom(!!sec.soWhat, !!(sec.footnote || sec.note));
    var flagY = 0;
    if (flagH) {
      flagY = CONTENT_BOTTOM - flagH;
      if (sec.footnote) flagY = Math.min(flagY, PT.exhibit.footnoteY - flagH - 0.06);
      if (sec.soWhat) flagY = Math.min(flagY, PT.exhibit.soWhatY - flagH - 0.06);
      if (sec.footnote || sec.soWhat) flagY = Math.min(flagY, CONTENT_BOTTOM_NOTE - flagH);
      bodyBottom = Math.min(bodyBottom, flagY - (_F.gap || 0.12));
    }

    if (type === 'metrics') {
      var M = PT.metrics, ms = sec.metrics || [], n = Math.max(1, ms.length);
      var mReg = regOf('metrics', 'primary') || { x: MX, y: M.bandY, w: CW, h: M.cardH };
      var g = cols(mReg.w, n, M.gap);
      var mw = Math.min(M.maxW, g.w);
      var gx = mReg.x + (mReg.w - n * mw - (n - 1) * M.gap) / 2;
      var cardH = Math.min(mReg.h, CONTENT_BOTTOM - mReg.y);
      ms.forEach(function (m, i) {
        var x = gx + i * (mw + M.gap);
        sh.push(shape('roundRect', x, mReg.y, mw, cardH, S.surface, { line: S.line, adj: 4000 }));
        var vSize = estTextH(m[0], mw - 0.2, 40, 1.1) > cardH * 0.5 ? 30 : 40;
        sh.push(txSp(x, M.valY, mw, M.valH, [[{ t: m[0], sz: vSize, b: 1, col: S.accent, font: S.fontDisplay }]], { align: 'ctr' }));
        sh.push(txSp(x + 0.15, M.capY, mw - 0.3, M.capH, [[{ t: m[1], sz: 11.5, col: S.body, font: S.font }]], { align: 'ctr' }));
      });
    } else if (type === 'kpi') {
      var K = PT.kpi, hro = sec.hero || [];
      var hReg = regOf('kpi', 'hero') || { x: MX, y: K.heroY, w: CW * K.heroW, h: K.heroH };
      sh.push(txSp(hReg.x, hReg.y, hReg.w, hReg.h, [[{ t: String(hro[0] || ''), sz: 64, b: 1, col: S.accent, font: S.fontDisplay }]]));
      sh.push(txSp(hReg.x + 0.05, hReg.y + 1.5, hReg.w - 0.4, 0.55, [[{ t: String(hro[1] || ''), sz: 15, b: 1, col: S.ink, font: S.font }]]));
      if (hro[2]) sh.push(txSp(hReg.x + 0.05, hReg.y + 2.1, hReg.w - 0.4, 0.4, [[{ t: '▲ ' + hro[2], sz: 12, b: 1, col: S.accent, font: S.font }]]));
      var kdivX = MX + CW * K.dividerX;
      sh.push(shape('rect', kdivX, K.heroY + 0.15, 0.025, 3.1, S.line));
      var mRegK = regOf('kpi', 'metrics') || { x: kdivX + 0.35, y: K.metricY0, w: CW * (1 - K.dividerX) - 0.5 };
      var kmets = sec.metrics || [];
      /* 容量按最小允许行高判断，行高按全部指标自适应压缩 —— 禁静默丢数据（与 B 通道同规则） */
      var kAvailA = CONTENT_BOTTOM - mRegK.y;
      var kCap = Math.max(1, Math.floor(kAvailA / 0.42));
      var kRows = Math.min(kmets.length, kCap);
      if (kRows < kmets.length && typeof console !== 'undefined')
        console.warn('[pptx-export] KPI 页「' + (sec.title || '') + '」支撑指标 ' + kmets.length +
          ' 个超出容量，仅渲染前 ' + kRows + ' 个 —— 建议拆页');
      var kRowH = fitRowH(kAvailA, kRows, K.metricRowH, 0.42);
      var kTopH = Math.min(0.55, kRowH * 0.62);
      kmets.slice(0, kRows).forEach(function (m, i) {
        var ky = mRegK.y + i * kRowH;
        sh.push(txSp(mRegK.x, ky, mRegK.w, kTopH, [[{ t: m[0], sz: 22, b: 1, col: S.accent, font: S.fontDisplay }]]));
        sh.push(txSp(mRegK.x, ky + kTopH, mRegK.w, Math.max(0.24, kRowH - kTopH), [[{ t: m[1], sz: 10.5, col: S.faint, font: S.font }]]));
      });
    } else if (type === 'comparison') {
      var C2 = PT.comparison;
      var lR = regOf('comparison', 'left') || { x: MX, y: C2.panelY, w: (CW - C2.panelGap) / 2, h: C2.panelH };
      var rR = regOf('comparison', 'right') || { x: MX + (CW + C2.panelGap) / 2, y: C2.panelY, w: (CW - C2.panelGap) / 2, h: C2.panelH };
      var cw2 = lR.w, cpy = lR.y, cph = lR.h, rx2 = rR.x;
      sh.push(shape('roundRect', lR.x, cpy, cw2, cph, S.surface, { adj: 4000, line: S.line }));
      sh.push(shape('roundRect', rx2, cpy, cw2, cph, S.soft, { adj: 4000 }));
      [{ x: lR.x, d: (sec.left || {}) }, { x: rx2, d: (sec.right || {}) }].forEach(function (sd) {
        var isRight = sd.x === rx2;
        var pts = sd.d.points || [];
        var avail = cph - C2.titleH - 0.34;
        var rowH2 = fitRowH(avail, pts.length, C2.rowH, 0.34);
        var fz = rowH2 < 0.5 ? 11.5 : 13;
        sh.push(txSp(sd.x + 0.22, cpy + 0.18, cw2 - 0.44, C2.titleH,
          [[{ t: sd.d.title || '', sz: 15, b: 1, col: isRight ? S.accent : S.ink, font: S.font }]]));
        pts.forEach(function (p, pi) {
          var py = cpy + 0.18 + C2.titleH + 0.16 + pi * rowH2;
          sh.push(shape('rect', sd.x + 0.24, py + rowH2 / 2 - 0.06, 0.12, 0.12, isRight ? S.accent : S.faint));
          sh.push(txSp(sd.x + 0.5, py, cw2 - 0.75, rowH2 - 0.04,
            [[{ t: p[0] + '　', sz: fz, b: 1, col: S.ink, font: S.font },
              { t: p[1], sz: fz - 1, col: S.body, font: S.font }]]));
        });
      });
      /* R2：verdict 与 soWhat 共用 annotation 槽位——只画一个（verdict 优先） */
      if (sec.verdict) {
        var vR = regOf('exhibit', 'annotation') || { x: MX, y: PT.exhibit.soWhatY, w: CW, h: 0.62 };
        sh.push(shape('rect', vR.x, vR.y, vR.w, vR.h, S.accent, { name: 'tr:soWhat' }));
        sh.push(txSp(vR.x + 0.22, vR.y + 0.06, vR.w - 0.44, vR.h - 0.12,
          [[{ t: '结论　', sz: 11, b: 1, col: S.onAccent, font: S.font, spc: 150 },
            { t: sec.verdict, sz: 12.5, b: 1, col: S.onAccent, font: S.font }]], { anchor: 'ctr', name: 'tr:soWhat' }));
      }
    } else if (type === 'quote') {
      var Q = PT.quote;
      var qR = regOf('quote', 'primary') || { x: MX + 1.05, y: Q.textY, w: CW - 2.1, h: Q.textH };
      /* 金句页用主题一致强调带（accent-soft 底）——浅色主题下不再出现深色页 */
      sh.push(shape('rect', 0, 0, PW, PH, S.soft));
      if (sec.eyebrow) sh.push(txSp(MX, PT.common.headEyebrowY, CW, 0.4, [[{ t: sec.eyebrow, sz: 13, b: 1, col: S.accent, font: S.font, spc: 200 }]]));
      sh.push(txSp(MX, PT.common.headTitleY, CW, 1.0, [[{ t: sec.title, sz: 30, b: 1, col: S.ink, font: S.fontDisplay }]]));
      sh.push(shape('rect', MX, PT.common.headRuleY, 0.9, 0.045, S.accent));
      sh.push(txSp(MX + 0.05, Q.markY, 1.2, 1.1, [[{ t: '「', sz: 60, b: 1, col: S.accent, font: S.fontDisplay }]]));
      var qSize = estTextH(sec.quote, qR.w, 20, 1.4) > qR.h ? 16 : 20;
      sh.push(txSp(qR.x, qR.y, qR.w, qR.h, [[{ t: sec.quote, sz: qSize, b: 1, col: S.ink, font: S.fontDisplay }]], { anchor: 'ctr' }));
      sh.push(txSp(qR.x, Q.authorY, qR.w, 0.45, [[{ t: '—— ' + sec.author, sz: 13, b: 1, col: S.accent, font: S.font }]], { align: 'r' }));
      if (sec.context) sh.push(txSp(qR.x, Q.contextY, qR.w, 0.4, [[{ t: sec.context, sz: 11, col: S.faint, font: S.font }]], { align: 'r' }));
    } else if (type === 'image') {
      /* 素材图片页：full 版心全宽 / half 左图右注 / bleed 通栏出血 / grid 多图网格 /
         compare 双图对比 / wall Logo 墙；无图（image.placeholder）走原生占位块 + 标签文本 */
      var IM = PT.image, img = sec.image || {};
      var items = Array.isArray(img.items) ? img.items.filter(Boolean) : [];
      var layout = String(img.layout || (items.length > 1 ? 'grid' : 'full')).toLowerCase();
      var fit = String(img.fit || ((typeof IMG !== 'undefined' && IMG && IMG.fitDefault) || 'cover')).toLowerCase();
      var isPh = !!img.placeholder;
      var iR = regOf('image', 'primary', { top: bodyY, caption: !!img.caption }) ||
        { x: MX, y: Math.max(IM.y, bodyY), w: CW, h: IM.h };
      var iy = iR.y;
      var capH2 = img.caption ? 0.32 : 0;
      var ih = Math.max(1.2, iR.h);
      var capYImg = imageLayoutShapes(sh, S, layout, img, items, sec.points || [], isPh, fit, iy, iy + ih);
      if (img.caption) sh.push(txSp(MX, capYImg + 0.04, CW, capH2, [[{ t: img.caption, sz: 10.5, col: S.faint, font: S.font }]]));
    } else if (type === 'donut') {
      var dcn = sec.chart || {};
      if (dcn.labels && dcn.values) donutChart(sh, dcn, S, dcn.colors || donutColors(model.style, S, model.theme), bodyBottom);
    } else if (type === 'heatmap') {
      var H = PT.heatmap;
      var hR = regOf('heatmap', 'primary', { bottom: bodyBottom }) || { x: MX, y: H.y, w: CW, h: bodyBottom - H.y };
      var rowsH = sec.rowHeads || [], colsH = sec.colHeads || [], cells = sec.cells || [];
      var nR = Math.max(1, rowsH.length), nC = Math.max(1, colsH.length);
      var availH = hR.h;
      var rowH3 = fitRowH(availH - H.headH, nR, H.cellH, 0.24);
      var gridW = hR.w - H.labelW;
      var cw3 = (gridW - (nC - 1) * H.cellGap) / nC;
      var flat = [], k2;
      for (k2 = 0; k2 < cells.length; k2++) for (var j2 = 0; j2 < (cells[k2] || []).length; j2++) { var nv = Number(cells[k2][j2]); if (!isNaN(nv)) flat.push(nv); }
      var vmax3 = flat.length ? Math.max.apply(null, flat) : 1;
      var vmin3 = flat.length ? Math.min.apply(null, flat) : 0;
      var levels = [S.surface, S.soft, S.line, S.accent];
      colsH.forEach(function (ch2, ci) {
        sh.push(txSp(hR.x + H.labelW + ci * (cw3 + H.cellGap), hR.y, cw3, H.headH,
          [[{ t: ch2, sz: 11, b: 1, col: S.body, font: S.font }]], { align: 'ctr', anchor: 'ctr' }));
      });
      var rowsUse = Math.min(nR, cells.length);
      for (var ri = 0; ri < rowsUse; ri++) {
        var yy = hR.y + H.headH + 0.08 + ri * (rowH3 + H.cellGap);
        sh.push(txSp(hR.x, yy, H.labelW - 0.15, rowH3, [[{ t: rowsH[ri] || '', sz: 11, b: 1, col: S.body, font: S.font }]], { align: 'r', anchor: 'ctr' }));
        for (var ci2 = 0; ci2 < nC; ci2++) {
          var v2 = Number((cells[ri] || [])[ci2]);
          var has2 = !isNaN(v2);
          var p2 = (has2 && vmax3 > vmin3) ? (v2 - vmin3) / (vmax3 - vmin3) : 0.5;
          var lvl = p2 >= 0.86 ? 3 : (p2 >= 0.55 ? 2 : (p2 >= 0.25 ? 1 : 0));
          var cx2 = hR.x + H.labelW + ci2 * (cw3 + H.cellGap);
          sh.push(shape('roundRect', cx2, yy, cw3, rowH3, levels[lvl],
            { adj: 3000, line: lvl === 0 ? S.line : undefined }));
          sh.push(txSp(cx2, yy, cw3, rowH3,
            [[{ t: has2 ? valText(v2, sec.unit) : '—', sz: 11.5, b: lvl >= 2 ? 1 : 0,
                col: lvl >= 3 ? S.onAccent : S.body, font: S.font }]], { align: 'ctr', anchor: 'ctr' }));
        }
      }
      var lg = sec.scaleLabel || ['低', '高'];
      var lgy = hR.y + H.headH + 0.08 + rowsUse * (rowH3 + H.cellGap) + 0.06;
      sh.push(txSp(hR.x, lgy, 0.6, 0.3, [[{ t: lg[0] || '低', sz: 9.5, col: S.faint, font: S.font }]]));
      for (var li2 = 0; li2 < 4; li2++) {
        sh.push(shape('rect', hR.x + 0.45 + li2 * 0.3, lgy + 0.04, 0.28, 0.16, levels[li2],
          { line: li2 === 0 ? S.line : undefined }));
      }
      sh.push(txSp(hR.x + 1.75, lgy, 0.6, 0.3, [[{ t: lg[1] || '高', sz: 9.5, col: S.faint, font: S.font }]]));
    } else if (type === 'bullet') {
      var B = PT.bullet, its = sec.items || [], nB = Math.max(1, its.length);
      var bR = regOf('bullet', 'primary', { bottom: bodyBottom }) || { x: MX, y: B.y, w: CW, h: bodyBottom - B.y };
      var availB = bR.h;
      var rowHB = fitRowH(availB, nB, B.rowH, 0.26);
      var trackX = bR.x + B.labelW + 0.15;
      var trackW = bR.w - B.labelW - B.valW - 0.3;
      var nums = [], q2;
      for (q2 = 0; q2 < its.length; q2++) { var nq = Number(its[q2][1]); if (!isNaN(nq)) nums.push(nq); }
      var vmaxB = sec.max || (nums.length ? Math.max.apply(null, nums) : 1);
      its.forEach(function (it, i) {
        var yy2 = bR.y + i * rowHB + rowHB / 2 - B.barH / 2;
        var v = Number(it[1]) || 0, tgt = Number(it[2]);
        var hit = !isNaN(tgt) && v >= tgt;
        sh.push(txSp(bR.x, bR.y + i * rowHB, B.labelW, rowHB, [[{ t: String(it[0]), sz: 12, b: 1, col: S.ink, font: S.font }]], { anchor: 'ctr' }));
        sh.push(shape('roundRect', trackX, yy2, trackW, B.barH, S.surface, { adj: 50000, line: S.line }));
        var fw = Math.max(0.02, Math.min(1, v / (vmaxB || 1)) * trackW);
        sh.push(shape('roundRect', trackX, yy2, fw, B.barH, hit ? S.accent : S.faint, { adj: 50000 }));
        if (!isNaN(tgt)) {
          var tx2 = trackX + Math.min(1, tgt / (vmaxB || 1)) * trackW;
          sh.push(shape('rect', tx2 - 0.01, yy2 - 0.07, 0.02, B.barH + 0.14, S.body));
        }
        sh.push(txSp(trackX + trackW + 0.12, bR.y + i * rowHB, B.valW, rowHB,
          [[{ t: String(it[1]) + (sec.unit || ''), sz: 12, b: 1, col: hit ? S.accent : S.body, font: S.font },
            { t: isNaN(tgt) ? '' : ' / ' + tgt + (sec.unit || ''), sz: 10, col: S.faint, font: S.font }]],
          { align: 'r', anchor: 'ctr' }));
      });
    } else if (type === 'pyramid') {
      var P = PT.pyramid, lv = sec.levels || [], nP = Math.max(1, lv.length);
      var pR = regOf('pyramid', 'primary', { bottom: bodyBottom }) || { x: MX, y: P.y, w: CW, h: bodyBottom - P.y };
      var availP = pR.h;
      var rowHP = fitRowH(availP - (nP - 1) * P.gap, nP, P.rowH, 0.26);
      lv.forEach(function (l, i) {
        var frac = P.minW + (1 - P.minW) * (nP === 1 ? 1 : i / (nP - 1));
        var w2 = pR.w * frac, x2 = pR.x + (pR.w - w2) / 2, y2 = pR.y + i * (rowHP + P.gap);
        var acc = isRec(l) && l.accent;
        var lt = isRec(l) ? (l.t || '') : String(l[0] || '');
        var ld = isRec(l) ? (l.d || '') : String(l[1] || '');
        sh.push(shape('roundRect', x2, y2, w2, rowHP, acc ? S.soft : S.surface, { adj: 5000, line: acc ? undefined : S.line }));
        var lwP = Math.min(P.labelW, (w2 - 0.44) * (P.labelFrac == null ? 0.32 : P.labelFrac));
        var descW = w2 - 0.44 - lwP;
        /* 窄层判定：说明列 < 1.2in，或标题在标题列内放不下单行 → 单框混排（与 B 通道同规则） */
        var narrowP = descW < 1.2 || (ld && estLines(lt, lwP, 13.5) > 1) || (!ld && estLines(lt, w2 - 0.44, 13.5) > 1);
        if (narrowP) {
          /* 顶层窄 → 标题上、说明下单框混排（HTML 窄屏 .pyr__lvl 即单列，与 B 通道同规则） */
          sh.push(txSp(x2 + 0.22, y2 + 0.03, w2 - 0.44, 0.30,
            [[{ t: lt, sz: 12.5, b: 1, col: acc ? S.accent : S.ink, font: S.font }]]));
          sh.push(txSp(x2 + 0.22, y2 + 0.33, w2 - 0.44, Math.max(0.2, rowHP - 0.36),
            [[{ t: ld, sz: 10.5, col: S.faint, font: S.font }]]));
        } else {
          sh.push(txSp(x2 + 0.22, y2, lwP, rowHP, [[{ t: lt, sz: 13.5, b: 1, col: acc ? S.accent : S.ink, font: S.font }]], { anchor: 'ctr' }));
          if (ld) sh.push(txSp(x2 + 0.22 + lwP, y2, descW, rowHP, [[{ t: ld, sz: 11, col: S.faint, font: S.font }]], { anchor: 'ctr' }));
        }
      });
    } else if (type === 'steps') {
      var S2 = PT.steps, st = sec.steps || [], maxPer = S2.maxPerRow || 6, groups = sec.groups || [];
      var sR = regOf('steps', 'primary') || { x: MX, y: S2.y, w: CW, h: S2.barH };
      var chunks = [];
      if (groups.length) {
        var kk = 0;
        groups.forEach(function (gp) { var cnt = Number(gp[1]) || 0; chunks.push({ label: gp[0], items: st.slice(kk, kk + cnt) }); kk += cnt; });
        if (kk < st.length) chunks.push({ label: '', items: st.slice(kk) });
      } else {
        for (var i3 = 0; i3 < st.length; i3 += maxPer) chunks.push({ label: '', items: st.slice(i3, i3 + maxPer) });
      }
      var rowsN = Math.max(1, chunks.length);
      var availS = bodyBottom - sR.y;
      var rowHS = fitRowH(availS - (rowsN - 1) * 0.3, rowsN, sR.h || S2.barH, 0.3);
      var cyS = sR.y;
      chunks.forEach(function (ck) {
        if (ck.label) {
          sh.push(txSp(sR.x, cyS - 0.02, sR.w, 0.26, [[{ t: ck.label, sz: 10, b: 1, col: S.faint, font: S.font, spc: 100 }]]));
          cyS += 0.28;
        }
        var n4 = Math.max(1, ck.items.length);
        var g4 = cols(sR.w, n4, S2.gap + S2.arrowW);
        ck.items.forEach(function (it, i) {
          var acc = isRec(it) && it.accent;
          var t4 = isRec(it) ? (it.t || '') : String(it[0] || '');
          var d4 = isRec(it) ? (it.d || '') : String(it[1] || '');
          var x4 = sR.x + i * g4.step;
          sh.push(shape('roundRect', x4, cyS, g4.w, rowHS, acc ? S.soft : S.surface, { adj: 5000, line: acc ? undefined : S.line }));
          var num = String(i + 1); if (num.length < 2) num = '0' + num;
          var pd = S2.pad, numH = S2.numH, ttlH = S2.titleH;
          sh.push(txSp(x4 + 0.14, cyS + pd, g4.w - 0.28, numH, [[{ t: num, sz: 10, b: 1, col: S.accent, font: S.font }]]));
          sh.push(txSp(x4 + 0.14, cyS + pd + numH, g4.w - 0.28, ttlH, [[{ t: t4, sz: 13, b: 1, col: acc ? S.accent : S.ink, font: S.font }]]));
          if (d4) sh.push(txSp(x4 + 0.14, cyS + pd + numH + ttlH, g4.w - 0.28, Math.max(0.2, rowHS - pd * 2 - numH - ttlH), [[{ t: d4, sz: 10, col: S.faint, font: S.font }]]));
          if (i < n4 - 1) {
            sh.push(txSp(x4 + g4.w, cyS, S2.arrowW + S2.gap, rowHS, [[{ t: '→', sz: 12, col: S.faint, font: S.font }]], { align: 'ctr', anchor: 'ctr' }));
          }
        });
        cyS += rowHS + 0.3;
      });
    } else if (type === 'table') {
      var tR = regOf('table', 'primary', { bottom: bodyBottom }) || { x: MX, y: CONTENT_TOP, w: CW, h: bodyBottom - CONTENT_TOP };
      var headRow = sec.table.head;
      var colW = sec.table.colW || headRow.map(function () { return tR.w / headRow.length; });
      sh.push(table(tR.x, tR.y, tR.w, colW, [headRow].concat(sec.table.rows), S, { availH: tR.h }));
    } else if (type === 'timeline') {
      var T = PT.timeline, ps = sec.phases || [], np = Math.max(1, ps.length);
      var tLR = regOf('timeline', 'primary') || { x: MX, y: T.labelY, w: CW };
      var stepW = (tLR.w - 1.0) / np;
      sh.push(shape('rect', tLR.x + 0.2, T.axisY, tLR.w - 0.4, 0.02, S.line));
      ps.forEach(function (p, i) {
        var x5 = tLR.x + 0.2 + i * stepW;
        var on = p[3] === 'done' || p[3] === 'now';
        sh.push(shape('ellipse', x5 - T.dotR / 2, T.dotY, T.dotR, T.dotR, on ? S.accent : S.line));
        sh.push(txSp(x5 - 0.1, T.labelY, stepW - 0.2, 0.4, [[{ t: p[0], sz: 12, b: 1, col: S.accent, font: S.font, spc: 100 }]]));
        sh.push(txSp(x5 - 0.1, T.nameY, stepW - 0.2, 0.5, [[{ t: p[1], sz: 17, b: 1, col: p[3] === 'now' ? S.accent : S.ink, font: S.fontDisplay }]]));
        sh.push(txSp(x5 - 0.1, T.descY, stepW - 0.25, T.descH, [[{ t: p[2] || '', sz: 12, col: S.body, font: S.font }]], { lineSpacing: 18 }));
      });
    } else if (type === 'bar') {
      var ch = sec.chart || {};
      var dcols2 = (ch.colors || dataColors(model.style, model.theme));
      var botY = chartBottom(!!sec.soWhat, !!(sec.footnote || sec.note)) - 0.05;
      var isHBar = ch.type === 'hbar';
      var bRR = regOf('bar', isHBar ? 'hbar' : 'primary', { bottom: botY }) ||
        { x: isHBar ? MX : MX + PT.bar.chartX, y: isHBar ? PT.bar.hbarY0 : PT.bar.chartY,
          w: isHBar ? CW : CW - PT.bar.chartW, h: 3 };
      var ptsB = (sec.points || []).filter(Boolean);
      var bx = bRR.x, bw = bRR.w;
      if (ptsB.length && !isHBar) {
        var sideW = Math.min(3.6, Math.max(2.6, bRR.w * 0.30));
        bw = Math.max(3.2, bRR.w - sideW - 0.28);
        var sx = bRR.x + bw + 0.28;
        var rowHb = Math.min(0.72, (bRR.h - 0.1) / Math.max(1, ptsB.length));
        ptsB.slice(0, 6).forEach(function (p, i) {
          var k = Array.isArray(p) ? String(p[0] || '') : String((p && p.t) || '');
          var v = Array.isArray(p) ? String(p[1] || '') : String((p && p.d) || '');
          var y = bRR.y + i * rowHb;
          sh.push(shape('rect', sx, y + 0.12, 0.08, 0.08, S.accent));
          sh.push(txSp(sx + 0.2, y, sideW - 0.25, rowHb,
            [[{ t: k + (v ? '　' : ''), sz: 12, b: 1, col: S.ink, font: S.font },
              { t: v, sz: 11, col: S.body, font: S.font }]], { anchor: 'ctr' }));
        });
      }
      if (isHBar) {
        chartBlockShapes(sh, ch, S, bx, bRR.y, bw, bRR.h, dcols2);
      } else {
        chartBlockShapes(sh, ch, S, bx, bRR.y, bw, Math.max(1.5, bRR.h), dcols2);
      }
    } else if (type === 'twocol' || type === 'threecol') {
      var ps2 = sec.paragraphs || [];
      var nCol = (type === 'threecol') ? 3 : 2;
      var gapC = (type === 'threecol') ? PT.research.col3Gap : PT.twocol.colGap;
      /* R3：多栏均分用版心全宽（regOf('twocol') 返回单栏宽，当总宽会压扁三栏） */
      var tcR = { x: MX, y: bodyY, w: CW, h: bodyBottom - bodyY };
      var gC = cols(tcR.w, nCol, gapC);
      var perC = Math.ceil(ps2.length / nCol);
      var availC = tcR.h;
      /* 探针与 build_pptx.js 同算法：按「各栏字数之和」的最大值估算（保证两通道字号一致） */
      var longest = 0, gi, pi2;
      for (gi = 0; gi < nCol; gi++) {
        var colG = ps2.slice(gi * perC, (gi + 1) * perC), ssum = 0;
        for (pi2 = 0; pi2 < colG.length; pi2++) ssum += String(colG[pi2][1] || '').length;
        if (ssum > longest) longest = ssum;
      }
      var probe = [], w4;
      for (w4 = 0; w4 < longest / 120; w4++) probe.push(new Array(121).join('x'));
      if (!probe.length) probe.push(new Array(1 + longest).join('x'));
      var fzC = fitFont(probe, gC.w, availC, { max: 13.5, gapFactor: 1.2 });
      for (var ci3 = 0; ci3 < nCol; ci3++) {
        var colC = ps2.slice(ci3 * perC, (ci3 + 1) * perC);
        if (!colC.length) continue;
        var runsC = [];
        colC.forEach(function (p) {
          runsC.push([{ t: p[0] + '　', sz: fzC, b: 1, col: S.ink, font: S.font },
                      { t: p[1], sz: fzC - 1, col: S.body, font: S.font }]);
        });
        sh.push(txSp(tcR.x + ci3 * gC.step, tcR.y, gC.w, availC, runsC,
          { lineSpacing: fzC * 1.5, spaceBefore: 7 }));
      }
    } else if (type === 'halftable') {
      var yH = sec.lead ? PT.common.bodyYWithLead : PT.research.denseTableY;
      var hLR = regOf('halftable', 'left', { top: yH, bottom: bodyBottom }) ||
        { x: MX, y: yH, w: CW * PT.research.halfTableW, h: bodyBottom - yH };
      var hRR = regOf('halftable', 'right', { top: yH, bottom: bodyBottom }) ||
        { x: MX + CW * PT.research.halfChartX, y: yH, w: CW * PT.research.halfChartW, h: bodyBottom - yH };
      var lwH = hLR.w;
      if (sec.table && sec.table.head) {
        var colWH = sec.table.colW || sec.table.head.map(function () { return lwH / sec.table.head.length; });
        sh.push(table(hLR.x, hLR.y, lwH, colWH, [sec.table.head].concat(sec.table.rows || []), S,
          { availH: hLR.h, maxRowH: PT.research.denseRowH + 0.1, minRowH: 0.28 }));
      }
      var ecH = sec.chart || {};
      if (ecH.labels && ecH.values) {
        chartBlockShapes(sh, ecH, S, hRR.x, hRR.y, hRR.w, Math.max(1.2, hRR.h),
          (ecH.colors || dataColors(model.style, model.theme)));
      }
    } else if (type === 'matrix') {
      var rhH = sec.rowHeads || [], chH = sec.colHeads || [];
      var mxR = regOf('matrix', 'primary', { bottom: bodyBottom }) ||
        { x: MX, y: PT.research.matrixY, w: CW, h: bodyBottom - PT.research.matrixY };
      var mY = mxR.y, mLW = PT.research.matrixLabelW;
      var rowsC = sec.cells || [], nR2 = Math.max(1, rowsC.length);
      var availM = mxR.h - 0.42;
      var mCH = fitRowH(availM, nR2, PT.research.matrixCellH, 0.3);
      var mW = (mxR.w - mLW) / Math.max(1, chH.length);
      chH.forEach(function (ch3, ci) {
        sh.push(txSp(mxR.x + mLW + ci * mW, mY, mW, 0.34, [[{ t: ch3, sz: 11, b: 1, col: S.body, font: S.font }]], { align: 'ctr', anchor: 'ctr' }));
      });
      rowsC.forEach(function (rowC, ri) {
        var y6 = mY + 0.42 + ri * mCH;
        sh.push(txSp(mxR.x, y6 + (mCH - 0.5) / 2, mLW - 0.15, 0.5, [[{ t: rhH[ri] || '', sz: 11, b: 1, col: S.body, font: S.font }]], { align: 'r', anchor: 'ctr' }));
        rowC.forEach(function (cell, ci) {
          var acc = isRec(cell) && cell.accent;
          var txt = isRec(cell) ? (cell.t || '') : String(cell);
          var cx4 = mxR.x + mLW + ci * mW;
          sh.push(shape('roundRect', cx4 + 0.04, y6, mW - 0.08, mCH - 0.1, acc ? S.soft : S.surface,
            { adj: 3000, line: acc ? undefined : S.line }));
          sh.push(txSp(cx4 + 0.14, y6 + 0.08, mW - 0.28, mCH - 0.26, [[{ t: txt, sz: 11, col: acc ? S.accent : S.body, font: S.font }]], { anchor: 'ctr' }));
        });
      });
    } else if (type === 'lane') {
      var lnS = sec.lanes || [], nL = Math.max(1, lnS.length);
      var startL = sec.lead ? PT.common.bodyYWithLead : PT.arch.fullStartY;
      var lnR = regOf('lane', 'primary', { mode: model.mode, bottom: bodyBottom }) ||
        { x: MX, y: startL, w: CW, h: bodyBottom - startL };
      var availL = lnR.h;
      var lnH = fitRowH(availL - (nL - 1) * PT.arch.laneGap, nL, PT.arch.laneH, 0.3);
      var lnGap = PT.arch.laneGap, lnHW = PT.arch.laneHeadW;
      lnS.forEach(function (ln, li) {
        var y7 = lnR.y + li * (lnH + lnGap);
        sh.push(shape('roundRect', lnR.x, y7, lnR.w, lnH, S.surface, { adj: 2500, line: S.line }));
        sh.push(shape('rect', lnR.x, y7, lnHW, lnH, S.surface, { line: S.line }));
        sh.push(txSp(lnR.x + 0.08, y7, lnHW - 0.16, lnH, [[{ t: ln[0], sz: 11, b: 1, col: S.body, font: S.font }]], { align: 'ctr', anchor: 'ctr' }));
        var steps = ln[1] || [];
        var stepW2 = Math.min(PT.arch.stepMaxW, (lnR.w - lnHW - 0.4 - (steps.length - 1) * PT.arch.stepGap) / Math.max(1, steps.length));
        steps.forEach(function (st, si) {
          var stAcc = isRec(st) && st.accent;
          var stT = isRec(st) ? st.t : st;
          var sx2 = lnR.x + lnHW + 0.2 + si * (stepW2 + PT.arch.stepGap);
          sh.push(shape('roundRect', sx2, y7 + 0.13, stepW2, lnH - 0.26, stAcc ? S.soft : S.bg,
            { adj: 4000, line: stAcc ? undefined : S.line }));
          sh.push(txSp(sx2 + 0.06, y7 + 0.13, stepW2 - 0.12, lnH - 0.26,
            [[{ t: stT, sz: 11, b: stAcc ? 1 : 0, col: stAcc ? S.accent : S.ink, font: S.font }]], { align: 'ctr', anchor: 'ctr' }));
          if (si < steps.length - 1) {
            sh.push(txSp(sx2 + stepW2, y7 + 0.13, PT.arch.stepGap, lnH - 0.26, [[{ t: '→', sz: 11, col: S.faint, font: S.font }]], { align: 'ctr', anchor: 'ctr' }));
          }
        });
      });
    } else if (type === 'cards') {
      var cdC = PT.cards, cds = sec.cards || [];
      var cR = regOf('cards', 'primary', { bottom: bodyBottom }) ||
        { x: MX, y: cdC.startY, w: CW, h: bodyBottom - cdC.startY };
      var cN = Math.min(sec.columns || 3, cds.length || 1);
      var rN = Math.ceil((cds.length || 1) / cN);
      var gw2 = (cR.w - (cN - 1) * cdC.gap) / cN;
      var gh2 = fitRowH(cR.h - (rN - 1) * cdC.gap, rN, cdC.maxH, 0.6);
      cds.forEach(function (cd, i) {
        var col2 = i % cN, row2 = Math.floor(i / cN);
        var x8 = cR.x + col2 * (gw2 + cdC.gap), y8 = cR.y + row2 * (gh2 + cdC.gap);
        sh.push(shape('roundRect', x8, y8, gw2, gh2, S.surface, { line: S.line, adj: 5000 }));
        /* 卡片头路标（与 B 通道同源：accent 小方块 = PPTX 侧图标等价物） */
        var ico2 = 0.18;
        sh.push(shape('roundRect', x8 + 0.18, y8 + 0.2, ico2, ico2, S.accent, { adj: 2500 }));
        sh.push(txSp(x8 + 0.18 + ico2 + 0.1, y8 + 0.14, gw2 - 0.36 - ico2 - 0.1, cdC.titleH,
          [[{ t: cd.title, sz: 15, b: 1, col: S.ink, font: S.font }]]));
        var paras2 = (cd.points || []).map(function (pt) {
          var line;
          if (pt && pt.length != null && typeof pt !== 'string') {
            var k = pt[0] == null ? '' : String(pt[0]);
            var v = pt[1] == null ? '' : String(pt[1]);
            line = (k && v) ? ('· ' + k + '　' + v) : ('· ' + (k || v));
          } else if (pt && typeof pt === 'object') {
            line = '· ' + String(pt.t || '') + (pt.d ? '　' + String(pt.d) : '');
          } else {
            line = '· ' + String(pt == null ? '' : pt);
          }
          return [{ t: line, sz: 12, col: S.body, font: S.font }];
        });
        sh.push(txSp(x8 + 0.18, y8 + 0.14 + cdC.titleH + 0.06, gw2 - 0.36, Math.max(0.4, gh2 - cdC.titleH - 0.34), paras2,
          { lineSpacing: 18 }));
      });
    } else if (type === 'split') {
      /* 双区自由组合页：左区与右区各可为 要点 / 图表 / 表格 / 图片（与 B 通道同语义）。 */
      var SP = PT.split;
      var lRs = regOf('split', 'left', { bottom: bodyBottom }) ||
        { x: MX, y: SP.chartY, w: CW * SP.leftW, h: bodyBottom - SP.chartY };
      var rRs = regOf('split', 'right', { bottom: bodyBottom }) ||
        { x: MX + CW * SP.rightX, y: SP.chartY, w: CW * SP.rightW, h: bodyBottom - SP.chartY };
      var lw2 = lRs.w, rw2 = rRs.w, rxL = rRs.x;
      var lt2 = (sec.left && sec.left.type) || 'points';
      /* 要点区渲染（左右两区共用；与 B 通道同算法同文本） */
      var drawPointsL = function (el, x, w) {
        var ptsP = (el && el.points) || [];
        var lyP = bodyY, availP = bodyBottom - lyP;
        var rowHP = fitRowH(availP, ptsP.length, SP.rowH, 0.3);
        var probeP = [], q5;
        for (q5 = 0; q5 < ptsP.length; q5++) probeP.push(String(ptsP[q5][0] || '') + String(ptsP[q5][1] || ''));
        var fzP = fitFont(probeP, w - 0.4, availP, { max: 14, gapFactor: 0.6 });
        ptsP.forEach(function (pt, i) {
          var ly2 = lyP + i * rowHP;
          sh.push(shape('rect', x, ly2 + rowHP / 2 - 0.06, 0.12, 0.12, S.accent));
          sh.push(txSp(x + 0.28, ly2, w - 0.4, rowHP - 0.04,
            [[{ t: pt[0] + '　', sz: fzP, b: 1, col: S.ink, font: S.font },
              { t: pt[1], sz: snapFont(fzP - 1), col: S.body, font: S.font }]]));
        });
      };
      if (lt2 === 'table') {
        var lhL = [sec.left.head].concat(sec.left.rows);
        var lcwL = sec.left.colW || sec.left.head.map(function () { return lw2 / sec.left.head.length; });
        sh.push(table(lRs.x, SP.tableY, lw2, lcwL, lhL, S, { availH: bodyBottom - SP.tableY, maxRowH: SP.tableRowH, minRowH: 0.3 }));
      } else if (lt2 === 'image') {
        var imL = (sec.left && sec.left.image) || {};
        addImageEl(sh, imL.src, S, lRs.x, SP.chartY, lw2, Math.max(1.4, bodyBottom - SP.chartY),
          { placeholder: !!imL.placeholder || !imL.src, layout: 'half', multi: false, fit: imL.fit });
        if (imL.caption) sh.push(txSp(lRs.x, SP.capY, lw2, 0.35, [[{ t: imL.caption, sz: 11, col: S.faint, font: S.font }]], { align: 'ctr' }));
      } else if (lt2 !== 'points') {
        var lc2 = sec.left;
        chartBlockShapes(sh, lc2, S, lRs.x, SP.chartY, lw2,
          Math.max(1.4, bodyBottom - SP.chartY - (lc2.cap ? 0.1 : 0)),
          lc2.colors || dataColors(model.style, model.theme));
        if (lc2.cap) sh.push(txSp(lRs.x, SP.capY, lw2, 0.35, [[{ t: lc2.cap, sz: 12, col: S.body, font: S.font }]], { align: 'ctr' }));
      } else {
        drawPointsL(sec.left, lRs.x, lw2);
      }
      var rt = (sec.right && sec.right.type) || 'bar';
      if (rt === 'table') {
        var rrL = [sec.right.head].concat(sec.right.rows);
        var rcwL = sec.right.colW || sec.right.head.map(function () { return rw2 / sec.right.head.length; });
        sh.push(table(rxL, SP.tableY, rw2, rcwL, rrL, S, { availH: bodyBottom - SP.tableY, maxRowH: SP.tableRowH, minRowH: 0.3 }));
      } else if (rt === 'image') {
        var im2 = (sec.right && sec.right.image) || {};
        addImageEl(sh, im2.src, S, rxL, SP.chartY, rw2, Math.max(1.4, bodyBottom - SP.chartY),
          { placeholder: !!im2.placeholder || !im2.src, layout: 'half', multi: false });
        if (im2.caption) sh.push(txSp(rxL, SP.capY, rw2, 0.35, [[{ t: im2.caption, sz: 11, col: S.faint, font: S.font }]], { align: 'ctr' }));
      } else if (rt === 'points') {
        drawPointsL(sec.right, rxL, rw2);
      } else {
        var bc2 = sec.right;
        var dcols3 = bc2.colors || dataColors(model.style, model.theme);
        chartBlockShapes(sh, bc2, S, rxL, SP.chartY, rw2, Math.max(1.4, bodyBottom - SP.chartY - (bc2.cap ? 0.1 : 0)), dcols3);
        if (bc2.cap) sh.push(txSp(rxL, SP.capY, rw2, 0.35, [[{ t: bc2.cap, sz: 12, col: S.body, font: S.font }]], { align: 'ctr' }));
      }
    } else if (type === 'diagram') {
      var D = PT.diagram, lys = sec.layers || [];
      var dgR = regOf('diagram', 'primary', { mode: _mode, bottom: bodyBottom }) ||
        { x: MX, y: D.bodyStartY, w: CW, h: bodyBottom - D.bodyStartY };
      var dStart = dgR.y;
      var dEnd = dgR.y + dgR.h;
      var nLay = Math.max(1, lys.length);
      var lh2 = Math.max(0.5, Math.min(D.maxLayerH, (dEnd - dStart) / nLay - D.layerGap));
      lys.forEach(function (lay, li) {
        var y9 = dStart + li * (lh2 + D.layerGap);
        var focus = lay[2] === 'focus';
        sh.push(shape('roundRect', dgR.x, y9, D.layerBarW, lh2, focus ? S.accent : S.surface,
          { adj: 3000, line: focus ? undefined : S.line }));
        sh.push(txSp(dgR.x + 0.1, y9 + 0.1, D.layerBarW - 0.2, lh2 - 0.2, [[{ t: lay[0], sz: 12, b: 1, col: focus ? S.onAccent : S.body, font: S.font }]], { align: 'ctr', anchor: 'ctr' }));
        var nodes = lay[1] || [], nn2 = Math.max(1, nodes.length);
        var availW = dgR.w - D.layerBarW - 0.2;
        var nw2 = Math.min(D.nodeMaxW, (availW - (nn2 - 1) * D.nodeGap) / nn2);
        nodes.forEach(function (nd, ni) {
          var x10 = dgR.x + D.layerBarW + 0.2 + ni * (nw2 + D.nodeGap);
          var ndacc = isRec(nd) ? nd.accent : false;
          var ntt = isRec(nd) ? nd.t : nd;
          var nds = isRec(nd) ? (nd.d || '') : '';
          sh.push(shape('roundRect', x10, y9, nw2, lh2, ndacc ? S.soft : S.surface, { adj: 4000, line: S.line }));
          /* R1: 注解不得「浮回」标题上。标题顶对齐，注解钳在标题下边；空间不足降级单框混排。 */
          var padXn = 0.12, padYn = 0.10;
          var innerWn = nw2 - padXn * 2;
          var titleHn = 0.32, noteHn = 0.34, gapTNn = 0.04;
          var needHn = titleHn + gapTNn + (nds ? noteHn : 0) + padYn * 2;
          if (!nds || lh2 >= needHn) {
            var tYn = y9 + padYn;
            sh.push(txSp(x10 + padXn, nds ? tYn : y9 + lh2 / 2 - 0.18, innerWn, titleHn,
              [[{ t: ntt, sz: nds ? 11 : 12.5, b: 1, col: ndacc ? S.accent : S.ink, font: S.font }]],
              { anchor: 'ctr' }));
            if (nds) {
              var nYn = Math.max(tYn + titleHn + gapTNn, y9 + lh2 - padYn - noteHn);
              sh.push(txSp(x10 + padXn, nYn, innerWn, Math.min(noteHn, y9 + lh2 - padYn - nYn),
                [[{ t: nds, sz: 10, col: S.faint, font: S.font }]], { anchor: 't' }));
            }
          } else {
            sh.push(txSp(x10 + padXn, y9 + padYn * 0.5, innerWn, lh2 - padYn,
              [[{ t: ntt, sz: 11, b: 1, col: ndacc ? S.accent : S.ink, font: S.font }],
               [{ t: nds, sz: 9, col: S.faint, font: S.font }]], { anchor: 't', lineSpacing: 12 }));
          }
        });
        if (li < lys.length - 1) {
          var cy2 = y9 + lh2 + D.layerGap / 2;
          var cxm2 = dgR.x + D.layerBarW / 2;
          sh.push(shape('rect', cxm2 - 0.01, cy2 - 0.1, 0.02, 0.14, focus ? S.accent : S.line));
          sh.push(shape('rect', cxm2 - 0.06, cy2 + 0.04, 0.12, 0.02, focus ? S.accent : S.line));
        }
      });
      if (sec.legend) {
        /* R2：图例进图区底部（与 HTML .arch__legend 同源），禁用 PH-0.62 固定偏移 */
        var lgH2 = 0.28;
        var lgY2 = Math.max(dStart, bodyBottom - lgH2 - 0.02);
        var nLg2 = Math.max(1, sec.legend.length);
        var step2 = Math.min(2.4, CW / nLg2);
        sec.legend.forEach(function (lg2, li2) {
          sh.push(txSp(MX + CW - nLg2 * step2 + li2 * step2, lgY2, step2 - 0.05, lgH2,
            [[{ t: '● ' + lg2, sz: 10, col: S.faint, font: S.font }]]));
        });
      }
    } else if (type === 'exhibit') {
      var eReg = regOf('exhibit', 'primary')
        || { x: MX, y: PT.exhibit.chartY, w: CW, badgeY: PT.exhibit.badgeY };
      if (sec.exhibitNo) {
        sh.push(txSp(MX, eReg.badgeY != null ? eReg.badgeY : PT.exhibit.badgeY, CW, 0.35, [[{ t: exhibitBadge(sec.exhibitNo), sz: 11.5, b: 1, col: S.accent, font: S.font, spc: 200 }]]));
      }
      var ec2 = sec.chart || {};
      if (ec2.labels && ec2.values) {
        var edcols2 = (ec2.colors || dataColors(model.style, model.theme));
        var hh2 = Math.max(1.2, chartBottom(!!sec.soWhat, !!(sec.footnote || sec.note)) - eReg.y - 0.05);
        if (ec2.type === 'hbar') {
          chartBlockShapes(sh, ec2, S, eReg.x, eReg.y, eReg.w, hh2, edcols2);
        } else {
          chartBlockShapes(sh, ec2, S, eReg.x + 0.4, eReg.y - 0.1, eReg.w - 0.8, hh2 + 0.15, edcols2);
        }
      }
    } else if (type === 'sankey' || type === 'treemap' || type === 'boxplot'
      || type === 'network' || type === 'marimekko' || type === 'streamgraph') {
      var infoR = regOf(type, 'primary', { bottom: bodyBottom }) ||
        { x: MX, y: bodyY, w: CW, h: bodyBottom - bodyY };
      infoApprox(sh, sec, S, infoR.y, infoR.y + infoR.h);
    } else {
      /* points（默认）：要点列表 + 可选右侧指标列 */
      var P2 = PT.points, pts3 = sec.points || [];
      var hasM = !!(sec.metrics && sec.metrics.length);
      var ptsR = regOf('points', 'primary', { top: bodyY, bottom: bodyBottom }) ||
        { x: MX, y: bodyY, w: CW, h: bodyBottom - bodyY };
      /* 指标列最多 3 个 + 文本区严格分区（与 build_pptx.js 同算法） */
      var nm2 = hasM ? Math.min(sec.metrics.length, 3) : 0;
      var mw2 = hasM ? Math.min(P2.metricW, Math.max(1.6, (CW - 4.8) / nm2)) : 0;
      var textW = hasM ? Math.max(4.2, (PW - MX - nm2 * mw2) - MX - 0.35) : CW - 0.4;
      var availPt = ptsR.h;
      var rowHPt = fitRowH(availPt, pts3.length, P2.rowH, 0.3);
      var probeP = [], q5;
      for (q5 = 0; q5 < pts3.length; q5++) probeP.push(String(pts3[q5][0] || '') + String(pts3[q5][1] || ''));
      var fzP = fitFont(probeP, textW - 0.32, availPt, { max: 15, gapFactor: 0.55 });
      pts3.forEach(function (p, i) {
        var y11 = ptsR.y + i * rowHPt;
        sh.push(shape('rect', ptsR.x, y11 + rowHPt / 2 - P2.markSize / 2, P2.markSize, P2.markSize, S.accent));
        sh.push(txSp(ptsR.x + 0.32, y11, textW, rowHPt - 0.04,
          [[{ t: p[0] + '　', sz: fzP, b: 1, col: S.ink, font: S.font },
            { t: p[1], sz: snapFont(fzP - 1), col: S.body, font: S.font }]]));
      });
      if (hasM) {
        var gx2 = PW - MX - nm2 * mw2;
        var vSz = nm2 >= 3 ? 28 : 34;
        sec.metrics.slice(0, nm2).forEach(function (m, i) {
          var x12 = gx2 + i * mw2;
          sh.push(txSp(x12, P2.metricY, mw2 - 0.2, P2.metricValH, [[{ t: m[0], sz: vSz, b: 1, col: S.accent, font: S.fontDisplay }]]));
          sh.push(txSp(x12, P2.metricCapY, mw2 - 0.2, 0.9, [[{ t: m[1], sz: 11, col: S.faint, font: S.font }]]));
        });
      }
    }
    /* research 通用可选件：so-what 结论条 + 页脚来源行 + 待核实条（共用同一槽位） */
    /* R2：verdict 已占 annotation 槽位时跳过 soWhat，禁止同槽双条叠印 */
    if (sec.soWhat && !sec.verdict) soWhatBar(sh, sec.soWhat, S);
    /* R2：note 与 footnote 共用注释带末行（禁 note.y=6.55 压 so-what） */
    noteOrFootnote(sh, sec, S);
    if (flagH) flagBar(sh, flagItems, S, flagY);
    slides.push(sh);
  });

  /* 收尾（主题一致强调带——accent-soft 底 + 常规文字，浅色模式不再出深色页） */
  var CL = PT.closing;
  var cl = [shape('rect', 0, 0, PW, PH, S.soft)];
  cl.push(shape('rect', MX, CL.eyebrowY, 0.9, 0.045, S.accent));
  cl.push(txSp(MX, CL.eyebrowY + 0.16, CW, 0.4, [[{ t: '下一步', sz: 13, b: 1, col: S.accent, font: S.font, spc: 200 }]]));
  cl.push(txSp(MX, CL.titleY, CW - 1, CL.titleH, [[{ t: model.closing.title, sz: 30, b: 1, col: S.ink, font: S.fontDisplay }]]));
  var clPts = model.closing.points || [], clN = Math.max(1, clPts.length);
  var clW = (CW - (clN - 1) * 0.3) / clN;
  clPts.forEach(function (p, i) {
    var x13 = MX + i * (clW + 0.3);
    cl.push(shape('roundRect', x13, CL.pointsY - 0.2, clW, CL.pointTitleH + CL.pointBodyH + 0.32, S.surface, { line: S.line, adj: 4000 }));
    cl.push(txSp(x13 + 0.18, CL.pointsY, clW - 0.36, CL.pointTitleH, [[{ t: p[0], sz: 17, b: 1, col: S.accent, font: S.font }]]));
    cl.push(txSp(x13 + 0.18, CL.pointsY + CL.pointTitleH, clW - 0.36, CL.pointBodyH, [[{ t: p[1], sz: 12.5, col: S.body, font: S.font }]]));
  });
  slides.push(cl);

  /* 页码 */
  var total = slides.length;
  slides.forEach(function (sh, i) {
    sh.push(txSp(PW - 1.4, (LAY.pageNumY != null ? LAY.pageNumY : PH - 0.5), 0.9, 0.3,
      [[{ t: (i + 1) + ' / ' + total, sz: 10, col: S.faint, font: S.font }]], { align: 'r' }));
  });
  return slides;
}

/* ── 打包骨架 ── */
var NS = {
  a: 'http://schemas.openxmlformats.org/drawingml/2006/main',
  p: 'http://schemas.openxmlformats.org/presentationml/2006/main',
  r: 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
};
function slideXml(shapes) {
  return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<p:sld xmlns:a="' + NS.a + '" xmlns:p="' + NS.p + '" xmlns:r="' + NS.r + '">' +
    '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>' +
    '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>' +
    shapes.join('') + '</p:spTree></p:cSld><p:clrMapOvr><a:overrideClrMapping bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/></p:clrMapOvr></p:sld>';
}
function relsXml(pairs) {
  var rs = pairs.map(function (p) {
    return '<Relationship Id="' + p[0] + '" Type="' + p[1] + '" Target="' + p[2] + '"/>';
  }).join('');
  return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + rs + '</Relationships>';
}
var RT = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/';

/* 每页 slide XML（预览模态用：与导出同一引擎，所见即所得）
   theme="dark" 时用 PRESETS_DARK（与页面深色主题同源），默认 light */
function themePresets(theme) {
  return (theme === 'dark' && typeof PRESETS_DARK !== 'undefined' &&
          PRESETS_DARK && Object.keys(PRESETS_DARK).length) ? PRESETS_DARK : PRESETS;
}
function slidesXml(model) {
  var S = themePresets(model && model.theme)[model.style] || PRESETS['business-blue'];
  return slidesOf(model, S).map(slideXml);
}

/* ── 模型自检（schema 单源驱动：scripts/model-schema.json 经 sync_runtime 注入的 MODEL_SCHEMA；
      与 scripts/extract_model.py 本地校验同一份定义，双端不漂移） ── */
function schemaGet(obj, path) {
  var cur = obj, ks = path.split('.');
  for (var i = 0; i < ks.length; i++) {
    if (cur == null || typeof cur !== 'object') return undefined;
    cur = cur[ks[i]];
  }
  return cur;
}
function schemaFieldOk(sec, spec) {
  /* 'anyof:a|b:c'（任一满足，用于 image 页型 src/items/placeholder 三选一）；
     'a.b:array' / 'a.b:str' / 'a.b'（真值检查）——与 scripts/extract_model.py 同语义。 */
  if (spec.indexOf('anyof:') === 0) {
    return spec.slice(6).split('|').some(function (alt) { return alt && schemaFieldOk(sec, alt); });
  }
  var m = spec.match(/^(.*?)(?::(array|str))?$/), path = m[1], kind = m[2];
  var v = schemaGet(sec, path);
  if (kind === 'array') return Array.isArray(v) && v.length > 0;
  if (kind === 'str') return typeof v === 'string' && v.trim().length > 0;
  return !!v;
}
/* 图片模型软校验：版式 / 裁切策略 / 多图数量 / 外链 src——与 validate_pptx.py 硬门禁同口径，
   浏览器预览与 extract_model.py 都能提前看到问题。 */
function imageModelWarnings(sec, where, warnings) {
  var IS = (typeof IMG !== 'undefined' && IMG) || {};
  var holders = [{ img: sec.image, at: where + '.image' }];
  if (sec.right && sec.right.image) holders.push({ img: sec.right.image, at: where + '.right.image' });
  holders.forEach(function (h) {
    var img = h.img;
    if (!img || typeof img !== 'object') return;
    var layouts = IS.layouts || ['full', 'half', 'bleed', 'grid', 'compare', 'wall'];
    var fitEnum = IS.fitEnum || ['cover', 'contain'];
    var items = Array.isArray(img.items) ? img.items.filter(Boolean) : [];
    var layout = String(img.layout || (items.length > 1 ? 'grid' : 'full')).toLowerCase();
    if (layouts.indexOf(layout) < 0) {
      warnings.push(h.at + '.layout="' + layout + '" 未知（应为 ' + layouts.join('/') + '）');
    }
    if (img.fit && fitEnum.indexOf(String(img.fit).toLowerCase()) < 0) {
      warnings.push(h.at + '.fit="' + img.fit + '" 未知（应为 ' + fitEnum.join('/') + '）');
    }
    if (img.placeholder && (img.src || items.length)) {
      warnings.push(h.at + ' 同时声明 placeholder 与图片源（placeholder 优先，图片将被忽略）');
    }
    if (items.length > (IS.maxPerPage || 6)) {
      warnings.push(h.at + '.items 共 ' + items.length + ' 张，超出单页上限 ' + (IS.maxPerPage || 6));
    }
    if (layout === 'compare' && items.length && items.length !== 2) {
      warnings.push(h.at + '.items 为 compare 版式时应为 2 张（当前 ' + items.length + '）');
    }
    [img].concat(items).forEach(function (it) {
      if (it && typeof it === 'object' && typeof it.src === 'string' &&
          /^\s*(?:https?:)?\/\//.test(it.src)) {
        warnings.push(h.at + ' 含外链 src（只允许 data: 内联或相对路径）');
      }
    });
  });
}

function validateModel(model) {
  var missing = [], warnings = [];
  var M = (typeof MODEL_SCHEMA !== 'undefined' && MODEL_SCHEMA) || {};
  var pageTypes = M.pageTypes || {};
  if (!model || typeof model !== 'object') {
    return { ok: false, missing: ['window.REPORT_MODEL（内容模型缺失）'], warnings: warnings, pages: 0 };
  }
  (M.model && M.model.required || ['title', 'sections:array', 'closing.title', 'closing.points:array'])
    .forEach(function (spec) {
      if (!schemaFieldOk(model, spec)) missing.push(spec.split(':')[0] + '（顶层必填）');
    });
  var mode = model.mode || 'presentation';
  var hasAgenda = Array.isArray(model.agenda) && model.agenda.length > 0;
  var agMin = (M.model && M.model.agendaMin && M.model.agendaMin[mode]) || 0;
  if (agMin > 0 && (!hasAgenda || model.agenda.length < agMin)) {
    missing.push('agenda（大纲 ≥' + agMin + ' 条）');
  }
  var secs = model.sections || [];
  if (!Array.isArray(secs) || secs.length < ((M.model && M.model.sectionsMin) || 1)) {
    missing.push('sections（章节页 ≥1）');
  }
  if (!model.closing || !model.closing.title) missing.push('closing（收尾页）');
  secs.forEach(function (sec, i) {
    var t = sec.type || 'points';
    var def = pageTypes[t];
    var where = 'sections[' + i + ']';
    if (!def) { missing.push(where + '.type="' + t + '"（未知页型）'); return; }
    if (!sec.title) missing.push(where + '.title（第 ' + (i + 1) + ' 章标题）');
    (def.required || []).forEach(function (spec) {
      if (!schemaFieldOk(sec, spec)) missing.push(where + '.' + spec + '（' + (def.label || t) + '必填）');
    });
    if (def.modes && def.modes.indexOf(mode) < 0) {
      warnings.push('sections[' + i + '] 页型 "' + t + '" 文档口径适用于 ' + def.modes.join('/') + '，当前 mode="' + mode + '"');
    }
    imageModelWarnings(sec, where, warnings);
  });
  if (M.modes && model.mode && M.modes.indexOf(model.mode) < 0) {
    warnings.push('mode="' + model.mode + '" 未知，按 presentation 处理');
  }
  if (model.style && !PRESETS[model.style]) warnings.push('style="' + model.style + '" 未知，回落商务蓝');
  if (model.theme && model.theme !== 'light' && model.theme !== 'dark') {
    warnings.push('theme="' + model.theme + '" 未知（应为 light/dark），按浅色导出');
  }
  if (secs.length < ((M.model && M.model.sectionsRecommended) || 3)) {
    warnings.push('章节页仅 ' + secs.length + ' 页，正式报告建议 ≥3');
  }
  var agMax = (M.model && M.model.agendaComfortMax) || 16;
  if ((model.agenda || []).length > agMax) {
    warnings.push('agenda ' + model.agenda.length + ' 条超出单页舒适上限 ' + agMax + '，将自动分页');
  }
  var agPageCount = hasAgenda ? Math.ceil(model.agenda.length / 12) : 0;
  var pages = 1 + agPageCount + secs.length + 1;   /* 封面+大纲(可多页)+章节+收尾 */
  return { ok: missing.length === 0, missing: missing, warnings: warnings, pages: pages };
}

var api = {
  slidesXml: slidesXml,
  validateModel: validateModel,
  /* 以下供 scripts/gen_channel_a.js 在 Node 侧组装完整 PPTX 包（回归双裁判内部质量路径） */
  slidesOf: slidesOf, slideXml: slideXml, relsXml: relsXml, NS: NS, RT: RT, PRESETS: PRESETS,
  PRESETS_DARK: (typeof PRESETS_DARK !== 'undefined' ? PRESETS_DARK : null),
  dataColors: dataColors,
  esc: esc, solid: solid, E: E
};
if (typeof module !== 'undefined' && module.exports) module.exports = api; /* Node：gen_channel_a.js 用 */
g.TopPptHtml = api;
})(typeof window !== 'undefined' ? window : globalThis);
