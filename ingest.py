# ingest.py
import os
from pathlib import Path
from dotenv import load_dotenv
import time 
import json
from langchain_community.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

from config import DATA_DIR, CHUNK_SIZE, CHUNK_OVERLAP, CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL, ROOT_DIR, BATCH_DELAY, BATCH_SIZE

load_dotenv()

LOADERS = {
    ".txt":  (TextLoader,     {"encoding": "utf-8"}),
    ".pdf":  (PyPDFLoader,    {}),
    ".md":   (TextLoader,     {"encoding": "utf-8"}),
    ".docx": (Docx2txtLoader, {}),
}


def load_documents(data_dir: Path = DATA_DIR) -> list[Document]:
    """
    Recursively loads all supported documents from data_dir.
    Returns a flat list of Document objects, one per page (PDF) or file (txt, md, docx).
    Unsupported file types are skipped and reported.
    """
    docs = []
    skipped = []

    for path in data_dir.rglob("*"):
        if path.is_dir():
            continue

        entry = LOADERS.get(path.suffix.lower())
        if entry is None:
            skipped.append(path.name)
            continue

        loader_cls, kwargs = entry
        try:
            loaded = loader_cls(str(path), **kwargs).load()
            docs.extend(loaded)
            print(f"  [ok] {path.relative_to(data_dir)}  ({len(loaded)} doc(s))")
        except Exception as e:
            print(f"  [error] {path.name}: {e}")

    if skipped:
        print(f"\n  [skipped] {len(skipped)} unsupported file(s): {', '.join(skipped)}")

    return docs


def chunk_documents(docs: list[Document]) -> list[Document]:
    """
    Splits a list of Documents into smaller chunks.
    Returns a flat list of chunk Documents with inherited metadata.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    chunks = splitter.split_documents(docs)
    print(f"  Split {len(docs)} documents into {len(chunks)} chunks")
    return chunks

PROGRESS_FILE = ROOT_DIR / "embed_progress.json"

def embed_documents(chunks: list[Document]) -> Chroma:
    """
    Embeds chunks and stores them in a local Chroma vector DB.
    If the DB already exists, loads it instead of rebuilding.
    """
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)

    if CHROMA_DIR.exists() and not PROGRESS_FILE.exists():
        print("Loading existing vector index...")
        vectordb = Chroma(
            persist_directory=str(CHROMA_DIR),
            embedding_function=embeddings,
            collection_name=COLLECTION_NAME,
        )
        print(f"Loaded {vectordb._collection.count()} chunks from {CHROMA_DIR}")
        return vectordb

    print("Building vector index...") 

    start_batch = 0
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            progress = json.load(f)
            start_batch = progress.get("last_completed_batch", 0) + 1
            print(f"  Resuming from batch {start_batch + 1}...")

    vectordb = None
    
    if start_batch > 0 and CHROMA_DIR.exists():
        vectordb = Chroma(
            persist_directory=str(CHROMA_DIR),
            embedding_function=embeddings,
            collection_name=COLLECTION_NAME,
        )
        print(f"  Loaded partial DB with {vectordb._collection.count()} chunks")

    total_batches = (len(chunks) - 1) // BATCH_SIZE + 1

    for i in range(start_batch * BATCH_SIZE, len(chunks), BATCH_SIZE):
        batch_num = i // BATCH_SIZE
        batch = chunks[i:i + BATCH_SIZE]
        print(f"  Embedding batch {batch_num + 1}/{total_batches}...")

        for attempt in range(5):
            try:
                if vectordb is None:
                    vectordb = Chroma.from_documents(
                        documents=batch,
                        embedding=embeddings,
                        persist_directory=str(CHROMA_DIR),
                        collection_name=COLLECTION_NAME,
                    )
                else:
                    vectordb.add_documents(batch)
                
                # Save progress after each successful batch
                with open(PROGRESS_FILE, "w") as f:
                    json.dump({"last_completed_batch": batch_num}, f)
                break

            except Exception as e:
                if "429" in str(e):
                    wait = 60 * (attempt + 1)
                    print(f"    Rate limit hit, waiting {wait} seconds...")
                    time.sleep(wait)
                else:
                    raise
        else:
            # Python for-else: this block runs only when the inner loop exhausted all
            # 5 attempts without a successful break — i.e., the daily quota is truly hit.
            print(f"    Daily limit reached — stopping at batch {batch_num + 1}")
            print(f"    Rerun tomorrow to continue from this point.")
            return vectordb

        time.sleep(BATCH_DELAY)

    # Finished — clean up progress file
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()
        print("  Embedding complete — progress file removed")

    if vectordb is None:
        raise RuntimeError("Failed to build vector index — all batches failed.")

    return vectordb


if __name__ == "__main__":
    print(f"Loading documents from: {DATA_DIR}\n")
    docs = load_documents()
    print(f"\nTotal documents loaded: {len(docs)}")

    print(f"\nChunking documents...\n")
    chunks = chunk_documents(docs)
    print(f"\nTotal chunks: {len(chunks)}")

    print(f"\nEmbedding chunks...\n")
    vectordb = embed_documents(chunks)
    print(f"\nVector DB ready.")