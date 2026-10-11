#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression gates for usage-feedback defects (validator + static engine checks)."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import validate_pptx as V  # noqa: E402

EMU = 914400
NS = V.NS
fails: list[str] = []


def ok(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        fails.append(name)


def test_shape_bounds_reads_p_xfrm() -> None:
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:graphicFrame xmlns:a="{NS["a"]}" xmlns:p="{NS["p"]}">'
        "<p:xfrm>"
        f'<a:off x="{int(0.6 * EMU)}" y="{int(2.5 * EMU)}"/>'
        f'<a:ext cx="{int(8.5 * EMU)}" cy="{int(3.5 * EMU)}"/>'
        "</p:xfrm>"
        "</p:graphicFrame>"
    )
    el = ET.fromstring(xml)
    box = V.shape_bounds(el)
    ok("1 shape_bounds reads p:xfrm", box is not None and box[2] > 0, f"got {box}")


def test_shape_bounds_still_reads_a_xfrm() -> None:
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:sp xmlns:a="{NS["a"]}" xmlns:p="{NS["p"]}">'
        "<p:spPr><a:xfrm>"
        f'<a:off x="{EMU}" y="{EMU}"/>'
        f'<a:ext cx="{2 * EMU}" cy="{EMU}"/>'
        "</a:xfrm></p:spPr></p:sp>"
    )
    el = ET.fromstring(xml)
    box = V.shape_bounds(el)
    ok("1b shape_bounds reads a:xfrm", box is not None and box[0] == EMU)


def _text_shape(paras, x=0.6, y=2.5, w=4.0, h=0.6):
    parts = []
    for text, pt in paras:
        parts.append(
            f'<a:p><a:r><a:rPr sz="{int(pt * 100)}"/><a:t>{text}</a:t></a:r></a:p>'
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:sp xmlns:a="{NS["a"]}" xmlns:p="{NS["p"]}">'
        "<p:spPr><a:xfrm>"
        f'<a:off x="{int(x * EMU)}" y="{int(y * EMU)}"/>'
        f'<a:ext cx="{int(w * EMU)}" cy="{int(h * EMU)}"/>'
        "</a:xfrm></p:spPr>"
        f'<p:txBody>{"".join(parts)}</p:txBody></p:sp>'
    )
    return ET.fromstring(xml)


def test_text_overflow_vertical() -> None:
    paras = [(f"这是第{i}段足够长的中文内容用来累计行高", 12.0) for i in range(8)]
    shape = _text_shape(paras, h=0.55)
    issues = V.text_overflow_vertical_check(shape, 1)
    codes = [i["code"] for i in issues]
    ok(
        "2 TEXT_OVERFLOW_VERTICAL fires on multi-segment cumulative",
        "TEXT_OVERFLOW_VERTICAL" in codes,
        f"codes={codes}",
    )


def test_annotation_band_overlap() -> None:
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:sp xmlns:a="{NS["a"]}" xmlns:p="{NS["p"]}">'
        "<p:spPr><a:xfrm>"
        f'<a:off x="{int(0.6 * EMU)}" y="{int(5.5 * EMU)}"/>'
        f'<a:ext cx="{int(4 * EMU)}" cy="{int(1.4 * EMU)}"/>'
        "</a:xfrm></p:spPr></p:sp>"
    )
    el = ET.fromstring(xml)
    issues = V.annotation_band_overlap_check([el], 1, int(7.5 * EMU))
    codes = [i["code"] for i in issues]
    ok(
        "3 ANNOTATION_BAND_OVERLAP fires when content crushes band",
        "ANNOTATION_BAND_OVERLAP" in codes,
        f"codes={codes}",
    )


