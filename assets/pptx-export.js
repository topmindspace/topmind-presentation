/* ═══════════════════════════════════════════════════════════════════════════
 * topmind-presentation · 浏览器端 PPTX 页序运行时（M2 起：只做模型自检与页序计划，不再画几何）
 * 零依赖、随报告单文件分发。
 *
 * 定位：HTML 是阅读与演示界面，PPTX 是协作与修改格式——两者来自同一内容模型
 * （window.REPORT_MODEL）。M2 之前这里有一套 2000 行的浏览器端 OOXML 几何序列化器，
 * 与服务端 build_pptx.js 各算各的坐标，长期漂移（同一页两端版式不同）。M2 删除该第二引擎：
 *   · 版式几何只有一个实现：scripts/build_pptx.js（原生可编辑图表 + strict 门禁）；
 *   · 浏览器端只保留「同源」的部分：schema 自检 + 布局求解器（容量 / 拆页，与服务端同一份
 *     scripts/lib_solver.js 注入）→ 得到与 PPTX 完全一致的页序计划；
 *   · 预览模态展示页序计划，并直接用页面上对应的 HTML 幻灯片做缩略图（所见即同源内容）。
 *
 * API：
 *   TopPptHtml.validateModel(model) → {ok, missing[], warnings[], pages}（schema 单源驱动，含容量拆页）
 *   TopPptHtml.pagePlan(model)      → [{kind: cover|agenda|section|closing, type, title, cont}]
 *   TopPptHtml.solver               → lib_solver（rows / fitUp / capacity / splitModel / grid12）
 *
 * ★ 单源机制（scripts/sync_runtime.py 注入，标记块内禁止手改）：
 *   - 版式常量：scripts/layout-constants.json → __TOPPPT_CONSTANTS__ 块
 *   - DSL schema：scripts/model-schema.json → __TOPPPT_SCHEMA__ 块
 *   - 布局求解器：scripts/lib_solver.js → __TOPPPT_SOLVER__ 块
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
/* STYLE_DATA_COLORS(_DARK) = 12 套风格各自的编码色板 c1–c5（数据系列；结构色纪律不变） */
/* LAYOUT_SLOTS + regionOf = 页型布局区域 IR（与 scripts/lib_layout_regions.js 同源） */
var PW = 13.333, PH = 7.5, MX = 0.6, CW = PW - 2 * MX, EMU = 914400;
var TS_BASE = {"coverTitle":44,"coverSub":18,"h1":30,"h2":17,"lead":14,"body":13,"caption":11,"micro":10};
var MTS = {"presentation":{"coverTitle":44,"coverSub":18,"h1":32,"h2":17,"lead":14,"body":13,"caption":11,"micro":10,"chapterNum":96,"chapterTitle":32,"kpiCard":24,"kpiHero":36,"stepTitle":22,"coverHero":52},"research":{"coverTitle":44,"coverSub":14,"h1":24,"h2":15,"lead":12.5,"body":11.5,"caption":10.5,"micro":9.5,"chapterNum":80,"chapterTitle":34,"kpiCard":22,"kpiHero":34,"stepTitle":16,"coverHero":48},"architecture":{"coverTitle":44,"coverSub":19,"h1":32,"h2":17,"lead":14,"body":13,"caption":11,"micro":10,"chapterNum":96,"chapterTitle":32,"kpiCard":24,"kpiHero":36,"stepTitle":22,"coverHero":52}};
var PT = {"layout":{"contentTop":2.35,"contentBottom":6.9,"contentBottomWithNote":6.4,"pageNumY":7.0},"common":{"headEyebrowY":0.48,"headTitleY":0.82,"headRuleY":1.72,"leadY":1.88,"bodyY":2.35,"bodyYWithLead":2.55,"pagerY":7.0},"cover":{"metaY":0.7,"titleY":2.4,"titleH":2.0,"subtitleY":4.5,"subtitleH":0.8},"closing":{"eyebrowY":0.7,"titleY":1.2,"titleH":1.2,"pointsY":3.0,"pointTitleH":0.6,"pointBodyH":1.2},"points":{"listY":2.5,"rowH":0.72,"rowHMin":0.5,"markSize":0.14,"metricY":4.7,"metricW":2.6,"metricValH":0.9,"metricCapY":5.6},"metrics":{"bandY":3.1,"cardH":2.3,"valY":3.45,"valH":1.1,"capY":4.55,"capH":0.7,"gap":0.3,"maxW":2.9},"table":{"y":2.5,"rowH":0.55,"rowHMin":0.32,"headRowH":0.5},"bar":{"hbarY0":2.6,"hbarY1":6.25,"chartX":0.6,"chartY":2.95,"chartW":1.2,"chartH":3.35,"noteY":6.55},"note":{"y":6.55,"h":0.4},"exhibit":{"badgeY":2.35,"chartY":2.75,"chartH":3.25,"soWhatY":6.05,"footnoteY":6.72},"twocol":{"colGap":0.5,"bodyH":3.6,"rowHMin":0.5},"hbar":{"labelW":1.9,"valW":1.0,"rowH":0.55,"barRatio":0.5},"diagram":{"layerBarW":1.35,"layerGap":0.15,"nodeGap":0.15,"bodyStartY":2.9,"maxLayerH":1.15,"nodeMaxW":2.2},"split":{"leftW":0.55,"rightW":0.415,"rightX":0.585,"pointsY":2.7,"rowH":0.78,"capY":2.55,"chartY":3.0,"chartH":3.7,"tableY":2.7,"tableRowH":0.5},"cards":{"startY":3.0,"gap":0.25,"maxH":2.0,"titleH":0.4},"timeline":{"labelY":2.95,"axisY":3.58,"dotY":3.51,"dotR":0.18,"nameY":3.9,"descY":4.45,"descH":1.2},"research":{"col3Gap":0.38,"matrixLabelW":1.5,"matrixCellH":0.85,"matrixY":2.2,"denseTableY":2.2,"denseRowH":0.42,"halfTableW":0.52,"halfChartX":0.57,"halfChartW":0.43},"arch":{"fullStartY":2.1,"fullEndY":6.9,"laneH":0.72,"laneHMin":0.5,"laneGap":0.14,"laneHeadW":1.3,"stepGap":0.12,"stepMaxW":1.9},"kpi":{"heroY":2.9,"heroW":0.52,"heroH":1.6,"dividerX":0.56,"metricY0":2.95,"metricRowH":0.85},"comparison":{"panelGap":0.4,"panelY":2.55,"panelH":3.4,"titleH":0.45,"rowH":0.62},"quote":{"markY":1.75,"textY":2.7,"textH":2.3,"authorY":5.25,"contextY":5.8},"donut":{"centerX":3.05,"centerY":4.6,"r":1.6,"holeR":0.95,"legendX":5.6,"legendRowH":0.55,"legendLabelW":3.4,"legendValW":1.3,"legendPctX":10.8,"legendPctW":1.3},"steps":{"y":3.05,"barH":1.35,"gap":0.12,"arrowW":0.3,"numH":0.3,"titleH":0.34,"pad":0.08,"maxPerRow":6},"heatmap":{"y":2.6,"labelW":1.7,"headH":0.42,"cellH":0.6,"cellGap":0.06,"legendW":1.6},"pyramid":{"y":2.35,"rowH":0.72,"gap":0.08,"minW":0.34,"labelW":3.2},"bullet":{"y":2.6,"rowH":0.8,"labelW":2.4,"valW":1.7,"barH":0.26},"image":{"y":2.3,"h":4.2,"halfW":0.56,"halfGap":0.06,"capY":6.6,"capH":0.3,"radius":0.09,"noteRowH":0.62,"gridGap":0.16,"gridCols":{"2":2,"3":3,"4":4,"6":3},"gridCapH":0.28,"compareGap":0.3,"compareTagH":0.26,"wallCellH":0.92,"wallGap":0.18,"wallMaxRows":2},"flagbar":{"hdH":0.26,"rowH":0.24,"maxRows":3,"gap":0.12},"sankey":{"y":2.45,"h":4.1,"nodeW":0.32,"nodeGap":0.14,"labelW":1.55,"minBandH":0.22,"maxNodes":12,"maxFlows":24},"treemap":{"y":2.45,"h":4.1,"gap":0.05,"labelMinH":0.34,"maxLeaves":16,"maxDepth":3},"boxplot":{"y":2.7,"h":3.7,"labelW":1.5,"groupGap":0.3,"boxMaxW":0.9,"whiskerCapW":0.34,"maxGroups":8},"network":{"y":2.4,"h":4.2,"nodeR":0.28,"nodeRMin":0.18,"labelMaxW":1.4,"maxNodes":18,"maxEdges":30},"marimekko":{"y":2.6,"h":3.75,"labelW":1.55,"colGap":0.06,"legendH":0.42,"maxCols":6,"maxSegs":4},"streamgraph":{"y":2.6,"h":3.75,"labelW":1.4,"bandMinH":0.12,"maxSeries":6},"chapter":{"numW":3.6,"numY":1.15,"titleY":1.72,"itemRowH":0.5,"maxItems":5}};
var PRESETS = {
  'business-blue': { accent:'1A73E8', ink:'202124', body:'5F6368', faint:'80868B', bg:'FFFFFF', surface:'F8F9FA', line:'DADCE0', soft:'E8F0FE', onAccent:'FFFFFF', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'apple-mono': { accent:'1D1D1F', ink:'1D1D1F', body:'6E6E73', faint:'86868B', bg:'FFFFFF', surface:'F5F5F7', line:'D2D2D7', soft:'F5F5F7', onAccent:'FFFFFF', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'mckinsey': { accent:'003A70', ink:'101828', body:'475467', faint:'667085', bg:'FFFFFF', surface:'F2F4F7', line:'D0D5DD', soft:'EEF4FB', onAccent:'FFFFFF', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'brand-red': { accent:'D0021B', ink:'1F1A1B', body:'5D5456', faint:'8A8083', bg:'FFFFFF', surface:'FAF7F7', line:'E2D9DA', soft:'FBECEC', onAccent:'FFFFFF', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'warm-sand': { accent:'96681F', ink:'2A2521', body:'6B5F52', faint:'93836F', bg:'FBF9F6', surface:'F6F2EC', line:'E0D7C9', soft:'F3ECDD', onAccent:'FFFFFF', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'deep-teal': { accent:'0F6B5C', ink:'14201E', body:'4A5A57', faint:'73837F', bg:'FFFFFF', surface:'F2F6F5', line:'CFDEDC', soft:'E4F1EE', onAccent:'FFFFFF', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'graphite-dark': { accent:'0369A1', ink:'1A1D21', body:'4B5158', faint:'767C84', bg:'F4F5F7', surface:'ECEEF1', line:'CED1D6', soft:'E2EFF7', onAccent:'FFFFFF', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'indigo-violet': { accent:'5B5BD6', ink:'1B1A2E', body:'52506B', faint:'7A779A', bg:'FFFFFF', surface:'F4F4FB', line:'D7D7E8', soft:'ECECF9', onAccent:'FFFFFF', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'spectrum': { accent:'4563EF', ink:'171A21', body:'4D5566', faint:'7B8494', bg:'FBFCFE', surface:'F4F6FA', line:'D6DCE6', soft:'ECEEFF', onAccent:'FFFFFF', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'ink-academic': { accent:'1F3A5F', ink:'14181F', body:'454D59', faint:'6B7380', bg:'FFFFFF', surface:'F4F6F9', line:'D5DAE1', soft:'E9EEF5', onAccent:'FFFFFF', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'coral-launch': { accent:'C4402A', ink:'1E1A19', body:'5A5250', faint:'857C79', bg:'FFFFFF', surface:'FBF6F5', line:'EADFDC', soft:'FDEDEA', onAccent:'FFFFFF', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'sky-airy': { accent:'0B7BC4', ink:'0F1D2A', body:'4A5968', faint:'73818F', bg:'FFFFFF', surface:'F3F8FC', line:'D6E4EF', soft:'E3F1FB', onAccent:'FFFFFF', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' }
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
  'spectrum': { accent:'8BA0F8', ink:'E8EBF2', body:'A7AFBF', faint:'7E8798', bg:'0E1116', surface:'171C26', line:'2B3342', soft:'1B2242', onAccent:'141A38', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'ink-academic': { accent:'9DB8DC', ink:'E6E9EE', body:'B3BAC5', faint:'8A929E', bg:'0E1117', surface:'151A22', line:'2B323D', soft:'18243A', onAccent:'0E1626', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'coral-launch': { accent:'FF8A73', ink:'F3ECEA', body:'C9BCB8', faint:'9C908C', bg:'141010', surface:'1C1615', line:'3A2D2A', soft:'3A1E18', onAccent:'2A0F0A', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' },
  'sky-airy': { accent:'7CC4F2', ink:'E6EEF5', body:'B0C0CE', faint:'8797A6', bg:'0C1218', surface:'121A22', line:'26343F', soft:'12293A', onAccent:'0A1E2C', font:'Microsoft YaHei', fontDisplay:'Microsoft YaHei' }
};
var STYLE_DATA_COLORS = {"business-blue":["1a73e8","3526bb","21a199","b77148","99983d"],"apple-mono":["1d1d1f","0071e3","0f7b6c","c2410c","7c3aed"],"mckinsey":["003a70","2826bb","21a18e","b76848","99903d"],"brand-red":["d0021b","bb6326","d634ae","40a182","438aa8"],"warm-sand":["96681f","839324","cf3b3e","4d88b2","4a47a4"],"deep-teal":["0f6b5c","2683bb","22aa3e","b74870","a85c43"],"graphite-dark":["0369a1","2637bb","1f9977","b75948","a18a40"],"indigo-violet":["5b5bd6","7432ae","4197c8","a08f4b","7ca04b"],"spectrum":["4563ef","5b26bb","269ebb","af8746","83993d"],"ink-academic":["1f3a5f","4f7cac","8a6d3b","6b8f71","9a5b6f"],"coral-launch":["c4402a","2f6fde","c27a12","2aa39a","7b5bd6"],"sky-airy":["0b7bc4","16a37f","c4720f","8d6ad9","d9577c"]};
var STYLE_DATA_COLORS_DARK = {"business-blue":["8ab4f8","7966e0","88e7e5","d4ad91","cbce83"],"apple-mono":["f5f5f7","2997ff","2dd4bf","ff9f0a","bf5af2"],"mckinsey":["7fb2e5","6f6bdb","8ce3d8","d1a694","cbc586"],"brand-red":["ff5a66","e09e66","e788cb","91d4c2","83b4ce"],"warm-sand":["d9b36a","c2d571","df9391","97b5ce","8e89c7"],"deep-teal":["4fc3b0","7aaecd","97d8a4","c99cac","c29c8f"],"graphite-dark":["4da3ff","6c66e0","88e7dc","d4a691","cec983"],"indigo-violet":["a5a4f0","a967e0","89c3e7","d3c792","aece83"],"spectrum":["8ba0f8","9066e0","88d6e7","d4ba91","bdce83"],"ink-academic":["9db8dc","7fc4b8","c9ad7d","9fc0a4","c995a6"],"coral-launch":["ff8a73","86aaf0","e6d27a","6fd1c8","ab97ea"],"sky-airy":["7cc4f2","6fd4b6","f7bf7f","b6a1ea","eb98b0"]};
var GRID = {"columns":12,"gutter":0.16,"colW":0.8644,"x":[0.6,1.6244,2.6488,3.6732,4.6976,5.722,6.7464,7.7708,8.7952,9.8196,10.844,11.8684,12.733],"y":[2.35,3.27,4.19,5.11,6.03,6.9],"safe":{"top":0.4,"bottom":0.4,"left":0.6,"right":0.6}};
var TYPO = {"levels":[{"id":"C0","name":"封面/章节幕标题","role":"coverTitle","usage":"封面主标题、章节幕标题"},{"id":"T1","name":"页码/章节徽章","role":"caption","usage":"页码徽章、章节编号"},{"id":"T2","name":"页面主标题/结论标题","role":"h1","usage":"每页顶部结论句（research 行动标题）"},{"id":"T3","name":"副标题/语境说明","role":"lead","usage":"主标题下方导语"},{"id":"T4","name":"模块标题/图表标题","role":"h2","usage":"卡片标题、图表标题、面板标题"},{"id":"T5","name":"证据编号/轻量标签","role":"micro","usage":"Exhibit 编号、状态标签"},{"id":"T6","name":"证据块标题/小节标题","role":"h2","usage":"分栏小标题、证据块标题"},{"id":"T7","name":"正文解释段落","role":"body","usage":"证据解释、管理解读正文、表格正文"},{"id":"T8","name":"结论条文字","role":"body","usage":"结论条、核心结论框"},{"id":"T9","name":"结论条标签（可选·默认隐藏）","role":"caption","usage":"结论条可选标签（默认不显示）"},{"id":"T10","name":"结论条正文/业务含义","role":"body","usage":"结论条正文、行动含义、表格行动项"},{"id":"T11","name":"图表轴/图例/刻度/微标签","role":"micro","usage":"坐标轴、图例、刻度、单位（禁用于表格正文与完整短句）"},{"id":"T12","name":"图表数据标签","role":"caption","usage":"折线点值、柱形标签、百分比标注"},{"id":"T13","name":"关键 KPI 大数字","role":"h1","usage":"KPI 大数字、hero 数值"},{"id":"T14","name":"注释/口径/来源/页脚","role":"micro","usage":"footnote、来源行、页脚、小页码"}],"tableSemanticRule":{"body":["T7","T10"],"microAllowed":["T11"],"microForbiddenFor":["表格正文","行动项","风险项","解释句","建议句","长项目符号","完整短句"]}};
var CONT = {"pad":{"card":0.18,"panel":0.2,"cell":0.08,"band":0.16,"soWhat":0.16,"kpi":0.18,"chart":0.1,"head":0.05,"footer":0.05,"node":0.06},"minPad":0.06,"textMetrics":{"lineFactor":1.45,"emAsciiRatio":0.52},"overflowRule":"溢出处置优先级（禁静默截断）：① 重构承载（列表/卡片/表/图/组合版式）→ ② 拆页/分章（议程→主张→证据卡→明细；01a/01b；信息须完整）→ ③ 换布局形态（V1–V4/多列/卡栅格）→ ④ 有限 fontShrink（阶梯内、模式 floor 以上、最多 4 档）→ ⑤ 禁止：静默截断、砍 so-what/证据/口径、为审美稀疏删决策必需信息。单页字数预算是预警不是删字许可证。","fontShrink":{"ladder":[15,14,13.5,13,12.5,12,11.5,11,10.5,10,9.5,9,8.5],"maxShrinkSteps":4,"floorPt":{"presentation":10,"research":9,"architecture":10},"preferContentFirst":true,"warnBelow":9.5},"continuousTextRule":"语义连续的一句话 / so-what 主句 / 结论句 / 表格单元格正文不得拆成多个独立文本框（避免异常空格、断句、基线漂移）；局部加粗高亮必须用同一文本框内富文本。","adaptiveText":{"title":{"base":30,"step1":24,"longChars":28,"longMax":24,"xlongChars":44,"xlongMax":20},"list":{"denseItems":6,"gapFactor":0.5,"denseGapFactor":0.25,"lineFactor":1.45,"denseLineFactor":1.3,"max":14,"denseMax":12},"table":{"cellMax":12.5,"cellFloor":9,"headMax":13,"longCellChars":24,"rowFloorIn":0.22,"cellPadIn":0.07}}};
var REG = {"bar":{"html":"svg-bars","pptx":"native","nativeType":"bar","dataTable":"notes","min":{"vbHeightMin":160}},"hbar":{"html":"svg-hbars","pptx":"native","nativeType":"bar","dataTable":"notes","min":{"vbHeightMin":100}},"stack":{"html":"svg-stack","pptx":"native","nativeType":"bar","dataTable":"notes","min":{"vbHeightMin":160},"nativeOpt":{"barGrouping":"stacked"}},"stackline":{"html":"svg-stackline","pptx":"native","nativeType":"bar","dataTable":"notes","min":{"vbHeightMin":40},"nativeOpt":{"barGrouping":"percentStacked"}},"line":{"html":"svg-line","pptx":"native","nativeType":"line","dataTable":"notes","min":{"vbHeightMin":160}},"dualline":{"html":"svg-dualline","pptx":"native","nativeType":"line","dataTable":"notes","min":{"vbHeightMin":160}},"area":{"html":"svg-area","pptx":"native","nativeType":"area","dataTable":"notes","min":{"vbHeightMin":160}},"donut":{"html":"svg-donut","pptx":"native","nativeType":"doughnut","dataTable":"notes","min":{"pxWidthMin":140}},"multidonut":{"html":"svg-mdonut","pptx":"native","nativeType":"doughnut","dataTable":"notes","min":{"pxWidthMin":140}},"pie":{"html":"svg-pie","pptx":"native","nativeType":"pie","dataTable":"notes","min":{"pxWidthMin":140}},"radar":{"html":"svg-radar","pptx":"native","nativeType":"radar","dataTable":"notes","min":{"pxWidthMin":220}},"scatter":{"html":"svg-scatter","pptx":"native","nativeType":"scatter","dataTable":"notes","min":{"vbHeightMin":180}},"bubble":{"html":"svg-bubble","pptx":"native","nativeType":"bubble","dataTable":"notes","min":{"vbHeightMin":180}},"waterfall":{"html":"svg-wf","pptx":"native","nativeType":"bar","dataTable":"notes","min":{"vbHeightMin":170},"nativeTrick":"stacked+hiddenBase+connector"},"gauge":{"html":"svg-gauge","pptx":"native","nativeType":"doughnut","dataTable":"notes","min":{"pxWidthMin":180},"nativeTrick":"doughnut+firstSliceAng+hiddenRemainder"},"pareto":{"html":"svg-pareto","pptx":"native","nativeType":"bar","dataTable":"notes","min":{"vbHeightMin":180},"nativeTrick":"multiType+bar+line"},"gantt":{"html":"svg-gantt","pptx":"native","dataTable":"notes","min":{"vbHeightMin":130},"nativeType":"bar","nativeTrick":"rows:gantt"},"vsbar":{"html":"svg-vsbar","pptx":"native","dataTable":"notes","min":{"vbHeightMin":100},"nativeType":"bar","nativeTrick":"rows:vsbar"},"progress":{"html":"svg-progress","pptx":"native","dataTable":"notes","min":{"vbHeightMin":100},"nativeType":"bar","nativeTrick":"rows:progress"},"sparkline":{"html":"svg-spark","pptx":"shape","dataTable":"off","min":{"vbHeightMin":20},"path":{"forbidPresetShapes":true}},"funnel":{"html":"svg-funnel","pptx":"native","dataTable":"notes","min":{"vbHeightMin":160},"nativeType":"bar","nativeTrick":"rows:funnel"},"treemap":{"html":"svg-treemap","pptx":"shape","dataTable":"appendix","min":{"vbHeightMin":170},"path":{"forbidPresetShapes":true}},"marimekko":{"html":"svg-marimekko","pptx":"shape","dataTable":"appendix","min":{"vbHeightMin":160},"path":{"forbidPresetShapes":true}},"boxplot":{"html":"svg-boxplot","pptx":"shape","dataTable":"appendix","min":{"vbHeightMin":180},"path":{"forbidPresetShapes":true}},"network":{"html":"svg-network","pptx":"shape","dataTable":"appendix","min":{"vbHeightMin":200},"path":{"forbidPresetShapes":true}},"sankey":{"html":"svg-sankey","pptx":"shape","dataTable":"appendix","min":{"vbHeightMin":200},"path":{"minSamplePoints":16,"trackBothEdges":true,"forbidPresetShapes":true}},"streamgraph":{"html":"svg-stream","pptx":"shape","dataTable":"appendix","min":{"vbHeightMin":160},"path":{"minSamplePoints":24,"trackBothEdges":true,"forbidPresetShapes":true}},"slope":{"html":"svg-slope","pptx":"shape","dataTable":"notes","min":{"vbHeightMin":180},"path":{"forbidPresetShapes":true}},"dumbbell":{"html":"svg-dumbbell","pptx":"shape","dataTable":"notes","min":{"vbHeightMin":160},"path":{"forbidPresetShapes":true}},"lollipop":{"html":"svg-lollipop","pptx":"shape","dataTable":"notes","min":{"vbHeightMin":140},"path":{"forbidPresetShapes":true}},"dotplot":{"html":"svg-dotplot","pptx":"shape","dataTable":"notes","min":{"vbHeightMin":120},"path":{"forbidPresetShapes":true}},"bulletchart":{"html":"svg-bullet","pptx":"shape","dataTable":"notes","min":{"vbHeightMin":140},"path":{"forbidPresetShapes":true}},"waffle":{"html":"svg-waffle","pptx":"shape","dataTable":"notes","min":{"vbHeightMin":160},"path":{"forbidPresetShapes":true}},"radialbar":{"html":"svg-radialbar","pptx":"shape","dataTable":"notes","min":{"pxWidthMin":200},"path":{"minSamplePoints":16,"forbidPresetShapes":true}},"rose":{"html":"svg-rose","pptx":"shape","dataTable":"notes","min":{"pxWidthMin":180},"path":{"minSamplePoints":16,"forbidPresetShapes":true}},"candlestick":{"html":"svg-candle","pptx":"shape","dataTable":"appendix","min":{"vbHeightMin":180},"path":{"forbidPresetShapes":true}}};
var DEEP = {"triggers":["高保真","1:1","一比一","精确还原","按图还原","正式交付","不能偏移","像素级","严格对照","逐页验收"],"complexCharts":["sankey","streamgraph","treemap","marimekko","boxplot","network","rose","radialbar","candlestick","funnel"],"checks":{"anchors":true,"containerOverflow":true,"renderCompare":true,"manifest":true},"renderCompare":{"engine":"soffice","fallback":"powerpoint-com","skipIfMissing":true,"dpi":96}};
var IMG = {"layouts":["full","half","bleed","grid","compare","wall"],"multiLayouts":["grid","compare","wall"],"fitEnum":["cover","contain"],"fitDefault":"cover","formats":["png","jpeg","jpg","webp","svg"],"ratioDefault":{"full":"3:1","half":"4:3","bleed":"21:9","grid":"4:3","compare":"4:3","wall":"1:1"},"ratioCssClass":{"full":"media--r3-1","half":"media--r4-3","bleed":"media--r21-9","grid":"media--r4-3","compare":"media--r4-3","wall":"media--r1-1"},"recommendedSizePx":{"full":"2400×800","half":"1400×1050","bleed":"2560×1100","grid":"900×675","compare":"1400×1050","wall":"480×480"},"maxInlineBytes":1572864,"maxTotalInlineBytes":8388608,"maxPerPage":6,"placeholderLabel":"配图占位","placeholderHintPrefix":"建议 ","placeholderHintSuffix":"px","zeroExternal":true,"qualityRule":"位图优先提供 ≥2× 显示尺寸；截图用 16:9 或 4:3 锁定比例；数据图不要用截图（应用内联 SVG 图表，可随主题变色）。"};
var LAYOUT_SLOTS = {"version":"0.1","pageTypes":{"points":{"mode":["presentation","research","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".grid.g-2 / .card / .ul","pptx":"points columns","minUnits":1},{"id":"annotation","role":"annotation","required":false,"html":".sowhat / .note","pptx":"soWhatBar / footnoteLine"}]},"metrics":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".metric","pptx":"metric row","minUnits":4},{"id":"annotation","role":"annotation","required":false,"html":"口径行 / .sowhat","pptx":"footnoteLine / soWhatBar"}]},"kpi":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"hero","role":"primary","required":true,"html":".t-metric hero","pptx":"hero number"},{"id":"metrics","role":"secondary","required":false,"html":".metric","pptx":"support metrics"},{"id":"annotation","role":"annotation","required":false,"html":".sowhat / .note","pptx":"soWhatBar"}]},"exhibit":{"mode":["research","presentation"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead / .exhibit__hd","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"svg[data-chart] / .exhibit","pptx":"nativeChart | shapeChart","channel":"registry"},{"id":"secondary","role":"secondary","required":false,"html":"要点列表","pptx":"side bullets"},{"id":"annotation","role":"annotation","required":true,"html":".exhibit__src / .sowhat","pptx":"footnoteLine / soWhatBar / notes"}]},"split":{"mode":["presentation","research","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"left","role":"primary","required":true,"html":"左区（points/table/image/chart）","pptx":"left zone"},{"id":"right","role":"secondary","required":true,"html":"右区（points/table/image/chart）","pptx":"right zone"},{"id":"annotation","role":"annotation","required":false,"html":".sowhat / .note","pptx":"soWhatBar"}]},"table":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".tbl-wrap table","pptx":"addTable","maxRows":{"presentation":8,"research":16}},{"id":"annotation","role":"annotation","required":false,"html":".sowhat / .note","pptx":"soWhatBar / footnoteLine"}]},"bar":{"mode":["presentation","research","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"svg[data-chart]","pptx":"nativeChart | shapeChart","channel":"registry"},{"id":"annotation","role":"annotation","required":true,"html":"note / dataTable","pptx":"footnoteLine / notes / inline table"}]},"donut":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"svg[data-chart=donut]","pptx":"addChart doughnut"},{"id":"annotation","role":"annotation","required":false,"html":"中心合计 / 图例 / .note","pptx":"center label / legend / notes"}]},"twocol":{"mode":["research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".cols-2","pptx":"two text columns"},{"id":"annotation","role":"annotation","required":false,"html":".sowhat","pptx":"soWhatBar"}]},"threecol":{"mode":["research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".cols-3","pptx":"three text columns"},{"id":"annotation","role":"annotation","required":false,"html":".sowhat","pptx":"soWhatBar"}]},"halftable":{"mode":["research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"左表","pptx":"addTable left"},{"id":"secondary","role":"secondary","required":true,"html":"右图","pptx":"chart right"},{"id":"annotation","role":"annotation","required":false,"html":".sowhat","pptx":"soWhatBar"}]},"matrix":{"mode":["research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".matrix","pptx":"matrix cells"},{"id":"annotation","role":"annotation","required":false,"html":".sowhat","pptx":"soWhatBar"}]},"comparison":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"left","role":"primary","required":true,"html":"左面板","pptx":"left panel"},{"id":"right","role":"secondary","required":true,"html":"右面板","pptx":"right panel"},{"id":"annotation","role":"annotation","required":false,"html":"verdict / .sowhat","pptx":"verdict bar"}]},"quote":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"金句正文","pptx":"quote text"}]},"timeline":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".tl","pptx":"timeline axis"}]},"steps":{"mode":["presentation","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".steps","pptx":"step row"}]},"cards":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".card grid","pptx":"card grid"}]},"heatmap":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".heat","pptx":"heat cells"}]},"bullet":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".bul","pptx":"bullet rows"}]},"pyramid":{"mode":["presentation","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".pyr","pptx":"pyramid layers"}]},"image":{"mode":["presentation","research","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".media*","pptx":"imageLayoutShapes"}]},"diagram":{"mode":["architecture","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".arch / layers","pptx":"layered nodes + edges","maxNodes":24,"maxLayers":4},{"id":"annotation","role":"annotation","required":false,"html":".arch__legend / .note","pptx":"legend chips / notes"}]},"lane":{"mode":["architecture","research"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":".lane","pptx":"lanes + steps"}]},"sankey":{"mode":["research","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"svg[data-chart=sankey]","pptx":"infoSankey","maxNodes":12},{"id":"annotation","role":"annotation","required":true,"html":"dataTable / .note","pptx":"notes"}]},"treemap":{"mode":["research","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"svg[data-chart=treemap]","pptx":"infoTreemap"},{"id":"annotation","role":"annotation","required":true,"html":"dataTable / .note","pptx":"notes"}]},"boxplot":{"mode":["research","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"svg[data-chart=boxplot]","pptx":"infoBoxplot"},{"id":"annotation","role":"annotation","required":true,"html":"dataTable / .note","pptx":"notes"}]},"network":{"mode":["research","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"svg[data-chart=network]","pptx":"infoNetwork"},{"id":"annotation","role":"annotation","required":true,"html":"dataTable / .note","pptx":"notes"}]},"marimekko":{"mode":["research","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"svg[data-chart=marimekko]","pptx":"infoMarimekko"},{"id":"annotation","role":"annotation","required":true,"html":"dataTable / .note","pptx":"notes"}]},"streamgraph":{"mode":["research","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".shead","pptx":"head()"},{"id":"primary","role":"primary","required":true,"html":"svg[data-chart=streamgraph]","pptx":"infoStreamgraph"},{"id":"annotation","role":"annotation","required":true,"html":"dataTable / .note","pptx":"notes"}]},"chapter":{"mode":["presentation","research","architecture"],"slots":[{"id":"head","role":"chrome","required":true,"html":".chap__body .t-eyebrow + h2","pptx":"chapter title"},{"id":"primary","role":"primary","required":true,"html":".chap__no","pptx":"chapter number"},{"id":"secondary","role":"secondary","required":false,"html":".chap__list","pptx":"chapter items"}]}}};

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
var MODEL_SCHEMA = {"version":"0.1","modes":["presentation","research","architecture"],"model":{"required":["title","sections:array","closing.title","closing.points:array"],"optional":["mode","style","theme","subtitle","meta","agenda:array","agendaTitle","agendaEyebrow","contentLocked","coverNotes","agendaNotes"],"agendaMin":{"presentation":3,"research":3,"architecture":0},"agendaMax":7,"agendaMaxWithRefs":8,"agendaHint":"agenda 条目 = 章（篇/section），3–7 条；每章可含多页（sections[] 按页建模）。禁止把逐页标题当大纲。sections[].eyebrow 的 `NN ·` 前缀 = 章键，须与某条 agenda 对应；跳转锚点 = 该章第一页。含「参考资料」条目时 +1 仍 ≤8。","sectionsMin":1,"sectionsRecommended":3,"agendaComfortMax":8},"commonSectionFields":["eyebrow","title","lead","soWhat","footnote","note","flags","image","exhibitNo","layoutPreset","variant","anchor","cap","source","highlightCol","sourceSlide","speakerNotes"],"mutualExclusionHint":"verdict 与 soWhat 互斥：二者共用 annotation 结论条槽位，同页双填必叠印。comparison 页填 verdict 时不要再填 soWhat（渲染器已自动二选一，但模型侧应只给一个）。","flagsHint":"flags = 待核实/待二次修改条目字符串数组（如 '2027 增速 xx%（口径未定）'）；渲染为 accent 强调色标注行，提示用户核对。","imageHint":"image = 素材图片/配图占位对象。三选一必填：src（用户图，data: 内联或相对路径，零外链铁律禁 http(s)）｜items（多图版式：grid/compare/wall，元素 {src?, alt?, caption?, placeholder?}）｜placeholder:true（无图时出配图占位，原生形状渲染、pictures 不增）。其余可选：layout（full/half/bleed/grid/compare/wall，见 layout-constants.json imageSpec.layouts）、fit（cover 默认 / contain）、caption、alt、hint、ratio。","imageLayoutHint":"layout 与 HTML 版式对应：full=版心全宽图｜half=左图右注（points 为右栏注解）｜bleed=通栏出血｜grid=多图网格（items 2/3/4/6 张）｜compare=双图 A/B 对比（items 2 张）｜wall=Logo 墙（items 3–12 张小图）。占位符标签文本由双引擎按 imageSpec 拼同一串，保证 HTML 与 PPTX 逐页文本一致。","chartTypes":["bar","hbar","stack","stackline","line","dualline","area","donut","multidonut","pie","radar","scatter","bubble","waterfall","gauge","pareto","funnel","gantt","vsbar","progress","sparkline","slope","dumbbell","lollipop","dotplot","bulletchart","waffle","radialbar","rose","candlestick"],"chartTypesHint":"chart.type 可取值 = 本表（30 类：16 原生 + 14 形状还原）。其余 6 类复杂信息图（sankey/treemap/boxplot/network/marimekko/streamgraph）是**专属页型**而非 chart.type——它们要按列/段/节点等结构化载荷表达，故走 sections[].type。不变量：charts.registry.types == chartTypes ∪ 上述 6 类页型（sync_runtime.py 校验）。","chartDataTable":{"enum":["notes","inline","appendix","off"],"default":"notes","rule":"非原生图表（registry.pptx=shape）的 dataTable 不得为 off；缺失时按 registry 默认值补齐。"},"pageTypes":{"points":{"label":"要点列表页","modes":["presentation","research","architecture"],"required":["points:array"],"optional":["metrics:array"]},"metrics":{"label":"指标带页（4–6 个核心数字）","modes":["presentation","research","architecture"],"required":["metrics:array"],"optional":["points:array"]},"kpi":{"label":"大数指标页（hero 大数字 + 支撑指标行）","modes":["presentation","research"],"required":["hero:array"],"optional":["metrics:array"]},"table":{"label":"对比表页","modes":["presentation","research","architecture"],"required":["table.head:array","table.rows:array"],"optional":["table.colW:array"]},"timeline":{"label":"时间线 / 路线页","modes":["presentation","research","architecture"],"required":["phases:array"]},"steps":{"label":"步骤条页（N 步横排 + 箭头，可分组）","modes":["presentation","research","architecture"],"required":["steps:array"],"optional":["groups:array","note"]},"bar":{"label":"图表页（chart.type 见 chartTypes；native 通道走原生数据图表，shape 通道走高保真形状还原 + 数据表）","modes":["presentation","research"],"required":["chart.labels:array","chart.values:array"],"optional":["chart.type","chart.series:array","chart.points:array","chart.max","chart.unit","chart.colors:array","chart.start:array","chart.target:array","chart.dataTable","note","points:array","keyMetrics:array","chart2","minis:array","compose"],"density":["points","keyMetrics"]},"donut":{"label":"环形图页（原生 pie 楔形 + 图例）","modes":["presentation","research"],"required":["chart.labels:array","chart.values:array"],"optional":["chart.unit","chart.centerLabel","chart.centerTotal","chart.colors:array","chart.dataTable","note","points:array","keyMetrics:array","chart2","minis:array","compose"],"density":["points","keyMetrics"]},"heatmap":{"label":"热力矩阵页（行 × 列 + 强度色阶）","modes":["presentation","research"],"required":["rowHeads:array","colHeads:array","cells:array"],"optional":["unit","scaleLabel:array","note","points:array","keyMetrics:array","chart2","minis:array","compose"],"density":["points","keyMetrics"]},"bullet":{"label":"达成对比页（实际 vs 目标条）","modes":["presentation","research"],"required":["items:array"],"optional":["unit","max","note","points:array","keyMetrics:array","chart2","minis:array","compose"],"density":["points","keyMetrics"]},"pyramid":{"label":"金字塔页（层级递进，顶层最窄）","modes":["presentation","research","architecture"],"required":["levels:array"],"optional":["note","points:array"]},"image":{"label":"素材图片页（full/half/bleed/grid/compare/wall，效果与位置锁定；支持配图占位）","modes":["presentation","research","architecture"],"required":["anyof:image.src:str|image.items:array|image.placeholder"],"optional":["image.caption","image.alt","image.layout","image.fit","image.ratio","image.hint","points:array","note"]},"cards":{"label":"卡片网格页（cards 元素须为 {title, points:[[k,v]…], icon?}，不接受元组）","modes":["presentation","research","architecture"],"required":["cards:array"],"optional":["columns"],"cardItemHint":"cards[] 元素：{title:str, points:[[k,v]…]|[{t,d}…]|[str…], icon?:str}。icon = 语义图标名（icon_lib.js 键：增长/下降/数据/图表/趋势/占比/表格/效率/成果/安全/权限/检查/风险/团队/流程/计划/智能/洞察/工具/清单），HTML 与 PPTX 同名真导出；缺省按标题语义自动挑选。"},"split":{"label":"双区组合页（left / right 各可为 要点｜图表｜表格｜图片：type = points（默认）| table | image | 图表类型名；图表/表格字段直接挂在对应侧）","modes":["presentation","research"],"required":["anyof:left.points:array|left.type:str"],"optional":["left.cap","left.image","left.labels:array","left.values:array","left.series:array","left.points:array","left.max","left.unit","left.colors:array","left.dataTable","left.head:array","left.rows:array","left.colW:array","right.type","right.cap","right.image","right.labels:array","right.values:array","right.series:array","right.points:array","right.max","right.unit","right.colors:array","right.dataTable","right.head:array","right.rows:array","right.colW:array"]},"comparison":{"label":"对比页（左右双栏 + 可选结论条）","modes":["presentation","research","architecture"],"required":["left.title","left.points:array","right.title","right.points:array"],"optional":["verdict"]},"quote":{"label":"引用 / 金句页（须带 metrics 证据 2–4 个，禁空页）","modes":["presentation","research"],"required":["quote","author"],"optional":["context","metrics:array"]},"diagram":{"label":"分层架构页（architecture 模式走全幅几何）","modes":["presentation","research","architecture"],"required":["layers:array"],"optional":["legend:array","aside"]},"exhibit":{"label":"Exhibit 编号图表页（research R2）","modes":["research"],"required":["chart.labels:array","chart.values:array"],"optional":["exhibitNo","chart.type","chart.series:array","chart.points:array","chart.max","chart.unit","chart.colors:array","chart.dataTable","note","points:array","keyMetrics:array","chart2","minis:array","compose"],"density":["points","keyMetrics"]},"twocol":{"label":"双栏论证页（research R1）","modes":["research"],"required":["paragraphs:array"]},"threecol":{"label":"三栏证据页（research R6）","modes":["research"],"required":["paragraphs:array"]},"halftable":{"label":"半表半图页（research R7）","modes":["research"],"required":["table.head:array","table.rows:array","chart.labels:array","chart.values:array"],"optional":["table.colW:array","chart.type","chart.series:array","chart.points:array","chart.max","chart.unit","chart.colors:array","chart.dataTable","note","points:array","keyMetrics:array","chart2","minis:array","compose"],"density":["points","keyMetrics"]},"matrix":{"label":"矩阵图页（research R8）","modes":["research"],"required":["rowHeads:array","colHeads:array","cells:array"],"optional":["points:array"]},"lane":{"label":"泳道页（architecture A2）","modes":["architecture"],"required":["lanes:array"],"optional":["points:array"]},"sankey":{"label":"桑基图页（节点-流带，流向与流量）","modes":["research","architecture"],"required":["flows:array"],"optional":["unit","chart.dataTable","note","points:array","keyMetrics:array","chart2","minis:array","compose"],"density":["points","keyMetrics"]},"treemap":{"label":"树图页（面积编码的层级构成）","modes":["research","architecture"],"required":["items:array"],"optional":["unit","chart.dataTable","note","points:array","keyMetrics:array","chart2","minis:array","compose"],"density":["points","keyMetrics"]},"boxplot":{"label":"箱线图页（分布对比：min/q1/median/q3/max）","modes":["research","architecture"],"required":["groups:array"],"optional":["unit","chart.dataTable","note","points:array","keyMetrics:array","chart2","minis:array","compose"],"density":["points","keyMetrics"]},"network":{"label":"关系网络页（节点-边拓扑）","modes":["research","architecture"],"required":["nodes:array","edges:array"],"optional":["chart.dataTable","note","points:array"]},"marimekko":{"label":"马赛克图页（列宽 × 列高双重编码）","modes":["research","architecture"],"required":["cols:array","cells:array"],"optional":["unit","chart.dataTable","note","points:array","keyMetrics:array","chart2","minis:array","compose"],"density":["points","keyMetrics"]},"streamgraph":{"label":"流带图页（时间上的构成演变）","modes":["research","architecture"],"required":["series:array"],"optional":["labels:array","chart.dataTable","note","points:array","keyMetrics:array","chart2","minis:array","compose"],"density":["points","keyMetrics"]},"chapter":{"label":"章节扉页（结构家族：大号章节号 + 章标题 + 本章看点 ≤5 条；每章第一页作视觉锚点）","modes":["presentation","research","architecture"],"required":["title"],"optional":["number","items:array"]}},"densityHint":"M7 信息密度契约：每页 = 论点（结论句标题）+ 证据（图表 / 表格 / 数据）+ 解读（points：[事实, 原因 / 影响 / 下一步]，不复述图上数字，只用已有事实）。图表页必须配 points（演示 ≥2 条、研究 ≥3 条）与 keyMetrics（2–4 个关键数字；单序列图表缺省时按数据推导最高 / 最低 / 首末变化）。chart2 = 双图对照；minis = 主图 + 最多 2 个小图；compose:\"off\" 关闭复合版式。门禁：scripts/check_density.py（DENSITY_ECHO / DENSITY_NO_INSIGHT 提示复述，DENSITY_MINIS_MAX 拦 >2 小图）。"};
/* __TOPPPT_SCHEMA_END__ */

