# -*- coding: utf-8 -*-
"""Text beats: title, question, say, source, verse, keyword, number, list, closing.
Every renderer returns (html, js_lines). Text may mark highlight words with *word*."""
from beat_util import HL_RE, breathe, esc, q, times, word_reveal

RING_R = 190


def _chapter_map(b):
    n, cur = b.get("_chcount", 0), b.get("_chnum", 0)
    if not n:
        return ""
    dots = "".join(f'<i class="cm{" on" if k == cur else (" done" if k < cur else "")}"></i>' for k in range(n))
    return f'<div class="chmap">{dots}</div>'


def title(bid, b, s, dur, rel, i):
    num = b.get("_chnum")
    badge = f'<div class="chnum num" id="{bid}-n">{num}</div>' if num else ""
    h = (f'<div class="in center"><div class="wipe"></div>{badge}'
         f'<div class="eyebrow gold">{esc(b.get("eyebrow"))}</div>'
         f'<h1 class="h1 tt">{esc(b["title"])}</h1><div class="rule"></div>'
         f'<div class="body dim sub">{esc(b.get("sub"))}</div>{_chapter_map(b)}</div>')
    js = [f'tl.fromTo(R.querySelector("#{bid} .wipe"), {{ scaleX: 1 }}, {{ scaleX: 0, duration: 0.9, ease: "power3.inOut" }}, {s});',
          f'K.in(tl, R, "#{bid} .eyebrow", {s + 0.3}, {{ y: 20 }});',
          f'K.words(tl, R, "#{bid} .tt", {s + 0.5}, {{ stagger: 0.09 }});',
          f'tl.fromTo(R.querySelector("#{bid} .rule"), {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.8, ease: "power2.out" }}, {s + 1.0});',
          f'K.in(tl, R, "#{bid} .sub", {s + 1.4}, {{ y: 24 }});']
    if num:
        js += [f'K.pop(tl, R, "#{bid}-n", {s + 0.2}, {{ overshoot: 2.2 }});',
               f'K.count(tl, R, "#{bid}-n", 0, {num}, {s + 0.2}, 0.8);']
    if _chapter_map(b):
        js.append(f'K.pop(tl, R, {q(bid, ".cm")}, {s + 1.2}, {{ stagger: 0.04 }});')
    return h, js + breathe(bid, ".tt", s + 2, dur - 2.5)


def closing(bid, b, s, dur, rel, i):
    h, js = title(bid, {**b, "_chcount": 0, "_chnum": None}, s, dur, rel, i)
    return h.replace('class="in center"', 'class="in center closing"'), js


def question(bid, b, s, dur, rel, i):
    h = (f'<div class="in center"><div class="qmark">?</div><h1 class="h1 qq">{esc(b["text"])}</h1>'
         f'<div class="body dim sub">{esc(b.get("sub"))}</div></div>')
    js = [f'K.pop(tl, R, "#{bid} .qq", {s + 0.1}, {{ overshoot: 2.4, dur: 0.6 }});',
          f'tl.fromTo(R.querySelector("#{bid} .qq"), {{ x: -12 }}, {{ x: 12, duration: 0.07, repeat: 5, yoyo: true, ease: "none", immediateRender: false }}, {s + 0.7});',
          f'tl.to(R.querySelector("#{bid} .qq"), {{ x: 0, duration: 0.1 }}, {s + 1.15});',
          f'tl.fromTo(R.querySelector("#{bid} .qmark"), {{ opacity: 0, rotation: -25, scale: 0.6 }}, {{ opacity: 0.12, rotation: 8, scale: 1, duration: 1.2, ease: "back.out(1.6)" }}, {s});',
          f'tl.to(R.querySelector("#{bid} .qmark"), {{ rotation: -6, duration: {max(dur - 1.5, 0.5):.2f}, ease: "sine.inOut" }}, {s + 1.2});',
          f'K.in(tl, R, "#{bid} .sub", {rel[0] if rel else s + 1.3}, {{ y: 30 }});']
    return h, js + breathe(bid, ".qq", s + 1.4, dur - 1.9, 1.03)


def _card(bid, b, s, dur, rel, cls):
    q_cls = "q sm" if b.get("size") == "sm" else "q"
    h = (f'<div class="in center"><div class="src {cls}"><div class="{q_cls}">{esc(b["q"])}</div>'
         f'<div class="cite">{esc(b.get("cite"))}</div></div></div>')
    js = [f'K.in(tl, R, "#{bid} .src", {s + 0.1}, {{ y: 50, dur: 0.7 }});']
    n_hl = len(HL_RE.findall(b["q"]))
    if n_hl:
        js.append(f'K.in(tl, R, "#{bid} .q", {s + 0.3}, {{ y: 16 }});')
        js += [f'K.mark(tl, R, [{q(bid, ".hl", k)}], {t});' for k, t in enumerate(times(rel, n_hl, s + 1.2, 0.8))]
    else:
        js.append(word_reveal(bid, ".q", s + 0.3, b["q"]))
    js.append(f'K.in(tl, R, "#{bid} .cite", {s + 0.9}, {{ y: 16 }});')
    return h, js + breathe(bid, ".src", s + 1.5, dur - 2, 1.012)


