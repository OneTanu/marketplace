from django.contrib import admin

from .models import MeetingSpot, School, SchoolDomain


class SchoolDomainInline(admin.TabularInline):
    model = SchoolDomain
    extra = 1


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ["name", "short_name", "slug", "marketplace_status", "signup_is_open"]
    list_filter = ["marketplace_status", "signup_is_open", "country_code"]
    search_fields = ["name", "short_name", "domains__domain"]
    ordering = ["sort_order", "name"]
    prepopulated_fields = {"slug": ["short_name"]}
    inlines = [SchoolDomainInline]


@admin.register(MeetingSpot)
class MeetingSpotAdmin(admin.ModelAdmin):
    list_display = ["name", "school", "is_indoor", "is_active", "sort_order"]
    list_filter = ["school", "is_active", "is_indoor"]
    search_fields = ["name", "directions"]
