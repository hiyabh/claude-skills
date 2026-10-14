"""Run PlanWalk's OpenCV extraction and keep the frame it worked in.

Runs under PlanWalk's own interpreter (prepare.py launches it), because it needs
OpenCV, PyMuPDF and Tesseract from that venv. PlanWalk itself is not modified:
this only calls its public extract() and saves three things into the work folder:

    sheet.png      the upright sheet PlanWalk analysed (the shared pixel space)
    cv.plan.json   PlanWalk's plan, unchanged
    frame.json     px_per_m + origin_px, so other scripts can map metres <-> pixels

Usage (normally via prepare.py):
    <planwalk-python> cv_extract.py <plan.pdf|png> <work> [--page N] [--dpi D] [--scale-ratio R]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

from common import SHEET_FILE, save_frame, utf8_stdout


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path)
    parser.add_argument("work", type=Path)
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--dpi", type=float, default=200.0)
    parser.add_argument("--scale-ratio", type=int, default=None)
    parser.add_argument("--wall-height", type=float, default=2.70)
    parser.add_argument("--planwalk", type=Path, required=True, help="PlanWalk checkout root")
    return parser.parse_args()


def _write_frame(args: argparse.Namespace, result) -> None:
    height, width = result.sheet.image.shape[:2]
    save_frame(args.work, {
        "sheet": SHEET_FILE, "width": width, "height": height, "dpi": args.dpi,
        "px_per_m": result.graph.px_per_m, "origin_px": list(result.graph.origin_px),
        "rotation": result.sheet.rotation_applied, "scale_method": result.plan.scale.method,
        "engine": "planwalk", "source": {"file": args.input.name, "page": args.page},
    })


def main() -> int:
    utf8_stdout()
    args = _parse()
    sys.path.insert(0, str(args.planwalk / "src"))
    from planwalk.extract.pipeline import ExtractOptions, extract

    options = ExtractOptions(
        page=args.page, dpi=args.dpi, scale_ratio=args.scale_ratio, wall_height=args.wall_height
    )
    result = extract(args.input, options)
    args.work.mkdir(parents=True, exist_ok=True)

    ok, buffer = cv2.imencode(".png", result.sheet.image)
    if not ok:
        raise SystemExit("could not encode the sheet image as PNG")
    buffer.tofile(str(args.work / SHEET_FILE))  # tofile copes with Hebrew paths
    result.plan.save(args.work / "cv.plan.json")

    _write_frame(args, result)
    plan = result.plan
    print(f"cv        {len(plan.walls)} walls, {len(plan.openings)} openings, {len(plan.rooms)} rooms")
    print(f"scale     {plan.scale.px_per_m:.2f} px/m via {plan.scale.method} ({result.scale_detail})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
