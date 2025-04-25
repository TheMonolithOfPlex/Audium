# app/email_manager.py
import os
import json
import smtplib
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    filename='logs/email.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def send_email(subject, body, recipient_email):
    """
    Sends an email with the specified subject and body to the recipient.
    """
    try:
        smtp_server = os.getenv('SMTP_SERVER')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        sender_email = os.getenv('EMAIL_ADDRESS')
        sender_password = os.getenv('EMAIL_PASSWORD')

        if not all([smtp_server, smtp_port, sender_email, sender_password]):
            logging.error("Missing SMTP configuration in environment variables.")
            return False

        # Create the email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Send the email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)

        logging.info(f"Email sent to {recipient_email} with subject: {subject}")
        return True

    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        return False