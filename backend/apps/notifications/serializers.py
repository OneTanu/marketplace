from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "kind", "title", "body", "link", "created_at", "read_at"]
        read_only_fields = fields


class NotificationUnreadCountSerializer(serializers.Serializer):
    unread = serializers.IntegerField(read_only=True)


class NotificationMarkReadSerializer(serializers.Serializer):
    # Leave out to mark everything read.
    ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False)
