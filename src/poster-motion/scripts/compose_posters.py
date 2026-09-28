"""HTML + GSAP for part (b): the poster shots, the gallery finale, the end card.

Each function returns (html, js) strings; build_composition.py stitches them.
Motion itself lives in templates/runtime.js (the PM.* calls) - this file only
decides *what* moves *when*, from layers.json and shots.json.

Two wrappers per moving thing, always: the outer one takes the entrance, the
inner one the loop. A drift that writes `y` on the element an entrance also
tweens would fight it whenever the playhead seeks backwards.
"""

import html

WIN_PAD = 4                  # px around each word box - keeps anti-aliasing
MINOR_WORD_AREA = 0.0012     # smaller ink groups fade in with the object
PUSH_SCALE = 1.035
STRIP_W = 18                 # rope-wave strip width, px
ROPE_AMP = 7
DRIFT_AMP = 6
EDGE_TOUCH_PX = 6
EDGE_MIN_H = 0.6
RISE_BOTTOM = 0.85
STAMP_TITLE_H = 0.2
ROPE_MAX_H = 0.12
ROPE_MIN_W = 0.8
FINALE_CARD_W = 0.40
FINALE_GAP = 26
END_CARD_W = 0.52


def esc(text):
    return html.escape(str(text), quote=True)


def _area(b):
    return b[2] * b[3]


def draft_poster(p, canvas):
    """Default archetype choice for one poster - Claude refines it in step 4."""
    w, h = canvas
    ib = p.get("ink_bbox") or [0, 0, 0, 0]
    main = [x for x in p["words"] if _area(x["bbox"]) >= MINOR_WORD_AREA * w * h]
    if ib[2] > ROPE_MIN_W * w and ib[3] < ROPE_MAX_H * h:
        text = "rope"
    elif len(main) <= 4 and ib[3] > STAMP_TITLE_H * h:
        text = "stamp"
    else:
        text = "write"
    spec = {"id": p["id"], "beats": 8, "text": text, "object": "none",
            "accents": "scatter" if p["accents"] else "none", "drift_words": []}
    if p.get("object"):
        spec["object"] = _object_kind(p["object"]["bbox"], canvas)
    return spec


def _object_kind(bbox, canvas):
    """edge: a tall object cut off by a side of the frame (an elephant's leg).
    A low one that merely reaches the side - a bag and its floor shadow - rises."""
    w, h = canvas
    x, y, bw, bh = bbox
    touches_side = x + bw >= w - EDGE_TOUCH_PX or x <= EDGE_TOUCH_PX
    if touches_side and bh > EDGE_MIN_H * h:
        return "edge"
    if y + bh >= RISE_BOTTOM * h:
        return "rise"
    return "pop"


def _edge_side(bbox, canvas):
    w, h = canvas
    x, y, bw, bh = bbox
    gaps = {"right": w - (x + bw), "left": x, "bottom": h - (y + bh), "top": y}
    return min(gaps, key=gaps.get)


def _word_html(k, i, bbox, canvas, src):
    w, h = canvas
    x, y, bw, bh = bbox
    x0, y0 = max(0, x - WIN_PAD), max(0, y - WIN_PAD)
    x1, y1 = min(w, x + bw + WIN_PAD), min(h, y + bh + WIN_PAD)
    ww, wh = x1 - x0, y1 - y0
    return (f'<div class="win" id="s{k}w{i}" data-w="{ww}" style="right:{w - x1}px;'
            f'top:{y0}px;width:{ww}px;height:{wh}px"><div class="win-in" style="'
            f'width:{ww}px;height:{wh}px;background-image:url({src});'
            f'background-position:-{x0}px -{y0}px;background-size:{w}px {h}px"></div></div>')


def _strips_html(k, p, canvas, src):
    w, h = canvas
    x, _, bw, _ = p["ink_bbox"]
    out = []
    for i, sx in enumerate(range(max(0, x - WIN_PAD), min(w, x + bw + WIN_PAD), STRIP_W)):
        out.append(f'<div class="strip s{k}r" style="left:{sx}px;width:{STRIP_W}px;'
                   f'background-image:url({src});background-position:-{sx}px 0;'
                   f'background-size:{w}px {h}px"></div>')
    return out


def _object_html(k, p, spec, canvas, base):
    if spec["object"] == "none" or not p.get("object"):
        return ""
    img = f'<div class="obj-in" id="s{k}oi"><img src="{base}/object.png" alt=""></div>'
    if spec["object"] == "peek":
        x, y, bw, bh = p["object"]["bbox"]
        return (f'<div class="peek" style="height:{y + bh}px"><div class="layer" '
                f'id="s{k}o" style="height:{canvas[1]}px">{img}</div></div>')
    return f'<div class="layer" id="s{k}o">{img}</div>'


