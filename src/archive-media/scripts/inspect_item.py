#!/usr/bin/env python3
"""Inspect one archive.org item: rights grade, best file, and a contact sheet to pick shots from.

Usage:
  python inspect_item.py OnGuard1956 --out work/                 (24 frames across the whole film)
  python inspect_item.py OnGuard1956 --range 120-240 --out work/ (zoom into a section)
  python inspect_item.py 78_in-siam_the-all-star-trio_gbia0083310a   (audio: lists tracks)
The contact sheet is read with the Read tool; each cell is labelled with its timestamp.
Films up to CACHE_MAX_MB are downloaded once to <out>/.ia-cache (fetch_clip.py reuses the copy);
larger ones are sampled with HTTP seeks. Archive.org's own '.thumbs' are NOT used: their file-name
numbers are not seconds in the playable file (verified 2026-10-26), so shots picked from them miss.
"""
import argparse
import json
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

from ia_api import DETAILS_URL, item_metadata, rights_grade
from media_files import (audio_tracks, best_video, cache_path, describe, download, label_font,
                         require_ffmpeg, run_ffmpeg)

DEFAULT_FRAMES = 24
GRID_COLS = 6
CELL_WIDTH = 320
FETCH_WORKERS = 4
EDGE_MARGIN_S = 1.0
FRAME_RETRIES = 2
CACHE_MAX_MB = 400


def stamp(seconds):
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def timestamps(length, frames, rng):
    start, end = rng if rng else (0.0, length)
    end = min(end, length - EDGE_MARGIN_S) if length else end
    step = (end - start) / frames
    return [round(start + step * (i + 0.5), 2) for i in range(frames)]


def grab_frame(t, src, path, font):
    vf = f"scale={CELL_WIDTH}:-2,format=yuvj420p"
    if font:
        vf += (f",drawtext=fontfile='{font}':text='{stamp(t).replace(':', chr(92) + ':')}'"
               ":x=6:y=6:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=4")
    args = ["-ss", str(t), "-i", src, "-frames:v", "1", "-vf", vf, "-q:v", "3", path]
    for attempt in range(FRAME_RETRIES):
        try:
            return run_ffmpeg(args, timeout=180)
        except RuntimeError:
            if attempt == FRAME_RETRIES - 1:
                raise


def frame_source(identifier, video, out_dir):
    """Local cached copy when small enough (fast sheet + fast cuts later), else the remote URL."""
    if video["size_mb"] > CACHE_MAX_MB:
        print(f"קובץ גדול ({video['size_mb']}MB) - דוגם בקפיצות HTTP, בלי הורדה מלאה (איטי יותר).")
        return video["url"]
    path = cache_path(out_dir, identifier, video["name"])
    if not os.path.exists(path):
        print(f"מוריד למטמון ({video['size_mb']}MB, פעם אחת)...")
    return download(video["url"], path)


def contact_sheet(src, times, out_path):
    """Grab frames in parallel, then tile them into one image."""
    font = label_font()
    with tempfile.TemporaryDirectory() as tmp:
        paths = [os.path.join(tmp, f"f_{i:03d}.jpg") for i in range(len(times))]
        with ThreadPoolExecutor(FETCH_WORKERS) as pool:
            list(pool.map(lambda a: grab_frame(a[0], src, a[1], font), zip(times, paths)))
        rows = -(-len(times) // GRID_COLS)
        run_ffmpeg(["-framerate", "1", "-i", os.path.join(tmp, "f_%03d.jpg"),
                    "-vf", f"tile={GRID_COLS}x{rows}:padding=4:color=black", "-frames:v", "1", out_path])
    return font is not None


def report_video(identifier, video, args):
    print(f"קובץ נבחר: {video['name']} ({video['format']}, {video['width']}x{video['height']}, "
          f"{stamp(video['length_s'])}, {video['size_mb']}MB)")
    times = timestamps(video["length_s"], args.frames, args.range)
    sheet = os.path.join(args.out, f"sheet_{identifier}.jpg")
    labelled = contact_sheet(frame_source(identifier, video, args.out), times, sheet)
    print(f"\ncontact sheet: {sheet}  (שורות של {GRID_COLS}, משמאל לימין)")
    if not labelled:
        print("לא נמצא פונט לתוויות - מיפוי תא→זמן:")
    print("  " + "  ".join(f"{i + 1}={stamp(t)}" for i, t in enumerate(times)))
    return {"video": video, "sheet": sheet, "sheet_times": times}


def report_audio(identifier, files):
    tracks = [describe(identifier, f) for f in audio_tracks(files)]
    print("רצועות שמע:")
    for i, t in enumerate(tracks, 1):
        print(f"  {i}. {t['name']}  ({stamp(t['length_s'])}, {t['format']})")
    return {"audio": tracks}


def parse_range(text):
    if not text:
        return None
    a, _, b = text.partition("-")
    return float(a), float(b)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("identifier")
    ap.add_argument("--frames", type=int, default=DEFAULT_FRAMES)
    ap.add_argument("--range", type=parse_range, help="seconds, e.g. 120-240")
    ap.add_argument("--out", default=".")
    args = ap.parse_args()
    require_ffmpeg()
    os.makedirs(args.out, exist_ok=True)

    data = item_metadata(args.identifier)
    md = data["metadata"]
    grade, reason = rights_grade(md)
    print(f"{md.get('title')}  [{md.get('date') or md.get('year') or '----'}]\n{DETAILS_URL.format(args.identifier)}")
    print(f"זכויות: {grade} {reason}\nרישיון: {md.get('licenseurl') or 'לא מסומן'}\n")
    info = {"identifier": args.identifier, "title": md.get("title"), "grade": grade, "reason": reason,
            "licenseurl": md.get("licenseurl")}
    video = best_video(data["files"])
    if video:
        info.update(report_video(args.identifier, describe(args.identifier, video), args))
    else:
        info.update(report_audio(args.identifier, data["files"]))
    path = os.path.join(args.out, f"item_{args.identifier}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(info, fh, ensure_ascii=False, indent=2)
    print(f"\nנשמר: {path}")


if __name__ == "__main__":
    main()
