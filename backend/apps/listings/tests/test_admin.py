import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.accounts.models import User
from apps.listings import services
from apps.listings.models import Category, ItemDetails, Listing
from apps.schools.models import School

CHANGE_URL = "/admin/listings/listing/{}/change/"
ADD_URL = "/admin/listings/listing/add/"


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def listing():
    seller = User.objects.create_user(
        "seller@umd.edu", "pw-123456789", username="seller", school=School.objects.get(slug="umd")
    )
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buffer, "JPEG")
    return services.create_item_listing(
        seller,
        category=Category.objects.get(slug="clothing"),
        title="Gray winter jacket",
        description="Worn one season.",
        price_cents=2500,
        condition="like_new",
        size="M",
        photos=[SimpleUploadedFile("a.jpg", buffer.getvalue())],
    )


@pytest.fixture
def admin_client(client):
    admin = User.objects.create_superuser("admin@example.com", "pw-123456789", username="admin")
    client.force_login(admin)
    return client


def change_form(listing, **overrides):
    """What the change page posts for a listing with one photo."""
    details = listing.item_details
    data = {
        "title": listing.title,
        "description": listing.description,
        "photos-TOTAL_FORMS": "1",
        "photos-INITIAL_FORMS": "1",
        "photos-0-id": listing.photos.get().pk,
        "photos-0-listing": listing.pk,
        "item_details-TOTAL_FORMS": "1",
        "item_details-INITIAL_FORMS": "1",
        "item_details-0-id": details.pk,
        "item_details-0-listing": listing.pk,
        "item_details-0-condition": details.condition,
        "item_details-0-size": details.size,
        "item_details-0-brand": details.brand,
        "item_details-0-color": details.color,
    }
    return data | overrides


@pytest.mark.django_db
def test_change_page_shows_the_listing(admin_client, listing):
    response = admin_client.get(CHANGE_URL.format(listing.pk))
    assert response.status_code == 200
    assert b"Gray winter jacket" in response.content


@pytest.mark.django_db
def test_admin_edits_wording_but_not_price_category_photos_or_details_row(admin_client, listing):
    photo = listing.photos.get()
    response = admin_client.post(
        CHANGE_URL.format(listing.pk),
        change_form(
            listing,
            title="Gray jacket",
            price_cents="0",
            category=Category.objects.get(slug="free").pk,
            **{
                "photos-0-position": "3",
                "photos-0-DELETE": "on",
                "item_details-0-DELETE": "on",
            },
        ),
    )
    assert response.status_code == 302, response.context["errors"]
    listing.refresh_from_db()
    assert listing.title == "Gray jacket"
    assert listing.price_cents == 2500
    assert listing.category.slug == "clothing"
    assert listing.photos.get() == photo
    assert listing.photos.get().position == 0
    assert ItemDetails.objects.filter(listing=listing).exists()


@pytest.mark.django_db
def test_admin_save_does_not_undo_a_status_change(admin_client, listing):
    """The form was loaded while the listing was Available; Deals moved it to Pending before
    the admin saved."""
    services.mark_pending(listing)
    response = admin_client.post(CHANGE_URL.format(listing.pk), change_form(listing))
    assert response.status_code == 302
    listing.refresh_from_db()
    assert listing.status == Listing.Status.PENDING


@pytest.mark.django_db
def test_admin_cannot_add_listings(admin_client):
    assert admin_client.get(ADD_URL).status_code == 403
