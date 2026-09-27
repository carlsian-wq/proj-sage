# CHANGELOG — proj-sage

Project-specific change history for Project Sage (local RAG / Streamlit doc search, port **8504**, Ollama + Chroma).  
Written for humans and for **Project Sage** semantic search (this project indexes itself including this file). Newest first.  
Agents: append after every meaningful change (workspace `AGENTS.md`).

Entries must include **When:** with Pacific wall time and **PDT** or **PST** (BOT-HOUSE operator zone). Newest first.


---

## 2026-09-27 — SageLive share created (New-SmbShare needs elevation)

**Project:** `proj-sage`
**When:** 2026-09-27 11:49 PDT
**Summary:** The read-only `SageLive` share is up on BOT-HOUSE. The first `New-SmbShare` failed with `Access is denied` because the PowerShell window was not elevated. UAC filters the administrator token even for `c_sia`.

**Details:**
- Junctions under `C:\Users\c_sia\Documents\SageLive` were already created by the non-elevated script: `coding-notes`, `hyperliquid-bot`, `rh-agnt-trdg`.
- Elevated `New-SmbShare -Name SageLive -ReadAccess c_sia` succeeded. ACL is `BOT-HOUSE-A7-MA\c_sia` Allow Read. No Everyone entry.
- Windows NetBIOS name is `BOT-HOUSE-A7-MA` (15 characters). DNS hostname remains `BOT-HOUSE-A7-MAX`. Share login from CODE-HOUSE is `BOT-HOUSE-A7-MA\c_sia`.
- Local UNC checks succeeded for `coding-notes.jsonl`, `hyperliquid-bot\config.yaml`, and `rh-agnt-trdg\rh_agnt_trdg_state.json`, including through the junctions.
- Wi-Fi `Insane67` is Private and File and Printer Sharing (SMB-In) is allowed on Private.

**Verify / operate:**
- `Get-SmbShare -Name SageLive` shows path `C:\Users\c_sia\Documents\SageLive`.
- From CODE-HOUSE: `Get-ChildItem \\BOT-HOUSE-A7-MAX\SageLive\coding-notes\coding-notes.jsonl` (fallback `\\BOT-HOUSE-A7-MA\...` or `\\10.0.0.200\...`).
- `net use \\BOT-HOUSE-A7-MAX\SageLive /user:BOT-HOUSE-A7-MA\c_sia /persistent:yes`

**Files:** `CODE-HOUSE-HANDOFF.md`, `CHANGELOG.md`

---

## 2026-09-27 — CODE-HOUSE handoff for live-folder SMB ingest

**Project:** `proj-sage`
**When:** 2026-09-27 11:35 PDT
**Summary:** Project Sage should run on CODE-HOUSE so Ollama stops competing with the BOT-HOUSE trading engines. A handoff lists the three BOT-HOUSE folders that must be shared read-only, and the git-tracked repos that stay as local clones. Streamlit now binds to 127.0.0.1 because the index can contain hyperliquid-bot `.env`.

