# -*- coding: utf-8 -*-
"""Vector Hebrew type for the cover: text items from the spec -> positioned runs.

Hebrew without niqqud needs no shaping, only visual reordering (python-bidi), so the PDF draws the
visual string. Sizes shrink until the text fits its box. Ink extents come from Pillow, advances from
reportlab, so a line is centred on its real letters and a spine line on the spine's centre.
"""
from dataclasses import dataclass
from functools import lru_cache

from bidi.algorithm import get_display
from PIL import Image, ImageCms, ImageFont
from reportlab.lib.colors import CMYKColor, Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from common import fail, parse_colour, warn
from geometry import Box

PT_TO_MM = 25.4 / 72
MEASURE_PX = 400              # Pillow measuring size (px per em)
SHRINK = 0.97                 # step when a text does not fit
MIN_SCALE = 0.4               # never below 40% of the requested size
SPINE_SIDE = 1.6              # mm clear of each spine fold
SPINE_END = 12                # mm clear of the spine's head and tail
VERTICAL_BELOW_MM = 25        # spines narrower than this default to rotated text
MIN_SPINE_TEXT_MM = 5         # no spine text below this width
DEFAULT_COLOUR = "cmyk 0 0 0 100"


@dataclass
class Run:
    visual: str
    font: str                 # font key (registered under that name)
    pt: float
    x: float                  # start of the visual string, at the baseline (sheet mm)
    y: float
    angle: int                # 0, 90 (reads top-down, tops to the left) or -90
    colour: object
    panel: str
    width: float              # advance, mm


def register(fonts):
    for key, path in fonts.items():
        pdfmetrics.registerFont(TTFont(key, path))


def check_glyphs(text, key):
    face = pdfmetrics.getFont(key).face
    missing = sorted({ch for ch in text if not ch.isspace() and ord(ch) not in face.charToGlyph})
    if missing:
        names = " ".join(f"'{ch}' (U+{ord(ch):04X})" for ch in missing)
        fail(f"בגופן '{key}' חסרים התווים {names} בטקסט '{text}'. החלף גופן או תו "
             f"(למשל ״ במקום \" או להפך) - אחרת יודפס ריבוע ריק.")


def width_mm(visual, key, size):
    return pdfmetrics.stringWidth(visual, key, size) * PT_TO_MM


@lru_cache(maxsize=None)
def _pil_font(path):
    return ImageFont.truetype(path, MEASURE_PX)


def ink(visual, path, size):
    """(above, below) the baseline in mm, from the real letters."""
    left, top, right, bottom = _pil_font(path).getbbox(visual, anchor="ls")
    scale = size * PT_TO_MM / MEASURE_PX
    return -top * scale, bottom * scale


def pdf_colour(value, mode, icc):
    kind, v = parse_colour(value)
    if kind == mode or (kind == "cmyk" and mode == "rgb" and icc is None):
        return CMYKColor(*v) if kind == "cmyk" else Color(*(c / 255 for c in v))
    pixel = Image.new("CMYK" if kind == "cmyk" else "RGB", (1, 1),
                      tuple(round(c * 255) for c in v) if kind == "cmyk" else v)
    srgb = ImageCms.createProfile("sRGB")
    src, dst, out = (icc, srgb, "RGB") if kind == "cmyk" else (srgb, icc, "CMYK")
    got = ImageCms.profileToProfile(pixel, src, dst, outputMode=out).getpixel((0, 0))
    return Color(*(c / 255 for c in got)) if out == "RGB" else CMYKColor(*(c / 255 for c in got))


def panel_box(item, panel, safe):
    """The item's box in sheet mm. 'box' = [x, y, w, h] from the panel's top-left corner."""
    if "box" not in item:
        return panel.inset(safe)
    x, y, w, h = item["box"]
    if x == "center":                 # centred on the board, whatever its width
        x = (panel.w - w) / 2
    return Box(panel.x + x, panel.top - y - h, w, h)


def wrap_words(text, key, size, max_w):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            trial = f"{cur} {word}".strip()
            if cur and width_mm(get_display(trial), key, size) > max_w:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        lines.append(cur)
    return lines


def block_fits(lines, key, path, size, box, leading):
    widths = [width_mm(get_display(line), key, size) for line in lines]
    above = ink(get_display(lines[0]), path, size)[0]
    below = ink(get_display(lines[-1]), path, size)[1]
    height = above + below + (len(lines) - 1) * leading * size * PT_TO_MM
    return max(widths) <= box.w and height <= box.h, height, above


