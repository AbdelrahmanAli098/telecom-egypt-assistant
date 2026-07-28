# Telecom Egypt Intelligent Assistant

A bilingual (Arabic / English / Egyptian dialect) customer service assistant for Telecom Egypt. Supports text chat, voice input/output, and user document upload — all grounded in retrieval from the official te.eg website, running fully on-premises via Ollama.

---

## 1. Architecture Overview

```
                    ┌──────────────────────┐
                    │   Streamlit UI       │  (ui.py)
                    │  text / voice / docs │
                    └──────────┬───────────┘
                               │ HTTP (requests)
                    ┌──────────▼───────────┐
                    │   FastAPI backend    │  (app/main.py)
                    │ /chat /upload /voice │
                    └──────────┬───────────┘
              ┌────────────────┼────────────────┐
              ▼                ▼                 ▼
      ┌───────────────┐ ┌─────────────┐  ┌──────────────┐
      │ faster-whisper│ │ RAG pipeline│  │    Piper     │
      │  (ASR, local) │ │ (rag/*)     │  │  (TTS, local)│
      └───────────────┘ └──────┬──────┘  └──────────────┘
                                │
                    ┌───────────▼────────────┐
                    │   Qdrant (vector DB)   │
                    │   collection: TE.Eg    │
                    └───────────┬────────────┘
                                │
                    ┌───────────▼────────────┐
                    │  bge-m3 embeddings +   │
                    │  qwen2.5:7b generation │
                    │       (via Ollama)     │
                    └────────────────────────┘
```

---

## 2. Tech Stack

| Component | Choice | Notes |
|---|---|---|
| LLM (generation) | `qwen2.5:7b` via Ollama | See §5 for why, not `qwen3.5` |
| Embeddings | `bge-m3` via Ollama | Multilingual, 1024-dim, verified on Arabic + English |
| Vector DB | Qdrant | Local, Docker, cosine similarity |
| ASR | `faster-whisper` (`large-v3`) | Auto language detection, VAD-filtered (see §6) |
| TTS | Piper | Local, `langdetect`-driven voice selection |
| Scraping | Playwright + BeautifulSoup | Liferay CMS requires JS rendering |
| Doc ingestion | pypdf, python-docx, EasyOCR | OCR fallback for scanned PDFs/images |
| Chunking | LlamaIndex `SentenceSplitter` | `chunk_size=300`, `overlap=50` |
| Backend | FastAPI + Uvicorn | |
| Frontend | Streamlit | |
| Package management | `uv` | |

---

## 3. Setup Instructions

