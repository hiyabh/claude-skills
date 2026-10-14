# -*- coding: utf-8 -*-
"""Generate 16:9 story illustrations with Gemini from build/scenes.py (SCENES, HISTORIC_SCENES, ANCIENT_SCENES, ANCIENT).
Cheapest model by default (verify price on the day). Output -> clip/assets/img/<name>.png at 1920x1080. Skips files that already exist."""
import base64
import os
from concurrent.futures import ThreadPoolExecutor
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ENV_PATH = Path(os.environ.get("GOOGLE_ENV_FILE", ".env"))  # optional .env fallback for the key
MODEL = os.environ.get("IMG_MODEL", "gemini-3.1-flash-lite-image")
BASE = "https://generativelanguage.googleapis.com/v1beta"
OUT_DIR = Path(__file__).resolve().parents[1] / "clip" / "assets" / "img"
MIN_BYTES = 50_000
RETRIES = 4

ART = (
    " ART STYLE: flat 2D vector storybook illustration, soft rounded shapes, clean outlines, gentle shading, "
    "evening palette of deep forest green, night blue and warm golden lamplight, calm and reverent mood, wide 16:9 framing, "
    "the scene fills the whole frame edge to edge with no empty or blank areas. "
)
TAIL = " Wholesome, family-friendly. No text, no Hebrew or English letters, no captions, no logos, no watermark."
# Modern scenes: religious-Zionist dress. Women: headscarf only, never a veil.
MODERN = (
    "MODESTY (STRICT, non-negotiable): every modern-day human is an observant RELIGIOUS-ZIONIST (Dati-Leumi) Jew "
    "dressed fully modestly - men and boys wear a KNITTED KIPPAH (kippah seruga), NOT a chareidi black hat, "
    "beard optional, a long-sleeved shirt with tzitzit; GIRLS NEVER WEAR A KIPPAH: any child with long hair, braids or ponytails is a girl and has "
    "NOTHING at all on her head, bare uncovered hair, long skirt); women have their hair covered with a Jewish TICHEL tied in a knot at the BACK of the head, face, chin, "
    "jawline and neck fully visible - NEVER a hijab wrapped around the face or under the chin, NEVER a hood, "
    "NEVER a face veil, nothing in Arab or Muslim style, long sleeves to the wrist, a high neckline, and a long skirt. "
    "Inside a synagogue hall there are ONLY men and boys. NO mosques, NO Dome of the Rock, NO golden domes, NO minarets anywhere."
)
# Historic Eastern-European scenes: knitted kippot did not exist then.
HISTORIC = (
    "HISTORICAL ERA (STRICT): 18th-19th century Eastern European Jews. ABSOLUTELY NO KNITTED OR COLORFUL "
    "KIPPOT anywhere - every man and boy wears a plain BLACK cloth skullcap, a round black hat, a peaked "
    "worker's cap or a fur hat; long dark coats or simple period workwear, full beards, peyot. Women wear a "
    "simple kerchief tied at the back of the head over their hair, face, chin and neck fully visible - "
    "NEVER a hood, NEVER a hijab wrapped around the face, NEVER a face veil, long period "
    "dresses with long sleeves."
)
from scenes import SCENES, HISTORIC_SCENES, ANCIENT_SCENES, ANCIENT


def load_key():
    if os.environ.get("GOOGLE_API_KEY"):
        return os.environ["GOOGLE_API_KEY"]
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.is_file() else []
    for line in lines:
        if line.startswith("GOOGLE_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GOOGLE_API_KEY missing: set the env var or add it to " + str(ENV_PATH))


def http_post(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            print("  HTTP", e.code, e.read().decode("utf-8", "ignore")[:300], flush=True)
            if e.code in (429, 500, 503) and attempt < RETRIES - 1:
                time.sleep(12 * (attempt + 1))
                continue
            raise


def extract_png(resp):
    for c in resp.get("candidates", []):
        for p in c.get("content", {}).get("parts", []):
            d = p.get("inlineData") or p.get("inline_data")
            if d and d.get("data"):
                return base64.b64decode(d["data"])
    return None


def normalize(raw, out):
    tmp = out.with_suffix(".raw")
    tmp.write_bytes(raw)
    subprocess.run(["ffmpeg", "-y", "-i", str(tmp), "-vf",
                    "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1", str(out)],
                   check=True, capture_output=True)
    tmp.unlink()


WORKERS = 4


def era_block(name):
    if name in ANCIENT_SCENES:
        return ANCIENT
    return HISTORIC if name in HISTORIC_SCENES else MODERN


def one(key, name, subj):
    out = OUT_DIR / f"{name}.png"
    if out.exists() and out.stat().st_size > MIN_BYTES:
        return f"skip {name}"
    resp = http_post(f"{BASE}/models/{MODEL}:generateContent?key={key}",
                     {"contents": [{"parts": [{"text": subj + ART + era_block(name) + TAIL}]}],
                      "generationConfig": {"imageConfig": {"aspectRatio": "16:9"}}})
    raw = extract_png(resp)
    if not raw:
        return f"NO IMAGE {name} {json.dumps(resp)[:300]}"
    normalize(raw, out)
    return f"SAVED {name} {out.stat().st_size // 1024} KB"


def main(only):
    key = load_key()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jobs = [(n, s) for n, s in SCENES.items() if not only or n in only]
    print("model", MODEL, "jobs", len(jobs), flush=True)
    with ThreadPoolExecutor(WORKERS) as ex:
        for msg in ex.map(lambda j: one(key, *j), jobs):
            print(msg, flush=True)
    print("DONE")


if __name__ == "__main__":
    main(set(sys.argv[1:]))
