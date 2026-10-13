"""Deal state transitions for offers, full-price requests, and in-person handoffs."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.services import verified_users
from apps.listings import services as listing_services
from apps.listings.models import Listing
from apps.messaging.services import send_message, start_direct_conversation
from apps.notifications import services as notification_services
from apps.schools.models import MeetingSpot
from apps.trust import checks as trust_checks

from .models import (
    Deal,
    DealEvent,
    DealOffer,
    HandoffConfirmation,
    MeetupAvailabilityOverride,
    MeetupAvailabilityWindow,
    MeetupPreference,
    MeetupProposal,
    MeetupStatusUpdate,
)

SELLER_RESPONSE_TIME = timedelta(hours=24)
HANDOFF_TIME = timedelta(hours=72)
MAX_AMOUNT_CENTS = 1_000_000
MAX_TRADE_ITEMS = 5
MEETUP_SLOT = timedelta(minutes=30)
MEETUP_NOTICE = timedelta(hours=1)
LATE_MINUTES = {5, 10, 15}
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


def _local_zone() -> ZoneInfo:
    # Schools outside Eastern time will supply this once School gains a time-zone field.
    return ZoneInfo(settings.TIME_ZONE)


@transaction.atomic
def update_meetup_preferences(*, user, meeting_spot_ids, windows, overrides) -> MeetupPreference:
    if user.school_id is None:
        raise ValidationError(
            "Your account must belong to a school before setting meetup preferences."
        )
    spots = list(
        MeetingSpot.objects.filter(
            id__in=meeting_spot_ids,
            school_id=user.school_id,
            is_active=True,
        )
    )
    if len(spots) != len(set(meeting_spot_ids)):
        raise ValidationError({"meeting_spot_ids": "Choose active meetup spots from your school."})
    if not spots:
        raise ValidationError({"meeting_spot_ids": "Choose at least one meetup spot."})
    if not windows:
        raise ValidationError({"windows": "Add at least one usual availability window."})

    preference, _ = MeetupPreference.objects.select_for_update().get_or_create(user=user)
    preference.meeting_spots.set(spots)
    preference.availability_windows.all().delete()
    preference.availability_overrides.all().delete()
    MeetupAvailabilityWindow.objects.bulk_create(
        [MeetupAvailabilityWindow(preference=preference, **window) for window in windows]
    )
    MeetupAvailabilityOverride.objects.bulk_create(
        [MeetupAvailabilityOverride(preference=preference, **override) for override in overrides]
    )
    preference.save(update_fields=["updated_at"])
    return preference


def meetup_slots(*, seller, now=None, days: int = 4) -> list[datetime]:
    """Return seller-local half-hour starts after notice, bounded for pre-accept scheduling."""
    try:
        preference = seller.meetup_preference
    except MeetupPreference.DoesNotExist:
        return []
    zone = _local_zone()
    now = now or timezone.now()
    earliest = now + MEETUP_NOTICE
    latest = now + SELLER_RESPONSE_TIME + HANDOFF_TIME
    local_now = now.astimezone(zone)
    windows = list(preference.availability_windows.all())
    overrides = list(
        preference.availability_overrides.filter(
            date__gte=local_now.date(), date__lte=(local_now + timedelta(days=days)).date()
        )
    )
    by_date: dict = {}
    for override in overrides:
        by_date.setdefault(override.date, []).append(override)

    starts: list[datetime] = []
    for offset in range(days + 1):
        day = (local_now + timedelta(days=offset)).date()
        day_overrides = by_date.get(day)
        if day_overrides is not None:
            source = [item for item in day_overrides if not item.is_unavailable]
        else:
            source = [item for item in windows if item.weekday == day.weekday()]
        for window in source:
            if window.start_time is None or window.end_time is None:
                continue
            cursor = datetime.combine(day, window.start_time, tzinfo=zone)
            end = datetime.combine(day, window.end_time, tzinfo=zone)
            while cursor + MEETUP_SLOT <= end:
                utc_cursor = cursor.astimezone(UTC)
                if earliest <= utc_cursor <= latest:
                    starts.append(utc_cursor)
                cursor += MEETUP_SLOT
    return sorted(set(starts))


def _validate_meetup(*, deal: Deal, actor, meeting_spot: MeetingSpot, starts_at: datetime) -> None:
    _require_party(deal, actor)
    if meeting_spot.school_id != deal.listing.school_id or not meeting_spot.is_active:
        raise ValidationError({"meeting_spot_id": "Choose an active meetup spot for this school."})
    try:
        preference = deal.seller.meetup_preference
    except MeetupPreference.DoesNotExist as exc:
        raise ValidationError("The seller has not configured meetup preferences yet.") from exc
    if not preference.meeting_spots.filter(pk=meeting_spot.pk).exists():
        raise ValidationError({"meeting_spot_id": "Choose one of the seller's preferred spots."})
    if starts_at not in meetup_slots(seller=deal.seller):
        raise ValidationError(
            {"starts_at": "Choose one of the seller's currently available times."}
        )
    if deal.handoff_deadline is not None and starts_at > deal.handoff_deadline:
        raise ValidationError({"starts_at": "Choose a time before the handoff deadline."})


def _fresh_pending_meetups(deal: Deal) -> list[MeetupProposal]:
    return list(
        deal.meetup_proposals.filter(
            status=MeetupProposal.Status.PENDING, starts_at__gt=timezone.now()
        )
    )


def _close_pending_meetups(deal: Deal, status=MeetupProposal.Status.WITHDRAWN, exclude=None):
    pending = deal.meetup_proposals.filter(status=MeetupProposal.Status.PENDING)
    if exclude is not None:
        pending = pending.exclude(pk=exclude.pk)
    pending.update(status=status, responded_at=timezone.now())


@transaction.atomic
def propose_meetup(
    *, deal: Deal, actor, meeting_spot: MeetingSpot, starts_at: datetime
) -> MeetupProposal:
    locked = _lock_deal(deal)
    if locked.status not in {
        Deal.Status.AWAITING_SELLER,
        Deal.Status.AWAITING_BUYER,
        Deal.Status.PENDING,
    }:
        raise DealStateError(locked, "schedule meetup for")
    if locked.status != Deal.Status.PENDING:
        _require_can_negotiate(locked, actor)
    _validate_meetup(deal=locked, actor=actor, meeting_spot=meeting_spot, starts_at=starts_at)
    _close_pending_meetups(locked, MeetupProposal.Status.SUPERSEDED)
    proposal = MeetupProposal.objects.create(
        deal=locked,
        proposed_by=actor,
        meeting_spot=meeting_spot,
        starts_at=starts_at,
    )
    _event(
        locked,
        "meetup_proposed",
        actor,
        meetup_proposal_id=proposal.pk,
        meeting_spot_id=meeting_spot.pk,
        starts_at=starts_at.isoformat(),
    )
    if locked.status != Deal.Status.PENDING and actor.pk == _recipient(locked):
        # Suggesting another time while it's your turn is a counter: the other person
        # now answers it. The person waiting can only replace their own times.
        locked.status = (
            Deal.Status.AWAITING_BUYER
            if actor.pk == locked.seller_id
            else Deal.Status.AWAITING_SELLER
        )
        locked.response_deadline = timezone.now() + SELLER_RESPONSE_TIME
        locked.save(update_fields=["status", "response_deadline", "updated_at"])
        _event(locked, "countered_meetup", actor, meetup_proposal_id=proposal.pk)
        _schedule_expiry(locked, locked.response_deadline, locked.status)
    return proposal


def _accept_meetup(
    *, deal: Deal, proposal: MeetupProposal, actor, allow_own: bool = False
) -> MeetupProposal:
    if proposal.deal_id != deal.pk or proposal.status != MeetupProposal.Status.PENDING:
        raise ValidationError("This meetup proposal is no longer available.")
    if proposal.proposed_by_id == actor.pk and not allow_own:
        raise PermissionDenied("The other person must accept this meetup proposal.")
    if proposal.starts_at <= timezone.now():
        raise ValidationError("That meetup time has passed. Suggest a new time.")
    if deal.handoff_deadline is not None and proposal.starts_at > deal.handoff_deadline:
        raise ValidationError("That meetup time is after the handoff deadline. Suggest a new time.")
    deal.meetup_proposals.filter(status=MeetupProposal.Status.ACCEPTED).update(
        status=MeetupProposal.Status.SUPERSEDED,
        responded_at=timezone.now(),
    )
    _close_pending_meetups(deal, MeetupProposal.Status.SUPERSEDED, exclude=proposal)
    proposal.status = MeetupProposal.Status.ACCEPTED
    proposal.responded_at = timezone.now()
    proposal.save(update_fields=["status", "responded_at"])
    _event(deal, "meetup_accepted", actor, meetup_proposal_id=proposal.pk)
    return proposal


@transaction.atomic
def accept_meetup(*, deal: Deal, actor, proposal: MeetupProposal) -> MeetupProposal:
    locked = _lock_deal(deal)
    _require_party(locked, actor)
    if locked.status != Deal.Status.PENDING:
        raise DealStateError(locked, "accept meetup for")
    return _accept_meetup(deal=locked, proposal=proposal, actor=actor)


@transaction.atomic
def meetup_status(*, deal: Deal, actor, kind: str, minutes_late: int | None = None):
    locked = _lock_deal(deal)
    _require_party(locked, actor)
    if locked.status != Deal.Status.PENDING:
        raise DealStateError(locked, "update meetup for")
    if not locked.meetup_proposals.filter(status=MeetupProposal.Status.ACCEPTED).exists():
        raise ValidationError("Confirm a meetup before sending an arrival update.")
    if kind == MeetupStatusUpdate.Kind.RUNNING_LATE:
        if minutes_late not in LATE_MINUTES:
            raise ValidationError({"minutes_late": "Choose 5, 10, or 15 minutes."})
    elif kind == MeetupStatusUpdate.Kind.ARRIVED:
        minutes_late = None
    else:
        raise ValidationError({"kind": "Choose Running late or Arrived."})
    update = MeetupStatusUpdate.objects.create(
        deal=locked,
        actor=actor,
        kind=kind,
        minutes_late=minutes_late,
    )
    _event(locked, "meetup_status_updated", actor, kind=kind, minutes_late=minutes_late)
    return update


def _event(deal: Deal, event_type: str, actor=None, **data) -> None:
    """Durable product event. Notifications can consume these later without deal logic
    calling the Notifications app directly."""
    DealEvent.objects.create(deal=deal, event_type=event_type, actor=actor, data=data)


def _schedule_expiry(deal: Deal, deadline, expected_status: str) -> None:
    from .tasks import expire_deal

    expire_deal.configure(schedule_at=deadline).defer(
        deal_id=deal.pk, expected_status=expected_status
    )


def _dollars(amount_cents: int) -> str:
    dollars, cents = divmod(amount_cents, 100)
    return f"${dollars:,}.{cents:02d}"


def _validate_amount(amount_cents: int) -> None:
    if not 1 <= amount_cents <= MAX_AMOUNT_CENTS:
        raise ValidationError(
            {"amount_cents": f"Amount must be between $0.01 and ${MAX_AMOUNT_CENTS // 100:,}."}
        )


@transaction.atomic
def create_deal(
    *,
    listing: Listing,
    buyer,
    kind: str,
    amount_cents: int | None = None,
    meeting_spot: MeetingSpot | None = None,
    proposed_starts_at: list[datetime] | None = None,
    asap: bool = False,
) -> Deal:
    listing = Listing.objects.select_for_update().select_related("seller").get(pk=listing.pk)
    if listing.status != Listing.Status.AVAILABLE:
        raise ValidationError("This listing is no longer available.")
    if listing.seller_id == buyer.pk:
        raise ValidationError("You cannot buy your own listing.")
    if not verified_users().filter(pk=buyer.pk).exists():
        raise PermissionDenied("Your account must be active and verified to make a request.")
    trust_checks.require_can(buyer, trust_checks.Kind.DEALS)
    trust_checks.require_not_blocked(buyer, listing.seller)
    if listing.seller_id in set(trust_checks.hidden_seller_ids().values_list("user_id", flat=True)):
        raise ValidationError("This listing isn't available right now.")
    if kind not in Deal.Kind.values:
        raise ValidationError({"kind": "Choose Buy now, Make offer, or Trade."})
    if Deal.objects.filter(listing=listing, buyer=buyer, status__in=OPEN_STATUSES).exists():
        raise ValidationError("You already have an active request for this item.")

    if kind == Deal.Kind.BUY_NOW:
        amount_cents = listing.price_cents
    elif kind == Deal.Kind.TRADE:
        # The seller builds the first package from the buyer's listings.
        amount_cents = 0
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
        asap=asap,
        response_deadline=deadline,
    )
    if kind != Deal.Kind.TRADE:
        DealOffer.objects.create(deal=deal, offered_by=buyer, amount_cents=amount_cents)
    _event(deal, "request_created", buyer, amount_cents=amount_cents, kind=kind, asap=asap)
    amount = _dollars(amount_cents)
    if kind == Deal.Kind.TRADE:
        message = (
            "Wants to trade for this item. Look through their listings and pick what you'd take."
        )
    elif kind == Deal.Kind.OFFER:
        message = f"Made an offer of {amount} for this item."
    else:
        message = f"Sent a request to buy this item for {amount}."
    if asap:
        message += " They'd like to meet as soon as possible."
    send_message(
        conversation=conversation,
        sender=buyer,
        body=message,
        listing=listing,
        automated=True,
    )
    proposed_starts_at = proposed_starts_at or []
    if meeting_spot is not None:
        for starts_at in proposed_starts_at:
            _validate_meetup(
                deal=deal,
                actor=buyer,
                meeting_spot=meeting_spot,
                starts_at=starts_at,
            )
            proposal = MeetupProposal.objects.create(
                deal=deal,
                proposed_by=buyer,
                meeting_spot=meeting_spot,
                starts_at=starts_at,
            )
            _event(
                deal,
                "meetup_proposed",
                buyer,
                meetup_proposal_id=proposal.pk,
                meeting_spot_id=meeting_spot.pk,
                starts_at=starts_at.isoformat(),
            )
    _schedule_expiry(deal, deadline, Deal.Status.AWAITING_SELLER)
    return deal


def _lock_deal(deal: Deal) -> Deal:
    """Lock listing before deal everywhere, matching Listings' lock order."""
    listing = Listing.objects.select_for_update().get(pk=deal.listing_id)
    locked = Deal.objects.select_for_update().select_related("listing").get(pk=deal.pk)
    locked.listing = listing
    return locked


