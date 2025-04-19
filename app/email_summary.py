import os
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO   = os.getenv("EMAIL_TO", "").split(",")

HISTORY_FILE = 'uploads.json'

def load_today_uploads():
    if not os.path.exists(HISTORY_FILE):
        return []

    with open(HISTORY_FILE, 'r') as f:
        try:
            all_uploads = json.load(f)
        except json.JSONDecodeError:
            print("⚠️ Failed to decode uploads.json")
            return []

    today = datetime.now().strftime("%Y-%m-%d")
    uploads_today = []

    for item in all_uploads:
        timestamp = item.get("timestamp", "")
        if timestamp.startswith(today):
            uploads_today.append(item)

    return uploads_today

def send_summary_email():
    uploads = load_today_uploads()
    if not uploads:
        print("📭 No uploads today. Skipping email.")
        return

    subject = f"WhisperX Daily Upload Summary – {datetime.now().strftime('%Y-%m-%d')}"
    html_body = "<h2>📥 Today's Uploads</h2><ul style='font-family:sans-serif;'>"

    for item in uploads:
        filename = item.get("filename", "Unknown File")
        timestamp = item.get("timestamp", "Unknown Time")
        user = item.get("user", "Unknown User")
        html_body += f"<li><strong>{filename}</strong> at {timestamp} (by {user})</li>"

    html_body += "</ul>"

    msg = MIMEMultipart("alternative")
    msg["From"] = EMAIL_USER
    msg["To"] = ", ".join(EMAIL_TO)
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())
        print("✅ Summary email sent successfully.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

if __name__ == "__main__":
    send_summary_email()
