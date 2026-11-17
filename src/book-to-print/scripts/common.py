# -*- coding: utf-8 -*-
"""Shared helpers: units, paths, fonts, colours, ICC profiles and Hebrew error messages.

Every script in this skill imports this first. Units are millimetres unless a name says otherwise.
"""
import os
import sys
from pathlib import Path

MM_PER_IN = 25.4
PT_PER_MM = 72 / MM_PER_IN
SKILL_DIR = Path(__file__).resolve().parent.parent
FONTS_DIR = SKILL_DIR / "assets" / "fonts"
ICC_DIR = SKILL_DIR / "assets" / "icc"
WINDOWS_FONTS = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
WINDOWS_ICC = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "spool" / "drivers" / "color"
# ISO Coated v2 (ECI) = FOGRA39, the usual profile for coated/laminated covers in Israeli offset shops.
ICC_PREFERRED = ("ISOcoated_v2_eci.icc", "ISOcoated_v2_300_eci.icc", "CoatedFOGRA39.icc")
ICC_FALLBACK = "RSWOP.icm"          # US SWOP, ships with Windows: usable, but ask the printer
NIQQUD = range(0x0591, 0x05C8)      # cantillation + vowel points: the PDF engine cannot position them
FORBIDDEN_IN_NAMES = set('<>:/\\|?*')

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def fail(message):
    """Stop with a Hebrew message that says what is wrong and what to do."""
    print(f"שגיאה: {message}", file=sys.stderr)
    sys.exit(1)


def warn(message):
    print(f"אזהרה: {message}")


def pt(mm):
    return mm * PT_PER_MM


def px(mm, dpi):
    return round(mm / MM_PER_IN * dpi)


def resolve_font(name):
    """A font file from a bare file name, a skill font, a Windows font or a full path."""
    candidates = [Path(name), FONTS_DIR / name, WINDOWS_FONTS / name]
    for path in candidates:
        if path.is_file():
            if path.suffix.lower() == ".otf":
                fail(f"הגופן {path.name} הוא OTF, ומנוע ה-PDF תומך רק ב-TTF. בחר גרסת TTF של הגופן.")
            return path
    fail(f"לא נמצא קובץ גופן בשם '{name}'. חפשתי ב-{FONTS_DIR} וב-{WINDOWS_FONTS}. "
         f"כתוב שם קובץ מדויק (למשל david.ttf) או נתיב מלא.")


def find_icc(choice="auto"):
    """(path, note). 'auto' prefers ISO Coated v2 (FOGRA39), then the Windows SWOP profile."""
    if choice and choice != "auto":
        path = Path(choice)
        if not path.is_file():
            fail(f"פרופיל הצבע {choice} לא נמצא. הרץ setup_check.py או כתוב 'auto'.")
        return path, "לפי המפרט"
    for name in ICC_PREFERRED:
        for folder in (ICC_DIR, WINDOWS_ICC):
            if (folder / name).is_file():
                return folder / name, "ISO Coated v2 (FOGRA39)"
    if (WINDOWS_ICC / ICC_FALLBACK).is_file():
        warn("לא נמצא ISO Coated v2. משתמש ב-US SWOP של Windows. הרץ setup_check.py כדי להוריד את הפרופיל.")
        return WINDOWS_ICC / ICC_FALLBACK, "US Web Coated SWOP (גיבוי)"
    fail("לא נמצא שום פרופיל CMYK. הרץ setup_check.py.")


def parse_colour(value):
    """('cmyk', (c, m, y, k) in 0-1) from 'cmyk 0 20 90 0', or ('rgb', (r, g, b)) from '#rrggbb'."""
    text = str(value).strip().lower()
    if text.startswith("cmyk"):
        parts = text[4:].replace(",", " ").split()
        if len(parts) != 4:
            fail(f"צבע '{value}': צריך ארבעה מספרים, למשל 'cmyk 0 0 0 100'.")
        return "cmyk", tuple(float(p) / 100 for p in parts)
    if text.startswith("#") and len(text) == 7:
        return "rgb", tuple(int(text[i:i + 2], 16) for i in (1, 3, 5))
    fail(f"צבע '{value}' לא מובן. כתוב '#1a2b3c' או 'cmyk C M Y K' (באחוזים).")


def has_niqqud(text):
    return any(ord(ch) in NIQQUD for ch in text)


def safe_name(text):
    """A file name Windows accepts: gershayim for '"', no other forbidden characters."""
    text = text.replace('"', "״").replace("'", "׳")
    return "".join(ch for ch in text if ch not in FORBIDDEN_IN_NAMES).strip(" .")


def mm_from_pt(value):
    return value / PT_PER_MM
