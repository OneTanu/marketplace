"""Deal state machine: requests, offers, trades, backups, handoffs and disputes.

Every status change goes through _transition(), which refuses any move not in TRANSITIONS and
records who made it, when, and the status before and after (a DealEvent). Deals are never
deleted; canceled, declined and expired ones stay as history.

    awaiting_seller  -> awaiting_buyer   seller counters (price, trade package or meetup time)
    awaiting_buyer   -> awaiting_seller  buyer counters
    awaiting_*       -> pending          the person whose turn it is accepts (before the
                                         24-hour response deadline, listing still Available)
    awaiting_*       -> declined         the person whose turn it is declines
    awaiting_*       -> canceled         either side withdraws
    awaiting_*       -> expired          the 24-hour response deadline passes (system)
    awaiting_*       -> backup           another buyer's deal for the listing is accepted
    backup           -> awaiting_seller  promoted, first in queue, when the listing comes back
    backup           -> declined         the seller takes them off the queue
    backup           -> canceled         the buyer withdraws, or can no longer deal (system)
    backup           -> expired          the listing sold (system)
    pending          -> completed        both sides confirmed the handoff
    pending          -> canceled         either side cancels before any confirmation, or
                                         reports a no-show before any confirmation
    pending          -> expired          72 hours pass with no confirmation (system)
    pending          -> disputed         72 hours pass with one confirmation (system), or a
                                         problem is reported after a confirmation
    disputed         -> completed        a moderator decides the handoff happened
    disputed         -> canceled         a moderator decides it didn't
    any open status  -> canceled         moderation (a removed listing, a ban, a block)

The listing follows: Available -> Pending on acceptance; Pending -> Sold only on completion
(two confirmations or a moderator's decision); Pending -> Available when a pending deal is
canceled or expires. A disputed deal keeps its listing Pending until a moderator decides.

Deadlines are enforced twice: background jobs settle them on time, and every action first
settles a passed deadline (in its own transaction, so it sticks even though the action is then
refused) and re-checks it under the row lock.

Concurrency: actions lock the listing row, then the deal row (Listings' order). A partial
unique constraint allows one pending or disputed deal per listing, so two primary buyers are
impossible even if a code path forgets the lock.
"""

from datetime import UTC, datetime, timedelta
from functools import wraps
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Max, Q
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
    DealDispute,
    DealEvent,
    DealOffer,
    DealProblem,
    HandoffConfirmation,
    MeetupAvailabilityOverride,
    MeetupAvailabilityWindow,
    MeetupPreference,
    MeetupProposal,
    MeetupStatusUpdate,
)

SELLER_RESPONSE_TIME = timedelta(hours=24)
HANDOFF_TIME = timedelta(hours=72)
# A reschedule both sides agree to can push the handoff deadline out once, by up to 48 hours,
# so rescheduling can't hold a listing indefinitely.
MAX_HANDOFF_EXTENSIONS = 1
MAX_HANDOFF_EXTENSION = timedelta(hours=48)
# After an agreed meetup, time left to confirm the handoff before the deadline.
HANDOFF_CONFIRM_GRACE = timedelta(hours=2)
# An unanswered meetup proposal lapses after this (or at its start time, if sooner).
MEETUP_PROPOSAL_TTL = timedelta(hours=24)
MAX_AMOUNT_CENTS = 1_000_000
MAX_TRADE_ITEMS = 5
MEETUP_SLOT = timedelta(minutes=30)
MEETUP_NOTICE = timedelta(hours=1)
LATE_MINUTES = {5, 10, 15}
# A repeated identical arrival update within this window is the same update.
STATUS_UPDATE_REPEAT = timedelta(minutes=1)

S = Deal.Status
NEGOTIATING = {S.AWAITING_SELLER, S.AWAITING_BUYER}
OPEN_STATUSES = {S.AWAITING_SELLER, S.AWAITING_BUYER, S.BACKUP, S.PENDING, S.DISPUTED}
CLOSED_STATUSES = {S.CANCELED, S.DECLINED, S.EXPIRED}

TRANSITIONS: dict[str, set[str]] = {
    S.AWAITING_SELLER: {S.AWAITING_BUYER, S.PENDING, S.DECLINED, S.CANCELED, S.EXPIRED, S.BACKUP},
    S.AWAITING_BUYER: {S.AWAITING_SELLER, S.PENDING, S.DECLINED, S.CANCELED, S.EXPIRED, S.BACKUP},
    S.BACKUP: {S.AWAITING_SELLER, S.DECLINED, S.CANCELED, S.EXPIRED},
    S.PENDING: {S.COMPLETED, S.CANCELED, S.EXPIRED, S.DISPUTED},
    S.DISPUTED: {S.COMPLETED, S.CANCELED},
    S.COMPLETED: set(),
    S.CANCELED: set(),
    S.DECLINED: set(),
    S.EXPIRED: set(),
}


class DealStateError(Exception):
    def __init__(self, deal: Deal, action: str, why: str = ""):
        self.deal_id = deal.pk
        self.status = deal.status
        why = why or f"it is {deal.get_status_display()}"
        super().__init__(f"Can't {action} deal {deal.pk}: {why}.")


def _local_zone() -> ZoneInfo:
    # Schools outside Eastern time will supply this once School gains a time-zone field.
    return ZoneInfo(settings.TIME_ZONE)


# --- Meetup preferences and slots ---


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


# --- Building blocks ---


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
    """Whose turn it is: the person who answers the current request or counteroffer."""
    if deal.status == S.AWAITING_SELLER:
        return deal.seller_id
    if deal.status == S.AWAITING_BUYER:
        return deal.buyer_id
    return None


def _other_party_id(deal: Deal, user_id: int) -> int:
    return deal.seller_id if user_id == deal.buyer_id else deal.buyer_id


def _deadline(deal: Deal):
    if deal.status in NEGOTIATING:
        return deal.response_deadline
    if deal.status == S.PENDING:
        return deal.handoff_deadline
    return None


def _is_due(deal: Deal, now=None) -> bool:
    deadline = _deadline(deal)
    return deadline is not None and deadline <= (now or timezone.now())


