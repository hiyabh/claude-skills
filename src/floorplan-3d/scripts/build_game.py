"""Game mode: build a photoreal, walkable apartment as a multi-file Artifact folder.

Usage:
    python build_game.py <plan.json> -o <out-folder> [--tier high|lite] [--title T] [--views <views-folder>]

Writes <out>/index.html (publish this), <out>/preview.html (local only, has a doctype) and
<out>/assets/... (textures, HDRIs, models). Prints the exact `files` list to publish with.
Budget: an Artifact serves at most 16 MB per file and 64 MB per publish.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

import assets
from build_viewer import _json_for_script, variant
from common import utf8_stdout

SKILL = Path(__file__).resolve().parent.parent
GAME = SKILL / "assets" / "game"
VERSIONS = {"THREE": "0.186.1", "POSTPROCESSING": "6.39.5", "N8AO": "2.0.1", "PATHTRACER": "0.0.27", "BVH": "0.9.16",
            "FFLATE": "0.8.3"}  # npm, 2026-10-09
EXTERNALS = ["three", "three/webgpu", "three/addons/*", "three/examples/jsm/*", "postprocessing", "n8ao", "three-gpu-pathtracer",
             "three-mesh-bvh", "fflate"]
FILE_LIMIT = 16 * 1024 * 1024
PUBLISH_LIMIT = 64 * 1024 * 1024
PREVIEW_HEAD = ('<!doctype html>\n<html lang="he" dir="rtl">\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n')
# What the engine needs: every finish option (they swap live) and the models furniture maps onto.
TEXTURES = ["floor_porcelain", "floor_oak", "floor_light_oak", "floor_herringbone", "floor_concrete", "wall_plaster",
            "veneer_oak", "veneer_white_oak", "veneer_walnut", "fabric_cotton", "fabric_linen", "fabric_velvet"]
HDRIS = ["morning", "afternoon", "sunset", "night"]
MODELS = {"high": ["ceiling_lamp", "coffee_table", "plant", "tv_console", "outdoor_set"],
          "lite": ["ceiling_lamp", "coffee_table", "plant_small", "tv_console", "outdoor_set"]}


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plan", type=Path)
    parser.add_argument("-o", "--out", type=Path, required=True)
    parser.add_argument("--tier", choices=("high", "lite"), default="high")
    parser.add_argument("--title", default=None)
    parser.add_argument("--views", type=Path, default=None, help="folder from views.py (window views)")
    return parser.parse_args()


def bundle() -> str:
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        raise SystemExit("npx not found - install Node.js 18+ to bundle the game")
    cmd = [npx, "--yes", "esbuild@0.28.2", str(GAME / "main.js"), "--bundle", "--format=esm",
           *[f"--external:{e}" for e in EXTERNALS], "--legal-comments=none", "--log-level=error"]
    done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=GAME)
    if done.returncode != 0:
        raise SystemExit(f"esbuild failed:\n{done.stderr.strip()}")
    return done.stdout


def export_assets(out: Path, tier: str) -> dict:
    index = assets.export(out / "assets", tier, {"textures": TEXTURES, "hdris": HDRIS, "models": MODELS[tier]})
    if "plant_small" in index["models"]:
        index["models"]["plant"] = index["models"].pop("plant_small")   # the engine asks for "plant"
    return index


def copy_views(src: Path | None, out: Path) -> dict | None:
    """Window views from views.py -> assets/v/, as page-relative paths per compass side."""
    if not src:
        return None
    index = json.loads((src / "views.json").read_text(encoding="utf-8"))["views"]
    dest = out / "assets" / "v"
    dest.mkdir(parents=True, exist_ok=True)
    result = {}
    for side, files in index.items():
        for when in ("day", "night"):
            shutil.copy(src / files[when], dest / files[when])
        result[side] = {"day": f"assets/v/{files['day']}", "night": f"assets/v/{files['night']}"}
    return result


def page(data: dict, code: str, title: str) -> str:
    html = (GAME / "template.html").read_text(encoding="utf-8").replace("@@TITLE", title.replace("<", "&lt;"))
    for key, version in VERSIONS.items():
        html = html.replace(f"@@{key}", version)
    head, _, tail = html.partition("@@BUNDLE")
    html = head + code.replace("</script", "<\\/script") + tail
    head, _, tail = html.partition("@@DATA")
    return head + _json_for_script(data) + tail


def report(out: Path) -> list[str]:
    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "preview.html")
    total = sum(p.stat().st_size for p in files)
    too_big = [p for p in files if p.stat().st_size > FILE_LIMIT]
    if too_big or total > PUBLISH_LIMIT:
        raise SystemExit(f"over the Artifact budget: {total / 1e6:.1f} MB total, oversized: {[p.name for p in too_big]}")
    rel = [p.relative_to(out).as_posix() for p in files if p.name not in ("index.html", "publish-files.json", "assets.json")]
    print(f"wrote {out} - {len(files)} files, {total / 1e6:.1f} MB (limit 64 MB per publish)")
    return rel


def main() -> int:
    utf8_stdout()
    args = _parse()
    shutil.rmtree(args.out / "assets", ignore_errors=True)
    args.out.mkdir(parents=True, exist_ok=True)
    v = variant("תוכנית", args.plan)
    meta = dict(v["plan"].get("meta", {}))
    title = args.title or meta.get("title") or "סיור בדירה"
    data = {"meta": meta, "variants": [{"plan": v["plan"], "items": v["items"]}], "assets": export_assets(args.out, args.tier),
            "views": copy_views(args.views, args.out)}
    html = page(data, bundle(), title)
    (args.out / "index.html").write_text(html, encoding="utf-8")
    (args.out / "preview.html").write_text(PREVIEW_HEAD + html, encoding="utf-8")
    files = report(args.out)
    (args.out / "publish-files.json").write_text(json.dumps(files, indent=1), encoding="utf-8")
    print(f"publish: file_path=index.html, root={args.out}, files=publish-files.json ({len(files)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
