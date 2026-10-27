"""Serializers for the staff-only moderation API. Students never reach these (see
staff_views.IsModerator)."""

from rest_framework import serializers

from apps.accounts.models import User
from apps.deals.models import DealDispute

from .models import (
    Appeal,
    EvidenceSnapshot,
    InfoRequest,
    ModerationAction,
    ModerationCase,
    Report,
    UserRestriction,
)


class StaffUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name"]
        read_only_fields = fields


class CaseListingSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    removed_by = serializers.CharField(read_only=True)


class CaseRowSerializer(serializers.ModelSerializer):
    """One line in the moderation queue."""

    subject_user = StaffUserSerializer(read_only=True)
    assigned_to = StaffUserSerializer(read_only=True, allow_null=True)
    listing = CaseListingSerializer(read_only=True, allow_null=True)
    school_name = serializers.CharField(source="school.short_name", read_only=True, default="")
    priority_label = serializers.CharField(source="get_priority_display", read_only=True)
    # Annotated by services.moderation_queue().
    report_count = serializers.IntegerField(read_only=True)
    reporter_count = serializers.IntegerField(read_only=True)
    prior_case_count = serializers.IntegerField(read_only=True)
    # Warnings, restrictions, removals, suspensions, or bans in the last 90 days.
    recent_consequences = serializers.IntegerField(read_only=True)
    latest_report_at = serializers.DateTimeField(read_only=True, allow_null=True)
    reasons = serializers.SerializerMethodField()
    target_types = serializers.SerializerMethodField()

    class Meta:
        model = ModerationCase
        fields = [
            "id",
            "status",
            "priority",
            "priority_label",
            "escalated",
            "subject_user",
            "listing",
            "school_name",
            "assigned_to",
            "report_count",
            "reporter_count",
            "prior_case_count",
            "recent_consequences",
            "latest_report_at",
            "reasons",
            "target_types",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_reasons(self, case) -> list[str]:
        return sorted({report.reason for report in case.reports.all()})

    def get_target_types(self, case) -> list[str]:
        return sorted({report.target_type for report in case.reports.all()})


class EvidenceSerializer(serializers.ModelSerializer):
    files = serializers.SerializerMethodField()

    class Meta:
        model = EvidenceSnapshot
        fields = ["id", "kind", "source_id", "data", "files", "created_at"]
        read_only_fields = fields

    def get_files(self, snapshot) -> list[str]:
        return [evidence.file.url for evidence in snapshot.files.all()]


class CaseReportSerializer(serializers.ModelSerializer):
    reporter = StaffUserSerializer(read_only=True)
    reason_label = serializers.CharField(source="get_reason_display", read_only=True)
    evidence = EvidenceSerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields = [
            "id",
            "reporter",
            "target_type",
            "reason",
            "reason_label",
            "prohibited_category",
            "details",
            "listing_id",
            "conversation_id",
            "message_id",
            "deal_id",
            "review_id",
            "evidence",
            "created_at",
        ]
        read_only_fields = fields


class ActionSerializer(serializers.ModelSerializer):
    actor = StaffUserSerializer(read_only=True, allow_null=True)
    target_user = StaffUserSerializer(read_only=True, allow_null=True)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = ModerationAction
        fields = [
            "id",
            "kind",
            "kind_label",
            "actor",
            "target_user",
            "listing_id",
            "case_id",
            "reason",
            "user_message",
            "data",
            "created_at",
        ]
        read_only_fields = fields


class StaffRestrictionSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = UserRestriction
        fields = ["id", "kind", "kind_label", "reason", "expires_at", "created_at"]
        read_only_fields = fields


class SubjectHistorySerializer(serializers.Serializer):
    """The reported student's record, so a moderator can see whether this is a pattern."""

    user = StaffUserSerializer(read_only=True)
    email = serializers.EmailField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)
    school_name = serializers.CharField(read_only=True, allow_blank=True)
    active_restrictions = StaffRestrictionSerializer(many=True, read_only=True)
    past_actions = ActionSerializer(many=True, read_only=True)
    other_cases = CaseRowSerializer(many=True, read_only=True)
    reports_received = serializers.IntegerField(read_only=True)
    reports_made = serializers.IntegerField(read_only=True)
    recent_consequences = serializers.IntegerField(read_only=True)
    repeat_offender = serializers.BooleanField(read_only=True)


