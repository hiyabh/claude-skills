# -*- coding: utf-8 -*-
"""Picture and layout beats: story (+ camera shots), imgtext, split, compare, kinetic."""
from beat_util import KEN_PRESETS, breathe, esc, particles, q, times, word_reveal

AUTO_SHOT_MIN = 11       # a story beat longer than this gets automatic camera moves
AUTO_SHOT_EVERY = 6
AUTO_FOCUS = [(34, 40, 1.35), (68, 56, 1.4), (50, 34, 1.25), (50, 50, 1.0)]
SHOT_MOVE = 1.4
KIN_SIZES = [150, 98, 124, 86, 112]
KIN_TILT = [-3, 2, -1.5, 3, -2]


def _shift(f, z):
    """xPercent/yPercent that brings focus point f (0-100) toward centre without exposing an edge."""
    limit = (z - 1) * 50
    return round(max(-limit, min(limit, (50 - f) * z)), 2)


def _shot_plan(b, s, dur, shot_times):
    """Explicit shots at their anchors, plus automatic moves filling any long stretch between them."""
    plan = [(t, *sh.get("focus", (50, 50)), sh.get("zoom", 1.35)) for t, sh in zip(shot_times, b.get("shots") or [])]
    if dur < AUTO_SHOT_MIN or b.get("shots") == []:
        return plan
    t, k = s + AUTO_SHOT_EVERY, 0
    while t < s + dur - 3:
        if all(abs(t - p[0]) > AUTO_SHOT_EVERY / 2 for p in plan):
            plan.append((round(t, 2), *AUTO_FOCUS[k % len(AUTO_FOCUS)]))
            k += 1
        t += AUTO_SHOT_EVERY
    return sorted(plan)


def _picture(bid, img, s, dur, kb, shot_plan):
    f, t, x, y = KEN_PRESETS[kb % len(KEN_PRESETS)]
    html = (f'<div class="illus"><div class="kb" id="{bid}-kb"><img id="{bid}-img" src="assets/img/{img}.png" alt="" /></div>'
            f'<div class="shade"></div></div>')
    js = [f'K.ken(tl, R, "#{bid}-kb", {s}, {dur}, {{ from: {f}, to: {t}, x: {x}, y: {y} }});']
    for at, fx, fy, z in shot_plan:
        js.append(f'tl.to(R.querySelector("#{bid}-img"), {{ scale: {z}, xPercent: {_shift(fx, z)}, '
                  f'yPercent: {_shift(fy, z)}, duration: {SHOT_MOVE}, ease: "power2.inOut" }}, {at});')
    return html, js


def story(bid, b, s, dur, rel, i):
    pic, js = _picture(bid, b["img"], s, dur, b.get("kb", i), _shot_plan(b, s, dur, b.get("_shots", [])))
    motes, mjs = particles(bid, s, dur)
    cap = ""
    if b.get("cap"):
        cap = f'<div class="scap"><div class="ct">{esc(b["cap"])}</div><div class="cs">{esc(b.get("sub"))}</div></div>'
        t = rel[0] if rel else s + 0.6
        js += [f'K.in(tl, R, "#{bid} .scap", {t}, {{ x: 60, y: 0 }});', word_reveal(bid, ".ct", t + 0.1, b["cap"], 1.2),
               f'K.in(tl, R, "#{bid} .cs", {t + 0.9}, {{ y: 14 }});']
    return f'<div class="in" style="padding:0">{pic}{motes}{cap}</div>', js + mjs


def imgtext(bid, b, s, dur, rel, i):
    lines = "".join(f'<div class="body ln">{esc(x)}</div>' for x in b.get("lines", []))
    h = (f'<div class="in"><div class="half"><div class="kb" id="{bid}-kb"><img src="assets/img/{b["img"]}.png" alt="" /></div></div>'
         f'<div class="side"><h2 class="h2 gold">{esc(b["title"])}</h2>{lines}</div></div>')
    js = [f'tl.fromTo(R.querySelector("#{bid} .half"), {{ clipPath: "inset(0% 0% 0% 100%)" }}, {{ clipPath: "inset(0% 0% 0% 0%)", duration: 1.0, ease: "power3.inOut" }}, {s});',
          f'K.ken(tl, R, "#{bid}-kb", {s}, {dur}, {{ from: 1.0, to: 1.14, x: 20 }});',
          f'K.in(tl, R, "#{bid} .side h2", {s + 0.4}, {{ x: -40, y: 0 }});']
    for k, t in enumerate(times(rel, len(b.get("lines", [])), s + 1.0, 0.6)):
        js.append(f'K.in(tl, R, {q(bid, ".ln", k)}, {t}, {{ y: 24 }});')
    return h, js


