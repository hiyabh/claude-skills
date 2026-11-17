# -*- coding: utf-8 -*-
"""Press-ready cover PDF from a spec, plus flat previews (clean and with guides).

    python build_cover.py <cover_spec.json>

Output: <spec folder>/לדפוס/<title> - כריכה לדפוס.pdf (the folder that goes to the printer; "output"
in the spec can change it), and, outside it, <spec folder>/תצוגות/ (previews, crops, mockup) and _work/.
One folder per edition: two specs in one folder would overwrite each other.
Guides: red = trim, cyan = folds, green = safe area, magenta = barcode zone, yellow = panel centres.
Every word is vector type in an embedded font; the picture under it has no text.
"""
import sys
from pathlib import Path

import fitz
from bidi.algorithm import get_display
from PIL import Image, ImageCms, ImageDraw

import art
import geometry as G
import spec as S
import typeset as T
from common import fail, find_icc, safe_name, warn
from press import Press, barcode_box

JPEG_QUALITY = 95
PREVIEW_DPI = 110
GUIDES = {"trim": (255, 40, 40), "fold": (0, 210, 255), "safe": (90, 230, 90), "barcode": (255, 0, 200),
          "centre": (255, 220, 0)}


def out_paths(spec):
    out = spec.get("output", {})
    folder = Path(out.get("folder") or Path(spec["spec_path"]).parent / "לדפוס")
    if not folder.is_absolute():
        folder = Path(spec["spec_path"]).parent / folder
    name = safe_name(out.get("name") or f"{spec.get('title', 'ספר')} - כריכה לדפוס.pdf")
    base = Path(spec["spec_path"]).parent          # previews and work files stay OUT of the printer's folder
    previews, work = base / "תצוגות", base / "_work"
    for d in (folder, previews, work):
        d.mkdir(parents=True, exist_ok=True)
    return folder / name, previews, work


def label(spec, lay):
    parts = [spec.get("title", ""), f"גיליון {lay.width:g}x{lay.height:g} מ״מ", f"שדרה {lay.spine.w:g}"]
    if spec["binding"] == "hard":
        h = spec["hard"]
        parts += [f"קרטון {h['board'][0]:g}x{h['board'][1]:g}", f"ביג {h['joint']:g}", f"גלישה {h['wrap']:g}"]
    parts += [f"גלישה לחיתוך {spec['bleed']:g}", f"{spec['pages']} עמ׳"]
    return "  |  ".join(get_display(p) for p in reversed(parts) if p)     # visual order, right to left


def bitmap(spec, lay, work, icc_path):
    rgb = art.render(spec, lay)
    path = work / "cover_bitmap.jpg"
    if spec["colour"] == "cmyk":
        srgb = ImageCms.createProfile("sRGB")
        rgb = ImageCms.profileToProfile(rgb, srgb, str(icc_path), renderingIntent=0, outputMode="CMYK")
    rgb.save(path, quality=JPEG_QUALITY, dpi=(spec["dpi"],) * 2)
    return path


def box_px(box, k, o, height):
    return ((o + box.x) * k, height - (o + box.top) * k, (o + box.right) * k, height - (o + box.y) * k)


def guides(img, spec, lay, o):
    d, k, h = ImageDraw.Draw(img), PREVIEW_DPI / 25.4, img.height
    d.rectangle(box_px(G.Box(0, 0, lay.width, lay.height), k, o, h), outline=GUIDES["trim"], width=2)
    for box in (lay.front, lay.back, lay.spine) + lay.joints:
        if box.w > 0:
            d.rectangle(box_px(box, k, o, h), outline=GUIDES["fold"], width=2)
    for box in (lay.front, lay.back):
        d.rectangle(box_px(box.inset(spec["safe"]), k, o, h), outline=GUIDES["safe"], width=1)
    for box in (lay.front, lay.back, lay.spine):
        x = (o + box.cx) * k
        for y in range(int((o + box.y) * k), int((o + box.top) * k), 14):
            d.line((x, h - y, x, h - y - 7), fill=GUIDES["centre"], width=1)
    zone = barcode_box(spec, lay)
    if zone:
        d.rectangle(box_px(zone, k, o, h), outline=GUIDES["barcode"], width=3)
    return img


def previews(spec, lay, pdf_path, folder, o):
    page = fitz.open(pdf_path)[0]
    pix = page.get_pixmap(dpi=PREVIEW_DPI)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    clean, guided = folder / "תצוגה פרוסה.jpg", folder / "תצוגה פרוסה עם קווי עזר.jpg"
    img.save(clean, quality=90)
    guides(img, spec, lay, o).save(guided, quality=90)
    return clean, guided


def build(spec_path):
    spec = S.load(spec_path)
    if spec["missing_art"]:
        fail(f"קובץ הציור לא נמצא: {', '.join(spec['missing_art'])}. בדוק את הנתיב ב-art במפרט.")
    lay = G.layout(spec)
    icc_path, icc_note = find_icc(spec["icc"]) if spec["colour"] == "cmyk" else (None, "RGB")
    icc = ImageCms.getOpenProfile(str(icc_path)) if icc_path else None
    runs = T.runs_for(spec, lay, icc)
    pdf_path, preview_dir, work = out_paths(spec)
    press = Press(str(pdf_path), spec, lay)
    press.image(str(bitmap(spec, lay, work, icc_path)))
    zone = barcode_box(spec, lay)
    if zone:
        press.barcode(zone)
        if not spec["barcode"].get("isbn") and spec["barcode"].get("fill", "white") == "white":
            warn("אין מסת\"ב, ובכל זאת יודפס בגב ריבוע לבן ריק. כתוב \"fill\": \"clear\" כדי רק לשמור את המקום.")
    for r in runs:
        press.run(r)
    press.marks(label(spec, lay))
    press.save()
    clean, guided = previews(spec, lay, pdf_path, preview_dir, press.o)
    report(spec, lay, pdf_path, clean, guided, icc_note)


def report(spec, lay, pdf_path, clean, guided, icc_note):
    print(f"כריכה: {pdf_path}")
    print(f"  גיליון {lay.width:g}x{lay.height:g} מ\"מ, שדרה {lay.spine.w:g} מ\"מ ({spec['spine_source']}), "
          f"צבע {spec['colour'].upper()} ({icc_note}), {pdf_path.stat().st_size / 1e6:.1f} MB")
    print(f"  תצוגה: {clean}")
    print(f"  עם קווי עזר: {guided}")
    for line in spec["estimated"]:
        warn(f"ערך משוער, לא מבית הדפוס: {S.estimate_text(line)}. לבקש מבית הדפוס ולעדכן את המפרט.")
    print("הבא: python check_cover.py <spec> - ואז לפתוח את התצוגות ואת חיתוכי הזום ולבדוק בעין.")


def main():
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if len(sys.argv) == 2 else 1)
    build(sys.argv[1])


if __name__ == "__main__":
    main()
