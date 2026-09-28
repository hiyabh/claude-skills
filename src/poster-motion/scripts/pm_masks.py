"""Pure mask maths for split_layers.py: paper, ink, object, accents, words.

The posters this skill is built for share one trait: artwork on plain paper.
Everything here leans on that. The paper is estimated first, and every other
layer is defined as a departure from it:

  ink     - darker than the paper and colourless, in shapes surrounded by paper
            (text, a drawn line, a feather). A dark shape surrounded by *object*
            pixels (a cat inside a bag, lettering printed on a box) is part of
            the object instead - the "ring" test.
  accents - small saturated shapes (pink butterflies, a red dot)
  object  - whatever else stands off the paper (lite) or BiRefNet's matte (ai)

All sizes are fractions of the canvas height so the same thresholds work at
720x900 and 1080x1920.
"""

import cv2
import numpy as np

# --- paper -------------------------------------------------------------------
PAPER_DOWNSCALE = 8          # paper is smooth; estimate it at 1/8 resolution
PAPER_SEED_DE = 6.0          # Lab distance from the border median = not paper
BORDER_FRAC = 0.03           # border strip used for the first paper guess
FG_DE = 9.0                  # Lab distance from the paper map = foreground

# --- ink -----------------------------------------------------------------------
INK_DL = 18.0                # this much darker than paper (L is 0..100)
INK_CHROMA = 16.0            # and at most this colourful
INK_MAX_H = 0.45             # a component taller than this is never ink
INK_MAX_AREA = 0.06          # nor one covering more of the canvas than this
RING_FRAC = 0.012            # ring width around a component, x canvas height
RING_OBJECT_MAX = 0.35       # more object than this around it -> object, not ink
RING_STRONG = 2.0            # only pixels this many x FG_DE off paper count as
                             # object in the ring - soft shadows and gradients don't
AI_OVERLAP_MAX = 0.3         # a stroke mostly outside BiRefNet's matte is ink
INK_MIN_AREA = 0.00006       # smaller specks are kept only beside real ink
INK_ALPHA_PCT = 5            # percentile of ink L taken as fully opaque ink

# --- accents / object ----------------------------------------------------------
ACCENT_CHROMA = 9.0          # above the paper's own chroma
ACCENT_MIN_PX = 40
ACCENT_GROW_PX = 9
ACCENT_MARGIN_PX = 6
ACCENT_MAX_AREA = 0.02
MAX_ACCENTS = 16
OBJECT_MIN_AREA = 0.012
OBJECT_CLOSE_FRAC = 0.008
OBJECT_FEATHER_PX = 1.2

# --- words ---------------------------------------------------------------------
WORD_GAP = 0.32              # letters closer than this x letter height = one word
LINE_OVERLAP = 0.5


def lab(rgb):
    return cv2.cvtColor(rgb.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)


def delta_e(lab_a, lab_b):
    return np.sqrt(((lab_a - lab_b) ** 2).sum(axis=2))


def to_canvas(rgb, w, h):
    """Cover-crop to w x h, centred - the poster fills the frame edge to edge."""
    ih, iw = rgb.shape[:2]
    scale = max(w / iw, h / ih)
    rw, rh = round(iw * scale), round(ih * scale)
    big = cv2.resize(rgb, (rw, rh), interpolation=cv2.INTER_AREA
                     if scale < 1 else cv2.INTER_CUBIC)
    x0, y0 = (rw - w) // 2, (rh - h) // 2
    return big[y0:y0 + h, x0:x0 + w].copy()


