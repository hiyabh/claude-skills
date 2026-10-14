"""Stage 4: build the self-contained 3D viewer page from one or more plan.json files.

Usage:
    python build_viewer.py <plan.json> -o <out.html> [--work <work>] [--title T] [--preview]
    python build_viewer.py "חלופה א=a.json" "חלופה ב=b.json" -o out.html ...   # A/B variants

--work embeds the original drawing (cropped to the plan) so the page can open on the
flat sheet and lift it into 3D, and offer it as a "שרטוט" overlay in work mode.
The published page has no doctype (the Artifact wraps it); --preview also writes
<out>.preview.html with one, for opening locally through `python -m http.server`.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image

import runs
from common import SHEET_FILE, has_world, load_frame, read_json, to_px, utf8_stdout

SKILL = Path(__file__).resolve().parent.parent
VIEWER = SKILL / "assets" / "viewer"
THREE_VERSION = "0.186.1"     # verified on npm 2026-10-08
FFLATE_VERSION = "0.8.3"      # verified on npm 2026-10-08
UNDERLAY_MARGIN_M = 0.6
UNDERLAY_MAX_PX = 2048
PAGE_LIMIT = 16 * 1024 * 1024
EYE_H = 1.6
ELEVATION_BACK_M = 3.2       # open-plan kitchens let the camera step back into the next room
PREVIEW_HEAD = ('<!doctype html>\n<html lang="he" dir="rtl">\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n')


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plans", nargs="+", help="plan.json, or 'name=plan.json' per variant")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--work", type=Path, default=None, help="work folder, to embed the drawing")
    parser.add_argument("--title", default=None)
    parser.add_argument("--preview", action="store_true")
    return parser.parse_args()


def _inside(p, poly) -> bool:
    x, y, hit = p[0], p[1], False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i - 1], poly[i]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def elevation_views(plan: dict, boxes: list[dict]) -> list[dict]:
    """One camera per cabinet run: standing in the room, facing the run, like its elevation sheet."""
    polys = [r["polygon"] for r in plan["rooms"]]
    views = []
    for run in plan.get("runs", []):
        own = [b for b in boxes if b["group"] == run["id"] and b["tier"] in ("base", "tall")]
        if not own:
            continue
        cx = sum(b["center"][0] for b in own) / len(own)
        cy = sum(b["center"][1] for b in own) / len(own)
        r = own[0]["rot"]
        nx, ny = math.cos(r), math.sin(r)
        back = ELEVATION_BACK_M
        while back > 0.8 and not any(_inside((cx + nx * back, cy + ny * back), p) for p in polys):
            back -= 0.1
        views.append({"id": f"run-{run['id']}", "label": run.get("label") or run["id"],
                      "eye": [cx + nx * back, cy + ny * back, EYE_H], "target": [cx, cy, 1.15]})
    for island in plan.get("islands", []):
        x, y = island["center"]
        views.append({"id": f"isl-{island['id']}", "label": island.get("label") or "אי",
                      "eye": [x + 1.8, y - 2.2, 1.9], "target": [x, y, 0.8]})
    return views


def variant(name: str, path: Path) -> dict:
    plan = read_json(path)
    boxes = runs.expand(plan)
    return {"name": name, "plan": plan, "items": boxes, "views": elevation_views(plan, boxes)}


def underlay(work: Path, plan: dict) -> dict | None:
    frame = load_frame(work)
    if not has_world(frame) or not (work / SHEET_FILE).exists():
        return None
    pts = [p for w in plan["walls"] for p in (w["a"], w["b"])]
    x0, y0 = min(p[0] for p in pts) - UNDERLAY_MARGIN_M, min(p[1] for p in pts) - UNDERLAY_MARGIN_M
    x1, y1 = max(p[0] for p in pts) + UNDERLAY_MARGIN_M, max(p[1] for p in pts) + UNDERLAY_MARGIN_M
    ax, ay = to_px(frame, (x0, y1))
    bx, by = to_px(frame, (x1, y0))
    Image.MAX_IMAGE_PIXELS = None
    crop = Image.open(work / SHEET_FILE).convert("RGB").crop((int(ax), int(ay), int(bx), int(by)))
    crop.thumbnail((UNDERLAY_MAX_PX, UNDERLAY_MAX_PX), Image.LANCZOS)
    buf = io.BytesIO()
    crop.save(buf, "JPEG", quality=82, optimize=True)
    src = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    # Bounds follow the pixel crop exactly, so the drawing registers with the walls.
    wx0, wy1 = (int(ax) - frame["origin_px"][0]) / frame["px_per_m"], (frame["origin_px"][1] - int(ay)) / frame["px_per_m"]
    wx1, wy0 = (int(bx) - frame["origin_px"][0]) / frame["px_per_m"], (frame["origin_px"][1] - int(by)) / frame["px_per_m"]
    return {"src": src, "bounds": [wx0, wy0, wx1, wy1]}


def bundle() -> str:
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        raise SystemExit("npx not found - install Node.js 18+ to bundle the viewer")
    cmd = [npx, "--yes", "esbuild@0.28.2", str(VIEWER / "main.js"), "--bundle", "--format=esm",
           "--external:three", "--external:three/addons/*", "--external:fflate", "--legal-comments=none", "--log-level=error"]
    done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=VIEWER)
    if done.returncode != 0:
        raise SystemExit(f"esbuild failed:\n{done.stderr.strip()}")
    return done.stdout


def _json_for_script(data: dict) -> str:
    # "</" would end the <script> element early; "<\/" is the same string to JSON.parse.
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def page(data: dict, code: str, title: str) -> str:
    template = (VIEWER / "template.html").read_text(encoding="utf-8")
    html = (template.replace("@@TITLE", title.replace("<", "&lt;"), 1)
            .replace("@@THREE", THREE_VERSION).replace("@@FFLATE", FFLATE_VERSION))
    head, _, tail = html.partition("@@BUNDLE")
    html = head + code.replace("</script", "<\\/script") + tail
    head, _, tail = html.partition("@@DATA")
    return head + _json_for_script(data) + tail


def main() -> int:
    utf8_stdout()
    args = _parse()
    variants = []
    for spec in args.plans:
        name, sep, path = spec.partition("=")
        variants.append(variant(name if sep else "תוכנית", Path(path if sep else name)))
    meta = dict(variants[0]["plan"].get("meta", {}))
    meta.setdefault("title", args.title or "מודל תלת-מימד")
    if args.title:
        meta["title"] = args.title
    meta["file"] = re.sub(r"\s+", " ", args.output.stem).strip()
    data = {"meta": meta, "variants": variants, "underlay": underlay(args.work, variants[0]["plan"]) if args.work else None}
    html = page(data, bundle(), meta["title"])
    size = len(html.encode("utf-8"))
    if size > PAGE_LIMIT:
        raise SystemExit(f"page is {size / 1e6:.1f} MB, over the 16 MB Artifact limit - drop --work or simplify the plan")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(f"wrote {args.output} ({size / 1024:.0f} KB, {len(variants)} variant(s), "
          f"{sum(len(v['items']) for v in variants)} items, underlay {'yes' if data['underlay'] else 'no'})")
    if args.preview:
        preview = args.output.with_suffix(".preview.html")
        preview.write_text(PREVIEW_HEAD + html, encoding="utf-8")
        print(f"wrote {preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
