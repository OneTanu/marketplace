from allauth.account.models import EmailAddress
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    GenericAPIView,
    ListAPIView,
    RetrieveAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import User
from .serializers import CurrentUserSerializer, PublicUserSerializer
from .services import follow_user, unfollow_user


def public_users():
    verified_ids = EmailAddress.objects.filter(verified=True).values("user_id")
    return User.objects.filter(is_active=True, id__in=verified_ids).select_related("school")


class CurrentUserView(RetrieveUpdateAPIView):
    serializer_class = CurrentUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserSearchView(ListAPIView):
    serializer_class = PublicUserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query = self.request.query_params.get("q", "").strip()
        if not query:
            return User.objects.none()
        school_scope = self.request.query_params.get("school")
        users = public_users()
        if school_scope == "all":
            pass
        elif school_scope:
            users = users.filter(school__slug=school_scope)
        elif self.request.user.school_id:
            users = users.filter(school_id=self.request.user.school_id)
        else:
            return User.objects.none()
        return (
            users.filter(Q(username__icontains=query) | Q(first_name__icontains=query))
            .annotate(
                exact_username=Case(
                    When(username__iexact=query, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            )
            .order_by("exact_username", "username")[:25]
        )


class PublicUserView(RetrieveAPIView):
    serializer_class = PublicUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return get_object_or_404(public_users(), username__iexact=self.kwargs["username"])


class FollowUserView(GenericAPIView):
    serializer_class = PublicUserSerializer
    permission_classes = [IsAuthenticated]

    def get_target(self, username):
        return get_object_or_404(public_users(), username__iexact=username)

    def post(self, request, username):
        target = self.get_target(username)
        try:
            follow_user(follower=request.user, following=target)
        except DjangoValidationError as error:
            raise ValidationError({"detail": error.message}) from error
        return Response(self.get_serializer(target).data)

    def delete(self, request, username):
        target = self.get_target(username)
        unfollow_user(follower=request.user, following=target)
        return Response(status=204)
