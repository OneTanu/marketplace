from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Category, Listing, ListingKind
from .serializers import CategorySerializer, ListingCreateSerializer, ListingSerializer

# Views only translate HTTP to and from Listings services. Every endpoint requires a signed-in
# user (REST_FRAMEWORK defaults); allauth's mandatory verification means they're verified.


def listing_queryset():
    return Listing.objects.select_related(
        "category", "school", "seller", "item_details"
    ).prefetch_related("photos")


@extend_schema(
    parameters=[
        OpenApiParameter("kind", enum=ListingKind.values, description="Only this listing kind.")
    ]
)
class CategoryListView(generics.ListAPIView):
    """Active categories, optionally for one listing kind."""

    serializer_class = CategorySerializer

    def get_queryset(self):
        categories = Category.objects.filter(is_active=True)
        kind = self.request.query_params.get("kind")
        if kind is not None:
            if kind not in ListingKind.values:
                raise serializers.ValidationError({"kind": f'"{kind}" is not a listing kind.'})
            categories = categories.filter(kind=kind)
        return categories


class ListingCreateView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request={"multipart/form-data": ListingCreateSerializer},
        responses={201: ListingSerializer},
    )
    def post(self, request):
        """Post an item listing at the seller's school. Photos are sent as repeated `photos`
        files, in order."""
        serializer = ListingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            listing = services.create_item_listing(request.user, **serializer.validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(serializers.as_serializer_error(exc)) from exc
        return Response(
            ListingSerializer(listing_queryset().get(pk=listing.pk)).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    parameters=[
        OpenApiParameter(
            "status", enum=Listing.Status.values, description="Only listings with this status."
        )
    ]
)
class MyListingsView(generics.ListAPIView):
    """The signed-in seller's own listings, newest first."""

    serializer_class = ListingSerializer

    def get_queryset(self):
        # Removed listings are left out for now. #11 adds removed_by and changes this to:
        # exclude seller-removed listings, include moderation-removed ones (with a notice).
        listings = (
            listing_queryset()
            .filter(seller=self.request.user)
            .exclude(status=Listing.Status.REMOVED)
            .order_by("-created_at", "-id")
        )
        listing_status = self.request.query_params.get("status")
        if listing_status is not None:
            if listing_status not in Listing.Status.values:
                raise serializers.ValidationError(
                    {"status": f'"{listing_status}" is not a listing status.'}
                )
            listings = listings.filter(status=listing_status)
        return listings


class ListingDetailView(generics.RetrieveAPIView):
    """Any signed-in student can fetch a listing, whatever its school."""

    serializer_class = ListingSerializer

    def get_queryset(self):
        return listing_queryset()
