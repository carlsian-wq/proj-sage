"""Load text from supported documentation file types."""

from __future__ import annotations

import csv
import json
import os
from io import StringIO
from pathlib import Path

from sage.config import SKIP_DIR_NAMES, SUPPORTED_EXTENSIONS

_SKIP_LOWER = {n.lower() for n in SKIP_DIR_NAMES}


def is_supported_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def iter_supported_files(root: Path) -> list[Path]:
    """Walk a folder and return supported files, skipping noisy directories."""
    root = root.resolve()
    found: list[Path] = []
    if not root.is_dir():
        return found

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skip dirs and hidden folders in-place
        dirnames[:] = [
            d
            for d in dirnames
            if d.lower() not in _SKIP_LOWER and not d.startswith(".")
        ]
        for name in filenames:
            p = Path(dirpath) / name
            if is_supported_file(p):
                found.append(p)
    return sorted(found)


def load_file_text(path: Path) -> str:
    """Extract plain text from a supported file."""
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".markdown"}:
        return _read_text(path)
    if suffix == ".pdf":
        return _load_pdf(path)
    if suffix == ".csv":
        return _load_csv(path)
    if suffix == ".json":
        return _load_json(path)
    if suffix == ".docx":
        return _load_docx(path)
    if suffix == ".doc":
        return _load_doc_legacy(path)
    raise ValueError(f"Unsupported file type: {suffix}")


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _load_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts: list[str] = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            parts.append(f"--- Page {i + 1} ---\n{text}")
    return "\n\n".join(parts)


def _load_csv(path: Path) -> str:
    text = _read_text(path)
    reader = csv.reader(StringIO(text))
    rows = list(reader)
    if not rows:
        return ""
    lines = [" | ".join(cell.strip() for cell in row) for row in rows]
    return "\n".join(lines)


def _load_json(path: Path) -> str:
    text = _read_text(path)
    try:
        data = json.loads(text)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        return text


def _load_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    paras = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text and c.text.strip()]
            if cells:
                paras.append(" | ".join(cells))
    return "\n\n".join(paras)


def _load_doc_legacy(path: Path) -> str:
    """Best-effort for old .doc binary format."""
    try:
        raw = path.read_bytes()
        chunks: list[str] = []
        current: list[str] = []
        for b in raw:
            if 32 <= b < 127 or b in (9, 10, 13):
                current.append(chr(b))
            else:
                if len(current) >= 40:
                    chunks.append("".join(current))
                current = []
        if len(current) >= 40:
            chunks.append("".join(current))
        text = "\n".join(c.strip() for c in chunks if c.strip())
        if len(text) < 50:
            return (
                f"[Limited extraction from legacy .doc: {path.name}. "
                "Prefer converting to .docx or .pdf for better results.]"
            )
        return text
    except OSError as e:
        return f"[Could not read .doc file {path.name}: {e}]"
