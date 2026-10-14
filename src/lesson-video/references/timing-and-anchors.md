# Timing and anchors

## How anchors resolve
- `anchor.find(words, phrase, after)` normalizes both sides (niqqud and punctuation stripped) and matches each
  phrase word as a **substring** of consecutive transcript words, searching only after `after`.
- Beats resolve **in order**: each search starts at the previous beat's time, so the same phrase later in the
  chapter is found correctly. A beat appears `LEAD = 0.15s` after its anchor word starts.
- Reveals and shots search from their own beat's start (an inner reveal may reuse the beat's own phrase).
- A beat shorter than 2.5s, or an anchor past the chapter end, is a build error.

## Whisper quirks seen on Hebrew lessons (ivrit-ai turbo)
- Geresh words are split: `"פיצ" + "'ר"`, `"חז" + "'ל"`, `"תורג" + "'מן"`. `anchor.merged()` glues them back,
  for anchors **and** captions - write the phrase normally ("פיצ'ר", "חז'ל").
- Spelling drifts from the edited text: "בא אריזל", "שמולו תחת לראשי", "תם סופר", "צלחתי כדבריך",
  "מיוחד שעל פי המקובלים". Always copy anchors from `transcript_lines.txt` (dump: `s['s'], s['text']` per segment),
  never from the edited lesson text.
- Very short words ("צא", "בניסן") match as substrings of longer words - prefer 2-3 word phrases.
- A private name can come out as a real word ("רחל כהן" → "רחל כוהן"): hide it with `timed_drops` [from, to, token].
- Some sentences are simply not transcribed (a quoted pasuk mumbled fast). Anchor to the next clear phrase.

## Checking resolution (do this every time)
Print a table: beat time, type, anchor, and the transcript segment at that time. Read it top to bottom - a phrase
that resolved to a later occurrence shows up as a beat whose line has nothing to do with its content.

## Density
`density_check.py` counts beat starts, anchored reveals and story camera moves (automatic every 6s on story
beats longer than 11s). Any stretch over `density_max_gap` (12s) fails the build and prints the words spoken in
it. Typical fixes: a `KIN` on the punchline, a `reveal` list for items already on screen, a `Q`, or splitting a
long `SAY` with a diagram of what is being explained.

## Captions
`clean_words.py` → `captions.json`: lines of ≤7 words / ≤38 chars, broken at pauses >0.8s, held 0.5s after the
last word. `video.json`: `fixes` (token → replacement, "" drops it), `blocked_names` (exact, with ו/ל/ה/ב/מ/ש
prefixes), `blocked_stems` (prefix match), `timed_drops`, `keywords` (always gold).
