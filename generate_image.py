"""Generate hero images for the Shahnameh site using OpenAI's image API.

Usage: python generate_image.py [target]
  target = "cover" | "cover-ref" | "078"    (default: cover)

The "cover-ref" target uses images.edit() with downloaded reference images of
Ferdowsi to anchor the generation in the canonical visual depiction.
"""
from __future__ import annotations

import base64
import os
import sys
import urllib.request
from pathlib import Path

import httpx
from dotenv import load_dotenv
from openai import OpenAI, BadRequestError, NotFoundError

ROOT = Path(__file__).parent
IMAGES_DIR = ROOT / "public" / "images"
REFS_DIR = ROOT / "references"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
REFS_DIR.mkdir(exist_ok=True)

REFERENCE_URLS = [
    ("ref-1-gstatic.jpg",
     "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTE383UxV7blyxeb2RASjECWoMFCUD2KQSKMw&s"),
    ("ref-2-independent.jpg",
     "https://www.independentpersian.com/sites/default/files/styles/1368x911/public/%D9%81%D8%B1%D8%AF%D9%88%D8%B3%DB%8C.jpg?itok=YeHdSmMb"),
    ("ref-3-dowlatabadi.jpg",
     "https://dowlatabadi.net/wp-content/uploads/2025/11/%D9%81%D8%B1%D8%AF%D9%88%D8%B3%DB%8C.jpg"),
    ("ref-4-tza.jpg",
     "https://www.t-z-a.org/Content/Images/Ferdosi.jpg"),
    ("ref-5-statue.jpg",
     "https://erfaniran.wordpress.com/wp-content/uploads/2012/04/ferdowsi_statue.jpg"),
]


def download_references() -> list[Path]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )
    }
    paths = []
    with httpx.Client(headers=headers, follow_redirects=True, timeout=30) as client:
        for name, url in REFERENCE_URLS:
            path = REFS_DIR / name
            if not path.exists():
                print(f"  downloading {url}")
                try:
                    r = client.get(url)
                    r.raise_for_status()
                    path.write_bytes(r.content)
                    print(f"    saved {len(r.content)//1024} KB → {path.relative_to(ROOT)}")
                except Exception as e:
                    print(f"    skipped ({type(e).__name__}: {e})")
                    continue
            else:
                print(f"  cached  {path.relative_to(ROOT)}")
            paths.append(path)
    return paths

PROMPT_COVER = (
    "An atmospheric painted close-up portrait of a fictional elderly medieval "
    "Iranian scholar-poet from the Khorasan region around the year 1000 CE. "
    "Painted in the classical Persian manuscript tradition with rich painterly depth.\n\n"

    "The figure is dignified and serene, with a long full white beard reaching the "
    "chest, a traditional white Khorasani turban with a small flowing tail, "
    "olive-toned weathered skin, and a modest robe of muted dark olive-green wool "
    "over a cream undergarment. His expression is calm and contemplative — the "
    "eyes deep warm brown, slightly lidded, looking past the viewer toward "
    "something eternal, full of quiet intelligence.\n\n"

    "Lighting: a single warm oil lamp glow from one side casts golden light across "
    "half the face while the other half rests in deep velvety shadow. The white of "
    "his beard and turban catches the lamplight beautifully.\n\n"

    "Background: nearly black, deep indigo and umber, dissolving into mystery. "
    "Faint, dreamlike hints of a mythic world barely visible in the darkness — "
    "the silhouette of a great mythical bird's outspread wing arcing through the "
    "upper darkness, a tiny distant lone rider on horseback crossing a far horizon, "
    "soft stars and a thin crescent moon. These elements are felt more than seen.\n\n"

    "Frame: an elegant illuminated Persian manuscript border at the very edges — "
    "fine gold arabesque, paisley (boteh) motifs, and small shamseh sun-medallions "
    "in the four corners on a lapis-blue ground.\n\n"

    "Palette: warm gold, ivory, silver-white on the figure; deep indigo, umber and "
    "black behind; vermillion and lapis-lazuli blue accents in the borders.\n\n"

    "Style: classical Persian portrait tradition, painterly atmospheric realism, "
    "museum-quality, reverent and intimate. No text, no calligraphy in the image, "
    "no signatures, no watermarks, no modern objects."
)

