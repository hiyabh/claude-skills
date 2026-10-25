#!/usr/bin/env python3
"""Propose an effects timeline from what the speaker says -> fx_plan.json.

Reads word timings (transcribe.py), finds speech cues (cues.py: numbers -> growth chart,
an enumeration -> checklist, "imagine" -> green screen, ...), then enforces pacing: a hook in
the first seconds, minimum gaps, heavy effects spread out, no type repeated back to back, a
matte budget, and camera-move fillers so the picture never sits still too long.

The result is a DRAFT. Every effect carries a "why" - Claude reviews it, rewrites params
(on-screen Hebrew text, chat prompt, chart numbers, masthead), drops weak picks, and shows
the table to the user before any matting or rendering.

Usage:
    python plan_fx.py words.json -o fx_plan.json [--pacing reel|long] [--canvas 1080x1920]
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # cues.py sits next to this script
from cues import FILLER_DUR, FILLERS, HEAVY, PACING, RULES

HEB_PREFIXES = "והבלמשכ"
PHRASE_GAP = 0.45          # silence that ends a phrase
PHRASE_MAX_WORDS = 12
HOOK_WINDOW = 1.5          # an effect must start this early
SAME_TYPE_GAP = 12.0       # seconds before the same effect type may repeat
END_PAD = 0.15
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
MAX_CHART_VALUE = 1000


def phrases(words):
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        ends = w[0][-1:] in ".!?" or len(cur) >= PHRASE_MAX_WORDS
        if nxt is None or ends or nxt[1] - w[2] > PHRASE_GAP:
            out.append({"text": " ".join(x[0] for x in cur), "start": cur[0][1], "end": cur[-1][2], "words": cur})
            cur = []
    return out


def norm_tokens(text):
    """Each word plus its forms with up to two Hebrew prefix letters removed
    ('ובטלפון' -> 'ובטלפון', 'בטלפון', 'טלפון'), so cues that start with a prefix letter
    ('לסיכום') still match as written."""
    toks = []
    for raw in text.lower().split():
        t = raw.strip(".,!?;:\"'״׳()-")
        toks.append(t)
        for _ in range(2):
            if len(t) > 3 and t[0] in HEB_PREFIXES:
                t = t[1:]
                toks.append(t)
    return toks


def match_cue(text, toks, cue):
    if cue in "!?%":
        return cue in text
    if " " in cue.strip():
        return cue.strip() in text.lower()
    return any(t == cue or (len(cue) >= 4 and t.startswith(cue)) for t in toks)


def guess_params(kind, ph, nxt):
    """First-pass on-screen text; Claude rewrites these during review."""
    if kind == "growth_chart":
        nums = [float(n.replace(",", ".")) for n in NUMBER_RE.findall(ph["text"])]
        top = next((n for n in nums if 1 < n <= MAX_CHART_VALUE), 10)
        pct = "%" in ph["text"] or "אחוז" in ph["text"]
        return {"from": 0 if pct else 1, "to": top, "suffix": "%" if pct else "x"}
    if kind == "checklist_pop":
        return {"items": [" ".join(p["text"].split()[:2]) for p in nxt[:3]] or ["שלב 1", "שלב 2", "שלב 3"]}
    if kind == "chat_takeover":
        return {"prompt": ph["text"][:70]}
    if kind == "headline_storm":
        return {"lines": [" ".join(p["text"].split()[:4]) for p in [ph] + nxt[:2]]}
    return {}


def candidates(phs):
    out = []
    for i, ph in enumerate(phs):
        toks = norm_tokens(ph["text"])
        for kind, rule in RULES.items():
            hit = next((c for c in rule["cues"] if match_cue(ph["text"], toks, c)), None)
            if hit:
                out.append({"type": kind, "start": round(max(0.0, ph["start"] - 0.05), 2), "dur": rule["dur"],
                            "score": rule["score"], "matte": rule["matte"],
                            "params": guess_params(kind, ph, phs[i + 1:i + 4]),
                            "why": f"cue '{hit}' in: {ph['text'][:60]}"})
    return out


def fits(c, chosen, pace, matte_used, minutes):
    for o in chosen:
        if c["start"] < o["start"] + o["dur"] + pace["gap"] and o["start"] < c["start"] + c["dur"] + pace["gap"]:
            return False
        if c["type"] in HEAVY and o["type"] in HEAVY and abs(c["start"] - o["start"]) < pace["heavy_gap"]:
            return False
        if c["type"] == o["type"] and abs(c["start"] - o["start"]) < SAME_TYPE_GAP:
            return False
    return not (c["matte"] and matte_used + 1 > max(1, round(pace["matte_per_min"] * minutes)))


def select(cands, pace, duration):
    chosen, matte_used, minutes = [], 0, max(duration / 60.0, 0.25)
    for c in sorted(cands, key=lambda x: (-x["score"], x["start"])):
        c["dur"] = round(min(c["dur"], duration - c["start"] - END_PAD), 2)
        if c["dur"] < 0.8 or not fits(c, chosen, pace, matte_used, minutes):
            continue
        chosen.append(c)
        matte_used += c["matte"]
    return sorted(chosen, key=lambda x: x["start"])


def add_hook(chosen, words):
    if not words or (chosen and chosen[0]["start"] <= HOOK_WINDOW):
        return chosen
    t = round(words[0][1], 2)
    hook = {"type": "punch_zoom", "start": t, "dur": 1.1, "params": {}, "matte": False, "why": "hook: open on motion"}
    if not chosen or chosen[0]["start"] > t + hook["dur"] + 0.3:
        chosen.insert(0, hook)
    return chosen


def fill_idle(chosen, words, pace, duration):
    """Insert camera moves into stretches longer than max_idle, aligned to a word start."""
    out, k, cursor = [], 0, 0.0
    for nxt in chosen + [{"start": duration, "dur": 0}]:
        while nxt["start"] - cursor > pace["max_idle"]:
            target = cursor + pace["max_idle"] * 0.6
            w = next((x for x in words if x[1] >= target), None)
            kind = FILLERS[k % len(FILLERS)]
            if not w or w[1] + FILLER_DUR[kind] + pace["gap"] > nxt["start"]:
                break
            out.append({"type": kind, "start": round(w[1], 2), "dur": FILLER_DUR[kind], "params": {},
                        "matte": False, "why": "filler: long stretch without an effect"})
            k += 1
            cursor = w[1] + FILLER_DUR[kind]
        if "type" in nxt:
            out.append(nxt)
            cursor = nxt["start"] + nxt["dur"]
    return out


def link_recap(effects):
    """A closing recap lists what the checklists promised (or the cue phrases of the main effects)."""
    items = [i for e in effects if e["type"] == "checklist_pop" for i in e["params"].get("items", [])]
    if not items:
        items = [e["why"].split(": ", 1)[-1][:24] for e in effects if e["why"].startswith("cue")][:8]
    for e in effects:
        if e["type"] == "recap_checklist":
            e["params"] = {"title": "סיכום", "items": items}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("words")
    ap.add_argument("-o", "--out", default="fx_plan.json")
    ap.add_argument("--pacing", default="reel", choices=sorted(PACING))
    ap.add_argument("--canvas", default="1080x1920")
    ap.add_argument("--duration", type=float, help="footage length (default: last word end + 0.5s)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # Hebrew output through a pipe on non-Hebrew Windows
    words = json.loads(Path(a.words).read_text(encoding="utf-8"))
    duration = a.duration or (words[-1][2] + 0.5 if words else 0)
    pace = PACING[a.pacing]
    chosen = add_hook(select(candidates(phrases(words)), pace, duration), words)
    effects = fill_idle(chosen, words, pace, duration)
    link_recap(effects)
    for e in effects:
        e.pop("score", None)
        e.pop("matte", None)
    w, h = (int(v) for v in a.canvas.lower().split("x"))
    plan = {"canvas": [w, h], "pacing": a.pacing, "theme": {}, "captions": {}, "progress": None, "effects": effects}
    Path(a.out).write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(effects)} effects over {duration:.1f}s ({a.pacing}) -> {a.out}")
    for e in effects:
        print(f"  {e['start']:7.2f}s  {e['type']:<16} {e['why']}")


if __name__ == "__main__":
    main()
