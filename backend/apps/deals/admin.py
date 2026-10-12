from django.contrib import admin

from .models import Deal, DealEvent, DealOffer, HandoffConfirmation


class DealOfferInline(admin.TabularInline):
    model = DealOffer
    extra = 0
    readonly_fields = ["offered_by", "amount_cents", "created_at"]


class HandoffConfirmationInline(admin.TabularInline):
    model = HandoffConfirmation
    extra = 0
    readonly_fields = ["user", "confirmed_at"]


class DealEventInline(admin.TabularInline):
    model = DealEvent
    extra = 0
    readonly_fields = ["event_type", "actor", "data", "created_at"]


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ["id", "listing", "buyer", "seller", "status", "current_amount_cents"]
    list_filter = ["status", "kind", "currency"]
    search_fields = ["listing__title", "buyer__username", "seller__username"]
    inlines = [DealOfferInline, HandoffConfirmationInline, DealEventInline]
