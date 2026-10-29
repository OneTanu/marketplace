import pytest
from allauth.account.models import EmailAddress
from django.db import IntegrityError, connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from apps.listings import pagination, services
from apps.listings.models import Bookmark, Listing
from apps.trust.models import UserRestriction

from .test_feed import gw, make, media_root, seller, student, umd  # noqa: F401

LIST_URL = "/api/bookmarks/"


def bookmark_url(listing_id):
    return f"/api/listings/{listing_id}/bookmark/"


@pytest.fixture
def viewer(umd):  # noqa: F811
    return student("viewer@umd.edu", umd)


@pytest.fixture
def client(viewer):
    client = Client()
    client.force_login(viewer)
    return client


def saved(client, **params):
    response = client.get(LIST_URL, params)
    assert response.status_code == 200, response.json()
    return response.json()


def set_status(listing, status, **fields):
    Listing.objects.filter(pk=listing.pk).update(status=status, **fields)


# --- Saving and unsaving ---


@pytest.mark.django_db
def test_bookmarking_is_idempotent(client, viewer, seller):  # noqa: F811
    listing = make(seller, "Lamp")

    for _ in range(2):
        response = client.put(bookmark_url(listing.pk))
        assert response.status_code == 200
        assert response.json() == {"is_bookmarked": True}

    assert Bookmark.objects.filter(user=viewer, listing=listing).count() == 1


@pytest.mark.django_db
def test_unbookmarking_is_idempotent(client, viewer, seller):  # noqa: F811
    listing = make(seller, "Lamp")
    client.put(bookmark_url(listing.pk))

    assert client.delete(bookmark_url(listing.pk)).status_code == 204
    assert client.delete(bookmark_url(listing.pk)).status_code == 204
    assert not Bookmark.objects.exists()


@pytest.mark.django_db
def test_one_bookmark_per_student_and_listing_in_the_database(viewer, seller):  # noqa: F811
    listing = make(seller, "Lamp")
    Bookmark.objects.create(user=viewer, listing=listing)

    with pytest.raises(IntegrityError):
        Bookmark.objects.create(user=viewer, listing=listing)


@pytest.mark.django_db
def test_bookmarks_need_a_signed_in_student(seller):  # noqa: F811
    listing = make(seller, "Lamp")

    assert Client().put(bookmark_url(listing.pk)).status_code == 403
    assert Client().get(LIST_URL).status_code == 403


@pytest.mark.django_db
def test_cant_bookmark_your_own_listing(seller):  # noqa: F811
    listing = make(seller, "Lamp")
    client = Client()
    client.force_login(seller)

    response = client.put(bookmark_url(listing.pk))

    assert response.status_code == 400
    assert not Bookmark.objects.exists()


@pytest.mark.django_db
def test_pending_listings_can_be_saved_but_sold_ones_cant(client, seller):  # noqa: F811
    pending = make(seller, "Pending lamp", status=Listing.Status.PENDING)
    sold = make(seller, "Sold lamp", status=Listing.Status.SOLD)

    assert client.put(bookmark_url(pending.pk)).status_code == 200
    response = client.put(bookmark_url(sold.pk))
    assert response.status_code == 409
    assert "Sold" in response.json()["detail"]


@pytest.mark.django_db
def test_removed_and_missing_listings_are_a_404(client, seller):  # noqa: F811
    removed = make(seller, "Gone", status=Listing.Status.REMOVED)

    assert client.put(bookmark_url(removed.pk)).status_code == 404
    assert client.put(bookmark_url(999999)).status_code == 404


@pytest.mark.django_db
def test_listings_at_other_schools_can_be_saved(client, gw):  # noqa: F811
    # Like the listing page, which any signed-in student can open whatever its school.
    listing = make(student("colonial@gwu.edu", gw), "GW lamp")

    assert client.put(bookmark_url(listing.pk)).status_code == 200


@pytest.mark.django_db
def test_a_saved_listing_that_later_sells_can_still_be_saved_again(client, seller):  # noqa: F811
    listing = make(seller, "Lamp")
    client.put(bookmark_url(listing.pk))
    set_status(listing, Listing.Status.SOLD)

    assert client.put(bookmark_url(listing.pk)).status_code == 200
    assert client.delete(bookmark_url(listing.pk)).status_code == 204


@pytest.mark.django_db
def test_deleting_a_listing_or_student_deletes_their_bookmarks(viewer, seller):  # noqa: F811
    first, second = make(seller, "One"), make(seller, "Two")
    services.bookmark_listing(viewer, first)
    services.bookmark_listing(viewer, second)

    first.delete()
    assert list(Bookmark.objects.values_list("listing_id", flat=True)) == [second.pk]
    viewer.delete()
    assert not Bookmark.objects.exists()


# --- is_bookmarked on listings ---


