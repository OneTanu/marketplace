import io
from datetime import timedelta
from pathlib import Path

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.utils import timezone
from PIL import ExifTags, Image, ImageCms

from apps.accounts.models import User
from apps.listings import services
from apps.listings.models import Category, Listing, ListingKind, ListingPhoto
from apps.schools.models import School

CATEGORIES_URL = "/api/categories/"
LISTINGS_URL = "/api/listings/"
MY_LISTINGS_URL = "/api/listings/mine/"
# Departments in nav order (0007_seed_category_tree). Clothing (0004) is retired.
SEEDED_DEPARTMENTS = [
    "women",
    "men",
    "shoes",
    "accessories",
    "dorm-furniture",
    "electronics",
    "textbooks",
    "free",
    "other",
]


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
        "category": category("women-coats-jackets").pk,
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
    body = response.json()
    assert set(body[0]) == {"id", "name", "slug", "parent"}
    slugs = [c["slug"] for c in body]
    assert "retired" not in slugs and "tutoring" not in slugs and "clothing" not in slugs
    # Siblings come in display order; `parent` is the parent category id (null at the top).
    assert [c["slug"] for c in body if c["parent"] is None] == SEEDED_DEPARTMENTS
    by_id = {c["id"]: c["slug"] for c in body}
    men = [c["slug"] for c in body if by_id.get(c["parent"]) == "men"]
    assert men[:3] == ["men-t-shirts", "men-shirts", "men-jeans"]
    shoes = [c["name"] for c in body if by_id.get(c["parent"]) == "shoes"]
    assert shoes == ["Women's", "Men's", "Unisex"]


@pytest.mark.django_db
def test_categories_rejects_unknown_kind(seller_client):
    response = seller_client.get(CATEGORIES_URL, {"kind": "tickets"})
    assert response.status_code == 400
    assert "kind" in response.json()


# --- Sign-in ---


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", CATEGORIES_URL),
        ("post", LISTINGS_URL),
        ("get", f"{LISTINGS_URL}1/"),
        ("get", MY_LISTINGS_URL),
        ("patch", f"{LISTINGS_URL}1/"),
        ("delete", f"{LISTINGS_URL}1/"),
        ("post", f"{LISTINGS_URL}1/photos/"),
        ("delete", f"{LISTINGS_URL}1/photos/1/"),
        ("put", f"{LISTINGS_URL}1/photos/order/"),
    ],
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
        "id": category("women-coats-jackets").pk,
        "name": "Coats & Jackets",
        "slug": "women-coats-jackets",
        "parent": category("women").pk,
    }
    assert body["school"] == {"id": umd.pk, "short_name": "UMD"}
    assert body["seller"] == {"id": seller.pk, "username": "seller"}
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
@pytest.mark.parametrize("slug", ["women", "shoes", "accessories"])
def test_listing_cant_go_in_a_department_with_subcategories(seller_client, slug):
    response = post_listing(seller_client, category=category(slug).pk)
    assert response.status_code == 400
    assert response.json()["category"] == [f"Choose a subcategory of {category(slug).name}."]
    assert not Listing.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("slug", ["shoes-men", "men-jeans", "electronics"])
def test_listing_goes_in_a_leaf(seller_client, slug):
    body = posted(seller_client, category=category(slug).pk)
    assert body["category"]["slug"] == slug


@pytest.mark.django_db
def test_a_department_whose_subcategories_are_all_retired_is_a_leaf(seller_client):
    Category.objects.filter(parent__slug="shoes").update(is_active=False)
    assert post_listing(seller_client, category=category("shoes").pk).status_code == 201


