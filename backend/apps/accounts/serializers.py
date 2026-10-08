from rest_framework import serializers

from apps.schools.serializers import SchoolSerializer

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

    def update(self, instance, validated_data):
        # Raises Django ValidationErrors; CurrentUserView turns them into 400s.
        return update_profile(instance, **validated_data)


class PublicUserSerializer(serializers.ModelSerializer):
    school = SchoolSerializer(read_only=True, allow_null=True)
    # Annotated by public_users() in views.py.
    follower_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)
    is_following = serializers.BooleanField(read_only=True)
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

    def get_is_self(self, user) -> bool:
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and request.user.pk == user.pk)
