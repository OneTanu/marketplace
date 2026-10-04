from django.contrib import admin

from .models import School, SchoolDomain


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
