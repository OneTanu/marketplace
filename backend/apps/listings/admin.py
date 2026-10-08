from django.contrib import admin, messages

from . import services
from .models import Category, ItemDetails, Listing, ListingKind, ListingPhoto, ServiceDetails


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "kind", "parent", "is_active"]
    list_filter = ["kind", "is_active"]
    prepopulated_fields = {"slug": ["name"]}


class ListingPhotoInline(admin.TabularInline):
    # View only: uploads go through listings services, which strip location data, resize,
    # and keep positions 0..n-1. A file added here would skip all of that.
    model = ListingPhoto
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ItemDetailsInline(admin.StackedInline):
    model = ItemDetails
    can_delete = False  # an item listing always has its details (condition)


class ServiceDetailsInline(admin.StackedInline):
    model = ServiceDetails


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ["title", "kind", "status", "price_cents", "seller", "school", "created_at"]
    list_filter = ["school", "kind", "status", "category"]
    search_fields = ["title", "description", "seller__email"]
    # Moderators can fix wording (title, description, details) and remove listings. Everything
    # with rules attached changes only through listings services: status (see the action
    # below), price and category (the Free/$0 rule, later price-drop alerts), and the seller
    # and school (a listing's school is always its seller's school).
    readonly_fields = [
        "school",
        "seller",
        "kind",
        "category",
        "price_cents",
        "currency",
        "status",
        "removed_by",
        "removed_at",
    ]
    actions = ["remove_by_moderation"]

    def get_inlines(self, request, obj):
        # Only the detail table matching the listing's kind.
        if obj is not None and obj.kind == ListingKind.SERVICE:
            return [ListingPhotoInline, ServiceDetailsInline]
        return [ListingPhotoInline, ItemDetailsInline]

    def has_add_permission(self, request):
        # Listings are posted through the API, which applies the listing rules.
        return False

    def has_delete_permission(self, request, obj=None):
        # Removal is a soft delete (the Remove action below); conversations, deals and reports
        # point at listings, so the row must stay.
        return False

    def save_model(self, request, obj, form, change):
        # obj was loaded before this save, so a service may have changed a read-only field
        # (e.g. status) in between. Never write those back.
        fields = [
            f.name
            for f in obj._meta.concrete_fields
            if not f.primary_key and f.name not in self.readonly_fields
        ]
        obj.save(update_fields=fields)

    @admin.action(description="Remove (moderation)")
    def remove_by_moderation(self, request, queryset):
        removed, skipped = 0, 0
        for listing in queryset:
            try:
                services.remove_by_moderation(listing)
                removed += 1
            except (services.ListingStatusError, Listing.DoesNotExist):
                skipped += 1  # already removed, or deleted since the page loaded
        if removed:
            self.message_user(request, f"Removed {removed} listing(s).", messages.SUCCESS)
        if skipped:
            self.message_user(
                request, f"Skipped {skipped} listing(s) already removed or gone.", messages.WARNING
            )
