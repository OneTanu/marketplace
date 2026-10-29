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
    DealListingSerializer,
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
    ReportProblemSerializer,
    TradeOfferSerializer,
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
            "offers__trade_items__school",
            Prefetch("offers__trade_items__photos", queryset=cover, to_attr="deal_cover_photos"),
            "events__actor",
            "confirmations",
            "meetup_proposals__proposed_by",
            "meetup_proposals__meeting_spot",
            "meetup_updates__actor",
            "problems",
        )
        .select_related("dispute")
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
        section = query.validated_data.get("section")
        if section:
            deals = deals.filter(services.SECTION_FILTERS[section](self.request.user))
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


class ReportProblemView(GenericAPIView):
    """Report a problem with an accepted deal: a no-show, an item not as described, a payment
    or safety concern. It goes to Tanu's moderators with a snapshot of the deal; nobody is
    penalized automatically. If the handoff was already confirmed by someone, the deal is held
    as a dispute until a moderator decides."""

    serializer_class = ReportProblemSerializer

    @extend_schema(responses={200: DealSerializer})
    def post(self, request, pk):
        deal = get_object_or_404(deal_queryset(request.user), pk=pk)
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        with service_errors():
            services.report_problem(deal=deal, actor=request.user, **payload.validated_data)
        refreshed = deal_queryset(request.user).get(pk=deal.pk)
        return Response(DealSerializer(refreshed, context={"request": request}).data)


class ArchiveDealView(GenericAPIView):
    """Move a canceled, declined or expired deal into (POST) or out of (DELETE) your
    Archived activity. Nothing is deleted."""

    serializer_class = DealSerializer

    def _set(self, request, pk, archived):
        deal = get_object_or_404(deal_queryset(request.user), pk=pk)
        with service_errors():
            services.set_archived(deal=deal, actor=request.user, archived=archived)
        refreshed = deal_queryset(request.user).get(pk=deal.pk)
        return Response(self.get_serializer(refreshed).data)

    @extend_schema(request=None)
    def post(self, request, pk):
        return self._set(request, pk, True)

    def delete(self, request, pk):
        return self._set(request, pk, False)


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


class TradeOfferView(GenericAPIView):
    """Offer a trade package (some of the buyer's items, plus optional cash from either side)
    on a trade request. The seller sends the first one; after that each side can counter."""

    serializer_class = TradeOfferSerializer

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
            services.counter_trade(
                deal=deal,
                actor=request.user,
                item_ids=payload.validated_data["trade_item_ids"],
                cash_cents=payload.validated_data["cash_cents"],
                cash_payer=payload.validated_data["cash_payer"],
                meetup_proposal=proposal,
            )
        refreshed = deal_queryset(request.user).get(pk=deal.pk)
        return Response(DealSerializer(refreshed, context={"request": request}).data)


class TradeOptionsView(ListAPIView):
    """The buyer's Available items that can go into a trade package. Only the two people in
    the deal can see it."""

    serializer_class = DealListingSerializer
    pagination_class = None

    def get_queryset(self):
        deal = get_object_or_404(deal_queryset(self.request.user), pk=self.kwargs["pk"])
        cover = ListingPhoto.objects.filter(position=0)
        return (
            services.tradable_listings(deal)
            .select_related("school")
            .prefetch_related(Prefetch("photos", queryset=cover, to_attr="deal_cover_photos"))
            .order_by("-created_at", "-id")
        )
