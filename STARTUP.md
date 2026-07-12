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
| **Project Sage Streamlit** | Streamlit server console only (keep this open while using the app) |

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

## If Streamlit shows ImportError after an update

Usually a stale process or OneDrive mid-sync on `sage/*.py`. Fix:

1. Stop the Streamlit console (close the window or Ctrl+C).
2. Re-launch with **Project Sage** or **Project Sage Streamlit**.
3. Hard-refresh the browser/app window (Ctrl+F5).

`normalize_tag` / `suggest_tag_from_path` live in `sage/registry.py` and are also guarded with fallbacks in `app.py`.

## Search robustness

Retrieval results normalize missing Chroma documents to `""` so formatting never calls `.strip()` on `None` (fixed when some hits had null `text`).

**Clear Search:** sets a session flag and reruns; the query widget key is cleared at the top of the next run (Streamlit forbids changing `st.session_state.<widget_key>` after that widget is instantiated).

## Formats: YAML, env & logs (local only)

Supported alongside docs: **`.yaml` / `.yml`**, **`.env`** (also `.env.local`, `*.env`), and **`.log`**.

- YAML: `yaml.safe_load` only (requires `PyYAML` in `.venv`).
- Env: keys/values indexed into local Chroma under `data/` for natural-language questions about config.
- Log: plain-text load (UTF-8 and common fallbacks) — good for app/server logs under watched folders.
- No cloud upload — Ollama + Streamlit stay on localhost. Keep `data/` private and gitignored.

After upgrading deps:

```powershell
.\.venv\Scripts\pip install -r requirements.txt
```

Then **Force ingest** the project so existing folders pick up new `.yaml` / `.env` / `.log` files.

## Scripts

| Script | Role |
|--------|------|
| `scripts/build_icon.py` | Build multi-size `assets/logo.ico` from `assets/logo.jpg` |
| `scripts/launch_project_sage.ps1` | Full launch: Ollama + Streamlit + browser app window |
| `scripts/start_streamlit.ps1` | Streamlit only |
| `scripts/install_desktop_shortcuts.ps1` | Create/refresh Desktop `.lnk` files with logo icon |
| `scripts/launch_project_sage.vbs` | Optional VBS wrapper for the full launcher |
