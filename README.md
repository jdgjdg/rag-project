# Database Course Assistant

A Retrieval-Augmented Generation (RAG) chatbot for a university database course. Students ask questions about course material; the system retrieves the most relevant lecture chunks and generates a concise, Socratic response — without giving away assignment answers.

Sign-in is required and restricted to `@rice.edu` Google accounts.

---

## Live deployment

| Component | URL |
|---|---|
| Frontend | https://poetic-puffpuff-a13e5c.netlify.app |
| Backend (Cloud Run) | https://rag-assistant-552296794218.us-central1.run.app |

GCP project: `ai-tutor-496718` · Region: `us-central1`

---

## Architecture

```
Student (browser — Netlify)
    │  POST /query  {question, history}  + Google ID token
    ▼
FastAPI (Cloud Run — api.py)
    ├─ verify_token()       ─── validates Google OAuth2 token, enforces @rice.edu
    ├─ assignment_guard.py  ─── similarity search against assignment DB (threshold 0.80)
    │                           → if match, adds CRITICAL OVERRIDE to system prompt
    └─ chain.py
        ├─ retriever.py     ─── Chroma similarity search → top 6 chunks
        │                       → CrossEncoder rerank → top 3 chunks
        └─ Gemini LLM       ─── system prompt + context + history + question
            │                   fallback through 4 models on 429 quota errors
            └─ answer (+ sources, model name)

ChromaDB (two collections)
    ├─ chroma_db/           ─── course material (built by ingest.py)
    └─ chroma_assignment/   ─── assignment questions (built on first load)
    Both stored in GCS bucket: gs://rag-assistant-db-ai-tutor/
    Downloaded to /tmp/ on Cloud Run startup; used from disk locally.
```

For a full visual walkthrough, open `overview.html` in a browser.

---

## Local development

### Prerequisites

| Tool | Version |
|---|---|
| Python | 3.10+ |
| Node.js / npm | 18+ |
| Google API Key | Gemini access required |

### 1. Python environment

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Environment variables

Create a `.env` file at the project root:

```
GOOGLE_API_KEY=your_key_here
```

### 3. Build the vector database (first run only)

```bash
python ingest.py
```

Reads everything in `data_clean/`, chunks it, embeds it with Gemini, and writes `chroma_db/`. Resumable — progress is saved in `embed_progress.json`.

The assignment question index (`chroma_assignment/`) is built automatically on first backend startup if it does not exist locally.

### 4. Frontend

```bash
cd frontend/chat
npm install
```

### 5. Run locally

One command (Windows):
```bat
start.bat
```

Or manually:

```bash
# Terminal 1 — backend
.venv\Scripts\activate
uvicorn api:app --reload

# Terminal 2 — frontend
cd frontend/chat
npm start
```

Open `http://localhost:4200`.

> **Note:** Google Sign-In works in production but the One Tap prompt may be blocked by browser extensions locally. You can temporarily disable the auth gate for local testing by commenting out `email = verify_token(http_request)` in `api.py`.

---

## Project structure

```
RAG project/
│
├── api.py                  # FastAPI server — /query endpoint + auth + startup
├── chain.py                # RAG chain + model fallback logic
├── retriever.py            # Chroma vector DB connection + CrossEncoder reranking
├── assignment_guard.py     # Detects assignment questions to prevent cheating
├── ingest.py               # Loads, chunks, embeds documents → chroma_db/
├── query.py                # CLI for testing without the frontend
├── rewrite_transcripts.py  # One-time script: cleans raw transcripts with LLM
├── config.py               # All constants (models, paths, prompts, thresholds)
│
├── data/                   # Raw source material (PDFs + transcripts)
├── data_clean/             # Cleaned data used for ingestion
├── chroma_db/              # Local vector index (built by ingest.py, excluded from Docker)
├── chroma_assignment/      # Local assignment index (auto-built, excluded from Docker)
│
├── frontend/chat/          # Angular 19 chat UI
├── notebooks/              # Jupyter experimentation
│
├── Dockerfile              # Cloud Run image
├── .dockerignore           # Excludes chroma_db/, chroma_assignment/, data/, .env
├── env.yaml                # Cloud Run environment variables (GOOGLE_API_KEY)
├── requirements.txt        # Python dependencies
├── start.bat               # Windows one-click local launcher
└── overview.html           # Visual architecture walkthrough
```