def _require_can_negotiate(deal: Deal, actor) -> None:
    """Making, answering, or countering a request needs deal privileges, and the seller side
    also needs selling privileges. Finishing a Pending deal (meetup, handoff, cancel) doesn't,
    so a restriction never strands the other student mid-handoff."""
    trust_checks.require_can(actor, trust_checks.Kind.DEALS)
    if actor.pk == deal.seller_id:
        trust_checks.require_can(actor, trust_checks.Kind.SELLING)


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
def counter_offer(
    *, deal: Deal, actor, amount_cents: int, meetup_proposal: MeetupProposal | None = None
) -> Deal:
    locked = _lock_deal(deal)
    _require_party(locked, actor)
    if locked.status not in {Deal.Status.AWAITING_SELLER, Deal.Status.AWAITING_BUYER}:
        raise DealStateError(locked, "counter")
    if actor.pk != _recipient(locked):
        raise PermissionDenied("Only the person responding to the current offer can counter it.")
    _require_can_negotiate(locked, actor)
    if locked.kind == Deal.Kind.TRADE:
        raise ValidationError("Counter a trade with a new trade offer.")
    _validate_amount(amount_cents)
    _keep_one_meetup(locked, meetup_proposal)

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


def _keep_one_meetup(deal: Deal, meetup_proposal: MeetupProposal | None) -> None:
    """A counter keeps one proposed time on the table, so accepting it later also confirms
    the meetup."""
    fresh = _fresh_pending_meetups(deal)
    if meetup_proposal is not None:
        if meetup_proposal.pk not in {proposal.pk for proposal in fresh}:
            raise ValidationError("That meetup time is no longer available. Suggest a new time.")
        _close_pending_meetups(deal, MeetupProposal.Status.SUPERSEDED, exclude=meetup_proposal)
    elif len(fresh) > 1:
        raise ValidationError("Choose which proposed meetup time to keep with your counter.")


