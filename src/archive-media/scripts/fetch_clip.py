#!/usr/bin/env python3
"""Cut an edit-ready clip from an archive.org item and log it in sources.json for credits.

Video (b-roll):  python fetch_clip.py Century21964 --start 5:00 --end 5:06 --out work/
                 -> 1920x1080 30fps H.264, NO audio by default (old soundtracks can be protected).
                 --size 1080x1920 for vertical, --fit pad to keep the whole 4:3 frame.
Audio (music):   python fetch_clip.py <78-id> --start 0:08 --end 0:40 --restore-78 --out work/
                 -> loudness-normalised .m4a; --restore-78 adds gentle hiss/rumble cleanup.
                 The track (MP3 by default, FLAC with --hq) is cached whole first.
Rights gate:     🔴 items are refused unless --allow-noncommercial (private, non-commercial use only).
"""
import argparse
import contextlib
import json
import os
import re
import sys
import time

from ia_api import DETAILS_URL, RED, YELLOW, as_list, item_metadata, rights_grade
from media_files import (audio_tracks, best_video, cache_path, describe, download, probe, require_ffmpeg,
                         run_ffmpeg)

FPS = 30
CRF = 18
AUDIO_BITRATE = "192k"
FADE_IN_S = 0.3
FADE_OUT_S = 1.0
LOUDNORM = "loudnorm=I=-16:TP=-1.5:LRA=11"
RESTORE_78 = "highpass=f=60,lowpass=f=9000,afftdn=nf=-25"
LOCK_TRIES = 100
LOCK_WAIT_S = 0.1
MIN_DURATION_RATIO = 0.9


def parse_time(text):
    """'5:06', '1:02:03' or '306.5' -> seconds."""
    secs = 0.0
    for part in str(text).split(":"):
        secs = secs * 60 + float(part)
    return secs


def slug(text, limit=40):
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")[:limit] or "clip"


def video_filter(size, fit):
    w, h = size.lower().split("x")
    if fit == "pad":
        scale = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"
    else:
        scale = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    return f"{scale},setsar=1,fps={FPS},format=yuv420p"


def source_for(item_id, media, kind, out_dir):
    """Cached copy when present. Audio is always cached first: remote FLAC/MP3 seeks can silently
    yield an empty file. Video falls back to HTTP seeks (films can be hundreds of MB)."""
    cached = cache_path(out_dir, item_id, media["name"])
    if kind == "audio" or os.path.exists(cached):
        return download(media["url"], cached)
    return media["url"]


def verify(clip, kind, dur):
    kinds, got = probe(clip)
    if kind not in kinds or got < dur * MIN_DURATION_RATIO:
        raise SystemExit(f"Clip check failed: {clip} has streams {sorted(kinds) or 'none'} and {got:.1f}s "
                         f"(expected {kind}, ~{dur}s). The source may be cut short - rerun; if it repeats, "
                         "try another file of the item (inspect_item.py) or a shorter range.")


def cut_video(src, start, dur, out_path, args):
    audio = ["-c:a", "aac", "-b:a", AUDIO_BITRATE, "-af", LOUDNORM] if args.keep_audio else ["-an"]
    run_ffmpeg(["-ss", str(start), "-i", src, "-t", str(dur), "-vf", video_filter(args.size, args.fit),
                "-c:v", "libx264", "-preset", "medium", "-crf", str(CRF), "-movflags", "+faststart",
                *audio, out_path], timeout=900)


def cut_audio(src, start, dur, out_path, args):
    chain = [RESTORE_78] if args.restore_78 else []
    chain += [LOUDNORM, f"afade=t=in:d={FADE_IN_S}", f"afade=t=out:st={max(dur - FADE_OUT_S, 0)}:d={FADE_OUT_S}"]
    run_ffmpeg(["-ss", str(start), "-i", src, "-t", str(dur), "-vn", "-af", ",".join(chain),
                "-ar", "48000", "-c:a", "aac", "-b:a", AUDIO_BITRATE, out_path], timeout=600)


