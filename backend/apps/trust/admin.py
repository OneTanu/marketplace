"""A first moderation queue in Django admin. Records are read-only here: decisions go through
trust.services, so each one is checked and audited. The branded /moderation portal replaces
this for everyday work."""

from django.contrib import admin

from .models import (
    BannedEmail,
    Block,
    EvidenceAccess,
    EvidenceSnapshot,
    ModerationAction,
    ModerationCase,
    ModeratorScope,
    Report,
    UserRestriction,
)


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ReportInline(admin.TabularInline):
    model = Report
    fields = ["reason", "prohibited_category", "target_type", "reporter", "details", "created_at"]
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


class ActionInline(admin.TabularInline):
    model = ModerationAction
    fields = ["created_at", "kind", "actor", "target_user", "reason"]
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ModerationCase)
class ModerationCaseAdmin(ReadOnlyAdmin):
    list_display = [
        "id",
        "priority",
        "status",
        "subject_user",
        "listing",
        "school",
        "assigned_to",
        "escalated",
        "created_at",
    ]
    list_filter = ["status", "priority", "school", "escalated"]
    search_fields = ["subject_user__username", "subject_user__email", "listing__title"]
    inlines = [ReportInline, ActionInline]


@admin.register(Report)
class ReportAdmin(ReadOnlyAdmin):
    list_display = [
        "id",
        "reason",
        "prohibited_category",
        "target_type",
        "reporter",
        "reported_user",
        "status",
        "created_at",
    ]
    list_filter = ["reason", "target_type", "status", "school"]
    search_fields = ["reporter__username", "reported_user__username"]


@admin.register(ModerationAction)
class ModerationActionAdmin(ReadOnlyAdmin):
    list_display = ["created_at", "kind", "actor", "target_user", "case", "reason"]
    list_filter = ["kind"]
    search_fields = ["target_user__username", "actor__username", "reason"]


@admin.register(UserRestriction)
class UserRestrictionAdmin(ReadOnlyAdmin):
    list_display = ["user", "kind", "expires_at", "lifted_at", "created_at"]
    list_filter = ["kind"]
    search_fields = ["user__username", "user__email"]


admin.site.register(EvidenceSnapshot, ReadOnlyAdmin)
admin.site.register(EvidenceAccess, ReadOnlyAdmin)
admin.site.register(Block, ReadOnlyAdmin)
admin.site.register(BannedEmail, ReadOnlyAdmin)


@admin.register(ModeratorScope)
class ModeratorScopeAdmin(admin.ModelAdmin):
    """Superusers set which schools each staff member moderates."""

    filter_horizontal = ["schools"]
