import base64
import io
import json
from datetime import UTC, datetime, timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from PIL import Image

from apps.accounts.models import User
from apps.listings import pagination, services
from apps.listings.models import Category, Listing
from apps.schools.models import MarketplaceStatus, School

FEED_URL = "/api/listings/"
# Listings are dated relative to this, so ones made "minutes_ago" apart tie exactly.
BASE_TIME = datetime(2026, 10, 1, 12, tzinfo=UTC)


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def umd():
    return School.objects.get(slug="umd")


@pytest.fixture
def gw():
    return School.objects.create(
        name="George Washington University",
        short_name="GW",
        slug="gw",
        marketplace_status=MarketplaceStatus.OPEN,
    )


def student(email, school):
    return User.objects.create_user(
        email, "pw-123456789", username=email.split("@")[0], school=school
    )


@pytest.fixture
def seller(umd):
    return student("seller@umd.edu", umd)


@pytest.fixture
def viewer_client(umd):
    client = Client()
    client.force_login(student("viewer@umd.edu", umd))
    return client


def image():
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buffer, "JPEG")
    return SimpleUploadedFile("photo.jpg", buffer.getvalue())


def make(
    owner,
    title,
    *,
    category="electronics",
    price_cents=2500,
    status=Listing.Status.AVAILABLE,
    minutes_ago=0,
    **details,
):
    listing = services.create_item_listing(
        owner,
        category=Category.objects.get(slug=category),
        title=title,
        price_cents=price_cents,
        condition=details.pop("condition", "good"),
        photos=[image()],
        **details,
    )
    Listing.objects.filter(pk=listing.pk).update(
        status=status, created_at=BASE_TIME - timedelta(minutes=minutes_ago)
    )
    return listing


def feed(client, **params):
    response = client.get(FEED_URL, params)
    assert response.status_code == 200, response.json()
    return response.json()


def titles(client, **params):
    return [card["title"] for card in feed(client, **params)["results"]]


# --- Scope and status ---


@pytest.mark.django_db
def test_feed_defaults_to_the_viewers_school(viewer_client, seller, gw):
    make(seller, "At UMD")
    make(student("colonial@gwu.edu", gw), "At GW")

    assert titles(viewer_client) == ["At UMD"]
    assert titles(viewer_client, school="gw") == ["At GW"]
    assert set(titles(viewer_client, school="all")) == {"At UMD", "At GW"}


@pytest.mark.django_db
def test_unknown_school_is_a_400(viewer_client):
    response = viewer_client.get(FEED_URL, {"school": "nowhere"})
    assert response.status_code == 400
    assert "school" in response.json()


@pytest.mark.django_db
def test_schools_whose_marketplace_isnt_open_are_left_out(viewer_client, seller, gw):
    make(seller, "At UMD")
    make(student("colonial@gwu.edu", gw), "At GW")
    gw.marketplace_status = MarketplaceStatus.PAUSED
    gw.save()

    assert titles(viewer_client, school="all") == ["At UMD"]
    assert viewer_client.get(FEED_URL, {"school": "gw"}).status_code == 400


@pytest.mark.django_db
def test_feed_has_available_and_pending_but_not_sold_or_removed(viewer_client, seller):
    for status in Listing.Status.values:
        make(seller, status, status=status)

    cards = {card["title"]: card for card in feed(viewer_client)["results"]}

    assert set(cards) == {"available", "pending"}
    assert cards["pending"]["status"] == "pending"


@pytest.mark.django_db
def test_card_fields(viewer_client, seller, umd):
    listing = make(seller, "Lamp", condition="like_new", size="Twin XL", brand="IKEA")

    [card] = feed(viewer_client)["results"]

    cover = listing.photos.get()
    assert card == {
        "id": listing.pk,
        "status": "available",
        "title": "Lamp",
        "price_cents": 2500,
        "currency": "USD",
        # The thumbnail job hasn't run, so the full image stands in.
        "cover_url": cover.image.url,
        "condition": "like_new",
        "size": "Twin XL",
        "brand": "IKEA",
        "school": {"id": umd.pk, "short_name": "UMD"},
        "seller": {"id": seller.pk, "username": "seller"},
        "created_at": card["created_at"],
    }


