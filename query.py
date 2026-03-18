from chain import build_chain
from retriever import get_retriever, load_vectordb, get_sources


def ask(question: str) -> None:
    """
    Runs a question through the RAG chain and prints the answer and sources.
    """
    
    vectordb = load_vectordb()
    retriever = get_retriever(vectordb)
    chain = build_chain(retriever)
    
    answer = chain.invoke(question)
    print(f"\nQ: {question}")
    print(f"\nA: {answer}")
    get_sources(retriever, question)

import time

def ask_with_retry(question: str) -> None:
    vectordb = load_vectordb()
    retriever = get_retriever(vectordb)
    chain = build_chain(retriever)

    for attempt in range(3):
        try:
            answer = chain.invoke(question)
            break
        except Exception as e:
            if "429" in str(e):
                print(f"Rate limit hit, waiting 30 seconds... (attempt {attempt + 1}/3)")
                time.sleep(30)
            else:
                raise
    else:
        print("Failed after 3 attempts. Try again later.")
        return

    print(f"\nQ: {question}")
    print(f"\nA: {answer}")
    get_sources(retriever, question)

if __name__ == "__main__":
    while True:
        question = input("\nAsk a question (or 'quit' to exit): ")
        if question.strip().lower() == "quit":
            break
        ask_with_retry(question)