def paper_map(rgb):
    """The poster with everything that is not paper painted out, smoothly."""
    h, w = rgb.shape[:2]
    small = cv2.resize(rgb, (w // PAPER_DOWNSCALE, h // PAPER_DOWNSCALE),
                       interpolation=cv2.INTER_AREA)
    b = max(1, int(small.shape[0] * BORDER_FRAC))
    border = np.concatenate([small[:b].reshape(-1, 3), small[-b:].reshape(-1, 3),
                             small[:, :b].reshape(-1, 3), small[:, -b:].reshape(-1, 3)])
    seed = np.median(border, axis=0).astype(np.float32)
    seed_lab = lab(seed.reshape(1, 1, 3).astype(np.uint8))
    not_paper = delta_e(lab(small), seed_lab) > PAPER_SEED_DE
    # Wide margin: soft contact shadows sit below PAPER_SEED_DE and would
    # otherwise be smeared into the fill as a brown ghost.
    not_paper = cv2.dilate(not_paper.astype(np.uint8), np.ones((5, 5), np.uint8))
    filled = cv2.inpaint(small, not_paper, 5, cv2.INPAINT_TELEA)
    filled = cv2.GaussianBlur(filled, (0, 0), 2)
    return cv2.resize(filled, (w, h), interpolation=cv2.INTER_CUBIC)


def _components(mask):
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    return n, labels, stats


def _ring_object_ratio(comp, fg_other, ring_px):
    """Share of the ring around `comp` that is non-paper, non-dark pixels."""
    k = np.ones((2 * ring_px + 1, 2 * ring_px + 1), np.uint8)
    ring = cv2.dilate(comp.astype(np.uint8), k).astype(bool) & ~comp
    total = int(ring.sum())
    return float((ring & fg_other).sum()) / total if total else 1.0


def _dark(img_lab, paper_lab):
    dl = paper_lab[..., 0] - img_lab[..., 0]
    chroma = np.sqrt(img_lab[..., 1] ** 2 + img_lab[..., 2] ** 2)
    dark = (dl > INK_DL) & (chroma < INK_CHROMA)
    return cv2.morphologyEx(dark.astype(np.uint8), cv2.MORPH_CLOSE,
                            np.ones((3, 3), np.uint8)).astype(bool)


def _is_ink(stats_row, comp, fg_other, h, ring_px):
    _, _, _, bh, area = stats_row
    if bh > INK_MAX_H * h or area > INK_MAX_AREA * comp.size:
        return False
    return _ring_object_ratio(comp, fg_other, ring_px) <= RING_OBJECT_MAX


def _outside_matte(comp, ai_core):
    if ai_core is None:
        return False
    return float((comp & ai_core).sum()) / max(int(comp.sum()), 1) < AI_OVERLAP_MAX


def ink_mask(img_lab, paper_lab, fg_strong, ai_core=None):
    """Boolean mask of ink: dark, colourless, standing on paper.

    Specks below INK_MIN_AREA survive only next to a real stroke - that keeps
    niqqud and feather barbs and drops the paper's own grain. With a BiRefNet
    matte (`ai_core`), a stroke the matte leaves out is ink even where it
    touches the object - lettering right above a fork's tines."""
    h = img_lab.shape[0]
    dark = _dark(img_lab, paper_lab)
    fg_other = fg_strong & ~dark
    ring_px = max(2, int(h * RING_FRAC))
    n, labels, stats = _components(dark)
    big = np.zeros_like(dark)
    small = np.zeros_like(dark)
    for i in range(1, n):
        comp = labels == i
        if stats[i][4] < INK_MIN_AREA * dark.size:
            small |= comp
        elif (_is_ink(stats[i], comp, fg_other, h, ring_px)
              or _outside_matte(comp, ai_core)):
            big |= comp
    near = cv2.dilate(big.astype(np.uint8), np.ones((2 * ring_px + 1,) * 2, np.uint8))
    return big | (small & near.astype(bool))


def ink_rgba(rgb, paper, img_lab, paper_lab, ink):
    """Anti-aliased ink layer: alpha from darkness, colour un-mixed from paper."""
    grown = cv2.dilate(ink.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    dl = paper_lab[..., 0] - img_lab[..., 0]
    full = np.percentile(dl[ink], 100 - INK_ALPHA_PCT) if ink.any() else 1.0
    alpha = np.clip(dl / max(full, 1e-3), 0, 1) * grown
    a3 = np.maximum(alpha[..., None], 1e-3)
    colour = (rgb.astype(np.float32) - (1 - a3) * paper.astype(np.float32)) / a3
    out = np.zeros(rgb.shape[:2] + (4,), np.uint8)
    out[..., :3] = np.clip(colour, 0, 255)
    out[..., 3] = (alpha * 255).astype(np.uint8)
    return out


def accent_boxes(img_lab, paper_lab, fg, blocked):
    """Boxes of small coloured shapes standing on paper, largest first."""
    chroma = np.sqrt(img_lab[..., 1] ** 2 + img_lab[..., 2] ** 2)
    paper_chroma = np.sqrt(paper_lab[..., 1] ** 2 + paper_lab[..., 2] ** 2)
    colour = (chroma - paper_chroma > ACCENT_CHROMA) & fg & ~blocked
    k = np.ones((ACCENT_GROW_PX, ACCENT_GROW_PX), np.uint8)
    mask = cv2.dilate(colour.astype(np.uint8), k)
    n, labels, stats = _components(mask)
    ring_px = max(2, int(mask.shape[0] * RING_FRAC))
    h, w = mask.shape
    boxes = []
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        if not ACCENT_MIN_PX <= area <= ACCENT_MAX_AREA * mask.size:
            continue
        if _ring_object_ratio(labels == i, fg & ~colour, ring_px) > RING_OBJECT_MAX:
            continue
        m = ACCENT_MARGIN_PX
        x0, y0 = max(0, x - m), max(0, y - m)
        boxes.append((int(x0), int(y0), int(min(w, x + bw + m) - x0),
                      int(min(h, y + bh + m) - y0)))
    boxes.sort(key=lambda b: -b[2] * b[3])
    return boxes[:MAX_ACCENTS]


def object_mask_lite(fg, ink, accents_mask):
    """Everything that stands off the paper and is not ink or an accent."""
    h = fg.shape[0]
    grown_ink = cv2.dilate(ink.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    mask = fg & ~grown_ink & ~accents_mask
    k = max(3, int(h * OBJECT_CLOSE_FRAC)) | 1
    mask = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    n, labels, stats = _components(mask)
    keep = np.zeros(mask.shape, np.uint8)
    for i in range(1, n):
        if stats[i][4] >= OBJECT_MIN_AREA * mask.size:
            keep[labels == i] = 1
    return _fill_holes(keep).astype(bool)


def _fill_holes(mask):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = np.zeros_like(mask)
    cv2.drawContours(out, contours, -1, 1, thickness=cv2.FILLED)
    return out


def feather(mask):
    return cv2.GaussianBlur(mask.astype(np.float32), (0, 0), OBJECT_FEATHER_PX)


def word_boxes(ink):
    """Word boxes grouped into lines: top line first, each line right-to-left."""
    n, _, stats = _components(ink)
    heights = [stats[i][3] for i in range(1, n) if stats[i][4] > ACCENT_MIN_PX]
    if not heights:
        return []
    letter_h = float(np.median(heights))
    kx = max(3, int(letter_h * WORD_GAP)) | 1
    ky = max(1, int(letter_h * WORD_GAP * 0.4)) | 1
    merged = cv2.dilate(ink.astype(np.uint8), np.ones((ky, kx), np.uint8))
    m, _, st = _components(merged)
    boxes = [tuple(int(v) for v in st[i][:4]) for i in range(1, m)
             if st[i][4] > ACCENT_MIN_PX]
    return _order_rtl(boxes)


def _order_rtl(boxes):
    lines = []
    for box in sorted(boxes, key=lambda b: b[1] + b[3] / 2):
        for line in lines:
            ly, lh = line["y"], line["h"]
            overlap = min(box[1] + box[3], ly + lh) - max(box[1], ly)
            if overlap > LINE_OVERLAP * min(box[3], lh):
                line["boxes"].append(box)
                break
        else:
            lines.append({"y": box[1], "h": box[3], "boxes": [box]})
    out = []
    for li, line in enumerate(lines):
        for box in sorted(line["boxes"], key=lambda b: -(b[0] + b[2])):
            out.append({"bbox": list(box), "line": li})
    return out
