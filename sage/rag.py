"""RAG: retrieve chunks + generate answer with Ollama qwen2.5:7b."""

from __future__ import annotations

from typing import Any

import ollama

from sage.config import (
    CANDIDATE_MULTIPLIER,
    LEXICAL_WEIGHT,
    LLM_MODEL,
    MAX_CANDIDATES,
    MIN_CANDIDATES,
    OLLAMA_HOST,
    TOP_K,
)
from sage.rerank import rerank_hits
from sage import vectorstore

SYSTEM_PROMPT = """You are Project Sage, an intelligent documentation search assistant.
Answer the user's question using ONLY the provided source excerpts from project documentation.
Rules:
- Be clear, structured, and practical.
- Use ONLY facts that appear in the source excerpts. Do not invent CLI flags, config keys,
  file names, defaults, ports, or shell commands that are not written in the excerpts.
- If the excerpts are insufficient or off-topic, say what is missing instead of guessing.
- Do not substitute a related concept for the asked one. Example: market "regime" / bullish
  vs bearish is NOT the same as a poll/loop "interval" or startup timing — only answer
  interval questions with interval/poll keys and flags actually present in the excerpts.
- Prefer exact names from the sources (e.g. --interval, poll_interval_sec, file paths).
- Cite sources inline like [1], [2] matching the excerpt numbers.
- Prefer short paragraphs and bullet lists when helpful.
- If multiple projects appear, note which project each point comes from.
"""


def _hit_text(hit: dict[str, Any]) -> str:
    """Chroma may return document=None; never call .strip() on None."""
    text = hit.get("text")
    if text is None:
        return ""
    return str(text).strip()


def _format_context(hits: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for i, hit in enumerate(hits, start=1):
        meta = hit.get("metadata") or {}
        tag = meta.get("project_tag") or "?"
        path = meta.get("source_path") or "?"
        score = hit.get("score")
        score_s = f"{score:.2f}" if isinstance(score, (int, float)) else "n/a"
        body = _hit_text(hit) or "(empty excerpt)"
        parts.append(f"[{i}] project={tag} | score={score_s} | file={path}\n{body}")
    return "\n\n".join(parts)


def _candidate_k(top_k: int) -> int:
    """How many semantic neighbors to pull before hybrid re-rank."""
    return min(MAX_CANDIDATES, max(MIN_CANDIDATES, int(top_k) * CANDIDATE_MULTIPLIER))


def retrieve_hits(
    question: str,
    *,
    project_tag: str | None = None,
    top_k: int = TOP_K,
) -> list[dict[str, Any]]:
    """Semantic over-fetch + hybrid lexical re-rank → top_k hits."""
    raw = vectorstore.query(
        question,
        project_tag=project_tag,
        top_k=_candidate_k(top_k),
    )
    return rerank_hits(
        raw,
        question,
        top_k=top_k,
        lexical_weight=LEXICAL_WEIGHT,
    )


def search_and_answer(
    question: str,
    *,
    project_tag: str | None = None,
    top_k: int = TOP_K,
) -> dict[str, Any]:
    """Run retrieval + LLM generation. Returns answer, hits, and errors."""
    question = (question or "").strip()
    if not question:
        return {"answer": "", "hits": [], "error": "Empty question."}

    try:
        hits = retrieve_hits(question, project_tag=project_tag, top_k=top_k)
    except vectorstore.ChromaIndexError as e:
        return {"answer": "", "hits": [], "error": str(e)}
    except Exception as e:
        msg = str(e)
        hint = ""
        low = msg.lower()
        if "ollama" in low or "connection" in low or "embed" in low:
            hint = " Is Ollama running with nomic-embed-text?"
        elif "finding id" in low or "executing plan" in low:
            hint = (
                " Chroma index looks corrupted — close Project Sage and run "
                r".\.venv\Scripts\python.exe scripts\rebuild_chroma.py"
            )
        return {
            "answer": "",
            "hits": [],
            "error": f"Retrieval failed: {msg}.{hint}",
        }

    if not hits:
        return {
            "answer": (
                "No indexed documentation matched your query. "
                "Add a project source and run ingest from the sidebar."
            ),
            "hits": [],
            "error": None,
        }

    context = _format_context(hits)
    user_msg = (
        f"Question: {question}\n\n"
        f"Source excerpts:\n{context}\n\n"
        "Write a helpful answer with citations. Ground every claim in the excerpts. "
        "If the excerpts discuss a different topic than the question, say so and do not "
        "present the related topic as the answer."
    )

    try:
        client = ollama.Client(host=OLLAMA_HOST)
        resp = client.chat(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            options={"temperature": 0.1},
        )
        # SDK: resp.message.content
        message = getattr(resp, "message", None)
        if message is not None:
            answer = getattr(message, "content", None) or ""
        elif isinstance(resp, dict):
            answer = (resp.get("message") or {}).get("content", "")
        else:
            answer = str(resp)
    except Exception as e:
        return {
            "answer": "",
            "hits": hits,
            "error": f"LLM generation failed: {e}. Is Ollama running with model '{LLM_MODEL}'?",
        }

    return {"answer": (answer or "").strip(), "hits": hits, "error": None}
