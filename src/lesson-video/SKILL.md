---
name: lesson-video
description: >-
  Turn a full-length recorded Torah lesson / shiur (30-90 min audio) into a richly animated 16:9 YouTube video
  at minimal cost: the uncut recording under ~200 timed beats (titles, questions, pesukim, kinetic type, live
  diagrams - flow, cycle, timeline, bars, balance, venn, stack, ladder - and illustrations with camera moves),
  karaoke captions, a YouTube thumbnail, a YouTube settings file with chapters, optional 9:16 reels.
  HyperFrames + local Whisper; only cheap flash-lite images cost money (~$2-3).
  TRIGGER on Hebrew: 'תעשה סרטון לשיעור', 'סרטון להקלטה', 'הנפש את השיעור', 'סרטון מונפש לשיעור',
  'סרטון יוטיוב לשיעור', 'סרטון עם הנפשות ותרשימים'. English: 'animate this lesson recording', 'lesson video',
  'shiur video'. NOT for a short TTS dvar Torah reel (dvar-torah-animation), NOT for event footage
  (event-recap-video), NOT for editing lesson text (shiur-editor).
---

# Lesson Video - שיעור מוקלט ← סרטון מונפש

The recording plays uncut; the screen shows the eye what to look at **exactly when it is said**.
Built from the Sukkot 5787 video (47:52, 16 chapters, 180 beats, 47 images, $2.5) and upgraded so the
picture **never stands still more than 12 seconds** - the engine fails the build otherwise.

## Iron rules
- **Never show something before it is said.** Every beat and every inner element sits on an anchor phrase.
- **Cheap by design.** No sub-agents writing HTML: Claude writes a compact Python beat script; scripts render it.
  Images: `gemini-3.1-flash-lite-image`; edits: `gemini-3.1-flash-image`. Verify prices on the day - they change.
- **Modesty + identity**: tichel tied at the back, never hijab; girls bare-headed;
  only men inside a synagogue hall; no Dome of the Rock / mosques; negative characters not identifiably Jewish;
  no portraits of real people (hostages, rabbis, family) - symbolic images instead. Check every image with crops.
