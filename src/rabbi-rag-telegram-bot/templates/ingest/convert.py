"""המרת קובץ DOC/DOCX/PDF לטקסט אחיד עם cache לוקלי."""
from __future__ import annotations

import hashlib
from pathlib import Path

from config import CONVERTED_DIR
from extractors import extract_docx, extract_pdf, extract_old_doc


def _cache_key(path: Path) -> str:
    h = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    return f"{path.stem}-{h}.txt"


def convert_to_text(path: Path, use_cache: bool = True) -> str:
    """מחזיר טקסט מאוחד (פסקאות מופרדות בשורה ריקה)."""
    suffix = path.suffix.lower()
    cache_file = CONVERTED_DIR / _cache_key(path)

    if use_cache and cache_file.exists():
        return cache_file.read_text(encoding="utf-8")

    if suffix == ".docx":
        paras = extract_docx(path)
    elif suffix == ".doc":
        paras = extract_old_doc(path)
    elif suffix == ".pdf":
        paras = extract_pdf(path)
    elif suffix == ".txt":
        raw = path.read_text(encoding="utf-8", errors="replace")
        paras = [p.strip() for p in raw.split("\n\n") if p.strip()]
    else:
        raise ValueError(f"סיומת לא נתמכת: {suffix}")

    text = "\n\n".join(paras)
    if use_cache:
        cache_file.write_text(text, encoding="utf-8")
    return text
