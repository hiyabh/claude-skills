"""Render scanned PDFs to PNG with rotation/mirror autodetect.

Usage:
    python render_pdfs.py <pdf_dir> <output_dir> [--rotation 90|180|270|0] [--mirror]

For Hebrew Ministry of Education forms scanned via mobile, defaults are:
    - rotation 90 (forms scanned in landscape)
    - no mirror

For BDO accountant approval letters: rotation 180.

If unsure, run with --probe to render all 4 rotations × mirror toggle for the first
PDF, then visually inspect to determine correct settings.
"""
import sys, os, argparse
import fitz
from PIL import Image, ImageOps
import io

# Windows pipes stdout/stderr through the ANSI code page by default; force
# UTF-8 so Hebrew filenames in progress output don't crash the run.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8', errors='replace')


def render(pdf_path: str, out_dir: str, rotation: int = 90, mirror: bool = False, dpi: int = 300):
    os.makedirs(out_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        img = Image.open(io.BytesIO(pix.tobytes('png')))
        if mirror:
            img = ImageOps.mirror(img)
        if rotation:
            img = img.rotate(rotation, expand=True)
        out = os.path.join(out_dir, f'{base}_p{i+1:02d}.png')
        img.save(out)
    doc.close()
    return len(doc)


def probe(pdf_path: str, out_dir: str, dpi: int = 200):
    """Render first page in 8 variants for manual inspection."""
    os.makedirs(out_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes('png')))
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    for rot in [0, 90, 180, 270]:
        for mir in [False, True]:
            v = img.copy()
            if mir:
                v = ImageOps.mirror(v)
            if rot:
                v = v.rotate(rot, expand=True)
            tag = f'r{rot}{"_m" if mir else ""}'
            v.save(os.path.join(out_dir, f'{base}_PROBE_{tag}.png'))
    doc.close()
    print(f'PROBE saved 8 variants in {out_dir}/')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('source', help='PDF file or directory')
    p.add_argument('output', help='Output PNG directory')
    p.add_argument('--rotation', type=int, default=90)
    p.add_argument('--mirror', action='store_true')
    p.add_argument('--dpi', type=int, default=300)
    p.add_argument('--probe', action='store_true', help='Render first PDF page in 8 variants')
    args = p.parse_args()

    files = []
    if os.path.isdir(args.source):
        files = [os.path.join(args.source, f) for f in os.listdir(args.source) if f.lower().endswith('.pdf')]
    else:
        files = [args.source]

    if args.probe:
        probe(files[0], args.output, dpi=args.dpi)
        return

    total = 0
    for f in files:
        n = render(f, args.output, rotation=args.rotation, mirror=args.mirror, dpi=args.dpi)
        print(f'{n}p  {f}')
        total += n
    print(f'Done — {total} pages from {len(files)} PDFs')


if __name__ == '__main__':
    main()
