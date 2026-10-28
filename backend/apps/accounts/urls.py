from django.urls import path

from .views import (
    CurrentUserView,
    DeactivateView,
    DeactivationPreviewView,
    FollowUserView,
    PasswordResetKeyStatusView,
    PublicUserView,
    ReactivateView,
    UserSearchView,
)

urlpatterns = [
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("me/deactivation/", DeactivationPreviewView.as_view(), name="deactivation-preview"),
    path("me/deactivate/", DeactivateView.as_view(), name="deactivate-account"),
    path("account/reactivate/", ReactivateView.as_view(), name="reactivate-account"),
    path(
        "password-reset/key-status/",
        PasswordResetKeyStatusView.as_view(),
        name="password-reset-key-status",
    ),
    path("users/", UserSearchView.as_view(), name="user-search"),
    path("users/<str:username>/", PublicUserView.as_view(), name="public-user"),
    path("users/<str:username>/follow/", FollowUserView.as_view(), name="follow-user"),
]
