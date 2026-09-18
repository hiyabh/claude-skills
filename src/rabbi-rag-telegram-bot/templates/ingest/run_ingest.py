"""CLI entrypoint: discover → convert → chunk → embed → upsert."""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone

from tqdm import tqdm

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from config import required_for_ingest
from ingest.chunk import chunk_text
from ingest.convert import convert_to_text
from ingest.discover import discover_files, SourceFile
from ingest.embed import embed_documents
from ingest.manifest import file_sha256, load_manifest, needs_reingest, save_manifest
from ingest.store import (
    delete_by_file,
    ensure_collection,
    get_client,
    upsert_points,
)


def build_payloads(sf: SourceFile, chunks) -> list[dict]:
    return [
        {
            "book": sf.book,
            "subsection": sf.subsection,
            "section_label": c.section_label,
            "file_source": sf.rel_key,
            "is_primary": sf.is_primary,
            "chunk_index": c.chunk_index,
            "char_start": c.char_start,
            "char_end": c.char_end,
            "text": c.text,
        }
        for c in chunks
    ]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="עיבוד מחדש גם אם hash לא השתנה")
    parser.add_argument("--limit", type=int, default=None, help="N קבצים ראשונים בלבד")
    parser.add_argument("--only", type=str, default=None, help="רק קבצים שכוללים מחרוזת זו")
    args = parser.parse_args(argv)

    missing = required_for_ingest()
    if missing:
        print(f"❌ env vars חסרים: {missing}")
        return 2

    print("🔍 מגלה קבצים...")
    files = discover_files()
    if args.only:
        files = [f for f in files if args.only in f.rel_key]
    if args.limit:
        files = files[: args.limit]
    print(f"✓ נמצאו {len(files)} קבצים לקליטה")

    manifest = load_manifest()
    client = get_client()

    total_chunks = 0
    skipped = 0
    failed: list[tuple[str, str]] = []
    pending: list[tuple[SourceFile, list, list[list[float]] | None]] = []

    print("\n📄 ממיר ומפצל...")
    for sf in tqdm(files, desc="convert"):
        try:
            current_hash = file_sha256(sf.path)
        except Exception as e:
            failed.append((sf.rel_key, f"sha256: {e}"))
            continue

        if not args.force and not needs_reingest(sf.rel_key, current_hash, manifest):
            skipped += 1
            continue

        try:
            text = convert_to_text(sf.path)
        except Exception as e:
            failed.append((sf.rel_key, f"convert: {type(e).__name__}: {e}"))
            continue

        chunks = chunk_text(text)
        if not chunks:
            failed.append((sf.rel_key, "0 chunks"))
            continue

        pending.append((sf, chunks, None))
        manifest[sf.rel_key] = {
            "hash": current_hash,
            "chunks": len(chunks),
            "book": sf.book,
            "subsection": sf.subsection,
            "is_primary": sf.is_primary,
            "ingested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

    if pending:
        print(f"\n🧬 embed {sum(len(c) for _, c, _ in pending)} chunks...")
        all_texts = []
        owners: list[tuple[int, int]] = []
        for pi, (_, chunks, _) in enumerate(pending):
            for ci, c in enumerate(chunks):
                all_texts.append(c.text)
                owners.append((pi, ci))

        t0 = time.time()
        vectors = embed_documents(all_texts)
        print(f"✓ embed הושלם ב-{time.time() - t0:.1f}s")

        per_file_vecs: dict[int, list[list[float]]] = {pi: [] for pi in range(len(pending))}
        for (pi, _), vec in zip(owners, vectors):
            per_file_vecs[pi].append(vec)
        for pi in range(len(pending)):
            pending[pi] = (pending[pi][0], pending[pi][1], per_file_vecs[pi])

    if pending:
        sample_vec_size = len(pending[0][2][0])
        ensure_collection(client, vector_size=sample_vec_size)

        print(f"\n📤 העלאה ל-Qdrant...")
        for sf, chunks, vecs in tqdm(pending, desc="upsert"):
            payloads = build_payloads(sf, chunks)
            try:
                delete_by_file(client, sf.rel_key)
            except Exception:
                pass
            try:
                upsert_points(client, vecs, payloads)
                total_chunks += len(chunks)
            except Exception as e:
                failed.append((sf.rel_key, f"upsert: {type(e).__name__}: {e}"))

    save_manifest(manifest)

    print("\n" + "=" * 50)
    print(f"✅ סיום ingestion")
    print(f"  קבצים מעובדים: {len(pending)}")
    print(f"  קבצים מדולגים: {skipped}")
    print(f"  chunks חדשים/מעודכנים: {total_chunks}")
    if failed:
        print(f"  ❌ נכשלו: {len(failed)}")
        for rk, err in failed[:10]:
            print(f"    - {rk}: {err}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
