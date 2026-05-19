"""Per-page extraction via pdfplumber.

Pdfplumber gives every word with exact (x0,top,x1,bottom). For Persian
poetry this is gold:
  * Cluster words into lines by `top` (Y).
  * Split each line into two hemistichs by X-center relative to the
    page midpoint (the gutter between the two columns).
  * pdfplumber returns each word's characters in *visual* order
    (reversed from Unicode logical order for RTL scripts) -- reverse
    each word to recover logical text.

Output: pages.json -- list (one entry per body PDF page) of:
  {"page_pdf": <int>, "lines": [{"text": "...", "h1": "...", "h2": "..."}, ...]}
"""
import json
import re
import sys

import pdfplumber


PDF_PATH = "shahnameh2.pdf"
FIRST_BODY_PAGE = 31    # PDF page (1-indexed) where body starts
LAST_PAGE = 1973        # inclusive
Y_TOLERANCE = 3.0       # words within this Y span belong to the same line
ZWNJ = "‌"


def reverse_word(text: str) -> str:
    """Pdfplumber chars come in visual (reversed) order for RTL.
    Reversing the codepoint sequence yields logical Unicode order."""
    return text[::-1]


def cluster_lines(words):
    """Group words into lines by their `top` Y coordinate."""
    words = sorted(words, key=lambda w: (w["top"], w["x0"]))
    lines = []
    current_top = None
    current = []
    for w in words:
        if current_top is None or abs(w["top"] - current_top) <= Y_TOLERANCE:
            current.append(w)
            current_top = w["top"] if current_top is None else current_top
        else:
            lines.append(current)
            current = [w]
            current_top = w["top"]
    if current:
        lines.append(current)
    return lines


def line_to_hemistichs(line_words, page_mid_x):
    """Given the words of one PDF line (sorted by top), produce the line's
    text as hem1/hem2 (logical order, Persian R-to-L)."""
    # Sort by X descending = Persian reading order
    line_words = sorted(line_words, key=lambda w: -((w["x0"] + w["x1"]) / 2))
    right_col = [w for w in line_words if (w["x0"] + w["x1"]) / 2 > page_mid_x]
    left_col = [w for w in line_words if (w["x0"] + w["x1"]) / 2 <= page_mid_x]
    h1_text = " ".join(reverse_word(w["text"]) for w in right_col)
    h2_text = " ".join(reverse_word(w["text"]) for w in left_col)
    return h1_text, h2_text


HEADER_TEXT = "www.takbook.com"
FOOTER_RE = re.compile(r"^\s*\d+\s*$")


def is_header_word(w):
    return "takbook" in w["text"].lower()


def is_footer(line_words):
    if len(line_words) != 1:
        return False
    return bool(FOOTER_RE.match(line_words[0]["text"]))


MIN_GUTTER_PT = 25.0  # minimum gap between hem1 and hem2 to call a line a beyt


def process_page(page, page_pdf: int) -> dict:
    page_mid_x = page.width / 2
    words = [w for w in page.extract_words(x_tolerance=2) if not is_header_word(w)]
    line_clusters = cluster_lines(words)
    lines = []
    for cluster in line_clusters:
        if is_footer(cluster):
            continue
        right_col = [w for w in cluster if (w["x0"] + w["x1"]) / 2 > page_mid_x]
        left_col  = [w for w in cluster if (w["x0"] + w["x1"]) / 2 <= page_mid_x]

        # Decide: is this a beyt (two hemistichs split by a real gutter) or a
        # single text run (heading, prose paragraph)?
        is_beyt = False
        if right_col and left_col:
            left_right_edge = max(w["x1"] for w in left_col)
            right_left_edge = min(w["x0"] for w in right_col)
            gutter = right_left_edge - left_right_edge
            is_beyt = gutter >= MIN_GUTTER_PT

        if is_beyt:
            h1, h2 = line_to_hemistichs(cluster, page_mid_x)
            lines.append({"text": f"{h1} || {h2}", "h1": h1, "h2": h2})
        else:
            # Heading or single text run -- output as one Persian-ordered line
            sorted_words = sorted(cluster, key=lambda w: -((w["x0"] + w["x1"]) / 2))
            text = " ".join(reverse_word(w["text"]) for w in sorted_words)
            lines.append({"text": text, "h1": None, "h2": None})
    return {"page_pdf": page_pdf, "lines": lines}


def main(pages_to_run: range):
    out = []
    with pdfplumber.open(PDF_PATH) as pdf:
        for i, page_pdf in enumerate(pages_to_run, 1):
            page = pdf.pages[page_pdf - 1]
            try:
                out.append(process_page(page, page_pdf))
            except Exception as e:
                print(f"  page {page_pdf} ERROR: {e}", file=sys.stderr)
                out.append({"page_pdf": page_pdf, "lines": []})
            if i % 100 == 0:
                print(f"  processed {i}/{len(pages_to_run)} pages")
    with open("pages.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"Wrote pages.json ({len(out)} pages)")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "sample":
        # Just test the rostam-birth page
        main(range(181, 184))
    else:
        main(range(FIRST_BODY_PAGE, LAST_PAGE + 1))
