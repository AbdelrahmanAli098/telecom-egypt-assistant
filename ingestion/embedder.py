from langchain_ollama import OllamaEmbeddings
import os 
from pathlib import Path
import json
import time

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434"
os.environ["OLLAMA_HOST"] = OLLAMA_BASE_URL

embedding = OllamaEmbeddings(
    model= "bge-m3",
    base_url=OLLAMA_BASE_URL,
)

embeddings_dim = 1024 

def embed_chunks(chunks: list[dict], max_retries: int = 3) -> list[dict]:
    for chunk in chunks:
        for attempt in range(max_retries):
            try:
                vector = embedding.embed_documents([chunk["chunk_text"]])[0]
                chunk["embedding"] = vector
                break
            except Exception:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 * (attempt + 1))
    return chunks

def save_embeddings(chunks: list[dict], output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    print(f"Saved {len(chunks)} embedded chunks to {output_path}")