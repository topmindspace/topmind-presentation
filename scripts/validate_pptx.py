#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TopPPT HTML· PPTX 质检（交付硬门禁）

用法:
    python validate_pptx.py <报告.pptx> [--strict] [--model=报告.model.json] [--json-out=报告.json]
                            [--allow-shape-charts]
                            [--deep --emit-manifest=报告.manifest.json]   # 深度模式（高保真/1:1）
输出约定:
    **stdout 恒为完整 JSON 报告**（供 probe_image_export.py / 流水线直接 json.loads 消费）；
    `--json-out` 额外落盘一份；人读建议 `--json-out` 后用编辑器查看。

检查面：
  ① 包结构：可解析 PPTX（ZIP + presentation.xml + sldSz），16:9 比例
  ② 可编辑性：全原生形状/文本框/表格；图片默认必须为 0（pictures=0），
     仅当模型显式声明 section.image / split.right.image 时放行对应数量的图片（PICTURES_NOT_DECLARED 硬拦）；
     配图占位（image.placeholder）走原生形状、不计入图片数；
     另拦图片版式/裁切非法、单页多图超限、相对路径文件缺失（IMAGE_LAYOUT_INVALID / IMAGE_FIT_INVALID /
     IMAGE_ITEMS_TOO_MANY / IMAGE_SRC_MISSING）与外链 src（IMAGE_SRC_EXTERNAL）
  ③ 版式安全：元素越界 / 负坐标 / 非正尺寸（PowerPoint 会判损坏）、页内文本溢出估算、
     覆盖率与信息密度、字体下限、占位符文本
  ③b 色值合法性：所有 srgbClr val 必须是 6 位 hex（不带 # 前缀）——编码色板与图表系列色
     由双引擎直写 OOXML，单源一旦带 # 就是非法色值（PowerPoint 静默忽略/触发修复）
     → INVALID_HEX_COLOR 硬拦
  ④ 内容保真（--model）：页数结构、章节/封面/收尾标题落位、逐页内容覆盖（≥roundtripMin 关键串，
     比对语料 = 幻灯片形状文本 ∪ 演讲者备注 ∪ 关联 chart part 文本——原生图表类别标签与 notes-only
     字段不得被误判为内容丢失）、主题 token 亮暗一致、模型图表必须落成原生可编辑图表（MODEL_CHART_COUNT）、
     图片源非外链
  ⑤ --strict：0 errors / 0 warnings 才通过（退出码 0）；否则 1（errors）或 2（warnings）

零第三方依赖（纯标准库）；python-pptx 交叉裁判见 scripts/cross_verify.py（可选）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Any

# Windows GBK 控制台兜底：强制 UTF-8 输出
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
from xml.etree import ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
}
GLOBAL_MIN_FONT_PT = 6.5          # 全篇字体下限（低于此值投影/打印不可读）
LARGE_IMAGE_AREA_RATIO = 0.40     # 单图面积告警阈值（未声明的图片命中即告警）
FULL_SLIDE_IMAGE_RATIO = 0.90
TEXT_OVERFLOW_TOLERANCE = 1.18    # 文本溢出估算容差（18%，与 cross_verify 一致）
# 下两项只是读不到 layout-constants.json 时的兵底；真值走 containers.textMetrics（与 build_pptx.js 同源）
LINE_FACTOR = 1.45                # 行高系数
EM_ASCII_RATIO = 0.52             # 拉丁/数字相对 CJK 的字宽比
UNBALANCED_GAP_RATIO = 0.28       # 右/下留白告警阈值
MIN_EDGE_MARGIN_IN = 0.02         # 元素不得贴边/越界的安全边距（英寸）

# OOXML ST_HexColorRGB = 6 位 hex；# 前缀 / 3 位缩写 / 非 hex 一律非法（PowerPoint 会忽略或触发修复）
HEX_COLOR_RE = re.compile(r'srgbClr val="([^"]*)"')
HEX6_RE = re.compile(r"[0-9A-Fa-f]{6}")

# --strict 下升级为 error 的告警码（其余告警仍以 warning 计，同样阻止 strict 通过）
STRICT_FAILURE_CODES = {
    "INVALID_SHAPE_BOUNDS",
    "SHAPE_OUTSIDE_SLIDE",
    "PICTURES_NOT_ALLOWED",
    "PICTURES_NOT_DECLARED",
    "PICTURES_UNDER_DECLARED",
    "FULL_SLIDE_BACKGROUND_RISK",
    "NO_NATIVE_TEXT_WITH_EDITABLE_TEXT_REQUIRED",
    "FONT_SIZE_BELOW_FOOTER_MIN",
    "MODEL_ROUNDTRIP_SLIDE_COUNT",
    "MODEL_ROUNDTRIP_TITLE_MISSING",
    "MODEL_ROUNDTRIP_COVER_TITLE",
    "MODEL_ROUNDTRIP_CLOSING_TITLE",
    "MODEL_ROUNDTRIP_CONTENT_MISSING",
    "MODEL_CHART_COUNT",
    "MODEL_CHART_DATATABLE",
    "MODEL_CHART_NOTES_MISSING",
    "FONT_SIZE_OFF_SCALE",
    "MODEL_THEME_BG_MISMATCH",
    "IMAGE_SRC_EXTERNAL",
    # 容器级与表格级硬门禁（比页面级越界更严格）
    "CONTAINER_OVERFLOW",
    "TABLE_SEMANTIC_TYPE",
    "TABLE_DENSITY",
    # 素材图片模型门禁（版式/裁切/多图数量/文件缺失；外链 src 见 IMAGE_SRC_EXTERNAL）
    "IMAGE_LAYOUT_INVALID",
    "IMAGE_FIT_INVALID",
    "IMAGE_ITEMS_TOO_MANY",
    "IMAGE_SRC_MISSING",
    # v9：截图级真缺陷纳入 strict（原 WARN/缺失会「假过」）
    "HTML_TAG_IN_TEXT",
    "TITLE_ONLY_PAGE",
    "UNDERFILL_PAGE",
    "LOW_TEXT_DENSITY",
    "LOW_CONTENT_DENSITY",
    "EMPTY_OR_UNMEASURABLE_SLIDE",
    "UNBALANCED_EMPTY_SPACE",
    "UNJUSTIFIED_LARGE_IMAGE",
    "TEXT_OVERFLOW_ESTIMATE",
    "TEXT_OVERFLOW_VERTICAL",
    "ANNOTATION_BAND_OVERLAP",
    "FONT_SIZE_NOT_SNAPPED",
    "TEXT_INCOMPLETE",
    "CHART_SKEW_INVALID",
    "CHART_OVERSIZE",
    "LAYOUT_MULTI_FOCUS",
    "LAYOUT_ALIGN_DRIFT",
    "LAYOUT_LABEL_COLLIDE",
    # R6：元素两两重叠 + 版心填充率（本次诊断盲区）
    "ELEMENT_OVERLAP",
    "LAYOUT_FILL",
}
# 深度模式专属校验码（--deep 时并入 STRICT_FAILURE_CODES；默认不跑，保持轻量）
DEEP_STRICT_CODES = {
    "CONTINUOUS_TEXT_FLOW",
    "ANCHOR_TITLE_MISALIGNED",
}
PLACEHOLDER_RE = re.compile(
    r"\b(?:TODO|TBD)\b|Lorem ipsum|Click to add|单击此处添加",
    re.IGNORECASE,
)
SLIDE_RE = re.compile(r"ppt/slides/slide(\d+)\.xml$")
# 探针跳过的非「可见正文」键：色值/图标/链接/标识/类型/量程单位等元数据，
# 以及 image.hint/src/alt 这类素材声明或只写进备注的交付指引。
# chart.labels / note / lead / soWhat / footnote / centerLabel 等仍作探针——
# 它们的落点（形状文本 / 备注 / chart part）由 _roundtrip_corpus 并集覆盖。
_PROBE_SKIP_KEYS = {
    "colors", "color", "icon", "href", "id", "type", "exhibitNo", "max", "unit",
    "hint", "src", "alt", "fit", "layout", "placeholder", "ratio", "dataTable",
    "variant",  # 版式变体注册值（bento-grid/timeline/2-col-feature）不渲染为文本
}


def issue(code: str, message: str, *, slide: int | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"code": code, "message": message}
    if slide is not None:
        item["slide"] = slide
    return item


def read_xml(archive: zipfile.ZipFile, name: str) -> ET.Element:
    return ET.fromstring(archive.read(name))


def find_slide_names(archive: zipfile.ZipFile) -> list[str]:
    matched: list[tuple[int, str]] = []
    for name in archive.namelist():
        result = SLIDE_RE.fullmatch(name)
        if result:
            matched.append((int(result.group(1)), name))
    return [name for _, name in sorted(matched)]


def _slide_rels(archive: zipfile.ZipFile, slide_name: str) -> list[str]:
    """该幻灯片 rels 里的 Target 列表（无 rels 返回空列表）。"""
    base = slide_name.rsplit("/", 1)[-1]
    rels_name = f"ppt/slides/_rels/{base}.rels"
    try:
        rels = read_xml(archive, rels_name)
    except (KeyError, ET.ParseError):
        return []
    return [(rel.get("Target") or "") for rel in rels]


def _resolve_slide_part(slide_name: str, target: str) -> str:
    """把 rels Target（常为 ../charts/chart1.xml）解析成包内绝对 part 路径。"""
    from posixpath import dirname, normpath, join
    return normpath(join(dirname(slide_name), target))


def slide_notes_text(archive: zipfile.ZipFile, slide_name: str) -> str:
    """取该页演讲者备注的纯文本（经 slide rels 定位 notesSlide；无备注返回空串）。"""
    target = next((t for t in _slide_rels(archive, slide_name) if "notesSlide" in t), "")
    if not target:
        return ""
    part = _resolve_slide_part(slide_name, target)
    try:
        return text_content(read_xml(archive, part))
    except (KeyError, ET.ParseError):
        return ""


def slide_chart_text(archive: zipfile.ZipFile, slide_name: str) -> str:
    """取该页关联 chart part 的文本（类别/系列/缓存值）。

    原生数据图表的 labels 落在 ppt/charts/chartN.xml 的 c:pt/c:v，不在幻灯片
    形状 a:t 里——往返保真比对必须把 chart part 并入语料，否则类别标签必然 MISS。
    """
    chunks: list[str] = []
    for target in _slide_rels(archive, slide_name):
        if "charts/chart" not in target.replace("\\", "/"):
            continue
        part = _resolve_slide_part(slide_name, target)
        try:
            root = read_xml(archive, part)
        except (KeyError, ET.ParseError):
            continue
        chunks.append(text_content(root))
        for node in root.findall(".//c:v", NS):
            if node.text and node.text.strip():
                chunks.append(node.text.strip())
    return " ".join(chunks).strip()


def shape_bounds(element: ET.Element) -> tuple[int, int, int, int] | None:
    """Read shape geometry from DrawingML ``a:xfrm`` **or** PresentationML ``p:xfrm``.

    Native charts live in ``p:graphicFrame``, which carries ``p:xfrm`` (not ``a:xfrm``).
    Skipping ``p:xfrm`` made chart overflow / overlap gates blind.
    """
    xfrm = element.find(".//a:xfrm", NS)
    if xfrm is None:
        xfrm = element.find(".//p:xfrm", NS)
    if xfrm is None:
        return None
    # p:xfrm and a:xfrm both nest a:off / a:ext
    offset = xfrm.find("a:off", NS)
    extent = xfrm.find("a:ext", NS)
    if offset is None or extent is None:
        return None
    try:
        return (
            int(offset.get("x", "0")),
            int(offset.get("y", "0")),
            int(extent.get("cx", "0")),
            int(extent.get("cy", "0")),
        )
    except ValueError:
        return None


