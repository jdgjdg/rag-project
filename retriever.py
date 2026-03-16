from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from config import CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL, TOP_K

load_dotenv()


def load_vectordb() -> Chroma:
    """
    Connects to the existing Chroma vector DB on disk.
    Raises an error if the DB has not been built yet.
    """
    if not CHROMA_DIR.exists():
        raise FileNotFoundError(
            f"No vector DB found at {CHROMA_DIR}. Run ingest.py first."
        )

    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)

    vectordb = Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME,
    )

    return vectordb


def get_retriever(vectordb: Chroma):
    """
    Returns a retriever from the vector DB.
    k controls how many chunks are returned per query.
    """
    return vectordb.as_retriever(search_kwargs={"k": TOP_K})

def get_sources(retriever, query: str) -> None:
    """
    Prints the unique source filenames for chunks retrieved by a query.
    """
    docs = retriever.invoke(query)
    seen = set()
    print("\n--- Sources ---")
    for d in docs:
        source = d.metadata.get("source", "unknown")
        filename = source.split("\\")[-1].split("/")[-1]
        if filename not in seen:
            seen.add(filename)
            print(f"  {filename}")

if __name__ == "__main__":
    vectordb = load_vectordb()
    retriever = get_retriever(vectordb)

    query = "What is a primary key?"
    docs = retriever.invoke(query)

    print(f"Query: {query}")
    print(f"Retrieved {len(docs)} chunks\n")
    for i, d in enumerate(docs, 1):
        print(f"--- Chunk {i} ---")
        print(d.page_content[:300])
        print()

    get_sources(retriever, query)