"""
Shared pytest fixtures: a Flask test client backed by a throwaway in-memory
database.
"""

import os

import pytest

# This MUST happen before importing the app. app/config.py is read at import
# time and Flask-SQLAlchemy builds its database connection immediately, so
# setting it any later would leave these tests running against - and then
# deleting - the real nba2k25.db.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app import app as flask_app, db
from app.models import User

# db.drop_all() in the teardown below deletes every table it can reach, so
# refuse to start unless we are certainly pointed at a throwaway database.
# Without this, any mismatch between the name above and the one read in
# app/config.py silently sends the tests at the real nba2k25.db.
_uri = flask_app.config["SQLALCHEMY_DATABASE_URI"]
if ":memory:" not in _uri:
    raise RuntimeError(
        f"Tests must run against an in-memory database, but the app is "
        f"pointed at {_uri!r}. Refusing to run."
    )

@pytest.fixture
def test_app():
    """
    The Flask app, pointed at a fresh empty database for one single test.
    """
    flask_app.config.update(
        TESTING=True,
        MAIL_USERNAME="test@example.com",
        MAIL_PASSWORD="test-password",
        MAIL_DEFAULT_SENDER="test@example.com",
    )

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(test_app):
    """A fake browser that can make requests without running a real server."""
    return test_app.test_client()


@pytest.fixture
def existing_user(test_app):
    """An already-registered user, for the 'this account exists' cases."""
    user = User(
        username="tester",
        email="tester@example.com",
        password="not-a-real-hash",
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()
    return user