def text_content(element: ET.Element) -> str:
    return " ".join((node.text or "") for node in element.findall(".//a:t", NS)).strip()


def _all_run_sizes(root: ET.Element) -> list[float]:
    """页内所有非空文本 run 的字号（pt）——只取真正承载文字的 run，避免空占位样式干扰。"""
    out: list[float] = []
    for run in root.findall(".//a:r", NS):
        text = "".join(t.text or "" for t in run.findall("a:t", NS))
        if not text.strip():
            continue
        pr = run.find("a:rPr", NS)
        raw = pr.get("sz") if pr is not None else None
        if raw is None:
            continue
        try:
            out.append(int(raw) / 100.0)
        except (TypeError, ValueError):
            continue
    return out


def font_sizes_pt(element: ET.Element) -> list[float]:
    sizes: list[float] = []
    for node in element.findall(".//a:rPr", NS) + element.findall(".//a:defRPr", NS):
        raw_size = node.get("sz")
        if raw_size is None:
            continue
        try:
            size = int(raw_size) / 100
        except ValueError:
            continue
        if size > 0:
            sizes.append(size)
    return sizes


def est_text_width_in(text: str, font_pt: float) -> float:
    """估算文本宽度（英寸）：CJK 1em、ASCII emAsciiRatio（与 build_pptx.js estLines 同口径）。"""
    ratio = _containers_cfg()["emAsciiRatio"]
    em = sum(1.0 if ord(c) > 0x2E80 else ratio for c in text)
    return em * font_pt / 72.0


def text_overflow_check(shape: ET.Element, slide_no: int) -> list[dict[str, Any]]:
    """文本溢出估算：逐段估宽 × 可容行数 vs 文本框高度。"""
    out: list[dict[str, Any]] = []
    box = shape_bounds(shape)
    if box is None:
        return out
    _, _, cx, cy = box
    w_in, h_in = cx / 914400, cy / 914400
    if w_in <= 0 or h_in <= 0:
        return out
    lf = _containers_cfg()["lineFactor"]
    for para in shape.findall(".//a:p", NS):
        line = "".join((t.text or "") for t in para.findall(".//a:t", NS))
        if not line.strip():
            continue
        sizes = font_sizes_pt(para)
        fz = min(sizes) if sizes else 12.0
        est_w = est_text_width_in(line, fz)
        lines_avail = max(1, int(h_in / (fz / 72.0 * lf)))
        capacity = w_in * lines_avail
        if est_w > capacity * TEXT_OVERFLOW_TOLERANCE:
            out.append(issue(
                "TEXT_OVERFLOW_ESTIMATE",
                f'文本可能溢出："{line[:18]}…" 估算 {est_w:.1f}in > 容量 {capacity:.1f}in（{fz:.1f}pt × {lines_avail} 行）。',
                slide=slide_no,
            ))
    return out


def text_overflow_vertical_check(shape: ET.Element, slide_no: int) -> list[dict[str, Any]]:
    """Multi-segment cumulative vertical overflow (TEXT_OVERFLOW_VERTICAL).

    Per-paragraph area checks miss the case where each line fits individually but
    the *sum* of estimated line heights exceeds the text-frame height.
    """
    out: list[dict[str, Any]] = []
    box = shape_bounds(shape)
    if box is None:
        return out
    _, _, cx, cy = box
    w_in, h_in = cx / 914400.0, cy / 914400.0
    if w_in <= 0 or h_in <= 0:
        return out
    cfg = _containers_cfg()
    lf = float(cfg.get("lineFactor") or 1.35)
    total_h = 0.0
    segments = 0
    for para in shape.findall(".//a:p", NS):
        line = "".join((t.text or "") for t in para.findall(".//a:t", NS))
        if not line.strip():
            continue
        sizes = font_sizes_pt(para)
        fz = min(sizes) if sizes else 12.0
        est_w = est_text_width_in(line, fz)
        lines_needed = max(1, int((est_w / max(w_in, 0.01)) + 0.999))
        total_h += lines_needed * (fz / 72.0) * lf
        segments += 1
    # Single-segment cases already covered by TEXT_OVERFLOW_ESTIMATE; this gate
    # targets multi-para cumulative overflow (tolerance mirrors horizontal gate).
    if segments >= 2 and total_h > h_in * TEXT_OVERFLOW_TOLERANCE:
        out.append(issue(
            "TEXT_OVERFLOW_VERTICAL",
            f"多段文本累计高度估算 {total_h:.2f}in > 文本框 {h_in:.2f}in"
            f"（{segments} 段，容差 {TEXT_OVERFLOW_TOLERANCE:.0%}）——"
            "请拆段/缩字号阶梯/换页，禁止静默截断。",
            slide=slide_no,
        ))
    return out


def annotation_band_overlap_check(
    elements: list[ET.Element],
    slide_no: int,
    slide_height_emu: int,
    slide_width_emu: int | None = None,
) -> list[dict[str, Any]]:
    """Detect primary content crushing into the annotation band.

    Geometry (layout-constants pageTypes.layout / exhibit / note):
      soWhatY ≈ 6.05 · contentBottomWithNote ≈ 6.4 · footnote/note ≈ 6.55 ·
      contentBottom ≈ 6.9 · pager ≈ 7.0

    Semantics (0.1.7 · D9/D11):
      - Full-bleed backgrounds, full-height accent strips, and pager/footer
        chrome are never "content crushing the band".
      - so-what / 口径 / 来源 bars that live in the annotation zone are the
        band itself — not invaders.
      - Crush = starts ABOVE band_top and overlaps down into the band.
        Shapes whose top is already at/below band_top are in-band chrome.
      - When so-what is present, band_top = soWhatY so invasions in
        (soWhatY, contentBottomWithNote] are reported (D11). Footnote/source
        only keeps band_top = contentBottomWithNote.
      - When no annotation is present, main content may use up to
        contentBottom; only a severe invasion (≥0.35in into the nominal
        withNote band) still fires as a safety net.
      - Report ALL invaders per slide (D9) — do not break after the first.
    """
    out: list[dict[str, Any]] = []
    try:
        lc_path = Path(__file__).resolve().parent / "layout-constants.json"
        lc = json.loads(lc_path.read_text(encoding="utf-8"))
        lay = ((lc.get("pageTypes") or {}).get("layout") or {})
        exhibit = ((lc.get("pageTypes") or {}).get("exhibit") or {})
        note = ((lc.get("pageTypes") or {}).get("note") or {})
        nominal_band_top_in = float(lay.get("contentBottomWithNote") or 6.4)
        band_bot_in = float(lay.get("contentBottom") or 6.9)
        so_what_y_in = float(exhibit.get("soWhatY") or 6.05)
        note_y_in = float(note.get("y") or exhibit.get("footnoteY") or 6.55)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        nominal_band_top_in, band_bot_in, so_what_y_in, note_y_in = 6.4, 6.9, 6.05, 6.55

    band_top_in = nominal_band_top_in
    band_top = int(band_top_in * 914400)
    nominal_band_top = int(nominal_band_top_in * 914400)
    band_bot = int(band_bot_in * 914400)
    so_what_y = int(so_what_y_in * 914400)
    note_y = int(note_y_in * 914400)
    slide_w = int(slide_width_emu) if slide_width_emu else int(13.333333 * 914400)
    slide_h = int(slide_height_emu)
    slide_area = max(slide_w * slide_h, 1)
    pager_floor = int(min(band_bot_in + 0.05, slide_h / 914400.0 - 0.05) * 914400)
    min_overlap = int(0.10 * 914400)
    severe_overlap = int(0.35 * 914400)
    full_bleed_area = 0.85
    full_height_frac = 0.90
    # Label-like prefixes only — body text containing「来源」must not count (agenda FP)
    ann_pat = re.compile(
        r"(?:^|\n)\s*(结论|SO\s*WHAT|口径\s*[:：]?|来源\s*[:：]|数据来源\s*[:：]|"
        r"Source\s*[:：]|Note\s*[:：]|footnote|注\s*[:：])",
        re.IGNORECASE,
    )

    def _text(el: ET.Element) -> str:
        return (text_content(el) or "").strip()

    def _has_txbody(el: ET.Element) -> bool:
        # 命名空间无关：是否存在 p:txBody 后代（文本框）
        for d in el.iter():
            if isinstance(d.tag, str) and d.tag.rsplit("}", 1)[-1] == "txBody":
                return True
        return False

    def _is_chrome_or_bg(y: int, cy: int, cx: int) -> bool:
        if (cx * cy) / slide_area >= full_bleed_area and y <= int(0.05 * 914400):
            return True
        if cy >= int(full_height_frac * slide_h) and y <= int(0.05 * 914400):
            return True
        if y >= band_bot - int(0.02 * 914400):
            return True
        if y >= pager_floor:
            return True
        return False

    def _is_bar_like(cy: int, cx: int) -> bool:
        return cy <= int(0.75 * 914400) and cx >= int(0.45 * slide_w)

    def _is_note_like(y: int, cy: int, text: str) -> bool:
        return y >= note_y - int(0.05 * 914400) and cy <= int(0.55 * 914400) and bool(text)

    def _at_so_what_slot(y: int) -> bool:
        # Engine locks so-what to soWhatY; agenda trailing rows sit lower (~+0.12)
        return abs(y - so_what_y) <= int(0.08 * 914400)

    def _is_annotation_self(y: int, cy: int, cx: int, text: str) -> bool:
        """so-what / footnote / source row living in the annotation zone."""
        if _at_so_what_slot(y) and cy <= int(0.85 * 914400):
            # Fill rect, accent strip, or 结论条正文 — all live in the slot
            if ann_pat.search(text) or _is_bar_like(cy, cx) or cx <= int(0.15 * 914400):
                return True
        if _is_note_like(y, cy, text):
            return True
        # Entirely inside the nominal withNote band (6.40 口径)
        if y >= nominal_band_top - int(0.02 * 914400):
            return True
        return False

    has_annotation = False
    has_so_what = False
    for el in elements:
        box = shape_bounds(el)
        if box is None:
            continue
        _x, y, cx, cy = box
        if cx <= 0 or cy <= 0:
            continue
        if _is_chrome_or_bg(y, cy, cx):
            continue
        txt = _text(el)
        note_like = _is_note_like(y, cy, txt)
        labeled = bool(ann_pat.search(txt))
        bar = _is_bar_like(cy, cx)
        # Fill rect sits on soWhatY (±0.02); 结论条正文 may sit slightly below
        on_fill = abs(y - so_what_y) <= int(0.02 * 914400) and bar
        labeled_slot = labeled and _at_so_what_slot(y) and cy <= int(0.85 * 914400)
        if note_like:
            has_annotation = True
        elif labeled_slot or on_fill:
            has_annotation = True
            has_so_what = True

    if has_so_what:
        band_top_in = min(nominal_band_top_in, so_what_y_in)
        band_top = int(band_top_in * 914400)

    # Pass 2: body invaders that START ABOVE the band and crush down (D9: all of them)
    for el in elements:
        box = shape_bounds(el)
        if box is None:
            continue
        x, y, cx, cy = box
        if cx <= 0 or cy <= 0:
            continue
        bottom = y + cy
        if _is_chrome_or_bg(y, cy, cx):
            continue
        if _is_annotation_self(y, cy, cx, _text(el)):
            continue
        # Crush-from-above only: top must sit above band_top
        if y >= band_top - int(0.02 * 914400):
            continue
        if bottom <= band_top:
            continue
        overlap = min(bottom, band_bot) - band_top
        if overlap < min_overlap:
            continue
        # 无注释页文本框底框到 contentBottom 是引擎有意为之（框内无墨水侵入注释带），
        # severe 安全网仅对非文本形状保留（feedback gate 用例 3：无 txBody 形状仍触发）。
        if has_annotation or (overlap >= severe_overlap and not _has_txbody(el)):
            out.append(issue(
                "ANNOTATION_BAND_OVERLAP",
                f"主内容侵入注释带（元素底边 {bottom/914400:.2f}in 越过注释带顶 "
                f"{band_top_in:.2f}in，重叠 {overlap/914400:.2f}in）——"
                "图例/系列请收入主图区或压缩系列数，禁止压进结论条/来源行。",
                slide=slide_no,
            ))
    return out


