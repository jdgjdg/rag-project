# chain.py
from dotenv import load_dotenv

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI

from config import FALLBACK_MODELS, LLM_TEMPERATURE, SYSTEM_PROMPT, ASSIGNMENT_NOTE
from retriever import load_vectordb, get_retriever, rerank

load_dotenv()


def format_history(history: list) -> str:
    """Formats conversation history as labeled text for the prompt."""
    if not history:
        return "No previous conversation."
    lines = []
    for msg in history:
        role = "Student" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)

def format_docs(docs):
    """
    Merges a list of Documents into a single string for the prompt context.
    """
    return "\n\n---\n\n".join(d.page_content for d in docs)


def build_chain(retriever, model: str, history: list = [], is_assignment: bool = False, image: str = None, imageType: str = None):
    """
    Builds and returns the full RAG chain using the specified model.
    """
    llm = ChatGoogleGenerativeAI(
        model=model,
        temperature=LLM_TEMPERATURE,
    )

    formatted_history = format_history(history)

    assignment_note = ASSIGNMENT_NOTE if is_assignment else ""

    if image:
        human_message = [
            {
                "type": "image_url",
                "image_url": {"url": f"data:{imageType};base64,{image}"}
            },
            {
                "type": "text",
                "text": """Context:\n{context}

                Conversation History:
                {history}

                <user_query>{question}</user_query>
                Answer:"""
            }
        ]
    else:
        human_message = """Context:\n{context}

        Conversation History:
        {history}

        <user_query>{question}</user_query>
        Answer:"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT + assignment_note),
        ("human", human_message)
    ])

    def retrieve_and_rerank(question: str) -> str:
        docs = retriever.invoke(question)
        reranked = rerank(question, docs)
        return format_docs(reranked)

    rag_chain = (
        {
            "context": RunnableLambda(retrieve_and_rerank),
            "history": RunnableLambda(lambda _: formatted_history),
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return rag_chain


def invoke_with_fallback(retriever_simple, retriever_multi, question: str, exhausted_models: set, history: list = [], is_assignment: bool = False, image: str = None, imageType: str = None, progress: object | None = None) -> tuple[str, str]:
    """
    Tries each model in FALLBACK_MODELS in order.
    Falls back to the next model on 429 errors.
    """

    def _progress(stage: str):
        progress(stage) if progress else None

    for model in FALLBACK_MODELS:
        if model in exhausted_models:
            print(f"  [skipping] {model} already exhausted")
            _progress("skipping_model")
            continue
        
        try:
            _progress("building_chain")
            chain = build_chain(retriever_simple, model, history, is_assignment, image, imageType)
            _progress("invoking_question")
            print(type(chain))
            answer = chain.invoke(question)
            print(f"  [model used] {model}")
            _progress("model_used")

            # The system prompt instructs the LLM to say this exact phrase when it
            # can't find relevant context. We catch it here to retry with richer
            # retrieval (multi-query expansion) before giving up.
            if "I lack specific course context" in answer:
                print("  [retrying with query translation]")
                _progress("retrying_query_translation")
                chain = build_chain(retriever_multi, model, history, is_assignment, image, imageType)
                _progress("invoking_question")
                answer = chain.invoke(question)
                print("  [query translation used]")
                _progress("query_translation_used")
            
            return answer, model

        except Exception as e:
            if "429" in str(e):
                print(f"  [fallback] {model} quota exhausted, trying next...")
                _progress("fallback_model")
                exhausted_models.add(model)
                continue
            raise

    raise Exception("All models exhausted — try again later.")


if __name__ == "__main__":
    vectordb = load_vectordb()
    retriever = get_retriever(vectordb)
    question = "What is a primary key?"
    answer, model_used = invoke_with_fallback(retriever, retriever, question, set())
    print(f"Q: {question}\n")
    print(f"A: {answer}\n")
    print(f"Model: {model_used}")