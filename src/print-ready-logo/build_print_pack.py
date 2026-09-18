# -*- coding: utf-8 -*-
"""
print-ready-logo — turn any logo/image into a print-ready pack:
  1. ensure a real transparent background (keep existing alpha, or remove a solid bg)
  2. trim transparent margins
  3. AI super-resolution upscale (Real-ESRGAN ncnn-vulkan) for high pixel quality
  4. export a clean transparent PNG + a 300-DPI PDF that PRESERVES transparency

Usage:
  python build_print_pack.py INPUT [options]

Options:
  --output-dir DIR   where to write outputs (default: input's folder)
  --name NAME        base name for outputs (default: input stem)
  --scale N          upscale factor 1/2/3/4 (default: 4; 1 = no upscale)
  --dpi N            print DPI metadata (default: 300)
  --model NAME       realesrgan model (default: realesrgan-x4plus;
                     use realesrgan-x4plus-anime for flat line-art/text logos)
  --remove-bg        force solid-background removal even if alpha already exists
  --no-remove-bg     never touch the background (only upscale + pack)
  --bg-tolerance N   color tolerance for solid-bg flood fill (default: 25)
  --rembg            use the rembg AI model for complex (non-solid) backgrounds
"""
import argparse
import os
import sys
import subprocess
import urllib.request
import zipfile

import numpy as np
from PIL import Image

try:
    import cv2
except ImportError:
    cv2 = None

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(SKILL_DIR, "bin")
EXE = os.path.join(BIN_DIR, "realesrgan-ncnn-vulkan.exe")
ESRGAN_URL = ("https://github.com/xinntao/Real-ESRGAN/releases/download/"
              "v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip")
PT_PER_INCH = 72.0


# ---------- background handling ----------

def has_real_transparency(im):
    """True if the image already has meaningful transparent pixels."""
    if im.mode != "RGBA":
        return False
    alpha = im.getchannel("A")
    lo, _ = alpha.getextrema()
    return lo < 250  # at least some pixels are (semi-)transparent


def remove_solid_bg(im, tol):
    """Flood-fill from the four corners to clear a solid/near-solid background."""
    if cv2 is None:
        raise RuntimeError("opencv-python required for solid-bg removal: pip install opencv-python")
    rgba = np.array(im.convert("RGBA"))
    h, w = rgba.shape[:2]
    bgr = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2BGR).copy()
    mask = np.zeros((h + 2, w + 2), np.uint8)
    flags = cv2.FLOODFILL_MASK_ONLY | (255 << 8)
    for seed in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        cv2.floodFill(bgr, mask, seed, 0, (tol,) * 3, (tol,) * 3, flags)
    rgba[mask[1:-1, 1:-1] > 0, 3] = 0
    return Image.fromarray(rgba, "RGBA")


def remove_bg_rembg(im):
    """AI background removal for complex (non-solid) backgrounds."""
    try:
        from rembg import remove
    except ImportError:
        print("Installing rembg (first run only)...", flush=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "rembg", "onnxruntime", "--quiet"], check=True)
        from rembg import remove
    return remove(im.convert("RGBA"))


def ensure_transparent(im, args):
    """Return an RGBA image with a transparent background per the chosen strategy."""
    im = im.convert("RGBA")
    if args.rembg:
        return remove_bg_rembg(im)
    if args.no_remove_bg:
        return im
    if has_real_transparency(im) and not args.remove_bg:
        print("Existing transparency detected — keeping it.", flush=True)
        return im
    print("Removing solid background (corner flood fill)...", flush=True)
    return remove_solid_bg(im, args.bg_tolerance)


def trim(im):
    """Crop away fully transparent margins."""
    bbox = im.getbbox()
    return im.crop(bbox) if bbox else im


# ---------- upscaling ----------

