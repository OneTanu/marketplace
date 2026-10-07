import io
from pathlib import Path

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image

from apps.accounts.models import User
from apps.listings.models import Category, Listing, ListingKind, ListingPhoto
from apps.schools.models import School

CATEGORIES_URL = "/api/categories/"
LISTINGS_URL = "/api/listings/"
SEEDED_ITEM_CATEGORIES = {
    "Clothing",
    "Dorm & furniture",
    "Electronics",
    "Textbooks",
    "Free",
    "Other",
}


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.fixture
def umd():
    return School.objects.get(slug="umd")


@pytest.fixture
def gw():
    return School.objects.create(name="George Washington University", short_name="GW", slug="gw")


@pytest.fixture
def seller(umd):
    return User.objects.create_user("seller@umd.edu", "pw-123456789", username="seller", school=umd)


@pytest.fixture
def seller_client(client, seller):
    client.force_login(seller)
    return client


def category(slug):
    return Category.objects.get(slug=slug)


def image(name="photo.jpg", image_format="JPEG"):
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buffer, image_format)
    return SimpleUploadedFile(name, buffer.getvalue())


def listing_data(**overrides):
    data = {
        "category": category("clothing").pk,
        "title": "Gray winter jacket",
        "description": "Worn one season.",
        "price_cents": 2500,
        "condition": "like_new",
        "size": "M",
        "brand": "Patagonia",
        "color": "gray",
        "photos": [image()],
    }
    return data | overrides


def post_listing(client, **overrides):
    return client.post(LISTINGS_URL, listing_data(**overrides))


# --- Categories ---


@pytest.mark.django_db
def test_categories_returns_active_item_categories(seller_client):
    Category.objects.create(name="Retired", slug="retired", kind=ListingKind.ITEM, is_active=False)
    Category.objects.create(name="Tutoring", slug="tutoring", kind=ListingKind.SERVICE)
    response = seller_client.get(CATEGORIES_URL, {"kind": "item"})
    assert response.status_code == 200
    assert {c["name"] for c in response.json()} == SEEDED_ITEM_CATEGORIES
    assert set(response.json()[0]) == {"id", "name", "slug"}


@pytest.mark.django_db
def test_categories_rejects_unknown_kind(seller_client):
    response = seller_client.get(CATEGORIES_URL, {"kind": "tickets"})
    assert response.status_code == 400
    assert "kind" in response.json()


# --- Sign-in ---


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("method", "url"),
    [("get", CATEGORIES_URL), ("post", LISTINGS_URL), ("get", f"{LISTINGS_URL}1/")],
)
def test_endpoints_require_sign_in(client, method, url):
    response = getattr(client, method)(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_without_school_cannot_post(client):
    admin = User.objects.create_superuser("admin@example.com", "pw-123456789", username="admin")
    client.force_login(admin)
    response = post_listing(client)
    assert response.status_code == 403
    assert "school" in response.json()["detail"]
    assert not Listing.objects.exists()


# --- Creating ---


@pytest.mark.django_db
def test_create_listing_with_details_and_photos(seller_client, seller, umd, media_root):
    photos = [image("a.jpg", "JPEG"), image("b.png", "PNG"), image("c.webp", "WEBP")]
    response = post_listing(seller_client, photos=photos)

    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "item"
    assert body["status"] == "available"
    assert body["currency"] == "USD"
    assert body["title"] == "Gray winter jacket"
    assert body["description"] == "Worn one season."
    assert body["price_cents"] == 2500
    assert body["category"] == {
        "id": category("clothing").pk,
        "name": "Clothing",
        "slug": "clothing",
    }
    assert body["school"] == {"id": umd.pk, "short_name": "UMD"}
    assert body["seller"] == {"id": seller.pk}
    assert body["item_details"] == {
        "condition": "like_new",
        "size": "M",
        "brand": "Patagonia",
        "color": "gray",
    }
    assert [p["position"] for p in body["photos"]] == [0, 1, 2]
    # Photos keep the order they were sent in (the first is the cover), under random names
    # with the extension of their detected format.
    paths = [Path(p["image_url"]) for p in body["photos"]]
    assert [p.suffix for p in paths] == [".jpg", ".png", ".webp"]
    assert not {p.stem for p in paths} & {"a", "b", "c"}
    assert all(p["image_url"].startswith("/media/listings/") for p in body["photos"])
    for photo in ListingPhoto.objects.filter(listing_id=body["id"]):
        assert (media_root / photo.image.name).is_file()

    listing = Listing.objects.get(pk=body["id"])
    assert listing.seller == seller
    assert listing.item_details.condition == "like_new"


@pytest.mark.django_db
def test_multi_picture_jpeg_is_accepted(seller_client):
    """Phones save HDR and similar shots as JPEGs holding several pictures; Pillow calls
    that format MPO."""
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(
        buffer, "MPO", save_all=True, append_images=[Image.new("RGB", (8, 8), "blue")]
    )
    assert Image.open(io.BytesIO(buffer.getvalue())).format == "MPO"
    response = post_listing(
        seller_client, photos=[SimpleUploadedFile("hdr.jpg", buffer.getvalue())]
    )
    assert response.status_code == 201, response.json()
    assert response.json()["photos"][0]["image_url"].endswith(".jpg")


@pytest.mark.django_db
def test_uploaded_filename_does_not_choose_the_stored_name(seller_client):
    response = post_listing(seller_client, photos=[image("page.html", "PNG")])
    assert response.status_code == 201
    stored = Path(response.json()["photos"][0]["image_url"])
    assert stored.suffix == ".png"
    assert stored.stem != "page"


@pytest.mark.django_db
def test_description_line_breaks_are_normalized(seller_client):
    # 5,000 characters once browser CRLF line breaks become LF.
    response = post_listing(seller_client, description="a\r\n" * 2_500)
    assert response.status_code == 201, response.json()
    assert response.json()["description"] == ("a\n" * 2_500).strip()


@pytest.mark.django_db
def test_optional_details_can_be_omitted(seller_client):
    data = listing_data()
    for field in ("description", "size", "brand", "color"):
        del data[field]
    response = seller_client.post(LISTINGS_URL, data)
    assert response.status_code == 201
    assert response.json()["item_details"] == {
        "condition": "like_new",
        "size": "",
        "brand": "",
        "color": "",
    }


@pytest.mark.django_db
def test_server_sets_kind_school_currency_and_status(seller_client, umd, gw):
    response = post_listing(
        seller_client, kind="service", school=gw.pk, currency="EUR", status="sold"
    )
    assert response.status_code == 201
    listing = Listing.objects.get(pk=response.json()["id"])
    assert listing.kind == ListingKind.ITEM
    assert listing.school == umd
    assert listing.currency == "USD"
    assert listing.status == Listing.Status.AVAILABLE


@pytest.mark.django_db
def test_listing_belongs_to_the_sellers_school(client, gw):
    colonial = User.objects.create_user(
        "colonial@gwu.edu", "pw-123456789", username="colonial", school=gw
    )
    client.force_login(colonial)
    response = post_listing(client)
    assert response.status_code == 201
    assert response.json()["school"]["short_name"] == "GW"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("slug", "price_cents"),
    [("free", 0), ("clothing", 1), ("clothing", 1_000_000)],
)
def test_valid_prices(seller_client, slug, price_cents):
    response = post_listing(seller_client, category=category(slug).pk, price_cents=price_cents)
    assert response.status_code == 201, response.json()