@pytest.mark.django_db
def test_editing_into_a_department_is_rejected(seller_client):
    body = posted(seller_client)
    response = patch_listing(seller_client, body["id"], {"category": category("men").pk})
    assert response.status_code == 400
    assert response.json()["category"] == ["Choose a subcategory of Men."]
    assert (
        patch_listing(seller_client, body["id"], {"category": category("men-pants").pk}).json()[
            "category"
        ]["slug"]
        == "men-pants"
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("slug", "price_cents"),
    [("free", 0), ("women-coats-jackets", 1), ("women-coats-jackets", 1_000_000)],
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
    assert [set(p) for p in body["photos"]] == [{"id", "position", "image_url", "thumbnail_url"}]
    assert body["removed_by"] is None  # only the seller sees it


@pytest.mark.django_db
def test_seller_sees_removed_by(seller_client):
    body = posted(seller_client)
    assert body["removed_by"] == ""
    assert seller_client.get(listing_url(body["id"])).json()["removed_by"] == ""


@pytest.mark.django_db
def test_fetching_a_missing_listing_is_404(seller_client):
    assert seller_client.get(f"{LISTINGS_URL}999999/").status_code == 404


# --- My listings ---


def make_listing(owner, title, *, status=Listing.Status.AVAILABLE, days_ago=0):
    """A listing posted days_ago, already moved to status (status services arrive with #6)."""
    listing = services.create_item_listing(
        owner,
        category=category("women-coats-jackets"),
        title=title,
        price_cents=2500,
        condition="good",
        photos=[image()],
    )
    Listing.objects.filter(pk=listing.pk).update(
        status=status, created_at=timezone.now() - timedelta(days=days_ago)
    )
    return listing


def titles(response):
    return [listing["title"] for listing in response.json()]


@pytest.mark.django_db
def test_my_listings_has_only_the_signed_in_sellers_listings(seller_client, seller, umd, gw):
    make_listing(seller, "Mine")
    classmate = User.objects.create_user(
        "classmate@umd.edu", "pw-123456789", username="classmate", school=umd
    )
    make_listing(classmate, "Classmate's")
    make_listing(
        User.objects.create_user(
            "colonial@gwu.edu", "pw-123456789", username="colonial", school=gw
        ),
        "GW",
    )

    response = seller_client.get(MY_LISTINGS_URL)

    assert response.status_code == 200
    assert titles(response) == ["Mine"]
    body = response.json()[0]
    assert body["seller"] == {"id": seller.pk, "username": "seller"}
    assert [p["position"] for p in body["photos"]] == [0]


@pytest.mark.django_db
def test_my_listings_are_newest_first(seller_client, seller):
    # Created out of order, so the result can't come from id order by accident.
    make_listing(seller, "Two days old", days_ago=2)
    make_listing(seller, "New", days_ago=0)
    make_listing(seller, "Five days old", days_ago=5)

    response = seller_client.get(MY_LISTINGS_URL)

    assert titles(response) == ["New", "Two days old", "Five days old"]


@pytest.mark.django_db
@pytest.mark.parametrize("listing_status", ["available", "pending", "sold"])
def test_my_listings_status_filter(seller_client, seller, listing_status):
    for each in ("available", "pending", "sold"):
        make_listing(seller, f"{each} 1", status=each, days_ago=1)
        make_listing(seller, f"{each} 2", status=each)

    response = seller_client.get(MY_LISTINGS_URL, {"status": listing_status})

    assert response.status_code == 200
    assert titles(response) == [f"{listing_status} 2", f"{listing_status} 1"]
    assert {listing["status"] for listing in response.json()} == {listing_status}


@pytest.mark.django_db
def test_my_listings_rejects_unknown_status(seller_client):
    response = seller_client.get(MY_LISTINGS_URL, {"status": "draft"})
    assert response.status_code == 400
    assert "status" in response.json()


@pytest.mark.django_db
def test_my_listings_hides_seller_removed_and_shows_moderation_removed(seller_client, seller):
    make_listing(seller, "Still for sale", days_ago=2)
    services.remove_by_seller(make_listing(seller, "Taken down", days_ago=1), seller)
    services.remove_by_moderation(make_listing(seller, "Prohibited"))

    response = seller_client.get(MY_LISTINGS_URL)

    assert titles(response) == ["Prohibited", "Still for sale"]
    assert [listing["removed_by"] for listing in response.json()] == ["moderation", ""]
    assert titles(seller_client.get(MY_LISTINGS_URL, {"status": "removed"})) == ["Prohibited"]


# --- Editing ---


def listing_url(listing_id):
    return f"{LISTINGS_URL}{listing_id}/"


def photos_url(listing_id):
    return f"{LISTINGS_URL}{listing_id}/photos/"


def photo_url(listing_id, photo_id):
    return f"{LISTINGS_URL}{listing_id}/photos/{photo_id}/"


def order_url(listing_id):
    return f"{LISTINGS_URL}{listing_id}/photos/order/"


def patch_listing(client, listing_id, data):
    return client.patch(listing_url(listing_id), data, content_type="application/json")


def put_order(client, listing_id, photo_ids):
    return client.put(
        order_url(listing_id), {"photo_ids": photo_ids}, content_type="application/json"
    )


def posted(client, photo_count=1, **overrides):
    """A listing posted through the API, as its response body."""
    photos = [image(f"{i}.jpg") for i in range(photo_count)]
    response = post_listing(client, photos=photos, **overrides)
    assert response.status_code == 201, response.json()
    return response.json()


def photo_ids(body):
    return [photo["id"] for photo in sorted(body["photos"], key=lambda p: p["position"])]


def stored_positions(listing_id):
    return list(
        ListingPhoto.objects.filter(listing_id=listing_id)
        .order_by("position")
        .values_list("id", "position")
    )


def stored_files(media_root):
    return {f for f in media_root.rglob("*") if f.is_file()}


def set_status(listing_id, listing_status):
    Listing.objects.filter(pk=listing_id).update(status=listing_status)


@pytest.fixture
def classmate_client(umd):
    classmate = User.objects.create_user(
        "classmate@umd.edu", "pw-123456789", username="classmate", school=umd
    )
    client = Client()
    client.force_login(classmate)
    return client


# Each write endpoint, as a function of (client, listing body) that sends a valid request.
EDIT_REQUESTS = {
    "patch": lambda client, body: patch_listing(client, body["id"], {"title": "New title"}),
    "add photo": lambda client, body: client.post(photos_url(body["id"]), {"photo": image()}),
    "delete photo": lambda client, body: client.delete(photo_url(body["id"], photo_ids(body)[0])),
    "reorder": lambda client, body: put_order(client, body["id"], photo_ids(body)[::-1]),
}


@pytest.mark.django_db
def test_seller_edits_fields_and_item_details(seller_client):
    body = posted(seller_client)

    response = patch_listing(
        seller_client,
        body["id"],
        {
            "title": "Blue winter jacket",
            "description": "Worn two seasons.\r\nNo stains.",
            "category": category("other").pk,
            "price_cents": 1999,
            "item_details": {"condition": "good", "color": "blue"},
        },
    )

    assert response.status_code == 200, response.json()
    edited = response.json()
    assert edited["title"] == "Blue winter jacket"
    assert edited["description"] == "Worn two seasons.\nNo stains."
    assert edited["category"]["slug"] == "other"
    assert edited["price_cents"] == 1999
    # Item details left out keep their value.
    assert edited["item_details"] == {
        "condition": "good",
        "size": "M",
        "brand": "Patagonia",
        "color": "blue",
    }
    assert edited["photos"] == body["photos"]
    assert edited["updated_at"] > body["updated_at"]
    assert seller_client.get(listing_url(body["id"])).json() == edited


@pytest.mark.django_db
def test_patch_can_clear_optional_details(seller_client):
    body = posted(seller_client)
    response = patch_listing(
        seller_client,
        body["id"],
        {"description": "", "item_details": {"size": "", "brand": "", "color": ""}},
    )
    assert response.status_code == 200, response.json()
    assert response.json()["description"] == ""
    assert response.json()["item_details"] == {
        "condition": "like_new",
        "size": "",
        "brand": "",
        "color": "",
    }


@pytest.mark.django_db
def test_patch_ignores_server_set_fields(seller_client, umd, gw):
    body = posted(seller_client)
    response = patch_listing(
        seller_client,
        body["id"],
        {
            "title": "Still a jacket",
            "school": gw.pk,
            "status": "sold",
            "kind": "service",
            "currency": "EUR",
            "seller": 999,
        },
    )
    assert response.status_code == 200, response.json()
    listing = Listing.objects.get(pk=body["id"])
    assert listing.title == "Still a jacket"
    assert listing.school == umd
    assert listing.status == Listing.Status.AVAILABLE
    assert listing.kind == ListingKind.ITEM
    assert listing.currency == "USD"
    assert listing.seller_id == body["seller"]["id"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("posted_as", "changes", "accepted"),
    [
        # The Free/$0 rule applies to the resulting category and price.
        ("women-coats-jackets", {"category": "free"}, False),  # Free, but still $25
        ("women-coats-jackets", {"category": "free", "price_cents": 0}, True),
        ("women-coats-jackets", {"price_cents": 0}, False),  # $0 outside Free
        ("free", {"price_cents": 500}, False),
        ("free", {"category": "women-coats-jackets"}, False),  # leaving Free at $0
        ("free", {"category": "women-coats-jackets", "price_cents": 500}, True),
        ("free", {"title": "Free lamp"}, True),
    ],
)
def test_patch_free_rule(seller_client, posted_as, changes, accepted):
    body = posted(
        seller_client,
        category=category(posted_as).pk,
        price_cents=0 if posted_as == "free" else 2500,
    )
    data = changes | (
        {"category": category(changes["category"]).pk} if "category" in changes else {}
    )

    response = patch_listing(seller_client, body["id"], data)

    assert (response.status_code == 200) is accepted, response.json()
    if not accepted:
        assert response.status_code == 400
        assert "price_cents" in response.json()
        listing = Listing.objects.get(pk=body["id"])
        assert (listing.category.slug, listing.price_cents) == (
            posted_as,
            body["price_cents"],
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("data", "field"),
    [
        ({"title": ""}, "title"),
        ({"title": "x" * 121}, "title"),
        ({"description": "x" * 5_001}, "description"),
        ({"price_cents": -1}, "price_cents"),
        ({"price_cents": 1_000_001}, "price_cents"),
        ({"price_cents": "24.99"}, "price_cents"),
        ({"category": service_category}, "category"),
        ({"category": retired_category}, "category"),
        ({"category": 999_999}, "category"),
        ({"item_details": {"condition": "mint"}}, "item_details"),
        ({"item_details": {"condition": ""}}, "item_details"),
        ({"item_details": {"color": "teal"}}, "item_details"),
        ({"item_details": {"size": "x" * 31}}, "item_details"),
    ],
)
def test_patch_validation_errors_are_field_level(seller_client, data, field):
    body = posted(seller_client)
    resolved = {key: value() if callable(value) else value for key, value in data.items()}

    response = patch_listing(seller_client, body["id"], resolved)

    assert response.status_code == 400
    assert field in response.json(), response.json()
    assert seller_client.get(listing_url(body["id"])).json() == body


@pytest.mark.django_db
def test_item_details_errors_from_the_service_are_nested(seller_client):
    """A listing can lack an ItemDetails row (e.g. made in the admin). Adding details then
    needs a condition, which only the update service can tell."""
    body = posted(seller_client)
    Listing.objects.get(pk=body["id"]).item_details.delete()

    response = patch_listing(seller_client, body["id"], {"item_details": {"size": "M"}})

    assert response.status_code == 400
    assert set(response.json()) == {"item_details"}
    assert set(response.json()["item_details"]) == {"condition"}
    assert not Listing.objects.filter(pk=body["id"], item_details__isnull=False).exists()


@pytest.mark.django_db
def test_seller_and_status_are_checked_before_fields(seller_client, classmate_client):
    body = posted(seller_client)
    invalid = {"title": "", "price_cents": -1}
    assert patch_listing(classmate_client, body["id"], invalid).status_code == 403
    set_status(body["id"], "pending")
    assert patch_listing(seller_client, body["id"], invalid).status_code == 409
    assert seller_client.post(photos_url(body["id"]), {}).status_code == 409


@pytest.mark.django_db
def test_listing_in_a_retired_category_can_still_be_edited(seller_client):
    body = posted(seller_client)
    Category.objects.filter(slug="women-coats-jackets").update(is_active=False)
    response = patch_listing(
        seller_client,
        body["id"],
        {"title": "Jacket", "category": category("women-coats-jackets").pk},
    )
    assert response.status_code == 200, response.json()


@pytest.mark.django_db
@pytest.mark.parametrize("request_name", list(EDIT_REQUESTS))
def test_only_the_seller_can_edit(seller_client, classmate_client, media_root, request_name):
    body = posted(seller_client, photo_count=2)
    files_before = stored_files(media_root)

    response = EDIT_REQUESTS[request_name](classmate_client, body)

    assert response.status_code == 403
    assert seller_client.get(listing_url(body["id"])).json() == body
    assert stored_files(media_root) == files_before


@pytest.mark.django_db
@pytest.mark.parametrize("request_name", list(EDIT_REQUESTS))
@pytest.mark.parametrize("listing_status", ["pending", "sold", "removed"])
def test_only_available_listings_can_be_edited(
    seller_client, media_root, request_name, listing_status
):
    body = posted(seller_client, photo_count=2)
    set_status(body["id"], listing_status)
    files_before = stored_files(media_root)

    response = EDIT_REQUESTS[request_name](seller_client, body)

    assert response.status_code == 409
    assert "Only Available listings can be edited" in response.json()["detail"]
    assert seller_client.get(listing_url(body["id"])).json() == body | {"status": listing_status}
    assert stored_files(media_root) == files_before


@pytest.mark.django_db
def test_another_student_sees_the_listing_and_its_sellers_username(
    seller_client, seller, classmate_client
):
    body = posted(seller_client)

    response = classmate_client.get(listing_url(body["id"]))

    assert response.status_code == 200
    assert response.json()["seller"] == {"id": seller.pk, "username": "seller"}
    assert response.json()["removed_by"] is None  # only the seller learns who removed it


@pytest.mark.django_db
@pytest.mark.parametrize("request_name", list(EDIT_REQUESTS))
def test_removed_listing_is_404_for_others(seller_client, classmate_client, request_name):
    body = posted(seller_client, photo_count=2)
    set_status(body["id"], "removed")
    assert EDIT_REQUESTS[request_name](classmate_client, body).status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("request_name", list(EDIT_REQUESTS))
def test_editing_a_missing_listing_is_404(seller_client, request_name):
    missing = {"id": 999_999, "photos": [{"id": 1, "position": 0}]}
    assert EDIT_REQUESTS[request_name](seller_client, missing).status_code == 404


@pytest.mark.django_db
def test_add_photo_goes_last_and_is_cleaned(seller_client, media_root):
    body = posted(seller_client, photo_count=2)
    exif = Image.Exif()
    exif[ExifTags.IFD.GPSInfo] = {
        ExifTags.GPS.GPSLatitudeRef: "N",
        ExifTags.GPS.GPSLatitude: (38.0, 59.0, 10.0),
    }
    upload = encode(Image.new("RGB", (3000, 1000), "blue"), "JPEG", exif=exif.tobytes())
    assert Image.open(io.BytesIO(upload)).getexif().get_ifd(ExifTags.IFD.GPSInfo)

    response = seller_client.post(
        photos_url(body["id"]), {"photo": SimpleUploadedFile("garage.html", upload)}
    )

    assert response.status_code == 201, response.json()
    edited = response.json()
    assert photo_ids(edited)[:2] == photo_ids(body)
    assert [p["position"] for p in edited["photos"]] == [0, 1, 2]
    added = edited["photos"][2]
    assert Path(added["image_url"]).suffix == ".jpg"
    assert Path(added["image_url"]).stem != "garage"
    data, stored = stored_photo(media_root, response, index=2)
    assert not stored.getexif()
    assert b"Exif" not in data
    assert stored.size == (2048, 683)


@pytest.mark.django_db
def test_add_photo_closes_gaps_in_positions(seller_client):
    body = posted(seller_client, photo_count=2)
    first, second = photo_ids(body)
    ListingPhoto.objects.filter(pk=second).update(position=5)  # e.g. set in the admin

    response = seller_client.post(photos_url(body["id"]), {"photo": image()})

    assert response.status_code == 201, response.json()
    added = photo_ids(response.json())[2]
    assert stored_positions(body["id"]) == [(first, 0), (second, 1), (added, 2)]


@pytest.mark.django_db
def test_add_photo_caps_a_listing_at_ten(seller_client, media_root):
    body = posted(seller_client, photo_count=9)
    assert seller_client.post(photos_url(body["id"]), {"photo": image()}).status_code == 201
    files_before = stored_files(media_root)

    response = seller_client.post(photos_url(body["id"]), {"photo": image()})

    assert response.status_code == 400
    assert response.json()["photo"] == [
        "A listing can have up to 10 photos. Delete one to add another."
    ]
    assert ListingPhoto.objects.filter(listing_id=body["id"]).count() == 10
    assert stored_files(media_root) == files_before


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("upload", "error"),
    [
        (lambda: SimpleUploadedFile("notes.jpg", b"not an image"), "isn't a JPEG, PNG or WebP"),
        (gif_photo, "isn't a JPEG, PNG or WebP"),
        (lambda: truncated("PNG"), "couldn't be read"),
        (oversized_photo, "larger than 10 MB"),
    ],
)
def test_add_photo_rejects_bad_files(seller_client, media_root, upload, error):
    body = posted(seller_client)
    files_before = stored_files(media_root)

    response = seller_client.post(photos_url(body["id"]), {"photo": upload()})

    assert response.status_code == 400
    assert error in response.json()["photo"][0]
    assert ListingPhoto.objects.filter(listing_id=body["id"]).count() == 1
    assert stored_files(media_root) == files_before


