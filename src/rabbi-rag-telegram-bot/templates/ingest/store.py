"""Qdrant upsert + collection management."""
from __future__ import annotations

import hashlib
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from config import QDRANT_API_KEY, QDRANT_COLLECTION, QDRANT_URL


def get_client() -> QdrantClient:
    if not QDRANT_URL or not QDRANT_API_KEY:
        raise RuntimeError("QDRANT_URL / QDRANT_API_KEY חסרים ב-.env")
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=60)


def ensure_collection(client: QdrantClient, vector_size: int) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if QDRANT_COLLECTION in existing:
        info = client.get_collection(QDRANT_COLLECTION)
        existing_size = info.config.params.vectors.size
        if existing_size != vector_size:
            raise RuntimeError(
                f"Collection {QDRANT_COLLECTION} קיים עם vector_size={existing_size}, "
                f"אבל המודל מחזיר {vector_size}. מחק את הקולקשן או שנה QDRANT_COLLECTION."
            )
        return
    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=qm.VectorParams(size=vector_size, distance=qm.Distance.COSINE),
    )


def _point_id(file_source: str, chunk_index: int) -> str:
    raw = f"{file_source}::{chunk_index}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"


def upsert_points(
    client: QdrantClient,
    vectors: list[list[float]],
    payloads: list[dict[str, Any]],
) -> int:
    assert len(vectors) == len(payloads)
    points = []
    for vec, payload in zip(vectors, payloads):
        pid = _point_id(payload["file_source"], payload["chunk_index"])
        points.append(qm.PointStruct(id=pid, vector=vec, payload=payload))
    client.upsert(collection_name=QDRANT_COLLECTION, points=points, wait=True)
    return len(points)


def delete_by_file(client: QdrantClient, file_source: str) -> None:
    client.delete(
        collection_name=QDRANT_COLLECTION,
        points_selector=qm.FilterSelector(
            filter=qm.Filter(
                must=[qm.FieldCondition(key="file_source", match=qm.MatchValue(value=file_source))]
            )
        ),
        wait=True,
    )


def collection_stats(client: QdrantClient) -> dict[str, Any]:
    info = client.get_collection(QDRANT_COLLECTION)
    return {
        "points_count": info.points_count,
        "vector_size": info.config.params.vectors.size,
        "status": str(info.status),
    }
