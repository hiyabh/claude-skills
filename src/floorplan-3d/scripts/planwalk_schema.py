"""Canonical plan.json format: parsing, serialisation and validation.

Vendored verbatim from PlanWalk (src/planwalk/schema.py @ d3988f0) so the skill
validates plans even on a machine without PlanWalk. Do not edit here; sync it.

plan.json is the hand-editable contract between the three pipeline stages.
Everything is in metres, absolute coordinates, with stable ids and no derived
fields. X points right, Y points up, origin at the bounding box corner.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

SCHEMA_VERSION = "planwalk/1"

RoomType = Literal[
    "living", "bedroom", "kitchen", "bathroom", "toilet", "hallway",
    "balcony", "garden", "storage", "safe_room", "other",
]
ROOM_TYPES: tuple[str, ...] = (
    "living", "bedroom", "kitchen", "bathroom", "toilet", "hallway",
    "balcony", "garden", "storage", "safe_room", "other",
)
OPENING_KINDS: tuple[str, ...] = ("door", "window", "opening")

# Rooms without a ceiling are open to the sky and get a railing, not a wall.
OPEN_AIR_TYPES: frozenset[str] = frozenset({"balcony", "garden"})

Point = tuple[float, float]


class PlanError(ValueError):
    """Raised when a plan.json fails validation, with a human-readable reason."""


def _pt(value: Any, where: str) -> Point:
    if not (isinstance(value, (list, tuple)) and len(value) == 2):
        raise PlanError(f"{where}: expected a [x, y] pair, got {value!r}")
    try:
        return (float(value[0]), float(value[1]))
    except (TypeError, ValueError):
        raise PlanError(f"{where}: coordinates must be numbers, got {value!r}") from None


@dataclass(slots=True)
class Scale:
    px_per_m: float
    method: str = "unknown"
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "px_per_m": round(self.px_per_m, 4),
            "method": self.method,
            "confidence": round(self.confidence, 3),
        }


@dataclass(slots=True)
class Defaults:
    wall_height: float = 2.70
    wall_thickness: float = 0.15
    door_height: float = 2.05
    window_height: float = 1.40
    window_sill: float = 0.90

    def to_dict(self) -> dict[str, Any]:
        return {
            "wall_height": self.wall_height,
            "wall_thickness": self.wall_thickness,
            "door_height": self.door_height,
            "window_height": self.window_height,
            "window_sill": self.window_sill,
        }


# The parsers fall back to these values. Read them from an instance: on a slots dataclass the
# class attribute (Defaults.wall_height) is a member descriptor, not 2.70.
DEFAULTS = Defaults()


@dataclass(slots=True)
class Wall:
    id: str
    a: Point
    b: Point
    thickness: float
    exterior: bool = False

    @property
    def length(self) -> float:
        return math.dist(self.a, self.b)

    @property
    def angle(self) -> float:
        """Direction of a->b in radians."""
        return math.atan2(self.b[1] - self.a[1], self.b[0] - self.a[0])

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "a": [round(self.a[0], 4), round(self.a[1], 4)],
            "b": [round(self.b[0], 4), round(self.b[1], 4)],
            "thickness": round(self.thickness, 4),
            "exterior": self.exterior,
        }


@dataclass(slots=True)
class Opening:
    id: str
    wall: str
    kind: str
    center: Point
    width: float
    height: float
    sill: float = 0.0
    hinge: str = "a"          # which wall end the door pivots on
    swing: str = "inward"     # relative to rooms[0]
    rooms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": self.id,
            "wall": self.wall,
            "kind": self.kind,
            "center": [round(self.center[0], 4), round(self.center[1], 4)],
            "width": round(self.width, 4),
            "height": round(self.height, 4),
            "sill": round(self.sill, 4),
            "rooms": list(self.rooms),
        }
        if self.kind == "door":
            out["hinge"] = self.hinge
            out["swing"] = self.swing
        return out


@dataclass(slots=True)
class Room:
    id: str
    label: str
    type: str
    polygon: list[Point]
    floor: str = "tile"
    ceiling: bool = True
    ceiling_height: float = 2.70

    @property
    def area(self) -> float:
        """Shoelace area in square metres."""
        pts = self.polygon
        total = sum(
            pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
            for i in range(len(pts))
        )
        return abs(total) / 2.0

    @property
    def centroid(self) -> Point:
        xs = [p[0] for p in self.polygon]
        ys = [p[1] for p in self.polygon]
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "polygon": [[round(x, 4), round(y, 4)] for x, y in self.polygon],
            "floor": self.floor,
            "ceiling": self.ceiling,
            "ceiling_height": self.ceiling_height,
        }


@dataclass(slots=True)
class Light:
    id: str
    room: str
    position: Point
    height: float = 2.60
    kind: str = "ceiling"
    watts: float = 60.0
    switch_default: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "room": self.room,
            "position": [round(self.position[0], 4), round(self.position[1], 4)],
            "height": self.height,
            "kind": self.kind,
            "watts": self.watts,
            "switch_default": self.switch_default,
        }


@dataclass(slots=True)
class Plan:
    scale: Scale
    source: dict[str, Any] = field(default_factory=dict)
    defaults: Defaults = field(default_factory=Defaults)
    walls: list[Wall] = field(default_factory=list)
    openings: list[Opening] = field(default_factory=list)
    rooms: list[Room] = field(default_factory=list)
    lights: list[Light] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA_VERSION,
            "units": "meters",
            "source": self.source,
            "scale": self.scale.to_dict(),
            "defaults": self.defaults.to_dict(),
            "walls": [w.to_dict() for w in self.walls],
            "openings": [o.to_dict() for o in self.openings],
            "rooms": [r.to_dict() for r in self.rooms],
            "lights": [lt.to_dict() for lt in self.lights],
        }

    def wall_by_id(self, wall_id: str) -> Wall | None:
        return next((w for w in self.walls if w.id == wall_id), None)

    def room_by_id(self, room_id: str) -> Room | None:
        return next((r for r in self.rooms if r.id == room_id), None)

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path


def _parse_walls(raw: list[Any]) -> list[Wall]:
    walls = []
    for i, w in enumerate(raw):
        where = f"walls[{i}]"
        if "id" not in w:
            raise PlanError(f"{where}: missing 'id'")
        walls.append(Wall(
            id=str(w["id"]),
            a=_pt(w.get("a"), f"{where}.a"),
            b=_pt(w.get("b"), f"{where}.b"),
            thickness=float(w.get("thickness", DEFAULTS.wall_thickness)),
            exterior=bool(w.get("exterior", False)),
        ))
    return walls


def _parse_openings(raw: list[Any]) -> list[Opening]:
    openings = []
    for i, o in enumerate(raw):
        where = f"openings[{i}]"
        for key in ("id", "wall", "kind", "center", "width"):
            if key not in o:
                raise PlanError(f"{where}: missing '{key}'")
        openings.append(Opening(
            id=str(o["id"]),
            wall=str(o["wall"]),
            kind=str(o["kind"]),
            center=_pt(o["center"], f"{where}.center"),
            width=float(o["width"]),
            height=float(o.get("height", DEFAULTS.door_height)),
            sill=float(o.get("sill", 0.0)),
            hinge=str(o.get("hinge", "a")),
            swing=str(o.get("swing", "inward")),
            rooms=[str(r) for r in o.get("rooms", [])],
        ))
    return openings


def _parse_rooms(raw: list[Any]) -> list[Room]:
    rooms = []
    for i, r in enumerate(raw):
        where = f"rooms[{i}]"
        if "id" not in r:
            raise PlanError(f"{where}: missing 'id'")
        poly = r.get("polygon") or []
        rooms.append(Room(
            id=str(r["id"]),
            label=str(r.get("label", "")),
            type=str(r.get("type", "other")),
            polygon=[_pt(p, f"{where}.polygon[{j}]") for j, p in enumerate(poly)],
            floor=str(r.get("floor", "tile")),
            ceiling=bool(r.get("ceiling", True)),
            ceiling_height=float(r.get("ceiling_height", DEFAULTS.wall_height)),
        ))
    return rooms


def _parse_lights(raw: list[Any]) -> list[Light]:
    return [
        Light(
            id=str(lt["id"]),
            room=str(lt.get("room", "")),
            position=_pt(lt.get("position"), f"lights[{i}].position"),
            height=float(lt.get("height", 2.60)),
            kind=str(lt.get("kind", "ceiling")),
            watts=float(lt.get("watts", 60.0)),
            switch_default=bool(lt.get("switch_default", True)),
        )
        for i, lt in enumerate(raw)
    ]


def load(path: str | Path) -> Plan:
    """Read a plan.json from disk and validate it."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA_VERSION:
        raise PlanError(
            f"unsupported schema {data.get('schema')!r}; this build expects {SCHEMA_VERSION!r}"
        )
    scale_raw = data.get("scale") or {}
    defaults_raw = data.get("defaults") or {}
    plan = Plan(
        scale=Scale(
            px_per_m=float(scale_raw.get("px_per_m", 0.0)),
            method=str(scale_raw.get("method", "unknown")),
            confidence=float(scale_raw.get("confidence", 0.0)),
        ),
        source=data.get("source") or {},
        defaults=Defaults(**{
            k: float(v) for k, v in defaults_raw.items()
            if k in Defaults.__slots__
        }),
        walls=_parse_walls(data.get("walls") or []),
        openings=_parse_openings(data.get("openings") or []),
        rooms=_parse_rooms(data.get("rooms") or []),
        lights=_parse_lights(data.get("lights") or []),
    )
    validate(plan)
    return plan


