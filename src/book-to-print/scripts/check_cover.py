# -*- coding: utf-8 -*-
"""Preflight of a built cover PDF against its spec. Writes zoom crops to look at by eye.

    python check_cover.py <cover_spec.json> [--pdf <cover.pdf>]

Checks: sheet size and boxes against the layout; every font embedded; image resolution and colour
space; every line of text inside its panel's safe area (spine: inside the folds); text boxes centred
on their board; whether the picture itself is centred on each board (the symmetry of the art -
an AI painting is often a few mm off, and on a flat preview the eye does not see it); nothing
printed in the barcode zone. Exit 1 when something must be fixed.
"""
import argparse
import sys
from pathlib import Path

import fitz
import numpy as np
from PIL import Image, ImageCms

Image.MAX_IMAGE_PIXELS = None

import build_cover as B
import geometry as G
import spec as S
import typeset as T
from common import fail, find_icc, mm_from_pt
from press import barcode_box

SIZE_TOL = 0.2          # mm
OUT_TOL = 1.0           # mm a font box may cross a line before it is an error (the box is taller than the ink)
CENTRE_TOL = 0.5        # mm
MIN_PPI, LOW_PPI = 300, 200
SYMMETRY_DPI = 40
SYMMETRY_SEARCH = 0.15  # share of the board width searched for the art's axis
SYMMETRY_SCORE = 0.7    # below this the art is not symmetric enough for the test to mean anything
SYMMETRY_TOL = 1.5      # mm
MIN_CONTRAST = 3.0      # WCAG ratio for large text
MAX_BUSY = 45           # grey-level spread under a line above which the picture fights the type
CROP_DPI = 300


class Report:
    def __init__(self):
        self.errors, self.warnings, self.ok = [], [], []

    def check(self, good, ok_text, bad_text, error=True):
        if good:
            self.ok.append(ok_text)
        else:
            (self.errors if error else self.warnings).append(bad_text)

    def show(self):
        for line in self.ok:
            print(f"  תקין: {line}")
        for line in self.warnings:
            print(f"  אזהרה: {line}")
        for line in self.errors:
            print(f"  שגיאה: {line}")
        print(f"סיכום: {len(self.errors)} שגיאות, {len(self.warnings)} אזהרות")


def check_boxes(rep, page, lay, spec):
    trim, bleed = page.trimbox, page.bleedbox
    w, h = mm_from_pt(trim.width), mm_from_pt(trim.height)
    rep.check(abs(w - lay.width) < SIZE_TOL and abs(h - lay.height) < SIZE_TOL,
              f"גיליון {w:.1f}x{h:.1f} מ\"מ כמו בפריסה", f"גיליון {w:.1f}x{h:.1f} במקום {lay.width:g}x{lay.height:g}")
    b = mm_from_pt(trim.x0 - bleed.x0)
    rep.check(abs(b - spec["bleed"]) < SIZE_TOL, f"גלישה לחיתוך {b:.1f} מ\"מ", f"גלישה {b:.1f} במקום {spec['bleed']}")


def check_fonts(rep, page):
    fonts = page.get_fonts(full=True)
    bad = [f[3] for f in fonts if f[1] in ("", "n/a")]
    rep.check(not bad, f"{len(fonts)} גופנים, כולם מוטמעים", f"גופנים לא מוטמעים: {bad}")


def check_images(rep, page, spec):
    for info in page.get_image_info():
        ppi = info["width"] / (info["bbox"][2] - info["bbox"][0]) * 72
        rep.check(ppi >= MIN_PPI - 1, f"תמונה ב-{ppi:.0f}ppi", f"תמונה ב-{ppi:.0f}ppi (צריך 300)", error=ppi < LOW_PPI)
        if spec["colour"] == "cmyk":
            rep.check(info["colorspace"] == 4, "התמונה ב-CMYK", f"התמונה ב-{info['colorspace']} ערוצים ולא CMYK")


def spans(page, o):
    h = mm_from_pt(page.rect.height)
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for s in line["spans"]:
                if s["text"].strip():
                    x0, y0, x1, y1 = (mm_from_pt(v) for v in s["bbox"])
                    yield s["text"], G.Box(x0 - o, h - y1 - o, x1 - x0, y1 - y0)


def area_of(box, lay, spec):
    cx, cy = box.cx, box.cy
    for name in ("front", "back"):
        p = lay.panel(name)
        if p.x <= cx <= p.right and p.y <= cy <= p.top:
            return name, p.inset(spec["safe"])
    s = lay.spine
    if s.x <= cx <= s.right:
        return "spine", G.Box(s.x + T.SPINE_SIDE / 2, s.y + 3, s.w - T.SPINE_SIDE, s.h - 6)
    return None, None


