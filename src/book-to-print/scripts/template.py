# -*- coding: utf-8 -*-
"""A to-scale cover template for a designer or an image generator, plus the measurements in mm and px.

    python template.py <cover_spec.json> [--dpi 300]

Writes next to the spec, in "תבנית כריכה/":
    תבנית כריכה.png          full size (sheet + bleed) with every zone drawn and named
    מידות הכריכה.txt          every measurement, and the pixel size of each area at the dpi
The spec needs only trim, pages, binding, printer and (for a hard cover) the bindery's numbers.
"""
import argparse
from pathlib import Path

from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont

import geometry as G
import spec as S
from art import panel_art_box
from common import FONTS_DIR, px
from press import barcode_box

COLOURS = {"bleed": (255, 205, 210), "turn_in": (255, 228, 190), "board": (255, 255, 255),
           "joint": (215, 215, 215), "spine": (205, 230, 255), "safe": (40, 170, 70), "trim": (220, 30, 30),
           "fold": (0, 150, 220), "barcode": (220, 0, 180), "centre": (200, 160, 0), "ink": (40, 40, 40)}
LABEL_FONT = FONTS_DIR / "FrankRuhlLibre[wght].ttf"
LINE = 4


class Sheet:
    def __init__(self, lay, dpi):
        self.lay, self.dpi, self.b = lay, dpi, lay.bleed
        self.img = Image.new("RGB", (px(lay.width + 2 * self.b, dpi), px(lay.height + 2 * self.b, dpi)),
                             COLOURS["bleed"])
        self.d = ImageDraw.Draw(self.img)

    def rect(self, box):
        x0, y0 = px(box.x + self.b, self.dpi), px(self.lay.height + self.b - box.top, self.dpi)
        return x0, y0, x0 + px(box.w, self.dpi), y0 + px(box.h, self.dpi)

    def fill(self, box, colour):
        self.d.rectangle(self.rect(box), fill=colour)

    def outline(self, box, colour, width=LINE):
        self.d.rectangle(self.rect(box), outline=colour, width=width)

    def label(self, box, text, size_mm=6, dy=0.0):
        font = ImageFont.truetype(str(LABEL_FONT), px(size_mm, self.dpi))
        x0, y0, x1, y1 = self.rect(box)
        self.d.text(((x0 + x1) / 2, (y0 + y1) / 2 + px(dy, self.dpi)), get_display(text), font=font,
                    fill=COLOURS["ink"], anchor="mm")

    def vline(self, x, colour):
        x_px = px(x + self.b, self.dpi)
        for y in range(0, self.img.height, px(6, self.dpi)):
            self.d.line((x_px, y, x_px, y + px(3, self.dpi)), fill=colour, width=LINE)


def draw(sheet, spec, lay):
    sheet.fill(G.Box(0, 0, lay.width, lay.height), COLOURS["turn_in"] if lay.wrap else COLOURS["board"])
    for box in lay.joints:
        if box.w:
            sheet.fill(box, COLOURS["joint"])
    sheet.fill(lay.front, COLOURS["board"])
    sheet.fill(lay.back, COLOURS["board"])
    sheet.fill(lay.spine, COLOURS["spine"])
    for box in (lay.front, lay.back):
        sheet.outline(box.inset(spec["safe"]), COLOURS["safe"])
    for box in (lay.front, lay.back, lay.spine) + lay.joints:
        if box.w:
            sheet.outline(box, COLOURS["fold"])
    sheet.outline(G.Box(0, 0, lay.width, lay.height), COLOURS["trim"])
    for box in (lay.front, lay.back, lay.spine):
        sheet.vline(box.cx, COLOURS["centre"])
    zone = barcode_box(spec, lay)
    if zone:
        sheet.outline(zone, COLOURS["barcode"])
        sheet.label(zone, "ברקוד", 5)


def labels(sheet, spec, lay):
    sheet.label(lay.front, "חזית", 18)
    sheet.label(lay.front, "הקו הירוק: אזור בטוח לטקסט", 5, dy=16)
    sheet.label(lay.back, "גב", 18)
    sheet.label(lay.back, "הקו הצהוב: מרכז הלוח", 5, dy=16)
    top = G.Box(0, lay.height - max(lay.wrap, 8), lay.width, max(lay.wrap, 8))
    note = "גלישה - מתקפלת אל מאחורי הקרטון" if lay.wrap else "קו אדום: קו החיתוך. הוורוד מסביב נחתך"
    sheet.label(top, note, 4)


def measurements(spec, lay, dpi):
    def row(name, box):
        return f"{name}: {box.w:.1f} x {box.h:.1f} מ\"מ = {px(box.w, dpi)} x {px(box.h, dpi)} פיקסלים"
    full = G.Box(0, 0, lay.width + 2 * lay.bleed, lay.height + 2 * lay.bleed)
    lines = [f"כריכה {'קשה' if spec['binding'] == 'hard' else 'רכה'}, {spec['pages']} עמודים, "
             f"דף {spec['trim'][0]:g}x{spec['trim'][1]:g} מ\"מ, כיוון {spec['direction']}",
             f"שדרה {lay.spine.w:g} מ\"מ ({spec['spine_source']})", f"רזולוציה {dpi} dpi", "",
             "גודל הציור לפי הדרך שבה הוא ניתן במפרט:",
             row('  ציור אחד לכל הפריסה, "fit": "visible" (ברירת המחדל) - מה שנראה על הספר הסגור',
                 lay.visible if lay.wrap else G.Box(0, 0, lay.width, lay.height)),
             row('  ציור אחד לכל הפריסה, "fit": "sheet" - כל הקובץ כולל הגלישות', full),
             row("  ציור לחזית בלבד (art.front), ממורכז על הקרטון", panel_art_box(lay, "front")),
             row("  ציור לגב בלבד (art.back)", panel_art_box(lay, "back")), "",
             row("קרטון/דף החזית", lay.front), row("קרטון/דף הגב", lay.back), row("שדרה", lay.spine)]
    if spec["estimated"]:
        lines += ["", "ערכים משוערים (לבקש מבית הדפוס):"] + [f"  {S.estimate_text(e)}" for e in spec["estimated"]]
    lines += ["", "בספר עברי החזית בצד שמאל של הקובץ והגב בצד ימין." if lay.rtl else "LTR: front on the right."]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--dpi", type=int, default=300)
    a = ap.parse_args()
    spec = S.load(a.spec)
    lay = G.layout(spec)
    sheet = Sheet(lay, a.dpi)
    draw(sheet, spec, lay)
    labels(sheet, spec, lay)
    out = Path(spec["spec_path"]).parent / "תבנית כריכה"
    out.mkdir(exist_ok=True)
    sheet.img.save(out / "תבנית כריכה.png", dpi=(a.dpi, a.dpi))
    (out / "מידות הכריכה.txt").write_text(measurements(spec, lay, a.dpi), encoding="utf-8")
    print(measurements(spec, lay, a.dpi))
    print(f"תבנית: {out / 'תבנית כריכה.png'}")


if __name__ == "__main__":
    main()