def split(bid, b, s, dur, rel, i):
    h = (f'<div class="in"><div class="half"><div class="kb" id="{bid}-kb"><img src="assets/img/{b["img"]}.png" alt="" /></div></div>'
         f'<div class="side"><div class="src"><div class="q sm">{esc(b["q"])}</div><div class="cite">{esc(b.get("cite"))}</div></div></div></div>')
    js = [f'tl.fromTo(R.querySelector("#{bid} .half"), {{ clipPath: "inset(0% 100% 0% 0%)" }}, {{ clipPath: "inset(0% 0% 0% 0%)", duration: 1.0, ease: "power3.inOut" }}, {s});',
          f'K.ken(tl, R, "#{bid}-kb", {s}, {dur}, {{ from: 1.12, to: 1.0, x: -20 }});',
          f'K.in(tl, R, "#{bid} .src", {s + 0.5}, {{ x: -50, y: 0 }});']
    if "*" in b["q"]:
        js += [f'K.mark(tl, R, "#{bid} .hl", {t});' for t in times(rel, 1, s + 1.4)]
    else:
        js.append(word_reveal(bid, ".q", s + 0.7, b["q"]))
    return h, js + [f'K.in(tl, R, "#{bid} .cite", {s + 1.3}, {{ y: 14 }});']


def compare(bid, b, s, dur, rel, i):
    def col(side, c):
        ls = "".join(f'<div class="body ln">{esc(x)}</div>' for x in c.get("lines", []))
        return f'<div class="col c{side}"><h2 class="h2">{esc(c["h"])}</h2>{ls}</div>'
    h = (f'<div class="in"><div class="cols">{col("r", b["r"])}<div class="vs">{esc(b.get("mid", ""))}</div>'
         f'{col("l", b["l"])}</div></div>')
    t_left = rel[0] if rel else round(s + max(1.5, dur * 0.4), 2)
    js = [f'K.in(tl, R, "#{bid} .cr", {s + 0.15}, {{ x: 60, y: 0 }});',
          f'K.in(tl, R, "#{bid} .cr .ln", {s + 0.6}, {{ y: 20, stagger: 0.35 }});',
          f'K.pop(tl, R, "#{bid} .vs", {round(t_left - 0.2, 2)});',
          f'K.in(tl, R, "#{bid} .cl", {t_left}, {{ x: -60, y: 0 }});',
          f'K.in(tl, R, "#{bid} .cl .ln", {t_left + 0.45}, {{ y: 20, stagger: 0.35 }});',
          f'K.dim(tl, R, "#{bid} .cr", {t_left}, {{ to: 0.55 }});',
          f'K.back(tl, R, "#{bid} .cr", {round(t_left + 2.5, 2)});']
    return h, js + breathe(bid, ".vs", t_left + 1, dur - (t_left - s) - 1.5, 1.08)


def kinetic(bid, b, s, dur, rel, i):
    """Key words slam in one by one, timed to the moment each is spoken."""
    words = b["words"]
    spans = "".join(f'<span class="kn{" gold" if k % 2 == 0 else ""}" style="font-size:{KIN_SIZES[k % len(KIN_SIZES)]}px">'
                    f'{esc(w)}</span>' for k, w in enumerate(words))
    h = f'<div class="in center"><div class="kin">{spans}</div><div class="body dim sub">{esc(b.get("sub"))}</div></div>'
    js = []
    reveal = times(rel, len(words), s + 0.2, 0.55)
    for k, t in enumerate(reveal):
        js.append(f'tl.fromTo({q(bid, ".kn", k)}, {{ opacity: 0, scale: 2.6, rotation: 0 }}, '
                  f'{{ opacity: 1, scale: 1, rotation: {KIN_TILT[k % len(KIN_TILT)]}, duration: 0.45, ease: "expo.out" }}, {t});')
    js.append(f'K.in(tl, R, "#{bid} .sub", {reveal[-1] + 0.6}, {{ y: 24 }});')
    return h, js + breathe(bid, ".kin", reveal[-1] + 0.6, dur - (reveal[-1] - s) - 1.2, 1.03)


RENDER = {"story": story, "imgtext": imgtext, "split": split, "compare": compare, "kinetic": kinetic}
