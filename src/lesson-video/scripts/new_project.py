# -*- coding: utf-8 -*-
"""Scaffold a lesson-video project next to the recording and normalize the audio.
Usage: python new_project.py --audio "<recording>" --title "<lesson title>" [--subtitle "..."] [--out "<lesson folder>"]
Creates <out>/סרטון/build (scripts + templates + video.json) and <out>/סרטון/clip (HyperFrames project)."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
ASSETS = SKILL / "assets"
LOUDNORM = "loudnorm=I=-16:TP=-1.5:LRA=11"
SKIP = {"new_project.py"}


def video_json(args):
    return {
        "title": args.title, "subtitle": args.subtitle, "audio": str(Path(args.audio).resolve()),
        "density_max_gap": 12, "keywords": [],
        "blocked_names": [], "blocked_stems": [], "timed_drops": [], "fixes": {},
        "thumb": {"img": "thumb-hero", "title": args.title, "kicker": "שיעור", "sub": args.subtitle, "badge": ""},
        "youtube": {"title": args.title, "description": "", "tags": [], "category": "Education", "playlist": ""},
        "reels": [],
    }


def copy_build(build, args):
    build.mkdir(parents=True, exist_ok=True)
    for f in SCRIPTS.glob("*"):
        if f.is_file() and f.name not in SKIP:
            shutil.copy2(f, build / f.name)
    shutil.copy2(ASSETS / "thumb_template" / "index.html", build / "thumb_template.html")
    shutil.copy2(ASSETS / "reel_template.html", build / "reel_template.html")
    for name in ("scenes.py", "edits.py", "chapter_spec.json"):
        shutil.copy2(ASSETS / "project_template" / name, build / name)
    shutil.copytree(ASSETS / "project_template" / "specs", build / "specs", dirs_exist_ok=True)
    (build / "beats").mkdir(exist_ok=True)
    (build / "video.json").write_text(json.dumps(video_json(args), ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = Path(args.out or Path(args.audio).resolve().parent) / "סרטון"
    if (root / "build" / "video.json").exists():
        raise SystemExit(f"{root} already has a project - edit it instead of re-scaffolding")
    copy_build(root / "build", args)
    shutil.copytree(ASSETS / "clip_template", root / "clip", dirs_exist_ok=True)
    audio_dir = root / "clip" / "assets" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", args.audio, "-af", LOUDNORM, "-c:a", "aac", "-b:a", "160k",
                    "-ar", "48000", str(audio_dir / "lesson.m4a")], check=True)
    print(f"project ready: {root}\nnext: cd \"{root / 'build'}\" && python -u transcribe.py > transcribe.log 2>&1  (background)")


if __name__ == "__main__":
    main()
