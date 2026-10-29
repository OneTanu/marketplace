"""Migrating deals made by the old code (0003) to the state-machine schema (0004, 0005)."""

from datetime import timedelta

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

BEFORE = [("deals", "0003_trade_and_asap")]
AFTER = [("deals", "0005_backfill_state_machine")]


def migrate(targets):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    return executor.loader.project_state(targets).apps


@pytest.mark.django_db(transaction=True, serialized_rollback=True)
def test_old_deals_migrate_into_a_consistent_state():
    old = migrate(BEFORE)
    # Only the deals tables are rolled back; everything else is current.
    from apps.accounts.models import User
    from apps.listings.models import Category, Listing
    from apps.messaging.models import Conversation
    from apps.schools.models import School

    Deal = old.get_model("deals", "Deal")
    HandoffConfirmation = old.get_model("deals", "HandoffConfirmation")

    umd = School.objects.get(slug="umd")
    users = [
        User.objects.create_user(f"m{i}@umd.edu", "pw-123456789", username=f"m{i}", school=umd)
        for i in range(5)
    ]
    seller, first, second, third, fourth = users
    category = Category.objects.get(slug="women-coats-jackets")

    def listing(title):
        return Listing.objects.create(
            school=umd, seller=seller, category=category, title=title, price_cents=1000
        )

    conversation = Conversation.objects.create(created_by=seller)
    now = timezone.now()

    def deal(listing, buyer, status, **fields):
        return Deal.objects.create(
            listing_id=listing.pk,
            buyer_id=buyer.pk,
            seller_id=seller.pk,
            conversation_id=conversation.pk,
            kind="buy_now",
            status=status,
            current_amount_cents=1000,
            **fields,
        )

    # Two pending deals on one listing: the old code allowed it. The confirmed one stays.
    crowded = listing("Crowded")
    plain = deal(crowded, first, "pending", handoff_deadline=now + timedelta(days=1))
    confirmed = deal(crowded, second, "pending", handoff_deadline=now + timedelta(days=1))
    HandoffConfirmation.objects.create(deal=confirmed, user_id=second.pk)
    # Backups get queue positions in request order.
    queued = listing("Queued")
    deal(queued, first, "pending", handoff_deadline=now + timedelta(days=1))
    late = deal(queued, third, "backup")
    early = deal(queued, fourth, "backup")
    Deal.objects.filter(pk=early.pk).update(created_at=now - timedelta(hours=2))
    # A stalled handoff (one confirmation, clock stopped) gets a deadline so it's settled.
    stalled = deal(listing("Stalled"), third, "pending", handoff_deadline=None)
    # Closed deals get closed_at.
    closed = deal(listing("Closed"), fourth, "declined")

    new = migrate(AFTER)
    Deal = new.get_model("deals", "Deal")

    assert Deal.objects.get(pk=confirmed.pk).status == "pending"
    repaired = Deal.objects.get(pk=plain.pk)
    assert (repaired.status, repaired.close_reason) == ("canceled", "duplicate_holder")
    assert repaired.events.filter(to_status="canceled").count() == 1
    assert Deal.objects.get(pk=early.pk).backup_position == 1
    assert Deal.objects.get(pk=late.pk).backup_position == 2
    assert Deal.objects.get(pk=stalled.pk).handoff_deadline is not None
    assert Deal.objects.get(pk=closed.pk).closed_at is not None

    # Running the backfill again changes nothing.
    from importlib import import_module

    backfill = import_module("apps.deals.migrations.0005_backfill_state_machine").backfill
    before = list(Deal.objects.order_by("id").values())
    backfill(new, None)
    assert list(Deal.objects.order_by("id").values()) == before
