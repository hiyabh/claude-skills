"""One entry point for the whole skill: it chains the stage scripts and always says what comes next.

Usage:
    python pipeline.py start  <plan.pdf|png> [--work W] [--scale-ratio 50] [--page N]
    python pipeline.py check  <work>                         # reconcile + overlay, after vision.plan.json exists
    python pipeline.py build  <work> [--game] [--tier high|lite] [--views] [--city C] [--title T]
    python pipeline.py status <work>

The one step no script can do is reading the sheet: between `start` and `check` Claude writes
<work>/vision.plan.json (references/plan-format.md, reading-plans.md). Outputs land in <work>/out/:
  viewer.html (+ .preview.html)      the architectural model (single file)
  game/index.html + game/assets/...  the walkable photoreal apartment (multi-file)
  publish.json                       exactly what to pass to the Artifact tool for each
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from common import read_json, utf8_stdout, write_json

SCRIPTS = Path(__file__).resolve().parent
WORK_PREFIX = "3d-"
VIEWER_NAME = "viewer.html"


def step(script: str, *args: str, allow: tuple[int, ...] = (0,)) -> int:
    """Run one stage script, streaming its output; stop the pipeline on an unexpected exit code."""
    print(f"\n== {script} {' '.join(a for a in args if not a.startswith(str(Path.home())))}")
    code = subprocess.run([sys.executable, str(SCRIPTS / script), *args], cwd=SCRIPTS).returncode
    if code not in allow:
        raise SystemExit(f"{script} failed (exit {code}) - fix the problem above, then re-run this pipeline step")
    return code


def cmd_start(args) -> None:
    work = args.work or args.input.parent / f"{WORK_PREFIX}{args.input.stem[:14]}"
    extra = ["--page", str(args.page)] + (["--scale-ratio", str(args.scale_ratio)] if args.scale_ratio else [])
    step("prepare.py", str(args.input), str(work), *extra)
    print(f"\nnext: read the sheet into {work / 'vision.plan.json'}, then:  python pipeline.py check \"{work}\"")


def cmd_check(args) -> None:
    if not (args.work / "vision.plan.json").exists():
        raise SystemExit(f"{args.work / 'vision.plan.json'} is missing - read the sheet first (SKILL.md step 2)")
    code = step("reconcile.py", str(args.work), allow=(0, 1, 2))
    verdict = {0: "clean", 2: "warnings - resolve or turn each into a note", 1: "INVALID - fix plan.json"}[code]
    if (args.work / "frame.json").exists():
        step("overlay.py", str(args.work))
        print(f"\nreconcile: {verdict}. Open {args.work / 'overlay_plan.png'} and compare it with the sheet.")
    else:
        print(f"\nreconcile: {verdict}. No sheet in this work folder (no frame.json), so there is no overlay to check.")
    if code != 1:
        print(f"next:  python pipeline.py build \"{args.work}\" [--game --views --city <city>]")


def build_viewer(work: Path, out: Path, title: str | None) -> dict:
    page = out / VIEWER_NAME
    sheet = ["--work", str(work)] if (work / "frame.json").exists() else []   # the drawing underlay needs a sheet
    step("build_viewer.py", str(work / "plan.json"), "-o", str(page), *sheet, "--preview", *(["--title", title] if title else []))
    step("check_viewer.py", str(page.with_suffix(".preview.html")), "--shots", str(out / "checks-viewer"))
    return {"file_path": str(page), "capabilities": {"downloads": True}, "icon": "home"}


def build_game(work: Path, out: Path, args) -> dict:
    game = out / "game"
    views = work / "views"
    if args.views and not (views / "views.json").exists():
        step("views.py", str(work / "plan.json"), "-o", str(views), "--city", args.city)
    extra = ["--views", str(views)] if (views / "views.json").exists() else []
    step("build_game.py", str(work / "plan.json"), "-o", str(game), "--tier", args.tier, *extra, *(["--title", args.title] if args.title else []))
    step("check_game.py", str(game), "--play", "--shots", str(out / "checks-game"))
    files = json.loads((game / "publish-files.json").read_text(encoding="utf-8"))
    return {"file_path": str(game / "index.html"), "root": str(game), "files": files, "capabilities": {"downloads": True}, "icon": "home"}


def cmd_build(args) -> None:
    if not (args.work / "plan.json").exists():
        raise SystemExit(f"{args.work / 'plan.json'} is missing - run:  python pipeline.py check \"{args.work}\"")
    out = args.work / "out"
    out.mkdir(exist_ok=True)
    publish = {"viewer": build_viewer(args.work, out, args.title)}
    if args.game:
        publish["game"] = build_game(args.work, out, args)
    write_json(out / "publish.json", publish)
    print(f"\nready: {out / 'publish.json'} lists what to publish. Look at the screenshots in {out} first.")


def cmd_status(args) -> None:
    w = args.work
    stages = [("sheet prepared", w / "frame.json"), ("vision plan written", w / "vision.plan.json"),
              ("reconciled", w / "plan.json"), ("viewer built", w / "out" / VIEWER_NAME),
              ("window views", w / "views" / "views.json"), ("game built", w / "out" / "game" / "index.html")]
    for name, path in stages:
        print(f"  [{'x' if path.exists() else ' '}] {name}")
    if (w / "reconcile.md").exists():
        print("\n" + (w / "reconcile.md").read_text(encoding="utf-8")[:1500])
    if (w / "plan.json").exists():
        plan = read_json(w / "plan.json")
        print(f"rooms {len(plan['rooms'])}, walls {len(plan['walls'])}, openings {len(plan['openings'])}, notes {len(plan.get('notes', []))}")


def main() -> int:
    utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start"); s.add_argument("input", type=Path); s.add_argument("--work", type=Path)
    s.add_argument("--scale-ratio", type=int); s.add_argument("--page", type=int, default=1)
    sub.add_parser("check").add_argument("work", type=Path)
    b = sub.add_parser("build"); b.add_argument("work", type=Path); b.add_argument("--game", action="store_true")
    b.add_argument("--tier", choices=("high", "lite"), default="high"); b.add_argument("--views", action="store_true")
    b.add_argument("--city", default="Jerusalem"); b.add_argument("--title")
    sub.add_parser("status").add_argument("work", type=Path)
    args = parser.parse_args()
    {"start": cmd_start, "check": cmd_check, "build": cmd_build, "status": cmd_status}[args.cmd](args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
