from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from .models import School
from .serializers import SchoolSerializer


class SchoolViewSet(viewsets.ReadOnlyModelViewSet):
    """Public directory of schools known to Tanu and their marketplace state."""

    queryset = School.objects.prefetch_related("domains").all()
    serializer_class = SchoolSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"
