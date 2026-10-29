from django.contrib.auth import logout
from django.db.models import Case, Count, Exists, IntegerField, OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.generics import (
    GenericAPIView,
    ListAPIView,
    RetrieveAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.errors import service_validation_errors
from apps.listings.services import sold_count_annotation

from .models import Follow, User
from .serializers import (
    CurrentUserSerializer,
    DeactivateSerializer,
    DeactivationPreviewSerializer,
    PasswordResetKeyStatusRequestSerializer,
    PasswordResetKeyStatusSerializer,
    PublicUserSerializer,
    ReactivateSerializer,
)
from .services import (
    deactivate_account,
    deactivation_preview,
    follow_user,
    password_reset_key_status,
    reactivate_account,
    unfollow_user,
    verified_users,
)


def follow_count(**filters):
    """A subquery counting the Follow rows that match `filters` (0 when there are none)."""
    follows = Follow.objects.filter(**filters).order_by().values(*filters)
    return Coalesce(Subquery(follows.annotate(total=Count("pk")).values("total")), 0)


def public_users(viewer):
    """Verified users loaded for PublicUserSerializer in a fixed number of queries, however many
    there are: follow and sold counts and the viewer's follow state are annotated."""
    return (
        verified_users()
        .select_related("school")
        .prefetch_related("school__domains")
        .annotate(
            # Deactivated or suspended students don't count toward anyone's follows.
            follower_count=follow_count(following=OuterRef("pk"), follower__is_active=True),
            following_count=follow_count(follower=OuterRef("pk"), following__is_active=True),
            sold_count=sold_count_annotation(),
            is_following=Exists(Follow.objects.filter(follower=viewer, following=OuterRef("pk"))),
        )
    )


class CurrentUserView(RetrieveUpdateAPIView):
    serializer_class = CurrentUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        with service_validation_errors():
            serializer.save()


@extend_schema(
    parameters=[
        OpenApiParameter("q", description="Text to match against usernames and first names."),
        OpenApiParameter(
            "school",
            description='A school slug, or "all". Defaults to the signed-in user\'s school.',
        ),
    ]
)
class UserSearchView(ListAPIView):
    serializer_class = PublicUserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query = self.request.query_params.get("q", "").strip()
        if not query:
            return User.objects.none()
        school_scope = self.request.query_params.get("school")
        users = public_users(self.request.user)
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
        return get_object_or_404(
            public_users(self.request.user), username__iexact=self.kwargs["username"]
        )


class FollowUserView(GenericAPIView):
    serializer_class = PublicUserSerializer
    permission_classes = [IsAuthenticated]

    def get_target(self, username):
        return get_object_or_404(public_users(self.request.user), username__iexact=username)

    @extend_schema(request=None)
    def post(self, request, username):
        target = self.get_target(username)
        with service_validation_errors():
            follow_user(follower=request.user, following=target)
        # Reload so the annotated counts and is_following include the new follow.
        return Response(self.get_serializer(self.get_target(username)).data)

    def delete(self, request, username):
        target = self.get_target(username)
        unfollow_user(follower=request.user, following=target)
        return Response(status=204)


class PasswordResetKeyStatusView(GenericAPIView):
    """Explains a password reset link (valid, expired, used or invalid) so the reset page can
    say why it doesn't work. Checking and using the key stays with allauth's
    /api/auth/.../auth/password/reset. POST, so keys stay out of URLs and access logs."""

    serializer_class = PasswordResetKeyStatusRequestSerializer
    permission_classes = [AllowAny]
    # Signed-out students open reset links; there's no session to protect.
    authentication_classes = []

    @extend_schema(responses=PasswordResetKeyStatusSerializer)
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        status = password_reset_key_status(serializer.validated_data["key"])
        return Response(PasswordResetKeyStatusSerializer({"status": status}).data)


class DeactivationPreviewView(GenericAPIView):
    """What deactivating would do now: deals that must be settled first, open deals that
    would be withdrawn, and listings that would be hidden."""

    serializer_class = DeactivationPreviewSerializer

    def get(self, request):
        return Response(DeactivationPreviewSerializer(deactivation_preview(request.user)).data)


class DeactivateView(GenericAPIView):
    """Close my account after checking my password. Signs me out everywhere."""

    serializer_class = DeactivateSerializer

    @extend_schema(responses={204: None})
    def post(self, request):
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        with service_validation_errors():
            deactivate_account(user=request.user, **payload.validated_data)
        logout(request)
        return Response(status=204)


class ReactivateView(GenericAPIView):
    """Turn a deactivated account back on, before logging in. Same answer for wrong details
    whether or not the account exists; rate limited because it checks passwords signed out."""

    serializer_class = ReactivateSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "reactivate"

    @extend_schema(responses={204: None})
    def post(self, request):
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        with service_validation_errors():
            reactivate_account(**payload.validated_data)
        return Response(status=204)
