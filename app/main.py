from fastapi import FastAPI

from app.routes.chat import router as chat_router
from app.routes.upload import router as upload_router
from app.routes.voice import router as voice_router

app = FastAPI(title="Telecom Egypt Assistant")

app.include_router(chat_router)
app.include_router(upload_router)
app.include_router(voice_router)