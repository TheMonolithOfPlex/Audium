from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import os
import json
from functools import wraps

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'your_secret_key_here'

UPLOAD_FOLDER = 'uploads'
HISTORY_FILE = 'uploads.json'
TRANSCRIPTS_FOLDER = 'transcripts'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TRANSCRIPTS_FOLDER, exist_ok=True)
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'w') as f:
        json.dump([], f)

# Login decorator (as before)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash("You must be logged in to access that page.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

# [ ... Existing routes ... ]

# -- NEW: Update Transcript Segment by ID --
@app.route('/transcript/<transcript_id>/segment/<segment_id>', methods=['PUT'])
@login_required
def update_transcript_segment(transcript_id, segment_id):
    """
    Receives: { "text": "Corrected text" }
    Edits the transcript segment and saves the transcript.
    """
    transcript_path = os.path.join(TRANSCRIPTS_FOLDER, f"{transcript_id}.json")
    if not os.path.exists(transcript_path):
        return jsonify({'success': False, 'message': 'Transcript not found'}), 404
    with open(transcript_path, 'r') as f:
        data = json.load(f)
    updated = False
    for seg in data.get('segments', []):
        if seg.get('id') == segment_id:
            if request.is_json and isinstance(request.json, dict) and 'text' in request.json:
                seg['text'] = request.json['text']
            updated = True
            break
    if updated:
        with open(transcript_path, 'w') as f:
            json.dump(data, f, indent=2)
        return jsonify({'success': True, 'message': 'Segment updated'})
    else:
        return jsonify({'success': False, 'message': 'Segment not found'}), 404

# [ ... Rest of your app ... ]

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9200)