def ensure_esrgan():
    """Download + extract Real-ESRGAN ncnn-vulkan on first use."""
    if os.path.exists(EXE):
        return
    os.makedirs(BIN_DIR, exist_ok=True)
    zip_path = os.path.join(BIN_DIR, "realesrgan.zip")
    print("Downloading Real-ESRGAN (first run only, ~45MB)...", flush=True)
    urllib.request.urlretrieve(ESRGAN_URL, zip_path)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(BIN_DIR)
    os.remove(zip_path)
    if not os.path.exists(EXE):
        raise RuntimeError("Real-ESRGAN extraction failed")


def upscale(im, scale, model, work_dir):
    """Run Real-ESRGAN on an RGBA image; returns the upscaled RGBA image."""
    if scale <= 1:
        return im
    ensure_esrgan()
    src = os.path.join(work_dir, "_pp_in.png")
    dst = os.path.join(work_dir, "_pp_out.png")
    im.save(src, "PNG")
    cmd = [EXE, "-i", src, "-o", dst, "-n", model, "-s", str(scale)]
    print(f"Upscaling x{scale} with {model}...", flush=True)
    subprocess.run(cmd, check=True)
    out = Image.open(dst).convert("RGBA")
    for f in (src, dst):
        try:
            os.remove(f)
        except OSError:
            pass
    return out


# ---------- export ----------

def export_pack(im, dpi, out_dir, base):
    """Write the transparent PNG and the transparency-preserving print PDF."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader

    png_path = os.path.join(out_dir, f"{base} - רקע שקוף.png")
    pdf_path = os.path.join(out_dir, f"{base} - להדפסה.pdf")
    w_px, h_px = im.size
    im.save(png_path, "PNG", dpi=(dpi, dpi), optimize=True)

    w_pt = w_px / dpi * PT_PER_INCH
    h_pt = h_px / dpi * PT_PER_INCH
    c = canvas.Canvas(pdf_path, pagesize=(w_pt, h_pt))
    c.drawImage(ImageReader(im), 0, 0, width=w_pt, height=h_pt, mask="auto")
    c.showPage()
    c.save()

    mm_w = w_pt / PT_PER_INCH * 25.4
    mm_h = h_pt / PT_PER_INCH * 25.4
    print(f"\nPNG: {w_px}x{h_px}px @ {dpi}dpi  ({os.path.getsize(png_path)//1024} KB)")
    print(f"     {png_path}")
    print(f"PDF: {mm_w:.1f}x{mm_h:.1f}mm @ {dpi}dpi, transparent  ({os.path.getsize(pdf_path)//1024} KB)")
    print(f"     {pdf_path}")
    print(f"\nSharp print size @ {dpi}dpi: up to {mm_w/10:.1f} cm wide.")


# ---------- cli ----------

def parse_args():
    p = argparse.ArgumentParser(description="Make a print-ready transparent PNG + PDF from a logo/image.")
    p.add_argument("input")
    p.add_argument("--output-dir", default=None)
    p.add_argument("--name", default=None)
    p.add_argument("--scale", type=int, default=4, choices=[1, 2, 3, 4])
    p.add_argument("--dpi", type=int, default=300)
    p.add_argument("--model", default="realesrgan-x4plus")
    p.add_argument("--remove-bg", action="store_true")
    p.add_argument("--no-remove-bg", action="store_true")
    p.add_argument("--bg-tolerance", type=int, default=25)
    p.add_argument("--rembg", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    if not os.path.isfile(args.input):
        sys.exit(f"Input not found: {args.input}")
    out_dir = args.output_dir or os.path.dirname(os.path.abspath(args.input))
    os.makedirs(out_dir, exist_ok=True)
    base = args.name or os.path.splitext(os.path.basename(args.input))[0]

    im = Image.open(args.input)
    im = ensure_transparent(im, args)
    im = trim(im)
    im = trim(upscale(im, args.scale, args.model, out_dir))
    export_pack(im, args.dpi, out_dir, base)


if __name__ == "__main__":
    main()
