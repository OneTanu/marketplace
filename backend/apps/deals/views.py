from contextlib import contextmanager

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.exceptions import APIException
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.response import Response

from apps.listings.models import Listing, ListingPhoto

from . import services
from .models import Deal
from .serializers import AmountSerializer, CreateDealSerializer, DealQuerySerializer, DealSerializer


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This deal's status no longer allows that action."
    default_code = "conflict"


@contextmanager
def service_errors():
    try:
        yield
    except DjangoValidationError as exc:
        if hasattr(exc, "error_dict"):
            raise serializers.ValidationError(exc.message_dict) from exc
        raise serializers.ValidationError({"detail": " ".join(exc.messages)}) from exc
    except services.DealStateError as exc:
        raise Conflict(str(exc)) from exc


def deal_queryset(user):
    cover = ListingPhoto.objects.filter(position=0)
    return (
        Deal.objects.filter(Q(buyer=user) | Q(seller=user))
        .select_related("listing__school", "buyer", "seller", "conversation")
        .prefetch_related(
            Prefetch("listing__photos", queryset=cover, to_attr="deal_cover_photos"),
            "offers__offered_by",
            "events__actor",
            "confirmations",
        )
    )


@extend_schema(parameters=[DealQuerySerializer])
class DealListView(ListAPIView):
    serializer_class = DealSerializer

    def get_queryset(self):
        deals = deal_queryset(self.request.user)
        query = DealQuerySerializer(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        conversation = query.validated_data.get("conversation")
        if conversation:
            deals = deals.filter(conversation_id=conversation)
        return deals


class ListingDealCreateView(GenericAPIView):
    serializer_class = CreateDealSerializer

    @extend_schema(responses={201: DealSerializer})
    def post(self, request, listing_id):
        listing = get_object_or_404(Listing, pk=listing_id)
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        with service_errors():
            deal = services.create_deal(
                listing=listing, buyer=request.user, **payload.validated_data
            )
        return Response(
            DealSerializer(
                deal_queryset(request.user).get(pk=deal.pk), context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED,
        )


class DealDetailView(RetrieveAPIView):
    serializer_class = DealSerializer

    def get_queryset(self):
        return deal_queryset(self.request.user)


class DealActionView(GenericAPIView):
    serializer_class = DealSerializer
    action = None

    def post(self, request, pk):
        deal = get_object_or_404(deal_queryset(request.user), pk=pk)
        with service_errors():
            getattr(services, self.action)(deal=deal, actor=request.user)
        refreshed = deal_queryset(request.user).get(pk=deal.pk)
        return Response(self.get_serializer(refreshed).data)


class AcceptDealView(DealActionView):
    action = "accept_deal"


class DeclineDealView(DealActionView):
    action = "decline_deal"


class CancelDealView(DealActionView):
    action = "cancel_deal"


class ConfirmHandoffView(DealActionView):
    action = "confirm_handoff"


class CounterOfferView(GenericAPIView):
    serializer_class = AmountSerializer

    @extend_schema(responses={200: DealSerializer})
    def post(self, request, pk):
        deal = get_object_or_404(deal_queryset(request.user), pk=pk)
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        with service_errors():
            services.counter_offer(deal=deal, actor=request.user, **payload.validated_data)
        refreshed = deal_queryset(request.user).get(pk=deal.pk)
        return Response(DealSerializer(refreshed, context={"request": request}).data)
