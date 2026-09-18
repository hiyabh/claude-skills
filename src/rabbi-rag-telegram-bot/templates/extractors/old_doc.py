"""Old .doc / .rtf → paragraphs via LibreOffice headless conversion to .docx."""
from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path

from .docx_x import extract_docx
from config import TMP_DIR


def _find_soffice() -> str | None:
    return (
        shutil.which("libreoffice")
        or shutil.which("soffice")
        or shutil.which("soffice.com")
    )


def extract_old_doc(path: Path) -> list[str]:
    soffice = _find_soffice()
    if not soffice:
        raise RuntimeError(
            "LibreOffice not installed — cannot convert .doc. "
            "Install: https://www.libreoffice.org/ (Windows) or apt-get install libreoffice (Linux)"
        )

    work = TMP_DIR / f"convert-{uuid.uuid4().hex[:8]}"
    work.mkdir(parents=True, exist_ok=True)
    try:
        cmd = [
            soffice,
            "--headless",
            "--convert-to",
            "docx",
            "--outdir",
            str(work),
            str(path),
        ]
        subprocess.run(cmd, check=True, timeout=180, capture_output=True)
        out_files = list(work.glob("*.docx"))
        if not out_files:
            raise RuntimeError(f"LibreOffice produced no output for {path.name}")
        return extract_docx(out_files[0])
    finally:
        shutil.rmtree(work, ignore_errors=True)
