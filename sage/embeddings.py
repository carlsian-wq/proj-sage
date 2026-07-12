"""Ollama embedding client (nomic-embed-text)."""

from __future__ import annotations

from typing import Sequence

import ollama

from sage.config import EMBED_MODEL, OLLAMA_HOST


def get_client() -> ollama.Client:
    return ollama.Client(host=OLLAMA_HOST)


def embed_texts(texts: Sequence[str], *, model: str = EMBED_MODEL) -> list[list[float]]:
    """Embed a batch of texts. Returns one vector per input string."""
    if not texts:
        return []
    client = get_client()
    vectors: list[list[float]] = []
    # nomic via ollama embed API — one call per text is reliable across versions
    for text in texts:
        cleaned = text.replace("\x00", " ").strip()
        if not cleaned:
            cleaned = " "
        resp = client.embed(model=model, input=cleaned)
        # ollama python SDK: resp.embeddings is list[list[float]] for batch input
        emb = getattr(resp, "embeddings", None)
        if emb is None and isinstance(resp, dict):
            emb = resp.get("embeddings")
        if emb and isinstance(emb[0], (list, tuple)):
            vectors.append(list(emb[0]))
        elif emb:
            vectors.append(list(emb))
        else:
            # older shape: embedding singular
            single = getattr(resp, "embedding", None) or (resp.get("embedding") if isinstance(resp, dict) else None)
            if single is None:
                raise RuntimeError(f"Unexpected embed response shape: {resp!r}")
            vectors.append(list(single))
    return vectors


def embed_query(text: str, *, model: str = EMBED_MODEL) -> list[float]:
    vecs = embed_texts([text], model=model)
    return vecs[0]
