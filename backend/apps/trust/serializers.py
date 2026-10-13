from rest_framework import serializers

from .models import Appeal, Block, InfoRequest, ModerationAction, Report, UserRestriction


class ReportCreateSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=Report.TargetType.choices)
    target_id = serializers.IntegerField(min_value=1)
    reason = serializers.ChoiceField(choices=Report.Reason.choices)
    prohibited_category = serializers.ChoiceField(
        choices=Report.ProhibitedCategory.choices, required=False, allow_blank=True, default=""
    )
    details = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    # For a conversation report: the messages that show what happened.
    message_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, default=list, max_length=20
    )
    block = serializers.BooleanField(required=False, default=False)


class ReportReceiptSerializer(serializers.ModelSerializer):
    """All a reporter gets back. Moderator notes and outcomes stay private."""

    class Meta:
        model = Report
        fields = ["id", "created_at"]
        read_only_fields = fields


class BlockedUserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="blocked.username", read_only=True)
    first_name = serializers.CharField(source="blocked.first_name", read_only=True)

    class Meta:
        model = Block
        fields = ["username", "first_name", "created_at"]
        read_only_fields = fields


class BlockCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=30)


class MyRestrictionSerializer(serializers.ModelSerializer):
    """A student's own active restriction: what it stops and until when. The moderator's
    reasoning stays internal."""

    kind_label = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = UserRestriction
        fields = ["kind", "kind_label", "expires_at"]
        read_only_fields = fields


class MyAppealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appeal
        fields = ["id", "status", "created_at", "decided_at"]
        read_only_fields = fields


class MyNoticeSerializer(serializers.Serializer):
    """A decision about me: what happened and whether I can still appeal. The moderator's
    internal reason is never included; `message` is what they chose to tell me."""

    id = serializers.IntegerField(source="action.id", read_only=True)
    kind = serializers.ChoiceField(
        source="action.kind", choices=ModerationAction.Kind.choices, read_only=True
    )
    kind_label = serializers.CharField(source="action.get_kind_display", read_only=True)
    message = serializers.CharField(source="action.user_message", read_only=True)
    created_at = serializers.DateTimeField(source="action.created_at", read_only=True)
    can_appeal = serializers.BooleanField(read_only=True)
    appeal_deadline = serializers.DateTimeField(read_only=True)
    appeal = MyAppealSerializer(read_only=True, allow_null=True)


class MyInfoRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = InfoRequest
        fields = ["id", "question", "answer", "created_at", "answered_at"]
        read_only_fields = fields


class StandingSerializer(serializers.Serializer):
    restrictions = MyRestrictionSerializer(many=True, read_only=True)
    notices = MyNoticeSerializer(many=True, read_only=True)
    info_requests = MyInfoRequestSerializer(many=True, read_only=True)


class AppealCreateSerializer(serializers.Serializer):
    action_id = serializers.IntegerField(min_value=1)
    message = serializers.CharField(max_length=2000)


class AnswerSerializer(serializers.Serializer):
    answer = serializers.CharField(max_length=2000)
