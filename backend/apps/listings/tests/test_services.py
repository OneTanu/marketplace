import threading
from datetime import timedelta

import pytest
from django.db import connection, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.listings import services
from apps.listings.models import Category, Listing, ListingKind
from apps.listings.services import ListingStatusError
from apps.schools.models import School

AVAILABLE, PENDING, SOLD, REMOVED = (
    Listing.Status.AVAILABLE,
    Listing.Status.PENDING,
    Listing.Status.SOLD,
    Listing.Status.REMOVED,
)
SELLER, MODERATION = Listing.RemovedBy.SELLER, Listing.RemovedBy.MODERATION

# Every (function, from) the rules allow, with the resulting status. Everything else
# in the cross product of functions x statuses must be rejected.
ALLOWED = {
    ("mark_pending", AVAILABLE): PENDING,
    ("return_to_available", PENDING): AVAILABLE,
    ("mark_sold", PENDING): SOLD,
    ("remove_by_seller", AVAILABLE): REMOVED,
    ("remove_by_moderation", AVAILABLE): REMOVED,
    ("remove_by_moderation", PENDING): REMOVED,
    ("remove_by_moderation", SOLD): REMOVED,
}
FUNCTIONS = ["mark_pending", "return_to_available", "mark_sold"]
FUNCTIONS += ["remove_by_seller", "remove_by_moderation"]
STATUSES = [AVAILABLE, PENDING, SOLD, REMOVED]
DISALLOWED = [(f, s) for f in FUNCTIONS for s in STATUSES if (f, s) not in ALLOWED]


def make_listing(status=AVAILABLE, **fields):
    umd = School.objects.get(slug="umd")
    seller = User.objects.create_user(
        "seller@umd.edu", "pw-123456789", username="seller", school=umd
    )
    category = Category.objects.create(name="Clothing", slug="clothing", kind=ListingKind.ITEM)
    return Listing.objects.create(
        school=umd,
        seller=seller,
        category=category,
        title="Gray jeans",
        price_cents=2500,
        status=status,
        **fields,
    )


@pytest.mark.django_db
@pytest.mark.parametrize(("function", "from_status"), list(ALLOWED))
def test_allowed_move(function, from_status):
    listing = make_listing(status=from_status)

    returned = getattr(services, function)(listing)

    listing.refresh_from_db()
    assert listing.status == ALLOWED[(function, from_status)]
    assert returned.status == listing.status


@pytest.mark.django_db
@pytest.mark.parametrize(("function", "from_status"), DISALLOWED)
def test_disallowed_move_raises_and_changes_nothing(function, from_status):
    removed_at = timezone.now() - timedelta(days=1)
    removed = {"removed_by": SELLER, "removed_at": removed_at} if from_status == REMOVED else {}
    listing = make_listing(status=from_status, **removed)
    before = Listing.objects.values().get(pk=listing.pk)

    with pytest.raises(ListingStatusError) as excinfo:
        getattr(services, function)(listing)

    assert Listing.objects.values().get(pk=listing.pk) == before
    assert excinfo.value.listing_id == listing.pk
    assert excinfo.value.status == from_status
    assert str(listing.pk) in str(excinfo.value)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("function", "removed_by"),
    [("remove_by_seller", SELLER), ("remove_by_moderation", MODERATION)],
)
def test_removal_records_who_and_when(function, removed_by):
    listing = make_listing()
    before = timezone.now()

    getattr(services, function)(listing)

    listing.refresh_from_db()
    assert listing.status == REMOVED
    assert listing.removed_by == removed_by
    assert before <= listing.removed_at <= timezone.now()


@pytest.mark.django_db
@pytest.mark.parametrize("function", ["mark_pending", "return_to_available", "mark_sold"])
def test_non_removal_moves_leave_removal_fields_blank(function):
    listing = make_listing(status=PENDING if function != "mark_pending" else AVAILABLE)

    getattr(services, function)(listing)

    listing.refresh_from_db()
    assert listing.removed_by == ""
    assert listing.removed_at is None


@pytest.mark.django_db
def test_status_is_checked_against_the_database_not_a_stale_instance():
    first = make_listing()
    stale = Listing.objects.get(pk=first.pk)

    services.mark_pending(first)

    assert stale.status == AVAILABLE  # still in memory, but the row has moved on
    with pytest.raises(ListingStatusError):
        services.mark_pending(stale)


@pytest.mark.django_db(transaction=True, serialized_rollback=True)
def test_concurrent_mark_pending_only_one_succeeds():
    """Thread A marks the listing Pending and holds its transaction open until thread B
    is blocked on the row lock. Without the lock, B would read the committed Available
    status and also succeed."""
    listing = make_listing()
    a_holds_lock = threading.Event()
    release_a = threading.Event()
    results = {}

    def run(name, hold=False):
        try:
            with transaction.atomic():
                services.mark_pending(Listing.objects.get(pk=listing.pk))
                if hold:
                    a_holds_lock.set()
                    release_a.wait(timeout=10)
            results[name] = "ok"
        except ListingStatusError:
            results[name] = "rejected"
        finally:
            a_holds_lock.set()
            connection.close()

    a = threading.Thread(target=run, args=("a", True))
    a.start()
    assert a_holds_lock.wait(timeout=10)
    b = threading.Thread(target=run, args=("b",))
    b.start()
    _wait_for_a_backend_blocked_on_a_lock()
    release_a.set()
    a.join(timeout=10)
    b.join(timeout=10)

    assert results == {"a": "ok", "b": "rejected"}
    listing.refresh_from_db()
    assert listing.status == PENDING


def _wait_for_a_backend_blocked_on_a_lock(timeout=10):
    deadline = timezone.now() + timedelta(seconds=timeout)
    with connection.cursor() as cursor:
        while timezone.now() < deadline:
            cursor.execute(
                "SELECT count(*) FROM pg_stat_activity "
                "WHERE datname = current_database() AND wait_event_type = 'Lock'"
            )
            if cursor.fetchone()[0]:
                return
            threading.Event().wait(0.05)
    raise AssertionError("thread B never blocked on the listing's row lock")
