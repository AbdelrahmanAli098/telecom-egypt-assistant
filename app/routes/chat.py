from rag.pipeline import answer_question
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None

@router.post("/chat")
def chat(request: ChatRequest):
    # Process the question using the RAG pipeline
    result = answer_question(request.question, session_id=request.session_id)

    return result