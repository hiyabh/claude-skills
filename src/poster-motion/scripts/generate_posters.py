"""Generate a matching poster series from a brief, with Gemini image models.

    python generate_posters.py <project>                  # all posters in the brief
    python generate_posters.py <project> --only p3        # redo one
    python generate_posters.py <project> --model gemini-3.1-flash-image

Reads <project>/poster_brief.json (Claude writes it in step 1):

    {"aspect": "4:5",
     "style": "minimalist editorial poster, off-white textured paper ...",
     "posters": [{"id": "p1", "text": "חתול בשק",
                  "scene": "a crumpled brown paper bag, a black cat peeking out"}]}

The first poster is generated from text alone; every later one gets it as a
style reference, so the series shares paper, ink and light. Writes
posters/<id>.png. Image models misspell Hebrew often - LOOK at every poster
and redo (`--only`) any whose lettering is wrong before moving on.

Key: GOOGLE_API_KEY in the environment, or `--key-file path/.env`.
Model ids verified against GET /v1beta/models on 2026-09-28.
"""

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

from pm_common import flag, project_arg, read_json

DEFAULT_MODEL = "gemini-3-pro-image"
API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
TRIES = 4
RETRY_CODES = (429, 500, 503)
BACKOFF_S = 8
TIMEOUT_S = 180
RULES = ("The Hebrew text must be spelled EXACTLY as given, letter for letter, "
         "right-to-left, no niqqud unless given, no other text, no watermark, no border, "
         "no frame, no signature. Plain paper background edge to edge. Leave clear "
         "paper around the lettering and around the object - they are separated later.")
REF_NOTE = ("Match the reference image's paper, lighting, lettering style and overall "
            "art direction exactly - this poster belongs to the same series.")


def load_key():
    if os.environ.get("GOOGLE_API_KEY"):
        return os.environ["GOOGLE_API_KEY"]
    path = flag("key-file")
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("GOOGLE_API_KEY="):
                    return line.split("=", 1)[1].strip()
    sys.exit("no GOOGLE_API_KEY: set it in the environment or pass --key-file <.env>. "
             "Without a key, bring finished poster images into <project>/posters/ instead.")


def post(url, payload):
    data = json.dumps(payload).encode("utf-8")
    for attempt in range(1, TRIES + 1):
        try:
            req = urllib.request.Request(url, data=data,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")[:300]
            print(f"  HTTP {e.code} (try {attempt}/{TRIES}): {body}")
            if e.code not in RETRY_CODES or attempt == TRIES:
                raise
        except OSError as e:
            print(f"  network error (try {attempt}/{TRIES}): {e}")
            if attempt == TRIES:
                raise
        time.sleep(BACKOFF_S * attempt)


def image_of(resp):
    for cand in resp.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])
    return None


def prompt_for(brief, poster):
    return (f"{brief['style']}\n\nScene: {poster['scene']}\n"
            f"Hebrew lettering on the poster: \"{poster['text']}\"\n\n{RULES}")


def generate(url, brief, poster, ref_png):
    parts = [{"text": prompt_for(brief, poster)}]
    if ref_png:
        parts += [{"inlineData": {"mimeType": "image/png",
                                  "data": base64.b64encode(ref_png).decode("ascii")}},
                  {"text": REF_NOTE}]
    payload = {"contents": [{"parts": parts}],
               "generationConfig": {"responseModalities": ["IMAGE"],
                                    "imageConfig": {"aspectRatio": brief.get("aspect", "4:5")}}}
    return image_of(post(url, payload))


def main():
    project = project_arg()
    brief = read_json(os.path.join(project, "poster_brief.json"))
    url = API.format(model=flag("model", DEFAULT_MODEL), key=load_key())
    out_dir = os.path.join(project, "posters")
    os.makedirs(out_dir, exist_ok=True)
    only = flag("only")
    ref = None
    first = os.path.join(out_dir, f"{brief['posters'][0]['id']}.png")
    if os.path.exists(first) and only:
        with open(first, "rb") as fh:
            ref = fh.read()
    for poster in brief["posters"]:
        if only and poster["id"] != only:
            continue
        png = generate(url, brief, poster, ref)
        if not png:
            print(f"  {poster['id']}: no image returned - rephrase the scene and retry")
            continue
        with open(os.path.join(out_dir, f"{poster['id']}.png"), "wb") as fh:
            fh.write(png)
        ref = ref or png
        print(f"  {poster['id']}: {poster['text']} ({len(png) // 1024} KB)")


if __name__ == "__main__":
    main()
