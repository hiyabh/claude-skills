# -*- coding: utf-8 -*-
"""Karaoke caption layer for one chapter: the line slides in, the spoken word pops (lift + scale + gold),
and chapter keywords stay highlighted after they are said."""
import html
import json
import re

from config import BUILD, CFG

CAPTIONS = json.loads((BUILD / "captions.json").read_text(encoding="utf-8"))
FG, GOLD = "#F1E9D6", "#E8B84A"
CAP_TRACK = 6
FADE = 0.22
POP = 0.12
CORE = re.compile(r"[^\wא-ת]")
GLOBAL_KEYWORDS = set(CFG.get("keywords", []))


def _is_key(word, keys):
    c = CORE.sub("", word)
    return c in keys or (len(c) > 2 and c[1:] in keys)


def _word_js(bid, times, keys_mask):
    """One compact loop per caption: pop each word at its start, settle at its end."""
    return (f'(function () {{ const ws = R.querySelectorAll("#{bid} .cw"); const T = {json.dumps(times)}; '
            f'const K = {json.dumps(keys_mask)}; T.forEach((t, i) => {{ '
            f'tl.to(ws[i], {{ color: "{GOLD}", scale: 1.1, y: -5, duration: {POP}, ease: "back.out(3)" }}, t[0]); '
            f'tl.to(ws[i], {{ color: K[i] ? "{GOLD}" : "{FG}", scale: 1, y: 0, duration: 0.25 }}, Math.max(t[1], t[0] + {POP})); '
            f'}}); }})();')


def captions_section(cid, start, end, keywords=()):
    keys = GLOBAL_KEYWORDS | set(keywords)
    total = round(end - start, 3)
    rows, js = [], []
    for k, c in enumerate(x for x in CAPTIONS if start <= x["s"] < end):
        s = round(c["s"] - start, 2)
        e = round(max(min(c["e"], end - 0.05) - start, s + FADE * 2), 2)
        bid = f"{cid}-c{k}"
        mask = [1 if _is_key(w["w"], keys) else 0 for w in c["words"]]
        words = " ".join(f'<span class="cw{" ck" if m else ""}">{html.escape(w["w"])}</span>'
                         for w, m in zip(c["words"], mask))
        rows.append(f'<div class="caprow"><div class="capbox" id="{bid}">{words}</div></div>')
        js.append(f'tl.fromTo(R.querySelector("#{bid}"), {{ opacity: 0, y: 26, scale: 0.96 }}, '
                  f'{{ opacity: 1, y: 0, scale: 1, duration: {FADE}, ease: "power2.out" }}, {s});')
        js.append(f'tl.to(R.querySelector("#{bid}"), {{ opacity: 0, y: -10, duration: {FADE}, ease: "power1.in" }}, {round(e - FADE, 2)});')
        times = [[round(w["s"] - start, 2), round(w["e"] - start, 2)] for w in c["words"]]
        js.append(_word_js(bid, times, mask))
    section = (f'<section id="{cid}-caps" class="clip caps" data-start="0" data-duration="{total}" '
               f'data-track-index="{CAP_TRACK}">' + "".join(rows) + "</section>")
    return section, js
