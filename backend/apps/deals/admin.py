from django.contrib import admin

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


class MeetupAvailabilityInline(admin.TabularInline):
    model = MeetupAvailabilityWindow
    extra = 0


class MeetupOverrideInline(admin.TabularInline):
    model = MeetupAvailabilityOverride
    extra = 0


@admin.register(MeetupPreference)
class MeetupPreferenceAdmin(admin.ModelAdmin):
    list_display = ["user", "updated_at"]
    search_fields = ["user__username", "user__email"]
    filter_horizontal = ["meeting_spots"]
    inlines = [MeetupAvailabilityInline, MeetupOverrideInline]


@admin.register(MeetupProposal)
class MeetupProposalAdmin(admin.ModelAdmin):
    list_display = ["id", "deal", "meeting_spot", "starts_at", "status", "proposed_by"]
    list_filter = ["status", "meeting_spot__school"]
    search_fields = ["deal__listing__title", "proposed_by__username"]


@admin.register(MeetupStatusUpdate)
class MeetupStatusUpdateAdmin(admin.ModelAdmin):
    list_display = ["deal", "actor", "kind", "minutes_late", "created_at"]
    list_filter = ["kind"]
