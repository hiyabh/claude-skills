#!/usr/bin/env python3
"""Readiness check for talking-head-fx - reports what is missing, in Hebrew, with the install command.

Usage:  python preflight.py        (exit 0 = ready, 1 = something required is missing)
"""
import importlib.util
import shutil
import subprocess
import sys

REQUIRED_MODULES = [("cv2", "opencv-python", "מעקב פנים"), ("numpy", "numpy", "מעקב פנים")]
OPTIONAL_MODULES = [("faster_whisper", "faster-whisper", "תמלול מקומי לכתוביות ולתכנון")]
REQUIRED_BINARIES = [("ffmpeg", "חיתוך וקידוד וידאו"), ("ffprobe", "קריאת אורך ורזולוציה"),
                     ("node", "הרצת HyperFrames"), ("npx", "הרצת HyperFrames")]
INSTALL_HINT = {
    "ffmpeg": "https://ffmpeg.org/download.html (ב-Windows: winget install Gyan.FFmpeg)",
    "ffprobe": "מגיע יחד עם ffmpeg",
    "node": "https://nodejs.org (גרסה 22 ומעלה)",
    "npx": "מגיע יחד עם Node.js",
}


def check_modules(mods, required):
    missing = []
    for mod, pip_name, why in mods:
        ok = importlib.util.find_spec(mod) is not None
        mark = "✓" if ok else ("✗" if required else "○")
        print(f"  {mark} {pip_name:<16} - {why}")
        if not ok:
            missing.append(pip_name)
    return missing


def check_binaries():
    missing = []
    for name, why in REQUIRED_BINARIES:
        ok = shutil.which(name) is not None
        print(f"  {'✓' if ok else '✗'} {name:<16} - {why}")
        if not ok:
            missing.append(name)
    return missing


def hyperframes_version():
    try:
        r = subprocess.run("npx --yes hyperframes --version", shell=True, capture_output=True, text=True, timeout=180)
        return r.stdout.strip().splitlines()[-1] if r.returncode == 0 and r.stdout.strip() else None
    except (subprocess.TimeoutExpired, OSError):
        return None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("בדיקת מוכנות - talking-head-fx\n\nספריות Python:")
    miss_req = check_modules(REQUIRED_MODULES, True)
    miss_opt = check_modules(OPTIONAL_MODULES, False)
    print("\nכלים במערכת:")
    miss_bin = check_binaries()
    hf = hyperframes_version() if not {"node", "npx"} & set(miss_bin) else None
    print(f"  {'✓' if hf else '✗'} hyperframes      - {hf or 'לא נמצא (npx יוריד אותו בהרצה הראשונה, נדרש אינטרנט)'}")
    if miss_req or miss_opt:
        print(f"\nלהתקנה: {sys.executable} -m pip install " + " ".join(miss_req + miss_opt))
    for b in miss_bin:
        print(f"להתקנת {b}: {INSTALL_HINT[b]}")
    if miss_opt and not miss_req:
        print("faster-whisper הוא רשות: בלעדיו צריך להביא תמלול מוכן (words.json) או לוותר על כתוביות.")
    ready = not miss_req and not miss_bin
    print("\n" + ("מוכן לעבודה." if ready else "חסרים רכיבי חובה - להתקין ולהריץ שוב."))
    sys.exit(0 if ready else 1)


if __name__ == "__main__":
    main()
