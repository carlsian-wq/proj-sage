"""RAG: retrieve chunks + generate answer with Ollama qwen2.5:7b."""

from __future__ import annotations

from typing import Any

import ollama

from sage.config import LLM_MODEL, OLLAMA_HOST, TOP_K
from sage import vectorstore

SYSTEM_PROMPT = """You are Project Sage, an intelligent documentation search assistant.
Answer the user's question using ONLY the provided source excerpts from project documentation.
Rules:
- Be clear, structured, and practical.
- If the sources are insufficient, say what is missing instead of inventing details.
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
        hits = vectorstore.query(question, project_tag=project_tag, top_k=top_k)
    except Exception as e:
        return {
            "answer": "",
            "hits": [],
            "error": f"Retrieval failed: {e}. Is Ollama running with nomic-embed-text?",
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
        "Write a helpful answer with citations."
    )

    try:
        client = ollama.Client(host=OLLAMA_HOST)
        resp = client.chat(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            options={"temperature": 0.2},
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
