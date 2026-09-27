# CODE-HOUSE handoff — run Project Sage here

**Written on:** BOT-HOUSE-A7-MAX, 2026-09-27 11:35 PDT  
**For:** the agent setting up Project Sage on CODE-HOUSE-A7-MAX  
**App repo:** `proj-sage` (Streamlit + Ollama + Chroma). Port **8504**.  
**This file is the procedure.** Do the steps in order. Stop and tell the user if a check fails.

Project Sage is a local RAG app. It is not a trading bot. It does not place orders. Moving it off BOT-HOUSE is so Ollama embedding and `qwen2.5:7b` stop competing with the live engines.

---

## What you are building

| Piece | Where it runs |
| --- | --- |
| Streamlit `app.py`, Chroma, watcher | CODE-HOUSE only, from that machine's `proj-sage` clone |
| Ollama `qwen2.5:7b` + `nomic-embed-text` | CODE-HOUSE `http://127.0.0.1:11434` |
| Log Sage, trading engines, journals | Stay on BOT-HOUSE |
| Live files Sage must read | Three SMB folders exported from BOT-HOUSE (list below) |
| Git-tracked docs | CODE-HOUSE clones of those repos, after `git pull` |

One Project Sage process in the house. BOT-HOUSE port **8504 was not listening** at 11:31 PDT on 2026-09-27. Leave it that way. Do not start Sage there again after CODE-HOUSE is up.

Ollama on BOT-HOUSE stays up. Log Sage (port 8502) uses it. Do not point this app at BOT-HOUSE's Ollama. `sage/config.py` hardcodes `OLLAMA_HOST = http://127.0.0.1:11434`.

---

## Folders to share from BOT-HOUSE

Share these three folders, **read-only**, and no others. Measured 2026-09-27 from the live registry in `proj-sage/data/registry.json` plus a walk with `sage/loaders.py` skip rules.

| Share junction name | BOT-HOUSE path | Why a git clone is not enough |
| --- | --- | --- |
| `coding-notes` | `C:\Users\c_sia\Documents\GitHub\coding-notes` | Not a git repo. Live file `coding-notes.jsonl` (~2.1 MB) is rewritten by Log Sage about every 120 seconds from this host's `C:\Users\c_sia\.grok\sessions`. |
| `hyperliquid-bot` | `C:\Users\c_sia\Documents\GitHub\hyperliquid-bot` | 11 gitignored files Sage indexes, including root `.env` and the engine state JSON files. `liquidity_trend.json` is tracked but had uncommitted changes on BOT-HOUSE. |
| `rh-agnt-trdg` | `C:\Users\c_sia\Documents\GitHub\rh-agnt-trdg` | Gitignored `rh_agnt_trdg_state.json` (~10 KB) is the live Robinhood state Sage indexes. |

UNC root after the operator script below:

```text
\\BOT-HOUSE-A7-MAX\SageLive\coding-notes
\\BOT-HOUSE-A7-MAX\SageLive\hyperliquid-bot
\\BOT-HOUSE-A7-MAX\SageLive\rh-agnt-trdg
```

BOT-HOUSE Wi-Fi IPv4 on 2026-09-27 was **10.0.0.200** (manual address). Use the hostname if it resolves. If it does not, use `\\10.0.0.200\SageLive\...` for every registry path. Pick one spelling and keep it. Chunk ids are `project-tag::absolute-path::chunk-index`. A second spelling of the same folder duplicates the index.

### Live files inside those folders

Sage indexes these gitignored (or non-git) files today:

**coding-notes** (no `.git`):

