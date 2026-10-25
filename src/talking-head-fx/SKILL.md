---
name: talking-head-fx
description: >-
  20 viral-reel effects on real footage of a person talking to camera, aimed at the face and
  timed to the words: punch/jump/dolly/camcorder zooms, face portal, glass lens, frame break,
  pop-up checklist, headline ribbons, the video inside a chat card/phone/editor, head breaking
  out of a frame, cut-out speaker on green screen/studio/paper/magazine/growth chart, recap,
  plus karaoke captions. Plans effects from speech cues, builds a HyperFrames project.
  TRIGGER on Hebrew: "תוסיף אפקטים לסרטון", "תערוך את הסרטון שלי", "אפקטים כמו בריל",
  "זום על הפנים", "סרטון שאני מדבר למצלמה", "כתוביות ואפקטים", "עריכה ויראלית", "רילס",
  "שורטס". English: "add effects to my talking-head video", "edit my reel", "punch-in zooms".
  USE THIS whenever the footage shows a person speaking, whole video or a segment inside a
  HyperFrames project (load after `hyperframes`). NOT for generated videos without camera
  footage, NOT for event b-roll montages (event-recap-video).
---

# talking-head-fx: viral effects on talking-head footage

Turns a raw clip of someone talking to camera into an edited reel. The effects are aimed at
the face and timed to the words. The catalog of all 20 effects, with params and when to use
each one, is in [references/effects.md](references/effects.md). Read it before planning.

**Stack:** HyperFrames (HTML + GSAP) with a small runtime in `assets/runtime/`. Python
scripts handle the analysis: OpenCV face track, faster-whisper words, and
`npx hyperframes remove-background` for cut-outs. All of it is local, with no API keys.

## When it applies

- The footage shows a person speaking (selfie, webcam, interview, lecture). Vertical works
  best. Landscape works, but a 9:16 crop of a 16:9 webcam is tight and soft; offer
  `face-track-reframe` first, or keep a 16:9 canvas.
- **Inside another workflow:** when a `hyperframes` project (talking-head-recut,
  embedded-captions, general-video) has a speaker segment, use this skill's runtime for that
  segment instead of hand-building zooms.

## Workflow

Scripts live in `~/.claude/skills/talking-head-fx/scripts/`. Work in a scratch or project
folder with an **ASCII path**, because headless rendering breaks on Hebrew paths. Copy the
footage there first.

```bash
S=~/.claude/skills/talking-head-fx/scripts   # PowerShell does not expand ~ in quotes: resolve it once with
                                             # python -c "import os;print(os.path.expanduser('~/.claude/skills/talking-head-fx/scripts'))"
python $S/preflight.py                                             # 0. once per machine: what is missing, in Hebrew
python $S/transcribe.py talk.mp4 -o words.json --lang he          # 1. words (skip if you have them)
python $S/face_track.py talk.mp4 -o face.json                      # 2. face position over time
python $S/plan_fx.py words.json -o fx_plan.json --pacing reel     # 3. DRAFT plan
#    -> review and edit fx_plan.json, show the table to the user (see below)
python $S/matte_segments.py talk.mp4 --plan fx_plan.json --out subjects   # 4. only if matte effects
python $S/build_project.py --footage talk.mp4 --plan fx_plan.json --face face.json \
       --words words.json --subjects subjects --out reel                  # 5. HyperFrames project
cd reel && npx hyperframes check                                          # 6. must pass
npx hyperframes snapshot --at <midpoint of every effect>                  # 7. look at every frame
npx hyperframes preview --background   # then render after approval:
npx hyperframes render --quality high --output reel.mp4   # CLI 0.7.x: draft|standard|high (0.8+: delivery)
```

### Step 3: reviewing the draft plan (this is where the quality comes from)

`plan_fx.py` matches cues and enforces pacing. It cannot write good on-screen text. For every
effect:

1. **Read the `why`** and the words around it in `words.json`. Keep it only if the effect
   *illustrates* that moment. A cue match alone is not enough.