def pick_media(item_id, files, track, lossless):
    video = best_video(files)
    if video and not track:
        return "video", describe(item_id, video)
    tracks = audio_tracks(files, lossless)
    if not tracks:
        raise SystemExit(f"No playable video or audio file in '{item_id}'. Open {DETAILS_URL.format(item_id)} to check.")
    index = (track or 1) - 1
    if index >= len(tracks):
        raise SystemExit(f"--track {track} is out of range: the item has {len(tracks)} track(s).")
    return "audio", describe(item_id, tracks[index])


def gate(grade, reason, args):
    if grade == RED and not args.allow_noncommercial:
        raise SystemExit(f"🔴 נחסם: {reason}\nלשימוש פרטי/לא-מסחרי בלבד - הוסף --allow-noncommercial אם זה המקרה.")
    if grade == YELLOW:
        print(f"🟡 אזהרה: {reason}")


@contextlib.contextmanager
def file_lock(path):
    """Exclusive lock file, so parallel fetch_clip.py runs don't drop each other's log entries."""
    lock = path + ".lock"
    for _ in range(LOCK_TRIES):
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL)
            break
        except FileExistsError:
            time.sleep(LOCK_WAIT_S)
    else:
        raise SystemExit(f"Timed out waiting for {lock}. If no other fetch is running, delete it and retry.")
    try:
        yield
    finally:
        os.close(fd)
        os.remove(lock)


def log_source(out_dir, entry):
    path = os.path.join(out_dir, "sources.json")
    with file_lock(path):
        data = []
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        data = [d for d in data if d["clip"] != entry["clip"]] + [entry]
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
    return path


def build_entry(item_id, md, media, kind, start, end, clip, grade, reason):
    return {"clip": clip, "kind": kind, "identifier": item_id, "title": md.get("title"),
            "creator": ", ".join(map(str, as_list(md.get("creator")))) or None,
            "date": md.get("date") or md.get("year"), "file": media["name"],
            "start_s": start, "end_s": end, "grade": grade, "reason": reason,
            "licenseurl": md.get("licenseurl"), "details": DETAILS_URL.format(item_id),
            "collection": as_list(md.get("collection"))}


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("identifier")
    ap.add_argument("--start", required=True, type=parse_time)
    ap.add_argument("--end", required=True, type=parse_time)
    ap.add_argument("--track", type=int, help="audio track number from inspect_item.py (1-based)")
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--fit", choices=["crop", "pad"], default="crop")
    ap.add_argument("--keep-audio", action="store_true", help="keep the film's own soundtrack")
    ap.add_argument("--restore-78", action="store_true", help="hiss/rumble cleanup for 78rpm audio")
    ap.add_argument("--hq", action="store_true", help="use the lossless FLAC instead of the MP3")
    ap.add_argument("--allow-noncommercial", action="store_true")
    ap.add_argument("--name", help="output base name (ASCII)")
    ap.add_argument("--out", default=".")
    return ap.parse_args()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    if args.end <= args.start:
        raise SystemExit("--end must be after --start.")
    require_ffmpeg()
    os.makedirs(args.out, exist_ok=True)
    data = item_metadata(args.identifier)
    md = data["metadata"]
    grade, reason = rights_grade(md)
    gate(grade, reason, args)
    kind, media = pick_media(args.identifier, data["files"], args.track, args.hq)
    dur = round(args.end - args.start, 3)
    ext = "mp4" if kind == "video" else "m4a"
    clip = os.path.join(args.out, f"{args.name or slug(args.identifier)}_{int(args.start)}-{int(args.end)}.{ext}")
    cutter = cut_video if kind == "video" else cut_audio
    cutter(source_for(args.identifier, media, kind, args.out), args.start, dur, clip, args)
    verify(clip, kind, dur)
    entry = build_entry(args.identifier, md, media, kind, args.start, args.end, clip, grade, reason)
    print(f"{grade} נוצר: {clip}  ({dur}s, {kind})\nנרשם ב: {log_source(args.out, entry)}")


if __name__ == "__main__":
    main()
