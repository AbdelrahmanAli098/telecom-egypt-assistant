from llama_index.core.node_parser import SentenceSplitter
from pathlib import Path
import json

data_path = Path("data\\raw\\scraped_pages.json")
output_path = Path("data/processed/chunks.jsonl")
splitter = SentenceSplitter(chunk_size=300, chunk_overlap=50)

def load_chunk_json(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = []
    for item in data:
        content = item.get("content", "")
        if not content.strip():
            continue

        content_type = item.get("content_type", "plain")

        # FAQ / clause / definition are already atomic — don't fragment them
        if content_type in ("faq", "clause", "definition"):
            split_texts = [content]
        else:
            split_texts = splitter.split_text(content)

        for i, chunk_text in enumerate(split_texts):
            chunks.append({
                "chunk_text": chunk_text,
                "url": item.get("url"),
                "language": item.get("language"),
                "title": item.get("title"),
                "category": item.get("category"),
                "content_type": content_type,
                "chunk_index": i,
            })

    return chunks


def save_chunks(chunks: list[dict], output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    print(f"Saved {len(chunks)} chunks to {output_path}")


chunks = load_chunk_json(data_path)
save_chunks(chunks, output_path)