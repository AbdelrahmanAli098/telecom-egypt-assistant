import os
from langchain_ollama import ChatOllama, OllamaEmbeddings
from ingestion.vector_store import QdrantStorage

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434"
os.environ["OLLAMA_HOST"] = OLLAMA_BASE_URL

embedding = OllamaEmbeddings(
    model= "bge-m3",
    base_url=OLLAMA_BASE_URL,
)
client = ChatOllama(
    model="qwen2.5:7b",
    temperature=0.1,
    base_url=OLLAMA_BASE_URL,
)
store = QdrantStorage()

def search(question: str, top_k: int = 10, session_id: str | None = None) -> dict:
    query_vec = embedding.embed_query(question)
    found = store.search(query_vec, top_k, session_id=session_id)
    return {"contexts": found["contexts"], "sources": found["sources"]}

def generate_answer(question: str, contexts: list[str]) -> str:
    context_str = "\n\n".join(contexts)
    prompt = f"""You are a helpful customer service assistant for Telecom Egypt.answer only from the given context, answer in the same language as the question, say so explicitly if the context doesn't contain the answer"""
    response = client.invoke([("user", f"{prompt}\n\nContext: {context_str}\n\nQuestion: {question}")])
    if not response.content.strip():
        return "I'm sorry, I wasn't able to generate a response. Please try rephrasing your question."
    
    return response.content