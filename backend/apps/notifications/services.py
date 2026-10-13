"""Notifications: in-app, plus email for things a student needs even when they can't sign in
(e.g. a suspension). Other apps call notify(); nothing else creates Notification rows."""

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import Notification

Kind = Notification.Kind


def notify(
    user, *, kind: str, title: str, body: str = "", link: str = "", email: bool = False
) -> Notification:
    """Record a notification. With `email`, also queue an email, which only goes out if the
    surrounding transaction commits (the job lives in the same database)."""
    notification = Notification.objects.create(
        user=user, kind=kind, title=title, body=body, link=link
    )
    if email and user.email:
        from .tasks import send_notification_email

        send_notification_email.defer(notification_id=notification.pk)
    return notification


def unread(user):
    return Notification.objects.filter(user=user, read_at__isnull=True)


def mark_read(user, ids: list[int] | None = None) -> int:
    """Mark some (or, with no ids, all) of a user's notifications read. Returns how many."""
    notifications = unread(user)
    if ids is not None:
        notifications = notifications.filter(pk__in=ids)
    return notifications.update(read_at=timezone.now())


@transaction.atomic
def send_email(*, notification_id: int) -> None:
    notification = Notification.objects.select_related("user").filter(pk=notification_id).first()
    if notification is None:
        return
    link = f"\n\n{settings.WEB_APP_URL}{notification.link}" if notification.link else ""
    send_mail(
        subject=f"Tanu: {notification.title}",
        message=f"{notification.body}{link}\n\n— Tanu",
        from_email=None,
        recipient_list=[notification.user.email],
    )
