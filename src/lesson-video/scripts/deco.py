# -*- coding: utf-8 -*-
"""Colour and playful motion for every beat, at zero cost (pure CSS/SVG + GSAP, deterministic).

- accent(): each beat gets its own accent colour by overriding --torah on its section, so titles,
  highlight bars, chips, dots and step numbers rotate through a palette instead of one gold.
- shapes(): small floating shapes (ring, dot, plus, squiggle, triangle, sparkle) pop into the
  margins of text and diagram beats, then drift and spin gently until the beat fades out.
Positions and choices derive from the beat index only, so every render is identical."""

PALETTE = ["#E8B84A", "#EE9A70", "#86B9EA", "#B9A2E8", "#6CCB9C", "#F28DB2"]
NO_SHAPES = ("story", "imgtext", "split", "title", "closing", "link", "phone")
# (left %, top %) slots in the side margins, clear of the centre text, the top bar and the captions.
SLOTS = [(3.5, 20), (93, 24), (6, 64), (91, 60), (14, 14), (82, 13), (2.5, 42), (95.5, 44)]
# Right-aligned layouts (lists) fill the right margin with text, so their shapes stay on the left.
LEFT_ONLY = ("list",)
LEFT_SLOTS = [(3.5, 20), (6, 64), (14, 14), (2.5, 42), (12, 78), (20, 30), (9, 52), (24, 70)]
N_SHAPES = 5
SIZE = (46, 74)
POP_START, POP_STAGGER = 0.35, 0.12
FLOAT_PERIOD = 2.6

SVG = {
    "ring": '<circle cx="50" cy="50" r="34" fill="none" stroke="{c}" stroke-width="12"/>',
    "dot": '<circle cx="50" cy="50" r="30" fill="{c}"/>',
    "plus": '<path d="M50 14v72M14 50h72" stroke="{c}" stroke-width="16" stroke-linecap="round"/>',
    "squiggle": '<path d="M8 60 Q 25 25 42 55 T 76 55 T 96 40" fill="none" stroke="{c}" stroke-width="11" stroke-linecap="round"/>',
    "tri": '<path d="M50 14 L86 80 L14 80 Z" fill="none" stroke="{c}" stroke-width="11" stroke-linejoin="round"/>',
    "spark": '<path d="M50 6 C54 38 62 46 94 50 C62 54 54 62 50 94 C46 62 38 54 6 50 C38 46 46 38 50 6 Z" fill="{c}"/>',
}
KINDS = list(SVG)


def accent(n):
    """Accent colour for global beat number n (title and closing beats keep the chapter ink)."""
    return PALETTE[n % len(PALETTE)]


def shapes(bid, beat_type, n, s, dur):
    """Return (html, js) for the floating shapes of one beat; empty for picture/window/title beats."""
    if beat_type in NO_SHAPES or dur < 3:
        return "", []
    items, js = [], []
    slots = LEFT_SLOTS if beat_type in LEFT_ONLY else SLOTS
    for j in range(N_SHAPES):
        slot = slots[(n * 3 + j * 5) % len(slots)]
        kind = KINDS[(n + j * 2) % len(KINDS)]
        color = PALETTE[(n + j + 1) % len(PALETTE)]
        size = SIZE[(n + j) % 2]
        items.append(f'<svg class="dc" viewBox="0 0 100 100" style="left:{slot[0]}%;top:{slot[1]}%;width:{size}px;height:{size}px">'
                     f'{SVG[kind].format(c=color)}</svg>')
    sel = f'R.querySelectorAll("#{bid} .dc")'
    t0 = round(s + POP_START, 2)
    reps = max(0, int(dur / FLOAT_PERIOD) - 1)
    js.append(f'tl.fromTo({sel}, {{ opacity: 0, scale: 0, rotation: -120 }}, '
              f'{{ opacity: 0.85, scale: 1, rotation: 0, duration: 0.7, ease: "back.out(2.2)", stagger: {POP_STAGGER} }}, {t0});')
    js.append(f'{sel}.forEach((d, k) => tl.fromTo(d, {{ y: 0 }}, {{ y: (k % 2 ? 1 : -1) * (14 + k * 4), duration: {FLOAT_PERIOD / 2}, '
              f'ease: "sine.inOut", yoyo: true, repeat: {reps}, immediateRender: false }}, {round(t0 + 0.8, 2)}));')
    js.append(f'{sel}.forEach((d, k) => tl.to(d, {{ rotation: (k % 2 ? 1 : -1) * 70, duration: {round(max(dur - 1.2, 1), 2)}, '
              f'ease: "none" }}, {round(t0 + 0.7, 2)}));')
    return f'<div class="deco">{"".join(items)}</div>', js


# Live diagrams sit on faint graph paper, so their lines read as a technical drawing being drafted.
DIAGRAMS = ("flow", "cycle", "timeline", "bars", "scale", "venn", "stack", "ladder")


def paper(bid, beat_type, s):
    if beat_type not in DIAGRAMS:
        return "", []
    js = [f'tl.fromTo(R.querySelector("#{bid} .paper"), {{ opacity: 0, scale: 1.04 }}, '
          f'{{ opacity: 1, scale: 1, duration: 0.8, ease: "power2.out" }}, {round(s, 2)});']
    return '<div class="paper"></div>', js
