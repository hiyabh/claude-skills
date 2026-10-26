---
name: archive-media
description: >-
  Free archival b-roll and period music from archive.org, no API key: Prelinger Archives
  films (ads, industrial, educational, 1920s-1970s), Great 78 Project 78rpm records, Live
  Music Archive. Searches, grades each item's reuse rights (cleared / check / blocked), builds a
  timestamped contact sheet to pick shots, cuts edit-ready 1080p clips (old soundtrack stripped)
  and cleaned 78rpm music, and writes credits. TRIGGER on Hebrew: "צילומי ארכיון", "b-roll
  וינטג'", "סרט ישן", "פרסומת רטרו", "מוזיקה תקופתית", "תקליט 78", "מוזיקה ישנה בחינם",
  "צילומי סטוק בחינם". English: "archival b-roll", "period music", "Prelinger", "78rpm",
  "vintage footage", "retro ad". USE THIS whenever an edit needs archival footage or period
  music, inside any video workflow (epic-video-studio, hyperframes, event-recap-video). NOT
  for the user's own footage, NOT for modern stock (Pexels) or AI-generated media.
---

# archive-media: Prelinger footage and 78rpm music from archive.org

archive.org has a free, keyless API over millions of films and recordings. This skill uses
three collections:
- **Prelinger Archives:** about 10,000 ephemeral films (ads, industrial, educational). Great
  for artistic retro-tech ads.
- **Great 78 Project:** about 187,000 78rpm records.
- **Live Music Archive:** about 300,000 live recordings, non-commercial only.

The skill finds candidates, **grades the reuse rights of every item**, lets you see the shots,
cuts clips ready for any editor (HyperFrames, ffmpeg, Premiere) and writes the credits.

**Standing instruction (from the user):** whenever an edit needs archival b-roll or period
music, search the Prelinger and 78rpm collections with this skill and use them in the edit.
Only 🟢 items go into a commercial deliverable.

**Stack:** Python standard library plus ffmpeg. No API key and no pip packages.

## Rights first

Many Prelinger films are **not** public domain. Read [references/rights.md](references/rights.md)
once per project. Every script prints a grade:

| Grade | Meaning | In a deliverable |
|---|---|---|
| 🟢 | PD/CC0/CC BY license on the item, or a 78rpm recording old enough to be US public domain (2026: through 1925) | yes, with credits |
| 🟡 | no license on the item, or unknown year | only after an explicit decision; say so in the handoff |
| 🔴 | NC/ND license, 78rpm newer than the cutoff, live recordings | no; `fetch_clip.py` refuses unless `--allow-noncommercial` |

Two more defaults:
- **The film's own soundtrack is stripped.** Music inside a public-domain film can still be
  protected.
- **78rpm on YouTube:** a public-domain recording can still get a Content ID claim. Warn the
  user when the target is YouTube.

## Workflow

Work in a project or scratch folder with an **ASCII path**. Clips land in `--out`, and
films are cached in `--out/.ia-cache`.

```bash
S=~/.claude/skills/archive-media/scripts   # PowerShell does not expand ~ in quotes: resolve it once with
                                           # python -c "import os;print(os.path.expanduser('~/.claude/skills/archive-media/scripts'))"
python $S/preflight.py                                                     # 0. ffmpeg + archive.org reachable
python $S/search.py --preset prelinger --query "telephone OR computer" --cleared-only --out work
python $S/search.py --preset 78rpm --query "foxtrot OR jazz" --years 1920-1925 --out work
python $S/inspect_item.py Century21964 --out work                         # 1. rights + contact sheet
#    -> Read work/sheet_Century21964.jpg, pick shots by the timestamp on each cell
python $S/inspect_item.py Century21964 --range 670-700 --frames 12 --out work   # 2. zoom into a section
python $S/fetch_clip.py Century21964 --start 11:16 --end 11:21 --name dial --out work   # 3. cut (parallel OK)
python $S/fetch_clip.py <78-id> --start 0:10 --end 0:40 --restore-78 --name music --out work
python $S/credits.py --out work                                            # 4. credits.md + on-screen line
```

### Choosing shots

1. **Search wide, then filter.** Use `--cleared-only` for commercial work. Without it, 🟡 items
   show up so you can look for a licensed copy of the same film.
   [references/collections.md](references/collections.md) has queries per need.
2. **Look before you cut.** Read the contact sheet. Pick shots that *illustrate* the beat, not
   just match a keyword. Avoid prominent brand logos and dated stereotypes in ads.
3. **Short clips:** 3-6 s per shot for b-roll. Cut 0.5 s extra on each side when the edit uses
   crossfades.
4. **Vertical:** `--size 1080x1920`. Crop keeps the center; check that the subject is centered
   on the sheet first, or use `--fit pad`.
5. **Music:** for 78rpm, start a few seconds in to skip the needle drop. Use `--restore-78`
   for hiss and rumble, and `--hq` for the FLAC instead of the MP3.

### Handing clips to other skills

- **HyperFrames** (`epic-video-studio`, `general-video`): copy the clips into the project's
  `assets/` and use them as `<video>`/`<audio>` clips. They are already H.264 1080p30 with
  faststart, so no re-encode is needed.
- **ffmpeg montage** (`event-recap-video`): the clips share size and fps, so `xfade` and
  concat work directly.
- **Credits:** put the on-screen line from `credits.py` in the end card or the video
  description. List every 🟡 item in the handoff message.

## Limits and gotchas

- **Do not use archive.org's own `.thumbs`.** The numbers in their file names are not seconds
  in the playable file. Shots picked from them landed 2-3 minutes off (verified 2026-10-26).
  `inspect_item.py` grabs real frames instead.
- **Speed:** archive.org serves about 1 MB/s. A film of 400 MB or less is downloaded once
  (an 87 MB film takes about 40-90 s), and the sheet and every cut after that are local and
  take seconds. Bigger films are sampled with HTTP seeks, at about 15-20 s per frame.
- **Silent failures are caught:** a remote cut can end up empty while ffmpeg still exits 0.
  `fetch_clip.py` probes every output, so a failure says what happened and does not report
  success. Audio is always cached whole before cutting for this reason.
- **Long names:** 78rpm identifiers run about 90 characters. Cache files use short hashed
  names so they stay under the Windows 260-character path limit. Keep `--out` short.
- **Resolution:** most Prelinger films are 640x480. Upscaled to 1080p they look soft, which
  suits the look. Don't promise crisp footage.
- **Politeness:** requests carry a User-Agent and a short delay. Don't parallelize searches
  heavily. Running 4-5 `fetch_clip.py` processes at once is fine.

## Files

| Path | What |
|---|---|
| `scripts/preflight.py` | readiness check: ffmpeg/ffprobe, archive.org reachable |
| `scripts/ia_api.py` | HTTP with retries, search, metadata, collection presets, **`rights_grade()`** |
| `scripts/media_files.py` | best video/audio file of an item, cache, download, ffmpeg/ffprobe helpers |
| `scripts/search.py` | search + grade → table + `candidates.json` |
| `scripts/inspect_item.py` | rights, chosen file, timestamped contact sheet / audio track list → `item_<id>.json` |
| `scripts/fetch_clip.py` | rights gate, cut, normalize, verify, log to `sources.json` |
| `scripts/credits.py` | `sources.json` → `credits.md` + on-screen credit line; flags 🟡/🔴 |
| `references/rights.md` | the rights rules with sources and dates, and what was not checked |
| `references/collections.md` | collection IDs, sizes, query syntax, good queries per need |
