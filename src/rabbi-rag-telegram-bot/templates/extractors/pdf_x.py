"""pdf → paragraphs via pypdf."""
from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader


def extract_pdf(path: Path) -> list[str]:
    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        t = page.extract_text() or ""
        pages.append(t)
    full = "\n\n".join(pages)
    parts = re.split(r"\n\s*\n", full.strip())
    return [p.strip() for p in parts if p.strip()]
