"""Split every poster into animatable layers.

    python split_layers.py <project>                 # AI when models exist
    python split_layers.py <project> --lite          # OpenCV only, no models
    python split_layers.py <project> --aspect 9:16   # canvas (default 4:5)

For each poster p<N> writes, all at the canvas size so the composition stacks
them with `inset: 0` and no offsets:

  assets/layers/pN/poster.png   the poster, cover-cropped to the canvas
  assets/layers/pN/plate.png    clean paper - ink, object and accents removed
  assets/layers/pN/ink.png      RGBA text and line art, anti-aliased
  assets/layers/pN/object.png   RGBA main object (absent if none was found)
  assets/layers/pN/aK.png       RGBA crop of each small colour accent

and one layers.json for the project, plus layers_sheet.png to eyeball:
poster | plate | ink | object per row. Look at the sheet before step 4 -
a ghost of the text on the plate, or text inside the object, is fixed here
(see references/layering.md), not in the composition.
"""

import os

import cv2
import numpy as np

import pm_masks as M
import pm_models
from pm_common import CANVAS, DEFAULT_ASPECT, flag, list_posters, poster_id, \
    project_arg, write_json

PLATE_GROW_FRAC = 0.006      # hole margin beyond each removed layer
SHADOW_FRAC = 0.025          # extra hole below an object for its contact shadow
GRAIN_SEED = 7
SHEET_THUMB_W = 180
CHECKER = 12
OBJECT_ALPHA_MIN = 0.5
INK_OFF_OBJECT_PX = 3
ACCENT_ALPHA_FROM = 0.5


def load_rgb(path, w, h):
    bgr = cv2.imread(path, cv2.IMREAD_COLOR)
    if bgr is None:
        raise SystemExit(f"cannot read {path}")
    return M.to_canvas(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), w, h)


def save_rgb(path, rgb):
    cv2.imwrite(path, cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))


def save_rgba(path, rgba):
    cv2.imwrite(path, cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))


def object_alpha(fg, ink, accents_mask, ai_alpha):
    """0..1 matte of the object with the ink cut out of it."""
    if ai_alpha is not None:
        alpha = ai_alpha
    else:
        alpha = M.feather(M.object_mask_lite(fg, ink, accents_mask))
    k = np.ones((2 * INK_OFF_OBJECT_PX + 1,) * 2, np.uint8)
    no_ink = ~cv2.dilate(ink.astype(np.uint8), k).astype(bool)
    alpha = alpha * no_ink * ~accents_mask
    if (alpha > OBJECT_ALPHA_MIN).mean() < M.OBJECT_MIN_AREA:
        return None
    return alpha


def plate_hole(ink, alpha, accents_mask, h):
    hole = ink | accents_mask
    if alpha is not None:
        obj = alpha > 0.05
        shadow = int(h * SHADOW_FRAC)
        below = np.zeros_like(obj)
        below[shadow:] = obj[:-shadow]
        hole |= obj | below
    k = max(3, int(h * PLATE_GROW_FRAC) * 2 + 1)
    return cv2.dilate(hole.astype(np.uint8), np.ones((k, k), np.uint8)).astype(bool)


def lite_fill(rgb, paper, hole):
    """Smooth paper estimate plus grain matched to the real paper."""
    residual = rgb.astype(np.float32) - cv2.GaussianBlur(rgb, (0, 0), 2).astype(np.float32)
    std = residual[~hole].std(axis=0) if (~hole).any() else np.zeros(3)
    rng = np.random.default_rng(GRAIN_SEED)
    grain = rng.normal(0, 1, rgb.shape).astype(np.float32) * std
    fill = np.clip(paper.astype(np.float32) + grain, 0, 255).astype(np.uint8)
    soft = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), 1.5)[..., None]
    return (fill * soft + rgb * (1 - soft)).astype(np.uint8)


def _colour_region(img_lab, paper_lab, box):
    """Soft mask of the coloured shape inside an accent box - without it, paper
    variation inside the box shows as a faint rectangle when the accent flies."""
    x, y, w, h = box
    il, pl = img_lab[y:y + h, x:x + w], paper_lab[y:y + h, x:x + w]
    chroma = np.hypot(il[..., 1], il[..., 2]) - np.hypot(pl[..., 1], pl[..., 2])
    region = (chroma > M.ACCENT_CHROMA * ACCENT_ALPHA_FROM).astype(np.uint8)
    region = cv2.dilate(region, np.ones((5, 5), np.uint8)).astype(np.float32)
    return cv2.GaussianBlur(region, (0, 0), 1.5)


def write_accents(folder, rgb, paper_lab, img_lab, boxes):
    """Each accent as a cropped RGBA, alpha from its distance to the paper."""
    out = []
    dist = M.delta_e(img_lab, paper_lab)
    for k, (x, y, w, h) in enumerate(boxes, 1):
        crop = np.zeros((h, w, 4), np.uint8)
        crop[..., :3] = rgb[y:y + h, x:x + w]
        # Pale watercolour accents sit barely above FG_DE; start the ramp at half
        # of it or they come out as faint smudges. Paper itself is under ~4.
        a = np.clip((dist[y:y + h, x:x + w] - ACCENT_ALPHA_FROM * M.FG_DE) / M.FG_DE, 0, 1)
        crop[..., 3] = (a * _colour_region(img_lab, paper_lab, (x, y, w, h)) * 255).astype(np.uint8)
        name = f"a{k}.png"
        save_rgba(os.path.join(folder, name), crop)
        out.append({"file": name, "bbox": [x, y, w, h]})
    return out


