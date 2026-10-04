from rest_framework import serializers

from apps.schools.serializers import SchoolSerializer

from .models import User


class CurrentUserSerializer(serializers.ModelSerializer):
    school = SchoolSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "school"]
