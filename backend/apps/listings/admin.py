from django.contrib import admin

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

    def get_inlines(self, request, obj):
        # Only the detail table matching the listing's kind. New listings default to items.
        if obj is not None and obj.kind == ListingKind.SERVICE:
            return [ListingPhotoInline, ServiceDetailsInline]
        return [ListingPhotoInline, ItemDetailsInline]
