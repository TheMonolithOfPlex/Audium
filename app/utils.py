# utils.py

import os
import json
from datetime import datetime

UPLOAD_FOLDER = 'uploads'
HISTORY_FILE = 'uploads.json'


def ensure_directories():
    """Ensure upload directory and history file exist."""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
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

    entry = {
        "filename": filename,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": username
    }

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
        list of dicts with keys: filename, timestamp, user
    """
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return []
