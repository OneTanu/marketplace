import re

import pytest
from allauth.account.models import EmailAddress
from django.core import mail
from django.core.cache import cache
from django.test import Client

from apps.accounts.models import User
from apps.accounts.services import set_account_active
from apps.schools.models import School
from apps.trust.models import BannedEmail

AUTH = "/api/auth/browser/v1"
REQUEST_URL = f"{AUTH}/auth/password/request"
RESET_URL = f"{AUTH}/auth/password/reset"
LOGIN_URL = f"{AUTH}/auth/login"
SESSION_URL = f"{AUTH}/auth/session"
KEY_STATUS_URL = "/api/password-reset/key-status/"
PASSWORD = "the-old-password-123"
NEW_PASSWORD = "a-brand-new-password-456"
RESET_LINK = re.compile(r"http://localhost:3000/account/password/reset/(\S+)")


@pytest.fixture(autouse=True)
def fresh_rate_limits():
    # allauth counts reset requests per email in the cache, which outlives each test.
    cache.clear()


def verified_user(email="terp@umd.edu"):
    user = User.objects.create_user(
        email, PASSWORD, username=email.split("@")[0], school=School.objects.get(slug="umd")
    )
    EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
    return user


def request_reset(client, email):
    return client.post(REQUEST_URL, {"email": email}, content_type="application/json")


def reset_key(email="terp@umd.edu"):
    """Request a reset and return the key from the emailed link."""
    request_reset(Client(), email)
    keys = [m for message in mail.outbox if (m := RESET_LINK.search(message.body))]
    assert len(keys) == 1, [message.body for message in mail.outbox]
    return keys[0].group(1)


def reset(client, key, password=NEW_PASSWORD):
    return client.post(
        RESET_URL, {"key": key, "password": password}, content_type="application/json"
    )


def log_in(client, password):
    return client.post(
        LOGIN_URL, {"email": "terp@umd.edu", "password": password}, content_type="application/json"
    )


def key_status(client, key):
    return client.post(KEY_STATUS_URL, {"key": key}, content_type="application/json")


# --- Requesting a link ---


@pytest.mark.django_db
def test_requesting_a_reset_emails_a_link_to_the_web_app(client):
    verified_user()

    response = request_reset(client, "terp@umd.edu")

    assert response.status_code == 200
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["terp@umd.edu"]
    assert RESET_LINK.search(mail.outbox[0].body)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "email",
    ["nobody@umd.edu", "someone@gmail.com", "banned@umd.edu"],
    ids=["unknown-account", "non-school-domain", "banned-account"],
)
def test_reset_requests_answer_the_same_way_whether_or_not_an_account_exists(client, email):
    verified_user()
    banned = verified_user("banned@umd.edu")
    set_account_active(banned, False)
    BannedEmail.objects.create(school=banned.school, local_part="banned", email=banned.email)
    known = request_reset(Client(), "terp@umd.edu")
    mail.outbox.clear()

    response = request_reset(client, email)

    assert response.status_code == known.status_code == 200
    assert response.json() == known.json()
    # No usable link goes out for an address without an active account.
    assert not any(RESET_LINK.search(message.body) for message in mail.outbox)


# --- Using the link ---


@pytest.mark.django_db
def test_a_valid_key_resets_the_password(client):
    user = verified_user()
    key = reset_key()

    lookup = client.get(RESET_URL, HTTP_X_PASSWORD_RESET_KEY=key)
    assert lookup.status_code == 200
    assert lookup.json()["data"]["user"]["email"] == "terp@umd.edu"
    assert key_status(client, key).json() == {"status": "valid"}

    response = reset(client, key)

    # 401: the password changed, but allauth doesn't sign the student in
    # (ACCOUNT_LOGIN_ON_PASSWORD_RESET is off), so they log in with the new password.
    assert response.status_code == 401
    assert response.json()["meta"]["is_authenticated"] is False
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
    assert log_in(Client(), PASSWORD).status_code == 400
    assert log_in(Client(), NEW_PASSWORD).status_code == 200


@pytest.mark.django_db
def test_a_weak_password_is_refused_and_the_key_still_works(client):
    user = verified_user()
    key = reset_key()

    response = reset(client, key, password="password")

    assert response.status_code == 400
    assert {error["param"] for error in response.json()["errors"]} == {"password"}
    user.refresh_from_db()
    assert user.check_password(PASSWORD)
    assert reset(client, key).status_code == 401


@pytest.mark.django_db
def test_a_used_key_is_refused_and_explained(client):
    verified_user()
    key = reset_key()
    assert reset(client, key).status_code == 401

    again = reset(client, key, password="yet-another-password-789")

    assert again.status_code == 400
    assert again.json()["errors"][0]["code"] == "invalid_password_reset"
    assert client.get(RESET_URL, HTTP_X_PASSWORD_RESET_KEY=key).status_code == 400
    assert key_status(client, key).json() == {"status": "used"}


@pytest.mark.django_db
def test_an_expired_key_is_refused_and_explained(client, settings):
    verified_user()
    key = reset_key()
    # Every key is older than a negative timeout.
    settings.PASSWORD_RESET_TIMEOUT = -1

    assert client.get(RESET_URL, HTTP_X_PASSWORD_RESET_KEY=key).status_code == 400
    assert reset(client, key).status_code == 400
    assert key_status(client, key).json() == {"status": "expired"}


@pytest.mark.django_db
@pytest.mark.parametrize("key", ["", "nonsense", "1-not!base36-abc", "zz-"])
def test_a_malformed_key_is_invalid(client, key):
    assert client.get(RESET_URL, HTTP_X_PASSWORD_RESET_KEY=key).status_code == 400
    if key:
        assert key_status(client, key).json() == {"status": "invalid"}


@pytest.mark.django_db
def test_key_status_does_not_reveal_whether_a_user_exists(client):
    user = verified_user()
    key = reset_key()
    _, rest = key.split("-", 1)

    # A fresh key for a user id that doesn't exist reads like any other rejected key.
    assert key_status(client, f"zzzzzz-{rest}").json() == {"status": "used"}
    user.delete()
    assert key_status(client, key).json() == {"status": "used"}


@pytest.mark.django_db
def test_key_status_rejects_a_missing_key(client):
    assert key_status(client, "").status_code == 400


# --- Sessions ---


@pytest.mark.django_db
def test_resetting_the_password_signs_out_every_existing_session():
    """Django stores a hash of the password in each session and drops sessions whose hash no
    longer matches, so a reset signs the student out everywhere, including any browser an
    attacker was using."""
    verified_user()
    laptop, phone = Client(), Client()
    assert log_in(laptop, PASSWORD).status_code == 200
    assert log_in(phone, PASSWORD).status_code == 200
    assert laptop.get("/api/me/").status_code == 200
    key = reset_key()

    assert reset(Client(), key).status_code == 401

    for device in (laptop, phone):
        assert device.get("/api/me/").status_code == 403
        assert device.get(SESSION_URL).status_code == 401


@pytest.mark.django_db
def test_resetting_from_a_signed_in_browser_signs_it_out_too(client):
    verified_user()
    assert log_in(client, PASSWORD).status_code == 200
    key = reset_key()

    assert reset(client, key).status_code == 401
    assert client.get(SESSION_URL).status_code == 401
