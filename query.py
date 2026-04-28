from chain import build_chain
from retriever import get_retriever, load_vectordb, get_sources
from config import LLM_MODEL
import time


def ask_with_retry(question: str, retriever) -> None:
    chain = build_chain(retriever, LLM_MODEL)

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
    vectordb = load_vectordb()
    retriever = get_retriever(vectordb)
    while True:
        question = input("\nAsk a question (or 'quit' to exit): ")
        if question.strip().lower() == "quit":
            break
        ask_with_retry(question, retriever)
