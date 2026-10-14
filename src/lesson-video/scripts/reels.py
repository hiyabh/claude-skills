# -*- coding: utf-8 -*-
"""Optional 9:16 reels cut from the lesson, reusing the resolved beats.
video.json "reels": [{"name": "kebab-name", "start": sec, "end": sec, "hook": "כותרת הרילס"}]  (45-90s each)
Usage: python reels.py <name>   -> build/reels/<name>/ project; then render + mux with render.sh/mux.sh --reel <name>.
Picture beats become full-height Ken Burns shots; text beats become big animated text cards."""
import html
import json
import shutil
import subprocess
import sys

import beats
from anchor import stream
from config import AUDIO, BUILD, CFG, CLIP, TITLE

W, H = 1080, 1920
WORDS_PER_LINE = 4
PICTURE = {"story", "imgtext", "split"}
TEXT_KEYS = ("title", "text", "big", "q", "label")
END_CARD = 2.5


def beats_in(t0, t1):
    words, out = stream(), []
    for ch in beats.CHAPTERS["chapters"]:
        spec = beats.load_spec(ch["id"])
        if not spec or ch["end"] <= t0 or ch["start"] >= t1:
            continue
        resolved = beats.resolve(words, spec["beats"], ch)
        ends = [b["g"] for b in resolved[1:]] + [ch["end"]]
        out += [(b, max(b["g"], t0), min(e, t1)) for b, e in zip(resolved, ends) if e > t0 and b["g"] < t1]
    return out


def beat_text(b):
    for key in TEXT_KEYS:
        if b.get(key):
            return b[key].replace("*", "")
    return " ".join(b.get("words") or b.get("items") or b.get("nodes") or [])


def layer(k, b, s, dur):
    if b["t"] in PICTURE:
        sec = (f'<section id="r{k}" class="clip shot" data-start="{s}" data-duration="{dur}" data-track-index="{1 + k % 2}">'
               f'<div class="in"><img id="r{k}i" src="assets/img/{b["img"]}.png" alt="" /></div></section>')
        js = [f'K.beat(tl, R, "r{k}", {s}, {dur});',
              f'tl.fromTo("#r{k}i", {{ scale: 1.25, xPercent: {-8 if k % 2 else 8} }}, {{ scale: 1.05, xPercent: 0, duration: {dur}, ease: "none" }}, {s});']
        return sec, js, b["img"]
    sec = (f'<section id="r{k}" class="clip card" data-start="{s}" data-duration="{dur}" data-track-index="{1 + k % 2}">'
           f'<div class="in"><div class="ct">{html.escape(beat_text(b))}</div></div></section>')
    js = [f'K.beat(tl, R, "r{k}", {s}, {dur});', f'K.pop(tl, R, "#r{k} .ct", {s + 0.1}, {{ overshoot: 2 }});',
          f'K.breathe(tl, R, "#r{k} .ct", {s + 0.8}, {max(dur - 1.2, 0.5):.2f}, {{ scale: 1.04 }});']
    return sec, js, None


def caption_lines(t0, t1):
    caps = json.loads((BUILD / "captions.json").read_text(encoding="utf-8"))
    words = [w for c in caps for w in c["words"] if t0 <= w["s"] < t1]
    return [words[i:i + WORDS_PER_LINE] for i in range(0, len(words), WORDS_PER_LINE)]


def captions(t0, t1):
    rows, js = [], []
    lines = caption_lines(t0, t1)
    for k, line in enumerate(lines):
        nxt = lines[k + 1][0]["s"] - t0 - 0.13 if k + 1 < len(lines) else t1 - t0
        s, e = round(line[0]["s"] - t0, 2), round(min(line[-1]["e"] - t0 + 0.3, nxt), 2)
        rows.append(f'<div class="cap" id="c{k}">' + " ".join(f'<span>{html.escape(w["w"])}</span>' for w in line) + "</div>")
        js.append(f'tl.fromTo("#c{k}", {{ opacity: 0, scale: 0.8 }}, {{ opacity: 1, scale: 1, duration: 0.18, ease: "back.out(2)" }}, {s});')
        js.append(f'tl.to("#c{k}", {{ opacity: 0, duration: 0.12 }}, {e});')
        js += [f'tl.to("#c{k} span:nth-child({j + 1})", {{ color: "#E8B84A", duration: 0.08 }}, {round(w["s"] - t0, 2)});'
               for j, w in enumerate(line)]
    return "".join(rows), js


def page(reel, layers, js, caps_html, total):
    hook = html.escape(reel["hook"])
    return (BUILD / "reel_template.html").read_text(encoding="utf-8") \
        .replace("__LAYERS__", "\n".join(layers)).replace("__CAPS__", caps_html).replace("__HOOK__", hook) \
        .replace("__TITLE__", html.escape(TITLE)).replace("__TOTAL__", str(total)) \
        .replace("__END__", str(round(total - END_CARD, 2))).replace("__JS__", "\n      ".join(js))


def main(name):
    reel = next(r for r in CFG["reels"] if r["name"] == name)
    t0, t1 = float(reel["start"]), float(reel["end"])
    proj = BUILD / "reels" / name
    shutil.copytree(CLIP / "assets" / "fonts", proj / "assets" / "fonts", dirs_exist_ok=True)
    (proj / "assets" / "img").mkdir(parents=True, exist_ok=True)
    shutil.copy2(CLIP / "assets" / "kit.js", proj / "assets")
    shutil.copy2(CLIP / "package.json", proj)
    layers, js = [], []
    for k, (b, a, e) in enumerate(beats_in(t0, t1)):
        sec, lines, img = layer(k, b, round(a - t0, 2), round(e - a, 2))
        layers.append(sec)
        js += lines
        if img:
            shutil.copy2(CLIP / "assets" / "img" / f"{img}.png", proj / "assets" / "img")
    caps_html, cap_js = captions(t0, t1)
    (proj / "index.html").write_text(page(reel, layers, js + cap_js, caps_html, round(t1 - t0, 2)), encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t0), "-to", str(t1), "-i", str(AUDIO),
                    "-c:a", "aac", "-b:a", "160k", str(proj / "reel.m4a")], check=True)
    print(f"reel {name}: {t1 - t0:.0f}s, {len(layers)} layers -> {proj}")


if __name__ == "__main__":
    main(sys.argv[1])