**Details:**
- Measured the live registry (11 folder sources) and walked them with `sage/loaders.py` skip rules. About 108 supported files, about 6 MB of text. Python, `logs\`, and `data\` journals are not indexed.
- Must share from BOT-HOUSE: `coding-notes` (not a git repo; `coding-notes.jsonl` is rewritten by Log Sage every ~120s), `hyperliquid-bot` (gitignored engine state JSON plus root `.env`; `liquidity_trend.json` was dirty), `rh-agnt-trdg` (`rh_agnt_trdg_state.json`).
- Fully git-tracked and level with origin on this date, so CODE-HOUSE clones are enough: `proj-sage`, `sample_docs` (`demo-sage`), `log-sage`, `net-comd-comp`, `pred-mkt-sage`, `bot-hlth-stat`, `sol-ms-bot`, `brk-out-bot`.
- Do not copy `data\chroma` or `registry.json`. Chunk ids embed the absolute path. One spelling of each UNC path.
- `.streamlit/config.toml` sets `address = "127.0.0.1"`. The previous default listened on all interfaces.
- Port 8504 was not listening on BOT-HOUSE at measurement time. Ollama on BOT-HOUSE stays for Log Sage. CODE-HOUSE runs its own Ollama.

**Verify / operate:**
- On BOT-HOUSE, create the read-only `SageLive` share as written in `CODE-HOUSE-HANDOFF.md`.
- On CODE-HOUSE, `git pull`, confirm `address = "127.0.0.1"`, install `.venv`, `ollama pull qwen2.5:7b` and `nomic-embed-text`, add the eleven folder sources, Force ingest.
- `Get-NetTCPConnection -LocalPort 8504` shows 127.0.0.1. Watcher status says poll-only. A coding-notes hit cites the UNC path.

**Files:** `CODE-HOUSE-HANDOFF.md`, `.streamlit/config.toml`, `STARTUP.md`, `README.md`, `AGENTS.md`, `CHANGELOG.md`

---

## 2026-08-01 — Add folder source no longer kills Streamlit (Chroma race)

**Project:** `proj-sage`
**When:** 2026-08-01 13:35 PDT
**Summary:** Fix silent Streamlit exit when loading a new project via **Add folder source**. UI ingest and the folder watcher no longer hit Chroma at the same time; poll-only mode no longer hard-restarts the watcher after each folder add.

**Details:**
- Symptom: paste folder path → Add folder source → browser “connection lost”, console returns to prompt with little/no traceback. `data/faulthandler.log` showed `Windows fatal exception: access violation` in chromadb `_upsert` concurrent with UI `_count`.
- Root cause: UI folder ingest + auto-start poll scanner (and a short `watcher.restart()` join) raced on the same PersistentClient/HNSW index; native crash kills the process.
- `sage/watcher.py`: `ui_ingest_exclusive()` gate shared with poll/FS ingest; generation id so timed-out poll threads exit; longer stop join + gate drain; `note_sources_changed()` soft-refresh for poll-only (no restart).
- `app.py`: wrap folder add, upload, force ingest, per-source ingest, and delete with exclusive gate; call `note_sources_changed` / auto-start after registry change instead of `restart()`; migrate remaining `use_container_width` → `width="stretch"`.
- Documented in TROUBLESHOOTING under “Add folder source kills Streamlit”.

**Verify / operate:**
- Restart Streamlit: `.\scripts\stop_project_sage.ps1` then `.\scripts\start_streamlit.ps1` (or Project Sage Streamlit shortcut).
- Add a small folder (e.g. `sample_docs` or a project path). Expect success toast and non-zero chunk count; console must stay running.
- Confirm watcher status still shows poll-only after add (no need to Restart unless using native FS observer).

**Files:** `sage/watcher.py`, `app.py`, `TROUBLESHOOTING.md`, `CHANGELOG.md`

---

## 2026-07-30 — Hybrid re-rank + grounding fix for off-topic answers

**Project:** `proj-sage`
**When:** 2026-07-30 21:37 PDT
**Summary:** Fixed bad natural-language answers where semantic search alone ranked adjacent topics (e.g. live_engine **regime** / 1h trend) above the docs that actually answer the question (e.g. poll **interval** via `--interval` and `poll_interval_sec`). Answers now use hybrid retrieval and a stricter no-invention prompt.

**Details:**
- User asked (filter `hyperliquid-bot`): “how do I change the interval on live_engine.py startup?” Project Sage answered with `--regime bullish/bearish`, citing SETUP.md at score ~0.60 — wrong. Correct ops docs are in hyperliquid-bot `RUNNING.md` (`--interval` seconds, `poll_interval_sec` in config.yaml).
- Root cause: pure Chroma cosine retrieval + qwen2.5:7b over-generalizing from weak/adjacent excerpts; “interval” in everyday English is not the same embedding neighborhood as the technical key `poll_interval_sec`.
- Added `sage/rerank.py`: extract flags, filenames, snake_case tokens, and content words from the question; over-fetch semantic candidates; re-rank with lexical/path boosts; return TOP_K.
- `sage/rag.py`: candidate over-fetch (`CANDIDATE_MULTIPLIER` / `MIN_CANDIDATES`), hybrid re-rank, lower temperature (0.1), system prompt forbids inventing CLI flags and forbids swapping related concepts (regime ≠ interval).
- UI Sources expanders show hybrid score plus semantic/lexical breakdown.
- Unit-checked re-ranker: synthetic SETUP vs RUNNING vs ARCHIVE chunks for the interval query put **RUNNING.md first**.

**Verify / operate:**
- Restart Project Sage Streamlit (code change; not hot-reloaded for imports already in memory).
- With `hyperliquid-bot` indexed, search: `how do I change the interval on live_engine.py startup?`
- Expect answer mentioning `--interval` and/or `poll_interval_sec`, with RUNNING.md (or equivalent) in Sources — not only `--regime`.
- Offline re-rank smoke: `.\.venv\Scripts\python.exe -c "from sage.rerank import extract_query_terms; print(extract_query_terms('change interval on live_engine.py'))"`

**Files:** `sage/rerank.py`, `sage/rag.py`, `sage/config.py`, `app.py`, `README.md`, `TROUBLESHOOTING.md`, `CHANGELOG.md`

---

## 2026-07-28 — CODE-HOUSE .venv; OneDrive path cleanup

**Project:** `proj-sage`
**When:** 2026-07-28 22:00 PDT
**Summary:** Created project `.venv\` with chromadb/streamlit/ollama client deps on CODE-HOUSE. README/TROUBLESHOOTING paths no longer point at OneDrive. Ollama server + models still required before RAG ingest works.

**Details:**
- Uses **`.venv`** (not `venv`) per project AGENTS.
- Fresh Chroma/registry will be created on first run after Ollama is installed (`qwen2.5:7b`, `nomic-embed-text`).
- Independent of BOT-HOUSE index — re-ingest local folders when ready.

**Verify / operate:**
- `.\.venv\Scripts\python.exe -c "import streamlit, chromadb; print('ok')"`
- Install Ollama then pull models before full UI RAG tests.

**Files:** `.venv/` (local), `README.md`, `TROUBLESHOOTING.md`

---

## 2026-07-27 — Require Pacific PDT/PST timestamp on every CHANGELOG entry

**Project:** `proj-sage`
**When:** 2026-07-27 14:42 PDT
**Summary:** Every CHANGELOG entry in this project (and workspace-wide) must record a Pacific date/time with an explicit PDT or PST label so Project Sage and operators can order and search changes by local wall clock, not bare calendar dates or UTC-only stamps.

**Details:**
- Workspace root AGENTS.md template now requires a `**When:** YYYY-MM-DD HH:MM PDT` (or PST) field on every entry.
- Heading keeps `YYYY-MM-DD` (Pacific calendar day); body carries the full timestamp.
- Existing entries below were backfilled with approximate Pacific times where the original session day was known.

**Verify / operate:** Open this file and confirm the newest section has a **When:** line ending in PDT or PST. After the next project edit, agents must add a new timestamped section.

**Files:** `CHANGELOG.md`, workspace `AGENTS.md`, project `AGENTS.md`

---

## 2026-07-27 — Adopt project CHANGELOG.md for Project Sage search

**Project:** `proj-sage`  
**When:** 2026-07-27 14:30 PDT
**Summary:** CHANGELOG.md is now required in every workspace project; Project Sage AGENTS.md also lists CHANGELOG among docs to update each turn. Changelog prose is meant to be ingested so questions like “what fixed zero indexed chunks” hit this file. Workspace root AGENTS.md defines the entry template (summary, details, verify, files) optimized for semantic search.

**Verify / operate:** Force ingest or folder-watch the `proj-sage` path; search for “CHANGELOG” or a recent title phrase. After other projects change, their folders’ CHANGELOG.md should be re-ingested too.

**Files:** `CHANGELOG.md`, `AGENTS.md`, workspace `AGENTS.md`

---

## 2026-07-25–26 — Zero chunks after OneDrive dump; venv streamlit.proto; git repair

**Project:** `proj-sage`  
**When:** 2026-07-25 18:00 PDT
**Summary:** Streamlit failed on missing `streamlit.proto`; after fix the UI showed zero indexed chunks because `registry.json` was empty and source paths still pointed at deleted OneDrive folders.

**Details:**
- `.venv` had broken pip and incomplete streamlit; force-reinstalled requirements.
- Restored registry from `data/registry-A7_Max.json`, remapped `OneDrive\Documents\GitHub` → `Documents\GitHub`, ran `scripts/rebuild_chroma.py` (79 files, **3525 chunks**).
- STARTUP paths updated off OneDrive. Git invalid-object / logo.ico tree errors fixed by replacing `.git` and pushing STARTUP path fix.

**Verify / operate:** `.\scripts\start_streamlit.ps1` → http://localhost:8504; non-zero chunk count; search across project tags. Rebuild: stop Streamlit then `.\.venv\Scripts\python.exe scripts\rebuild_chroma.py`.

**Files:** `data/registry.json`, `scripts/rebuild_chroma.py`, `STARTUP.md`, `.venv`
