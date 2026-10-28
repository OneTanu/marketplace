from rest_framework import serializers

from apps.listings.services import sold_count
from apps.schools.serializers import SchoolSerializer
from apps.trust.services import is_moderator, is_senior_moderator

from .models import User
from .services import update_profile


class CurrentUserSerializer(serializers.ModelSerializer):
    school = SchoolSerializer(read_only=True, allow_null=True)
    # Blank means no handle (and clears one). Not nullable: the schema would then type the
    # response as string | null too, though it's always a string.
    instagram_handle = serializers.CharField(required=False, allow_blank=True)
    follower_count = serializers.IntegerField(source="follower_relationships.count", read_only=True)
    following_count = serializers.IntegerField(
        source="following_relationships.count", read_only=True
    )
    sold_count = serializers.SerializerMethodField()
    # Staff roles, so the app can show the moderation portal link.
    is_moderator = serializers.SerializerMethodField()
    is_senior_moderator = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "school",
            "instagram_handle",
            "profile_description",
            "follower_count",
            "following_count",
            "sold_count",
            "date_joined",
            "is_moderator",
            "is_senior_moderator",
        ]
        read_only_fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "school",
            "date_joined",
        ]

    def get_sold_count(self, user) -> int:
        return sold_count(user)

    def get_is_moderator(self, user) -> bool:
        return is_moderator(user)

    def get_is_senior_moderator(self, user) -> bool:
        return is_senior_moderator(user)

    def update(self, instance, validated_data):
        # Raises Django ValidationErrors; CurrentUserView turns them into 400s.
        return update_profile(instance, **validated_data)


class PublicUserSerializer(serializers.ModelSerializer):
    school = SchoolSerializer(read_only=True, allow_null=True)
    # Annotated by public_users() in views.py.
    follower_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)
    sold_count = serializers.IntegerField(read_only=True)
    is_following = serializers.BooleanField(read_only=True)
    is_self = serializers.SerializerMethodField()
    # Only the initial: the full last name stays private.
    last_initial = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_initial",
            "school",
            "instagram_handle",
            "profile_description",
            "follower_count",
            "following_count",
            "sold_count",
            "date_joined",
            "is_following",
            "is_self",
        ]
        read_only_fields = fields

    def get_last_initial(self, user) -> str:
        return user.last_name[:1].upper()

    def get_is_self(self, user) -> bool:
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and request.user.pk == user.pk)


class PasswordResetKeyStatusRequestSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=200)


class PasswordResetKeyStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["valid", "expired", "used", "invalid"])


class BlockingDealSerializer(serializers.Serializer):
    """A deal that has to be settled before the account can be deactivated."""

    id = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    conversation = serializers.IntegerField(source="conversation_id", read_only=True)


class DeactivationPreviewSerializer(serializers.Serializer):
    blockers = BlockingDealSerializer(many=True, read_only=True)
    open_deals = serializers.IntegerField(read_only=True)
    listings_to_hide = serializers.IntegerField(read_only=True)


class DeactivateSerializer(serializers.Serializer):
    password = serializers.CharField(trim_whitespace=False, max_length=4096)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class ReactivateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False, max_length=4096)
