import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.listings.models import Category, ItemDetails, Listing, ListingKind
from apps.schools.models import School


@pytest.fixture
def umd():
    return School.objects.get(slug="umd")


@pytest.fixture
def seller(umd):
    return User.objects.create_user("seller@umd.edu", "pw-123456789", username="seller", school=umd)


@pytest.fixture
def clothing():
    return Category.objects.get(slug="clothing")  # seeded by a data migration


def make_listing(**overrides):
    fields = {"title": "Gray jeans", "price_cents": 2500} | overrides
    return Listing(**fields)


@pytest.mark.django_db
def test_item_listing_with_details(umd, seller, clothing):
    listing = make_listing(school=umd, seller=seller, category=clothing)
    listing.full_clean()
    listing.save()
    ItemDetails.objects.create(listing=listing, condition="good", color="gray", size="32")
    listing.refresh_from_db()
    assert listing.status == Listing.Status.AVAILABLE
    assert listing.kind == ListingKind.ITEM
    assert listing.item_details.color == "gray"


@pytest.mark.django_db
def test_category_must_match_kind(umd, seller):
    tutoring = Category.objects.create(name="Tutoring", slug="tutoring", kind=ListingKind.SERVICE)
    listing = make_listing(school=umd, seller=seller, category=tutoring)
    with pytest.raises(ValidationError, match="kind"):
        listing.full_clean()


@pytest.mark.django_db
def test_listing_school_must_be_sellers_school(seller, clothing):
    gw = School.objects.create(name="George Washington University", short_name="GW", slug="gw")
    listing = make_listing(school=gw, seller=seller, category=clothing)
    with pytest.raises(ValidationError, match="seller's school"):
        listing.full_clean()