def trade_items(deal: Deal) -> list[Listing]:
    """The buyer's items in a trade's latest package (empty before the seller picks)."""
    if deal.kind != Deal.Kind.TRADE:
        return []
    offer = deal.offers.order_by("-created_at", "-id").first()
    return list(offer.trade_items.all()) if offer else []


def tradable_listings(deal: Deal):
    """The buyer's listings that can go into a trade package for this deal."""
    return Listing.objects.filter(
        seller_id=deal.buyer_id, kind=deal.listing.kind, status=Listing.Status.AVAILABLE
    ).exclude(pk=deal.listing_id)


@transaction.atomic
def counter_trade(
    *,
    deal: Deal,
    actor,
    item_ids: list[int],
    cash_cents: int = 0,
    cash_payer: str = "",
    meetup_proposal: MeetupProposal | None = None,
) -> Deal:
    """Offer a trade package: some of the buyer's items, plus cash from either side. The seller
    sends the first one; after that each side can counter with a different package."""
    locked = _lock_deal(deal)
    _require_party(locked, actor)
    if locked.kind != Deal.Kind.TRADE:
        raise ValidationError("Only trade requests take a trade offer.")
    if locked.status not in {Deal.Status.AWAITING_SELLER, Deal.Status.AWAITING_BUYER}:
        raise DealStateError(locked, "counter")
    if actor.pk != _recipient(locked):
        raise PermissionDenied("Only the person responding to the current offer can counter it.")
    _require_can_negotiate(locked, actor)

    item_ids = list(dict.fromkeys(item_ids))
    if not item_ids:
        raise ValidationError({"trade_item_ids": "Choose at least one item for the trade."})
    if len(item_ids) > MAX_TRADE_ITEMS:
        raise ValidationError(
            {"trade_item_ids": f"A trade can include up to {MAX_TRADE_ITEMS} items."}
        )
    items = list(tradable_listings(locked).filter(pk__in=item_ids))
    if len(items) != len(item_ids):
        raise ValidationError({"trade_item_ids": "Choose items the buyer still has available."})
    if cash_cents < 0 or cash_cents > MAX_AMOUNT_CENTS:
        raise ValidationError({"cash_cents": "Enter an amount between $0 and $10,000."})
    if cash_cents and cash_payer not in DealOffer.CashPayer.values:
        raise ValidationError({"cash_payer": "Choose who adds the cash."})
    cash_payer = cash_payer if cash_cents else ""
    _keep_one_meetup(locked, meetup_proposal)

    locked.current_amount_cents = cash_cents
    locked.status = (
        Deal.Status.AWAITING_BUYER if actor.pk == locked.seller_id else Deal.Status.AWAITING_SELLER
    )
    locked.response_deadline = timezone.now() + SELLER_RESPONSE_TIME
    locked.save(update_fields=["current_amount_cents", "status", "response_deadline", "updated_at"])
    offer = DealOffer.objects.create(
        deal=locked, offered_by=actor, amount_cents=cash_cents, cash_payer=cash_payer
    )
    offer.trade_items.set(items)
    _event(
        locked,
        "trade_offered",
        actor,
        trade_item_ids=[item.pk for item in items],
        cash_cents=cash_cents,
        cash_payer=cash_payer,
    )
    _schedule_expiry(locked, locked.response_deadline, locked.status)
    return locked


