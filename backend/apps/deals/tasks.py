"""Scheduled Deals jobs. Business logic stays in services."""

from procrastinate.contrib.django import app

from . import services


@app.task(name="deals.expire_deal")
def expire_deal(deal_id: int, expected_status: str) -> None:
    services.expire(deal_id=deal_id, expected_status=expected_status)