def box_of(mask):
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1),
            int(ys.max() - ys.min() + 1)]


def analyse(rgb, use_ai):
    """Every mask one poster needs, as a dict."""
    paper = M.paper_map(rgb)
    img_lab, paper_lab = M.lab(rgb), M.lab(paper)
    de = M.delta_e(img_lab, paper_lab)
    fg = de > M.FG_DE
    ai_alpha = pm_models.object_alpha(rgb) if use_ai else None
    ai_core = ai_alpha > OBJECT_ALPHA_MIN if use_ai else None
    ink = M.ink_mask(img_lab, paper_lab, de > M.FG_DE * M.RING_STRONG, ai_core)
    boxes = M.accent_boxes(img_lab, paper_lab, fg, ink)
    accents_mask = np.zeros(ink.shape, bool)
    for x, y, w, h in boxes:
        accents_mask[y:y + h, x:x + w] = True
    return dict(paper=paper, img_lab=img_lab, paper_lab=paper_lab, fg=fg,
                ink=ink, boxes=boxes, accents_mask=accents_mask, ai_alpha=ai_alpha)


def split_one(path, project, w, h, use_ai):
    pid = poster_id(path)
    folder = os.path.join(project, "assets", "layers", pid)
    os.makedirs(folder, exist_ok=True)
    rgb = load_rgb(path, w, h)
    a = analyse(rgb, use_ai)
    alpha = object_alpha(a["fg"], a["ink"], a["accents_mask"], a["ai_alpha"])
    hole = plate_hole(a["ink"], alpha, a["accents_mask"], h)
    plate = pm_models.inpaint(rgb, hole) if use_ai else lite_fill(rgb, a["paper"], hole)
    save_rgb(os.path.join(folder, "poster.png"), rgb)
    save_rgb(os.path.join(folder, "plate.png"), plate)
    save_rgba(os.path.join(folder, "ink.png"),
              M.ink_rgba(rgb, a["paper"], a["img_lab"], a["paper_lab"], a["ink"]))
    obj = None
    if alpha is not None:
        rgba = np.dstack([rgb, (alpha * 255).astype(np.uint8)])
        save_rgba(os.path.join(folder, "object.png"), rgba)
        obj = {"bbox": box_of(alpha > OBJECT_ALPHA_MIN),
               "area": round(float((alpha > OBJECT_ALPHA_MIN).mean()), 4)}
    return {"id": pid, "mode": "ai" if use_ai else "lite",
            "paper": [int(v) for v in np.median(a["paper"].reshape(-1, 3), axis=0)],
            "ink_bbox": box_of(a["ink"]), "words": M.word_boxes(a["ink"]),
            "object": obj,
            "accents": write_accents(folder, rgb, a["paper_lab"], a["img_lab"], a["boxes"])}


def _checker(h, w):
    yy, xx = np.mgrid[0:h, 0:w]
    tile = (((yy // CHECKER) + (xx // CHECKER)) % 2).astype(np.uint8)
    return np.dstack([np.where(tile, 205, 245)] * 3).astype(np.uint8)


def _over_checker(path, h, w):
    if not os.path.exists(path):
        return np.full((h, w, 3), 80, np.uint8)
    rgba = cv2.cvtColor(cv2.imread(path, cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA)
    a = rgba[..., 3:4].astype(np.float32) / 255
    return (rgba[..., :3] * a + _checker(h, w) * (1 - a)).astype(np.uint8)


def contact_sheet(project, entries, w, h):
    rows = []
    th = int(h * SHEET_THUMB_W / w)
    for e in entries:
        folder = os.path.join(project, "assets", "layers", e["id"])
        tiles = [cv2.cvtColor(cv2.imread(os.path.join(folder, n)), cv2.COLOR_BGR2RGB)
                 for n in ("poster.png", "plate.png")]
        tiles += [_over_checker(os.path.join(folder, n), h, w)
                  for n in ("ink.png", "object.png")]
        rows.append(np.hstack([cv2.resize(t, (SHEET_THUMB_W, th)) for t in tiles]))
    save_rgb(os.path.join(project, "layers_sheet.png"), np.vstack(rows))


def main():
    project = project_arg()
    aspect = flag("aspect", DEFAULT_ASPECT)
    w, h = CANVAS[aspect]
    use_ai = not flag("lite") and pm_models.available("birefnet") \
        and pm_models.available("lama")
    if not use_ai and not flag("lite"):
        print("models missing - running --lite. `python setup_models.py` for AI mode")
    entries = []
    for path in list_posters(project):
        e = split_one(path, project, w, h, use_ai)
        obj = f"object {e['object']['area']:.0%}" if e["object"] else "no object"
        print(f"  {e['id']}: {len(e['words'])} ink groups, {obj}, "
              f"{len(e['accents'])} accents ({e['mode']})")
        entries.append(e)
    write_json(os.path.join(project, "layers.json"),
               {"aspect": aspect, "canvas": [w, h], "posters": entries})
    contact_sheet(project, entries, w, h)
    print(f"layers.json + layers_sheet.png written for {len(entries)} posters")


if __name__ == "__main__":
    main()
