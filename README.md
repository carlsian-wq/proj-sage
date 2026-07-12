# Project Sage

Local **RAG search agent** for coding project documentation.

- **UI:** Streamlit  
- **LLM:** Ollama `qwen2.5:7b`  
- **Embeddings:** Ollama `nomic-embed-text`  
- **Vector store:** Chroma (on disk under `data/`)

Tag projects, point at local folders or upload files (`txt`, `md`, `pdf`, `csv`, `json`, `doc`, `docx`), auto-ingest on change, and ask natural-language questions with grounded answers + citations.

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

```powershell
.\.venv\Scripts\streamlit run app.py
```

Open the URL Streamlit prints (usually http://localhost:8501).

## How to use

1. **Create a project tag** in the sidebar (e.g. `my-api`).
2. **Add sources**
   - Paste a **local folder path** and click *Add folder source* (indexes all supported files; skips `.git`, `node_modules`, venvs, etc.), or
   - **Upload** files under that tag.
3. Ingest runs automatically on add; use **Force ingest** if you need a full rebuild.
4. Optionally **Start** the folder watcher so edits on disk re-embed automatically.
5. In the main panel, choose **All projects** or a tag filter, type a question, **Search**.

## Data layout

```
data/
  registry.json     # project tags + source metadata
  chroma/           # vector index
  uploads/          # files uploaded via the UI
```

Everything stays on your machine. `data/` is gitignored.

## Notes

- Legacy `.doc` extraction is best-effort; prefer `.docx` or `.pdf`.
- Ollama must be reachable at `http://127.0.0.1:11434`.
- First embed/search can be slow while models load into memory.

## Project layout

```
app.py              # Streamlit entrypoint
sage/
  config.py         # models, paths, extensions
  registry.py       # project/source registry
  loaders.py        # file text extraction
  chunking.py
  embeddings.py     # Ollama embeddings
  vectorstore.py    # Chroma
  ingest.py         # hash-aware ingest pipeline
  rag.py            # retrieve + answer
  watcher.py        # folder auto-ingest
```
