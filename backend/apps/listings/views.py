from contextlib import contextmanager

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, serializers, status
from rest_framework.exceptions import APIException
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Category, Listing, ListingKind, ListingPhoto
from .serializers import (
    CategorySerializer,
    ListingCreateSerializer,
    ListingPhotoOrderSerializer,
    ListingPhotoUploadSerializer,
    ListingSerializer,
    ListingUpdateSerializer,
)

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


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The listing's status doesn't allow this."
    default_code = "conflict"


NOT_AVAILABLE = OpenApiResponse(description="The listing isn't Available, so it can't be edited.")


@contextmanager
def service_errors():
    """Turn Listings services' errors into API errors: field errors are 400 and status
    conflicts are 409. (DRF already makes PermissionDenied a 403 and Http404 a 404.)"""
    try:
        yield
    except DjangoValidationError as exc:
        raise serializers.ValidationError(nested(serializers.as_serializer_error(exc))) from exc
    except services.ListingStatusError as exc:
        label = Listing.Status(exc.status).label
        raise Conflict(f"This listing is {label}. Only Available listings can be edited.") from exc


def nested(errors: dict) -> dict:
    """Services key nested fields' errors by path ("item_details.condition"); the API nests
    them the way DRF reports a nested serializer's errors ({"item_details": {"condition": ...}})."""
    result = {}
    for key, messages in errors.items():
        parent, dot, child = key.partition(".")
        if dot:
            result.setdefault(parent, {})[child] = messages
        else:
            result[key] = messages
    return result


def listing_to_edit(request, pk) -> Listing:
    """The listing a write request is for, checked for seller (403) and Available (409) before
    any field errors are reported. A Removed listing looks missing to everyone but its seller.
    The services check again on the locked row."""
    listing = get_object_or_404(Listing, pk=pk)
    if listing.status == Listing.Status.REMOVED and listing.seller_id != request.user.pk:
        raise Http404
    with service_errors():
        services.check_can_edit(listing, request.user)
    return listing


def listing_response(listing: Listing, status_code=status.HTTP_200_OK) -> Response:
    return Response(ListingSerializer(listing_queryset().get(pk=listing.pk)).data, status_code)


class ListingDetailView(generics.RetrieveAPIView):
    """Any signed-in student can fetch a listing, whatever its school."""

    serializer_class = ListingSerializer
    parser_classes = [JSONParser]

    def get_queryset(self):
        return listing_queryset()

    @extend_schema(
        request=ListingUpdateSerializer,
        responses={200: ListingSerializer, 409: NOT_AVAILABLE},
    )
    def patch(self, request, pk):
        """Edit an Available listing (seller only). Send only the fields that change; item
        details go in a nested `item_details` object."""
        listing = listing_to_edit(request, pk)
        serializer = ListingUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with service_errors():
            services.update_item_listing(listing, request.user, **serializer.validated_data)
        return listing_response(listing)


class ListingPhotosView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request={"multipart/form-data": ListingPhotoUploadSerializer},
        responses={201: ListingSerializer, 409: NOT_AVAILABLE},
    )
    def post(self, request, pk):
        """Add one photo to an Available listing (seller only), after its other photos.
        A listing has at most 10 photos. Returns the whole listing."""
        listing = listing_to_edit(request, pk)
        serializer = ListingPhotoUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with service_errors():
            services.add_photo(listing, request.user, serializer.validated_data["photo"])
        return listing_response(listing, status.HTTP_201_CREATED)


class ListingPhotoDetailView(APIView):
    @extend_schema(responses={200: ListingSerializer, 409: NOT_AVAILABLE})
    def delete(self, request, pk, photo_id):
        """Delete a photo from an Available listing (seller only). A listing's last photo
        can't be deleted. Later photos move up. Returns the whole listing."""
        listing = listing_to_edit(request, pk)
        with service_errors():
            try:
                services.delete_photo(listing, request.user, photo_id)
            except ListingPhoto.DoesNotExist as exc:
                raise Http404 from exc
        return listing_response(listing)


class ListingPhotoOrderView(APIView):
    parser_classes = [JSONParser]

    @extend_schema(
        request=ListingPhotoOrderSerializer,
        responses={200: ListingSerializer, 409: NOT_AVAILABLE},
    )
    def put(self, request, pk):
        """Reorder an Available listing's photos (seller only). Returns the whole listing."""
        listing = listing_to_edit(request, pk)
        serializer = ListingPhotoOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with service_errors():
            services.reorder_photos(listing, request.user, serializer.validated_data["photo_ids"])
        return listing_response(listing)
