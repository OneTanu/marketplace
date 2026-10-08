import io
from pathlib import Path

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import ExifTags, Image, ImageCms

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


# --- Photo cleaning ---


def encode(picture, image_format, **options):
    buffer = io.BytesIO()
    picture.save(buffer, image_format, **options)
    return buffer.getvalue()


def stored_photo(media_root, response, index=0):
    """The stored file's bytes and the decoded image, for one photo in a create response."""
    photo = ListingPhoto.objects.get(pk=response.json()["photos"][index]["id"])
    data = (media_root / photo.image.name).read_bytes()
    return data, Image.open(io.BytesIO(data))


@pytest.mark.django_db
def test_photo_is_rotated_upright_and_stored_without_metadata(seller_client, media_root):
    """A phone photo held upright is saved sideways with Orientation=6 ("rotate 90 degrees
    clockwise to display"), and carries the GPS position where it was taken."""
    picture = Image.new("RGB", (400, 200), "blue")
    picture.paste(Image.new("RGB", (200, 200), "red"))  # left half red
    exif = Image.Exif()
    exif[ExifTags.Base.Orientation] = 6
    exif[ExifTags.Base.Make] = "Phone"
    exif[ExifTags.IFD.GPSInfo] = {
        ExifTags.GPS.GPSLatitudeRef: "N",
        ExifTags.GPS.GPSLatitude: (38.0, 59.0, 10.0),
        ExifTags.GPS.GPSLongitudeRef: "W",
        ExifTags.GPS.GPSLongitude: (76.0, 56.0, 30.0),
    }
    icc_profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    upload = encode(
        picture,
        "JPEG",
        exif=exif.tobytes(),
        xmp=b"<x:xmpmeta xmlns:x='adobe:ns:meta/'>secret</x:xmpmeta>",
        comment="Taken at 123 Main St",
        icc_profile=icc_profile,
    )
    assert Image.open(io.BytesIO(upload)).getexif().get_ifd(ExifTags.IFD.GPSInfo)

    response = post_listing(seller_client, photos=[SimpleUploadedFile("p.jpg", upload)])

    assert response.status_code == 201, response.json()
    data, stored = stored_photo(media_root, response)
    assert stored.format == "JPEG"
    assert not stored.getexif()
    assert not {"exif", "xmp", "comment"} & set(stored.info)
    assert b"Exif" not in data
    assert b"secret" not in data
    assert b"Main St" not in data
    assert stored.info["icc_profile"] == icc_profile  # colour profile isn't location data
    # Upright: the 400x200 landscape becomes 200x400, the left (red) half now on top.
    assert stored.size == (200, 400)
    red, _, blue = stored.convert("RGB").getpixel((100, 50))
    assert red > 200 and blue < 50
    red, _, blue = stored.convert("RGB").getpixel((100, 350))
    assert red < 50 and blue > 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("image_format", "size", "stored_size"),
    [
        ("JPEG", (4000, 3000), (2048, 1536)),
        ("PNG", (1000, 4000), (512, 2048)),
        ("WEBP", (4096, 4096), (2048, 2048)),
        ("JPEG", (300, 200), (300, 200)),  # smaller photos aren't upscaled
        ("PNG", (2048, 100), (2048, 100)),
    ],
)
def test_photo_long_edge_is_capped(seller_client, media_root, image_format, size, stored_size):
    upload = encode(Image.new("RGB", size, "green"), image_format)
    response = post_listing(seller_client, photos=[SimpleUploadedFile("p", upload)])
    assert response.status_code == 201, response.json()
    _, stored = stored_photo(media_root, response)
    assert stored.size == stored_size


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("image_format", "mode", "stored_format", "extension"),
    [
        ("JPEG", "RGB", "JPEG", ".jpg"),
        ("JPEG", "L", "JPEG", ".jpg"),
        ("PNG", "RGBA", "PNG", ".png"),
        ("PNG", "P", "PNG", ".png"),
        ("WEBP", "RGB", "WEBP", ".webp"),
        ("WEBP", "RGBA", "WEBP", ".webp"),
    ],
)
def test_photo_keeps_its_format(
    seller_client, media_root, image_format, mode, stored_format, extension
):
    upload = encode(Image.new(mode, (64, 48)), image_format)
    response = post_listing(seller_client, photos=[SimpleUploadedFile("p", upload)])
    assert response.status_code == 201, response.json()
    assert Path(response.json()["photos"][0]["image_url"]).suffix == extension
    _, stored = stored_photo(media_root, response)
    assert stored.format == stored_format
    assert stored.mode == mode


