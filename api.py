from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager

from retriever import load_vectordb, get_retriever
from chain import invoke_with_fallback

# ── Startup: load vectordb and chain once ──────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    vectordb = load_vectordb()
    retriever = get_retriever(vectordb)
    app.state.retriever = retriever
    yield

app = FastAPI(lifespan=lifespan)

# ── CORS: allows Angular (localhost:4200) to talk to this server ───────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request/Response shapes ────────────────────────────────────────────────
class QuestionRequest(BaseModel):
    question: str

class AnswerResponse(BaseModel):
    answer: str
    sources: list[str]

# ── Endpoint ───────────────────────────────────────────────────────────────
@app.post("/query", response_model=AnswerResponse)
def query(request: QuestionRequest):
    answer = invoke_with_fallback(app.state.retriever, request.question)
    
    docs = app.state.retriever.invoke(request.question)
    sources = list({
        d.metadata.get("source", "unknown").split("\\")[-1].split("/")[-1]
        for d in docs
    })

    return AnswerResponse(answer=answer, sources=sources)