"""Generate what each window looks out on (Gemini image model), day and night, for game mode.

Usage:
    python views.py <plan.json> -o <views-folder> [--city "Jerusalem"] [--floor 2] [--dry-run]

One wide (21:9) eye-level view per compass direction that has glazing, horizon at mid-height;
the night version is an edit of the day image so the scene stays the same. Prints the cost first.
Key: GOOGLE_API_KEY, or a .env file (GOOGLE_ENV_FILE, default ./.env).
AI-image rule: no people, no text/logos; open and inspect every image before using it.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import math
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

from common import read_json, utf8_stdout, write_json

MODEL = "gemini-3.1-flash-image"            # verified available on the key, 2026-10-09
COST_PER_IMAGE_USD = 0.101                  # 2K output, Google list price per tokencost.app, 2026-10-09
IMAGE_SIZE = "2K"
OUT_WIDTH = 2560
ENV_FILE = Path(os.environ.get("GOOGLE_ENV_FILE", ".env"))  # optional .env fallback for the key
STOREY_M = 3.0
DIRECTIONS = ["north", "east", "south", "west"]
NO_PEOPLE = "Absolutely no people, no animals, no text, no signs, no logos, no watermarks."
DAY_PROMPT = (
    "A photorealistic eye-level photograph from inside an apartment on floor {floor} (about {height:.0f} m above the "
    "street), looking straight out of a window toward the {direction}. Show ONLY the outside: no window frame, no "
    "curtains, no interior, no glass reflections. A pleasant residential neighbourhood in {city}, Israel: 4-8 storey "
    "apartment buildings clad in pale cream limestone with balconies and planters, some cypress, olive and pine trees, "
    "the street partly visible below, soft hills on the horizon, clear blue sky with a few light clouds, warm "
    "afternoon sun. The horizon sits exactly at the vertical middle of the frame. Wide 21:9 panorama, natural "
    "colours, sharp and realistic. " + NO_PEOPLE
)
NIGHT_PROMPT = (
    "Edit this photo: the exact same view and composition at night. Deep blue night sky, warm lights on in many "
    "windows of the buildings, warm street lamps glowing, the limestone softly lit. Keep every building, tree and "
    "hill exactly where it is. " + NO_PEOPLE
)


def load_key() -> str:
    if os.environ.get("GOOGLE_API_KEY"):
        return os.environ["GOOGLE_API_KEY"]
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.is_file() else []
    for line in lines:
        if line.startswith("GOOGLE_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GOOGLE_API_KEY not found - set it, or use --dry-run to see the prompts")


def facing_directions(plan: dict) -> list[str]:
    """Compass directions (after the plan's north rotation) that have windows or glass doors."""
    walls = {w["id"]: w for w in plan["walls"]}
    rooms = {r["id"]: r for r in plan["rooms"]}
    north = math.radians(plan.get("meta", {}).get("north_deg", 0))
    found = set()
    for o in plan["openings"]:
        if not (o["kind"] == "window" or o.get("style") == "sliding") or o["wall"] not in walls:
            continue
        w = walls[o["wall"]]
        ux, uy = w["b"][0] - w["a"][0], w["b"][1] - w["a"][1]
        n = (-uy, ux)
        room = rooms.get((o.get("rooms") or [None])[0])
        if room:
            cx = sum(p[0] for p in room["polygon"]) / len(room["polygon"])
            cy = sum(p[1] for p in room["polygon"]) / len(room["polygon"])
            if n[0] * (o["center"][0] - cx) + n[1] * (o["center"][1] - cy) < 0:
                n = (uy, -ux)
        bearing = (math.degrees(math.atan2(n[0], n[1])) + math.degrees(north)) % 360   # 0 = north, clockwise
        found.add(DIRECTIONS[int(((bearing + 45) % 360) // 90)])
    return [d for d in DIRECTIONS if d in found]


def call(key: str, parts: list[dict], tries: int = 4) -> bytes:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={key}"
    payload = {"contents": [{"parts": parts}],
               "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "21:9", "imageSize": IMAGE_SIZE}}}
    data = json.dumps(payload).encode("utf-8")
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=240) as r:
                resp = json.loads(r.read().decode("utf-8"))
            for cand in resp.get("candidates", []):
                for part in cand.get("content", {}).get("parts", []):
                    inline = part.get("inlineData") or part.get("inline_data")
                    if inline and inline.get("data"):
                        return base64.b64decode(inline["data"])
            raise RuntimeError(f"no image in response: {str(resp)[:300]}")
        except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError, TimeoutError) as error:
            code = getattr(error, "code", None)
            if attempt == tries - 1 or code in (400, 401, 403):
                body = error.read().decode("utf-8", "ignore")[:300] if hasattr(error, "read") else str(error)
                raise SystemExit(f"Gemini image call failed ({code}): {body}")
            time.sleep(8 * (attempt + 1))
    raise SystemExit("unreachable")


def save_jpg(raw: bytes, dest: Path) -> None:
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    if im.width > OUT_WIDTH:
        im = im.resize((OUT_WIDTH, round(im.height * OUT_WIDTH / im.width)), Image.LANCZOS)
    im.save(dest, "JPEG", quality=88, optimize=True)


def main() -> int:
    utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plan", type=Path)
    parser.add_argument("-o", "--out", type=Path, required=True)
    parser.add_argument("--city", default="Jerusalem")
    parser.add_argument("--floor", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    plan = read_json(args.plan)
    meta = plan.get("meta", {})
    if args.floor is None and "floor" not in meta:
        print("warning: no --floor and no meta.floor - assuming floor 2; the view height will be wrong if the sheet says otherwise")
    if "north_deg" not in meta:
        print("warning: no meta.north_deg - assuming the sheet's up is north; read the north arrow (references/reading-plans.md)")
    floor = args.floor if args.floor is not None else int(meta.get("floor", 2))
    dirs = facing_directions(plan)
    print(f"directions with glazing: {', '.join(dirs) or 'none'} -> {len(dirs) * 2} images, about ${len(dirs) * 2 * COST_PER_IMAGE_USD:.2f}")
    prompts = {d: DAY_PROMPT.format(floor=floor, height=floor * STOREY_M + 1.6, direction=d, city=args.city) for d in dirs}
    if args.dry_run:
        for d, p in prompts.items():
            print(f"\n[{d}] {p}")
        return 0
    key = load_key()
    args.out.mkdir(parents=True, exist_ok=True)
    index = {}
    for d in dirs:
        day = call(key, [{"text": prompts[d]}])
        save_jpg(day, args.out / f"{d}_day.jpg")
        night = call(key, [{"inlineData": {"mimeType": "image/png", "data": base64.b64encode(day).decode()}}, {"text": NIGHT_PROMPT}])
        save_jpg(night, args.out / f"{d}_night.jpg")
        index[d] = {"day": f"{d}_day.jpg", "night": f"{d}_night.jpg"}
        print(f"view     {d}: day + night saved")
    write_json(args.out / "views.json", {"city": args.city, "floor": floor, "model": MODEL, "views": index})
    print(f"done - open every image in {args.out} and check it before building")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
