---
name: floorplan-3d
description: |
  Turn architectural drawings (an apartment floor plan, plus elevations/sections for a kitchen or other millwork) into an interactive, shareable 3D model: a single-file Artifact with a 2D-to-3D reveal, dollhouse view, elevations, a first-person walk, dimensions tagged "from the drawing" vs "estimated", rooms/areas, finishes, architect notes, A/B variants and GLB export. Claude reads the sheet, optional OpenCV snaps the geometry, reconcile.py proves it.
  TRIGGER on Hebrew: "תוכנית דירה לתלת מימד", "תהפוך תוכנית לתלת מימד", "מודל תלת מימד מהתוכנית", "תשריט לתלת מימד", "הדמיית מטבח מהחזיתות", "סיור וירטואלי בדירה", "הדמיה של הדירה".
  English: "floor plan to 3D", "3D model from floor plan", "kitchen from elevations", "virtual tour of the apartment", "dollhouse view".
  USE THIS when the input is an architectural drawing (PDF/JPG/PNG) and the output is a 3D model or walkthrough. NOT for generic Three.js scenes (threejs-viewer), NOT for marketing videos (epic-video-studio).
---

# floorplan-3d

From drawings to a 3D model you can send as a link, for two audiences at once:
- **Presentation mode** (for buyers): the drawing lies flat, the walls rise out of it, then a dollhouse view with furniture, a guided tour, a walk, and finishes.
- **Work mode** (for the architect): dimensions tagged by source, wall IDs, measurement, the drawing as an underlay, notes and open questions, A/B alternatives, GLB/PNG/JSON export.

The working principle: **Claude decides what exists, the CV decides where it is exactly, and the dimension strings decide who's right.** Every number in the model is tagged `drawing` (from the drawing) or `estimated` (an estimate). Nothing is invented without a tag.

## Paths and tools

```
SK = ~/.claude/skills/floorplan-3d
scripts/pipeline.py     single entry point: start / check / build / status (chains everything below)
scripts/prepare.py      render the sheet + PlanWalk (if installed) + overview/tiles with a grid
scripts/zoom.py         zoom with a coordinate grid / set origin / calibrate the scale from a dimension string
scripts/overlay.py      draw plan.json over the sheet for a visual check
scripts/reconcile.py    vision + CV merge, schema validation, areas, dimension strings, reachability, joinery
scripts/build_viewer.py build a single HTML file (Artifact) from one plan.json or several (alternatives)
scripts/check_viewer.py desktop + iPhone check in a real browser, with screenshots
scripts/runs.py         expand cabinet runs and islands into boxes (shared by the overlay and the viewer)
scripts/assets.py       game mode: Poly Haven (CC0) into a cache, exported in formats the Artifact serves
scripts/views.py        game mode: Gemini view from each window (day + night)
scripts/build_game.py   game mode: a multi-file Artifact folder (high/lite)
scripts/check_game.py   game mode: real GPU, frame rate, doors/lights/finishes/walking, phone
references/plan-format.md   the plan.json format + extensions (runs/islands/fixtures/dimensions/notes)
references/reading-plans.md how to read an Israeli drawing correctly + traps already discovered
references/viewer-guide.md  the viewer's architecture, adding an item kind, Artifact limits
references/game-mode.md     game mode: pipeline, Artifact limits (no fetch!), engine, lessons
examples/demo-a.plan.json, demo-b.plan.json   synthetic plan (island vs. dining table) for testing
```

PlanWalk (the OpenCV engine) is optional: `~/Documents/דירות בתלת מימד`, or `FLOORPLAN3D_PLANWALK`.
`FLOORPLAN3D_NO_PLANWALK=1` forces vision-only mode. Requirements: Python with PyMuPDF and Pillow, Node 18+ (npx esbuild), and Python Playwright for the check.

## The short path (one entry point)

```bash
python $SK/scripts/pipeline.py start "<plan.pdf>" --scale-ratio 50      # prepare the sheet (+ PlanWalk), work folder next to the source
#   <- here Claude reads the sheet and writes <work>/vision.plan.json (step 2 below)
python $SK/scripts/pipeline.py check "<work>"                           # reconcile + overlay; repeat until clean
python $SK/scripts/pipeline.py build "<work>" --game --views --city "<city>"   # viewer + game + all checks
python $SK/scripts/pipeline.py status "<work>"                          # where we are and what comes next
```
`build` writes `<work>/out/publish.json` with exactly what to pass to the Artifact tool (viewer: a single file; game: `root` + `files`).
Before publishing, open the screenshots in `out/checks-*`. The detailed stages are below, for when something needs fixing.

## Workflow

### 0. Collect inputs and decide the scope
- **Floor plan** = apartment level. **Elevations/sections** (`חזית A`, `חתך HH`) + an appliance table = room level (kitchen/bathroom/joinery). Both together = both levels in one model.
- Work folder next to the source, **with a short path** (Windows 260-character limit: keep each segment ≤20 characters): `<source folder>\3d-<short name>\`.
- Drawings may contain addresses and client names. The Artifact is private by default; **don't copy a real client's drawing into `examples/`**.

### 1. Prepare the sheet
```bash
python $SK/scripts/prepare.py "<plan.pdf>" "<work>" --scale-ratio 50 [--page N] [--dpi 200]
```
Look at `overview.png` first, then `tiles/`. Identify:
- the title block (title, date, floor, unit number);
- the scale;
- the stated apartment area (`שטח X מ"ר`);
- the legend (concrete vs. block walls);
- the north arrow;
- dimension chains;
- room names.

`--scale-ratio` always when a scale is printed (exact). Without PlanWalk: `zoom.py --calibrate PX0,PY0,PX1,PY1,CM` from a reliable dimension string, then `--set-origin` at a corner of the footprint.

