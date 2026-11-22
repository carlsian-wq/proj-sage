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
| Where it runs | **CODE-HOUSE** (see `CODE-HOUSE-HANDOFF.md`). Leave :8504 stopped on BOT-HOUSE. |
| Bind | **`10.0.0.201:8504`** (CODE-HOUSE Wi-Fi, Private). Operator requested LAN access on 2026-09-27. Do not rebind to `127.0.0.1` or `0.0.0.0` unless they ask. Index may contain `hyperliquid-bot\.env`. Ollama stays on `127.0.0.1:11434`. |

- Work from `proj-sage/` for pip, tests, and Streamlit.
- Use `.venv\Scripts\python.exe` / `streamlit.exe`.
- Status ports: `scripts/show_running.ps1`. Stop: `scripts/stop_project_sage.ps1`.
- Desktop shortcuts: `scripts/install_desktop_shortcuts.ps1`.
- **Visible console (required).** Start and restart the dashboard in a visible PowerShell 7 window so the operator can watch errors. Do not run `scripts\start_streamlit.ps1` inside the agent tool shell, including a background job. That shell is hidden. When the tool command ends, the job kills the console and can leave Streamlit running with nobody watching it.
- Do not use `Start-Process` from the agent shell for this. Create the process with `Win32_Process.Create` so the parent is `WmiPrvSE`, not the agent job. Use `cmd /c start "Project Sage"` and the installed `pwsh.exe` under `C:\Program Files\WindowsApps\Microsoft.PowerShell_*`. Do not use the `WindowsApps` execution alias (`...\Microsoft.PowerShell_8wekyb3d8bbwe\pwsh.exe`): WMI cannot start it (return value 8). Do not use Windows PowerShell 5.1 (`powershell.exe`).
- Leave that **Project Sage** window open while the app runs. `data/streamlit.log` is a copy of the console, not a substitute for it. The desktop shortcut **Project Sage Streamlit** is also a visible console, but it launches Windows PowerShell 5.1. Agents use PowerShell 7.

  ```powershell
  $pwshExe = (Get-ChildItem 'C:\Program Files\WindowsApps\Microsoft.PowerShell_*\pwsh.exe' | Select-Object -First 1).FullName
  $script = 'C:\Users\c_sia\Documents\GitHub\proj-sage\scripts\start_streamlit.ps1'
  $cmdLine = 'C:\Windows\System32\cmd.exe /c start "Project Sage" "' + $pwshExe + '" -NoExit -NoProfile -ExecutionPolicy Bypass -WorkingDirectory "C:\Users\c_sia\Documents\GitHub\proj-sage" -File "' + $script + '"'
  Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmdLine; CurrentDirectory = 'C:\Users\c_sia\Documents\GitHub\proj-sage' }
  ```

  `ReturnValue` 0 means the window was created. Stop an old server with `scripts\stop_project_sage.ps1` before starting a new one.

---

## Product rules (do not regress)

1. **Update docs after every turn** — `README.md`, `STARTUP.md`, `TROUBLESHOOTING.md`, **`CHANGELOG.md`** (required; see workspace `AGENTS.md`), this file when conventions change.
2. **Folder add creates the project tag** — default tag = folder basename (`suggest_tag_from_path`). Never silently attach a new folder to an unrelated Active project without the user opting in (“Attach to active project”).
3. **Uploads use Active project** only; require a selected tag.
4. **Local-only processing** — no cloud LLM/upload paths for indexed content. Sensitive: `.env` / `.env.*` stay on disk under `data/`.
5. **Supported files** — see `sage/config.py` + `sage/loaders.py`. Includes **`.jsonl`**. Use `is_env_file()` / `is_supported_file()`. Skip `SKIP_FILE_NAMES` sidecars.
6. **Coding notes (multi-project)** — central hub `GitHub\coding-notes\` (not log-sage-only). Tag **`coding-notes`** → that folder. Produced by log-sage `export_coding_notes.py` from `~/.grok/sessions/`. Do not add duplicate tags for the same folder.
7. **Clear Search** — clear widget state via a flag before the text_area is created (never mutate `search_query` after the widget instantiates).
8. **Chroma docs may be null** — coerce hit text before `.strip()`.
9. **“Error finding id” on search** = corrupted Chroma HNSW (not Ollama). Stop app → `scripts/rebuild_chroma.py` → restart. Do not re-ingest while Streamlit is open.
10. **Hybrid retrieval** — do not regress pure-embedding-only ranking for answers. Search path is `vectorstore.query` over-fetch → `sage/rerank.py` lexical/path boosts → TOP_K → grounded LLM (`sage/rag.py`). Prompt must forbid inventing flags and swapping related concepts (regime ≠ interval). If excerpts disagree, prefer `OPERATIONS.md` over CHANGELOG or older RUNNING.md tables.
11. **Engine tags** — `live-engine`, `swing-engine`, and `brk-out-engine` are separate folder sources under each repo's `sage-docs/`. Do not merge them back into `hyperliquid-bot`. `sage-docs` is a skipped directory on parent walks. `rhc_` files and `RHCREADME.md` / `RHCSETUP.md` stay out of the index.
12. **Status apps** — tags `bot-hlth-stat` (BOT-HOUSE :8507), `code-house-stat` (CODE-HOUSE :8507), and `log-sage` (:8502). Their current spec is each repo's root `OPERATIONS.md`. Do not register `net-comd-comp`, `pred-mkt-sage`, `sol-ms-bot`, `rh-agnt-trdg`, or `rh-agnt-engine` again unless the operator reopens them.
13. **Visible PowerShell 7 console** — The operator monitors Project Sage from a visible window titled **Project Sage**. Agents open it with `Win32_Process.Create`, `cmd /c start "Project Sage"`, and installed `pwsh.exe` (see Environment). Never attach the server to an agent background shell.
14. **One app, two processes** — The PowerShell console and a second `python.exe` are normal. `.venv\Scripts\python.exe` is a launcher; its child is `Python312\python.exe` with the same `streamlit` command. The child owns port 8504. Do not investigate this pair or kill one of them. A second Project Sage is a second listener on 8504, or a second venv launcher that is not the parent of the first. Workspace rule: root `AGENTS.md`, "One Python app, two processes".

---

## Agent hygiene

- Prefer project modules over scattering `_temp_*.py`; delete temps after use.
- PowerShell: here-strings / small scripts for anything with `$` or nested quotes (see root `Agents.md`).
- Do not invent monorepo packages shared with other GitHub projects.
- After user-facing changes, end with **What you should do** (reload/restart/verify bullets) when action matters.
- **CHANGELOG.md (required):** after every meaningful change, append a dated entry (what / why / verify) for Project Sage search; include **When:** `YYYY-MM-DD HH:MM PDT` or `PST`. Template and rules: workspace root `AGENTS.md`.

---

## What you should do (for the user, when relevant)

Agents: close implementation replies with a short action list, e.g.:

```markdown
## What you should do

- Restart Streamlit (or use Project Sage desktop shortcut)
- Hard-refresh the app window if UI looks stale
```
