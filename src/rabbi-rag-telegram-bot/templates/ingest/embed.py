"""Cohere embed-v4.0 batching + throttling for trial 100K tokens/min limit."""
from __future__ import annotations

import logging
import time
from typing import Iterable

import cohere
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import COHERE_API_KEY, EMBED_MODEL

log = logging.getLogger("embed")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

BATCH_SIZE = 32           # Cohere trial: 100K tokens/min — ~500 tokens/chunk × 32 = ~16K tokens/batch
SLEEP_BETWEEN_BATCHES = 12.0


def _client() -> cohere.ClientV2:
    if not COHERE_API_KEY:
        raise RuntimeError("COHERE_API_KEY חסר ב-.env")
    return cohere.ClientV2(api_key=COHERE_API_KEY)


@retry(
    reraise=True,
    stop=stop_after_attempt(8),
    wait=wait_exponential(multiplier=4, min=15, max=120),
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(log, logging.WARNING),
)
def _embed_batch(co: cohere.ClientV2, texts: list[str], input_type: str) -> list[list[float]]:
    resp = co.embed(
        model=EMBED_MODEL,
        texts=texts,
        input_type=input_type,
        embedding_types=["float"],
    )
    return [list(e) for e in resp.embeddings.float]


def embed_documents(texts: Iterable[str], *, progress_cb=None) -> list[list[float]]:
    co = _client()
    items = list(texts)
    out: list[list[float]] = []
    total_batches = (len(items) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i : i + BATCH_SIZE]
        batch_idx = i // BATCH_SIZE + 1
        log.info(f"  embed batch {batch_idx}/{total_batches} ({len(batch)} items)")
        vecs = _embed_batch(co, batch, "search_document")
        out.extend(vecs)
        if progress_cb:
            progress_cb(len(out), len(items))
        if i + BATCH_SIZE < len(items):
            time.sleep(SLEEP_BETWEEN_BATCHES)
    return out


def embed_query(text: str) -> list[float]:
    co = _client()
    return _embed_batch(co, [text], "search_query")[0]
