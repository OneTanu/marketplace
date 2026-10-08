from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import User
from apps.schools.serializers import SchoolSerializer

from .models import MESSAGE_MAX_LENGTH, Conversation, Message


class MessagingUserSerializer(serializers.ModelSerializer):
    school = SchoolSerializer(read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "school"]
        read_only_fields = fields


class MessageSerializer(serializers.ModelSerializer):
    sender = MessagingUserSerializer(read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "conversation", "sender", "body", "created_at", "is_mine"]
        read_only_fields = fields

    def get_is_mine(self, message) -> bool:
        request = self.context.get("request")
        return bool(request and message.sender_id == request.user.pk)


class MessagePageSerializer(serializers.Serializer):
    messages = MessageSerializer(many=True, read_only=True)
    has_more = serializers.BooleanField(read_only=True)


class UnreadCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField(read_only=True)


class MessageQuerySerializer(serializers.Serializer):
    before_id = serializers.IntegerField(required=False, min_value=1)
    after_id = serializers.IntegerField(required=False, min_value=1)

    def validate(self, attrs):
        if "before_id" in attrs and "after_id" in attrs:
            raise serializers.ValidationError("Use either before_id or after_id, not both.")
        return attrs


class ConversationSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    latest_message = serializers.SerializerMethodField()
    # Annotated by conversation_queryset().
    unread_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "id",
            "other_user",
            "latest_message",
            "unread_count",
            "created_at",
            "last_message_at",
        ]
        read_only_fields = fields

    @extend_schema_field(MessagingUserSerializer)
    def get_other_user(self, conversation):
        request = self.context["request"]
        other = next(
            (
                record.user
                for record in conversation.participant_records.all()
                if record.user_id != request.user.pk
            ),
            None,
        )
        return MessagingUserSerializer(other).data if other else None

    @extend_schema_field(MessageSerializer(allow_null=True))
    def get_latest_message(self, conversation):
        # Prefetched by conversation_queryset(): a list holding at most the latest message.
        message = next(iter(conversation.latest_messages), None)
        return MessageSerializer(message, context=self.context).data if message else None


class StartConversationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=30)


class SendMessageSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=MESSAGE_MAX_LENGTH, trim_whitespace=True)


class MarkReadSerializer(serializers.Serializer):
    message_id = serializers.IntegerField(required=False, min_value=1)
