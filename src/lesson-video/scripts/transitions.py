# -*- coding: utf-8 -*-
"""Entrance transitions, rotated per beat family so consecutive beats never enter the same way.
K.beat already fades .in in/out; a transition adds motion on .in or an overlay sibling of .in."""

ROTATION = {
    "picture": ["zoom", "iris", "push", "flash"],
    "diagram": ["push", "blinds", "slide"],
    "text": ["slide", "zoom", "blinds", "push", "fade"],
    "title": ["wipe"],
}
FAMILY = {
    "story": "picture", "imgtext": "picture", "split": "picture",
    "flow": "diagram", "cycle": "diagram", "timeline": "diagram", "bars": "diagram", "scale": "diagram",
    "venn": "diagram", "stack": "diagram", "ladder": "diagram", "compare": "diagram",
    "title": "title", "closing": "title",
}
BLINDS = 6


def pick(beat_type, index, override=None):
    if override:
        return override
    options = ROTATION[FAMILY.get(beat_type, "text")]
    return options[index % len(options)]


def _in(bid):
    return f'R.querySelector("#{bid} > .in")'


def transition(bid, kind, s):
    """Return (overlay_html, js_lines) for one beat entrance at local time s."""
    if kind == "zoom":
        return "", [f'tl.fromTo({_in(bid)}, {{ scale: 1.12 }}, {{ scale: 1, duration: 0.9, ease: "power3.out" }}, {s});']
    if kind == "push":
        return "", [f'tl.fromTo({_in(bid)}, {{ x: -220 }}, {{ x: 0, duration: 0.7, ease: "power3.out" }}, {s});']
    if kind == "slide":
        return "", [f'tl.fromTo({_in(bid)}, {{ y: 90 }}, {{ y: 0, duration: 0.7, ease: "power3.out" }}, {s});']
    if kind == "iris":
        return "", [f'tl.fromTo({_in(bid)}, {{ clipPath: "circle(0% at 50% 50%)" }}, '
                    f'{{ clipPath: "circle(80% at 50% 50%)", duration: 1.0, ease: "power2.inOut" }}, {s});']
    if kind == "flash":
        return ('<div class="tr-flash"></div>',
                [f'tl.fromTo(R.querySelector("#{bid} .tr-flash"), {{ opacity: 0.7 }}, {{ opacity: 0, duration: 0.6, ease: "power2.out" }}, {s});'])
    if kind == "blinds":
        strips = "".join(f'<i style="left:{k * 100 / BLINDS:.3f}%"></i>' for k in range(BLINDS))
        return (f'<div class="tr-blinds">{strips}</div>',
                [f'tl.fromTo(R.querySelectorAll("#{bid} .tr-blinds i"), {{ scaleX: 1 }}, '
                 f'{{ scaleX: 0, duration: 0.55, ease: "power2.inOut", stagger: 0.06 }}, {s});'])
    return "", []
