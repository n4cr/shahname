"""Render a story with each مصراع justified using *kashida* (تطویل).

Persian typography traditionally justifies poetry by elongating letter
connections within words (the kashida glyph ـ U+0640), not by widening
word spaces. The result reads more smoothly: word boundaries stay visually
intact, and stretch is spread across letter joins throughout the line.

Algorithm per hemistich:
  1. Measure natural width of the visual-shaped text.
  2. If shorter than the target column width, estimate how many kashidas
     are needed (kashida_pt ≈ font-dependent constant).
  3. Distribute them evenly across all valid insertion points
     (after any letter that joins forward to the next letter).
  4. Re-measure and right-align in the column. Any residual width gap is
     <~3pt and barely visible.

Usage: .venv/bin/python make_story_pdf_kashida.py <story_index>
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
KASHIDA = "ـ"  # ـ — Arabic Tatweel

# Persian/Arabic letters that DO NOT join forward (so no kashida can follow):
NON_JOINING_FORWARD = set("اآإأدذرزژوؤةءۀ")
# Any non-letter (space, punctuation, ZWNJ, digit, Latin char) is not a letter.
# We accept the Persian/Arabic block 0x0600–0x06FF (minus the non-joining set) as joiners.

def _is_arabic_letter(ch: str) -> bool:
    if not ch:
        return False
    cp = ord(ch)
    return 0x0600 <= cp <= 0x06FF and ch not in {"‌", "‍"}


def kashida_positions(word: str) -> list[int]:
    """Indices i s.t. a kashida can be inserted between word[i-1] and word[i].
    Both word[i-1] and word[i] must be Arabic letters, and word[i-1] must
    join forward (i.e., not be in NON_JOINING_FORWARD)."""
    positions = []
    for i in range(1, len(word)):
        prev, cur = word[i - 1], word[i]
        if not _is_arabic_letter(prev) or not _is_arabic_letter(cur):
            continue
        if prev in NON_JOINING_FORWARD:
            continue
        positions.append(i)
    return positions


def add_kashidas(text: str, n_total: int) -> str:
    """Insert n_total kashidas spread evenly across valid positions."""
    if n_total <= 0:
        return text
    words = text.split(" ")
    positions_per_word = [kashida_positions(w) for w in words]
    total_positions = sum(len(p) for p in positions_per_word)
    if total_positions == 0:
        return text
    per_pos = n_total // total_positions
    extra = n_total % total_positions
    out_words = []
    flat_idx = 0
    for w, positions in zip(words, positions_per_word):
        if not positions:
            out_words.append(w)
            continue
        chunks = []
        prev = 0
        for p in positions:
            chunks.append(w[prev:p])
            count = per_pos + (1 if flat_idx < extra else 0)
            chunks.append(KASHIDA * count)
            prev = p
            flat_idx += 1
        chunks.append(w[prev:])
        out_words.append("".join(chunks))
    return " ".join(out_words)


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
    body_size = 15           # slightly bigger than the centered version for readability
    beyt_gap_v = 12 * mm
    head_gap_v = 9 * mm
    hem_gap_h = 18 * mm
    center_x = width / 2
    # ---------------------------------------------------------------------

    out_path = f"story-pdf-kashida-{entry['filename'].replace('.txt', '.pdf')}"
    c = canvas.Canvas(out_path, pagesize=page_size)

    # Calibrate kashida width once for this font/size.
    base_w = c.stringWidth(visual("بیامد"), FONT_BODY, body_size)
    plus10_w = c.stringWidth(visual("ب" + KASHIDA * 10 + "یامد"), FONT_BODY, body_size)
    kashida_pt = max(0.1, (plus10_w - base_w) / 10)

    # Column targets: widest natural hemistich on each side.
    natural_h1 = [c.stringWidth(visual(a), FONT_BODY, body_size) for kind, a, _ in items if kind == "beyt"]
    natural_h2 = [c.stringWidth(visual(b), FONT_BODY, body_size) for kind, _, b in items if kind == "beyt"]
    col_h1_w = max(natural_h1) if natural_h1 else 0
    col_h2_w = max(natural_h2) if natural_h2 else 0
    usable = width - 2 * margin_x
    if col_h1_w + col_h2_w + hem_gap_h > usable:
        scale = (usable - hem_gap_h) / (col_h1_w + col_h2_w)
        col_h1_w *= scale
        col_h2_w *= scale
    total_w = col_h1_w + hem_gap_h + col_h2_w
    composition_left = (width - total_w) / 2
    h2_right = composition_left + col_h2_w
    h1_right = composition_left + total_w

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

    def justify_with_kashida(text: str, target_width: float) -> str:
        """Return the text with enough kashidas to approximately fill
        target_width when reshaped."""
        natural = c.stringWidth(visual(text), FONT_BODY, body_size)
        gap = target_width - natural
        if gap <= 0.5:
            return text
        # One-shot estimate, then a couple of refinement passes.
        n = max(1, int(round(gap / kashida_pt)))
        out = add_kashidas(text, n)
        # Refine: shrink/grow if we overshot/undershot by more than 1.5pt
        for _ in range(3):
            w = c.stringWidth(visual(out), FONT_BODY, body_size)
            diff = target_width - w
            if abs(diff) < 1.5:
                break
            delta = int(round(diff / kashida_pt))
            if delta == 0:
                break
            n = max(0, n + delta)
            out = add_kashidas(text, n)
        return out

    def draw_hem(text: str, col_right: float, col_width: float, y: float):
        natural = c.stringWidth(visual(text), FONT_BODY, body_size)
        if natural >= col_width - 1:
            # Already as wide as (or wider than) the column — just right-align.
            c.drawRightString(col_right, y, visual(text))
            return
        text2 = justify_with_kashida(text, col_width)
        c.drawRightString(col_right, y, visual(text2))

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
            draw_hem(b, h2_right, col_h2_w, y)
            draw_hem(a, h1_right, col_h1_w, y)
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
    print(f"  Column widths: h1={col_h1_w:.1f}pt  h2={col_h2_w:.1f}pt   kashida_pt={kashida_pt:.2f}")


if __name__ == "__main__":
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 78
    main(idx)
