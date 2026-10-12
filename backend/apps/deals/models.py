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
