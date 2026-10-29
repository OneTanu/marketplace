"""Scheduled Deals jobs. Business logic stays in services."""

from procrastinate.contrib.django import app

from . import services


@app.task(name="deals.expire_deal")
def expire_deal(deal_id: int, expected_status: str) -> None:
    services.expire(deal_id=deal_id, expected_status=expected_status)


@app.periodic(cron="*/10 * * * *", periodic_id="deals.settle_due_deals")
@app.task(name="deals.settle_due_deals", queueing_lock="deals.settle_due_deals")
def settle_due_deals(timestamp: int) -> None:
    """Backstop for the per-deal jobs: settle every deal whose deadline has passed."""
    services.settle_due_deals()
