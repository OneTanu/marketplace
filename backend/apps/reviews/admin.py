from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["id", "deal", "author", "subject", "rating", "created_at"]
    list_filter = ["rating", "created_at"]
    search_fields = ["author__username", "subject__username", "comment"]
    readonly_fields = ["deal", "author", "subject", "rating", "comment", "created_at"]
