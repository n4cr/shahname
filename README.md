# شاهنامه — Shahnameh

A static, bilingual (Persian / English) website honoring Ferdowsi's *Shahnameh* — the original verse alongside accessible retellings and Persian-miniature-style illustrations.

## Stack

- **Astro** — static site generation, content collections, i18n routing
- **YAML** — one file per highlighted story under `src/content/stories/`
- **GitHub Pages** — hosting (free, via the workflow in `.github/workflows/deploy.yml`)
- **Python (.venv)** — image generation via OpenAI's `gpt-image-1` / `gpt-image-2` (`generate_image.py`)

## Layout

```
shahnameh/
├── src/
│   ├── pages/
│   │   ├── index.astro                 ← FA home (/)
│   │   ├── stories/[slug].astro        ← FA story pages (/stories/{slug})
│   │   └── en/
│   │       ├── index.astro             ← EN home (/en)
│   │       └── stories/[slug].astro    ← EN story pages (/en/stories/{slug})
│   ├── content/stories/                ← bilingual YAML, one per highlighted story
│   ├── layouts/Base.astro              ← shared shell, fonts, language switcher
│   ├── lib/poem.ts                     ← verse parser (couplets, stanzas)
│   └── styles/global.css               ← shared design tokens
├── public/images/                      ← illustrations served as static assets
├── stories/*.txt                       ← raw source poems (679 files, untouched)
├── toc.json, manifest.json             ← chapter metadata (for future TOC page)
├── generate_image.py                   ← image generation script (OpenAI)
├── references/                         ← reference images used by generate_image.py
├── tools/pdf-extraction/               ← archived one-time PDF→stories pipeline
└── .github/workflows/deploy.yml        ← GitHub Pages CI/CD
```

## Develop

```bash
npm install
npm run dev          # http://localhost:4321
npm run build        # → dist/
npm run preview
```

## Coverage tiers

Every story is on one of three tiers. URLs use the 3-digit id, e.g. `/stories/078`.

| Tier | What's there | Where it appears | Effort to add |
|---|---|---|---|
| **Plain** | original verses only (from `stories/{id}.txt`) | FA only — `/stories/{id}` | 0 — automatic, all 679 already exist |
| **FA highlight** | + Persian prose retelling, optional image, cast, pull quote | FA story tabs | one YAML + (optional) one image |
| **Bilingual highlight** | + English prose | EN side appears at `/en/stories/{id}` | add `prose.en` to the same YAML |

The full FA index at `/stories` lists every story, with a gold ◆ marker on the highlighted ones. The EN index at `/en/stories` lists only the bilingual ones.

## Add a highlight

1. Pick a story id (3-digit, e.g. `142`).
2. (Optional, ~$0.10–0.30) Generate a hero illustration:
   ```bash
   .venv/bin/python generate_image.py 142   # writes public/images/142-*.png
   ```
3. Create `src/content/stories/142.yaml`. Use `078.yaml` as the template. Only these fields are required:
   - `id`, `order`
   - `chapter.num`, `chapter.fa`
   - `title.fa`
   - `prose.fa` (a list of paragraphs; use `"::quote::"` to mark where the pull quote sits inline)
   - `versesFa` (paste a cleaned-up version of the original verses)
4. To enable the English side, add `prose.en` (and ideally `title.en`, `chapter.en`).
5. Push — both routes rebuild automatically.

## Deploy

Push to `main`. The workflow builds with Astro and deploys to GitHub Pages.

### Custom domain

1. Buy the domain
2. Add a `public/CNAME` file containing the bare domain (e.g. `shahnameh.org`)
3. Point DNS at GitHub Pages (their docs)
4. In `astro.config.mjs`, update `site:` to the full URL

### Hosting on `username.github.io/shahnameh` instead

Set `base: "/shahnameh"` in `astro.config.mjs`.

## Image generation

The Python script uses OpenAI's image API. Reference images of Ferdowsi live in `references/`. Output writes to `public/images/`.

```bash
.venv/bin/python generate_image.py cover-ref   # Ferdowsi portrait (anchored by references)
.venv/bin/python generate_image.py 078         # Rostam-zad illumination
```
