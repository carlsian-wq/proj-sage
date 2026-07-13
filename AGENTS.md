# Agent notes — Project Sage

## Standing instructions

- **Update project documentation after every turn** — keep `README.md`, `STARTUP.md`, and related docs in sync with code, scripts, shortcuts, and assets you add or change.

## Local conventions

- Python venv path: `.venv` (not `venv`)
- Streamlit default port: **8504** (8501 hyperliquid-bot, 8502 log-sage, 8503 net-comd-comp)
- Status all ports: `scripts/show_running.ps1` — see **TROUBLESHOOTING.md**
- Branding: `assets/logo.jpg` (UI), `assets/logo.ico` (Windows shortcuts)
- Desktop install: `scripts/install_desktop_shortcuts.ps1`
- **Folder add must create/select a project tag** — default tag = folder basename via `suggest_tag_from_path`; never silently attach to an unrelated active tag without the user opting in.
- **Supported formats** include `.yaml`/`.yml` and `.env` / `.env.*` (see `sage/config.py` + `sage/loaders.py`). `.log` files and `logs/` dirs are excluded. All processing is local-only; never add cloud upload paths for these files.
- File named exactly `.env` has empty `Path.suffix` — use `is_env_file()` / `is_supported_file()`, not suffix alone.
