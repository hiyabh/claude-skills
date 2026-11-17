# -*- coding: utf-8 -*-
"""Prepare and check an interior PDF for the printer.

    python prep_interior.py <in.pdf> <out.pdf> [--printer offset|bookpod|digital] [--multiple N]
                            [--bleed MM] [--has-bleed] [--forbid TEXT ...]

Checks the source: one page size for all pages, every font embedded, image resolution, colour
images in what may be a black-and-white book. Pads with blank pages AT THE END to a multiple of
N (BookPod 4; offset printers print in signatures of 16 or 32 - ask them), and, when the printer
wants bleed on the interior, centres every page on a sheet that much larger (vector placement:
fonts stay embedded, nothing is rasterised). Then re-checks the output and writes a Hebrew report
next to it. Exit 1 on a problem that must be fixed.
"""
import argparse
import sys
from pathlib import Path

import fitz

from common import PT_PER_MM, fail

PRESETS = {"bookpod": {"multiple": 4, "bleed": 3.2, "range": ((105, 220), (148, 297))},
           "offset": {"multiple": 16, "bleed": 0.0, "range": None},
           "digital": {"multiple": 2, "bleed": 0.0, "range": None}}
TOLERANCE_PT = 0.5
MIN_PPI, LOW_PPI = 300, 200


def page_size_mm(doc):
    sizes = {(round(p.rect.width, 1), round(p.rect.height, 1)) for p in doc}
    if len(sizes) != 1:
        fail(f"העמודים בגדלים שונים: {sorted(sizes)[:5]} (בנקודות). כל הספר צריך להיות בגודל עמוד אחד - "
             f"תקן בקובץ המקור וייצא שוב.")
    w, h = sizes.pop()
    return w / PT_PER_MM, h / PT_PER_MM


def font_problems(doc):
    fonts = {f[3]: (f[1], f[2]) for p in doc for f in p.get_fonts(full=True)}
    bad = [f"גופן לא מוטמע: {n}" for n, (ext, _) in fonts.items() if ext in ("", "n/a")]
    bad += [f"גופן שהפך לתמונה (Type3): {n} - Word לא הורשה להטמיע אותו; החלף גופן"
            for n, (_, kind) in fonts.items() if kind == "Type3"]
    return len(fonts), bad


def coloured_text_pages(doc):
    """Pages with text that is not grey/black (e.g. Word's blue headings) - grey in a B&W print."""
    pages = []
    for i, page in enumerate(doc, 1):
        for block in page.get_text("dict")["blocks"]:
            colours = {s["color"] for line in block.get("lines", []) for s in line["spans"] if s["text"].strip()}
            if any(len({(c >> 16) & 255, (c >> 8) & 255, c & 255}) > 1 for c in colours):
                pages.append(i)
                break
    return pages


def image_findings(doc):
    """(low-resolution pages, pages with colour images)."""
    low, colour = [], []
    for i, page in enumerate(doc, 1):
        for info in page.get_image_info():
            width_in = (info["bbox"][2] - info["bbox"][0]) / 72
            if width_in > 0.3 and info["width"] / width_in < MIN_PPI - 1:
                low.append((i, round(info["width"] / width_in)))
            if info["colorspace"] >= 3 and i not in colour:
                colour.append(i)
    return low, colour


