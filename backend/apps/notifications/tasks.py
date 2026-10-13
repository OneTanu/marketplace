"""Notification jobs. Business logic stays in services."""

from procrastinate.contrib.django import app

from . import services


@app.task(name="notifications.send_email")
def send_notification_email(notification_id: int) -> None:
    services.send_email(notification_id=notification_id)
