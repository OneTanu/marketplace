"""Listings business rules. Views, serializers, the admin and other apps change listings only
through these functions; nothing else sets a listing's `status`.

The allowed status moves are:

    Available -> Pending    mark_pending (Deals: seller accepted a buyer)
    Pending   -> Available  return_to_available (Deals: fell through or timed out)
    Pending   -> Sold       mark_sold (Deals: both sides confirmed the handoff)
    Available -> Removed    remove_by_seller, remove_by_moderation
    Pending   -> Removed    remove_by_moderation
    Sold      -> Removed    remove_by_moderation

Any other move raises ListingStatusError and leaves the listing unchanged.
"""

from collections.abc import Sequence
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone
from PIL import Image

from .models import Category, ItemDetails, Listing, ListingKind, ListingPhoto

MAX_PRICE_CENTS = 1_000_000  # $10,000
MAX_TITLE_LENGTH = 120
MAX_DESCRIPTION_LENGTH = 5_000
MIN_PHOTOS = 1
MAX_PHOTOS = 10
MAX_PHOTO_BYTES = 10 * 1024 * 1024  # 10 MB
# Accepted Pillow formats and the extension each is stored with. Pillow reports JPEGs that
# hold more than one picture (iPhone HDR, many Android cameras) as MPO.
PHOTO_EXTENSIONS = {"JPEG": "jpg", "MPO": "jpg", "PNG": "png", "WEBP": "webp"}
FREE_CATEGORY_SLUG = "free"  # seeded by migration 0004_seed_item_categories


def validate_item_category(category: Category) -> None:
    if category.kind != ListingKind.ITEM or not category.is_active:
        raise ValidationError("Choose an active item category.")


def validate_price(category: Category, price_cents: int) -> None:
    """Price range, plus the Free rule: $0 only in Free, and Free requires $0."""
    if not 0 <= price_cents <= MAX_PRICE_CENTS:
        raise ValidationError(
            {"price_cents": f"Price must be between $0 and ${MAX_PRICE_CENTS // 100:,}."}
        )
    is_free = category.slug == FREE_CATEGORY_SLUG
    if is_free and price_cents != 0:
        raise ValidationError({"price_cents": "Items in Free must be $0."})
    if not is_free and price_cents == 0:
        raise ValidationError({"price_cents": "Set a price, or choose the Free category."})


def validate_photos(photos: Sequence[UploadedFile]) -> None:
    """1 to 10 photos, each a JPEG, PNG or WebP of at most 10 MB."""
    if not MIN_PHOTOS <= len(photos) <= MAX_PHOTOS:
        raise ValidationError(f"Add between {MIN_PHOTOS} and {MAX_PHOTOS} photos.")
    errors = []
    for number, photo in enumerate(photos, start=1):
        if photo.size > MAX_PHOTO_BYTES:
            errors.append(f"Photo {number} is larger than {MAX_PHOTO_BYTES // (1024 * 1024)} MB.")
        elif _image_format(photo) not in PHOTO_EXTENSIONS:
            errors.append(f"Photo {number} isn't a JPEG, PNG or WebP image.")
    if errors:
        raise ValidationError(errors)


def _image_format(photo: UploadedFile) -> str | None:
    """The Pillow format name from the file's contents (never its name or content type)."""
    try:
        photo.seek(0)
        with Image.open(photo) as image:
            image_format = image.format
            image.verify()
    except Exception:  # Pillow raises many types for corrupt or non-image data.
        image_format = None
    finally:
        photo.seek(0)
    return image_format


def create_item_listing(
    seller,
    *,
    category: Category,
    title: str,
    price_cents: int,
    condition: str,
    photos: Sequence[UploadedFile],
    description: str = "",
    size: str = "",
    brand: str = "",
    color: str = "",
) -> Listing:
    """Create an Available item listing at the seller's school, with its item details and
    photos in order (the first is the cover)."""
    if seller.school_id is None:
        raise PermissionDenied("Your account isn't linked to a school, so it can't post listings.")
    try:
        validate_item_category(category)
    except ValidationError as exc:
        raise ValidationError({"category": exc.messages}) from exc
    validate_price(category, price_cents)
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise ValidationError(
            {"description": f"Keep the description under {MAX_DESCRIPTION_LENGTH:,} characters."}
        )
    try:
        validate_photos(photos)
    except ValidationError as exc:
        raise ValidationError({"photos": exc.messages}) from exc

    with transaction.atomic():
        listing = Listing(
            school_id=seller.school_id,
            seller=seller,
            kind=ListingKind.ITEM,
            category=category,
            title=title,
            description=description,
            price_cents=price_cents,
            currency="USD",
            status=Listing.Status.AVAILABLE,
        )
        listing.full_clean()
        listing.save()
        details = ItemDetails(
            listing=listing, condition=condition, size=size, brand=brand, color=color
        )
        details.full_clean()
        details.save()
        for position, photo in enumerate(photos):
            _store_photo(listing, photo, position=position)
    return listing


