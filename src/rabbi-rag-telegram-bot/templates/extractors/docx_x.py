"""docx → paragraphs via python-docx."""
from __future__ import annotations

from pathlib import Path

from docx import Document


def extract_docx(path: Path) -> list[str]:
    doc = Document(str(path))
    paras = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if text:
            paras.append(text)
    return paras
