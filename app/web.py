from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_wtf.csrf import CSRFProtect
from functools import wraps
import os
import json
import uuid
import filelock
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
from utils import ensure_directories, save_upload, get_upload_history, update_job_status
from auth_utils import validate_user, is_admin, create_user, migrate_users_to_hashed_passwords

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    filename='logs/app.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('web')

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24).hex())  # Get from environment variable or generate
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'  # Secure cookies in production
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access to cookies
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)  # Session expiration
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # Limit uploads to 500MB

csrf = CSRFProtect(app)  # Enable CSRF protection

UPLOAD_FOLDER = 'uploads'
HISTORY_FILE = 'uploads.json'
USERS_FILE = 'users.json'
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'flac', 'aac', 'ogg'}

# Ensure folders/files exist
ensure_directories()

# Migrate plaintext passwords (will run once at startup)
try:
    migration_result = migrate_users_to_hashed_passwords()
    if migration_result:
        logger.info("Successfully migrated user passwords to secure hashes")
    else:
        logger.info("No password migration needed or it failed")
except Exception as e:
    logger.error(f"Error during password migration: {e}")

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ----------------------------
# Authentication Middleware
# ----------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash("You must be logged in to access that page.", "error")
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash("You must be logged in to access that page.", "error")
            return redirect(url_for('login', next=request.path))
        
        if not is_admin(session['username']):
            flash("Administrator access required.", "error")
            return redirect(url_for('index'))
        
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
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('login.html')
        
        if validate_user(username, password):
            session['username'] = username
            session.permanent = True  # Use the permanent session lifetime
            
            # Create a new session ID to prevent session fixation
            session.regenerate = True
            
            next_page = request.args.get('next', url_for('index'))
            flash('Logged in successfully.', 'success')
            
            logger.info(f"Successful login: {username}")
            return redirect(next_page)
        else:
            flash('Invalid credentials or account inactive.', 'error')
            logger.warning(f"Failed login attempt for username: {username}")
            
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('register.html')
        
        # Validate username (alphanumeric and underscore only)
        if not username.isalnum() and '_' not in username:
            flash('Username must contain only letters, numbers, and underscores.', 'error')
            return render_template('register.html')
        
        # Validate password strength
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return render_template('register.html')
        
        # Create user
        success, message = create_user(username, email, password)
        if success:
            flash('Registration successful. You can now log in.', 'success')
            logger.info(f"New user registered: {username}")
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
    
    return render_template('register.html')


