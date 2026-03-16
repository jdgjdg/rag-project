# config.py
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT_DIR    = Path(__file__).parent
DATA_DIR    = ROOT_DIR / "data"
CHROMA_DIR  = ROOT_DIR / "chroma_db"

# ── Chroma ─────────────────────────────────────────────────────────────────
COLLECTION_NAME = "rag_collection"

# ── Chunking ───────────────────────────────────────────────────────────────
CHUNK_SIZE    = 1000
CHUNK_OVERLAP = 200

# ── Retrieval ──────────────────────────────────────────────────────────────
TOP_K = 3

# ── Models ─────────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "gemini-embedding-001"
LLM_MODEL       = "models/gemini-2.0-flash-001"
LLM_TEMPERATURE = 0.2