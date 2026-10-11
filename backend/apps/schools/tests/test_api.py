import pytest
from django.core.exceptions import ValidationError

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
    assert umd["colors"] == ["#E21833", "#FFD200", "#000000"]


@pytest.mark.django_db
def test_school_colors_must_be_uppercase_hex():
    umd = School.objects.get(slug="umd")
    umd.colors = ["red"]

    with pytest.raises(ValidationError, match="hex color"):
        umd.full_clean()


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
