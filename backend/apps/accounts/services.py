from django.core.exceptions import ValidationError

from .models import Follow, User


def follow_user(*, follower: User, following: User) -> Follow:
    if follower.pk == following.pk:
        raise ValidationError("You cannot follow yourself.")
    relationship, _ = Follow.objects.get_or_create(follower=follower, following=following)
    return relationship


def unfollow_user(*, follower: User, following: User) -> None:
    Follow.objects.filter(follower=follower, following=following).delete()
