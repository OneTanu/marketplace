from django.conf import settings
from django.db import models
from django.db.models import Q


class Review(models.Model):
    deal = models.ForeignKey("deals.Deal", on_delete=models.PROTECT, related_name="reviews")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reviews_written"
    )
    subject = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reviews_received"
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["deal", "author"], name="reviews_one_per_party"),
            models.CheckConstraint(
                condition=~Q(author=models.F("subject")), name="reviews_not_self"
            ),
            models.CheckConstraint(
                condition=Q(rating__gte=1, rating__lte=5), name="reviews_rating_1_5"
            ),
        ]

    def __str__(self):
        return f"{self.rating}-star review of {self.subject_id} for deal {self.deal_id}"