@pytest.mark.django_db
def test_add_photo_requires_a_file(seller_client):
    body = posted(seller_client)
    response = seller_client.post(photos_url(body["id"]), {})
    assert response.status_code == 400
    assert "photo" in response.json()


@pytest.mark.django_db
@pytest.mark.parametrize("deleted_index", [0, 1, 2])
def test_delete_photo_keeps_positions_contiguous(
    seller_client, media_root, django_capture_on_commit_callbacks, deleted_index
):
    body = posted(seller_client, photo_count=3)
    ids = photo_ids(body)
    deleted = ListingPhoto.objects.get(pk=ids[deleted_index])

    with django_capture_on_commit_callbacks(execute=True):
        response = seller_client.delete(photo_url(body["id"], ids[deleted_index]))

    assert response.status_code == 200, response.json()
    remaining = [photo_id for photo_id in ids if photo_id != ids[deleted_index]]
    assert photo_ids(response.json()) == remaining  # deleting the cover promotes the next one
    assert stored_positions(body["id"]) == [(remaining[0], 0), (remaining[1], 1)]
    assert not (media_root / deleted.image.name).exists()


@pytest.mark.django_db
def test_last_photo_cannot_be_deleted(seller_client, media_root):
    body = posted(seller_client)
    files_before = stored_files(media_root)

    response = seller_client.delete(photo_url(body["id"], photo_ids(body)[0]))

    assert response.status_code == 400
    assert "at least one photo" in response.json()["photo"][0]
    assert stored_positions(body["id"]) == [(photo_ids(body)[0], 0)]
    assert stored_files(media_root) == files_before