class ReporterRecordSerializer(serializers.Serializer):
    """How often a reporter's reviewed reports led to action."""

    user = StaffUserSerializer(read_only=True)
    reviewed = serializers.IntegerField(read_only=True)
    upheld = serializers.IntegerField(read_only=True)
    possible_false_reporter = serializers.BooleanField(read_only=True)


class StaffAppealSerializer(serializers.ModelSerializer):
    user = StaffUserSerializer(read_only=True)
    decided_by = StaffUserSerializer(read_only=True, allow_null=True)
    action = ActionSerializer(read_only=True)

    class Meta:
        model = Appeal
        fields = [
            "id",
            "action",
            "user",
            "message",
            "status",
            "decided_by",
            "decision_reason",
            "created_at",
            "decided_at",
        ]
        read_only_fields = fields


class StaffInfoRequestSerializer(serializers.ModelSerializer):
    recipient = StaffUserSerializer(read_only=True)
    asked_by = StaffUserSerializer(read_only=True)

    class Meta:
        model = InfoRequest
        fields = [
            "id",
            "recipient",
            "asked_by",
            "question",
            "answer",
            "created_at",
            "answered_at",
        ]
        read_only_fields = fields


class ViewerSerializer(serializers.Serializer):
    can_act = serializers.BooleanField(read_only=True)
    is_senior = serializers.BooleanField(read_only=True)
    conflict = serializers.CharField(read_only=True, allow_null=True)
    conflict_overridable = serializers.BooleanField(read_only=True)


class DealDisputeSerializer(serializers.ModelSerializer):
    """A disputed handoff in a case, with the deal as it stood when the dispute opened."""

    deal_id = serializers.IntegerField(read_only=True)
    listing_title = serializers.CharField(source="deal.listing.title", read_only=True)
    buyer = StaffUserSerializer(source="deal.buyer", read_only=True)
    seller = StaffUserSerializer(source="deal.seller", read_only=True)
    deal_status = serializers.CharField(source="deal.status", read_only=True)
    resolved_by = StaffUserSerializer(read_only=True, allow_null=True)

    class Meta:
        model = DealDispute
        fields = [
            "id",
            "deal_id",
            "listing_title",
            "buyer",
            "seller",
            "deal_status",
            "reason",
            "snapshot",
            "opened_at",
            "outcome",
            "resolved_by",
            "resolved_at",
            "resolution_note",
        ]
        read_only_fields = fields


class CaseDetailSerializer(serializers.Serializer):
    case = CaseRowSerializer(read_only=True)
    legal_hold = serializers.BooleanField(read_only=True)
    reports = CaseReportSerializer(many=True, read_only=True)
    actions = ActionSerializer(many=True, read_only=True)
    appeals = StaffAppealSerializer(many=True, read_only=True)
    info_requests = StaffInfoRequestSerializer(many=True, read_only=True)
    deal_disputes = DealDisputeSerializer(many=True, read_only=True)
    subject = SubjectHistorySerializer(read_only=True)
    # Reporters too, since consequences can go to them (e.g. for false reports).
    involved_users = StaffUserSerializer(many=True, read_only=True)
    reporter_records = ReporterRecordSerializer(many=True, read_only=True)
    eligible_assignees = StaffUserSerializer(many=True, read_only=True)
    viewer = ViewerSerializer(read_only=True)


class QueueSummarySerializer(serializers.Serializer):
    open = serializers.IntegerField(read_only=True)
    urgent = serializers.IntegerField(read_only=True)
    assigned_to_me = serializers.IntegerField(read_only=True)
    escalated = serializers.IntegerField(read_only=True)


class QueueQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[("active", "Open, investigating, or appealed"), *ModerationCase.Status.choices],
        required=False,
        default="active",
    )
    priority = serializers.ChoiceField(choices=ModerationCase.Priority.choices, required=False)
    school = serializers.SlugField(required=False)
    reason = serializers.ChoiceField(choices=Report.Reason.choices, required=False)
    target_type = serializers.ChoiceField(choices=Report.TargetType.choices, required=False)
    assigned = serializers.ChoiceField(
        choices=[("me", "Assigned to me"), ("none", "Unassigned")], required=False
    )
    repeat = serializers.BooleanField(required=False, default=False)


