# Game mode: a photorealistic apartment you can walk around

Built on 09.10.2026 following Yuval Avidani's video: the quality of a 3D game comes from the **assets**, not the code.
The same `plan.json` feeds a second output, a multi-file Artifact with real materials, real furniture, light by time of day,
a view from the windows and game controls.

## Pipeline

```bash
python $SK/scripts/assets.py sync                                    # once per machine: Poly Haven into ~/.cache/floorplan-3d (~130MB)
python $SK/scripts/views.py <plan.json> -o <views> --city "Jerusalem" # Gemini: view per direction, day + night (~$0.10 per image)
python $SK/scripts/build_game.py <plan.json> -o <out> --tier high --views <views>   # 'lite' for phones
python $SK/scripts/check_game.py <out> --play                        # real GPU, doors/lights/finishes/walking, screenshots
python $SK/scripts/check_game.py <out> --play --phone                # iPhone emulation
```
Publish: `file_path=<out>/index.html`, `root=<out>`, `files=` the list in `publish-files.json`.
The `downloads` capability is needed to save photos (ask the user before declaring it).

## Artifact limits discovered in the spike (09.10.2026)

- **Served types:** `.js .json .jpg .webp .png .txt` are served. `.glb .hdr .bin` are refused at publish.
- **`fetch()` is unreliable:** v1 of the spike, loading with fetch, failed; v2, loading with `import()`, passed. So **nothing depends on fetch**:
  - **Models:** `<key>.gltf.js` = `export default <glTF JSON>`, with the buffer and the WebP textures embedded as data URIs.
    `loader.js` answers every `data:` URL from memory (a fetch shim), so GLTFLoader never reaches the network.
  - **HDRI:** `<key>.hdr.js` = `export default "<base64 Radiance>"` → `HDRLoader.parse`.
  - **Surface textures:** JPG via `TextureLoader` (`<img>`), which is proven to work.
- **n8ao imports `three/examples/jsm/...`.** It needs that mapping in the import map, besides `three/addons/`.
- **three-gpu-pathtracer imports `three/webgpu`.** It also needs `fflate` as an external if `viewer/export.js` is imported.
- **Budget:** 16MB per file, 64MB per publish. F1: high = 31MB, lite = 16MB.

## Engine (`assets/game/`)

| Module | Role |
|---|---|
| `loader.js` | fetch shim for data URIs, `loadHdr`/`loadModel` via import, `loadTextureSet` via img, real progress |
| `materials-pbr.js` | **the same keys** as `viewer/materials.js`, so all the viewer's geometry is built unchanged. Plaster and fabric = relief only (normal + roughness), with colour from the palette. Finishes swap live |
| `world.js` | the viewer's shell/cabinetry + Poly Haven models by `kind` (coffee table, plant, TV console, balcony set), ceiling lamp per room, ceilings cast shadows |
| `decor.js` | accent wall behind the sofa/bed by room type, original abstract art (seeded canvas), sheer curtains by the windows |
| `lighting.js` | sun from the hour plus Israel's latitude plus `meta.north_deg`. HDRI per part of day. **Indoor probe** (CubeCamera in the main room → PMREM = second bounce). Per-room lights. `bestHour()` = the hour the sun enters the main room |
| `outside.js` | ring of planes at 32m (real parallax), horizon at eye height, day/sunset/night |
| `render.js` | N8AO, bloom, SMAA, **Neutral** tone mapping (beat AgX/ACES by eye), saturation and contrast per part of day. Quality tiers with auto step-down only |
| `player.js` / `interact.js` / `hud.js` | Pointer Lock + WASD + Shift, head bob, closed doors block. Look+E: door / light / swap finish. Mini-map, clock, start screen (touch-specific instructions) |
| `photo.js` | **snapshot**: instant 4K at Ultra (the primary option). **takePhoto**: path tracer, experimental (see below) |

## Lessons (measured on F1, Intel Arc 140T)

- **Wall look:** a scanned plaster diffuse looks like dirty concrete. Take only its normal and roughness, with the colour from the palette.
- **Sofa and fabric colour:** a fabric diffuse multiplied by a colour = unexpected colour (red velvet × green = dark red). Same fix: relief only.
- **Auto-tune quality:** loading frames are cheap (62 fps) while real views run at 33-44. Only step quality down, never up.
- **Grade by time of day:** a colour boost that suits daytime burns out the night (warm lamps already saturate it). The grade changes with the hour.
- **Path tracer, interior lit through a window:**
  - **Grain:** after about 2.5 minutes it's still grainy.
  - **Glass:** transmissive glass turns direct sun into fireflies, so hide it during the photo.
  - **Fixes:** a firefly filter and DenoiseMaterial help, but it's not clean.
  - **Hence:** the 4K snapshot is the primary option.
- **AI views:** the night version as an edit of the day image keeps the scene identical. Zoom into the streets to check there are no people.
- **Performance:** at "high" 47-61 fps at 1080p on the Arc.
