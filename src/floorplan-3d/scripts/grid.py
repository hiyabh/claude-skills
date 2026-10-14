"""Draw a labelled coordinate grid over a crop of the sheet.

Vision models read positions badly from a bare drawing but well from a grid:
"the corner sits on the 3.40 line". So every crop Claude looks at carries grid
lines labelled in world metres (when the frame is known) or sheet pixels.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from common import has_world, to_px, to_world

MAX_SIDE = 1400            # Claude's image reader downsizes anything larger
GRID_COLOUR = (0, 140, 255, 110)
MAJOR_COLOUR = (230, 40, 90, 170)
LABEL_BG = (255, 255, 255, 215)
LABEL_FG = (200, 20, 70, 255)
NICE_STEPS = (0.05, 0.1, 0.2, 0.25, 0.5, 1.0, 2.0, 5.0)
TARGET_LINES = 14          # aim for about this many grid lines across the crop
LABEL_GAP_PX = 64          # label only every n-th line so labels never collide


def font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def nice_step(span: float) -> float:
    raw = span / TARGET_LINES
    return min(NICE_STEPS, key=lambda s: abs(math.log(s / raw)))


def _lines(lo: float, hi: float, step: float) -> list[float]:
    start = math.ceil(lo / step) * step
    count = int((hi - start) / step) + 1
    return [round(start + i * step, 4) for i in range(max(count, 0))]


def _label(draw: ImageDraw.ImageDraw, xy, text: str, size: int, anchor: str) -> None:
    """Centre the label ON its line (anchor mt / lm) so nobody reads the label edge as the line."""
    f = font(size)
    box = draw.textbbox(xy, text, font=f, anchor=anchor)
    draw.rectangle((box[0] - 2, box[1] - 1, box[2] + 2, box[3] + 1), fill=LABEL_BG, outline=LABEL_FG)
    draw.text(xy, text, font=f, fill=LABEL_FG, anchor=anchor)


def _stride(step_px: float) -> int:
    return max(1, math.ceil(LABEL_GAP_PX / max(step_px, 1e-6)))


def _world_grid(draw, frame, box, zoom, step) -> None:
    x0, y0, x1, y1 = box
    wx0, wy1 = to_world(frame, (x0, y0))
    wx1, wy0 = to_world(frame, (x1, y1))
    stride = _stride(step * frame["px_per_m"] * zoom)
    for wx in _lines(wx0, wx1, step):
        px = (to_px(frame, (wx, 0))[0] - x0) * zoom
        labelled = abs(wx / (step * stride) - round(wx / (step * stride))) < 1e-6
        draw.line((px, 0, px, (y1 - y0) * zoom), fill=MAJOR_COLOUR if labelled else GRID_COLOUR, width=1)
        if labelled:
            _label(draw, (px, 2), f"x{wx:.2f}", 15, "mt")
    for wy in _lines(wy0, wy1, step):
        py = (to_px(frame, (0, wy))[1] - y0) * zoom
        labelled = abs(wy / (step * stride) - round(wy / (step * stride))) < 1e-6
        draw.line((0, py, (x1 - x0) * zoom, py), fill=MAJOR_COLOUR if labelled else GRID_COLOUR, width=1)
        if labelled:
            _label(draw, (2, py), f"y{wy:.2f}", 15, "lm")


def _pixel_grid(draw, box, zoom, step) -> None:
    x0, y0, x1, y1 = box
    for px in _lines(x0, x1, step):
        draw.line(((px - x0) * zoom, 0, (px - x0) * zoom, (y1 - y0) * zoom), fill=GRID_COLOUR, width=1)
        _label(draw, ((px - x0) * zoom, 2), f"px{int(px)}", 14, "mt")
    for py in _lines(y0, y1, step):
        draw.line((0, (py - y0) * zoom, (x1 - x0) * zoom, (py - y0) * zoom), fill=GRID_COLOUR, width=1)
        _label(draw, (2, (py - y0) * zoom), f"py{int(py)}", 14, "lm")


def render(sheet: Image.Image, frame: dict, box, out: Path, step: float | None = None) -> Path:
    """Crop box (sheet pixels), scale to fit MAX_SIDE, overlay the grid, save."""
    x0, y0, x1, y1 = (int(v) for v in box)
    crop = sheet.crop((x0, y0, x1, y1)).convert("RGBA")
    zoom = min(MAX_SIDE / crop.width, MAX_SIDE / crop.height, 4.0)
    crop = crop.resize((max(1, int(crop.width * zoom)), max(1, int(crop.height * zoom))), Image.LANCZOS)
    layer = Image.new("RGBA", crop.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    if has_world(frame):
        span_m = (x1 - x0) / frame["px_per_m"]
        _world_grid(draw, frame, (x0, y0, x1, y1), zoom, step or nice_step(span_m))
    else:
        _pixel_grid(draw, (x0, y0, x1, y1), zoom, step or nice_step((x1 - x0) / 100) * 100)
    Image.alpha_composite(crop, layer).convert("RGB").save(out)
    return out
