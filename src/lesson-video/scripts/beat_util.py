# -*- coding: utf-8 -*-
"""Shared helpers for the beat renderers. Times are chapter-local seconds."""
import html
import re

STAGGER = 0.45          # default gap between reveals that have no anchor
HL_RE = re.compile(r"\*([^*]+)\*")
GOLDEN = 0.6180339887   # spreads seeded positions evenly without randomness
KEN_PRESETS = [         # (from, to, x, y) - rotated so repeated images never move the same way
    (1.02, 1.14, -50, 0), (1.14, 1.02, 0, 20), (1.0, 1.12, 40, -12), (1.12, 1.0, -30, 0),
]


def esc(text):
    """Escape, then turn *word* into a highlight span swept by K.mark."""
    return HL_RE.sub(r'<span class="hl">\1<i class="bar"></i></span>', html.escape(text or ""))


def times(rel, n, start, gap=STAGGER):
    """Reveal times: explicit anchors when given, else a stagger after the previous reveal."""
    out = []
    for k in range(n):
        out.append(rel[k] if k < len(rel) else round((out[-1] + gap) if out else start, 2))
    return out


def breathe(bid, sel, t0, dur, scale=1.02):
    if dur <= 1:
        return []
    return [f'K.breathe(tl, R, "#{bid} {sel}", {round(t0, 2)}, {round(dur, 2)}, {{ scale: {scale} }});']


def q(bid, sel, k=None):
    """JS expression for one element (k given) or a NodeList inside the beat."""
    if k is None:
        return f'R.querySelectorAll("#{bid} {sel}")'
    return f'R.querySelectorAll("#{bid} {sel}")[{k}]'


def particles(bid, s, dur, n=14):
    """Deterministic drifting light motes over a picture (no Math.random)."""
    dots = "".join(
        f'<i class="mote" style="left:{(k * GOLDEN * 100) % 100:.1f}%;top:{30 + (k * 37) % 65}%;'
        f'width:{6 + k % 4 * 3}px;height:{6 + k % 4 * 3}px"></i>' for k in range(n))
    js = [f'{q(bid, ".mote")}.forEach((m, k) => tl.fromTo(m, {{ opacity: 0, y: 0 }}, '
          f'{{ opacity: 0.55, y: -160 - (k % 5) * 40, duration: {round(dur, 2)}, ease: "none" }}, {s}));']
    return f'<div class="motes">{dots}</div>', js


def word_reveal(bid, sel, t, text, span=3.0):
    """Word-by-word reveal paced to fit `span` seconds."""
    n = max(len(text.split()), 1)
    return f'K.words(tl, R, "#{bid} {sel}", {round(t, 2)}, {{ stagger: {round(min(0.12, span / n), 3)} }});'
