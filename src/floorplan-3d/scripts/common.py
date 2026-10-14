"""Shared helpers: the work folder, the sheet frame, and where PlanWalk lives.

Every script in this skill works on one *work folder* that holds the rendered
sheet (sheet.png), its frame (frame.json: how sheet pixels map to metres), and
the plan files. The frame is the single source of truth for that mapping, so
the zoom grids, the overlay and the CV result all agree on coordinates.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

FRAME_FILE = "frame.json"
SHEET_FILE = "sheet.png"
METRES_PER_INCH = 0.0254

# PlanWalk is optional. Point FLOORPLAN3D_PLANWALK at a checkout to use it, or
# set FLOORPLAN3D_NO_PLANWALK=1 to force the vision-only path (portability test).
DEFAULT_PLANWALK = Path.home() / "Documents" / "דירות בתלת מימד"


def utf8_stdout() -> None:
    """Hebrew labels go to the console; Windows defaults to a legacy codepage."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def planwalk_dir() -> Path | None:
    if os.environ.get("FLOORPLAN3D_NO_PLANWALK") == "1":
        return None
    root = Path(os.environ.get("FLOORPLAN3D_PLANWALK", DEFAULT_PLANWALK))
    return root if (root / "src" / "planwalk" / "schema.py").exists() else None


def planwalk_python(root: Path) -> Path | None:
    """PlanWalk's own venv interpreter, which has OpenCV and Tesseract bindings."""
    for rel in ("Scripts/python.exe", "bin/python"):
        candidate = root / ".venv" / rel
        if candidate.exists():
            return candidate
    return None


def px_per_m_from_ratio(dpi: float, ratio: int) -> float:
    """A 1:ratio drawing rendered at dpi: one real metre is this many pixels."""
    return dpi / METRES_PER_INCH / ratio


def load_frame(work: Path) -> dict:
    path = Path(work) / FRAME_FILE
    if not path.exists():
        raise SystemExit(f"{path} not found - run prepare.py on this work folder first")
    return json.loads(path.read_text(encoding="utf-8"))


def save_frame(work: Path, frame: dict) -> Path:
    path = Path(work) / FRAME_FILE
    path.write_text(json.dumps(frame, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def has_world(frame: dict) -> bool:
    return bool(frame.get("px_per_m")) and frame.get("origin_px") is not None


def to_px(frame: dict, point) -> tuple[float, float]:
    """World metres (x east, y north) to sheet pixels (y down)."""
    ox, oy = frame["origin_px"]
    s = frame["px_per_m"]
    return (point[0] * s + ox, oy - point[1] * s)


def to_world(frame: dict, px) -> tuple[float, float]:
    ox, oy = frame["origin_px"]
    s = frame["px_per_m"]
    return ((px[0] - ox) / s, (oy - px[1]) / s)


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> Path:
    path = Path(path)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
