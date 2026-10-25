#!/usr/bin/env python3
"""Word-level transcript for planning and karaoke captions -> words.json [[text, start, end], ...].

Uses faster-whisper (local, no API). Hebrew by default.

Usage:
    python transcribe.py footage.mp4 -o words.json [--lang he] [--model large-v3]
"""
import argparse
import json
import sys

DEFAULT_MODEL = "large-v3"
PUNCT = ".,!?;:\"'״׳…"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio")
    ap.add_argument("-o", "--out", default="words.json")
    ap.add_argument("--lang", default="he")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # Hebrew output through a pipe on non-Hebrew Windows
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("ERROR: faster-whisper is not installed - run `pip install faster-whisper`.")
    model = WhisperModel(a.model, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(a.audio, language=a.lang, word_timestamps=True, vad_filter=True)
    words = []
    for seg in segments:
        for w in seg.words or []:
            text = w.word.strip()
            if text.strip(PUNCT):
                words.append([text, round(w.start, 3), round(w.end, 3)])
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False)
    print(f"{len(words)} words -> {a.out}")


if __name__ == "__main__":
    main()
