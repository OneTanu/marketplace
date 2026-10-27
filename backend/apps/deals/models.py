from django.conf import settings
from django.db import models
from django.db.models import Q

# Statuses in which a deal is still in progress (see services.TRANSITIONS).
OPEN_STATUSES = ["awaiting_seller", "awaiting_buyer", "backup", "pending", "disputed"]
# A deal that holds its listing: at most one per listing.
HOLDING_STATUSES = ["pending", "disputed"]


class Deal(models.Model):
    """A buyer's request for a listing, from first offer to handoff. Status only changes in
    services.py, which records each change as a DealEvent (who, when, from, to). Deals are
    never deleted: canceled and expired ones stay as history."""

    class Kind(models.TextChoices):
        BUY_NOW = "buy_now", "Buy now"
        OFFER = "offer", "Offer"
        TRADE = "trade", "Trade"

    class Status(models.TextChoices):
        AWAITING_SELLER = "awaiting_seller", "Awaiting seller"
        AWAITING_BUYER = "awaiting_buyer", "Awaiting buyer"
        BACKUP = "backup", "Backup"
        PENDING = "pending", "Pending handoff"
        # The handoff is contested (one-sided confirmation, or a problem reported after a
        # confirmation). The listing stays held until a moderator decides.
        DISPUTED = "disputed", "Under review"
        COMPLETED = "completed", "Completed"
        CANCELED = "canceled", "Canceled"
        DECLINED = "declined", "Declined"
        EXPIRED = "expired", "Expired"

    listing = models.ForeignKey("listings.Listing", on_delete=models.PROTECT, related_name="deals")
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="buying_deals"
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="selling_deals"
    )
    conversation = models.ForeignKey(
        "messaging.Conversation", on_delete=models.PROTECT, related_name="deals"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    status = models.CharField(max_length=30, choices=Status.choices)
    current_amount_cents = models.PositiveIntegerField()
    agreed_amount_cents = models.PositiveIntegerField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="USD")
    # The buyer asked to meet as soon as possible. Only shown to the seller; no rules change.
    asap = models.BooleanField(default=False)
    response_deadline = models.DateTimeField(null=True, blank=True)
    handoff_deadline = models.DateTimeField(null=True, blank=True)
    # How many times an agreed reschedule pushed the handoff deadline out (capped).
    handoff_extensions = models.PositiveSmallIntegerField(default=0)
    # Place in the listing's backup queue (lower goes first); null unless status is BACKUP.
    backup_position = models.PositiveIntegerField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    # When and by whom the deal reached a final status other than Completed. A null actor
    # with a closed_at means the system (a deadline, or the listing selling elsewhere).
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    close_reason = models.CharField(max_length=40, blank=True)
    # Each side can tidy closed deals out of their list; nothing is deleted.
    buyer_archived_at = models.DateTimeField(null=True, blank=True)
    seller_archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(buyer=models.F("seller")), name="deals_buyer_is_not_seller"
            ),
            models.UniqueConstraint(
                fields=["listing", "buyer"],
                condition=Q(status__in=OPEN_STATUSES),
                name="deals_one_active_per_buyer_listing",
            ),
            # One primary buyer per listing, whatever races the application lets through.
            models.UniqueConstraint(
                fields=["listing"],
                condition=Q(status__in=HOLDING_STATUSES),
                name="deals_one_holder_per_listing",
            ),
        ]
        indexes = [
            models.Index(fields=["seller", "status", "-updated_at"], name="deal_seller_status_idx"),
            models.Index(fields=["buyer", "status", "-updated_at"], name="deal_buyer_status_idx"),
        ]

    def __str__(self):
        return f"Deal {self.pk} for listing {self.listing_id}"


class DealOffer(models.Model):
    """One round of a negotiation. For a trade it's a whole package: the buyer's items the
    seller would get, plus `amount_cents` of cash paid by `cash_payer` (blank when no cash)."""

    class CashPayer(models.TextChoices):
        BUYER = "buyer", "Buyer"
        SELLER = "seller", "Seller"

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="offers")
    offered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="deal_offers"
    )
    amount_cents = models.PositiveIntegerField()
    trade_items = models.ManyToManyField(
        "listings.Listing", blank=True, related_name="trade_offers"
    )
    cash_payer = models.CharField(max_length=10, choices=CashPayer.choices, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"Offer {self.pk} on deal {self.deal_id}"


class HandoffConfirmation(models.Model):
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="confirmations")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="handoff_confirmations"
    )
    confirmed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["deal", "user"], name="deals_one_confirmation_per_user")
        ]

    def __str__(self):
        return f"Handoff confirmation by {self.user_id} on deal {self.deal_id}"


class DealEvent(models.Model):
    """The deal's audit trail: one row per meaningful change, with who did it (null for the
    system) and, for status changes, the status before and after."""

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=50)
    from_status = models.CharField(max_length=30, blank=True)
    to_status = models.CharField(max_length=30, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deal_events",
    )
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.event_type} on deal {self.deal_id}"


