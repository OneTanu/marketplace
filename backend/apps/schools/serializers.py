from rest_framework import serializers

from .models import School


class SchoolSerializer(serializers.ModelSerializer):
    domains = serializers.SlugRelatedField(many=True, read_only=True, slug_field="domain")

    class Meta:
        model = School
        fields = [
            "name",
            "short_name",
            "slug",
            "signup_is_open",
            "marketplace_status",
            "city",
            "state",
            "country_code",
            "domains",
        ]
