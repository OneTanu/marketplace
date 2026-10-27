from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.listings.models import Category, Color, ItemDetails, ListingKind
from apps.listings.services import ALL_SCHOOLS
from apps.schools.models import MarketplaceStatus, School

from .models import Notification, SavedSearch


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "kind", "title", "body", "link", "created_at", "read_at"]
        read_only_fields = fields


class NotificationUnreadCountSerializer(serializers.Serializer):
    unread = serializers.IntegerField(read_only=True)


class NotificationMarkReadSerializer(serializers.Serializer):
    # Leave out to mark everything read.
    ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False)


class SavedSearchFiltersSerializer(serializers.Serializer):
    """A saved search's filters, named like the feed's query parameters (GET /api/listings/).
    Blank or null means "any"."""

    q = serializers.CharField(
        source="query", max_length=100, allow_blank=True, required=False, default=""
    )
    school = serializers.CharField(
        allow_blank=True,
        required=False,
        default="",
        help_text='A school slug, "all", or blank for your own school.',
    )
    category = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Category.objects.filter(kind=ListingKind.ITEM, is_active=True),
        allow_null=True,
        required=False,
        default=None,
    )
    brand = serializers.CharField(max_length=100, allow_blank=True, required=False, default="")
    min_price = serializers.IntegerField(
        source="min_price_cents",
        min_value=0,
        allow_null=True,
        required=False,
        default=None,
        help_text="In cents.",
    )
    max_price = serializers.IntegerField(
        source="max_price_cents",
        min_value=0,
        allow_null=True,
        required=False,
        default=None,
        help_text="In cents.",
    )
    size = serializers.CharField(
        max_length=30,
        allow_blank=True,
        required=False,
        default="",
        help_text='Exact size. Jeans and pants are "<waist>x<inseam>", e.g. 32x30.',
    )
    condition = serializers.ChoiceField(
        choices=ItemDetails.Condition.choices, allow_blank=True, required=False, default=""
    )
    color = serializers.ChoiceField(
        choices=Color.choices, allow_blank=True, required=False, default=""
    )
    sort = serializers.ChoiceField(
        choices=SavedSearch.Sort.choices, required=False, default=SavedSearch.Sort.NEWEST
    )

    def validate_school(self, slug):
        if slug in ("", ALL_SCHOOLS):
            return slug
        school = School.objects.filter(slug=slug, marketplace_status=MarketplaceStatus.OPEN)
        if not school.exists():
            raise serializers.ValidationError(f'There\'s no open marketplace for "{slug}".')
        return slug

    def to_representation(self, search):
        data = super().to_representation(search)
        data["school"] = (
            ALL_SCHOOLS if search.all_schools else search.school.slug if search.school else ""
        )
        return data

    @staticmethod
    def service_kwargs(validated_data) -> dict:
        """Validated filters as notifications.services.create_saved_search arguments."""
        data = dict(validated_data)
        slug = data.pop("school")
        data["all_schools"] = slug == ALL_SCHOOLS
        data["school"] = School.objects.get(slug=slug) if slug and slug != ALL_SCHOOLS else None
        return data


class SavedSearchSerializer(serializers.ModelSerializer):
    filters = serializers.SerializerMethodField()

    class Meta:
        model = SavedSearch
        fields = ["id", "name", "filters", "alerts_enabled", "created_at", "updated_at"]
        read_only_fields = fields

    @extend_schema_field(SavedSearchFiltersSerializer)
    def get_filters(self, search):
        return SavedSearchFiltersSerializer(search).data


class SavedSearchCreateSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=80,
        allow_blank=True,
        required=False,
        default="",
        help_text="Leave blank for a name made from the filters.",
    )
    filters = SavedSearchFiltersSerializer()
    alerts_enabled = serializers.BooleanField(required=False, default=True)


class SavedSearchUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80, required=False)
    alerts_enabled = serializers.BooleanField(required=False)
