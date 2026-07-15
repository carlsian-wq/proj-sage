"""
Project Sage — Streamlit UI for local project documentation RAG search.
Run:  .venv\\Scripts\\streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on path when launched via streamlit
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from sage.config import (
    EMBED_MODEL,
    LLM_MODEL,
    SUPPORTED_EXTENSIONS,
    ensure_data_dirs,
)
from sage import vectorstore
from sage.vectorstore import ChromaIndexError
from sage.ingest import ingest_all, ingest_project, ingest_source, save_upload
from sage.rag import search_and_answer
from sage.registry import (
    add_folder_source,
    add_upload_source,
    delete_project,
    ensure_project,
    get_project_sources,
    list_projects,
    remove_source,
)
from sage.settings import load_settings, update_settings
from sage.watcher import get_watcher
from sage.crashlog import install as install_crashlog

# Prefer helpers from registry; keep local fallbacks so a partial OneDrive
# sync of registry.py cannot crash the page on import.
try:
    from sage.registry import normalize_tag, suggest_tag_from_path
except ImportError:  # pragma: no cover - transient sync / stale process
    def normalize_tag(tag: str) -> str:
        return " ".join((tag or "").split()).strip()

    def suggest_tag_from_path(folder_path: str | Path) -> str:
        try:
            path = Path(folder_path).expanduser()
            name = path.resolve().name if path.exists() else path.name
        except OSError:
            name = Path(str(folder_path)).name
        return normalize_tag(name)

LOGO_PATH = ROOT / "assets" / "logo.jpg"
_PAGE_ICON = str(LOGO_PATH) if LOGO_PATH.is_file() else "🌿"

st.set_page_config(
    page_title="Project Sage",
    page_icon=_PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

ensure_data_dirs()
install_crashlog()
vectorstore.ensure_chroma_ready()


def _render_header() -> None:
    """Prominent logo + title block at the top of the main panel."""
    logo_col, text_col = st.columns([1, 4], vertical_alignment="center", gap="medium")
    with logo_col:
        if LOGO_PATH.is_file():
            st.image(str(LOGO_PATH), width=160)
        else:
            st.markdown("### 🌿")
    with text_col:
        st.markdown(
            """
            <h1 style="margin-bottom:0.15rem;">Project Sage</h1>
            <p style="margin-top:0; opacity:0.85; font-size:1.05rem;">
            Intelligent search over your coding project documentation —
            powered by <strong>Ollama</strong> locally.
            </p>
            """,
            unsafe_allow_html=True,
        )
    st.divider()


def _sync_watcher_status() -> None:
    """Reflect the real in-process watcher state (survives Streamlit reruns)."""
    w = get_watcher()
    st.session_state.watcher_status = w.status_message() if w.running else "Stopped"


def _maybe_auto_start_watcher() -> None:
    if not load_settings().get("watcher_auto_start"):
        return
    w = get_watcher(on_event=lambda m: None)
    if not w.running:
        st.session_state.watcher_status = w.start()
    else:
        _sync_watcher_status()


def _init_state() -> None:
    defaults = {
        "selected_tag": None,
        "last_ingest_log": "",
        "watcher_status": "Stopped",
        "search_result": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    _maybe_auto_start_watcher()
    if get_watcher().running:
        _sync_watcher_status()


def _refresh_projects() -> list[str]:
    return list_projects()


def _render_sources_panel(tag: str) -> None:
    sources = get_project_sources(tag)
    if not sources:
        st.caption("No sources yet for this project.")
        return
    for src in sources:
        kind = src.get("type", "?")
        path = src.get("path", "")
        label = src.get("original_name") or path
        last = src.get("last_ingested_at") or "never"
        count = src.get("file_count", 0)
        col_a, col_b, col_c = st.columns([4, 1, 1])
        with col_a:
            st.markdown(f"**{kind}** · `{label}`  \nFiles: {count} · Last ingest: `{last}`")
        with col_b:
            if st.button("Ingest", key=f"ingest_src_{src['id']}", use_container_width=True):
                log_lines: list[str] = []
                progress_slot = st.empty()

                def _progress(msg: str) -> None:
                    log_lines.append(msg)
                    progress_slot.caption(msg)

                with st.spinner("Ingesting changed files…"):
                    report = ingest_source(
                        tag,
                        src,
                        force=False,
                        progress=_progress,
                    )
                    st.session_state.last_ingest_log = "\n".join(log_lines) + "\n\n" + report.summary()
                st.success("Source ingest complete.")
                st.rerun()
        with col_c:
            if st.button("Remove", key=f"rm_src_{src['id']}", use_container_width=True):
                # Drop vectors for files under this source when possible
                if src.get("type") == "file":
                    vectorstore.delete_by_source_path(tag, src["path"])
                remove_source(tag, src["id"])
                st.rerun()


def _apply_pending_selected_tag(projects: list[str]) -> None:
    """Apply deferred Active-project changes *before* the selectbox is created.

    selected_tag is bound with key= on the selectbox; Streamlit forbids writing
    that key after the widget exists on the same run.
    """
    if "_pending_selected_tag" not in st.session_state:
        return
    pending = st.session_state.pop("_pending_selected_tag")
    if pending is None:
        # Drop key so the next selectbox run re-defaults cleanly.
        st.session_state.pop("selected_tag", None)
    elif projects and pending in projects:
        st.session_state.selected_tag = pending
    elif pending:
        # Tag may have just been created; keep it if projects not refreshed yet.
        st.session_state.selected_tag = pending


def _sidebar() -> None:
    if LOGO_PATH.is_file():
        st.sidebar.image(str(LOGO_PATH), width=96)
    st.sidebar.title("Project Sage")
    st.sidebar.caption(f"LLM: `{LLM_MODEL}` · Embed: `{EMBED_MODEL}`")

    projects = _refresh_projects()
    _apply_pending_selected_tag(projects)

    st.sidebar.subheader("Project tags")
    new_tag = st.sidebar.text_input(
        "Create project tag",
        placeholder="e.g. my-api-docs",
        help="Optional if you add a folder below — the folder name becomes the tag automatically.",
    )
    if st.sidebar.button("Create / select project", use_container_width=True):
        tag_name = normalize_tag(new_tag or "")
        if tag_name:
            ensure_project(tag_name)
            # Selectbox may already exist this run; defer assignment to next run.
            st.session_state._pending_selected_tag = tag_name
            st.sidebar.success(f"Project “{tag_name}” ready.")
            st.rerun()
        else:
            st.sidebar.warning("Enter a project name tag.")

    if projects:
        # Bind via key only — do NOT pass index= each run. In Streamlit 1.59+,
        # index is part of the widget element id, so changing it on every
        # selection creates a new widget, desyncs the frontend, and can kill
        # the server session with no useful traceback.
        if st.session_state.get("selected_tag") not in projects:
            st.session_state.selected_tag = projects[0]
        st.sidebar.selectbox(
            "Active project",
            options=projects,
            key="selected_tag",
            help="Used for uploads, force-ingest, and sources list. Folder add uses its own tag field.",
        )
    else:
        st.sidebar.info("Add a local folder below (tag is created from the folder name), or create a tag first.")
        st.session_state.pop("selected_tag", None)

    tag = st.session_state.get("selected_tag")

    st.sidebar.divider()
    st.sidebar.subheader("Add local folder")
    st.sidebar.caption(
        "Folder name becomes the project tag (and appears in filter dropdowns) unless you override it."
    )

    folder = st.sidebar.text_input(
        "Local folder path",
        placeholder=r"C:\Users\...\my-project",
        key="folder_path_input",
        help="All supported docs under this folder will be indexed (skipping node_modules, .git, venvs, …).",
    )

    # Keep tag field in sync with the folder basename when the path changes
    suggested = suggest_tag_from_path(folder) if (folder or "").strip() else ""
    prev_path = st.session_state.get("_folder_path_for_tag", "")
    if (folder or "") != prev_path:
        st.session_state._folder_path_for_tag = folder or ""
        if suggested:
            st.session_state.folder_tag_input = suggested

    if "folder_tag_input" not in st.session_state:
        st.session_state.folder_tag_input = suggested or (tag or "")

    folder_tag = st.sidebar.text_input(
        "Project tag for this folder",
        key="folder_tag_input",
        help="Auto-filled from the folder name. Edit to use a different tag. Created if it does not exist.",
    )

    use_active = False
    if tag:
        # Stable key + label: avoid widget-id thrash when active tag changes.
        use_active = st.sidebar.checkbox(
            f"Attach to active project instead ({tag})",
            key="attach_to_active_project",
            help="When checked, the folder is stored under the Active project tag above.",
        )

    if st.sidebar.button("Add folder source", use_container_width=True, type="primary"):
        if not folder or not folder.strip():
            st.sidebar.warning("Enter a folder path.")
        else:
            target_tag = tag if use_active and tag else normalize_tag(folder_tag or "")
            if not target_tag:
                target_tag = suggest_tag_from_path(folder.strip())
            if not target_tag:
                st.sidebar.warning("Could not determine a project tag. Enter one above.")
            else:
                try:
                    ensure_project(target_tag)
                    add_folder_source(target_tag, folder.strip())
                    with st.spinner(f"Ingesting into project “{target_tag}”…"):
                        log_lines: list[str] = []
                        srcs = get_project_sources(target_tag)
                        resolved = Path(folder.strip()).expanduser().resolve()
                        folder_src = next(
                            (
                                s
                                for s in reversed(srcs)
                                if s.get("type") == "folder"
                                and Path(s["path"]).resolve() == resolved
                            ),
                            srcs[-1] if srcs else None,
                        )
                        if folder_src:
                            report = ingest_source(
                                target_tag,
                                folder_src,
                                force=False,
                                progress=lambda m: log_lines.append(m),
                            )
                            st.session_state.last_ingest_log = (
                                f"Project tag: {target_tag}\n"
                                + "\n".join(log_lines)
                                + "\n\n"
                                + report.summary()
                            )
                    st.session_state._pending_selected_tag = target_tag
                    st.sidebar.success(
                        f"Folder added under project tag “{target_tag}” (now in filter dropdowns)."
                    )
                    w = get_watcher()
                    if w.running:
                        st.session_state.watcher_status = w.restart()
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(str(e))

    st.sidebar.divider()
    st.sidebar.subheader(f"Uploads · {tag or 'select a project'}")

    # File upload (requires an active project)
    display_exts = sorted(ext for ext in SUPPORTED_EXTENSIONS if ext != ".log")
    st.sidebar.caption("Supported: " + ", ".join(display_exts))
    upload_types = sorted({ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS} | {"yml", "yaml", "env"})
    uploads = st.sidebar.file_uploader(
        "Upload project files",
        type=upload_types,
        accept_multiple_files=True,
        disabled=not bool(tag),
        help="Includes yaml/yml and env. All files stay on this machine (local Ollama + data/).",
    )
    if uploads and st.sidebar.button("Upload & ingest", use_container_width=True, disabled=not bool(tag)):
        log_lines: list[str] = []
        with st.spinner("Uploading and embedding…"):
            for uf in uploads:
                data = uf.getvalue()
                dest = save_upload(tag, uf.name, data)
                add_upload_source(tag, dest, uf.name)
                srcs = get_project_sources(tag)
                match = next(
                    (
                        s
                        for s in reversed(srcs)
                        if s.get("type") == "file" and Path(s["path"]) == dest.resolve()
                    ),
                    None,
                )
                if match:
                    report = ingest_source(
                        tag,
                        match,
                        force=True,
                        progress=lambda m: log_lines.append(m),
                    )
                    log_lines.append(report.summary())
        st.session_state.last_ingest_log = "\n".join(log_lines)
        st.sidebar.success(f"Uploaded {len(uploads)} file(s) under “{tag}”.")
        st.rerun()

    st.sidebar.divider()
    st.sidebar.subheader("Force ingest")
    c1, c2 = st.sidebar.columns(2)
    with c1:
        if st.button(
            "This project",
            use_container_width=True,
            help="Re-embed every file under the active tag (slow on large repos)",
            disabled=not bool(tag),
        ):
            log_lines: list[str] = []
            progress_slot = st.sidebar.empty()

            def _progress(msg: str) -> None:
                log_lines.append(msg)
                progress_slot.caption(msg[:120])

            with st.spinner(f"Force ingesting “{tag}”…"):
                report = ingest_project(tag, force=True, progress=_progress)
                st.session_state.last_ingest_log = "\n".join(log_lines) + "\n\n" + report.summary()
            st.sidebar.success("Project ingest complete.")
            st.rerun()
    with c2:
        if st.button(
            "All projects",
            use_container_width=True,
            help="Re-embed every registered source (slowest)",
        ):
            log_lines = []
            progress_slot = st.sidebar.empty()

            def _progress_all(msg: str) -> None:
                log_lines.append(msg)
                progress_slot.caption(msg[:120])

            with st.spinner("Force ingesting all projects…"):
                report = ingest_all(force=True, progress=_progress_all)
                st.session_state.last_ingest_log = "\n".join(log_lines) + "\n\n" + report.summary()
            st.sidebar.success("Full ingest complete.")
            st.rerun()

    st.sidebar.divider()
    st.sidebar.subheader("Folder watcher")
    _sync_watcher_status()
    st.sidebar.caption(st.session_state.watcher_status)
    if sys.platform == "win32":
        st.sidebar.caption(
            "Windows default: **poll-only** (scans supported docs every N seconds, "
            "skips venv/node_modules). Full recursive polling was pegging CPU on large "
            "repos and could kill Streamlit with no error."
        )
    auto_start = st.sidebar.checkbox(
        "Auto-start watcher on launch",
        value=bool(load_settings().get("watcher_auto_start")),
        help="Restarts the watcher when you open Project Sage (Streamlit must stay running).",
    )
    if auto_start != bool(load_settings().get("watcher_auto_start")):
        update_settings(watcher_auto_start=auto_start)
        if auto_start and not get_watcher().running:
            st.session_state.watcher_status = get_watcher(on_event=lambda m: None).start()
        st.rerun()
    wc1, wc2, wc3 = st.sidebar.columns(3)
    with wc1:
        if st.button("Start", use_container_width=True):
            msg = get_watcher(on_event=lambda m: None).start()
            st.session_state.watcher_status = msg
            st.rerun()
    with wc2:
        if st.button("Stop", use_container_width=True):
            msg = get_watcher().stop()
            st.session_state.watcher_status = msg
            st.rerun()
    with wc3:
        if st.button("Restart", use_container_width=True):
            msg = get_watcher(on_event=lambda m: None).restart()
            st.session_state.watcher_status = msg
            st.rerun()

    with st.sidebar.expander("Sources for active project", expanded=True):
        if tag:
            _render_sources_panel(tag)
        else:
            st.caption("No active project selected.")

    with st.sidebar.expander("Danger zone"):
        if st.button(
            "Delete project tag + vectors",
            type="secondary",
            disabled=not bool(tag),
        ):
            vectorstore.delete_project(tag)
            delete_project(tag)
            st.session_state._pending_selected_tag = None
            st.rerun()

    if st.session_state.last_ingest_log:
        with st.sidebar.expander("Last ingest log"):
            st.code(st.session_state.last_ingest_log, language="text")


def _main_search() -> None:
    _render_header()

    # Clear Search sets a flag then reruns; mutate widget state only *before*
    # the text_area with key="search_query" is created.
    if st.session_state.pop("_clear_search", False):
        st.session_state.search_query = ""
        st.session_state.search_result = None

    projects = _refresh_projects()
    filter_options = ["All projects"] + projects

    col_filter, col_stats = st.columns([2, 1])
    with col_filter:
        tag_filter = st.selectbox(
            "Filter by project tag",
            options=filter_options,
            key="tag_filter",
            help="Limit retrieval to one project, or search across all.",
        )
    with col_stats:
        try:
            n = vectorstore.count_chunks(
                None if tag_filter == "All projects" else tag_filter
            )
            st.metric("Indexed chunks", n)
        except ChromaIndexError as e:
            st.metric("Indexed chunks", "—")
            st.error(str(e))

    query = st.text_area(
        "Search project docs",
        placeholder="e.g. How do I configure the authentication middleware?",
        height=100,
        key="search_query",
    )
    btn_search, btn_clear, _ = st.columns([1, 1, 4])
    with btn_search:
        search_clicked = st.button("Search", type="primary", use_container_width=True)
    with btn_clear:
        clear_clicked = st.button("Clear Search", use_container_width=True)

    if clear_clicked:
        st.session_state._clear_search = True
        st.rerun()

    if search_clicked:
        if not (query or "").strip():
            st.warning("Enter a search question.")
        elif n == 0:
            st.warning("Nothing indexed yet. Add sources and ingest from the sidebar.")
        else:
            with st.spinner("Retrieving sources and generating answer…"):
                result = search_and_answer(
                    query.strip(),
                    project_tag=None if tag_filter == "All projects" else tag_filter,
                )
                st.session_state.search_result = result

    result = st.session_state.search_result
    if not result:
        st.info(
            "Add a project tag, attach a local folder or upload files, then ask a question. "
            "Results appear here as a grounded answer with source citations."
        )
        return

    if result.get("error"):
        st.error(result["error"])

    st.subheader("Answer")
    answer = result.get("answer") or ""
    if answer:
        st.markdown(answer)
    else:
        st.caption("No answer generated.")

    hits = result.get("hits") or []
    if hits:
        st.subheader("Sources")
        for i, hit in enumerate(hits, start=1):
            meta = hit.get("metadata") or {}
            score = hit.get("score")
            score_s = f"{score:.2f}" if isinstance(score, (int, float)) else "n/a"
            path = meta.get("source_path", "?")
            tag = meta.get("project_tag", "?")
            with st.expander(f"[{i}] {tag} · score {score_s} · {Path(path).name}"):
                st.caption(path)
                st.markdown(hit.get("text") or "")


def main() -> None:
    try:
        _init_state()
        _sidebar()
        _main_search()
    except Exception as exc:
        st.error(f"Project Sage error: {exc}")
        st.exception(exc)
        raise


if __name__ == "__main__":
    main()