def _refuse_if_due(deal: Deal, action: str) -> None:
    """Deadlines hold at request time, not only when the job runs."""
    if _is_due(deal):
        window = "handoff" if deal.status == S.PENDING else "response"
        raise DealStateError(deal, action, f"its {window} window has closed")


def _event(deal: Deal, event_type: str, actor=None, *, from_status="", to_status="", **data):
    event = DealEvent.objects.create(
        deal=deal,
        event_type=event_type,
        actor=actor,
        from_status=from_status,
        to_status=to_status,
        data=data,
    )
    _notify_event(deal, event)
    return event


def _transition(
    deal: Deal,
    to: str,
    event_type: str,
    actor=None,
    *,
    action: str = "",
    close_reason: str = "",
    fields=(),
    **data,
) -> DealEvent:
    """Move a locked deal to `to`, if TRANSITIONS allows it, saving `fields` too, and record
    the change. Final statuses also record when, by whom and why the deal closed."""
    if to not in TRANSITIONS[deal.status]:
        raise DealStateError(deal, action or event_type.replace("_", " "))
    from_status = deal.status
    deal.status = to
    update = {"status", "updated_at", *fields}
    now = timezone.now()
    if to == S.COMPLETED:
        deal.completed_at = now
        update.add("completed_at")
    if to in CLOSED_STATUSES:
        deal.closed_at, deal.closed_by_id = now, getattr(actor, "pk", None)
        deal.close_reason = close_reason or event_type
        update |= {"closed_at", "closed_by", "close_reason"}
    if to not in NEGOTIATING:
        deal.response_deadline = None
        update.add("response_deadline")
    if to not in {S.PENDING}:
        deal.handoff_deadline = None
        update.add("handoff_deadline")
    if to != S.BACKUP:
        deal.backup_position = None
        update.add("backup_position")
    deal.save(update_fields=sorted(update))
    if to in CLOSED_STATUSES | {S.COMPLETED}:
        _close_pending_meetups(deal)
    return _event(deal, event_type, actor, from_status=from_status, to_status=to, **data)


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


def settles_deadline(function):
    """Run an action after settling any passed deadline on its deal. The settling commits on
    its own, so an action refused for being late still leaves the deal expired (or disputed)
    rather than waiting for the job."""

    @wraps(function)
    def wrapper(*, deal: Deal, **kwargs):
        settle_deadline(deal_id=deal.pk)
        with transaction.atomic():
            return function(deal=deal, **kwargs)

    return wrapper


# --- Meetups ---


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
        if not _can_extend_to(deal, starts_at):
            raise ValidationError({"starts_at": _extension_refusal(deal)})


def _can_extend_to(deal: Deal, starts_at: datetime) -> bool:
    """Whether an agreed meetup at `starts_at` may push the handoff deadline out."""
    return (
        deal.handoff_deadline is not None
        and deal.handoff_extensions < MAX_HANDOFF_EXTENSIONS
        and starts_at <= deal.handoff_deadline + MAX_HANDOFF_EXTENSION
    )