@pytest.mark.django_db
def test_feed_requires_sign_in(client):
    assert client.get(FEED_URL).status_code == 403


# --- Filters ---


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("category", "expected"),
    [
        ("men", {"Men's jeans", "Men's tee"}),  # a department includes its subcategories
        ("men-jeans", {"Men's jeans"}),
        ("shoes", {"Men's boots", "Women's boots"}),
        ("shoes-women", {"Women's boots"}),
        ("electronics", {"Calculator"}),  # a top-level leaf
    ],
)
def test_category_filter_includes_everything_under_it(viewer_client, seller, category, expected):
    make(seller, "Men's jeans", category="men-jeans")
    make(seller, "Men's tee", category="men-t-shirts")
    make(seller, "Men's boots", category="shoes-men")
    make(seller, "Women's boots", category="shoes-women")
    make(seller, "Calculator", category="electronics")

    assert set(titles(viewer_client, category=category)) == expected


@pytest.mark.django_db
def test_category_filter_includes_retired_subcategories(viewer_client, seller):
    make(seller, "Old tee", category="men-t-shirts")
    Category.objects.filter(slug="men-t-shirts").update(is_active=False)
    assert titles(viewer_client, category="men") == ["Old tee"]


@pytest.mark.django_db
def test_price_condition_color_size_and_brand_filters(viewer_client, seller):
    make(seller, "Cheap", price_cents=500, condition="fair", color="black", size="M")
    make(seller, "Mid", price_cents=2500, condition="good", color="gray", size="32x30")
    make(seller, "Dear", price_cents=9000, condition="like_new", color="blue", brand="Levi's")

    assert set(titles(viewer_client, min_price=2500)) == {"Mid", "Dear"}
    assert set(titles(viewer_client, max_price=2500)) == {"Cheap", "Mid"}
    assert titles(viewer_client, min_price=1000, max_price=5000) == ["Mid"]
    assert set(titles(viewer_client, condition=["fair", "like_new"])) == {"Cheap", "Dear"}
    assert set(titles(viewer_client, color=["gray", "blue"])) == {"Mid", "Dear"}
    assert titles(viewer_client, size="32X30") == ["Mid"]  # exact, but any case
    assert titles(viewer_client, size="32") == []
    assert titles(viewer_client, brand="levi's") == ["Dear"]
    assert titles(viewer_client, color="black", condition="fair", max_price=500) == ["Cheap"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"category": "no-such-category"}, "category"),
        ({"category": "clothing"}, "category"),  # retired
        ({"condition": "excellent"}, "condition"),
        ({"color": "grey"}, "color"),
        ({"min_price": "-1"}, "min_price"),
        ({"min_price": "abc"}, "min_price"),
        ({"min_price": "5000", "max_price": "100"}, "max_price"),
        ({"sort": "relevance"}, "sort"),
        ({"cursor": "not-a-cursor"}, "cursor"),
    ],
)
def test_invalid_filters_are_a_400_with_the_field(viewer_client, params, field):
    response = viewer_client.get(FEED_URL, params)
    assert response.status_code == 400
    assert field in response.json()


# --- Sorting and paging ---


@pytest.mark.django_db
def test_sorts(viewer_client, seller):
    make(seller, "Old $10", price_cents=1000, minutes_ago=30)
    make(seller, "New $30", price_cents=3000, minutes_ago=0)
    make(seller, "Mid $20", price_cents=2000, minutes_ago=10)

    assert titles(viewer_client) == ["New $30", "Mid $20", "Old $10"]
    assert titles(viewer_client, sort="price_asc") == ["Old $10", "Mid $20", "New $30"]
    assert titles(viewer_client, sort="price_desc") == ["New $30", "Mid $20", "Old $10"]


def all_pages(client, between_pages=None, **params):
    """Every page's titles in order, calling between_pages() after the first page. Fails
    rather than looping forever if the cursor stops moving."""
    seen = []
    cursor = None
    for _ in range(20):
        body = feed(client, **params, **({"cursor": cursor} if cursor else {}))
        seen += [card["title"] for card in body["results"]]
        cursor = body["next_cursor"]
        if between_pages:
            between_pages()
            between_pages = None
        if cursor is None:
            return seen
    pytest.fail(f"still paging after 20 pages: {seen}")


