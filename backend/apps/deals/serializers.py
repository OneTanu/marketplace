from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import User
from apps.schools.serializers import MeetingSpotSerializer

from . import services
from .models import (
    Deal,
    DealDispute,
    DealEvent,
    DealOffer,
    DealProblem,
    HandoffConfirmation,
    MeetupAvailabilityOverride,
    MeetupAvailabilityWindow,
    MeetupPreference,
    MeetupProposal,
    MeetupStatusUpdate,
)


class DealUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name"]
        read_only_fields = fields


class DealListingSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    price_cents = serializers.IntegerField(read_only=True)
    currency = serializers.CharField(read_only=True)
    school_slug = serializers.CharField(source="school.slug", read_only=True)
    school_name = serializers.CharField(source="school.short_name", read_only=True)
    cover_url = serializers.SerializerMethodField()

    def get_cover_url(self, listing) -> str | None:
        photo = next(iter(getattr(listing, "deal_cover_photos", [])), None)
        if photo is None:
            return None
        return photo.thumbnail.url if photo.thumbnail else photo.image.url


class DealOfferSerializer(serializers.ModelSerializer):
    offered_by = DealUserSerializer(read_only=True)
    trade_items = DealListingSerializer(many=True, read_only=True)

    class Meta:
        model = DealOffer
        fields = ["id", "offered_by", "amount_cents", "trade_items", "cash_payer", "created_at"]
        read_only_fields = fields


class DealEventSerializer(serializers.ModelSerializer):
    actor = DealUserSerializer(read_only=True, allow_null=True)

    class Meta:
        model = DealEvent
        fields = ["id", "event_type", "actor", "from_status", "to_status", "data", "created_at"]
        read_only_fields = fields


class MeetupProposalSerializer(serializers.ModelSerializer):
    proposed_by = DealUserSerializer(read_only=True)
    meeting_spot = MeetingSpotSerializer(read_only=True)

    class Meta:
        model = MeetupProposal
        fields = [
            "id",
            "proposed_by",
            "meeting_spot",
            "starts_at",
            "status",
            "created_at",
            "responded_at",
        ]
        read_only_fields = fields


class MeetupStatusUpdateSerializer(serializers.ModelSerializer):
    actor = DealUserSerializer(read_only=True)

    class Meta:
        model = MeetupStatusUpdate
        fields = ["id", "actor", "kind", "minutes_late", "created_at"]
        read_only_fields = fields


class DealDisputeSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = DealDispute
        fields = ["reason", "opened_at", "outcome", "resolved_at"]
        read_only_fields = fields


class DealActionsSerializer(serializers.Serializer):
    """What the viewer can do now. The server still checks every action."""

    accept = serializers.BooleanField()
    counter = serializers.BooleanField()
    decline = serializers.BooleanField()
    cancel = serializers.BooleanField()
    confirm_handoff = serializers.BooleanField()
    report_problem = serializers.BooleanField()
    archive = serializers.BooleanField()
    unarchive = serializers.BooleanField()


