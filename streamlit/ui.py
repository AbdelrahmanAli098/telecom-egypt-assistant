import base64
import uuid

import requests
import streamlit as st
from streamlit_mic_recorder import mic_recorder

# Config
API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Telecom Egypt Assistant", page_icon="📞", layout="centered")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []  # each item: {"role": "user"/"assistant", "text": ..., "sources": [...], "audio_b64": None}

if "pending_audio" not in st.session_state:
    st.session_state.pending_audio = None  # holds bytes waiting for review/send

st.title("📞 Telecom Egypt Assistant")
st.caption(f"Session: `{st.session_state.session_id[:8]}...`")

# Helper functions — thin wrappers around the FastAPI endpoints
def call_chat(question: str) -> dict:
    resp = requests.post(
        f"{API_BASE_URL}/chat",
        json={"question": question, "session_id": st.session_state.session_id},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def call_upload(file) -> dict:
    files = {"file": (file.name, file.getvalue(), file.type)}
    data = {"session_id": st.session_state.session_id}
    resp = requests.post(f"{API_BASE_URL}/upload", files=files, data=data, timeout=180)
    resp.raise_for_status()
    return resp.json()


def call_voice(audio_bytes: bytes) -> dict:
    files = {"file": ("recording.wav", audio_bytes, "audio/wav")}
    data = {"session_id": st.session_state.session_id}
    resp = requests.post(f"{API_BASE_URL}/voice", files=files, data=data, timeout=180)
    resp.raise_for_status()
    return resp.json()


def render_sources(sources: list[str]):
    if sources:
        with st.expander(f"Sources ({len(sources)})"):
            for src in sources:
                st.markdown(f"- {src}")


def process_voice_bytes(audio_bytes: bytes):
    with st.chat_message("user"):
        st.audio(audio_bytes, format="audio/wav")

    with st.spinner("Transcribing and thinking..."):
        try:
            result = call_voice(audio_bytes)
        except requests.exceptions.RequestException as e:
            st.error(f"Voice request failed: {e}")
            return

    transcript = result.get("transcript", "")
    answer = result.get("answer", "")
    sources = result.get("sources", [])
    audio_b64 = result.get("audio_base64")

    st.session_state.messages.append({"role": "user", "text": transcript})
    st.session_state.messages.append(
        {"role": "assistant", "text": answer, "sources": sources, "audio_b64": audio_b64}
    )
    st.session_state.pending_audio = None
    st.rerun()


# Sidebar — document upload
with st.sidebar:
    st.header("📄 Upload a document")
    st.caption("PDF, DOCX, TXT, or images. Only visible to your session.")
    uploaded_file = st.file_uploader(
        "Choose a file", type=["pdf", "docx", "txt", "png", "jpg", "jpeg"]
    )
    if uploaded_file is not None:
        if st.button("Upload & index"):
            with st.spinner("Processing document..."):
                try:
                    result = call_upload(uploaded_file)
                    st.success(
                        f"Uploaded: {result['stored_chunks']} chunks indexed."
                    )
                except requests.exceptions.RequestException as e:
                    st.error(f"Upload failed: {e}")

    st.divider()
    if st.button("🗑️ Clear chat history"):
        st.session_state.messages = []
        st.rerun()

# Chat history display
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["text"])
        if msg["role"] == "assistant":
            render_sources(msg.get("sources", []))
            if msg.get("audio_b64"):
                st.audio(base64.b64decode(msg["audio_b64"]), format="audio/wav")

# Voice input
st.subheader("🎙️ Ask by voice")
tab_record, tab_upload = st.tabs(["Record", "Upload a recording"])

with tab_record:
    mic_result = mic_recorder(
        start_prompt="🔴 Start recording",
        stop_prompt="⏹️ Stop recording",
        just_once=True,
        use_container_width=True,
        key="mic_recorder",
    )
    if mic_result is not None and mic_result.get("bytes"):
        st.session_state.pending_audio = mic_result["bytes"]

with tab_upload:
    st.caption("If the recorder ever cuts off words, record with any voice memo app and upload the file here instead.")
    uploaded_audio = st.file_uploader("Upload audio", type=["wav", "m4a", "mp3", "ogg"], key="voice_upload")
    if uploaded_audio is not None:
        st.session_state.pending_audio = uploaded_audio.getvalue()

# Review step: listen before sending
if st.session_state.pending_audio:
    st.markdown("**Review your recording:**")
    st.audio(st.session_state.pending_audio)

    col_send, col_discard = st.columns(2)
    with col_send:
        if st.button("✅ Sounds good — send", use_container_width=True):
            process_voice_bytes(st.session_state.pending_audio)
    with col_discard:
        if st.button("🗑️ Discard and re-record", use_container_width=True):
            st.session_state.pending_audio = None
            st.rerun()

# Text input
text_question = st.chat_input("Type your question here...")

if text_question:
    st.session_state.messages.append({"role": "user", "text": text_question})

    with st.spinner("Thinking..."):
        try:
            result = call_chat(text_question)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "text": result.get("answer", ""),
                    "sources": result.get("sources", []),
                    "audio_b64": None,  # text chat has no TTS response
                }
            )
        except requests.exceptions.RequestException as e:
            st.session_state.messages.append(
                {"role": "assistant", "text": f"Error contacting backend: {e}", "sources": []}
            )

    st.rerun()