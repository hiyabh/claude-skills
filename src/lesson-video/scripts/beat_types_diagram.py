# -*- coding: utf-8 -*-
"""Diagram beats drawn live: flow, cycle, timeline, bars, scale, venn, stack, ladder.
Geometry is in frame pixels (1920x1080); RTL - sequences start on the right."""
import math

from beat_util import breathe, esc, q, times

W, H = 1920, 1080
MID_Y = 560
DRAW = 0.4                # arrow draw time, finishing just as its target node appears
NODE_H = 130


def _title(b):
    return f'<h2 class="h2 gold dtitle">{esc(b.get("title"))}</h2>' if b.get("title") else ""


def _node(cls, label, cx, cy, w, h=NODE_H):
    return (f'<div class="{cls}" style="left:{cx - w / 2:.0f}px;top:{cy - h / 2:.0f}px;width:{w:.0f}px;height:{h}px">'
            f'<span>{esc(label)}</span></div>')


def _head(x, y, deg):
    """Arrowhead polygon at (x, y) pointing along deg (0 = right, 180 = left)."""
    return (f'<polygon class="ah" points="0,-13 22,0 0,13" '
            f'transform="translate({x:.1f},{y:.1f}) rotate({deg:.1f})" />')


def _svg(bid, body):
    return f'<svg class="dsvg" viewBox="0 0 {W} {H}">{body}</svg>'


def _intro(bid, b, s):
    return [f'K.in(tl, R, "#{bid} .dtitle", {s + 0.1}, {{ x: 50, y: 0 }});'] if b.get("title") else []


def _reveal_nodes(bid, sel, reveal, arrows=True):
    js = []
    for k, t in enumerate(reveal):
        if arrows and k:
            js.append(f'K.draw(tl, R, [{q(bid, ".ar", k - 1)}], {round(max(t - DRAW, reveal[k - 1] + 0.1), 2)}, {DRAW});')
            js.append(f'tl.fromTo({q(bid, ".ah", k - 1)}, {{ opacity: 0 }}, {{ opacity: 1, duration: 0.1 }}, {round(t - 0.05, 2)});')
        js.append(f'K.pop(tl, R, {q(bid, sel, k)}, {t}, {{ overshoot: 2 }});')
    return js


def flow(bid, b, s, dur, rel, i):
    n = len(b["nodes"])
    step = (W - 520) / max(n - 1, 1)
    w = min(330, step - 90)
    xs = [W - 260 - k * step for k in range(n)]
    nodes = "".join(_node("dnode", lab, x, MID_Y, w) for lab, x in zip(b["nodes"], xs))
    paths = "".join(f'<path class="ar" d="M{xs[k] - w / 2 - 12:.0f},{MID_Y} L{xs[k + 1] + w / 2 + 26:.0f},{MID_Y}" />'
                    + _head(xs[k + 1] + w / 2 + 26, MID_Y, 180) for k in range(n - 1))
    reveal = times(rel, n, s + 0.6, 1.0)
    h = f'<div class="in" style="padding:0">{_title(b)}{_svg(bid, paths)}{nodes}</div>'
    return h, _intro(bid, b, s) + _reveal_nodes(bid, ".dnode", reveal) + breathe(bid, ".dnode", reveal[-1] + 0.6, dur - (reveal[-1] - s) - 1, 1.03)


