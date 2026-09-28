"""Render index.html to MP4, verify the file, deliver it, and make a proof sheet.

    python render.py <project> --out "C:/.../01 - ניבים בתנועה.mp4"
    python render.py <project> --out ... --snapshot     # skip the native try
    python render.py <project> --verify-only --out ...  # re-check a render
    python render.py <project> --preview 24             # 24 stills -> preview.png, no MP4

Native `hyperframes render` first. On some Windows machines it dies with
`spawn UNKNOWN` (Chrome cannot start); when it fails the fallback is the proven
path - `snapshot --at` every frame, then one ffmpeg encode.

`hyperframes check` validates the composition, not the encoded file, so the
file itself is checked here: duration against data-duration, an audio stream,
and first/last frames that are not empty.
"""

import json
import os
import re
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

from build_composition import HF_CLI
from pm_common import FPS, flag, project_arg

SHELL = os.name == "nt"
DURATION_TOLERANCE_S = 0.15
EMPTY_DETAIL = 2.0
PROOF_COLS = 6
PROOF_ROWS = 4
PROOF_THUMB_W = 180
SNAPSHOT_BATCH = 300


def film_length(project):
    with open(os.path.join(project, "index.html"), encoding="utf-8") as fh:
        m = re.search(r'id="root"[^>]*data-duration="([\d.]+)"', fh.read(), re.S)
    if not m:
        sys.exit("index.html has no root data-duration - rebuild it")
    return float(m.group(1))


def native(project, out):
    cmd = ["npx", "--yes", HF_CLI, "render", "--quality", "delivery", "--output", out]
    r = subprocess.run(cmd, cwd=project, shell=SHELL)
    return r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0


def _capture(project, frames_dir, n_frames):
    for lo in range(0, n_frames, SNAPSHOT_BATCH):
        at = ",".join(f"{i / FPS:.4f}" for i in range(lo, min(n_frames, lo + SNAPSHOT_BATCH)))
        out = os.path.join(frames_dir, f"b{lo:05d}")
        subprocess.run(["npx", "--yes", HF_CLI, "snapshot", "--at", at, "--no-end",
                        "--describe", "false", "-o", out], cwd=project, check=True, shell=SHELL,
                       capture_output=True)
        print(f"  captured {min(n_frames, lo + SNAPSHOT_BATCH)}/{n_frames}")


def _sequence(frames_dir, n_frames):
    """Snapshot names pad to the widest index, so sort numerically, then link."""
    found = {}
    for batch in sorted(os.listdir(frames_dir)):
        if not batch.startswith("b"):
            continue
        lo = int(batch[1:])
        for name in os.listdir(os.path.join(frames_dir, batch)):
            m = re.match(r"frame-(\d+)", name)
            if m and name.endswith(".png"):
                found[lo + int(m.group(1))] = os.path.join(frames_dir, batch, name)
    missing = [i for i in range(n_frames) if i not in found]
    if missing:
        sys.exit(f"capture is short {len(missing)} frames, first missing {missing[0]}")
    seq = os.path.join(frames_dir, "seq")
    os.makedirs(seq, exist_ok=True)
    for i in range(n_frames):
        dest = os.path.join(seq, f"f{i:05d}.png")
        if not os.path.exists(dest):
            os.link(found[i], dest)
    return seq


def snapshot_render(project, out, total):
    n_frames = int(round(total * FPS))
    frames_dir = os.path.join(project, "work", "frames")
    shutil.rmtree(frames_dir, ignore_errors=True)
    os.makedirs(frames_dir)
    _capture(project, frames_dir, n_frames)
    seq = _sequence(frames_dir, n_frames)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS),
                    "-i", os.path.join(seq, "f%05d.png"),
                    "-i", os.path.join(project, "assets", "music", "bed.m4a"),
                    "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", out], check=True)
    shutil.rmtree(frames_dir, ignore_errors=True)


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration:stream=codec_type,width,height", "-of", "json", path],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def frame_at(path, seconds):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{seconds:.3f}", "-i", path,
                        "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, check=True)
    info = probe(path)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    return np.frombuffer(r.stdout, np.uint8).reshape(v["height"], v["width"], 3)


