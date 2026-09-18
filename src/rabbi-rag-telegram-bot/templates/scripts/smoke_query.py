"""CLI: שלח שאלה אחת וקבל תשובה + Top hits."""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.answer import answer_question


def main(argv):
    if len(argv) < 2:
        print("usage: python scripts/smoke_query.py \"<שאלה>\"")
        return 2
    question = " ".join(argv[1:])
    print(f"\n❓ {question}\n")
    result = answer_question(question)
    print("─" * 60)
    print("📚 Top hits (rerank order):")
    for i, h in enumerate(result.hits, 1):
        p = h.payload
        loc = " · ".join(filter(None, [p.get("book"), p.get("subsection"), p.get("section_label")]))
        primary = "ראשוני" if p.get("is_primary") else "ביאור"
        print(f"  {i}. [{primary}] {loc}  (rerank={h.score:.3f}, vec={h.vector_score:.3f})")
    print("─" * 60)
    print(result.text)
    print("─" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
