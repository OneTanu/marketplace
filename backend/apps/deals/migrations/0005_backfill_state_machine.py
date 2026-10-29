"""Fill the new audit and queue fields for deals that existed before them."""

from django.db import migrations
from django.db.models import F
from django.utils import timezone

CLOSED = ["canceled", "declined", "expired"]


def backfill(apps, schema_editor):
    Deal = apps.get_model("deals", "Deal")
    # Backup queues, in the order the requests were made.
    listing_ids = (
        Deal.objects.filter(status="backup").values_list("listing_id", flat=True).distinct()
    )
    for listing_id in listing_ids:
        queue = Deal.objects.filter(listing_id=listing_id, status="backup").order_by(
            "created_at", "id"
        )
        for position, deal in enumerate(queue, start=1):
            Deal.objects.filter(pk=deal.pk).update(backup_position=position)
    # Closed and completed deals: the last change is the best record of when.
    Deal.objects.filter(status__in=CLOSED, closed_at__isnull=True).update(
        closed_at=F("updated_at")
    )
    Deal.objects.filter(status="completed", completed_at__isnull=True).update(
        completed_at=F("updated_at")
    )
    # Before this change, a handoff with one confirmation stopped its clock and held the
    # listing indefinitely. Give those a deadline of now, so the deadline sweep sends them to
    # a moderator as disputes.
    Deal.objects.filter(status="pending", handoff_deadline__isnull=True).update(
        handoff_deadline=timezone.now()
    )


class Migration(migrations.Migration):
    dependencies = [("deals", "0004_state_machine_audit")]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
