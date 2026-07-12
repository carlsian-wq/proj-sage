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
from sage.watcher import get_watcher

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
                with st.spinner("Ingesting source…"):
                    log_lines: list[str] = []
                    report = ingest_source(
                        tag,
                        src,
                        force=True,
                        progress=lambda m: log_lines.append(m),
                    )
                    st.session_state.last_ingest_log = "\n".join(log_lines) + "\n\n" + report.summary()
                st.success("Source re-ingested.")
                st.rerun()
        with col_c:
            if st.button("Remove", key=f"rm_src_{src['id']}", use_container_width=True):
                # Drop vectors for files under this source when possible
                if src.get("type") == "file":
                    vectorstore.delete_by_source_path(tag, src["path"])
                remove_source(tag, src["id"])
                st.rerun()


def _sidebar() -> None:
    if LOGO_PATH.is_file():
        st.sidebar.image(str(LOGO_PATH), width=96)
    st.sidebar.title("Project Sage")
    st.sidebar.caption(f"LLM: `{LLM_MODEL}` · Embed: `{EMBED_MODEL}`")

    projects = _refresh_projects()

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
            st.session_state.selected_tag = tag_name
            st.sidebar.success(f"Project “{tag_name}” ready.")
            st.rerun()
        else:
            st.sidebar.warning("Enter a project name tag.")

    if projects:
        selected = st.sidebar.selectbox(
            "Active project",
            options=projects,
            index=projects.index(st.session_state.selected_tag)
            if st.session_state.selected_tag in projects
            else 0,
            help="Used for uploads, force-ingest, and sources list. Folder add uses its own tag field.",
        )
        st.session_state.selected_tag = selected
    else:
        st.sidebar.info("Add a local folder below (tag is created from the folder name), or create a tag first.")
        st.session_state.selected_tag = None

    tag = st.session_state.selected_tag

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
        use_active = st.sidebar.checkbox(
            f"Attach to active project instead ({tag})",
            value=False,
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
                    st.session_state.selected_tag = target_tag
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
    st.sidebar.caption(
        "Supported: " + ", ".join(sorted(SUPPORTED_EXTENSIONS))
    )
    upload_types = sorted({ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS} | {"yml", "yaml", "env"})
    uploads = st.sidebar.file_uploader(
        "Upload project files",
        type=upload_types,
        accept_multiple_files=True,
        disabled=not bool(tag),
        help="Includes yaml/yml, env, and log. All files stay on this machine (local Ollama + data/).",
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
            help="Re-ingest all sources under the active tag",
            disabled=not bool(tag),
        ):
            with st.spinner(f"Ingesting project “{tag}”…"):
                log_lines = []
                report = ingest_project(tag, force=True, progress=lambda m: log_lines.append(m))
                st.session_state.last_ingest_log = "\n".join(log_lines) + "\n\n" + report.summary()
            st.sidebar.success("Project ingest complete.")
            st.rerun()
    with c2:
        if st.button("All projects", use_container_width=True, help="Re-ingest every registered source"):
            with st.spinner("Ingesting all projects…"):
                log_lines = []
                report = ingest_all(force=True, progress=lambda m: log_lines.append(m))
                st.session_state.last_ingest_log = "\n".join(log_lines) + "\n\n" + report.summary()
            st.sidebar.success("Full ingest complete.")
            st.rerun()

    st.sidebar.divider()
    st.sidebar.subheader("Folder watcher")
    st.sidebar.caption(st.session_state.watcher_status)
    wc1, wc2 = st.sidebar.columns(2)
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
            st.session_state.selected_tag = None
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
            help="Limit retrieval to one project, or search across all.",
        )
    with col_stats:
        n = vectorstore.count_chunks(
            None if tag_filter == "All projects" else tag_filter
        )
        st.metric("Indexed chunks", n)

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
    _init_state()
    _sidebar()
    _main_search()


if __name__ == "__main__":
    main()
