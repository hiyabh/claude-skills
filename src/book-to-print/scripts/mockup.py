# -*- coding: utf-8 -*-
"""A simple 3D mockup of the closed book, cut from the press PDF itself (so it shows what will print).

    python mockup.py <cover_spec.json> [--pdf <cover.pdf>]

Writes <output folder>/תצוגות/הדמיה.jpg: the front cover facing the viewer, the spine turned away on
the side it really is on (right for a Hebrew book), a soft shadow, on white. For WhatsApp, a shop page
or the author's approval - not a proof of colour.
"""
import argparse
from pathlib import Path

import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

import build_cover as B
import geometry as G
import spec as S
from common import fail

DPI = 120
SPINE_SQUEEZE = 0.45        # the spine's apparent width, turned away
SPINE_SHADE = 0.72
TILT = 0.06                 # how much the far edge of the spine shrinks (share of the height)
MARGIN = 140
SHADOW_BLUR = 28


def cut(page, box, o):
    h = page.rect.height * 25.4 / 72
    clip = fitz.Rect(*(v * 72 / 25.4 for v in (o + box.x, h - o - box.top, o + box.right, h - o - box.y)))
    pix = page.get_pixmap(dpi=DPI, clip=clip)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def coeffs(src, dst):
    """Perspective coefficients that map dst quad points back to src (for Image.transform)."""
    rows, rhs = [], []
    for (x, y), (u, v) in zip(dst, src):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        rhs += [u, v]
    return np.linalg.solve(np.array(rows, float), np.array(rhs, float)).tolist()


def turned_spine(spine, height, right_side):
    w = max(2, round(spine.width * SPINE_SQUEEZE))
    t = round(height * TILT)
    near, far = (0, w) if right_side else (w, 0)
    dst = [(near, 0), (far, t), (far, height - t), (near, height)] if right_side else \
          [(far, t), (near, 0), (near, height), (far, height - t)]
    src = [(0, 0), (spine.width, 0), (spine.width, spine.height), (0, spine.height)]
    img = spine.resize((spine.width, height)).transform((w, height), Image.PERSPECTIVE, coeffs(src, dst),
                                                        Image.BICUBIC)
    mask = Image.new("L", (w, height), 0)
    ImageDraw.Draw(mask).polygon(dst, fill=255)
    return ImageEnhance.Brightness(img).enhance(SPINE_SHADE), mask


def compose(front, spine, rtl):
    sp, mask = turned_spine(spine, front.height, right_side=rtl)
    w, h = front.width + sp.width + 2 * MARGIN, front.height + 2 * MARGIN
    canvas = Image.new("RGB", (w, h), "white")
    fx = MARGIN if rtl else MARGIN + sp.width
    sx = MARGIN + front.width if rtl else MARGIN
    shadow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(shadow).rectangle((min(fx, sx) + 18, MARGIN + 26, max(fx + front.width, sx + sp.width) + 18,
                                      MARGIN + front.height + 26), fill=110)
    canvas.paste((60, 60, 60), (0, 0), shadow.filter(ImageFilter.GaussianBlur(SHADOW_BLUR)))
    canvas.paste(front, (fx, MARGIN))
    canvas.paste(sp, (sx, MARGIN), mask)
    return canvas


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
    front, spine = cut(page, lay.front, o), cut(page, lay.spine, o)
    out = B.out_paths(spec)[1] / "הדמיה.jpg"
    compose(front, spine, lay.rtl).save(out, quality=92)
    print(f"הדמיה: {out}")


if __name__ == "__main__":
    main()
