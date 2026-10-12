import pytest
from django.core.exceptions import ValidationError

from apps.schools.models import MarketplaceStatus, MeetingSpot, School


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


@pytest.mark.django_db
def test_school_meeting_spots_returns_only_active_locations(client):
    umd = School.objects.get(slug="umd")
    MeetingSpot.objects.create(
        school=umd, name="Library entrance", directions="Meet beside the main doors."
    )
    MeetingSpot.objects.create(
        school=umd, name="Retired spot", directions="Old location.", is_active=False
    )

    response = client.get("/api/schools/umd/meeting-spots/")

    assert response.status_code == 200
    names = [spot["name"] for spot in response.json()]
    assert "Library entrance" in names
    assert "Retired spot" not in names
