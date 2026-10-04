from django.urls import path

from .views import CurrentUserView, FollowUserView, PublicUserView, UserSearchView

urlpatterns = [
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("users/", UserSearchView.as_view(), name="user-search"),
    path("users/<str:username>/", PublicUserView.as_view(), name="public-user"),
    path("users/<str:username>/follow/", FollowUserView.as_view(), name="follow-user"),
]
