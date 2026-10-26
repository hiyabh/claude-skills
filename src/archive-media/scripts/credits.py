#!/usr/bin/env python3
"""Turn sources.json (written by fetch_clip.py) into credits.md + a one-line on-screen credit.

Usage:  python credits.py --out work/
Prints a rights summary; any 🟡/🔴 clip is listed first so it can't slip into a delivery unnoticed.
"""
import argparse
import json
import os
import sys

from ia_api import GREEN

ONSCREEN_PRELINGER = "Archival footage: Prelinger Archives / Internet Archive"
ONSCREEN_78 = "Music: Great 78 Project / Internet Archive"
ONSCREEN_OTHER = "Archival media: Internet Archive"


def load(out_dir):
    path = os.path.join(out_dir, "sources.json")
    if not os.path.exists(path):
        raise SystemExit(f"No sources.json in {out_dir}. Run fetch_clip.py first - it writes one per clip.")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def onscreen_line(entries):
    cols = {c for e in entries for c in e.get("collection") or []}
    parts = []
    if "prelinger" in cols:
        parts.append(ONSCREEN_PRELINGER)
    if "georgeblood" in cols or "78rpm" in cols:
        parts.append(ONSCREEN_78)
    return " · ".join(parts) or ONSCREEN_OTHER


def entry_md(e):
    who = f" - {e['creator']}" if e.get("creator") else ""
    lic = e.get("licenseurl") or "לא מסומן"
    return (f"- {e['grade']} **{e['title']}**{who} ({e.get('date') or '----'})  \n"
            f"  {e['details']} · קטע {e['start_s']:.1f}-{e['end_s']:.1f}s · רישיון: {lic}  \n"
            f"  {e['reason']}")


def build_md(entries):
    flagged = [e for e in entries if e["grade"] != GREEN]
    lines = ["# קרדיטים - חומרי ארכיון", "", f"שורת קרדיט למסך: `{onscreen_line(entries)}`", ""]
    if flagged:
        lines += ["## דורש החלטה לפני מסירה", ""] + [entry_md(e) for e in flagged] + [""]
    lines += ["## כל המקורות", ""] + [entry_md(e) for e in entries]
    return "\n".join(lines) + "\n", flagged


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=".")
    args = ap.parse_args()
    entries = load(args.out)
    text, flagged = build_md(entries)
    path = os.path.join(args.out, "credits.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"נשמר: {path}  ({len(entries)} קטעים)\nקרדיט למסך: {onscreen_line(entries)}")
    if flagged:
        print(f"\nשים לב: {len(flagged)} קטעים אינם 🟢 - לא למסור לפני החלטה מפורשת:")
        for e in flagged:
            print(f"  {e['grade']} {e['title']} - {e['reason']}")


if __name__ == "__main__":
    main()
