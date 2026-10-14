# -*- coding: utf-8 -*-
"""chapter_spec.json (start phrases) -> chapters.json (global start/end seconds)."""
import json
import subprocess
from pathlib import Path

from anchor import find, stream

BUILD = Path(__file__).resolve().parent
AUDIO = BUILD.parent / "clip" / "assets" / "audio" / "lesson.m4a"


def duration():
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(AUDIO)],
                         capture_output=True, text=True, check=True).stdout
    return round(float(out), 2)


def main():
    words, spec, total = stream(), json.loads((BUILD / "chapter_spec.json").read_text(encoding="utf-8")), duration()
    starts, cursor = [], 0.0
    for ch in spec:
        at = ch["at"]
        t = float(at) if isinstance(at, (int, float)) else (find(words, at, cursor) or [None])[0]
        if t is None:
            raise SystemExit(f"{ch['id']}: {at!r} not found after {cursor:.1f}")
        starts.append(round(t, 2))
        cursor = t
    chapters = [{"id": c["id"], "title": c["title"], "ink": c["ink"], "start": s,
                 "end": starts[i + 1] if i + 1 < len(starts) else total} for i, (c, s) in enumerate(zip(spec, starts))]
    (BUILD / "chapters.json").write_text(json.dumps({"total": total, "chapters": chapters}, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    for c in chapters:
        print(f'{c["id"]:5} {c["start"]:8.2f} {c["end"] - c["start"]:7.1f}s  {c["title"]}')


if __name__ == "__main__":
    main()
