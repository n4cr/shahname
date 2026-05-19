"""Diagnose which TOC titles failed to match exactly on their start page."""
import json
import re

BIDI_CHARS = set("‎‏‪‫‬‭‮⁦⁧⁨⁩")
PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
DIGIT_MAP = {ord(c): str(i) for i, c in enumerate(PERSIAN_DIGITS)}
DIGIT_MAP.update({ord(c): str(i) for i, c in enumerate(ARABIC_DIGITS)})


def clean_page(raw: str) -> list[str]:
    lines = raw.split("\n")
    out = []
    for ln in lines:
        ln = "".join(c for c in ln if c not in BIDI_CHARS).translate(DIGIT_MAP).strip()
        if not ln:
            continue
        if ln == "www.takbook.com":
            continue
        if re.fullmatch(r"\d+", ln):
            continue
        out.append(re.sub(r"\s+", " ", ln))
    return out


def squish(s):
    return s.replace("‌", "").replace(" ", "")


with open("toc.json", encoding="utf-8") as f:
    toc = json.load(f)
with open("body.txt", encoding="utf-8") as f:
    raw_pages = f.read().split("\f")
pages = [clean_page(p) for p in raw_pages]

print(f"{'idx':>4}  {'pp':>5}  title  -> first 3 lines of page")
print("-" * 100)
for idx, entry in enumerate(toc):
    title = re.sub(r"\s+", " ", entry["title"].strip())
    pp = entry["printed_page"]
    lines = pages[pp - 1]
    found_exact = title in lines
    found_contained = any(title in l for l in lines)
    found_squish = any(squish(title) in squish(l) for l in lines)
    if not found_exact:
        why = "contained" if found_contained else ("squish" if found_squish else "NOT FOUND")
        print(f"{idx + 1:>4}  {pp:>5}  [{why}] {title}")
        for l in lines[:4]:
            print(f"              | {l}")