def _extension_refusal(deal: Deal) -> str:
    if deal.handoff_extensions >= MAX_HANDOFF_EXTENSIONS:
        return "The handoff deadline was already extended once. Choose a time before it."
    hours = int(MAX_HANDOFF_EXTENSION.total_seconds() // 3600)
    return f"Choose a time no more than {hours} hours after the handoff deadline."


def _proposal_expires_at(starts_at: datetime) -> datetime:
    return min(timezone.now() + MEETUP_PROPOSAL_TTL, starts_at)


def _fresh_pending_meetups(deal: Deal) -> list[MeetupProposal]:
    now = timezone.now()
    return list(
        deal.meetup_proposals.filter(status=MeetupProposal.Status.PENDING, starts_at__gt=now)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .order_by("created_at", "id")
    )


def _close_pending_meetups(deal: Deal, status=MeetupProposal.Status.WITHDRAWN, exclude=None):
    pending = deal.meetup_proposals.filter(status=MeetupProposal.Status.PENDING)
    if exclude is not None:
        pending = pending.exclude(pk=exclude.pk)
    pending.update(status=status, responded_at=timezone.now())


@settles_deadline
def propose_meetup(
    *, deal: Deal, actor, meeting_spot: MeetingSpot, starts_at: datetime
) -> MeetupProposal:
    """Suggest a meetup. While negotiating, a time from the person whose turn it is counts as a
    counter. On a Pending deal it's a reschedule: the confirmed meetup stays until the other
    person accepts the new one."""
    locked = _lock_deal(deal)
    _require_party(locked, actor)
    if locked.status not in NEGOTIATING | {S.PENDING}:
        raise DealStateError(locked, "schedule meetup for")
    _refuse_if_due(locked, "schedule meetup for")
    repeat = locked.meetup_proposals.filter(
        status=MeetupProposal.Status.PENDING,
        proposed_by=actor,
        meeting_spot=meeting_spot,
        starts_at=starts_at,
    ).first()
    if repeat is not None:
        return repeat
    if locked.status != S.PENDING:
        _require_can_negotiate(locked, actor)
    if locked.meetup_proposals.filter(
        status=MeetupProposal.Status.ACCEPTED, meeting_spot=meeting_spot, starts_at=starts_at
    ).exists():
        raise ValidationError({"starts_at": "That's already the confirmed meetup."})
    _validate_meetup(deal=locked, actor=actor, meeting_spot=meeting_spot, starts_at=starts_at)
    _close_pending_meetups(locked, MeetupProposal.Status.SUPERSEDED)
    proposal = MeetupProposal.objects.create(
        deal=locked,
        proposed_by=actor,
        meeting_spot=meeting_spot,
        starts_at=starts_at,
        expires_at=_proposal_expires_at(starts_at),
    )
    _event(
        locked,
        "meetup_proposed",
        actor,
        meetup_proposal_id=proposal.pk,
        meeting_spot_id=meeting_spot.pk,
        starts_at=starts_at.isoformat(),
        reschedule=locked.status == S.PENDING,
    )
    if locked.status in NEGOTIATING and actor.pk == _recipient(locked):
        # Suggesting another time while it's your turn is a counter: the other person
        # now answers it. The person waiting can only replace their own times.
        turn = S.AWAITING_BUYER if actor.pk == locked.seller_id else S.AWAITING_SELLER
        locked.response_deadline = timezone.now() + SELLER_RESPONSE_TIME
        _transition(
            locked,
            turn,
            "countered_meetup",
            actor,
            fields=["response_deadline"],
            meetup_proposal_id=proposal.pk,
        )
        _schedule_expiry(locked, locked.response_deadline, locked.status)
    return proposal


def _accept_meetup(
    *, deal: Deal, proposal: MeetupProposal, actor, allow_own: bool = False
) -> MeetupProposal:
    if proposal.deal_id != deal.pk or proposal.status != MeetupProposal.Status.PENDING:
        raise ValidationError("This meetup proposal is no longer available.")
    if proposal.proposed_by_id == actor.pk and not allow_own:
        raise PermissionDenied("The other person must accept this meetup proposal.")
    now = timezone.now()
    if proposal.starts_at <= now:
        raise ValidationError("That meetup time has passed. Suggest a new time.")
    if proposal.expires_at is not None and proposal.expires_at <= now:
        raise ValidationError("That meetup suggestion expired. Suggest a new time.")
    extends = deal.handoff_deadline is not None and proposal.starts_at > deal.handoff_deadline
    if extends and not _can_extend_to(deal, proposal.starts_at):
        raise ValidationError(_extension_refusal(deal))
    # Only now is the old meetup replaced: until both agree, the confirmed one stands.
    deal.meetup_proposals.filter(status=MeetupProposal.Status.ACCEPTED).update(
        status=MeetupProposal.Status.SUPERSEDED,
        responded_at=now,
    )
    _close_pending_meetups(deal, MeetupProposal.Status.SUPERSEDED, exclude=proposal)
    proposal.status = MeetupProposal.Status.ACCEPTED
    proposal.responded_at = now
    proposal.save(update_fields=["status", "responded_at"])
    # When it's confirmed by accepting the deal itself, the acceptance is the news.
    _event(deal, "meetup_accepted", actor, meetup_proposal_id=proposal.pk, quiet=allow_own)
    if extends:
        previous = deal.handoff_deadline
        deal.handoff_deadline = proposal.starts_at + HANDOFF_CONFIRM_GRACE
        deal.handoff_extensions += 1
        deal.save(update_fields=["handoff_deadline", "handoff_extensions", "updated_at"])
        _event(
            deal,
            "handoff_extended",
            actor,
            previous_deadline=previous.isoformat(),
            handoff_deadline=deal.handoff_deadline.isoformat(),
        )
        _schedule_expiry(deal, deal.handoff_deadline, S.PENDING)
    return proposal


@settles_deadline
def accept_meetup(*, deal: Deal, actor, proposal: MeetupProposal) -> MeetupProposal:
    locked = _lock_deal(deal)
    _require_party(locked, actor)
    proposal.refresh_from_db()
    if (
        proposal.deal_id == locked.pk
        and proposal.status == MeetupProposal.Status.ACCEPTED
        and proposal.proposed_by_id != actor.pk
    ):
        return proposal  # already accepted
    if locked.status != S.PENDING:
        raise DealStateError(locked, "accept meetup for")
    _refuse_if_due(locked, "accept meetup for")
    return _accept_meetup(deal=locked, proposal=proposal, actor=actor)


@settles_deadline
def meetup_status(*, deal: Deal, actor, kind: str, minutes_late: int | None = None):
    locked = _lock_deal(deal)
    _require_party(locked, actor)
    if locked.status != S.PENDING:
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
    repeat = locked.meetup_updates.filter(
        actor=actor,
        kind=kind,
        minutes_late=minutes_late,
        created_at__gte=timezone.now() - STATUS_UPDATE_REPEAT,
    ).first()
    if repeat is not None:
        return repeat
    update = MeetupStatusUpdate.objects.create(
        deal=locked,
        actor=actor,
        kind=kind,
        minutes_late=minutes_late,
    )
    _event(locked, "meetup_status_updated", actor, kind=kind, minutes_late=minutes_late)
    return update


# --- Requests and negotiation ---


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
    """A buyer's request. Sending the same request again returns the open one; a different
    request while one is open is refused."""
    listing = Listing.objects.select_for_update().select_related("seller").get(pk=listing.pk)
    if kind not in Deal.Kind.values:
        raise ValidationError({"kind": "Choose Buy now, Make offer, or Trade."})
    existing = Deal.objects.filter(listing=listing, buyer=buyer, status__in=OPEN_STATUSES).first()
    if existing is not None:
        same_amount = kind != Deal.Kind.OFFER or existing.current_amount_cents == amount_cents
        if existing.kind == kind and same_amount and existing.offers.count() <= 1:
            return existing
        raise ValidationError("You already have an active request for this item.")
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
        status=S.AWAITING_SELLER,
        current_amount_cents=amount_cents,
        currency=listing.currency,
        asap=asap,
        response_deadline=deadline,
    )
    if kind != Deal.Kind.TRADE:
        DealOffer.objects.create(deal=deal, offered_by=buyer, amount_cents=amount_cents)
    _event(
        deal,
        "request_created",
        buyer,
        to_status=S.AWAITING_SELLER,
        amount_cents=amount_cents,
        kind=kind,
        asap=asap,
    )
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
                expires_at=_proposal_expires_at(starts_at),
            )
            DealEvent.objects.create(
                deal=deal,
                event_type="meetup_proposed",
                actor=buyer,
                data={
                    "meetup_proposal_id": proposal.pk,
                    "meeting_spot_id": meeting_spot.pk,
                    "starts_at": starts_at.isoformat(),
                },
            )
    _schedule_expiry(deal, deadline, S.AWAITING_SELLER)
    return deal


def _counter_turn(deal: Deal, actor) -> str:
    return S.AWAITING_BUYER if actor.pk == deal.seller_id else S.AWAITING_SELLER


