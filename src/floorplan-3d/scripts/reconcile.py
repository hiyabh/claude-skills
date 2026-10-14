"""Stage 3: merge Claude's reading with PlanWalk's geometry, then prove it.

Usage:
    python reconcile.py <work> [--vision vision.plan.json] [--cv cv.plan.json] [--no-snap]

Division of labour:
  * Claude (vision.plan.json) decides WHAT exists: which walls, which rooms,
    their names and types, openings, dimensions read off the sheet, kitchens.
  * PlanWalk (cv.plan.json) knows WHERE ink is to the pixel. Each vision wall
    that has a parallel CV wall within SNAP_M is moved onto the CV axis, and
    room corners and wall ends follow onto the snapped lines.
Then the checks that make the result trustworthy: schema validation, stated
areas vs computed areas, every room reachable, kitchen items inside rooms.

Writes plan.json (the merged plan) and reconcile.md (the report) to <work>.
Exit code 0 = clean, 2 = warnings to review, 1 = invalid plan.
"""

from __future__ import annotations

import argparse
import math
import tempfile
from pathlib import Path

import planwalk_schema as schema
import runs
from common import read_json, utf8_stdout, write_json

SNAP_M = 0.12            # how far a wall may move onto CV ink
FACE_SNAP_M = 0.10       # how far a room corner may move onto a wall face
PARALLEL_DEG = 3.0
MIN_OVERLAP = 0.4        # fraction of the vision wall the CV wall must cover
AREA_TOLERANCE = 0.05
MISSED_WALL_MIN_M = 0.8
OPEN_KINDS = {"door", "opening"}
GLAZING_BAND_M = 0.35    # CV lines this close to a window/glass-door wall are frame rows, not partitions
OPEN_EDGE_M = 0.6        # shared un-walled boundary that counts as an open-plan link
DIM_TOLERANCE_M = 0.03   # a dimension string may differ from geometry by this much


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("work", type=Path)
    parser.add_argument("--vision", default="vision.plan.json")
    parser.add_argument("--cv", default="cv.plan.json")
    parser.add_argument("--no-snap", action="store_true", help="validate only, keep vision geometry as-is")
    return parser.parse_args()


# ---------------------------------------------------------------- geometry

def _dir(w) -> tuple[float, float, float]:
    dx, dy = w["b"][0] - w["a"][0], w["b"][1] - w["a"][1]
    length = math.hypot(dx, dy) or 1e-9
    return dx / length, dy / length, length


def _offset(point, w) -> float:
    """Signed perpendicular distance of point from wall w's axis."""
    ux, uy, _ = _dir(w)
    return (point[0] - w["a"][0]) * -uy + (point[1] - w["a"][1]) * ux


def _span(w, onto) -> tuple[float, float]:
    ux, uy, _ = _dir(onto)
    ts = [(p[0] - onto["a"][0]) * ux + (p[1] - onto["a"][1]) * uy for p in (w["a"], w["b"])]
    return min(ts), max(ts)


def _overlap(vw, cw) -> float:
    lo, hi = _span(cw, vw)
    return max(0.0, min(hi, _dir(vw)[2]) - max(lo, 0.0)) / _dir(vw)[2]


def _parallel(a, b) -> bool:
    ax, ay, _ = _dir(a)
    bx, by, _ = _dir(b)
    return abs(ax * by - ay * bx) < math.sin(math.radians(PARALLEL_DEG))


def shoelace(poly) -> float:
    return abs(sum(poly[i][0] * poly[i - 1][1] - poly[i - 1][0] * poly[i][1] for i in range(len(poly)))) / 2


def inside(point, poly) -> bool:
    x, y, hit = point[0], point[1], False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i - 1], poly[i]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


# ---------------------------------------------------------------- snapping

def _best_cv(vw, cv_walls):
    best = None
    for cw in cv_walls:
        if not _parallel(vw, cw) or _overlap(vw, cw) < MIN_OVERLAP:
            continue
        shift = _offset(cw["a"], vw)
        if abs(shift) <= SNAP_M and (best is None or abs(shift) < abs(best[1])):
            best = (cw, shift)
    return best


