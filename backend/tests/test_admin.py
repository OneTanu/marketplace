import pytest

from apps.accounts.models import User

ADMIN_PAGES = [
    "/admin/schools/school/",
    "/admin/schools/school/add/",
    "/admin/listings/listing/",
    "/admin/listings/category/",
    "/admin/accounts/user/",
]


@pytest.mark.django_db
@pytest.mark.parametrize("url", ADMIN_PAGES)
def test_admin_pages_render(client, url):
    admin = User.objects.create_superuser("admin@umd.edu", "pw-123456789", username="admin")
    client.force_login(admin)
    assert client.get(url).status_code == 200


@pytest.mark.django_db
def test_admin_user_form_shows_an_error_for_a_bad_instagram_handle(client):
    # Regression: the handle was only checked in User.save(), so a bad one was a 500.
    admin = User.objects.create_superuser("admin@umd.edu", "pw-123456789", username="admin")
    student = User.objects.create_user("student@umd.edu", "pw-123456789", username="student")
    client.force_login(admin)

    response = client.post(
        f"/admin/accounts/user/{student.pk}/change/",
        {
            "email": student.email,
            "username": student.username,
            "instagram_handle": "foo!",
            "is_active": "on",
            "date_joined_0": "2026-10-01",
            "date_joined_1": "12:00:00",
        },
    )

    assert response.status_code == 200
    assert "instagram_handle" in response.context["adminform"].form.errors
    student.refresh_from_db()
    assert student.instagram_handle == ""
