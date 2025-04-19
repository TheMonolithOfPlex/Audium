# app/utils.py

import os
import json
import uuid
import filelock
import logging
from datetime import datetime

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
        # Generate a secure filename to prevent path traversal
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

        # Use file locking to prevent race conditions
        lock = filelock.FileLock(f"{HISTORY_FILE}.lock")
        with lock:
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)

            history.insert(0, entry)

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
        list of dicts with keys: filename, timestamp, user, etc.
    """
    try:
        if os.path.exists(HISTORY_FILE):
            lock = filelock.FileLock(f"{HISTORY_FILE}.lock")
            with lock:
                with open(HISTORY_FILE, 'r') as f:
                    return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Error loading upload history: {str(e)}")
        return []


def update_job_status(job_id, status, error_message=None):
    """
    Update job status in history file.
    
    Args:
        job_id: ID of the job to update
        status: New status ("Complete", "Failed", etc.)
        error_message: Optional error message
    
    Returns:
        bool: True if update was successful, False otherwise
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
        job_id: ID of the job to find
    
    Returns:
        dict: Job details if found, None otherwise
    """
    try:
        history = get_upload_history()
        for job in history:
            if job.get('job_id') == job_id:
                return job
        return None
    except Exception as e:
        logger.error(f"Error getting job by ID: {str(e)}")
        return None


def clean_old_uploads(days=30):
    """
    Remove uploads older than specified days.
    
    Args:
        days: Number of days to keep uploads
    
    Returns:
        int: Number of files cleaned up
    """
    try:
        history = get_upload_history()
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0
        
        for job in history:
            timestamp = job.get('timestamp')
            if timestamp:
                try:
                    job_date = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                    if job_date < cutoff_date:
                        # Delete associated files
                        filename = job.get('filename')
                        job_id = job.get('job_id')
                        
                        if filename:
                            filepath = os.path.join(UPLOAD_FOLDER, filename)
                            if os.path.exists(filepath):
                                os.remove(filepath)
                        
                        # Delete transcript files
                        transcript_path = os.path.join(TRANSCRIPTS_FOLDER, f"{job_id}.txt")
                        if os.path.exists(transcript_path):
                            os.remove(transcript_path)
                        
                        cleaned_count += 1
                except ValueError:
                    logger.warning(f"Invalid timestamp format: {timestamp}")
        
        # Update history file to remove deleted jobs
        if cleaned_count > 0:
            new_history = [job for job in history if job.get('timestamp') and 
                           datetime.strptime(job.get('timestamp'), "%Y-%m-%d %H:%M:%S") >= cutoff_date]
            
            lock = filelock.FileLock(f"{HISTORY_FILE}.lock")
            with lock:
                with open(HISTORY_FILE, 'w') as f:
                    json.dump(new_history, f, indent=2)
        
        logger.info(f"Cleaned up {cleaned_count} old uploads")
        return cleaned_count
    
    except Exception as e:
        logger.error(f"Error cleaning old uploads: {str(e)}")
        return 0