def snap_walls(vision: dict, cv: dict, log: list[str]) -> set[str]:
    """Move vision walls onto matching CV axes; return ids of CV walls used."""
    used: set[str] = set()
    run_walls = {r["wall"] for r in vision.get("runs", [])}
    for vw in vision["walls"]:
        if vw.get("src") == "drawing":
            continue  # measured from dimension strings: the sheet outranks the ink
        if vw["id"] in run_walls:
            continue  # a cabinet run hangs off this wall's a->b direction and `from`; never move it under the run
        match = _best_cv(vw, cv["walls"])
        if match is None:
            vw.setdefault("_note", "no CV match")
            continue
        cw, shift = match
        ux, uy, _ = _dir(vw)
        nx, ny = -uy * shift, ux * shift
        vw["a"] = [vw["a"][0] + nx, vw["a"][1] + ny]
        vw["b"] = [vw["b"][0] + nx, vw["b"][1] + ny]
        if vw.get("src") != "drawing":
            vw["thickness"] = cw["thickness"]
        used.add(cw["id"])
        if abs(shift) > 0.02:
            log.append(f"wall {vw['id']}: moved {shift * 100:+.0f} cm onto CV {cw['id']}")
    return used


def _nearest_line(value: float, lines: list[float]) -> float:
    best = min(lines, key=lambda v: abs(v - value), default=value)
    return best if abs(best - value) <= FACE_SNAP_M else value


def snap_corners(plan: dict, log: list[str]) -> None:
    """Pull room corners onto wall faces and wall ends onto crossing axes (axis-aligned walls only).

    A wall whose ends would cross or collapse (both ends pulled to one line) keeps its drawn ends:
    flipping a->b silently mirrors every cabinet run and door hinge on it.
    """
    xs_face, ys_face, xs_axis, ys_axis = [], [], [], []
    for w in plan["walls"]:
        ux, uy, _ = _dir(w)
        half = w["thickness"] / 2
        if abs(ux) < 1e-3:   # vertical
            xs_axis.append(w["a"][0])
            xs_face += [w["a"][0] - half, w["a"][0] + half]
        elif abs(uy) < 1e-3:  # horizontal
            ys_axis.append(w["a"][1])
            ys_face += [w["a"][1] - half, w["a"][1] + half]
    for room in plan["rooms"]:
        room["polygon"] = [[_nearest_line(x, xs_face), _nearest_line(y, ys_face)] for x, y in room["polygon"]]
    run_walls = {r["wall"] for r in plan.get("runs", [])}
    for w in plan["walls"]:
        if w["id"] in run_walls or w.get("src") == "drawing":
            continue
        ux, uy, length = _dir(w)
        before = (list(w["a"]), list(w["b"]))
        for end in ("a", "b"):
            x, y = w[end]
            w[end] = [_nearest_line(x, xs_axis) if abs(uy) < 1e-3 else x,
                      _nearest_line(y, ys_axis) if abs(ux) < 1e-3 else y]
        nx, ny, new_len = _dir(w)
        if nx * ux + ny * uy <= 0 or new_len < length * 0.5:
            w["a"], w["b"] = before
            log.append(f"wall {w['id']}: snapping its ends would flip or collapse it - kept as drawn")


def project_openings(plan: dict) -> None:
    walls = {w["id"]: w for w in plan["walls"]}
    for op in plan.get("openings", []):
        w = walls.get(op["wall"])
        if w is None:
            continue
        ux, uy, length = _dir(w)
        t = (op["center"][0] - w["a"][0]) * ux + (op["center"][1] - w["a"][1]) * uy
        t = min(max(t, op["width"] / 2), length - op["width"] / 2)
        op["center"] = [w["a"][0] + ux * t, w["a"][1] + uy * t]


def _on_box(point, boxes) -> bool:
    """Is point on the footprint of a cabinet/fixture (CV often reads their edges as walls)?"""
    for box in boxes:
        (cx, cy), (w, d, _), r = box["center"], box["size"], box["rot"]
        fx, fy = math.cos(r), math.sin(r)
        along = (point[0] - cx) * -fy + (point[1] - cy) * fx
        out = (point[0] - cx) * fx + (point[1] - cy) * fy
        if abs(along) <= w / 2 + 0.08 and abs(out) <= d / 2 + 0.08:
            return True
    return False