def test_annotation_band_ignores_full_bleed_bg() -> None:
    """Full-slide background must not false-positive as band crush."""
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:sp xmlns:a="{NS["a"]}" xmlns:p="{NS["p"]}">'
        "<p:spPr><a:xfrm>"
        f'<a:off x="0" y="0"/>'
        f'<a:ext cx="{int(13.333 * EMU)}" cy="{int(7.5 * EMU)}"/>'
        "</a:xfrm></p:spPr></p:sp>"
    )
    el = ET.fromstring(xml)
    issues = V.annotation_band_overlap_check(
        [el], 1, int(7.5 * EMU), int(13.333 * EMU),
    )
    codes = [i["code"] for i in issues]
    ok(
        "3b full-bleed background does not fire ANNOTATION_BAND_OVERLAP",
        "ANNOTATION_BAND_OVERLAP" not in codes,
        f"codes={codes}",
    )


def test_annotation_band_allows_content_without_note() -> None:
    """Without so-what/source, content may use up to contentBottom (~6.9)."""
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:sp xmlns:a="{NS["a"]}" xmlns:p="{NS["p"]}">'
        "<p:spPr><a:xfrm>"
        f'<a:off x="{int(0.6 * EMU)}" y="{int(5.5 * EMU)}"/>'
        f'<a:ext cx="{int(4 * EMU)}" cy="{int(1.0 * EMU)}"/>'
        "</a:xfrm></p:spPr>"
        "<p:txBody><a:p><a:r><a:t>AgendaCard</a:t></a:r></a:p></p:txBody>"
        "</p:sp>"
    )
    el = ET.fromstring(xml)
    issues = V.annotation_band_overlap_check([el], 1, int(7.5 * EMU))
    codes = [i["code"] for i in issues]
    ok(
        "3c content to 6.50 without annotation does not fire",
        "ANNOTATION_BAND_OVERLAP" not in codes,
        f"codes={codes}",
    )


def test_annotation_band_fires_when_note_present() -> None:
    """With so-what bar present, body overlapping the withNote band must fire."""
    def sp(y, h, w, text):
        return ET.fromstring(
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<p:sp xmlns:a="{NS["a"]}" xmlns:p="{NS["p"]}">'
            "<p:spPr><a:xfrm>"
            f'<a:off x="{int(0.6 * EMU)}" y="{int(y * EMU)}"/>'
            f'<a:ext cx="{int(w * EMU)}" cy="{int(h * EMU)}"/>'
            "</a:xfrm></p:spPr>"
            f"<p:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody>"
            "</p:sp>"
        )
    els = [
        sp(5.5, 1.0, 4.0, "LegendSeries"),
        sp(6.05, 0.55, 12.0, "结论 平台化是唯一路径"),
    ]
    issues = V.annotation_band_overlap_check(els, 1, int(7.5 * EMU), int(13.333 * EMU))
    codes = [i["code"] for i in issues]
    ok(
        "3d body crush with so-what present fires ANNOTATION_BAND_OVERLAP",
        "ANNOTATION_BAND_OVERLAP" in codes,
        f"codes={codes}",
    )


def test_annotation_band_textbox_to_content_bottom_no_note() -> None:
    """Text box framed to contentBottom (6.9) with no annotation is engine-intent
    (empty frame, no ink invasion) — severe safety net must not fire (cf. 3c)."""
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:sp xmlns:a="{NS["a"]}" xmlns:p="{NS["p"]}">'
        "<p:spPr><a:xfrm>"
        f'<a:off x="{int(0.6 * EMU)}" y="{int(2.35 * EMU)}"/>'
        f'<a:ext cx="{int(6 * EMU)}" cy="{int(4.55 * EMU)}"/>'
        "</a:xfrm></p:spPr>"
        "<p:txBody><a:p><a:r><a:t>发现要点</a:t></a:r></a:p></p:txBody>"
        "</p:sp>"
    )
    el = ET.fromstring(xml)
    issues = V.annotation_band_overlap_check([el], 1, int(7.5 * EMU))
    codes = [i["code"] for i in issues]
    ok(
        "3e textbox to 6.90 without annotation does not fire",
        "ANNOTATION_BAND_OVERLAP" not in codes,
        f"codes={codes}",
    )


