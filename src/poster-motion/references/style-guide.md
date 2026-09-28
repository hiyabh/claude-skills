# Style guide - the look of the reference film

Source: `דוגמא מושיין.mp4`, 720x900 (4:5), 30 fps, 156 s, AAC stereo.

## Structure of the reference

| Time | Part | Content |
|---|---|---|
| 0-6 s | making-of | Claude Code window: the prompt typed, 7 poster thumbnails attached |
| 6-20 s | making-of | a big "7", the posters in a grid, then a film strip |
| 20-80 s | making-of | six steps, each opened by a numbered red stamp: 01 הפרדה, 02 שכבות, 03 קוד, 04 קצב, 05 WebGL, 06 ליטוש - each followed by a demo (layer cards, code window, waveform with BPM, shader, pixel audit) |
| 80-84 s | hand-over | "שבעה ניבים כפשוטם" - a poster card grows to fill the frame |
| 84-142 s | the film | seven posters, ~8 s each, built layer by layer on the beat |
| 142-150 s | finale | all posters on a tightrope, sliding past |
| 150-156 s | end card | a poster on kraft with a red splash, tools list, music credit |

## Palette

| Token | Value | Use |
|---|---|---|
| paper | `#efebe3` (per poster: `layers.json` → `paper`) | poster backgrounds, finale |
| cream | `#f6f2ea` | cards, chips, caption strip |
| kraft | `#b28860` + fibres (`assets/tex/kraft.png`) | making-of and end-card stage |
| red | `#d63a24` | the one highlighted word per caption, stamps, step tag |
| dark red | `#6e1c10` | red text ON kraft (plain red fails contrast, 1.6:1) |
| ink | `#1c1a18` | titles, rules, rope |

One red word per caption, never more. Everything else is ink on paper.

## Type

| Role | Font | Size (720 wide) |
|---|---|---|
| captions | Heebo 800 | 29 px, on the torn strip |
| step titles, big numbers | Karantina 700 | 118-190 px |
| end title | Karantina 700 | 64 px |
| chips, code, tool list | JetBrains Mono 400 | 12-17 px |

Fonts come from `@fontsource/*@5.3.0` on jsdelivr and are saved into the project
(`assets/fonts/`), Hebrew and Latin subsets split with `unicode-range`.

## Pacing

- The reference is 87 BPM; `sneaky` (Sneaky Snitch, the same track) measures 86.1.
- 8 beats a poster ≈ 5.6 s. Under 6 beats the lettering has no time to land.
- Every cut is on a beat. Inside a shot, entrances start on beats (`*_at` fields);
  writing speed is derived from the room left, so all words land 2 beats before the cut.
- Hard cuts with a 0.3 s punch-in. No cross-fades between posters - they read as mush
  on paper-on-paper.

## Motion character

Physical, paper-like: things are stamped, written, slid, dropped. Eases are
`power3.out` / `back.out` for arrivals, `none` for loops. Loops are small (6-7 px).
Nothing spins for its own sake except scattering accents.
