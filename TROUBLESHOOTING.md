# Project Sage — Troubleshooting

Quick fixes for the Streamlit desktop apps on this PC. For first-time setup and shortcuts, see [STARTUP.md](STARTUP.md).

---

## Port map (one app per port)

| Port | App | Start | Stop |
|------|-----|-------|------|
| **8501** | hyperliquid-bot — Trading dashboard | hyperliquid-bot `launch.ps1 dashboard` | Close its Streamlit console |
| **8502** | log-sage — Log Sage | log-sage desktop shortcut | `log-sage\scripts\stop_log_sage.ps1` |
| **8503** | net-comd-comp | net-comd-comp Streamlit console | Close its Streamlit console |
| **8504** | **Project Sage** | **Project Sage Streamlit** shortcut | `.\scripts\stop_project_sage.ps1` |

---

## Status at a glance (start here)

**Command:** `.\scripts\show_running.ps1` — quick health check for all four Streamlit apps on this PC (`:8501`–`:8504`).

**When to use it:**

- Before starting Project Sage — confirm `:8504` is **stopped** (avoid a duplicate server).
- After starting or restarting — confirm `:8504` shows **RUNNING** and note the PID.
- Browser says “connection lost” but you are not sure the server died — if `:8504` is **stopped**, the console closed or crashed; if **RUNNING**, refresh the browser or restart the Streamlit console.
- You suspect duplicate instances (e.g. log-sage “running twice”) — **one row per port**; one `RUNNING` on `:8502` = one Log Sage.
- Any time you are unsure which dashboard ports are in use.

```powershell
cd C:\Users\c_sia\Documents\GitHub\proj-sage
.\scripts\show_running.ps1
```

More detail (parent PowerShell → streamlit → python PIDs):

```powershell
.\scripts\show_running.ps1 -Details
```

Example output:

```
  :8501  Trading dashboard      RUNNING   PID 47488
  :8502  Log Sage               RUNNING   PID 30568
  :8503  net-comd-comp          RUNNING   PID 46712
  :8504  Project Sage           stopped

  Summary: 3 of 4 apps running
```

**One row = one app.** If `:8502` shows **RUNNING** once, you have **one** Log Sage. Windows may show **3–4 PIDs per app** in `-Details` — that is normal (powershell → streamlit → python), not duplicates.

---

## Desktop shortcuts: flash vs visible window

| Shortcut | What happens |
|----------|----------------|
| **Project Sage** | Opens Chrome/Edge app window. Starts Streamlit in a **second** console only if :8504 is down. Launcher window may flash and close — **that is OK**. |
| **Project Sage Streamlit** | PowerShell window **stays open** with Streamlit logs. **Use this** when you want a visible server console. |

**Closing the browser app does not stop the server.** Close the **Project Sage Streamlit** window (or run `stop_project_sage.ps1`).

**After code or config changes:** restart the **Streamlit console**, not just the browser. The launcher reuses an already-running server on :8504.

