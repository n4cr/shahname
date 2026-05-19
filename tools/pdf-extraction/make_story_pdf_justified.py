"""Render a story to PDF with each مصراع (hemistich) *justified* — the left
end of every hemistich lines up across all beyts, so both columns have flat
right and flat left edges, like a typeset diwan.

Differs from make_story_pdf.py only in how each beyt is drawn:
  * Pick a fixed column width for hem1 and a fixed column width for hem2
    (largest natural width of any hemistich in the story).
  * For each hemistich, split the visual-ordered glyph string into words,
    compute the spare space, and distribute it as extra inter-word padding.
  * Single-word hemistichs are right-aligned (can't justify one word).

Usage: .venv/bin/python make_story_pdf_justified.py <story_index>
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
    beyt_gap_v = 11 * mm
    head_gap_v = 9 * mm
    hem_gap_h = 18 * mm
    center_x = width / 2
    # ---------------------------------------------------------------------

    out_path = f"story-pdf-justified-{entry['filename'].replace('.txt', '.pdf')}"
    c = canvas.Canvas(out_path, pagesize=page_size)

    # Determine each column's target (justified) width:
    # use the natural width of the widest hemistich on each side, so we
    # never *stretch* below 100% and shrink-stretch shorter ones only.
    c.setFont(FONT_BODY, body_size)
    natural_h1 = [c.stringWidth(visual(a), FONT_BODY, body_size) for kind, a, _ in items if kind == "beyt"]
    natural_h2 = [c.stringWidth(visual(b), FONT_BODY, body_size) for kind, _, b in items if kind == "beyt"]
    col_h1_w = max(natural_h1) if natural_h1 else 0
    col_h2_w = max(natural_h2) if natural_h2 else 0

    # If the composition is wider than the page, shrink columns proportionally.
    usable = width - 2 * margin_x
    if col_h1_w + col_h2_w + hem_gap_h > usable:
        scale = (usable - hem_gap_h) / (col_h1_w + col_h2_w)
        col_h1_w *= scale
        col_h2_w *= scale

    total_w = col_h1_w + hem_gap_h + col_h2_w
    composition_left = (width - total_w) / 2
    h2_left = composition_left
    h2_right = h2_left + col_h2_w
    h1_left = h2_right + hem_gap_h
    h1_right = h1_left + col_h1_w

    space_w = c.stringWidth(" ", FONT_BODY, body_size)

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

    def draw_justified(text: str, col_left: float, col_right: float, y: float):
        """Draw a single hemistich justified between col_left and col_right.

        The visual-ordered string from bidi already has spaces in place; we
        split on those, measure each word, and add extra space evenly.
        """
        visual_text = visual(text)
        words = [w for w in visual_text.split(" ") if w]
        if not words:
            return
        widths = [c.stringWidth(w, FONT_BODY, body_size) for w in words]
        target = col_right - col_left
        natural = sum(widths) + space_w * (len(words) - 1)
        # If one word or natural width already meets/exceeds target, fall back
        # to right-align (most poetic for Persian; left edge floats).
        if len(words) <= 1 or natural >= target:
            c.drawRightString(col_right, y, visual_text)
            return
        extra = (target - natural) / (len(words) - 1)
        gap = space_w + extra
        x = col_left
        for i, w in enumerate(words):
            c.drawString(x, y, w)
            x += widths[i] + (gap if i < len(words) - 1 else 0)

    page_num = 1
    draw_header(page_num)
    y = draw_title(height - margin_top)

    c.setFont(FONT_BODY, body_size)
    c.setFillColorRGB(0, 0, 0)

    for kind, a, b in items:
        need = beyt_gap_v if kind == "beyt" else head_gap_v + body_size
        if y - need < margin_bottom:
            c.showPage()
            page_num += 1
            draw_header(page_num)
            y = height - margin_top
            c.setFont(FONT_BODY, body_size)
            c.setFillColorRGB(0, 0, 0)
        if kind == "beyt":
            draw_justified(b, h2_left, h2_right, y)
            draw_justified(a, h1_left, h1_right, y)
            y -= beyt_gap_v
        else:
            c.setFont(FONT_BOLD, body_size + 2)
            c.setFillColorRGB(0.2, 0.2, 0.2)
            c.drawCentredString(center_x, y, visual(a))
            c.setFont(FONT_BODY, body_size)
            c.setFillColorRGB(0, 0, 0)
            y -= head_gap_v

    c.save()
    print(f"Wrote {out_path}")
    print(f"  Story: {title_text}")
    print(f"  Beyts: {sum(1 for k, _, _ in items if k == 'beyt')}, Pages: {page_num}")
    print(f"  Column widths: h1={col_h1_w:.1f}pt  h2={col_h2_w:.1f}pt")


if __name__ == "__main__":
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 78
    main(idx)