class DealSerializer(serializers.ModelSerializer):
    listing = DealListingSerializer(read_only=True)
    buyer = DealUserSerializer(read_only=True)
    seller = DealUserSerializer(read_only=True)
    offers = DealOfferSerializer(many=True, read_only=True)
    events = DealEventSerializer(many=True, read_only=True)
    buyer_confirmed = serializers.SerializerMethodField()
    seller_confirmed = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()
    awaiting_me = serializers.SerializerMethodField()
    meetup_proposals = MeetupProposalSerializer(many=True, read_only=True)
    meetup_updates = MeetupStatusUpdateSerializer(many=True, read_only=True)
    section = serializers.SerializerMethodField(
        help_text="Where it belongs in the viewer's activity."
    )
    actions = serializers.SerializerMethodField()
    dispute = serializers.SerializerMethodField()
    my_problems = serializers.SerializerMethodField(
        help_text="Kinds of problem the viewer has reported on this deal."
    )

    class Meta:
        model = Deal
        fields = [
            "id",
            "listing",
            "buyer",
            "seller",
            "conversation",
            "kind",
            "status",
            "current_amount_cents",
            "agreed_amount_cents",
            "currency",
            "response_deadline",
            "handoff_deadline",
            "handoff_extensions",
            "backup_position",
            "accepted_at",
            "completed_at",
            "closed_at",
            "close_reason",
            "section",
            "actions",
            "dispute",
            "my_problems",
            "buyer_confirmed",
            "seller_confirmed",
            "my_role",
            "awaiting_me",
            "asap",
            "offers",
            "events",
            "meetup_proposals",
            "meetup_updates",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def _confirmed_user_ids(self, deal) -> set[int]:
        if not hasattr(deal, "_confirmed_user_ids"):
            deal._confirmed_user_ids = {item.user_id for item in deal.confirmations.all()}
        return deal._confirmed_user_ids

    def get_buyer_confirmed(self, deal) -> bool:
        return deal.buyer_id in self._confirmed_user_ids(deal)

    def get_seller_confirmed(self, deal) -> bool:
        return deal.seller_id in self._confirmed_user_ids(deal)

    def _viewer(self):
        request = self.context.get("request")
        return request.user if request else None

    @extend_schema_field(
        serializers.ChoiceField(choices=["current", "history", "cancelled", "archived"])
    )
    def get_section(self, deal) -> str:
        viewer = self._viewer()
        return services.section_for(deal, viewer) if viewer else "current"

    @extend_schema_field(DealActionsSerializer)
    def get_actions(self, deal) -> dict:
        viewer = self._viewer()
        S = Deal.Status
        mine = viewer is not None and viewer.pk in {deal.buyer_id, deal.seller_id}
        turn = mine and self.get_awaiting_me(deal) and deal.status != S.BACKUP
        confirmed = self._confirmed_user_ids(deal)
        section = self.get_section(deal)
        return {
            "accept": turn,
            "counter": turn,
            "decline": turn or (mine and deal.status == S.BACKUP and viewer.pk == deal.seller_id),
            # A backup buyer leaves the line; the seller removes them with decline instead.
            "cancel": mine
            and (
                deal.status in services.NEGOTIATING
                or (deal.status == S.BACKUP and viewer.pk == deal.buyer_id)
                or (deal.status == S.PENDING and not confirmed)
            ),
            "confirm_handoff": mine and deal.status == S.PENDING and viewer.pk not in confirmed,
            "report_problem": mine and deal.status in {S.PENDING, S.DISPUTED, S.COMPLETED},
            "archive": mine and section == "cancelled",
            # Declined and expired deals live in Archived; only a hand-archived cancel moves back.
            "unarchive": mine and section == "archived" and deal.status == S.CANCELED,
        }

    @extend_schema_field(DealDisputeSummarySerializer(allow_null=True))
    def get_dispute(self, deal):
        try:
            dispute = deal.dispute
        except DealDispute.DoesNotExist:
            return None
        return DealDisputeSummarySerializer(dispute).data

    def get_my_problems(self, deal) -> list[str]:
        viewer = self._viewer()
        if viewer is None:
            return []
        return [p.kind for p in deal.problems.all() if p.reporter_id == viewer.pk]

    def get_my_role(self, deal) -> str:
        request = self.context.get("request")
        return "seller" if request and request.user.pk == deal.seller_id else "buyer"

    def get_awaiting_me(self, deal) -> bool:
        request = self.context.get("request")
        if request is None:
            return False
        return bool(
            (deal.status == Deal.Status.AWAITING_SELLER and request.user.pk == deal.seller_id)
            or (deal.status == Deal.Status.AWAITING_BUYER and request.user.pk == deal.buyer_id)
        )


class CreateDealSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=Deal.Kind.choices)
    amount_cents = serializers.IntegerField(required=False, min_value=1)
    asap = serializers.BooleanField(required=False, default=False)
    meeting_spot_id = serializers.IntegerField(required=False, min_value=1, write_only=True)
    proposed_starts_at = serializers.ListField(
        child=serializers.DateTimeField(),
        required=False,
        min_length=1,
        max_length=2,
        write_only=True,
    )

    def validate(self, attrs):
        if attrs.get("kind") == Deal.Kind.TRADE and attrs.get("amount_cents") is not None:
            raise serializers.ValidationError(
                {"amount_cents": "A trade request starts without an amount."}
            )
        spot = attrs.get("meeting_spot_id")
        starts = attrs.get("proposed_starts_at")
        if (spot is None) != (starts is None):
            raise serializers.ValidationError(
                "Choose both a meetup location and at least one proposed time."
            )
        if attrs.get("kind") == Deal.Kind.BUY_NOW and starts and len(starts) != 1:
            raise serializers.ValidationError(
                {"proposed_starts_at": "Buy now uses one proposed meetup time."}
            )
        return attrs


