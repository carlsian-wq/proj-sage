"""Watch registered local folders and re-ingest on file changes."""

from __future__ import annotations

import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal

from watchdog.events import FileSystemEvent, FileSystemEventHandler

from sage.ingest import ingest_file
from sage.vectorstore import is_write_locked
from sage.loaders import is_env_file, is_supported_file, iter_supported_files
from sage.registry import get_all_sources, update_source_ingest_meta
from sage.settings import load_settings

ProgressCb = Callable[[str], None]
ObserverMode = Literal["none", "native", "polling", "auto"]


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


def _resolve_observer_mode(settings: dict) -> ObserverMode:
    """
    Resolve FS observer strategy.

    Windows default is **none** (smart poll only). PollingObserver walks *every*
    file under registered roots — including venv/ — and on large OneDrive trees
    (~10–20k files per repo) it pegs CPU, spins fans, and can kill Streamlit
    with no Python traceback.
    """
    raw = str(settings.get("watcher_fs_observer", "auto") or "auto").strip().lower()
    if raw in ("none", "native", "polling"):
        return raw  # type: ignore[return-value]
    # auto
    if sys.platform == "win32":
        return "none"
    return "native"


def _make_observer(mode: ObserverMode):
    if mode == "polling":
        from watchdog.observers.polling import PollingObserver

        return PollingObserver()
    if mode == "native":
        from watchdog.observers import Observer

        return Observer()
    return None


class _DebouncedHandler(FileSystemEventHandler):
    def __init__(
        self,
        project_tag: str,
        source_id: str,
        *,
        debounce_s: float = 1.5,
        on_event: ProgressCb | None = None,
        on_activity: Callable[[], None] | None = None,
        ingest_gate: threading.Lock | None = None,
    ):
        super().__init__()
        self.project_tag = project_tag
        self.source_id = source_id
        self.debounce_s = debounce_s
        self.on_event = on_event
        self.on_activity = on_activity
        self._ingest_gate = ingest_gate
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

    def _ingest_path(self, path: str, ingest_gate: threading.Lock | None = None) -> None:
        if is_write_locked():
            if self.on_event:
                self.on_event(f"Auto-ingest deferred — Chroma ingest in progress: {path}")
            return
        acquired = False
        if ingest_gate is not None:
            acquired = ingest_gate.acquire(blocking=False)
            if not acquired:
                if self.on_event:
                    self.on_event(f"Auto-ingest deferred — scan busy: {path}")
                return
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
        finally:
            if acquired and ingest_gate is not None:
                ingest_gate.release()

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
                self._ingest_path(path, ingest_gate=self._ingest_gate)

    def stop(self) -> None:
        self._stop.set()