# ── R6：元素两两重叠（本次诊断 31 处节点叠印 + 2 处整条结论叠印均漏检） ──
# 面积阈值 0.05 in²；同页 >3 处升为硬失败。chrome/背景/注释带自身豁免。
ELEMENT_OVERLAP_MIN_AREA_IN2 = 0.05
ELEMENT_OVERLAP_MAX_PER_SLIDE = 3


def _is_full_bleed_or_bg(box: tuple[int, int, int, int], width: int, height: int) -> bool:
    """整页/大面积底衬：不参与两两重叠判定。"""
    x, y, cx, cy = box
    return cx * cy >= 0.85 * width * height


def element_overlap_check(
    elements: list[ET.Element],
    slide_no: int,
    width: int,
    height: int,
) -> list[dict[str, Any]]:
    """元素两两重叠（ELEMENT_OVERLAP）。

    收集所有可测元素的包围盒，跳过整页背景 / 页码 chrome / 注释带自身
    （tr:soWhat / tr:footnote / tr:band），以及页头区（眉题/标题/装饰线，y < 2.0in）
    ——页头元素上下紧邻是版式语义，不是叠印。只对正文区（y ≥ 2.0in）元素做两两相交判定。
    同页超过 ELEMENT_OVERLAP_MAX_PER_SLIDE 处时在末条 issue 标注「密集叠印」。
    """
    out: list[dict[str, Any]] = []
    boxes: list[tuple[tuple[int, int, int, int], str]] = []
    min_area = int(ELEMENT_OVERLAP_MIN_AREA_IN2 * 914400 * 914400)
    head_limit = int(2.0 * 914400)  # 页头区下界：眉题 0.48 / 标题 0.82 / 装饰线 1.72
    for el in elements:
        box = shape_bounds(el)
        if box is None:
            continue
        if _is_full_bleed_or_bg(box, width, height):
            continue
        x, y, cx, cy = box
        # 页头/页码 chrome 不参与正文叠印判定
        if y + cy <= head_limit:
            continue
        oname = (_shape_object_name(el) or "")
        # 注释带自身（结论条/来源/待核实条）不参与互撞——它们共用槽位由引擎互斥
        if any(k in oname for k in ("soWhat", "footnote", "tr:band", "tr:flag")):
            continue
        text = text_content(el).strip()
        label = (text[:14] + "…") if len(text) > 14 else (text or oname or "shape")
        boxes.append((box, label))

    hits = 0
    for i in range(len(boxes)):
        (ax, ay, aw, ah), la = boxes[i]
        for j in range(i + 1, len(boxes)):
            (bx, by, bw, bh), lb = boxes[j]
            ox = min(ax + aw, bx + bw) - max(ax, bx)
            oy = min(ay + ah, by + bh) - max(ay, by)
            if ox <= 0 or oy <= 0:
                continue
            area = ox * oy
            if area < min_area:
                continue
            # 纯包含（一方完全罩住另一方）多半是卡片+内文，不算叠印
            if (ax >= bx and ay >= by and ax + aw <= bx + bw and ay + ah <= by + bh) or \
               (bx >= ax and by >= ay and bx + bw <= ax + aw and by + bh <= ay + ah):
                continue
            # 短标签 + 长正文共处一卡（title+body 紧排）不算叠印：两者水平对齐且纵向仅微碰
            short_long = (len(la) <= 12) != (len(lb) <= 12)
            v_touch = oy < int(0.12 * 914400)  # 纵向重叠 <0.12in 视为基线紧排
            if short_long and v_touch:
                continue
            # 两个都是短标签/数值（图表轴标签、指标值、图例文字）：数据展示的常规紧排，不是叠印
            if len(la) <= 12 and len(lb) <= 12:
                continue
            hits += 1
            out.append(issue(
                "ELEMENT_OVERLAP",
                f"元素叠印：「{la}」∩「{lb}」重叠 {area / (914400 * 914400):.2f}in²"
                f"（≥{ELEMENT_OVERLAP_MIN_AREA_IN2}in²）——请错开坐标或合并为同一文本框。",
                slide=slide_no,
            ))
    if hits > ELEMENT_OVERLAP_MAX_PER_SLIDE:
        out.append(issue(
            "ELEMENT_OVERLAP",
            f"同页元素叠印 {hits} 处（>{ELEMENT_OVERLAP_MAX_PER_SLIDE}）——几何算法与内容量脱钩，需重构布局。",
            slide=slide_no,
        ))
    return out


def layout_fill_check(
    bounds: list[tuple[int, int, int, int]],
    slide_no: int,
    width: int,
    height: int,
    is_structural: bool = False,
) -> list[dict[str, Any]]:
    """版心填充率（LAYOUT_FILL）：宽、高分别算，低于下限告警。

    structural 页（封面/大纲/收尾/引用）豁免——它们本来就是留白页。
    目标带取 layout-constants.json 的 layoutSystem.fillTarget（按模式），
    这里用「包围盒占画布比」的宽高分量做保守近似。
    """
    out: list[dict[str, Any]] = []
    if is_structural or not bounds:
        return out
    try:
        lc_path = Path(__file__).resolve().parent / "layout-constants.json"
        lc = json.loads(lc_path.read_text(encoding="utf-8"))
        ft = ((lc.get("layoutSystem") or {}).get("fillTarget") or {})
        # 默认取 research 带（最常见研究报告）
        target = ft.get("research") or [70, 85]
        fill_min = float(target[0]) / 100.0
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        fill_min = 0.55

    left = min(x for x, _, _, _ in bounds)
    top = min(y for _, y, _, _ in bounds)
    right = max(x + cx for x, _, cx, _ in bounds)
    bottom = max(y + cy for _, y, _, cy in bounds)
    w_fill = max(0.0, (right - left) / max(width, 1))
    h_fill = max(0.0, (bottom - top) / max(height, 1))
    # 硬下限 0.55（诊断口径），目标带下限作 WARN
    hard_min = 0.55
    if w_fill < hard_min or h_fill < hard_min:
        out.append(issue(
            "LAYOUT_FILL",
            f"版心填充不足（宽 {w_fill:.0%} / 高 {h_fill:.0%}，硬下限 {hard_min:.0%}）——"
            "多栏请按版心推导列宽，低密度页补从件（指标/小图/对照表）。",
            slide=slide_no,
        ))
    elif w_fill < fill_min or h_fill < fill_min:
        out.append(issue(
            "LAYOUT_FILL",
            f"版心填充偏低（宽 {w_fill:.0%} / 高 {h_fill:.0%}，目标下限 {fill_min:.0%}）。",
            slide=slide_no,
        ))
    return out



def font_size_snap_check(root: ET.Element, slide_no: int) -> list[dict[str, Any]]:
    """Font sizes must sit on the declared type scale / fontShrink ladder.

    fitFont already selects from the ladder; this gate catches callers that
    arithmetic-shift sizes (e.g. fz-1) or hardcode off-ladder values without
    re-snapping through the ladder / modeSize path.

    Allowed set = containers.fontShrink.ladder ∪ typeScale ∪ all modeTypeScale
    roles ∪ a small cover/hero display whitelist. Intentional h2 (17pt) and
    other mode roles must pass; off-ladder 11.3pt etc. must still fail.
    """
    out: list[dict[str, Any]] = []
    try:
        lc_path = Path(__file__).resolve().parent / "layout-constants.json"
        lc = json.loads(lc_path.read_text(encoding="utf-8"))
        ladder = ((lc.get("containers") or {}).get("fontShrink") or {}).get("ladder") or []
        allowed = {round(float(v), 2) for v in ladder}
        scale_sources: list[Any] = [lc.get("typeScale") or {}]
        mts = lc.get("modeTypeScale") or {}
        if isinstance(mts, dict):
            scale_sources.extend(v for v in mts.values() if isinstance(v, dict))
        for src in scale_sources:
            if not isinstance(src, dict):
                continue
            for key, val in src.items():
                if str(key).startswith("$"):
                    continue
                try:
                    allowed.add(round(float(val), 2))
                except (TypeError, ValueError):
                    continue
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        allowed = {15, 14, 13.5, 13, 12.5, 12, 11.5, 11, 10.5, 10, 9.5, 9, 8.5}
        allowed |= {44, 36, 30, 22, 19, 18, 17, 14, 13, 11, 10, 8.5}
    # Cover/hero intermediate display sizes (not every mode lists every step)
    allowed |= {28, 24, 22, 20, 16, 8.0, 7.5}
    alien: list[float] = []
    for run in root.findall(".//a:r", NS):
        text = "".join(t.text or "" for t in run.findall("a:t", NS))
        if not text.strip():
            continue
        pr = run.find("a:rPr", NS)
        raw = pr.get("sz") if pr is not None else None
        if raw is None:
            continue
        try:
            pt = int(raw) / 100.0
        except (TypeError, ValueError):
            continue
        if round(pt, 2) not in allowed and abs(pt * 2 - round(pt * 2)) > 0.01:
            alien.append(pt)
        elif round(pt, 2) not in allowed:
            # On 0.5 grid but not on declared ladder / display set — still flag
            # when far from any allowed value (>0.26pt)
            if min(abs(pt - a) for a in allowed) > 0.26:
                alien.append(pt)
    if alien:
        out.append(issue(
            "FONT_SIZE_NOT_SNAPPED",
            f"页内出现未对齐字号阶梯的字号 {sorted(set(round(v,2) for v in alien))[:8]}——"
            "fitFont/modeSize 须回落到 containers.fontShrink.ladder（或封面展示档）。",
            slide=slide_no,
        ))
    return out


@lru_cache(maxsize=1)
def _containers_cfg() -> dict[str, Any]:
    """容器内边距与锚点容差（单源 scripts/layout-constants.json 的 containers / anchorTolerance）。"""
    lc_path = Path(__file__).resolve().parent / "layout-constants.json"
    try:
        lc = json.loads(lc_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"pad": {}, "minPad": 0.06, "anchorKeyPx": 6, "fontShrink": {},
                "lineFactor": LINE_FACTOR, "emAsciiRatio": EM_ASCII_RATIO}
    cont = lc.get("containers") or {}
    anch = lc.get("anchorTolerance") or {}
    tm = cont.get("textMetrics") or {}
    return {
        "pad": cont.get("pad") or {},
        "minPad": float(cont.get("minPad") or 0.06),
        "anchorKeyPx": float(anch.get("keyPx") or 6),
        "fontShrink": cont.get("fontShrink") or {},
        "overflowRule": cont.get("overflowRule") or "",
        "lineFactor": float(tm.get("lineFactor") or LINE_FACTOR),
        "emAsciiRatio": float(tm.get("emAsciiRatio") or EM_ASCII_RATIO),
    }


