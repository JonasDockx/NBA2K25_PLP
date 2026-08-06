"""
This is the config file containing all necessary information.
"""

from datetime import timedelta
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """
    This is the config class.
    """
    SECRET_KEY = os.environ.get('SECRET_KEY')
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT')
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///nba2k25.db")

    # Login (Project B) environment variables
    LOGIN_CLIENT_ID = os.environ.get('LOGIN_CLIENT_ID')
    LOGIN_CLIENT_SECRET = os.environ.get('LOGIN_CLIENT_SECRET')
    LOGIN_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
    LOGIN_REDIRECT_URI = os.environ.get('LOGIN_REDIRECT_URI')

    # Flask-Mail configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')  # Address we send from
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')  # Google App Password, no spaces
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_USERNAME')
    MAIL_DEFAULT_RECIPIENT = os.environ.get("MAIL_DEFAULT_RECIPIENT")
