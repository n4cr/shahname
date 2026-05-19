"""Render a story to a clean text-only PDF, poetic layout.

Each beyt occupies one visual row, centered on the page:
  hemistich-1 (right side)   <gap>   hemistich-2 (left side)
Both hemistichs are right-aligned within their own half so the centre
seam is clean. Vertical breathing room separates couplets.

Usage: .venv/bin/python make_story_pdf.py <story_index>
"""
import json
import os
import sys

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONT_BODY = "GeezaPro"
FONT_BOLD = "GeezaProBold"
pdfmetrics.registerFont(TTFont(FONT_BODY, "/System/Library/Fonts/GeezaPro.ttc", subfontIndex=0))
pdfmetrics.registerFont(TTFont(FONT_BOLD, "/System/Library/Fonts/GeezaPro.ttc", subfontIndex=1))

HEMISTICH_SEP = " || "


def visual(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))


def main(story_index: int):
    with open("manifest.json", encoding="utf-8") as f:
        manifest = json.load(f)
    entry = next((m for m in manifest if m["index"] == story_index), None)
    if entry is None:
        raise SystemExit(f"No story with index {story_index}")

    story_path = os.path.join("stories", entry["filename"])
    with open(story_path, encoding="utf-8") as f:
        raw_lines = [ln.rstrip() for ln in f]

    title_text = raw_lines[0].strip()
    # Beyts (those with the separator) vs other lines (headings); skip blanks
    items = []
    for ln in raw_lines[1:]:
        s = ln.strip()
        if not s:
            continue
        if HEMISTICH_SEP in s:
            h1, h2 = s.split(HEMISTICH_SEP, 1)
            items.append(("beyt", h1.strip(), h2.strip()))
        else:
            items.append(("head", s, None))

    # Layout knobs --------------------------------------------------------
    page_size = landscape(A4)
    width, height = page_size
    margin_x = 22 * mm
    margin_top = 25 * mm
    margin_bottom = 22 * mm
    title_size = 28
    body_size = 14
    beyt_gap_v = 11 * mm        # vertical space between couplets
    head_gap_v = 9 * mm         # vertical space around a sub-heading
    hem_gap_h = 18 * mm         # horizontal gap between two hemistichs
    center_x = width / 2
    # ---------------------------------------------------------------------

    out_path = f"story-pdf-{entry['filename'].replace('.txt', '.pdf')}"
    c = canvas.Canvas(out_path, pagesize=page_size)

    def draw_header(page_num: int):
        c.setFillColorRGB(0.55, 0.55, 0.55)
        c.setFont(FONT_BODY, 9)
        c.drawRightString(width - margin_x, height - 12 * mm, visual("شاهنامه فردوسی"))
        c.setFont("Helvetica", 9)
        c.drawString(margin_x, height - 12 * mm, f"{page_num}")
        c.setStrokeColorRGB(0.88, 0.88, 0.88)
        c.setLineWidth(0.5)
        c.line(margin_x, height - 15 * mm, width - margin_x, height - 15 * mm)

    def draw_title(y: float) -> float:
        title_v = visual(title_text)
        c.setFont(FONT_BOLD, title_size)
        c.setFillColorRGB(0.1, 0.1, 0.1)
        c.drawCentredString(center_x, y, title_v)
        tw = c.stringWidth(title_v, FONT_BOLD, title_size)
        c.setStrokeColorRGB(0.6, 0.48, 0.18)
        c.setLineWidth(0.8)
        c.line(center_x - tw / 2, y - 5, center_x + tw / 2, y - 5)
        return y - 16 * mm

    # Pre-measure max hemistich width so all beyts align in two columns.
    c.setFont(FONT_BODY, body_size)
    max_h1_w = 0.0
    max_h2_w = 0.0
    for kind, a, b in items:
        if kind == "beyt":
            w1 = c.stringWidth(visual(a), FONT_BODY, body_size)
            w2 = c.stringWidth(visual(b), FONT_BODY, body_size)
            if w1 > max_h1_w: max_h1_w = w1
            if w2 > max_h2_w: max_h2_w = w2

    # Cap if the composition is wider than the page; scale down proportionally.
    usable = width - 2 * margin_x
    total_w = max_h1_w + hem_gap_h + max_h2_w
    if total_w > usable:
        scale = (usable - hem_gap_h) / (max_h1_w + max_h2_w)
        max_h1_w *= scale
        max_h2_w *= scale
        total_w = max_h1_w + hem_gap_h + max_h2_w

    # Composition is centered on the page.
    # x positions for drawRightString (right edge of each hemistich):
    composition_left = (width - total_w) / 2
    h2_right_x = composition_left + max_h2_w   # right edge of h2 column
    h1_right_x = composition_left + total_w    # right edge of h1 column (= page right of composition)

    def draw_beyt(h1: str, h2: str, y: float):
        c.setFont(FONT_BODY, body_size)
        c.setFillColorRGB(0, 0, 0)
        # Persian text: each hemistich right-aligns in its column.
        c.drawRightString(h2_right_x, y, visual(h2))
        c.drawRightString(h1_right_x, y, visual(h1))

    page_num = 1
    draw_header(page_num)
    y = draw_title(height - margin_top)

    for kind, a, b in items:
        needed = beyt_gap_v if kind == "beyt" else head_gap_v + body_size
        if y - needed < margin_bottom:
            c.showPage()
            page_num += 1
            draw_header(page_num)
            y = height - margin_top
        if kind == "beyt":
            draw_beyt(a, b, y)
            y -= beyt_gap_v
        else:
            c.setFont(FONT_BOLD, body_size + 2)
            c.setFillColorRGB(0.2, 0.2, 0.2)
            c.drawCentredString(center_x, y, visual(a))
            y -= head_gap_v

    c.save()
    print(f"Wrote {out_path}")
    print(f"  Story: {title_text}")
    print(f"  Items: {len(items)} ({sum(1 for k,_,_ in items if k=='beyt')} beyts)")
    print(f"  Pages: {page_num}")


if __name__ == "__main__":
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 78
    main(idx)
