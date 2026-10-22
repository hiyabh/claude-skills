# -*- coding: utf-8 -*-
"""Mix build/sfx.json into one WAV the length of the narration.
Usage: python sfx_track.py <audio.m4a> <out.wav>   (exit 1 and no file when sfx is off or there are no events)"""
import json
import subprocess
import sys

import sfx
from config import BUILD

EVENTS = BUILD / "sfx.json"


def duration(audio):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", audio],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def main(audio, out):
    if not EVENTS.exists():
        return 1
    events = json.loads(EVENTS.read_text(encoding="utf-8"))
    if not events:
        return 1
    sfx.build_track(events, duration(audio), out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
