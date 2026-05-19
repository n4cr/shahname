"""Parse Shahnameh TOC into structured story list.

TOC pages = PDF 6-30. Body starts at PDF 31 = printed page 1 (offset +30).
Each TOC entry has the form: <title>........<page_number>
Bold entries (major reigns) and indented entries (sub-stories) both have the
same dotted-leader pattern; the visual hierarchy isn't reliably encoded in
the text stream, so we treat everything as a flat story list.

Numbers in the TOC are a mix of:
  - ASCII digits (e.g., 1325)
  - Persian/Arabic-Indic digits (e.g., ۱۳۲۵)
Both must be normalized.
"""
import re
import json
import unicodedata

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
DIGIT_MAP = {ord(c): str(i) for i, c in enumerate(PERSIAN_DIGITS)}
DIGIT_MAP.update({ord(c): str(i) for i, c in enumerate(ARABIC_DIGITS)})

# pdftotext wraps RTL runs with these bidi control chars
BIDI_CHARS = "‪‫‬‭‮‎‏⁦⁧⁨⁩"


def normalize(s: str) -> str:
    s = s.translate(DIGIT_MAP)
    s = "".join(c for c in s if c not in BIDI_CHARS)
    return s.strip()


# Layout looks like: <RLE>title<LRE>NUMBER<dots><PDF>
# After stripping bidi controls: "title<digits><dots>"
# (the number sits between title and dotted leader, no whitespace)
ENTRY_RE = re.compile(r"^(.+?)(\d+)\.{2,}\s*$")


def parse_toc(path: str) -> list[dict]:
    entries = []
    seen = set()
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = normalize(raw)
            if not line:
                continue
            # Skip the website header line and single-character page footers
            if "takbook.com" in line or len(line) <= 2:
                continue
            # Skip the "فهرست" header
            if line == "فهرست":
                continue
            m = ENTRY_RE.match(line)
            if not m:
                continue
            title = m.group(1).strip()
            page = int(m.group(2))
            # Some titles end with stray dots from leader bleed-through
            title = title.rstrip(".").strip()
            if not title:
                continue
            key = (title, page)
            if key in seen:
                continue
            seen.add(key)
            entries.append({"title": title, "printed_page": page, "pdf_page": page + 30})
    return entries


if __name__ == "__main__":
    stories = parse_toc("toc.txt")
    with open("toc.json", "w", encoding="utf-8") as f:
        json.dump(stories, f, ensure_ascii=False, indent=2)
    print(f"Parsed {len(stories)} entries")
    print("First 5:")
    for s in stories[:5]:
        print(f"  p{s['printed_page']:>4} (pdf {s['pdf_page']}): {s['title']}")
    print("Last 5:")
    for s in stories[-5:]:
        print(f"  p{s['printed_page']:>4} (pdf {s['pdf_page']}): {s['title']}")
