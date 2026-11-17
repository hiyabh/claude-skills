# -*- coding: utf-8 -*-
"""Load and check a cover spec (JSON). Fills printer presets and defaults, resolves relative paths,
and records every number that is OUR estimate rather than the printer's (spec["estimated"]).

    python spec.py <cover_spec.json>      prints the resolved spec and the estimates
"""
import json
import sys
from pathlib import Path

from common import fail, has_niqqud, parse_colour, resolve_font, warn
from spine import BOARD_THICKNESS, SPINE_EXTRA, spine_mm

PRESETS = {
    # BookPod (verified 2026-11-15, re-verify per references/softcover.md)
    "bookpod": {"binding": "soft", "bleed": 3.2, "marks": False, "colour": "rgb",
                "barcode": {"zone": [51, 30], "edge": 6.35, "position": "spine-bottom", "fill": "clear"},
                "trim_range": [[105, 220], [148, 297]]},
    "offset": {"bleed": 3, "marks": True, "colour": "cmyk"},
    "digital": {"bleed": 3, "marks": True, "colour": "cmyk"},
}
DEFAULTS = {"direction": "rtl", "dpi": 300, "safe": 6, "slug": 12, "icc": "auto", "background": "#ffffff",
            "printer": "offset", "binding": "soft", "text": [], "images": [], "fonts": {}, "art": {}}
HARD_GUESS = {"joint": 9, "wrap": 18, "board_thickness": BOARD_THICKNESS, "spine_extra": SPINE_EXTRA}
BOARD_W_OVER_TRIM = 4      # board + joint is about the page width + 4 mm (bindery drawing, 2026-11-02)
BOARD_H_OVER_TRIM = 5      # board height is about the page height + 5 mm
PANELS = ("front", "back", "spine")
ESTIMATE_NAMES = {"hard.board": "קרטון", "hard.joint": "ביג", "hard.wrap": "גלישה מסביב לקרטון",
                  "hard.board_thickness": "עובי קרטון", "hard.spine_extra": "מרווח בשדרה", "spine": "רוחב שדרה"}
BOOKPOD_MENU = {"A5": (148, 210), "B5": (165, 235), "פרוזה": (135, 210), "A4": (210, 297), "ילדים": (220, 220)}
PAPER_NAMES = {"white": "לבן", "cream": "שמנת", "chromo-matte": "כרומו מט"}


def estimate_text(entry):
    """'hard.joint = 9' -> 'ביג: 9 מ"מ'."""
    key, _, value = entry.partition(" = ")
    return f"{ESTIMATE_NAMES.get(key, key)}: {value.split(' (')[0]} מ\"מ"


def paper_text(paper):
    kind, _, gsm = paper.rpartition("-")
    return f"{PAPER_NAMES.get(kind, kind)} {gsm} גרם" if gsm.isdigit() else paper


def check_bookpod_size(spec):
    if spec["printer"] != "bookpod" or tuple(spec["trim"]) in BOOKPOD_MENU.values():
        return
    near = min(BOOKPOD_MENU, key=lambda k: sum(abs(a - b) for a, b in zip(BOOKPOD_MENU[k], spec["trim"])))
    warn(f"הגודל {spec['trim'][0]:g}x{spec['trim'][1]:g} לא בתפריט של בוקפוד, ויעלה בהדפסה כ-20% יותר. "
         f"הקרוב בתפריט: {near} {BOOKPOD_MENU[near][0]}x{BOOKPOD_MENU[near][1]} (דורש עימוד מחדש).")


def merge_preset(raw):
    spec = dict(DEFAULTS)
    preset = PRESETS.get(raw.get("printer", DEFAULTS["printer"]))
    if preset is None:
        fail(f"printer '{raw.get('printer')}' לא מוכר. האפשרויות: {', '.join(PRESETS)}.")
    spec.update(preset)
    for key, value in raw.items():
        if isinstance(value, dict) and isinstance(spec.get(key), dict):
            spec[key] = {**spec[key], **value}
        else:
            spec[key] = value
    return spec


