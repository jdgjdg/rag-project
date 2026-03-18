# chain.py
from dotenv import load_dotenv

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI

from config import LLM_MODEL, LLM_TEMPERATURE
from retriever import load_vectordb, get_retriever

load_dotenv()


def format_docs(docs):
    """
    Merges a list of Documents into a single string for the prompt context.
    """
    return "\n\n---\n\n".join(d.page_content for d in docs)


def build_chain(retriever):
    """
    Builds and returns the full RAG chain.
    """
    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system",
        "You are a helpful assistant for a database course. Answer the user's question using ONLY the provided context. "
        "Rewrite the information clearly and in well-structured prose — do not copy the phrasing from the context directly. "
        "Use complete sentences and organize your answer logically. "
        "If the answer is not in the context, say: 'I don't know based on the provided context.'"),
        ("human",
         "Context:\n{context}\n\nQuestion:\n{question}\n\nAnswer:")
    ])

    rag_chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return rag_chain


if __name__ == "__main__":
    vectordb = load_vectordb()
    retriever = get_retriever(vectordb)
    chain = build_chain(retriever)
    question = "What is a primary key?"
    answer = chain.invoke(question)
    print(f"Q: {question}\n")
    print(f"A: {answer}")
