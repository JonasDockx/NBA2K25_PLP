"""
Sending outgoing e-mail over SMTP, through the Flask-Mail instance created in
app/__init__.py.
"""

import logging

from flask_mail import Message
import socket

from app import app, mail

logger = logging.getLogger(__name__)

def mail_is_configured():
    """
    True when the app actually has SMTP credentials to send with.
    """
    return bool(app.config.get("MAIL_USERNAME") and app.config.get("MAIL_PASSWORD"))

def send_email(recipient, subject, message_text):
    """
    Send a plain-text e-mail.

    Returns True if the message was accepted by the mail server, False if it
    was not. This never raises: the caller decides what to tell the user.
    """
    if not mail_is_configured():
        logger.error(
            "Not sending e-mail to %s: MAIL_USERNAME/MAIL_PASSWORD are not set.",
            recipient
        )
        return False

    message = Message(
        subject=subject,
        recipients=[recipient],
        body=message_text,
        sender=app.config["MAIL_DEFAULT_SENDER"]
    )

    # Flask-Mail opens its SMTP socket with no timeout, so an unreachable mail
    # server hangs the worker until gunicorn kills it at 30s. Cap it well below
    # that, and put the global default back afterwards so nothing else is
    # affected.
    previous_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(15)
    try:
        mail.send(message)
    except Exception:
        logger.exception("Failed to send e-mail to %s", recipient)
        return False
    finally:
        socket.setdefaulttimeout(previous_timeout)


    logger.info("Sent e-mail to %s (subject: %s)", recipient, subject)
    return True
