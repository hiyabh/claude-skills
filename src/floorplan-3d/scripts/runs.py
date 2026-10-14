"""Expand cabinet runs and islands into positioned boxes.

Claude describes a kitchen the way an elevation sheet does: "along wall w12,
from 12 cm, a 60 drawer unit, a 90 cooktop, a 60 dishwasher...". This module
turns that into boxes with world positions, once, in Python - the overlay and
the 3D viewer both consume the result, so there is a single implementation.

A box: {id, group, kind, label, center:[x,y], size:[w,d,h], z, rot, src, tier}
  rot  = direction the front faces, radians in the plan frame (x east, y north)
  tier = "base" | "tall" | "upper" | "counter" | "island" | "stool"
"""

from __future__ import annotations

import math

TALL_KINDS = frozenset({"tall", "fridge", "oven_tower", "pantry"})
NO_COUNTER_KINDS = TALL_KINDS | {"gap"}
DEFAULTS = {
    "depth": 0.60, "base_h": 0.87, "counter_t": 0.03, "counter_over": 0.02,
    "tall_h": 2.30, "upper_z": 1.45, "upper_h": 0.75, "upper_depth": 0.35,
    "stool_pitch": 0.55, "island_h": 0.90, "overhang": 0.30,
}


def _axis(wall: dict, side: str) -> tuple[tuple, tuple, tuple]:
    (ax, ay), (bx, by) = wall["a"], wall["b"]
    length = math.hypot(bx - ax, by - ay) or 1.0
    u = ((bx - ax) / length, (by - ay) / length)
    n = (-u[1], u[0]) if side == "left" else (u[1], -u[0])
    return (ax, ay), u, n


def _place(origin, u, n, along: float, out: float) -> list[float]:
    return [origin[0] + u[0] * along + n[0] * out, origin[1] + u[1] * along + n[1] * out]


def _item_box(run, item, idx, frame, cursor, tier) -> dict:
    origin, u, n, face = frame
    w = float(item["w"])
    if tier == "upper":
        d, h, z = run.get("upper_depth", DEFAULTS["upper_depth"]), item.get("h", run.get("upper_h", DEFAULTS["upper_h"])), run.get("upper_z", DEFAULTS["upper_z"])
    elif item.get("kind") in TALL_KINDS:
        tier, d, h, z = "tall", run.get("depth", DEFAULTS["depth"]), item.get("h", DEFAULTS["tall_h"]), 0.0
    else:
        d, h, z = run.get("depth", DEFAULTS["depth"]), item.get("h", run.get("base_h", DEFAULTS["base_h"])), 0.0
    return {
        "id": f"{run['id']}.{tier[0]}{idx + 1}", "group": run["id"], "kind": item.get("kind", "cabinet"),
        "label": item.get("label", ""), "center": _place(origin, u, n, cursor + w / 2, face + d / 2),
        "size": [w, d, h], "z": z, "rot": math.atan2(n[1], n[0]), "src": item.get("src", run.get("src", "estimated")),
        "tier": tier, "room": run.get("room"),
    }


def _counters(run, bases, frame) -> list[dict]:
    """One slab per stretch of consecutive counter-height units."""
    origin, u, n, face = frame
    depth = run.get("depth", DEFAULTS["depth"]) + DEFAULTS["counter_over"]
    slabs, stretch = [], []
    for box in bases + [None]:
        if box is not None and box["kind"] not in NO_COUNTER_KINDS:
            stretch.append(box)
            continue
        if stretch:
            start = stretch[0]["_from"]
            end = stretch[-1]["_from"] + stretch[-1]["size"][0]
            top = max(b["size"][2] for b in stretch)
            slabs.append({
                "id": f"{run['id']}.c{len(slabs) + 1}", "group": run["id"], "kind": "counter", "label": "",
                "center": _place(origin, u, n, (start + end) / 2, face + depth / 2),
                "size": [end - start, depth, run.get("counter_t", DEFAULTS["counter_t"])], "z": top,
                "rot": math.atan2(n[1], n[0]), "src": run.get("src", "estimated"), "tier": "counter",
                "room": run.get("room"),
            })
        stretch = []
    return slabs