- `coding-notes.jsonl` — canonical export, last write 2026-09-27 11:28 PDT (Log Sage is the writer)
- `coding-notes-A7_Max.jsonl` — frozen snapshot, 2026-07-25, 2.9 MB. Sage will embed it once because it sits in the folder. Optional, on BOT-HOUSE only: move `coding-notes-A7_Max.jsonl`, `coding_notes_state-A7_Max.json`, and `coding_notes_status-A7_Max.json` into `coding-notes\_archive\` (that directory name is already skipped). Do not delete them. Do not do this from CODE-HOUSE.
- `README.md`, `AGENTS.md`, `CHANGELOG.md`
- Exact names `coding_notes_state.json` and `coding_notes_status.json` are skipped. The `*-A7_Max` copies of those sidecars are not skipped.

**hyperliquid-bot** gitignored, all at the repo root:

- `.env` (secrets — Sage embeds this file)
- `engine_state.json`, `swing_engine_state.json`, `rhc_engine_state.json`, `regime_state.json`
- `rrp_cache.json`, `broad_usd_index_cache.json`, `dxy_cache.json`, `us10y_cache.json`, `fed_balance_sheet_cache.json`, `yield_curve_cache.json`

**rh-agnt-trdg**:

- `rh_agnt_trdg_state.json`

Poll cost of these three trees is small. With skip rules applied, the walker entered 1 directory in coding-notes (10 files listed), 3 directories in hyperliquid-bot (204 files listed), and 12 directories in rh-agnt-trdg (74 files listed). `venv`, `.venv`, `.git`, `logs`, `data`, `env`, and `node_modules` are pruned before descent.

---

## Folders that do not need a share

These registry sources are entirely git-tracked, and on 2026-09-27 each repo was clean and level with its origin. Point Sage at the CODE-HOUSE clone after `git pull`.

| Project tag | CODE-HOUSE path (confirm the clone root) |
| --- | --- |
| `proj-sage` | `C:\Users\c_sia\Documents\GitHub\proj-sage` |
| `demo-sage` | `C:\Users\c_sia\Documents\GitHub\proj-sage\sample_docs` |
| `log-sage` | `C:\Users\c_sia\Documents\GitHub\log-sage` |
| `net-comd-comp` | `C:\Users\c_sia\Documents\GitHub\net-comd-comp` |
| `pred-mkt-sage` | `C:\Users\c_sia\Documents\GitHub\pred-mkt-sage` |
| `bot-hlth-stat` | `C:\Users\c_sia\Documents\GitHub\bot-hlth-stat` |
| `sol-ms-bot` | `C:\Users\c_sia\Documents\GitHub\sol-ms-bot` |
| `brk-out-bot` | `C:\Users\c_sia\Documents\GitHub\brk-out-bot` |

If a clone is missing, stop and tell the user. Do not substitute the BOT-HOUSE copy over SMB for these, and do not clone extra repos beyond what the user already has unless they ask.

### Do not share, and do not copy onto CODE-HOUSE

- `proj-sage\data\` (Chroma, `registry.json`, logs). Paths inside the BOT-HOUSE index are `C:\Users\c_sia\...`. They will not match UNC paths. Build a new `data\` on CODE-HOUSE.
- Any `.venv` or `venv`. Create a new `.venv` on CODE-HOUSE.
- Bot `logs\` and `data\` journals (`trade_journal.jsonl` and similar). Sage skips those directories. Log Sage on BOT-HOUSE is the log search tool.
- The existing SMB share named `Users` (`C:\Users`, Everyone / Full). Do not register `\\BOT-HOUSE-A7-MAX\Users\...` as a Sage source.
- Admin shares `C$` and `ADMIN$`.

`env\.env` for Robinhood, breakout, and Solana sits under a directory named `env`, which Sage skips. Sharing `rh-agnt-trdg` still exposes `env\.env` to anyone who can read the share, even though Sage will not embed it. The share stays read-only and limited to `c_sia`.

---

## What Sage indexes

Extensions: `.txt`, `.md`, `.markdown`, `.pdf`, `.csv`, `.json`, `.jsonl`, `.yaml`, `.yml`, `.env`, `.doc`, `.docx`.

Not indexed: `.py`, `.log`, anything under `logs`, `data`, `venv`, `.venv`, `env`, `node_modules`, `.git`, `backtest_results`, `archive`, `exports`, `_archive`, or a directory whose name starts with `.`.

Corpus size on 2026-09-27: about 108 files, about 6 MB of text. The heavy part is re-embedding `coding-notes.jsonl`, not walking the trees.

Log Sage export (`auto_export_seconds: 120` in `log-sage/config.yaml`) rewrites `coding-notes.jsonl` from scratch every cycle and stamps CLI/Telegram reference notes with the current time. The file hash changes even when no new Grok session arrived. The Sage watcher (poll every 120s) will re-embed that file on CODE-HOUSE whenever the hash changes. That periodic Ollama spike is the load being moved. It is expected. Do not flip the watcher to `polling` or `native` to chase it.

CODE-HOUSE has its own `C:\Users\c_sia\.grok\sessions`. Those sessions are not in the BOT-HOUSE JSONL. Do not run a second exporter against the same `coding-notes.jsonl` (two writers will corrupt it). Log Sage on BOT-HOUSE is the only writer.

---

## Step 0 — operator on BOT-HOUSE (you cannot do this from CODE-HOUSE)

**Status (2026-09-27):** done on BOT-HOUSE. `C:\Users\c_sia\Documents\SageLive` exists with three junctions, and SMB share `SageLive` is read-only for `BOT-HOUSE-A7-MA\c_sia`. A normal window cannot create shares: `New-SmbShare` returns `Access is denied` even though `c_sia` is an administrator, because UAC filters that token. The share command has to run in a process that says Administrator.

Skip the recreate block if this already opens:

```powershell
Get-ChildItem \\BOT-HOUSE-A7-MAX\SageLive\coding-notes\coding-notes.jsonl
```

Names on this PC:

| Use this | Value |
| --- | --- |
| DNS hostname | `BOT-HOUSE-A7-MAX` |
| NetBIOS name (15-character limit) | `BOT-HOUSE-A7-MA` |
| Share login | `BOT-HOUSE-A7-MA\c_sia` |
| Wi-Fi IPv4 (2026-09-27, manual) | `10.0.0.200` |

`net use /user:BOT-HOUSE-A7-MAX\c_sia` is the wrong account name. The Windows logon domain is the NetBIOS name.

### Recreate only if the share is missing

Junctions (normal PowerShell 7 window):

```powershell
$root = "C:\Users\c_sia\Documents\SageLive"
New-Item -ItemType Directory -Force -Path $root | Out-Null
$links = @{
  "coding-notes"    = "C:\Users\c_sia\Documents\GitHub\coding-notes"
  "hyperliquid-bot" = "C:\Users\c_sia\Documents\GitHub\hyperliquid-bot"
  "rh-agnt-trdg"    = "C:\Users\c_sia\Documents\GitHub\rh-agnt-trdg"
}
foreach ($name in $links.Keys) {
  $dest = Join-Path $root $name
  if (-not (Test-Path -LiteralPath $dest)) {
    New-Item -ItemType Junction -Path $dest -Target $links[$name] | Out-Null
  }
}
```

Share (PowerShell 7 **Run as administrator**):

```powershell
$root = "C:\Users\c_sia\Documents\SageLive"
$existing = Get-SmbShare -Name SageLive -ErrorAction SilentlyContinue
if (-not $existing) {
  New-SmbShare -Name SageLive -Path $root -ReadAccess "c_sia" -Description "Project Sage read-only live folders" | Out-Null
}
$access = @(Get-SmbShareAccess -Name SageLive)
foreach ($row in $access) {
  if ($row.AccountName -eq "Everyone") {
    Revoke-SmbShareAccess -Name SageLive -AccountName Everyone -Force | Out-Null
  }
}
Get-SmbShareAccess -Name SageLive | Format-Table Name, AccountName, AccessControlType, AccessRight -AutoSize
```

Expected ACL: `BOT-HOUSE-A7-MA\c_sia` Allow Read, and no Everyone row.

Wi-Fi profile `Insane67` is Private, and inbound File and Printer Sharing (SMB-In) is allowed on Private. Hotspot Shield stays installed; do not disable it. The share has to answer on `10.0.0.200`, not through the VPN adapter.

From CODE-HOUSE, a successful check lists `coding-notes.jsonl`. Try the DNS name, then the NetBIOS name, then the IP. Register folder sources with whichever spelling answers, and use that same spelling for every path:

```powershell
Get-ChildItem \\BOT-HOUSE-A7-MAX\SageLive\coding-notes\coding-notes.jsonl
Get-ChildItem \\BOT-HOUSE-A7-MA\SageLive\coding-notes\coding-notes.jsonl
Get-ChildItem \\10.0.0.200\SageLive\coding-notes\coding-notes.jsonl
```

If all three fail, stop. Do not ingest via the `Users` share.

Map the share as the same Windows user who will launch Streamlit (interactive logon, not a service account):

```powershell
net use \\BOT-HOUSE-A7-MAX\SageLive /user:BOT-HOUSE-A7-MA\c_sia /persistent:yes
```

Let Windows prompt for the BOT-HOUSE password. Do not invent one, and do not write it into a file. If the DNS name does not resolve from CODE-HOUSE, use `\\10.0.0.200\SageLive` or `\\BOT-HOUSE-A7-MA\SageLive` in that command and in the registry.

---

## Step 1 — app checkout on CODE-HOUSE

```powershell
cd C:\Users\c_sia\Documents\GitHub\proj-sage
git status -sb
git pull
```

Confirm the machine name is CODE-HOUSE. Confirm you are not inside a BOT-HOUSE path over SMB. The app directory is the local clone.

If `git pull` does not contain this handoff yet, the file was written on BOT-HOUSE and still needs a commit and push from there. You can read it directly while the share is up:

```text
\\BOT-HOUSE-A7-MAX\Users\c_sia\Documents\GitHub\proj-sage\CODE-HOUSE-HANDOFF.md
```

That `Users` path is only for reading this document. Do not add it as a folder source.

Create the venv if `.venv\Scripts\python.exe` is missing. Python 3.12. Venv folder name is `.venv`, not `venv`.

```powershell
cd C:\Users\c_sia\Documents\GitHub\proj-sage
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## Step 2 — bind the UI to localhost

