from pathlib import Path
from pypdf import PdfReader
from docx import Document
import easyocr
from pdf2image import convert_from_path
from llama_index.core.node_parser import SentenceSplitter


splitter = SentenceSplitter(chunk_size=300, chunk_overlap=50)

user_output_path = Path("data/processed/user_chunks.jsonl")
reader = easyocr.Reader(['ar', 'en'])

def extract_text_from_pdf(file_path: Path) -> str:
    pdf = PdfReader(str(file_path))
    text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    if len(text.strip()) < 30:
        text = extract_text_from_scanned_pdf(file_path)

    return text

def extract_text_from_scanned_pdf(file_path: Path) -> str:
    images = convert_from_path(str(file_path))
    ocr_text = []
    for img in images:
        result = reader.readtext(img, detail=0)
        ocr_text.append(" ".join(result))
    return "\n".join(ocr_text)

def extract_text_from_docx(file_path: Path) -> str:
    doc = Document(str(file_path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

def extract_text_from_txt(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")

def extract_text_from_image(file_path: Path) -> str:
    result = reader.readtext(str(file_path), detail=0)
    return " ".join(result)

def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    elif suffix == ".docx":
        return extract_text_from_docx(file_path)
    elif suffix == ".txt":
        return extract_text_from_txt(file_path)
    elif suffix in (".png", ".jpg", ".jpeg"):
        return extract_text_from_image(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

def chunk_uploaded_document(file_path: Path, session_id: str) -> list[dict]:
    text = extract_text(file_path)
    if not text.strip():
        return []
    split_texts = splitter.split_text(text)
    chunks = []
    for i, chunk_text in enumerate(split_texts):
        chunks.append({
            "chunk_text": chunk_text,
            "url": None,
            "language": None,
            "title": file_path.name,
            "category": "user_upload",
            "content_type": "user_upload",
            "source_type": "user_upload",
            "session_id": session_id,
            "chunk_index": i,
        })
    return chunks