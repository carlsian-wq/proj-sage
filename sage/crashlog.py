"""Process-wide crash / fault logging for the Streamlit server."""

from __future__ import annotations

import atexit
import faulthandler
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from sage.config import DATA_DIR

_LOG_PATH = DATA_DIR / "crash.log"
_FAULT_PATH = DATA_DIR / "faulthandler.log"
_INSTALLED = False


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(text)
        if not text.endswith("\n"):
            fh.write("\n")


def _log_unhandled(exc_type, exc, tb) -> None:
    lines = [
        f"\n--- {_ts()} unhandled exception ---",
        "".join(traceback.format_exception(exc_type, exc, tb)),
    ]
    _append(_LOG_PATH, "".join(lines))
    sys.__excepthook__(exc_type, exc, tb)


def _log_exit() -> None:
    _append(_LOG_PATH, f"--- {_ts()} process exit (atexit) ---")


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        fault_fh = _FAULT_PATH.open("a", encoding="utf-8")
        faulthandler.enable(file=fault_fh, all_threads=True)
    except OSError:
        faulthandler.enable(all_threads=True)
    sys.excepthook = _log_unhandled
    atexit.register(_log_exit)
    _append(_LOG_PATH, f"--- {_ts()} Project Sage crash logging enabled ---")
    _INSTALLED = True