def test_font_size_h2_17_allowed() -> None:
    """modeTypeScale h2=17 must be on the allowed set (cover/display whitelist)."""
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:sld xmlns:a="{NS["a"]}" xmlns:p="{NS["p"]}">'
        "<p:cSld><p:spTree><p:sp><p:txBody>"
        '<a:p><a:r><a:rPr sz="1700"/><a:t>AgendaSectionTitle</a:t></a:r></a:p>'
        "</p:txBody></p:sp></p:spTree></p:cSld></p:sld>"
    )
    root = ET.fromstring(xml)
    issues = V.font_size_snap_check(root, 1)
    codes = [i["code"] for i in issues]
    ok(
        "4b FONT_SIZE_NOT_SNAPPED allows intentional 17pt h2",
        "FONT_SIZE_NOT_SNAPPED" not in codes,
        f"codes={codes}",
    )


def test_font_size_not_snapped() -> None:
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:sld xmlns:a="{NS["a"]}" xmlns:p="{NS["p"]}">'
        "<p:cSld><p:spTree><p:sp><p:txBody>"
        '<a:p><a:r><a:rPr sz="1130"/><a:t>OffLadderSampleTextHere</a:t></a:r></a:p>'
        "</p:txBody></p:sp></p:spTree></p:cSld></p:sld>"
    )
    root = ET.fromstring(xml)
    issues = V.font_size_snap_check(root, 1)
    codes = [i["code"] for i in issues]
    ok(
        "4 FONT_SIZE_NOT_SNAPPED fires on off-ladder size",
        "FONT_SIZE_NOT_SNAPPED" in codes,
        f"codes={codes}",
    )


def test_annotation_band_reports_all_invaders() -> None:
    """D9: do not break after the first ANNOTATION_BAND_OVERLAP on a slide."""
    def sp(y, h, w, text):
        return ET.fromstring(
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<p:sp xmlns:a="{NS["a"]}" xmlns:p="{NS["p"]}">'
            "<p:spPr><a:xfrm>"
            f'<a:off x="{int(0.6 * EMU)}" y="{int(y * EMU)}"/>'
            f'<a:ext cx="{int(w * EMU)}" cy="{int(h * EMU)}"/>'
            "</a:xfrm></p:spPr>"
            f"<p:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody>"
            "</p:sp>"
        )
    els = [
        sp(5.0, 1.2, 4.0, "PlotSeriesA"),
        sp(5.2, 1.1, 4.0, "PlotSeriesB"),
        sp(6.05, 0.55, 12.0, "Platform locked path takeaway"),
    ]
    issues = V.annotation_band_overlap_check(els, 1, int(7.5 * EMU), int(13.333 * EMU))
    codes = [i["code"] for i in issues]
    ok(
        "3e D9 reports all invaders (not just first)",
        codes.count("ANNOTATION_BAND_OVERLAP") >= 2,
        f"codes={codes}",
    )


def test_annotation_band_so_what_band_top() -> None:
    """D11: with so-what present, invasions in (6.05, 6.40] must fire."""
    def sp(y, h, w, text):
        return ET.fromstring(
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<p:sp xmlns:a="{NS["a"]}" xmlns:p="{NS["p"]}">'
            "<p:spPr><a:xfrm>"
            f'<a:off x="{int(0.6 * EMU)}" y="{int(y * EMU)}"/>'
            f'<a:ext cx="{int(w * EMU)}" cy="{int(h * EMU)}"/>'
            "</a:xfrm></p:spPr>"
            f"<p:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody>"
            "</p:sp>"
        )
    els = [
        # Body ends at 6.30 — inside (soWhatY=6.05, contentBottomWithNote=6.40]
        sp(5.0, 1.3, 4.0, "LegendCrushMid"),
        sp(6.05, 0.55, 12.0, "Platform first takeaway text"),
    ]
    issues = V.annotation_band_overlap_check(els, 1, int(7.5 * EMU), int(13.333 * EMU))
    codes = [i["code"] for i in issues]
    msgs = " ".join(i.get("message") or "" for i in issues)
    ok(
        "3f D11 band_top=soWhatY catches invasion in (6.05, 6.40]",
        "ANNOTATION_BAND_OVERLAP" in codes and "6.05" in msgs,
        f"codes={codes} msgs={msgs[:120]}",
    )


