# -*- coding: utf-8 -*-
"""Project settings from build/video.json (written by new_project.py, edited per lesson)."""
import json
from pathlib import Path

BUILD = Path(__file__).resolve().parent
CLIP = BUILD.parent / "clip"
LESSON_DIR = BUILD.parents[1]
CFG = json.loads((BUILD / "video.json").read_text(encoding="utf-8"))

TITLE = CFG["title"]
SUBTITLE = CFG.get("subtitle", "")
SOURCE_AUDIO = Path(CFG["audio"])
AUDIO = CLIP / "assets" / "audio" / "lesson.m4a"
MAX_GAP = CFG.get("density_max_gap", 12)


def out_name(suffix):
    """Deliverable path in the lesson folder: '<title> - <suffix>'."""
    return LESSON_DIR / f"{TITLE} - {suffix}"
