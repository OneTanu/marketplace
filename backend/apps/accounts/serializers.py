from rest_framework import serializers

from apps.schools.serializers import SchoolSerializer

from .models import Follow, User
from .services import update_profile


class CurrentUserSerializer(serializers.ModelSerializer):
    school = SchoolSerializer(read_only=True, allow_null=True)
    instagram_handle = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    follower_count = serializers.IntegerField(source="follower_relationships.count", read_only=True)
    following_count = serializers.IntegerField(
        source="following_relationships.count", read_only=True
    )

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
        ]
        read_only_fields = ["id", "email", "username", "first_name", "last_name", "school"]

    def validate_instagram_handle(self, value):
        # null clears the handle, like a blank one.
        return value or ""

    def update(self, instance, validated_data):
        # Raises Django ValidationErrors; CurrentUserView turns them into 400s.
        return update_profile(instance, **validated_data)


class PublicUserSerializer(serializers.ModelSerializer):
    school = SchoolSerializer(read_only=True, allow_null=True)
    follower_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    is_self = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "school",
            "instagram_handle",
            "profile_description",
            "follower_count",
            "following_count",
            "is_following",
            "is_self",
        ]
        read_only_fields = fields

    def get_follower_count(self, user) -> int:
        return user.follower_relationships.count()

    def get_following_count(self, user) -> int:
        return user.following_relationships.count()

    def get_is_following(self, user) -> bool:
        request = self.context.get("request")
        return bool(
            request
            and request.user.is_authenticated
            and Follow.objects.filter(follower=request.user, following=user).exists()
        )

    def get_is_self(self, user) -> bool:
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and request.user.pk == user.pk)
