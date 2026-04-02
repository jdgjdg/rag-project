from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.load import dumps, loads

from config import CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL, TOP_K, FALLBACK_MODELS

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

def get_unique_union(documents: list[list]):
    """ Unique union of retrieved docs """
    # Flatten list of lists, and convert each Document to string
    flattened_docs = [dumps(doc) for sublist in documents for doc in sublist]
    # Get unique documents
    unique_docs = list(set(flattened_docs))
    # Return
    return [loads(doc) for doc in unique_docs]

def get_retriever(vectordb: Chroma, queries: int=1):
    """
    Returns a retriever from the vector DB.
    k controls how many chunks are returned per query.
    """
    if queries > 1:
        template = f"""You are an AI language model assistant. Your task is to generate {queries} 
        different versions of the given user question to retrieve relevant documents from a vector 
        database. By generating multiple perspectives on the user question, your goal is to help
        the user overcome some of the limitations of the distance-based similarity search. 
        Provide these alternative questions separated by newlines. Original question: {{question}}"""
        prompt_perspectives = ChatPromptTemplate.from_template(template)

        generate_queries = (
            (lambda q: {"question": q})
            | prompt_perspectives
            | ChatGoogleGenerativeAI(model=FALLBACK_MODELS[0], temperature=0)
            | StrOutputParser() 
            | (lambda x: x.split("\n"))
        )
    
        retriever = vectordb.as_retriever(search_kwargs={"k": TOP_K})
        retrieval_chain = generate_queries | retriever.map() | get_unique_union
        return retrieval_chain
    
    else:
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