@pytest.mark.django_db
def test_deleting_another_listings_photo_is_404(seller_client):
    first = posted(seller_client, photo_count=2)
    second = posted(seller_client, photo_count=2)
    response = seller_client.delete(photo_url(first["id"], photo_ids(second)[0]))
    assert response.status_code == 404
    assert ListingPhoto.objects.filter(listing_id=second["id"]).count() == 2


@pytest.mark.django_db
def test_reorder_photos(seller_client):
    body = posted(seller_client, photo_count=3)
    a, b, c = photo_ids(body)

    response = put_order(seller_client, body["id"], [c, a, b])

    assert response.status_code == 200, response.json()
    assert photo_ids(response.json()) == [c, a, b]
    assert stored_positions(body["id"]) == [(c, 0), (a, 1), (b, 2)]
    # The API lists photos cover first.
    assert [p["id"] for p in seller_client.get(listing_url(body["id"])).json()["photos"]] == [
        c,
        a,
        b,
    ]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "order",
    [
        lambda ids, other: ids[:2],  # one missing
        lambda ids, other: [*ids, ids[0]],  # one twice
        lambda ids, other: [ids[0], ids[0], ids[1]],  # one twice, one missing
        lambda ids, other: [*ids, other],  # another listing's photo
        lambda ids, other: [ids[0], ids[1], other],  # swapped for another listing's photo
        lambda ids, other: [*ids, 999_999],  # no such photo
        lambda ids, other: [],
    ],
)
def test_reorder_must_list_exactly_the_current_photos(seller_client, order):
    body = posted(seller_client, photo_count=3)
    other = photo_ids(posted(seller_client))[0]
    before = stored_positions(body["id"])

    response = put_order(seller_client, body["id"], order(photo_ids(body), other))

    assert response.status_code == 400
    assert "photo_ids" in response.json()
    assert stored_positions(body["id"]) == before


