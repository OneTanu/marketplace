from allauth.account.forms import UserTokenForm
from allauth.account.models import EmailAddress
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.http import base36_to_int

from .models import Follow, User, normalize_instagram_handle

INSTAGRAM_HANDLE_TAKEN = "This Instagram handle is already connected to another Tanu account."


def verified_users() -> QuerySet[User]:
    """Active users with a verified email: the students others can find, follow and message."""
    verified_ids = EmailAddress.objects.filter(verified=True).values("user_id")
    return User.objects.filter(is_active=True, id__in=verified_ids)


def update_profile(
    user: User, *, instagram_handle: str | None = None, profile_description: str | None = None
) -> User:
    """Update the user's editable profile fields; a field left as None is unchanged. The
    Instagram handle is normalized and may belong to only one account (blank clears it)."""
    update_fields = []
    if instagram_handle is not None:
        try:
            handle = normalize_instagram_handle(instagram_handle)
        except ValidationError as error:
            raise ValidationError({"instagram_handle": error.messages}) from error
        taken = User.objects.exclude(pk=user.pk).filter(instagram_handle__iexact=handle)
        if handle and taken.exists():
            raise ValidationError({"instagram_handle": INSTAGRAM_HANDLE_TAKEN})
        user.instagram_handle = handle
        update_fields.append("instagram_handle")
    if profile_description is not None:
        user.profile_description = profile_description.strip()
        update_fields.append("profile_description")
    try:
        with transaction.atomic():
            user.save(update_fields=update_fields)
    except IntegrityError as error:
        # Another account took the handle between the check above and the save.
        if "accounts_user_instagram_ci_unique" in str(error):
            raise ValidationError({"instagram_handle": INSTAGRAM_HANDLE_TAKEN}) from error
        raise
    return user


def follow_user(*, follower: User, following: User) -> Follow:
    if follower.pk == following.pk:
        raise ValidationError("You cannot follow yourself.")
    relationship, _ = Follow.objects.get_or_create(follower=follower, following=following)
    return relationship


def unfollow_user(*, follower: User, following: User) -> None:
    Follow.objects.filter(follower=follower, following=following).delete()


def set_account_active(user: User, active: bool) -> User:
    """Switch an account off (a suspension or ban) or back on. Django won't sign an inactive
    user in, and treats their existing sessions as signed out on the next request."""
    User.objects.filter(pk=user.pk).update(is_active=active)
    user.is_active = active
    return user


def password_reset_key_status(key: str) -> str:
    """Why a password reset link from allauth works or not: "valid", "expired", "used" or
    "invalid". allauth (which checks and uses the key) rejects every bad key with the same
    error; this only tells the student which one so the page can explain it.

    allauth's key is "<uidb36>-<timestamp>-<hash>" (Django's token generator). A well-formed
    key that is past PASSWORD_RESET_TIMEOUT is "expired". One that is still fresh but fails
    the check is "used": its hash covers the password and last login, so it stops working
    once the password changes or the student logs in. That answer never depends on whether
    the uid matches a user, so a key can't be used to probe which accounts exist.
    """
    uidb36, _, token = key.partition("-")
    ts_b36, _, token_hash = token.partition("-")
    try:
        timestamp = base36_to_int(ts_b36)
    except ValueError:
        return "invalid"
    if not uidb36 or not token_hash:
        return "invalid"
    if UserTokenForm(data={"uidb36": uidb36, "key": token}).is_valid():
        return "valid"
    generator = UserTokenForm.token_generator
    now = generator._num_seconds(generator._now())  # the generator's own clock
    if now - timestamp > settings.PASSWORD_RESET_TIMEOUT:
        return "expired"
    return "used"


# --- Deactivation (closing your own account) ---
#
# Deactivating switches the account off (signed out everywhere) and hides the student's
# Available listings, after withdrawing them from every open deal the state machine lets them
# leave. Deals with a handoff confirmation or a dispute can't be left, so they block it.
# Nothing is deleted: completed deals, messages, reviews, reports, and moderation records stay.
# Signing in again reactivates the account, unless moderation has suspended or banned it.
# Other apps are imported inside the functions: Deals imports this module.

REACTIVATION_REFUSED = "We couldn't reactivate an account with that email and password."


def deactivation_blockers(user: User):
    """Deals that must be settled before deactivating: Pending with a handoff confirmation
    (which can't be canceled) or disputed (a moderator is deciding)."""
    from apps.deals.models import Deal

    status = Deal.Status
    return (
        Deal.objects.filter(Q(buyer=user) | Q(seller=user))
        .filter(Q(status=status.DISPUTED) | Q(status=status.PENDING, confirmations__isnull=False))
        .select_related("listing", "buyer", "seller")
        .distinct()
    )


