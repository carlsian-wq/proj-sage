# CHANGELOG — proj-sage

Project-specific change history for Project Sage (local RAG / Streamlit doc search, port **8504**, Ollama + Chroma).  
Written for humans and for **Project Sage** semantic search (this project indexes itself including this file). Newest first.  
Agents: append after every meaningful change (workspace `AGENTS.md`).

Entries must include **When:** with Pacific wall time and **PDT** or **PST** (BOT-HOUSE operator zone). Newest first.


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
