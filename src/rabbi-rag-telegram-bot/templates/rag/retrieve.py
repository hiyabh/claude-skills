"""צינור retrieval: embed query → Qdrant top-K → Cohere rerank top-N."""
from __future__ import annotations

from dataclasses import dataclass

import cohere

from config import (
    COHERE_API_KEY,
    QDRANT_COLLECTION,
    RERANK_MODEL,
    RERANK_SCORE_THRESHOLD,
    TOP_K_VECTOR,
    TOP_N_RERANK,
)
from ingest.embed import embed_query
from ingest.store import get_client


@dataclass
class Hit:
    payload: dict
    score: float
    vector_score: float


def _qdrant_search(qclient, vector: list[float], top_k: int) -> list[tuple[dict, float]]:
    res = qclient.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=vector,
        limit=top_k,
        with_payload=True,
    )
    return [(r.payload, float(r.score)) for r in res]


def _rerank(question: str, docs: list[tuple[dict, float]], top_n: int) -> list[Hit]:
    if not docs:
        return []
    co = cohere.ClientV2(api_key=COHERE_API_KEY)
    texts = [p.get("text", "") for p, _ in docs]
    resp = co.rerank(
        model=RERANK_MODEL,
        query=question,
        documents=texts,
        top_n=top_n,
    )
    hits: list[Hit] = []
    for r in resp.results:
        payload, v_score = docs[r.index]
        hits.append(Hit(payload=payload, score=float(r.relevance_score), vector_score=v_score))
    return hits


def retrieve(question: str, *, top_k: int | None = None, top_n: int | None = None) -> list[Hit]:
    k = top_k or TOP_K_VECTOR
    n = top_n or TOP_N_RERANK
    qvec = embed_query(question)
    qclient = get_client()
    raw = _qdrant_search(qclient, qvec, k)
    hits = _rerank(question, raw, n)
    return [h for h in hits if h.score >= RERANK_SCORE_THRESHOLD]