def test_chrome_footer_ignores_bare_integers() -> None:
    """CHROME_DRIFT FP: bare year/exhibit numbers must not count as pager."""
    def sp(y, text):
        return ET.fromstring(
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<p:sp xmlns:a="{NS["a"]}" xmlns:p="{NS["p"]}">'
            "<p:spPr><a:xfrm>"
            f'<a:off x="{int(0.6 * EMU)}" y="{int(y * EMU)}"/>'
            f'<a:ext cx="{int(1.0 * EMU)}" cy="{int(0.3 * EMU)}"/>'
            "</a:xfrm></p:spPr>"
            f'<p:txBody><a:p><a:r><a:rPr sz="1100"/><a:t>{text}</a:t></a:r></a:p></p:txBody>'
            "</p:sp>"
        )
    shapes = [sp(6.14, "2024"), sp(6.14, "06"), sp(7.0, "3 / 14")]
    y = V.chrome_footer_y_in(shapes, int(7.5 * EMU))
    ok(
        "5 chrome_footer_y_in uses N / M only (ignores bare ints)",
        y is not None and abs(y - 7.0) < 0.05,
        f"got {y}",
    )


def test_chart_bottom_no_short_circuit() -> None:
    """D8: chartBottom must Math.min soWhat/footnote — no footnote-first return."""
    build = (ROOT.parent / "scripts" / "build_pptx.js").read_text(encoding="utf-8")
    m = re.search(r"function chartBottom\([\s\S]*?\n\}", build)
    body = m.group(0) if m else ""
    ok(
        "D8 chartBottom uses Math.min (no footnote short-circuit)",
        "Math.min" in body
        and "hasFootnote) return" not in body
        and "CONTENT_BOTTOM_NOTE" in body,
        f"body={body[:200]!r}",
    )



def test_engine_static() -> None:
    export = (ROOT.parent / "assets" / "pptx-export.js").read_text(encoding="utf-8")
    build = (ROOT.parent / "scripts" / "build_pptx.js").read_text(encoding="utf-8")

    m = re.search(r"function vbarShapes\([\s\S]*?\n\}", export)
    body = m.group(0) if m else ""
    ok("B vbarShapes handles ec.series", "ec.series" in body and "series.forEach" in body)

    ok(
        "C A-channel streamgraph reserves legend inside plot",
        "Reserve legend INSIDE" in export and "plotBottom" in export,
    )
    ok(
        "C B-channel infoStreamgraph reserves legend inside plot",
        "Reserve legend INSIDE" in build and "plotBottom" in build,
    )

    ok(
        "D A-channel caption uses capYImg from imageLayoutShapes",
        "capYImg" in export
        and re.search(r"capYImg\s*=\s*imageLayoutShapes", export) is not None,
    )
    ok(
        "D B-channel caption uses capYImg from imageLayoutShapes",
        "capYImg" in build
        and re.search(r"capYImg\s*=\s*imageLayoutShapes", build) is not None,
    )

    cards = re.search(
        r"else if \(type === 'cards'\) \{[\s\S]*?else if \(type === 'split'\)",
        export,
    )
    cards_body = cards.group(0) if cards else ""
    ok(
        "A A-channel cards uses sz: N object props (not bare sz())",
        "sz: 12" in cards_body
        and not re.search(r"(?<![\w.])sz\s*\(\s*12\s*\)", cards_body),
    )
    ok(
        "A modeSize applied in txSp serialization",
        "function modeSize" in export and "modeSize(" in export,
    )


def _sp(x: float, y: float, w: float, h: float, text: str = "T") -> ET.Element:
    """构造带 xfrm + 文本的 p:sp 测试件。"""
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:sp xmlns:a="{NS["a"]}" xmlns:p="{NS["p"]}">'
        f'<p:spPr><a:xfrm><a:off x="{int(x * EMU)}" y="{int(y * EMU)}"/>'
        f'<a:ext cx="{int(w * EMU)}" cy="{int(h * EMU)}"/></a:xfrm></p:spPr>'
        f'<p:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody>'
        "</p:sp>"
    )
    return ET.fromstring(xml)


