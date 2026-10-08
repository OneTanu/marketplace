from django.contrib import admin, messages

from . import services
from .models import Category, ItemDetails, Listing, ListingKind, ListingPhoto, ServiceDetails


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "kind", "parent", "is_active"]
    list_filter = ["kind", "is_active"]
    prepopulated_fields = {"slug": ["name"]}


class ListingPhotoInline(admin.TabularInline):
    model = ListingPhoto
    extra = 1


class ItemDetailsInline(admin.StackedInline):
    model = ItemDetails


class ServiceDetailsInline(admin.StackedInline):
    model = ServiceDetails


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ["title", "kind", "status", "price_cents", "seller", "school", "created_at"]
    list_filter = ["school", "kind", "status", "category"]
    search_fields = ["title", "description", "seller__email"]
    raw_id_fields = ["seller"]
    # Status only changes through listings services (see the action below).
    readonly_fields = ["status", "removed_by", "removed_at"]
    actions = ["remove_by_moderation"]

    def get_inlines(self, request, obj):
        # Only the detail table matching the listing's kind. New listings default to items.
        if obj is not None and obj.kind == ListingKind.SERVICE:
            return [ListingPhotoInline, ServiceDetailsInline]
        return [ListingPhotoInline, ItemDetailsInline]

    def has_delete_permission(self, request, obj=None):
        # Removal is a soft delete (Remove action above); conversations, deals and reports
        # point at listings, so the row must stay.
        return False

    def save_model(self, request, obj, form, change):
        if not change:
            return super().save_model(request, obj, form, change)
        # Status isn't in the form, but obj was loaded before this save, so a service may
        # have moved the listing in between. Never write the status fields back.
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
