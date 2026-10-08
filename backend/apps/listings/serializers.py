from rest_framework import serializers

from apps.schools.models import School

from . import services
from .models import Category, Color, ItemDetails, Listing, ListingPhoto


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]
        read_only_fields = fields


class SchoolSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ["id", "short_name"]
        read_only_fields = fields


class SellerSummarySerializer(serializers.Serializer):
    # Accounts doesn't expose public profile fields yet; add them here when it does.
    id = serializers.IntegerField(read_only=True)


class ItemDetailsSerializer(serializers.ModelSerializer):
    # Declared so the schema keeps "" (no color) as a possible value.
    color = serializers.ChoiceField(choices=Color.choices, allow_blank=True, read_only=True)

    class Meta:
        model = ItemDetails
        fields = ["condition", "size", "brand", "color"]
        read_only_fields = fields


class ListingPhotoSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ListingPhoto
        fields = ["id", "position", "image_url"]
        read_only_fields = fields

    def get_image_url(self, photo) -> str:
        return photo.image.url


class ListingSerializer(serializers.ModelSerializer):
    """A listing as returned by the API."""

    category = CategorySerializer(read_only=True)
    school = SchoolSummarySerializer(read_only=True)
    seller = SellerSummarySerializer(read_only=True)
    item_details = ItemDetailsSerializer(read_only=True, allow_null=True)
    photos = ListingPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = Listing
        fields = [
            "id",
            "kind",
            "status",
            "title",
            "description",
            "price_cents",
            "currency",
            "category",
            "school",
            "seller",
            "item_details",
            "photos",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class MultilineCharField(serializers.CharField):
    """Normalizes line breaks to LF. Browsers send textarea line breaks as CRLF in multipart
    forms, which would count twice against max_length."""

    def to_internal_value(self, data):
        return super().to_internal_value(data).replace("\r\n", "\n").replace("\r", "\n")


class ListingCreateSerializer(serializers.Serializer):
    """Multipart input for creating an item listing. Kind, school, currency and status are set
    by the server, so they aren't fields here and are ignored if sent."""

    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    title = serializers.CharField(max_length=services.MAX_TITLE_LENGTH)
    description = MultilineCharField(
        max_length=services.MAX_DESCRIPTION_LENGTH, allow_blank=True, required=False, default=""
    )
    price_cents = serializers.IntegerField(min_value=0, max_value=services.MAX_PRICE_CENTS)
    condition = serializers.ChoiceField(choices=ItemDetails.Condition.choices)
    size = serializers.CharField(
        max_length=ItemDetails._meta.get_field("size").max_length,
        allow_blank=True,
        required=False,
        default="",
    )
    brand = serializers.CharField(
        max_length=ItemDetails._meta.get_field("brand").max_length,
        allow_blank=True,
        required=False,
        default="",
    )
    color = serializers.ChoiceField(
        choices=Color.choices, allow_blank=True, required=False, default=""
    )
    photos = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False,
        help_text="1 to 10 JPEG, PNG or WebP files of up to 10 MB each, in order. "
        "The first is the cover.",
    )

    def validate_category(self, category):
        services.validate_item_category(category)
        return category

    def validate_photos(self, photos):
        services.validate_photos(photos)
        return photos

    def validate(self, attrs):
        services.validate_price(attrs["category"], attrs["price_cents"])
        return attrs


class ItemDetailsUpdateSerializer(serializers.Serializer):
    condition = serializers.ChoiceField(choices=ItemDetails.Condition.choices, required=False)
    size = serializers.CharField(
        max_length=ItemDetails._meta.get_field("size").max_length,
        allow_blank=True,
        required=False,
    )
    brand = serializers.CharField(
        max_length=ItemDetails._meta.get_field("brand").max_length,
        allow_blank=True,
        required=False,
    )
    color = serializers.ChoiceField(choices=Color.choices, allow_blank=True, required=False)


class ListingUpdateSerializer(serializers.Serializer):
    """JSON input for editing an Available item listing. Every field is optional; fields left
    out keep their value. Kind, school, currency and status aren't fields here and are ignored
    if sent. The category and Free/$0 rules are checked by the update service, against the
    listing's resulting category and price."""

    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), required=False)
    title = serializers.CharField(max_length=services.MAX_TITLE_LENGTH, required=False)
    description = MultilineCharField(
        max_length=services.MAX_DESCRIPTION_LENGTH, allow_blank=True, required=False
    )
    price_cents = serializers.IntegerField(
        min_value=0, max_value=services.MAX_PRICE_CENTS, required=False
    )
    item_details = ItemDetailsUpdateSerializer(required=False)


class ListingPhotoUploadSerializer(serializers.Serializer):
    photo = serializers.FileField(
        help_text="One JPEG, PNG or WebP file of up to 10 MB. It goes after the other photos."
    )


class ListingPhotoOrderSerializer(serializers.Serializer):
    photo_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        help_text="Every photo ID of the listing, each once, in the new order. "
        "The first is the cover.",
    )
