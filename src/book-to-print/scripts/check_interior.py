# -*- coding: utf-8 -*-
"""Measure what really came out of the interior PDF: margins by odd/even page, blank pages, pages
whose content comes close to the trim, and contact sheets of every spread to look at.

    python check_interior.py <interior.pdf> [--direction rtl|ltr] [--expect INNER OUTER TOP BOTTOM]
                             [--sheets] [--per-sheet 8]

--expect is measured to the outermost ink: a running head or a page number counts, so give the
margins to those (e.g. the head at 9 mm), or ignore the top/bottom lines of the comparison.

In a Hebrew book (rtl) the odd pages are the LEFT-hand pages and their binding edge is on the RIGHT.
Word and LaTeX both assume the opposite unless told, so a margin that "should" be 23 mm by the spine
can come out on the outside. Only a measurement of the PDF settles it.
"""
import argparse
import statistics
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

from common import mm_from_pt

NEAR_TRIM_MM = 6           # content closer than this to the trim edge is flagged (cutting tolerance)
EXPECT_TOL = 1.5           # mm between the expected and the measured margin
THUMB_W = 240              # px per page on the contact sheets
GAP = 24


def trim_rect(page):
    tb = page.trimbox
    return tb if tb and tb != page.mediabox else page.rect


def content_box(page):
    rects = [fitz.Rect(s["bbox"]) for b in page.get_text("dict")["blocks"] for line in b.get("lines", [])
             for s in line["spans"] if s["text"].strip()]
    rects += [fitz.Rect(i["bbox"]) for i in page.get_image_info()]
    if not rects:
        return None
    box = rects[0]
    for r in rects[1:]:
        box |= r
    return box


def margins(page):
    """(left, right, top, bottom) in mm from the trim, or None for a blank page."""
    box, t = content_box(page), trim_rect(page)
    if box is None:
        return None
    return tuple(mm_from_pt(v) for v in (box.x0 - t.x0, t.x1 - box.x1, box.y0 - t.y0, t.y1 - box.y1))


def inner_outer(parity_odd, left, right, rtl):
    """Binding-side margin first. rtl: odd pages are left-hand pages, bound on their right."""
    bound_right = parity_odd == rtl
    return (right, left) if bound_right else (left, right)


def survey(doc, rtl):
    rows, blank, near = {True: [], False: []}, [], []
    for i, page in enumerate(doc, 1):
        m = margins(page)
        if m is None:
            blank.append(i)
            continue
        left, right, top, bottom = m
        inner, outer = inner_outer(i % 2 == 1, left, right, rtl)
        rows[i % 2 == 1].append((inner, outer, top, bottom))
        if min(m) < NEAR_TRIM_MM:
            near.append((i, round(min(m), 1)))
    return rows, blank, near


def median_row(rows):
    return tuple(statistics.median(r[k] for r in rows) for k in range(4)) if rows else None


def report(doc, rtl, expect):
    rows, blank, near = survey(doc, rtl)
    names = ("פנימי (ליד השדרה)", "חיצוני", "עליון (כולל כותרת רצה)", "תחתון (כולל מספר עמוד)")
    problems = []
    for odd in (True, False):
        med = median_row(rows[odd])
        if med is None:
            continue
        side = "שמאליים" if odd == rtl else "ימניים"
        print(f"עמודים {'אי-זוגיים' if odd else 'זוגיים'} (העמודים ה{side} בספר הפתוח), חציון במ\"מ:")
        print("   " + " | ".join(f"{n} {v:.1f}" for n, v in zip(names, med)))
        if expect:
            off = [(k, n, v, e) for k, (n, v, e) in enumerate(zip(names, med, expect)) if abs(v - e) > EXPECT_TOL]
            problems += [f"{'אי-זוגי' if odd else 'זוגי'}: {n} {v:.1f} במקום {e:g}" for k, n, v, e in off if k < 2]
            for k, n, v, e in off:
                if k >= 2:
                    print(f"   הערה: {n} {v:.1f} ולא {e:g} - כותרת, מספר עמוד או שורה אחרונה שלא ממלאת את הדף")
    odd_m, even_m = median_row(rows[True]), median_row(rows[False])
    if odd_m and even_m and abs(odd_m[0] - even_m[0]) > EXPECT_TOL:
        problems.append(f"השוליים הפנימיים לא שווים בין זוגי ({even_m[0]:.1f}) לאי-זוגי ({odd_m[0]:.1f}) - "
                        f"שולי מראה לא הוגדרו, או שהצד הפוך")
    if odd_m and odd_m[0] < odd_m[1] - EXPECT_TOL:
        print(f"הערה: השוליים ליד השדרה ({odd_m[0]:.1f}) צרים מהחיצוניים ({odd_m[1]:.1f}). בספר עבה הטקסט "
              f"נבלע בכריכה - לבדוק שזה מכוון ולא צד הפוך.")
    print(f"עמודים ריקים: {blank if blank else 'אין'}")
    if near:
        print(f"תוכן קרוב לקו החיתוך (פחות מ-{NEAR_TRIM_MM} מ\"מ): " + ", ".join(f"עמ' {p} ({v})" for p, v in near[:30]))
    for p in problems:
        print(f"בעיה: {p}")
    return problems