class AcceptDealSerializer(serializers.Serializer):
    meetup_proposal_id = serializers.IntegerField(required=False, min_value=1)


class CounterOfferSerializer(serializers.Serializer):
    amount_cents = serializers.IntegerField(min_value=1)
    meetup_proposal_id = serializers.IntegerField(required=False, min_value=1)


class TradeOfferSerializer(serializers.Serializer):
    trade_item_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), min_length=1, max_length=5
    )
    cash_cents = serializers.IntegerField(required=False, default=0, min_value=0)
    cash_payer = serializers.ChoiceField(
        choices=DealOffer.CashPayer.choices, required=False, allow_blank=True, default=""
    )
    meetup_proposal_id = serializers.IntegerField(required=False, min_value=1)


class DealQuerySerializer(serializers.Serializer):
    conversation = serializers.IntegerField(required=False, min_value=1)
    section = serializers.ChoiceField(
        choices=list(services.SECTION_FILTERS),
        required=False,
        help_text="current: in progress or under review. history: completed purchases, sales "
        "and trades only. cancelled: canceled deals. archived: declined and expired deals, plus "
        "canceled ones you archived.",
    )


class ReportProblemSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=DealProblem.Kind.choices)
    details = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class HandoffConfirmationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HandoffConfirmation
        fields = ["confirmed_at"]
        read_only_fields = fields


WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class AvailabilityWindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetupAvailabilityWindow
        fields = ["id", "weekday", "start_time", "end_time"]
        read_only_fields = ["id"]
        extra_kwargs = {"weekday": {"max_value": 6}}


class AvailabilityOverrideSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetupAvailabilityOverride
        fields = ["id", "date", "is_unavailable", "start_time", "end_time"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        unavailable = attrs.get("is_unavailable", False)
        start = attrs.get("start_time")
        end = attrs.get("end_time")
        if unavailable and (start is not None or end is not None):
            raise serializers.ValidationError("An unavailable day cannot include a time window.")
        if not unavailable and (start is None or end is None):
            raise serializers.ValidationError("Available overrides require start and end times.")
        if start is not None and end is not None and end <= start:
            raise serializers.ValidationError("End time must be later than start time.")
        return attrs


class MeetupPreferenceSerializer(serializers.ModelSerializer):
    meeting_spots = MeetingSpotSerializer(many=True, read_only=True)
    availability_windows = AvailabilityWindowSerializer(many=True, read_only=True)
    availability_overrides = AvailabilityOverrideSerializer(many=True, read_only=True)
    updated_at = serializers.DateTimeField(read_only=True, allow_null=True)

    class Meta:
        model = MeetupPreference
        fields = [
            "meeting_spots",
            "availability_windows",
            "availability_overrides",
            "updated_at",
        ]
        read_only_fields = fields


class MeetupPreferenceUpdateSerializer(serializers.Serializer):
    meeting_spot_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), min_length=1
    )
    windows = AvailabilityWindowSerializer(many=True, min_length=1)
    overrides = AvailabilityOverrideSerializer(many=True, required=False, default=list)

    def validate_windows(self, windows):
        for window in windows:
            if window["end_time"] <= window["start_time"]:
                raise serializers.ValidationError("End time must be later than start time.")
        ordered = sorted(windows, key=lambda window: (window["weekday"], window["start_time"]))
        for previous, window in zip(ordered, ordered[1:], strict=False):
            same_day = window["weekday"] == previous["weekday"]
            if same_day and window["start_time"] < previous["end_time"]:
                day = WEEKDAY_NAMES[window["weekday"]]
                raise serializers.ValidationError(f"Your {day} time ranges overlap.")
        return windows


class MeetupSlotSerializer(serializers.Serializer):
    starts_at = serializers.DateTimeField(read_only=True)


class MeetupOptionsSerializer(serializers.Serializer):
    seller_configured = serializers.BooleanField(read_only=True)
    meeting_spots = MeetingSpotSerializer(many=True, read_only=True)
    slots = MeetupSlotSerializer(many=True, read_only=True)


class MeetupProposalCreateSerializer(serializers.Serializer):
    meeting_spot_id = serializers.IntegerField(min_value=1)
    starts_at = serializers.DateTimeField()


class MeetupProposalAcceptSerializer(serializers.Serializer):
    proposal_id = serializers.IntegerField(min_value=1)


class MeetupStatusCreateSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=MeetupStatusUpdate.Kind.choices)
    minutes_late = serializers.IntegerField(required=False, allow_null=True)
