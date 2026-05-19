# PDF Extraction (archived)

One-time pipeline that turned a scanned/digital Shahnameh PDF into the per-story `.txt` files that live in `/stories/`. **You almost never need to run any of this again** — the output is already in the repo and is the source of truth for the verses.

These files are kept around purely so the extraction process is reproducible / debuggable.

## What each script did

| Script | Purpose |
|---|---|
| `extract_pdfplumber.py` | Pulled raw page text from the source PDF → `pages.json` + `body.txt` |
| `parse_toc.py` | Read the printed table of contents → `toc.json`, `toc.txt` |
| `split_stories.py` | Sliced `body.txt` into one file per story using the TOC offsets → `/stories/*.txt` |
| `diagnose.py` | Ad-hoc inspection helper used while iterating |
| `make_story_pdf*.py` | Three variants (basic, justified, kashida-stretched) that re-typeset a single story as a PDF for proofing |

## Data artifacts here

- `body.txt` — full extracted Persian text in reading order
- `pages.json` — per-page extraction with positions
- `toc.txt` — raw TOC text before parsing

## If you ever want to re-run

The source PDF (`shahnameh2.pdf`, ~5.8 MB) was deleted from the repo once extraction was complete. Drop a fresh copy at the project root, then from this folder:

```bash
../../.venv/bin/python extract_pdfplumber.py
../../.venv/bin/python parse_toc.py
../../.venv/bin/python split_stories.py
```
