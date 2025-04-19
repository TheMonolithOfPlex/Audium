# web_transcribe.py
import os
import json
import logging
import time
from datetime import datetime
import filelock
import torch
import uuid
import traceback
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    filename='logs/transcribe.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

UPLOAD_FOLDER = "uploads"
TRANSCRIPTS_FOLDER = "transcripts"
HISTORY_FILE = "uploads.json"

os.makedirs(TRANSCRIPTS_FOLDER, exist_ok=True)

# Load models with error handling
try:
    whisper_model = WhisperModel("large-v2", compute_type="float16" if torch.cuda.is_available() else "int8")
    logger.info("Whisper model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load Whisper model: {str(e)}")
    whisper_model = None

try:
    diarization_pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token=os.getenv("HF_TOKEN"))
    logger.info("Diarization pipeline loaded successfully")
except Exception as e:
    logger.error(f"Failed to load diarization pipeline: {str(e)}")
    diarization_pipeline = None

def update_job_status(job_id, status, error_message=None):
    """Update job status in history file"""
    if not os.path.exists(HISTORY_FILE):
        return False
    
    lock = filelock.FileLock(f"{HISTORY_FILE}.lock")
    with lock:
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)
        
        for job in data:
            if job.get('job_id') == job_id:
                job['status'] = status
                if error_message:
                    job['error_message'] = error_message
                break
        
        with open(HISTORY_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    
    return True

def transcribe_file(job_id=None, filename=None, language="en", user="unknown"):
    """
    Transcribe an audio file with diarization.
    
    Args:
        job_id: Optional job ID (creates new one if None)
        filename: Name of the file to transcribe
        language: Language code for transcription
        user: Username who initiated the transcription
    
    Returns:
        tuple: (job_id, transcript_path)
    """
    if not job_id:
        job_id = str(uuid.uuid4())
    
    if not filename:
        logger.error("No filename provided for transcription")
        return job_id, None
    
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(filepath):
        error_msg = f"File not found: {filepath}"
        logger.error(error_msg)
        update_job_status(job_id, "Failed", error_msg)
        return job_id, None
    
    file_size = os.path.getsize(filepath)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    transcript_path = os.path.join(TRANSCRIPTS_FOLDER, f"{job_id}.txt")
    
    # Record the job start time
    start_time = time.time()
    
    try:
        logger.info(f"Starting transcription of {filename} (job_id: {job_id})")
        
        # Update status to "Processing"
        update_job_status(job_id, "Processing")
        
        # Check if models loaded correctly
        if not whisper_model:
            raise Exception("Whisper model failed to load")
        
        has_diarization = False
        if diarization_pipeline:
            try:
                logger.info(f"Running diarization on {filename}")
                diarization = diarization_pipeline(filepath)
                has_diarization = True
                logger.info("Diarization completed successfully")
            except Exception as e:
                logger.warning(f"Diarization failed, continuing with transcription only: {str(e)}")
        else:
            logger.warning("Diarization pipeline not available, skipping diarization")
        
        # Whisper transcription
        logger.info(f"Running Whisper transcription on {filename}")
        segments, _ = whisper_model.transcribe(filepath, language=language, beam_size=5)
        
        transcript_lines = []
        for segment in segments:
            text = segment.text.strip()
            start = segment.start
            end = segment.end
            transcript_lines.append(f"[{start:.2f} - {end:.2f}] {text}")
        
        transcript_text = "\n".join(transcript_lines)
        
        # Write transcript to file
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript_text)
        
        # Calculate duration
        transcription_duration = time.time() - start_time
        
        # Update job status
        lock = filelock.FileLock(f"{HISTORY_FILE}.lock")
        with lock:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r') as f:
                    data = json.load(f)
            else:
                data = []
            
            # Update existing job or create new one
            job_updated = False
            for job in data:
                if job.get('job_id') == job_id:
                    job['status'] = "Complete"
                    job['diarization'] = has_diarization
                    job['transcription_duration'] = round(transcription_duration, 2)
                    job_updated = True
                    break
            
            if not job_updated:
                # Create new job record
                record = {
                    "job_id": job_id,
                    "filename": filename,
                    "timestamp": timestamp,
                    "status": "Complete",
                    "language": language,
                    "file_size": file_size,
                    "user": user,
                    "diarization": has_diarization,
                    "transcription_duration": round(transcription_duration, 2)
                }
                data.insert(0, record)
            
            with open(HISTORY_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        
        logger.info(f"Transcription completed for {filename} (job_id: {job_id})")
        return job_id, transcript_path
    
    except Exception as e:
        error_msg = f"Transcription failed: {str(e)}"
        logger.error(f"Error transcribing {filename}: {error_msg}")
        logger.error(traceback.format_exc())
        update_job_status(job_id, "Failed", error_msg)
        return job_id, None
