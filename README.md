# Project Sage

Local **RAG search agent** for coding project documentation.

- **UI:** Streamlit  
- **LLM:** Ollama `qwen2.5:7b`  
- **Embeddings:** Ollama `nomic-embed-text`  
- **Vector store:** Chroma (on disk under `data/`)

Tag projects, point at local folders or upload files (`txt`, `md`, `pdf`, `csv`, `json`, `yaml`/`yml`, `.env`, `doc`, `docx`), auto-ingest on change, and ask natural-language questions with grounded answers + citations.

## Requirements

- Python 3.12+
- [Ollama](https://ollama.com) running locally with:

```bash
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

## Setup

```powershell
cd C:\Users\c_sia\OneDrive\Documents\GitHub\proj-sage
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

### Desktop app (Chrome / Edge)

Install shortcuts once (logo icon included):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_desktop_shortcuts.ps1
# optional: -Browser edge
```

| Shortcut | Purpose |
|----------|---------|
| **Project Sage** | Start server if needed → open as desktop web app (`--app=http://localhost:8504`) |
| **Project Sage Streamlit** | Streamlit console only |

Details: [STARTUP.md](STARTUP.md). Problems: [TROUBLESHOOTING.md](TROUBLESHOOTING.md) (`show_running.ps1 -Details` for PID chains).

### CLI

```powershell
.\.venv\Scripts\streamlit run app.py
```

Open the URL Streamlit prints (usually http://localhost:8504).

## How to use

1. **Add a local folder** (simplest path):
   - Paste a folder path in the sidebar.
   - **Project tag defaults to the folder name** (e.g. `...\proj-sage` → tag `proj-sage`) and is **created automatically** if new.
   - You can edit the tag before clicking *Add folder source*, or check *Attach to active project instead* to reuse the active tag.
2. **Or create a tag first** with *Create project tag*, then upload files under the active project.
3. Ingest runs automatically on add; use **Force ingest** if you need a full rebuild.
4. **Folder watcher** — enable **Auto-start watcher on launch** (recommended), or click **Start** each session. On Windows the default is **poll-only**: every ~2 minutes it walks supported docs only (skips `venv`, `node_modules`, `logs`, …). Full recursive `PollingObserver` is off by default — it was pegging CPU on large OneDrive trees and could kill Streamlit with no error.
5. **Last ingest** in the sources panel updates after full **Ingest** / **Force ingest**, and also after the watcher auto-ingests changed files.
6. In the main panel, choose **All projects** or a **project tag** filter, type a question, **Search**. Use **Clear Search** next to Search to reset the query and results.

> **Note:** Tags only appear in filter dropdowns after they exist in the registry. Adding a folder creates the tag; merely embedding under another active project (old behavior) did not.

## Branding / assets

| File | Use |
|------|-----|
| `assets/logo.jpg` | In-app header + sidebar logo |
| `assets/logo.ico` | Windows desktop shortcut icon (built by `scripts/build_icon.py`) |

## Data layout

```
data/
  registry.json     # project tags + source metadata
  settings.json     # watcher auto-start, poll interval, fs observer mode
  chroma/           # vector index
  uploads/          # files uploaded via the UI
  launcher.log      # desktop launcher events
```

Everything stays on your machine. `data/` is gitignored.

## Notes

- Legacy `.doc` extraction is best-effort; prefer `.docx` or `.pdf`.
- Ollama must be reachable at `http://127.0.0.1:11434`.
- First embed/search can be slow while models load into memory.
- Default port is **8504** (8501 hyperliquid-bot, 8502 log-sage, 8503 net-comd-comp).
- **Active project** is bound with a stable Streamlit widget key (do not reintroduce `index=` on that selectbox — it can silently kill the server on Streamlit 1.59+). See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Supported formats & privacy

| Format | Notes |
|--------|--------|
| `.txt`, `.md` | Plain text |
| `.pdf`, `.csv`, `.json` | Extracted / pretty-printed locally |
| `.yaml`, `.yml` | Parsed with **PyYAML `safe_load`** (no code execution) |
| `.env`, `.env.*`, `*.env` | Parsed as dotenv key/value text for local search |
| `.doc`, `.docx` | Docx preferred |

**Local & secure by design**

- Embeddings and answers use **local Ollama** only (`127.0.0.1:11434`).
- Vectors and uploads live under **`data/`** (gitignored) on your disk.
- Project Sage does **not** call external LLM/cloud APIs.
- `.env` content is still sensitive: anyone with access to your PC/`data/` can read the index. Do not commit `data/`, and do not expose port 8504 on untrusted networks.

## Project layout

```
app.py                 # Streamlit entrypoint
assets/
  logo.jpg             # app branding
  logo.ico             # shortcut icon
scripts/
  build_icon.py
  launch_project_sage.ps1
  start_streamlit.ps1
  install_desktop_shortcuts.ps1
  launch_project_sage.vbs
STARTUP.md             # desktop / launcher guide
TROUBLESHOOTING.md     # show_running, ports, Chroma, shortcuts
sage/
  config.py            # models, paths, extensions
  registry.py          # project/source registry
  loaders.py           # file text extraction
  chunking.py
  embeddings.py        # Ollama embeddings
  vectorstore.py       # Chroma
  ingest.py            # hash-aware ingest pipeline
  rag.py               # retrieve + answer
  settings.py          # persisted watcher preferences
  watcher.py           # folder auto-ingest (poll-only by default on Windows)
```

## Documentation policy

Update project documentation (`README.md`, `STARTUP.md`, and any feature-specific docs) **after every change turn** so startup steps, shortcuts, assets, and layout stay accurate.
