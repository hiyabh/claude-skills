"""HTML + GSAP for part (a): the optional "how this was made" segment.

Kraft-paper stage, a torn-paper caption strip at the bottom with one word in
red, a top rail (file chip, "צעד N / M" tag, progress segments). Every number
it shows is real - layer count, BPM, frame count, the GSAP it prints - taken
from the run that made the film. A making-of that shows invented numbers is a
fake making-of.

Captions mark the red word with *asterisks*. Placeholders filled from the run:
{N} posters, {L} layers, {BPM}, {F} frames, {FPS}.
"""

import re

from compose_posters import esc
from pm_common import FPS
from pm_textures import SEED

TORN_POINTS = 46
TORN_JAG = 9
THUMB_W = 0.25
SPLIT_W = 0.34
WAVE_BARS = 80
CODE_LINES = 6

DEFAULT_SCENES = [
    {"type": "prompt", "beats": 4, "say": "הכול התחיל ב*פרומפט* אחד:"},
    {"type": "posters", "beats": 4, "say": "*{N}* פוסטרים. בלי מצלמה."},
    {"type": "step", "beats": 2, "title": "הפרדה", "chip": "split_layers.py"},
    {"type": "split", "beats": 5, "say": "כל פוסטר *מתפרק* לשכבות"},
    {"type": "step", "beats": 2, "title": "שכבות", "chip": "assets/layers/"},
    {"type": "layers", "beats": 4, "say": "*{L}* שכבות, וכל אחת זזה לבד"},
    {"type": "step", "beats": 2, "title": "קוד", "chip": "index.html"},
    {"type": "code", "beats": 5, "say": "*GSAP* מחייה כל שכבה"},
    {"type": "step", "beats": 2, "title": "קצב", "chip": "beat_grid.py"},
    {"type": "rhythm", "beats": 5, "say": "*{BPM}* פעימות לדקה - כל חיתוך על ביט"},
    {"type": "step", "beats": 2, "title": "ליטוש", "chip": "layers_sheet.png"},
    {"type": "polish", "beats": 4, "say": "בדיקה *פיקסל* מול פיקסל"},
    {"type": "result", "beats": 3, "say": "*והתוצאה:*"},
]
DEFAULT_PROMPT = ("take these posters and make an amazing MOTION GRAPHIC video from them, "
                  "matching the ideas in an amazing style")


def fill(text, facts):
    for key, val in facts.items():
        text = text.replace("{" + key + "}", str(val))
    return text


def rich(text):
    """*word* -> red highlight; digits kept LTR inside Hebrew."""
    out = esc(text)
    out = re.sub(r"\*([^*]+)\*", r'<span class="hl">\1</span>', out)
    return re.sub(r"(\d[\d.,]*)", r"<bdi>\1</bdi>", out)


def _torn_svg(k):
    """A white strip whose top edge is torn - seeded, so identical every render."""
    s = (SEED * 7919 + k * 104729) & 0xFFFFFFFF
    pts = []
    for i in range(TORN_POINTS + 1):
        s = (s * 1664525 + 1013904223) & 0xFFFFFFFF
        pts.append(f"{i * 1000 / TORN_POINTS:.1f},{4 + (s / 2 ** 32) * TORN_JAG:.1f}")
    path = "M0,100 L" + " L".join(pts) + " L1000,100 Z"
    return (f'<svg viewBox="0 0 1000 100" preserveAspectRatio="none"><path d="{path}" '
            f'fill="#f7f4ee"/><path d="{path}" fill="none" stroke="#d9d2c4" stroke-width="1"/></svg>')


def caption(k, say, t, dur):
    """One inline span inside the flex strip: as bare flex items, the text runs
    and the red span lose the spaces between them and reorder."""
    html_ = (f'<div class="torn" id="m{k}cap" data-layout-allow-overflow>{_torn_svg(k)}'
             f'<div class="say"><span>{rich(say)}</span></div></div>')
    return html_, f"PM.caption(tl, '#m{k}cap', {t + 0.05:.4f}, {dur - 0.05:.4f});"


def _rail(k, chip, step_no, steps):
    segs = "".join(f'<div class="seg{" on" if i < step_no else ""}"></div>' for i in range(steps))
    return (f'<div class="rail" id="m{k}rail"><div class="chip">~/{esc(chip)}</div>'
            f'<div class="tag">צעד <bdi>{step_no} / {steps}</bdi></div>'
            f'<div class="segs">{segs}</div></div>')


