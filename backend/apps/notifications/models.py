from django.conf import settings
from django.db import models
from django.db.models import Q


class Notification(models.Model):
    """Something a student or staff member should know about, shown in the app (and sometimes
    emailed). Other apps create these through notifications.services.notify()."""

    class Kind(models.TextChoices):
        DEAL = "deal", "Deal"
        MODERATION_NOTICE = "moderation_notice", "Moderation notice"
        REPORT_UPDATE = "report_update", "Report update"
        INFO_REQUEST = "info_request", "Moderator question"
        APPEAL_UPDATE = "appeal_update", "Appeal update"
        STAFF_ALERT = "staff_alert", "Staff alert"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=30, choices=Kind.choices)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    # A path in the web app ("/deals"), not a full URL, so it works on any domain.
    link = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["user", "-created_at"],
                condition=Q(read_at__isnull=True),
                name="notification_unread_idx",
            ),
            models.Index(fields=["user", "-created_at"], name="notification_user_idx"),
        ]

    def __str__(self):
        return f"{self.kind} for {self.user_id}: {self.title}"
