#!/usr/bin/env python3
"""Cut the speaker out of the footage, only where the plan needs it.

For every matte effect in fx_plan.json (green_screen, studio, paper_cutout, magazine_cover,
growth_chart, frame_escape) this cuts that window out of the footage and runs
`npx hyperframes remove-background` on it -> subjects/subject_<i>.webm (VP9 with alpha),
where <i> is the effect's index in plan["effects"]. Matting only the windows keeps a
10-minute video from costing a 10-minute segmentation pass.

Usage:
    python matte_segments.py footage.mp4 --plan fx_plan.json --out subjects/ [--quality balanced]
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # cues.py sits next to this script
from cues import MATTE_TYPES

SEGMENT_CRF = "12"   # near-lossless intermediate so the cut-out matches the source colours


def cut_segment(footage, start, dur, dst):
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-i", str(footage), "-t", f"{dur:.3f}",
           "-an", "-c:v", "libx264", "-crf", SEGMENT_CRF, "-pix_fmt", "yuv420p", str(dst)]
    subprocess.run(cmd, check=True)


def remove_background(src, dst, quality):
    cmd = f'npx hyperframes remove-background "{src}" -o "{dst}" --quality {quality}'
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0 or not Path(dst).exists():
        sys.exit(f"ERROR: remove-background failed for {src.name}:\n{(r.stderr or r.stdout)[-800:]}\n"
                 "Check `npx hyperframes remove-background --info`; the first run downloads ~168MB of weights.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("footage", type=Path)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", default="subjects", type=Path)
    ap.add_argument("--quality", default="balanced", choices=["fast", "balanced", "best"])
    ap.add_argument("--force", action="store_true", help="re-matte segments that already exist")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # Hebrew output through a pipe on non-Hebrew Windows
    with open(a.plan, encoding="utf-8") as f:
        effects = json.load(f)["effects"]
    a.out.mkdir(parents=True, exist_ok=True)
    todo = [(i, e) for i, e in enumerate(effects) if e["type"] in MATTE_TYPES]
    if not todo:
        print("no matte effects in the plan - nothing to do")
        return
    with tempfile.TemporaryDirectory() as tmp:
        for n, (i, e) in enumerate(todo, 1):
            dst = a.out / f"subject_{i}.webm"
            if dst.exists() and not a.force:
                print(f"[{n}/{len(todo)}] {dst.name} exists - skipped")
                continue
            seg = Path(tmp) / f"seg_{i}.mp4"
            cut_segment(a.footage, e["start"], e["dur"], seg)
            remove_background(seg, dst, a.quality)
            print(f"[{n}/{len(todo)}] {e['type']} @ {e['start']}s -> {dst}")


if __name__ == "__main__":
    main()
