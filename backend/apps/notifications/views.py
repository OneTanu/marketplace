from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response

from . import services
from .models import Notification
from .serializers import (
    NotificationMarkReadSerializer,
    NotificationSerializer,
    NotificationUnreadCountSerializer,
)


class NotificationListView(ListAPIView):
    """My latest notifications, newest first."""

    serializer_class = NotificationSerializer
    pagination_class = None

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)[:50]


class UnreadCountView(GenericAPIView):
    serializer_class = NotificationUnreadCountSerializer

    def get(self, request):
        return Response({"unread": services.unread(request.user).count()})


class MarkReadView(GenericAPIView):
    serializer_class = NotificationMarkReadSerializer

    @extend_schema(responses={200: NotificationUnreadCountSerializer})
    def post(self, request):
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.mark_read(request.user, payload.validated_data.get("ids"))
        return Response({"unread": services.unread(request.user).count()})
