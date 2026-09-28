# Making-of - part (a)

Enabled by `"making_of": {"enabled": true}` in shots.json, or `--making-of` on
build_composition.py. Code: `scripts/compose_makingof.py`.

## The rule

**Every number on screen is real.** Placeholders are filled from the run:

| Placeholder | Value |
|---|---|
| `{N}` | number of posters in the film |
| `{L}` | layers produced (plate + ink + object + accents, all posters) |
| `{BPM}` | the grid tempo from beats.json |
| `{F}` | frames in the finished film |
| `{FPS}` | 30 |

The code window types the **actual GSAP** of the film's first shot, and the waveform is
the bed's real loudness envelope. If you add a scene that shows a number, compute it -
never type one in.

## Scenes

A scene: `{"type": ..., "beats": n, "say": "caption with one *red* word"}`.

| type | Shows | Extra fields |
|---|---|---|
| `prompt` | Claude Code window, the prompt typed character by character | `prompt` (else making_of.prompt) |
| `posters` | all posters pop into a grid | - |
| `step` | red stamp with the step number, title in Karantina, underline; starts the top rail (file chip, "צעד N / M", progress segments) | `title`, `chip` |
| `split` | the demo poster, then its plate / ink / object cards fan out, labelled LaMa / OpenCV / BiRefNet | - |
| `layers` | counter up to `{L}`, three layer cards exploding apart | - |
| `code` | code window typing the first shot's GSAP, frame counter | - |
| `rhythm` | BPM counter, waveform with a red playhead sweep | - |
| `polish` | poster next to its clean plate, "✓ clean" | - |
| `result` | the first poster's plate grows to fill the frame - part (b) opens on that exact plate, so the hand-over is seamless | - |

Demo poster = the first poster that has an object.

The default list (`DEFAULT_SCENES`) is 13 scenes, 44 beats (~31 s at 86 BPM): prompt,
posters, then five step+demo pairs (הפרדה, שכבות, קוד, קצב, ליטוש), then result. The
reference ran ~80 s - lengthen with more beats per demo rather than more scenes.

## Captions

- One red word, marked `*like this*`. Digits are wrapped in `<bdi>` automatically so
  "86 פעימות" does not reorder.
- Keep captions under ~34 characters at 720 px wide - the strip is one line, no wrap.
- Tone: short, a little proud, present tense. The reference: "הכול התחיל בפרומפט אחד:",
  "BiRefNet גוזר את החתול", "ומה שהיה מאחוריהם?", "והתוצאה:".

## Prompt text

`making_of.prompt` should be the user's real request (translated to what was actually
typed, if they wrote in Hebrew - the reference shows the English prompt). Do not invent
a more impressive prompt than the one given.