def scene_prompt(k, ctx, t, dur, sc):
    w, h = ctx["canvas"]
    text = sc.get("prompt", ctx["prompt"])
    body = (f'<div class="term" id="m{k}t" style="left:{w * 0.07:.0f}px;top:{h * 0.2:.0f}px;'
            f'width:{w * 0.86:.0f}px"><div class="term-bar"><i style="left:10px;background:#e0645a">'
            f'</i><i style="left:26px;background:#e8b64c"></i><i style="left:42px;'
            f'background:#69b35b"></i><b>Claude Code</b></div><div class="term-body">&gt; '
            f'<span id="m{k}typed"></span><span class="caret"></span></div></div>')
    js = [f"tl.fromTo('#m{k}t', {{y: 30, opacity: 0}}, {{y: 0, opacity: 1, duration: 0.4, "
          f"ease: 'power3.out'}}, {t:.4f});",
          f"PM.type(tl, '#m{k}typed', {text!r}, {t + 0.4:.4f}, {dur * 0.7:.4f});"]
    return body, js


def scene_posters(k, ctx, t, dur, sc):
    w, h = ctx["canvas"]
    ids = ctx["ids"]
    cw, cols = round(w * THUMB_W), 3
    ch = round(cw * h / w)
    rows = (len(ids) + cols - 1) // cols
    top0 = max(70, (h - 110 - rows * (ch + 18)) // 2)
    cards, js = [], []
    step = min(dur * 0.6 / max(1, len(ids)), 0.3)
    for i, pid in enumerate(ids):
        r, c = divmod(i, cols)
        in_row = min(cols, len(ids) - r * cols)
        left = (w - in_row * cw - (in_row - 1) * 18) // 2 + (in_row - 1 - c) * (cw + 18)
        cards.append(f'<div class="card m{k}c" style="left:{left}px;top:{top0 + r * (ch + 18)}px;'
                     f'width:{cw}px;height:{ch}px"><img src="assets/layers/{pid}/poster.png" alt=""></div>')
    js.append(f"tl.fromTo('.m{k}c', {{scale: 0.3, opacity: 0, rotation: -8}}, {{scale: 1, "
              f"opacity: 1, rotation: 0, duration: 0.35, ease: 'back.out(1.8)', stagger: {step:.3f}}}, "
              f"{t + 0.1:.4f});")
    return "".join(cards), js


def scene_step(k, ctx, t, dur, sc):
    num = f"{sc['step_no']:02d}"
    body = (f'{_rail(k, sc.get("chip", ""), sc["step_no"], ctx["steps"])}'
            f'<div class="num" id="m{k}n"><img src="assets/tex/stamp.png" alt=""><span>{num}</span></div>'
            f'<div class="step-title" id="m{k}s">{esc(sc["title"])}</div>'
            f'<div class="step-rule" id="m{k}u"></div>')
    js = [f"tl.fromTo('#m{k}rail', {{opacity: 0}}, {{opacity: 1, duration: 0.2}}, {t:.4f});",
          f"tl.fromTo('#m{k}n', {{scale: 1.8, opacity: 0, rotation: -12}}, {{scale: 1, opacity: 1, "
          f"rotation: 0, duration: 0.22, ease: 'power4.in'}}, {t + 0.05:.4f});",
          f"PM.shake(tl, '#m{k}n', {t + 0.27:.4f}, 8);",
          f"tl.fromTo('#m{k}s', {{y: 30, opacity: 0}}, {{y: 0, opacity: 1, duration: 0.35, "
          f"ease: 'power3.out'}}, {t + 0.3:.4f});",
          f"tl.fromTo('#m{k}u', {{scaleX: 0}}, {{scaleX: 1, duration: 0.4, ease: 'power2.out'}}, "
          f"{t + 0.45:.4f});"]
    return body, js


def _layer_card(k, cls, src, left, top, cw, ch, label):
    lbl = f'<div class="lbl" style="left:8px;bottom:8px">{label}</div>' if label else ""
    return (f'<div class="card {cls}" id="{cls}" style="left:{left}px;top:{top}px;width:{cw}px;'
            f'height:{ch}px"><img src="{src}" alt="">{lbl}</div>')


def scene_split(k, ctx, t, dur, sc):
    w, h = ctx["canvas"]
    base = f"assets/layers/{ctx['demo']}"
    cw = round(w * SPLIT_W)
    ch = round(cw * h / w)
    left, top = (w - cw) // 2, round(h * 0.2)
    names = [("plate", "plate.png", "<b>LaMa</b> · inpaint"),
             ("ink", "ink.png", "<b>OpenCV</b> · ink key"),
             ("object", "object.png", "<b>BiRefNet</b> · cutout")]
    body = [_layer_card(k, f"m{k}{n}", f"{base}/{f}", left, top, cw, ch, lab) for n, f, lab in names]
    body.append(_layer_card(k, f"m{k}src", f"{base}/poster.png", left, top, cw, ch, ""))
    spread = {"plate": (0, 70, 0), "ink": (cw * 0.62, -20, 6), "object": (-cw * 0.62, -20, -6)}
    js = [f"tl.fromTo('.m{k}src', {{scale: 0.8, opacity: 0}}, {{scale: 1, opacity: 1, "
          f"duration: 0.35, ease: 'power3.out'}}, {t:.4f});",
          f"tl.to('.m{k}src', {{opacity: 0, duration: 0.3}}, {t + dur * 0.3:.4f});"]
    for n, (dx, dy, rot) in spread.items():
        js.append(f"tl.fromTo('.m{k}{n}', {{x: 0, y: 0, rotation: 0}}, {{x: {dx:.0f}, y: {dy}, "
                  f"rotation: {rot}, duration: 0.6, ease: 'back.out(1.4)'}}, {t + dur * 0.32:.4f});")
    # Labels wait for the fan: stacked, all three would print over each other.
    js.append(f"tl.fromTo('#m{k} .lbl', {{opacity: 0}}, {{opacity: 1, duration: 0.25, "
              f"stagger: 0.12}}, {t + dur * 0.32 + 0.6:.4f});")
    return "".join(body), js


def scene_layers(k, ctx, t, dur, sc):
    w, h = ctx["canvas"]
    base = f"assets/layers/{ctx['demo']}"
    cw = round(w * 0.3)
    ch = round(cw * h / w)
    body = [f'<div class="big" id="m{k}big" style="top:{h * 0.1:.0f}px">0</div>']
    js = [f"PM.count(tl, '#m{k}big', {ctx['facts']['L']}, {t:.4f}, {dur * 0.6:.4f});"]
    for i, f in enumerate(["plate.png", "object.png", "ink.png"]):
        cls = f"m{k}l{i}"
        body.append(_layer_card(k, cls, f"{base}/{f}", (w - cw) // 2, round(h * 0.42), cw, ch, ""))
        js.append(f"tl.fromTo('.{cls}', {{y: 0, x: 0}}, {{y: {-40 + i * 40}, x: {(i - 1) * 90}, "
                  f"rotation: {(i - 1) * 5}, duration: 0.7, ease: 'power3.out'}}, {t + 0.3 + i * 0.12:.4f});")
    return "".join(body), js


def scene_code(k, ctx, t, dur, sc):
    w, h = ctx["canvas"]
    code = "\n".join(ctx["code"][:CODE_LINES])
    body = (f'<div class="term" id="m{k}t" style="left:{w * 0.05:.0f}px;top:{h * 0.12:.0f}px;'
            f'width:{w * 0.9:.0f}px"><div class="term-bar"><b>index.html - GSAP</b></div>'
            f'<div class="term-body" style="font-size:12px" id="m{k}typed"></div></div>'
            f'<div class="big" id="m{k}f" style="top:{h * 0.58:.0f}px">0<small>frames @ {FPS}fps</small></div>')
    js = [f"tl.fromTo('#m{k}t', {{y: 30, opacity: 0}}, {{y: 0, opacity: 1, duration: 0.35}}, {t:.4f});",
          f"PM.type(tl, '#m{k}typed', {code!r}, {t + 0.3:.4f}, {dur * 0.55:.4f});",
          f"PM.count(tl, '#m{k}f', {ctx['facts']['F']}, {t + dur * 0.45:.4f}, {dur * 0.4:.4f});"]
    return body, js


def _bars(env, cls):
    step = max(1, len(env) // WAVE_BARS)
    vals = [max(env[i:i + step]) for i in range(0, len(env), step)][:WAVE_BARS]
    return "".join(f'<i class="{cls}" style="height:{8 + v * 150:.0f}px"></i>' for v in vals)


def scene_rhythm(k, ctx, t, dur, sc):
    w, h = ctx["canvas"]
    env = ctx["envelope"]
    top = round(h * 0.42)
    body = (f'<div class="big" id="m{k}b" style="top:{h * 0.13:.0f}px">0<small>BPM</small></div>'
            f'<div class="wave" style="top:{top}px;height:170px">{_bars(env, "")}</div>'
            f'<div id="m{k}clip" style="position:absolute;left:30px;top:{top}px;height:170px;'
            f'width:0;overflow:hidden"><div class="wave" data-layout-allow-overflow style="left:0;width:{w - 60}px;right:auto;'
            f'height:170px">{_bars(env, "on")}</div></div>')
    js = [f"PM.count(tl, '#m{k}b', {round(ctx['facts']['BPM'])}, {t:.4f}, {dur * 0.4:.4f});",
          f"tl.fromTo('#m{k}clip', {{width: 0}}, {{width: {w - 60}, duration: {dur * 0.9:.4f}, "
          f"ease: 'none'}}, {t + 0.1:.4f});"]
    return body, js


def scene_polish(k, ctx, t, dur, sc):
    w, h = ctx["canvas"]
    base = f"assets/layers/{ctx['demo']}"
    cw = round(w * 0.4)
    ch = round(cw * h / w)
    top = round(h * 0.2)
    body = (_layer_card(k, f"m{k}a", f"{base}/poster.png", round(w * 0.06), top, cw, ch,
                        "<b>poster</b>") +
            _layer_card(k, f"m{k}b", f"{base}/plate.png", w - cw - round(w * 0.06), top, cw, ch,
                        "<b>plate</b> · ✓ clean"))
    js = [f"tl.fromTo('.m{k}a, .m{k}b', {{y: 40, opacity: 0}}, {{y: 0, opacity: 1, duration: 0.4, "
          f"ease: 'power3.out', stagger: 0.2}}, {t:.4f});"]
    return body, js


def scene_result(k, ctx, t, dur, sc):
    """The first poster's clean paper grows to fill the frame - part (b)
    opens on that exact plate, so the hand-over is seamless."""
    w, h = ctx["canvas"]
    body = (f'<div class="card" id="m{k}r" style="left:0;top:0;width:{w}px;height:{h}px">'
            f'<img src="assets/layers/{ctx["ids"][0]}/plate.png" alt=""></div>')
    js = [f"tl.fromTo('#m{k}r', {{scale: 0.42, rotation: -3}}, {{scale: 1, rotation: 0, "
          f"duration: {dur * 0.55:.4f}, ease: 'power3.inOut'}}, {t + dur * 0.45:.4f});"]
    return body, js


SCENES = {"prompt": scene_prompt, "posters": scene_posters, "step": scene_step,
          "split": scene_split, "layers": scene_layers, "code": scene_code,
          "rhythm": scene_rhythm, "polish": scene_polish, "result": scene_result}


def build(ctx, scenes, t0, period):
    """All making-of scenes from t0. Returns (html, js, end time)."""
    steps = sum(1 for s in scenes if s["type"] == "step")
    ctx["steps"] = steps
    t, step_no, chip, html_parts, js_parts = t0, 0, "", [], []
    for k, sc in enumerate(scenes):
        dur = sc["beats"] * period
        if sc["type"] == "step":
            step_no += 1
            chip = sc.get("chip", "")
            sc = dict(sc, step_no=step_no)
        body, js = SCENES[sc["type"]](k, ctx, t, dur, sc)
        if step_no and sc["type"] not in ("step", "result"):
            body = _rail(k, chip, step_no, steps) + body
            js.append(f"tl.set('#m{k}rail', {{opacity: 1}}, {t:.4f});")
        if sc.get("say"):
            cap_html, cap_js = caption(k, fill(sc["say"], ctx["facts"]), t, dur)
            body += cap_html
            js.append(cap_js)
        html_parts.append(f'    <div id="m{k}" class="shot clip" data-start="{t:.4f}" '
                          f'data-duration="{dur:.4f}" data-track-index="2">{body}</div>')
        js_parts.append(f"// making-of {k}: {sc['type']}\n      " + "\n      ".join(js))
        t += dur
    kraft = (f'    <div id="kraftbg" class="clip" data-start="{t0:.4f}" data-duration="{t - t0:.4f}" '
             f'data-track-index="0"><img class="kraft" src="assets/tex/kraft.png" alt=""></div>')
    return kraft + "\n" + "\n".join(html_parts), "\n      ".join(js_parts), t
