"""One-time: download the two ONNX models and prove they load and run.

    python setup_models.py            # download if missing, then self-test
    python setup_models.py --check    # self-test only

Files land in ~/.cache/poster-motion/ (about 430 MB). The self-test runs each
model once on a synthetic poster - a dark square on paper - and checks that the
cutout finds the square and the fill removes it.
"""

import sys
import time

import numpy as np

from pm_common import download, flag
from pm_models import MODELS, available, inpaint, model_path, object_alpha

PAPER = 235
SQUARE = (slice(300, 600), slice(210, 510))
TEST_SIZE = (900, 720, 3)
CUTOUT_MIN_CONTRAST = 0.5    # mean alpha inside minus outside the square
FILL_MAX_DARKNESS = 40       # paper minus mean filled value


def fetch():
    for key, (_, url, size) in MODELS.items():
        if available(key):
            print(f"  {key}: present")
            continue
        print(f"  {key}: downloading {size // 2 ** 20} MB ...")
        download(url, model_path(key))
        if not available(key):
            sys.exit(f"  {key}: size mismatch after download - delete "
                     f"{model_path(key)} and retry")


def self_test():
    img = np.full(TEST_SIZE, PAPER, np.uint8)
    img[SQUARE] = 30
    t = time.time()
    alpha = object_alpha(img)
    inside = float(alpha[SQUARE].mean())
    outside = float(alpha[:200].mean())
    print(f"  birefnet: {time.time() - t:.1f}s, alpha inside {inside:.2f} "
          f"outside {outside:.2f}")
    t = time.time()
    hole = np.zeros(TEST_SIZE[:2], bool)
    hole[SQUARE] = True
    filled = inpaint(img, hole)
    dark = PAPER - float(filled[SQUARE].mean())
    print(f"  lama:     {time.time() - t:.1f}s, filled square is {dark:.0f} "
          f"below paper")
    ok = inside - outside > CUTOUT_MIN_CONTRAST and dark < FILL_MAX_DARKNESS
    print("  self-test", "PASSED" if ok else "FAILED")
    return ok


if __name__ == "__main__":
    if not flag("check"):
        fetch()
    sys.exit(0 if self_test() else 1)
