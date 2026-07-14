"""Ingest pipeline: discover files, hash, load, chunk, embed, upsert."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from sage.chunking import chunk_text
from sage.config import UPLOADS_DIR, ensure_data_dirs
from sage.loaders import is_supported_file, iter_supported_files, load_file_text
from sage.registry import (
    get_all_sources,
    get_project_sources,
    load_registry,
    update_source_ingest_meta,
)
from sage import vectorstore

ProgressCb = Callable[[str], None]


@dataclass
class IngestReport:
    files_seen: int = 0
    files_ingested: int = 0
    files_skipped_unchanged: int = 0
    files_failed: int = 0
    chunks_written: int = 0
    errors: list[str] = field(default_factory=list)

    def merge(self, other: "IngestReport") -> "IngestReport":
        self.files_seen += other.files_seen
        self.files_ingested += other.files_ingested
        self.files_skipped_unchanged += other.files_skipped_unchanged
        self.files_failed += other.files_failed
        self.chunks_written += other.chunks_written
        self.errors.extend(other.errors)
        return self

    def summary(self) -> str:
        lines = [
            f"Seen: {self.files_seen}",
            f"Ingested: {self.files_ingested}",
            f"Unchanged (skipped): {self.files_skipped_unchanged}",
            f"Failed: {self.files_failed}",
            f"Chunks written: {self.chunks_written}",
        ]
        if self.errors:
            lines.append("Errors:")
            lines.extend(f"  - {e}" for e in self.errors[:20])
            if len(self.errors) > 20:
                lines.append(f"  … and {len(self.errors) - 20} more")
        return "\n".join(lines)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _known_file_hash(project_tag: str, source_path: str) -> str | None:
    """Read stored file_hash from any existing chunk metadata."""
    try:
        return vectorstore.get_stored_file_hash(project_tag, source_path)
    except Exception:
        return None


def ingest_file(
    path: Path,
    *,
    project_tag: str,
    source_id: str,
    force: bool = False,
    progress: ProgressCb | None = None,
) -> IngestReport:
    report = IngestReport()
    path = path.resolve()
    report.files_seen = 1

    if not is_supported_file(path):
        report.files_failed = 1
        report.errors.append(f"Unsupported: {path}")
        return report

    path_str = str(path)
    try:
        current_hash = file_sha256(path)
        if not force:
            prev = _known_file_hash(project_tag, path_str)
            if prev and prev == current_hash:
                report.files_skipped_unchanged = 1
                if progress:
                    progress(f"Unchanged: {path.name}")
                return report

        if progress:
            progress(f"Loading: {path.name}")
        text = load_file_text(path)
        chunks = chunk_text(text)
        if progress:
            progress(f"Embedding {len(chunks)} chunk(s): {path.name}")
        n = vectorstore.upsert_chunks(
            project_tag=project_tag,
            source_path=path_str,
            source_id=source_id,
            file_hash=current_hash,
            mtime=path.stat().st_mtime,
            chunks=chunks,
        )
        report.files_ingested = 1
        report.chunks_written = n
    except Exception as e:
        report.files_failed = 1
        report.errors.append(f"{path.name}: {e}")
        if progress:
            progress(f"Failed: {path.name} — {e}")
    return report


def _files_for_source(source: dict) -> list[Path]:
    p = Path(source["path"])
    if source.get("type") == "folder":
        if not p.is_dir():
            return []
        return iter_supported_files(p)
    if p.is_file():
        return [p]
    return []


def ingest_source(
    project_tag: str,
    source: dict,
    *,
    force: bool = False,
    progress: ProgressCb | None = None,
) -> IngestReport:
    report = IngestReport()
    source_id = source.get("id", "")
    files = _files_for_source(source)
    if not files and source.get("type") == "folder" and not Path(source["path"]).is_dir():
        report.errors.append(f"Folder missing: {source['path']}")
        return report

    for fpath in files:
        r = ingest_file(
            fpath,
            project_tag=project_tag,
            source_id=source_id,
            force=force,
            progress=progress,
        )
        report.merge(r)

    update_source_ingest_meta(
        project_tag,
        source_id,
        file_count=len(files),
        last_ingested_at=datetime.now(timezone.utc).isoformat(),
    )
    return report


def ingest_project(
    project_tag: str,
    *,
    force: bool = False,
    progress: ProgressCb | None = None,
) -> IngestReport:
    report = IngestReport()
    for source in get_project_sources(project_tag):
        if progress:
            progress(f"Source: {source.get('path')}")
        report.merge(ingest_source(project_tag, source, force=force, progress=progress))
    return report


def ingest_all(
    *,
    force: bool = False,
    progress: ProgressCb | None = None,
) -> IngestReport:
    report = IngestReport()
    for tag, source in get_all_sources():
        if progress:
            progress(f"[{tag}] {source.get('path')}")
        report.merge(ingest_source(tag, source, force=force, progress=progress))
    return report


def save_upload(project_tag: str, uploaded_name: str, data: bytes) -> Path:
    """Persist an uploaded file under data/uploads/<tag>/."""
    ensure_data_dirs()
    safe_tag = "".join(c if c.isalnum() or c in "-_ " else "_" for c in project_tag).strip() or "untagged"
    dest_dir = UPLOADS_DIR / safe_tag
    dest_dir.mkdir(parents=True, exist_ok=True)
    # Avoid path traversal
    name = Path(uploaded_name).name
    dest = dest_dir / name
    # If collision, add numeric suffix
    if dest.exists():
        stem, suf = dest.stem, dest.suffix
        i = 1
        while dest.exists():
            dest = dest_dir / f"{stem}_{i}{suf}"
            i += 1
    dest.write_bytes(data)
    return dest


def list_registry_snapshot() -> dict:
    return load_registry()