def deactivation_preview(user: User) -> dict:
    """What deactivating would do right now, for the confirmation screen."""
    from apps.deals.models import Deal
    from apps.deals.services import OPEN_STATUSES
    from apps.listings.models import Listing

    blockers = list(deactivation_blockers(user))
    open_deals = Deal.objects.filter(
        Q(buyer=user) | Q(seller=user), status__in=OPEN_STATUSES
    ).exclude(pk__in=[deal.pk for deal in blockers])
    listings = Listing.objects.filter(
        seller=user, status__in=[Listing.Status.AVAILABLE, Listing.Status.PENDING]
    )
    return {
        "blockers": blockers,
        "open_deals": open_deals.count(),
        "listings_to_hide": listings.count(),
    }


def _withdraw_from_open_deals(user: User) -> None:
    """Leave every open deal the state machine allows. Canceling a Pending sale can promote the
    next backup buyer into a fresh request for this student's listing, so repeat until nothing
    changes."""
    from apps.deals import services as deal_services
    from apps.deals.models import Deal

    previous: set[int] | None = None
    while True:
        open_ids = set(
            Deal.objects.filter(
                Q(buyer=user) | Q(seller=user), status__in=deal_services.OPEN_STATUSES
            ).values_list("pk", flat=True)
        )
        if not open_ids or open_ids == previous:
            return
        previous = open_ids
        for deal in Deal.objects.filter(pk__in=open_ids):
            try:
                deal_services.cancel_deal(deal=deal, actor=user)
            except (deal_services.DealStateError, ValidationError):
                # Its deadline passed and it settled as we went, or it now needs a
                # moderator; whatever is still open is reported below.
                continue


@transaction.atomic
def deactivate_account(*, user: User, password: str, reason: str = "") -> User:
    """Close your own account: withdraw from open deals, hide Available listings, sign out
    everywhere. Refused while a confirmed or disputed deal is unsettled."""
    from apps.deals.models import Deal
    from apps.deals.services import OPEN_STATUSES
    from apps.listings import services as listing_services
    from apps.listings.models import Listing
    from apps.notifications import services as notification_services

    if not user.check_password(password):
        raise ValidationError({"password": "That password isn't right."})
    if not user.is_active or user.deactivated_at is not None:
        raise ValidationError("This account is already deactivated.")
    unsettled = "Finish or resolve your confirmed or disputed deals before deactivating."
    if deactivation_blockers(user).exists():
        raise ValidationError(unsettled)

    _withdraw_from_open_deals(user)
    if Deal.objects.filter(Q(buyer=user) | Q(seller=user), status__in=OPEN_STATUSES).exists():
        raise ValidationError(unsettled)
    for listing in Listing.objects.filter(seller=user, status=Listing.Status.AVAILABLE):
        listing_services.hide_for_deactivation(listing)

    user.deactivated_at = timezone.now()
    user.deactivation_reason = reason.strip()[:500]
    user.is_active = False
    user.save(update_fields=["deactivated_at", "deactivation_reason", "is_active"])
    notification_services.notify(
        user,
        kind=notification_services.Kind.ACCOUNT,
        title="Your Tanu account is deactivated",
        body=(
            "Your profile and listings are hidden and you've been signed out everywhere. "
            "To come back, log in again with your school email and password; your listings "
            "will be available again."
        ),
        email=True,
    )
    return user


@transaction.atomic
def reactivate_account(*, email: str, password: str) -> User:
    """Turn a self-deactivated account back on after checking its password. Accounts switched
    off by moderation stay off. Wrong details get the same answer whether or not the account
    exists."""
    from apps.listings import services as listing_services
    from apps.notifications import services as notification_services
    from apps.trust import checks

    user = User.objects.filter(email__iexact=email.strip()).first()
    if user is None or not user.check_password(password):
        raise ValidationError(REACTIVATION_REFUSED)
    if user.is_active:
        return user
    off = checks.active_restrictions(user).filter(
        kind__in=[checks.Kind.SUSPENSION, checks.Kind.BAN]
    )
    if user.deactivated_at is None or off.exists():
        raise ValidationError(
            "This account can't be reactivated. Check your email for messages from Tanu."
        )
    user.is_active = True
    user.deactivated_at = None
    user.save(update_fields=["is_active", "deactivated_at"])
    listing_services.restore_after_reactivation(user)
    notification_services.notify(
        user,
        kind=notification_services.Kind.ACCOUNT,
        title="Welcome back",
        body="Your account is active again, and your hidden listings are back.",
    )
    return user
