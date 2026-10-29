from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response

from apps.errors import service_validation_errors

from . import services
from .models import Notification, SavedSearch
from .serializers import (
    NotificationMarkReadSerializer,
    NotificationSerializer,
    NotificationUnreadCountSerializer,
    SavedSearchCreateSerializer,
    SavedSearchFiltersSerializer,
    SavedSearchSerializer,
    SavedSearchUpdateSerializer,
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


class SavedSearchListView(GenericAPIView):
    serializer_class = SavedSearchSerializer

    @extend_schema(operation_id="saved_searches_list", responses=SavedSearchSerializer(many=True))
    def get(self, request):
        """My saved searches, newest first (at most 25, so not paged)."""
        searches = SavedSearch.objects.filter(user=request.user).select_related(
            "school", "category"
        )
        return Response(self.get_serializer(searches, many=True).data)

    @extend_schema(request=SavedSearchCreateSerializer, responses={201: SavedSearchSerializer})
    def post(self, request):
        """Save the current feed filters. 400 if nothing is filtered, the same filters are
        already saved, or you already have 25 saved searches."""
        payload = SavedSearchCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        filters = SavedSearchFiltersSerializer.service_kwargs(payload.validated_data["filters"])
        with service_validation_errors():
            search = services.create_saved_search(
                request.user,
                name=payload.validated_data["name"],
                alerts_enabled=payload.validated_data["alerts_enabled"],
                **filters,
            )
        return Response(self.get_serializer(search).data, status=status.HTTP_201_CREATED)


class SavedSearchDetailView(GenericAPIView):
    serializer_class = SavedSearchSerializer

    def get_object(self):
        # Someone else's search is a 404, as if it didn't exist.
        return get_object_or_404(
            SavedSearch.objects.select_related("school", "category"),
            pk=self.kwargs["pk"],
            user=self.request.user,
        )

    def get(self, request, pk):
        return Response(self.get_serializer(self.get_object()).data)

    @extend_schema(request=SavedSearchUpdateSerializer)
    def patch(self, request, pk):
        """Rename a saved search or turn its alerts on or off."""
        search = self.get_object()
        payload = SavedSearchUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        with service_validation_errors():
            services.update_saved_search(search, request.user, **payload.validated_data)
        return Response(self.get_serializer(search).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        services.delete_saved_search(self.get_object(), request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
