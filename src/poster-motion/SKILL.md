---
name: poster-motion
description: >-
  Turn a series of still posters (ink lettering + an object on plain paper, e.g. illustrated
  Hebrew idioms) into a beat-synced motion-graphics film: posters are split into layers
  (ink, object, clean paper, colour accents), animated with GSAP in HyperFrames, cut on the
  music's beat, with an optional making-of opening. Posters can be supplied or generated
  with Gemini. TRIGGER on Hebrew: 'סרטון מושן מפוסטרים', 'תחיה את הפוסטרים',
  'תנפיש את הפוסטרים', 'מושן גרפיק מתמונות', 'פוסטרים מונפשים', 'סרטון ניבים מונפש',
  'תעשה מהתמונות האלה מושן'. English: 'animate these posters', 'poster motion video',
  'motion graphic from these images', 'bring these posters to life'. USE THIS for a SERIES
  of designed stills that should come alive layer by layer. NOT for event photo montages,
  sung kids clips, or free-form HyperFrames pieces with no posters.
---

# Poster Motion - פוסטרים שמתעוררים לחיים

Reverse-engineered from a sample film, "דוגמא מושיין" (Sep 2026, 720x900, 156s): seven Hebrew-idiom
posters (חתול בשק, לצאת מהקופסה, על קצה המזלג, על חבל דק, עוף מוזר, פרפרים בבטן,
פיל בחדר) animated layer by layer on an 87 BPM track, preceded by a making-of on kraft
paper. The pipeline here rebuilds that film from any poster series.

## The one idea

**A poster on plain paper is already a layer stack - the paper is the separator.** Estimate
the paper, and everything that departs from it is a layer: dark colourless strokes are ink,
small saturated shapes are accents, the rest is the object. Remove them all and repaint the
paper and you have the plate the film starts on. Then the film *builds the poster back*,
one layer per beat.

## Pipeline at a glance

```
posters/ ──► split_layers.py ──► assets/layers/pN/{poster,plate,ink,object,aK}.png + layers.json
                                         │                         + layers_sheet.png (LOOK)
music ────► beat_grid.py ──────► assets/music/beats.json (BPM, period, envelope)
                                         │
Claude ───► shots.json (step 4: archetype per poster - the creative step)
                                         │
            build_composition.py ──► index.html + bed.m4a (cut to the film) + fonts + textures
                                         │
            render.py ──────────────► MP4 in the delivery folder + renders_proof.png (LOOK)
```

All scripts live in `~/.claude/skills/poster-motion/scripts/` and take the project folder as
their first argument. Run them from that folder (`cd` there) - they import each other.

## Reference files (read the one you need)

| File | Read when |
|---|---|
| `references/motion-archetypes.md` | step 4 - writing shots.json. The full schema and every archetype |
| `references/layering.md` | the layer sheet looks wrong (ghosts, text in the object, missing accents) |
| `references/style-guide.md` | palette, fonts, pacing, what the reference film does shot by shot |
| `references/making-of.md` | part (a) is on - scene types, captions, placeholders |
| `references/poster-generation.md` | no posters were supplied - writing poster_brief.json |
| `references/traps.md` | before rendering, and whenever a render looks wrong |

## Ordered workflow

### 0. Preflight + discovery
Run `python preflight.py` once per machine. It lists anything missing (Python packages,
ffmpeg, Node) in Hebrew, with the install command for each.

Then ask once, in one AskUserQuestion:
- Posters: a folder of images, or only a topic? (topic → step 1)
- Making-of opening: yes / no (default no)
- Aspect: 4:5 (default, WhatsApp/Instagram), 9:16 (Reels/Status), 1:1
- Music: one of the bundled tracks (`sneaky` default, `investigations`, `riley`, `duck`,
  `carefree`, `monkeys` - all Kevin MacLeod CC BY), or a file/URL the user brings