### Prerequisites
- Python 3.14
- [Ollama](https://ollama.com) installed and running locally
- Docker (for Qdrant)
- An NVIDIA GPU + CUDA 12.x runtime is **recommended** but not required — ASR/embedding/generation all have CPU fallback paths (slower; see §6 for the measured latency difference)

### 3.1 Pull the required Ollama models
```bash
ollama pull qwen2.5:7b
ollama pull bge-m3
```

### 3.2 Start Qdrant
```bash
docker run -d -p 6333:6333 --name qdrantDB qdrant/qdrant
```

### 3.3 Python environment
```bash
uv venv
# Windows:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

uv pip install -r requirements.txt
```



### 3.4 Piper (TTS) setup
Piper is not bundled — download it once:
1. Get the Piper binary for your OS from the [Piper releases page](https://github.com/rhasspy/piper/releases).
2. Download voice models: `en_US-lessac-medium` (English) and `ar_JO-kareem-medium` (Arabic) — `.onnx` + `.onnx.json` pairs, from Piper's [voices repo](https://huggingface.co/rhasspy/piper-voices).
3. Place them at:
   ```
   voice/piper.exe (or piper on Linux/Mac)
   voice/voices/en/en_US-lessac-medium.onnx (+ .json)
   voice/voices/ar/ar_JO-kareem-medium.onnx (+ .json)
   ```

### 3.5 Whisper model download (first run only)
`faster-whisper` downloads `large-v3` (~3GB) from Hugging Face on first use and caches it locally. This can take a while depending on your connection — it is a one-time cost, not a per-run cost.

### 3.6 Populate the knowledge base
```bash
python -m scraper.extractor      # scrape te.eg -> data/raw/scraped_pages.json
python -m ingestion.chunker      # -> data/processed/chunks.jsonl
python -m ingestion.run_embed    # -> data/embeddings/embeddings.jsonl + upserts into Qdrant
```

### 3.7 Run the app
Two processes, run simultaneously in separate terminals:
```bash
# Terminal 1 — backend
uvicorn app.main:app

# Terminal 2 — frontend
streamlit run streamlit/ui.py
```
Open the Streamlit URL it prints (default `http://localhost:8501`).

---

### 3.8 Docker Compose

This repository includes a `docker-compose.yml` and Dockerfiles to run the full stack locally (Qdrant, Ollama, backend, and Streamlit UI).

- **Ports:** Qdrant `:6333`, Ollama `:11434`, backend `:8000`, UI `:8501`.
- **Volumes:** persistent volumes include `qdrant_data`, `ollama_data`, and `whisper_cache` (see `docker-compose.yml`).
- **Notes:** the backend image copies local Piper/TTS artifacts from `voice/piper` and `voice/voices` at build time — make sure those paths exist if you need TTS. Ollama and the backend request GPU devices when available; configure the NVIDIA container runtime on the host to enable GPU acceleration.

Quick start:

```bash
# Build and start all services (first run may pull models and take time)
docker compose up --build

# Run in background
docker compose up --build -d
```

Pre-pull Ollama models (optional, speeds first startup):

```bash
docker compose run --rm ollama-init
```

Run only selected services:

```bash
# Backend + Qdrant only
docker compose up --build backend qdrant
```

Troubleshooting tips:

- Check logs: `docker compose logs <service>` (e.g. `docker compose logs ollama`).
- If Ollama fails to load models, ensure `ollama` service has network access and sufficient resources.
- If Piper/TTS isn't working, verify the local `voice/piper` binary and `voice/voices` are present and were included during the backend image build (see [docker/app.Dockerfile](docker/app.Dockerfile)).



## 4. Features

- **Text chat** with source citations (`/chat`)
- **Voice input**: record via browser mic (or upload a pre-recorded clip as a reliability fallback — see §6) → ASR → RAG → spoken + text response, with a listen-before-send review step
- **Document upload**: PDF / DOCX / TXT / images (OCR fallback for scanned docs), embedded and scoped to the uploading user's session only — never leaks into other users' retrieval context (see §5)
- **Chat history** displayed in-session
- **Bilingual**: Arabic (MSA + Egyptian dialect) and English, auto-detected

---

## 5. Key Engineering Decisions & Tradeoffs

**LLM choice — `qwen2.5:7b` over `qwen3.5:4b`.**
`qwen3.5:4b` was tried first but has "thinking mode" enabled by default, which silently consumed the entire `num_predict` token budget before producing visible output — resulting in empty answers, up to ~80s latency, and Arabic answer truncation even at `num_predict=2000`. `qwen2.5:7b` produces correct, complete, appropriately-fast answers in both languages. `Falcon-Arabic 7B` and `Jais 30B` were also evaluated (dialect-specialized / best Arabic quality respectively) but not adopted — Jais was too heavy for the target hardware, Falcon-Arabic didn't outperform qwen2.5 enough to justify the switch given time constraints.



**Session-scoped document retrieval.** Uploaded documents are tagged with a `session_id` and filtered at query time (Qdrant `Filter`) so that a document uploaded by one user is never retrievable by another user's questions — only the general te.eg knowledge base is shared. This was a deliberate design decision given the brief specifies documents are "uploaded by user."

**Deterministic Qdrant point IDs.** Point IDs are an MD5 hash of `url + content_type + chunk_index + a hash of the chunk's own text` (not a random UUID), so re-running ingestion updates existing points instead of duplicating them. This required two iterations to get right


## 6. Known Issues & Limitations

- **Streamlit's built-in `st.audio_input()` has a confirmed upstream bug** (multiple open issues on Streamlit's GitHub) causing intermittent mid-recording audio corruption / dropped words. Switched to `streamlit-mic-recorder`, which records the full clip client-side and sends it as a single complete blob on stop, structurally avoiding the continuous-stream issue. A manual file-upload path is also provided as a guaranteed-reliable fallback, with a listen-before-send review step so a bad take is never silently sent to the model.
- **ASR language misdetection on very short clips**, especially without VAD filtering — found via a reproducible test (a short English clip was transcribed as Russian and consequently answered in Korean). Fixed by enabling `vad_filter=True` in `faster-whisper`, confirmed via before/after test on the same audio file.
- **A small number of scraped pages contain duplicate content** (same URL/content appearing twice in the dataset, likely from an overlapping crawl pass) — these correctly collapse to a single Qdrant point under the current deduping logic rather than causing retrieval noise, but the root duplication in the crawl itself hasn't been separately investigated given time constraints.
- **Content behind in-page JS tabs/scenario-selectors may not be captured.** The scraper (Playwright) takes one snapshot of each page's default-rendered state. If a page shows different content depending on a user-driven toggle (e.g. "select your case: new customer / tenant / foreign national / heir") without changing the URL, that content is not currently captured — a scope limitation for future work rather than an extraction bug.
- **No GPU fallback for Silero VAD** (used internally by `vad_filter=True`) — it always runs on CPU regardless of the main Whisper model's device setting. This is expected/upstream behavior and has negligible performance impact since VAD is lightweight relative to full transcription.


## 7. Notable Bugs Found & Fixed During Development

A few worth calling out as they reflect real debugging rather than just "it worked first try":

1. **Footer-text content corruption during scraping.** An early version of the article-selection logic sometimes picked a sitewide footer/regulatory-boilerplate block instead of real page content. Fixed by explicitly excluding blocks containing footer markers (English + Arabic) before selecting the best content block.
2. **Template-detection exclusivity bug.** Pages with both a main content section and an FAQ accordion were being classified as "FAQ-only," silently dropping their primary content (e.g. a "required documents" list) entirely. Fixed by extracting all applicable content types per page independently instead of picking one. Verified before/after: scraped record count went from 398 → 432 records after the fix.
3. **Qdrant point-ID collisions.** FAQ/legal/definition records don't get a meaningful `chunk_index` from the chunker (they're passed through as atomic units), so an ID scheme based on `chunk_index` alone caused many distinct FAQ questions on the same page to silently overwrite each other. Diagnosed via direct collision counting (263 of 639 chunks were being lost), then fixed by hashing each chunk's actual text content into the ID instead of relying on `chunk_index` or type-specific metadata that doesn't survive the chunking step.

---

## 8. Repository Structure
```
telecom-egypt-assistant/
├── app/                  # FastAPI backend (main.py + routes/)
├── data/                 # raw, processed, and embedded knowledge base data
├── scraper/               # te.eg crawler + extractor
├── ingestion/             # chunking, embedding, vector store, user-doc loader
├── rag/                   # generator + pipeline (retrieval + generation)
├── voice/                 # ASR (asr.py) + TTS (tts.py)
├── ui.py                  # Streamlit frontend
└── requirements.txt
```
