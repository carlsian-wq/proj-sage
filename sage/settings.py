"""Persisted UI settings (data/settings.json)."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from sage.config import DATA_DIR, ensure_data_dirs

SETTINGS_PATH = DATA_DIR / "settings.json"
_lock = threading.RLock()

_DEFAULTS: dict[str, Any] = {
    "watcher_auto_start": True,
    "watcher_poll_scan_s": 120,
    # auto → Windows: poll-only (safe); other OS: native FS observer
    # none | native | polling | auto
    # Avoid "polling" on large OneDrive trees — it walks every file under venv/ too.
    "watcher_fs_observer": "auto",
}


def load_settings() -> dict[str, Any]:
    ensure_data_dirs()
    with _lock:
        if not SETTINGS_PATH.exists():
            return dict(_DEFAULTS)
        try:
            with SETTINGS_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return dict(_DEFAULTS)
        out = dict(_DEFAULTS)
        out.update(data)
        return out


def save_settings(settings: dict[str, Any]) -> None:
    ensure_data_dirs()
    merged = dict(_DEFAULTS)
    merged.update(settings)
    with _lock:
        tmp = SETTINGS_PATH.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        tmp.replace(SETTINGS_PATH)


def update_settings(**kwargs: Any) -> dict[str, Any]:
    current = load_settings()
    current.update(kwargs)
    save_settings(current)
    return current