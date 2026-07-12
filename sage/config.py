"""Paths and model defaults for Project Sage."""

from pathlib import Path

# Project root (repo folder)
ROOT = Path(__file__).resolve().parent.parent

# Persistent local data
DATA_DIR = ROOT / "data"
REGISTRY_PATH = DATA_DIR / "registry.json"
CHROMA_DIR = DATA_DIR / "chroma"
UPLOADS_DIR = DATA_DIR / "uploads"

# Ollama models (match local install)
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "qwen2.5:7b"
OLLAMA_HOST = "http://127.0.0.1:11434"

# Chunking
CHUNK_SIZE = 1200  # characters (~800 tokens-ish for mixed text)
CHUNK_OVERLAP = 200

# Retrieval
TOP_K = 6

# Supported source extensions
SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".pdf",
    ".csv",
    ".json",
    ".doc",
    ".docx",
}

# Directories to skip when walking local project folders
SKIP_DIR_NAMES = {
    ".git",
    ".svn",
    ".hg",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    ".idea",
    ".vscode",
    "dist",
    "build",
    ".eggs",
    "data",  # avoid re-ingesting Sage's own data if nested
    "chroma",
    ".chroma",
}


def ensure_data_dirs() -> None:
    """Create data directories if missing."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
