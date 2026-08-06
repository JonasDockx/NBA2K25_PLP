"""
Tokens used in the e-mail flows.

See CONTEXT.md for the difference between a Confirmation Token and a Reset
Token. They currently share a salt and a lifetime, which means one can be
used in place of the other; splitting them properly is tracked in
.scratch/email-delivery/issues/02-harden-password-reset-flow.md
"""

from itsdangerous import URLSafeTimedSerializer

from app import app

def generate_confirmation_token(email):
    """
    Generating a confirmation token.
    """
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    return serializer.dumps(email, salt=app.config["SECURITY_PASSWORD_SALT"])

def confirm_token(token, expiration=3600):
    """
    Confirming the token.

    Returns the e-mail address the token was made for, or False if the token
    is invalid or has expired. Note that it returns False rather than raising.
    """
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    try:
        email = serializer.loads(
            token,
            salt=app.config["SECURITY_PASSWORD_SALT"],
            max_age=expiration
        )
    except Exception:
        return False
    return email
