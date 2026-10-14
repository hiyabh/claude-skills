# -*- coding: utf-8 -*-
"""Targeted Gemini edits of existing illustrations: change only the named detail, keep everything else.
Usage: IMG_MODEL=gemini-3.1-flash-image python edit_images.py <name> ...
The lite model ignores edit instructions - always edit with flash-image. Originals kept as build/img_old/<name>_v1.png;
if a _v1 backup already exists from an older image, rename it first or the OLD image gets edited."""
import base64
import shutil
import sys
from pathlib import Path

from gen_images import BASE, MODEL, OUT_DIR, extract_png, http_post, load_key, normalize

OLD_DIR = Path(__file__).resolve().parent / "img_old"

KEEP = (" Keep EVERYTHING else exactly the same: the same composition, camera framing, people positions and poses, "
        "background, lighting, colors and flat 2D storybook art style. Change nothing except what is described. "
        "No text, no letters, no captions, no logos.")
TICHEL = ("a Jewish married-woman's TICHEL: a colorful cloth scarf covering only the hair, tied in a knot at the BACK "
          "of the head at the nape, so the whole face, the chin, the jawline, the ears area and the neck stay fully "
          "visible and uncovered. NOT a hijab, NOT wrapped around the face, chin or neck, NOT pinned under the chin, "
          "NOT draped over the shoulders, no veil of any kind")

# Project edits live in build/edits.py: EDITS = {"name": "Change ONLY ... {TICHEL} ..."}
from edits import EDITS  # noqa: E402


def edit(key, name):
    src = OUT_DIR / f"{name}.png"
    OLD_DIR.mkdir(exist_ok=True)
    backup = OLD_DIR / f"{name}_v1.png"
    if not backup.exists():
        shutil.copy2(src, backup)
    img = base64.b64encode(backup.read_bytes()).decode()
    resp = http_post(f"{BASE}/models/{MODEL}:generateContent?key={key}",
                     {"contents": [{"parts": [{"inlineData": {"mimeType": "image/png", "data": img}},
                                              {"text": EDITS[name].replace("{TICHEL}", TICHEL) + KEEP}]}],
                      "generationConfig": {"imageConfig": {"aspectRatio": "16:9"}}})
    raw = extract_png(resp)
    if not raw:
        print("  NO IMAGE", name, flush=True)
        return
    normalize(raw, src)
    print("  EDITED", name, src.stat().st_size // 1024, "KB", flush=True)


def main(names):
    key = load_key()
    for name in names or EDITS:
        print("==", name, flush=True)
        edit(key, name)
    print("DONE")


if __name__ == "__main__":
    main(sys.argv[1:])