---

## Updating the course material (new documents or re-ingest)

1. Add or update files in `data_clean/`.
2. Delete the old index so it gets rebuilt from scratch:
   ```bash
   rm -rf chroma_db/
   ```
3. Run ingestion:
   ```bash
   python ingest.py
   ```
4. Upload the new index to GCS so Cloud Run picks it up:
   ```bash
   gcloud storage cp -r chroma_db/ gs://rag-assistant-db-ai-tutor/chroma_db/
   ```
5. Redeploy the backend (see below) — or simply restart the Cloud Run service so it re-downloads from GCS on next cold start.

To update assignment questions, edit `data_clean/assignment_questions_clean.txt`, then:
```bash
rm -rf chroma_assignment/
gcloud storage cp -r chroma_assignment/ gs://rag-assistant-db-ai-tutor/chroma_assignment/
```
The assignment index is rebuilt automatically on next backend startup if the directory does not exist.

---

## Redeploying the backend

From the project root (not `frontend/chat/`):

```bash
gcloud run deploy rag-assistant \
  --source . \
  --region us-central1 \
  --memory 4Gi \
  --env-vars-file env.yaml
```

`env.yaml` must contain:
```yaml
GOOGLE_API_KEY: "your_key_here"
```

Cloud Run will build the Docker image, push it to Artifact Registry, and deploy. The new revision downloads ChromaDB from GCS on first startup.

**Important:** `chroma_db/`, `chroma_assignment/`, and `data_clean/` are excluded via `.dockerignore`. The databases are never baked into the image — they always come from GCS at runtime.

---

## Redeploying the frontend

The frontend is a static Angular build hosted on Netlify.

```bash
cd frontend/chat
npm run build          # output goes to dist/chat/browser/
```

Then drag-and-drop the `dist/chat/browser/` folder onto the Netlify site dashboard, or use:
```bash
netlify deploy --prod --dir dist/chat/browser
```

If you change the backend URL, update the `http.post(...)` call in [frontend/chat/src/app/app.component.ts](frontend/chat/src/app/app.component.ts) (line ~221) and add the new frontend origin to the `allow_origins` list in [api.py](api.py).

---

## Key configuration (`config.py`)

| Constant | What it controls |
|---|---|
| `FALLBACK_MODELS` | Ordered list of Gemini models tried on 429 quota errors |
| `SIMILARITY_THRESHOLD` | Cosine similarity score (0–1) above which a question is treated as an assignment question (default 0.80) |
| `TOP_K` / `RERANK_TOP_N` | Chunks retrieved (6) and kept after reranking (3) |
| `SYSTEM_PROMPT` | Tutor persona, guardrails, Socratic protocol, KaTeX instruction |
| `CHROMA_DIR` | Automatically `/tmp/chroma_db` on Cloud Run, `./chroma_db` locally |

---

## Key design decisions

| Decision | Why |
|---|---|
| ChromaDB on GCS | Cloud Run's container scanner rejects images with binary/pickle files (`.bin`, `.pickle`); storing the DB in GCS and downloading at startup avoids this |
| CrossEncoder reranking | Bi-encoder retrieval maximises recall; reranking maximises precision |
| Multi-query expansion | Overcomes embedding limitations for semantically distant paraphrases |
| 4-model fallback chain | Gemini free-tier models have per-minute quotas; fallback prevents downtime |
| Assignment vector DB | Separate index lets us tune the similarity threshold independently |
| Stateless backend | Conversation history is passed per-request; no server-side session state |
| KaTeX math rendering | System prompt instructs the LLM to wrap expressions in `$...$` / `$$...$$`; frontend renders them via KaTeX — essential for relational algebra notation |
| Google Sign-In (NgZone) | Sign-in callback runs outside Angular's change detection; `ngZone.run()` is required to trigger re-render after token is received |
| Rice-only auth | `verify_token()` in `api.py` enforces `@rice.edu` email domain; change or remove this check to open access |
