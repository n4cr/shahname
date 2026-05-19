"""Split body into per-story files.

Strategy: trust the body's actual heading positions, not the TOC order.

Some titles on the same printed page appear in the body in a different order
than the TOC lists them (e.g., printed page 3 has ستایش خرد first, آفرینش جهان
second — TOC says the opposite). So:

  1. Clean every body page.
  2. For each TOC entry, locate its title heading in the body (search starts
     on its claimed page, then expands +/- 1 to handle small drift).
  3. Build (page, line) anchors and sort by body position.
  4. Each story is the slice between its anchor and the next anchor.
"""
import json
import os
import re

BIDI_CHARS = set("‎‏‪‫‬‭‮⁦⁧⁨⁩")
HEADER_RE = re.compile(r"^\s*www\.takbook\.com\s*$")
FOOTER_RE = re.compile(r"^\s*\d+\s*$")
PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
DIGIT_MAP = {ord(c): str(i) for i, c in enumerate(PERSIAN_DIGITS)}
DIGIT_MAP.update({ord(c): str(i) for i, c in enumerate(ARABIC_DIGITS)})

# pdftotext wraps each RTL text "run" with U+202B (RLE) ... U+202C (PDF).
# Runs are laid out spatially L-to-R; to recover Persian reading order
# (R-to-L), we reverse the run order. Words *inside* a run are already in
# logical order, so they stay put.
RLE = "‫"
PDFCH = "‬"
SEGMENT_RE = re.compile(re.escape(RLE) + r"(.+?)" + re.escape(PDFCH))


def _strip_bidi(s: str) -> str:
    return "".join(c for c in s if c not in BIDI_CHARS)


HEMISTICH_SEP = " || "


def _clean_segment(text: str) -> str:
    text = _strip_bidi(text).translate(DIGIT_MAP)
    return re.sub(r"\s+", " ", text).strip()


