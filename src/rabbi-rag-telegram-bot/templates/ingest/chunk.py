"""חלוקת טקסט ל-chunks עם זיהוי גבולות סמנטיות עבריות (פרק/שער/סימן)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from config import CHUNK_OVERLAP, CHUNK_SIZE, MIN_CHUNK_CHARS

SECTION_PATTERNS = [
    (re.compile(r"^\s*פרק\s+([א-ת״׳'\d]+)"), "פרק"),
    (re.compile(r"^\s*שער\s+([א-ת״׳'\d]+)"), "שער"),
    (re.compile(r"^\s*סימן\s+([א-ת״׳'\d]+)"), "סימן"),
    (re.compile(r"^\s*אות\s+([א-ת״׳'\d]+)"), "אות"),
    (re.compile(r"^\s*דרוש\s+([א-ת״׳'\d]+)"), "דרוש"),
    (re.compile(r"^\s*פתח\s+([א-ת״׳'\d]+)"), "פתח"),
    (re.compile(r"^\s*חלק\s+([א-ת״׳'\d]+)"), "חלק"),
    (re.compile(r"^\s*הקדמ[הת]\b"), "הקדמה"),
    (re.compile(r"^\s*מאמר\s+([א-ת״׳'\d]+)"), "מאמר"),
    (re.compile(r"^\s*דרשה\s+([א-ת״׳'\d]+)"), "דרשה"),
    (re.compile(r"^\s*הלכה\s+([א-ת״׳'\d]+)"), "הלכה"),
]


@dataclass
class Chunk:
    text: str
    section_label: str | None
    chunk_index: int
    char_start: int
    char_end: int


@dataclass
class Section:
    label: str | None
    lines: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.lines).strip()


def _detect_section(line: str) -> str | None:
    stripped = line.strip()
    for pattern, prefix in SECTION_PATTERNS:
        m = pattern.match(stripped)
        if m:
            if prefix == "הקדמה":
                return "הקדמה"
            num = m.group(1)
            return f"{prefix} {num}"
    return None


def split_into_sections(text: str) -> list[Section]:
    sections: list[Section] = [Section(label=None)]
    for line in text.split("\n"):
        label = _detect_section(line)
        if label is not None:
            sections.append(Section(label=label, lines=[line]))
        else:
            sections[-1].lines.append(line)
    return [s for s in sections if s.text]


def _split_text_to_windows(text: str, size: int, overlap: int) -> list[tuple[str, int, int]]:
    """sliding window עם חיתוך עדיף בסוף משפט."""
    if len(text) <= size:
        return [(text, 0, len(text))]

    out: list[tuple[str, int, int]] = []
    pos = 0
    while pos < len(text):
        end = min(pos + size, len(text))
        if end < len(text):
            for sep in (". ", ".\n", ": ", "; ", "\n\n"):
                idx = text.rfind(sep, pos + size // 2, end)
                if idx != -1:
                    end = idx + len(sep)
                    break
        out.append((text[pos:end].strip(), pos, end))
        if end >= len(text):
            break
        pos = max(pos + 1, end - overlap)
    return out


def chunk_text(text: str) -> list[Chunk]:
    sections = split_into_sections(text)
    chunks: list[Chunk] = []

    merged: list[Section] = []
    buf: Section | None = None
    for s in sections:
        if buf is None:
            buf = Section(label=s.label, lines=list(s.lines))
            continue
        if len(buf.text) < MIN_CHUNK_CHARS:
            buf.lines.append("")
            buf.lines.extend(s.lines)
            if buf.label is None:
                buf.label = s.label
        else:
            merged.append(buf)
            buf = Section(label=s.label, lines=list(s.lines))
    if buf is not None:
        merged.append(buf)

    cursor = 0
    chunk_index = 0
    for section in merged:
        body = section.text
        if not body:
            continue
        windows = _split_text_to_windows(body, CHUNK_SIZE, CHUNK_OVERLAP)
        for w_text, w_start, w_end in windows:
            if not w_text.strip():
                continue
            chunks.append(Chunk(
                text=w_text,
                section_label=section.label,
                chunk_index=chunk_index,
                char_start=cursor + w_start,
                char_end=cursor + w_end,
            ))
            chunk_index += 1
        cursor += len(body) + 1
    return chunks
