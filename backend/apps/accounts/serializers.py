from django.db import IntegrityError, transaction
from rest_framework import serializers

from apps.schools.serializers import SchoolSerializer

from .models import User


class CurrentUserSerializer(serializers.ModelSerializer):
    school = SchoolSerializer(read_only=True)
    instagram_handle = serializers.CharField(required=False, allow_blank=True, allow_null=True)

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
