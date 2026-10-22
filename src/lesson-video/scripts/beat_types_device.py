# -*- coding: utf-8 -*-
"""Device beats: phone (a mobile-app conversation) and link (a card with a scannable QR code).
Every renderer returns (html, js_lines); times are chapter-local seconds."""
import io

import sfx
from beat_util import breathe, esc, q, times

PHONE_W, PHONE_H, PHONE_TOP, PHONE_LEFT = 470, 740, 110, 300   # bottom edge stays above the captions
STEP_GAP = 1.4
ALLOW_DELAY = 1.0        # the Allow button pops this long after its message
QR_PX = 360
LIVE_PULSE = 0.6


def _msg(st):
    k, text = st["k"], esc(st.get("text", ""))
    if k == "you":
        return f'<div class="pm pyou"><span>{text}</span></div>'
    if k == "done":
        return f'<div class="pm pdone"><i>✓</i><span>{text}</span></div>'
    if k == "ask":
        return (f'<div class="pm pask"><b>{text}</b><span>{esc(st.get("detail", ""))}</span>'
                f'<em class="pallow">Allow</em></div>')
    return f'<div class="pm psay"><i class="spark"></i><span>{text}</span></div>'


def _phone_html(bid, b):
    title = esc(b.get("title", "השיחה במחשב"))
    msgs = "".join(_msg(st) for st in b.get("steps", []))
    return (f'<div class="in" style="padding:0"><div class="phone" id="{bid}-ph" style="left:{PHONE_LEFT}px;top:{PHONE_TOP}px;'
            f'width:{PHONE_W}px;height:{PHONE_H}px"><i class="notch"></i>'
            f'<div class="phd"><span class="pt">Code</span><span class="ps"><i class="pc">🖥️</i>{title}<i class="live"></i></span></div>'
            f'<div class="pmsgs">{msgs}</div><div class="pin">כתבו הודעה…</div></div>'
            f'<div class="pside"><h2 class="h2 gold pht">{title}</h2><div class="body psub">{esc(b.get("sub", ""))}</div></div></div>')


def phone(bid, b, s, dur, rel, i):
    steps = b.get("steps", [])
    js = [f'tl.fromTo(R.querySelector("#{bid}-ph"), {{ opacity: 0, y: 80, rotationY: -28, transformPerspective: 1600 }}, '
          f'{{ opacity: 1, y: 0, rotationY: 0, duration: 0.9, ease: "power3.out" }}, {s});',
          f'tl.fromTo(R.querySelector("#{bid} .live"), {{ scale: 0.7 }}, {{ scale: 1.3, duration: {LIVE_PULSE}, yoyo: true, '
          f'repeat: {max(1, int(dur / LIVE_PULSE) - 1)}, ease: "sine.inOut", immediateRender: false }}, {s + 0.5});']
    n_ask = 0
    for k, t in enumerate(times(rel, len(steps), s + 0.9, STEP_GAP)):
        js.append(f'K.in(tl, R, [{q(bid, ".pm", k)}], {t}, {{ y: 24, dur: 0.45 }});')
        sfx.ev("pop", t)
        if steps[k]["k"] == "ask":
            allow = round(t + ALLOW_DELAY, 2)
            js.append(f'K.pop(tl, R, [{q(bid, ".pallow", n_ask)}], {allow}, {{ overshoot: 3 }});')
            sfx.ev("click", allow)
            n_ask += 1
    js.append(f'K.in(tl, R, "#{bid} .pht", {s + 0.5}, {{ x: 50, y: 0 }});')
    if b.get("sub"):
        js.append(f'K.in(tl, R, "#{bid} .psub", {s + 1.2}, {{ y: 20 }});')
    return _phone_html(bid, b), js + breathe(bid, ".phone", s + 1.5, dur - 2, 1.012)


def _qr_svg(url):
    import qrcode                      # imported here: only LINK beats need the package (pip install qrcode)
    import qrcode.image.svg
    buf = io.BytesIO()
    qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, border=1).save(buf)
    svg = buf.getvalue().decode("utf-8")
    return svg[svg.index("<svg"):].replace("<svg ", f'<svg class="qrsvg" width="{QR_PX}" height="{QR_PX}" ', 1)


def link(bid, b, s, dur, rel, i):
    sfx.ev("chime", s + 0.6)
    h = (f'<div class="in center"><div class="lcard" id="{bid}-lc"><div class="lqr">{_qr_svg(b["url"])}</div>'
         f'<div class="ltxt"><div class="lic">{esc(b.get("icon", "🔗"))}</div><div class="lh">{esc(b["title"])}</div>'
         f'<div class="lurl">{esc(b["url"].split("://")[-1])}</div><div class="lsub">{esc(b.get("sub", ""))}</div></div></div></div>')
    js = [f'tl.fromTo(R.querySelector("#{bid}-lc"), {{ opacity: 0, y: 60, rotation: -2 }}, {{ opacity: 1, y: 0, rotation: 0, duration: 0.7, ease: "back.out(1.6)" }}, {s});',
          f'K.pop(tl, R, "#{bid} .lic", {s + 0.35}, {{ overshoot: 3 }});',
          f'K.in(tl, R, "#{bid} .lh", {s + 0.5}, {{ x: 40, y: 0 }});',
          f'tl.fromTo(R.querySelector("#{bid} .lqr"), {{ opacity: 0, scale: 0.6, rotation: 8 }}, {{ opacity: 1, scale: 1, rotation: 0, duration: 0.7, ease: "back.out(2)" }}, {s + 0.6});',
          f'K.in(tl, R, "#{bid} .lurl", {s + 0.9}, {{ y: 20 }});',
          f'K.in(tl, R, "#{bid} .lsub", {rel[0] if rel else s + 1.3}, {{ y: 20 }});']
    return h, js + breathe(bid, ".lqr", s + 1.5, dur - 2, 1.03)


RENDER = {"phone": phone, "link": link}
