# -*- coding: utf-8 -*-
"""Bitmap pass: the cover's picture at print resolution (sheet + bleed), with no text at all.

Art can be one picture for the whole wrap (art.wrap) or one per panel (art.front / art.back /
art.spine, or art.spine_colour). A wrap picture made for what shows on the closed book (fit:
"visible") is extended into the turn-ins and the bleed by mirroring its edges. A panel picture is
centred on its BOARD, not on its strip, so the art stays centred on the closed book.
"""
import numpy as np
from PIL import Image

from common import parse_colour, px, warn
from geometry import Box

Image.MAX_IMAGE_PIXELS = None
ASPECT_WARN = 0.03


class Canvas:
    def __init__(self, spec, lay):
        self.dpi, self.b, self.h = spec["dpi"], lay.bleed, lay.height
        size = (self.px(lay.width + 2 * self.b), self.px(lay.height + 2 * self.b))
        self.img = Image.new("RGB", size, rgb(spec["background"]))

    def px(self, mm):
        return px(mm, self.dpi)

    def rect(self, box):
        """Pixel rectangle (left, top, right, bottom) of a sheet box."""
        x0, y0 = self.px(box.x + self.b), self.px(self.h + self.b - box.top)
        return x0, y0, x0 + self.px(box.w), y0 + self.px(box.h)

    def paste(self, img, box, clip=None):
        x0, y0, x1, y1 = self.rect(box)
        img = img.resize((x1 - x0, y1 - y0), Image.LANCZOS)
        layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        layer.paste(img.convert("RGBA"), (x0, y0))
        if clip is not None:
            mask = Image.new("L", self.img.size, 0)
            mask.paste(255, self.rect(clip))
            layer.putalpha(Image.fromarray(np.minimum(np.asarray(layer.getchannel("A")), np.asarray(mask))))
        self.img.paste(layer, (0, 0), layer)

    def fill(self, box, colour):
        self.img.paste(rgb(colour), self.rect(box))


def rgb(value):
    kind, v = parse_colour(value)
    if kind == "rgb":
        return v
    c, m, y, k = v
    return tuple(round(255 * (1 - ch) * (1 - k)) for ch in (c, m, y))


def cover_fit(img, w, h, name):
    """Scale to cover w x h pixels and crop the middle; warn when the shapes differ."""
    if abs(img.width / img.height - w / h) > ASPECT_WARN * w / h:
        warn(f"הציור {name} ביחס {img.width / img.height:.3f} והשטח ביחס {w / h:.3f}: הוא ייחתך. "
             f"בנה את הציור לפי template.py כדי ששום דבר חשוב לא ייחתך.")
    scale = max(w / img.width, h / img.height)
    img = img.resize((max(w, round(img.width * scale)), max(h, round(img.height * scale))), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def mirror_extend(img, left, top, right, bottom):
    a = np.asarray(img)
    return Image.fromarray(np.pad(a, ((top, bottom), (left, right), (0, 0)), mode="symmetric"))


def paint_wrap(cv, spec, lay, path):
    img = Image.open(path).convert("RGB")
    sheet = Box(-lay.bleed, -lay.bleed, lay.width + 2 * lay.bleed, lay.height + 2 * lay.bleed)
    if spec["art"].get("fit", "visible") == "sheet":
        x0, y0, x1, y1 = cv.rect(sheet)
        cv.img.paste(cover_fit(img, x1 - x0, y1 - y0, "wrap"), (0, 0))
        return
    vis = lay.visible if spec["binding"] == "hard" else Box(0, 0, lay.width, lay.height)
    if abs(img.width / img.height - sheet.w / sheet.h) < abs(img.width / img.height - vis.w / vis.h) / 3:
        warn("הציור ביחס של הקובץ המלא עם הגלישות. אם הוא נבנה כך, כתוב במפרט \"fit\": \"sheet\" - "
             "אחרת הוא ייחתך והמרכז שלו יזוז מהקרטון.")
    x0, y0, x1, y1 = cv.rect(vis)
    fitted = cover_fit(img, x1 - x0, y1 - y0, "wrap")
    full = mirror_extend(fitted, x0, y0, cv.img.width - x1, cv.img.height - y1)
    cv.img.paste(full.crop((0, 0) + cv.img.size), (0, 0))


def panel_art_box(lay, name):
    """The area a panel picture is fitted to: its board, grown evenly so it stays centred on the board."""
    board = lay.panel(name)
    extra = max(lay.wrap + lay.bleed, *(j.w for j in lay.joints))
    return Box(board.x - extra, board.y - extra, board.w + 2 * extra, board.h + 2 * extra)


def paint_panel(cv, lay, name, path):
    box = panel_art_box(lay, name)
    x0, y0, x1, y1 = cv.rect(box)
    img = cover_fit(Image.open(path).convert("RGB"), x1 - x0, y1 - y0, name)
    cv.paste(img, box, clip=lay.art_region(name))


def contain(img, box_w, box_h):
    scale = min(box_w / img.width, box_h / img.height)
    return img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)


def paint_images(cv, spec, lay):
    for item in spec["images"]:
        panel = lay.panel(item["panel"])
        x, y, w, h = item["box"]
        x = (panel.w - w) / 2 if x == "center" else x
        box = Box(panel.x + x, panel.top - y - h, w, h)
        img = Image.open(item["file"]).convert("RGBA")
        x0, y0, x1, y1 = cv.rect(box)
        small = contain(img, x1 - x0, y1 - y0)
        cv.img.paste(small, (x0 + (x1 - x0 - small.width) // 2, y0 + (y1 - y0 - small.height) // 2), small)


def render(spec, lay):
    cv, art = Canvas(spec, lay), spec["art"]
    if art.get("wrap"):
        paint_wrap(cv, spec, lay, art["wrap"])
    for name in ("front", "back"):
        if art.get(name):
            paint_panel(cv, lay, name, art[name])
    if art.get("spine"):
        region = lay.art_region("spine")
        x0, y0, x1, y1 = cv.rect(region)
        cv.paste(cover_fit(Image.open(art["spine"]).convert("RGB"), x1 - x0, y1 - y0, "spine"), region)
    elif art.get("spine_colour"):
        cv.fill(lay.art_region("spine"), art["spine_colour"])
    paint_images(cv, spec, lay)
    return cv.img
