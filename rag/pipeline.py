import time

from rag.generator import generate_answer, search

def answer_question(question: str, top_k: int = 10, session_id: str | None = None) -> dict:
    start_time = time.time()
    search_results = search(question, top_k, session_id=session_id)
    contexts = search_results["contexts"]
    sources = search_results["sources"]

    if not contexts:
        return {
            "answer": "I'm sorry, I don't have information about that in our knowledge base.",
            "sources": []
        }

    answer = generate_answer(question, contexts)
    end_time = time.time()
    print(f"Total time: {end_time - start_time:.2f} seconds")
    return {"answer": answer, "sources": list(sources)}