PROMPT_078 = (
    "A cinematic illuminated folio honoring the birth of Rostam from Ferdowsi's "
    "Shahnameh — a fusion of the classical Tabriz and Safavid miniature schools "
    "(Bayasanghori Shahnameh, Shah Tahmasp Shahnameh, Behzad) with the modern "
    "atmospheric school of Mahmoud Farshchian. Epic, sacred, mythic — yet emotionally "
    "intimate and accessible to a modern viewer.\n\n"

    "FOCAL POINT — the radiant newborn Rostam at the visual heart of the composition, "
    "bathed in a luminous golden halo of divine farr (the Iranian glory of kings and heroes). "
    "He is an unusually large, perfectly serene infant, held gently aloft by his mother "
    "RUDABE — a queenly Persian beauty with long jet-black braids interwoven with pearls, "
    "a jeweled diadem, almond eyes painted with kohl, and richly embroidered robes of "
    "vermillion silk over indigo. Beside her stands ZAL, the white-haired hero-father, "
    "lowering his head in reverence, one hand on his heart.\n\n"

    "ABOVE — emerging from the upper margin as if from another realm, the great SIMORGH: "
    "a mythic Persian bird of paradise with vast outspread wings, peacock-iridescent "
    "plumage of lapis-blue, emerald, gold and crimson, a long flowing tail, eyes like "
    "embers. Her wings arc protectively over the scene; a few feathers drift down, glowing.\n\n"

    "SETTING — a moonlit Persian palace pavilion: a great pointed arch of intricate "
    "muqarnas tile work in turquoise and cobalt; slender columns; carved cypress doors; "
    "a courtyard beyond with tall cypress trees, blooming pomegranate, a still reflecting "
    "pool catching starlight. In the lower foreground a small, exquisite gathering of "
    "courtiers, musicians (kamancheh, daf, ney), and gift-bearers in turbans and "
    "embroidered caftans — rendered tiny and reverent, drawn back to give the holy moment air.\n\n"

    "LIGHT — dual lighting: warm golden candlelight from within the pavilion catching "
    "Rudabe and the child, and cool silver moonlight and starlight from the night sky "
    "beyond. The farr-halo around Rostam is the brightest source, casting subtle gold "
    "reflections on the faces around him.\n\n"

    "PALETTE — deep lapis-lazuli ultramarine, antique gold leaf, vermillion, saffron, "
    "emerald, ivory. Texture of aged hand-laid paper, faint cracks in the gold leaf, "
    "jewel-like saturated pigments. Fine ink outlines, layered detail.\n\n"

    "BORDER — an elaborate illuminated frame of arabesque vine-scrolls, paisley (boteh), "
    "shamseh sun-medallions in the corners, and stylized peacocks — all in gold on "
    "lapis ground. The whole image reads as a single sacred folio from a royal manuscript.\n\n"

    "MOOD — reverent, mythic, hushed, monumental. The birth of a hero foretold by destiny. "
    "Honors Ferdowsi and the Iranian epic tradition with absolute respect — no orientalist "
    "kitsch, no fantasy-novel cliché, no flatness. Museum-quality. Wide cinematic format.\n\n"

    "STRICT — no text, no Arabic or Persian calligraphy in the image, no captions, "
    "no signatures, no watermarks, no modern elements."
)