def _store_photo(listing: Listing, photo: UploadedFile, *, position: int) -> ListingPhoto:
    """The one place a listing photo is written to storage. Every upload path (create, and
    later add-photo) goes through here.

    The stored name is random, with the extension of the detected format: the uploader's
    filename can't leak or choose how the file is served (e.g. a valid image named x.html).
    Stores the contents as uploaded for now; re-encoding and EXIF/GPS stripping (#8) go here.
    """
    extension = PHOTO_EXTENSIONS.get(_image_format(photo) or "")
    if extension is None:
        raise ValidationError({"photos": "Photos must be JPEG, PNG or WebP images."})
    listing_photo = ListingPhoto(listing=listing, position=position)
    listing_photo.image.save(f"{uuid4().hex}.{extension}", photo, save=False)
    listing_photo.save()
    return listing_photo


# --- Status ---

Status = Listing.Status


class ListingStatusError(Exception):
    """A status move the rules don't allow (the API maps this to 409 Conflict)."""

    def __init__(self, listing: Listing, action: str):
        self.listing_id = listing.pk
        self.status = listing.status
        self.action = action
        label = Status(listing.status).label
        super().__init__(f"Can't {action} listing {listing.pk}: it is {label}.")


def mark_pending(listing: Listing) -> Listing:
    """Available -> Pending, when the seller accepts a buyer."""
    return _move(listing, "mark as Pending", allowed_from={Status.AVAILABLE}, to=Status.PENDING)


def return_to_available(listing: Listing) -> Listing:
    """Pending -> Available, when a deal falls through or its timer runs out."""
    return _move(listing, "return to Available", allowed_from={Status.PENDING}, to=Status.AVAILABLE)


def mark_sold(listing: Listing) -> Listing:
    """Pending -> Sold, once buyer and seller both confirm the handoff."""
    return _move(listing, "mark as Sold", allowed_from={Status.PENDING}, to=Status.SOLD)


def remove_by_seller(listing: Listing) -> Listing:
    """Available -> Removed by the seller (soft delete). Checking that the caller is
    the seller is the API's job."""
    return _move(
        listing,
        "remove (seller)",
        allowed_from={Status.AVAILABLE},
        to=Status.REMOVED,
        removed_by=Listing.RemovedBy.SELLER,
    )


def remove_by_moderation(listing: Listing) -> Listing:
    """Any listing that isn't already Removed -> Removed by moderation (soft delete)."""
    return _move(
        listing,
        "remove (moderation)",
        allowed_from={Status.AVAILABLE, Status.PENDING, Status.SOLD},
        to=Status.REMOVED,
        removed_by=Listing.RemovedBy.MODERATION,
    )


def _move(
    listing: Listing,
    action: str,
    *,
    allowed_from: set[str],
    to: str,
    removed_by: str = "",
) -> Listing:
    """Lock the row, check the current status in the database (not the possibly stale
    instance passed in), then apply the move. Concurrent callers queue on the lock, so
    the second one sees the first one's result and is rejected."""
    with transaction.atomic():
        locked = Listing.objects.select_for_update().get(pk=listing.pk)
        if locked.status not in allowed_from:
            raise ListingStatusError(locked, action)
        locked.status = to
        if removed_by:
            locked.removed_by = removed_by
            locked.removed_at = timezone.now()
        locked.save(update_fields=["status", "removed_by", "removed_at", "updated_at"])

    # Keep the caller's instance in step with the database.
    for field in ("status", "removed_by", "removed_at", "updated_at"):
        setattr(listing, field, getattr(locked, field))
    return listing