def cycle(bid, b, s, dur, rel, i):
    n, r, cx, cy, gap = len(b["nodes"]), 290, W / 2, MID_Y + 15, 24
    ang = [-90 + k * 360 / n for k in range(n)]
    pt = lambda a: (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
    nodes = "".join(_node("dnode cyc", lab, *pt(a), 290, 110) for lab, a in zip(b["nodes"], ang))
    arcs = ""
    for k in range(n):
        a0, a1 = ang[k] + gap, ang[k] + 360 / n - gap
        (x0, y0), (x1, y1) = pt(a0), pt(a1)
        arcs += f'<path class="ar" d="M{x0:.1f},{y0:.1f} A{r},{r} 0 0 1 {x1:.1f},{y1:.1f}" />' + _head(x1, y1, a1 + 90)
    center = f'<div class="dcenter">{esc(b.get("center", ""))}</div>' if b.get("center") else ""
    reveal = times(rel, n, s + 0.6, 1.0)
    js = _intro(bid, b, s) + _reveal_nodes(bid, ".dnode", reveal)
    close = reveal[-1] + 0.6
    js += [f'K.draw(tl, R, [{q(bid, ".ar", n - 1)}], {close}, {DRAW});',
           f'tl.fromTo({q(bid, ".ah", n - 1)}, {{ opacity: 0 }}, {{ opacity: 1, duration: 0.1 }}, {close + DRAW});']
    if center:
        js.append(f'K.pop(tl, R, "#{bid} .dcenter", {close + 0.3});')
    h = f'<div class="in" style="padding:0">{_title(b)}{_svg(bid, arcs)}{nodes}{center}</div>'
    return h, js + breathe(bid, ".dcenter", close + 1, dur - (close - s) - 1.5, 1.05)


def timeline(bid, b, s, dur, rel, i):
    items, dates = b["items"], b.get("dates", [""] * len(b["items"]))
    n, x0, x1 = len(items), W - 220, 220
    xs = [x0 - 90 - k * (x0 - x1 - 180) / max(n - 1, 1) for k in range(n)]
    line = f'<path class="tline" d="M{x0},{MID_Y} L{x1},{MID_Y}" />'
    dots = "".join(f'<circle class="tdot" cx="{x:.0f}" cy="{MID_Y}" r="16" />' for x in xs)
    labels = "".join(
        f'<div class="tlab {"up" if k % 2 == 0 else "dn"}" style="left:{x - 160:.0f}px"><b>{esc(d)}</b><span>{esc(it)}</span></div>'
        for k, (x, it, d) in enumerate(zip(xs, items, dates)))
    reveal = times(rel, n, s + 1.2, 0.9)
    js = _intro(bid, b, s) + [f'K.draw(tl, R, "#{bid} .tline", {s + 0.3}, 1.2);']
    for k, t in enumerate(reveal):
        js += [f'K.pop(tl, R, {q(bid, ".tdot", k)}, {t}, {{ overshoot: 3 }});',
               f'K.in(tl, R, {q(bid, ".tlab", k)}, {t + 0.1}, {{ y: {-24 if k % 2 else 24} }});']
    return f'<div class="in" style="padding:0">{_title(b)}{_svg(bid, line + dots)}{labels}</div>', js


def bars(bid, b, s, dur, rel, i):
    vals = b["bars"]
    top = max(v["value"] for v in vals) or 1
    n = len(vals)
    step = (W - 500) / n
    cols = "".join(
        f'<div class="bar" style="left:{W - 250 - (k + 1) * step + step * 0.18:.0f}px;width:{step * 0.64:.0f}px;'
        f'height:{480 * v["value"] / top:.0f}px"><b class="num" id="{bid}-v{k}">0</b><i class="bfill"></i>'
        f'<span class="blab">{esc(v["label"])}</span></div>' for k, v in enumerate(vals))
    reveal = times(rel, n, s + 0.6, 0.7)
    js = _intro(bid, b, s)
    for k, (t, v) in enumerate(zip(reveal, vals)):
        js += [f'tl.fromTo({q(bid, ".bfill", k)}, {{ scaleY: 0 }}, {{ scaleY: 1, duration: 0.9, ease: "power3.out" }}, {t});',
               f'K.count(tl, R, "#{bid}-v{k}", 0, {v["value"]}, {t}, 0.9, {{ suffix: "{v.get("suffix", "")}" }});',
               f'K.in(tl, R, {q(bid, ".blab", k)}, {t}, {{ y: 16 }});']
    return f'<div class="in" style="padding:0">{_title(b)}<div class="bars">{cols}</div></div>', js


def scale(bid, b, s, dur, rel, i):
    tilt = {"r": 11, "l": -11}.get(b.get("tilt", "0"), 0)
    drop = round(470 * math.sin(math.radians(abs(tilt))), 1)
    h = (f'<div class="in" style="padding:0">{_title(b)}<div class="sc"><div class="post"></div><div class="beam"></div>'
         f'<div class="pan pr"><span>{esc(b["r"])}</span></div><div class="pan pl"><span>{esc(b["l"])}</span></div></div></div>')
    t_r, t_l, t_tilt = times(rel, 3, s + 0.8, 1.2)
    sign = 1 if tilt > 0 else -1
    js = _intro(bid, b, s) + [f'K.in(tl, R, "#{bid} .post, #{bid} .beam", {s + 0.3}, {{ y: 40 }});',
                              f'K.pop(tl, R, "#{bid} .pr", {t_r});', f'K.pop(tl, R, "#{bid} .pl", {t_l});']
    if tilt:
        js += [f'tl.to(R.querySelector("#{bid} .beam"), {{ rotation: {tilt}, duration: 1.2, ease: "elastic.out(1, 0.5)" }}, {t_tilt});',
               f'tl.to(R.querySelector("#{bid} .pr"), {{ y: {sign * drop}, duration: 1.2, ease: "elastic.out(1, 0.5)" }}, {t_tilt});',
               f'tl.to(R.querySelector("#{bid} .pl"), {{ y: {-sign * drop}, duration: 1.2, ease: "elastic.out(1, 0.5)" }}, {t_tilt});']
    return h, js


def venn(bid, b, s, dur, rel, i):
    h = (f'<div class="in" style="padding:0">{_title(b)}<div class="venn"><div class="vc vr"><span>{esc(b["r"])}</span></div>'
         f'<div class="vc vl"><span>{esc(b["l"])}</span></div><div class="vmid">{esc(b.get("mid", ""))}</div></div></div>')
    t_r, t_l, t_m = times(rel, 3, s + 0.5, 1.0)
    js = _intro(bid, b, s) + [
        f'tl.fromTo(R.querySelector("#{bid} .vr"), {{ opacity: 0, x: 320 }}, {{ opacity: 1, x: 0, duration: 0.9, ease: "power3.out" }}, {t_r});',
        f'tl.fromTo(R.querySelector("#{bid} .vl"), {{ opacity: 0, x: -320 }}, {{ opacity: 1, x: 0, duration: 0.9, ease: "power3.out" }}, {t_l});',
        f'K.pop(tl, R, "#{bid} .vmid", {t_m}, {{ overshoot: 2.6 }});']
    return h, js + breathe(bid, ".vmid", t_m + 0.8, dur - (t_m - s) - 1.2, 1.08)


def stack(bid, b, s, dur, rel, i):
    n = len(b["items"])
    blocks = "".join(f'<div class="blk" style="bottom:{220 + k * 118}px;width:{900 - k * 70}px;margin-left:{-(900 - k * 70) / 2:.0f}px">'
                     f'<span>{esc(it)}</span></div>' for k, it in enumerate(b["items"]))
    reveal = times(rel, n, s + 0.6, 0.8)
    js = _intro(bid, b, s) + [
        f'tl.fromTo({q(bid, ".blk", k)}, {{ opacity: 0, y: -520 }}, {{ opacity: 1, y: 0, duration: 0.8, ease: "bounce.out" }}, {t});'
        for k, t in enumerate(reveal)]
    return f'<div class="in" style="padding:0">{_title(b)}<div class="stack">{blocks}</div></div>', js


def ladder(bid, b, s, dur, rel, i):
    n, base, rise, wstep = len(b["steps"]), 900, 120, 330
    xs = [W - 330 - k * wstep for k in range(n)]
    steps = "".join(f'<div class="step" style="left:{x - wstep / 2 + 8:.0f}px;width:{wstep - 16}px;top:{base - (k + 1) * rise}px;'
                    f'height:{(k + 1) * rise}px"><span>{esc(lab)}</span></div>' for k, (x, lab) in enumerate(zip(xs, b["steps"])))
    marker = f'<div class="lmark" style="left:{xs[0] - 22:.0f}px;top:{base - rise - 60}px"></div>'
    reveal = times(rel, n, s + 0.6, 1.0)
    js = _intro(bid, b, s)
    for k, t in enumerate(reveal):
        js.append(f'tl.fromTo({q(bid, ".step", k)}, {{ opacity: 0, scaleY: 0 }}, {{ opacity: 1, scaleY: 1, duration: 0.6, ease: "back.out(1.6)" }}, {t});')
        js.append(f'tl.to(R.querySelector("#{bid} .lmark"), {{ x: {xs[k] - xs[0]:.0f}, y: {-k * rise}, duration: 0.5, ease: "power2.out" }}, {t + 0.3});')
    js.insert(0, f'K.pop(tl, R, "#{bid} .lmark", {reveal[0] + 0.3});')
    return f'<div class="in" style="padding:0">{_title(b)}{steps}{marker}</div>', js


RENDER = {"flow": flow, "cycle": cycle, "timeline": timeline, "bars": bars, "scale": scale,
          "venn": venn, "stack": stack, "ladder": ladder}
