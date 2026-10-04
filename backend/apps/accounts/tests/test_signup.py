import pytest
from django.core import mail
from django.db import IntegrityError

from apps.accounts.models import User
from apps.schools.models import School

SIGNUP_URL = "/api/auth/browser/v1/auth/signup"
LOGIN_URL = "/api/auth/browser/v1/auth/login"
PASSWORD = "a-long-test-password-123"


def signup_data(email="terp@umd.edu", username="testterp", **overrides):
    return {
        "email": email,
        "username": username,
        "first_name": "Test",
        "last_name": "Student",
        "password": PASSWORD,
        **overrides,
    }


@pytest.mark.django_db
def test_signup_rejects_non_umd_email(client):
    response = client.post(
        SIGNUP_URL,
        signup_data(email="terp@gmail.com"),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert not User.objects.exists()


@pytest.mark.django_db
def test_signup_with_umd_email_requires_verification(client):
    response = client.post(
        SIGNUP_URL,
        signup_data(),
        content_type="application/json",
    )
    # 401 + a pending "verify_email" flow: account created but not signed in yet.
    assert response.status_code == 401
    flows = response.json()["data"]["flows"]
    assert any(f["id"] == "verify_email" and f.get("is_pending") for f in flows)
    user = User.objects.get(email="terp@umd.edu")
    assert user.school.slug == "umd"
    assert user.username == "testterp"
    assert user.first_name == "Test"
    assert user.last_name == "Student"
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_unverified_user_cannot_log_in(client):
    client.post(
        SIGNUP_URL,
        signup_data(),
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
    User.objects.create_user("terp@umd.edu", PASSWORD, username="testterp")
    duplicate = User(email="Terp@UMD.edu", username="anotherterp")
    duplicate.set_password(PASSWORD)
    with pytest.raises(IntegrityError):
        duplicate.save()


@pytest.mark.django_db
def test_signup_with_terpmail_email_requires_verification(client):
    response = client.post(
        SIGNUP_URL,
        signup_data(email="terp@terpmail.umd.edu"),
        content_type="application/json",
    )
    assert response.status_code == 401
    assert User.objects.get(email="terp@terpmail.umd.edu").school.slug == "umd"


@pytest.mark.django_db
def test_signup_rejected_when_school_signup_is_closed(client):
    School.objects.filter(slug="umd").update(signup_is_open=False)
    response = client.post(
        SIGNUP_URL,
        signup_data(),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert not User.objects.exists()


@pytest.mark.django_db
def test_signup_requires_identity_fields(client):
    response = client.post(
        SIGNUP_URL,
        {"email": "terp@umd.edu", "password": PASSWORD},
        content_type="application/json",
    )

    assert response.status_code == 400
    params = {error["param"] for error in response.json()["errors"]}
    assert {"username", "first_name", "last_name"} <= params


@pytest.mark.django_db
def test_username_is_unique_regardless_of_case(client):
    first = client.post(SIGNUP_URL, signup_data(), content_type="application/json")
    assert first.status_code == 401

    second = client.post(
        SIGNUP_URL,
        signup_data(email="other@umd.edu", username="TESTTERP"),
        content_type="application/json",
    )

    assert second.status_code == 400
    assert User.objects.count() == 1
