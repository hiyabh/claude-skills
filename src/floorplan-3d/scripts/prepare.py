"""Stage 1: render a plan sheet into a work folder and give Claude a way to read it.

Usage:
    python prepare.py <plan.pdf|png|jpg> <work> [--page N] [--dpi D] [--scale-ratio R] [--rotate DEG]

What lands in <work>:
    sheet.png        upright sheet, the shared pixel space for everything else
    frame.json       px_per_m + origin_px (metres <-> pixels); origin is null until known
    cv.plan.json     PlanWalk's OpenCV result, when PlanWalk is installed
    overview.png     the whole sheet, small, with a grid - start here
    tiles/tile_RC.png  3x3 overlapping zooms with grids, for reading dimension strings

With PlanWalk the frame comes from its wall graph (origin = bottom-left of the
footprint). Without it, the scale comes from --scale-ratio and the origin is set
later by `zoom.py <work> --set-origin X,Y` once Claude has picked a corner.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

import grid
from common import (
    SHEET_FILE, load_frame, planwalk_dir, planwalk_python, px_per_m_from_ratio,
    save_frame, utf8_stdout,
)

SCRIPTS = Path(__file__).resolve().parent
TILE_GRID = 3
TILE_OVERLAP = 0.15
Image.MAX_IMAGE_PIXELS = None  # A1 sheets at 200 dpi are legitimately huge


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path)
    parser.add_argument("work", type=Path)
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--dpi", type=float, default=200.0)
    parser.add_argument("--scale-ratio", type=int, default=None, help="50 for a 1:50 sheet")
    parser.add_argument("--rotate", type=int, default=0, choices=(0, 90, 180, 270),
                        help="counter-clockwise turn for the vision-only path - the same convention as "
                             "PlanWalk's frame.rotation, so both engines land in one pixel space")
    parser.add_argument("--no-cv", action="store_true", help="skip PlanWalk even if installed")
    return parser.parse_args()


def run_planwalk(args: argparse.Namespace) -> bool:
    root = planwalk_dir()
    python = planwalk_python(root) if root else None
    if args.no_cv or python is None:
        return False
    cmd = [str(python), str(SCRIPTS / "cv_extract.py"), str(args.input), str(args.work),
           "--page", str(args.page), "--dpi", str(args.dpi), "--planwalk", str(root)]
    if args.scale_ratio:
        cmd += ["--scale-ratio", str(args.scale_ratio)]
    done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=SCRIPTS)
    print(done.stdout.strip())
    if done.returncode != 0:
        print(f"PlanWalk failed, continuing vision-only:\n{done.stderr.strip()[-800:]}")
        return False
    return True


def render_vision_only(args: argparse.Namespace) -> None:
    if args.input.suffix.lower() == ".pdf":
        with fitz.open(args.input) as doc:
            pix = doc[args.page - 1].get_pixmap(dpi=int(args.dpi))
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    else:
        image = Image.open(args.input).convert("RGB")
    if args.rotate:
        image = image.rotate(args.rotate, expand=True)   # PIL: positive = counter-clockwise
    image.save(args.work / SHEET_FILE)
    ratio_known = args.scale_ratio and args.input.suffix.lower() == ".pdf"
    save_frame(args.work, {
        "sheet": SHEET_FILE, "width": image.width, "height": image.height, "dpi": args.dpi,
        "px_per_m": px_per_m_from_ratio(args.dpi, args.scale_ratio) if ratio_known else None,
        "origin_px": None, "rotation": args.rotate, "scale_method": "stated-ratio" if ratio_known else None,
        "engine": "vision", "source": {"file": args.input.name, "page": args.page},
    })


def write_views(work: Path) -> None:
    frame = load_frame(work)
    sheet = Image.open(work / SHEET_FILE)
    w, h = sheet.width, sheet.height
    grid.render(sheet, frame, (0, 0, w, h), work / "overview.png")
    tiles = work / "tiles"
    tiles.mkdir(exist_ok=True)
    tw, th = w / TILE_GRID, h / TILE_GRID
    for r in range(TILE_GRID):
        for c in range(TILE_GRID):
            box = (max(0, (c - TILE_OVERLAP) * tw), max(0, (r - TILE_OVERLAP) * th),
                   min(w, (c + 1 + TILE_OVERLAP) * tw), min(h, (r + 1 + TILE_OVERLAP) * th))
            grid.render(sheet, frame, box, tiles / f"tile_{r}{c}.png")


def main() -> int:
    utf8_stdout()
    args = _parse()
    if not args.input.exists():
        raise SystemExit(f"{args.input} not found")
    args.work.mkdir(parents=True, exist_ok=True)
    used_cv = run_planwalk(args)
    if not used_cv:
        render_vision_only(args)
    write_views(args.work)
    frame = load_frame(args.work)
    print(f"engine    {frame['engine']}  sheet {frame['width']}x{frame['height']}px")
    print(f"scale     {frame['px_per_m'] or 'unknown - pass --scale-ratio or set it with zoom.py'} px/m")
    print(f"origin    {frame['origin_px'] or 'not set - pick a corner, then zoom.py --set-origin'}")
    print(f"next      look at {args.work / 'overview.png'}, then the tiles/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
