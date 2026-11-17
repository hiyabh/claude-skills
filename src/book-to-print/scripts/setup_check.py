# -*- coding: utf-8 -*-
"""First run on a new computer: install what is missing, fetch the colour profile, and prove it all works.

    python setup_check.py [--with-upscaler] [--no-install]

1. Python 3.10 or newer.
2. Python packages (installed with pip when missing): pymupdf, reportlab, pillow, python-bidi,
   python-docx, numpy, opencv-python-headless, and pywin32 on Windows (for Word).
3. ISO Coated v2 (FOGRA39) and PSO Uncoated (FOGRA47) from the European Color Initiative, free,
   into assets/icc/ (https://www.eci.org/lib/exe/eci_offset_2009.zip, verified 2026-11-17).
4. Optional: Real-ESRGAN (upscaling AI art to print size) into assets/tools/realesrgan/.
5. Word (only for the Word tools) and the bundled fonts.
6. A test cover is built and checked in a temporary folder.
"""
import argparse
import io
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
SKILL = SCRIPTS.parent
PACKAGES = {"fitz": "pymupdf", "reportlab": "reportlab", "PIL": "pillow", "bidi": "python-bidi",
            "docx": "python-docx", "numpy": "numpy", "cv2": "opencv-python-headless"}
WINDOWS_PACKAGES = {"win32com": "pywin32"}
ICC_ZIP = "https://www.eci.org/lib/exe/eci_offset_2009.zip"
ICC_FILES = ("ISOcoated_v2_eci.icc", "PSO_Uncoated_ISO12647_eci.icc")
ESRGAN_ZIP = ("https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/"
              "realesrgan-ncnn-vulkan-20220424-windows.zip")
MIN_PYTHON = (3, 10)

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def say(ok, text):
    print(f"  {'✓' if ok else '✗'} {text}")
    return ok


def importable(module):
    """In a fresh process: pywin32 registers itself at start-up, so an in-process import right after
    pip install fails even when the install worked."""
    return subprocess.run([sys.executable, "-c", f"import {module}"], capture_output=True).returncode == 0


def packages(install):
    wanted = dict(PACKAGES, **(WINDOWS_PACKAGES if sys.platform == "win32" else {}))
    missing = [pip_name for module, pip_name in wanted.items() if not importable(module)]
    if missing and install:
        print(f"  מתקין: {' '.join(missing)}")
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", *missing], check=False)
        return packages(False)
    return say(not missing, "כל ספריות Python מותקנות" if not missing else f"חסרות: {' '.join(missing)}")


def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": "book-to-print-setup"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def icc():
    folder = SKILL / "assets" / "icc"
    folder.mkdir(parents=True, exist_ok=True)
    if all((folder / name).is_file() for name in ICC_FILES):
        return say(True, "פרופילי הצבע (ISO Coated v2, PSO Uncoated) קיימים")
    try:
        with zipfile.ZipFile(io.BytesIO(download(ICC_ZIP))) as z:
            for info in z.infolist():
                name = Path(info.filename).name
                if name in ICC_FILES and "__MACOSX" not in info.filename:
                    (folder / name).write_bytes(z.read(info))
    except (OSError, zipfile.BadZipFile) as e:
        return say(False, f"הורדת פרופילי הצבע נכשלה ({e}). המנוע ישתמש בפרופיל של Windows; לנסות שוב מאוחר יותר.")
    return say(all((folder / n).is_file() for n in ICC_FILES), f"פרופילי הצבע הורדו אל {folder}")


def upscaler():
    folder = SKILL / "assets" / "tools" / "realesrgan"
    if (folder / "realesrgan-ncnn-vulkan.exe").is_file():
        return say(True, "Real-ESRGAN קיים")
    try:
        with zipfile.ZipFile(io.BytesIO(download(ESRGAN_ZIP))) as z:
            z.extractall(folder)
    except (OSError, zipfile.BadZipFile) as e:
        return say(False, f"הורדת Real-ESRGAN נכשלה ({e})")
    return say((folder / "realesrgan-ncnn-vulkan.exe").is_file(), f"Real-ESRGAN הותקן אל {folder}")


def word():
    if sys.platform != "win32":
        return say(True, "לא Windows - את Word מייצאים ל-PDF ידנית")
    try:
        import win32com.client
        app = win32com.client.DispatchEx("Word.Application")
        app.Quit()
        return say(True, "Word נמצא (לכלי word_export.py)")
    except Exception:  # noqa: BLE001 - any COM failure means "no Word"
        return say(True, "Word לא נמצא - הכלים לכריכה עובדים בלעדיו; לספר ב-Word צריך Word מותקן")


def sample(folder):
    import numpy as np
    from PIL import Image
    y, x = np.mgrid[0:600, 0:900]
    art = np.stack([20 + x * 0.1, 40 + y * 0.15, 90 + x * 0.12], axis=-1).clip(0, 255).astype("uint8")
    Image.fromarray(art).save(folder / "art.png")
    spec = SKILL / "assets" / "cover_spec.soft.example.json"
    text = spec.read_text(encoding="utf-8").replace('"art/wrap.png"', '"art.png"')
    (folder / "spec.json").write_text(text, encoding="utf-8")
    return folder / "spec.json"


def smoke_test():
    with tempfile.TemporaryDirectory() as tmp:
        spec = sample(Path(tmp))
        for script in ("build_cover.py", "check_cover.py"):
            r = subprocess.run([sys.executable, str(SCRIPTS / script), str(spec)], capture_output=True,
                               text=True, encoding="utf-8", errors="replace")
            if r.returncode != 0:
                print(r.stdout[-1500:], r.stderr[-1500:])
                return say(False, f"בדיקת הדוגמה נכשלה ב-{script}")
    return say(True, "כריכת דוגמה נבנתה ונבדקה בהצלחה")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-upscaler", action="store_true")
    ap.add_argument("--no-install", action="store_true")
    a = ap.parse_args()
    print("בדיקת התקנה - ספר לדפוס")
    ok = say(sys.version_info >= MIN_PYTHON, f"Python {sys.version.split()[0]}")
    ok &= packages(not a.no_install)
    ok &= icc()
    if a.with_upscaler:
        ok &= upscaler()
    word()
    fonts = list((SKILL / "assets" / "fonts").glob("*.ttf"))
    ok &= say(bool(fonts), f"{len(fonts)} גופנים בסקיל")
    if ok:
        ok &= smoke_test()
    print("הכול מוכן." if ok else "יש בעיות - ראה את השורות עם ✗.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
