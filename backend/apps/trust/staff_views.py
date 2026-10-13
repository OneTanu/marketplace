"""The staff-only moderation API behind /moderation. Every view requires a moderator; a
student gets 403 even with a hand-typed URL. Decisions go through trust.services, which check
the role, school scope, and conflicts of interest, and write the audit trail."""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from apps.accounts.models import User
from apps.errors import service_validation_errors
from apps.listings.models import Listing

from . import services
from .models import Appeal, ModerationCase, UserRestriction
from .staff_serializers import (
    CaseActionSerializer,
    CaseDetailSerializer,
    CaseRowSerializer,
    LiftRestrictionSerializer,
    ModerationStatsSerializer,
    QueueQuerySerializer,
    QueueSummarySerializer,
    StaffRestrictionSerializer,
    StatsQuerySerializer,
)


class IsModerator(BasePermission):
    message = "Only moderators can open the moderation portal."

    def has_permission(self, request, view):
        return services.is_moderator(request.user)


class StaffView(GenericAPIView):
    permission_classes = [IsModerator]


@extend_schema(parameters=[QueueQuerySerializer])
class CaseQueueView(ListAPIView):
    """The moderation queue: most urgent and oldest first, with filters."""

    permission_classes = [IsModerator]
    serializer_class = CaseRowSerializer
    pagination_class = None

    def get_queryset(self):
        query = QueueQuerySerializer(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        return services.moderation_queue(self.request.user, **query.validated_data)[:200]


class QueueSummaryView(StaffView):
    serializer_class = QueueSummarySerializer

    def get(self, request):
        return Response(QueueSummarySerializer(services.queue_summary(request.user)).data)


class CaseDetailView(StaffView):
    serializer_class = CaseDetailSerializer

    def get(self, request, pk):
        case = get_object_or_404(ModerationCase, pk=pk)
        with service_validation_errors():
            detail = services.case_detail(request.user, case)
        return Response(CaseDetailSerializer(detail).data)


class CaseActionView(StaffView):
    """Take one action on a case. Every action needs a reason and is permanently recorded."""

    serializer_class = CaseActionSerializer

    @extend_schema(responses={200: CaseDetailSerializer})
    def post(self, request, pk):
        case = get_object_or_404(ModerationCase, pk=pk)
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        common = {
            "staff": request.user,
            "case": case,
            "override_reason": data["override_reason"],
        }
        action = data["action"]

        def user():
            return get_object_or_404(User, pk=data.get("user_id") or case.subject_user_id)

        def listing():
            if case.listing_id is None:
                raise_field("action", "This case isn't about a listing.")
            return get_object_or_404(Listing, pk=case.listing_id)

        with service_validation_errors():
            if action == "note":
                services.add_note(note=data["reason"], **common)
            elif action == "assign":
                assignee = get_object_or_404(User, pk=data.get("assignee_id") or request.user.pk)
                services.assign_case(
                    assignee=assignee, reason=data["reason"] or "Assigned", **common
                )
            elif action == "escalate":
                services.escalate_case(reason=data["reason"], **common)
            elif action == "request_info":
                services.request_info(user=user(), question=data["reason"], **common)
            elif action == "decide_appeal":
                if not data.get("decision"):
                    raise_field("decision", "Choose to uphold or overturn.")
                appeal = get_object_or_404(Appeal, pk=data.get("appeal_id"), action__case=case)
                services.decide_appeal(
                    staff=request.user,
                    appeal=appeal,
                    uphold=data["decision"] == "uphold",
                    reason=data["reason"],
                    override_reason=data["override_reason"],
                )
            elif action == "dismiss":
                services.dismiss_case(reason=data["reason"], **common)
            elif action == "resolve":
                services.resolve_case(reason=data["reason"], **common)
            elif action == "remove_listing":
                services.remove_listing(
                    listing=listing(),
                    reason=data["reason"],
                    user_message=data["user_message"],
                    **common,
                )
            elif action == "restore_listing":
                services.restore_listing(listing=listing(), reason=data["reason"], **common)
            elif action == "warn":
                services.warn_user(
                    user=user(), reason=data["reason"], user_message=data["user_message"], **common
                )
            elif action == "restrict":
                if not data.get("restriction_kind"):
                    raise_field("restriction_kind", "Choose what to restrict.")
                services.restrict_user(
                    user=user(),
                    kind=data["restriction_kind"],
                    reason=data["reason"],
                    expires_at=data.get("until"),
                    user_message=data["user_message"],
                    **common,
                )
            elif action == "suspend":
                services.suspend_user(
                    user=user(),
                    reason=data["reason"],
                    until=data.get("until"),
                    user_message=data["user_message"],
                    **common,
                )
            elif action == "ban":
                services.ban_user(
                    user=user(), reason=data["reason"], user_message=data["user_message"], **common
                )
        case.refresh_from_db()
        return Response(CaseDetailSerializer(services.case_detail(request.user, case)).data)


def raise_field(field: str, message: str):
    raise ValidationError({field: [message]})


class LiftRestrictionView(StaffView):
    serializer_class = LiftRestrictionSerializer

    @extend_schema(responses={200: StaffRestrictionSerializer})
    def post(self, request, pk):
        restriction = get_object_or_404(UserRestriction, pk=pk)
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        case_id = payload.validated_data.get("case_id")
        case = get_object_or_404(ModerationCase, pk=case_id) if case_id else None
        with service_validation_errors():
            restriction = services.lift_restriction(
                staff=request.user,
                restriction=restriction,
                reason=payload.validated_data["reason"],
                case=case,
            )
        return Response(StaffRestrictionSerializer(restriction).data)


@extend_schema(parameters=[StatsQuerySerializer])
class ModerationStatsView(StaffView):
    """Moderation numbers for the schools I moderate: volume, speed, outcomes, appeals, and
    patterns worth a look (repeat offenders, reporters whose reports are mostly dismissed)."""

    serializer_class = ModerationStatsSerializer

    def get(self, request):
        query = StatsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        stats = services.moderation_stats(request.user, **query.validated_data)
        return Response(ModerationStatsSerializer(stats).data)