@pytest.mark.django_db
@pytest.mark.parametrize("sort", ["newest", "price_asc", "price_desc"])
def test_paging_has_no_duplicates_or_gaps_when_a_listing_is_posted_between_pages(
    viewer_client, seller, monkeypatch, sort
):
    monkeypatch.setattr(pagination, "PAGE_SIZE", 2)
    # Ties on every sort key except id: equal prices, and pairs posted in the same instant.
    for i in range(7):
        make(seller, f"L{i}", price_cents=2500 if i % 2 else 1000, minutes_ago=i // 3)

    seen = all_pages(
        viewer_client,
        between_pages=lambda: make(seller, "Posted mid-scroll", price_cents=2500),
        sort=sort,
    )

    assert len(seen) == len(set(seen)), f"duplicates in {seen}"
    assert {f"L{i}" for i in range(7)} <= set(seen)


@pytest.mark.django_db
@pytest.mark.parametrize("sort", ["newest", "price_asc", "price_desc"])
def test_pages_join_up_in_sort_order(viewer_client, seller, monkeypatch, sort):
    for i, price in enumerate([3000, 1000, 2000, 1000, 3000]):
        make(seller, f"L{i}", price_cents=price, minutes_ago=i // 3)
    one_page = titles(viewer_client, sort=sort)

    monkeypatch.setattr(pagination, "PAGE_SIZE", 2)

    assert all_pages(viewer_client, sort=sort) == one_page


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("made_for", "used_with"), [("price_asc", "newest"), ("price_asc", "price_desc")]
)
def test_a_cursor_from_another_sort_is_a_400(
    viewer_client, seller, monkeypatch, made_for, used_with
):
    monkeypatch.setattr(pagination, "PAGE_SIZE", 1)
    make(seller, "A")
    make(seller, "B")
    cursor = feed(viewer_client, sort=made_for)["next_cursor"]
    response = viewer_client.get(FEED_URL, {"cursor": cursor, "sort": used_with})
    assert response.status_code == 400
    assert "cursor" in response.json()


def crafted(payload) -> str:
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("sort", "cursor"),
    [
        ("price_asc", crafted({"sort": "price_asc", "after": [float("inf"), 1]})),
        ("price_asc", crafted({"sort": "price_asc", "after": [True, 1]})),
        ("price_asc", crafted({"sort": "price_asc", "after": [2**70, 1]})),
        ("price_asc", crafted({"sort": "price_asc", "after": ["10", 1]})),
        ("price_asc", crafted({"sort": "price_asc", "after": [1]})),
        ("price_asc", crafted({"sort": "price_asc", "after": {"a": 1}})),
        ("price_asc", crafted({"after": [1, 1]})),
        ("price_asc", crafted([1, 1])),
        ("newest", crafted({"sort": "newest", "after": ["9999-12-31T23:59:59.999999-23:59", 1]})),
        ("newest", crafted({"sort": "newest", "after": ["2026-10-01T12:00:00", 1]})),  # naive
        ("newest", crafted({"sort": "newest", "after": [12, 1]})),
        ("newest", "[" * 150),
        ("newest", "A" * 201),
        ("newest", "%%%"),
    ],
)
def test_edited_cursors_are_a_400_not_a_500(viewer_client, sort, cursor):
    response = viewer_client.get(FEED_URL, {"cursor": cursor, "sort": sort})
    assert response.status_code == 400
    assert "cursor" in response.json()


@pytest.mark.django_db
def test_query_count_doesnt_grow_with_the_page(viewer_client, seller):
    make(seller, "First")
    with CaptureQueriesContext(connection) as one:
        feed(viewer_client)
    for i in range(10):
        make(seller, f"More {i}")
    with CaptureQueriesContext(connection) as eleven:
        assert len(feed(viewer_client)["results"]) == 11

    assert len(eleven) == len(one)
