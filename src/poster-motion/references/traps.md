# Traps

Each of these was hit while building or testing this skill, or an earlier beat-grid
film pipeline whose render path it reuses. Symptom first.

## Rendering

**`hyperframes render` fails: "Chrome cannot start ... --version (UNKNOWN)".**
On some Windows machines the native renderer cannot spawn its headless Chrome
(Windows Application Control, same family as the rembg DLL block). `snapshot --at` does
start Chrome, so `render.py` falls back to snapshotting every frame and encoding
once. Cost: about 1 s per frame, so a 60 s film takes around 30 min. Pass
`--snapshot` to skip the doomed native attempt, run it in the background, and
tell the user the ETA.

**You want to see the film before paying the half hour.**
`python render.py <project> --preview 36` snapshots 36 evenly spaced moments into
`preview.png` in about a minute. Read it, fix, then render.

**The video is black but previews fine.**
`dir="rtl"` on `<html>`. Direction is scoped in the CSS (`.say`, `.step-title` ...).

**The first half of the render is black.**
More than ~25 elements with `filter`, `blur()`, `clip-path` or `radial-gradient`.
This skill uses none: shadows are `box-shadow`, and textures are PNGs
(`pm_textures.py`). Keep it that way.

**The film opens on a sliver of empty frame.**
The beat grid's phase. `Grid.t(0)` is clamped to 0.0 in build_composition.py.
Never schedule the first shot at `phase`.

**`check` passes and the MP4 is still wrong.**
`check` validates the composition, not the file. `render.py` checks the file:
duration within 0.15 s, an audio stream, non-empty first and last frames.

## Composition

**Caption words run together ("מתפרקלשכבות") and numbers jump to the line end.**
Text and a `<span>` sitting directly in a flex container become separate flex items,
which drops the spaces between them and reorders them. The caption goes in ONE inline
`<span>` inside the flex strip (`compose_makingof.caption`).

**`content_overlap` errors on the split scene.**
The three layer cards start stacked, so their labels overlap until the fan-out.
The labels fade in after the spread. Do the same for any new stacked-then-spread scene.

**Contrast failure on kraft.**
`--red` on kraft measures 1.6:1. Red text on kraft uses `#6e1c10` when large (26px+ bold) and `#4f1208` when small; small ink text uses `#24190e`. The red fill
(stamps, tags with white text) is fine.

**Something jitters when seeking backwards.**
A loop (`drift`, `rope`) writing a transform the entrance also tweens. Loops go on
the INNER wrapper (`.obj-in`, `.acc img`, `.win-in`), entrances on the outer one.

**Motion differs between two renders.**
Nothing may depend on wall-clock time: no `Math.random` (use `PM.lcg(seed)`), no
`Date.now`, no `repeat: -1`, no CSS `@keyframes`. Loops are one proxy tween with
`ease: "none"`, mapped in `onUpdate`.

## Layers

**`import rembg` fails although pip lists it.**
Application Control blocks numba's DLLs. Not needed: `pm_models.py` uses onnxruntime directly.

**BiRefNet fails with "bad allocation" (onnxruntime GatherND).**
Out of memory. The 1024x1024 BiRefNet pass needs several GB of RAM. It failed while a
snapshot render (headless Chrome) was running in parallel. Run AI splits when nothing
heavy is running, or use `--lite`.

**The HuggingFace download dies with "connection reset" / curl exit 35.**
The CDN (`cdn.hf.co`) resets TLS handshakes intermittently on some networks. `download()`
retries 4 times, and a retry is usually enough. GitHub release downloads are unaffected.

**Coloured accents come out as faint smudges.**
Alpha ramps from half of `FG_DE`, masked to the coloured region (`_colour_region`).
The pink haze around watercolour butterflies is really in the poster.

## Paths and delivery

- Project folder segments ≤ 20 characters (`pm-idioms`, not the film title). The
  Hebrew title goes in the MP4 file name.
- `work/frames/` holds several GB of PNGs during a snapshot render. render.py deletes
  it after encoding. Never commit or deliver it.
