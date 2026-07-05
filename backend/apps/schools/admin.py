from django.contrib import admin

from .models import School, SchoolDomain


class SchoolDomainInline(admin.TabularInline):
    model = SchoolDomain
    extra = 1


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ["name", "short_name", "slug", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "short_name", "domains__domain"]
    prepopulated_fields = {"slug": ["short_name"]}
    inlines = [SchoolDomainInline]
