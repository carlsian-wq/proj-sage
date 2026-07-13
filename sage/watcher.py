"""Watch registered local folders and re-ingest on file changes."""

from __future__ import annotations

import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler

# Windows + OneDrive: native FS events are unreliable; polling observer is safer.
if sys.platform == "win32":
    from watchdog.observers.polling import PollingObserver as Observer
else:
    from watchdog.observers import Observer

from sage.ingest import ingest_file
from sage.loaders import is_env_file, is_supported_file, iter_supported_files
from sage.registry import get_all_sources, update_source_ingest_meta
from sage.settings import load_settings

ProgressCb = Callable[[str], None]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_under_hidden_dir(path: Path) -> bool:
    """True if any parent directory is hidden (e.g. .git, .venv). Allows .env files."""
    for part in path.parent.parts:
        if part in (".", "..", ""):
            continue
        if part.startswith("."):
            return True
    return False


def _touch_source_meta(project_tag: str, source_id: str) -> None:
    update_source_ingest_meta(
        project_tag,
        source_id,
        last_ingested_at=_utc_now(),
    )


class _DebouncedHandler(FileSystemEventHandler):
    def __init__(
        self,
        project_tag: str,
        source_id: str,
        *,
        debounce_s: float = 1.5,
        on_event: ProgressCb | None = None,
        on_activity: Callable[[], None] | None = None,
    ):
        super().__init__()
        self.project_tag = project_tag
        self.source_id = source_id
        self.debounce_s = debounce_s
        self.on_event = on_event
        self.on_activity = on_activity
        self._pending: dict[str, float] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._worker = threading.Thread(target=self._loop, daemon=True)
        self._worker.start()

    def _schedule(self, path: str) -> None:
        p = Path(path)
        from sage.config import SUPPORTED_EXTENSIONS

        # is_supported_file requires an existing file; events may fire before stat settles
        ok = is_supported_file(p) if p.is_file() else (
            is_env_file(p) or p.suffix.lower() in SUPPORTED_EXTENSIONS
        )
        if not ok:
            return
        if _is_under_hidden_dir(p):
            return
        with self._lock:
            try:
                key = str(p.resolve())
            except OSError:
                key = str(p)
            self._pending[key] = time.time()

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._schedule(event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._schedule(event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            dest = getattr(event, "dest_path", None) or event.src_path
            self._schedule(dest)

    def _ingest_path(self, path: str) -> None:
        try:
            if self.on_event:
                self.on_event(f"Auto-ingest: {path}")
            report = ingest_file(
                Path(path),
                project_tag=self.project_tag,
                source_id=self.source_id,
                force=False,
                progress=self.on_event,
            )
            if report.files_ingested:
                _touch_source_meta(self.project_tag, self.source_id)
                if self.on_activity:
                    self.on_activity()
        except Exception as e:
            if self.on_event:
                self.on_event(f"Watcher error: {e}")

    def _loop(self) -> None:
        while not self._stop.is_set():
            time.sleep(0.5)
            now = time.time()
            ready: list[str] = []
            with self._lock:
                for path, ts in list(self._pending.items()):
                    if now - ts >= self.debounce_s:
                        ready.append(path)
                        del self._pending[path]
            for path in ready:
                self._ingest_path(path)

    def stop(self) -> None:
        self._stop.set()


class FolderWatcherService:
    """Manages watchdog observers for all registered folder sources."""

    def __init__(self, on_event: ProgressCb | None = None):
        self.on_event = on_event
        self._observer: Observer | None = None
        self._handlers: list[_DebouncedHandler] = []
        self._lock = threading.Lock()
        self._watched_count = 0
        self._last_activity: str | None = None
        self._poll_stop = threading.Event()
        self._poll_thread: threading.Thread | None = None
        self._poll_scan_s = int(load_settings().get("watcher_poll_scan_s", 120))

    @property
    def running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()

    def _note_activity(self) -> None:
        self._last_activity = _utc_now()

    def status_message(self) -> str:
        if not self.running:
            return "Stopped"
        mode = "polling observer" if sys.platform == "win32" else "native observer"
        parts = [f"Watching {self._watched_count} folder source(s) ({mode})"]
        parts.append(f"scan every {self._poll_scan_s}s")
        if self._last_activity:
            parts.append(f"last activity {self._last_activity}")
        return " · ".join(parts)

    def _poll_scan(self) -> None:
        """Fallback for OneDrive/cloud-synced folders that miss FS events."""
        for tag, source in get_all_sources():
            if source.get("type") != "folder":
                continue
            root = Path(source["path"])
            if not root.is_dir():
                continue
            source_id = source.get("id", "")
            for fpath in iter_supported_files(root):
                try:
                    report = ingest_file(
                        fpath,
                        project_tag=tag,
                        source_id=source_id,
                        force=False,
                        progress=None,
                    )
                    if report.files_ingested:
                        _touch_source_meta(tag, source_id)
                        self._note_activity()
                        if self.on_event:
                            self.on_event(f"Poll-ingest: {fpath}")
                except Exception as e:
                    if self.on_event:
                        self.on_event(f"Poll scan error ({fpath.name}): {e}")

    def _poll_loop(self) -> None:
        while not self._poll_stop.is_set():
            if self._poll_stop.wait(self._poll_scan_s):
                break
            if not self.running:
                continue
            self._poll_scan()

    def start(self) -> str:
        with self._lock:
            if self.running:
                return self.status_message()
            settings = load_settings()
            self._poll_scan_s = max(30, int(settings.get("watcher_poll_scan_s", 120)))

            observer = Observer()
            handlers: list[_DebouncedHandler] = []
            watched = 0
            for tag, source in get_all_sources():
                if source.get("type") != "folder":
                    continue
                path = Path(source["path"])
                if not path.is_dir():
                    continue
                handler = _DebouncedHandler(
                    tag,
                    source.get("id", ""),
                    on_event=self.on_event,
                    on_activity=self._note_activity,
                )
                observer.schedule(handler, str(path), recursive=True)
                handlers.append(handler)
                watched += 1
            if watched == 0:
                return "No local folders to watch. Add a folder source first."
            observer.start()
            self._observer = observer
            self._handlers = handlers
            self._watched_count = watched

            self._poll_stop.clear()
            self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._poll_thread.start()
            return self.status_message()

    def stop(self) -> str:
        with self._lock:
            if not self._observer:
                return "Watcher not running."
            self._poll_stop.set()
            if self._poll_thread:
                self._poll_thread.join(timeout=2)
            self._poll_thread = None
            self._observer.stop()
            self._observer.join(timeout=5)
            for h in self._handlers:
                h.stop()
            self._observer = None
            self._handlers = []
            self._watched_count = 0
            return "Watcher stopped."

    def restart(self) -> str:
        self.stop()
        return self.start()


# Process-wide singleton for Streamlit sessions
_service: FolderWatcherService | None = None
_service_lock = threading.Lock()


def get_watcher(on_event: ProgressCb | None = None) -> FolderWatcherService:
    global _service
    with _service_lock:
        if _service is None:
            _service = FolderWatcherService(on_event=on_event)
        elif on_event is not None:
            _service.on_event = on_event
        return _service