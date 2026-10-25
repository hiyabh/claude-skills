#!/usr/bin/env python3
"""Build a HyperFrames project that plays talking-head footage with the planned effects.

Inputs come from the earlier steps of the talking-head-fx workflow:
    footage.mp4        the speaker clip (its audio is the video's soundtrack)
    fx_plan.json       effects timeline (plan_fx.py, then reviewed/edited by Claude)
    face.json          face track (face_track.py)
    words.json         optional word timings [[text,start,end],...] (transcribe.py) -> captions
    subjects/          optional subject_<i>.webm cut-outs for matte effects (matte_segments.py)

Usage:
    python build_project.py --footage talk.mp4 --plan fx_plan.json --face face.json \
        [--words words.json] [--subjects subjects/] --out my-video
Then: cd my-video && npx hyperframes check && npx hyperframes snapshot --at ...
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # cues.py sits next to this script
from cues import MATTE_TYPES

SKILL = Path(__file__).resolve().parent.parent
RUNTIME = SKILL / "assets" / "runtime"
RUNTIME_SCRIPTS = ["thfx-core.js", "fx-camera.js", "fx-frames.js", "fx-matte.js", "fx-overlay.js", "thfx-text.js"]
GSAP_URL = "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"
MATTE_REQUIRED = MATTE_TYPES - {"growth_chart", "frame_escape"}  # these two degrade gracefully
DEFAULT_CANVAS = (1080, 1920)
FACE_TARGET_Y = 0.36  # where the face should sit vertically when the crop allows it


def probe(path):
    """(width, height, duration) of a video via ffprobe."""
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    s = d["streams"][0]
    return int(s["width"]), int(s["height"]), float(d["format"]["duration"])


def cover_fit(canvas, src, face):
    """object-position (0..1) that puts the average face near the centre-top of the crop."""
    W, H = canvas
    sw, sh = src
    scale = max(W / sw, H / sh)
    dw, dh = sw * scale, sh * scale
    samples = face.get("samples") or [[0, 0.5, 0.38, 0.2]]
    cx = sum(s[1] for s in samples) / len(samples)
    cy = sum(s[2] for s in samples) / len(samples)

    def solve(span_c, span_d, target, c):
        if abs(span_c - span_d) < 1:
            return 0.5
        return min(1.0, max(0.0, (target - c * span_d) / (span_c - span_d)))
    return {"x": round(solve(W, dw, W / 2, cx), 4), "y": round(solve(H, dh, H * FACE_TARGET_Y, cy), 4)}


def init_project(out):
    """Scaffold with the official CLI (package.json, hyperframes.json) unless already a project."""
    if (out / "hyperframes.json").exists():
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = f'npx hyperframes init "{out.name}" --non-interactive --example blank'
    r = subprocess.run(cmd, shell=True, cwd=out.parent, capture_output=True, text=True)
    if r.returncode != 0 or not (out / "hyperframes.json").exists():
        sys.exit(f"ERROR: 'npx hyperframes init' failed - is the hyperframes CLI installed?\n{r.stderr[-800:]}")


def link_or_copy(src, dst):
    """The lens needs its own file: two <video>s with one src/start/duration get discovered twice."""
    if dst.exists():
        dst.unlink()
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def copy_assets(out, footage, subjects_dir, effects):
    """Copy footage, runtime and per-effect subject cut-outs. Returns {effect_index: rel_path}."""
    assets = out / "assets"
    assets.mkdir(exist_ok=True)
    main = assets / ("footage" + footage.suffix.lower())
    shutil.copy2(footage, main)
    link_or_copy(main, assets / ("footage_lens" + footage.suffix.lower()))
    shutil.copytree(RUNTIME, out / "thfx", dirs_exist_ok=True)
    found = {}
    for i, e in enumerate(effects):
        if e["type"] not in MATTE_TYPES or not subjects_dir:
            continue
        src = Path(subjects_dir) / f"subject_{i}.webm"
        if src.exists():
            shutil.copy2(src, assets / src.name)
            found[i] = f"assets/{src.name}"
        elif e["type"] in MATTE_REQUIRED:
            print(f"WARNING: effect #{i} ({e['type']}) has no {src.name} - it will be skipped. "
                  f"Run matte_segments.py first.")
    return found


def subject_tags(effects, subjects):
    tags = []
    for i, rel in sorted(subjects.items()):
        e = effects[i]
        tags.append(
            f'    <div id="subj-{i}" class="layer subj">\n'
            f'      <video id="subject-{i}" class="clip" src="{rel}" data-start="{e["start"]}" data-duration="{e["dur"]}" '
            f'data-media-start="0" data-track-index="{2 + i}" muted playsinline></video>\n    </div>')
    return "\n".join(tags)


def theme_css(theme, fit):
    pairs = [f"--fx-{k}: {v};" for k, v in (theme or {}).items()]
    pairs += [f"--fit-x: {fit['x'] * 100:.2f}%;", f"--fit-y: {fit['y'] * 100:.2f}%;"]
    return ":root { " + " ".join(pairs) + " }"


def render_html(plan, footage_rel, subjects):
    W, H = plan["canvas"]["w"], plan["canvas"]["h"]
    D = plan["footage"]["duration"]
    scripts = "\n".join(f'    <script src="thfx/{s}"></script>' for s in RUNTIME_SCRIPTS)
    return f"""<!doctype html>
