from django.db import models


class MarketplaceStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    WAITLIST = "waitlist", "Waitlist"
    OPEN = "open", "Open"
    PAUSED = "paused", "Paused"


class School(models.Model):
    """A campus on Tanu. Users and listings belong to exactly one school."""

    name = models.CharField(max_length=200)  # "University of Maryland"
    short_name = models.CharField(max_length=50)  # "UMD"
    slug = models.SlugField(unique=True)
    # Signup and marketplace availability are separate product decisions. A school
    # can remain browseable while new registrations are temporarily closed.
    signup_is_open = models.BooleanField(default=False)
    marketplace_status = models.CharField(
        max_length=20,
        choices=MarketplaceStatus.choices,
        default=MarketplaceStatus.PLANNED,
    )
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country_code = models.CharField(max_length=2, default="US")
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.short_name


class SchoolDomain(models.Model):
    """An email domain that proves membership in a school, e.g. "umd.edu"."""

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="domains")
    domain = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["domain"]

    def __str__(self):
        return self.domain

    def save(self, *args, **kwargs):
        self.domain = self.domain.strip().lower()
        super().save(*args, **kwargs)