@app.route('/logout')
def logout():
    username = session.pop('username', None)
    session.clear()
    if username:
        logger.info(f"User logged out: {username}")
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
    
    if not allowed_file(file.filename):
        flash(f"Unsupported file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}", "error")
        return redirect(url_for('index'))
    
    try:
        # Generate a secure filename to prevent path traversal attacks
        original_filename = file.filename
        secure_filename = str(uuid.uuid4()) + os.path.splitext(original_filename)[1]
        job_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user = session.get('username', 'unknown')
        language = request.form.get('language', 'en')
        filepath = os.path.join(UPLOAD_FOLDER, secure_filename)
        file.save(filepath)
        file_size = os.path.getsize(filepath)

        # Build job metadata
        job_metadata = {
            "job_id": job_id,
            "original_filename": original_filename,  # Store original name
            "filename": secure_filename,  # Store secure name
            "timestamp": timestamp,
            "status": "Pending",
            "language": language,
            "file_size": file_size,
            "user": user,
            "diarization": False,
            "transcription_duration": None,
            "error_message": None,
            "display_name": original_filename  # For display purposes
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

        logger.info(f"File uploaded: {original_filename} by {user}")
        flash("File uploaded successfully. Transcription will begin shortly.", "success")
        
        # To actually start the transcription, we'd need to either:
        # 1. Call a function to start transcription (blocking)
        # 2. Add the job to a queue for background processing (better)
        # For now we'll just redirect to history
        return redirect(url_for('history'))
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        flash(f"Error uploading file: {str(e)}", "error")
        return redirect(url_for('index'))


@app.route('/history')
@login_required
def history():
    uploads = get_upload_history()
    # Filter uploads for non-admin users to only show their own uploads
    if 'username' in session and not is_admin(session['username']):
        uploads = [u for u in uploads if u.get('user') == session['username']]
    return render_template('history.html', uploads=uploads)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        language = request.form.get('language', 'en')
        auto_delete = 'auto_delete' in request.form
        
        # Update user settings here
        # For now, we'll just show a success message
        flash("Settings updated successfully.", "success")
        logger.info(f"User {session['username']} updated settings")
        
    return render_template('settings.html')


@app.route('/admin')
@admin_required
def admin():
    users = []
    raw_users = get_users()
    for user in raw_users:
        users.append({
            'username': user.get('username'),
            'email': user.get('email'),
            'role': user.get('role', 'user'),
            'status': 'Active' if user.get('active', True) else 'Inactive',
            'created_at': user.get('created_at', 'Unknown')
        })
    
    return render_template('admin.html', users=users)


@app.route('/admin/toggle/<username>', methods=['POST'])
@admin_required
def toggle_user_status(username):
    if username == session['username']:
        flash("You cannot deactivate your own account.", "error")
        return redirect(url_for('admin'))
    
    users_data = get_users()
    
    lock = filelock.FileLock(f"{USERS_FILE}.lock")
    with lock:
        user_found = False
        for user in users_data:
            if user.get('username') == username:
                user['active'] = not user.get('active', True)
                user_found = True
                status = 'activated' if user['active'] else 'deactivated'
                logger.info(f"User {username} {status} by {session['username']}")
                break
        
        if user_found:
            with open(USERS_FILE, 'w') as f:
                json.dump(users_data, f, indent=2)
            flash(f"User {username} has been {'activated' if user['active'] else 'deactivated'}.", "success")
        else:
            flash(f"User {username} not found.", "error")
    
    return redirect(url_for('admin'))


@app.route('/admin/delete/<job_id>', methods=['DELETE'])
@admin_required
def delete_job(job_id):
    try:
        uploads = get_upload_history()
        job_to_delete = None
        
        # Find the job
        for job in uploads:
            if job.get('job_id') == job_id:
                job_to_delete = job
                break
        
        if not job_to_delete:
            return jsonify({"message": "Job not found"}), 404
        
        # Remove the actual files
        filename = job_to_delete.get('filename')
        if filename:
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                
        # Remove transcript files
        transcript_path = os.path.join('transcripts', f"{job_id}.txt")
        if os.path.exists(transcript_path):
            os.remove(transcript_path)
            
        # Update history file
        lock = filelock.FileLock(f"{HISTORY_FILE}.lock")
        with lock:
            uploads = [job for job in uploads if job.get('job_id') != job_id]
            with open(HISTORY_FILE, 'w') as f:
                json.dump(uploads, f, indent=2)
        
        logger.info(f"Job {job_id} deleted by {session['username']}")
        return jsonify({"message": "Job deleted successfully"}), 200
    
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {str(e)}")
        return jsonify({"message": f"Error: {str(e)}"}), 500


@app.route('/admin/rename/<job_id>', methods=['POST'])
@admin_required
def rename_job(job_id):
    try:
        data = request.json
        new_name = data.get('new_name', '').strip()
        
        if not new_name:
            return jsonify({"message": "New name cannot be empty"}), 400
        
        uploads = get_upload_history()
        
        lock = filelock.FileLock(f"{HISTORY_FILE}.lock")
        with lock:
            job_updated = False
            for job in uploads:
                if job.get('job_id') == job_id:
                    job['display_name'] = new_name
                    job_updated = True
                    break
            
            if job_updated:
                with open(HISTORY_FILE, 'w') as f:
                    json.dump(uploads, f, indent=2)
                logger.info(f"Job {job_id} renamed to '{new_name}' by {session['username']}")
                return jsonify({"message": "File renamed successfully"}), 200
            else:
                return jsonify({"message": "Job not found"}), 404
    
    except Exception as e:
        logger.error(f"Error renaming job {job_id}: {str(e)}")
        return jsonify({"message": f"Error: {str(e)}"}), 500


@app.route('/analytics')
@login_required
def analytics():
    uploads = get_upload_history()
    
    # For admin, show all uploads. For regular users, filter to their uploads
    if not is_admin(session.get('username')):
        uploads = [u for u in uploads if u.get('user') == session.get('username')]
    
    stats = {
        'total_uploads': len(uploads),
        'average_size': 0,
        'peak_hour': 'N/A',
        'success_rate': 0
    }
    
    if uploads:
        # Calculate average file size
        total_size = sum(u.get('file_size', 0) for u in uploads)
        stats['average_size'] = round(total_size / len(uploads) / (1024 * 1024), 2)  # in MB
        
        # Calculate success rate
        completed = sum(1 for u in uploads if u.get('status') == 'Complete')
        stats['success_rate'] = round((completed / len(uploads)) * 100, 1)
        
        # Find peak usage time (hour)
        hour_counts = {}
        for upload in uploads:
            ts = upload.get('timestamp', '')
            if ts:
                try:
                    dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                    hour = dt.hour
                    hour_counts[hour] = hour_counts.get(hour, 0) + 1
                except ValueError:
                    pass
        
        if hour_counts:
            peak_hour = max(hour_counts, key=hour_counts.get)
            stats['peak_hour'] = f"{peak_hour:02d}:00 - {peak_hour+1:02d}:00"
    
    return render_template('analytics.html', stats=stats)


@app.route('/log')
@admin_required
def log():
    log_file = 'logs/app.log'
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                log_lines = f.readlines()[-100:]  # show last 100 lines
        except Exception as e:
            log_lines = [f"Error reading log file: {str(e)}"]
    else:
        log_lines = ["Log file does not exist yet."]
    return render_template('log.html', log_lines=log_lines)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error="404 - Page Not Found"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error="500 - Server Error"), 500


# ----------------------------
# Run Server
# ----------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9200, debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true')