`.streamlit\config.toml` should contain:

```toml
[server]
port = 8504
address = "127.0.0.1"
headless = true
fileWatcherType = "none"
```

The repo on BOT-HOUSE was updated 2026-09-27 to set `address = "127.0.0.1"`. After `git pull`, confirm the line is present. The Streamlit default with no address is `0.0.0.0` (this install binds IPv6 `::`), which would publish an index that contains `hyperliquid-bot\.env`.

Keep `fileWatcherType = "none"`. That setting is Streamlit's own reload watcher. Document ingest is `sage/watcher.py`.

---

## Step 3 — local Ollama

```powershell
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

`nomic-embed-text:latest` satisfies the model name `nomic-embed-text`. Confirm:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

Both names must appear. Models already present on BOT-HOUSE do not transfer.

---

## Step 4 — settings, then one folder source per tag

Write `proj-sage\data\settings.json` before the first start (the directory is created on first launch if you would rather set these in the sidebar):

```json
{
  "watcher_auto_start": true,
  "watcher_poll_scan_s": 120,
  "watcher_fs_observer": "none"
}
```

`none` is poll-only: supported files every 120 seconds, skip `venv` / `logs` / `data`. On Windows, `auto` also resolves to poll-only. Values `polling` and `native` are rejected for this move. `polling` is the CPU-heavy watchdog observer.

Start the server only after the share lists files:

```powershell
cd C:\Users\c_sia\Documents\GitHub\proj-sage
.\scripts\start_streamlit.ps1
```

Open `http://127.0.0.1:8504`. In the sidebar, add each folder once. The default tag is the leaf folder name. Leave "Attach to active project" unchecked. Tags must match the table exactly.

