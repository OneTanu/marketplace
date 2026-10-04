import pytest

from apps.accounts.models import User
from apps.schools.models import School


@pytest.mark.django_db
def test_current_user_requires_authentication(client):
    assert client.get("/api/me/").status_code == 403


@pytest.mark.django_db
def test_current_user_includes_home_school(client):
    umd = School.objects.get(slug="umd")
    user = User.objects.create_user(
        "student@umd.edu", "pw-123456789", username="student", school=umd
    )
    client.force_login(user)

    response = client.get("/api/me/")

    assert response.status_code == 200
    assert response.json()["email"] == "student@umd.edu"
    assert response.json()["username"] == "student"
    assert response.json()["school"]["slug"] == "umd"


@pytest.mark.django_db
def test_profile_normalizes_instagram_handle(client):
    user = User.objects.create_user("student@umd.edu", "pw-123456789", username="student")
    client.force_login(user)

    response = client.patch(
        "/api/me/",
        {"instagram_handle": "https://www.instagram.com/Test.Student/"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["instagram_handle"] == "test.student"
    user.refresh_from_db()
    assert user.instagram_handle == "test.student"


@pytest.mark.django_db
def test_profile_rejects_duplicate_instagram_handle(client):
    User.objects.create_user(
        "first@umd.edu",
        "pw-123456789",
        username="firststudent",
        instagram_handle="same.handle",
    )
    user = User.objects.create_user("second@umd.edu", "pw-123456789", username="secondstudent")
    client.force_login(user)

    response = client.patch(
        "/api/me/",
        {"instagram_handle": "@SAME.HANDLE"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["instagram_handle"] == [
        "This Instagram handle is already connected to another Tanu account."
    ]


@pytest.mark.django_db
def test_profile_rejects_invalid_instagram_handle(client):
    user = User.objects.create_user("student@umd.edu", "pw-123456789", username="student")
    client.force_login(user)

    response = client.patch(
        "/api/me/",
        {"instagram_handle": "not a handle"},
        content_type="application/json",
    )

    assert response.status_code == 400
