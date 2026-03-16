# ingest.py
import os
from pathlib import Path
from dotenv import load_dotenv

from langchain_community.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

from config import DATA_DIR, CHUNK_SIZE, CHUNK_OVERLAP, CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL

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


def embed_documents(chunks: list[Document]) -> Chroma:
    """
    Embeds chunks and stores them in a local Chroma vector DB.
    If the DB already exists, loads it instead of rebuilding.
    """
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)

    if CHROMA_DIR.exists():
        print("Loading existing vector index...")
        vectordb = Chroma(
            persist_directory=str(CHROMA_DIR),
            embedding_function=embeddings,
            collection_name=COLLECTION_NAME,
        )
        print(f"Loaded {vectordb._collection.count()} chunks from {CHROMA_DIR}")

    else:
        print("Building vector index...")
        vectordb = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=str(CHROMA_DIR),
            collection_name=COLLECTION_NAME,
        )
        print(f"Stored {len(chunks)} chunks in {CHROMA_DIR}")

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