Refresh shortcuts after script updates:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_desktop_shortcuts.ps1
```

---

## Stop / restart Project Sage only

```powershell
.\scripts\stop_project_sage.ps1
.\scripts\start_streamlit.ps1
# or double-click **Project Sage Streamlit**
```

Confirm:

```powershell
.\scripts\show_running.ps1
# :8504 should show stopped, then RUNNING after start
```

---

## PowerShell error `0x800700e8` on launch

Caused by a malformed inline `powershell.exe -Command ...` (nested quotes). **Do not** paste long one-liners.

Use instead:

- Desktop shortcut **Project Sage Streamlit**, or
- `.\scripts\start_streamlit.ps1`

---

## Sidebar still shows `.log` in supported formats

The on-disk config is correct; the **old Streamlit process** was still in memory.

1. `.\scripts\stop_project_sage.ps1`
2. Start **Project Sage Streamlit** again
3. Ctrl+F5 in the app window

---

## Force ingest spins for hours (hyperliquid-bot)

**Cause:** Force ingest re-embeds **every** supported file through local Ollama, even if unchanged. `hyperliquid-bot` had **~250 files** indexed — mostly `backtest_results/*.csv` and `*.json` run artifacts (~1,300+ embedding chunks). That can take **30–90+ minutes** on CPU Ollama with little search value.

**Fix (after pulling latest Project Sage):**

1. `backtest_results/` and `archive/` are now **skipped** during folder walks (~22 doc files, ~80 chunks for hyperliquid-bot).
2. Embeddings are **batched** (32 chunks per Ollama call) instead of one call per chunk.
3. Stale `data/chroma/.write.lock` from a crashed ingest is auto-cleared when the owning PID is gone.

**What to use instead of Force ingest**

| Goal | Action |
|------|--------|
| Pick up edited `TROUBLESHOOTING.md`, `WEBHOOKS.md`, etc. | Sidebar **Ingest** on the hyperliquid-bot source (incremental — unchanged files skipped) |
| Watcher missed a OneDrive sync | Same — per-source **Ingest**, or wait for the 2‑min poll scan |
| Full rebuild after Chroma corruption | `rebuild_chroma.py`, then **Force ingest → This project** once |

**While a long Force ingest runs:** expand **Last ingest log** in the sidebar — filenames should advance. If the caption is frozen for 10+ minutes, check Ollama (`http://127.0.0.1:11434`) and remove a stale lock only if ingest is not running:

```powershell
cd C:\Users\c_sia\Documents\GitHub\proj-sage
Get-Content data\chroma\.write.lock   # PID holding the lock
.\scripts\stop_project_sage.ps1       # if you need to abort
Remove-Item data\chroma\.write.lock -ErrorAction SilentlyContinue
.\scripts\start_streamlit.ps1
```

**Rule:** Prefer per-source **Ingest** for doc updates. Reserve **Force ingest** for rare full rebuilds.

---

## Folder watcher / Last ingest not updating

The watcher runs **inside** the Streamlit process — not as a Windows service.

| Symptom | Fix |
|---------|-----|
| **Last ingest** stuck | **Force ingest → This project**, or enable **Auto-start watcher on launch** + **Restart** |
| Watcher **Stopped** after reopen | Enable auto-start; keep **Project Sage Streamlit** console open |
| OneDrive edits slow to appear | Wait up to **2 min** (poll scan on Windows), or click **Ingest** on the source |

Settings: `data/settings.json` (`watcher_auto_start`, `watcher_poll_scan_s`).

---

## Chroma error (`hnsw` / `compactor` / `Error loading hnsw index`)

Usually: **CLI ingest while Project Sage was open**, or OneDrive syncing `data/chroma/` mid-write.

1. Close Project Sage (`stop_project_sage.ps1` or Ctrl+C in Streamlit console).
2. Rebuild (backs up old index automatically):

```powershell
.\.venv\Scripts\python.exe scripts\rebuild_chroma.py
```

3. Relaunch Project Sage.

**Prevention:** use sidebar **Force ingest** while the app is open, or close the app before CLI ingest. Runtime `logs/` folders are skipped during ingest.

---

## Streamlit ImportError after pull / OneDrive sync

1. Stop Streamlit console (Ctrl+C).
2. Re-launch **Project Sage Streamlit**.
3. Hard-refresh app window (Ctrl+F5).

---

## Search / UI quirks

- **Clear Search** uses a session flag + rerun (Streamlit widget rule).
- Missing Chroma document text is normalized to `""` so answers do not crash on `None`.

---

## Streamlit exits with no console error

Silent return to the PowerShell prompt usually means a **hard kill** (OOM / native crash / CPU thrash) — not a normal Python traceback. Fans spinning hard right before exit is a strong clue.

**Check logs (new runs write here):**

| File | What it captures |
|------|------------------|
| `data/streamlit.log` | Full Streamlit console output (via `start_streamlit.ps1`) |
| `data/crash.log` | Uncaught Python exceptions |
| `data/faulthandler.log` | Segfaults / hard faults (`PYTHONFAULTHANDLER=1`) |
| `data/launcher.log` | Browser launcher only (not the server) |

```powershell
cd C:\Users\c_sia\Documents\GitHub\proj-sage
Get-Content data\streamlit.log -Tail 40
Get-Content data\crash.log -Tail 20 -ErrorAction SilentlyContinue
Get-Content data\faulthandler.log -Tail 20 -ErrorAction SilentlyContinue
```

**Common causes**

1. **Folder watcher CPU thrash (Windows)** — old builds used `PollingObserver` on every registered folder **including `venv/`**. With several GitHub repos under OneDrive that is **tens of thousands of files** scanned continuously → fans max out → Streamlit dies with no traceback. **Fix (current tree):** default is **poll-only** (`watcher_fs_observer: none` / `auto` on Windows) — smart scan of supported docs only, skips `venv`, `node_modules`, `logs`, etc. Confirm `data/settings.json` has `"watcher_fs_observer": "none"` (or `"auto"`) and `"watcher_auto_start": true` for live index updates. Never set `"polling"` on large trees. Restart Streamlit after changing settings.

   **Note:** Streamlit `[server] fileWatcherType` only hot-reloads **app code** (`app.py`). It does **not** control document auto-ingest. Keep `fileWatcherType = "none"` on OneDrive; document freshness still comes from the folder watcher poll (every ~120s, first scan ~30s after start).
2. **Chroma index corruption** — concurrent ingest + watcher poll, or OneDrive syncing `data/chroma/` mid-write. UI may show:
   - `Retrieval failed: … Error finding id` / `Error executing plan: Internal error`
   - Misleading “Is Ollama running with nomic-embed-text?” (older builds; Ollama is usually fine — **count can still show thousands of chunks** while HNSW query crashes).
   **Fix:** stop Project Sage → rebuild → restart:
   ```powershell
   .\scripts\stop_project_sage.ps1
   .\.venv\Scripts\python.exe scripts\rebuild_chroma.py
   .\scripts\start_streamlit.ps1
   ```
3. **Active project dropdown** — fixed in current `app.py` (stable `key="selected_tag"`). Restart after pull.
4. **Watcher auto-ingest during Force ingest** — poll scan and file-watch ingest skip when Chroma write lock is held. All Chroma reads/writes are serialized in-process (UI + watcher threads). Still avoid CLI ingest while the app is open.
5. **Closing the wrong window** — **Project Sage** shortcut only opens the browser; the server runs in **Project Sage Streamlit**. Closing that console stops :8504 with no error text.
6. **RAM pressure** — Project Sage + Ollama (`qwen2.5:7b` + embed) + trading dashboard + live engine. Close unused Streamlit apps (`show_running.ps1`) if the machine is thrashing.

**Restart with logging:**

```powershell
.\scripts\stop_project_sage.ps1
.\scripts\start_streamlit.ps1
.\scripts\show_running.ps1   # confirm :8504 RUNNING
```

---

## Active project dropdown kills Streamlit (silent exit to prompt)

**Symptom:** Changing **Active project** in the sidebar makes the Streamlit console return to the PowerShell prompt with little or no traceback. The browser then shows connection lost.

**Cause (Streamlit 1.59+):** The old code passed a changing `index=` into `st.selectbox` and also copied the value into `session_state`. In current Streamlit, `index` is part of the widget **element id**, so each selection created a *new* widget identity, desynced the frontend, and could tear down the server session. Concurrent Chroma `PersistentClient` instances (UI + folder watcher) made native crashes more likely.

**Fix (current tree):**

- Active project uses a stable `key="selected_tag"` (no per-run `index=`).
- Deferred tag changes (create / folder add / delete) use `_pending_selected_tag` so the widget key is never written *after* the selectbox is created.
- Chroma uses one process-wide client/collection.

**What to do:** pull/restart Project Sage (`stop_project_sage.ps1` then **Project Sage Streamlit**). If the console still dies with no Python error, rebuild Chroma once (index corruption can still hard-crash the process):

```powershell
.\scripts\stop_project_sage.ps1
.\.venv\Scripts\python.exe scripts\rebuild_chroma.py
.\scripts\start_streamlit.ps1
```

---

## Script reference

| Script | Purpose |
|--------|---------|
| `scripts/show_running.ps1` | **First check** — which apps are up on :8501–:8504 (use before/after start, after crashes) |
| `scripts/show_running.ps1 -Details` | Same, plus PID chains for running apps |
| `scripts/stop_project_sage.ps1` | Stop Project Sage (:8504) |
| `scripts/start_streamlit.ps1` | Start Project Sage console |
| `scripts/rebuild_chroma.py` | Fix corrupted vector index |
| `scripts/install_desktop_shortcuts.ps1` | Refresh Desktop shortcuts |