def _latest_offer(deal: Deal) -> DealOffer | None:
    return deal.offers.order_by("-created_at", "-id").first()


@settles_deadline
def counter_offer(
    *, deal: Deal, actor, amount_cents: int, meetup_proposal: MeetupProposal | None = None
) -> Deal:
    locked = _lock_deal(deal)
    _require_party(locked, actor)
    latest = _latest_offer(locked)
    if (
        locked.status == _counter_turn(locked, actor)
        and latest is not None
        and latest.offered_by_id == actor.pk
        and latest.amount_cents == amount_cents
    ):
        return locked  # the same counter, sent again
    if locked.status not in NEGOTIATING:
        raise DealStateError(locked, "counter")
    _refuse_if_due(locked, "counter")
    if actor.pk != _recipient(locked):
        raise PermissionDenied("Only the person responding to the current offer can counter it.")
    _require_can_negotiate(locked, actor)
    if locked.kind == Deal.Kind.TRADE:
        raise ValidationError("Counter a trade with a new trade offer.")
    _validate_amount(amount_cents)
    _keep_one_meetup(locked, meetup_proposal)

    locked.current_amount_cents = amount_cents
    locked.response_deadline = timezone.now() + SELLER_RESPONSE_TIME
    DealOffer.objects.create(deal=locked, offered_by=actor, amount_cents=amount_cents)
    _transition(
        locked,
        _counter_turn(locked, actor),
        "countered",
        actor,
        fields=["current_amount_cents", "response_deadline"],
        amount_cents=amount_cents,
    )
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
    offer = _latest_offer(deal)
    return list(offer.trade_items.all()) if offer else []


def tradable_listings(deal: Deal):
    """The buyer's listings that can go into a trade package for this deal."""
    return Listing.objects.filter(
        seller_id=deal.buyer_id, kind=deal.listing.kind, status=Listing.Status.AVAILABLE
    ).exclude(pk=deal.listing_id)


@settles_deadline
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
    item_ids = list(dict.fromkeys(item_ids))
    cash_payer = cash_payer if cash_cents else ""
    latest = _latest_offer(locked)
    if (
        locked.status == _counter_turn(locked, actor)
        and latest is not None
        and latest.offered_by_id == actor.pk
        and latest.amount_cents == cash_cents
        and latest.cash_payer == cash_payer
        and sorted(latest.trade_items.values_list("pk", flat=True)) == sorted(item_ids)
    ):
        return locked  # the same package, sent again
    if locked.status not in NEGOTIATING:
        raise DealStateError(locked, "counter")
    _refuse_if_due(locked, "counter")
    if actor.pk != _recipient(locked):
        raise PermissionDenied("Only the person responding to the current offer can counter it.")
    _require_can_negotiate(locked, actor)

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
    _keep_one_meetup(locked, meetup_proposal)

    locked.current_amount_cents = cash_cents
    locked.response_deadline = timezone.now() + SELLER_RESPONSE_TIME
    offer = DealOffer.objects.create(
        deal=locked, offered_by=actor, amount_cents=cash_cents, cash_payer=cash_payer
    )
    offer.trade_items.set(items)
    _transition(
        locked,
        _counter_turn(locked, actor),
        "trade_offered",
        actor,
        fields=["current_amount_cents", "response_deadline"],
        trade_item_ids=[item.pk for item in items],
        cash_cents=cash_cents,
        cash_payer=cash_payer,
    )
    _schedule_expiry(locked, locked.response_deadline, locked.status)
    return locked


# --- Acceptance and the backup queue ---


def _move_open_requests_to_backup(listing: Listing, *, exclude: Deal) -> None:
    """Other open requests for a listing that's now spoken for join its backup queue, in the
    order they were made, after anyone already queued."""
    alternatives = (
        Deal.objects.filter(listing=listing, status__in=NEGOTIATING)
        .exclude(pk=exclude.pk)
        .order_by("created_at", "id")
        .select_for_update()
    )
    last = Deal.objects.filter(listing=listing, status=S.BACKUP).aggregate(
        last=Max("backup_position")
    )["last"]
    position = last or 0
    for alternative in alternatives:
        position += 1
        alternative.backup_position = position
        _transition(
            alternative,
            S.BACKUP,
            "moved_to_backup",
            fields=["backup_position"],
            backup_position=position,
        )


def _backup_is_eligible(backup: Deal) -> bool:
    buyer = backup.buyer
    return (
        verified_users().filter(pk=buyer.pk).exists()
        and not trust_checks.has_active(buyer, trust_checks.Kind.DEALS)
        and not trust_checks.active_restrictions(buyer)
        .filter(kind__in=[trust_checks.Kind.SUSPENSION, trust_checks.Kind.BAN])
        .exists()
        and not trust_checks.is_blocked(buyer, backup.seller)
    )


def _promote_next_backup(listing: Listing) -> Deal | None:
    """When a listing is Available again, offer it to the first backup buyer in line (and only
    one): their request goes back to the seller with a fresh 24 hours. Backups who can't deal
    any more are closed and skipped. Call with the listing row locked."""
    if listing.status != Listing.Status.AVAILABLE:
        return None
    seller_hidden = trust_checks.hidden_seller_ids().filter(user_id=listing.seller_id).exists()
    if seller_hidden:
        return None
    promoted_open = Deal.objects.filter(
        listing=listing, status__in=NEGOTIATING, events__event_type="promoted_from_backup"
    ).exists()
    if promoted_open:
        return None  # someone from the queue already has their turn
    queue = (
        Deal.objects.filter(listing=listing, status=S.BACKUP)
        .select_related("buyer", "seller")
        .order_by("backup_position", "created_at", "id")
        .select_for_update()
    )
    for backup in queue:
        if not _backup_is_eligible(backup):
            _transition(backup, S.CANCELED, "backup_closed", close_reason="backup_ineligible")
            continue
        backup.response_deadline = timezone.now() + SELLER_RESPONSE_TIME
        _transition(
            backup,
            S.AWAITING_SELLER,
            "promoted_from_backup",
            fields=["response_deadline"],
        )
        _schedule_expiry(backup, backup.response_deadline, S.AWAITING_SELLER)
        return backup
    return None


