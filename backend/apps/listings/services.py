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
from io import BytesIO
from typing import NamedTuple
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageOps

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
# Stored photos are re-encoded in the format they arrived in (a multi-picture JPEG keeps only
# its primary picture), in a pixel mode that format can hold. PNG holds any mode.
PHOTO_SAVE_FORMATS = {"JPEG": "JPEG", "MPO": "JPEG", "PNG": "PNG", "WEBP": "WEBP"}
PHOTO_SAVE_MODES = {"JPEG": {"L", "RGB", "CMYK"}, "WEBP": {"RGB", "RGBA"}}
MAX_PHOTO_EDGE = 2048  # px. Longer edges are scaled down; smaller photos are never upscaled.
PHOTO_QUALITY = 85  # JPEG and WebP
# Photo errors, each following "Photo <number> ".
NOT_A_PHOTO = "isn't a JPEG, PNG or WebP image"
DAMAGED_PHOTO = "couldn't be read. It may be damaged; try another photo"
TOO_MANY_PIXELS = "has too many pixels"
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
        elif problem := _photo_problem(photo):
            errors.append(f"Photo {number} {problem}.")
    if errors:
        raise ValidationError(errors)


def _photo_problem(photo: UploadedFile) -> str | None:
    """Why the file can't be a listing photo, judged from its contents (never its name or
    content type), or None. A quick structural check; some damage only shows when the photo is
    decoded and re-encoded (_clean_photo)."""
    image_format = decoded_pixels = None
    try:
        photo.seek(0)
        with Image.open(photo) as image:
            image_format = image.format
            if image_format in {"JPEG", "MPO"} and not image.info.get("progressive"):
                # The size _clean_photo will actually decode at (see draft() there).
                image.draft(None, (MAX_PHOTO_EDGE, MAX_PHOTO_EDGE))
            decoded_pixels = image.width * image.height
            image.verify()
    except Image.DecompressionBombError:
        return TOO_MANY_PIXELS
    except Exception:  # Pillow raises many types for corrupt or non-image data.
        return DAMAGED_PHOTO if image_format in PHOTO_EXTENSIONS else NOT_A_PHOTO
    finally:
        photo.seek(0)
    if image_format not in PHOTO_EXTENSIONS:
        return NOT_A_PHOTO
    # A small file mustn't expand into gigabytes of memory (a decompression bomb). Pillow only
    # warns between its limit (~89 MP) and twice that, so refuse anything that would decode past
    # the limit. Baseline JPEGs decode at reduced scale, so a 108 MP phone photo is fine; a very
    # wide or tall one, or a progressive JPEG, still decodes at full size and is refused.
    if Image.MAX_IMAGE_PIXELS is not None and decoded_pixels > Image.MAX_IMAGE_PIXELS:
        return TOO_MANY_PIXELS
    return None


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
        # Clean every photo before storing any: a file written to storage isn't removed when
        # the transaction rolls back, so a bad photo 2 mustn't fail after photo 1 is stored.
        cleaned = _clean_photos(photos)
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
        for position, photo in enumerate(cleaned):
            _store_photo(listing, photo, position=position)
    return listing


class CleanedPhoto(NamedTuple):
    """A re-encoded photo ready for storage. Only _clean_photo makes these."""

    content: bytes
    extension: str


def _clean_photos(photos: Sequence[UploadedFile]) -> list[CleanedPhoto]:
    """Clean each photo, or raise one ValidationError listing every photo that failed."""
    cleaned, errors = [], []
    for number, photo in enumerate(photos, start=1):
        try:
            cleaned.append(_clean_photo(photo))
        except ValidationError as exc:
            errors.append(f"Photo {number} {exc.message}.")
    if errors:
        raise ValidationError(errors)
    return cleaned


def _store_photo(listing: Listing, photo: CleanedPhoto, *, position: int) -> ListingPhoto:
    """The one place a listing photo is written to storage. Every upload path (create, and
    later add-photo) goes through here, and it only takes a CleanedPhoto, so every stored
    photo has been cleaned.

    The stored name is random, with the extension of the detected format: the uploader's
    filename can't leak or choose how the file is served (e.g. a valid image named x.html).
    """
    listing_photo = ListingPhoto(listing=listing, position=position)
    listing_photo.image.save(
        f"{uuid4().hex}.{photo.extension}", ContentFile(photo.content), save=False
    )
    listing_photo.save()
    return listing_photo


def _clean_photo(photo: UploadedFile) -> CleanedPhoto:
    """Re-encode an uploaded photo for storage and return (contents, extension).

    Rotates it upright from the camera's EXIF orientation, scales the long edge down to
    MAX_PHOTO_EDGE, and writes a fresh file in the same format with no EXIF (GPS), XMP or
    comment metadata; only the ICC colour profile is carried over. Multi-picture JPEGs and
    animated PNG/WebP keep their first picture. Raises ValidationError (message only, no
    field) for anything that isn't a decodable photo.
    """
    if problem := _photo_problem(photo):
        raise ValidationError(problem)
    try:
        with Image.open(photo) as original:
            image_format = original.format
            icc_profile = original.info.get("icc_profile")
            # Lets a large JPEG decode at 1/2, 1/4 or 1/8 scale (never below the cap), which
            # is faster and uses far less memory. A no-op for other formats.
            original.draft(None, (MAX_PHOTO_EDGE, MAX_PHOTO_EDGE))
            image = ImageOps.exif_transpose(original)  # a decoded copy of the first picture
        save_format = PHOTO_SAVE_FORMATS[image_format]
        image = _photo_mode(image, save_format)
        image.thumbnail((MAX_PHOTO_EDGE, MAX_PHOTO_EDGE), Image.Resampling.LANCZOS)
        # Drop everything Pillow might write back from the original (e.g. a JPEG comment);
        # PNG transparency is image data, not metadata.
        image.info = {k: v for k, v in image.info.items() if k == "transparency"}
        options = {"icc_profile": icc_profile} if icc_profile else {}
        if save_format != "PNG":
            options["quality"] = PHOTO_QUALITY
        buffer = BytesIO()
        image.save(buffer, save_format, **options)
    except Exception as exc:  # truncated or otherwise damaged image data
        raise ValidationError(DAMAGED_PHOTO) from exc
    finally:
        photo.seek(0)
    return CleanedPhoto(buffer.getvalue(), PHOTO_EXTENSIONS[image_format])


def _photo_mode(image: Image.Image, save_format: str) -> Image.Image:
    """The image in a pixel mode the output format can hold and that resizes smoothly (1-bit
    and palette images would otherwise be scaled down with nearest-neighbour)."""
    allowed = PHOTO_SAVE_MODES.get(save_format)
    if allowed is None:  # PNG
        if image.mode not in {"1", "P", "PA"} or max(image.size) <= MAX_PHOTO_EDGE:
            return image
    elif image.mode in allowed:
        return image
    if image.mode == "1":
        return image.convert("L")
    if image.has_transparency_data and (allowed is None or "RGBA" in allowed):
        return image.convert("RGBA")
    return image.convert("RGB")


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
