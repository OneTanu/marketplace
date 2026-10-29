"""Read-only checks other apps call before letting a student act: restrictions and blocks.

Kept apart from services.py (which calls Deals and Listings) so those apps can import it
without a circular import.
"""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Case, F, Q, QuerySet, When
from django.utils import timezone

from .models import BannedEmail, Block, UserRestriction

Kind = UserRestriction.Kind

# What each restriction stops, in words a student sees.
_STOPS = {
    Kind.SELLING: "post or sell items",
    Kind.MESSAGING: "send messages",
    Kind.DEALS: "make or answer requests",
}


class Restricted(PermissionDenied):
    """A student tried something a moderator has restricted. Carries a code and end time so
    the app can explain it ("Your selling privileges are paused until Oct 20")."""

    def __init__(self, restriction: UserRestriction):
        self.restriction = restriction
        self.code = f"restricted_{restriction.kind}"
        self.expires_at = restriction.expires_at
        until = (
            f" until {timezone.localtime(restriction.expires_at):%b %-d, %-I:%M %p}"
            if restriction.expires_at
            else ""
        )
        doing = _STOPS.get(restriction.kind, "use Tanu")
        super().__init__(f"Your account can't {doing}{until} after a moderation review.")


def active_restrictions(user=None) -> QuerySet[UserRestriction]:
    restrictions = UserRestriction.objects.filter(lifted_at__isnull=True).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    )
    return restrictions if user is None else restrictions.filter(user=user)


def require_can(user, kind: str) -> None:
    """Raise Restricted if `user` has an active restriction of `kind`, or is suspended or
    banned."""
    restriction = (
        active_restrictions(user)
        .filter(kind__in=[kind, Kind.SUSPENSION, Kind.BAN])
        .order_by("-expires_at")
        .first()
    )
    if restriction is not None:
        raise Restricted(restriction)


def has_active(user, kind: str) -> bool:
    return active_restrictions(user).filter(kind=kind).exists()


def hidden_seller_ids():
    """Sellers whose listings are hidden from browsing: restricted from selling, suspended,
    or banned. A subquery of user ids."""
    return (
        active_restrictions()
        .filter(kind__in=[Kind.SELLING, Kind.SUSPENSION, Kind.BAN])
        .values("user_id")
    )


def is_blocked(first, second) -> bool:
    return Block.objects.filter(
        Q(blocker=first, blocked=second) | Q(blocker=second, blocked=first)
    ).exists()


def blocked_either_way_ids(user_id: int):
    """Ids of users who blocked `user_id` or whom they blocked. A subquery."""
    return (
        Block.objects.filter(Q(blocker_id=user_id) | Q(blocked_id=user_id))
        .annotate(
            other=Case(When(blocker_id=user_id, then=F("blocked_id")), default=F("blocker_id"))
        )
        .values("other")
    )


def require_not_blocked(first, second) -> None:
    """Neutral on purpose: a blocked student is never told they were blocked."""
    if is_blocked(first, second):
        raise ValidationError("This action isn't available.")


def email_is_banned(email: str, school) -> bool:
    local_part = email.rsplit("@", 1)[0].strip().lower()
    return BannedEmail.objects.filter(school=school, local_part=local_part).exists()
