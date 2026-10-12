from django.conf import settings
from django.db import models
from django.db.models import Q


class Deal(models.Model):
    class Kind(models.TextChoices):
        BUY_NOW = "buy_now", "Buy now"
        OFFER = "offer", "Offer"

    class Status(models.TextChoices):
        AWAITING_SELLER = "awaiting_seller", "Awaiting seller"
        AWAITING_BUYER = "awaiting_buyer", "Awaiting buyer"
        BACKUP = "backup", "Backup"
        PENDING = "pending", "Pending handoff"
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
    response_deadline = models.DateTimeField(null=True, blank=True)
    handoff_deadline = models.DateTimeField(null=True, blank=True)
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
                condition=Q(
                    status__in=[
                        "awaiting_seller",
                        "awaiting_buyer",
                        "backup",
                        "pending",
                    ]
                ),
                name="deals_one_active_per_buyer_listing",
            ),
        ]
        indexes = [
            models.Index(fields=["seller", "status", "-updated_at"], name="deal_seller_status_idx"),
            models.Index(fields=["buyer", "status", "-updated_at"], name="deal_buyer_status_idx"),
        ]

    def __str__(self):
        return f"Deal {self.pk} for listing {self.listing_id}"


class DealOffer(models.Model):
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="offers")
    offered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="deal_offers"
    )
    amount_cents = models.PositiveIntegerField()
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
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=50)
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