def _on_glazing(cw: dict, mid, plan: dict) -> bool:
    """Is this CV line part of a window or glass door (parallel to it, within its span and near its wall)?"""
    walls = {w["id"]: w for w in plan["walls"]}
    for o in plan.get("openings", []):
        w = walls.get(o["wall"])
        if not w or not (o["kind"] == "window" or o.get("style") == "sliding") or not _parallel(w, cw):
            continue
        ux, uy, _ = _dir(w)
        along = (mid[0] - o["center"][0]) * ux + (mid[1] - o["center"][1]) * uy
        if abs(along) <= o["width"] / 2 + 0.2 and abs(_offset(mid, w)) <= GLAZING_BAND_M:
            return True
    return False


def missed_walls(cv: dict, used: set[str], plan: dict) -> list[str]:
    rooms = [r["polygon"] for r in plan["rooms"]]
    open_air = [r["polygon"] for r in plan["rooms"] if r.get("type") in schema.OPEN_AIR_TYPES]
    try:
        boxes = runs.expand(plan)
    except (KeyError, ValueError):
        boxes = []
    out = []
    for cw in cv.get("walls", []):
        mid = ((cw["a"][0] + cw["b"][0]) / 2, (cw["a"][1] + cw["b"][1]) / 2)
        if cw["id"] in used or _dir(cw)[2] < MISSED_WALL_MIN_M or not any(inside(mid, p) for p in rooms):
            continue
        if _on_box(mid, boxes) or _on_box(cw["a"], boxes) or _on_box(cw["b"], boxes):
            continue
        if cw["id"] in plan.get("checks", {}).get("dismiss_cv", {}):
            continue
        if any(inside(mid, p) for p in open_air) or _on_glazing(cw, mid, plan):
            continue  # balcony tile grids and the frame rows of glass doors read as walls to the CV
        out.append(f"CV wall {cw['id']} ({_dir(cw)[2]:.2f} m at {mid[0]:.2f},{mid[1]:.2f}) runs through a room - missed partition?")
    return out


# ---------------------------------------------------------------- checks

def check_areas(plan: dict) -> list[str]:
    out = []
    for room in plan["rooms"]:
        stated = room.get("stated_area_m2")
        if stated:
            area = shoelace(room["polygon"])
            if abs(area - stated) / stated > AREA_TOLERANCE:
                out.append(f"room {room['id']} {room.get('label', '')}: {area:.2f} m2 vs {stated} m2 on the sheet")
    checks = plan.get("checks", {})
    if checks.get("stated_total_m2") and checks.get("footprint"):
        gross = shoelace(checks["footprint"])
        stated = checks["stated_total_m2"]
        if abs(gross - stated) / stated > AREA_TOLERANCE:
            out.append(f"footprint {gross:.2f} m2 vs stated apartment area {stated} m2")
    return out


def _edges(poly):
    return [(poly[i - 1], poly[i]) for i in range(len(poly))]


def _shared(e1, e2) -> tuple[float, tuple[float, float]] | None:
    """Overlap length and midpoint of two collinear edges, or None."""
    (a, b), (c, d) = e1, e2
    w = {"a": a, "b": b}
    if math.dist(a, b) < 1e-6 or abs(_offset(c, w)) > 0.02 or abs(_offset(d, w)) > 0.02:
        return None
    ux, uy, length = _dir(w)
    ts = sorted(((c[0] - a[0]) * ux + (c[1] - a[1]) * uy, (d[0] - a[0]) * ux + (d[1] - a[1]) * uy))
    lo, hi = max(0.0, ts[0]), min(length, ts[1])
    if hi - lo <= 0:
        return None
    mid = (lo + hi) / 2
    return hi - lo, (a[0] + ux * mid, a[1] + uy * mid)


