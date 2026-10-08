from allauth.account.models import EmailAddress
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import QuerySet

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