def _shape_object_name(shape: ET.Element) -> str:
    el = shape.find(".//p:cNvPr", NS)
    return (el.get("name") if el is not None else "") or ""


def _infer_container_pad(shape: ET.Element, pad_map: dict[str, float], min_pad: float) -> tuple[float, str]:
    """推断容器类型，返回 (pad_in, kind)。

    优先读引擎写入的 objectName（`tr:<kind>`，见 build_pptx.js trName）；
    未标注时回落 minPad——文本框坐标通常已由引擎 inset，再按 card/panel 大 pad
    扣会双重计算，导致误报。仅在显式标注 soWhat/band/card/… 时才用对应 pad。
    """
    name = _shape_object_name(shape)
    kind = ""
    if name.startswith("tr:"):
        kind = name[3:].split("|")[0].strip()
    if kind and kind in pad_map:
        return float(pad_map[kind]), kind
    if kind:
        return min_pad, kind
    # 启发式兜底：仅对明确的结论条 / 待核实文本用对应 pad（其余 minPad）
    text = text_content(shape)
    # Legacy "SO WHAT" label OR tr:soWhat already handled above; keep SO WHAT for old files
    if "SO WHAT" in text or "结论条" in text:
        return float(pad_map.get("soWhat") or min_pad), "soWhat"
    if "待核实" in text:
        return float(pad_map.get("band") or min_pad), "band"
    return min_pad, "text"


def container_overflow_check(shape: ET.Element, slide_no: int) -> list[dict[str, Any]]:
    """容器级溢出：文字不得越过**归属容器**边界——即使没超出页面画布。

    容器类型优先来自引擎 objectName（tr:<kind>）；无标注时按 minPad 安全边距判定。
    溢出处置：优先优化内容（列表化/精炼/拆页/换组合），其次调整容器，最后才是有限缩字号。
    """
    out: list[dict[str, Any]] = []
    cfg = _containers_cfg()
    pad_map = cfg["pad"] or {}
    min_pad = cfg["minPad"]
    pad, kind = _infer_container_pad(shape, pad_map, min_pad)
    box = shape_bounds(shape)
    if box is None:
        return out
    _, _, cx, cy = box
    w_in = cx / 914400 - 2 * pad
    h_in = cy / 914400 - 2 * pad
    if w_in <= 0.05 or h_in <= 0.02:
        return out
    lf = cfg["lineFactor"]
    for para in shape.findall(".//a:p", NS):
        line = "".join((t.text or "") for t in para.findall(".//a:t", NS))
        if not line.strip():
            continue
        sizes = font_sizes_pt(para)
        fz = min(sizes) if sizes else 12.0
        est_w = est_text_width_in(line, fz)
        lines_avail = max(1, int(h_in / (fz / 72.0 * lf)))
        capacity = w_in * lines_avail
        if est_w > capacity * TEXT_OVERFLOW_TOLERANCE:
            out.append(issue(
                "CONTAINER_OVERFLOW",
                f'文本越过归属容器（{kind}，已扣内边距 {pad:.2f}in）："{line[:18]}…" '
                f'估算 {est_w:.1f}in > 容器可用 {capacity:.1f}in。'
                f'处置：①列表化/精炼 ②调容器/换行/拆页 ③有限缩字号（floor 见 containers.fontShrink）。',
                slide=slide_no,
            ))
    return out


def table_checks(table: ET.Element, slide_no: int) -> list[dict[str, Any]]:
    """表格语义字号与密度。

    - TABLE_SEMANTIC_TYPE：句子型单元格（≥12 字）不得用 micro 档字号（≤9.5pt）。
    - TABLE_DENSITY：单元格大面积空洞（空单元格占比 >0.6 且总数 ≥12）——字号没低于下限但版面塌陷。
    """
    out: list[dict[str, Any]] = []
    cells = table.findall(".//a:tc", NS)
    if not cells:
        return out
    empty = 0
    for cell in cells:
        text = text_content(cell).strip()
        if not text:
            empty += 1
            continue
        sizes = font_sizes_pt(cell)
        if sizes and len(text) >= 12 and min(sizes) <= 9.5:
            out.append(issue(
                "TABLE_SEMANTIC_TYPE",
                f'表格句子型内容（{len(text)} 字）用了 micro 档字号 {min(sizes):.1f}pt：'
                "表格正文/行动项/解释句必须 T7/T10（body 档），T11 仅限轴标签/单位/列短标签。",
                slide=slide_no,
            ))
    if len(cells) >= 12 and empty / len(cells) > 0.6:
        out.append(issue(
            "TABLE_DENSITY",
            f"表格 {len(cells)} 个单元格中 {empty} 个为空（{empty / len(cells):.0%}）——"
            "表格密度与内容不匹配（阅读重心塌陷）；请精简行列或换承载形态。",
            slide=slide_no,
        ))
    return out


def continuous_text_flow_check(shapes: list[ET.Element], slide_no: int) -> list[dict[str, Any]]:
    """连续文本流（深度模式）：语义连续句不得拆成多个独立文本框。

    启发式：同一水平带上紧邻（间距 <0.06in）的两个文本框，前框以非句末标点结尾且后框以
    非标点/非数字开头、字号相同 → 判定为可能被拆分的连续句（应改用同一文本框内富文本）。
    """
    out: list[dict[str, Any]] = []
    items = []
    for shape in shapes:
        text = text_content(shape)
        box = shape_bounds(shape)
        if not text or box is None:
            continue
        sizes = font_sizes_pt(shape)
        items.append((box, text, (min(sizes) if sizes else 12.0)))
    tail_re = re.compile(r"[^\s。！？；：!?;:）)】」”\"]$")
    head_re = re.compile(r"^[^，。！？；：、,.;:!?）)】」”\"0-9]")
    # 只判「句」不判「标签」：两侧都必须是句长文本（轴标签/图例/矩阵行头一律排除）
    MIN_SENTENCE_CHARS = 12
    for i, (box_a, text_a, sz_a) in enumerate(items):
        if len(text_a) < MIN_SENTENCE_CHARS:
            continue
        ax, ay, aw, ah = box_a
        for box_b, text_b, sz_b in items[i + 1:]:
            if len(text_b) < MIN_SENTENCE_CHARS:
                continue
            bx, by, bw, bh = box_b
            if abs(sz_a - sz_b) > 0.6:
                continue
            # 同一水平带（纵向重叠 >50%）且后框紧跟在右
            overlap = min(ay + ah, by + bh) - max(ay, by)
            if overlap < min(ah, bh) * 0.5:
                continue
            gap = bx - (ax + aw)
            if -0.02 * 914400 < gap < 0.06 * 914400:
                if tail_re.search(text_a) and head_re.match(text_b):
                    out.append(issue(
                        "CONTINUOUS_TEXT_FLOW",
                        f'疑似拆分连续句："{text_a[-10:]}" + "{text_b[:10]}"（同一水平带紧邻的两个文本框）——'
                        "语义连续句应放在同一文本框内用富文本高亮。",
                        slide=slide_no,
                    ))
                    break
    return out


def skill_version() -> str:
    """技能版本（单源 layout-constants.json 的 version）——manifest 不再手写版本号。"""
    lc_path = Path(__file__).resolve().parent / "layout-constants.json"
    try:
        lc = json.loads(lc_path.read_text(encoding="utf-8"))
        return str(lc.get("version") or "0.0")
    except (OSError, json.JSONDecodeError):
        return "0.0"


def page_margin_in() -> float:
    """版心左边界（英寸，layout-constants.json 的 page.mx）。"""
    lc_path = Path(__file__).resolve().parent / "layout-constants.json"
    try:
        lc = json.loads(lc_path.read_text(encoding="utf-8"))
        return float((lc.get("page") or {}).get("mx") or 0.6)
    except (OSError, json.JSONDecodeError):
        return 0.6


