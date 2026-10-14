"""Find the exact start second of phrases in words.json.
Usage: python anchor.py "phrase one" "phrase two" ...   (optionally --after 300 to skip earlier hits)"""
import json
import os
import re
import sys
from pathlib import Path

WORDS = Path(os.environ.get("WORDS_FILE", Path(__file__).resolve().parent / "words.json"))
NIQQUD = re.compile(r"[֑-ׇ]")
PUNCT = re.compile(r"[^\wא-ת ]")


def norm(s):
    return PUNCT.sub("", NIQQUD.sub("", s)).strip()


def merged(words):
    """Whisper splits geresh words ("פיצ" + "'ר", "חז" + "'ל"); glue the apostrophe tail back on."""
    out = []
    for w in words:
        if out and w["w"].strip().startswith(("'", "׳")):
            out[-1] = {**out[-1], "w": out[-1]["w"] + w["w"].strip(), "e": w["e"]}
        else:
            out.append(dict(w))
    return out


def stream():
    out = []
    for seg in json.loads(WORDS.read_text(encoding="utf-8")):
        for w in merged(seg["words"]):
            t = norm(w["w"])
            if t:
                out.append((t, w["s"]))
    return out


def find(words, phrase, after):
    target = norm(phrase).split()
    n = len(target)
    hits = []
    for i in range(len(words) - n + 1):
        if words[i][1] < after:
            continue
        if all(target[k] in words[i + k][0] for k in range(n)):
            hits.append(words[i][1])
    return hits


def main():
    args = sys.argv[1:]
    after = 0.0
    if "--after" in args:
        i = args.index("--after")
        after = float(args[i + 1])
        args = args[:i] + args[i + 2:]
    words = stream()
    for phrase in args:
        hits = find(words, phrase, after)
        print(f"{phrase!r}: {', '.join(f'{h:.2f}' for h in hits[:6]) or 'NOT FOUND'}")


if __name__ == "__main__":
    main()