# --- Removing ---


def removal_fields(listing_id):
    return Listing.objects.values("status", "removed_by", "removed_at").get(pk=listing_id)


@pytest.mark.django_db
def test_seller_removes_a_listing(seller_client, classmate_client):
    body = posted(seller_client)
    before = timezone.now()

    response = seller_client.delete(listing_url(body["id"]))

    assert response.status_code == 204
    fields = removal_fields(body["id"])
    assert (fields["status"], fields["removed_by"]) == ("removed", "seller")
    assert before <= fields["removed_at"] <= timezone.now()
    assert seller_client.get(MY_LISTINGS_URL).json() == []
    # Soft delete: the seller can still fetch it; to everyone else it doesn't exist.
    seller_view = seller_client.get(listing_url(body["id"]))
    assert seller_view.status_code == 200
    assert seller_view.json()["removed_by"] == "seller"
    assert classmate_client.get(listing_url(body["id"])).status_code == 404


@pytest.mark.django_db
def test_only_the_seller_can_remove(seller_client, classmate_client):
    body = posted(seller_client)
    before = removal_fields(body["id"])

    response = classmate_client.delete(listing_url(body["id"]))

    assert response.status_code == 403
    assert removal_fields(body["id"]) == before


@pytest.mark.django_db
@pytest.mark.parametrize("listing_status", ["pending", "sold"])
def test_only_available_listings_can_be_removed(seller_client, listing_status):
    body = posted(seller_client)
    set_status(body["id"], listing_status)
    before = removal_fields(body["id"])

    response = seller_client.delete(listing_url(body["id"]))

    assert response.status_code == 409
    assert response.json()["detail"] == (
        f"This listing is {listing_status.title()}. Only Available listings can be removed."
    )
    assert removal_fields(body["id"]) == before


@pytest.mark.django_db
@pytest.mark.parametrize("remove", ["seller", "moderation"])
def test_removed_listing_is_404_to_others_and_a_409_to_its_seller(
    seller_client, classmate_client, seller, remove
):
    body = posted(seller_client)
    listing = Listing.objects.get(pk=body["id"])
    if remove == "seller":
        services.remove_by_seller(listing, seller)
    else:
        services.remove_by_moderation(listing)
    before = removal_fields(body["id"])

    assert classmate_client.get(listing_url(body["id"])).status_code == 404
    assert classmate_client.delete(listing_url(body["id"])).status_code == 404
    assert seller_client.get(listing_url(body["id"])).json()["removed_by"] == remove
    assert seller_client.delete(listing_url(body["id"])).status_code == 409
    assert removal_fields(body["id"]) == before


@pytest.mark.django_db
def test_removing_a_missing_listing_is_404(seller_client):
    assert seller_client.delete(listing_url(999_999)).status_code == 404


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
