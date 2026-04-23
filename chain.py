# chain.py
from dotenv import load_dotenv

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI

from config import FALLBACK_MODELS, LLM_TEMPERATURE
from retriever import load_vectordb, get_retriever, rerank

load_dotenv()


def format_docs(docs):
    """
    Merges a list of Documents into a single string for the prompt context.
    """
    return "\n\n---\n\n".join(d.page_content for d in docs)


def build_chain(retriever, model: str):
    """
    Builds and returns the full RAG chain using the specified model.
    """
    llm = ChatGoogleGenerativeAI(
        model=model,
        temperature=LLM_TEMPERATURE,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system",
        "You are a helpful assistant for a database course. Answer the user's question using ONLY the provided context. "
        "Rewrite the information clearly and in well-structured prose — do not copy the phrasing from the context directly. "
        "Use complete sentences and organize your answer logically. "
        "If the answer is not in the context, say: 'I don't know based on the provided context.'"),  
        ("human", "Context:\n{context}\n\nQuestion:\n{question}\n\nAnswer:")
    ])

    def retrieve_and_rerank(question: str) -> str:
        docs = retriever.invoke(question)
        reranked = rerank(question, docs)
        return format_docs(reranked)

    rag_chain = (
        {
            "context": RunnableLambda(retrieve_and_rerank),
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return rag_chain


def invoke_with_fallback(retriever_simple, retriever_multi, question: str, exhausted_models: set) -> str:
    """
    Tries each model in FALLBACK_MODELS in order.
    Falls back to the next model on 429 errors.
    """

    for model in FALLBACK_MODELS:
        if model in exhausted_models:
            print(f"  [skipping] {model} already exhausted")
            continue
        
        try:
            chain = build_chain(retriever_simple, model)
            answer = chain.invoke(question)
            print(f"  [model used] {model}")

            if "I don't know based on the provided context" in answer:
                print("  [retrying with query translation]")
                chain = build_chain(retriever_multi, model)
                answer = chain.invoke(question)
                print("  [query translation used]")
            
            return answer, model

        except Exception as e:
            if "429" in str(e):
                print(f"  [fallback] {model} quota exhausted, trying next...")
                exhausted_models.add(model)
                continue
            raise

    raise Exception("All models exhausted — try again later.")


if __name__ == "__main__":
    vectordb = load_vectordb()
    retriever = get_retriever(vectordb)
    question = "What is a primary key?"
    answer = invoke_with_fallback(retriever, question)
    print(f"Q: {question}\n")
    print(f"A: {answer}")