def source(bid, b, s, dur, rel, i):
    return _card(bid, b, s, dur, rel, "")


def verse(bid, b, s, dur, rel, i):
    return _card(bid, b, s, dur, rel, "verse")


def say(bid, b, s, dur, rel, i):
    h = (f'<div class="in center"><div class="qt">&#8221;</div><h1 class="h1 say">{esc(b["text"])}</h1>'
         f'<div class="body dim sub">{esc(b.get("sub"))}</div></div>')
    js = [f'tl.fromTo(R.querySelector("#{bid} .qt"), {{ opacity: 0, y: -40 }}, {{ opacity: 0.35, y: 0, duration: 0.6, ease: "power2.out" }}, {s});']
    if HL_RE.search(b["text"]):
        js.append(f'K.in(tl, R, "#{bid} .say", {s + 0.15}, {{ y: 40, ease: "expo.out", dur: 0.8 }});')
        js += [f'K.mark(tl, R, "#{bid} .hl", {t});' for t in times(rel, 1, s + 1.1)]
    else:
        js.append(f'K.words(tl, R, "#{bid} .say", {s + 0.15}, {{ stagger: 0.1, y: 30 }});')
    js.append(f'K.in(tl, R, "#{bid} .sub", {rel[1] if len(rel) > 1 else s + 1.6}, {{ y: 24 }});')
    return h, js + breathe(bid, ".say", s + 2, dur - 2.5)


def keyword(bid, b, s, dur, rel, i):
    chips = "".join(f'<span class="kw">{esc(w)}</span>' for w in b["words"])
    big = f'<h2 class="h2 gold big">{esc(b["big"])}</h2>' if b.get("big") else ""
    h = f'<div class="in center">{big}<div class="chips">{chips}</div><div class="body dim sub">{esc(b.get("sub"))}</div></div>'
    js = [f'K.in(tl, R, "#{bid} .big", {s + 0.1}, {{ y: 40 }});'] if big else []
    reveal = times(rel, len(b["words"]), s + (0.7 if big else 0.2))
    js += [f'K.pop(tl, R, {q(bid, ".kw", k)}, {t});' for k, t in enumerate(reveal)]
    js.append(f'K.in(tl, R, "#{bid} .sub", {reveal[-1] + 0.6 if reveal else s + 1}, {{ y: 24 }});')
    return h, js + breathe(bid, ".chips", (reveal[-1] if reveal else s) + 0.8, dur - 2.5, 1.025)


def number(bid, b, s, dur, rel, i):
    ring = (f'<svg class="ring" viewBox="0 0 440 440"><circle class="rg" cx="220" cy="220" r="{RING_R}" /></svg>')
    h = (f'<div class="in center"><div class="numwrap">{ring}<div class="num bignum" id="{bid}-n">{b.get("from", 0)}</div></div>'
         f'<div class="h3 nlabel">{esc(b["label"])}</div><div class="body dim sub">{esc(b.get("sub"))}</div></div>')
    js = [f'K.pop(tl, R, "#{bid}-n", {s + 0.1});',
          f'K.draw(tl, R, "#{bid} .rg", {s + 0.1}, 1.7);',
          f'K.count(tl, R, "#{bid}-n", {b.get("from", 0)}, {b["n"]}, {s + 0.2}, 1.6, {{ suffix: "{b.get("suffix", "")}" }});',
          f'K.in(tl, R, "#{bid} .nlabel", {s + 0.7}, {{ y: 30 }});',
          f'K.in(tl, R, "#{bid} .sub", {rel[0] if rel else s + 1.5}, {{ y: 24 }});']
    return h, js + breathe(bid, ".numwrap", s + 2, dur - 2.5, 1.04)


def listing(bid, b, s, dur, rel, i):
    items = "".join(f'<div class="li"><i class="dot"></i><span>{esc(x)}</span></div>' for x in b["items"])
    h = f'<div class="in"><h2 class="h2 gold lt">{esc(b["title"])}</h2><div class="items">{items}</div></div>'
    js = [f'K.in(tl, R, "#{bid} .lt", {s + 0.1}, {{ x: 50, y: 0 }});']
    for k, t in enumerate(times(rel, len(b["items"]), s + 0.8, 0.7)):
        js.append(f'K.pop(tl, R, {q(bid, ".dot", k)}, {t}, {{ overshoot: 3 }});')
        js.append(f'K.in(tl, R, {q(bid, ".li span", k)}, {t + 0.08}, {{ x: 50, y: 0 }});')
    return h, js


RENDER = {"title": title, "closing": closing, "question": question, "source": source, "verse": verse,
          "say": say, "keyword": keyword, "number": number, "list": listing}
