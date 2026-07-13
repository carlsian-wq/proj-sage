"""Chroma vector store — one collection for all projects, filtered by tag metadata."""

from __future__ import annotations

import hashlib
import os
import time
from contextlib import contextmanager
from typing import Any, Iterator

import chromadb
from chromadb.config import Settings

from sage.config import CHROMA_DIR, ensure_data_dirs
from sage.embeddings import embed_query, embed_texts

COLLECTION_NAME = "project_sage_docs"
_WRITE_LOCK = CHROMA_DIR / ".write.lock"
_LOCK_TIMEOUT_S = 600


class ChromaIndexError(RuntimeError):
    """Raised when the on-disk HNSW index is unreadable (common after OneDrive sync races)."""


@contextmanager
def _write_lock() -> Iterator[None]:
    """Exclusive lock so CLI ingest and Streamlit do not corrupt Chroma concurrently."""
    ensure_data_dirs()
    deadline = time.time() + _LOCK_TIMEOUT_S
    fh = None
    while time.time() < deadline:
        try:
            fh = open(_WRITE_LOCK, "x", encoding="utf-8")
            fh.write(str(os.getpid()))
            fh.flush()
            break
        except FileExistsError:
            time.sleep(0.5)
    else:
        raise TimeoutError(
            "Chroma is busy (another ingest or rebuild is running). "
            "Stop Project Sage or wait for the other job to finish."
        )
    try:
        yield
    finally:
        if fh:
            fh.close()
        try:
            _WRITE_LOCK.unlink(missing_ok=True)
        except OSError:
            pass


def _client() -> chromadb.PersistentClient:
    ensure_data_dirs()
    return chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )


def _wrap_chroma_err(exc: Exception) -> Exception:
    msg = str(exc).lower()
    if "hnsw" in msg or "compactor" in msg or "segment reader" in msg:
        return ChromaIndexError(
            "Chroma vector index is corrupted. Close Project Sage, then run: "
            r".venv\Scripts\python.exe scripts\rebuild_chroma.py"
        )
    return exc


def get_collection():
    client = _client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def make_chunk_id(project_tag: str, source_path: str, chunk_index: int) -> str:
    raw = f"{project_tag}::{source_path}::{chunk_index}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def make_file_id(project_tag: str, source_path: str) -> str:
    raw = f"{project_tag}::{source_path}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def delete_by_source_path(project_tag: str, source_path: str) -> int:
    """Remove all chunks for a given file under a project tag. Returns deleted count estimate."""
    with _write_lock():
        col = get_collection()
        file_key = make_file_id(project_tag, source_path)
        try:
            existing = col.get(where={"file_key": file_key})
            ids = existing.get("ids") or []
            if ids:
                col.delete(ids=ids)
            return len(ids)
        except Exception as e:
            wrapped = _wrap_chroma_err(e)
            if isinstance(wrapped, ChromaIndexError):
                raise wrapped
            try:
                existing = col.get(
                    where={
                        "$and": [
                            {"project_tag": project_tag},
                            {"source_path": source_path},
                        ]
                    }
                )
                ids = existing.get("ids") or []
                if ids:
                    col.delete(ids=ids)
                return len(ids)
            except Exception as e2:
                raise _wrap_chroma_err(e2) from e2


def delete_project(project_tag: str) -> int:
    with _write_lock():
        col = get_collection()
        try:
            existing = col.get(where={"project_tag": project_tag})
            ids = existing.get("ids") or []
            if ids:
                col.delete(ids=ids)
            return len(ids)
        except Exception as e:
            raise _wrap_chroma_err(e) from e


def upsert_chunks(
    *,
    project_tag: str,
    source_path: str,
    source_id: str,
    file_hash: str,
    mtime: float,
    chunks: list[str],
) -> int:
    """Replace all chunks for a file with new embeddings. Returns chunk count."""
    with _write_lock():
        col = get_collection()
        file_key = make_file_id(project_tag, source_path)
        try:
            existing = col.get(where={"file_key": file_key})
            ids = existing.get("ids") or []
            if ids:
                col.delete(ids=ids)
        except Exception as e:
            raise _wrap_chroma_err(e) from e

        if not chunks:
            return 0

        ids = [make_chunk_id(project_tag, source_path, i) for i in range(len(chunks))]
        embeddings = embed_texts(chunks)
        metadatas: list[dict[str, Any]] = []
        for i, _ in enumerate(chunks):
            metadatas.append(
                {
                    "project_tag": project_tag,
                    "source_path": source_path,
                    "source_id": source_id,
                    "file_key": file_key,
                    "file_hash": file_hash,
                    "mtime": float(mtime),
                    "chunk_index": i,
                }
            )

        batch = 32
        try:
            for start in range(0, len(chunks), batch):
                end = start + batch
                col.upsert(
                    ids=ids[start:end],
                    embeddings=embeddings[start:end],
                    documents=chunks[start:end],
                    metadatas=metadatas[start:end],
                )
        except Exception as e:
            raise _wrap_chroma_err(e) from e
        return len(chunks)


def query(
    query_text: str,
    *,
    project_tag: str | None = None,
    top_k: int = 6,
) -> list[dict[str, Any]]:
    """Semantic search. project_tag=None means all projects."""
    col = get_collection()
    try:
        total = col.count()
    except Exception as e:
        raise _wrap_chroma_err(e) from e
    if total == 0:
        return []

    qvec = embed_query(query_text)
    kwargs: dict[str, Any] = {
        "query_embeddings": [qvec],
        "n_results": min(top_k, max(total, 1)),
        "include": ["documents", "metadatas", "distances"],
    }
    if project_tag and project_tag != "All projects":
        kwargs["where"] = {"project_tag": project_tag}

    try:
        result = col.query(**kwargs)
    except Exception as e:
        raise _wrap_chroma_err(e) from e
    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    dists = (result.get("distances") or [[]])[0]
    ids = (result.get("ids") or [[]])[0]

    hits: list[dict[str, Any]] = []
    for i, doc in enumerate(docs):
        meta = metas[i] if i < len(metas) else {}
        dist = dists[i] if i < len(dists) else None
        score = None if dist is None else max(0.0, 1.0 - float(dist))
        text = "" if doc is None else str(doc)
        hits.append(
            {
                "id": ids[i] if i < len(ids) else None,
                "text": text,
                "metadata": meta or {},
                "score": score,
            }
        )
    return hits


def count_chunks(project_tag: str | None = None) -> int:
    col = get_collection()
    try:
        if not project_tag or project_tag == "All projects":
            return col.count()
        res = col.get(where={"project_tag": project_tag})
        return len(res.get("ids") or [])
    except Exception as e:
        raise _wrap_chroma_err(e) from e