def shot_html(k, p, spec, canvas, start, dur):
    base = f"assets/layers/{p['id']}"
    parts = [f'<img class="layer" src="{base}/plate.png" alt="">',
             _object_html(k, p, spec, canvas, base)]
    if spec["text"] == "rope":
        parts += _strips_html(k, p, canvas, f"{base}/ink.png")
    else:
        parts += [_word_html(k, i, wd["bbox"], canvas, f"{base}/ink.png")
                  for i, wd in enumerate(p["words"])]
    for i, a in enumerate(p["accents"]):
        x, y, bw, bh = a["bbox"]
        parts.append(f'<div class="acc s{k}a" style="left:{x}px;top:{y}px;width:{bw}px;'
                     f'height:{bh}px"><img class="s{k}ai" src="{base}/{a["file"]}" alt=""></div>')
    body = "\n        ".join(x for x in parts if x)
    return (f'    <div id="s{k}" class="shot clip" data-start="{start:.4f}" '
            f'data-duration="{dur:.4f}" data-track-index="1">\n'
            f'      <div class="cam" id="s{k}cam" data-layout-allow-overflow>\n        {body}\n      </div>\n    </div>')


def _split_words(k, p, canvas):
    w, h = canvas
    main, minor = [], []
    for i, wd in enumerate(p["words"]):
        (main if _area(wd["bbox"]) >= MINOR_WORD_AREA * w * h else minor).append(f"#s{k}w{i}")
    return main, minor


def _text_js(k, p, spec, t, period, dur, canvas):
    """JS for the ink layer; returns (js lines, time the text is done)."""
    beat_in = t + spec.get("text_at", 1) * period
    if spec["text"] == "rope":
        return [f"PM.rope(tl, '.s{k}r', {beat_in:.4f}, {2 * period:.4f}, "
                f"{t + dur - beat_in:.4f}, {ROPE_AMP});"], beat_in + 2 * period
    main, minor = _split_words(k, p, canvas)
    js = []
    if minor:
        js.append(f"PM.fade(tl, '{','.join(minor)}', {t + 0.1:.4f}, 0.4);")
    sel = ",".join(main)
    if not sel:
        return js, beat_in
    if spec["text"] == "stamp":
        js.append(f"PM.stamp(tl, '{sel}', {beat_in:.4f}, {period:.4f}, '#s{k}cam');")
        return js, beat_in + len(main) * period
    if spec["text"] == "fade":
        js.append(f"PM.fade(tl, '{sel}', {beat_in:.4f}, {period:.4f});")
        return js, beat_in + period
    room = max(period, dur - (beat_in - t) - 2 * period)
    each = min(period * 0.9, room / max(1, len(main)) / 1.15)
    js.append(f"PM.write(tl, '{sel}', {beat_in:.4f}, {each:.4f}, {each * 0.15:.4f});")
    return js, beat_in + len(main) * each * 1.15


def _object_js(k, p, spec, t, period, dur, canvas):
    kind = spec["object"]
    if kind == "none" or not p.get("object"):
        return []
    w, h = canvas
    bbox = p["object"]["bbox"]
    at = t + spec.get("object_at", 0) * period + 0.05
    d = f"{{W:{w},H:{h},h:{bbox[3]},side:'{_edge_side(bbox, canvas)}'}}"
    js = [f"PM.enter(tl, '#s{k}o', '{kind}', {at:.4f}, {period * 1.2:.4f}, {d});"]
    if spec.get("float"):
        start = at + period * 1.2
        js.append(f"PM.drift(tl, '#s{k}oi', {start:.4f}, {t + dur - start:.4f}, "
                  f"{DRIFT_AMP}, {k + 1});")
    return js


def _accent_js(k, p, spec, t, period, dur, text_done):
    if spec["accents"] == "none" or not p["accents"]:
        return []
    at = t + spec.get("accents_at", 2) * period
    each = period / 2
    settle = at + each * (len(p["accents"]) + 1)
    return [f"PM.scatter(tl, '.s{k}a', {at:.4f}, {each:.4f}, {k + 7});",
            f"PM.drift(tl, '.s{k}ai', {settle:.4f}, {max(0.5, t + dur - settle):.4f}, "
            f"{DRIFT_AMP}, {k + 3});"]