def check_text_areas(rep, page, lay, spec, o):
    for text, box in spans(page, o):
        if box.y < -spec["bleed"] or box.top > lay.height + spec["bleed"]:
            continue                       # the information line in the slug
        name, safe = area_of(box, lay, spec)
        label = text.strip()[:25]
        if name is None:
            rep.errors.append(f"'{label}' נמצא מחוץ לחזית, לשדרה ולגב (בקיפול או בגלישה)")
            continue
        inside = safe.contains(box, tol=OUT_TOL)
        rep.check(inside, f"'{label}' בתוך האזור הבטוח ({name})",
                  f"'{label}' יוצא מהאזור הבטוח של {name} - יזוז פנימה או ייחתך")


def check_centring(rep, spec, lay, icc):
    for r in T.runs_for(spec, lay, icc):
        if r.angle:
            continue
        panel = lay.panel(r.panel)
        dev = r.x + r.width / 2 - panel.cx
        rep.check(abs(dev) <= CENTRE_TOL, f"'{r.visual[::-1][:20]}' ממורכז ({dev:+.1f} מ\"מ)",
                  f"'{r.visual[::-1][:20]}' סוטה {dev:+.1f} מ\"מ ממרכז ה-{r.panel}. אם זה לא מכוון - "
                  f"תקן את box", error=False)


def symmetry_axis(gray):
    """(offset of the art's mirror axis from the middle, in px; score 0-1) from column edge energy."""
    edges = np.abs(np.diff(gray.astype(np.float32), axis=1)).sum(axis=0)
    if edges.std() < 1e-3:
        return 0, 0.0                  # a flat or smooth picture has no axis to measure
    edges = (edges - edges.mean()) / edges.std()
    n, best = len(edges), (0, -1.0)
    reach = int(n * SYMMETRY_SEARCH)
    for shift in range(-reach, reach + 1):
        a = edges[max(0, 2 * shift):n + min(0, 2 * shift)]
        if len(a) <= 10 or a.std() < 1e-6:
            continue
        score = float(np.corrcoef(a, a[::-1])[0, 1])
        if score > best[1]:
            best = (shift, score)
    return best


def check_art_symmetry(rep, bitmap_path, lay):
    """Measured on the text-free bitmap (_work/cover_bitmap.jpg): type would hide the art's own axis."""
    if not bitmap_path.is_file():
        rep.warnings.append("לא נמצא _work/cover_bitmap.jpg - מרכוז הציור לא נבדק")
        return
    img, k = Image.open(bitmap_path).convert("L"), SYMMETRY_DPI / 25.4
    img = img.resize((round(img.width * SYMMETRY_DPI / 300), round(img.height * SYMMETRY_DPI / 300)))
    for name in ("front", "back"):
        b = lay.panel(name)
        x0, y0 = round((lay.bleed + b.x) * k), round((lay.bleed + lay.height - b.top) * k)
        gray = np.asarray(img.crop((x0, y0, x0 + round(b.w * k), y0 + round(b.h * k))))
        shift, score = symmetry_axis(gray)
        dev = shift / k
        if score < SYMMETRY_SCORE:
            rep.ok.append(f"ציור ה-{name} לא סימטרי (ציון {score:.2f}) - את המרכוז שלו בודקים בעין")
            continue
        rep.check(abs(dev) <= SYMMETRY_TOL, f"ציור ה-{name} ממורכז על הקרטון ({dev:+.1f} מ\"מ)",
                  f"ציור ה-{name} סימטרי סביב ציר שסוטה {dev:+.1f} מ\"מ ממרכז הקרטון. בדוק בעין "
                  f"בתצוגה עם קווי עזר (קו צהוב), והזז את הציור או את הטקסט", error=False)


def luminance(rgb):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(float(v)) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def run_box(r):
    """The run's area in sheet mm (letters roughly 0.75 em tall above the baseline)."""
    h = r.pt * T.PT_TO_MM
    if r.angle == 0:
        return G.Box(r.x, r.y - 0.2 * h, r.width, 0.95 * h)
    x = r.x - 0.75 * h if r.angle == 90 else r.x - 0.2 * h
    y = r.y if r.angle == 90 else r.y - r.width
    return G.Box(x, y, 0.95 * h, r.width)


