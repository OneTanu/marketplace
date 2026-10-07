"""Listings services: the only code that changes a listing's status.

Deals, moderation and (later) the listings API call these functions and never set
`status` themselves. The allowed moves are:

    Available -> Pending    mark_pending (Deals: seller accepted a buyer)
    Pending   -> Available  return_to_available (Deals: fell through or timed out)
    Pending   -> Sold       mark_sold (Deals: both sides confirmed the handoff)
    Available -> Removed    remove_by_seller, remove_by_moderation
    Pending   -> Removed    remove_by_moderation
    Sold      -> Removed    remove_by_moderation

Any other move raises ListingStatusError and leaves the listing unchanged.
"""

from django.db import transaction
from django.utils import timezone

from .models import Listing

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
