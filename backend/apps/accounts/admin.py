from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = [
        "email",
        "username",
        "school",
        "first_name",
        "last_name",
        "is_staff",
        "date_joined",
    ]
    list_filter = ["school", "is_staff", "is_active"]
    search_fields = ["email", "username", "first_name", "last_name", "instagram_handle"]
    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        (
            "Profile",
            {
                "fields": [
                    "school",
                    "username",
                    "first_name",
                    "last_name",
                    "instagram_handle",
                    "profile_description",
                ]
            },
        ),
        (
            "Permissions",
            {"fields": ["is_active", "is_staff", "is_superuser", "groups", "user_permissions"]},
        ),
        ("Dates", {"fields": ["last_login", "date_joined"]}),
    ]
    add_fieldsets = [
        (
            None,
            {"classes": ["wide"], "fields": ["email", "username", "password1", "password2"]},
        )
    ]