def _walled(point, walls) -> bool:
    for w in walls:
        ux, uy, length = _dir(w)
        t = (point[0] - w["a"][0]) * ux + (point[1] - w["a"][1]) * uy
        if -0.05 <= t <= length + 0.05 and abs(_offset(point, w)) <= w["thickness"] / 2 + 0.03:
            return True
    return False


def open_links(plan: dict) -> list[tuple[str, str]]:
    """Rooms that share at least OPEN_EDGE_M of boundary with no wall on it (open-plan)."""
    links, rooms = [], plan["rooms"]
    for i, r1 in enumerate(rooms):
        for r2 in rooms[i + 1:]:
            for e1 in _edges(r1["polygon"]):
                hits = [s for e2 in _edges(r2["polygon"]) if (s := _shared(e1, e2))]
                if any(length >= OPEN_EDGE_M and not _walled(mid, plan["walls"]) for length, mid in hits):
                    links.append((r1["id"], r2["id"]))
                    break
    return links


def area_summary(plan: dict) -> str:
    net = sum(shoelace(r["polygon"]) for r in plan["rooms"] if r.get("type") not in schema.OPEN_AIR_TYPES)
    text = f"net rooms (no balconies) {net:.2f} m2"
    footprint = plan.get("checks", {}).get("footprint")
    if footprint:
        text += f", footprint {shoelace(footprint):.2f} m2"
    stated = plan.get("checks", {}).get("stated_total_m2")
    return text + (f", sheet states {stated} m2" if stated else "")


def reachable(plan: dict) -> tuple[set[str], set[str]]:
    rooms = {r["id"] for r in plan["rooms"]}
    links: dict[str, set[str]] = {r: set() for r in rooms}
    for a, b in open_links(plan):
        links[a].add(b)
        links[b].add(a)
    starts = set()
    for op in plan.get("openings", []):
        if op["kind"] not in OPEN_KINDS:
            continue
        ids = [r for r in op.get("rooms", []) if r in rooms]
        if op.get("entrance") or len(ids) == 1:
            starts.update(ids)
        for a in ids:
            links[a].update(i for i in ids if i != a)
    seen, stack = set(), list(starts or list(rooms)[:1])
    while stack:
        room = stack.pop()
        if room not in seen:
            seen.add(room)
            stack.extend(links[room] - seen)
    return seen, rooms - seen


def acknowledged(plan: dict) -> list[str]:
    """Findings Claude reviewed and documented: listed every run, never counted as warnings."""
    out = [f"CV wall {wid}: {why}" for wid, why in plan.get("checks", {}).get("dismiss_cv", {}).items()]
    out += [f"dimension {d.get('id')} ({d.get('cm')} cm): known discrepancy, see note {d['known']}"
            for d in plan.get("dimensions", []) if d.get("known")]
    return out


def dimension_summary(plan: dict) -> str:
    drawn = [d for d in plan.get("dimensions", []) if d.get("src") == "drawing" and d.get("cm")]
    known = sum(1 for d in drawn if d.get("known"))
    if not drawn:
        return "no drawing dimensions to check - add the strings you read"
    tail = f" ({known} more are known discrepancies, listed under acknowledged)" if known else ""
    return f"{len(drawn) - known} checked, all within {DIM_TOLERANCE_M * 100:.0f} cm / 1.5%{tail}"


def check_dimensions(plan: dict) -> list[str]:
    out = []
    for i, dim in enumerate(plan.get("dimensions", [])):
        if dim.get("src") != "drawing" or not dim.get("cm"):
            continue
        measured = math.dist(dim["a"][:2], dim["b"][:2])
        stated = dim["cm"] / 100
        if abs(measured - stated) > max(DIM_TOLERANCE_M, stated * 0.015) and not dim.get("known"):
            out.append(f"dimension {dim.get('id', i)} ({dim.get('ref', '')}): sheet says {dim['cm']:g} cm, "
                       f"geometry gives {measured * 100:.0f} cm")
    return out


def check_boxes(plan: dict) -> list[str]:
    try:
        boxes = runs.expand(plan)
    except (KeyError, ValueError) as error:
        return [f"kitchen/fixtures: {error}"]
    polys = {r["id"]: r["polygon"] for r in plan["rooms"]}
    out = []
    for box in boxes:
        poly = polys.get(box.get("room"))
        if poly and not inside(box["center"], poly):
            out.append(f"{box['id']} ({box['kind']}) is outside room {box['room']}")
    return out


