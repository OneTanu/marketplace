from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import School
from .serializers import MeetingSpotSerializer, SchoolSerializer


class SchoolViewSet(viewsets.ReadOnlyModelViewSet):
    """Public directory of schools known to Tanu and their marketplace state."""

    queryset = School.objects.prefetch_related("domains").all()
    serializer_class = SchoolSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"

    @extend_schema(responses=MeetingSpotSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="meeting-spots")
    def meeting_spots(self, request, slug=None):
        school = self.get_object()
        spots = school.meeting_spots.filter(is_active=True)
        return Response(MeetingSpotSerializer(spots, many=True).data)
