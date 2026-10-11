"""The fields behind the student ID card on profiles: last initial, join date, and sold count."""

import pytest

from apps.listings.models import Category, Listing

from .test_social import verified_user


def listing(seller, status):
    return Listing.objects.create(
        school=seller.school,
        seller=seller,
        category=Category.objects.get(slug="women-coats-jackets"),
        title="Jacket",
        price_cents=2500,
        status=status,
    )


@pytest.mark.django_db
def test_public_profile_has_last_initial_join_date_and_sold_count(client):
    viewer = verified_user("viewer", "Viewer")
    maya = verified_user("maya", "Maya")
    listing(maya, Listing.Status.SOLD)
    listing(maya, Listing.Status.SOLD)
    listing(maya, Listing.Status.PENDING)
    listing(maya, Listing.Status.AVAILABLE)
    listing(viewer, Listing.Status.SOLD)
    client.force_login(viewer)

    body = client.get("/api/users/maya/").json()

    assert body["last_initial"] == "P"  # verified_user's last name is "Private"
    assert "last_name" not in body
    assert body["date_joined"].startswith(str(maya.date_joined.year))
    assert body["sold_count"] == 2
    assert body["school"]["colors"] == ["#E21833", "#FFD200", "#000000"]


@pytest.mark.django_db
def test_public_profile_sold_count_is_zero_without_sales(client):
    viewer = verified_user("viewer", "Viewer")
    verified_user("maya", "Maya")
    client.force_login(viewer)

    assert client.get("/api/users/maya/").json()["sold_count"] == 0


@pytest.mark.django_db
def test_current_user_has_join_date_and_sold_count(client):
    maya = verified_user("maya", "Maya")
    listing(maya, Listing.Status.SOLD)
    listing(maya, Listing.Status.AVAILABLE)
    client.force_login(maya)

    body = client.get("/api/me/").json()

    assert body["sold_count"] == 1
    assert body["date_joined"].startswith(str(maya.date_joined.year))
