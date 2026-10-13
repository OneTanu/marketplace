"""Scheduled Trust jobs. Business logic stays in services."""

from procrastinate.contrib.django import app

from . import services


@app.task(name="trust.end_suspension")
def end_suspension(restriction_id: int) -> None:
    services.end_expired_suspension(restriction_id=restriction_id)
