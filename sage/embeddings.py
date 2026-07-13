"""Ollama embedding client (nomic-embed-text)."""

from __future__ import annotations

from typing import Sequence

import ollama

from sage.config import EMBED_MODEL, OLLAMA_HOST

# Ollama accepts batched input; one round-trip per batch is much faster than per-chunk.
EMBED_BATCH_SIZE = 32


def get_client() -> ollama.Client:
    return ollama.Client(host=OLLAMA_HOST)


def _extract_embeddings(resp) -> list[list[float]]:
    emb = getattr(resp, "embeddings", None)
    if emb is None and isinstance(resp, dict):
        emb = resp.get("embeddings")
    if emb is not None:
        return [list(v) for v in emb]
    single = getattr(resp, "embedding", None) or (
        resp.get("embedding") if isinstance(resp, dict) else None
    )
    if single is not None:
        return [list(single)]
    raise RuntimeError(f"Unexpected embed response shape: {resp!r}")


def embed_texts(texts: Sequence[str], *, model: str = EMBED_MODEL) -> list[list[float]]:
    """Embed texts via Ollama. Batches requests for throughput."""
    if not texts:
        return []
    client = get_client()
    cleaned: list[str] = []
    for text in texts:
        c = text.replace("\x00", " ").strip()
        cleaned.append(c if c else " ")

    vectors: list[list[float]] = []
    for start in range(0, len(cleaned), EMBED_BATCH_SIZE):
        batch = cleaned[start : start + EMBED_BATCH_SIZE]
        resp = client.embed(model=model, input=batch)
        vectors.extend(_extract_embeddings(resp))
    if len(vectors) != len(cleaned):
        raise RuntimeError(
            f"Embedding count mismatch: got {len(vectors)} for {len(cleaned)} inputs"
        )
    return vectors


def embed_query(text: str, *, model: str = EMBED_MODEL) -> list[float]:
    vecs = embed_texts([text], model=model)
    return vecs[0]