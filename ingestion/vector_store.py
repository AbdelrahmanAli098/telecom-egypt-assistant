import hashlib
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue

def _make_point_id(chunk: dict) -> str:
    url = (chunk.get("url") or chunk.get("session_id") or "").strip()
    chunk_index = chunk.get("chunk_index", 0)
    content_type = chunk.get("content_type", "")
    key = f"{url}|{chunk_index}|{content_type}"
    return hashlib.md5(key.encode("utf-8")).hexdigest()

class QdrantStorage:
    def __init__(self, url="http://localhost:6333", collection="TE.Eg", dim=1024):
        self.client = QdrantClient(url=url, timeout=30)
        self.collection = collection
        if not self.client.collection_exists(collection_name=collection):
            self.client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE))

    def upsert_chunks(self, chunks: list[dict]):
        points = []
        for chunk in chunks:
            vector = chunk["embedding"]
            payload = {k: v for k, v in chunk.items() if k != "embedding"}  # everything except the vector itself
            point_id = _make_point_id(chunk)
            points.append(PointStruct(id=point_id, vector=vector, payload=payload))

        self.client.upsert(self.collection, points=points)

    def search(self, query_vector, top_k=5, session_id: str | None = None):
        if session_id:
            query_filter = Filter(
                should=[
                    Filter(
                        must_not=[
                            FieldCondition(key="source_type", match=MatchValue(value="user_upload"))
                        ]
                    ),
                    FieldCondition(key="session_id", match=MatchValue(value=session_id)),
                ]
            )
        else:
            query_filter = Filter(must_not=[FieldCondition(key="source_type", match=MatchValue(value="user_upload"))])

        results = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            query_filter=query_filter,
            with_payload=True,
            limit=top_k)

        contexts = []
        sources = set()

        for point in results.points:
            payload = point.payload
            chunk_text = payload.get("chunk_text")
            url = payload.get("url")
            if chunk_text:
                contexts.append(chunk_text)
            if url:
                sources.add(url)

        return {"contexts": contexts, "sources": sources}