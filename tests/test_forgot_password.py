"""
The forgot-password flow must never tell a user an e-mail was sent when it
was not, and must not reveal which addresses are registered.
"""

from unittest.mock import patch

SENT_MESSAGE = b"If an account exists for that e-mail address"
FAILURE_MESSAGE = b"Please try again in a few minutes"


def post_forgot_password(client, email):
    return client.post(
        "/forgot_password",
        data={"email": email},
        follow_redirects=True,
    )


def test_sends_a_reset_link_to_a_known_address(client, existing_user):
    with patch("app.routes.send_email", return_value=True) as send:
        response = post_forgot_password(client, "tester@example.com")

    assert response.status_code == 200
    assert SENT_MESSAGE in response.data

    send.assert_called_once()
    recipient, subject, body = send.call_args.args
    assert recipient == "tester@example.com"
    assert "/reset_password/" in body


def test_tells_the_truth_when_sending_fails(client, existing_user):
    """The bug that started all this: never claim success on a failed send."""
    with patch("app.routes.send_email", return_value=False):
        response = post_forgot_password(client, "tester@example.com")

    assert FAILURE_MESSAGE in response.data
    assert SENT_MESSAGE not in response.data


def test_an_unknown_address_looks_identical_to_success(client):
    """Otherwise the form reveals which e-mail addresses have accounts."""
    with patch("app.routes.send_email", return_value=True) as send:
        response = post_forgot_password(client, "nobody@example.com")

    assert SENT_MESSAGE in response.data
    send.assert_not_called()
