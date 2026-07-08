import json
import os
import threading
from queue import Queue
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager

from retriever import load_vectordb, get_retriever
from chain import invoke_with_fallback
from assignment_guard import load_assignment_db, is_assignment_question

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from fastapi import Request, HTTPException

from config import CHROMA_DIR, ASSIGNMENT_CHROMA_DIR

GCS_BUCKET = "rag-assistant-db-ai-tutor"

def _download_from_gcs(prefix: str, local_path: Path) -> None:
    if local_path.exists():
        return
    from google.cloud import storage as gcs_storage
    print(f"  [startup] Downloading gs://{GCS_BUCKET}/{prefix} ...")
    client = gcs_storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blobs = list(bucket.list_blobs(prefix=prefix))
    local_path.mkdir(parents=True, exist_ok=True)
    for blob in blobs:
        if blob.name.endswith("/"):
            continue
        dest = local_path / blob.name[len(prefix):]
        dest.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(dest))
    print(f"  [startup] Done ({len(blobs)} files → {local_path})")

GOOGLE_CLIENT_ID = "552296794218-rs88k3i25s97snuomulfnurpfd36bct6.apps.googleusercontent.com"

def verify_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    
    token = auth_header.split(" ")[1]
    
    try:
        payload = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
        email = payload.get("email", "")
        if not email.endswith("@rice.edu"):
            raise HTTPException(status_code=403, detail="Must use Rice University account")
        return email
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    
# ── Startup: load vectordb and chain once ──────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("K_SERVICE"):
        _download_from_gcs("chroma_db/", CHROMA_DIR)
        _download_from_gcs("chroma_assignment/", ASSIGNMENT_CHROMA_DIR)
    vectordb = load_vectordb()
    app.state.retriever_simple = get_retriever(vectordb, queries=1)
    app.state.retriever_multi = get_retriever(vectordb, queries=3)
    app.state.exhausted_models = set()
    app.state.assignment_db = load_assignment_db()
    yield

app = FastAPI(lifespan=lifespan)

# ── CORS: allows Angular (localhost:4200) to talk to this server ───────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "https://rag-assistant-552296794218.us-central1.run.app",
        "https://poetic-puffpuff-a13e5c.netlify.app"
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request/Response shapes ────────────────────────────────────────────────
class MessageHistory(BaseModel):
    role: str
    content: str

class QuestionRequest(BaseModel):
    question: str
    history: list[MessageHistory] = []
    image: str | None = None
    imageType: str | None = None

# ── Endpoint ───────────────────────────────────────────────────────────────
@app.post("/query")
def query(request: QuestionRequest, http_request: Request):
    email = verify_token(http_request)
    print(f"  [user] {email}")
    history = [{"role": m.role, "content": m.content} for m in request.history]

    is_assignment, matched = is_assignment_question(
        request.question,
        app.state.assignment_db
    )

    progress_queue: Queue[object] = Queue()

    def _format_sse(event: str, data: str) -> str:
        return f"event: {event}\ndata: {data}\n\n"

    def progress(stage: str) -> None:
        payload = {"stage": stage}
        progress_queue.put(_format_sse("progress", json.dumps(payload)))

    def worker() -> None: 
        try:
            answer, model_used = invoke_with_fallback(
                app.state.retriever_simple,
                app.state.retriever_multi,
                request.question,
                app.state.exhausted_models,
                history,
                is_assignment,
                image=request.image,
                imageType=request.imageType,
                progress=progress,
            )
            docs = app.state.retriever_simple.invoke(request.question)
            sources = list({
                d.metadata.get("source", "unknown").split("\\")[-1].split("/")[-1]
                for d in docs
            })
            progress_queue.put(_format_sse("answer", json.dumps({"answer": answer, "sources": sources, "model_used": model_used})))
            progress_queue.put(_format_sse("done", json.dumps({})))
        except Exception as e:
            progress_queue.put(_format_sse("error", json.dumps({"message": str(e)})))
        finally:
            progress_queue.put(None)

    thread = threading.Thread(target=worker)
    thread.start()

    def event_generator():
        try:
            while True:
                item = progress_queue.get()
                if item is None:
                    break
                yield item
        finally:
            thread.join()

    return StreamingResponse(event_generator(), media_type="text/event-stream")