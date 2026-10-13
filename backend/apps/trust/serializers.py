from rest_framework import serializers

from .models import Block, Report, UserRestriction


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
