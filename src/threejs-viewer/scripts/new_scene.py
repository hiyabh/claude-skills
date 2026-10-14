"""Build a self-contained Three.js viewer page from a scene definition file.

Usage:
    python new_scene.py <scene.js> <out.html> --title "<page title>" [--preview]

The scene file holds only the scene block (META, TIMELINE, CONTROLS, READOUTS,
INFO, CAMERA, buildScene, update, onParam, plus any addon imports). It replaces
the block between the @@SCENE markers in assets/scene-template.html.
--preview also writes <out>.preview.html with a doctype, for opening locally.
"""
import argparse
import html
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "assets" / "scene-template.html"
BEGIN, END = "// @@SCENE-BEGIN", "// @@SCENE-END"
REQUIRED = ("META", "TIMELINE", "CONTROLS", "READOUTS", "INFO", "CAMERA", "buildScene", "update", "onParam")
PREVIEW_HEAD = (
    '<!doctype html>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
)
MODULE_RE = re.compile(r'<script type="module">(.*?)</script>', re.S)


def missing_names(scene: str) -> list[str]:
    return [n for n in REQUIRED if not re.search(rf"\b(?:const|let|function)\s+{n}\b", scene)]


def inject(template: str, scene: str, title: str) -> str:
    start = template.index(BEGIN)
    end = template.index(END) + len(END)
    page = template[:start] + BEGIN + "\n" + scene.strip() + "\n" + END + template[end:]
    return re.sub(r"<title>.*?</title>", f"<title>{html.escape(title)}</title>", page, count=1, flags=re.S)


def syntax_error(page: str) -> str | None:
    """Parse the page's module script with `node --check`; None means OK or node unavailable."""
    node = shutil.which("node")
    match = MODULE_RE.search(page)
    if not node or not match:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "scene.mjs"
        path.write_text(match.group(1), encoding="utf-8")
        result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, encoding="utf-8")
    if result.returncode == 0:
        return None
    return result.stderr.strip() or "node --check failed without output"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scene", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    scene = args.scene.read_text(encoding="utf-8")
    missing = missing_names(scene)
    if missing:
        print(f"Scene file is missing required declarations: {', '.join(missing)}")
        return 1
    page = inject(TEMPLATE.read_text(encoding="utf-8"), scene, args.title)
    error = syntax_error(page)
    if error:
        print(f"JavaScript syntax error in the scene:\n{error}")
        return 1
    args.out.write_text(page, encoding="utf-8")
    print(f"wrote {args.out} ({args.out.stat().st_size:,} bytes)")
    if args.preview:
        preview = args.out.with_suffix(".preview.html")
        preview.write_text(PREVIEW_HEAD + page, encoding="utf-8")
        print(f"wrote {preview}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
