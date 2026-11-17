# -*- coding: utf-8 -*-
"""Spine width from the page count and the paper. A printer's drawing always wins over this.

    python spine.py <pages> <paper> [--hard] [--board 2.5]
    python spine.py --from-drawing <pagesA> <spineA> <pagesB> <spineB>   (paper caliper from two spines)

The paper table is BookPod's (verified 2026-11-15) and is an ESTIMATE for other printers: the same
"80 gsm" was 0.10 mm a leaf at BookPod and 0.12 at an offset bindery. Ask the printer, or read it
off their cover drawing with --from-drawing.
"""
import argparse

from common import fail

# mm per LEAF (one sheet = two pages)
PAPER_MM = {
    "white-70": 0.09, "white-80": 0.10, "white-90": 0.13, "white-110": 0.15,
    "cream-70": 0.09, "cream-80": 0.10, "cream-90": 0.13, "cream-110": 0.15,
    "chromo-matte-105": 0.10, "chromo-matte-115": 0.11, "chromo-matte-130": 0.125,
    "chromo-matte-170": 0.16,
}
BOARD_THICKNESS = 2.5      # mm, grey board of a case binding (typical 2-3)
SPINE_EXTRA = 1.0          # mm of play around the block in a case binding


def caliper(spec):
    """mm per leaf: an explicit 'caliper_per_leaf' wins over the paper name."""
    if spec.get("caliper_per_leaf"):
        return float(spec["caliper_per_leaf"])
    paper = spec.get("paper", "white-80")
    if paper not in PAPER_MM:
        fail(f"סוג נייר לא מוכר: '{paper}'. האפשרויות: {', '.join(PAPER_MM)}, "
             f"או 'caliper_per_leaf' (עובי גיליון במ\"מ) לפי בית הדפוס.")
    return PAPER_MM[paper]


def block_mm(pages, leaf):
    return pages / 2 * leaf


def spine_mm(spec):
    """(width, source). source tells the author whether the number is from the printer or ours."""
    if spec.get("spine_override"):
        return float(spec["spine_override"]), "מבית הדפוס"
    block = block_mm(spec["pages"], caliper(spec))
    if spec["binding"] == "hard":
        hard = spec["hard"]
        width = block + 2 * hard["board_thickness"] + hard["spine_extra"]
        return round(width, 1), "הערכה - לקבל מהכריכייה"
    return round(block, 2), "חישוב לפי עובי הנייר"


def caliper_from_drawing(pages_a, spine_a, pages_b, spine_b):
    """Two volumes on the same paper: the spine difference over the leaf difference."""
    leaves = abs(pages_b - pages_a) / 2
    if leaves == 0:
        fail("שני הכרכים באותו מספר עמודים, ואי אפשר להסיק מהם את עובי הנייר.")
    return abs(spine_b - spine_a) / leaves


def main():
    ap = argparse.ArgumentParser(description="רוחב שדרה")
    ap.add_argument("pages", nargs="?", type=int)
    ap.add_argument("paper", nargs="?", default="white-80")
    ap.add_argument("--hard", action="store_true")
    ap.add_argument("--board", type=float, default=BOARD_THICKNESS)
    ap.add_argument("--from-drawing", nargs=4, type=float, metavar=("PA", "SA", "PB", "SB"))
    a = ap.parse_args()
    if a.from_drawing:
        leaf = caliper_from_drawing(*a.from_drawing)
        print(f"עובי גיליון לפי השרטוט: {leaf:.3f} מ\"מ")
        return
    if not a.pages:
        fail("כתוב מספר עמודים, למשל: python spine.py 320 white-80")
    spec = {"pages": a.pages, "paper": a.paper, "binding": "hard" if a.hard else "soft",
            "hard": {"board_thickness": a.board, "spine_extra": SPINE_EXTRA}}
    width, source = spine_mm(spec)
    print(f"שדרה: {width:g} מ\"מ ({source})")


if __name__ == "__main__":
    main()