def _release(deal: Deal) -> None:
    """A pending or disputed deal let go of its listings: they're Available again, and each
    offers itself to its next backup buyer."""
    for listing in [deal.listing, *trade_items(deal)]:
        locked = Listing.objects.select_for_update().get(pk=listing.pk)
        if locked.status == Listing.Status.PENDING:
            listing_services.return_to_available(locked)
        _promote_next_backup(locked)


@settles_deadline
def accept_deal(*, deal: Deal, actor, meetup_proposal: MeetupProposal | None = None) -> Deal:
    locked = _lock_deal(deal)
    _require_party(locked, actor)
    if locked.status in {S.PENDING, S.COMPLETED} and locked.accepted_by_id == actor.pk:
        return locked  # already accepted
    if locked.status == S.BACKUP:
        raise DealStateError(
            locked, "accept", "backup buyers are offered the item in line, when it comes back"
        )
    if locked.status not in NEGOTIATING:
        raise DealStateError(locked, "accept")
    _refuse_if_due(locked, "accept")
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
    now = timezone.now()
    locked.agreed_amount_cents = locked.current_amount_cents
    locked.handoff_deadline = now + HANDOFF_TIME
    locked.accepted_at, locked.accepted_by = now, actor
    try:
        with transaction.atomic():
            _transition(
                locked,
                S.PENDING,
                "accepted",
                actor,
                fields=["agreed_amount_cents", "handoff_deadline", "accepted_at", "accepted_by"],
                amount_cents=locked.agreed_amount_cents,
            )
    except IntegrityError as exc:  # deals_one_holder_per_listing: another buyer got there
        raise ValidationError("This listing already has a pending buyer.") from exc

    if meetup_proposal is not None:
        _accept_meetup(deal=locked, proposal=meetup_proposal, actor=actor, allow_own=True)

    # Every item changing hands is now spoken for, including the buyer's trade items.
    for listing in [locked.listing, *items]:
        _move_open_requests_to_backup(listing, exclude=locked)

    _schedule_expiry(locked, locked.handoff_deadline, S.PENDING)
    return locked


@settles_deadline
def decline_deal(*, deal: Deal, actor) -> Deal:
    locked = _lock_deal(deal)
    _require_party(locked, actor)
    if locked.status == S.DECLINED and locked.closed_by_id == actor.pk:
        return locked
    if locked.status not in NEGOTIATING | {S.BACKUP}:
        raise DealStateError(locked, "decline")
    if locked.status == S.BACKUP:
        if actor.pk != locked.seller_id:
            raise PermissionDenied("Only the seller can take someone off the backup queue.")
    else:
        _refuse_if_due(locked, "decline")
        if actor.pk != _recipient(locked):
            raise PermissionDenied("Only the person responding to this request can decline it.")
    _transition(locked, S.DECLINED, "declined", actor)
    _promote_next_backup(locked.listing)
    return locked


@settles_deadline
def cancel_deal(*, deal: Deal, actor) -> Deal:
    """Either side can walk away until the handoff is confirmed by anyone:

    - Before acceptance (or from the backup queue): the request is withdrawn.
    - After acceptance, before any confirmation: the listing (and any trade items) are
      Available again and offered to the next backup buyer.
    - After one confirmation: refused. Report a problem instead, and a moderator decides.
    """
    locked = _lock_deal(deal)
    _require_party(locked, actor)
    if locked.status == S.CANCELED and locked.closed_by_id == actor.pk:
        return locked
    if locked.status == S.DISPUTED:
        raise DealStateError(locked, "cancel", "a moderator is reviewing this handoff")
    if locked.status not in NEGOTIATING | {S.BACKUP, S.PENDING}:
        raise DealStateError(locked, "cancel")
    if locked.status == S.PENDING and locked.confirmations.exists():
        raise ValidationError(
            "This handoff already has a confirmation, so it can't be canceled. If something "
            "went wrong, report a problem and a moderator will review it."
        )
    was_pending = locked.status == S.PENDING
    _transition(locked, S.CANCELED, "canceled", actor)
    if was_pending:
        _release(locked)
    else:
        _promote_next_backup(locked.listing)
    return locked


# --- Handoff ---


@settles_deadline
def confirm_handoff(*, deal: Deal, actor) -> Deal:
    """Each side confirms the item changed hands. The second confirmation completes the deal
    and marks the listing (and any trade items) Sold; one confirmation alone never does."""
    locked = _lock_deal(deal)
    _require_party(locked, actor)
    mine = locked.confirmations.filter(user=actor).exists()
    if locked.status == S.COMPLETED and mine:
        return locked
    if locked.status == S.DISPUTED:
        raise DealStateError(locked, "confirm handoff for", "a moderator is reviewing it")
    if locked.status != S.PENDING:
        raise DealStateError(locked, "confirm handoff for")
    _refuse_if_due(locked, "confirm handoff for")
    if mine:
        return locked
    if locked.problems.filter(reporter=actor).exists():
        raise ValidationError(
            "You reported a problem with this handoff. A moderator will review it."
        )
    HandoffConfirmation.objects.create(deal=locked, user=actor)
    completes = locked.confirmations.count() == 2
    # The second confirmation completes the deal, so "confirm yours" would be stale.
    _event(locked, "handoff_confirmed", actor, quiet=completes)
    if completes:
        _complete(locked)
    return locked


def _complete(locked: Deal, actor=None, **data) -> None:
    # A trade's items change hands too, so they're sold along with the listing.
    sold = [locked.listing, *trade_items(locked)]
    for listing in sold:
        listing_services.mark_sold(Listing.objects.select_for_update().get(pk=listing.pk))
    _transition(locked, S.COMPLETED, "completed", actor, **data)
    backups = (
        Deal.objects.select_for_update()
        .filter(listing__in=sold, status__in=[S.BACKUP, *NEGOTIATING])
        .order_by("id")
    )
    for backup in backups:
        _transition(backup, S.EXPIRED, "closed_listing_sold", close_reason="listing_sold")


