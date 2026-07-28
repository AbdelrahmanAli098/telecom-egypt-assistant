from embedder import embed_chunks, save_embeddings
import json
from pathlib import Path

def load_chunks_from_jsonl(path: Path) -> list[dict]:
    chunks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            chunks.append(json.loads(line))
    return chunks

chunks = load_chunks_from_jsonl(Path("data/processed/chunks.jsonl"))
embedded = embed_chunks(chunks)
save_embeddings(embedded, Path("data/embeddings/embeddings.jsonl"))