def _row(run, items, frame, start, tier) -> list[dict]:
    boxes, cursor = [], start
    for idx, item in enumerate(items):
        if item.get("kind") != "gap":
            box = _item_box(run, item, idx, frame, cursor, tier)
            box["_from"] = cursor
            boxes.append(box)
        else:
            boxes.append({"kind": "gap", "_from": cursor, "size": [float(item["w"]), 0, 0]})
        cursor += float(item["w"])
    return boxes


def expand_run(run: dict, walls: dict) -> list[dict]:
    wall = walls.get(run["wall"])
    if wall is None:
        raise ValueError(f"run {run['id']}: unknown wall {run['wall']!r}")
    origin, u, n = _axis(wall, run.get("side", "left"))
    frame = (origin, u, n, wall.get("thickness", 0.15) / 2)
    bases = _row(run, run.get("base", []), frame, float(run.get("from", 0.0)), "base")
    uppers = _row(run, run.get("upper", []), frame, float(run.get("upper_from", run.get("from", 0.0))), "upper")
    counters = _counters(run, bases, frame) if run.get("counter", True) else []
    real = [b for b in bases + uppers if b["kind"] != "gap"]
    return [{k: v for k, v in b.items() if k != "_from"} for b in real + counters]


def _local(center, rot, along, out) -> list[float]:
    cx, cy = center
    ux, uy = math.cos(rot), math.sin(rot)          # rot = facing direction of the seating side
    return [cx + -uy * along + ux * out, cy + ux * along + uy * out]


def expand_island(island: dict) -> list[dict]:
    w, d = island["size"]
    rot = math.radians(island.get("rot", 0.0))     # degrees in plan.json, radians in boxes
    h = island.get("h", DEFAULTS["island_h"])
    src = island.get("src", "estimated")
    base = {"group": island["id"], "rot": rot, "src": src, "room": island.get("room")}
    over = island.get("overhang", DEFAULTS["overhang"]) if island.get("stools") else 0.0
    boxes = [
        {**base, "id": f"{island['id']}.body", "kind": island.get("kind", "island"), "label": island.get("label", ""),
         "center": _local(island["center"], rot, 0, -over / 2), "size": [w, d - over, h - 0.03], "z": 0.0, "tier": "island"},
        {**base, "id": f"{island['id']}.top", "kind": "counter", "label": "", "center": list(island["center"]),
         "size": [w, d, 0.03], "z": h - 0.03, "tier": "counter"},
    ]
    count = int(island.get("stools", 0))
    pitch = min(DEFAULTS["stool_pitch"], w / max(count, 1))
    for i in range(count):
        along = (i - (count - 1) / 2) * pitch
        boxes.append({**base, "id": f"{island['id']}.s{i + 1}", "kind": "stool", "label": "", "tier": "stool",
                      "center": _local(island["center"], rot, along, d / 2 + 0.12), "size": [0.42, 0.42, 0.75], "z": 0.0})
    return boxes


def expand(plan: dict) -> list[dict]:
    """All boxes for a plan: runs, islands and free-standing fixtures."""
    walls = {w["id"]: w for w in plan.get("walls", [])}
    boxes: list[dict] = []
    for run in plan.get("runs", []):
        boxes += expand_run(run, walls)
    for island in plan.get("islands", []):
        boxes += expand_island(island)
    for fx in plan.get("fixtures", []):
        w, d, h = fx["size"]
        boxes.append({"id": fx["id"], "group": fx["id"], "kind": fx["kind"], "label": fx.get("label", ""),
                      "center": list(fx["center"]), "size": [w, d, h], "z": fx.get("z", 0.0),
                      "rot": math.radians(fx.get("rot", 0.0)), "src": fx.get("src", "estimated"),
                      "tier": "fixture", "room": fx.get("room")})
    return boxes