def shot_js(k, p, spec, canvas, t, dur, period):
    js = [f"// {p['id']} - text:{spec['text']} object:{spec['object']} "
          f"accents:{spec['accents']}",
          f"PM.punch(tl, '#s{k}', {t:.4f});",
          f"PM.push(tl, '#s{k}cam', {t:.4f}, {dur:.4f}, {PUSH_SCALE});"]
    js += _object_js(k, p, spec, t, period, dur, canvas)
    text, done = _text_js(k, p, spec, t, period, dur, canvas)
    js += text
    js += _accent_js(k, p, spec, t, period, dur, done)
    words = [f"#s{k}w{i}" for i in spec.get("drift_words", []) if i < len(p["words"])]
    if words and spec["text"] != "rope":
        js.append(f"PM.drift(tl, '{','.join(w + ' .win-in' for w in words)}', "
                  f"{done:.4f}, {max(0.5, t + dur - done):.4f}, {DRIFT_AMP}, {k + 5});")
    return "\n      ".join(js)


def finale(posters, canvas, t, dur, period, paper):
    """Every poster on one line, sliding past right to left, bumping on the beat."""
    w, h = canvas
    cw = round(w * FINALE_CARD_W)
    ch = round(cw * h / w)
    top = (h - ch) // 2 - 20
    n = len(posters)
    cards = "".join(
        f'<div class="card" data-layout-allow-overflow style="left:{(n - 1 - i) * (cw + FINALE_GAP)}px;top:{top}px;'
        f'width:{cw}px;height:{ch}px"><img src="assets/layers/{p["id"]}/poster.png" alt="">'
        f'</div>' for i, p in enumerate(posters))
    x0 = w / 2 - cw / 2 - (n - 1) * (cw + FINALE_GAP)
    x1 = w / 2 - cw / 2
    html_ = (f'    <div id="fin" class="shot clip" data-start="{t:.4f}" data-duration="{dur:.4f}"'
             f' data-track-index="1" style="background:rgb({paper[0]},{paper[1]},{paper[2]})">\n'
             f'      <div class="rope" style="top:{top + ch + 34}px"></div>\n'
             f'      <div class="row" id="finrow">{cards}</div>\n    </div>')
    js = [f"tl.fromTo('#finrow', {{x: {x0:.1f}}}, {{x: {x1:.1f}, duration: {dur:.4f}, "
          f"ease: 'power1.inOut'}}, {t:.4f});"]
    beats = int(dur / period)
    for b in range(1, beats):
        at = t + b * period
        js.append(f"tl.to('#finrow', {{y: -7, duration: 0.07, ease: 'power2.out'}}, {at:.4f})"
                  f".to('#finrow', {{y: 0, duration: 0.3, ease: 'power2.in'}}, {at + 0.07:.4f});")
    return html_, "\n      ".join(js)


def end_card(first_id, canvas, t, dur, title, tools, credit):
    w, h = canvas
    cw = round(w * END_CARD_W)
    ch = round(cw * h / w)
    top = round(h * 0.16)
    left = (w - cw) // 2
    sw = round(cw * 1.5)
    html_ = f"""    <div id="end" class="shot clip" data-start="{t:.4f}" data-duration="{dur:.4f}" data-track-index="1">
      <img class="kraft" src="assets/tex/kraft.png" alt="">
      <img id="endsplash" src="assets/tex/splash.png" alt="" style="position:absolute;left:{(w - sw) // 2}px;top:{top + ch // 2 - round(sw * 0.4)}px;width:{sw}px">
      <div class="card" id="endcard" style="left:{left}px;top:{top}px;width:{cw}px;height:{ch}px"><img src="assets/layers/{first_id}/poster.png" alt=""></div>
      <div class="end-title" id="endtitle" style="top:{top + ch + 34}px">{esc(title)}</div>
      <div class="tools" id="endtools" style="top:{top + ch + 110}px">{tools}</div>
      <div class="credit" id="endcredit" style="top:{top + ch + 138}px">{esc(credit)}</div>
    </div>"""
    js = [f"tl.fromTo('#endsplash', {{scale: 0.2, opacity: 0}}, {{scale: 1, opacity: 1, "
          f"duration: 0.45, ease: 'back.out(1.8)'}}, {t + 0.05:.4f});",
          f"tl.fromTo('#endcard', {{scale: 0.86, rotation: 4, opacity: 0}}, {{scale: 1, "
          f"rotation: -2, opacity: 1, duration: 0.6, ease: 'power3.out'}}, {t:.4f});",
          f"PM.fade(tl, '#endtitle, #endtools, #endcredit', {t + 0.5:.4f}, 0.5);"]
    return html_, "\n      ".join(js)
