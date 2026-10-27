"""Races between real concurrent requests: each runs in its own thread, on its own database
connection, starting together. The row locks and the one-holder constraint must leave exactly
one consistent outcome."""

import threading
from datetime import timedelta

import pytest
from django.db import connection
from django.utils import timezone

from apps.deals import services
from apps.deals.models import Deal, DealEvent, HandoffConfirmation
from apps.deals.tests.test_services import listing_for, verified_user
from apps.listings.models import Listing

S = Deal.Status
RACE = pytest.mark.django_db(transaction=True, serialized_rollback=True)


def race(*calls):
    """Run the calls at the same moment in separate threads. Returns (outcome, value) per call:
    ("ok", result) or ("error", exception)."""
    barrier = threading.Barrier(len(calls))
    results = [None] * len(calls)

    def run(index, call):
        try:
            barrier.wait(timeout=10)
            results[index] = ("ok", call())
        except Exception as exc:  # noqa: BLE001 - the outcome is what's being tested
            results[index] = ("error", exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=run, args=(i, c)) for i, c in enumerate(calls)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return results


def outcomes(results):
    return sorted(outcome for outcome, _ in results)


def fresh(deal):
    return Deal.objects.get(pk=deal.pk)


@RACE
def test_simultaneous_acceptances_leave_one_primary_buyer():
    seller = verified_user("seller")
    listing = listing_for(seller)
    deals = [
        services.create_deal(
            listing=listing, buyer=verified_user(f"buyer{i}"), kind=Deal.Kind.BUY_NOW
        )
        for i in range(3)
    ]

    results = race(*(lambda d=d: services.accept_deal(deal=d, actor=seller) for d in deals))

    assert outcomes(results) == ["error", "error", "ok"]
    statuses = sorted(fresh(d).status for d in deals)
    assert statuses == [S.BACKUP, S.BACKUP, S.PENDING]
    assert Listing.objects.get(pk=listing.pk).status == Listing.Status.PENDING


@RACE
def test_acceptance_racing_cancellation_has_one_consistent_outcome():
    seller, buyer = verified_user("seller"), verified_user("buyer")
    listing = listing_for(seller)
    deal = services.create_deal(listing=listing, buyer=buyer, kind=Deal.Kind.BUY_NOW)

    results = race(
        lambda: services.accept_deal(deal=deal, actor=seller),
        lambda: services.cancel_deal(deal=deal, actor=buyer),
    )

    final = fresh(deal)
    listing.refresh_from_db()
    accepted, canceled = results
    # Either order is valid: accept then cancel (a pending deal with no confirmation can be
    # canceled), or cancel first and acceptance refused. Never both pending and canceled.
    assert canceled[0] == "ok"
    assert final.status == S.CANCELED
    assert listing.status == Listing.Status.AVAILABLE
    moves = list(
        DealEvent.objects.filter(deal=deal)
        .exclude(to_status="")
        .values_list("to_status", flat=True)
    )
    if accepted[0] == "ok":
        assert moves == [S.AWAITING_SELLER, S.PENDING, S.CANCELED]
    else:
        assert moves == [S.AWAITING_SELLER, S.CANCELED]


@RACE
def test_acceptance_racing_expiry_after_the_deadline_never_accepts():
    seller, buyer = verified_user("seller"), verified_user("buyer")
    listing = listing_for(seller)
    deal = services.create_deal(listing=listing, buyer=buyer, kind=Deal.Kind.BUY_NOW)
    Deal.objects.filter(pk=deal.pk).update(response_deadline=timezone.now() - timedelta(seconds=1))

    results = race(
        lambda: services.accept_deal(deal=deal, actor=seller),
        lambda: services.expire(deal_id=deal.pk, expected_status=S.AWAITING_SELLER),
    )

    assert results[0][0] == "error"
    assert fresh(deal).status == S.EXPIRED
    assert Listing.objects.get(pk=listing.pk).status == Listing.Status.AVAILABLE
    assert DealEvent.objects.filter(deal=deal, event_type="expired").count() == 1


@RACE
def test_a_counteroffer_racing_expiry_after_the_deadline_never_lands():
    seller, buyer = verified_user("seller"), verified_user("buyer")
    listing = listing_for(seller)
    deal = services.create_deal(
        listing=listing, buyer=buyer, kind=Deal.Kind.OFFER, amount_cents=3000
    )
    Deal.objects.filter(pk=deal.pk).update(response_deadline=timezone.now() - timedelta(seconds=1))

    results = race(
        lambda: services.counter_offer(deal=deal, actor=seller, amount_cents=4500),
        lambda: services.expire(deal_id=deal.pk, expected_status=S.AWAITING_SELLER),
    )

    assert results[0][0] == "error"
    final = fresh(deal)
    assert final.status == S.EXPIRED
    assert final.current_amount_cents == 3000
    assert final.offers.count() == 1


@RACE
def test_simultaneous_handoff_confirmations_complete_once():
    seller, buyer = verified_user("seller"), verified_user("buyer")
    listing = listing_for(seller)
    deal = services.create_deal(listing=listing, buyer=buyer, kind=Deal.Kind.BUY_NOW)
    services.accept_deal(deal=deal, actor=seller)

    results = race(
        lambda: services.confirm_handoff(deal=deal, actor=buyer),
        lambda: services.confirm_handoff(deal=deal, actor=seller),
    )

    assert outcomes(results) == ["ok", "ok"]
    assert fresh(deal).status == S.COMPLETED
    assert HandoffConfirmation.objects.filter(deal=deal).count() == 2
    assert DealEvent.objects.filter(deal=deal, event_type="completed").count() == 1
    assert Listing.objects.get(pk=listing.pk).status == Listing.Status.SOLD


@RACE
def test_the_same_confirmation_twice_at_once_counts_once():
    seller, buyer = verified_user("seller"), verified_user("buyer")
    listing = listing_for(seller)
    deal = services.create_deal(listing=listing, buyer=buyer, kind=Deal.Kind.BUY_NOW)
    services.accept_deal(deal=deal, actor=seller)

    race(
        lambda: services.confirm_handoff(deal=deal, actor=buyer),
        lambda: services.confirm_handoff(deal=deal, actor=buyer),
    )

    assert HandoffConfirmation.objects.filter(deal=deal).count() == 1
    assert fresh(deal).status == S.PENDING


@RACE
def test_a_cancellation_racing_backup_promotion_promotes_one_backup():
    seller = verified_user("seller")
    listing = listing_for(seller)
    backups = [
        services.create_deal(
            listing=listing, buyer=verified_user(f"backup{i}"), kind=Deal.Kind.OFFER,
            amount_cents=4000,
        )
        for i in range(2)
    ]  # fmt: skip
    primary_buyer = verified_user("primary")
    primary = services.create_deal(listing=listing, buyer=primary_buyer, kind=Deal.Kind.BUY_NOW)
    services.accept_deal(deal=primary, actor=seller)

    # Both sides walk away at once: one cancel succeeds, the other is a repeat or refused.
    race(
        lambda: services.cancel_deal(deal=primary, actor=primary_buyer),
        lambda: services.cancel_deal(deal=primary, actor=seller),
    )

    assert fresh(primary).status == S.CANCELED
    assert [fresh(b).status for b in backups] == [S.AWAITING_SELLER, S.BACKUP]
    promoted = DealEvent.objects.filter(event_type="promoted_from_backup")
    assert promoted.count() == 1
