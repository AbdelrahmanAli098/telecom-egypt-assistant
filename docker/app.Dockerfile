# app/Dockerfile
FROM python:3.11-slim


RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --break-system-packages

# --- Piper (TTS) ---
# Piper binary + voice models are not pip-installable; they must already be
# present in your build context at these paths (see README §3.4 for how to
# obtain them) before building this image.
COPY voice/piper /code/voice/piper
COPY voice/voices /code/voice/voices
RUN chmod +x /code/voice/piper

# --- Application code ---
COPY app /code/app
COPY rag /code/rag
COPY ingestion /code/ingestion
COPY voice /code/voice

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
