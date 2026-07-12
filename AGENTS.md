# Agent notes — Project Sage

## Standing instructions

- **Update project documentation after every turn** — keep `README.md`, `STARTUP.md`, and related docs in sync with code, scripts, shortcuts, and assets you add or change.

## Local conventions

- Python venv path: `.venv` (not `venv`)
- Streamlit default port: **8501**
- Branding: `assets/logo.jpg` (UI), `assets/logo.ico` (Windows shortcuts)
- Desktop install: `scripts/install_desktop_shortcuts.ps1`
- **Folder add must create/select a project tag** — default tag = folder basename via `suggest_tag_from_path`; never silently attach to an unrelated active tag without the user opting in.