PROMPT_COVER_REF = (
    "Using the provided reference images as visual anchor for the subject's face, "
    "facial features, beard, turban shape, and traditional Iranian scholarly attire, "
    "create a monumental, soul-stirring painted close-up portrait of the same iconic "
    "elderly Persian poet-scholar shown across the references — preserving his "
    "recognizable likeness (the noble bearing, the white-streaked dark beard, the "
    "distinctive Khorasani turban with its small flowing tail, the dignified jaw "
    "and brow), rendered in the painterly atmospheric tradition of classical Persian "
    "portrait painting.\n\n"

    "Pose: a tight close-up from the chest up, head turned about three-quarters toward "
    "the viewer, gaze directed slightly past the viewer toward eternity — calm, "
    "intelligent, deeply soulful.\n\n"

    "Lighting: single warm oil-lamp light from one side casting golden glow across "
    "half the face, the other half receding into deep velvety shadow. Subtle "
    "catchlights in the eyes. The white of beard and turban catches the lamplight "
    "like fresh snow at dusk.\n\n"

    "Background: nearly black, deep indigo and umber. Within the darkness — barely "
    "visible, dreamlike — float faint hints of the mythic world that lives in his mind: "
    "the silhouette of a great mythical bird's outspread wing arcing overhead, the "
    "tiny distant outline of a lone rider on horseback on a far horizon, soft stars "
    "and a thin crescent moon. These are felt more than seen.\n\n"

    "Frame: an elegant illuminated Persian manuscript border at the very edges — "
    "fine gold arabesque, paisley (boteh), and small shamseh sun-medallions in the "
    "four corners on a lapis-blue ground.\n\n"

    "Palette: warm gold, ivory, silver-white on the figure; deep indigo, umber and "
    "black behind; vermillion and lapis-lazuli accents in the borders.\n\n"

    "Style: painterly, museum-quality, reverent and intimate. No text, no "
    "calligraphy in the image, no signatures, no watermarks, no modern objects, "
    "no eyeglasses. Portrait orientation, like a folio from an illuminated manuscript."
)

TARGETS = {
    "cover": {
        "mode": "generate",
        "prompt": PROMPT_COVER,
        "size": "1024x1536",
        "out": "cover-ferdowsi.png",
    },
    "cover-ref": {
        "mode": "edit",
        "prompt": PROMPT_COVER_REF,
        "size": "1024x1536",
        "out": "cover-ferdowsi-ref.png",
    },
    "078": {
        "mode": "generate",
        "prompt": PROMPT_078,
        "size": "1536x1024",
        "out": "078-rostamzad-v2.png",
    },
}


def main() -> int:
    load_dotenv(ROOT / ".env")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY is empty in .env", file=sys.stderr)
        return 1

    target_name = sys.argv[1] if len(sys.argv) > 1 else "cover"
    if target_name not in TARGETS:
        print(f"ERROR: unknown target '{target_name}'. choices: {list(TARGETS)}", file=sys.stderr)
        return 2
    target = TARGETS[target_name]

    model = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")
    client = OpenAI(api_key=api_key)

    out_path = IMAGES_DIR / target["out"]
    print(f"Requesting image from model: {model}")
    print(f"Target: {target_name}  ({target['size']})")
    print(f"Output: {out_path.relative_to(ROOT)}")

    if target["mode"] == "edit":
        print("Downloading reference images...")
        refs = download_references()
        if not refs:
            print("ERROR: no reference images available", file=sys.stderr)
            return 3
        print(f"Using {len(refs)} reference image(s)")

    def call(model_name: str):
        if target["mode"] == "edit":
            handles = [open(p, "rb") for p in refs]
            try:
                return client.images.edit(
                    model=model_name,
                    image=handles,
                    prompt=target["prompt"],
                    size=target["size"],
                    n=1,
                )
            finally:
                for h in handles:
                    h.close()
        return client.images.generate(
            model=model_name,
            prompt=target["prompt"],
            size=target["size"],
            n=1,
        )

    try:
        resp = call(model)
    except (NotFoundError, BadRequestError) as e:
        msg = str(e)
        if model != "gpt-image-1" and ("model" in msg.lower() or "not found" in msg.lower()):
            print(f"  model '{model}' not available ({type(e).__name__}); falling back to gpt-image-1")
            resp = call("gpt-image-1")
        else:
            raise

    datum = resp.data[0]
    if getattr(datum, "b64_json", None):
        out_path.write_bytes(base64.b64decode(datum.b64_json))
    elif getattr(datum, "url", None):
        import urllib.request
        urllib.request.urlretrieve(datum.url, out_path)
    else:
        print("ERROR: response had no image payload", file=sys.stderr)
        return 1

    print(f"Saved {out_path.stat().st_size // 1024} KB → {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
