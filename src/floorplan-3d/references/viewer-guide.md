# The viewer: architecture and extension

`assets/viewer/` holds ES modules that `build_viewer.py` bundles with esbuild into one module inside `template.html`.
three.js (0.186.1) and fflate (0.8.3) come from jsdelivr through an importmap and are left out of the bundle.
The plan data sits embedded in `<script type="application/json" id="plan-data">`.

| Module | Role |
|---|---|
| `main.js` | App: renderer, light, environment, building a variant, views, guided tour, walk, layers, finishes, export, frame loop |
| `util.js` | `P(x,y,z)` plan->three (z=-y), `Spring`/`SpringVec3` (with sub-steps), geometry helpers |
| `materials.js` | canvas textures (wood, veneer, tile, speckle) + finish presets (floor/fronts/countertop) |
| `shell.js` | walls split around openings (sill/lintel), windows, hinged/sliding doors, railing, floors, ceilings, underlay |
| `parts.js` | box/cylinder/rounded/seam/handle |
| `cabinetry.js` | joinery and bathroom by kind/tier -> `buildItem` (falls through to furniture for unknown kinds) |
| `furniture.js` | furniture meshes |
| `autofurnish.js` | automatic furniture per room type: candidate sides, door swing zones, no overlaps |
| `camera.js` | `CameraRig` (OrbitControls + springs, cancelled by any input), `WallCutter` (dollhouse), `deriveViews` |
| `walk.js` | first person: grab-the-world drag, WASD, a joystick, collision in sub-steps |
| `labels.js` | HTML labels: rooms / items+chip / dimension lines / wall IDs / notes. Distance limits, overlap avoidance, wall occlusion |
| `measure.js` | measure between two points |
| `reveal.js` | opening: the drawing -> walls rising on a spring -> furniture |
| `ui.js` | toolbar, modes, side panel (rooms/finishes/notes/alternatives/export), captions, states |
| `export.js` | GLB (a ZIP inside an Artifact; `.glb` isn't on the allowed list), PNG, plan.json; through `claude.use('downloads')` or `<a download>` |

## Adding an item kind
1. In `cabinetry.js` (joinery/bathroom) or `furniture.js` (furniture), add a function to the matching table.
   Local frame: +X = width, +Y = up, +Z = the front. Use `parts.js`.
2. If it should block walking: by default every item with z<1.2 blocks (except rugs and countertops).
3. Document it in `plan-format.md`.

## Design (Apple/Fluid)
- **Camera:** every camera move is a critically damped spring, starting from the current position. Any drag/zoom cancels a flight.
- **Dollhouse cut:** exterior walls facing the camera drop to 1.05, and interior walls in the overview drop to 2.1.
- **Labels:** item and dimension labels appear only when you get close (6.5 / 10 m), as progressive disclosure.
- **Reduced motion:** with `prefers-reduced-motion`, no reveal and no flights (it jumps), and the CSS drops its movement.
- **RTL:** logical properties throughout. The toolbar scrolls sideways on a phone, with a fade at its end.

## Artifact limits
- Scripts only from jsdelivr/cdnjs/unpkg; no fetching external models or textures.
- The published file has no doctype (the `--preview` file gets one, for local use only).
- 16MB limit. A 2048px JPEG underlay ≈ 400KB, the whole page ≈ 550KB.
- Downloads go through `capabilities: {downloads: true}`; the viewer confirms each file.

## Testing
`check_viewer.py` = headless Chromium (software rendering, ~1-5 frames per second):
- **Devices:** desktop plus iPhone emulation.
- **Steps:** it waits for `reveal`/`flying` to settle after each step.
- **Pass condition:** any console error fails the run.

Springs and walking run in sub-steps, so a slow frame rate doesn't change the result (the walk tunneling bug was found exactly that way).
`window.__viewer` is exposed for tests: `goView(id)`, `enterWalk()`, `ui.setMode('work')`, `views`, `labels.entries`.
