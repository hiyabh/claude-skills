#!/usr/bin/env python3
"""Search archive.org for archival b-roll or period music and grade each hit's reuse rights.

Usage:
  python search.py --preset prelinger --query "computers OR automation" --cleared-only
  python search.py --preset 78rpm --query "foxtrot" --years 1900-1925
  python search.py --preset live --query "jazz"            (always non-commercial)
Writes candidates.json (in --out, default: current dir) for inspect_item.py / fetch_clip.py.
"""
import argparse
import json
import os
import sys

from ia_api import GREEN, PRESETS, advanced_search, as_list, build_query, item_year, rights_grade

TITLE_WIDTH = 48
DEFAULT_ROWS = 25


def parse_years(text):
    if not text:
        return None
    start, _, end = text.partition("-")
    if not (start.isdigit() and end.isdigit()):
        raise SystemExit(f"--years must look like 1950-1965, got '{text}'.")
    return int(start), int(end)


def runtime_seconds(raw):
    """'12:15' / '00:03:44' / '735.3' -> seconds (None if unparseable)."""
    if not raw:
        return None
    raw = str(as_list(raw)[0]).strip()
    try:
        if ":" in raw:
            secs = 0
            for part in raw.split(":"):
                secs = secs * 60 + float(part)
            return secs
        return float(raw.split()[0])
    except ValueError:
        return None


def to_row(doc):
    grade, reason = rights_grade(doc)
    return {"identifier": doc["identifier"], "title": str(as_list(doc.get("title"))[0])[:120],
            "year": item_year(doc), "runtime_s": runtime_seconds(doc.get("runtime")),
            "downloads": doc.get("downloads"), "licenseurl": doc.get("licenseurl"),
            "creator": ", ".join(map(str, as_list(doc.get("creator"))))[:80],
            "grade": grade, "reason": reason,
            "details": f"https://archive.org/details/{doc['identifier']}"}


def keep(row, args):
    if args.cleared_only and row["grade"] != GREEN:
        return False
    if args.min_runtime and (row["runtime_s"] or 0) < args.min_runtime:
        return False
    return True


def print_table(rows, total, query):
    print(f"שאילתה: {query}\nנמצאו {total} פריטים, מוצגים {len(rows)}:\n")
    for i, r in enumerate(rows, 1):
        dur = f"{int(r['runtime_s'] // 60)}:{int(r['runtime_s'] % 60):02d}" if r["runtime_s"] else "?"
        print(f"{i:>2}. {r['grade']} {r['title'][:TITLE_WIDTH]:<{TITLE_WIDTH}} {r['year'] or '----'} {dur:>6}")
        print(f"     {r['identifier']}")
        print(f"     {r['reason']}")
    if any(r["grade"] != GREEN for r in rows):
        print("\n🔴 = לא להכניס לתוצר מסחרי. 🟡 = רק אחרי בדיקה והחלטה מפורשת.")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preset", choices=sorted(PRESETS), default="prelinger")
    ap.add_argument("--query", default="", help="Lucene words, e.g. 'factory OR assembly line'")
    ap.add_argument("--years", help="range like 1950-1965")
    ap.add_argument("--min-runtime", type=float, default=0, help="seconds")
    ap.add_argument("--cleared-only", action="store_true", help=f"keep only {GREEN} items")
    ap.add_argument("--rows", type=int, default=DEFAULT_ROWS)
    ap.add_argument("--out", default=".")
    args = ap.parse_args()

    query = build_query(args.query, args.preset, parse_years(args.years), args.cleared_only)
    total, docs = advanced_search(query, rows=args.rows * 2 if args.cleared_only else args.rows)
    rows = [r for r in map(to_row, docs) if keep(r, args)][: args.rows]
    print_table(rows, total, query)
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, "candidates.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"query": query, "preset": args.preset, "items": rows}, fh, ensure_ascii=False, indent=2)
    print(f"\nנשמר: {path}")


if __name__ == "__main__":
    main()