/* __TOPPPT_SOLVER_START__ */
/* 由 scripts/sync_runtime.py 从 scripts/lib_solver.js 注入，禁止手改 */
var SOLVER = (function () { var module = { exports: {} };
/**
 * topmind-presentation · 布局求解器（M1）
 *
 * 纯函数、零依赖、确定性（同输入 → 同输出），HTML / PPTX 两端与测试共用。
 * 职责：
 *   1. rows()      —— 行/卡/泳道高度分配：先满足首选高度，空间富余时按 grow 上限拉伸，
 *                    仍有余量则给出整体垂直居中偏移（不再「挤在顶部、下半页空白」）。
 *   2. fitUp()     —— 字号求解：在阶梯内取「装得下的最大字号」，允许在稀疏时向上放大到 max。
 *   3. capacity()  —— 按页型估算内容量 / 版式承载力（>1 即超载）。
 *   4. splitModel()—— 超载页按条目拆成「续页」，标题加「（续）」，禁止静默截断。
 *   5. grid12()    —— 12 列网格列宽换算。
 * 几何单位：英寸（PPTX）；HTML 端按 px/in 比例换算即可。
 */
'use strict';

const LADDER = [32, 28, 24, 22, 20, 18, 17, 16, 15, 14, 13.5, 13, 12.5, 12, 11.5, 11, 10.5, 10, 9.5, 9, 8.5];

/** 行高分配。返回 { size, gap, offset, used }，offset 为整组垂直居中偏移。 */
function rows(avail, n, opts) {
  opts = opts || {};
  const k = Math.max(1, n | 0);
  const gap = opts.gap != null ? opts.gap : 0;
  const min = opts.min != null ? opts.min : 0.22;
  const pref = opts.pref != null ? opts.pref : min;
  const max = opts.max != null ? opts.max : pref * 1.8;
  const room = Math.max(0, avail - gap * (k - 1));
  const even = room / k;
  let size;
  if (even <= pref) size = Math.max(min, even);        // 紧张：压缩到 [min, pref]
  else size = Math.min(max, even);                     // 富余：拉伸到 max 为止
  const used = size * k + gap * (k - 1);
  const offset = opts.center === false ? 0 : Math.max(0, (avail - used) / 2);
  return { size: round(size), gap, offset: round(offset), used: round(used) };
}

/** 字号求解：needH(f) → 英寸；返回阶梯内装得下的最大字号（∈[min,max]），都装不下返回 min。 */
function fitUp(needH, avail, opts) {
  opts = opts || {};
  const max = opts.max != null ? opts.max : 16;
  const min = opts.min != null ? opts.min : 10;
  const lad = (opts.ladder || LADDER).filter(f => f <= max && f >= min);
  for (const f of lad) if (needH(f) <= avail) return f;
  return min;
}

/** 文本行数估算（CJK 计 1 字宽，拉丁计 0.55 字宽）——与 build_pptx estLines 同口径的近似。 */
function estLines(text, widthIn, pt) {
  const s = String(text == null ? '' : text);
  let units = 0;
  for (const ch of s) units += /[\u0000-\u00ff]/.test(ch) ? 0.55 : 1;
  const perLine = Math.max(1, Math.floor((widthIn * 72) / pt));
  return Math.max(1, Math.ceil(units / perLine));
}
function estTextH(text, widthIn, pt, lf) { return estLines(text, widthIn, pt) * pt * (lf || 1.45) / 72; }

/* ── 容量模型：每种列表型页型的「条目承载上限」，按模式区分 ── */
const CAP = {
  presentation: { points: 6, cards: 6, steps: 6, table: 8, comparison: 5, timeline: 6, bullet: 7, twocol: 6, threecol: 9, metrics: 6 },
  research:     { points: 8, cards: 8, steps: 7, table: 14, comparison: 7, timeline: 7, bullet: 10, twocol: 8, threecol: 12, metrics: 6 },
  architecture: { points: 7, cards: 6, steps: 7, table: 10, comparison: 5, timeline: 6, bullet: 8, twocol: 6, threecol: 9, metrics: 6 },
};
/** 按页型取「可拆的条目数组」的访问器：get(sec) → array；set(sec, arr) → 新 sec */
const LISTS = {
  points:     { get: s => s.points, set: (s, a) => Object.assign({}, s, { points: a }) },
  cards:      { get: s => s.cards, set: (s, a) => Object.assign({}, s, { cards: a }) },
  steps:      { get: s => s.steps, set: (s, a) => Object.assign({}, s, { steps: a, groups: undefined }) },
  timeline:   { get: s => s.phases, set: (s, a) => Object.assign({}, s, { phases: a }) },
  bullet:     { get: s => s.items, set: (s, a) => Object.assign({}, s, { items: a }) },
  metrics:    { get: s => s.metrics, set: (s, a) => Object.assign({}, s, { metrics: a }) },
  twocol:     { get: s => s.paragraphs, set: (s, a) => Object.assign({}, s, { paragraphs: a }) },
  threecol:   { get: s => s.paragraphs, set: (s, a) => Object.assign({}, s, { paragraphs: a }) },
  table:      { get: s => s.table && s.table.rows,
                set: (s, a) => Object.assign({}, s, { table: Object.assign({}, s.table, { rows: a }) }) },
};

/** M3 密度档（风格库 styleGrammar 的镜像；test_solver 校验与 layout-constants 一致）：
 *  紧凑风格一页多装、舒展风格少装——换风格同时换承载节奏。 */
const DENSITY_K = {"airy": 0.9, "normal": 1.0, "dense": 1.12};
const STYLE_DENSITY = {"business-blue": "normal", "apple-mono": "airy", "mckinsey": "dense", "brand-red": "normal", "warm-sand": "airy", "deep-teal": "normal", "graphite-dark": "dense", "indigo-violet": "normal", "spectrum": "dense", "ink-academic": "dense", "coral-launch": "airy", "sky-airy": "airy"};
function densityK(model) {
  const d = (model && (model.density || STYLE_DENSITY[model.style])) || 'normal';
  return DENSITY_K[d] || 1;
}

/** 容量比：条目数 / 上限（文字很长时按字数加权）。>1 = 超载。k = 密度系数。 */
function capacity(sec, mode, k) {
  const t = sec && sec.type;
  const acc = LISTS[t];
  if (!acc) return 0;
  const arr = acc.get(sec) || [];
  const cap = ((CAP[mode] || CAP.presentation)[t] || 99) * (k || 1);
  const chars = JSON.stringify(arr).length;
  const charCap = cap * (mode === 'research' ? 90 : 70);
  return round(Math.max(arr.length / cap, chars / charCap));
}

/** 超载页拆成续页。返回新 model（不改原对象）与拆页日志。 */
function splitModel(model, opts) {
  opts = opts || {};
  const mode = String(model.mode || 'presentation');
  const k = densityK(model);
  const out = [];
  const log = [];
  for (const sec of model.sections || []) {
    const ratio = capacity(sec, mode, k);
    const acc = LISTS[sec && sec.type];
    const arr = acc ? (acc.get(sec) || []) : [];
    if (!acc || ratio <= 1 || arr.length < 2) { out.push(sec); continue; }
    const parts = Math.min(arr.length, Math.ceil(ratio));
    const per = Math.ceil(arr.length / parts);
    for (let p = 0; p < parts; p++) {
      const slice = arr.slice(p * per, (p + 1) * per);
      if (!slice.length) continue;
      let ns = acc.set(sec, slice);
      if (p > 0) {
        ns = Object.assign({}, ns, { title: String(sec.title || '') + '（续）' });
        delete ns.soWhat; delete ns.verdict;            // 结论只在首页出现一次
      } else if (parts > 1) {
        delete ns.footnote;                             // 来源行放在最后一页
      }
      if (p > 0 && p < parts - 1) delete ns.footnote;
      out.push(ns);
    }
    log.push({ title: sec.title, type: sec.type, ratio, parts });
  }
  return { model: Object.assign({}, model, { sections: out }), log };
}

/** 12 列网格：span 列宽（含列间距）。 */
function grid12(totalW, span, gutter) {
  const g = gutter != null ? gutter : 0.25;
  const col = (totalW - g * 11) / 12;
  return round(col * span + g * (span - 1));
}

function round(v) { return Math.round(v * 1000) / 1000; }

module.exports = { rows, fitUp, estLines, estTextH, capacity, splitModel, grid12, densityK, CAP, LADDER, DENSITY_K, STYLE_DENSITY };
return module.exports; })();
/* __TOPPPT_SOLVER_END__ */

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
  /* 同源求解：与 build_pptx.js / render_from_model.py 同一容量模型，超载页给出拆页提示 */
  var sp = SOLVER.splitModel(model);
  sp.log.forEach(function (l) {
    warnings.push('「' + (l.title || l.type) + '」容量 ' + Math.round(l.ratio * 100) + '%，交付时自动拆为 ' + l.parts + ' 页');
  });
  var pages = pagePlan(model).length;
  return { ok: missing.length === 0, missing: missing, warnings: warnings, pages: pages };
}

/* 页序计划：封面 + 大纲(可多页，每页 12 条) + 章节（容量拆页后）+ 收尾 —— 与 build_pptx.js 同规则 */
function pagePlan(model) {
  if (!model || typeof model !== 'object') return [];
  var plan = [{ kind: 'cover', type: 'cover', title: model.title || '' }];
  var ag = Array.isArray(model.agenda) ? model.agenda : [];
  for (var i = 0; i < Math.ceil(ag.length / 12); i++) plan.push({ kind: 'agenda', type: 'agenda', title: '大纲' + (i ? '（续）' : '') });
  SOLVER.splitModel(model).model.sections.forEach(function (s) {
    plan.push({ kind: 'section', type: s.type || 'points', title: s.title || '', cont: /（续）$/.test(s.title || '') });
  });
  if (model.closing) plan.push({ kind: 'closing', type: 'closing', title: model.closing.title || '' });
  return plan;
}

var api = { validateModel: validateModel, pagePlan: pagePlan, solver: SOLVER, PRESETS: PRESETS };
if (typeof module !== 'undefined' && module.exports) module.exports = api;
g.TopPptHtml = api;
})(typeof window !== 'undefined' ? window : globalThis);
