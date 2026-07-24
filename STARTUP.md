# Project Sage — Startup

## Desktop shortcuts (recommended)

Install or refresh shortcuts (uses `assets/logo.ico`):

```powershell
cd C:\Users\c_sia\OneDrive\Documents\GitHub\proj-sage
powershell -ExecutionPolicy Bypass -File scripts\install_desktop_shortcuts.ps1
```

Prefer Edge app mode:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_desktop_shortcuts.ps1 -Browser edge
```

| Desktop shortcut | What it does |
|------------------|--------------|
| **Project Sage** | Starts Streamlit if needed, ensures Ollama is up, opens Chrome/Edge in `--app` mode (desktop web app, no browser tabs) at http://localhost:8504 |
| **Project Sage Streamlit** | Streamlit server console — **keep this window open** while using the app |

Both shortcuts use the Project Sage logo (`assets/logo.ico`).

## Manual run

```powershell
cd C:\Users\c_sia\OneDrive\Documents\GitHub\proj-sage
.\.venv\Scripts\Activate.ps1
streamlit run app.py
# uses port 8504 from .streamlit/config.toml (or: --server.port 8504)
```

Then open http://localhost:8504, or as a desktop app:

```powershell
# Chrome
& "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" --app=http://localhost:8504

# Edge
& "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe" --app=http://localhost:8504
```

## Prerequisites

1. `.venv` installed (`pip install -r requirements.txt`)
2. Ollama running with `qwen2.5:7b` and `nomic-embed-text`
3. Port **8504** free (local map: 8501 hyperliquid-bot, 8502 log-sage, 8503 net-comd-comp)

## Project tags

- Adding a **local folder** auto-fills **Project tag for this folder** from the leaf folder name and **creates that tag** on ingest.
- Example: `C:\...\GitHub\proj-sage` → tag `proj-sage` → appears in *Active project* and *Filter by project tag*.
- Uploads still use the **Active project** tag (create or select one first).
- Optional checkbox: *Attach to active project instead* if you want the folder under an existing tag rather than the folder name.

## Launcher logs

`data/launcher.log` (gitignored under `data/`) records start/open events from the app-mode launcher.

## Troubleshooting

See **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** for:

- `show_running.ps1` — all apps on :8501–:8504 at a glance
- Desktop shortcut flash vs visible console
- Stopping duplicates, Chroma rebuild, watcher issues, launch errors

Quick status:

```powershell
.\scripts\show_running.ps1
.\scripts\show_running.ps1 -Details   # PID chains for each running app
```

## Formats: YAML, env, JSONL (local only)

Supported alongside docs: **`.yaml` / `.yml`**, **`.env`** (also `.env.local`, `*.env`), and **`.jsonl`**.

- YAML: `yaml.safe_load` only (requires `PyYAML` in `.venv`).
- Env: keys/values indexed into local Chroma under `data/` for natural-language questions about config.
- JSONL: one JSON object per line; Log Sage **coding-notes** fields become labeled blocks for RAG.
- Runtime **`logs/`** folders and **`.log`** files are not indexed (too large; use log-sage for log search).
- Sidecars `coding_notes_state.json` / `*_status.json` are skipped when walking folders.
- No cloud upload — Ollama + Streamlit stay on localhost. Keep `data/` private and gitignored.

### Coding notes (all Grok projects — central hub)

```text
Hub:     C:\Users\c_sia\OneDrive\Documents\GitHub\coding-notes\
File:    coding-notes.jsonl
Tag:     coding-notes
Source:  ~/.grok/sessions/  (export via Log Sage)
```

Notes are **not log-sage-only** — the exporter scans every Grok session cwd and sets a `project` field (`proj-sage`, `hyperliquid-bot`, …).

1. One Project Sage tag: **`coding-notes`** → the hub folder above.
2. Refresh extract: `cd log-sage; .\venv\Scripts\python.exe scripts\export_coding_notes.py`
3. Then **Force ingest** on **coding-notes** (or folder watcher).
4. Search with filter **coding-notes** (ask about a repo by name in the query).

After upgrading deps:

```powershell
.\.venv\Scripts\pip install -r requirements.txt
```

Then **Force ingest** so existing folders pick up new extensions.

## Folder watcher (recommended)

Sidebar → **Folder watcher** → enable **Auto-start watcher on launch** → **Restart**.

Windows default is **poll-only** (supported docs every ~2 min; skips `venv` / `logs` / etc.). Status should say `poll-only`, not `polling observer (CPU-heavy)`.

If Streamlit dies silently with fans spinning hard, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md) → *Streamlit exits with no console error*.

## Scripts

| Script | Role |
|--------|------|
| `scripts/build_icon.py` | Build multi-size `assets/logo.ico` from `assets/logo.jpg` |
| `scripts/launch_project_sage.ps1` | Full launch: Ollama + Streamlit + browser app window |
| `scripts/start_streamlit.ps1` | Streamlit only |
| `scripts/install_desktop_shortcuts.ps1` | Create/refresh Desktop `.lnk` files with logo icon |
| `scripts/launch_project_sage.vbs` | Optional VBS wrapper for the full launcher |
| `scripts/rebuild_chroma.py` | Backup + wipe corrupted Chroma + re-ingest all projects |
| `scripts/show_running.ps1` | Status for :8501-:8504; add `-Details` for process chains |
| `scripts/stop_project_sage.ps1` | Stop Streamlit and free port 8504 |