ACTIONS = [
    ("note", "Add a note"),
    ("assign", "Assign"),
    ("escalate", "Escalate to a senior moderator"),
    ("request_info", "Ask for more information"),
    ("decide_appeal", "Decide an appeal"),
    ("dismiss", "Dismiss: no violation"),
    ("resolve", "Resolve"),
    ("remove_listing", "Remove listing"),
    ("restore_listing", "Restore listing"),
    ("warn", "Send warning"),
    ("restrict", "Restrict a feature"),
    ("suspend", "Suspend account"),
    ("ban", "Ban account"),
    ("resolve_deal_dispute", "Decide a disputed handoff"),
]


class CaseActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=ACTIONS)
    reason = serializers.CharField(max_length=2000, allow_blank=True)
    user_id = serializers.IntegerField(required=False, min_value=1)
    assignee_id = serializers.IntegerField(required=False, min_value=1)
    restriction_kind = serializers.ChoiceField(
        choices=[
            (UserRestriction.Kind.SELLING, "Selling"),
            (UserRestriction.Kind.MESSAGING, "Messaging"),
            (UserRestriction.Kind.DEALS, "Buying and deals"),
        ],
        required=False,
    )
    # Restrictions: optional end. Suspensions: required end.
    until = serializers.DateTimeField(required=False, allow_null=True)
    # What the affected student is told. Blank uses a standard message for the action.
    user_message = serializers.CharField(
        max_length=2000, required=False, allow_blank=True, default=""
    )
    appeal_id = serializers.IntegerField(required=False, min_value=1)
    # Deciding a disputed handoff.
    deal_id = serializers.IntegerField(required=False, min_value=1)
    dispute_outcome = serializers.ChoiceField(choices=DealDispute.Outcome.choices, required=False)
    decision = serializers.ChoiceField(
        choices=[("uphold", "Uphold"), ("overturn", "Overturn")], required=False
    )
    # A senior moderator stepping past a conflict of interest says why.
    override_reason = serializers.CharField(
        max_length=2000, required=False, allow_blank=True, default=""
    )


class LiftRestrictionSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000, allow_blank=True)
    case_id = serializers.IntegerField(required=False, min_value=1)


class CountRowSerializer(serializers.Serializer):
    key = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)
    count = serializers.IntegerField(read_only=True)


class OffenderSerializer(serializers.Serializer):
    user = StaffUserSerializer(read_only=True)
    count = serializers.IntegerField(read_only=True)


class FalseReporterSerializer(serializers.Serializer):
    user = StaffUserSerializer(read_only=True)
    reviewed = serializers.IntegerField(read_only=True)
    upheld = serializers.IntegerField(read_only=True)


class ModerationStatsSerializer(serializers.Serializer):
    days = serializers.IntegerField(read_only=True)
    cases_opened = serializers.IntegerField(read_only=True)
    cases_resolved = serializers.IntegerField(read_only=True)
    open_now = serializers.IntegerField(read_only=True)
    urgent_open = serializers.IntegerField(read_only=True)
    median_hours_to_first_action = serializers.FloatField(read_only=True, allow_null=True)
    median_hours_to_resolve = serializers.FloatField(read_only=True, allow_null=True)
    reports = serializers.IntegerField(read_only=True)
    reports_by_reason = CountRowSerializer(many=True, read_only=True)
    reports_by_school = CountRowSerializer(many=True, read_only=True)
    outcomes = CountRowSerializer(many=True, read_only=True)
    appeals_filed = serializers.IntegerField(read_only=True)
    appeals_overturned = serializers.IntegerField(read_only=True)
    appeals_upheld = serializers.IntegerField(read_only=True)
    appeals_pending = serializers.IntegerField(read_only=True)
    repeat_offenders = OffenderSerializer(many=True, read_only=True)
    possible_false_reporters = FalseReporterSerializer(many=True, read_only=True)


class StatsQuerySerializer(serializers.Serializer):
    days = serializers.ChoiceField(choices=[(7, "7"), (30, "30"), (90, "90")], default=30)
    school = serializers.SlugField(required=False, default="")
