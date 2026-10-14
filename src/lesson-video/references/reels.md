# Reels (optional, 9:16)

## Choosing passages
2-3 passages of 45-90s that stand alone: a story with its punchline, a mashal + nimshal, a sharp question and its
answer. Start on a clean sentence start and end right after the punchline (use segment times from
`transcript_lines.txt`). Avoid passages that depend on earlier context or contain private names.

## Spec
`video.json`:
```json
"reels": [{"name": "lo-mivtzar", "start": 206.3, "end": 262.0, "hook": "דוד המלך לא חיפש מבצר"}]
```
`hook` = 3-6 words, the curiosity line shown big for the first 3s, then pinned small at the top.

## Build
```bash
python reels.py lo-mivtzar          # build/reels/lo-mivtzar/ (index.html, assets, reel.m4a cut from the lesson)
bash render.sh --reel lo-mivtzar    # silent 1080x1920
bash mux.sh --reel lo-mivtzar       # "<title> - רילס lo-mivtzar.mp4"
```
What it does: every beat overlapping the passage becomes a layer - picture beats as full-height Ken Burns shots,
text and diagram beats as big animated text cards (their title/text/words). Captions are 4 words per line,
84px, centred low, the spoken word turns gold. A progress bar runs along the bottom; the last 2.5s show an end
card with the lesson title and "השיעור המלא ביוטיוב".

Check with `npx --yes hyperframes@0.8.106 snapshot --at 1.5,5,15,30,45 -o snaps` inside the reel folder:
caption lines must never overlap, the hook must be readable, faces must not be cropped out of the 9:16 frame
(if a picture crops badly, pick another passage).
