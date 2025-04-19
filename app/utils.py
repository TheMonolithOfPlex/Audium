# utils.py

import os
import json
import filelock
from datetime import datetime

UPLOAD_FOLDER = 'uploads'
HISTORY_FILE = 'uploads.json'
TRANSCRIPTS_FOLDER = 'transcripts'


def ensure_directories():
    """Ensure upload directory and history file exist."""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(TRANSCRIPTS_FOLDER, exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w') as f:
            json.dump([], f)


def save_upload(file_obj, username):
    """
    Save uploaded file and log it to history.

    Args:
        file_obj: Werkzeug FileStorage object
        username: User who uploaded the file
    Returns:
        filename (str): name of saved file
    """
    filename = file_obj.filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file_obj.save(filepath)
    file_size = os.path.getsize(filepath)

    entry = {
        "job_id": str(uuid.uuid4()),
        "filename": filename,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Pending",
        "language": "en",  # Default, update as needed
        "file_size": file_size,
        "user": username
    }

    # Use file locking to prevent race conditions
    lock = filelock.FileLock(f"{HISTORY_FILE}.lock")
    with lock:
        with open(HISTORY_FILE, 'r') as f:
            history = json.load(f)

        history.insert(0, entry)

        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)

    return filename


def get_upload_history():
    """
    Load upload history from file.

    Returns:
        list of dicts with keys: filename, timestamp, user, etc.
    """
    if os.path.exists(HISTORY_FILE):
        lock = filelock.FileLock(f"{HISTORY_FILE}.lock")
        with lock:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
    return []


def update_job_status(job_id, status, error_message=None):
    """
    Update job status in history file.
    
    Args:
        job_id: ID of the job to update
        status: New status ("Complete", "Failed", etc.)
        error_message: Optional error message
    """
    if not os.path.exists(HISTORY_FILE):
        return False
    
    lock = filelock.FileLock(f"{HISTORY_FILE}.lock")
    with lock:
        with open(HISTORY_FILE, 'r') as f:
            history = json.load(f)
        
        for job in history:
            if job.get('job_id') == job_id:
                job['status'] = status
                if error_message:
                    job['error_message'] = error_message
                break
        
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    
    return True
