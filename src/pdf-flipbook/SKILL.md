---
name: pdf-flipbook
description: Turn a PDF (or a flipbook viewer link like heyzine) into a polished static website that flips like a real book — page-curl animation, RTL by default (Hebrew), zoom, fullscreen, thumbnails, keyboard nav, PDF download — then deploy it to a shareable link on Vercel. Trigger phrases — "תבנה אתר לדפדף ב-PDF", "תהפוך את ה-PDF לספר", "אתר flipbook", "ספר דיגיטלי לדפדוף", "flipbook from this PDF", "make this PDF flippable", "turn this PDF into a book", "דפדוף כמו ספר", or when the user has a PDF / flipbook link and wants an interactive page-turning site. NOT for editing the PDF itself, NOT for video (use hyperframes).
---

# PDF Flipbook Builder

`<SKILL_DIR>` = the folder that contains this SKILL.md (normally
`~/.claude/skills/pdf-flipbook`). Resolve it once to an absolute path before
running commands - PowerShell/cmd do not expand `~` inside quotes.

Builds a self-contained static site that lets users flip through a PDF like a real book, and deploys it to a shareable URL. Pages are pre-rendered to high-DPI WebP (sharp, fast, lazy-loaded). Flip engine is [StPageFlip](https://github.com/Nodlik/StPageFlip), bundled locally.

## When to use
User has a **PDF** (local file or a flipbook viewer link such as heyzine) and wants an interactive page-turning website — typically to **share a link**.

## Key design facts (learned, don't re-derive)
- **RTL is the default** (Hebrew books): cover on the right, pages turn right-to-left.
- **RTL is done with a double-mirror on an OUTER wrapper** (`#flip-mirror`), NOT on the StPageFlip block — StPageFlip resets the transform on its own element. Each page `<img>` is un-mirrored so content stays readable, and the inner block is forced `dir="ltr"` so the library's own RTL positioning doesn't fight the mirror. This makes both the page order AND the flip animation correct.
- **Use HTML render (`loadFromHtml` with real `<img>`), NOT `loadFromImages` (canvas).** Canvas blurs on zoom and breaks the mirror mid-animation.
- **Render at 300 DPI** (source images are usually ~1024×1536). 150 DPI looks blurry, especially when zoomed.
- **Single large page** (`usePortrait: true`) beats a two-page spread for text-heavy / slide content: more readable, and a spread would show pages in reversed order under the mirror.

## Workflow

### 1. Get a PDF
- **Local PDF** → use it directly.
- **Flipbook link** (heyzine etc.) → extract the original PDF from its CDN:
  ```bash
  python "<SKILL_DIR>/scripts/fetch_pdf.py" "<URL>" --download "<PROJECT_DIR>/book.pdf"
  ```
  If that finds nothing, fetch the page HTML and grep for `.pdf`, or fall back to the `browser-album-downloader` approach. Always grab the **original PDF**, never screenshots of the viewer.

### 2. Build the site
```bash
pip install pymupdf pillow   # if missing
python "<SKILL_DIR>/scripts/build_flipbook.py" \
  "/path/to/book.pdf" "<PROJECT_DIR>" \
  --title "כותרת הספר" --subtitle "תת-כותרת (optional)"
```
- Title falls back to PDF metadata then filename if `--title` omitted.
- Add `--ltr` for left-to-right (non-Hebrew) books.
- `--dpi` / `--quality` tune size vs. sharpness (defaults 300 / 90 are good).

The script renders all pages, writes `assets/manifest.json`, and assembles `index.html` + `css/` + `js/` + `lib/` + `vercel.json`.

### 3. Verify locally (recommended)
```bash
python -m http.server 8901 --directory "<PROJECT_DIR>"
```
Open with Playwright and check: book loads, content is readable (not mirrored), flip animation goes the right way (RTL: pages move left→right when advancing), zoom is sharp, thumbnails + keyboard work. The `#flip-mirror` computed transform should be `matrix(-1, 0, 0, 1, 0, 0)` for RTL.

### 4. Deploy
```bash
cd "<PROJECT_DIR>" && vercel --prod --yes
```
Return the **Aliased** short URL (e.g. `https://<project>.vercel.app`). Verify it loads publicly (not behind Vercel auth) before handing it over.

## Features the site ships with
Page-curl flip (RTL/LTR) · single large readable page · zoom (buttons / Ctrl+wheel / double-click) + pan · fullscreen · thumbnails drawer · keyboard (arrows respect RTL, Home/End, +/−, F, Esc) · original-PDF download · lazy-loaded images · navy+gold dark theme · loading/error states.

## Files
```
scripts/build_flipbook.py   PDF → full site (render + assemble)
scripts/fetch_pdf.py        extract source PDF from a flipbook viewer link
templates/index.html        UI shell (title/subtitle/download filled from manifest by app.js)
templates/style.css         RTL theme + mirror + zoom/thumbs styles
templates/app.js            flip init, RTL mirror, zoom/pan, thumbnails, keyboard, lazy-load
templates/page-flip.browser.js  StPageFlip (bundled, offline)
templates/vercel.json       static hosting + cache headers
```

## Re-rendering after a PDF change
Replace the PDF and re-run `build_flipbook.py` with the same output dir. The templates are generic — the title, subtitle, page count and download link all come from `manifest.json`, so nothing in the HTML/JS needs editing per-book.