def fill_defaults(plan: dict) -> None:
    """Write every optional core field explicitly.

    PlanWalk's schema reads missing values from a slots dataclass, where the
    class attribute is a descriptor, not the number - so an omitted
    ceiling_height or thickness crashes its loader. Explicit values avoid that
    and make plan.json self-describing for PlanWalk's build stage too.
    """
    d = {**schema.Defaults().to_dict(), **plan.get("defaults", {})}
    plan["defaults"] = d
    for w in plan["walls"]:
        w.setdefault("thickness", d["wall_thickness"])
    for o in plan.get("openings", []):
        o.setdefault("height", d["door_height"] if o["kind"] != "window" else d["window_height"])
        o.setdefault("sill", d["window_sill"] if o["kind"] == "window" else 0.0)
    for r in plan["rooms"]:
        r.setdefault("ceiling", r.get("type") not in schema.OPEN_AIR_TYPES)
        r.setdefault("ceiling_height", d["wall_height"])
        r.setdefault("floor", "tile")


def validate_core(plan: dict) -> str | None:
    with tempfile.TemporaryDirectory() as tmp:
        path = write_json(Path(tmp) / "plan.json", plan)
        try:
            schema.load(path)
        except schema.PlanError as error:
            return str(error)
    return None


def provenance(plan: dict) -> str:
    items = runs.expand(plan) + plan.get("dimensions", [])
    if not items:
        return "no kitchen items or dimension lines"
    drawn = sum(1 for i in items if i.get("src") == "drawing")
    return f"{drawn}/{len(items)} sizes from the drawing, {len(items) - drawn} estimated"


# ---------------------------------------------------------------- main

def _report(work: Path, sections: dict[str, list[str]]) -> Path:
    lines = ["# reconcile report", ""]
    for title, items in sections.items():
        lines += [f"## {title}", *(f"- {i}" for i in items or ["none"]), ""]
    path = work / "reconcile.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def build_sections(plan: dict, moves: list[str], missed: list[str], had_cv: bool):
    unmatched = [f"wall {w['id']}: no CV ink found - confirm it on the overlay" for w in plan["walls"] if w.pop("_note", None)]
    seen, cut_off = reachable(plan)
    error = validate_core(plan)
    sections = {
        "schema": [error] if error else ["valid planwalk/1"],
        "snapped onto CV ink": moves,
        "vision walls with no CV ink": unmatched if had_cv else ["(no CV run)"],
        "CV walls not in the plan": missed,
        "areas vs the sheet": check_areas(plan) + [area_summary(plan)],
        "dimension strings vs geometry": check_dimensions(plan) or [dimension_summary(plan)],
        "reachability": [f"cannot reach: {', '.join(sorted(cut_off))}"] if cut_off else [f"all {len(seen)} rooms reachable"],
        "kitchen and fixtures": check_boxes(plan),
        "acknowledged (reviewed, documented)": acknowledged(plan),
        "provenance": [provenance(plan)],
    }
    return sections, error, cut_off


def main() -> int:
    utf8_stdout()
    args = _parse()
    plan = read_json(args.work / args.vision)
    fill_defaults(plan)
    cv_path = args.work / args.cv
    moves: list[str] = []
    missed: list[str] = []
    if cv_path.exists() and not args.no_snap:
        cv = read_json(cv_path)
        used = snap_walls(plan, cv, moves)
        snap_corners(plan, moves)
        missed = missed_walls(cv, used, plan)
    project_openings(plan)
    sections, error, cut_off = build_sections(plan, moves, missed, cv_path.exists())
    write_json(args.work / "plan.json", plan)
    report = _report(args.work, sections)
    print(report.read_text(encoding="utf-8"))
    warnings = missed + check_areas(plan) + check_dimensions(plan) + check_boxes(plan) + ([1] if cut_off else [])
    return 1 if error else (2 if warnings else 0)


if __name__ == "__main__":
    raise SystemExit(main())
