"""Draw a plan.json over the sheet so Claude can check it against the drawing.

Usage:
    python overlay.py <work> [--plan vision.plan.json] [--world X0,Y0,X1,Y1] [-o name.png]

Colours: walls red (exterior dark red) with ids, doors green, windows orange,
plain openings magenta, rooms translucent with id/type/area, cabinet and
fixture boxes blue (solid outline = from the drawing, dashed = estimated).
Look for: wall lines off the hatched/filled wall ink, room fills spilling
across walls or leaving bare floor, openings not sitting on their gap.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw

import grid
import runs
from common import SHEET_FILE, has_world, load_frame, read_json, to_px, utf8_stdout

Image.MAX_IMAGE_PIXELS = None
MARGIN_M = 0.8
ROOM_FILLS = [(80, 180, 90, 70), (70, 140, 220, 70), (230, 170, 40, 70), (190, 90, 200, 70), (40, 190, 190, 70)]
WALL = (220, 30, 40, 230)
WALL_EXT = (130, 0, 20, 240)
OPENING = {"door": (20, 170, 40, 255), "window": (240, 140, 0, 255), "opening": (210, 30, 210, 255)}
BOX = (20, 90, 230, 255)


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("work", type=Path)
    parser.add_argument("--plan", default="plan.json", help="plan file inside the work folder")
    parser.add_argument("--world", default=None, help="crop box in metres; default = plan bounds")
    parser.add_argument("-o", "--output", default=None)
    return parser.parse_args()


def shoelace(poly) -> float:
    return abs(sum(poly[i][0] * poly[i - 1][1] - poly[i - 1][0] * poly[i][1] for i in range(len(poly)))) / 2


def plan_bounds(plan: dict) -> tuple[float, float, float, float]:
    pts = [p for w in plan["walls"] for p in (w["a"], w["b"])] + [p for r in plan["rooms"] for p in r["polygon"]]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs) - MARGIN_M, min(ys) - MARGIN_M, max(xs) + MARGIN_M, max(ys) + MARGIN_M)


class Painter:
    """Maps world metres into the zoomed crop and draws on an RGBA layer."""

    def __init__(self, frame, box_px, zoom, size):
        self.frame, self.x0, self.y0, self.zoom = frame, box_px[0], box_px[1], zoom
        self.layer = Image.new("RGBA", size, (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.layer)
        self.px_per_m = frame["px_per_m"] * zoom

    def p(self, pt) -> tuple[float, float]:
        x, y = to_px(self.frame, pt)
        return ((x - self.x0) * self.zoom, (y - self.y0) * self.zoom)

    def text(self, pt, label: str, colour, size: int = 16) -> None:
        x, y = self.p(pt)
        f = grid.font(size)
        bbox = self.draw.textbbox((x, y), label, font=f, anchor="mm")
        self.draw.rectangle((bbox[0] - 3, bbox[1] - 2, bbox[2] + 3, bbox[3] + 2), fill=(255, 255, 255, 220))
        self.draw.text((x, y), label, font=f, fill=colour, anchor="mm")

    def dashed(self, pts, colour, width=2, dash=8) -> None:
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            length = math.hypot(bx - ax, by - ay)
            for s in range(0, int(length), dash * 2):
                t0, t1 = s / length, min(1.0, (s + dash) / length)
                self.draw.line((ax + (bx - ax) * t0, ay + (by - ay) * t0, ax + (bx - ax) * t1, ay + (by - ay) * t1),
                               fill=colour, width=width)


def draw_rooms(pt: Painter, plan: dict) -> None:
    for i, room in enumerate(plan["rooms"]):
        pt.draw.polygon([pt.p(q) for q in room["polygon"]], fill=ROOM_FILLS[i % len(ROOM_FILLS)])
    for room in plan["rooms"]:
        cx = sum(q[0] for q in room["polygon"]) / len(room["polygon"])
        cy = sum(q[1] for q in room["polygon"]) / len(room["polygon"])
        pt.text((cx, cy), f"{room['id']} {room.get('type', '')} {shoelace(room['polygon']):.1f}m2", (10, 60, 20, 255))


def draw_walls(pt: Painter, plan: dict) -> None:
    for wall in plan["walls"]:
        colour = WALL_EXT if wall.get("exterior") else WALL
        width = max(2, int(wall.get("thickness", 0.15) * pt.px_per_m * 0.35))
        pt.draw.line((*pt.p(wall["a"]), *pt.p(wall["b"])), fill=colour, width=width)
        mid = ((wall["a"][0] + wall["b"][0]) / 2, (wall["a"][1] + wall["b"][1]) / 2)
        pt.text(mid, wall["id"], colour, 13)


def draw_openings(pt: Painter, plan: dict) -> None:
    walls = {w["id"]: w for w in plan["walls"]}
    for op in plan.get("openings", []):
        wall = walls.get(op["wall"])
        if wall is None:
            continue
        (ax, ay), (bx, by) = wall["a"], wall["b"]
        length = math.hypot(bx - ax, by - ay) or 1.0
        ux, uy = (bx - ax) / length, (by - ay) / length
        cx, cy = op["center"]
        half = op["width"] / 2
        colour = OPENING.get(op["kind"], OPENING["opening"])
        pt.draw.line((*pt.p((cx - ux * half, cy - uy * half)), *pt.p((cx + ux * half, cy + uy * half))),
                     fill=colour, width=7)
        pt.text((cx, cy), op["id"], colour, 12)


def draw_boxes(pt: Painter, plan: dict) -> None:
    for box in runs.expand(plan):
        if box["tier"] == "upper":
            continue  # uppers sit over the bases; drawing both hides the plan
        (cx, cy), (w, d, _), r = box["center"], box["size"], box["rot"]
        fx, fy = math.cos(r), math.sin(r)            # facing direction
        ax, ay = -fy, fx                              # along the run
        corners = [(cx + ax * sw * w / 2 + fx * sd * d / 2, cy + ay * sw * w / 2 + fy * sd * d / 2)
                   for sw, sd in ((-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1))]
        pts = [pt.p(c) for c in corners]
        if box["src"] == "drawing":
            pt.draw.line(pts, fill=BOX, width=2)
        else:
            pt.dashed(pts, BOX)


def main() -> int:
    utf8_stdout()
    args = _parse()
    frame = load_frame(args.work)
    if not has_world(frame):
        raise SystemExit("frame has no scale/origin yet - see zoom.py --set-origin / --calibrate")
    plan = read_json(args.work / args.plan)
    box_m = [float(v) for v in args.world.split(",")] if args.world else plan_bounds(plan)
    ax, ay = to_px(frame, (box_m[0], box_m[3]))
    bx, by = to_px(frame, (box_m[2], box_m[1]))
    sheet = Image.open(args.work / SHEET_FILE).crop((int(ax), int(ay), int(bx), int(by))).convert("RGBA")
    zoom = min(grid.MAX_SIDE / sheet.width, grid.MAX_SIDE / sheet.height, 4.0)
    sheet = sheet.resize((int(sheet.width * zoom), int(sheet.height * zoom)), Image.LANCZOS)
    pt = Painter(frame, (int(ax), int(ay)), zoom, sheet.size)
    draw_rooms(pt, plan)
    draw_walls(pt, plan)
    draw_openings(pt, plan)
    draw_boxes(pt, plan)
    out = Path(args.output) if args.output else args.work / f"overlay_{Path(args.plan).stem.split('.')[0]}.png"
    Image.alpha_composite(sheet, pt.layer).convert("RGB").save(out)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