@pytest.mark.django_db
def test_large_palette_png_is_scaled_smoothly(seller_client, media_root):
    picture = Image.new("RGBA", (4096, 1024), (255, 0, 0, 0))
    picture.paste((0, 0, 255, 255), (0, 0, 2048, 1024))
    upload = encode(picture.convert("P"), "PNG")
    response = post_listing(seller_client, photos=[SimpleUploadedFile("p.png", upload)])
    assert response.status_code == 201, response.json()
    _, stored = stored_photo(media_root, response)
    assert stored.size == (2048, 512)
    assert stored.mode in {"RGB", "RGBA"}


@pytest.mark.django_db
@pytest.mark.parametrize("image_format", ["MPO", "PNG", "WEBP"])
def test_multi_frame_photo_keeps_only_the_first_picture(seller_client, media_root, image_format):
    upload = encode(
        Image.new("RGB", (32, 32), "red"),
        image_format,
        save_all=True,
        append_images=[Image.new("RGB", (32, 32), "blue")],
    )
    assert getattr(Image.open(io.BytesIO(upload)), "n_frames", 1) == 2
    response = post_listing(seller_client, photos=[SimpleUploadedFile("p", upload)])
    assert response.status_code == 201, response.json()
    _, stored = stored_photo(media_root, response)
    assert stored.format == ("JPEG" if image_format == "MPO" else image_format)
    assert getattr(stored, "n_frames", 1) == 1
    red, _, blue = stored.convert("RGB").getpixel((16, 16))
    assert red > 200 and blue < 50


def truncated(image_format):
    """A photo whose header is intact but whose image data is cut off."""
    noise = Image.effect_noise((256, 256), 64).convert("RGB")
    data = encode(noise, image_format)
    return SimpleUploadedFile("cut", data[: len(data) // 2])


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("image_format", "error"),
    [
        # A truncated JPEG only fails once it's decoded for re-encoding.
        ("JPEG", "Photo 2 couldn't be read. It may be damaged; try another photo."),
        ("PNG", "Photo 2 couldn't be read. It may be damaged; try another photo."),
        # Pillow can't even identify a truncated WebP.
        ("WEBP", "Photo 2 isn't a JPEG, PNG or WebP image."),
    ],
)
def test_damaged_photo_is_a_field_error(seller_client, media_root, image_format, error):
    response = post_listing(seller_client, photos=[image(), truncated(image_format)])
    assert response.status_code == 400
    assert response.json()["photos"] == [error]
    assert not Listing.objects.exists()
    assert not ListingPhoto.objects.exists()
    assert not [f for f in media_root.rglob("*") if f.is_file()]  # photo 1 wasn't stored


@pytest.mark.django_db
@pytest.mark.filterwarnings("ignore::PIL.Image.DecompressionBombWarning")
@pytest.mark.parametrize("size", [(11, 10), (21, 10)])  # Pillow warns past 100, raises past 200
def test_decompression_bomb_is_a_field_error(seller_client, monkeypatch, size):
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)
    upload = encode(Image.new("RGB", size), "PNG")
    response = post_listing(seller_client, photos=[SimpleUploadedFile("bomb.png", upload)])
    assert response.status_code == 400
    assert response.json()["photos"] == ["Photo 1 has too many pixels."]
    assert not Listing.objects.exists()


@pytest.mark.django_db
@pytest.mark.filterwarnings("ignore::PIL.Image.DecompressionBombWarning")
@pytest.mark.parametrize(
    ("size", "options", "accepted"),
    [
        ((4096, 4096), {}, True),  # decodes at 1/2 scale: 2048 x 2048
        ((4096, 4096), {"progressive": True}, False),  # progressive decodes at full size
        ((16384, 1024), {}, False),  # too narrow to scale down
    ],
)
def test_jpeg_pixel_limit_uses_decoded_size(seller_client, monkeypatch, size, options, accepted):
    """Large phone JPEGs (e.g. 108 MP) decode at reduced scale, so the limit applies to the
    size they decode at."""
    # 4096 x 4096 is past this limit but under twice it, where Pillow refuses to open it.
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 9_000_000)
    upload = encode(Image.new("RGB", size), "JPEG", **options)
    response = post_listing(seller_client, photos=[SimpleUploadedFile("big.jpg", upload)])
    assert (response.status_code == 201) is accepted


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
