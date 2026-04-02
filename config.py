# config.py
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT_DIR    = Path(__file__).parent
DATA_DIR    = ROOT_DIR / "data_clean"
CHROMA_DIR  = ROOT_DIR / "chroma_db"

# ── Chroma ─────────────────────────────────────────────────────────────────
COLLECTION_NAME = "rag_collection"

# ── Chunking ───────────────────────────────────────────────────────────────
CHUNK_SIZE    = 1000
CHUNK_OVERLAP = 200

# ── Retrieval ──────────────────────────────────────────────────────────────
TOP_K = 6

# ── Models ─────────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "gemini-embedding-001"
FALLBACK_MODELS = [
    #"models/gemini-2.5-pro",                  # smartest stable, try first
    #"models/gemini-3.1-pro-preview",          # smart but hits limit fast
    "models/gemini-3-flash-preview",          # good balance
    "models/gemini-2.5-flash",                # reliable
    "models/gemini-3.1-flash-lite-preview",   # most generous quota, proven
    "models/gemini-2.5-flash-lite",           # fallback
]
LLM_MODEL = "models/gemini-2.5-flash-lite"
LLM_TEMPERATURE = 0.2