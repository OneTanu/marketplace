from django.urls import path

from . import views

urlpatterns = [
    path("notifications/", views.NotificationListView.as_view(), name="notification-list"),
    path(
        "notifications/unread-count/",
        views.UnreadCountView.as_view(),
        name="notification-unread-count",
    ),
    path("notifications/read/", views.MarkReadView.as_view(), name="notification-read"),
    path("saved-searches/", views.SavedSearchListView.as_view(), name="saved-search-list"),
    path(
        "saved-searches/<int:pk>/",
        views.SavedSearchDetailView.as_view(),
        name="saved-search-detail",
    ),
]