def fit_block(item, key, path, box):
    size, leading = float(item["size"]), float(item.get("leading", 1.25))
    floor = size * MIN_SCALE
    while size >= floor:
        lines = wrap_words(item["text"], key, size, box.w) if item.get("wrap", True) else item["text"].split("\n")
        ok, height, above = block_fits(lines, key, path, size, box, leading)
        if ok:
            return lines, size, height, above
        size *= SHRINK
    fail(f"הטקסט '{item['text'][:30]}' לא נכנס לתיבה שלו ({box.w:.0f}x{box.h:.0f} מ\"מ) "
         f"גם ב-{floor:.0f} נק'. הגדל את התיבה או קצר את הטקסט.")


def block_top(item, box, height):
    valign = item.get("valign", "top")
    if valign == "middle":
        return box.cy + height / 2
    return box.y + height if valign == "bottom" else box.top


def line_x(align, box, w):
    if align == "right":
        return box.right - w
    return box.x if align == "left" else box.cx - w / 2


def horizontal(item, spec, lay, colour):
    key = item["font"]
    panel = lay.panel(item["panel"])
    safe = SPINE_SIDE if item["panel"] == "spine" else spec["safe"]
    box = panel_box(item, panel, safe)
    if item["panel"] == "spine" and "box" not in item:
        box = Box(panel.x + SPINE_SIDE, panel.y + SPINE_END, panel.w - 2 * SPINE_SIDE, panel.h - 2 * SPINE_END)
    lines, size, height, above = fit_block(item, key, spec["fonts"][key], box)
    base, step, runs = block_top(item, box, height) - above, float(item.get("leading", 1.25)) * size * PT_TO_MM, []
    for line in lines:
        vis = get_display(line)
        w = width_mm(vis, key, size)
        runs.append(Run(vis, key, size, line_x(item.get("align", "center"), box, w), base, 0, colour, item["panel"], w))
        base -= step
    return runs


def spine_span(item, spine):
    """(top, length) along the spine in sheet mm. 'box' = [from_top, length] for a rotated line."""
    if "box" in item:
        from_top, length = item["box"][:2]
        return spine.top - from_top, length
    return spine.top - SPINE_END, spine.h - 2 * SPINE_END


def vertical(item, spec, lay, colour):
    key, path, spine = item["font"], spec["fonts"][item["font"]], lay.spine
    top, length = spine_span(item, spine)
    across, size = spine.w - 2 * SPINE_SIDE, float(item["size"])
    vis = get_display(item["text"].replace("\n", "  "))
    while True:
        above, below = ink(vis, path, size)
        w = width_mm(vis, key, size)
        if w <= length and above + below <= across:
            break
        size *= SHRINK
        if size < float(item["size"]) * MIN_SCALE:
            fail(f"הטקסט '{item['text'][:30]}' לא נכנס לשדרה ({spine.w:.1f} מ\"מ). קצר אותו או הקטן גופן.")
    pos = item.get("position", "middle")
    centre = {"top": top - w / 2, "bottom": top - length + w / 2}.get(pos, top - length / 2)
    down = spec.get("spine_reading", "top-down") == "top-down"
    angle = (90 if lay.rtl else -90) if down else (-90 if lay.rtl else 90)
    mid = (above - below) / 2           # ink centre above the baseline
    x = spine.cx + mid if angle == 90 else spine.cx - mid
    y = centre - w / 2 if angle == 90 else centre + w / 2
    return [Run(vis, key, size, x, y, angle, colour, "spine", w)]


def runs_for(spec, lay, icc=None):
    register(spec["fonts"])
    out = []
    for item in spec["text"]:
        if item["panel"] == "spine" and lay.spine.w < MIN_SPINE_TEXT_MM:
            warn(f"השדרה {lay.spine.w:g} מ\"מ - צרה מ-{MIN_SPINE_TEXT_MM} מ\"מ, ולכן '{item['text'][:20]}' לא נכתב עליה.")
            continue
        check_glyphs(item["text"], item["font"])
        colour = pdf_colour(item.get("colour", DEFAULT_COLOUR), spec["colour"], icc)
        orient = item.get("orient") or ("vertical" if lay.spine.w < VERTICAL_BELOW_MM else "horizontal")
        rotated = item["panel"] == "spine" and orient == "vertical"
        out += vertical(item, spec, lay, colour) if rotated else horizontal(item, spec, lay, colour)
    return out
