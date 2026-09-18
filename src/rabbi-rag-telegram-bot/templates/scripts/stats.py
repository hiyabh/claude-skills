"""סטטיסטיקות המאגר — קבצים, chunks, ספרים."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingest.manifest import load_manifest
from ingest.store import collection_stats, get_client


def main():
    manifest = load_manifest()
    if not manifest:
        print("manifest ריק — לא רץ ingestion עדיין?")
    else:
        total_chunks = sum(e.get("chunks", 0) for e in manifest.values())
        books = Counter(e.get("book", "?") for e in manifest.values())
        primary_count = sum(1 for e in manifest.values() if e.get("is_primary"))
        secondary_count = sum(1 for e in manifest.values() if not e.get("is_primary", True))
        print("📊 לפי manifest.json:")
        print(f"  קבצים: {len(manifest)} (ראשוני: {primary_count}, ביאורים: {secondary_count})")
        print(f"  chunks: {total_chunks}")
        print(f"\n  לפי ספר:")
        for book, count in sorted(books.items(), key=lambda x: -x[1]):
            file_chunks = sum(e["chunks"] for e in manifest.values() if e.get("book") == book)
            print(f"    {book}: {count} קבצים, {file_chunks} chunks")

    print("\n📊 לפי Qdrant:")
    try:
        client = get_client()
        stats = collection_stats(client)
        for k, v in stats.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"  ❌ {e}")


if __name__ == "__main__":
    main()
