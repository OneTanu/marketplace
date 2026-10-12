"""Deal state transitions for offers, full-price requests, and in-person handoffs."""

from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.services import verified_users
from apps.listings import services as listing_services
from apps.listings.models import Listing
from apps.messaging.services import start_direct_conversation

from .models import Deal, DealEvent, DealOffer, HandoffConfirmation

SELLER_RESPONSE_TIME = timedelta(hours=24)
HANDOFF_TIME = timedelta(hours=72)
MAX_AMOUNT_CENTS = 1_000_000
OPEN_STATUSES = {
    Deal.Status.AWAITING_SELLER,
    Deal.Status.AWAITING_BUYER,
    Deal.Status.BACKUP,
    Deal.Status.PENDING,
}


class DealStateError(Exception):
    def __init__(self, deal: Deal, action: str):
        self.deal_id = deal.pk
        self.status = deal.status
        super().__init__(f"Can't {action} deal {deal.pk}: it is {deal.get_status_display()}.")


def _event(deal: Deal, event_type: str, actor=None, **data) -> None:
    """Durable product event. Notifications can consume these later without deal logic
    calling the Notifications app directly."""
    DealEvent.objects.create(deal=deal, event_type=event_type, actor=actor, data=data)


def _schedule_expiry(deal: Deal, deadline, expected_status: str) -> None:
    from .tasks import expire_deal

    expire_deal.configure(schedule_at=deadline).defer(
        deal_id=deal.pk, expected_status=expected_status
    )


def _validate_amount(amount_cents: int) -> None:
    if not 1 <= amount_cents <= MAX_AMOUNT_CENTS:
        raise ValidationError(
            {"amount_cents": f"Amount must be between $0.01 and ${MAX_AMOUNT_CENTS // 100:,}."}
        )


@transaction.atomic
def create_deal(*, listing: Listing, buyer, kind: str, amount_cents: int | None = None) -> Deal:
    listing = Listing.objects.select_for_update().select_related("seller").get(pk=listing.pk)
    if listing.status != Listing.Status.AVAILABLE:
        raise ValidationError("This listing is no longer available.")
    if listing.seller_id == buyer.pk:
        raise ValidationError("You cannot buy your own listing.")
    if not verified_users().filter(pk=buyer.pk).exists():
        raise PermissionDenied("Your account must be active and verified to make a request.")
    if kind not in Deal.Kind.values:
        raise ValidationError({"kind": "Choose Buy now or Make offer."})
    if Deal.objects.filter(listing=listing, buyer=buyer, status__in=OPEN_STATUSES).exists():
        raise ValidationError("You already have an active request for this item.")

    if kind == Deal.Kind.BUY_NOW:
        amount_cents = listing.price_cents
    elif amount_cents is None:
        raise ValidationError({"amount_cents": "Enter your offer amount."})
    if kind == Deal.Kind.OFFER:
        _validate_amount(amount_cents)

    conversation = start_direct_conversation(sender=buyer, recipient=listing.seller)
    deadline = timezone.now() + SELLER_RESPONSE_TIME
    deal = Deal.objects.create(
        listing=listing,
        buyer=buyer,
        seller=listing.seller,
        conversation=conversation,
        kind=kind,
        status=Deal.Status.AWAITING_SELLER,
        current_amount_cents=amount_cents,
        currency=listing.currency,
        response_deadline=deadline,
    )
    DealOffer.objects.create(deal=deal, offered_by=buyer, amount_cents=amount_cents)
    _event(deal, "request_created", buyer, amount_cents=amount_cents, kind=kind)
    _schedule_expiry(deal, deadline, Deal.Status.AWAITING_SELLER)
    return deal


def _lock_deal(deal: Deal) -> Deal:
    """Lock listing before deal everywhere, matching Listings' lock order."""
    listing = Listing.objects.select_for_update().get(pk=deal.listing_id)
    locked = Deal.objects.select_for_update().select_related("listing").get(pk=deal.pk)
    locked.listing = listing
    return locked


def _require_party(deal: Deal, user) -> None:
    if user.pk not in {deal.buyer_id, deal.seller_id}:
        raise PermissionDenied("Only this deal's buyer or seller can do that.")


def _recipient(deal: Deal):
    if deal.status == Deal.Status.AWAITING_SELLER:
        return deal.seller_id
    if deal.status == Deal.Status.AWAITING_BUYER:
        return deal.buyer_id
    if deal.status == Deal.Status.BACKUP:
        return deal.seller_id
    return None


@transaction.atomic
def counter_offer(*, deal: Deal, actor, amount_cents: int) -> Deal:
    locked = _lock_deal(deal)
    _require_party(locked, actor)
    if locked.status not in {Deal.Status.AWAITING_SELLER, Deal.Status.AWAITING_BUYER}:
        raise DealStateError(locked, "counter")
    if actor.pk != _recipient(locked):
        raise PermissionDenied("Only the person responding to the current offer can counter it.")
    _validate_amount(amount_cents)

    locked.current_amount_cents = amount_cents
    locked.status = (
        Deal.Status.AWAITING_BUYER if actor.pk == locked.seller_id else Deal.Status.AWAITING_SELLER
    )
    locked.response_deadline = timezone.now() + SELLER_RESPONSE_TIME
    locked.save(update_fields=["current_amount_cents", "status", "response_deadline", "updated_at"])
    DealOffer.objects.create(deal=locked, offered_by=actor, amount_cents=amount_cents)
    _event(locked, "countered", actor, amount_cents=amount_cents)
    _schedule_expiry(locked, locked.response_deadline, locked.status)
    return locked


