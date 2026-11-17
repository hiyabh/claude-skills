# -*- coding: utf-8 -*-
"""Vector pass: the press PDF - the bitmap, vector type, barcode, TrimBox/BleedBox, crop and fold marks."""
from reportlab import rl_config
from reportlab.lib.colors import CMYKColor, Color
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

import barcode as EAN
from common import fail
from geometry import Box

rl_config.useA85 = 0           # raw binary streams: ASCII85 only inflates the bitmap by a quarter
MARK_LEN, MARK_PT = 6, 0.25
REGISTRATION = CMYKColor(1, 1, 1, 1)
BLACK_100K = CMYKColor(0, 0, 0, 1)
WHITE = CMYKColor(0, 0, 0, 0)
BARCODE_EDGE = 10              # mm from the spine fold / outer edge and from the bottom
BARCODE_TEXT_PT = 9
BAR_MODULE_MM = 0.33           # EAN-13 at 100% (37.3 x 25.9 mm)


def barcode_box(spec, lay):
    """The barcode zone on the back cover, or None."""
    bc = spec.get("barcode")
    if not bc:
        return None
    w, h = bc.get("zone", [40, 25])
    edge, back = bc.get("edge", BARCODE_EDGE), lay.back
    spine_side_left = back.x > lay.spine.x
    pos = bc.get("position", "spine-bottom")
    if pos == "centre-bottom":
        x = back.cx - w / 2
    elif (pos == "spine-bottom") == spine_side_left:
        x = back.x + edge
    else:
        x = back.right - edge - w
    return Box(x, back.y + edge, w, h)


class Press:
    def __init__(self, path, spec, lay):
        self.s, self.lay = spec, lay
        self.o = spec["slug"] if spec["marks"] else spec["bleed"]
        page = ((lay.width + 2 * self.o) * mm, (lay.height + 2 * self.o) * mm)
        first_font = next(iter(spec["fonts"]))
        self.label_font = first_font
        self.c = canvas.Canvas(path, pagesize=page, initialFontName=first_font, initialFontSize=7)
        o, b = self.o, spec["bleed"]
        self.c.setTrimBox((o * mm, o * mm, (o + lay.width) * mm, (o + lay.height) * mm))
        self.c.setBleedBox(((o - b) * mm, (o - b) * mm, (o + lay.width + b) * mm, (o + lay.height + b) * mm))
        self.cmyk = spec["colour"] == "cmyk"

    def image(self, path):
        b, lay = self.s["bleed"], self.lay
        self.c.drawImage(path, (self.o - b) * mm, (self.o - b) * mm, (lay.width + 2 * b) * mm, (lay.height + 2 * b) * mm)

    def run(self, r):
        c = self.c
        c.saveState()
        c.translate((self.o + r.x) * mm, (self.o + r.y) * mm)
        c.rotate(r.angle)
        c.setFillColor(r.colour)
        t = c.beginText(0, 0)
        t.setFont(r.font, r.pt)
        t.textOut(r.visual)
        c.drawText(t)
        c.restoreState()

    def colour(self, cmyk):
        return cmyk if self.cmyk else Color(*(1 - min(1, ch + cmyk.black) for ch in (cmyk.cyan, cmyk.magenta, cmyk.yellow)))

    def barcode(self, box):
        bc = self.s["barcode"]
        if bc.get("fill", "white") == "white":
            self.c.setFillColor(self.colour(WHITE))
            self.c.rect((self.o + box.x) * mm, (self.o + box.y) * mm, box.w * mm, box.h * mm, stroke=0, fill=1)
        if bc.get("isbn"):
            self.ean13(bc["isbn"], box)

    def ean13(self, isbn, box):
        if not EAN.valid(isbn):
            fail(f"המסת\"ב {isbn} לא תקין (13 ספרות עם ספרת ביקורת נכונה). העתק אותו שוב מהספרייה הלאומית.")
        digits = "".join(str(d) for d in EAN.digits_of(isbn))
        module = min(BAR_MODULE_MM, box.w / (EAN.MODULES + EAN.QUIET_LEFT + EAN.QUIET_RIGHT))
        left = box.cx - EAN.MODULES * module / 2
        bottom, height = box.y + box.h * 0.20, box.h * 0.58
        self.c.setFillColor(self.colour(BLACK_100K))
        for start, width, guard in EAN.bars(isbn):
            extra = box.h * 0.06 if guard else 0
            self.c.rect((self.o + left + start * module) * mm, (self.o + bottom - extra) * mm,
                        width * module * mm, (height + extra) * mm, stroke=0, fill=1)
        self.c.setFont(self.label_font, BARCODE_TEXT_PT)
        pretty = f"ISBN {digits[:3]}-{digits[3:-1]}-{digits[-1]}"
        self.c.drawCentredString((self.o + box.cx) * mm, (self.o + box.y + box.h * 0.84) * mm, pretty)
        self.c.drawCentredString((self.o + box.cx) * mm, (self.o + box.y + box.h * 0.04) * mm, digits)

    def line(self, x0, y0, x1, y1):
        self.c.line((self.o + x0) * mm, (self.o + y0) * mm, (self.o + x1) * mm, (self.o + y1) * mm)

    def marks(self, label):
        if not self.s["marks"]:
            return
        c, lay = self.c, self.lay
        a = self.s["bleed"] + 1
        z = a + MARK_LEN
        c.setStrokeColor(self.colour(REGISTRATION))
        c.setLineWidth(MARK_PT)
        for x, sx in ((0, -1), (lay.width, 1)):
            for y, sy in ((0, -1), (lay.height, 1)):
                self.line(x + sx * a, y, x + sx * z, y)
                self.line(x, y + sy * a, x, y + sy * z)
        xs, ys = lay.folds()
        for x in xs:
            self.line(x, -a, x, -z)
            self.line(x, lay.height + a, x, lay.height + z)
        for y in ys:
            self.line(-a, y, -z, y)
            self.line(lay.width + a, y, lay.width + z, y)
        c.setFillColor(self.colour(REGISTRATION))
        c.setFont(self.label_font, 7)
        c.drawCentredString((self.o + lay.width / 2) * mm, 3 * mm, label)      # already visual

    def save(self):
        self.c.showPage()
        self.c.save()
