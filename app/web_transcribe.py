# web_transcribe.py
import os
import json
from datetime import datetime
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline
import torch
import uuid

UPLOAD_FOLDER = "uploads"
TRANSCRIPTS_FOLDER = "transcripts"
HISTORY_FILE = "uploads.json"

os.makedirs(TRANSCRIPTS_FOLDER, exist_ok=True)

# Load models
whisper_model = WhisperModel("large-v2", compute_type="float16" if torch.cuda.is_available() else "int8")
diarization_pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token=os.getenv("HF_TOKEN"))

def transcribe_file(filename, language="en", user="unknown"):
    job_id = str(uuid.uuid4())
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file_size = os.path.getsize(filepath)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Diarization
    diarization = diarization_pipeline(filepath)

    # Whisper transcription
    segments, _ = whisper_model.transcribe(filepath, language=language, beam_size=5)
    transcript_lines = []
    for segment in segments:
        text = segment.text.strip()
        start = segment.start
        end = segment.end
        transcript_lines.append(f"[{start:.2f} - {end:.2f}] {text}")

    transcript_text = "\n".join(transcript_lines)
    transcript_path = os.path.join(TRANSCRIPTS_FOLDER, f"{job_id}.txt")
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcript_text)

    # Update history
    record = {
        "job_id": job_id,
        "filename": filename,
        "timestamp": timestamp,
        "status": "Complete",
        "language": language,
        "file_size": file_size,
        "user": user
    }

    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)
    else:
        data = []

    data.insert(0, record)

    with open(HISTORY_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    return job_id, transcript_path
