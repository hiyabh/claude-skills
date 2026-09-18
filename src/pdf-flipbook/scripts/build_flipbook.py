"""Build a complete RTL flipbook website from a PDF.

Renders every PDF page to high-DPI WebP (display + thumbnail), writes a
manifest, and assembles the static site from the skill's templates.

Usage:
  python build_flipbook.py INPUT.pdf OUTPUT_DIR [options]

Options:
  --title "טקסט"      Book title shown in the toolbar (default: PDF metadata / filename)
  --subtitle "טקסט"   Optional subtitle under the title
  --dpi N             Render DPI (default 300; source images are usually ~1024x1536)
  --quality N         WebP quality 0-100 (default 90)
  --ltr               Left-to-right book (default is RTL / Hebrew)

Dependencies:  pip install pymupdf pillow
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
THUMB_WIDTH = 200
THUMB_QUALITY = 72


def pixmap_to_webp(pix, out_path: Path, quality: int) -> None:
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    img.save(out_path, format="WEBP", quality=quality, method=6)


def render_pdf(pdf: Path, out: Path, dpi: int, quality: int) -> dict:
    pages_dir = out / "assets" / "pages"
    thumbs_dir = out / "assets" / "thumbs"
    pages_dir.mkdir(parents=True, exist_ok=True)
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf)
    zoom = dpi / 72.0
    pages_meta = []
    first_w = first_h = None

    for i, page in enumerate(doc):
        num = i + 1
        rect = page.rect
        if first_w is None:
            first_w, first_h = rect.width, rect.height
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        pixmap_to_webp(pix, pages_dir / f"page-{num:03d}.webp", quality)
        tz = THUMB_WIDTH / rect.width
        tpix = page.get_pixmap(matrix=fitz.Matrix(tz, tz), alpha=False)
        pixmap_to_webp(tpix, thumbs_dir / f"thumb-{num:03d}.webp", THUMB_QUALITY)
        pages_meta.append({
            "n": num,
            "page": f"assets/pages/page-{num:03d}.webp",
            "thumb": f"assets/thumbs/thumb-{num:03d}.webp",
        })
        print(f"  page {num:>3}/{doc.page_count}  {pix.width}x{pix.height}px")

    meta = {
        "pageCount": doc.page_count,
        "aspect": round(first_h / first_w, 4),
        "pages": pages_meta,
    }
    doc.close()
    return meta


def copy_templates(out: Path) -> None:
    (out / "css").mkdir(exist_ok=True)
    (out / "js").mkdir(exist_ok=True)
    (out / "lib").mkdir(exist_ok=True)
    shutil.copy(TEMPLATES / "index.html", out / "index.html")
    shutil.copy(TEMPLATES / "style.css", out / "css" / "style.css")
    shutil.copy(TEMPLATES / "app.js", out / "js" / "app.js")
    shutil.copy(TEMPLATES / "page-flip.browser.js", out / "lib" / "page-flip.browser.js")
    shutil.copy(TEMPLATES / "vercel.json", out / "vercel.json")


def main() -> None:
    ap = argparse.ArgumentParser(description="Build an RTL flipbook site from a PDF.")
    ap.add_argument("pdf")
    ap.add_argument("out")
    ap.add_argument("--title", default=None)
    ap.add_argument("--subtitle", default=None)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--quality", type=int, default=90)
    ap.add_argument("--ltr", action="store_true")
    args = ap.parse_args()

    pdf = Path(args.pdf)
    out = Path(args.out)
    if not pdf.exists():
        sys.exit(f"PDF not found: {pdf}")
    out.mkdir(parents=True, exist_ok=True)

    # Title: explicit > PDF metadata > filename stem
    title = args.title
    if not title:
        try:
            md = fitz.open(pdf).metadata or {}
            title = (md.get("title") or "").strip() or pdf.stem
        except Exception:
            title = pdf.stem

    print(f"Rendering {pdf.name} @ {args.dpi} DPI ...")
    meta = render_pdf(pdf, out, args.dpi, args.quality)

    # Copy the source PDF for download (keep original filename)
    pdf_dest = out / "assets" / pdf.name
    shutil.copy(pdf, pdf_dest)

    meta.update({
        "title": title,
        "subtitle": args.subtitle or "",
        "pdf": f"assets/{pdf.name}",
        "dir": "ltr" if args.ltr else "rtl",
    })
    (out / "assets" / "manifest.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    copy_templates(out)

    # If LTR requested, neutralise the mirror by writing a tiny override.
    if args.ltr:
        css = out / "css" / "style.css"
        css.write_text(css.read_text(encoding="utf-8") +
                       "\n/* LTR override */\n.flip-mirror{transform:none!important}"
                       "\n.flipbook .page img{transform:none!important}\n",
                       encoding="utf-8")

    total_mb = sum(f.stat().st_size for f in (out / "assets").rglob("*")) / 1e6
    print(f"\nDone -> {out}")
    print(f"  title: {title}")
    print(f"  pages: {meta['pageCount']}  ·  assets: {total_mb:.1f} MB")
    print(f"\nPreview:  python -m http.server 8901 --directory \"{out}\"")
    print(f"Deploy:   cd \"{out}\" && vercel --prod --yes")


if __name__ == "__main__":
    main()
