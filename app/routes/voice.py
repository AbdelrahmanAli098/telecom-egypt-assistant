import base64
from pathlib import Path
import shutil
import uuid

from fastapi import APIRouter, File, UploadFile, Form

from voice.asr import transcribe
from voice.tts import synthesize
from rag.pipeline import answer_question

router = APIRouter()

TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)


@router.post("/voice")
def voice_query(file: UploadFile = File(...), session_id: str | None = Form(None)):
    # Save uploaded audio to a temp path
    temp_path = TEMP_DIR / f"{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # ASR
        question_text, detected_language = transcribe(str(temp_path))

        if not question_text.strip():
            return {
                "transcript": "",
                "detected_language": detected_language,
                "answer": "Sorry, I couldn't detect any speech in the audio. Could you try again?",
                "sources": [],
                "audio_base64": None,
            }

        # RAG
        result = answer_question(question_text, session_id=session_id)

        #TTS
        tts_result = synthesize(result["answer"])

        # Read synthesized audio and encode for JSON response
        audio_bytes = tts_result.path.read_bytes()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        return {
            "transcript": question_text,
            "detected_language": detected_language,
            "answer": result["answer"],
            "sources": result.get("sources", []),
            "audio_base64": audio_b64,
            "audio_language": tts_result.language,
        }
    finally:
        # Clean up temp input file regardless of success/failure
        temp_path.unlink(missing_ok=True)