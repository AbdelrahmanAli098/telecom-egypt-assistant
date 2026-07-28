from pathlib import Path
import shutil
import uuid
from fastapi import APIRouter, File, UploadFile, Form
from ingestion.user_loader import chunk_uploaded_document
from ingestion.embedder import embed_chunks
from ingestion.vector_store import QdrantStorage

router = APIRouter()

store = QdrantStorage()


@router.post("/upload")
def upload_file(file: UploadFile = File(...), session_id: str | None = Form(None)):

    session_id = session_id or str(uuid.uuid4())

    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)

    temp_path = temp_dir / file.filename

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        chunks = chunk_uploaded_document(temp_path, session_id)
        embeddings = embed_chunks(chunks)
        store.upsert_chunks(embeddings)
    finally:
        temp_path.unlink(missing_ok=True)

    return {
        "message": "Upload successful",
        "session_id": session_id,
        "stored_chunks": len(embeddings),
    }