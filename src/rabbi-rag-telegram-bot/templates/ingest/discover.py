"""מציאת קבצים בתיקיית המקור לפי סוג + סינון לפי books_index.json."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from config import BOOKS_INDEX_FILE, SOURCE_DIR

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ALLOWED_EXT = {".doc", ".docx", ".pdf", ".txt"}
SKIP_NAMES = {"Thumbs.db", ".DS_Store"}
SKIP_EXT = {".mp3", ".jpg", ".jpeg", ".gif", ".png", ".tmp", ".db"}


@dataclass
class SourceFile:
    path: Path
    rel_key: str
    book: str
    subsection: str | None
    is_primary: bool


def load_books_index() -> dict[str, dict]:
    raw = json.loads(BOOKS_INDEX_FILE.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def _rel_key(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def discover_files(source_dir: Path | None = None) -> list[SourceFile]:
    root = source_dir or SOURCE_DIR
    if not root.exists():
        raise FileNotFoundError(f"SOURCE_DIR לא קיים: {root}")

    index = load_books_index()
    out: list[SourceFile] = []
    unknown: list[str] = []

    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.name in SKIP_NAMES:
            continue
        suffix = p.suffix.lower()
        if suffix in SKIP_EXT:
            continue
        if suffix not in ALLOWED_EXT:
            continue

        key = _rel_key(p, root)
        meta = index.get(key)
        if meta is None:
            unknown.append(key)
            continue
        if not meta.get("preferred", True):
            continue

        out.append(SourceFile(
            path=p,
            rel_key=key,
            book=meta["book"],
            subsection=meta.get("subsection"),
            is_primary=meta.get("is_primary", True),
        ))

    if unknown:
        print(f"⚠️  {len(unknown)} קבצים לא ב-books_index.json (יידלגו):")
        for k in unknown[:10]:
            print(f"    - {k}")
        if len(unknown) > 10:
            print(f"    ... + {len(unknown) - 10} נוספים")

    return out
