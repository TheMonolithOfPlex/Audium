# app/utils.py

import os
import json
import uuid
import filelock
import logging
from datetime import datetime, timedelta

UPLOAD_FOLDER = 'uploads'
HISTORY_FILE = 'uploads.json'
TRANSCRIPTS_FOLDER = 'static/transcripts'
LOG_FOLDER = 'logs'

# Set up logging
logging.basicConfig(
    filename='logs/utils.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('utils')

def ensure_directories():
    """Ensure all required directories and history file exist."""
    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(TRANSCRIPTS_FOLDER, exist_ok=True)
        os.makedirs(LOG_FOLDER, exist_ok=True)
        
        lock = filelock.FileLock(f"{HISTORY_FILE}.lock")
        with lock:
            if not os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'w') as f:
                    json.dump([], f)
                
        logger.info("Directory structure validated")
    except Exception as e:
        logger.error(f"Error ensuring directories: {str(e)}")
        raise


def save_upload(file_obj, username, language="en"):
    """
    Save uploaded file and log it to history.

    Args:
        file_obj: Werkzeug FileStorage object
        username: User who uploaded the file
        language: Language code for transcription
    Returns:
        tuple: (job_id, filename) - identifiers for the saved file
    """
    try:
        # Validate file_obj and generate a secure filename to prevent path traversal
        if not file_obj or not hasattr(file_obj, 'filename'):
            raise ValueError("Invalid file object provided")
        original_filename = file_obj.filename
        secure_filename = str(uuid.uuid4()) + os.path.splitext(original_filename)[1]
        
        job_id = str(uuid.uuid4())
        filepath = os.path.join(UPLOAD_FOLDER, secure_filename)
        
        # Save the file
        file_obj.save(filepath)
        file_size = os.path.getsize(filepath)

        entry = {
            "job_id": job_id,
            "original_filename": original_filename,
            "filename": secure_filename,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "Pending",
            "language": language,
            "file_size": file_size,
            "user": username,
            "display_name": original_filename
        }
        lock = filelock.FileLock(f"{HISTORY_FILE}.lock")
        with lock:
            if os.path.exists(HISTORY_FILE) and os.path.getsize(HISTORY_FILE) > 0:
                with open(HISTORY_FILE, 'r') as f:
                    history = json.load(f)
            else:
                history = []

            history.insert(0, entry)

            with open(HISTORY_FILE, 'w') as f:
                json.dump(history, f, indent=2)
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
        
        logger.info(f"File saved: {original_filename} by {username}, job_id: {job_id}")
        return job_id, secure_filename
    
    except Exception as e:
        logger.error(f"Error saving upload: {str(e)}")
        raise


def get_upload_history():
    """
    Load upload history from file.

    Returns:
        list: List of upload history entries.
    """
    try:
        lock = filelock.FileLock(f"{HISTORY_FILE}.lock")
        with lock:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r') as f:
                    return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Error loading upload history: {str(e)}")
        return []

    def update_job_status(job_id, status, error_message=None):
        """
        Update the status of a job in the history file.
    
        Args:
            job_id (str): ID of the job to update.
            status (str): New status of the job.
            error_message (str, optional): Optional error message.
    
        Returns:
            bool: True if update was successful, False otherwise.
        """
        try:
            if not os.path.exists(HISTORY_FILE):
                logger.warning(f"History file not found when updating job {job_id}")
                return False
    
            lock = filelock.FileLock(f"{HISTORY_FILE}.lock")
            with lock:
                with open(HISTORY_FILE, 'r') as f:
                    history = json.load(f)
    
                job_updated = False
                for job in history:
                    if job.get('job_id') == job_id:
                        job['status'] = status
                        if error_message:
                            job['error_message'] = error_message
                        job_updated = True
                        break
    
                if job_updated:
                    with open(HISTORY_FILE, 'w') as f:
                        json.dump(history, f, indent=2)
                    logger.info(f"Job {job_id} status updated to '{status}'")
                    return True
                else:
                    logger.warning(f"Job {job_id} not found when updating status")
                    return False
    
        except Exception as e:
            logger.error(f"Error updating job status: {str(e)}")
            return False
def get_job_by_id(job_id):
    """
    Get job details by ID.

    Args:
        job_id (str): ID of the job to find.

    Returns:
        dict: Job details if found, None otherwise.
    """
    try:
        lock = filelock.FileLock(f"{HISTORY_FILE}.lock")
        with lock:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r') as f:
                    history = json.load(f)
                for job in history:
                    if job.get('job_id') == job_id:
                        return job
        return None
    except Exception as e:
        logger.error(f"Error retrieving job by ID: {str(e)}")
        return None

def remove_old_uploads(days):
    """
    Remove uploads older than specified days.

    Args:
        days (int): Number of days to keep uploads.

    Returns:
        int: Number of files cleaned up.
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0

        lock = filelock.FileLock(f"{HISTORY_FILE}.lock")
        with lock:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r') as f:
                    history = json.load(f)

                new_history = []
                for job in history:
                    timestamp = job.get('timestamp')
                    if timestamp:
                        job_date = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                        if job_date < cutoff_date:
                            filename = job.get('filename')
                            if filename:
                                filepath = os.path.join(UPLOAD_FOLDER, filename)
                                if os.path.exists(filepath):
                                    os.remove(filepath)
                            transcript_path = os.path.join(TRANSCRIPTS_FOLDER, f"{job.get('job_id')}.txt")
                            if os.path.exists(transcript_path):
                                os.remove(transcript_path)
                            cleaned_count += 1
                        else:
                            new_history.append(job)

                with open(HISTORY_FILE, 'w') as f:
                    json.dump(new_history, f, indent=2)

        logger.info(f"Cleaned up {cleaned_count} old uploads")
        return cleaned_count
    except Exception as e:
        logger.error(f"Error cleaning old uploads: {str(e)}")
        return 0
        return 0