def thumb(doc, index, height_px):
    if index is None or index >= len(doc):
        return Image.new("RGB", (THUMB_W, height_px), (235, 235, 235))
    page = doc[index]
    pix = page.get_pixmap(matrix=fitz.Matrix(THUMB_W / page.rect.width, THUMB_W / page.rect.width), clip=page.rect)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, img.width - 1, img.height - 1), outline=(150, 150, 150))
    d.rectangle((2, 2, 34, 16), fill=(255, 235, 120))
    d.text((5, 3), str(index + 1), fill=(0, 0, 0))       # the PDF page number, to name a bad page
    return img


def spreads(n, rtl):
    """(right page, left page) indexes, 0-based. rtl: page 1 opens alone on the left."""
    pairs = [(None, 0)] if rtl else [(0, None)]
    for first in range(1, n, 2):
        pairs.append((first, first + 1 if first + 1 < n else None) if rtl else (first + 1 if first + 1 < n else None, first))
    return pairs


def contact_sheets(doc, rtl, per_sheet, folder):
    folder.mkdir(parents=True, exist_ok=True)
    h = round(THUMB_W * doc[0].rect.height / doc[0].rect.width)
    pairs, cols, out = spreads(len(doc), rtl), 2, []
    for start in range(0, len(pairs), per_sheet):
        chunk = pairs[start:start + per_sheet]
        rows = -(-len(chunk) // cols)
        sheet = Image.new("RGB", (cols * (2 * THUMB_W + GAP) + GAP, rows * (h + GAP) + GAP), "white")
        for k, (right, left) in enumerate(chunk):
            col = (cols - 1 - k % cols) if rtl else k % cols
            x, y = GAP + col * (2 * THUMB_W + GAP), GAP + (k // cols) * (h + GAP)
            sheet.paste(thumb(doc, left, h), (x, y))
            sheet.paste(thumb(doc, right, h), (x + THUMB_W, y))
        path = folder / f"גיליון מגע {start // per_sheet + 1:03d}.jpg"
        sheet.save(path, quality=85)
        out.append(path)
    return out


def sheets_folder(pdf):
    """Outside the folder that goes to the printer, one per PDF so two editions never overwrite."""
    base = pdf.parent.parent if pdf.parent.name == "לדפוס" else pdf.parent
    return base / "בדיקות" / f"גיליונות מגע - {pdf.stem}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--direction", choices=("rtl", "ltr"), default="rtl")
    ap.add_argument("--expect", nargs=4, type=float, metavar=("INNER", "OUTER", "TOP", "BOTTOM"))
    ap.add_argument("--sheets", action="store_true")
    ap.add_argument("--per-sheet", type=int, default=8)
    a = ap.parse_args()
    doc, rtl = fitz.open(a.pdf), a.direction == "rtl"
    t = trim_rect(doc[0])
    print(f"{a.pdf}: {len(doc)} עמודים, דף {mm_from_pt(t.width):.1f}x{mm_from_pt(t.height):.1f} מ\"מ")
    problems = report(doc, rtl, a.expect)
    if a.sheets:
        paths = contact_sheets(doc, rtl, a.per_sheet, sheets_folder(Path(a.pdf)))
        print(f"{len(paths)} גיליונות מגע ב-{paths[0].parent} - לעבור על כולם בעין, כולל העמוד הראשון")
    print("שוליים: " + ("בעיה - ראה למעלה" if problems else "תקינים, והשוליים הרחבים בצד השדרה"))
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
