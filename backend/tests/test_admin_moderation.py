import pytest
from django.contrib import admin

from apps.accounts.models import User
from apps.listings import services
from apps.listings.models import Category, Listing
from apps.schools.models import School


@pytest.mark.django_db
def test_listing_status_is_read_only_and_moderation_action_removes(client):
    umd = School.objects.get(slug="umd")
    admin = User.objects.create_superuser(
        "admin@umd.edu", "pw-123456789", username="admin", school=umd
    )
    clothing = Category.objects.get(slug="clothing")  # seeded
    available, sold = (
        Listing.objects.create(
            school=umd,
            seller=admin,
            category=clothing,
            title=title,
            price_cents=100,
            status=status,
        )
        for title, status in [("Lamp", "available"), ("Desk", "sold")]
    )
    client.force_login(admin)

    html = client.get(f"/admin/listings/listing/{available.pk}/change/").content.decode()
    assert 'name="status"' not in html
    assert 'name="removed_by"' not in html

    response = client.post(
        "/admin/listings/listing/",
        {"action": "remove_by_moderation", "_selected_action": [available.pk, sold.pk]},
    )
    assert response.status_code == 302
    for listing in (available, sold):
        listing.refresh_from_db()
        assert listing.status == Listing.Status.REMOVED
        assert listing.removed_by == Listing.RemovedBy.MODERATION
        assert listing.removed_at is not None


@pytest.mark.django_db
def test_admin_save_does_not_overwrite_status_moved_meanwhile():
    """An admin edit loaded before Deals moved the listing must not write the old status back."""
    umd = School.objects.get(slug="umd")
    seller = User.objects.create_user(
        "seller@umd.edu", "pw-123456789", username="seller", school=umd
    )
    clothing = Category.objects.get(slug="clothing")  # seeded
    listing = Listing.objects.create(
        school=umd, seller=seller, category=clothing, title="Lamp", price_cents=100
    )
    stale = Listing.objects.get(pk=listing.pk)
    services.mark_pending(listing)

    stale.title = "Desk lamp"
    admin.site._registry[Listing].save_model(request=None, obj=stale, form=None, change=True)

    listing.refresh_from_db()
    assert listing.title == "Desk lamp"
    assert listing.status == Listing.Status.PENDING


@pytest.mark.django_db
def test_listings_cannot_be_hard_deleted_from_admin(client):
    umd = School.objects.get(slug="umd")
    admin_user = User.objects.create_superuser(
        "admin@umd.edu", "pw-123456789", username="admin", school=umd
    )
    clothing = Category.objects.get(slug="clothing")  # seeded
    listing = Listing.objects.create(
        school=umd, seller=admin_user, category=clothing, title="Lamp", price_cents=100
    )
    client.force_login(admin_user)

    assert client.get(f"/admin/listings/listing/{listing.pk}/delete/").status_code == 403
    changelist = client.get("/admin/listings/listing/").content.decode()
    assert 'value="delete_selected"' not in changelist
    assert Listing.objects.filter(pk=listing.pk).exists()
