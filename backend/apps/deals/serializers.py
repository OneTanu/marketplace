from rest_framework import serializers

from apps.accounts.models import User
from apps.schools.serializers import MeetingSpotSerializer

from .models import (
    Deal,
    DealEvent,
    DealOffer,
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
        fields = ["id", "event_type", "actor", "data", "created_at"]
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

    def get_my_role(self, deal) -> str:
        request = self.context.get("request")
        return "seller" if request and request.user.pk == deal.seller_id else "buyer"

    def get_awaiting_me(self, deal) -> bool:
        request = self.context.get("request")
        if request is None:
            return False
        return bool(
            (
                deal.status in {Deal.Status.AWAITING_SELLER, Deal.Status.BACKUP}
                and request.user.pk == deal.seller_id
            )
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