def check_legibility(rep, bitmap_path, spec, lay, icc):
    """Contrast of each line against the picture under it, and how busy that picture is."""
    if not bitmap_path.is_file():
        return
    img, k = Image.open(bitmap_path).convert("RGB"), SYMMETRY_DPI / 25.4
    img = img.resize((round(img.width * SYMMETRY_DPI / 300), round(img.height * SYMMETRY_DPI / 300)))
    for r in T.runs_for(spec, lay, icc):
        b = run_box(r)
        x0, y0 = round((lay.bleed + b.x) * k), round((lay.bleed + lay.height - b.top) * k)
        patch = np.asarray(img.crop((x0, y0, x0 + max(1, round(b.w * k)), y0 + max(1, round(b.h * k)))), np.float32)
        text_rgb = [round(255 * c) for c in r.colour.rgb()]
        ratio = (max(luminance(text_rgb), luminance(patch.reshape(-1, 3).mean(0))) + 0.05) /                 (min(luminance(text_rgb), luminance(patch.reshape(-1, 3).mean(0))) + 0.05)
        busy = float(patch.mean(axis=2).std())
        label = r.visual[::-1][:20]
        rep.check(ratio >= MIN_CONTRAST and busy <= MAX_BUSY, f"'{label}' קריא (ניגוד {ratio:.1f})",
                  f"'{label}' עלול להיות קשה לקריאה: ניגוד {ratio:.1f} (רצוי {MIN_CONTRAST}+), רקע "
                  f"{'עמוס' if busy > MAX_BUSY else 'שקט'}. שנה צבע, הזז, או הוסף מתחתיו שטח שקט בציור", error=False)


def check_barcode(rep, page, spec, lay, o):
    zone = barcode_box(spec, lay)
    if not zone:
        return
    def overlaps(box):
        return box.x < zone.right and box.right > zone.x and box.y < zone.top and box.top > zone.y
    digits = "".join(ch for ch in str(spec["barcode"].get("isbn", "")) if ch.isdigit())
    intruders = [t.strip() for t, box in spans(page, o)
                 if overlaps(box) and t.strip() != digits and not t.strip().startswith("ISBN")]
    rep.check(not intruders, "אזור הברקוד פנוי מטקסט", f"טקסט בתוך אזור הברקוד: {intruders}")


def crop(page, box, o, dpi, path):
    h = page.rect.height * 25.4 / 72
    clip = fitz.Rect(*(v * 72 / 25.4 for v in (o + box.x, h - o - box.top, o + box.right, h - o - box.y)))
    page.get_pixmap(dpi=dpi, clip=clip).save(str(path))
    return path


def crops(page, spec, lay, o, folder):
    folder.mkdir(parents=True, exist_ok=True)
    pad = 4
    s = lay.spine
    out = [crop(page, G.Box(s.x - pad, s.y - pad, s.w + 2 * pad, s.h + 2 * pad), o, CROP_DPI, folder / "שדרה.png")]
    for name, label in (("front", "חזית"), ("back", "גב")):
        out.append(crop(page, lay.panel(name), o, 150, folder / f"{label}.png"))
    zone = barcode_box(spec, lay)
    if zone:
        out.append(crop(page, zone.inset(-pad), o, CROP_DPI, folder / "ברקוד.png"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--pdf")
    a = ap.parse_args()
    spec = S.load(a.spec)
    lay = G.layout(spec)
    pdf = Path(a.pdf) if a.pdf else B.out_paths(spec)[0]
    if not pdf.is_file():
        fail(f"קובץ הכריכה {pdf} לא נמצא. הרץ קודם build_cover.py.")
    page, o = fitz.open(pdf)[0], spec["slug"] if spec["marks"] else spec["bleed"]
    icc_path = find_icc(spec["icc"])[0] if spec["colour"] == "cmyk" else None
    icc = ImageCms.getOpenProfile(str(icc_path)) if icc_path else None
    rep = Report()
    print(f"בדיקת כריכה: {pdf}")
    check_boxes(rep, page, lay, spec)
    check_fonts(rep, page)
    check_images(rep, page, spec)
    check_text_areas(rep, page, lay, spec, o)
    check_centring(rep, spec, lay, icc)
    _, previews, work = B.out_paths(spec)
    check_art_symmetry(rep, work / "cover_bitmap.jpg", lay)
    check_legibility(rep, work / "cover_bitmap.jpg", spec, lay, icc)
    check_barcode(rep, page, spec, lay, o)
    rep.show()
    print("לבדיקה בעין:")
    print(f"  {previews / 'תצוגה פרוסה עם קווי עזר.jpg'}")
    for path in crops(page, spec, lay, o, previews / "בדיקה"):
        print(f"  {path}")
    sys.exit(1 if rep.errors else 0)


if __name__ == "__main__":
    main()