2. **Rewrite params in natural Hebrew:**
   - checklist `items`: 2-4 words each, what the speaker actually lists
   - `headline_storm` `lines`, the chat `prompt`, the `magazine_cover` `masthead` and
     `lines`, `growth_chart` `from`/`to`/`suffix` (the real number said)
   - `recap_checklist` `items`
3. **Pacing** (the script enforces it; keep it when you edit):
   - Hook: an effect in the first ~1.5 s.
   - Reels: something changes every ~3 s. Long-form: an effect every 10-20 s, mostly camera
     moves.
   - No two heavy effects (frames and backgrounds) within 5 s in a reel.
   - Never the same effect twice in a row. Effects never overlap (`title` may).
   - Matte effects are the most striking and the most expensive: about 3-4 per minute in a
     reel, about 1 in long-form.
4. Use `title` for numbered tips ("טיפ 2"), `progress` for listicles, and `theme` for the
   brand colors (ask for them once if the user has a brand).
5. **Show the user a table** (time, effect, Hebrew name, what is on screen, why) and get
   approval *before* matting and rendering. Approval comes in stages: approve the plan as a
   table, then the snapshots, then the render.

### Step 7: verification

- `check` must end with `Check passed`. Layout `info` items about ribbons are expected.
  Contrast findings over moving footage are informational, but fix any text that is
  actually hard to read.
- Snapshot the **midpoint of every effect** and open the contact sheets. Check that:
  - zooms land on the face, the portal shows the whole face, and the escaping head lines up
    with the body inside the frame
  - cut-outs have clean edges, with no straight crop edges in mid-canvas
  - no text is hidden under the progress bar
- After rendering, `ffprobe` the duration and confirm the audio stream exists. Then pull 3-4
  frames from the MP4 at effect midpoints and look at them.

## Limits and gotchas

- **Face tracking** uses Haar cascades. A strong profile view or a covered face falls back to
  the last known position. `face.json` reports `found`; under 50%, aim effects manually
  (edit the samples, or avoid face-aimed effects).
- **Matting:** `u2net_human_seg` runs on CPU (~168 MB of weights downloaded on first run).
  Only the effect windows are matted. Hair and fast hands can have soft edges; `--quality best`
  is for masters.
- **A soft source stays soft:** webcam autofocus blur is in the footage. Zooms magnify it,
  so prefer `dolly_zoom` and lower `zoom` values on soft clips.
- `matte_segments.py` names cut-outs by effect index (`subject_<i>.webm`). After you add or
  remove effects, re-run it so the indices match. It skips files that exist, so pass
  `--force` when timings changed.
- Fonts: Rubik Bold ships in `assets/runtime/fonts` and covers Hebrew and Latin. A brand font
  needs an `@font-face` with a local file (a HyperFrames lint rule).

## Files

| Path | What |
|---|---|
| `scripts/preflight.py` | readiness check: Python modules, ffmpeg, Node, hyperframes CLI |
| `scripts/transcribe.py` | faster-whisper → `words.json` `[[text,start,end],...]` |
| `scripts/face_track.py` | OpenCV face track → `face.json` (normalised `[t,cx,cy,size]`) |
| `scripts/cues.py` | **When each effect fires:** cue words, scores, durations, pacing presets |
| `scripts/plan_fx.py` | words → draft `fx_plan.json` with a `why` per effect |
| `scripts/matte_segments.py` | cut-outs for matte effects only (`npx hyperframes remove-background`) |
| `scripts/build_project.py` | scaffolds the HyperFrames project and writes `index.html` |
| `assets/runtime/thfx-core.js` | layers, face → canvas mapping, effect dispatch, shared helpers |
| `assets/runtime/fx-camera.js` / `fx-frames.js` / `fx-matte.js` / `fx-overlay.js` | the effects |
| `assets/runtime/thfx-text.js` | karaoke captions, `title`, progress bar |
| `assets/runtime/thfx.css` | all styles; theme tokens `--fx-*` |
| `references/effects.md` | catalog, params, global options, how to add an effect |
