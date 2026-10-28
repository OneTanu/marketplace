from django.contrib import admin

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


class ReadOnlyAdminMixin:
    """Deal records are history: they change only through deals.services (which enforces the
    state machine and records who did what) and are never deleted. The admin can look, not
    touch; moderators decide disputes in the moderation portal."""

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class DealOfferInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = DealOffer
    extra = 0
    readonly_fields = ["offered_by", "amount_cents", "created_at"]


class HandoffConfirmationInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = HandoffConfirmation
    extra = 0
    readonly_fields = ["user", "confirmed_at"]


class DealEventInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = DealEvent
    extra = 0
    readonly_fields = ["event_type", "actor", "from_status", "to_status", "data", "created_at"]


class DealProblemInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = DealProblem
    extra = 0


@admin.register(Deal)
class DealAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ["id", "listing", "buyer", "seller", "status", "current_amount_cents"]
    list_filter = ["status", "kind", "currency"]
    search_fields = ["listing__title", "buyer__username", "seller__username"]
    inlines = [DealOfferInline, HandoffConfirmationInline, DealProblemInline, DealEventInline]


@admin.register(DealDispute)
class DealDisputeAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ["deal", "reason", "opened_at", "outcome", "resolved_by"]
    list_filter = ["reason", "outcome"]


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
class MeetupProposalAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ["id", "deal", "meeting_spot", "starts_at", "status", "proposed_by"]
    list_filter = ["status", "meeting_spot__school"]
    search_fields = ["deal__listing__title", "proposed_by__username"]


@admin.register(MeetupStatusUpdate)
class MeetupStatusUpdateAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ["deal", "actor", "kind", "minutes_late", "created_at"]
    list_filter = ["kind"]
