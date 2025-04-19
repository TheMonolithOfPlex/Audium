from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
import os
import json
from datetime import datetime
import uuid
import filelock
from dotenv import load_dotenv
from utils import ensure_directories, save_upload, get_upload_history

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.getenv('SECRET_KEY', 'generated_secret_key')  # Get from environment variable

UPLOAD_FOLDER = 'uploads'
HISTORY_FILE = 'uploads.json'
USERS_FILE = 'users.json'

# Ensure folders/files exist
ensure_directories()

# ----------------------------
# User Authentication Functions
# ----------------------------
def get_users():
    """Load users from JSON file"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return []

def validate_user(username, password):
    """Validate user credentials against stored users"""
    # In a production environment, this should use a proper database
    # and passwords should be hashed
    users_data = get_users()
    for user in users_data:
        if user.get('username') == username and user.get('password') == password:
            return user.get('active', True)  # Check if user is active
    return False

# ----------------------------
# Authentication Middleware
# ----------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash("You must be logged in to access that page.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash("You must be logged in to access that page.", "error")
            return redirect(url_for('login'))
        
        # Check if user is admin (you'll need to implement this logic)
        users_data = get_users()
        for user in users_data:
            if user.get('username') == session['username'] and user.get('role') == 'admin':
                return f(*args, **kwargs)
        
        flash("Administrator access required.", "error")
        return redirect(url_for('index'))
    return decorated_function

# ----------------------------
# Routes
# ----------------------------
@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if validate_user(username, password):
            session['username'] = username
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials or account inactive.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'file' not in request.files:
        flash("No file part in the request.", "error")
        return redirect(url_for('index'))
        
    file = request.files['file']
    if file.filename == '':
        flash("No file selected.", "error")
        return redirect(url_for('index'))
    
    try:
        filename = file.filename
        job_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user = session.get('username', 'unknown')
        language = request.form.get('language', 'en')
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        file_size = os.path.getsize(filepath)

        # Build job metadata
        job_metadata = {
            "job_id": job_id,
            "filename": filename,
            "timestamp": timestamp,
            "status": "Pending",
            "language": language,
            "file_size": file_size,
            "user": user,
            "diarization": False,
            "transcription_duration": None,
            "error_message": None
        }

        # Load existing uploads with file locking
        lock = filelock.FileLock(f"{HISTORY_FILE}.lock")
        with lock:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r') as f:
                    history = json.load(f)
            else:
                history = []

            # Insert new job at the top
            history.insert(0, job_metadata)

            # Save updated uploads
            with open(HISTORY_FILE, 'w') as f:
                json.dump(history, f, indent=2)

        flash("File uploaded successfully. Transcription will begin shortly.", "success")
        return redirect(url_for('history'))
    except Exception as e:
        flash(f"Error uploading file: {str(e)}", "error")
        return redirect(url_for('index'))


@app.route('/history')
@login_required
def history():
    uploads = get_upload_history()
    return render_template('history.html', uploads=uploads)


@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')


@app.route('/admin')
@admin_required
def admin():
    users = get_users()
    return render_template('admin.html', users=users)


@app.route('/admin/toggle/<username>', methods=['POST'])
@admin_required
def toggle_user_status(username):
    users_data = get_users()
    
    lock = filelock.FileLock(f"{USERS_FILE}.lock")
    with lock:
        for user in users_data:
            if user.get('username') == username:
                user['active'] = not user.get('active', True)
                break
        
        with open(USERS_FILE, 'w') as f:
            json.dump(users_data, f, indent=2)
    
    flash(f"User {username} status updated.", "success")
    return redirect(url_for('admin'))


@app.route('/analytics')
@login_required
def analytics():
    return render_template('analytics.html')


@app.route('/log')
@admin_required
def log():
    log_file = 'logs/system.log'
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            log_lines = f.readlines()[-100:]  # show last 100 lines
    else:
        log_lines = []
    return render_template('log.html', log_lines=log_lines)


# ----------------------------
# Run Server
# ----------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9200, debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true')
