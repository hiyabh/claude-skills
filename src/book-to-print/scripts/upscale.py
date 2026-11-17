# -*- coding: utf-8 -*-
"""Bring a painting up to print resolution: Real-ESRGAN detail on the painting's own colour and light.

    python upscale.py <in.png> <out.jpg> (--spec <cover_spec.json> [--area wrap|front|back] | --width PX)
                      [--exe <realesrgan-ncnn-vulkan.exe>]

Runs realesrgan-x4plus on an ASCII-named copy (the exe does not take Hebrew paths), then keeps only
the model's fine detail: colour and light below DETAIL_SIGMA come from the original, which the model
tends to shift. Without the exe (setup_check.py --with-upscaler downloads it) it falls back to a plain
Lanczos resize and says so - acceptable for soft painterly art, visibly soft for fine detail.
"""
import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

import geometry as G
import spec as S
from common import SKILL_DIR, fail, px, warn

Image.MAX_IMAGE_PIXELS = None
EXE = SKILL_DIR / "assets" / "tools" / "realesrgan" / "realesrgan-ncnn-vulkan.exe"
MODEL, SCALE = "realesrgan-x4plus", 4
DETAIL_SIGMA = 3.0


def esrgan(exe, src, work):
    shutil.copyfile(src, work / "in.png")
    subprocess.run([str(exe), "-i", str(work / "in.png"), "-o", str(work / "x4.png"), "-n", MODEL, "-s", str(SCALE)],
                   cwd=str(exe.parent), check=True, capture_output=True)
    return Image.open(work / "x4.png").convert("RGB")


def merge(original, detailed, size):
    import cv2
    a = np.asarray(original.resize(size, Image.LANCZOS), np.float32)
    b = np.asarray(detailed.resize(size, Image.LANCZOS), np.float32)
    low = lambda x: cv2.GaussianBlur(x, (0, 0), DETAIL_SIGMA)  # noqa: E731
    return Image.fromarray(np.clip(low(a) + b - low(b), 0, 255).astype(np.uint8))


def target_size(a, img):
    if a.width:
        width = a.width
    elif a.spec:
        spec = S.load(a.spec)
        lay = G.layout(spec)
        box = lay.panel(a.area) if a.area in ("front", "back") else (
            lay.visible if spec["binding"] == "hard" else G.Box(0, 0, lay.width, lay.height))
        width = px(box.w, spec["dpi"])
    else:
        fail("צריך --spec (כדי לחשב את הגודל לדפוס) או --width בפיקסלים.")
    return width, round(width * img.height / img.width)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"), ap.add_argument("out")
    ap.add_argument("--spec"), ap.add_argument("--area", default="wrap"), ap.add_argument("--width", type=int)
    ap.add_argument("--exe", default=str(EXE))
    a = ap.parse_args()
    img = Image.open(a.src).convert("RGB")
    size = target_size(a, img)
    exe = Path(a.exe)
    if exe.is_file():
        with tempfile.TemporaryDirectory() as work:
            detailed = esrgan(exe, a.src, Path(work))
        result = merge(img, detailed, size)
    else:
        warn("Real-ESRGAN לא מותקן (setup_check.py --with-upscaler). הגדלה רגילה - הפרטים הדקים יהיו רכים.")
        result = img.resize(size, Image.LANCZOS)
    result.save(a.out, quality=97)
    print(f"{a.out}: {img.width}x{img.height} -> {size[0]}x{size[1]}")


if __name__ == "__main__":
    main()
