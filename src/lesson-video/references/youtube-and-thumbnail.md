# YouTube settings and thumbnail

## Thumbnail (`make_thumbnail.py`)
- Source: the `thumb-hero` illustration (or any scene) + `video.json` `thumb`:
  `{"img", "title" (2-5 words, *gold word*), "kicker" (badge top), "sub" (one line), "badge" (corner, e.g. "47 דק'")}`.
- The page is HTML rendered by HyperFrames' browser, so Hebrew RTL, niqqud and fonts are correct (no PIL bidi).
- Layout: picture full-bleed, dark gradient on the right, title right-aligned 168px Frank Ruehl.
  Prompt the hero with the subject on the LEFT half so the title does not cover faces.
- Output: `<title> - תמונה ממוזערת.jpg`, 1280x720, JPEG quality stepped down until < 2MB (YouTube limit).
- Readability test: look at it at 320x180 - the title must still read.

## Settings file (`make_youtube.py`)
`video.json` `youtube`: `{"title", "description", "tags": [...], "category": "Education", "playlist", "audience_kids": false}`.
Writes `<title> - הגדרות יוטיוב.md` (copy-paste) and `build/youtube.json`, and checks:
- title ≤ 100 chars, description ≤ 5000, tags ≤ 500 chars total;
- chapters: the first at 0:00, at least 3, each ≥ 10s (chapter list is appended to the description);
- category id (Education = 27), language he, made for kids = no, thumbnail and video file names.

Uploading itself needs the user's YouTube login (OAuth) - hand over the file; do not attempt an automated upload.

## Description template
2-3 lines of hook (the question of the lesson), one line of what is inside, the chapter list (automatic),
then tags. No private names, no "subscribe" fluff unless the user asks.
