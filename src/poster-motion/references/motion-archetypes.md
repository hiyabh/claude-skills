# Motion archetypes and the shots.json schema

`shots.json` is the edit spec. `build_composition.py --draft` writes a rule-based
first version; step 4 is rewriting it with judgment. Times are in **beats** (one
beat = `period` from beats.json, ~0.7 s at 86 BPM), so a new track re-times the
film without touching this file.

## Schema

```json
{
  "title": "ניבים בעברית",
  "posters": [
    {"id": "p1", "beats": 8, "text": "stamp", "object": "rise", "accents": "none",
     "drift_words": [], "text_at": 1, "object_at": 0, "accents_at": 2, "float": false}
  ],
  "finale": {"beats": 8},
  "end": {"beats": 5},
  "making_of": {"enabled": false, "prompt": "...", "scenes": [ ... ]}
}
```

| Field | Default | Meaning |
|---|---|---|
| `id` | - | poster id (`p1` = posters/p1.png). Order of the list = order in the film |
| `beats` | 8 | shot length. 6 is brisk, 8 is the reference pace, 10+ for a slow reveal |
| `text` | by rule | how the ink layer arrives - see below |
| `object` | by rule | how the object arrives - see below |
| `accents` | `scatter` if any | how the colour accents arrive |
| `text_at` / `object_at` / `accents_at` | 1 / 0 / 2 | beat (inside the shot) each layer starts |
| `drift_words` | `[]` | ink-group indices that keep floating after they are written (a feather) |
| `float` | false | the object keeps bobbing after it lands |

Ink groups are indexed in reading order: top line first, each line right to left.
`layers.json` lists them (`words[i].bbox`) - check the index against the sheet.
Groups smaller than 0.12% of the canvas are "minor" (dust, a stray dot): they fade
in quietly at the shot's start instead of taking a beat each.

## Text archetypes (`text`)

| Value | What it does | Use for |
|---|---|---|
| `write` | each word wipes in from its right edge, one after another | handwriting, brush lettering, thin lines - חבל דק, פרפרים בבטן, פיל בחדר |
| `stamp` | each word slams in on its own beat, camera shakes on impact | heavy bold titles, 2-4 words - חתול בשק, לצאת מהקופסה |
| `fade` | words fade up together | quiet posters, lots of small text |
| `rope` | the whole ink layer is cut into vertical strips, drawn right to left, then rides a travelling sine wave for the rest of the shot | a single wide line of ink across the frame - על חבל דק |

The draft picks `rope` when the ink is wider than 80% of the frame and shorter than
12%; `stamp` for ≤4 big words taller than 20% of the frame; `write` otherwise.

## Object archetypes (`object`)

| Value | What it does | Use for |
|---|---|---|
| `rise` | comes up 18% of its height with a soft overshoot | objects standing on the floor - a bag, a fork |
| `pop` | scales from 55% with a springy overshoot | a box, anything that should feel playful |
| `edge` | slides in from the frame edge it is cropped by | an elephant's leg cut by the right edge |
| `drop` | falls from above and bounces | light objects, comic timing |
| `peek` | rises out of a slot at its own bottom edge (hidden below it) | something climbing out of the ground |
| `fade` | fades in | when motion would fight the idea |
| `none` | the object never appears - the plate is clean, so this removes it from the film | only when `layers.json` has no object |

`edge` picks its side automatically: the side of the frame nearest to the object's box.
The draft uses `edge` only for tall objects (over 60% of the frame) touching a side;
a low object touching a side is usually its floor shadow, so it gets `rise`.

## Accent archetypes (`accents`)

| Value | What it does |
|---|---|
| `scatter` | each accent flies in from a seeded offset, spinning, then flutters gently until the cut |
| `none` | accents stay hidden (they are cut from the plate, so they never appear) |

## Whole-shot motion (automatic)

Every shot gets a cut-in `punch` (scale 1.045 → 1 in 0.3 s) on its first beat and a
slow camera `push` (1 → 1.035) across its length. The finale lays every poster on one
line and slides it past right to left, bumping on each beat; the end card drops the
first poster on kraft paper with a red splash, the title, the tools and the music credit.

## Directing notes (what the reference film does)

- The object usually arrives first and the lettering answers it: the bag, then "חתול
  בשק" slams, then the cat peeks. Keep `object_at: 0`, `text_at: 1`.
- When the object *is* the punchline (the elephant in the room), delay it: text first
  (`text_at: 1`), object late (`object_at: 4`).
- One poster per beat-count family: vary 6 / 8 / 10 so the film breathes.
- A feather, a leaf, a balloon drawn in ink: `write` it, then `drift_words: [its index]`.
- Butterflies / confetti in colour: they are accents - `scatter`, `accents_at: 3`
  (after the lettering, so the eye is free).
- Do not stamp handwriting: the slam reads as a font, and brush text has too many
  groups (each one takes a beat).
