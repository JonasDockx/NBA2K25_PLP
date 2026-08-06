"""
This is the init file thatsets up Flask and the database.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail

from app.config import Config

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)

app = Flask(__name__, static_url_path="/static", static_folder="../static")
app.config.from_object(Config)
mail = Mail(app)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"

# Say loudly in the log whether outgoing e-mail is usable. We deliberately do
# NOT refuse to start: supervisor has autorestart=true, so exiting here would
# crash-loop the site off the internet over a mail problem.
if app.config["MAIL_USERNAME"] and app.config["MAIL_PASSWORD"]:
    app.logger.info(
        "Outgoing e-mail enabled, sending as %s", app.config["MAIL_USERNAME"]
    )
else:
    app.logger.error(
        "MAIL_USERNAME/MAIL_PASSWORD are not set - outgoing e-mail is DISABLED. "
        "Password reset links will NOT be delivered."
    )


@login_manager.user_loader
def load_user(user_id):
    """Loading the user to get the user id."""
    return User.query.get(int(user_id))

from app import routes
from app.models import User
from flask_migrate import Migrate
from app import app, db

migrate = Migrate(app, db)

# Define the custom getattr filter
@app.template_filter("getattr")
def getattr_filter(obj, attr):
    """
    Defining the custom getattr filter.
    """
    return getattr(obj, attr, None)

from app.errors.handlers import errors
app.register_blueprint(errors)