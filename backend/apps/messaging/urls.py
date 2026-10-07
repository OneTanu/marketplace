from django.urls import path

from .views import (
    ConversationDetailView,
    ConversationListCreateView,
    ConversationMessageView,
    MarkConversationReadView,
    UnreadCountView,
)

urlpatterns = [
    path("conversations/", ConversationListCreateView.as_view(), name="conversation-list"),
    path(
        "conversations/unread-count/", UnreadCountView.as_view(), name="conversation-unread-count"
    ),
    path("conversations/<int:pk>/", ConversationDetailView.as_view(), name="conversation-detail"),
    path(
        "conversations/<int:pk>/messages/",
        ConversationMessageView.as_view(),
        name="conversation-messages",
    ),
    path(
        "conversations/<int:pk>/read/", MarkConversationReadView.as_view(), name="conversation-read"
    ),
]
