from faster_whisper import WhisperModel, BatchedInferencePipeline

model_size = "large-v3"
model = WhisperModel(model_size,device="cpu", compute_type="int8")
pipeline = BatchedInferencePipeline(model)

def transcribe(audio_path: str) -> tuple[str, str]:
    # Transcribe the audio file using None for language to let the model detect the language automatically
    segments, info = pipeline.transcribe(audio_path, language=None, beam_size=5, vad_filter=True)
    
    # Print the transcription segments
    segment_list = list(segments) 
    for segment in segment_list:
        print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
    # Concatenate the text from all segments into a single string    
    text = " ".join(s.text for s in segment_list)
    # Return the full transcription text and the detected language
    return text, info.language