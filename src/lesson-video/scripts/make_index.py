"""Generate index.html: background, chapter chrome, chapter hosts and the lesson audio.
Usage: python make_index.py [chapters.json] [--dest <project dir>] [--no-audio]
Chapter times come from chapters.json (built from the transcript anchors)."""
import html as htmllib
import json
import sys
from pathlib import Path

from config import TITLE

BUILD = Path(__file__).resolve().parent
ARGS = sys.argv[1:]
DEST_FLAG, NO_AUDIO_FLAG = "--dest", "--no-audio"
CLIP = Path(ARGS[ARGS.index(DEST_FLAG) + 1]).resolve() if DEST_FLAG in ARGS else BUILD.parent / "clip"
WITH_AUDIO = NO_AUDIO_FLAG not in ARGS
CFG_NAME = ARGS[0] if ARGS and not ARGS[0].startswith("--") else "chapters.json"
CFG = json.loads((BUILD / CFG_NAME).read_text(encoding="utf-8-sig"))
INK = {"torah": "#E8B84A", "math": "#8DB8E0", "both": "#C9C08A", "warm": "#D98A5A"}
GLOW_PERIOD = 6
BG_MOTES = 26
GOLDEN = 0.6180339887


def bg_motes():
    """Slow background motes; positions are index-derived so every render is identical."""
    return "".join(
        f'<i class="bgm" style="left:{(k * GOLDEN * 100) % 100:.1f}%;top:{(k * 53) % 100 + 40}%;'
        f'width:{3 + k % 5 * 2}px;height:{3 + k % 5 * 2}px"></i>' for k in range(BG_MOTES))


def host(ch):
    dur = round(ch["end"] - ch["start"], 3)
    return (f'      <div id="host-{ch["id"]}" data-composition-id="{ch["id"]}" '
            f'data-composition-src="compositions/{ch["id"]}.html" data-start="{ch["start"]}" '
            f'data-duration="{dur}" data-track-index="2" data-width="1920" data-height="1080"></div>')


def chrome(chapters, total):
    segs = "".join(
        f'<i class="seg" style="flex:{ch["end"] - ch["start"]:.1f}"></i>' for ch in chapters if ch.get("title")
    )
    labels = "\n".join(
        f'        <div id="lbl-{ch["id"]}" class="clip chlabel" data-start="{ch["start"]}" '
        f'data-duration="{round(ch["end"] - ch["start"], 3)}" data-track-index="5">{ch["title"]}</div>'
        for ch in chapters if ch.get("title")
    )
    return f"""      <div id="chrome">
        <div id="bar"><div id="segs">{segs}</div><div id="fill"></div></div>
{labels}
      </div>"""


def timeline_js(chapters, total):
    lines = [
        "      const tl = gsap.timeline({ paused: true });",
        f"      const TOTAL = {total};",
        f'      tl.fromTo("#fill", {{ scaleX: 0 }}, {{ scaleX: 1, duration: TOTAL, ease: "none" }}, 0);',
        f"      const reps = Math.max(0, Math.floor(TOTAL / {GLOW_PERIOD / 2}) - 1);",
        f'      tl.fromTo("#glow", {{ scale: 1 }}, {{ scale: 1.12, duration: {GLOW_PERIOD / 2}, ease: "sine.inOut", yoyo: true, repeat: reps }}, 0);',
        '      tl.fromTo("#ghostgrain", { x: 0, y: 0 }, { x: -60, y: -40, duration: TOTAL, ease: "none" }, 0);',
        f'      tl.fromTo("#glow2", {{ x: 0, y: 0 }}, {{ x: 900, y: 260, duration: {GLOW_PERIOD * 4}, ease: "sine.inOut", yoyo: true, repeat: Math.max(0, Math.floor(TOTAL / {GLOW_PERIOD * 4}) - 1) }}, 0);',
        f'      tl.fromTo("#glow3", {{ x: 0, y: 0, scale: 1 }}, {{ x: -700, y: -240, scale: 1.25, duration: {GLOW_PERIOD * 3}, ease: "sine.inOut", yoyo: true, repeat: Math.max(0, Math.floor(TOTAL / {GLOW_PERIOD * 3}) - 1) }}, 0);',
        '      document.querySelectorAll("#bg .bgm").forEach((m, k) => tl.fromTo(m, { y: 0 }, { y: -900 - (k % 7) * 120, duration: TOTAL, ease: "none" }, 0));',
    ]
    prev = None
    for ch in chapters:
        ink = INK[ch.get("ink", "torah")]
        if prev is None:
            lines.append(f'      tl.set("#glow", {{ backgroundColor: "{ink}" }}, 0);')
        elif ink != prev:
            lines.append(f'      tl.to("#glow", {{ backgroundColor: "{ink}", duration: 2.5, ease: "sine.inOut" }}, {ch["start"]});')
        prev = ink
    lines.append('      window.__timelines["main"] = tl;')
    return "\n".join(lines)


def audio_tag(total):
    if not WITH_AUDIO:
        return ""
    return (f'      <audio id="lesson" src="assets/audio/lesson.m4a" data-start="0" data-duration="{total}" '
            f'data-track-index="10" data-volume="1"></audio>')


def main():
    chapters, total = CFG["chapters"], CFG["total"]
    html = f"""<!doctype html>
<html lang="he">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <title>{htmllib.escape(TITLE)}</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <link rel="stylesheet" href="assets/kit.css" />
    <link rel="stylesheet" href="assets/beats.css" />
    <link rel="stylesheet" href="assets/diagrams.css" />
    <link rel="stylesheet" href="assets/device.css" />
    <link rel="stylesheet" href="assets/index.css" />
    <script src="assets/kit.js"></script>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-width="1920" data-height="1080" data-duration="{total}">
      <div id="bg"><div id="glow"></div><div id="glow2"></div><div id="glow3"></div><div id="ghostgrain"></div>{bg_motes()}</div>
{chr(10).join(host(ch) for ch in chapters)}
      <div id="vignette"></div><div id="bloom"></div>
{chrome(chapters, total)}
{audio_tag(total)}
    </div>
    <script>
{timeline_js(chapters, total)}
    </script>
  </body>
</html>
"""
    (CLIP / "index.html").write_text(html, encoding="utf-8")
    print("index.html written:", len(chapters), "chapters, total", total)


if __name__ == "__main__":
    main()
