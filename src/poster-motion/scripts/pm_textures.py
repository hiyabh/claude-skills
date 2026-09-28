"""Procedural textures for the composition, drawn once per project.

They are PNGs rather than CSS for one reason: the snapshot render path turns a
film black once ~25 elements carry filter/blur/clip-path/radial-gradient (see
references/traps.md). An <img> costs nothing on that count.
Every texture is seeded, so a re-render is pixel-identical.

  kraft.png   brown cardboard with fibres - making-of and end-card background
  stamp.png   red ink stamp disc with worn speckles - behind the step numbers
  splash.png  red paint blob - behind the end-card poster
"""

import os

import cv2
import numpy as np

SEED = 11
KRAFT_RGB = (178, 136, 96)
KRAFT_NOISE = 9.0
FIBRES = 900
RED_RGB = (214, 58, 36)
STAMP_PX = 360
STAMP_HOLES = 0.10
SPLASH_PX = (520, 420)
SPLASH_LOBES = 14


def _rng(offset):
    return np.random.default_rng(SEED + offset)


def kraft(w, h):
    rng = _rng(0)
    base = np.array(KRAFT_RGB, np.float32)[None, None, :] * np.ones((h, w, 1), np.float32)
    coarse = cv2.resize(rng.normal(0, 1, (h // 24 + 1, w // 24 + 1)).astype(np.float32),
                        (w, h), interpolation=cv2.INTER_CUBIC)
    base += (coarse * KRAFT_NOISE)[..., None]
    base += rng.normal(0, KRAFT_NOISE * 0.5, (h, w, 1)).astype(np.float32)
    img = np.clip(base, 0, 255).astype(np.uint8)
    for _ in range(FIBRES):
        x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
        ang, ln = rng.uniform(0, np.pi), rng.uniform(4, 18)
        dx, dy = int(np.cos(ang) * ln), int(np.sin(ang) * ln)
        shade = int(rng.choice([-26, 22]))
        colour = tuple(int(np.clip(c + shade, 0, 255)) for c in KRAFT_RGB)
        cv2.line(img, (x, y), (x + dx, y + dy), colour, 1, cv2.LINE_AA)
    return img


def _worn(alpha, rng, holes):
    """Knock speckled holes into an alpha mask - the worn-ink look."""
    h, w = alpha.shape
    noise = cv2.resize(rng.random((h // 3, w // 3)).astype(np.float32), (w, h),
                       interpolation=cv2.INTER_NEAREST)
    alpha[noise < holes] = 0
    return cv2.GaussianBlur(alpha, (0, 0), 0.6)


def _rgba(alpha):
    out = np.zeros(alpha.shape + (4,), np.uint8)
    out[..., :3] = RED_RGB
    out[..., 3] = np.clip(alpha * 255, 0, 255).astype(np.uint8)
    return out


def stamp():
    rng = _rng(1)
    alpha = np.zeros((STAMP_PX, STAMP_PX), np.float32)
    c = STAMP_PX // 2
    cv2.circle(alpha, (c, c), int(c * 0.94), 1.0, -1, cv2.LINE_AA)
    return _rgba(_worn(alpha, rng, STAMP_HOLES))


def splash():
    rng = _rng(2)
    w, h = SPLASH_PX
    alpha = np.zeros((h, w), np.float32)
    cv2.ellipse(alpha, (w // 2, h // 2), (int(w * 0.36), int(h * 0.38)), 0, 0, 360, 1.0, -1)
    for _ in range(SPLASH_LOBES):
        ang = rng.uniform(0, 2 * np.pi)
        r = rng.uniform(0.3, 0.46)
        x, y = int(w / 2 + np.cos(ang) * w * r), int(h / 2 + np.sin(ang) * h * r)
        cv2.circle(alpha, (x, y), int(rng.uniform(0.04, 0.1) * w), 1.0, -1, cv2.LINE_AA)
    return _rgba(_worn(cv2.GaussianBlur(alpha, (0, 0), 1.2), rng, STAMP_HOLES / 3))


def write_all(folder, w, h):
    os.makedirs(folder, exist_ok=True)
    cv2.imwrite(os.path.join(folder, "kraft.png"), cv2.cvtColor(kraft(w, h), cv2.COLOR_RGB2BGR))
    cv2.imwrite(os.path.join(folder, "stamp.png"), cv2.cvtColor(stamp(), cv2.COLOR_RGBA2BGRA))
    cv2.imwrite(os.path.join(folder, "splash.png"), cv2.cvtColor(splash(), cv2.COLOR_RGBA2BGRA))
