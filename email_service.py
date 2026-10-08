import smtplib
import ssl
from email.message import EmailMessage

import streamlit as st


def _get_config():
    """Read email settings from .streamlit/secrets.toml. Returns None if missing."""
    try:
        cfg = st.secrets["email"]
        sender = str(cfg["sender"]).strip()
        password = str(cfg["app_password"]).strip()
        host = str(cfg.get("smtp_host", "smtp.gmail.com"))
        port = int(cfg.get("smtp_port", 465))
    except Exception:
        return None
    if "your_email" in sender or password.startswith("xxxx"):
        return None  # placeholder values, not configured yet
    return sender, password, host, port


def send_email(to_address, subject, body):
    """Send an email. NEVER raises an error. Returns (ok: bool, message: str)."""
    to_address = (to_address or "").strip()
    if not to_address:
        return False, "No email address provided."

    config = _get_config()
    if config is None:
        return False, "Email is not configured in secrets.toml."
    sender, password, host, port = config

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=15) as server:
            server.login(sender, password)
            server.send_message(msg)
        return True, f"Email sent to {to_address}."
    except Exception as exc:
        return False, f"Email could not be sent: {exc}"


def notify_submission(employee, email, req_id, leave_type, start_date, end_date, days):
    body = (
        f"Dear {employee},\n\n"
        f"Your leave request #{req_id} has been received.\n\n"
        f"Leave type : {leave_type}\n"
        f"From       : {start_date}\n"
        f"To         : {end_date}\n"
        f"Working days: {days}\n\n"
        "Status: PENDING. The administrator will review your request.\n\n"
        "RP Ngoma College - Smart Leave Management System"
    )
    return send_email(email, f"Leave request #{req_id} received", body)


def notify_decision(employee, email, req_id, status, note=""):
    body = (
        f"Dear {employee},\n\n"
        f"Your leave request #{req_id} has been {status.upper()} by the administrator.\n"
    )
    if note:
        body += f"\nAdministrator note: {note}\n"
    body += "\nRP Ngoma College - Smart Leave Management System"
    return send_email(email, f"Leave request #{req_id} {status}", body)