class FolderWatcherService:
    """Manages optional FS observers + a skip-dir-aware poll scan for folder sources.

    Document freshness does **not** depend on Streamlit's ``fileWatcherType``.
    On Windows, default mode is poll-only (no watchdog Observer) so registered
    project folders stay up to date without the CPU thrash of PollingObserver.
    """

    # Delay first poll so the UI can finish its first Chroma open after boot.
    _FIRST_POLL_DELAY_S = 30

    def __init__(self, on_event: ProgressCb | None = None):
        self.on_event = on_event
        self._observer = None
        self._handlers: list[_DebouncedHandler] = []
        self._lock = threading.Lock()
        self._watched_count = 0
        self._last_activity: str | None = None
        self._poll_stop = threading.Event()
        self._poll_thread: threading.Thread | None = None
        self._poll_scan_s = int(load_settings().get("watcher_poll_scan_s", 120))
        self._observer_mode: ObserverMode = "none"
        self._running = False
        # Single-flight: never overlap two poll scans (or poll + debounced FS ingest)
        self._ingest_gate = threading.Lock()
        # path -> (mtime_ns, size) seen after last successful check; skip cold hash/chroma
        self._seen_stat: dict[str, tuple[int, int]] = {}

    @property
    def running(self) -> bool:
        return self._running

    def _note_activity(self) -> None:
        self._last_activity = _utc_now()

    def status_message(self) -> str:
        if not self.running:
            return "Stopped"
        mode = self._observer_mode
        if mode == "none":
            obs = "poll-only (skip venv/node_modules)"
        elif mode == "polling":
            obs = "polling observer (CPU-heavy)"
        else:
            obs = "native FS observer"
        parts = [f"Watching {self._watched_count} folder source(s) ({obs})"]
        parts.append(f"scan every {self._poll_scan_s}s")
        if self._last_activity:
            parts.append(f"last activity {self._last_activity}")
        return " · ".join(parts)

    def _stat_sig(self, path: Path) -> tuple[int, int] | None:
        try:
            st = path.stat()
            return (int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))), int(st.st_size))
        except OSError:
            return None

    def _poll_scan(self) -> None:
        """Primary change detection: only supported files, skip venv/logs/etc."""
        if is_write_locked():
            if self.on_event:
                self.on_event("Poll scan skipped — Chroma ingest in progress")
            return
        # Do not stack poll scans; drop this tick if a previous scan still runs
        if not self._ingest_gate.acquire(blocking=False):
            if self.on_event:
                self.on_event("Poll scan skipped — previous scan still running")
            return
        try:
            for tag, source in get_all_sources():
                if not self.running:
                    break
                if source.get("type") != "folder":
                    continue
                root = Path(source["path"])
                if not root.is_dir():
                    continue
                source_id = source.get("id", "")
                for fpath in iter_supported_files(root):
                    if not self.running:
                        break
                    if is_write_locked():
                        if self.on_event:
                            self.on_event("Poll scan paused — Chroma write lock held")
                        return
                    key = str(fpath)
                    sig = self._stat_sig(fpath)
                    if sig is not None and self._seen_stat.get(key) == sig:
                        # Unchanged on disk since last check — no Chroma touch
                        continue
                    try:
                        report = ingest_file(
                            fpath,
                            project_tag=tag,
                            source_id=source_id,
                            force=False,
                            progress=None,
                        )
                        if sig is not None and (
                            report.files_ingested or report.files_skipped_unchanged
                        ):
                            self._seen_stat[key] = sig
                        if report.files_ingested:
                            _touch_source_meta(tag, source_id)
                            self._note_activity()
                            if self.on_event:
                                self.on_event(f"Poll-ingest: {fpath}")
                            # Brief yield after writes so UI queries can interleave
                            time.sleep(0.05)
                    except Exception as e:
                        if self.on_event:
                            self.on_event(f"Poll scan error ({fpath.name}): {e}")
        finally:
            self._ingest_gate.release()

    def _poll_loop(self) -> None:
        # First full scan after UI has had time to open Chroma (avoids boot race).
        if not self._poll_stop.wait(self._FIRST_POLL_DELAY_S):
            if self.running:
                if self.on_event:
                    self.on_event(
                        f"Starting first poll scan (every {self._poll_scan_s}s thereafter)"
                    )
                self._poll_scan()
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
            self._observer_mode = _resolve_observer_mode(settings)

            folder_sources = [
                (tag, source)
                for tag, source in get_all_sources()
                if source.get("type") == "folder" and Path(source["path"]).is_dir()
            ]
            if not folder_sources:
                return "No local folders to watch. Add a folder source first."

            handlers: list[_DebouncedHandler] = []
            observer = _make_observer(self._observer_mode)
            if observer is not None:
                for tag, source in folder_sources:
                    path = Path(source["path"])
                    handler = _DebouncedHandler(
                        tag,
                        source.get("id", ""),
                        on_event=self.on_event,
                        on_activity=self._note_activity,
                        ingest_gate=self._ingest_gate,
                    )
                    observer.schedule(handler, str(path), recursive=True)
                    handlers.append(handler)
                observer.start()
                self._observer = observer
                self._handlers = handlers
            else:
                self._observer = None
                self._handlers = []

            self._watched_count = len(folder_sources)
            self._running = True

            self._poll_stop.clear()
            self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._poll_thread.start()
            return self.status_message()

    def stop(self) -> str:
        with self._lock:
            if not self._running:
                return "Watcher not running."
            self._running = False
            self._poll_stop.set()
            if self._poll_thread:
                self._poll_thread.join(timeout=2)
            self._poll_thread = None
            if self._observer is not None:
                try:
                    self._observer.stop()
                    self._observer.join(timeout=5)
                except Exception:
                    pass
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
