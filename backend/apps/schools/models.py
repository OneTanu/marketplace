from django.contrib.postgres.fields import ArrayField
from django.core.validators import RegexValidator
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
    # School colors in order: the first leads the listing badge and the profile stripe, the
    # second is its accent. Shown as a stripe or badge only, never as a theme or logo.
    colors = ArrayField(
        models.CharField(
            max_length=7,
            validators=[RegexValidator(r"^#[0-9A-F]{6}$", "Use a hex color like #E21833.")],
        ),
        default=list,
        blank=True,
        size=4,
    )
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


class MeetingSpot(models.Model):
    """A school-curated public place that is suitable for marketplace handoffs."""

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="meeting_spots")
    name = models.CharField(max_length=120)
    directions = models.CharField(max_length=300)
    safety_note = models.CharField(max_length=300, blank=True)
    is_indoor = models.BooleanField(default=False)
    accessibility_notes = models.CharField(max_length=300, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="schools_meeting_spot_name")
        ]

    def __str__(self):
        return f"{self.name} ({self.school.short_name})"
