import pytest

from apps.accounts.models import User
from apps.listings.models import Category, Listing, ListingKind
from apps.schools.models import School


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("kind", "shown", "hidden"),
    [
        (ListingKind.ITEM, "item_details", "service_details"),
        (ListingKind.SERVICE, "service_details", "item_details"),
    ],
)
def test_listing_admin_shows_only_matching_details(client, kind, shown, hidden):
    umd = School.objects.get(slug="umd")
    admin = User.objects.create_superuser("admin@umd.edu", "pw-123456789", school=umd)
    category = Category.objects.create(name=str(kind), slug=str(kind), kind=kind)
    listing = Listing.objects.create(
        school=umd, seller=admin, kind=kind, category=category, title="x", price_cents=100
    )
    client.force_login(admin)
    html = client.get(f"/admin/listings/listing/{listing.pk}/change/").content.decode()
    assert f'id="{shown}-group"' in html
    assert f'id="{hidden}-group"' not in html