- **Private names never on screen.** Ask once what to do with names/sensitive stories; block them in captions.
- **Hebrew/RTL:** sequences start on the right; only "-" (no em/en dash); fractions in words; niqqud only on
  verified text (pull pesukim from Sefaria or the lesson's verified MD).
- **Render silent, mux with ffmpeg (`mux.sh`, which also mixes the sound effects)** - the HyperFrames audio mix timed out on long lessons.

## Workflow

### 0. Discovery (one AskUserQuestion)
Private names / sensitive passages in the recording (keep audio + hide names = default) · image budget
(default: as many as useful on flash-lite, ~1 per 60-75s) · reels yes/no. If the lesson's edited text (MD/DOCX)
exists, read it - it is the source for quotes and chapter titles. If a previous lesson project sits in the
Recycle Bin, copy what you need out first.

### 1. Scaffold + transcribe (local, background)
```bash
python ~/.claude/skills/lesson-video/scripts/new_project.py --audio "<recording>" --title "<lesson title>" --subtitle "..."
cd "<lesson>/סרטון/build" && python -u transcribe.py > transcribe.log 2>&1   # run_in_background, ~0.6x realtime
```
Creates `סרטון/build` (scripts, `video.json`, `specs/`, `scenes.py`, `edits.py`, `chapter_spec.json`) and
`סרטון/clip` (HyperFrames project, normalized `lesson.m4a`). While it runs, steps 2-3 can proceed from an
existing SRT/transcript (an SRT can be converted to a provisional words.json to test anchors early).

### 2. Plan chapters + pictures
- `chapter_spec.json`: 10-16 chapters, each opened by a phrase as transcribed (`"at"`), `ink` warm/torah/math/both.
- `scenes.py`: one subject line per picture + `"thumb-hero"` (subject on the LEFT, calm right half for the title).
- `python gen_images.py` (background) → review every image as contact sheets, then crop small/background
  figures. Fix with `edits.py` + `IMG_MODEL=gemini-3.1-flash-image python edit_images.py <name>`, or regenerate
  with a corrected prompt. See [references/images.md](references/images.md) for the failures to look for.

### 3. Write the beat script - this is where the animation comes from
`specs/chNN_*.py` with helpers from `spec_helpers.py`. Read [references/beat-catalog.md](references/beat-catalog.md)
first. Match the beat to the content - the richer the match, the more alive the video:

| What is said | Beat |
|---|---|
| A sequence / process / "first X, then Y" | `FLOW` (arrows draw between nodes) |
| Something that repeats or returns | `CYCLE` |
| Dates, years, days | `TL` timeline |
| Numbers, before/after, how much | `N` (counter + ring) or `BARS` |
| Weighing two things, "what matters more" | `SCALE` (tilts) |
| Two ideas that overlap | `VENN` |
| Building up, layers, foundations | `STACK` |
| Levels, stages, "higher and higher" | `LADDER` |
| A list of 2-5 items | `L` (or `KW` chips) |
| The punchline sentence | `KIN` (each word slams in when spoken) or `SAY` with *highlight* |
| A question to the audience | `Q` |
| Pasuk / source quote | `V` / `SRC` / `SPLIT` (picture + quote) |
| A chat/app conversation on a phone | `PHONE` (messages pop in; `you/say/ask/done` steps) |
| "The link is below the video" | `LINK` (card with a scannable QR code; needs `pip install qrcode`) |
| A story, mashal, scene | `S` with `shots` (camera moves to details) or `IT` |
| Contrast | `C` compare |

Density target: a beat or anchored reveal every **8-12s** (~5-6 beats/minute). Give lists/diagrams a
`reveal=[...]` so each element appears on its own word - reveals count as motion. Story beats get automatic
camera moves every 6s; add `shots=[{"at", "focus": [x%, y%], "zoom"}]` to point at a specific detail.
Per-chapter `"keywords"` turn gold in the captions.

### 4. Build, check, fix
```bash
bash build_all.sh      # specs → captions → chapters → index → beats → density_check → lint
```
- Anchor misses print as `chN: beat K anchor '...' not found` - find the real wording in the transcript
  (Whisper spells differently; see [references/timing-and-anchors.md](references/timing-and-anchors.md)).
- `density_check` lists every still stretch over 12s **with the words spoken in it** - add a beat or a reveal there.
- Then print the beat table (beat time vs. the transcript line at that time) and read it: a phrase can resolve to
  a later, wrong occurrence. Fix captions with `video.json` `fixes` / `blocked_names` / `blocked_stems` /
  `timed_drops`, then grep the compositions for every blocked name and for em/en dashes.

### 5. Look at it
`npx --yes hyperframes@0.8.106 snapshot --at <t1,t2,...> --no-end -o snapshots/x` from `clip/` - one frame per
beat (after its reveals) plus ~16 spread points. Read the contact sheets: RTL order, overlaps, clipped text,
caption matches the image, modesty.

### 6. Render + deliver
```bash
bash render.sh --draft && bash mux.sh --draft   # optional ~15fps preview -> build/qc/draft.mp4, for checking fixes fast
bash render.sh   # background; ~1.2x lesson length. Never pipe through `head`.
bash mux.sh      # "<title> - סרטון השיעור.mp4" in the lesson folder; mixes sfx, verifies, deletes clip/renders
```
Verify: `ffprobe` duration = audio, 1920x1080, audio stream; extract 6 frames from the final file; `volumedetect`.

### Polish layer (automatic, no spec changes needed)
- **Poster first frame:** frame 0 (chapter 0's title card) is fully composed - no fade-in, wipe or count-up. It is the
  WhatsApp / player preview image. Never start a lesson on an empty or half-animated frame.
- **Accent per beat + floating shapes + graph paper:** `deco.py` gives every beat its own accent (overrides `--torah`;
  titles keep the chapter ink), small SVG shapes drift in the margins of text/diagram beats (left side only for
  right-aligned `L` lists; none on picture, title, phone or link beats), and live diagrams sit on faint graph paper.
- **Sound effects:** `sfx.py` synthesizes soft whoosh (each beat change), chime (title/closing/link), pop (number landed,
  phone message) and click (Allow) locally; events go to `build/sfx.json`, and `mux.sh` mixes them under the narration at
  peak ~0.16 with a limiter. Turn off per project with `"sfx": false` in `video.json` (default on; needs numpy).
- **Cinematic finish:** vignette + faint bloom over the beats (below captions), a third violet background glow and coloured motes.
- **Stronger caption pop:** the spoken word scales to 1.22 and lifts 8px.
- **Draft mode:** `render.sh --draft` (15 fps, draft quality) then `mux.sh --draft` -> `build/qc/draft.mp4` (~1 min per
  minute of video). `mux.sh` after a real render verifies duration + audio stream and then deletes `clip/renders/*`.
- Guidance: effects stay far under the voice (never raise `PEAK`); look at diagram and list snapshots for shapes
  overlapping text; always check frame 0 in a snapshot (`--at 0`) before delivering.

### 7. Thumbnail + YouTube
Fill `video.json` `thumb` (2-5 word title, `*gold word*`, kicker, sub, badge) and `youtube` (title ≤100, description,
tags), then `python make_thumbnail.py` (1280x720 JPG <2MB, RTL rendered by the browser) and
`python make_youtube.py` (`<title> - הגדרות יוטיוב.md` + `youtube.json`, chapters from 0:00, limits checked).
See [references/youtube-and-thumbnail.md](references/youtube-and-thumbnail.md).

### 8. Reels (optional)
Pick 2-3 self-contained 45-90s passages, add them to `video.json` `reels`, then
`python reels.py <name>` → `bash render.sh --reel <name>` → `bash mux.sh --reel <name>`. See [references/reels.md](references/reels.md).

### 9. Close out
Tell the user anything sensitive that stays in the audio (private names, personal details) before they publish.

## Files
`scripts/` - engine (copied into each project's `build/` by new_project.py): `beats.py` (resolver + page), `deco.py` (accents, shapes, paper), `sfx.py` + `sfx_track.py` (sound effects),
`beat_types_device.py` (PHONE, LINK),
`beat_types_text.py` / `beat_types_visual.py` / `beat_types_diagram.py`, `transitions.py`, `captions_layer.py`,
`clean_words.py`, `anchor.py`, `density_check.py`, `make_chapters.py`, `make_index.py`, `gen_images.py`,
`edit_images.py`, `make_thumbnail.py`, `make_youtube.py`, `reels.py`, `build_all.sh`, `render.sh`, `mux.sh`.
`assets/` - `clip_template/` (kit.css/js, beats.css, diagrams.css, device.css, fonts), `thumb_template/`, `reel_template.html`,
`project_template/` (scenes.py, edits.py, chapter_spec.json, `specs/ch00_example.py` showing every beat type).
