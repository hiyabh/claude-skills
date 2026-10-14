"""Zoom into part of the sheet with a labelled grid, or fix the frame.

Usage:
    python zoom.py <work> --world X0,Y0,X1,Y1 [--step M] [-o name.png]   # box in metres
    python zoom.py <work> --px X0,Y0,X1,Y1 [--step S] [-o name.png]      # box in sheet pixels
    python zoom.py <work> --set-origin PX,PY        # pixel of world (0,0), e.g. a footprint corner
    python zoom.py <work> --calibrate PX0,PY0,PX1,PY1,CM   # scale from a dimension string you read

Read coordinates off the grid lines, never by guessing from a bare crop. Zoom
until a 10 cm step is legible when placing walls; 20-50 cm is enough for rooms.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image

import grid
from common import SHEET_FILE, has_world, load_frame, save_frame, to_px, utf8_stdout

Image.MAX_IMAGE_PIXELS = None
CM_PER_M = 100.0


def _floats(text: str, count: int) -> list[float]:
    values = [float(v) for v in text.split(",")]
    if len(values) != count:
        raise SystemExit(f"expected {count} comma-separated numbers, got {text!r}")
    return values


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("work", type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--world")
    group.add_argument("--px")
    group.add_argument("--set-origin")
    group.add_argument("--calibrate")
    parser.add_argument("--step", type=float, default=None)
    parser.add_argument("-o", "--output", default=None)
    return parser.parse_args()


def _next_name(work: Path) -> Path:
    zooms = work / "zooms"
    zooms.mkdir(exist_ok=True)
    n = len(list(zooms.glob("zoom_*.png"))) + 1
    return zooms / f"zoom_{n:02d}.png"


def _box_from_world(frame: dict, text: str) -> tuple[float, ...]:
    if not has_world(frame):
        raise SystemExit("frame has no origin/scale yet - use --px, then --set-origin / --calibrate")
    x0, y0, x1, y1 = _floats(text, 4)
    ax, ay = to_px(frame, (min(x0, x1), max(y0, y1)))
    bx, by = to_px(frame, (max(x0, x1), min(y0, y1)))
    return (ax, ay, bx, by)


def main() -> int:
    utf8_stdout()
    args = _parse()
    frame = load_frame(args.work)
    if args.set_origin:
        frame["origin_px"] = _floats(args.set_origin, 2)
        save_frame(args.work, frame)
        print(f"origin_px set to {frame['origin_px']}")
        return 0
    if args.calibrate:
        x0, y0, x1, y1, cm = _floats(args.calibrate, 5)
        frame["px_per_m"] = math.dist((x0, y0), (x1, y1)) / (cm / CM_PER_M)
        frame["scale_method"] = "calibrated-dimension"
        save_frame(args.work, frame)
        print(f"px_per_m set to {frame['px_per_m']:.3f} from a {cm:g} cm dimension")
        return 0
    box = _box_from_world(frame, args.world) if args.world else tuple(_floats(args.px, 4))
    sheet = Image.open(args.work / SHEET_FILE)
    out = Path(args.output) if args.output else _next_name(args.work)
    if not out.is_absolute() and out.parent == Path("."):
        out = _next_name(args.work).with_name(out.name)
    grid.render(sheet, frame, box, out, args.step)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
