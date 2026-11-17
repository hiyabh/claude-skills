---
name: book-to-print
description: >-
  Take a finished book to a real printer: the cover above all (hard case-bound from the bindery's
  drawing, or soft for BookPod / digital / offset), plus the interior's print settings. One JSON spec
  drives it: Hebrew front on the LEFT, every word real vector type over a text-free picture (own,
  designer's or AI), CMYK ISO Coated v2, bleed, crop and fold marks, EAN-13 ISBN, centring and
  legibility checks, a mockup and a Hebrew brief for the printer. Interior: Word setup and export,
  margins measured by odd/even page, padding, embedded fonts. TRIGGER on Hebrew: "ספר לדפוס",
  "להדפיס ספר", "בית דפוס", "כריכה לספר", "כריכה קשה", "כריכה רכה", "שדרה", "גלישה", "PDF לדפוס",
  "שרטוט כריכה", "עותק שמש", "ברקוד לספר". English: "print-ready book", "book cover for print",
  "spine width", "bleed". NOT for writing or editing the text.
---

# Book to print (ספר לדפוס)

Goal: the author hands the printer files that print right on the first run, and knows exactly
what to check on the proof. The author is usually not technical.

**Talk to the author in Hebrew only**, plain words, one decision at a time. Code, commands and
file paths stay in English. Every file the author has to look at is given as its full absolute path.

`<SKILL_DIR>` = the folder that contains this SKILL.md (normally `~/.claude/skills/book-to-print`).
Resolve it once to an absolute path before running commands - PowerShell/cmd do not expand `~` inside
quotes. Every `scripts/...` below means `<SKILL_DIR>/scripts/...`.

Scripts are in `scripts/` (run as `python <SKILL_DIR>/scripts/<name>.py`), knowledge in `references/`
(Hebrew), example specs in `assets/`. Read `references/lessons.md` before the first build: every
rule in it cost a real book a reprint or a round with the printer.

## 0. First run on a computer
`python scripts/setup_check.py` installs the Python packages, downloads the ISO Coated v2 colour
profile, finds Word and builds a test cover. Add `--with-upscaler` when AI art will be used.
If it fails, fix that before anything else.

## 1. Intake - read first, ask once
Read `references/intake.md`. Look at what the author already has (a Word file, a PDF, a designer, a
printer's quote or drawing). Then ask everything that is still open in ONE AskUserQuestion: the
state of the book, hard or soft cover, which printer, trim size, paper, ISBN, where the cover art
comes from. Do not ask what the files already answer.

## 2. The printer's numbers come first
Nothing is final until the printer has said it. Use `references/printer-questions.md` to write the
author a short message for the printer (in Hebrew, ready to paste). Until the answers arrive, build
with estimates; `spec.py` marks each one, the brief lists them as open questions, and the hand-over
says plainly which numbers are ours.
- **Hard cover:** the bindery's drawing (שרטוט כריכה) decides board, joint, turn-in and spine. Read
  `references/hardcover.md` - the drawing also tells you the real page size and paper caliper.
- **Soft cover / BookPod:** `references/softcover.md`. BookPod's facts must be re-checked live.

**One folder per edition** (e.g. `כריכה קשה/` and `בוקפוד/`), each with its own spec. Inside it,
`לדפוס/` holds only what goes to the printer (cover PDF, interior PDF, brief); previews, crops,
contact sheets and work files go next to it (`תצוגות/`, `בדיקות/`, `_work/`), never inside.

## 3. Interior
By the state of the book:
- **Word:** `references/interior-word.md`. `word_export.py inspect`, then `setup` on a COPY with the
  page size and margins, then `export`.
- **Finished PDF:** straight to the checks.
- **Designer / InDesign:** `references/interior-indesign.md` - what to ask the designer for.

Then, always:
1. `python scripts/prep_interior.py <in.pdf> "<edition folder>/לדפוס/<שם> - פנים הספר לדפוס.pdf" --printer offset|bookpod|digital`
   (pads to the signature, adds bleed if the printer wants it, checks fonts and images). Exit 1 = fix.
2. `python scripts/check_interior.py <pdf> --expect INNER OUTER TOP BOTTOM --sheets` - measures the
   margins by odd/even page. In a Hebrew book the margin by the spine must come out on the RIGHT of
   odd pages. Do not trust the settings; trust this measurement.
3. **Open every contact sheet** with Read (the first page too). Blank pages, a lost header, text
   cut by the trim, a page out of order - the scripts don't see these.

## 4. Cover
1. Copy `assets/cover_spec.hard.example.json` or `cover_spec.soft.example.json` next to the book,
   fill it (`references/spec.md` explains every key), and run `python scripts/spec.py <spec>`.
2. `python scripts/template.py <spec>` - a to-scale template and the pixel size of every area, for
   each way of giving the art (one wrap picture with `fit: visible` = what shows on the closed book,
   the default; `fit: sheet` = the whole file with bleed; or one picture per board). Tell the designer
   WHICH of those sizes to deliver, and set `fit` to match - a mismatch shifts the art off the board.
   Text boxes: `"box": ["center", y, w, h]` centres a box on its board, so it survives a new drawing.
3. Art, per `references/cover-art.md`: the author's or designer's picture, or
   `python scripts/ai_art.py <spec> --describe "..."` (needs the author's API key; costs money - say
   so first) and `python scripts/upscale.py` to reach 300 dpi. **No text in the picture.** Open every
   painting with Read and zoom into the background: fake letters, other religions' symbols, off-centre
   motifs.
4. `python scripts/build_cover.py <spec>` - the press PDF and flat previews.
5. `python scripts/check_cover.py <spec>` - must end with 0 errors. Read every warning: off-centre
   text or art, and low contrast or a busy picture under a line of type. Then **open everything it
   lists** (the guided preview, spine, front, back, barcode) with Read. Look at the spine enlarged.
6. `python scripts/mockup.py <spec>` - the closed book, for the author's approval.

## 5. Brief for the printer
`python scripts/brief.py <spec>` writes `00 - הנחיות לבית הדפוס - <title>.md/.docx`: files, measures
with their source, the exact wording, fonts and licences, technical facts, open questions.
Export it with `word_export.py export` and look at every page before handing it over.

## 6. Proof, drawing, rebuild
- Recommend a proof (הדפסת ניסיון / עותק שמש) before the full run, always.
- When the bindery's drawing or the printer's answers arrive: update the spec (`spine_override`,
  `hard.*`, `caliper_per_leaf`), keep the old PDF in an archive folder, rebuild, re-check, re-open
  the crops. A smaller board than expected means the printer shrank the pages: ask the author to
  check on the proof that nothing is cut.

## 7. Hand-over (Hebrew)
- The full absolute path of the folder and of every file, each with one line on what to check.
- Which numbers come from the printer and which are still our estimates.
- Decisions taken, and what was not verified (colour on paper, foil, a font licence).

## Rules that are never bent
1. Every word on the cover is vector type in an embedded font. Never text drawn by an image model.
2. Hebrew book: front on the LEFT of the flat cover, back on the right; spine text reads top-down.
3. The printer's drawing beats any default here. Estimates are marked as estimates, everywhere.
4. After every build: measure centring (`check_cover.py`) and look at the spine enlarged.
5. When the board size changes, the art is refitted to the new board before anything is measured.
6. Margins are measured in the PDF by odd/even page, never assumed from settings.
7. Look at every page and every crop, not a sample; the first page of every PDF too.
8. Printer and BookPod facts (bleed, caliper, prices, colour profile) are re-checked, or written as
   "דורש אימות" with the date. Never a number from memory.
9. AI art: the fixed exclusion line of other religions' symbols is in every prompt, and every
   painting is checked enlarged before use.
10. File names are descriptive Hebrew; folder names short (Windows 260-character path limit).
11. A proof copy before the full run.

## Scripts
| Script | What it does |
|---|---|
| `setup_check.py` | install, colour profile, optional Real-ESRGAN, test build |
| `spec.py` | load and check a cover spec; lists the estimates |
| `spine.py` | spine width; `--from-drawing` gets paper caliper from two spines |
| `template.py` | to-scale template + measurements for the designer or AI |
| `build_cover.py` | press PDF (CMYK, boxes, marks, barcode) + previews |
| `check_cover.py` | preflight + centring + crops to look at |
| `mockup.py` | 3D mockup from the press PDF |
| `brief.py` (+`brief_docx.py`) | Hebrew brief for the printer, MD + RTL Word |
| `prep_interior.py` | pad, bleed, fonts and image checks for the interior |
| `check_interior.py` | margins by odd/even page, blank pages, contact sheets |
| `word_export.py` | Word: inspect, set up a copy, export PDF |
| `ai_art.py`, `upscale.py` | optional AI painting, and upscaling to print resolution |