def fill_hard(spec):
    """Board, joint and turn-in: from the bindery drawing if given, else marked as our estimate."""
    hard = dict(spec.get("hard", {}))
    for key, value in HARD_GUESS.items():
        if key not in hard:
            hard[key] = value
            spec["estimated"].append(f"hard.{key} = {value}")
    if "board" not in hard:
        w, h = spec["trim"]
        hard["board"] = [w + BOARD_W_OVER_TRIM - hard["joint"], h + BOARD_H_OVER_TRIM]
        spec["estimated"].append(f"hard.board = {hard['board'][0]:g}x{hard['board'][1]:g}")
    spec["hard"] = hard


def check_basics(spec):
    for key in ("trim", "pages", "binding"):
        if key not in spec:
            fail(f"חסר השדה '{key}' במפרט. ראה assets/cover_spec.*.example.json.")
    if spec["binding"] not in ("hard", "soft"):
        fail("binding צריך להיות 'hard' (כריכה קשה) או 'soft' (כריכה רכה).")
    if spec["direction"] not in ("rtl", "ltr"):
        fail("direction צריך להיות 'rtl' (ספר עברי) או 'ltr'.")
    rng = spec.get("trim_range")
    if rng and not (rng[0][0] <= spec["trim"][0] <= rng[0][1] and rng[1][0] <= spec["trim"][1] <= rng[1][1]):
        fail(f"גודל הדף {spec['trim']} מחוץ לטווח של {spec['printer']}: רוחב {rng[0]}, גובה {rng[1]} מ\"מ.")


def resolve_paths(spec, base):
    def fix(value):
        return str((base / value).resolve()) if value and not Path(value).is_absolute() else value
    art, spec["missing_art"] = spec["art"], []
    for key in ("wrap", "front", "back", "spine"):
        if art.get(key):
            art[key] = fix(art[key])
            if not Path(art[key]).is_file():
                spec["missing_art"].append(art.pop(key))
    for item in spec["images"]:
        item["file"] = fix(item["file"])
        if not Path(item["file"]).is_file():
            fail(f"התמונה {item['file']} לא נמצאה.")
    spec["fonts"] = {k: str(resolve_font(v)) for k, v in spec["fonts"].items()}


def check_text(spec):
    for i, item in enumerate(spec["text"], 1):
        where = f"טקסט מספר {i} ('{item.get('text', '')[:20]}')"
        if item.get("panel") not in PANELS:
            fail(f"{where}: panel צריך להיות front, back או spine.")
        if item.get("font") not in spec["fonts"]:
            fail(f"{where}: הגופן '{item.get('font')}' לא מוגדר ב-fonts.")
        if has_niqqud(item.get("text", "")):
            fail(f"{where}: יש בו ניקוד או טעמים. מנוע ה-PDF לא ממקם ניקוד, והכיתוב על הכריכה נכתב בלי ניקוד.")
        parse_colour(item.get("colour", "cmyk 0 0 0 100"))
        if not item.get("size"):
            fail(f"{where}: חסר size (גודל מרבי בנקודות).")


def load(path):
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        fail(f"לא הצלחתי לקרוא את {path}: {e}. בדוק שהקובץ קיים ושה-JSON תקין (פסיקים, מרכאות).")
    spec = merge_preset(raw)
    spec["estimated"], spec["spec_path"] = [], str(path.resolve())
    check_basics(spec)
    check_bookpod_size(spec)
    if spec["binding"] == "hard":
        fill_hard(spec)
    resolve_paths(spec, path.parent)
    check_text(spec)
    spec["spine"], spec["spine_source"] = spine_mm(spec)
    if spec["printer"] == "bookpod" and not spec.get("spine_override"):
        spec["spine_source"] = "נוסחת בוקפוד: עמודים / 2 x עובי גיליון"
    elif not spec.get("spine_override"):
        spec["estimated"].append(f"spine = {spec['spine']:g} ({spec['spine_source']})")
    if not spec["marks"]:
        spec["slug"] = 0
    return spec


def main():
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if len(sys.argv) == 2 else 1)
    spec = load(sys.argv[1])
    print(json.dumps({k: v for k, v in spec.items() if k != "text"}, ensure_ascii=False, indent=2))
    for line in spec["estimated"]:
        warn(f"ערך משוער, לא מבית הדפוס: {estimate_text(line)}")


if __name__ == "__main__":
    main()
