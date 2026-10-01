/**
 * TopPPT HTML · 页型布局区域 IR（双通道几何收敛起点）
 *
 * 从 layout-constants.json（含 layoutSlots）派生「语义槽位 → 英寸矩形」。
 * B 通道（build_pptx.js）直接 require；A 通道消费同一 LC 常量（数字同源）。
 *
 * 纪律：改几何与槽位只改 layout-constants.json（layoutSlots 已并入）。
 * 新增页型先扩 LC.layoutSlots，再在此补 regionOf 分支，最后写双引擎。
 */
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const LC = JSON.parse(fs.readFileSync(path.join(__dirname, 'layout-constants.json'), 'utf8'));
const SLOTS = LC.layoutSlots;
if (!SLOTS || !SLOTS.pageTypes) {
  throw new Error('layout-constants.json 缺 layoutSlots.pageTypes（Batch 3 单源）');
}

const INFO_TYPES = {
  sankey: 1, treemap: 1, boxplot: 1, network: 1, marimekko: 1, streamgraph: 1,
};

function pageBox() {
  const p = LC.page;
  return { pw: p.pw, ph: p.ph, mx: p.mx, cw: p.pw - 2 * p.mx };
}

/** 内容区垂直范围（含注释层预留） */
function contentBand(opts) {
  const L = LC.pageTypes.layout;
  const C = LC.pageTypes.common;
  const withNote = !!(opts && opts.withNote);
  const top = (opts && opts.top != null) ? opts.top : C.bodyY;
  const bottom = withNote ? L.contentBottomWithNote : L.contentBottom;
  return { top, bottom, h: Math.max(0, bottom - top) };
}

/**
 * 语义槽位 → {x,y,w,h}（英寸）
 * 未识别页型/槽位时返回 null（调用方回落自身逻辑，不中断）。
 */