def reconstruct_line(raw_line: str) -> str:
    """Given one raw pdftotext line, return text in Persian reading order.

    Couplets are returned as "hem1 || hem2" (with HEMISTICH_SEP). Single-
    segment lines (headings, blanks) are returned as plain text.

    Splitting strategy: every Persian text run from pdftotext is wrapped in
    U+202B (RLE) … U+202C (PDF). Runs are laid out spatially L→R, but
    Persian reads R→L, so we reverse the run order. The hemistich boundary
    falls at the inter-segment gap closest to the line's spatial midpoint
    (works for both centered/non-justified and fully-justified couplets).
    """
    matches = list(SEGMENT_RE.finditer(raw_line))
    if not matches:
        return _strip_bidi(raw_line).translate(DIGIT_MAP).strip()
    cleaned = [(m, _clean_segment(m.group(1))) for m in matches]
    cleaned = [(m, t) for m, t in cleaned if t]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0][1]

    # Find the hemistich boundary:
    #   * If one inter-segment gap dominates (the line is *not* fully
    #     justified — there's a clear gutter between two short columns),
    #     use that gap.
    #   * Otherwise the line is fully justified; all gaps are similar and
    #     can't pick out the gutter. Fall back to splitting where the two
    #     halves are most balanced in word count.
    gaps = [
        cleaned[i + 1][0].start() - cleaned[i][0].end()
        for i in range(len(cleaned) - 1)
    ]
    sorted_gaps = sorted(gaps)
    median_gap = sorted_gaps[len(sorted_gaps) // 2]
    max_gap = max(gaps)
    if max_gap >= 2.5 * max(median_gap, 1):
        best_idx = gaps.index(max_gap)
    else:
        word_counts = [len(t.split()) for _, t in cleaned]
        total = sum(word_counts)
        best_idx = 0
        best_imbalance = float("inf")
        cum = 0
        for i in range(len(word_counts) - 1):
            cum += word_counts[i]
            imbalance = abs(cum - (total - cum))
            if imbalance < best_imbalance:
                best_imbalance = imbalance
                best_idx = i

    # cleaned[: best_idx+1] are the LEFT-column (hem2) segments, spatial L→R.
    # cleaned[best_idx+1 :] are the RIGHT-column (hem1) segments, spatial L→R.
    # To get logical Persian word order within each column, reverse.
    hem2_words = [t for _, t in reversed(cleaned[: best_idx + 1])]
    hem1_words = [t for _, t in reversed(cleaned[best_idx + 1 :])]
    hem1 = " ".join(hem1_words)
    hem2 = " ".join(hem2_words)
    return f"{hem1}{HEMISTICH_SEP}{hem2}"


def clean_page(raw: str) -> list[str]:
    out = []
    for ln in raw.split("\n"):
        line = reconstruct_line(ln)
        if not line:
            out.append("")
            continue
        if HEADER_RE.match(line) or FOOTER_RE.match(line):
            continue
        out.append(line)
    while out and not out[0]:
        out.pop(0)
    while out and not out[-1]:
        out.pop()
    return out


def squish(s: str) -> str:
    return s.replace("‌", "").replace(" ", "")


def find_title_in_page(lines: list[str], title: str) -> int:
    """Return line index of title in page, or -1."""
    title_norm = re.sub(r"\s+", " ", title.strip())
    for i, ln in enumerate(lines):
        if ln == title_norm:
            return i
    for i, ln in enumerate(lines):
        if title_norm in ln:
            return i
    tsq = squish(title_norm)
    if not tsq:
        return -1
    for i, ln in enumerate(lines):
        if squish(ln) == tsq:
            return i
    for i, ln in enumerate(lines):
        if tsq in squish(ln):
            return i
    return -1


def locate_title(pages: list[list[str]], title: str, hinted_page_idx: int) -> tuple[int, int]:
    """Find (page_idx, line_idx) for title. Search hinted page first, then
    a small window around it. Return (-1, -1) if not found."""
    candidates = [hinted_page_idx]
    for delta in range(1, 4):
        if hinted_page_idx - delta >= 0:
            candidates.append(hinted_page_idx - delta)
        if hinted_page_idx + delta < len(pages):
            candidates.append(hinted_page_idx + delta)
    for p in candidates:
        line = find_title_in_page(pages[p], title)
        if line >= 0:
            return (p, line)
    return (-1, -1)


def sanitize_filename(s: str) -> str:
    s = re.sub(r"[\/\\:*?\"<>|]", "_", s)
    s = re.sub(r"\s+", "_", s.strip())
    return s[:80]


def main():
    with open("toc.json", encoding="utf-8") as f:
        toc = json.load(f)
    # Prefer pdfplumber-extracted pages.json (clean hemistich splits).
    # Fall back to legacy body.txt cleaner if pages.json is missing.
    if os.path.exists("pages.json"):
        with open("pages.json", encoding="utf-8") as f:
            doc = json.load(f)
        # body.txt indexing: pages[0] = first body PDF page; same here.
        pages = [[ln["text"] for ln in p["lines"]] for p in doc]
    else:
        with open("body.txt", encoding="utf-8") as f:
            raw_pages = f.read().split("\f")
        pages = [clean_page(p) for p in raw_pages]
    print(f"Loaded {len(pages)} pages.")

    # Step 1: locate every TOC title in the body.
    located = []
    n_found = 0
    n_fallback = 0
    for entry in toc:
        hinted = entry["printed_page"] - 1
        p, l = locate_title(pages, entry["title"], hinted)
        if p < 0:
            p, l = hinted, 0
            n_fallback += 1
        else:
            n_found += 1
        located.append({**entry, "body_page": p, "body_line": l})

    # Step 2: sort by body position so out-of-order TOC entries land in real order.
    located.sort(key=lambda e: (e["body_page"], e["body_line"]))

    # Step 3: slice between anchors.
    out_dir = "stories"
    os.makedirs(out_dir, exist_ok=True)
    for fn in os.listdir(out_dir):
        os.remove(os.path.join(out_dir, fn))

    manifest = []
    for i, entry in enumerate(located):
        sp, sl = entry["body_page"], entry["body_line"]
        if i + 1 < len(located):
            ep, el = located[i + 1]["body_page"], located[i + 1]["body_line"]
        else:
            ep, el = len(pages) - 1, len(pages[-1])

        # Collect lines between (sp, sl) and (ep, el) exclusive of end.
        lines_out = []
        if sp == ep:
            lines_out.extend(pages[sp][sl:el])
        else:
            lines_out.extend(pages[sp][sl:])
            for p in range(sp + 1, ep):
                lines_out.append("")
                lines_out.extend(pages[p])
            if ep < len(pages):
                lines_out.append("")
                lines_out.extend(pages[ep][:el])

        text = "\n".join(lines_out).strip() + "\n"
        fname = f"{i + 1:03d}-{sanitize_filename(entry['title'])}.txt"
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
            f.write(text)
        manifest.append({
            "index": i + 1,
            "title": entry["title"],
            "printed_page": entry["printed_page"],
            "body_page": sp,
            "body_line": sl,
            "filename": fname,
            "non_empty_lines": sum(1 for l in lines_out if l.strip()),
        })

    with open("manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(manifest)} story files to {out_dir}/")
    print(f"  Title located precisely: {n_found}")
    print(f"  Title not found anywhere nearby (fell back to page top): {n_fallback}")
    # Distribution of story sizes
    sizes = sorted(m["non_empty_lines"] for m in manifest)
    n = len(sizes)
    print(f"  Story size couplets: min={sizes[0]} p50={sizes[n//2]} p95={sizes[int(n*0.95)]} max={sizes[-1]}")
    print(f"  Empty stories: {sum(1 for s in sizes if s == 0)}")


if __name__ == "__main__":
    main()
