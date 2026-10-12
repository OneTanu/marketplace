from rest_framework import serializers

from apps.accounts.models import User

from .models import Review


class ReviewUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name"]
        read_only_fields = fields


class ReviewSerializer(serializers.ModelSerializer):
    author = ReviewUserSerializer(read_only=True)
    subject = ReviewUserSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ["id", "deal", "author", "subject", "rating", "comment", "created_at"]
        read_only_fields = fields


class ReviewCreateSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=500, allow_blank=True, required=False, default="")