# --- Deadlines (jobs and request time) ---


@transaction.atomic
def expire(*, deal_id: int, expected_status: str | None = None) -> None:
    """Settle a passed deadline. Safe to run any number of times, early or late: it acts only
    if the deal is still in `expected_status` (when given) and its deadline has passed.

    - A request nobody answered in 24 hours expires.
    - A pending handoff with no confirmation after 72 hours expires; its listings come back.
    - A pending handoff with one confirmation goes to a moderator as a dispute: Tanu doesn't
      guess whether it happened.
    """
    deal = Deal.objects.filter(pk=deal_id).first()
    if deal is None:
        return
    locked = _lock_deal(deal)
    if expected_status is not None and locked.status != expected_status:
        return
    if not _is_due(locked):
        return
    if locked.status == S.PENDING:
        confirmed = list(locked.confirmations.values_list("user_id", flat=True))
        if confirmed:
            _open_dispute(
                locked,
                DealDispute.Reason.ONE_SIDED_CONFIRMATION,
                subject_id=_other_party_id(locked, confirmed[0]),
            )
            return
        _transition(locked, S.EXPIRED, "expired", close_reason="handoff_deadline")
        _release(locked)
        return
    _transition(locked, S.EXPIRED, "expired", close_reason="response_deadline")
    _promote_next_backup(locked.listing)


def settle_deadline(*, deal_id: int) -> None:
    expire(deal_id=deal_id)


SWEEP_BATCH = 200


def settle_due_deals() -> int:
    """Settle every open deal whose deadline has passed (the periodic sweep). Each deal is
    settled in its own transaction; returns how many were looked at."""
    now = timezone.now()
    due = Deal.objects.filter(
        Q(status__in=NEGOTIATING, response_deadline__lte=now)
        | Q(status=S.PENDING, handoff_deadline__lte=now)
    ).values_list("pk", flat=True)[:SWEEP_BATCH]
    ids = list(due)
    for deal_id in ids:
        expire(deal_id=deal_id)
    return len(ids)


# --- Problems and disputes ---

# What each kind of problem is reported to moderation as.
PROBLEM_REPORT_REASONS = {
    DealProblem.Kind.NO_SHOW: "no_show",
    DealProblem.Kind.NOT_AS_DESCRIBED: "misleading_listing",
    DealProblem.Kind.PAYMENT: "scam",
    DealProblem.Kind.SAFETY: "unsafe_meetup",
    DealProblem.Kind.OTHER: "other",
}


@settles_deadline
def report_problem(*, deal: Deal, actor, kind: str, details: str = "") -> DealProblem:
    """The buyer or seller reports a problem with an accepted deal. It always goes to
    moderation as a deal report (with a snapshot); it never punishes anyone by itself. What it
    does to the deal depends on where the handoff stands:

    - Nobody confirmed yet and it's a no-show: the reporter is out, as if they canceled.
    - Nobody confirmed yet, any other problem: the deal stays pending (either side can cancel).
    - Someone confirmed: the deal is disputed and a moderator decides.
    - Already disputed or completed: the report is added for the moderator.
    """
    if kind not in DealProblem.Kind.values:
        raise ValidationError({"kind": "Choose what went wrong."})
    details = details.strip()
    if len(details) > 1000:
        raise ValidationError({"details": "Keep details under 1,000 characters."})
    locked = _lock_deal(deal)
    _require_party(locked, actor)
    existing = locked.problems.filter(reporter=actor, kind=kind).first()
    if existing is not None:
        return existing
    if locked.status not in {S.PENDING, S.DISPUTED, S.COMPLETED}:
        raise DealStateError(
            locked, "report a problem with", "problems can be reported once a deal is accepted"
        )
    status_then = locked.status
    report, case = _file_report(locked, actor, kind, details)
    problem = DealProblem.objects.create(
        deal=locked,
        reporter=actor,
        kind=kind,
        details=details,
        deal_status=status_then,
        report=report,
        case=case,
    )
    _event(locked, "problem_reported", actor, kind=kind, problem_id=problem.pk)
    if locked.status == S.PENDING:
        if locked.confirmations.exists():
            dispute = _open_dispute(
                locked,
                DealDispute.Reason.PROBLEM_AFTER_CONFIRMATION,
                opened_by=actor,
                subject_id=_other_party_id(locked, actor.pk),
            )
            if problem.case_id is None:
                problem.case_id = dispute.case_id
                problem.save(update_fields=["case"])
        elif kind == DealProblem.Kind.NO_SHOW:
            _transition(locked, S.CANCELED, "canceled", actor, close_reason="no_show_reported")
            _release(locked)
    return problem


def _file_report(deal: Deal, reporter, kind: str, details: str):
    """Send the problem to moderation as a deal report. If the student can't file another
    report right now (already reported this deal, or the daily limit), the deal still reaches a
    moderator through its case."""
    from apps.trust import services as trust_services
    from apps.trust.models import Report

    try:
        with transaction.atomic():
            report = trust_services.create_report(
                reporter=reporter,
                target_type=Report.TargetType.DEAL,
                target_id=deal.pk,
                reason=PROBLEM_REPORT_REASONS[kind],
                details=details,
            )
        return report, report.case
    except ValidationError:
        open_report = Report.objects.filter(
            reporter=reporter, deal=deal, status=Report.Status.OPEN
        ).first()
        if open_report is not None:
            return open_report, open_report.case
        case = trust_services.open_case_for_deal(
            deal=deal, subject_user=deal.seller if reporter.pk == deal.buyer_id else deal.buyer
        )
        return None, case


