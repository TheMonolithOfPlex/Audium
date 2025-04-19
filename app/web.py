from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
import os
import json
from utils import ensure_directories, save_upload, get_upload_history

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'your_secret_key_here'  # Replace in production

USER_CREDENTIALS = {
    'jpratt': 'owens2128'
}

# Ensure folders/files exist
ensure_directories()

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
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            session['username'] = username
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


import uuid

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    file = request.files['file']
    if file:
        filename = file.filename
        job_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user = session.get('username', 'unknown')
        language = request.form.get('language', 'en')  # Optional language selection
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

        # Load existing uploads
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

    flash("No file selected.", "error")
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
@login_required
def admin():
    # Example user data
    users = [
        {'username': 'jpratt', 'role': 'admin', 'status': 'active'},
        {'username': 'testuser', 'role': 'user', 'status': 'inactive'}
    ]
    return render_template('admin.html', users=users)


@app.route('/analytics')
@login_required
def analytics():
    return render_template('analytics.html')


@app.route('/log')
@login_required
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
    app.run(host='0.0.0.0', port=9200)
