# -*- coding: utf-8 -*-
"""words.json -> captions.json: fix transcription errors, hide private names, group into caption lines.
Names/fixes come from video.json: blocked_names, blocked_stems, timed_drops, fixes."""
import json
import re

from anchor import WORDS, merged
from config import BUILD, CFG

PUNCT = re.compile(r"[^\wא-ת']")
MAX_WORDS = 7
MAX_CHARS = 38
MAX_GAP = 0.8          # a pause longer than this starts a new caption
TAIL = 0.5             # caption stays this long after its last word
PREFIXES = set("ולהבמש")
BLOCKED = set(CFG.get("blocked_names", []))
# Stems catch spelling variants of a name ("תורג" for תורג'מן / תורגמן).
BLOCKED_STEMS = tuple(CFG.get("blocked_stems", []))
# [from, to, token]: a private name the transcriber turned into a real word ("רחל כהן" -> "רחל כוהן").
TIMED_DROPS = [tuple(x) for x in CFG.get("timed_drops", [])]
FIXES = CFG.get("fixes", {})


def core(w):
    return PUNCT.sub("", w)


def clean(w):
    c = core(w)
    if c in BLOCKED or (c[:1] in PREFIXES and c[1:] in BLOCKED):
        return None
    if c in FIXES:
        return w.replace(c, FIXES[c]) if FIXES[c] else None
    return w


def is_dropped(w, prev_blocked):
    if prev_blocked and w["w"].strip().startswith(("'", "׳")):
        return True
    return any(t0 <= w["s"] <= t1 and core(w["w"]) == tok for t0, t1, tok in TIMED_DROPS)


def stem_blocked(w):
    return bool(BLOCKED_STEMS) and any(core(w["w"]).startswith(stem) for stem in BLOCKED_STEMS)


def groups_of(segments):
    out = []
    for seg in segments:
        cur, prev_blocked = [], False
        for w in merged(seg["words"]):
            text = None if is_dropped(w, prev_blocked) else clean(w["w"])
            prev_blocked = stem_blocked(w)
            if not text or prev_blocked:
                continue
            item = {"w": text, "s": w["s"], "e": w["e"]}
            chars = sum(len(x["w"]) + 1 for x in cur) + len(text)
            if cur and (len(cur) >= MAX_WORDS or chars > MAX_CHARS or w["s"] - cur[-1]["e"] > MAX_GAP):
                out.append(cur)
                cur = []
            cur.append(item)
        if cur:
            out.append(cur)
    return out


def main():
    groups = groups_of(json.loads(WORDS.read_text(encoding="utf-8")))
    caps = []
    for i, g in enumerate(groups):
        nxt = groups[i + 1][0]["s"] if i + 1 < len(groups) else g[-1]["e"] + TAIL
        caps.append({"s": g[0]["s"], "e": round(min(g[-1]["e"] + TAIL, nxt - 0.05), 2), "words": g})
    (BUILD / "captions.json").write_text(json.dumps(caps, ensure_ascii=False, indent=0), encoding="utf-8")
    print(len(caps), "captions,", sum(len(c["words"]) for c in caps), "words")


if __name__ == "__main__":
    main()
