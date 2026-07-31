"""Hybrid re-ranking: semantic hits + lexical/path boosts for technical queries.

Pure embedding search often ranks "nearby" prose (e.g. regime / 1h trend) above the
chunk that literally documents the asked flag or config key (e.g. --interval,
poll_interval_sec). This module re-orders candidate hits using exact-ish token
overlap so natural questions about CLIs and config still surface the right docs.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# Common English words that rarely disambiguate technical docs.
_STOPWORDS = frozenset(
    {
        "about",
        "after",
        "again",
        "also",
        "been",
        "before",
        "being",
        "between",
        "both",
        "change",
        "does",
        "doing",
        "during",
        "each",
        "from",
        "have",
        "having",
        "here",
        "into",
        "just",
        "like",
        "make",
        "more",
        "most",
        "need",
        "only",
        "other",
        "over",
        "please",
        "same",
        "should",
        "some",
        "such",
        "than",
        "that",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "under",
        "using",
        "very",
        "want",
        "what",
        "when",
        "where",
        "which",
        "while",
        "with",
        "would",
        "your",
        "how",
        "the",
        "and",
        "for",
        "are",
        "was",
        "were",
        "can",
        "you",
        "our",
        "any",
        "all",
        "not",
        "but",
        "out",
        "get",
        "set",
        "use",
        "run",
        "docs",
        "file",
        "code",
        "help",
    }
)

# Prefer these as high-signal tokens when present in the query.
_FILE_EXT = r"(?:py|md|markdown|yaml|yml|json|jsonl|toml|txt|ps1|sh|cfg|ini|env)"
_RE_FLAG = re.compile(r"--[a-zA-Z][\w-]*")
_RE_FILE = re.compile(rf"\b[\w.-]+\.{_FILE_EXT}\b", re.IGNORECASE)
_RE_SNAKE = re.compile(r"\b[a-zA-Z][a-zA-Z0-9]*(?:_[a-zA-Z0-9]+)+\b")
_RE_WORD = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]{2,}")


def extract_query_terms(question: str) -> list[str]:
    """Pull identifiers, flags, filenames, and content words from a natural question."""
    q = (question or "").strip()
    if not q:
        return []

    terms: list[str] = []
    seen: set[str] = set()

    def _add(raw: str, *, min_len: int = 2) -> None:
        t = raw.strip().lower()
        if len(t) < min_len or t in seen or t in _STOPWORDS:
            return
        seen.add(t)
        terms.append(t)

    for m in _RE_FLAG.finditer(q):
        _add(m.group(0), min_len=3)
    for m in _RE_FILE.finditer(q):
        _add(m.group(0), min_len=4)
        # Also add stem without extension (live_engine from live_engine.py)
        stem = Path(m.group(0)).stem.lower()
        _add(stem, min_len=3)
    for m in _RE_SNAKE.finditer(q):
        _add(m.group(0), min_len=3)
    for m in _RE_WORD.finditer(q):
        _add(m.group(0), min_len=4)

    return terms


def _path_blob(source_path: str) -> str:
    if not source_path:
        return ""
    p = Path(source_path)
    # Full path + basename + stem for matching live_engine / RUNNING.md
    parts = [source_path, p.name, p.stem]
    return " ".join(parts).lower()


def lexical_score(
    text: str,
    source_path: str,
    terms: list[str],
) -> float:
    """Score how well a chunk matches extracted query terms (higher is better)."""
    if not terms:
        return 0.0

    body = (text or "").lower()
    path_l = _path_blob(source_path)
    score = 0.0
    hits = 0

    for term in terms:
        in_body = term in body
        in_path = term in path_l
        if not in_body and not in_path:
            continue
        hits += 1
        # Base hit
        score += 1.0
        # Technical identifiers are high signal
        if term.startswith("--") or "_" in term or "." in term:
            score += 0.75
        if in_path:
            score += 0.9
        # Whole-word-ish bonus (avoid matching "interval" inside unrelated noise less)
        if in_body:
            if re.search(rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])", body):
                score += 0.35

    coverage = hits / max(len(terms), 1)
    score += coverage * 2.0
    return score


def combined_score(
    semantic: float | None,
    lexical: float,
    *,
    lexical_weight: float = 0.14,
) -> float:
    """Blend cosine-similarity-style semantic score with lexical boosts."""
    sem = float(semantic) if isinstance(semantic, (int, float)) else 0.0
    # Cap lexical contribution so pure keyword spam cannot fully dominate
    lex_component = min(lexical, 12.0) * lexical_weight
    return sem + lex_component


def rerank_hits(
    hits: list[dict[str, Any]],
    question: str,
    *,
    top_k: int,
    lexical_weight: float = 0.14,
) -> list[dict[str, Any]]:
    """Re-order retrieval hits; attach lexical/combined scores; return top_k."""
    if not hits:
        return []

    terms = extract_query_terms(question)
    ranked: list[dict[str, Any]] = []
    for hit in hits:
        meta = hit.get("metadata") or {}
        path = str(meta.get("source_path") or "")
        text = hit.get("text") or ""
        if text is None:
            text = ""
        else:
            text = str(text)
        sem = hit.get("score")
        lex = lexical_score(text, path, terms)
        comb = combined_score(sem if isinstance(sem, (int, float)) else None, lex, lexical_weight=lexical_weight)
        enriched = dict(hit)
        enriched["semantic_score"] = sem
        enriched["lexical_score"] = lex
        enriched["score"] = comb
        enriched["query_terms"] = terms
        ranked.append(enriched)

    ranked.sort(
        key=lambda h: (
            float(h.get("score") or 0.0),
            float(h.get("lexical_score") or 0.0),
            float(h.get("semantic_score") or 0.0) if isinstance(h.get("semantic_score"), (int, float)) else 0.0,
        ),
        reverse=True,
    )
    return ranked[: max(1, top_k)]
