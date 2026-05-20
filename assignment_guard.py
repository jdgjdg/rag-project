# assignment_guard.py
from dotenv import load_dotenv
from pathlib import Path
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
import time

from config import EMBEDDING_MODEL, ROOT_DIR, SIMILARITY_THRESHOLD, ASSIGNMENT_COLLECTION, ASSIGNMENT_FILE, ASSIGNMENT_BATCH_DELAY, ASSIGNMENT_BATCH_SIZE, ASSIGNMENT_CHROMA_DIR

load_dotenv()



def load_assignment_db() -> Chroma:
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
    assignment_db_dir = ASSIGNMENT_CHROMA_DIR

    if assignment_db_dir.exists():
        print("Loading existing assignment question index...")
        return Chroma(
            persist_directory=str(assignment_db_dir),
            embedding_function=embeddings,
            collection_name=ASSIGNMENT_COLLECTION,
        )

    print("Building assignment question index...")
    questions = ASSIGNMENT_FILE.read_text(encoding="utf-8").strip().split("\n")
    questions = [q.strip() for q in questions if q.strip()]
    print(f"  Loaded {len(questions)} questions")

    from langchain_core.documents import Document
    docs = [Document(page_content=q) for q in questions]


    vectordb = None
    for i in range(0, len(docs), ASSIGNMENT_BATCH_SIZE):
        batch = docs[i:i + ASSIGNMENT_BATCH_SIZE]
        print(f"  Embedding batch {i//ASSIGNMENT_BATCH_SIZE + 1}/{(len(docs)-1)//ASSIGNMENT_BATCH_SIZE + 1}...")

        for attempt in range(5):
            try:
                if vectordb is None:
                    vectordb = Chroma.from_documents(
                        documents=batch,
                        embedding=embeddings,
                        persist_directory=str(assignment_db_dir),
                        collection_name=ASSIGNMENT_COLLECTION,
                    )
                else:
                    vectordb.add_documents(batch)
                break
            except Exception as e:
                if "429" in str(e):
                    wait = 60 * (attempt + 1)
                    print(f"    Rate limit hit, waiting {wait} seconds...")
                    time.sleep(wait)
                else:
                    raise
        else:
            # Python for-else: runs only when all 5 retry attempts failed without break.
            print(f"    WARNING: batch failed after all attempts")

        time.sleep(ASSIGNMENT_BATCH_DELAY)

    print(f"  Indexed {len(questions)} assignment questions")
    return vectordb


def is_assignment_question(query: str, assignment_db: Chroma) -> tuple[bool, str]:
    """
    Checks if a query is similar to an assignment question.
    Returns (is_assignment, matched_question).
    """
    results = assignment_db.similarity_search_with_score(query, k=1)
    
    if not results:
        return False, ""
    
    doc, score = results[0]
    
    # Chroma returns cosine distance (lower = more similar)
    # Convert to similarity: similarity = 1 - distance
    similarity = 1 - score
    
    print(f"  [assignment check] similarity={similarity:.3f}, threshold={SIMILARITY_THRESHOLD}")
    
    if similarity >= SIMILARITY_THRESHOLD:
        print(f"  [assignment detected] matched: {doc.page_content[:80]}...")
        return True, doc.page_content
    
    return False, ""