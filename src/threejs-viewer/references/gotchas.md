# Gotchas

## Artifact sandbox (CSP)
- Scripts and ES modules load only from `cdn.jsdelivr.net/npm/`, `cdnjs`, `unpkg`. The import map points `three` and
  `three/addons/` at jsdelivr, so addons work. `esm.sh` and any other host are blocked silently.
- **No fetch of external assets**: GLTF models, textures and HDRIs from the web will not load. Build from primitives,
  generate textures on a `<canvas>` (`CanvasTexture`), or embed small assets as `data:` URIs (16MB page limit).
- No `alert` or `confirm`, no downloads, no `window.print`. All UI lives in the page.

## Template
- The published file must **not** start with `<!doctype>`/`<html>`. The Artifact skeleton wraps it. `--preview` adds
  a doctype only to the local `.preview.html`. Never publish the preview file.
- `[hidden] { display: none !important }` is in the template on purpose. Without it, any element with its own
  `display` ignores `hidden` locally (the Artifact skeleton has it, a plain browser does not).
- Import declarations inside the scene block are fine. ES modules allow `import` anywhere at top level.
- `const` declarations in the scene block are in the TDZ until it runs, and the engine comes after it. Do not reference
  engine helpers (`$`, `clock`) from top-level scene code. Use `ctx` inside the functions.

## Three.js
- `Object3D.lookAt` points the object's **+Z** at the target (a camera points −Z). Build models nose-forward on +Z.
- `THREE.Clock` is deprecated in recent releases. The engine uses the `setAnimationLoop` timestamp.
- `ExtrudeGeometry` fixes winding for you, so a mirrored point list extrudes correctly.
- On the runway or ground, zero the tangent's y before `lookAt`, or Catmull-Rom wobble tilts the object.
- `controls.maxPolarAngle = Math.PI / 2 - 0.02` keeps the camera above the ground plane.

## Testing
- Playwright screenshots must be saved under the workspace (`.playwright-mcp/...`). Paths in the scratchpad are refused.
- `file://` pages cannot load modules in some setups. Serve the folder with `python -m http.server`.
- The only expected console error is `favicon.ico` 404 from the local server.
- Portrait phones: the engine widens the vertical FOV when the screen is in portrait (capped at 80°) and starts with
  the panel collapsed under 640px. Frame `CAMERA` for landscape.
