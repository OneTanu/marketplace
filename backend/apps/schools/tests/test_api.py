import pytest

from apps.schools.models import MarketplaceStatus, School


@pytest.mark.django_db
def test_school_directory_is_public(client):
    response = client.get("/api/schools/")

    assert response.status_code == 200
    umd = response.json()[0]
    assert umd["slug"] == "umd"
    assert umd["marketplace_status"] == MarketplaceStatus.OPEN
    assert umd["signup_is_open"] is True
    assert umd["domains"] == ["terpmail.umd.edu", "umd.edu"]


@pytest.mark.django_db
def test_school_detail_uses_slug(client):
    response = client.get("/api/schools/umd/")

    assert response.status_code == 200
    assert response.json()["name"] == "University of Maryland"


@pytest.mark.django_db
def test_directory_exposes_marketplace_lifecycle(client):
    School.objects.create(
        name="Towson University",
        short_name="Towson",
        slug="towson",
        marketplace_status=MarketplaceStatus.WAITLIST,
        sort_order=10,
    )

    response = client.get("/api/schools/")

    assert response.status_code == 200
    assert [school["marketplace_status"] for school in response.json()] == [
        MarketplaceStatus.OPEN,
        MarketplaceStatus.WAITLIST,
    ]