# --- Validation ---


def oversized_photo():
    return SimpleUploadedFile("huge.jpg", b"\0" * (10 * 1024 * 1024 + 1))


def gif_photo():
    return image("anim.gif", "GIF")


def service_category():
    return Category.objects.create(name="Tutoring", slug="tutoring", kind=ListingKind.SERVICE).pk


def retired_category():
    return Category.objects.create(
        name="Retired", slug="retired", kind=ListingKind.ITEM, is_active=False
    ).pk


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"category": service_category}, "category"),
        ({"category": retired_category}, "category"),
        ({"category": 999_999}, "category"),
        ({"title": ""}, "title"),
        ({"title": "x" * 121}, "title"),
        ({"description": "x" * 5_001}, "description"),
        ({"price_cents": "24.99"}, "price_cents"),
        ({"price_cents": -1}, "price_cents"),
        ({"price_cents": 1_000_001}, "price_cents"),
        ({"price_cents": 0}, "price_cents"),  # $0 only in Free
        (
            {"category": lambda: category("free").pk, "price_cents": 500},
            "price_cents",
        ),  # Free is $0
        ({"condition": ""}, "condition"),
        ({"condition": "mint"}, "condition"),
        ({"color": "teal"}, "color"),
        ({"photos": []}, "photos"),
        ({"photos": lambda: [image(f"{i}.jpg") for i in range(11)]}, "photos"),
        ({"photos": lambda: [image(), gif_photo()]}, "photos"),
        ({"photos": lambda: [SimpleUploadedFile("notes.jpg", b"not an image")]}, "photos"),
        ({"photos": lambda: [image(), oversized_photo()]}, "photos"),
    ],
)
def test_validation_errors_are_field_level(seller_client, overrides, field):
    resolved = {key: value() if callable(value) else value for key, value in overrides.items()}
    data = listing_data(**resolved)
    data = {key: value for key, value in data.items() if value != []}  # [] = field omitted
    response = seller_client.post(LISTINGS_URL, data)
    assert response.status_code == 400
    assert field in response.json(), response.json()
    assert not Listing.objects.exists()
    assert not ListingPhoto.objects.exists()


@pytest.mark.django_db
def test_missing_condition_is_a_field_error(seller_client):
    data = listing_data()
    del data["condition"]
    response = seller_client.post(LISTINGS_URL, data)
    assert response.status_code == 400
    assert "condition" in response.json()


# --- Reading ---


@pytest.mark.django_db
def test_any_signed_in_student_can_fetch_a_listing(seller_client, gw):
    listing_id = post_listing(seller_client).json()["id"]
    other_client = Client()
    other_client.force_login(
        User.objects.create_user("colonial@gwu.edu", "pw-1234567", username="colonial", school=gw)
    )
    response = other_client.get(f"{LISTINGS_URL}{listing_id}/")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == listing_id
    assert body["school"]["short_name"] == "UMD"
    assert body["item_details"]["condition"] == "like_new"
    assert [set(p) for p in body["photos"]] == [{"id", "position", "image_url"}]


@pytest.mark.django_db
def test_fetching_a_missing_listing_is_404(seller_client):
    assert seller_client.get(f"{LISTINGS_URL}999999/").status_code == 404


# --- CSRF through the web app proxy ---


@pytest.mark.django_db
def test_multipart_post_from_web_app_origin_needs_and_passes_csrf(seller):
    """Browser uploads arrive through the Next.js proxy with the web app's Origin."""
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(seller)
    csrf_client.get("/api/auth/browser/v1/config")
    token = csrf_client.cookies["csrftoken"].value
    origin = {"Origin": settings.WEB_APP_URL}

    assert csrf_client.post(LISTINGS_URL, listing_data(), headers=origin).status_code == 403
    response = csrf_client.post(
        LISTINGS_URL, listing_data(), headers=origin | {"X-CSRFToken": token}
    )
    assert response.status_code == 201
