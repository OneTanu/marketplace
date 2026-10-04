import pytest

from apps.accounts.models import User
from apps.schools.models import School


@pytest.mark.django_db
def test_current_user_requires_authentication(client):
    assert client.get("/api/me/").status_code == 403


@pytest.mark.django_db
def test_current_user_includes_home_school(client):
    umd = School.objects.get(slug="umd")
    user = User.objects.create_user("student@umd.edu", "pw-123456789", school=umd)
    client.force_login(user)

    response = client.get("/api/me/")

    assert response.status_code == 200
    assert response.json()["email"] == "student@umd.edu"
    assert response.json()["school"]["slug"] == "umd"
