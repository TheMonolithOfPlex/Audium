import os
import json
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

HISTORY_FILE = 'uploads.json'

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO   = os.getenv("EMAIL_TO", "").split(",")  # Supports multiple recipients

def load_recent_uploads():
    if not os.path.exists(HISTORY_FILE):
        return []

    with open(HISTORY_FILE, 'r') as f:
        try:
            uploads = json.load(f)
        except json.JSONDecodeError:
            print("Failed to parse uploads.json")
            return []

    now = datetime.now()
    past_24_hours = now - timedelta(days=1)

    recent = []
    for item in uploads:
        ts_str = item.get('timestamp')
        if not ts_str:
            continue
        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            if ts > past_24_hours:
                recent.append(item)
        except ValueError:
            print(f"Skipping invalid timestamp: {ts_str}")
            continue
    return recent

def send_email_summary(uploads):
    if not uploads:
        print("No uploads in the last 24 hours.")
        return

    lines = [
        f"- {item.get('filename', 'Unknown File')} ({item.get('timestamp')}) uploaded by {item.get('username', 'unknown')}"
        for item in uploads
    ]
    body = "Here are the uploads from the last 24 hours:\n\n" + "\n".join(lines)

    msg = MIMEText(body)
    msg['Subject'] = f"WhisperX - Daily Upload Summary ({datetime.now().strftime('%Y-%m-%d')})"
    msg['From'] = EMAIL_USER
    msg['To'] = ", ".join(EMAIL_TO)

    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())
        print("✅ Daily summary sent successfully.")
    except Exception as e:
        print("❌ Failed to send email:", e)

if __name__ == "__main__":
    uploads = load_recent_uploads()
    send_email_summary(uploads)
