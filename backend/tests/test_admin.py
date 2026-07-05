import pytest

from apps.accounts.models import User

ADMIN_PAGES = [
    "/admin/schools/school/",
    "/admin/schools/school/add/",
    "/admin/listings/listing/",
    "/admin/listings/listing/add/",
    "/admin/listings/category/",
    "/admin/accounts/user/",
]


@pytest.mark.django_db
@pytest.mark.parametrize("url", ADMIN_PAGES)
def test_admin_pages_render(client, url):
    admin = User.objects.create_superuser("admin@umd.edu", "pw-123456789")
    client.force_login(admin)
    assert client.get(url).status_code == 200
