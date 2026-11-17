# -*- coding: utf-8 -*-
"""Optional: a TEXT-FREE cover painting from an image model, shaped to the cover from the spec.

    python ai_art.py <cover_spec.json> --describe "<what to paint>" [--area wrap|front|back]
                     [--provider gemini|openai] [--model ID] [--count 2] [--reference img.png]
    python ai_art.py <cover_spec.json> --list-models [--provider gemini|openai]

Key from the environment or a .env file next to the spec: GEMINI_API_KEY (or GOOGLE_API_KEY) /
OPENAI_API_KEY. The model id is checked against the provider's live model list first, because ids
change. Every prompt says: no letters at all (type is set later as vector - image models misspell
Hebrew), where the front, spine and back fall (front on the LEFT for a Hebrew wrap), and the fixed
exclusion of other religions' symbols. Writes <spec folder>/ציורים/<area>_<n>.png and says the
resolution it gives at print size. Generating costs money on the author's account.
"""
import argparse
import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import geometry as G
import spec as S
from common import fail, px, warn

DEFAULT_MODEL = {"gemini": "gemini-3-pro-image", "openai": "gpt-image-1"}   # checked live before use
GEMINI_RATIOS = ("1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9")
OPENAI_SIZES = {"1024x1024": 1.0, "1536x1024": 1.5, "1024x1536": 2 / 3}
TIMEOUT = 600
NO_TEXT = ("Absolutely NO text: no letters, no words, no numbers, no Hebrew or English characters, no logos, "
           "no signatures, no watermark. Leave the title areas as calm, plain, uncluttered surfaces.")
NO_OTHER_RELIGIONS = ("No crosses, no churches, no steeples, no mosques, no minarets, no crescent, no halos, "
                      "no angels with wings, no Christmas or Easter decor, no Buddhist/Hindu symbols, no religious "
                      "symbols of any non-Jewish religion.")


def api_key(provider, spec_dir):
    names = ("GEMINI_API_KEY", "GOOGLE_API_KEY") if provider == "gemini" else ("OPENAI_API_KEY",)
    for name in names:
        if os.environ.get(name):
            return os.environ[name]
    env = spec_dir / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() in names and value.strip():
                return value.strip().strip('"')
    fail(f"חסר מפתח API ({' או '.join(names)}). הגדר משתנה סביבה, או כתוב אותו בקובץ .env ליד המפרט. "
         f"אפשר גם לוותר על AI ולתת ציור משלך או של מעצב.")


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def image_models(provider, key):
    if provider == "gemini":
        data = get_json(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}&pageSize=1000")
        return sorted(m["name"].split("/")[-1] for m in data.get("models", []) if "image" in m["name"])
    data = get_json("https://api.openai.com/v1/models", {"Authorization": f"Bearer {key}"})
    return sorted(m["id"] for m in data.get("data", []) if "image" in m["id"])


def target(spec, lay, area):
    """(box to fill, prompt lines about the layout)."""
    if area in ("front", "back"):
        return lay.panel(area), [f"A single book {area} cover, portrait."]
    box = lay.visible if spec["binding"] == "hard" else G.Box(0, 0, lay.width, lay.height)
    pct = lambda x: round(100 * (x - box.x) / box.w)  # noqa: E731
    f, s, b = lay.front, lay.spine, lay.back
    lines = [f"A full wrap-around book cover laid flat, wide format. From {pct(f.x)}% to {pct(f.right)}% of the width "
             f"is the FRONT cover, from {pct(s.x)}% to {pct(s.right)}% is the narrow SPINE, from {pct(b.x)}% to "
             f"{pct(b.right)}% is the BACK cover.",
             f"The front cover's main motif is centred exactly at {pct(f.cx)}% of the width.",
             "The spine band is a calm vertical strip that continues the scene seamlessly.",
             "The back cover has a large calm area for a paragraph of text and a small plain area near its "
             "bottom corner by the spine for a barcode."]
    return box, lines


def prompt(describe, lines):
    return " ".join([describe.strip()] + lines + [NO_TEXT, NO_OTHER_RELIGIONS])