def verify(path, total):
    info = probe(path)
    dur = float(info["format"]["duration"])
    kinds = [s["codec_type"] for s in info["streams"]]
    problems = []
    if abs(dur - total) > DURATION_TOLERANCE_S:
        problems.append(f"duration {dur:.2f}s, composition says {total:.2f}s")
    if "audio" not in kinds:
        problems.append("no audio stream - check <audio id=...> in index.html")
    for label, t in (("first", 0.0), ("last", max(0.0, dur - 0.1))):
        detail = float(frame_at(path, t).astype(np.float32).mean(2).std(axis=1).mean())
        if detail < EMPTY_DETAIL:
            problems.append(f"{label} frame is empty (detail {detail:.2f})")
    print(f"  {os.path.basename(path)}: {dur:.2f}s, streams {kinds}")
    for p in problems:
        print(f"  PROBLEM: {p}")
    return not problems


def proof_sheet(path, total, dest):
    n = PROOF_COLS * PROOF_ROWS
    thumbs = []
    for i in range(n):
        im = Image.fromarray(frame_at(path, total * (i + 0.5) / n))
        thumbs.append(im.resize((PROOF_THUMB_W, round(im.height * PROOF_THUMB_W / im.width))))
    th = thumbs[0].height
    sheet = Image.new("RGB", (PROOF_COLS * PROOF_THUMB_W, PROOF_ROWS * th), "white")
    for i, im in enumerate(thumbs):
        sheet.paste(im, ((i % PROOF_COLS) * PROOF_THUMB_W, (i // PROOF_COLS) * th))
    sheet.save(dest)
    print(f"  proof sheet -> {dest}")


def preview(project, total, count):
    """Snapshot `count` evenly spaced moments into one sheet - minutes, not the
    half hour a snapshot render takes. Look at it before committing to a render."""
    folder = os.path.join(project, "work", "preview")
    shutil.rmtree(folder, ignore_errors=True)
    at = ",".join(f"{total * (i + 0.5) / count:.3f}" for i in range(count))
    subprocess.run(["npx", "--yes", HF_CLI, "snapshot", "--at", at, "--no-end",
                    "--describe", "false", "-o", folder], cwd=project, check=True,
                   shell=SHELL, capture_output=True)
    shots = sorted((int(m.group(1)), n) for n in os.listdir(folder)
                   if (m := re.match(r"frame-(\d+)-.*\.png$", n)))
    thumbs = [Image.open(os.path.join(folder, n)).convert("RGB") for _, n in shots]
    th = round(thumbs[0].height * PROOF_THUMB_W / thumbs[0].width)
    rows = (len(thumbs) + PROOF_COLS - 1) // PROOF_COLS
    sheet = Image.new("RGB", (PROOF_COLS * PROOF_THUMB_W, rows * th), "white")
    for i, im in enumerate(thumbs):
        sheet.paste(im.resize((PROOF_THUMB_W, th)),
                    ((i % PROOF_COLS) * PROOF_THUMB_W, (i // PROOF_COLS) * th))
    dest = os.path.join(project, "preview.png")
    sheet.save(dest)
    print(f"  preview sheet ({len(thumbs)} stills) -> {dest}")


def main():
    project = project_arg()
    if flag("preview"):
        count = flag("preview")
        preview(project, film_length(project), int(count) if count is not True else 24)
        return
    out = flag("out")
    if not out or out is True:
        sys.exit('--out "<delivery path>.mp4" is required - a descriptive Hebrew name')
    out = os.path.abspath(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    total = film_length(project)
    if not flag("verify-only"):
        if flag("snapshot") or not native(project, out):
            print("native render unavailable - rendering through snapshots")
            snapshot_render(project, out, total)
    ok = verify(out, total)
    proof_sheet(out, total, os.path.join(project, "renders_proof.png"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
