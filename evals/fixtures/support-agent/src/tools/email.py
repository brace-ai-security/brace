import os
import smtplib
from email.message import EmailMessage

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.sendgrid.net")
SMTP_USER = os.environ.get("SMTP_USER", "apikey")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
FROM_ADDR = "support@helpwise.io"


def send_email(to: str, subject: str, body: str) -> str:
    msg = EmailMessage()
    msg["From"] = FROM_ADDR
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, 587) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(msg)
    return f"Email sent to {to}."
