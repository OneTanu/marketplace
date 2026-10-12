from rest_framework import serializers

from apps.accounts.models import User

from .models import Deal, DealEvent, DealOffer, HandoffConfirmation


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

    class Meta:
        model = DealOffer
        fields = ["id", "offered_by", "amount_cents", "created_at"]
        read_only_fields = fields


class DealEventSerializer(serializers.ModelSerializer):
    actor = DealUserSerializer(read_only=True, allow_null=True)

    class Meta:
        model = DealEvent
        fields = ["id", "event_type", "actor", "data", "created_at"]
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
            "offers",
            "events",
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


class AmountSerializer(serializers.Serializer):
    amount_cents = serializers.IntegerField(min_value=1)


class DealQuerySerializer(serializers.Serializer):
    conversation = serializers.IntegerField(required=False, min_value=1)


class HandoffConfirmationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HandoffConfirmation
        fields = ["confirmed_at"]
        read_only_fields = fields
