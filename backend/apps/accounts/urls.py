from django.urls import path

from .views import (
    CurrentUserView,
    FollowUserView,
    PasswordResetKeyStatusView,
    PublicUserView,
    UserSearchView,
)

urlpatterns = [
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path(
        "password-reset/key-status/",
        PasswordResetKeyStatusView.as_view(),
        name="password-reset-key-status",
    ),
    path("users/", UserSearchView.as_view(), name="user-search"),
    path("users/<str:username>/", PublicUserView.as_view(), name="public-user"),
    path("users/<str:username>/follow/", FollowUserView.as_view(), name="follow-user"),
]