def _snapshot(deal: Deal) -> dict:
    listing = deal.listing
    details = getattr(listing, "item_details", None)
    return {
        "deal": {
            "id": deal.pk,
            "kind": deal.kind,
            "status": deal.status,
            "buyer": deal.buyer.username,
            "seller": deal.seller.username,
            "agreed_amount_cents": deal.agreed_amount_cents,
            "currency": deal.currency,
            "accepted_at": deal.accepted_at.isoformat() if deal.accepted_at else None,
            "confirmed_by": [
                {"user_id": c.user_id, "at": c.confirmed_at.isoformat()}
                for c in deal.confirmations.all()
            ],
            "trade_item_ids": [item.pk for item in trade_items(deal)],
        },
        "listing": {
            "id": listing.pk,
            "title": listing.title,
            "price_cents": listing.price_cents,
            "status": listing.status,
            "condition": getattr(details, "condition", ""),
            "brand": getattr(details, "brand", ""),
        },
        "meetups": [
            {
                "spot": p.meeting_spot.name,
                "starts_at": p.starts_at.isoformat(),
                "status": p.status,
                "proposed_by_id": p.proposed_by_id,
            }
            for p in deal.meetup_proposals.select_related("meeting_spot")
        ],
        "problems": [
            {"reporter_id": p.reporter_id, "kind": p.kind, "details": p.details}
            for p in deal.problems.all()
        ],
        "events": [
            {"type": e.event_type, "actor_id": e.actor_id, "at": e.created_at.isoformat()}
            for e in deal.events.all()
        ],
    }


def _open_dispute(locked: Deal, reason: str, *, opened_by=None, subject_id: int) -> DealDispute:
    """Hold a pending deal for a moderator. The listing stays Pending until they decide."""
    from apps.trust import services as trust_services

    subject = locked.buyer if subject_id == locked.buyer_id else locked.seller
    snapshot = _snapshot(locked)  # as it stood, before the status changes
    case = trust_services.open_case_for_deal(deal=locked, subject_user=subject)
    _transition(locked, S.DISPUTED, "disputed", opened_by, reason=reason)
    return DealDispute.objects.create(
        deal=locked, reason=reason, opened_by=opened_by, case=case, snapshot=snapshot
    )


@transaction.atomic
def resolve_dispute(*, deal: Deal, staff, outcome: str, note: str) -> Deal:
    """A moderator's decision on a disputed handoff (Trust checks they may make it): it
    happened (Completed, listing Sold) or it didn't (Canceled, listing Available and offered to
    the next backup). Deciding again with the same outcome changes nothing."""
    locked = _lock_deal(deal)
    dispute = DealDispute.objects.select_for_update().get(deal=locked)
    if dispute.outcome:
        if dispute.outcome == outcome:
            return locked
        raise DealStateError(locked, "resolve", "the dispute was already decided")
    if outcome not in DealDispute.Outcome.values:
        raise ValidationError({"outcome": "Choose whether the handoff happened."})
    if locked.status != S.DISPUTED:
        raise DealStateError(locked, "resolve")
    dispute.outcome = outcome
    dispute.resolved_by = staff
    dispute.resolved_at = timezone.now()
    dispute.resolution_note = note
    dispute.save(update_fields=["outcome", "resolved_by", "resolved_at", "resolution_note"])
    if outcome == DealDispute.Outcome.COMPLETED:
        _complete(locked, staff, decided_by_moderator=True)
    else:
        _transition(
            locked,
            S.CANCELED,
            "canceled",
            staff,
            close_reason="dispute_canceled",
            decided_by_moderator=True,
        )
        _release(locked)
    _event(locked, "dispute_resolved", staff, outcome=outcome)
    return locked


# --- Archiving ---


# Closed deals that go straight to Archived: nobody walked away, it just didn't happen.
AUTO_ARCHIVED = {S.DECLINED, S.EXPIRED}


@transaction.atomic
def set_archived(*, deal: Deal, actor, archived: bool) -> Deal:
    """Move a canceled deal into or out of the actor's Archived activity. Only hides it from
    their own Cancelled list; nothing is deleted. Declined and expired deals are always in
    Archived, and completed ones always in Transaction History."""
    locked = Deal.objects.select_for_update().get(pk=deal.pk)
    _require_party(locked, actor)
    if locked.status != S.CANCELED:
        raise DealStateError(locked, "archive", "only canceled deals can be archived")
    field = "buyer_archived_at" if actor.pk == locked.buyer_id else "seller_archived_at"
    current = getattr(locked, field)
    if archived and current is None:
        setattr(locked, field, timezone.now())
    elif not archived and current is not None:
        setattr(locked, field, None)
    else:
        return locked
    locked.save(update_fields=[field])
    return locked


def section_for(deal: Deal, user) -> str:
    """Where a deal goes in the user's activity:

    - current: still open, including backups and disputes under review
    - history: completed purchases, sales and trades, and nothing else
    - cancelled: canceled deals (until the user archives them)
    - archived: declined and expired deals, plus canceled ones the user archived
    """
    if deal.status in OPEN_STATUSES:
        return "current"
    if deal.status == S.COMPLETED:
        return "history"
    if deal.status in AUTO_ARCHIVED:
        return "archived"
    archived = deal.buyer_archived_at if user.pk == deal.buyer_id else deal.seller_archived_at
    return "archived" if archived else "cancelled"


def _archived_by(user) -> Q:
    return Q(buyer=user, buyer_archived_at__isnull=False) | Q(
        seller=user, seller_archived_at__isnull=False
    )


SECTION_FILTERS = {
    "current": lambda user: Q(status__in=OPEN_STATUSES),
    "history": lambda user: Q(status=S.COMPLETED),
    "cancelled": lambda user: Q(status=S.CANCELED) & ~_archived_by(user),
    "archived": lambda user: (
        Q(status__in=AUTO_ARCHIVED) | (Q(status=S.CANCELED) & _archived_by(user))
    ),
}


# --- Notifications ---


def _title(deal: Deal) -> str:
    return f"“{deal.listing.title}”"


def _name(user) -> str:
    return f"@{user.username}" if user else "Tanu"


