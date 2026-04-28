# Database Course Assistant

A Retrieval-Augmented Generation (RAG) chatbot for a university database course. Students ask questions about course material; the system retrieves the most relevant lecture chunks and generates a concise, Socratic response — without giving away assignment answers.

---

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.10+ |
| Node.js / npm | 18+ |
| Google API Key | Gemini access required |

---

## Setup

### 1. Python environment

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Environment variable

Create a `.env` file at the project root:

```
GOOGLE_API_KEY=your_key_here
```

### 3. Build the vector database (first run only)

```bash
python ingest.py
```

This reads everything in `data_clean/`, chunks it, embeds it with Gemini, and stores it in `chroma_db/`. Can be interrupted and resumed — progress is saved in `embed_progress.json`.

### 4. Frontend

```bash
cd frontend/chat
npm install
```

---

## Running

### One command (Windows)

```bat
start.bat
```

Opens FastAPI on port 8000, Angular on port 4200, and launches the browser.

### Manually

Terminal 1 — backend:
```bash
.venv\Scripts\activate
uvicorn api:app --reload
```

Terminal 2 — frontend:
```bash
cd frontend/chat
npm start
```

Then open `http://localhost:4200`.

---

## Project structure

```
RAG project/
│
├── api.py                  # FastAPI server — single /query endpoint
├── chain.py                # RAG chain construction + model fallback logic
├── retriever.py            # Chroma vector DB connection + reranking
├── assignment_guard.py     # Detects assignment questions to prevent cheating
├── ingest.py               # Loads, chunks, and embeds documents → Chroma
├── query.py                # Standalone CLI for testing without the frontend
├── rewrite_transcripts.py  # One-time script: cleans raw transcripts with LLM
├── config.py               # All constants (models, paths, prompts, thresholds)
│
├── data/                   # Raw source material (PDFs + transcripts)
├── data_clean/             # Cleaned/processed data used for ingestion
├── chroma_db/              # Embedded vector index (built by ingest.py)
├── chroma_assignment/      # Embedded assignment questions (built on first run)
│
├── frontend/chat/          # Angular 19 chat UI
├── notebooks/              # Jupyter experimentation
│
├── requirements.txt        # Python dependencies
├── start.bat               # Windows one-click launcher
└── overview.html           # Visual architecture walkthrough (open in browser)
```

---

## Architecture overview

```
User (browser :4200)
    │  POST /query {question, history}
    ▼
FastAPI (api.py :8000)
    ├─ assignment_guard.py  ─── similarity search against assignment DB
    │                           returns True if score ≥ 0.80
    └─ chain.py
        ├─ retriever.py     ─── Chroma similarity search → top 6 chunks
        │                       → CrossEncoder rerank → top 3 chunks
        └─ Gemini LLM       ─── system prompt + context + history + question
            │                   fallback through 4 models on 429 errors
            └─ answer (+ sources, model name)
```

For a full visual walkthrough, open `overview.html` in a browser.

---

## Data pipeline

```
data/transcripts/  →  rewrite_transcripts.py  →  data_clean/transcripts/
data/pdfs/         →  (copied unchanged)       →  data_clean/pdfs/
data_clean/        →  ingest.py                →  chroma_db/
```

---

## Key design decisions

| Decision | Why |
|---|---|
| CrossEncoder reranking | Bi-encoder retrieval optimises for recall; reranking optimises for precision |
| Multi-query expansion | Overcomes embedding limitations for semantically distant paraphrases |
| 4-model fallback chain | Gemini free-tier models have per-minute quotas; fallback prevents downtime |
| Assignment vector DB | Separate index lets us tune the similarity threshold independently |
| Stateless backend | Conversation history is passed per-request; no server-side session needed |