def _move_open_requests_to_backup(listing: Listing, *, exclude: Deal) -> None:
    alternatives = (
        Deal.objects.filter(listing=listing)
        .exclude(pk=exclude.pk)
        .filter(Q(status=Deal.Status.AWAITING_SELLER) | Q(status=Deal.Status.AWAITING_BUYER))
    )
    for alternative in alternatives.select_for_update():
        alternative.status = Deal.Status.BACKUP
        alternative.response_deadline = None
        alternative.save(update_fields=["status", "response_deadline", "updated_at"])
        _event(alternative, "moved_to_backup")


@transaction.atomic
def accept_deal(*, deal: Deal, actor, meetup_proposal: MeetupProposal | None = None) -> Deal:
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
    _require_can_negotiate(locked, actor)
    if locked.listing.status != Listing.Status.AVAILABLE:
        raise ValidationError("This listing already has a pending buyer.")
    items = trade_items(locked)
    if locked.kind == Deal.Kind.TRADE:
        if not items:
            raise ValidationError("Choose items for the trade before accepting.")
        locked_items = Listing.objects.select_for_update().filter(pk__in=[i.pk for i in items])
        if any(item.status != Listing.Status.AVAILABLE for item in locked_items):
            raise ValidationError(
                "One of the trade items is no longer available. Send a new trade offer."
            )
    # Accepting the price confirms the meetup. Any pending time from the person accepting
    # was already answered by the other side with a price counter, so it counts as agreed.
    if meetup_proposal is None:
        fresh = _fresh_pending_meetups(locked)
        if len(fresh) == 1:
            meetup_proposal = fresh[0]
        elif fresh:
            raise ValidationError("Choose one of the proposed meetup times.")
        elif locked.meetup_proposals.filter(status=MeetupProposal.Status.PENDING).exists():
            raise ValidationError(
                "The proposed meetup times have passed. Suggest a new time before accepting."
            )

    listing_services.mark_pending(locked.listing)
    for item in items:
        listing_services.mark_pending(item)
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

    if meetup_proposal is not None:
        _accept_meetup(deal=locked, proposal=meetup_proposal, actor=actor, allow_own=True)

    # Every item changing hands is now spoken for, including the buyer's trade items.
    for listing in [locked.listing, *items]:
        _move_open_requests_to_backup(listing, exclude=locked)

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
    _close_pending_meetups(locked)
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
        for listing in [locked.listing, *trade_items(locked)]:
            listing_services.return_to_available(listing)
    locked.status = Deal.Status.CANCELED
    locked.response_deadline = None
    locked.handoff_deadline = None
    locked.save(update_fields=["status", "response_deadline", "handoff_deadline", "updated_at"])
    _close_pending_meetups(locked)
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
        # A trade's items change hands too, so they're sold along with the listing.
        sold = [locked.listing, *trade_items(locked)]
        for listing in sold:
            listing_services.mark_sold(listing)
        locked.status = Deal.Status.COMPLETED
        locked.handoff_deadline = None
        locked.save(update_fields=["status", "handoff_deadline", "updated_at"])
        _close_pending_meetups(locked)
        _event(locked, "completed")
        backups = Deal.objects.select_for_update().filter(
            listing__in=sold, status=Deal.Status.BACKUP
        )
        for backup in backups:
            backup.status = Deal.Status.EXPIRED
            backup.save(update_fields=["status", "updated_at"])
            _close_pending_meetups(backup)
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
        for listing in [locked.listing, *trade_items(locked)]:
            listing_services.return_to_available(listing)
    locked.status = Deal.Status.EXPIRED
    locked.response_deadline = None
    locked.handoff_deadline = None
    locked.save(update_fields=["status", "response_deadline", "handoff_deadline", "updated_at"])
    _close_pending_meetups(locked)
    _event(locked, "expired")


