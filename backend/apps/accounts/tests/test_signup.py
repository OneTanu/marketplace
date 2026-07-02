import pytest
from django.core import mail
from django.db import IntegrityError

from apps.accounts.adapter import is_allowed_email
from apps.accounts.models import User

SIGNUP_URL = "/api/auth/browser/v1/auth/signup"
LOGIN_URL = "/api/auth/browser/v1/auth/login"
PASSWORD = "a-long-test-password-123"


@pytest.mark.parametrize(
    ("email", "allowed"),
    [
        ("terp@umd.edu", True),
        ("Terp@UMD.EDU", True),
        ("terp@terpmail.umd.edu", True),
        ("Terp@TerpMail.UMD.edu", True),
        ("terp@fake-terpmail.umd.edu", False),
        ("terp@gmail.com", False),
        ("terp@fakeumd.edu", False),
        ("terp@umd.edu.evil.com", False),
        ("terp@cs.umd.edu", False),
    ],
)
def test_is_allowed_email(email, allowed):
    assert is_allowed_email(email) is allowed


@pytest.mark.django_db
def test_signup_rejects_non_umd_email(client):
    response = client.post(
        SIGNUP_URL,
        {"email": "terp@gmail.com", "password": PASSWORD},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert not User.objects.exists()


@pytest.mark.django_db
def test_signup_with_umd_email_requires_verification(client):
    response = client.post(
        SIGNUP_URL,
        {"email": "terp@umd.edu", "password": PASSWORD},
        content_type="application/json",
    )
    # 401 + a pending "verify_email" flow: account created but not signed in yet.
    assert response.status_code == 401
    flows = response.json()["data"]["flows"]
    assert any(f["id"] == "verify_email" and f.get("is_pending") for f in flows)
    assert User.objects.filter(email="terp@umd.edu").exists()
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_unverified_user_cannot_log_in(client):
    client.post(
        SIGNUP_URL,
        {"email": "terp@umd.edu", "password": PASSWORD},
        content_type="application/json",
    )
    client.logout()
    response = client.post(
        LOGIN_URL,
        {"email": "terp@umd.edu", "password": PASSWORD},
        content_type="application/json",
    )
    assert response.status_code == 401
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_email_is_unique_regardless_of_case():
    User.objects.create_user("terp@umd.edu", PASSWORD)
    duplicate = User(email="Terp@UMD.edu")
    duplicate.set_password(PASSWORD)
    with pytest.raises(IntegrityError):
        duplicate.save()


@pytest.mark.django_db
def test_signup_with_terpmail_email_requires_verification(client):
    response = client.post(
        SIGNUP_URL,
        {"email": "terp@terpmail.umd.edu", "password": PASSWORD},
        content_type="application/json",
    )
    assert response.status_code == 401
    assert User.objects.filter(email="terp@terpmail.umd.edu").exists()