function regionOf(pageType, slotId, opts) {
  const type = String(pageType || 'points');
  const slot = String(slotId || '');
  const { mx, cw } = pageBox();
  const C = LC.pageTypes.common;
  const L = LC.pageTypes.layout;
  const PT = LC.pageTypes[type] || {};

  // ── chrome：页头 ──
  if (slot === 'head' || slot === 'chrome') {
    return {
      x: mx, y: C.headEyebrowY, w: cw,
      h: Math.max(0.4, (C.headRuleY || 1.95) - C.headEyebrowY),
      titleY: C.headTitleY, ruleY: C.headRuleY, leadY: C.leadY, bodyY: C.bodyY,
    };
  }

  // ── annotation：so-what / 来源 / note ──
  if (slot === 'annotation' || slot === 'soWhat') {
    const y = (LC.pageTypes.exhibit && LC.pageTypes.exhibit.soWhatY != null)
      ? LC.pageTypes.exhibit.soWhatY : 6.05;
    return { x: mx, y, w: cw, h: 0.62 };
  }
  if (slot === 'footnote') {
    const y = (LC.pageTypes.exhibit && LC.pageTypes.exhibit.footnoteY != null)
      ? LC.pageTypes.exhibit.footnoteY
      : ((LC.pageTypes.note && LC.pageTypes.note.y) || 6.55);
    return { x: mx, y, w: cw - 1.2, h: (LC.pageTypes.note && LC.pageTypes.note.h) || 0.32 };
  }

  // ── 页型主从区域 ──
  if (type === 'points') {
    const band = contentBand(opts);
    if (slot === 'primary' || slot === 'list') {
      return { x: mx, y: PT.listY || band.top, w: cw, h: Math.max(0.8, band.bottom - (PT.listY || band.top)) };
    }
    if (slot === 'metrics') {
      return { x: mx, y: PT.metricY || 4.7, w: cw, h: Math.max(0.6, L.contentBottom - (PT.metricY || 4.7)) };
    }
  }

  if (type === 'metrics') {
    if (slot === 'primary') {
      return {
        x: mx, y: PT.bandY || 3.1, w: cw, h: PT.cardH || 2.3,
        valY: PT.valY, valH: PT.valH, capY: PT.capY, capH: PT.capH,
        gap: PT.gap, maxW: PT.maxW,
      };
    }
  }

  if (type === 'table') {
    if (slot === 'primary') {
      const y = PT.y || L.contentTop;
      return {
        x: mx, y, w: cw,
        h: Math.max(1, ((opts && opts.bottom) || L.contentBottom) - y),
        rowH: PT.rowH, rowHMin: PT.rowHMin, headRowH: PT.headRowH,
      };
    }
  }

  if (type === 'bar') {
    if (slot === 'primary') {
      const y = PT.chartY || 2.95;
      const bottom = (opts && opts.bottom != null) ? opts.bottom
        : ((opts && opts.withNote) ? L.contentBottomWithNote : L.contentBottom);
      /* chartX/chartW 是历史误用：与 donut/table/hbar/exhibit 同口径，图表盒对齐版心 (mx, cw)。
         此前 `mx+chartX` / `cw-chartW` 造成 bar 图右移 0.6in，与标题/表格左边距不齐。 */
      return { x: mx, y, w: cw, h: Math.max(1.2, bottom - y) };
    }
    if (slot === 'hbar') {
      const y0 = PT.hbarY0 || 2.6;
      const y1 = (opts && opts.bottom != null) ? opts.bottom : (PT.hbarY1 || 6.25);
      return { x: mx, y: y0, w: cw, h: Math.max(1.2, y1 - y0) };
    }
  }

  if (type === 'donut') {
    if (slot === 'primary') {
      const y = PT.chartY || 2.95;
      const bottom = (opts && opts.bottom != null) ? opts.bottom : L.contentBottom;
      return { x: mx, y, w: cw, h: Math.max(1.2, bottom - y) };
    }
  }

  if (type === 'exhibit') {
    if (slot === 'primary') {
      const y = PT.chartY || 2.95;
      const h = Math.max(1.2, (L.contentBottomWithNote - y));
      return { x: mx, y, w: cw, h, badgeY: PT.badgeY };
    }
    if (slot === 'secondary') {
      return { x: mx, y: PT.badgeY || L.contentTop, w: cw * 0.32, h: 0.4 };
    }
  }

  if (type === 'points') {
    const band = contentBand(opts);
    if (slot === 'primary' || slot === 'list') {
      return {
        x: mx, y: PT.listY || band.top, w: cw,
        h: Math.max(0.8, (opts && opts.bottom != null ? opts.bottom : band.bottom) - (PT.listY || band.top)),
        rowH: PT.rowH, rowHMin: PT.rowHMin, markSize: PT.markSize,
      };
    }
    if (slot === 'metrics') {
      return {
        x: mx, y: PT.metricY || 4.7, w: cw,
        h: Math.max(0.6, L.contentBottom - (PT.metricY || 4.7)),
        metricW: PT.metricW, metricValH: PT.metricValH, metricCapY: PT.metricCapY,
      };
    }
  }

  if (type === 'split') {
    const SP = PT;
    const top = SP.chartY || L.contentTop;
    const bottom = (opts && opts.bottom != null) ? opts.bottom : L.contentBottom;
    if (slot === 'left') {
      return {
        x: mx, y: top, w: cw * (SP.leftW || 0.55),
        h: Math.max(1.2, bottom - top),
        tableY: SP.tableY, tableRowH: SP.tableRowH, rowH: SP.rowH, capY: SP.capY,
      };
    }
    if (slot === 'right') {
      const rx = mx + cw * (SP.rightX != null ? SP.rightX : 0.585);
      return {
        x: rx, y: top, w: cw * (SP.rightW || 0.415),
        h: Math.max(1.2, bottom - top),
        tableY: SP.tableY, tableRowH: SP.tableRowH, rowH: SP.rowH, capY: SP.capY,
      };
    }
  }

  if (type === 'twocol') {
    const gap = PT.colGap || 0.5;
    const colW = (cw - gap) / 2;
    const top = (opts && opts.top != null) ? opts.top : L.contentTop;
    const bottom = (opts && opts.bottom != null) ? opts.bottom : L.contentBottom;
    if (slot === 'primary' || slot === 'left') {
      return { x: mx, y: top, w: colW, h: Math.max(1, bottom - top), gap, colW };
    }
    if (slot === 'secondary' || slot === 'right') {
      return { x: mx + colW + gap, y: top, w: colW, h: Math.max(1, bottom - top), gap, colW };
    }
  }

  if (type === 'diagram' || type === 'lane') {
    if (slot === 'primary') {
      const arch = LC.pageTypes.arch || {};
      const y = (opts && opts.mode === 'architecture' && arch.fullStartY != null)
        ? arch.fullStartY
        : (PT.bodyStartY || 2.9);
      const b = (opts && opts.mode === 'architecture' && arch.fullEndY != null)
        ? arch.fullEndY
        : ((opts && opts.bottom != null) ? opts.bottom : L.contentBottom);
      return {
        x: mx, y, w: cw, h: Math.max(1.2, b - y),
        layerBarW: PT.layerBarW, layerGap: PT.layerGap, maxLayerH: PT.maxLayerH,
        laneH: arch.laneH, laneHeadW: arch.laneHeadW, laneGap: arch.laneGap,
        stepGap: arch.stepGap, stepMaxW: arch.stepMaxW,
      };
    }
  }

  // ── 剩余高频页型 ──
  if (type === 'kpi') {
    if (slot === 'primary' || slot === 'hero') {
      return {
        x: mx, y: PT.heroY || 2.9, w: cw * (PT.heroW || 0.52), h: PT.heroH || 1.6,
        dividerX: PT.dividerX, metricY0: PT.metricY0, metricRowH: PT.metricRowH,
      };
    }
    if (slot === 'metrics') {
      const dx = PT.dividerX != null ? PT.dividerX : 0.56;
      return {
        x: mx + cw * dx + 0.35, y: PT.metricY0 || 2.95,
        w: cw * (1 - dx) - 0.5, h: Math.max(0.6, L.contentBottom - (PT.metricY0 || 2.95)),
      };
    }
  }

  if (type === 'comparison') {
    const gap = PT.panelGap || 0.4;
    const panelW = (cw - gap) / 2;
    const y = PT.panelY || 2.55;
    const h = PT.panelH || 3.4;
    if (slot === 'primary' || slot === 'left') {
      return { x: mx, y, w: panelW, h, titleH: PT.titleH, rowH: PT.rowH };
    }
    if (slot === 'right' || slot === 'secondary') {
      return { x: mx + panelW + gap, y, w: panelW, h, titleH: PT.titleH, rowH: PT.rowH };
    }
  }

  if (type === 'quote') {
    if (slot === 'primary') {
      return {
        x: mx + 1.05, y: PT.textY || 2.7, w: cw - 2.1, h: PT.textH || 2.3,
        markY: PT.markY, authorY: PT.authorY, contextY: PT.contextY,
      };
    }
  }

  if (type === 'heatmap') {
    if (slot === 'primary') {
      const y = PT.y || 2.6;
      const bottom = (opts && opts.bottom != null) ? opts.bottom : L.contentBottom;
      return {
        x: mx, y, w: cw, h: Math.max(1, bottom - y),
        labelW: PT.labelW, headH: PT.headH, cellH: PT.cellH, cellGap: PT.cellGap,
      };
    }
  }

  if (type === 'bullet') {
    if (slot === 'primary') {
      const y = PT.y || 2.6;
      const bottom = (opts && opts.bottom != null) ? opts.bottom : L.contentBottom;
      return {
        x: mx, y, w: cw, h: Math.max(1, bottom - y),
        rowH: PT.rowH, labelW: PT.labelW, valW: PT.valW, barH: PT.barH,
      };
    }
  }

  if (type === 'pyramid') {
    if (slot === 'primary') {
      const y = PT.y || 2.35;
      const bottom = (opts && opts.bottom != null) ? opts.bottom : L.contentBottom;
      return {
        x: mx, y, w: cw, h: Math.max(1, bottom - y),
        rowH: PT.rowH, gap: PT.gap, minW: PT.minW, labelW: PT.labelW,
      };
    }
  }

  if (type === 'steps') {
    if (slot === 'primary') {
      const y = PT.y || 3.05;
      return {
        x: mx, y, w: cw, h: PT.barH || 1.35,
        gap: PT.gap, arrowW: PT.arrowW, numH: PT.numH, titleH: PT.titleH,
        pad: PT.pad, maxPerRow: PT.maxPerRow,
      };
    }
  }

  if (type === 'cards') {
    if (slot === 'primary') {
      const y = PT.startY || 3.0;
      const bottom = (opts && opts.bottom != null) ? opts.bottom : L.contentBottom;
      return { x: mx, y, w: cw, h: Math.max(1, bottom - y), gap: PT.gap, maxH: PT.maxH, titleH: PT.titleH };
    }
  }

  if (type === 'timeline') {
    if (slot === 'primary') {
      return {
        x: mx, y: PT.labelY || 2.95, w: cw,
        h: Math.max(1, L.contentBottom - (PT.labelY || 2.95)),
        axisY: PT.axisY, dotY: PT.dotY, dotR: PT.dotR, nameY: PT.nameY,
        descY: PT.descY, descH: PT.descH,
      };
    }
  }

  if (type === 'image') {
    if (slot === 'primary') {
      const y = Math.max(PT.y || 2.3, (opts && opts.top) || 0);
      /* R2：有图注时图片不得越过 contentBottomWithNote（图注本身落在注释带，属 annotation self）。
         否则图片底边（如 6.58）会被判「主内容侵入注释带」。 */
      const hasCap = !!(opts && opts.caption);
      const bottom = (opts && opts.bottom != null) ? opts.bottom
        : (hasCap ? L.contentBottomWithNote : L.contentBottom);
      return {
        x: mx, y, w: cw, h: Math.max(1.2, Math.min(PT.h || 4.2, bottom - y)),
        halfW: PT.halfW, halfGap: PT.halfGap, capY: PT.capY, capH: PT.capH || 0.3,
        radius: PT.radius, gridGap: PT.gridGap, gridCols: PT.gridCols,
      };
    }
  }

  if (type === 'halftable') {
    if (slot === 'primary' || slot === 'left') {
      const r = LC.pageTypes.research || {};
      const top = (opts && opts.top != null) ? opts.top : L.contentTop;
      const bottom = (opts && opts.bottom != null) ? opts.bottom : L.contentBottom;
      return { x: mx, y: top, w: cw * (r.halfTableW || 0.52), h: Math.max(1, bottom - top) };
    }
    if (slot === 'secondary' || slot === 'right') {
      const r = LC.pageTypes.research || {};
      const top = (opts && opts.top != null) ? opts.top : L.contentTop;
      const bottom = (opts && opts.bottom != null) ? opts.bottom : L.contentBottom;
      return {
        x: mx + cw * (r.halfChartX || 0.57), y: top,
        w: cw * (r.halfChartW || 0.43), h: Math.max(1, bottom - top),
      };
    }
  }

  if (type === 'matrix') {
    if (slot === 'primary') {
      const r = LC.pageTypes.research || {};
      const y = r.matrixY || 2.3;
      const bottom = (opts && opts.bottom != null) ? opts.bottom : L.contentBottom;
      return {
        x: mx, y, w: cw, h: Math.max(1, bottom - y),
        labelW: r.matrixLabelW, cellH: r.matrixCellH,
      };
    }
  }

  if (type === 'threecol') {
    const r = LC.pageTypes.research || {};
    const gap = r.col3Gap || 0.38;
    const colW = (cw - 2 * gap) / 3;
    const top = (opts && opts.top != null) ? opts.top : L.contentTop;
    const bottom = (opts && opts.bottom != null) ? opts.bottom : L.contentBottom;
    if (slot === 'primary' || slot === 'left') {
      return { x: mx, y: top, w: colW, h: Math.max(1, bottom - top), gap, colW, cols: 3 };
    }
    if (slot === 'middle') {
      return { x: mx + colW + gap, y: top, w: colW, h: Math.max(1, bottom - top), gap, colW, cols: 3 };
    }
    if (slot === 'right' || slot === 'secondary') {
      return { x: mx + 2 * (colW + gap), y: top, w: colW, h: Math.max(1, bottom - top), gap, colW, cols: 3 };
    }
  }

  // 信息图页型：内容区主图
  if (INFO_TYPES[type] && (slot === 'primary')) {
    const y = PT.y || L.contentTop;
    const h = PT.h || 4.1;
    const bottom = (opts && opts.bottom != null) ? opts.bottom : L.contentBottom;
    return { x: mx, y, w: cw, h: Math.max(1.2, Math.min(h, bottom - y)) };
  }

  // 默认：内容区全宽
  if (slot === 'primary' || slot === 'secondary' || slot === 'left' || slot === 'right') {
    const band = contentBand(opts);
    return { x: mx, y: band.top, w: cw, h: band.h };
  }
  return null;
}

/** 槽位是否在 LC.layoutSlots 中声明为 required */
function slotRequired(pageType, slotId) {
  const def = (SLOTS.pageTypes || {})[pageType];
  if (!def) return false;
  const s = (def.slots || []).find(x => x.id === slotId);
  return !!(s && s.required);
}

/** 列出页型已声明槽位 id */
function slotIds(pageType) {
  const def = (SLOTS.pageTypes || {})[pageType];
  return (def && def.slots) ? def.slots.map(s => s.id) : [];
}

module.exports = {
  LC,
  SLOTS,
  pageBox,
  contentBand,
  regionOf,
  slotRequired,
  slotIds,
};
