#!/usr/bin/env python3
"""Backup corrupted Chroma data and re-ingest all registered projects."""

from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sage.config import CHROMA_DIR, ensure_data_dirs
from sage.ingest import ingest_all


def main() -> int:
    ensure_data_dirs()
    if not CHROMA_DIR.exists():
        print("No chroma directory — running full ingest.")
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup = CHROMA_DIR.parent / f"chroma_backup_{stamp}"
        print(f"Backing up {CHROMA_DIR} -> {backup}")
        shutil.move(str(CHROMA_DIR), str(backup))
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    print("Re-ingesting all registered projects (force=True)…")
    report = ingest_all(force=True, progress=print)
    print(report.summary())
    return 0 if report.files_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())