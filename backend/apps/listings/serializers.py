from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.schools.models import MarketplaceStatus, School

from . import services
from .models import Category, Color, ItemDetails, Listing, ListingKind, ListingPhoto


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent"]
        read_only_fields = fields


class SchoolSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ["id", "short_name"]
        read_only_fields = fields


class SellerSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)


class ItemDetailsSerializer(serializers.ModelSerializer):
    # Declared so the schema keeps "" (no color) as a possible value.
    color = serializers.ChoiceField(choices=Color.choices, allow_blank=True, read_only=True)

    class Meta:
        model = ItemDetails
        fields = ["condition", "size", "brand", "color"]
        read_only_fields = fields


class ListingPhotoSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField(
        help_text="A 400 px (long edge) copy for lists. Null until the background job has made "
        "it; show image_url until then."
    )

    class Meta:
        model = ListingPhoto
        fields = ["id", "position", "image_url", "thumbnail_url"]
        read_only_fields = fields

    def get_image_url(self, photo) -> str:
        return photo.image.url

    def get_thumbnail_url(self, photo) -> str | None:
        return photo.thumbnail.url if photo.thumbnail else None


class ListingSerializer(serializers.ModelSerializer):
    """A listing as returned by the API."""

    category = CategorySerializer(read_only=True)
    school = SchoolSummarySerializer(read_only=True)
    seller = SellerSummarySerializer(read_only=True)
    item_details = ItemDetailsSerializer(read_only=True, allow_null=True)
    photos = ListingPhotoSerializer(many=True, read_only=True)
    removed_by = serializers.SerializerMethodField(
        help_text="Who removed a Removed listing, shown only to its seller: blank unless the "
        "listing is Removed, and null for everyone else."
    )

    class Meta:
        model = Listing
        fields = [
            "id",
            "kind",
            "status",
            "removed_by",
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

    @extend_schema_field(
        serializers.ChoiceField(
            choices=Listing.RemovedBy.choices, allow_blank=True, allow_null=True
        )
    )
    def get_removed_by(self, listing) -> str | None:
        # Reads the viewer from the request in the serializer context; with no request,
        # nobody counts as the seller.
        request = self.context.get("request")
        if request is None or request.user.pk != listing.seller_id:
            return None
        return listing.removed_by


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


class ListingCardSerializer(serializers.ModelSerializer):
    """A listing as a feed card: enough to show and link it, without description or every
    photo. Expects the queryset from views.card_queryset (cover photo prefetched)."""

    cover_url = serializers.SerializerMethodField(
        help_text="The cover photo's thumbnail, or its full image until the thumbnail job has "
        "made one."
    )
    condition = serializers.ChoiceField(
        source="item_details.condition", choices=ItemDetails.Condition.choices, read_only=True
    )
    size = serializers.CharField(source="item_details.size", read_only=True)
    brand = serializers.CharField(source="item_details.brand", read_only=True)
    school = SchoolSummarySerializer(read_only=True)
    seller = SellerSummarySerializer(read_only=True)

    class Meta:
        model = Listing
        fields = [
            "id",
            "status",
            "title",
            "price_cents",
            "currency",
            "cover_url",
            "condition",
            "size",
            "brand",
            "school",
            "seller",
            "created_at",
        ]
        read_only_fields = fields

    def get_cover_url(self, listing) -> str | None:
        cover = listing.cover_photos[0] if listing.cover_photos else None
        if cover is None:
            return None
        return (cover.thumbnail or cover.image).url


class ListingFeedPageSerializer(serializers.Serializer):
    results = ListingCardSerializer(many=True)
    next_cursor = serializers.CharField(
        allow_null=True,
        help_text="Pass as `cursor` to get the next page. Null on the last page.",
    )


class FeedQuerySerializer(serializers.Serializer):
    """The feed's query parameters. Repeat `condition` or `color` to match any of several."""

    school = serializers.CharField(
        required=False,
        help_text=f'A school slug, or "{services.ALL_SCHOOLS}". Defaults to your school.',
    )
    category = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Category.objects.filter(kind=ListingKind.ITEM, is_active=True),
        required=False,
        help_text="A category slug. Includes every category under it.",
    )
    min_price = serializers.IntegerField(min_value=0, required=False, help_text="In cents.")
    max_price = serializers.IntegerField(min_value=0, required=False, help_text="In cents.")
    condition = serializers.ListField(
        child=serializers.ChoiceField(choices=ItemDetails.Condition.choices), required=False
    )
    color = serializers.ListField(
        child=serializers.ChoiceField(choices=Color.choices), required=False
    )
    size = serializers.CharField(required=False, help_text="Exact size, any case, e.g. 32x30.")
    brand = serializers.CharField(required=False, help_text="Exact brand, any case.")
    sort = serializers.ChoiceField(choices=list(services.FEED_SORTS), default="newest")
    cursor = serializers.CharField(
        required=False,
        max_length=200,
        help_text="`next_cursor` from the last page, with the same sort.",
    )

    def validate_school(self, slug):
        if slug == services.ALL_SCHOOLS:
            return slug
        open_schools = School.objects.filter(marketplace_status=MarketplaceStatus.OPEN)
        if not open_schools.filter(slug=slug).exists():
            raise serializers.ValidationError(f'There\'s no open marketplace for "{slug}".')
        return slug

    def validate(self, attrs):
        low, high = attrs.get("min_price"), attrs.get("max_price")
        if low is not None and high is not None and low > high:
            raise serializers.ValidationError({"max_price": ["Must be at least min_price."]})
        return attrs

    def filters(self) -> services.FeedFilters:
        data = self.validated_data
        return services.FeedFilters(
            school=data.get("school", ""),
            category=data.get("category"),
            min_price=data.get("min_price"),
            max_price=data.get("max_price"),
            conditions=data.get("condition", ()),
            colors=data.get("color", ()),
            size=data.get("size", ""),
            brand=data.get("brand", ""),
        )
