# Project Sage — agent conventions

Adds to workspace root `GitHub/Agents.md`. **This file wins** on conflict inside `proj-sage/`.

Bot-only: operational rules for coding agents. Human product docs: `README.md`, `STARTUP.md`, `TROUBLESHOOTING.md`.

---

## Scope

- Local **RAG / Streamlit** doc search (Ollama + Chroma). Not a trading bot.
- Prefer reversible local edits. Confirm before destructive or shared ops (mass delete of `data/`, force-push, exposing ports).
- Do not expand into unrelated refactors or other repos unless asked.

---

## Environment

| Item | Convention |
|------|------------|
| OS / shell | Windows, **PowerShell 7** (`pwsh`) |
| Venv | **`.venv`** (not `venv`) |
| Entry | `app.py` → `streamlit run app.py` |
| Port | **8504** (8501 HL, 8502 log-sage, 8503 net-comd-comp) |
| Models | Ollama `qwen2.5:7b` + `nomic-embed-text` @ `127.0.0.1:11434` |
| Data | `data/` (registry, chroma, uploads) — **gitignored**, never commit |
| Branding | `assets/logo.jpg` (UI), `assets/logo.ico` (shortcuts) |

- Work from `proj-sage/` for pip, tests, and Streamlit.
- Use `.venv\Scripts\python.exe` / `streamlit.exe`.
- Status ports: `scripts/show_running.ps1`. Stop: `scripts/stop_project_sage.ps1`.
- Desktop shortcuts: `scripts/install_desktop_shortcuts.ps1`.

---

## Product rules (do not regress)

1. **Update docs after every turn** — `README.md`, `STARTUP.md`, `TROUBLESHOOTING.md`, this file when conventions change.
2. **Folder add creates the project tag** — default tag = folder basename (`suggest_tag_from_path`). Never silently attach a new folder to an unrelated Active project without the user opting in (“Attach to active project”).
3. **Uploads use Active project** only; require a selected tag.
4. **Local-only processing** — no cloud LLM/upload paths for indexed content. Sensitive: `.env` / `.env.*` stay on disk under `data/`.
5. **Supported files** — see `sage/config.py` + `sage/loaders.py`. Includes **`.jsonl`** (log-sage `coding-notes.jsonl`). Use `is_env_file()` / `is_supported_file()` (file named `.env` has empty `Path.suffix`). Skip sidecars in `SKIP_FILE_NAMES` (e.g. `coding_notes_state.json`).
6. **Coding notes corpus** — only tag **`coding-notes`** → `log-sage\exports`. Do **not** also register `exports` / `grokbuild-coding-notes` tags (duplicates). Dir name `exports` is skipped when walking other project roots so log-sage repo ingest does not double-index the jsonl.
7. **Clear Search** — clear widget state via a flag before the text_area is created (never mutate `search_query` after the widget instantiates).
8. **Chroma docs may be null** — coerce hit text before `.strip()`.
9. **“Error finding id” on search** = corrupted Chroma HNSW (not Ollama). Stop app → `scripts/rebuild_chroma.py` → restart. Do not re-ingest while Streamlit is open.

---

## Agent hygiene

- Prefer project modules over scattering `_temp_*.py`; delete temps after use.
- PowerShell: here-strings / small scripts for anything with `$` or nested quotes (see root `Agents.md`).
- Do not invent monorepo packages shared with other GitHub projects.
- After user-facing changes, end with **What you should do** (reload/restart/verify bullets) when action matters.

---

## What you should do (for the user, when relevant)

Agents: close implementation replies with a short action list, e.g.:

```markdown
## What you should do

- Restart Streamlit (or use Project Sage desktop shortcut)
- Hard-refresh the app window if UI looks stale
```
