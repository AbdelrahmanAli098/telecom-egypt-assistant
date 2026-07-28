from dataclasses import dataclass
from langdetect import detect, LangDetectException
from pathlib import Path
import subprocess
import uuid

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
PIPER = BASE_DIR / "piper.exe"
EN_MODEL = BASE_DIR / "voices" / "en" / "en_US-lessac-medium.onnx"
AR_MODEL = BASE_DIR / "voices" / "ar" / "ar_JO-kareem-medium.onnx"


@dataclass
class TTSResult:
    path: Path
    language: str

def detect_language_safe(text: str) -> str:
    try:
        return detect(text)
    except LangDetectException:
        return "en"

def synthesize(text: str) -> TTSResult:
    language = detect_language_safe(text)
    model = AR_MODEL if language == "ar" else EN_MODEL
    output_file = OUTPUT_DIR / f"{uuid.uuid4()}.wav"

    result = subprocess.run(
        [
            str(PIPER),
            "--model",
            str(model),
            "--output_file",
            str(output_file),
        ],
        input=text.encode("utf-8"),
        capture_output=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"""Piper failed.Return Code:{result.returncode}
                STDOUT:{result.stdout.decode('utf-8', errors='ignore')}
                STDERR:{result.stderr.decode('utf-8', errors='ignore')}"""
        )
    return TTSResult(
        path=output_file,
        language=language,
    )