def test_element_overlap() -> None:
    """R6: 两个内容框明显叠印必须 fire；纯包含（卡片+内文）不 fire。"""
    a = _sp(1.0, 2.0, 2.0, 1.0, "这是一个足够长的正文标题占位符")
    b = _sp(2.0, 2.3, 2.0, 1.0, "另一段同样足够长的正文内容占位")  # 与 A 重叠 1.0×0.7 = 0.7 in²
    issues = V.element_overlap_check([a, b], 1, int(13.333 * EMU), int(7.5 * EMU))
    codes = [i["code"] for i in issues]
    ok(
        "6a ELEMENT_OVERLAP fires on side-by-side crush",
        "ELEMENT_OVERLAP" in codes,
        f"codes={codes}",
    )
    outer = _sp(1.0, 2.0, 4.0, 2.0, "卡片容器标题占位")
    inner = _sp(1.2, 2.2, 1.0, 0.4, "内文")
    issues2 = V.element_overlap_check([outer, inner], 1, int(13.333 * EMU), int(7.5 * EMU))
    ok(
        "6b containment (card+inner) does not fire ELEMENT_OVERLAP",
        "ELEMENT_OVERLAP" not in [i["code"] for i in issues2],
    )
    # 两个短标签/数值（图表轴标签、指标值）不算叠印
    lab = _sp(1.0, 3.0, 1.0, 0.3, "已规模化")
    val = _sp(1.2, 3.15, 0.8, 0.3, "18%")
    issues3 = V.element_overlap_check([lab, val], 1, int(13.333 * EMU), int(7.5 * EMU))
    ok(
        "6f short label+value pairs do not fire ELEMENT_OVERLAP",
        "ELEMENT_OVERLAP" not in [i["code"] for i in issues3],
    )


def test_layout_fill() -> None:
    """R6: 宽/高填充低于硬下限须 fire；结构页豁免。"""
    def _box(x: float, y: float, w: float, h: float) -> tuple[int, int, int, int]:
        return (int(x * EMU), int(y * EMU), int(w * EMU), int(h * EMU))
    # 只占左侧窄条：宽填充 ~15%
    narrow = [_box(0.6, 2.0, 1.5, 3.0)]
    issues = V.layout_fill_check(narrow, 3, int(13.333 * EMU), int(7.5 * EMU), is_structural=False)
    codes = [i["code"] for i in issues]
    ok(
        "6c LAYOUT_FILL fires on underfill content page",
        "LAYOUT_FILL" in codes,
        f"codes={codes}",
    )
    ok(
        "6d structural page exempt from LAYOUT_FILL",
        "LAYOUT_FILL" not in [
            i["code"]
            for i in V.layout_fill_check(narrow, 2, int(13.333 * EMU), int(7.5 * EMU), is_structural=True)
        ],
    )
    wide = [_box(0.6, 1.5, 12.0, 5.5)]  # 宽 90% / 高 73%，落在 research 目标带 70–85 内
    ok(
        "6e full-width content page passes LAYOUT_FILL",
        "LAYOUT_FILL" not in [
            i["code"]
            for i in V.layout_fill_check(wide, 3, int(13.333 * EMU), int(7.5 * EMU), is_structural=False)
        ],
    )


def main() -> int:
    print("feedback-gates regression")
    test_shape_bounds_reads_p_xfrm()
    test_shape_bounds_still_reads_a_xfrm()
    test_text_overflow_vertical()
    test_annotation_band_overlap()
    test_annotation_band_ignores_full_bleed_bg()
    test_annotation_band_allows_content_without_note()
    test_annotation_band_fires_when_note_present()
    test_annotation_band_textbox_to_content_bottom_no_note()
    test_annotation_band_reports_all_invaders()
    test_annotation_band_so_what_band_top()
    test_element_overlap()
    test_layout_fill()
    test_chrome_footer_ignores_bare_integers()
    test_chart_bottom_no_short_circuit()
    test_font_size_h2_17_allowed()
    test_font_size_not_snapped()
    test_engine_static()
    print(f"\n{len(fails)} failed" if fails else "\nAll feedback gates PASS")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
