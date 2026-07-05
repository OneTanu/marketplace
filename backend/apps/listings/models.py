from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models


class ListingKind(models.TextChoices):
    ITEM = "item", "Item"
    SERVICE = "service", "Service"  # V2


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    kind = models.CharField(max_length=20, choices=ListingKind.choices)
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="children"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["kind", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Listing(models.Model):
    """Fields shared by every kind of listing. Kind-specific fields live in the
    one-to-one detail tables (ItemDetails, ServiceDetails)."""

    class Status(models.TextChoices):
        # Items: AVAILABLE -> PENDING (seller accepted a buyer) -> SOLD (handoff confirmed).
        # PENDING can fall back to AVAILABLE. Transitions are enforced in services, not here.
        AVAILABLE = "available", "Available"
        PENDING = "pending", "Pending"
        SOLD = "sold", "Sold"
        REMOVED = "removed", "Removed"  # by the seller or by moderation

    school = models.ForeignKey("schools.School", on_delete=models.PROTECT, related_name="listings")
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listings"
    )
    kind = models.CharField(max_length=20, choices=ListingKind.choices, default=ListingKind.ITEM)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="listings")
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    price_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # The default feed: a school's available listings, newest first.
            models.Index(fields=["school", "status", "-created_at"], name="listing_feed_idx"),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        if self.category_id and self.category.kind != self.kind:
            raise ValidationError({"category": "Category doesn't match the listing kind."})
        if self.seller_id and self.school_id and self.seller.school_id != self.school_id:
            raise ValidationError({"school": "A listing belongs to its seller's school."})


class ListingPhoto(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="listings/%Y/%m/")
    position = models.PositiveSmallIntegerField(default=0)  # 0 is the cover photo
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return f"Photo {self.position} of {self.listing_id}"


class Color(models.TextChoices):
    BLACK = "black", "Black"
    WHITE = "white", "White"
    GRAY = "gray", "Gray"
    BROWN = "brown", "Brown"
    BEIGE = "beige", "Beige"
    RED = "red", "Red"
    PINK = "pink", "Pink"
    ORANGE = "orange", "Orange"
    YELLOW = "yellow", "Yellow"
    GREEN = "green", "Green"
    BLUE = "blue", "Blue"
    PURPLE = "purple", "Purple"
    GOLD = "gold", "Gold"
    SILVER = "silver", "Silver"
    MULTI = "multi", "Multicolor"


class ItemDetails(models.Model):
    """Fields for kind=item. Structured on purpose: filters and watched searches match on them."""

    class Condition(models.TextChoices):
        NEW_WITH_TAGS = "new_with_tags", "New with tags"
        LIKE_NEW = "like_new", "Like new"
        GOOD = "good", "Good"
        FAIR = "fair", "Fair"
        POOR = "poor", "Poor"

    listing = models.OneToOneField(
        Listing, on_delete=models.CASCADE, primary_key=True, related_name="item_details"
    )
    condition = models.CharField(max_length=20, choices=Condition.choices)
    size = models.CharField(max_length=30, blank=True)
    brand = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=20, choices=Color.choices, blank=True)

    class Meta:
        verbose_name_plural = "item details"

    def __str__(self):
        return f"Item details for {self.listing_id}"


class ServiceDetails(models.Model):
    """Fields for kind=service. Unused until V2; defined now so services don't reshape Listing."""

    class LocationType(models.TextChoices):
        # Never UMD residence halls (see AGENTS.md).
        PROVIDER_PLACE = "provider_place", "Provider's off-campus place"
        CLIENT_PLACE = "client_place", "Client's off-campus place"
        LICENSED_SHOP = "licensed_shop", "Licensed shop"
        REMOTE = "remote", "Remote"

    listing = models.OneToOneField(
        Listing, on_delete=models.CASCADE, primary_key=True, related_name="service_details"
    )
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    location_types = ArrayField(
        models.CharField(max_length=20, choices=LocationType.choices), default=list, blank=True
    )
    license_number = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name_plural = "service details"

    def __str__(self):
        return f"Service details for {self.listing_id}"