class MeetupPreference(models.Model):
    """A seller's reusable handoff settings. Locations remain school-curated."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="meetup_preference",
    )
    meeting_spots = models.ManyToManyField(
        "schools.MeetingSpot",
        related_name="preferred_by",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Meetup preferences for {self.user_id}"


class MeetupAvailabilityWindow(models.Model):
    """A recurring local-time availability window for a seller."""

    preference = models.ForeignKey(
        MeetupPreference,
        on_delete=models.CASCADE,
        related_name="availability_windows",
    )
    weekday = models.PositiveSmallIntegerField()  # Monday=0, Sunday=6.
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["weekday", "start_time", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(weekday__gte=0, weekday__lte=6),
                name="deals_availability_valid_weekday",
            ),
            models.CheckConstraint(
                condition=Q(end_time__gt=models.F("start_time")),
                name="deals_availability_positive_window",
            ),
            models.UniqueConstraint(
                fields=["preference", "weekday", "start_time", "end_time"],
                name="deals_availability_unique_window",
            ),
        ]

    def __str__(self):
        return f"{self.preference_id}: {self.weekday} {self.start_time}-{self.end_time}"


class MeetupAvailabilityOverride(models.Model):
    """A one-day replacement for the recurring schedule."""

    preference = models.ForeignKey(
        MeetupPreference,
        on_delete=models.CASCADE,
        related_name="availability_overrides",
    )
    date = models.DateField()
    is_unavailable = models.BooleanField(default=False)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    class Meta:
        ordering = ["date", "start_time", "id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(is_unavailable=True, start_time__isnull=True, end_time__isnull=True)
                    | Q(
                        is_unavailable=False,
                        start_time__isnull=False,
                        end_time__isnull=False,
                        end_time__gt=models.F("start_time"),
                    )
                ),
                name="deals_override_valid_window",
            ),
        ]

    def __str__(self):
        return f"{self.preference_id}: override {self.date}"


class MeetupProposal(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        SUPERSEDED = "superseded", "Superseded"
        WITHDRAWN = "withdrawn", "Withdrawn"

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="meetup_proposals")
    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="meetup_proposals",
    )
    meeting_spot = models.ForeignKey(
        "schools.MeetingSpot",
        on_delete=models.PROTECT,
        related_name="meetup_proposals",
    )
    starts_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    # A proposal can't be accepted after this (24 hours, or its start time if sooner).
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["deal"],
                condition=Q(status="accepted"),
                name="deals_one_accepted_meetup",
            ),
        ]

    def __str__(self):
        return f"Meetup proposal {self.pk} for deal {self.deal_id}"


class MeetupStatusUpdate(models.Model):
    class Kind(models.TextChoices):
        RUNNING_LATE = "running_late", "Running late"
        ARRIVED = "arrived", "Arrived"

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="meetup_updates")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="meetup_status_updates",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    minutes_late = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.kind} on deal {self.deal_id}"


class DealProblem(models.Model):
    """A structured report from the buyer or seller about a handoff (a no-show, an item not as
    described...). It's sent to moderation as a deal report; it never punishes anyone by
    itself."""

    class Kind(models.TextChoices):
        NO_SHOW = "no_show", "The other person didn't show up"
        NOT_AS_DESCRIBED = "not_as_described", "Item wasn't as described"
        PAYMENT = "payment", "Payment problem"
        SAFETY = "safety", "Safety concern"
        OTHER = "other", "Something else"

    deal = models.ForeignKey(Deal, on_delete=models.PROTECT, related_name="problems")
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="deal_problems"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    details = models.CharField(max_length=1000, blank=True)
    # The deal's status when it was reported.
    deal_status = models.CharField(max_length=30)
    report = models.ForeignKey(
        "trust.Report", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    case = models.ForeignKey(
        "trust.ModerationCase", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["deal", "reporter", "kind"], name="deals_one_problem_per_kind"
            ),
        ]

    def __str__(self):
        return f"{self.kind} on deal {self.deal_id} by {self.reporter_id}"


class DealDispute(models.Model):
    """A handoff Tanu won't settle by guessing: a moderator decides whether it completed.
    Holds a snapshot of the deal and listing as they were when it opened."""

    class Reason(models.TextChoices):
        ONE_SIDED_CONFIRMATION = "one_sided_confirmation", "Only one side confirmed in time"
        PROBLEM_AFTER_CONFIRMATION = (
            "problem_after_confirmation",
            "A problem was reported after a confirmation",
        )

    class Outcome(models.TextChoices):
        COMPLETED = "completed", "Handoff happened"
        CANCELED = "canceled", "Handoff didn't happen"

    deal = models.OneToOneField(Deal, on_delete=models.PROTECT, related_name="dispute")
    reason = models.CharField(max_length=40, choices=Reason.choices)
    # Null when the system opened it (a deadline passed).
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    case = models.ForeignKey(
        "trust.ModerationCase",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="deal_disputes",
    )
    snapshot = models.JSONField(default=dict)
    opened_at = models.DateTimeField(auto_now_add=True)
    outcome = models.CharField(max_length=20, choices=Outcome.choices, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)

    def __str__(self):
        return f"Dispute on deal {self.deal_id}"