# --- Moderation (called by Trust, never by students) ---


@transaction.atomic
def cancel_for_moderation(*, deal: Deal, reason: str, announce: bool = True) -> Deal:
    """Cancel an open deal because of a moderation action, releasing every listing it holds.
    Unlike cancel_deal, this also cancels a Pending deal after a handoff confirmation.

    With `announce`, both students are told Tanu canceled it. A block passes False: the deal
    just shows as canceled, so the blocked student isn't told they were blocked."""
    locked = _lock_deal(deal)
    if locked.status not in OPEN_STATUSES:
        return locked
    if locked.status == Deal.Status.PENDING:
        for listing in [locked.listing, *trade_items(locked)]:
            if listing.status == Listing.Status.PENDING:
                listing_services.return_to_available(listing)
    locked.status = Deal.Status.CANCELED
    locked.response_deadline = None
    locked.handoff_deadline = None
    locked.save(update_fields=["status", "response_deadline", "handoff_deadline", "updated_at"])
    _close_pending_meetups(locked)
    if not announce:
        _event(locked, "canceled")
        return locked
    _event(locked, "canceled_by_moderation", reason=reason)
    for user in (locked.buyer, locked.seller):
        notification_services.notify(
            user,
            kind=notification_services.Kind.DEAL,
            title="A deal was canceled by Tanu",
            body=(
                f"Your deal for “{locked.listing.title}” was canceled after a moderation "
                "review. Any items in it are available again."
            ),
            link="/deals",
        )
    return locked


def _open_deals_holding(listing: Listing):
    """Open deals for this listing, plus open trades whose current package includes it."""
    direct = list(Deal.objects.filter(listing=listing, status__in=OPEN_STATUSES))
    trades = Deal.objects.filter(
        kind=Deal.Kind.TRADE, status__in=OPEN_STATUSES, offers__trade_items=listing
    ).distinct()
    in_package = [deal for deal in trades if listing in trade_items(deal)]
    return direct + [deal for deal in in_package if deal not in direct]


def cancel_deals_for_listing(listing: Listing, *, reason: str) -> None:
    for deal in _open_deals_holding(listing):
        cancel_for_moderation(deal=deal, reason=reason)


def cancel_deals_for_user(user, *, reason: str) -> None:
    for deal in Deal.objects.filter(Q(buyer=user) | Q(seller=user), status__in=OPEN_STATUSES):
        cancel_for_moderation(deal=deal, reason=reason)


def cancel_deals_between(first, second, *, reason: str, announce: bool = True) -> None:
    pair = Q(buyer=first, seller=second) | Q(buyer=second, seller=first)
    for deal in Deal.objects.filter(pair, status__in=OPEN_STATUSES):
        cancel_for_moderation(deal=deal, reason=reason, announce=announce)