def _image_spec() -> dict[str, Any]:
    """素材图片规格与配图占位约定（单源 layout-constants.json 的 imageSpec）。"""
    lc_path = Path(__file__).resolve().parent / "layout-constants.json"
    try:
        lc = json.loads(lc_path.read_text(encoding="utf-8"))
        spec = lc.get("imageSpec") or {}
        return spec if isinstance(spec, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def title_anchor_info(shapes: list[ET.Element]) -> dict[str, Any] | None:
    """页头标题锚点信息（最大字号的靠上文本块）：用于锚点检查与 manifest 登记。"""
    best = None
    for shape in shapes:
        text = text_content(shape)
        box = shape_bounds(shape)
        if not text or box is None or len(text) < 6:
            continue
        sizes = font_sizes_pt(shape)
        fz = max(sizes) if sizes else 0.0
        if fz < 18:            # 只锚定页头标题（大字号）
            continue
        if best is None or box[1] < best[0][1]:
            best = (box, text, fz)
    if best is None:
        return None
    (bx, by, bw, bh), text, fz = best
    mx = page_margin_in()
    return {
        "text": text[:40],
        "left_in": round(bx / 914400, 4),
        "top_in": round(by / 914400, 4),
        "font_pt": fz,
        "expected_left_in": mx,
        "delta_in": round(bx / 914400 - mx, 4),
        "tolerance_in": round(_containers_cfg()["anchorKeyPx"] / 96, 4),
    }



def chrome_footer_y_in(shapes: list[ET.Element], height: int) -> float | None:
    """页码 chrome y（英寸）：只认页码形文本（如 3 / 14），避免把 so-what/图注当页脚。"""
    zones = ((json.loads(Path(__file__).with_name("layout-constants.json").read_text(encoding="utf-8"))
              .get("layoutSystem") or {}).get("zones") or {})
    chrome = zones.get("chromePct") or [18, 24]
    bottom_frac = float(chrome[1] if isinstance(chrome, list) and len(chrome) > 1 else 24) / 100.0
    threshold = int(height * (1.0 - bottom_frac))
    ys: list[float] = []
    # Engine footer is always "N / M"; bare integers are chart/exhibit labels (CHROME_DRIFT FP)
    pager = re.compile(r"^\s*\d+\s*/\s*\d+\s*$")
    for shape in shapes:
        text = (text_content(shape) or "").strip()
        box = shape_bounds(shape)
        if not text or box is None:
            continue
        _x, y, _cx, _cy = box
        if y < threshold:
            continue
        if not pager.match(text):
            continue
        sizes = font_sizes_pt(shape)
        if sizes and max(sizes) > 14:
            continue
        ys.append(y / 914400.0)
    if not ys:
        return None
    return round(sum(ys) / len(ys), 4)


def anchor_check(shapes: list[ET.Element], slide_no: int, width: int) -> list[dict[str, Any]]:
    """空间锚点注册（深度模式）：标题/页头块的左边距必须对齐版心左边界。

    容差取自 layout-constants.json 的 anchorTolerance.keyPx（默认 6px @96dpi ≈ 0.0625in）；
    这是"相对位置还原"的确定性代理——不需要参考图即可复现。
    """
    out: list[dict[str, Any]] = []
    info = title_anchor_info(shapes)
    if info is None:
        return out
    if abs(info["delta_in"]) > info["tolerance_in"]:
        out.append(issue(
            "ANCHOR_TITLE_MISALIGNED",
            f'页头标题左边距 {info["left_in"]:.3f}in 偏离版心左边界 {info["expected_left_in"]:.3f}in'
            f'（偏差 {info["delta_in"]:+.3f}in > 容差 {info["tolerance_in"]:.3f}in）："{info["text"][:16]}…"',
            slide=slide_no,
        ))
    return out


def inspect_slide(
    root: ET.Element,
    slide_number: int,
    width: int,
    height: int,
    deep: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    warnings: list[dict[str, Any]] = []
    shapes = root.findall(".//p:sp", NS)
    pictures = root.findall(".//p:pic", NS)
    graphic_frames = root.findall(".//p:graphicFrame", NS)
    charts = root.findall(".//c:chart", NS)
    tables = root.findall(".//a:tbl", NS)

    native_text_shapes = sum(1 for shape in shapes if text_content(shape))
    all_elements = [*shapes, *pictures, *graphic_frames]
    bounds: list[tuple[int, int, int, int]] = []
    slide_area = max(width * height, 1)
    font_sizes = [size for shape in shapes for size in font_sizes_pt(shape)]
    picture_area_ratios: list[float] = []
    margin_emu = int(MIN_EDGE_MARGIN_IN * 914400)

    # 图标语义图（objectName `icon:` 前缀）单独计数：不进 pictures 内容图门禁
    def _is_icon_pic(el) -> bool:
        nv = el.find('.//p:cNvPr', NS)
        name = (nv.get('name') if nv is not None else '') or ''
        return name.startswith('icon:')
    icon_pictures = [p for p in pictures if _is_icon_pic(p)]
    content_pictures = [p for p in pictures if not _is_icon_pic(p)]

    for element in all_elements:
        box = shape_bounds(element)
        if box is None:
            continue
        bounds.append(box)
        x, y, cx, cy = box
        if cx <= 0 or cy <= 0 or x < 0 or y < 0:
            warnings.append(
                issue(
                    "INVALID_SHAPE_BOUNDS",
                    "元素尺寸非正或坐标为负；PowerPoint 可能判为损坏文件。",
                    slide=slide_number,
                )
            )
        # 越界判定带安全边距：贴边/超出画布都会在导出/打印时被裁切
        if x < -margin_emu or y < -margin_emu or \
           x + cx > width + margin_emu or y + cy > height + margin_emu:
            warnings.append(
                issue(
                    "SHAPE_OUTSIDE_SLIDE",
                    f"元素超出 {width // 914400}×{height // 914400}in 画布（每页高度稳定的硬约束：内容不得越界）。",
                    slide=slide_number,
                )
            )

    for shape in shapes:
        warnings.extend(text_overflow_check(shape, slide_number))
        warnings.extend(text_overflow_vertical_check(shape, slide_number))
        warnings.extend(container_overflow_check(shape, slide_number))

    warnings.extend(annotation_band_overlap_check(
        [*shapes, *pictures, *graphic_frames], slide_number, height, width))
    # R6：元素两两重叠（节点叠印 / 结论条叠印漏检主因）
    warnings.extend(element_overlap_check(
        [*shapes, *pictures, *graphic_frames], slide_number, width, height))
    warnings.extend(font_size_snap_check(root, slide_number))

    for table in tables:
        warnings.extend(table_checks(table, slide_number))

    if deep:
        warnings.extend(continuous_text_flow_check(shapes, slide_number))
        warnings.extend(anchor_check(shapes, slide_number, width))

    combined_text = " ".join(filter(None, (text_content(shape) for shape in shapes)))
    if PLACEHOLDER_RE.search(combined_text):
        warnings.append(
            issue("PLACEHOLDER_TEXT", "页面上残留作者占位符文本（TODO/TBD/Click to add 等）。",
                  slide=slide_number)
        )

    for picture in pictures:
        box = shape_bounds(picture)
        if box is None:
            continue
        _, _, cx, cy = box
        ratio = max(0.0, (cx * cy) / slide_area)
        picture_area_ratios.append(ratio)
        if ratio >= FULL_SLIDE_IMAGE_RATIO:
            warnings.append(
                issue("FULL_SLIDE_BACKGROUND_RISK",
                      "单张图片覆盖 ≥90% 页面（整页底图风险；TopPPT HTML 交付基线为全原生可编辑）。",
                      slide=slide_number)
            )
        elif ratio >= LARGE_IMAGE_AREA_RATIO:
            warnings.append(
                issue("UNJUSTIFIED_LARGE_IMAGE",
                      "单张图片覆盖 ≥40% 页面（TopPPT HTML 要求零图片，请改为原生形状/图表）。",
                      slide=slide_number)
            )

    total_picture_area_ratio = round(min(sum(picture_area_ratios), 1.0), 4)
    max_picture_area_ratio = round(max(picture_area_ratios, default=0.0), 4)

    if font_sizes:
        min_font_size = min(font_sizes)
        max_font_size = max(font_sizes)
        if min_font_size < GLOBAL_MIN_FONT_PT:
            warnings.append(
                issue("FONT_SIZE_BELOW_FOOTER_MIN",
                      f"存在 {min_font_size:.1f}pt 文本；全篇下限 {GLOBAL_MIN_FONT_PT:.1f}pt。",
                      slide=slide_number)
            )
    else:
        min_font_size = None
        max_font_size = None

    if bounds:
        left = min(x for x, _, _, _ in bounds)
        top = min(y for _, y, _, _ in bounds)
        right = max(x + cx for x, _, cx, _ in bounds)
        bottom = max(y + cy for _, y, _, cy in bounds)
        coverage = max(0.0, min(1.0, ((right - left) * (bottom - top)) / slide_area))
        right_gap = max(0, width - right) / max(width, 1)
        bottom_gap = max(0, height - bottom) / max(height, 1)
        # v9：任一轴留白过大即失衡（原「右+下同时」过严，漏掉上重下空等截图问题）
        if (right_gap > UNBALANCED_GAP_RATIO or bottom_gap > UNBALANCED_GAP_RATIO) and len(all_elements) >= 2:
            warnings.append(
                issue("UNBALANCED_EMPTY_SPACE",
                      f"留白失衡（右 {right_gap:.0%} / 下 {bottom_gap:.0%}，阈值 {UNBALANCED_GAP_RATIO:.0%}）。",
                      slide=slide_number)
            )
    else:
        coverage = 0.0
        warnings.append(
            issue("EMPTY_OR_UNMEASURABLE_SLIDE", "页面没有任何可测量的原生元素。", slide=slide_number)
        )

    # R6：版心填充率（宽/高分别算；封面/大纲/收尾等结构页豁免）
    _struct_text = combined_text[:200] if combined_text else ""
    _is_struct = bool(re.search(r"(报告大纲|AGENDA|下一步|参考资料|封面)", _struct_text)) or slide_number <= 2
    warnings.extend(layout_fill_check(bounds, slide_number, width, height, is_structural=_is_struct))

    if len(all_elements) <= 1 and not pictures:
        warnings.append(
            issue("LOW_CONTENT_DENSITY", "页面元素 ≤1 个；检查信息密度。", slide=slide_number)
        )

    if native_text_shapes >= 2 and len(combined_text) < 25 and not pictures:
        warnings.append(
            issue("LOW_TEXT_DENSITY", "多个文本框但总字符 <25；信息密度不足。", slide=slide_number)
        )

    if re.search(r"EXHIBIT\s*\d", combined_text, re.IGNORECASE):
        has_conclusion_bar = False
        for el in all_elements:
            oname = _shape_object_name(el)
            if "soWhat" in (oname or ""):
                has_conclusion_bar = True
                break
            box = shape_bounds(el)
            if box is None:
                continue
            _x, y, cx, cy = box
            # Wide fill at soWhatY ≈ 6.05in (MD3 结论条衬底)
            if abs(y / 914400 - 6.05) <= 0.08 and cx / 914400 >= 6.0 and cy / 914400 <= 0.85:
                has_conclusion_bar = True
                break
        if not has_conclusion_bar and "SO WHAT" not in combined_text:
            warnings.append(
                issue("EXHIBIT_PAGE_MISSING_SOWHAT",
                      "页面带 Exhibit 编号但没有结论条（research R2 版式 · MD3 衬条）。",
                      slide=slide_number)
            )

    # v9：HTML 标签源码泄漏进 PPTX 文本（模型字段未净化时原样露出）
    tag_leaks = re.findall(
        r"</?(?:a|strong|span|div|em|p)\b[^>]{0,40}|class=[\"']cite[\"']|href=",
        combined_text, re.IGNORECASE)
    if tag_leaks:
        warnings.append(
            issue("HTML_TAG_IN_TEXT",
                  f"文本含 HTML 标签源码泄漏 {tag_leaks[:3]}（模型字段须纯文本，引用写 [n]）。",
                  slide=slide_number)
        )

    # v9：标题空页（去页码/页眉后几乎无正文）
    body_chars = len(re.sub(r"\s+", "", combined_text))
    # 页码形如 "3 / 22" 或纯数字
    body_wo_pager = re.sub(r"\b\d+\s*/\s*\d+\b", "", combined_text)
    body_wo_pager = re.sub(r"^\s*\d+\s*$", "", body_wo_pager, flags=re.M)
    if body_chars < 40 and native_text_shapes <= 2 and not pictures and not tables and not charts:
        warnings.append(
            issue("TITLE_ONLY_PAGE",
                  f"页面可测文本仅 {body_chars} 字且无图/表/图表（疑似只有标题）。",
                  slide=slide_number)
        )

    metrics = {
        "slide": slide_number,
        "native_text_shapes": native_text_shapes,
        "native_graphic_shapes": len(shapes) + len(graphic_frames),
        "pictures": len(content_pictures),
        "icon_pictures": len(icon_pictures),
        "charts": len(charts),
        "tables": len(tables),
        "element_count": len(all_elements),
        "coverage_ratio": round(coverage, 4),
        "picture_area_ratio": total_picture_area_ratio,
        "max_picture_area_ratio": max_picture_area_ratio,
        "min_font_size_pt": round(min_font_size, 2) if min_font_size is not None else None,
        "max_font_size_pt": round(max_font_size, 2) if max_font_size is not None else None,
        "font_sizes_pt": sorted({round(v, 2) for v in _all_run_sizes(root)}),
        "text_characters": len(combined_text),
        "anchor": title_anchor_info(shapes),
        "chrome_footer_y_in": chrome_footer_y_in(shapes, height),
    }
    return metrics, warnings


def _norm_text(value: str) -> str:
    """比较前去除所有空白（PPTX 文本跨 run 拼接可能插空格/换行）。"""
    return "".join((value or "").split())


def _model_probe_strings(section: dict[str, Any], limit: int = 12) -> list[str]:
    """高保真探针：抽取 section 的代表性文本串（≥6 字，剔除色值等非渲染字段值）。"""
    probes: list[str] = []

    def walk(node: Any) -> None:
        if len(probes) >= limit:
            return
        if isinstance(node, dict):
            for key, child in node.items():
                if key in _PROBE_SKIP_KEYS:
                    continue
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            text = node.strip()
            if len(text) >= 6 and not text.startswith("#"):
                probes.append(text)

    walk(section)
    return probes


def slide_bg_color(slide_root: ET.Element) -> str | None:
    """取幻灯片背景色（精导固定写 p:bg/a:solidFill/a:srgbClr）。"""
    for node in slide_root.findall(".//p:bg//a:srgbClr", NS):
        value = (node.get("val") or "").strip()
        if value:
            return value.upper()
    return None


def validate_model_theme(
    model: dict[str, Any] | None,
    slide_bgs: list[str | None],
) -> list[dict[str, Any]]:
    """主题一致性：PPTX 实际背景 token 与 model.style × model.theme 对照
    （防 HTML 与 PPTX 亮暗不一致；封面/金句/收尾用 accent/ink 全幅底，天然不命中任一 token，不误报）。"""
    warnings: list[dict[str, Any]] = []
    if not model or not slide_bgs:
        return warnings
    style = str(model.get("style") or "").strip()
    theme = str(model.get("theme") or "light").strip().lower()
    if not style or theme not in {"light", "dark"}:
        return warnings
    lc_path = Path(__file__).resolve().parent / "layout-constants.json"
    try:
        lc = json.loads(lc_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return warnings
    light_bg = str(((lc.get("styles") or {}).get(style) or {}).get("bg") or "").upper()
    dark_bg = str(((lc.get("stylesDark") or {}).get(style) or {}).get("bg") or "").upper()
    if not light_bg and not dark_bg:
        return warnings
    expected = light_bg if theme == "light" else dark_bg
    opposite = dark_bg if theme == "light" else light_bg
    found = {bg for bg in slide_bgs if bg}
    if opposite and opposite in found and expected and expected not in found:
        first = next(i + 1 for i, bg in enumerate(slide_bgs) if bg == opposite)
        warnings.append(
            issue(
                "MODEL_THEME_BG_MISMATCH",
                f"model.theme={theme} 期望页面底色 {expected}，实际用了相反主题底色 {opposite}"
                "（HTML 与 PPTX 亮暗将不一致）。",
                slide=first,
            )
        )
    return warnings


_CHART_REG_CACHE: dict[str, Any] | None = None


def _chart_registry() -> dict[str, Any]:
    """图表登记四元组（单源 scripts/layout-constants.json 的 charts.registry）。"""
    global _CHART_REG_CACHE
    if _CHART_REG_CACHE is None:
        lc_path = Path(__file__).resolve().parent / "layout-constants.json"
        try:
            lc = json.loads(lc_path.read_text(encoding="utf-8"))
            reg = ((lc.get("charts") or {}).get("registry") or {})
            _CHART_REG_CACHE = {k: v for k, v in reg.items() if not str(k).startswith("$")}
        except (OSError, json.JSONDecodeError):
            _CHART_REG_CACHE = {}
    return _CHART_REG_CACHE


def _chart_channel(chart_type: str) -> str:
    """图表类型 → 交付通道（native 原生可编辑 / shape 形状还原）；未知类型按 native 保守处理。"""
    spec = _chart_registry().get(str(chart_type or "bar").lower()) or {}
    return str(spec.get("pptx") or "native")


def _chart_data_table_mode(chart: dict[str, Any]) -> str:
    """数据表策略：图表级 > 登记表默认（appendix 收敛为页内表格）。"""
    spec = _chart_registry().get(str(chart.get("type") or "bar").lower()) or {}
    mode = str(chart.get("dataTable") or spec.get("dataTable") or "notes").lower()
    return "inline" if mode == "appendix" else mode


def _section_chart(sec: dict[str, Any]) -> dict[str, Any] | None:
    """取章节页的图表对象（chart 页型 / split 右图），无则 None。"""
    st = sec.get("type") or ""
    if st in {"bar", "donut", "exhibit", "halftable"}:
        c = sec.get("chart") or {}
        if isinstance(c, dict) and c.get("labels") and c.get("values"):
            return c
    elif st == "split":
        right = sec.get("right") or {}
        if isinstance(right, dict) and (right.get("type") or "bar") != "table" \
                and right.get("labels") and right.get("values"):
            return right
    return None


def _model_chart_specs(model: dict[str, Any]) -> list[dict[str, Any]]:
    """模型里所有带数据图表的通道与数据表策略（按 charts.registry 分通道断言）。"""
    specs: list[dict[str, Any]] = []
    for sec in (model.get("sections") or []):
        if not isinstance(sec, dict):
            continue
        chart = _section_chart(sec)
        if chart is None:
            continue
        specs.append({
            "type": str(chart.get("type") or "bar").lower(),
            "channel": _chart_channel(chart.get("type") or "bar"),
            "dataTable": _chart_data_table_mode(chart),
            "pageType": sec.get("type") or "",
        })
    return specs


def validate_font_scale(model: dict[str, Any] | None,
                        slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """全篇字号必须出自该模式的 modeTypeScale（或有限缩字号阶梯）。

    字号是三模式密度契约的落地方式：任何硬编码字号或比例尺映射失灵，都会绕过
    契约而不被任何现有门禁发现（页面看上去“只是略微不同”）。
    """
    out: list[dict[str, Any]] = []
    if not model:
        return out
    lc_path = Path(__file__).resolve().parent / "layout-constants.json"
    try:
        lc = json.loads(lc_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return out
    mode = str(model.get("mode") or "presentation")
    scale = (lc.get("modeTypeScale") or {}).get(mode) or {}
    if not scale:
        return out
    ladder = ((lc.get("containers") or {}).get("fontShrink") or {}).get("ladder") or []
    allowed = {round(float(v), 2) for v in scale.values()} | {round(float(v), 2) for v in ladder}
    for s in slides:
        alien = [v for v in (s.get("font_sizes_pt") or []) if round(float(v), 2) not in allowed]
        if alien:
            out.append(issue(
                "FONT_SIZE_OFF_SCALE",
                f"第 {s['slide']} 页出现比例尺外的字号 {sorted(set(alien))}（{mode} 档允许 "
                f"{sorted(allowed)}）：字号须走 sz()/modeSize() 映射，不得硬编码。",
                slide=s["slide"]))
    return out


def _roundtrip_corpus(slide_text: str, note: str = "", chart_text: str = "") -> str:
    """往返保真比对语料 = 幻灯片形状文本 ∪ 演讲者备注 ∪ chart part 文本（去空白）。

    探针可能命中三类合法落点：版面形状、演讲者备注（note/lead/口径）、原生图表
    类别与缓存值。只比形状文本会把后两类误判成 MODEL_ROUNDTRIP_CONTENT_MISSING。
    """
    return _norm_text(" ".join(x for x in (slide_text, note, chart_text) if x))


def validate_model_roundtrip(
    model: dict[str, Any] | None,
    slide_texts: list[str],
    slide_count: int,
    chart_count: int = -1,
    allow_shape_charts: bool = False,
    slide_table_counts: list[int] | None = None,
    slide_notes: list[str] | None = None,
    slide_chart_texts: list[str] | None = None,
) -> list[dict[str, Any]]:
    """模型→PPTX 往返保真：页数结构与关键文本落位（内容不丢不串页）。
    关键串比对语料 = 形状文本 ∪ 备注 ∪ chart part（见 _roundtrip_corpus）。
    architecture 极简形态可省略 agenda（封面 + sections + 收尾）。"""
    warnings: list[dict[str, Any]] = []
    if not model:
        return warnings
    sections = [s for s in (model.get("sections") or []) if isinstance(s, dict)]
    has_agenda = bool(model.get("agenda"))
    expected = len(sections) + 2 + (1 if has_agenda else 0)  # 封面 + 大纲(可选) + sections + 收尾
    if slide_count != expected:
        warnings.append(
            issue(
                "MODEL_ROUNDTRIP_SLIDE_COUNT",
                f"模型应为 {expected} 页（封面 + {'大纲 + ' if has_agenda else ''}{len(sections)} 章节 + 收尾），"
                f"实际 {slide_count} 页。",
            )
        )
    first_sec = 3 if has_agenda else 2
    for i, sec in enumerate(sections):
        slide_no = first_sec + i
        if slide_no > len(slide_texts):
            break
        title = str(sec.get("title") or "").strip()
        if title and title not in slide_texts[slide_no - 1]:
            warnings.append(
                issue("MODEL_ROUNDTRIP_TITLE_MISSING",
                      f"第 {i + 1} 章标题「{title[:36]}」未落在第 {slide_no} 页。", slide=slide_no)
            )
        probes = _model_probe_strings(sec)
        if probes:
            slide_text = _roundtrip_corpus(
                slide_texts[slide_no - 1],
                (slide_notes[slide_no - 1] if slide_notes and slide_no - 1 < len(slide_notes) else ""),
                (slide_chart_texts[slide_no - 1]
                 if slide_chart_texts and slide_no - 1 < len(slide_chart_texts) else ""),
            )
            hits = sum(1 for p in probes if _norm_text(p) in slide_text)
            # v9：保真下限 0.80（原 0.50 放行半页截断/空白）
            min_ratio = 0.80
            try:
                lc_q = json.loads(
                    (Path(__file__).resolve().parent / "layout-constants.json")
                    .read_text(encoding="utf-8"))
                min_ratio = float((lc_q.get("qualityGates") or {}).get("roundtripMin") or 0.8)
            except Exception:
                pass
            if hits < len(probes) * min_ratio:
                warnings.append(
                    issue("MODEL_ROUNDTRIP_CONTENT_MISSING",
                          f"第 {i + 1} 章仅 {hits}/{len(probes)} 个关键串落在第 {slide_no} 页"
                          f"（内容保真 <{min_ratio:.0%}，疑似截断/空白）。",
                          slide=slide_no)
                )
    model_title = str(model.get("title") or "").strip()
    if model_title and slide_texts and model_title not in slide_texts[0]:
        warnings.append(issue("MODEL_ROUNDTRIP_COVER_TITLE", "模型封面标题未出现在第 1 页。"))
    # 原生数据图表硬门禁（按类型断言）：charts.registry 中 pptx=native 的图表必须落成
    # chart part（可编辑数据）；pptx=shape 的图表走高保真形状还原 + 数据表，不要求 chart part。
    # （allow_shape_charts=True 仅供 A 通道预览引擎回归豁免——交付通道一律要求原生图表）
    specs = _model_chart_specs(model)
    expected_native = sum(1 for s in specs if s["channel"] == "native")
    if not allow_shape_charts and chart_count >= 0 and expected_native > chart_count:
        warnings.append(
            issue(
                "MODEL_CHART_COUNT",
                f"模型含 {expected_native} 个原生通道数据图表，但 PPTX 只有 {chart_count} 个原生 chart part；"
                "原生通道图表必须是可编辑数据图表（addChart），不接受形状拼图。",
            )
        )
    # 数据可追溯硬门禁：非原生（形状还原）图表的 dataTable 不得为 off；
    # 声明 dataTable=inline 的图表，其所在页必须真的落有原生表格。
    for s in specs:
        if s["channel"] != "shape" or s["dataTable"] != "off":
            continue
        # 口径与 sync_runtime.py 一致：登记表**自身**声明 dataTable=off 的类型（纯装饰微图，
        # 如 sparkline）允许不附数据表；只有「形状通道 + 登记表默认非 off 却被显式关掉」才拦截。
        reg_default = str((_chart_registry().get(s["type"]) or {}).get("dataTable") or "notes").lower()
        if reg_default == "off":
            continue
        warnings.append(
            issue(
                "MODEL_CHART_DATATABLE",
                f"{s['pageType']} 页的 {s['type']} 图表为形状还原（非原生），"
                "dataTable 不得为 off —— 必须至少 notes（数据写入演讲者备注）保证数据可追溯。",
            )
        )
    if slide_table_counts is not None:
        for i, sec in enumerate(sections):
            slide_no = first_sec + i
            if slide_no - 1 >= len(slide_table_counts):
                break
            chart = _section_chart(sec)
            if chart is None:
                continue
            # donut 页型的图例即数据列（几何已被环形+图例占满），inline 收敛为 notes（数据入备注）
            if (sec.get("type") or "") == "donut":
                continue
            if _chart_data_table_mode(chart) == "inline" and slide_table_counts[slide_no - 1] <= 0:
                warnings.append(
                    issue(
                        "MODEL_CHART_DATATABLE",
                        f"第 {i + 1} 章图表声明 dataTable=inline，但第 {slide_no} 页没有原生表格（数据表未落位）。",
                        slide=slide_no,
                    )
                )
    # notes 策略声称「数据写入演讲者备注」——不核对就只是一句承诺：
    # 备注丢了，用户打开 PPTX 无从得知，图表数据就此不可追溯。
    # 仅对交付通道生效：A 预览引擎不产 notesSlide（预览也看不到备注），与
    # allow_shape_charts 同一道通道能力边界。
    if slide_notes is not None and not allow_shape_charts:
        for i, sec in enumerate(sections):
            slide_no = first_sec + i
            if slide_no - 1 >= len(slide_notes):
                break
            chart = _section_chart(sec)
            if chart is None or _chart_data_table_mode(chart) != "notes":
                continue
            if "数据表" not in (slide_notes[slide_no - 1] or ""):
                warnings.append(
                    issue(
                        "MODEL_CHART_NOTES_MISSING",
                        f"第 {i + 1} 章图表声明 dataTable=notes，但第 {slide_no} 页的演讲者备注里没有数据表（数据不可追溯）。",
                        slide=slide_no,
                    )
                )
    closing = model.get("closing") or {}
    closing_title = str((closing.get("title") if isinstance(closing, dict) else "") or "").strip()
    if closing_title and slide_texts and closing_title not in slide_texts[-1]:
        warnings.append(issue("MODEL_ROUNDTRIP_CLOSING_TITLE", "模型收尾标题未出现在最后一页。"))
    if isinstance(closing, dict) and slide_texts:
        closing_probes = _model_probe_strings(closing)
        if closing_probes:
            slide_text = _roundtrip_corpus(
                slide_texts[-1],
                (slide_notes[-1] if slide_notes else ""),
                (slide_chart_texts[-1] if slide_chart_texts else ""),
            )
            hits = sum(1 for p in closing_probes if _norm_text(p) in slide_text)
            if hits * 2 < len(closing_probes):
                warnings.append(
                    issue("MODEL_ROUNDTRIP_CONTENT_MISSING",
                          f"收尾页仅 {hits}/{len(closing_probes)} 个关键串落在最后一页（内容保真）。")
                )
    return warnings


def empty_report(path: Path) -> dict[str, Any]:
    return {
        "file": str(path),
        "summary": {
            "slide_count": 0,
            "width_emu": 0,
            "height_emu": 0,
            "aspect_ratio": 0.0,
            "native_text_shapes": 0,
            "native_graphic_shapes": 0,
            "pictures": 0,
            "icon_pictures": 0,
            "charts": 0,
            "tables": 0,
        },
        "errors": [],
        "warnings": [],
        "slides": [],
    }


def promote_strict_failures(report: dict[str, Any], deep: bool = False) -> None:
    codes = set(STRICT_FAILURE_CODES)
    if deep:
        codes |= DEEP_STRICT_CODES
    existing = {(item.get("code"), item.get("slide"), item.get("message")) for item in report["errors"]}
    for warning in report["warnings"]:
        if warning.get("code") not in codes:
            continue
        key = (warning.get("code"), warning.get("slide"), warning.get("message"))
        if key in existing:
            continue
        failure = dict(warning)
        failure["strict_failure"] = True
        report["errors"].append(failure)
        existing.add(key)



def validate_chrome_drift(slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """跨页 chrome（页脚/页码）y 一致性：相对中位数漂移超过 chromeDriftIn → WARN。

    封面/收尾页版式不同（常无页脚或 y 不同）豁免；仅比内容页。严格交付下任意 WARN 会挡
    smoke，故容差偏宽、只抓明显漂移。
    """
    out: list[dict[str, Any]] = []
    if len(slides) < 4:
        return out
    first_n = slides[0].get("slide")
    last_n = slides[-1].get("slide")
    ys = [(s.get("slide"), s.get("chrome_footer_y_in"))
          for s in slides
          if s.get("chrome_footer_y_in") is not None
          and s.get("slide") not in (first_n, last_n)]
    if len(ys) < 3:
        return out
    vals = sorted(y for _, y in ys)
    mid = vals[len(vals) // 2]
    try:
        lc = json.loads(Path(__file__).with_name("layout-constants.json").read_text(encoding="utf-8"))
        max_delta = float(((lc.get("qualityGates") or {}).get("chromeDriftIn") or {}).get("maxAbsDeltaIn") or 0.2)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        max_delta = 0.2
    drifted = [(n, y) for n, y in ys if abs(float(y) - mid) > max_delta]
    for n, y in drifted[:4]:
        out.append(issue(
            "CHROME_DRIFT",
            f"第{n}页页脚/页码 y={y:.3f}in 相对中位 {mid:.3f}in 漂移 {abs(y-mid):+.3f}in "
            f"（容差 {max_delta}in）；跨页 chrome 应锁死几何。",
            slide=n,
        ))
    return out


def validate_pptx(
    path: str | Path,
    model_path: str | Path | None = None,
    *,
    strict: bool = False,
    allow_shape_charts: bool = False,
    deep: bool = False,
) -> dict[str, Any]:
    source = Path(path)
    report = empty_report(source)
    model: dict[str, Any] | None = None
    if model_path is not None:
        try:
            model = json.loads(Path(model_path).read_text(encoding="utf-8"))
            if not isinstance(model, dict):
                model = None
                report["warnings"].append(issue("MODEL_INVALID", "--model 文件根节点必须是 JSON 对象。"))
        except (OSError, json.JSONDecodeError) as exc:
            report["warnings"].append(issue("MODEL_INVALID", f"无法解析 --model JSON：{exc}"))

    if not source.exists():
        report["errors"].append(issue("FILE_NOT_FOUND", f"文件不存在：{source}"))
        return report

    try:
        with zipfile.ZipFile(source) as archive:
            names = set(archive.namelist())
            required = {"[Content_Types].xml", "ppt/presentation.xml"}
            missing = sorted(required - names)
            if missing:
                report["errors"].append(issue("MISSING_PACKAGE_PART", f"缺少必需部件：{', '.join(missing)}"))
                return report

            presentation = read_xml(archive, "ppt/presentation.xml")
            slide_size = presentation.find("p:sldSz", NS)
            if slide_size is None:
                report["errors"].append(issue("MISSING_SLIDE_SIZE", "ppt/presentation.xml 无 p:sldSz。"))
                return report

            width = int(slide_size.get("cx", "0"))
            height = int(slide_size.get("cy", "0"))
            if width <= 0 or height <= 0:
                report["errors"].append(issue("INVALID_SLIDE_SIZE", f"页面尺寸非法：{width}×{height} EMU。"))
                return report

            ratio = width / height
            report["summary"].update({
                "width_emu": width,
                "height_emu": height,
                "aspect_ratio": round(ratio, 4),
            })
            if not 1.75 <= ratio <= 1.79:
                report["warnings"].append(
                    issue("NON_WIDESCREEN_ASPECT", f"页面比例 {ratio:.4f}，应为约 16:9。")
                )

            # 色值合法性：编码色板（c1–c5）与图表系列色经双引擎直写 srgbClr val——
            # 单源若带 # 前缀会原样落进 OOXML（非法，PowerPoint 静默忽略/触发修复）。
            bad_colors: list[str] = []
            for part in archive.namelist():
                if not part.endswith(".xml"):
                    continue
                try:
                    body = archive.read(part).decode("utf-8", "replace")
                except KeyError:
                    continue
                for match in HEX_COLOR_RE.finditer(body):
                    if not HEX6_RE.fullmatch(match.group(1)):
                        bad_colors.append(f"{part}: {match.group(0)}")
            if bad_colors:
                report["errors"].append(issue(
                    "INVALID_HEX_COLOR",
                    f"非法 srgbClr 色值 {len(bad_colors)} 处（须为 6 位 hex，不带 #）："
                    + "; ".join(bad_colors[:4])))

            slide_names = find_slide_names(archive)
            if not slide_names:
                report["errors"].append(issue("NO_SLIDES", "未找到 ppt/slides/slideN.xml。"))
                return report

            slide_texts: list[str] = []
            slide_bgs: list[str | None] = []
            slide_notes: list[str] = []
            slide_chart_texts: list[str] = []
            for slide_number, slide_name in enumerate(slide_names, start=1):
                try:
                    slide_root = read_xml(archive, slide_name)
                except (KeyError, ET.ParseError) as exc:
                    report["errors"].append(
                        issue("INVALID_SLIDE_XML", f"无法解析 {slide_name}：{exc}", slide=slide_number)
                    )
                    continue
                metrics, warnings = inspect_slide(slide_root, slide_number, width, height, deep=deep)
                report["slides"].append(metrics)
                report["warnings"].extend(warnings)
                slide_texts.append(text_content(slide_root))
                slide_bgs.append(slide_bg_color(slide_root))
                slide_notes.append(slide_notes_text(archive, slide_name))
                slide_chart_texts.append(slide_chart_text(archive, slide_name))

            report["summary"]["slide_count"] = len(slide_names)
            for field in ("native_text_shapes", "native_graphic_shapes", "pictures", "icon_pictures", "charts", "tables"):
                report["summary"][field] = sum(slide[field] for slide in report["slides"])

            # P1-6 chrome 一致性：页脚/页码 y 相对中位数漂移
            report["warnings"].extend(validate_chrome_drift(report["slides"]))

            # 图片门禁：默认零图片（pictures=0 全原生可编辑）；
            # 仅当模型显式声明 section.image / split.right.image 时才允许对应数量的图片落地。
            # 配图占位（image.placeholder）走原生形状，不计入图片数；版式/裁切/多图数量另做硬门禁。
            declared_images = count_model_images(model) if model_path is not None else 0
            n_pics = report["summary"]["pictures"]   # 内容图（已扣除 icon: 语义图标图）
            n_icons = int(report["summary"].get("icon_pictures", 0) or 0)
            img_issues: list[tuple[str, str]] = []
            if model_path is not None and model is not None:
                img_issues = model_image_issues(model, _image_spec(),
                                                Path(model_path).resolve().parent)
                for code, msg in img_issues:
                    report["warnings"].append(issue(code, msg))
            if declared_images:
                # 声明的图片属预期版面 → 大图面积告警豁免（仍保留 ≥90% 整页底图风险）
                report["warnings"] = [w for w in report["warnings"]
                                      if w["code"] != "UNJUSTIFIED_LARGE_IMAGE"]
                if n_pics > declared_images:
                    report["warnings"].append(
                        issue("PICTURES_NOT_DECLARED",
                              f"PPTX 含 {n_pics} 张图片，但模型只声明 {declared_images} 张"
                              f"（未声明的图片不允许：全原生可编辑是交付基线）。")
                    )
                # 反向门禁：声明了却没落地 = 引擎静默回落占位（图片损坏/超限/编码不支持）。
                # 缺失路径已由 IMAGE_SRC_MISSING 单独报出，此处按可用声明数扣除后再比，避免重复计数。
                unusable = sum(1 for code, _ in img_issues
                               if code in ("IMAGE_SRC_MISSING", "IMAGE_SRC_EXTERNAL"))
                expected = declared_images - unusable
                if n_pics < expected:
                    report["warnings"].append(
                        issue("PICTURES_UNDER_DECLARED",
                              f"PPTX 只落地 {n_pics} 张图片，但模型有 {expected} 张可用声明"
                              f"（{declared_images} 声明 − {unusable} 路径异常）。"
                              f"引擎可能已静默回落配图占位：请检查图片是否损坏/超出体积上限/编码不受支持。")
                    )
                for src in model_image_srcs(model):
                    if re.match(r"\s*(?:https?:)?//", src):
                        report["warnings"].append(
                            issue("IMAGE_SRC_EXTERNAL",
                                  f"模型 image.src 为外链（{src[:48]}…）：只允许 data: 内联或相对路径。")
                        )
            elif n_pics > 0:
                report["warnings"].append(
                    issue("PICTURES_NOT_ALLOWED",
                          f"PPTX 含 {n_pics} 张图片；TopPPT HTML 默认要求 pictures=0（全原生可编辑）。"
                          f"如确需图片，请在模型中显式声明 section.image。")
                )
            if report["summary"]["native_text_shapes"] == 0:
                report["warnings"].append(
                    issue("NO_NATIVE_TEXT_WITH_EDITABLE_TEXT_REQUIRED",
                          "PPTX 无原生文本形状；可编辑性不达标。")
                )

            if model_path is not None:
                report["warnings"].extend(
                    validate_model_roundtrip(
                        model, slide_texts, report["summary"]["slide_count"],
                        chart_count=report["summary"]["charts"],
                        allow_shape_charts=allow_shape_charts,
                        slide_table_counts=[s.get("tables", 0) for s in report["slides"]],
                        slide_notes=slide_notes,
                        slide_chart_texts=slide_chart_texts,
                    )
                )
                report["warnings"].extend(validate_model_theme(model, slide_bgs))
                report["warnings"].extend(validate_font_scale(model, report["slides"]))
    except zipfile.BadZipFile:
        report["errors"].append(issue("INVALID_PPTX_ZIP", "文件不是可读的 PPTX ZIP 包。"))
    except (ET.ParseError, KeyError, ValueError) as exc:
        report["errors"].append(issue("INVALID_PACKAGE_XML", str(exc)))

    if strict:
        promote_strict_failures(report, deep=deep)

    return report


def build_manifest(report: dict[str, Any], model_path: str | Path | None,
                   deep: bool = False) -> dict[str, Any]:
    """深度模式 manifest：锚点注册 / 容器清单 / 数据表清单 / 图表通道清单 / 图片资产登记。

    这是"按需深度模式"的机器可验证产物——不做 SHA-256 冻结与逐页人工验收（保持轻量），
    只把可复现的事实登记下来，供人工复核与渲染对照使用。
    """
    model: dict[str, Any] | None = None
    if model_path is not None:
        try:
            loaded = json.loads(Path(model_path).read_text(encoding="utf-8"))
            model = loaded if isinstance(loaded, dict) else None
        except (OSError, json.JSONDecodeError):
            model = None
    slides = report.get("slides") or []
    specs = _model_chart_specs(model) if model else []
    native_expected = sum(1 for s in specs if s["channel"] == "native")
    shape_expected = len(specs) - native_expected
    charts_actual = int((report.get("summary") or {}).get("charts", 0))
    anchors: list[dict[str, Any]] = []
    for slide in slides:
        info = slide.get("anchor")
        if not info:
            anchors.append({"slide": slide["slide"], "status": "no-title-anchor"})
            continue
        passed = abs(info["delta_in"]) <= info["tolerance_in"]
        anchors.append({
            "slide": slide["slide"], "title": info["text"],
            "left_in": info["left_in"], "expected_left_in": info["expected_left_in"],
            "delta_in": info["delta_in"], "tolerance_in": info["tolerance_in"],
            "status": "passed" if passed else "failed",
        })
    data_tables = [
        {"index": i + 1, "pageType": s["pageType"], "chart": s["type"],
         "channel": s["channel"], "dataTable": s["dataTable"]}
        for i, s in enumerate(specs)
    ]
    for slide in slides:
        if slide.get("tables"):
            data_tables.append({"slide": slide["slide"], "tables": slide["tables"], "source": "pptx"})
    pad = _containers_cfg()["minPad"]
    return {
        "file": report.get("file"),
        "version": skill_version(),
        "mode": (model or {}).get("mode"),
        "style": (model or {}).get("style"),
        "theme": (model or {}).get("theme") or "light",
        "deep": deep,
        "slide_count": (report.get("summary") or {}).get("slide_count", 0),
        "chartChannels": {
            "expectedNative": native_expected,
            "expectedShape": shape_expected,
            "actualChartParts": charts_actual,
            "nativeOk": charts_actual >= native_expected,
        },
        "dataTables": data_tables,
        "images": {
            "declared": count_model_images(model) if model else 0,
            "actual": int((report.get("summary") or {}).get("pictures", 0)),
            "placeholders": count_model_placeholders(model) if model else 0,
            "layouts": [
                {"section": i, "layout": str(img.get("layout") or
                                             ("grid" if len(img.get("items") or []) > 1 else "full")).lower(),
                 "fit": str(img.get("fit") or _image_spec().get("fitDefault") or "cover").lower(),
                 "srcs": len(_image_real_srcs(img)), "placeholder": bool(img.get("placeholder"))}
                for i, img in _model_image_holders(model)
            ] if model else [],
        },
        "anchors": anchors,
        "containers": [
            {"slide": s["slide"], "text_shapes": s.get("native_text_shapes", 0), "min_pad_in": pad}
            for s in slides
        ],
        "counts": {
            "errors": len(report.get("errors") or []),
            "warnings": len(report.get("warnings") or []),
        },
    }


def _model_image_holders(model: dict[str, Any] | None) -> list[tuple[int, dict[str, Any]]]:
    """页内承载素材图片的容器（section.image / split.right.image），带页序号便于定位。"""
    out: list[tuple[int, dict[str, Any]]] = []
    if not isinstance(model, dict):
        return out
    for i, sec in enumerate(model.get("sections") or []):
        if not isinstance(sec, dict):
            continue
        if isinstance(sec.get("image"), dict):
            out.append((i, sec["image"]))
        right = sec.get("right")
        if isinstance(right, dict) and isinstance(right.get("image"), dict):
            out.append((i, right["image"]))
    return out


def _image_real_srcs(img: dict[str, Any]) -> list[str]:
    """图片对象的真实 src（image.src + image.items[].src）；占位符不计（走原生形状）。"""
    if not isinstance(img, dict) or img.get("placeholder"):
        return []
    srcs: list[str] = []
    if isinstance(img.get("src"), str) and img["src"].strip():
        srcs.append(img["src"])
    for it in (img.get("items") or []):
        if isinstance(it, dict) and isinstance(it.get("src"), str) and it["src"].strip():
            srcs.append(it["src"])
        elif isinstance(it, str) and it.strip():
            srcs.append(it)
    return srcs


def count_model_images(model: dict[str, Any] | None) -> int:
    """统计模型显式声明的**真实图片**数（section.image / split.right.image 的 src 与 items）。
    TopPPT HTML 默认零图片（pictures=0 全原生可编辑）；仅当模型显式声明时才允许图片落地。
    配图占位（image.placeholder）由原生形状渲染，不计入图片数。"""
    n = 0
    for _, img in _model_image_holders(model):
        n += len(_image_real_srcs(img))
    return n


def model_image_srcs(model: dict[str, Any] | None) -> list[str]:
    out: list[str] = []
    for _, img in _model_image_holders(model):
        out.extend(_image_real_srcs(img))
    return out


def count_model_placeholders(model: dict[str, Any] | None) -> int:
    """配图占位页数（原生占位框；交付前建议用户替换为真实素材）。"""
    return sum(1 for _, img in _model_image_holders(model) if img.get("placeholder"))


def model_image_issues(model: dict[str, Any] | None, spec: dict[str, Any],
                       base_dir: str | Path | None = None) -> list[tuple[str, str]]:
    """图片模型硬门禁：版式 / 裁切 / 多图数量 / 外链 src / 相对路径文件缺失。
    与 validate_report.py 同口径（单源 layout-constants.json imageSpec）；
    相对路径以**模型文件所在目录**为锚（与 build_pptx.js 的 resolveImagePath 同规则）。"""
    issues: list[tuple[str, str]] = []
    layouts = {str(x).lower() for x in (spec.get("layouts") or
                                        ["full", "half", "bleed", "grid", "compare", "wall"])}
    fits = {str(x).lower() for x in (spec.get("fitEnum") or ["cover", "contain"])}
    max_per_page = int(spec.get("maxPerPage") or 6)
    base = Path(base_dir) if base_dir else None
    for i, img in _model_image_holders(model):
        items = img.get("items") or []
        layout = str(img.get("layout") or ("grid" if len(items) > 1 else "full")).lower()
        if layout not in layouts:
            issues.append(("IMAGE_LAYOUT_INVALID",
                           f"sections[{i}].image.layout={layout!r} 未登记（应为 {'/'.join(sorted(layouts))}）"))
        if img.get("fit") and str(img["fit"]).lower() not in fits:
            issues.append(("IMAGE_FIT_INVALID",
                           f"sections[{i}].image.fit={img['fit']!r} 未登记（应为 cover/contain）"))
        multi = {str(x).lower() for x in (spec.get("multiLayouts") or ["grid", "compare", "wall"])}
        if len(items) > max_per_page:
            issues.append(("IMAGE_ITEMS_TOO_MANY",
                           f"sections[{i}].image.items 共 {len(items)} 张，超出单页上限 {max_per_page}"))
        if layout in multi and not img.get("placeholder") and len(items) < 2:
            issues.append(("IMAGE_ITEMS_TOO_MANY",
                           f"sections[{i}].image.layout={layout!r} 属多图版式，items 需 ≥2 张（当前 {len(items)}）"))
        for src in _image_real_srcs(img):
            if re.match(r"\s*(?:https?:)?//", src):
                issues.append(("IMAGE_SRC_EXTERNAL",
                               f"sections[{i}].image 含外链 src（{src[:48]}…）：只允许 data: 内联或相对路径"))
                continue
            if base is None or src.startswith("data:"):
                continue
            p = Path(src)
            cand = p if p.is_absolute() else (base / p)
            if not cand.exists():
                issues.append(("IMAGE_SRC_MISSING",
                               f"sections[{i}].image.src 指向的文件不存在（{src[:60]}，"
                               f"按模型目录解析为 {cand}）：图片会回落成占位框，请修正路径或用 data: 内联"))
    return issues


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="TopPPT HTML PPTX 质检：结构 / 可编辑性 / 版式安全 / 内容保真。"
    )
    parser.add_argument("pptx", help="PPTX 文件路径")
    parser.add_argument("--model", help="TopPPT HTML model.json（extract_model.py 产物）：往返保真检查")
    parser.add_argument("--allow-shape-charts", action="store_true",
                        help="豁免 MODEL_CHART_COUNT 与 MODEL_CHART_NOTES_MISSING（仅 A 通道预览引擎回归；"
                             "交付通道要求原生图表与备注数据表）")
    parser.add_argument("--strict", action="store_true", help="0 errors / 0 warnings 才通过")
    parser.add_argument("--deep", action="store_true",
                        help="深度模式（高保真/1:1 诉求）：额外跑连续文本流与空间锚点检查，并纳入 strict 门禁")
    parser.add_argument("--json-out", help="可选：把 UTF-8 JSON 报告写到该路径")
    parser.add_argument("--emit-manifest", metavar="PATH",
                        help="深度模式：把 manifest（锚点/容器/数据表/图表通道/图片资产）写到该路径")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = validate_pptx(
        args.pptx,
        model_path=args.model,
        strict=args.strict,
        allow_shape_charts=args.allow_shape_charts,
        deep=args.deep,
    )
    if args.emit_manifest:
        manifest = build_manifest(report, args.model, deep=args.deep)
        target = Path(args.emit_manifest)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f'manifest 已写出: {target}')
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json_out:
        output = Path(args.json_out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    if report["errors"]:
        return 1
    if args.strict and report["warnings"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
