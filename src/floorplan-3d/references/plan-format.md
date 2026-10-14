# plan.json format

Base: PlanWalk's `planwalk/1` schema (validated by `scripts/planwalk_schema.py`, a verbatim copy).
On top of it come top-level extension keys. PlanWalk ignores them, so the same file still runs through PlanWalk's build.
Units: **metres**. X = east, Y = north. Angles in `fixtures`/`islands` are in **degrees**, and mean the direction the front faces
(0 = east, 90 = north, 180 = west, -90 = south). The `boxes` that come out of `runs.py` carry radians.

## Core (planwalk/1)

```jsonc
{
  "schema": "planwalk/1", "units": "meters",
  "source": {"image": "F1.PDF", "page": 1, "dpi": 200, "rotation": 90},
  "scale":  {"px_per_m": 157.48, "method": "stated-ratio", "confidence": 1.0},
  "defaults": {"wall_height": 2.70, "wall_thickness": 0.15, "door_height": 2.05, "window_height": 1.40, "window_sill": 0.90},
  "walls":    [{"id": "w1", "a": [x, y], "b": [x, y], "thickness": 0.20, "exterior": true}],
  "openings": [{"id": "o1", "wall": "w1", "kind": "door|window|opening", "center": [x, y], "width": 0.8,
                "height": 2.05, "sill": 0, "rooms": ["r1", "r2"], "hinge": "a|b", "swing": "inward|outward"}],
  "rooms":    [{"id": "r1", "label": "חדר שינה", "type": "<type>", "polygon": [[x, y], ...],
                "floor": "tile|parquet", "ceiling": true, "ceiling_height": 2.70}],
  "lights":   []
}
```
- `type`: living, bedroom, kitchen, bathroom, toilet, hallway, balcony, garden, storage, safe_room, other.
- A wall runs along the **axis** (centre of its thickness). A room polygon runs along the **inner faces** (net area).
- `swing` is relative to `rooms[0]` (inward = into the first room).
- reconcile fills in every optional field explicitly. PlanWalk's loader crashes on a missing value (`Defaults` is a slots dataclass).

## Extensions to core fields

| Field | Where | Meaning |
|---|---|---|
| `src: "drawing"` | wall | position measured from dimension strings; locked against snapping onto the CV |
| `kind: "railing"` | wall | glass railing 1.05 high (balcony), no full-height wall |
| `entrance: true` | opening | the entrance door; walk mode starts here, reachability is checked from here |
| `style: "sliding"` | door opening | sliding glass doors instead of a hinged leaf |
| `stated_area_m2` | room | the area written on the sheet for that room, checked to within 5% |

## Top-level extensions

```jsonc
"meta": {"title": "דירה F1 · 3 חדרים", "subtitle": "קומה 2 · קנ\"מ 1:50", "floor": 2, "north_deg": 0,
         "sheets": [{"name": "F1.PDF", "kind": "תוכנית דירה", "date": "2020-07-10"}]},   // north_deg: reading-plans.md

"runs": [{                       // cabinet run along a wall, read from an elevation
  "id": "k1", "room": "kitchen", "label": "מטבח · חזית B", "wall": "w13",
  "side": "left|right",           // side of the a->b direction the cabinets stand on
  "from": 0.108,                  // metres from point a of the wall to the start of the first unit
  "depth": 0.60, "base_h": 0.87, "counter": true, "src": "estimated",
  "base":  [{"w": 0.60, "kind": "drawers", "label": "מגירות", "src": "drawing"}, ...],
  "upper_from": 0.108, "upper_z": 1.45, "upper_h": 0.75, "upper_depth": 0.35,
  "upper": [{"w": 0.90, "kind": "hood"}, ...]
}],

"islands": [{"id": "i1", "room": "kitchen", "label": "אי", "center": [x, y], "size": [length, depth],
             "rot": 0, "h": 0.92, "stools": 3, "overhang": 0.30, "src": "drawing"}],   // rot = the seating side

"fixtures": [{"id": "wc", "room": "bath", "kind": "toilet", "label": "אסלה", "center": [x, y],
              "size": [w, d, h], "rot": 180, "z": 0, "src": "drawing"}],

"dimensions": [{"id": "d1", "a": [x, y, z], "b": [x, y, z], "cm": 277, "src": "drawing", "ref": "תוכנית"}],   // + "known": "n4" for a documented discrepancy
"notes": [{"id": "n1", "kind": "question|assumption", "text": "...", "at": [x, y, z?]}],
"checks": {"stated_total_m2": 57.0, "footprint": [[x, y], ...],      // footprint = outer faces, without balconies
           "dismiss_cv": {"w27": "balcony tile grid"}}              // CV lines reviewed on the overlay and rejected, with the reason
```

### Item kinds
- **base** (counter height): `cabinet`, `drawers`, `sink`, `cooktop`, `dishwasher`, `oven`, `gap` (an empty slot).
- **tall** (full height, no countertop above): `tall`, `fridge`, `oven_tower`, `pantry` (`h`, default 2.30).
- **upper**: `cabinet`, `open` (open shelf), `hood`.
- **fixtures**: `fridge`, `shower`, `toilet`, `vanity`, `washer`, `bathtub`, plus any furniture kind:
  `bed`, `nightstand`, `wardrobe`, `sofa`, `armchair`, `coffee_table`, `tv_unit`, `dining_table`, `chair`, `desk`,
  `rug`, `plant`, `outdoor_table`, `outdoor_chair`. An unknown kind renders as a neutral box (it never disappears).

### Dimensions: semantics
`a`/`b` sit **on the geometry** (wall faces), and `cm` is what's written on the sheet. reconcile compares the two
(tolerance: 3 cm or 1.5%), so this is a real check. An endpoint copied from the end of the dimension line only checks itself.

### Automatic furniture (the viewer)
For a bedroom, safe room (ממ"ד), living room or balcony that has no anchor item (bed/sofa/table) on the sheet, the viewer adds furniture tagged `estimated`.
A piece isn't placed if it blocks a door's swing zone, leaves the room, or overlaps joinery. The "ריהוט" (furniture) toggle in work mode hides it.
