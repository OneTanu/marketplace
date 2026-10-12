from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction

from apps.deals.models import Deal

from .models import Review


@transaction.atomic
def create_review(*, deal: Deal, author, rating: int, comment: str = "") -> Review:
    deal = Deal.objects.select_for_update().get(pk=deal.pk)
    if author.pk not in {deal.buyer_id, deal.seller_id}:
        raise PermissionDenied("Only the buyer or seller can review this handoff.")
    if deal.status != Deal.Status.COMPLETED:
        raise ValidationError("Reviews open after both people confirm the handoff.")
    if not 1 <= rating <= 5:
        raise ValidationError({"rating": "Choose a rating from 1 to 5."})
    comment = comment.strip()
    if len(comment) > 500:
        raise ValidationError({"comment": "Keep your review under 500 characters."})
    subject_id = deal.seller_id if author.pk == deal.buyer_id else deal.buyer_id
    try:
        with transaction.atomic():
            return Review.objects.create(
                deal=deal,
                author=author,
                subject_id=subject_id,
                rating=rating,
                comment=comment,
            )
    except IntegrityError as exc:
        raise ValidationError("You already reviewed this handoff.") from exc
