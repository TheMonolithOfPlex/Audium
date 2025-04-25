# app/email_manager.py
import os
import smtplib
import logging
# Removed unused import
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load environment variables
if not load_dotenv():
    logging.warning("Environment variables file (.env) not found or could not be loaded. Ensure environment variables are set.")
else:
    logging.info(".env file loaded successfully.")

# Ensure the logs directory exists
try:
    os.makedirs('logs', exist_ok=True)
except OSError as e:
    logging.error(f"Failed to create logs directory: {e}")
    raise

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
        smtp_port = int(os.getenv('SMTP_PORT', 587))
    except ValueError:
        logging.error("Invalid SMTP_PORT value in environment variables. Must be an integer.")
        raise ValueError("Invalid SMTP_PORT value in environment variables.")

    smtp_server = os.getenv('SMTP_SERVER', '').strip()
    sender_email = os.getenv('EMAIL_ADDRESS', '').strip()
    sender_password = os.getenv('EMAIL_PASSWORD', '').strip()

    if not smtp_server or not sender_email or not sender_password:
        logging.error("Missing SMTP configuration in environment variables.")
        raise ValueError("SMTP configuration is incomplete. Please check your .env file.")

    # Validate recipient email
    if not recipient_email or "@" not in recipient_email:
        logging.error(f"Invalid recipient email: {recipient_email}")
        raise ValueError("Invalid recipient email address.")

    # Create the email
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        logging.info(f"Email sent to {recipient_email} with subject: {subject}")
        return True
    except smtplib.SMTPException as smtp_error:
        logging.error(f"SMTP error occurred: {smtp_error}")
        return False
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        return False