- Delivery folder + a Hebrew file name (the file name matches the film's title)

Project folder: short name under the delivery folder, e.g. `<delivery>\pm-idioms\`
(path-length rule: segments ≤ 20 chars). Copy posters into `<project>\posters\` as
`p1.png, p2.png ...` in the order they should play.

### 1. Posters (only when generating)
Write `<project>/poster_brief.json` (see `references/poster-generation.md`), then
`python generate_posters.py <project>`. Build a contact sheet and **read every poster's
Hebrew letter by letter** - redo misspelled ones with `--only pN`. Show the user the sheet
and get approval before step 2: everything after this is built on these pixels.

### 2. Layers
First time on a machine: `python setup_models.py` (≈430 MB, CPU-only, no torch).
Then `python split_layers.py <project> [--aspect 9:16]`. It uses AI when both models are
present and falls back to OpenCV (`--lite`) otherwise, saying which in `layers.json`.
**Read `layers_sheet.png`** (poster | plate | ink | object per row). Fix problems here, not
in the composition - `references/layering.md` maps each symptom to the constant to change.

### 3. Music
`python beat_grid.py <project> --track sneaky` (or `--track "C:\...\song.mp3" --name ...
--credit "..."`). Prints BPM; outside 78-135 per minute it warns - pick another track.

### 4. Shots - the creative step
`python build_composition.py <project> --draft` writes a rule-based `shots.json`. Now look
at `layers_sheet.png` next to it and **rewrite it as a director**: which lettering should
slam in (stamp) and which should be written (write), which object rises and which enters
from the edge it is cut by, which ink group is a feather that should float
(`drift_words`), where the text waits for the object (`text_at`). Give the whole film a
title. Schema and archetypes: `references/motion-archetypes.md`.

### 5. Compose
`python build_composition.py <project> [--making-of]` then from the project folder
`npx --yes hyperframes@0.8.81 check`. Errors must be zero. Contrast failures on kraft use
the dark red `#6e1c10`, never `--red`.

### 6. Preview, then render
First `python render.py <project> --preview 36`, which writes `preview.png` in about a minute.
**Read it.** Fix whatever is wrong and rebuild. Only then render the MP4:
`python render.py <project> --out "<delivery>\<Hebrew title>.mp4"`.
- It tries the native renderer first. On some Windows machines (Application Control policies) that renderer cannot start Chrome. Once you have seen it fail, pass `--snapshot` to skip the attempt.
- It then falls back to per-frame snapshots at about 1 s per frame. Run it in the background and tell the user the ETA.
- When it finishes, it checks the duration, the audio, and that the first and last frames are not empty.

### 7. Verify + deliver
Read `renders_proof.png` (24 frames across the film). Check: every poster finishes whole
(no missing word), no text ghost on a plate, cuts land on the music, end card credit is
there. Report the file path, length, BPM, and any poster that fell back to `--lite`.

## Escalation points (ask the user)
- The layer sheet shows a poster that cannot separate (text painted over a photo, busy
  background): offer to animate it as one piece (camera push only) or to drop it.
- Generated Hebrew still misspelled after 3 tries.
- A user-supplied track has no license information - ask before using it.

## Anti-patterns
- Hand-editing `index.html` - it is generated; change shots.json or the scripts.
- Skipping the two LOOK steps (layer sheet, proof sheet). `hyperframes check` passed on
  films that opened on empty frames.
- Inventing numbers in the making-of - every figure comes from the run.
- `Math.random`, `repeat: -1`, CSS keyframes, `dir="rtl"` on `<html>` (see traps.md).
- Adding filter/blur/clip-path/radial-gradient elements - the snapshot renderer goes black.

## Definition of Done
- [ ] Every poster's `layers_sheet.png` row read and accepted
- [ ] `shots.json` hand-directed (not the raw draft), with a title
- [ ] `hyperframes check`: 0 errors
- [ ] `render.py` exits 0 (duration, audio, bookends verified)
- [ ] `renders_proof.png` read; delivered file name is descriptive Hebrew
- [ ] Music credit on the end card when the license requires it

## Credits & References
- Reference film: "דוגמא מושיין", a 156 s making-of + idiom-poster motion film
- Models: BiRefNet (ZhengPeng7, via rembg's ONNX export), LaMa (advimman, ONNX by Carve)
- Music: Kevin MacLeod, incompetech.com, CC BY 4.0