| Tag | Folder to add |
| --- | --- |
| `coding-notes` | `\\BOT-HOUSE-A7-MAX\SageLive\coding-notes` |
| `hyperliquid-bot` | `\\BOT-HOUSE-A7-MAX\SageLive\hyperliquid-bot` |
| `rh-agnt-trdg` | `\\BOT-HOUSE-A7-MAX\SageLive\rh-agnt-trdg` |
| `proj-sage` | `C:\Users\c_sia\Documents\GitHub\proj-sage` |
| `demo-sage` | `C:\Users\c_sia\Documents\GitHub\proj-sage\sample_docs` |
| `log-sage` | `C:\Users\c_sia\Documents\GitHub\log-sage` |
| `net-comd-comp` | `C:\Users\c_sia\Documents\GitHub\net-comd-comp` |
| `pred-mkt-sage` | `C:\Users\c_sia\Documents\GitHub\pred-mkt-sage` |
| `bot-hlth-stat` | `C:\Users\c_sia\Documents\GitHub\bot-hlth-stat` |
| `sol-ms-bot` | `C:\Users\c_sia\Documents\GitHub\sol-ms-bot` |
| `brk-out-bot` | `C:\Users\c_sia\Documents\GitHub\brk-out-bot` |

Do not also add the local `hyperliquid-bot`, `rh-agnt-trdg`, or `coding-notes` clones. Two copies of the same docs under one tag make search return a mix of live BOT-HOUSE state and a stale checkout.

