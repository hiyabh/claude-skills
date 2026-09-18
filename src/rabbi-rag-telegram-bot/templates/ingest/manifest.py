"""Manifest לאידמפוטנטיות: file_source → sha256."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from config import MANIFEST_FILE


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def load_manifest() -> dict[str, dict]:
    if not MANIFEST_FILE.exists():
        return {}
    return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))


def save_manifest(manifest: dict[str, dict]) -> None:
    MANIFEST_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def needs_reingest(rel_key: str, current_hash: str, manifest: dict[str, dict]) -> bool:
    prev = manifest.get(rel_key)
    if prev is None:
        return True
    return prev.get("hash") != current_hash