def _validate_walls(plan: Plan, problems: list[str]) -> None:
    seen: set[str] = set()
    for w in plan.walls:
        if w.id in seen:
            problems.append(f"wall {w.id}: duplicate id")
        seen.add(w.id)
        if w.length < 1e-6:
            problems.append(f"wall {w.id}: zero length (a and b are the same point)")
        if not 0.01 <= w.thickness <= 1.5:
            problems.append(f"wall {w.id}: implausible thickness {w.thickness} m")


def _validate_openings(plan: Plan, problems: list[str]) -> None:
    seen: set[str] = set()
    for o in plan.openings:
        if o.id in seen:
            problems.append(f"opening {o.id}: duplicate id")
        seen.add(o.id)
        if o.kind not in OPENING_KINDS:
            problems.append(f"opening {o.id}: unknown kind {o.kind!r}, expected one of {OPENING_KINDS}")
        wall = plan.wall_by_id(o.wall)
        if wall is None:
            problems.append(f"opening {o.id}: references unknown wall {o.wall!r}")
            continue
        if o.width > wall.length + 1e-6:
            problems.append(
                f"opening {o.id}: width {o.width:.2f} m exceeds wall {wall.id} length {wall.length:.2f} m"
            )
        if _distance_to_segment(o.center, wall.a, wall.b) > 0.25:
            problems.append(f"opening {o.id}: center is not on wall {wall.id}")
        if o.hinge not in ("a", "b"):
            problems.append(f"opening {o.id}: hinge must be 'a' or 'b', got {o.hinge!r}")


