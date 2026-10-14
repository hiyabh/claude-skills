---
name: threejs-viewer
description: >-
  Build an interactive 3D scene with Three.js and show it as a live page (Artifact) the user can rotate, zoom
  and control with sliders, play/pause and speed buttons. The Claude Code equivalent of the Claude Desktop
  in-chat 3D viewer. Use for 3D visualizations, simulators, interactive explainers and "teach me X visually"
  requests. TRIGGER on Hebrew: "תמחיש לי בתלת מימד", "תראה לי בתלת מימד", "סצנה תלת ממדית", "הדמיה תלת ממדית",
  "מודל תלת ממדי", "סימולטור", "סימולציה תלת ממדית", "תבנה לי בתלת מימד", "ThreeJS", "טרי ג'יי אס", "3D viewer".
  English: "show me in 3D", "3D visualization", "interactive 3D", "three.js scene", "3D simulator", "build a 3D
  model of". NOT for rendered video (use `three` with HyperFrames), NOT for scroll-driven website heroes (use
  `threejs-scroll-cinema`), NOT for 2D charts (use `dataviz`).
---

# Three.js Viewer

Interactive 3D in a page: the viewer drags to orbit, scrolls or pinches to zoom, and uses a Hebrew RTL control panel
with play/pause, a timeline, speed buttons (×1/×2/×4/×8), sliders, toggles and live readouts. The output is one
self-contained HTML file published as an Artifact.

## Files

| File | Purpose |
|---|---|
| `assets/scene-template.html` | Generic engine + panel. **Never edit per scene.** The scene block between `// @@SCENE-BEGIN` and `// @@SCENE-END` is replaced. |
| `scripts/new_scene.py` | Injects a scene file into the template, sets `<title>`, validates required declarations, runs `node --check`. |
| `examples/f16-pattern.scene.js` | Full worked example: F-16 takeoff, pattern and landing (route curve, speed profile, physical bank angle, afterburner, Sky/sunset). Read it before writing a vehicle or motion scene. |
| `references/recipes.md` | Building blocks: models from primitives, fire/glow, sky and sunset, paths, labels, explainers, performance. |
| `references/gotchas.md` | Artifact CSP limits, import map, coordinate conventions, testing traps. |

## Workflow

1. **Break the request into three parts.** *Model*: what geometry, built from primitives (no external model files,
   see gotchas). *Motion*: what changes over time, written as a function of `t`. *Controls*: which 2-5 parameters the
   viewer will want to change, and which 2-4 numbers deserve a live readout. Use real units and real proportions
   (metres, knots, degrees). That is the detail that makes the scene feel true.
2. **Write the scene file** in the scratchpad (`<name>.scene.js`). Copy the shape of the template's default scene or of
   the F-16 example. Required declarations (the script checks for them):
   - `META` `{ title, subtitle }`: Hebrew. The subtitle says how to interact.
   - `TIMELINE` `{ duration, loop, speeds, speed }`, or `null` for a scene with no timeline (ambient motion only).
     `buildScene` may overwrite `duration` (the F-16 example computes it).
   - `CONTROLS`: an array of `{ id, type: 'range'|'toggle'|'select', label, value, ... }`. Range takes `min, max, step, unit`.
     Select takes `options: [[value, label], ...]`.
   - `READOUTS`: an array of `{ id, label, unit? }`, updated with `ctx.readout(id, text)`.
   - `INFO`: an HTML string for the explainer section (`''` = hidden). For learning requests, this is where the explanation goes.
   - `CAMERA`: `{ position, target, fov, near, far }`.
   - `buildScene(ctx)`: builds the scene and returns `state`. `ctx = { THREE, scene, camera, renderer, controls, params, timeScale, readout, follow, unfollow, resetView }`.
   - `update(ctx, state, t, dt)`: runs every frame. **Derive positions from `t`** so that scrubbing the timeline works.
     Use `dt` only for accumulating effects. `dt` already includes the speed button and `ctx.timeScale`.
   - `onParam(ctx, state, id, value)`: reacts to a control change. Rebuild geometry only here, never in `update`.
   - Extra addons are imported at the top of the scene file: `import { Sky } from 'three/addons/objects/Sky.js';`
3. **Build**: `python ~/.claude/skills/threejs-viewer/scripts/new_scene.py <scene.js> <out.html> --title "<name>" --preview`.
   The title is a 2-4 word name, not a sentence.
4. **Check once in a browser** (Playwright): serve the folder with `python -m http.server <port> --bind 127.0.0.1`
   (run in the background), open `<out>.preview.html`, and save the screenshot under the workspace's `.playwright-mcp/`.
   Confirm that the scene renders (not the fallback box), that the console has no errors except `favicon.ico`, and that
   `window.__viewer` (`{ clock, ctx, state }`) works: set `__viewer.clock.t` to test a mid-timeline moment. Fix what you
   see in one pass. Do not loop.
5. **Publish** `<out>.html` (not the preview file) with the `Artifact` tool: `icon: "cube"` and a one-sentence Hebrew
   `description`. Load `artifact-design` first if it is not loaded yet. If the Artifact tool is unavailable, open the
   preview file in the default browser (`start "" "<path>"`) and say so.
6. **Reply** with the link and 2-3 short lines in Hebrew on what to try ("הזיזו את המצערת מעל 85%...").

## Rules

- RTL Hebrew UI comes from the template. Write labels, `INFO` and readouts in Hebrew. Units stay in their normal form (ft, kt, °, m/s).
- The panel follows the viewer's light or dark theme on its own. The 3D scene sets its own background (sky, fog,
  `scene.background`) or leaves the canvas transparent so the page token shows through.
- Every scene has to look right in its first frame: something visible, lit and framed by `CAMERA`, with sensible default control values.
- Keep the scene file readable: named constants instead of magic numbers, functions of 30 lines or fewer, one builder function per part.
- Facts shown in `INFO` or readouts (physics, specs, history) must be correct. If unsure, phrase it as "בהדמיה הזו...".
- Three.js version: the import map pins `three@0.186.1` (verified 2026-10-08). Before bumping it, check `npm view three version` and that `build/three.module.js` and `examples/jsm/` still exist on jsdelivr.