<html lang="he">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>talking-head-fx</title>
    <script src="{GSAP_URL}"></script>
    <link rel="stylesheet" href="thfx/thfx.css" />
    <style>{theme_css(plan.get("theme"), plan["footage"]["fit"])}</style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-width="{W}" data-height="{H}" data-duration="{D}">
    <div id="fx-bg" class="layer"></div>
    <div id="cam" class="layer">
      <video id="footage" class="clip" src="{footage_rel}" data-start="0" data-duration="{D}" data-track-index="0" data-has-audio="true" playsinline></video>
    </div>
    <div id="fx-mid" class="layer"></div>
{subject_tags(plan["effects"], subjects)}
    <div id="lens-wrap" class="layer">
      <div id="lens-inner">
        <video id="lens" class="clip" src="{footage_rel.replace("footage", "footage_lens")}" data-start="0" data-duration="{D}" data-track-index="1" muted playsinline></video>
      </div>
    </div>
    <div id="fx-top" class="layer"></div>
    <div id="captions" class="layer"></div>
    </div>
{scripts}
    <script>
      window.THFX_PLAN = {json.dumps(plan, ensure_ascii=False)};
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = THFX.run(window.THFX_PLAN);
    </script>
  </body>
</html>
"""


def load_json(path, default=None):
    if not path:
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_plan(a, raw_plan, face, words, src_w, src_h, dur):
    cw, ch = raw_plan.get("canvas", DEFAULT_CANVAS)
    plan = {
        "compositionId": "main", "seed": raw_plan.get("seed", 7),
        "canvas": {"w": cw, "h": ch}, "theme": raw_plan.get("theme", {}),
        "footage": {"w": src_w, "h": src_h, "duration": round(dur, 3), "fit": cover_fit((cw, ch), (src_w, src_h), face)},
        "face": face, "effects": [e for e in raw_plan["effects"] if e["start"] < dur],
        "progress": raw_plan.get("progress"),
    }
    cap = raw_plan.get("captions")
    if words and cap is not False:
        plan["captions"] = dict(cap if isinstance(cap, dict) else {}, words=words)
    return plan


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--footage", required=True, type=Path)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--face", required=True)
    ap.add_argument("--words")
    ap.add_argument("--subjects")
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # Hebrew output through a pipe on non-Hebrew Windows
    if not a.footage.exists():
        sys.exit(f"ERROR: footage not found: {a.footage}")
    src_w, src_h, dur = probe(a.footage)
    raw_plan, face, words = load_json(a.plan), load_json(a.face), load_json(a.words)
    plan = build_plan(a, raw_plan, face, words, src_w, src_h, dur)
    out = a.out.resolve()
    init_project(out)
    subjects = copy_assets(out, a.footage, a.subjects, plan["effects"])
    footage_rel = "assets/footage" + a.footage.suffix.lower()
    (out / "index.html").write_text(render_html(plan, footage_rel, subjects), encoding="utf-8")
    print(f"built {out / 'index.html'}: {len(plan['effects'])} effects, {len(subjects)} cut-outs, "
          f"{plan['canvas']['w']}x{plan['canvas']['h']}, {dur:.1f}s")


if __name__ == "__main__":
    main()