def _validate_rooms(plan: Plan, problems: list[str]) -> None:
    seen: set[str] = set()
    for r in plan.rooms:
        if r.id in seen:
            problems.append(f"room {r.id}: duplicate id")
        seen.add(r.id)
        if len(r.polygon) < 3:
            problems.append(f"room {r.id}: polygon needs at least 3 points, has {len(r.polygon)}")
        elif r.area < 0.5:
            problems.append(f"room {r.id}: area {r.area:.2f} m2 is too small to be a room")
        if r.type not in ROOM_TYPES:
            problems.append(f"room {r.id}: unknown type {r.type!r}, expected one of {ROOM_TYPES}")


def validate(plan: Plan) -> None:
    """Raise PlanError listing every problem found, or return silently."""
    problems: list[str] = []
    if plan.scale.px_per_m <= 0:
        problems.append("scale.px_per_m must be positive (the plan has no usable scale)")
    _validate_walls(plan, problems)
    _validate_openings(plan, problems)
    _validate_rooms(plan, problems)

    known_rooms = {r.id for r in plan.rooms}
    for lt in plan.lights:
        if lt.room and lt.room not in known_rooms:
            problems.append(f"light {lt.id}: references unknown room {lt.room!r}")

    if problems:
        raise PlanError(
            "plan.json has %d problem(s):\n  - %s" % (len(problems), "\n  - ".join(problems))
        )


def _distance_to_segment(p: Point, a: Point, b: Point) -> float:
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    denom = dx * dx + dy * dy
    if denom < 1e-12:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denom))
    return math.dist(p, (ax + t * dx, ay + t * dy))
