"""Watch registered local folders and re-ingest on file changes."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from sage.ingest import ingest_file
from sage.loaders import is_env_file, is_supported_file
from sage.registry import get_all_sources

ProgressCb = Callable[[str], None]


def _is_under_hidden_dir(path: Path) -> bool:
    """True if any parent directory is hidden (e.g. .git, .venv). Allows .env files."""
    for part in path.parent.parts:
        if part in (".", "..", ""):
            continue
        if part.startswith("."):
            return True
    return False


class _DebouncedHandler(FileSystemEventHandler):
    def __init__(
        self,
        project_tag: str,
        source_id: str,
        *,
        debounce_s: float = 1.5,
        on_event: ProgressCb | None = None,
    ):
        super().__init__()
        self.project_tag = project_tag
        self.source_id = source_id
        self.debounce_s = debounce_s
        self.on_event = on_event
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
                try:
                    if self.on_event:
                        self.on_event(f"Auto-ingest: {path}")
                    ingest_file(
                        Path(path),
                        project_tag=self.project_tag,
                        source_id=self.source_id,
                        force=False,
                        progress=self.on_event,
                    )
                except Exception as e:
                    if self.on_event:
                        self.on_event(f"Watcher error: {e}")

    def stop(self) -> None:
        self._stop.set()


class FolderWatcherService:
    """Manages watchdog observers for all registered folder sources."""

    def __init__(self, on_event: ProgressCb | None = None):
        self.on_event = on_event
        self._observer: Observer | None = None
        self._handlers: list[_DebouncedHandler] = []
        self._lock = threading.Lock()

    @property
    def running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()

    def start(self) -> str:
        with self._lock:
            if self.running:
                return "Watcher already running."
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
                )
                observer.schedule(handler, str(path), recursive=True)
                handlers.append(handler)
                watched += 1
            if watched == 0:
                return "No local folders to watch. Add a folder source first."
            observer.start()
            self._observer = observer
            self._handlers = handlers
            return f"Watching {watched} folder source(s)."

    def stop(self) -> str:
        with self._lock:
            if not self._observer:
                return "Watcher not running."
            self._observer.stop()
            self._observer.join(timeout=5)
            for h in self._handlers:
                h.stop()
            self._observer = None
            self._handlers = []
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