# event type -> (who hears about it, title, body). "other" is the party who didn't act;
# "both" is buyer and seller. Bodies say what to do next.
DEAL_NOTIFICATIONS = {
    "request_created": (
        "seller",
        "New request for {item}",
        "{actor} wants it. Reply within 24 hours.",
    ),
    "countered": (
        "other",
        "New counteroffer on {item}",
        "{actor} countered. Reply within 24 hours.",
    ),
    "trade_offered": (
        "other",
        "New trade offer for {item}",
        "{actor} sent a trade package. Reply within 24 hours.",
    ),
    "countered_meetup": (
        "other",
        "New meetup time for {item}",
        "{actor} suggested another time. Reply within 24 hours.",
    ),
    "accepted": (
        "other",
        "Deal accepted for {item}",
        "Meet up and both confirm the handoff within 72 hours.",
    ),
    "declined": (
        "other",
        "Request declined for {item}",
        "{actor} declined.",
    ),
    "canceled": (
        "other",
        "Deal canceled for {item}",
        "{actor} canceled.",
    ),
    "expired": (
        "both",
        "Deal expired for {item}",
        "The time to respond or hand off ran out.",
    ),
    "moved_to_backup": (
        "buyer",
        "You're a backup buyer for {item}",
        "Someone else's deal was accepted. If it falls through, you're next in line.",
    ),
    "promoted_from_backup": (
        "both",
        "Backup buyer's turn for {item}",
        (
            "The item is available again and goes to the next buyer in line. The seller has "
            "24 hours to reply."
        ),
    ),
    "backup_closed": (
        "buyer",
        "Backup request closed for {item}",
        "Your place in line for this item was closed.",
    ),
    "closed_listing_sold": (
        "buyer",
        "{item} sold",
        "It went to another buyer.",
    ),
    "handoff_confirmed": (
        "other",
        "Confirm your handoff for {item}",
        ("{actor} confirmed the handoff. Confirm yours once you have the item or payment."),
    ),
    "completed": (
        "both",
        "Handoff complete for {item}",
        "Both of you confirmed. You can leave a review.",
    ),
    "disputed": (
        "both",
        "A moderator will review {item}",
        (
            "The handoff couldn't be settled automatically. The listing stays on hold until "
            "Tanu decides."
        ),
    ),
    "dispute_resolved": (
        "both",
        "Review finished for {item}",
        "A moderator decided the handoff. Check the deal for the outcome.",
    ),
    "problem_reported": (
        "other",
        "A problem was reported with {item}",
        "Tanu's team will review it. No action is taken until they do.",
    ),
    "meetup_proposed": (
        "other",
        "New meetup suggestion for {item}",
        "{actor} suggested a time. The current meetup stands until you accept.",
    ),
    "meetup_accepted": (
        "other",
        "Meetup confirmed for {item}",
        "{actor} accepted the meetup time.",
    ),
    "handoff_extended": (
        "both",
        "Handoff deadline extended for {item}",
        "The new meetup time moved the deadline. It can only be extended once.",
    ),
    "canceled_by_moderation": (
        "both",
        "A deal was canceled by Tanu",
        (
            "Your deal for {item} was canceled after a moderation review. Any items in it "
            "are available again."
        ),
    ),
}


def _notify_event(deal: Deal, event: DealEvent) -> None:
    """One notification per recipient per event (keyed on the event), so retried jobs and
    repeated requests never notify twice."""
    spec = DEAL_NOTIFICATIONS.get(event.event_type)
    if spec is None:
        return
    if event.data.get("quiet"):
        return
    if event.event_type == "meetup_proposed" and not event.data.get("reschedule"):
        return  # negotiation-time suggestions arrive as counters
    who, title, body = spec
    if who == "other":
        if event.actor_id is None:
            return
        recipients = [_other_party_id(deal, event.actor_id)]
    elif who == "both":
        recipients = [deal.buyer_id, deal.seller_id]
    else:
        recipients = [deal.buyer_id if who == "buyer" else deal.seller_id]
    values = {"item": _title(deal), "actor": _name(event.actor)}
    for user_id in recipients:
        notification_services.notify(
            deal.buyer if user_id == deal.buyer_id else deal.seller,
            kind=notification_services.Kind.DEAL,
            title=title.format(**values),
            body=body.format(**values),
            link="/deals",
            dedupe_key=f"deal-event:{event.pk}",
        )


# --- Moderation (called by Trust, never by students) ---


@transaction.atomic
def cancel_for_moderation(
    *, deal: Deal, reason: str, announce: bool = True, promote_backups: bool = True
) -> Deal:
    """Cancel an open deal because of a moderation action, releasing every listing it holds.
    Unlike cancel_deal, this also cancels a Pending deal after a handoff confirmation, and a
    disputed one.

    With `announce`, both students are told Tanu canceled it. A block passes False: the deal
    just shows as canceled, so the blocked student isn't told they were blocked."""
    locked = _lock_deal(deal)
    if locked.status not in OPEN_STATUSES:
        return locked
    held = locked.status in {S.PENDING, S.DISPUTED}
    if announce:
        _transition(
            locked,
            S.CANCELED,
            "canceled_by_moderation",
            close_reason="moderation",
            reason=reason,
        )
    else:
        _transition(locked, S.CANCELED, "canceled_quietly", close_reason="moderation")
    if held:
        for listing in [locked.listing, *trade_items(locked)]:
            item = Listing.objects.select_for_update().get(pk=listing.pk)
            if item.status == Listing.Status.PENDING:
                listing_services.return_to_available(item)
            if promote_backups:
                _promote_next_backup(item)
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
    # The listing is about to be removed, so nobody is promoted from its queue.
    for deal in _open_deals_holding(listing):
        cancel_for_moderation(deal=deal, reason=reason, promote_backups=False)


def cancel_deals_for_user(user, *, reason: str) -> None:
    for deal in Deal.objects.filter(Q(buyer=user) | Q(seller=user), status__in=OPEN_STATUSES):
        cancel_for_moderation(deal=deal, reason=reason)


def cancel_deals_between(first, second, *, reason: str, announce: bool = True) -> None:
    pair = Q(buyer=first, seller=second) | Q(buyer=second, seller=first)
    for deal in Deal.objects.filter(pair, status__in=OPEN_STATUSES):
        cancel_for_moderation(deal=deal, reason=reason, announce=announce)