@transaction.atomic
def accept_deal(*, deal: Deal, actor) -> Deal:
    locked = _lock_deal(deal)
    _require_party(locked, actor)
    if locked.status not in {
        Deal.Status.AWAITING_SELLER,
        Deal.Status.AWAITING_BUYER,
        Deal.Status.BACKUP,
    }:
        raise DealStateError(locked, "accept")
    if actor.pk != _recipient(locked):
        raise PermissionDenied("Only the person responding to this request can accept it.")
    if locked.listing.status != Listing.Status.AVAILABLE:
        raise ValidationError("This listing already has a pending buyer.")

    listing_services.mark_pending(locked.listing)
    locked.status = Deal.Status.PENDING
    locked.agreed_amount_cents = locked.current_amount_cents
    locked.response_deadline = None
    locked.handoff_deadline = timezone.now() + HANDOFF_TIME
    locked.save(
        update_fields=[
            "status",
            "agreed_amount_cents",
            "response_deadline",
            "handoff_deadline",
            "updated_at",
        ]
    )
    _event(locked, "accepted", actor, amount_cents=locked.agreed_amount_cents)

    alternatives = (
        Deal.objects.filter(listing=locked.listing)
        .exclude(pk=locked.pk)
        .filter(Q(status=Deal.Status.AWAITING_SELLER) | Q(status=Deal.Status.AWAITING_BUYER))
    )
    for alternative in alternatives.select_for_update():
        alternative.status = Deal.Status.BACKUP
        alternative.response_deadline = None
        alternative.save(update_fields=["status", "response_deadline", "updated_at"])
        _event(alternative, "moved_to_backup")

    _schedule_expiry(locked, locked.handoff_deadline, Deal.Status.PENDING)
    return locked


@transaction.atomic
def decline_deal(*, deal: Deal, actor) -> Deal:
    locked = _lock_deal(deal)
    _require_party(locked, actor)
    if locked.status not in {
        Deal.Status.AWAITING_SELLER,
        Deal.Status.AWAITING_BUYER,
        Deal.Status.BACKUP,
    }:
        raise DealStateError(locked, "decline")
    if actor.pk != _recipient(locked):
        raise PermissionDenied("Only the person responding to this request can decline it.")
    locked.status = Deal.Status.DECLINED
    locked.response_deadline = None
    locked.save(update_fields=["status", "response_deadline", "updated_at"])
    _event(locked, "declined", actor)
    return locked


@transaction.atomic
def cancel_deal(*, deal: Deal, actor) -> Deal:
    locked = _lock_deal(deal)
    _require_party(locked, actor)
    if locked.status not in OPEN_STATUSES:
        raise DealStateError(locked, "cancel")
    if locked.status == Deal.Status.PENDING:
        if locked.confirmations.exists():
            raise ValidationError(
                "This handoff already has a confirmation, so it cannot be canceled automatically."
            )
        listing_services.return_to_available(locked.listing)
    locked.status = Deal.Status.CANCELED
    locked.response_deadline = None
    locked.handoff_deadline = None
    locked.save(update_fields=["status", "response_deadline", "handoff_deadline", "updated_at"])
    _event(locked, "canceled", actor)
    return locked


@transaction.atomic
def confirm_handoff(*, deal: Deal, actor) -> Deal:
    locked = _lock_deal(deal)
    _require_party(locked, actor)
    if locked.status != Deal.Status.PENDING:
        raise DealStateError(locked, "confirm handoff for")
    confirmation, created = HandoffConfirmation.objects.get_or_create(deal=locked, user=actor)
    if created:
        _event(locked, "handoff_confirmed", actor)
    if locked.confirmations.count() == 2:
        listing_services.mark_sold(locked.listing)
        locked.status = Deal.Status.COMPLETED
        locked.handoff_deadline = None
        locked.save(update_fields=["status", "handoff_deadline", "updated_at"])
        _event(locked, "completed")
        backups = Deal.objects.select_for_update().filter(
            listing=locked.listing, status=Deal.Status.BACKUP
        )
        for backup in backups:
            backup.status = Deal.Status.EXPIRED
            backup.save(update_fields=["status", "updated_at"])
            _event(backup, "closed_listing_sold")
    return locked


@transaction.atomic
def expire(*, deal_id: int, expected_status: str) -> None:
    deal = Deal.objects.filter(pk=deal_id).first()
    if deal is None:
        return
    locked = _lock_deal(deal)
    if locked.status != expected_status:
        return
    now = timezone.now()
    deadline = (
        locked.handoff_deadline
        if locked.status == Deal.Status.PENDING
        else locked.response_deadline
    )
    if deadline is None or deadline > now:
        return
    if locked.status == Deal.Status.PENDING:
        if locked.confirmations.exists():
            locked.handoff_deadline = None
            locked.save(update_fields=["handoff_deadline", "updated_at"])
            _event(locked, "confirmation_stalled")
            return
        listing_services.return_to_available(locked.listing)
    locked.status = Deal.Status.EXPIRED
    locked.response_deadline = None
    locked.handoff_deadline = None
    locked.save(update_fields=["status", "response_deadline", "handoff_deadline", "updated_at"])
    _event(locked, "expired")
