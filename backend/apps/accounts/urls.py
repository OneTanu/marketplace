from django.urls import path

from .views import (
    CurrentUserView,
    DeactivateView,
    DeactivationPreviewView,
    FollowListView,
    FollowUserView,
    PasswordResetKeyStatusView,
    ProfilePhotoView,
    PublicUserView,
    ReactivateView,
    UserSearchView,
)

urlpatterns = [
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("me/photo/", ProfilePhotoView.as_view(), name="profile-photo"),
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
    path(
        "users/<str:username>/followers/",
        FollowListView.as_view(direction="followers"),
        name="user-followers",
    ),
    path(
        "users/<str:username>/following/",
        FollowListView.as_view(direction="following"),
        name="user-following",
    ),
]
