from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.listings.models import Color, ItemDetails


class Notification(models.Model):
    """Something a student or staff member should know about, shown in the app (and sometimes
    emailed). Other apps create these through notifications.services.notify()."""

    class Kind(models.TextChoices):
        DEAL = "deal", "Deal"
        MODERATION_NOTICE = "moderation_notice", "Moderation notice"
        REPORT_UPDATE = "report_update", "Report update"
        INFO_REQUEST = "info_request", "Moderator question"
        APPEAL_UPDATE = "appeal_update", "Appeal update"
        STAFF_ALERT = "staff_alert", "Staff alert"
        SAVED_SEARCH = "saved_search", "Saved search match"
        ACCOUNT = "account", "Account"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=30, choices=Kind.choices)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    # A path in the web app ("/deals"), not a full URL, so it works on any domain.
    link = models.CharField(max_length=300, blank=True)
    # Set for notifications that must be sent once only (e.g. "deal-event:42"): notify() with a
    # key that's already been used returns the existing notification.
    dedupe_key = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["user", "-created_at"],
                condition=Q(read_at__isnull=True),
                name="notification_unread_idx",
            ),
            models.Index(fields=["user", "-created_at"], name="notification_user_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "dedupe_key"],
                condition=~Q(dedupe_key=""),
                name="notification_once_per_key",
            ),
        ]

    def __str__(self):
        return f"{self.kind} for {self.user_id}: {self.title}"


class SavedSearch(models.Model):
    """A feed search a student saved: the feed's filters as typed columns (blank or null means
    "any"), so running it rebuilds the same /search URL and alerts match exactly what the feed
    would show. Changes go through notifications.services."""

    class Sort(models.TextChoices):
        # The feed's sorts (listings.services.FEED_SORTS). Only used to run the search.
        NEWEST = "newest", "Newly listed"
        PRICE_ASC = "price_asc", "Price: low to high"
        PRICE_DESC = "price_desc", "Price: high to low"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_searches"
    )
    name = models.CharField(max_length=80)
    query = models.CharField(max_length=100, blank=True)  # keywords
    # School scope: a school, every open school, or (neither) the student's own school.
    school = models.ForeignKey(
        "schools.School", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    all_schools = models.BooleanField(default=False)
    # Matches this category and every category under it (a department or a subcategory).
    category = models.ForeignKey(
        "listings.Category", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    brand = models.CharField(max_length=100, blank=True)
    min_price_cents = models.PositiveIntegerField(null=True, blank=True)
    max_price_cents = models.PositiveIntegerField(null=True, blank=True)
    # Exact size, any case. Jeans and pants are "<waist>x<inseam>", e.g. "32x30".
    size = models.CharField(max_length=30, blank=True)
    condition = models.CharField(max_length=20, choices=ItemDetails.Condition.choices, blank=True)
    color = models.CharField(max_length=20, choices=Color.choices, blank=True)
    sort = models.CharField(max_length=20, choices=Sort.choices, default=Sort.NEWEST)
    alerts_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(school__isnull=False, all_schools=True),
                name="saved_search_one_school_scope",
            ),
            models.CheckConstraint(
                condition=Q(min_price_cents__isnull=True)
                | Q(max_price_cents__isnull=True)
                | Q(min_price_cents__lte=models.F("max_price_cents")),
                name="saved_search_price_range",
            ),
            # The same filters saved twice would send the same alerts twice. (Sort and name
            # don't change what matches.)
            models.UniqueConstraint(
                "user",
                "query",
                "school",
                "all_schools",
                "category",
                "brand",
                "min_price_cents",
                "max_price_cents",
                "size",
                "condition",
                "color",
                name="saved_search_unique_filters",
                nulls_distinct=False,
            ),
        ]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="saved_search_user_idx"),
            # Alert matching starts from the searches with alerts on.
            models.Index(
                fields=["category"],
                condition=Q(alerts_enabled=True),
                name="saved_search_alerting_idx",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.user_id})"


class SavedSearchMatch(models.Model):
    """A listing a student was alerted to. One per student and listing, ever, so a retried job
    or two matching saved searches never alert them twice."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    listing = models.ForeignKey("listings.Listing", on_delete=models.CASCADE, related_name="+")
    # The search that matched first; kept (as null) if the student deletes it.
    saved_search = models.ForeignKey(
        SavedSearch, on_delete=models.SET_NULL, null=True, blank=True, related_name="matches"
    )
    notification = models.ForeignKey(
        Notification, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "listing"], name="saved_search_match_once"),
        ]

    def __str__(self):
        return f"Listing {self.listing_id} matched for {self.user_id}"
