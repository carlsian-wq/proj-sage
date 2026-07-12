"""Project tags and source registry (JSON-backed)."""

from __future__ import annotations

import json
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sage.config import REGISTRY_PATH, ensure_data_dirs

_lock = threading.RLock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_registry() -> dict[str, Any]:
    return {"version": 1, "projects": {}}


def load_registry() -> dict[str, Any]:
    ensure_data_dirs()
    with _lock:
        if not REGISTRY_PATH.exists():
            reg = _empty_registry()
            _write_unlocked(reg)
            return reg
        with REGISTRY_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)


def save_registry(registry: dict[str, Any]) -> None:
    ensure_data_dirs()
    with _lock:
        _write_unlocked(registry)


def _write_unlocked(registry: dict[str, Any]) -> None:
    tmp = REGISTRY_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    tmp.replace(REGISTRY_PATH)


def list_projects(registry: dict[str, Any] | None = None) -> list[str]:
    reg = registry if registry is not None else load_registry()
    return sorted(reg.get("projects", {}).keys(), key=str.lower)


def ensure_project(tag: str, registry: dict[str, Any] | None = None) -> dict[str, Any]:
    tag = tag.strip()
    if not tag:
        raise ValueError("Project tag cannot be empty.")
    reg = registry if registry is not None else load_registry()
    if tag not in reg["projects"]:
        reg["projects"][tag] = {
            "created_at": _utc_now(),
            "sources": [],
        }
        save_registry(reg)
    return reg


def delete_project(tag: str) -> dict[str, Any]:
    reg = load_registry()
    reg["projects"].pop(tag, None)
    save_registry(reg)
    return reg


def add_folder_source(tag: str, folder_path: str) -> dict[str, Any]:
    path = Path(folder_path).expanduser().resolve()
    if not path.is_dir():
        raise ValueError(f"Not a directory: {path}")

    reg = ensure_project(tag)
    sources = reg["projects"][tag]["sources"]
    path_str = str(path)

    for src in sources:
        if src.get("type") == "folder" and Path(src["path"]).resolve() == path:
            return reg  # already registered

    sources.append(
        {
            "id": str(uuid.uuid4()),
            "type": "folder",
            "path": path_str,
            "added_at": _utc_now(),
            "last_ingested_at": None,
            "file_count": 0,
        }
    )
    save_registry(reg)
    return reg


def add_upload_source(tag: str, dest_path: Path, original_name: str) -> dict[str, Any]:
    reg = ensure_project(tag)
    sources = reg["projects"][tag]["sources"]
    dest = dest_path.resolve()
    path_str = str(dest)

    for src in sources:
        if src.get("type") == "file" and Path(src["path"]).resolve() == dest:
            return reg

    sources.append(
        {
            "id": str(uuid.uuid4()),
            "type": "file",
            "path": path_str,
            "original_name": original_name,
            "added_at": _utc_now(),
            "last_ingested_at": None,
            "file_count": 1,
        }
    )
    save_registry(reg)
    return reg


def remove_source(tag: str, source_id: str) -> dict[str, Any]:
    reg = load_registry()
    proj = reg["projects"].get(tag)
    if not proj:
        return reg
    proj["sources"] = [s for s in proj["sources"] if s.get("id") != source_id]
    save_registry(reg)
    return reg


def update_source_ingest_meta(
    tag: str,
    source_id: str,
    *,
    file_count: int | None = None,
    last_ingested_at: str | None = None,
) -> None:
    reg = load_registry()
    proj = reg["projects"].get(tag)
    if not proj:
        return
    for src in proj["sources"]:
        if src.get("id") == source_id:
            if file_count is not None:
                src["file_count"] = file_count
            if last_ingested_at is not None:
                src["last_ingested_at"] = last_ingested_at
            break
    save_registry(reg)


def get_all_sources(registry: dict[str, Any] | None = None) -> list[tuple[str, dict[str, Any]]]:
    """Return list of (project_tag, source_dict)."""
    reg = registry if registry is not None else load_registry()
    out: list[tuple[str, dict[str, Any]]] = []
    for tag, proj in reg.get("projects", {}).items():
        for src in proj.get("sources", []):
            out.append((tag, deepcopy(src)))
    return out


def get_project_sources(tag: str) -> list[dict[str, Any]]:
    reg = load_registry()
    proj = reg["projects"].get(tag, {})
    return deepcopy(proj.get("sources", []))
