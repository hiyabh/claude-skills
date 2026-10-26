#!/usr/bin/env python3
"""Readiness check for archive-media - reports what is missing, in Hebrew, with the install command.

Usage:  python preflight.py        (exit 0 = ready, 1 = something required is missing)
"""
import shutil
import sys

from ia_api import SEARCH_URL, http_get_json

REQUIRED_BINARIES = [("ffmpeg", "חיתוך, קידוד ו-contact sheet"), ("ffprobe", "בדיקת הקליפים")]
INSTALL_HINT = "https://ffmpeg.org/download.html (ב-Windows: winget install Gyan.FFmpeg, ב-macOS: brew install ffmpeg)"


def check_binaries():
    missing = []
    for name, why in REQUIRED_BINARIES:
        ok = shutil.which(name) is not None
        print(f"  {'✓' if ok else '✗'} {name:<10} - {why}")
        if not ok:
            missing.append(name)
    return missing


def check_archive():
    try:
        data = http_get_json(SEARCH_URL, {"q": "collection:prelinger", "fl[]": "identifier",
                                          "rows": 0, "output": "json"})
        found = data["response"]["numFound"]
        print(f"  ✓ archive.org - ה-API עונה ({found:,} סרטים באוסף Prelinger)")
        return True
    except (RuntimeError, KeyError) as err:
        print(f"  ✗ archive.org - אין תשובה: {err}")
        return False


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("בדיקת מוכנות - archive-media\n\nכלים במערכת:")
    missing = check_binaries()
    print("\nרשת:")
    online = check_archive()
    if missing:
        print(f"\nלהתקנת ffmpeg: {INSTALL_HINT}")
    if not online:
        print("לבדוק חיבור לאינטרנט, ואם יש פרוקסי ארגוני - שהוא מתיר את archive.org.")
    ready = not missing and online
    print("\n" + ("מוכן לעבודה." if ready else "חסרים רכיבים - לתקן ולהריץ שוב."))
    sys.exit(0 if ready else 1)


if __name__ == "__main__":
    main()
