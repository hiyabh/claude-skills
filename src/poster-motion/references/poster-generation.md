# Poster generation - when only a topic is given

Script: `scripts/generate_posters.py`. Key: `GOOGLE_API_KEY` in the environment or
`--key-file <path to .env>`. Default model `gemini-3-pro-image` (best Hebrew lettering);
`gemini-3.1-flash-image` is faster and cheaper. IDs verified 2026-09-28 against
`GET /v1beta/models` - re-verify if a call returns 404.

## poster_brief.json

```json
{
  "aspect": "4:5",
  "style": "Minimalist editorial poster on warm off-white textured paper. One real, photographic object with a soft natural shadow, centred low. Large hand-lettered Hebrew in black ink - brush or bold cut-paper letters - with generous empty paper around it. Muted natural colours, a single small accent colour at most. Studio light from the upper left. No gradients, no frame.",
  "posters": [
    {"id": "p1", "text": "חתול בשק", "scene": "a crumpled brown paper bag on the floor, a black cat peeking out of it"},
    {"id": "p2", "text": "לצאת מהקופסה", "scene": "an open cardboard box; the word לצאת bursts upward out of it, מהקופסה printed on its side"},
    {"id": "p3", "text": "על קצה המזלג", "scene": "a single silver fork standing upright, the words written tiny along its tip"}
  ]
}
```

## What makes a poster split well (write the scene for it)

- **Plain paper background, edge to edge.** No gradients, vignettes, frames or scenery -
  the paper is the separator (see layering.md).
- **Lettering on paper, not on the object** - unless it should move *with* the object
  (words printed on a box).
- **One object**, with clear paper around it. Two objects become one layer.
- **Accent colour in small shapes** (butterflies, a red dot) - they become accents that
  scatter in.
- A wide single line of ink (a tightrope with the words on it) → the `rope` archetype.

## Hebrew spelling - always check

Image models misspell Hebrew often: swapped or missing letters, mirrored words, stray
niqqud. After generation, build a contact sheet and read each poster letter by letter
against `text`. Redo a bad one with `--only pN` (it reuses p1 as the style reference).
After 3 failed tries, tell the user and offer: keep it anyway, simplify the phrase, or
supply that poster by hand.

## Idiom series ideas (tested concept)

The reference series: חתול בשק · לצאת מהקופסה · על קצה המזלג · על חבל דק · עוף מוזר ·
פרפרים בבטן · פיל בחדר - each idiom drawn *literally* ("כפשוטם"). The joke is the
literal picture; keep scenes literal and deadpan.