def gemini(key, model, text, ratio, reference):
    parts = [{"text": text}]
    if reference:
        parts.insert(0, {"inlineData": {"mimeType": "image/png",
                                        "data": base64.b64encode(Path(reference).read_bytes()).decode()}})
    for size in ("4K", None):
        cfg = {"aspectRatio": ratio, **({"imageSize": size} if size else {})}
        body = json.dumps({"contents": [{"parts": parts}],
                           "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": cfg}}).encode()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, body, {"Content-Type": "application/json"}),
                                        timeout=TIMEOUT) as r:
                resp = json.load(r)
        except urllib.error.HTTPError as e:
            warn(f"Gemini החזיר {e.code}: {e.read().decode(errors='replace')[:200]}")
            continue
        found = [p["inlineData"]["data"] for c in resp.get("candidates", [])
                 for p in c.get("content", {}).get("parts", []) if "inlineData" in p]
        if found:
            return base64.b64decode(found[0])
    return None


def openai(key, model, text, ratio):
    size = min(OPENAI_SIZES, key=lambda s: abs(OPENAI_SIZES[s] - ratio))
    body = json.dumps({"model": model, "prompt": text, "size": size, "n": 1}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/images/generations", body,
                                 {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return base64.b64decode(json.load(r)["data"][0]["b64_json"])
    except urllib.error.HTTPError as e:
        warn(f"OpenAI החזיר {e.code}: {e.read().decode(errors='replace')[:200]}")
        return None


def nearest_ratio(r):
    return min(GEMINI_RATIOS, key=lambda s: abs(int(s.split(":")[0]) / int(s.split(":")[1]) - r))


def resolution_note(path, box, dpi):
    from PIL import Image
    w = Image.open(path).width
    eff = w / (box.w / 25.4)
    need = "מספיק" if eff >= dpi - 1 else ("להגדיל עם upscale.py" if eff >= dpi / 3 else "נמוך מדי גם להגדלה")
    return f"{path}: {w}px על {box.w:.0f} מ\"מ = {eff:.0f}dpi ({need}; היעד {px(box.w, dpi)}px)"


def generate(a, spec, spec_dir, key, model):
    if not a.describe:
        fail("כתוב --describe עם תיאור הציור (נושא, סגנון, צבעים).")
    lay = G.layout(spec)
    box, lines = target(spec, lay, a.area)
    text, out_dir = prompt(a.describe, lines), spec_dir / "ציורים"
    out_dir.mkdir(exist_ok=True)
    for n in range(1, a.count + 1):
        data = (gemini(key, model, text, nearest_ratio(box.w / box.h), a.reference) if a.provider == "gemini"
                else openai(key, model, text, box.w / box.h))
        if not data:
            fail("היצירה נכשלה. בדוק את המפתח ואת המכסה, או נסה מודל אחר.")
        path = out_dir / f"{a.area}_{n}.png"
        path.write_bytes(data)
        print(resolution_note(path, box, spec["dpi"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--describe", default="")
    ap.add_argument("--area", choices=("wrap", "front", "back"), default="wrap")
    ap.add_argument("--provider", choices=("gemini", "openai"), default="gemini")
    ap.add_argument("--model")
    ap.add_argument("--count", type=int, default=2)
    ap.add_argument("--reference")
    ap.add_argument("--list-models", action="store_true")
    a = ap.parse_args()
    spec = S.load(a.spec)
    spec_dir = Path(spec["spec_path"]).parent
    key = api_key(a.provider, spec_dir)
    models = image_models(a.provider, key)
    if a.list_models:
        print("\n".join(models))
        return
    model = a.model or DEFAULT_MODEL[a.provider]
    if model not in models:
        fail(f"המודל {model} לא נמצא ברשימה החיה של {a.provider}. מודלים זמינים: {', '.join(models) or 'אין'}. "
             f"הרץ שוב עם --model.")
    generate(a, spec, spec_dir, key, model)
    print("לפתוח כל ציור ב-Read ולהגדיל את הרקע: אותיות מזויפות, סמלים אסורים, ציור שלא ממורכז.")


if __name__ == "__main__":
    main()
