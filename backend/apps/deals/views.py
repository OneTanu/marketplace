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
from apps.schools.models import MeetingSpot
from apps.schools.serializers import MeetingSpotSerializer

from . import services
from .models import Deal, MeetupPreference, MeetupProposal
from .serializers import (
    AcceptDealSerializer,
    CounterOfferSerializer,
    CreateDealSerializer,
    DealQuerySerializer,
    DealSerializer,
    MeetupOptionsSerializer,
    MeetupPreferenceSerializer,
    MeetupPreferenceUpdateSerializer,
    MeetupProposalAcceptSerializer,
    MeetupProposalCreateSerializer,
    MeetupProposalSerializer,
    MeetupStatusCreateSerializer,
    MeetupStatusUpdateSerializer,
)


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
            "meetup_proposals__proposed_by",
            "meetup_proposals__meeting_spot",
            "meetup_updates__actor",
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
        validated = dict(payload.validated_data)
        meeting_spot_id = validated.pop("meeting_spot_id", None)
        meeting_spot = (
            get_object_or_404(MeetingSpot, pk=meeting_spot_id)
            if meeting_spot_id is not None
            else None
        )
        with service_errors():
            deal = services.create_deal(
                listing=listing,
                buyer=request.user,
                meeting_spot=meeting_spot,
                **validated,
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
    serializer_class = AcceptDealSerializer
    action = "accept_deal"

    @extend_schema(responses={200: DealSerializer})
    def post(self, request, pk):
        deal = get_object_or_404(deal_queryset(request.user), pk=pk)
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        proposal_id = payload.validated_data.get("meetup_proposal_id")
        proposal = (
            get_object_or_404(deal.meetup_proposals, pk=proposal_id)
            if proposal_id is not None
            else None
        )
        with service_errors():
            services.accept_deal(deal=deal, actor=request.user, meetup_proposal=proposal)
        refreshed = deal_queryset(request.user).get(pk=deal.pk)
        return Response(DealSerializer(refreshed, context={"request": request}).data)


class DeclineDealView(DealActionView):
    action = "decline_deal"


class CancelDealView(DealActionView):
    action = "cancel_deal"


class ConfirmHandoffView(DealActionView):
    action = "confirm_handoff"


class CounterOfferView(GenericAPIView):
    serializer_class = CounterOfferSerializer

    @extend_schema(responses={200: DealSerializer})
    def post(self, request, pk):
        deal = get_object_or_404(deal_queryset(request.user), pk=pk)
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        proposal_id = payload.validated_data.get("meetup_proposal_id")
        proposal = (
            get_object_or_404(deal.meetup_proposals, pk=proposal_id)
            if proposal_id is not None
            else None
        )
        with service_errors():
            services.counter_offer(
                deal=deal,
                actor=request.user,
                amount_cents=payload.validated_data["amount_cents"],
                meetup_proposal=proposal,
            )
        refreshed = deal_queryset(request.user).get(pk=deal.pk)
        return Response(DealSerializer(refreshed, context={"request": request}).data)


class MeetupPreferenceView(GenericAPIView):
    serializer_class = MeetupPreferenceUpdateSerializer

    @extend_schema(responses={200: MeetupPreferenceSerializer})
    def get(self, request):
        preference = (
            MeetupPreference.objects.filter(user=request.user)
            .prefetch_related(
                "meeting_spots",
                "availability_windows",
                "availability_overrides",
            )
            .first()
        )
        if preference is None:
            return Response(
                {
                    "meeting_spots": [],
                    "availability_windows": [],
                    "availability_overrides": [],
                    "updated_at": None,
                }
            )
        return Response(MeetupPreferenceSerializer(preference).data)

    @extend_schema(responses={200: MeetupPreferenceSerializer})
    def put(self, request):
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        with service_errors():
            preference = services.update_meetup_preferences(
                user=request.user,
                meeting_spot_ids=payload.validated_data["meeting_spot_ids"],
                windows=payload.validated_data["windows"],
                overrides=payload.validated_data["overrides"],
            )
        preference = MeetupPreference.objects.prefetch_related(
            "meeting_spots", "availability_windows", "availability_overrides"
        ).get(pk=preference.pk)
        return Response(MeetupPreferenceSerializer(preference).data)


class ListingMeetupOptionsView(GenericAPIView):
    serializer_class = MeetupOptionsSerializer

    def get(self, request, listing_id):
        listing = get_object_or_404(Listing.objects.select_related("seller"), pk=listing_id)
        preference = (
            MeetupPreference.objects.filter(user=listing.seller)
            .prefetch_related(
                "meeting_spots",
                "availability_windows",
                "availability_overrides",
            )
            .first()
        )
        if preference is None:
            return Response({"seller_configured": False, "meeting_spots": [], "slots": []})
        spots = preference.meeting_spots.filter(is_active=True, school=listing.school)
        slots = [{"starts_at": value} for value in services.meetup_slots(seller=listing.seller)]
        return Response(
            {
                "seller_configured": bool(spots and slots),
                "meeting_spots": MeetingSpotSerializer(spots, many=True).data,
                "slots": slots,
            }
        )


class MeetupProposalCreateView(GenericAPIView):
    serializer_class = MeetupProposalCreateSerializer

    @extend_schema(responses={201: MeetupProposalSerializer})
    def post(self, request, pk):
        deal = get_object_or_404(deal_queryset(request.user), pk=pk)
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        spot = get_object_or_404(MeetingSpot, pk=payload.validated_data["meeting_spot_id"])
        with service_errors():
            proposal = services.propose_meetup(
                deal=deal,
                actor=request.user,
                meeting_spot=spot,
                starts_at=payload.validated_data["starts_at"],
            )
        return Response(MeetupProposalSerializer(proposal).data, status=status.HTTP_201_CREATED)


class MeetupProposalAcceptView(GenericAPIView):
    serializer_class = MeetupProposalAcceptSerializer

    @extend_schema(responses={200: MeetupProposalSerializer})
    def post(self, request, pk):
        deal = get_object_or_404(deal_queryset(request.user), pk=pk)
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        proposal = get_object_or_404(
            MeetupProposal,
            pk=payload.validated_data["proposal_id"],
            deal=deal,
        )
        with service_errors():
            proposal = services.accept_meetup(deal=deal, actor=request.user, proposal=proposal)
        return Response(MeetupProposalSerializer(proposal).data)


class MeetupStatusCreateView(GenericAPIView):
    serializer_class = MeetupStatusCreateSerializer

    @extend_schema(responses={201: MeetupStatusUpdateSerializer})
    def post(self, request, pk):
        deal = get_object_or_404(deal_queryset(request.user), pk=pk)
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        with service_errors():
            update = services.meetup_status(
                deal=deal,
                actor=request.user,
                **payload.validated_data,
            )
        return Response(
            MeetupStatusUpdateSerializer(update).data,
            status=status.HTTP_201_CREATED,
        )