@pytest.mark.django_db
def test_listings_say_whether_the_viewer_saved_them(client, viewer, umd, seller):  # noqa: F811
    saved_one, other = make(seller, "Saved"), make(seller, "Other")
    services.bookmark_listing(viewer, saved_one)
    services.bookmark_listing(student("someone@umd.edu", umd), other)

    feed = {c["title"]: c["is_bookmarked"] for c in client.get("/api/listings/").json()["results"]}
    assert feed == {"Saved": True, "Other": False}
    assert client.get(f"/api/listings/{saved_one.pk}/").json()["is_bookmarked"] is True
    assert client.get(f"/api/listings/{other.pk}/").json()["is_bookmarked"] is False
    # Public profiles are only for verified students.
    EmailAddress.objects.create(user=seller, email=seller.email, verified=True, primary=True)
    profile = client.get(f"/api/users/{seller.username}/listings/").json()
    assert {c["title"]: c["is_bookmarked"] for c in profile} == feed


# --- My bookmarks ---


@pytest.mark.django_db
def test_my_bookmarks_newest_first_and_only_mine(client, viewer, umd, seller):  # noqa: F811
    first, second = make(seller, "First"), make(seller, "Second")
    services.bookmark_listing(viewer, first)
    services.bookmark_listing(viewer, second)
    services.bookmark_listing(student("someone@umd.edu", umd), make(seller, "Theirs"))

    page = saved(client)

    assert [b["listing"]["title"] for b in page["results"]] == ["Second", "First"]
    assert all(b["listing"]["is_bookmarked"] for b in page["results"])
    assert page["next_cursor"] is None


@pytest.mark.django_db
def test_my_bookmarks_page_without_gaps_or_repeats(client, viewer, seller, monkeypatch):  # noqa: F811
    monkeypatch.setattr(pagination, "PAGE_SIZE", 2)
    listings = [make(seller, f"Item {i}") for i in range(5)]
    for listing in listings:
        services.bookmark_listing(viewer, listing)

    seen, cursor = [], None
    while True:
        page = saved(client, **({"cursor": cursor} if cursor else {}))
        seen += [b["listing_id"] for b in page["results"]]
        cursor = page["next_cursor"]
        if not cursor:
            break

    assert seen == [listing.pk for listing in reversed(listings)]


@pytest.mark.django_db
def test_an_edited_cursor_is_a_400(client):
    assert client.get(LIST_URL, {"cursor": "nonsense"}).status_code == 400


@pytest.mark.django_db
def test_saved_listings_that_changed_are_shown_safely(client, viewer, seller):  # noqa: F811
    pending, sold, removed = (make(seller, t) for t in ("Pending", "Sold", "Removed"))
    for listing in (pending, sold, removed):
        services.bookmark_listing(viewer, listing)
    set_status(pending, Listing.Status.PENDING)
    set_status(sold, Listing.Status.SOLD)
    set_status(removed, Listing.Status.REMOVED, removed_by=Listing.RemovedBy.MODERATION)
    other_seller = student("suspended@umd.edu", seller.school)
    hidden = make(other_seller, "Hidden")
    services.bookmark_listing(viewer, hidden)
    UserRestriction.objects.create(
        user=other_seller, kind=UserRestriction.Kind.SUSPENSION, reason="Test"
    )

    results = {b["listing_id"]: b for b in saved(client)["results"]}

    assert results[pending.pk]["availability"] == "pending"
    assert results[pending.pk]["listing"]["status"] == "pending"
    assert results[sold.pk]["availability"] == "sold"
    assert results[sold.pk]["listing"]["status"] == "sold"
    # A removed listing looks gone, as it does everywhere else; nothing about it is shown.
    assert results[removed.pk] == {
        "listing_id": removed.pk,
        "availability": "removed",
        "listing": None,
        "created_at": results[removed.pk]["created_at"],
    }
    assert results[hidden.pk]["availability"] == "unavailable"
    assert results[hidden.pk]["listing"] is None
    # ...and can still be unsaved.
    assert client.delete(bookmark_url(removed.pk)).status_code == 204


@pytest.mark.django_db
def test_my_bookmarks_query_count_doesnt_grow(client, viewer, seller):  # noqa: F811
    services.bookmark_listing(viewer, make(seller, "First"))
    with CaptureQueriesContext(connection) as one:
        assert len(saved(client)["results"]) == 1
    for i in range(10):
        services.bookmark_listing(viewer, make(seller, f"More {i}"))
    with CaptureQueriesContext(connection) as eleven:
        assert len(saved(client)["results"]) == 11

    assert len(eleven) == len(one)


@pytest.mark.django_db
def test_feed_query_count_doesnt_grow_with_bookmarks(client, viewer, seller):  # noqa: F811
    services.bookmark_listing(viewer, make(seller, "First"))
    with CaptureQueriesContext(connection) as one:
        client.get("/api/listings/")
    for i in range(10):
        services.bookmark_listing(viewer, make(seller, f"More {i}"))
    with CaptureQueriesContext(connection) as eleven:
        assert len(client.get("/api/listings/").json()["results"]) == 11

    assert len(eleven) == len(one)
