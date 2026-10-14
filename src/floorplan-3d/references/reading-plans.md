# Reading Israeli architectural drawings correctly

Lessons learned from the first run (sheet F1, a 3-room apartment, 1:50, 2026-10-08). Every item here cost a mistake.

## The sheet
- **Scale**: `קנ"מ 1:50` in the title block. PlanWalk's OCR drops the colon, so always pass `--scale-ratio 50`.
  At 200 dpi a 1:50 drawing gives 157.48 px/m (`dpi / 0.0254 / ratio`).
- **Dimensions are in cm** (277, 308). A chain = consecutive dimensions along one line. The outer chain gives the
  footprint (outer faces); the inner chain gives room widths between faces.
- **Stated area** ("דירה מס' 011, 57.0 מ"ר") = the apartment area per the Sale Law regulations, which **includes walls**
  (exterior walls in full, half of shared walls) and excludes balconies. Compare it with `checks.footprint`, not with the net room area.
  Net comes out roughly 15-20% lower (F1: 47.2 net against 58.3 footprint against 57.0 stated).
- **Legend**: diagonal yellow hatching = concrete wall; crosshatching = block wall; a dotted grid = sun balcony.
- **Light grey drawing outside the walls** = the neighbouring unit or the floor lobby. Not part of the apartment.
- **A sheet note** such as "סידור ארונות מטבח סופי יקבע..." (the final kitchen layout will be decided later) means the kitchen is indicative. Record it as an `assumption` note.

## North, floor, and the game-mode sun
- **`meta.north_deg`** = the compass bearing of the sheet's "up" (+y). Measure the north arrow's angle θ **clockwise from
  the sheet's up**, then `north_deg = (360 − θ) mod 360`. An arrow pointing straight up = 0. Pointing right (east on the
  sheet) = 270. Pointing left = 90. Without it the sun, the "best light" hour and the direction of the window views
  are all wrong.
- **`meta.floor`** = the floor number from the title block ("קומה 14"). It sets the window views' height. views.py warns
  when it is missing (it otherwise assumes floor 2).

## Dimension lines (where `a`/`b` go)
- An extension line may run past the face it measures, and a dimension chain may nest inside the overall dimension.
  Put `a`/`b` on **the faces the number refers to**, not at the ends of the drawn line. If 196 doesn't fit any pair of
  faces, that's a finding.
- A discrepancy you can't resolve: write a question note, then on the dimension `"known": "<note id>"`. reconcile lists it
  under "acknowledged" and doesn't block a clean exit.

## Symbols
| On the sheet | Meaning | Trap |
|---|---|---|
| Arc + straight line from a hinge | hinged door; the leaf is drawn in the open position | the CV sometimes reads a bedroom door as a window |
| Arc in the north wall of a ממ"ד | the blast window's steel leaf | it's a window, not a door |
| Row of small rectangles along the facade | sliding door / glazed wall | the CV doesn't detect it; set `style: "sliding"` |
| Thin double line on a facade | window (a corner window can wrap two walls) | |
| Square with a handle ("מקום מיועד למקרר") | fridge space | |
| 4 circles | cooktop | |
| Small rectangle with a cross / "V" in a circle | technical ventilation / riser | not a room, not a wall |
| A tube drawn across a wall ("צינור אוורור") | ventilation pipe | the CV reads it as a short wall |
| Narrow yellow-hatched strip next to the bathroom ("פיר") | shaft | outside the rooms |

## What the CV (PlanWalk) gets wrong, and Claude fixes
- **Predictable noise that reconcile already filters:**
  - a balcony tile grid (anything inside a balcony/garden polygon);
  - the frame rows of a glass sliding door and windows (parallel lines within 35 cm of a window's wall, along its span);
  - the edges of joinery, fixtures and the washer.

  What's left must be checked on the overlay. A line you're sure isn't a wall goes into `checks.dismiss_cv` with the
  reason (`{"w27": "balcony tile grid"}`).
- **Merges open spaces**: living + kitchen + hallway become one room. Split them into separate rooms. reconcile treats a
  shared boundary with no wall (≥60 cm) as an open passage.
- **Edges of fixtures and joinery read as walls**: counter edges, shower glass, the washer column, the vanity unit.
  reconcile already filters those that fall on a box, but inspect the rest.
- **Invents a door between two rooms** separated by a solid concrete wall, or "rooms" outside the apartment (F1: a "toilet"
  that was in the neighbouring unit).
- **What it gets right**: the positions and thicknesses of main walls, to about 1 cm. Copy coordinates from it.

## Reading coordinates without the CV
- The labels in `zoom.py` sit **on top of** their line. Read the line, never the edge of the label.
- Reading "by eye" from a grid drifts by about 15 cm (measured on F1). So: (a) zoom until 10 cm is clear, (b) better,
  start from one corner and **sum dimension chains**, (c) check against the overlay.
- A ממ"ד has thick walls (20-45 cm). Take its inner faces from the dimension string (276/350), not from the ink.

## Open-plan kitchen
- A run longer than the kitchen polygon (it continues into the living room) produces "outside room" warnings. Either
  make the kitchen an L-shaped polygon that includes the run, or set `room` on the run to the room holding most of it.
- A wall carrying a run is locked against snapping automatically (moving it would shift the run). `src:"drawing"` locks
  any wall.

## Room-level elevations
- An elevation is labelled with a letter (`ELEVATION F`, `חזית B`) and a section with two letters (`Section HH`). In the floor plan
  there's an arrow marking the elevation's direction. That's how you know which wall the run belongs to.
- Read the units from left to right as the viewer of the elevation sees them. In the plan, check which wall end `a`
  sits on the viewer's left. If it's reversed, flip `side` or count `from` from the other end.
- The appliance table (Oven / Cooktop / DW / Micro, with OA = overall, CO = cutout) gives exact widths: `src: "drawing"`.