If the clone root is not `C:\Users\c_sia\Documents\GitHub`, use the real local path for the eight git-backed tags. Keep the three SageLive paths as UNC.

Adding a folder ingests it. After all eleven exist, use **Force ingest** on each tag once so the file counts settle. Expect the first `coding-notes` embed to take several minutes (`coding-notes.jsonl` plus the July snapshot).

Rough file counts from the BOT-HOUSE disk on 2026-09-27 (proj-sage grows by one after this handoff is in the clone):

| Tag | Files |
| --- | ---: |
| coding-notes | 7 |
| hyperliquid-bot | 35 |
| rh-agnt-trdg | 12 |
| proj-sage | 10 |
| demo-sage | 2 |
| log-sage | 7 |
| net-comd-comp | 6 |
| pred-mkt-sage | 7 |
| bot-hlth-stat | 6 |
| sol-ms-bot | 10 |
| brk-out-bot | 7 |

Watcher status text should include `poll-only` and `scan every 120s`. It should not say `polling observer`.

Desktop shortcuts, after the venv exists:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_desktop_shortcuts.ps1
```

---

## Step 5 — prove it

1. `.\scripts\show_running.ps1` shows Project Sage **RUNNING** on port 8504. Listen address is `127.0.0.1` only (`Get-NetTCPConnection -LocalPort 8504 -State Listen`).
2. Sidebar watcher line says poll-only, 11 folder sources (or the count of folders that actually resolved).
3. Search filtered to `coding-notes` for a phrase you can see in `coding-notes.jsonl` (a project name such as `hyperliquid-bot` is enough). The cited path starts with the UNC share.
4. Search filtered to `hyperliquid-bot` for `poll_interval_sec` or `engine_state`. The cited path is the UNC share, not `C:\Users\c_sia\Documents\GitHub\hyperliquid-bot` on CODE-HOUSE.
5. Search filtered to `brk-out-bot` for a heading in that repo's `STARTUP.md`. The cited path is the local clone.
6. Ask one natural-language question with Ollama up. An answer with sources counts as success. Stop the server if the console dies during ingest; see `TROUBLESHOOTING.md` ("Add folder source kills Streamlit" and "Error finding id"). Rebuild command, only while Streamlit is stopped: `.\.venv\Scripts\python.exe scripts\rebuild_chroma.py`.

---

## Constraints

- Do not run Project Sage on BOT-HOUSE and CODE-HOUSE together.
- Do not start trading bots, Log Sage, or other Streamlit apps on CODE-HOUSE as part of this setup.
- Do not copy `data\chroma` or `data\registry.json` from BOT-HOUSE.
- Do not set `watcher_fs_observer` to `polling` or `native`.
- Do not register both a UNC path and a local clone for the same tag.
- Do not commit `data\`, `.env`, or `.venv`.
- Do not edit files on the SageLive share. It is a read-only view of the running host. Log Sage is mid-write on `coding-notes.jsonl` every couple of minutes. A poll that hits a torn write should fail that file and succeed on the next scan. Do not "fix" a single torn read by copying the JSONL into the clone.
- Do not disable Hotspot Shield on BOT-HOUSE.
- Do not expose port 8504 past `127.0.0.1`.

---

## Later pulls

Git-backed tags go stale until someone `git pull`s those clones on CODE-HOUSE. The three SageLive tags update through the watcher without a pull.

After a future push from either machine, pull the local clones. Force-ingest a tag only when a pull changed its docs and the watcher has not picked them up.

If a share path has to change (hostname vs IP), stop Streamlit and run `scripts\rebuild_chroma.py` after the registry points at the new paths. Leaving the old path strings in Chroma orphans chunks.