### 2. Read the plan into `vision.plan.json`
Format: [references/plan-format.md](references/plan-format.md). Traps: [references/reading-plans.md](references/reading-plans.md).
- **With CV** (there is a `cv.plan.json`): start from a copy of it and **curate it**:
  - delete false walls (fixture edges, pipes, neighbouring units);
  - add missing walls;
  - correct door vs. window;
  - split merged rooms (the living room swallows the kitchen and hallway);
  - drop "rooms" outside the apartment.

  Copy coordinates from the CV, which is accurate to the centimetre on main walls.
- **Without CV**: coordinates **from the grid lines** in `zoom.py` (labels sit on top of their line), down to 10 cm. Better still, sum dimension chains from a known corner.
- Rooms run to the **inner faces** of the walls (net area). Mark `entrance: true` on the entrance door.
- Every dimension string you read goes into `dimensions[]` with endpoints **on the geometry** (wall faces), not at the ends of the dimension line. That turns it into a real check.
- A wall whose position was set from dimension strings gets `"src": "drawing"`, which locks it against snapping.

### 3. Prove it: reconcile + overlay (usually 2-4 rounds)
```bash
python $SK/scripts/reconcile.py "<work>"     # -> plan.json + reconcile.md   (0 = clean, 2 = warnings, 1 = invalid)
python $SK/scripts/overlay.py "<work>"       # -> overlay_plan.png, open it and look
```
Go through every warning:
- **Fix it:** a real error (a wall off the ink, a room spilling over, an unreachable room).
- **Dismiss it:** a CV "missed wall" that is really a fixture edge or a pipe.
- **Turn it into a note:** an unresolved discrepancy (a dimension string doesn't match the geometry) becomes a `notes[]` entry with `kind: "question"`, plus `"known": "<note id>"` on the dimension. **Never hide a discrepancy.**
- **Dismiss a CV line:** after checking on the overlay, add `checks.dismiss_cv`. Exit 0 = everything clean or acknowledged, and the acknowledged items stay listed in the report.

### 4. Room level: joinery from the elevations (when there are elevations)
In each elevation, read the units from left to right as the viewer sees them.
- **Placement:** each run is a wall + a side + `from`.
- **Items:** units with widths, plus `kind` (cabinet/drawers/sink/cooktop/dishwasher/oven/fridge/tall/oven_tower/pantry/gap).
- **Uppers:** `upper` with `upper_z`/`upper_h`.
- **Label:** `label` = the elevation letter ("מטבח · חזית B").
- An island goes into `islands[]` with stools; free-standing items go into `fixtures[]`.
- `src: "drawing"` only for a width that is actually written on the sheet. Everything else is `estimated`.
- The viewer builds an elevation camera for every run automatically.

### 5. Build and check
```bash
python $SK/scripts/build_viewer.py "<work>/plan.json" -o "<out>/<שם>.html" --work "<work>" --preview
python $SK/scripts/build_viewer.py "חלופה א=a.json" "חלופה ב=b.json" -o ... # alternatives
python $SK/scripts/check_viewer.py "<out>/<שם>.preview.html"              # desktop + iPhone, 0 errors required
```
Open the screenshots from `checks/` (overview, elevation, walk, phone) and look at them. `--work` embeds the drawing (the reveal plus the "שרטוט" (drawing) layer).

### 6. Deliver
- Publish the `.html` (not `.preview.html`) as an Artifact. Use `icon: "home"` and `capabilities: {downloads: true}`, so GLB/PNG/JSON export goes through the viewer's confirmation dialog.
- In the reply:
  - the link;
  - a rooms and areas table (net vs. the stated area);
  - the discrepancies that became notes;
  - what is `estimated`.
- **Changes in plain language** ("move the wall 40 cm", "change to a wider island", "add alternative B"):
  1. edit `vision.plan.json`;
  2. reconcile;
  3. build;
  4. republish **to the same file**, which keeps the same link.

### 7. Game mode (optional): photorealistic and walkable
When the user wants "a real visualization", "like a computer game", or "to walk around the apartment", run it on the same `plan.json`:
`assets.py sync` → `views.py` (shows the cost first) → `build_game.py --views` → `check_game.py --play` (+`--phone`).
- **What it has:** scanned materials, real furniture, sun by the clock with the "best light" hour, a city view from the windows, WASD/mouse/E, and a 4K capture.
- **Details:** [references/game-mode.md](references/game-mode.md).
- **Assets:** CC0 only (Poly Haven), plus original art generated in code, plus AI views with no people (the AI Images rule).
- **City:** the view's city is an input. Don't guess it; ask, or say what was assumed.

## Practical
- **Zooms:** `zoom.py` writes to `<work>/zooms/` (`-o name.png` sets the name).
- **Encoding (Windows):** read JSON with `encoding="utf-8"` or set `PYTHONUTF8=1`. Otherwise cp1255 breaks on Hebrew.
- **Slow checks:** `check_viewer.py` takes about 3 minutes (two devices, software rendering) and `check_game.py` about 1-2 minutes.
  Run them in the background (`run_in_background`), not with a 120-second timeout.
- **`--tier lite`:** this is about smaller assets, and rendering on that tier also starts at "lite".

## Rules
- **The dimension string outranks the ink and the eye.** Rough reading from a grid drifts by about 15 cm. Measured on F1: CV +-1 cm against free-eye reading +-15 cm.
- A number without a source = `estimated`. A sheet with no ceiling height = an `assumption` note.
- Never report "matches the drawing" without reconcile at exit 0, or with every warning explained in the reply.
- Never publish a page that `check_viewer.py` failed on.
- The viewer is single-file: no external textures or models (CSP), and stays under 16MB (see viewer-guide).
