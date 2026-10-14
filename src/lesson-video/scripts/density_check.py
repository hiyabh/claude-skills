# -*- coding: utf-8 -*-
"""Fail when the picture stands still too long. An 'event' is a new beat, an anchored reveal or a camera
shot (explicit or automatic). Any gap above video.json density_max_gap (default 12s) is listed with the
words spoken inside it, so a beat can be anchored there. Usage: python density_check.py"""
import json
import sys

import beats
from anchor import stream
from beat_types_visual import _shot_plan
from config import BUILD, MAX_GAP

SEGMENTS = json.loads((BUILD / "words.json").read_text(encoding="utf-8")) if (BUILD / "words.json").exists() else []


def spoken(t0, t1):
    return " ".join(s["text"] for s in SEGMENTS if t0 <= s["s"] < t1)[:110]


def events_of(ch, beat_list):
    ev = []
    for k, b in enumerate(beat_list):
        end = beat_list[k + 1]["g"] if k + 1 < len(beat_list) else ch["end"]
        ev.append(b["g"])
        ev.extend(b.get("_reveal", []))
        if b["t"] == "story":
            ev.extend(t for t, *_ in _shot_plan(b, b["g"], end - b["g"], b.get("_shots", [])))
    return sorted(ev) + [ch["end"]]


def main():
    words, gaps, total_beats = stream(), [], 0
    for ch in beats.CHAPTERS["chapters"]:
        spec = beats.load_spec(ch["id"])
        if not spec:
            continue
        resolved = beats.resolve(words, spec["beats"], ch)
        total_beats += len(resolved)
        ev = events_of(ch, resolved)
        gaps += [(ch["id"], a, b) for a, b in zip(ev, ev[1:]) if b - a > MAX_GAP]
    dur = beats.CHAPTERS["total"]
    print(f"{total_beats} beats over {dur / 60:.1f} min = one beat per {dur / max(total_beats, 1):.1f}s")
    for cid, a, b in gaps:
        print(f"  STILL {b - a:5.1f}s  {cid} {a:7.1f}-{b:7.1f}  | {spoken(a + 1, b)}")
    print(f"{len(gaps)} gaps over {MAX_GAP}s" if gaps else f"density OK (no still stretch over {MAX_GAP}s)")
    sys.exit(1 if gaps else 0)


if __name__ == "__main__":
    main()