def place(src, out_pdf, bleed_mm, multiple):
    w, h = src[0].rect.width, src[0].rect.height
    b = bleed_mm * PT_PER_MM
    total = -(-len(src) // multiple) * multiple
    out = fitz.open()
    for i in range(total):
        page = out.new_page(width=w + 2 * b, height=h + 2 * b)
        if i < len(src):
            page.show_pdf_page(fitz.Rect(b, b, b + w, b + h), src, i)
        if b:
            page.set_trimbox(fitz.Rect(b, b, b + w, b + h))
    out.save(out_pdf, garbage=4, deflate=True)
    return total


def check_output(out_pdf, want_pt, multiple, forbid):
    doc = fitz.open(out_pdf)
    problems = [] if len(doc) % multiple == 0 else [f"{len(doc)} עמודים - לא כפולה של {multiple}"]
    for i, p in enumerate(doc, 1):
        if abs(p.rect.width - want_pt[0]) > TOLERANCE_PT or abs(p.rect.height - want_pt[1]) > TOLERANCE_PT:
            problems.append(f"עמוד {i}: {p.rect.width:.1f}x{p.rect.height:.1f} נק'")
    n_fonts, bad = font_problems(doc)
    text = "".join(p.get_text() for p in doc)
    problems += bad + [f"נמצא טקסט אסור: '{s}'" for s in forbid if s in text]
    return n_fonts, problems


def settings(a):
    preset = dict(PRESETS[a.printer])
    if a.multiple:
        preset["multiple"] = a.multiple
    if a.bleed is not None:
        preset["bleed"] = a.bleed
    return preset


def report_lines(src, trim, total, preset, n_fonts, problems, low, colour, text_colour):
    b = preset["bleed"]
    lines = [f"מקור: {len(src)} עמודים, גודל דף {trim[0]:.1f}x{trim[1]:.1f} מ\"מ",
             f"פלט: {total} עמודים ({total - len(src)} ריקים נוספו בסוף, כפולה של {preset['multiple']}), "
             f"{trim[0] + 2 * b:.1f}x{trim[1] + 2 * b:.1f} מ\"מ" + (f" כולל גלישה {b} מ\"מ" if b else " בלי גלישה"),
             f"גופנים: {n_fonts}, כולם מוטמעים: {'לא' if any('גופן' in p for p in problems) else 'כן'}"]
    if low:
        lines.append("תמונות ברזולוציה נמוכה (עמוד, ppi): " + ", ".join(f"{p}:{v}" for p, v in low[:20]))
    if colour:
        lines.append(f"תמונות צבעוניות בעמודים {colour[:20]} - בהדפסה בשחור-לבן הן יודפסו באפור; לבדוק שזה בסדר")
    if text_colour:
        lines.append(f"טקסט צבעוני (לא שחור) בעמודים {text_colour[:20]} - למשל כותרות כחולות של Word. בשחור-לבן "
                     f"הוא יוצא אפור ודהוי: לשנות את צבע הסגנון לשחור, אלא אם הספר מודפס בצבע")
    lines.append(f"בעיות: {len(problems)}")
    return lines + [f"  - {p}" for p in problems]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--printer", choices=PRESETS, default="offset")
    ap.add_argument("--multiple", type=int)
    ap.add_argument("--bleed", type=float)
    ap.add_argument("--has-bleed", action="store_true")
    ap.add_argument("--forbid", nargs="*", default=[])
    a = ap.parse_args()
    preset, src = settings(a), fitz.open(a.src)
    w, h = page_size_mm(src)
    trim = (w - 2 * preset["bleed"], h - 2 * preset["bleed"]) if a.has_bleed else (w, h)
    rng = preset["range"]
    if rng and not (rng[0][0] <= trim[0] <= rng[0][1] and rng[1][0] <= trim[1] <= rng[1][1]):
        fail(f"גודל הדף {trim[0]:.1f}x{trim[1]:.1f} מחוץ לטווח של {a.printer}: רוחב {rng[0]}, גובה {rng[1]}.")
    low, colour = image_findings(src)
    total = place(src, a.out, 0 if a.has_bleed else preset["bleed"], preset["multiple"])
    want = tuple((t + 2 * preset["bleed"]) * PT_PER_MM for t in trim)
    n_fonts, problems = check_output(a.out, want, preset["multiple"], a.forbid)
    problems += [f"תמונה ב-{v}ppi בעמוד {p} (פחות מ-{LOW_PPI})" for p, v in low if v < LOW_PPI]
    lines = report_lines(src, trim, total, preset, n_fonts, problems, low, colour, coloured_text_pages(src))
    Path(a.out).with_name("דוח בדיקה - פנים הספר.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
