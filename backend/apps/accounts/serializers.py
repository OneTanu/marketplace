from django.db import IntegrityError, transaction
from rest_framework import serializers

from apps.schools.serializers import SchoolSerializer

from .models import Follow, User


class CurrentUserSerializer(serializers.ModelSerializer):
    school = SchoolSerializer(read_only=True)
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
        from .models import normalize_instagram_handle

        value = normalize_instagram_handle(value)
        if (
            value
            and User.objects.exclude(pk=self.instance.pk)
            .filter(instagram_handle__iexact=value)
            .exists()
        ):
            raise serializers.ValidationError(
                "This Instagram handle is already connected to another Tanu account."
            )
        return value

    def validate_profile_description(self, value):
        return value.strip()

    def update(self, instance, validated_data):
        try:
            with transaction.atomic():
                return super().update(instance, validated_data)
        except IntegrityError as error:
            if "accounts_user_instagram_ci_unique" in str(error):
                raise serializers.ValidationError(
                    {
                        "instagram_handle": (
                            "This Instagram handle is already connected to another Tanu account."
                        )
                    }
                ) from error
            raise


class PublicUserSerializer(serializers.ModelSerializer):
    school = SchoolSerializer(read_only=True)
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
