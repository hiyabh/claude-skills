"""Check that this machine can run the pipeline, and say what is missing - in Hebrew.

    python preflight.py

Exit 0 when everything required is present (optional items only warn).
Imports are real imports, not a package lookup: a package can be installed and
still fail to load (a blocked DLL, a wheel for the wrong Python).
"""

import importlib
import os
import shutil
import sys

import pm_common  # noqa: F401 - sets UTF-8 stdout for the Hebrew report

REQUIRED_MODULES = [  # (import name, pip package, what it is for)
    ("numpy", "numpy", "חישובי תמונה"),
    ("cv2", "opencv-python", "הפרדת השכבות"),
    ("PIL", "pillow", "גיליונות בדיקה"),
    ("librosa", "librosa", "זיהוי הביט במוזיקה"),
]
OPTIONAL_MODULES = [
    ("onnxruntime", "onnxruntime", "מצב AI - חיתוך אובייקט ומילוי רקע (בלעדיו: מצב lite)"),
]
REQUIRED_BINARIES = [  # (binary, install hint, what it is for)
    ("ffmpeg", "https://ffmpeg.org/download.html  (Windows: winget install Gyan.FFmpeg)",
     "חיתוך המוזיקה וקידוד הסרטון"),
    ("ffprobe", "מגיע יחד עם ffmpeg", "בדיקת הסרטון המוגמר"),
    ("node", "https://nodejs.org  (Windows: winget install OpenJS.NodeJS.LTS)",
     "מריץ את HyperFrames"),
    ("npx", "מגיע יחד עם Node.js", "מריץ את HyperFrames"),
]


def check_module(name):
    try:
        importlib.import_module(name)
        return None
    except Exception as exc:  # noqa: BLE001 - any load failure means "not usable"
        return f"{type(exc).__name__}: {exc}"


def report_modules(rows, required):
    missing = []
    for name, pip_name, purpose in rows:
        err = check_module(name)
        mark = "✓" if err is None else ("✗" if required else "!")
        print(f"  {mark} {name:12} {purpose}")
        if err:
            print(f"      חסר או לא נטען ({err[:90]})")
            print(f"      התקנה: {sys.executable} -m pip install {pip_name}")
            missing.append(name)
    return missing


def report_binaries():
    missing = []
    for binary, hint, purpose in REQUIRED_BINARIES:
        found = shutil.which(binary)
        print(f"  {'✓' if found else '✗'} {binary:12} {purpose}")
        if not found:
            print(f"      לא נמצא ב-PATH. התקנה: {hint}")
            missing.append(binary)
    return missing


def main():
    print("poster-motion - בדיקת מוכנות\n")
    print("חבילות Python (חובה):")
    missing = report_modules(REQUIRED_MODULES, True)
    print("\nכלים (חובה):")
    missing += report_binaries()
    print("\nאופציונלי:")
    report_modules(OPTIONAL_MODULES, False)
    has_key = bool(os.environ.get("GOOGLE_API_KEY"))
    print(f"  {'✓' if has_key else '!'} GOOGLE_API_KEY  ייצור פוסטרים מנושא "
          f"({'מוגדר' if has_key else 'לא מוגדר - אפשר להביא פוסטרים מוכנים'})")
    if missing:
        print(f"\nחסרים {len(missing)} רכיבי חובה: {', '.join(missing)}. התקן ונסה שוב.")
        sys.exit(1)
    print("\nהכול מוכן.")


if __name__ == "__main__":
    main()
