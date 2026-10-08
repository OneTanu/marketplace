from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.generics import (
    GenericAPIView,
    ListAPIView,
    RetrieveAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.errors import service_validation_errors

from .models import User
from .serializers import CurrentUserSerializer, PublicUserSerializer
from .services import follow_user, unfollow_user, verified_users


def public_users():
    return verified_users().select_related("school")


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

    @extend_schema(request=None)
    def post(self, request, username):
        target = self.get_target(username)
        with service_validation_errors():
            follow_user(follower=request.user, following=target)
        return Response(self.get_serializer(target).data)

    def delete(self, request, username):
        target = self.get_target(username)
        unfollow_user(follower=request.user, following=target)
        return Response(status=204)
